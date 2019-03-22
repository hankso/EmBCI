#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# File: EmBCI/embci/io/readers.py
# Author: Hankso
# Webpage: https://github.com/hankso
# Time: Tue 06 Mar 2018 20:45:20 CST

'''Readers'''

# built-in
from __future__ import print_function
import os
import time
import mmap
import socket
import warnings
import threading
import traceback
import multiprocessing as mp
from ctypes import c_bool, c_char_p, c_uint8, c_uint16, c_float

# requirements.txt: data-processing: numpy, scipy, pylsl
# requirements.txt: drivers: pyserial
import numpy as np
import scipy.io
import scipy.signal
import pylsl
import serial

from ..utils import (check_input, find_serial_ports, find_pylsl_outlets,
                     find_spi_devices, LockedFile, Singleton)
from ..utils.ads1299_api import ADS1299_API
from ..utils.esp32_api import ESP32_API
from . import logger

__dir__ = os.path.dirname(os.path.abspath(__file__))
__all__ = [
    _ + 'Reader' for _ in (
        'Files', 'Pylsl', 'Serial',
        'ADS1299SPI', 'ESP32SPI',
        'SocketTCP', 'SocketUDP',
    )
]
__all__.append('FakeDataGenerator')


class StreamControlMixin(object):
    def __init__(self):
        '''only used for testing'''
        self._flag_pause = threading.Event()
        self._flag_close = threading.Event()
        self._started = False
        self._status = 'closed'

    def start(self):
        if self._started:
            if self._status == 'paused' and self._flag_pause.is_set():
                self.resume()
            return
        self._flag_pause.set()
        self._flag_close.clear()
        self._started = True
        self._status = 'started'
        self._start_time = time.time()

    def close(self):
        if not self._started:
            return
        self._flag_close.set()
        self._flag_pause.clear()
        self._started = False  # you can re-start this reader now, enjoy~~
        self._status = 'closed'

    def restart(self):
        if self._started:
            self.close()
        self.start()

    def pause(self):
        if not self._started:
            return
        self._flag_pause.clear()
        self._status = 'paused'

    def resume(self):
        if not self._started:
            return
        self._flag_pause.set()
        self._status = 'resumed'

    @property
    def status(self):
        return self._status

    def loop(self, func, args=(), kwargs={}, before=None, after=None):
        try:
            if before is not None:
                before()
            while not self._flag_close.is_set():
                self._flag_pause.wait()
                func(*args, **kwargs)
        except Exception:
            logger.error(traceback.format_exc())
        finally:
            self.close()
            if after is not None:
                after()


class ReaderIOMixin(object):
    def set_sample_rate(self, sample_rate, sample_time=None):
        self.sample_rate = int(sample_rate)
        if sample_time is not None and sample_time > 0:
            self.sample_time = sample_time
        self.window_size = int(self.sample_rate * self.sample_time)
        if self._status in ['started', 'resumed']:
            warnings.warn('Runtime sample rate changing is not suggested.')
            # TODO: change info and re-config self._data etc. at runtime.
            #  self.restart()
        return True

    def set_channel_num(self, num_channel):
        self.num_channel = num_channel
        self.channels = ['ch%d' % i for i in range(1, num_channel + 1)]
        self.channels += ['time']
        if self._status in ['started', 'resumed']:
            warnings.warn('Runtime channel num changing is not suggested.')
            #  self.restart()
        return True

    def is_streaming(self):
        if hasattr(self, '_task'):
            alive = self._task.is_alive()
        else:
            alive = False
        return self._started and self._flag_pause.is_set() and alive

    @property
    def realtime_samplerate(self):
        if not self.is_streaming():
            return 0
        try:
            t1, t2 = (self._index - 1) % self.window_size, self._index
            dt = self._data[-1, t1] - self._data[-1, t2]
            assert dt != 0
            return self.window_size / dt
        except (TypeError, AssertionError):
            return 0

    @property
    def data_channel(self, **k):
        '''Pick num_channel x 1 fresh data from FIFO queue'''
        if self.is_streaming():
            t = time.time()
            while self._last_ch == self._index:
                time.sleep(0)
                if (time.time() - t) > (10.0 / self.sample_rate):
                    logger.warn(self.name + ' there maybe error reading data')
                    break
            self._last_ch = self._index
        return self._data[:-1, (self._last_ch - 1) % self.window_size]

    @property
    def data_frame(self):
        '''Pick num_channel x window_size (all data) from FIFO queue'''
        if self.is_streaming():
            t = time.time()
            while self._last_fr == self._index:
                time.sleep(0)
                if (time.time() - t) > (10.0 / self.sample_rate):
                    logger.warn(self.name + ' there maybe error reading data')
                    break
            self._last_fr = self._index
        return np.concatenate((
            self._data[:-1, self._last_fr:],
            self._data[:-1, :self._last_fr]), -1)

    def __getitem__(self, items):
        if isinstance(items, tuple):
            for item in items:
                self = self.__getitem__(item)
            return self
        if self._data is not None:
            return self.data_frame[items]
        warnings.warn(self.name + ' not started yet')
        return np.zeros((self.num_channel, self.window_size), 'float32')[items]

    def __repr__(self):
        if not hasattr(self, 'status'):
            msg = 'not initialized - {}'.format(self.name[1:-1])
        else:
            msg = '{} - {}'.format(self._status, self.name[1:-1])
            msg += ': {}Hz'.format(self.sample_rate)
            msg += ', {}chs'.format(self.num_channel)
            msg += ', {}sec'.format(self.sample_time)
            if self._started:
                msg += ', {}B'.format(self._data[:-1].nbytes)
        return '<{}, at {}>'.format(msg, hex(self.__hash__()))


class CompatiableMixin(object):
    '''Methods defined here are for compatibility between all Readers.'''
    def set_input_source(self, src):
        self.input_source = src
        return True

    #  enable_bias = False
    #  measure_impedance = False


class BaseReader(StreamControlMixin, ReaderIOMixin, CompatiableMixin):
    name = '[embci.io.Reader]'

    def __init__(self, sample_rate, sample_time, num_channel, name=None,
                 *a, **k):
        # update basic info with arguments
        self.name = name or self.name
        self.set_sample_rate(sample_rate, sample_time)
        self.set_channel_num(num_channel)

        # fetch data used indexs
        self._last_ch = self._last_fr = self._index

        # these attributes will be initialized in method `start`
        self._data = self._datafile = self._pidfile = self._mmapfile = None

    def __new__(cls, *a, **k):
        obj = object.__new__(cls)
        # Basic stream reader attributes.
        # These values may be accessed in another thread or process.
        # So make them multiprocessing.Value and serve as properties.
        for target, t, v in [('_index', c_uint16, 0),
                             ('_status', c_char_p, 'closed'),
                             ('_started', c_bool, False),
                             ('_start_time', c_float, time.time()),
                             ('input_source', c_char_p, 'None'),
                             ('sample_rate', c_uint16, 250),
                             ('sample_time', c_float, 2),
                             ('window_size', c_uint16, 500),
                             ('num_channel', c_uint8, 1)]:
            source = '_mp_{}'.format(target)
            setattr(obj, source, mp.Value(t, v))
            if target in cls.__dict__:
                continue
            setattr(cls, target, property(
                lambda self, attr=source: getattr(
                    getattr(self, attr), 'value'),
                lambda self, value, attr=source: setattr(
                    getattr(self, attr), 'value', value),
                None,
                'property ' + target
            ))
        # stream control used flags
        obj._flag_pause = mp.Event()
        obj._flag_close = mp.Event()
        return obj

    def start(self, method='process', *a, **k):
        name = self.name[1:-1].replace(' ', '_')
        assert '/' not in name, 'Invalid reader name `%s`!' % self.name
        self._datafile = LockedFile('/tmp/mmap_' + name)
        self._pidfile = LockedFile('/run/embci/%s.pid' % name, pidfile=True)

        # lock mmap file to protect writing permission
        f = self._datafile.acquire()
        f.write('\x00' * 4 * (self.num_channel + 1) * self.window_size)
        f.flush()
        # register memory-mapped-file as data buffer
        self._mmapfile = mmap.mmap(f.fileno(), 0)
        self._data = np.ndarray(shape=(self.num_channel + 1, self.window_size),
                                dtype=np.float32, buffer=self._mmapfile)

        StreamControlMixin.start(self)
        args = (self._save_data_in_buffer,)
        kwargs = {
            'before': lambda: self._pidfile.acquire(),
            'after': lambda: self._pidfile.release()
        }
        if method == 'block':
            self.loop(*args, **kwargs)
            return
        elif method == 'thread':
            method = threading.Thread
        elif method == 'process':
            method = mp.Process
        else:
            raise RuntimeError('unknown method {}'.format(method))
        self._task = method(target=self.loop, args=args, kwargs=kwargs)
        self._task.daemon = True
        self._task.start()

    def _save_data_in_buffer(self):
        raise NotImplementedError(self.name + ' cannot use this directly')

    def close(self, *a, **k):
        StreamControlMixin.close(self)
        time.sleep(0.5)
        self._data = self._data.copy()  # remove reference to old data buffer
        self._mmapfile.close()
        self._datafile.release()
        logger.debug(self.name + ' shut down.')


class FakeDataGenerator(BaseReader):
    '''Generate random data, same as any Reader defined in io.py'''
    __num__ = 1

    def __init__(self, sample_rate=250, sample_time=2, num_channel=1,
                 send_to_pylsl=False, *a, **k):
        super(FakeDataGenerator, self).__init__(
            sample_rate, sample_time, num_channel,
            '[Fake data generator %d]' % FakeDataGenerator.__num__)
        FakeDataGenerator.__num__ += 1
        self.input_source = 'random'
        self._send_to_pylsl = send_to_pylsl

    def start(self, *a, **k):
        if self._started:
            self.resume()
            return
        if self._send_to_pylsl:
            self._outlet = pylsl.StreamOutlet(
                pylsl.StreamInfo(
                    'FakeDataGenerator', 'Reader Outlet', self.num_channel,
                    self.sample_rate, 'float32', self.name))
            logger.debug(self.name + ' pylsl outlet established')
        super(FakeDataGenerator, self).start(*a, **k)

    def _save_data_in_buffer(self):
        time.sleep(0.8 / self.sample_rate)
        d = np.random.rand(self.num_channel) / 10
        self._data[:-1, self._index] = d[:self.num_channel]
        self._data[-1, self._index] = time.time() - self._start_time
        self._index = (self._index + 1) % self.window_size
        if self._send_to_pylsl:
            self._outlet.push_sample(d)


class FilesReader(BaseReader):
    '''
    Read data from mat, fif, csv... file and simulate as a common data reader
    '''
    __num__ = 1

    def __init__(self, filename, sample_rate=250, sample_time=2, num_channel=1,
                 *a, **k):
        super(FilesReader, self).__init__(
            sample_rate, sample_time, num_channel,
            '[Files reader %d]' % FilesReader.__num__)
        FilesReader.__num__ += 1
        self.input_source = self.filename = filename

    def start(self, *a, **k):
        if self._started:
            self.resume()
            return
        # 1. try to open data file and load data into RAM
        logger.debug(self.name + ' reading data file...')
        while not os.path.exists(self.filename):
            self.filename = check_input(
                'No such file! Please check and input correct file name: ', {})
        try:
            if self.filename.endswith('.mat'):
                actionname = os.path.basename(self.filename).split('-')[0]
                mat = scipy.io.loadmat(self.filename)
                data = mat[actionname][0]
                sample_rate = mat.get('sample_rate', None)
                logger.debug('{} load data with shape of {} @ {}Hz'.format(
                    self.name, data.shape, sample_rate))
                assert data.ndim == 2, 'Invalid data shape!'
                n = data.shape[0]
                if n < self.num_channel:
                    logger.info('{} change num_channel to {}'.format(
                        self.name, n))
                    self.num_channel = n
                    self._data = self._data[:(n + 1)]
                if sample_rate and sample_rate != self.sample_rate:
                    logger.warn('{} resample source data to {}Hz'.format(
                        self.name, self.sample_rate))
                    raise NotImplementedError
                    data = scipy.signal.resample(data, self.sample_rate)
                self._get_data = self._get_data_g(data.T)
                self._get_data.next()
            elif self.filename.endswith('.fif'):
                raise NotImplementedError
            elif self.filename.endswith('.csv'):
                data = np.loadtxt(self.filename, np.float32, delimiter=',')
                self._get_data = self._get_data_g(data)
                self._get_data.next()
            else:
                raise NotImplementedError
        except Exception as e:
            logger.error(self.name + ' {}: {}'.format(type(e), e))
            logger.error(self.name + ' Abort...')
            return
        self._start_time = time.time()

        # 2. get ready to stream data
        super(FilesReader, self).start(*a, **k)

    def _get_data_g(self, data):
        self._last_time = time.time()
        d = 0.9 / self.sample_rate
        for line in data:
            while (time.time() - self._last_time) < d:
                time.sleep(d / 2)
            self._last_time = time.time()
            if (yield line) == 'quit':
                break

    def _save_data_in_buffer(self):
        d = self._get_data.next()
        self._data[:-1, self._index] = d[:self.num_channel]
        self._data[-1, self._index] = time.time() - self._start_time
        self._index = (self._index + 1) % self.window_size


class PylslReader(BaseReader):
    '''
    Connect to a data stream on localhost:port and read data into buffer.
    There should be at least one stream available.
    '''
    __num__ = 1

    def __init__(self, sample_rate=250, sample_time=2, num_channel=0, *a, **k):
        super(PylslReader, self).__init__(
            sample_rate, sample_time, num_channel,
            '[Pylsl reader %d]' % PylslReader.__num__
        )
        PylslReader.__num__ += 1

    def start(self, *a, **k):
        '''
        Here we take window_size(sample_rate x sample_time) as max_buflen
        In doc of pylsl.StreamInlet:
            max_buflen -- Optionally the maximum amount of data to buffer (in
                  seconds if there is a nominal sampling rate, otherwise
                  x100 in samples). Recording applications want to use a
                  fairly large buffer size here, while real-time
                  applications would only buffer as much as they need to
                  perform their next calculation. (default 360)
        '''
        if self._started:
            self.resume()
            return
        # 1. find available streaming info and build an inlet
        logger.debug(self.name + ' finding availabel outlets...  ')
        args, kwargs = k.pop('args', ()), k.pop('kwargs', {})
        info = k.get('info') or find_pylsl_outlets(*args, **kwargs)
        # 1.1 set sample rate
        fs = info.nominal_srate()
        if fs not in [self.sample_rate, pylsl.IRREGULAR_RATE]:
            self.set_sample_rate(fs)
        # 1.2 set channel num
        nch = info.channel_count()
        self.input_source = '{} @ {}'.format(info.name(), info.source_id())
        if nch < self.num_channel:
            logger.info(
                '{} You want {} channels data but only {} is provided by '
                'the pylsl outlet `{}`. Change num_channel to {}'.format(
                    self.name, self.num_channel, nch, info.name(), nch))
            self.num_channel = nch
        self.set_channel_num(self.num_channel or nch)
        # 1.3 construct inlet
        super(PylslReader, self).__init__(
            int(info.nominal_srate() or 250), self.sample_time,
            self.num_channel, self.name)
        max_buflen = int(self.sample_time if info.nominal_srate() != 0
                         else int(self.window_size / 100) + 1)
        self._inlet = pylsl.StreamInlet(info, max_buflen=max_buflen)

        # 2. start streaming process to fetch data into buffer continuously
        super(PylslReader, self).start(*a, **k)
        self._start_time = info.created_at()

    def close(self):
        super(PylslReader, self).close()
        time.sleep(0.2)
        self._inlet.close_stream()

    def _save_data_in_buffer(self):
        d, t = self._inlet.pull_sample()
        self._data[:-1, self._index] = d[:self.num_channel]
        self._data[-1, self._index] = t - self._start_time
        self._index = (self._index + 1) % self.window_size


class SerialReader(BaseReader):
    '''
    Connect to a serial port and fetch data into buffer.
    There should be at least one port available.
    '''
    __num__ = 1
    _serial = serial.Serial()

    def __init__(self, sample_rate=250, sample_time=2, num_channel=1,
                 send_to_pylsl=False, *a, **k):
        super(SerialReader, self).__init__(
            sample_rate, sample_time, num_channel,
            '[Serial reader %d]' % SerialReader.__num__)
        SerialReader.__num__ += 1
        self._send_to_pylsl = send_to_pylsl

    def start(self, port=None, baudrate=115200, *a, **k):
        if self._started:
            self.resume()
            return
        # 1. find serial port and connect to it
        logger.debug(self.name + ' finding availabel ports... ')
        self._serial.port = port or find_serial_ports()
        self._serial.baudrate = baudrate
        self._serial.open()
        self.input_source = 'Serial @ {}'.format(self._serial.port)
        logger.debug(self.name + ' `%s` opened.' % port)
        n = len(self._serial.read_until().strip().split(','))
        if n < self.num_channel:
            logger.info(
                '{} You want {} channel data but only {} channels is offered '
                'by serial port you select. Change num_channel to {}'.format(
                    self.name, self.num_channel, n, n))
            self.num_channel = n
            self._data = self._data[:(n + 1)]
        # 2. start get data process
        # here we only need to check one time whether send_to_pylsl is set
        # if put this work in thread, it will be checked thousands times.
        if self._send_to_pylsl:
            self._outlet = pylsl.StreamOutlet(
                pylsl.StreamInfo(
                    'SerialReader', 'Reader Outlet', self.num_channel,
                    self.sample_rate, 'float32', self._serial.port))
            logger.debug(self.name + ' pylsl outlet established')
        super(SerialReader, self).start(*a, **k)

    def close(self):
        self._serial.close()
        super(SerialReader, self).close()

    def _save_data_in_buffer(self):
        d = np.array(self._serial.read_until().strip().split(','), np.float32)
        self._data[:-1, self._index] = d[:self.num_channel]
        self._data[-1, self._index] = time.time() - self._start_time
        self._index = (self._index + 1) % self.window_size
        if self._send_to_pylsl:
            self._outlet.push_sample(d)


class ADS1299SPIReader(BaseReader):
    '''
    Read data through SPI connection with ADS1299.
    This Reader is only used on ARM. It depends on class ADS1299_API.
    '''
    __metaclass__ = Singleton
    name = '[ADS1299 SPI reader]'
    API = ADS1299_API

    def __init__(self, sample_rate=250, sample_time=2, num_channel=1,
                 send_to_pylsl=False, *a, **k):
        super(ADS1299SPIReader, self).__init__(
            sample_rate, sample_time, num_channel)
        self._send_to_pylsl = send_to_pylsl

    def __new__(cls, sample_rate=250, sample_time=2, num_channel=1,
                send_to_pylsl=False, measure_impedance=False,
                enable_bias=True, API=None, *a, **k):
        api = (API or cls.API)()
        self = super(ADS1299SPIReader, cls).__new__(cls)
        self._api = api
        cls.enable_bias = property(
            lambda self: getattr(self._api, 'enable_bias'),
            lambda self, v: setattr(self._api, 'enable_bias', v),
            None,
            'Whether to enable BIAS output on BIAS pin.'
        )
        cls.measure_impedance = property(
            lambda self: getattr(self._api, 'measure_impedance'),
            lambda self, v: setattr(self._api, 'measure_impedance', v),
            None,
            'Whether to measure impedance in ohm or raw signal in volt.'
        )
        self.enable_bias = enable_bias
        self.measure_impedance = measure_impedance
        self.input_source = 'normal'
        return self

    def __del__(self):
        Singleton.remove(self.__class__)

    def set_sample_rate(self, rate, time=None):
        rst = self._api.set_sample_rate(rate)
        if rst is not None:
            super(ADS1299SPIReader, self).set_sample_rate(rate, time)
            if self._started:
                logger.info('{} sample rate set to {}, you may want to '
                            'restart reader now.'.format(self.name, rst))
            return True
        logger.error(self.name + ' invalid sample rate {}'.format(rate))
        return False

    def set_input_source(self, src):
        rst = self._api.set_input_source(src)
        if rst is not None:
            self.input_source = src
            logger.info(self.name + ' input source set to {}'.format(rst))
            return True
        logger.error(self.name + ' invalid input source {}'.fotmat(src))
        return False

    def start(self, device=None, *a, **k):
        if self._started:
            self.resume()
            return
        # 1. find avalable spi devices
        logger.debug(self.name + ' finding available spi devices... ')
        device = device or find_spi_devices()
        self._api.open(device)
        self._api.start(self.sample_rate)
        logger.debug(self.name + ' `/dev/spidev%d-%d` opened.' % device)
        # 2. start get data process
        if self._send_to_pylsl:
            self._outlet = pylsl.StreamOutlet(
                pylsl.StreamInfo(
                    'SPIReader', 'Reader Outlet', self.num_channel,
                    self.sample_rate, 'float32', 'spi%d-%d ' % device))
            logger.debug(self.name + ' pylsl outlet established')
        super(ADS1299SPIReader, self).start(*a, **k)

    def close(self):
        self._api.close()
        super(ADS1299SPIReader, self).close()

    def _save_data_in_buffer(self):
        d = self._api.read()
        self._data[:-1, self._index] = d[:self.num_channel]
        self._data[-1, self._index] = time.time() - self._start_time
        self._index = (self._index + 1) % self.window_size
        if self._send_to_pylsl:
            self._outlet.push_sample(d)


class ESP32SPIReader(ADS1299SPIReader):
    '''
    Read data through SPI connection with onboard ESP32.
    This Reader is only used on ARM. It depends on class ESP32_API.
    '''
    __metaclass__ = Singleton
    name = '[ESP32 SPI reader]'
    API = ESP32_API


class SocketTCPReader(BaseReader):
    '''
    A reader that recieve data from specific host and port through TCP socket.
    '''
    __num__ = 1

    def __init__(self, sample_rate=250, sample_time=2, num_channel=1, *a, **k):
        super(SocketTCPReader, self).__init__(
            sample_rate, sample_time, num_channel,
            '[Socket TCP reader %d]' % SocketTCPReader.__num__)
        SocketTCPReader.__num__ += 1

    def start(self, *a, **k):
        if self._started:
            self.resume()
            return
        # 1. IP addr and port are offered by user, connect to that host:port
        logger.debug(self.name + ' configure IP address')
        while 1:
            extra = ''
            r = check_input((
                extra + 'Please input an address "host:port".\n'
                'Type `quit` to abort.\n'
                '> 192.168.0.1:8888 (example)\n> '), {})
            extra = ''
            if r in ['quit', '']:
                raise SystemExit(self.name + ' mannually exit')
            host, port = r.replace('localhost', '127.0.0.1').split(':')
            if int(port) <= 0:
                extra = self.name + 'port must be positive number!\n'
                continue
            try:
                socket.inet_aton(host)  # check if host is valid string
                break
            except socket.error:
                extra = self.name + ' invalid addr!\n'
        # TCP IPv4 socket connection
        self._client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._client.connect((host, int(port)))
        self.input_source = ':'.join([host, port])
        # 2. read data in another thread
        super(SocketTCPReader, self).start(*a, **k)

    def close(self):
        '''
        Keep in mind that socket `client` is continously receiving from server
        in other process/thread, so directly close client is dangerous because
        client may be blocking that process/thread by client.recv(n). We need
        to let server socket close the connection.
        '''
        super(SocketTCPReader, self).close()
        self._client.send('shutdown')
        try:
            self._client.shutdown(socket.SHUT_RDWR)
            self._client.close()
        except socket.error:
            pass

    def _save_data_in_buffer(self):
        # 8-channel float32 data = 8*32bits = 32bytes
        d = np.frombuffer(self._client.recv(32), np.float32)
        self._data[:-1, self._index] = d[:self.num_channel]
        self._data[-1, self._index] = time.time() - self._start_time
        self._index = (self._index + 1) % self.window_size


class SocketUDPReader(BaseReader):
    '''
    Socket UDP client, data receiver.
    '''
    __num__ = 1

    def __init__(self, sample_rate=250, sample_time=2, num_channel=1, *a, **k):
        super(SocketUDPReader, self).__init__(
            sample_rate, sample_time, num_channel,
            '[Socket UDP reader %d]' % SocketUDPReader.__num__)
        SocketUDPReader.__num__ += 1

    def start(self, *a, **k):
        raise

    def close(self):
        raise

    def _save_data_in_buffer(self):
        # 8-channel float32 data = 8*32bits = 32bytes
        # d is np.ndarray with a shape of (8, 1)
        d = np.frombuffer(self._client.recv(32), np.float32)
        self._data[:-1, self._index] = d[:self.num_channel]
        self._data[-1, self._index] = time.time() - self._start_time
        self._index = (self._index + 1) % self.window_size


# THE END
