#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# File: EmBCI/embci/io/readers.py
# Author: Hankso
# Webpage: https://github.com/hankso
# Time: Tue 06 Mar 2018 20:45:20 CST

'''
Readers represent data streams that can be started, paused, resumed and closed.
The source of streams can be various, for example:
    - Local files (.csv, .mat, .fif, etc.)
    - Network TCP/UDP sockets
    - Hardware interfaces like UART(serials) and SPI
    - Lab-streaming-layer (LSL)
    - Or even randomly generated data
'''

# built-in
from __future__ import print_function
import os
import re
import time
import mmap
import atexit
import socket
import warnings
import traceback
import threading
import multiprocessing as mp
from ctypes import c_bool, c_char_p, c_uint8, c_uint16, c_float

# requirements.txt: data-processing: numpy, scipy, pylsl
# requirements.txt: drivers: pyserial
import numpy as np
import scipy.io
import scipy.signal
import pylsl
import serial

from ..utils import (
    strtypes, ensure_unicode, ensure_bytes, get_boolean, format_size,
    validate_filename, random_id, check_input,
    find_serial_ports, find_pylsl_outlets, find_spi_devices,
    LockedFile, Singleton, LoopTaskMixin
)
from ..utils.ads1299_api import ADS1299_API
from ..utils.esp32_api import ESP32_API
from ..configs import DIR_PID, DIR_TMP
from . import logger

__all__ = ['FakeDataGenerator', ] + [
    _ + 'Reader' for _ in (
        'Files', 'Pylsl', 'Serial',
        'ADS1299SPI', 'ESP32SPI',
        'SocketTCP', 'SocketUDP',
    )
]

_readers = []
def ensure_readers_closed():                                       # noqa: E302
    '''
    In case of exiting python without calling `reader.close`.
    This function will be called by `atexit`, not for runtime usage.
    '''
    for reader in _readers:
        try:
            if reader.started:
                reader.close()
        except Exception:
            traceback.print_exc()
    del _readers[:]
atexit.register(ensure_readers_closed)                             # noqa: E305


_name_pattern = re.compile(r'^(\w+)_(\d+).pid$')
def valid_name(name):                                              # noqa: E302
    '''
    Find suitable name for reader instance in syntax of::
        {ReaderName} {ID}
    '''
    name = ''.join([
        c for c in validate_filename(name) if c not in '()[]'
    ]) or ('Reader ' + random_id(8))
    nows = name.replace(' ', '_').replace('.', '_')
    exist_files = [
        _name_pattern.findall(fn)[0]
        for fn in os.listdir(DIR_PID)
        if _name_pattern.match(fn)
    ]
    for i in range(0, 100):
        if (nows, str(i)) in exist_files:
            continue
        return '%s %d' % (name, i)
    raise RuntimeError('Invalid name: `%s`' % name)


class ReaderIOMixin(object):
    def set_sample_rate(self, sample_rate, sample_time=None):
        self.sample_rate = int(sample_rate)
        if sample_time is not None and sample_time > 0:
            self.sample_time = sample_time
        self.window_size = int(self.sample_rate * self.sample_time)
        self.sample_time = float(self.window_size) / self.sample_rate
        if self.status in ['started', 'resumed']:
            warnings.warn('Runtime sample rate changing is not suggested.')
            logger.info('{} sample rate set to {}, you may want to restart '
                        'reader now.'.format(self.name, self.sample_rate))
            return False
            # TODO: change info and re-config self._data etc. at runtime.
            #  self.restart()
        return True

    def set_channel_num(self, num_channel):
        self.num_channel = num_channel
        self.channels = ['ch%d' % i for i in range(1, num_channel + 1)]
        self.channels += ['time']
        if self.status in ['started', 'resumed']:
            warnings.warn('Runtime channel num changing is not suggested.')
            #  self.restart()
            return False
        return True

    def is_streaming(self):
        if hasattr(self, '_task'):
            alive = self._task.is_alive()
        else:
            alive = False
        return self.status not in ['closed', 'paused'] and alive

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
    def data_channel(self):
        '''Pick num_channel x 1 fresh data from FIFO queue'''
        if self.is_streaming():
            t = time.time()
            while self._lasti[0] == self._index:
                time.sleep(0)
                if (time.time() - t) > (10.0 / self.sample_rate):
                    logger.warning(self.name + ' read data timeout')
                    break
            self._lasti[0] = self._index
        return self._data[:-1, (self._lasti[0] - 1) % self.window_size]

    @property
    def data_frame(self):
        '''Pick num_channel x window_size (all data) from FIFO queue'''
        if self.is_streaming():
            t = time.time()
            while self._lasti[1] == self._index:
                time.sleep(0)
                if (time.time() - t) > (10.0 / self.sample_rate):
                    logger.warning(self.name + ' read data timeout')
                    break
            self._lasti[1] = self._index
        data, idx = self._data.copy(), self._lasti[1]
        return np.concatenate((data[:-1, idx:], data[:-1, :idx]), -1)

    @property
    def data_all(self):
        '''Pick (num_channel + time_channel) x window_size from FIFO queue'''
        if self.is_streaming():
            t = time.time()
            while self._index != 0:
                time.sleep(0)
                if (time.time() - t) > 10 * self.sample_time:
                    logger.warning(self.name + ' read data timeout')
                    break
        data, idx = self._data.copy(), self._index
        return np.concatenate((data[:, idx:], data[:, :idx]), -1)

    def register_buffer(self, obj):
        if not isinstance(obj, strtypes):
            obj = id(obj)
        if obj not in self._data_buffer:
            self._data_buffer[obj] = []

    def unregister_buffer(self, obj):
        if not isinstance(obj, strtypes):
            obj = id(obj)
        return np.concatenate(self._data_buffer.pop(obj, []), -1)

    def __getitem__(self, items):
        if isinstance(items, tuple):
            for item in items:
                self = self[item]
            return self
        return self._data[items]

    def __repr__(self):
        if not hasattr(self, 'status'):
            st, msg = 'not initialized', ''
        else:
            st = self.status
            msg = ': {}Hz, {}CHs, {:.2f}Sec'.format(
                self.sample_rate, self.num_channel, self.sample_time)
            if self.status != 'closed':
                msg += ', ' + format_size(self._data[:-1].nbytes)
        return '<%s (%s)%s at 0x%x>' % (self.name, st, msg, id(self))


class CompatiableMixin(object):
    '''Methods defined here are for compatibility between all Readers.'''
    def set_channel(self, ch, en):
        print('Reader setting: {}, {}'.format(ch, en))

    #  enable_bias = False
    #  measure_impedance = False


class BaseReader(LoopTaskMixin, ReaderIOMixin, CompatiableMixin):
    name = 'embci.io.Reader'
    _dtype = np.dtype('float32')

    def __new__(cls, *a, **k):
        obj = object.__new__(cls)
        # Basic stream reader attributes.
        # These values may be accessed in another thread or process.
        # So make them multiprocessing.Value and serve as properties.
        for target, t, v in [
            ('_index',         c_uint16,  0),
            ('__status__',     c_char_p,  b'closed'),
            ('__started__',    c_bool,    False),
            ('start_time',     c_float,   time.time()),
            ('sample_rate',    c_uint16,  250),
            ('sample_time',    c_float,   2),
            ('window_size',    c_uint16,  500),
            ('num_channel',    c_uint8,   1)
        ]:
            source = '_mp_{}'.format(target)
            setattr(obj, source, mp.Value(t, v))
            if target in cls.__dict__:
                continue
            setattr(cls, target, property(
                fget=lambda self, attr=source: getattr(self, attr).value,
                fset=lambda self, value, attr=source: setattr(
                    getattr(self, attr), 'value', value),
                fdel=None, doc='property `%s`' % target))
        # input source indicate data source of stream
        obj._mp_input_source = mp.Value(c_char_p,  b'')
        cls.input_source = property(
            fget=lambda self: ensure_unicode(self._mp_input_source.value),
            fset=lambda self, value: setattr(
                self._mp_input_source, 'value', ensure_bytes(value)),
            fdel=None, doc='Data source of stream.')
        # stream control used flags for `embci.utils.LoopTaskMixin`
        obj.__flag_pause__ = mp.Event()
        obj.__flag_close__ = mp.Event()
        _readers.append(obj)
        return obj

    def __init__(self, sample_rate, sample_time, num_channel, name=None,
                 input_source=None, send_pylsl=False, datatype=None, *a, **k):
        # Update basic info with arguments
        self.set_sample_rate(sample_rate, sample_time)
        self.set_channel_num(num_channel)
        self.input_source = input_source or 'Unknown'

        # Broadcast data to a lab-streaming-layer outlet.  Here we only need
        # to check one time whether send_pylsl is True. If put this work in
        # loop task, it will be checked thousands times.
        self.name = valid_name(name or self.__class__.name)
        self._dtype = np.dtype(datatype or self._dtype)
        if get_boolean(send_pylsl):
            if self._dtype.name not in pylsl.pylsl.string2fmt:
                raise ValueError('Invalid data type: %s' % self._dtype)
            info = pylsl.StreamInfo(
                name=self.__class__.name, type='Reader Outlet',
                channel_count=self.num_channel, nominal_srate=self.sample_rate,
                channel_format=self._dtype.name, source_id=self.name
            )
            self._lsl_outlet = pylsl.StreamOutlet(info)
            logger.debug(self.name + ' pylsl outlet established')
            self._loop_args = (self._loop_func_lsl, )
        else:
            self._loop_args = (self._loop_func, )

        # Locked file used to share data among processes
        name = self.name.replace(' ', '_').replace('.', '_')
        filename = os.path.join(DIR_PID, name + '.pid')
        self._file_pid = LockedFile(filename, pidfile=True)
        self._file_data = LockedFile(os.path.join(DIR_TMP, 'mmap_' + name))
        self._data = np.zeros(
            (self.num_channel + 1, self.window_size), self._dtype)
        self._data_buffer = []  # TODO: reader._data_buffer name & multiprocess

        # Indexs used to output data
        # 0:Channel 1:Frame 2:All 3-5: NotUsed
        self._lasti = [self._index] * 5

    def start(self, method='process', *a, **k):
        if not LoopTaskMixin.start(self):
            return False
        self._hook_before()

        # lock files to protect writing permission
        self._file_pid.acquire()
        shape = ((self.num_channel + 1), self.window_size)
        f = self._file_data.acquire()
        f.write('\x00' * shape[0] * shape[1] * self._dtype.itemsize)
        f.flush()

        # register memory-mapped-file as data buffer
        self._file_mmap = mmap.mmap(f.fileno(), 0)
        self._data = np.ndarray(
            shape=shape, dtype=self._dtype, buffer=self._file_mmap)

        if method == 'block':
            self.loop(*self._loop_args)
            return True
        elif method == 'thread':
            method = threading.Thread
        elif method == 'process':
            method = mp.Process
        else:
            raise RuntimeError('unknown method {}'.format(method))
        self._task = method(target=self.loop, args=self._loop_args)
        self._task.daemon = True
        self._task.start()
        return True

    def close(self, *a, **k):
        if not LoopTaskMixin.close(self):
            return False
        self._data = self._data.copy()  # remove reference to old data buffer
        self._file_mmap.close()
        self._file_data.release()
        self._file_pid.release()
        logger.debug(self.name + ' stream stopped')
        self._hook_after()
        return True

    def _hook_before(self):
        '''Hook function executed outside task(block/thread/process)'''
        pass

    def _hook_after(self):
        '''Hook function executed outside task(block/thread/process)'''
        pass

    def _loop_func_lsl(self):
        data, ts = self._data_fetch()
        self._lsl_outlet.push_sample(data, ts)
        for id in self._data_buffer:
            self._data_buffer[id].append(data)
        self._data_save(data, ts)

    def _loop_func(self):
        data, ts = self._data_fetch()
        for id in self._data_buffer:
            self._data_buffer[id].append(data)
        self._data_save(data, ts)

    def _data_fetch(self):
        raise NotImplementedError(self.name + ' cannot use this directly')

    def _data_save(self, data, ts):
        data = data[:self.num_channel]
        self._data[:len(data), self._index] = data
        self._data[-1, self._index] = ts
        self._index = (self._index + 1) % self.window_size


class FakeDataGenerator(BaseReader):
    '''
    Generate random data, same as any Reader defined in `embci/io/readers.py`
    '''
    name = 'Fake data generator'

    def __init__(self, sample_rate=250, sample_time=2, num_channel=1, **k):
        k.setdefault('input_source', 'random')
        super(FakeDataGenerator, self).__init__(
            sample_rate, sample_time, num_channel, **k)

    def _data_fetch(self):
        time.sleep(0.8 / self.sample_rate)
        data = np.random.rand(self.num_channel) / 10
        return data, time.time() - self.start_time


class FilesReader(BaseReader):
    '''
    Read data from mat, fif, csv... file and simulate as a common data reader
    '''
    name = 'Files reader'

    def __init__(self, filename,
                 sample_rate=250, sample_time=2, num_channel=1, **k):
        if not os.path.exist(filename):
            raise ValueError('Data file not exist: `%s`' % filename)
        k.setdefault('input_source', filename)
        super(FilesReader, self).__init__(
            sample_rate, sample_time, num_channel, **k)

    def start(self, *a, **k):
        if self.started:
            return self.resume()
        # 1. try to open data file and load data into RAM
        logger.debug(self.name + ' reading data file...')
        try:
            if self.input_source.endswith('.mat'):
                actionname = os.path.basename(self.input_source).split('-')[0]
                mat = scipy.io.loadmat(self.input_source)
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
                    logger.warning('{} resample source data to {}Hz'.format(
                        self.name, self.sample_rate))
                    raise NotImplementedError
                    data = scipy.signal.resample(data, self.sample_rate)
                self._get_data = self._get_data_g(data.T)
                self._get_data.next()
            elif self.input_source.endswith('.fif'):
                raise NotImplementedError
            elif self.input_source.endswith('.csv'):
                data = np.loadtxt(self.input_source, np.float32, delimiter=',')
                self._get_data = self._get_data_g(data)
                self._get_data.next()
            else:
                raise NotImplementedError
        except Exception:
            logger.error(traceback.format_exc())
            logger.error(self.name + ' Abort...')
            return False
        # 2. get ready to stream data
        return super(FilesReader, self).start(*a, **k)

    def _get_data_g(self, data):
        self._last_time = time.time()
        d = 0.9 / self.sample_rate
        for line in data:
            while (time.time() - self._last_time) < d:
                time.sleep(d / 2)
            self._last_time = time.time()
            if (yield line) == 'quit':
                break

    def _data_fetch(self):
        return self._get_data.next(), time.time() - self.start_time


class PylslReader(BaseReader):
    '''
    Connect to a data stream on localhost:port and read data into buffer.
    There should be at least one stream available.
    '''
    name = 'Pylsl reader'

    def __init__(self, sample_rate=250, sample_time=2, num_channel=0, **k):
        k['send_pylsl'] = False
        super(PylslReader, self).__init__(
            sample_rate, sample_time, num_channel, **k)

    def start(self, *a, **k):
        '''
        Here we take window_size(sample_rate x sample_time) as max_buflen
        '''
        if self.started:
            return self.resume()
        # 1. find available streaming info and build an inlet
        logger.debug(self.name + ' finding availabel outlets...  ')
        args, kwargs = k.pop('args', ()), k.pop('kwargs', {})
        info = k.get('info') or find_pylsl_outlets(*args, **kwargs)
        # 1.1 set sample rate
        fs = info.nominal_srate()
        if fs not in [self.sample_rate, pylsl.IRREGULAR_RATE]:
            self.set_sample_rate(fs)
        # 1.2 set channel num
        self.input_source = '{} @ {}'.format(info.name(), info.source_id())
        nch = info.channel_count()
        if nch < self.num_channel:
            logger.info(
                '{} You want {} channels data but only {} is provided by '
                'the pylsl outlet `{}`. Change num_channel to {}'.format(
                    self.name, self.num_channel, nch, info.name(), nch))
        elif self.num_channel:
            nch = self.num_channel
        self.set_channel_num(nch)
        # 1.3 construct inlet
        self.set_sample_rate(info.nominal_srate() or self.sample_rate)
        max_buflen = int(self.sample_time if info.nominal_srate() != 0
                         else int(self.window_size / 100) + 1)
        self._lsl_inlet = pylsl.StreamInlet(info, max_buflen=max_buflen)

        # 2. start streaming process to fetch data into buffer continuously
        rst = super(PylslReader, self).start(*a, **k)
        self.start_time = info.created_at()
        return rst

    def _hook_after(self):
        time.sleep(0.2)
        self._lsl_inlet.close_stream()

    def _data_fetch(self):
        data, ts = self._lsl_inlet.pull_sample()
        return data, ts - self.start_time


class SerialReader(BaseReader):
    '''
    Connect to a serial port and fetch data into buffer.
    There should be at least one port available.
    '''
    name = 'Serial reader'

    def __init__(self, sample_rate=250, sample_time=2, num_channel=1, **k):
        super(SerialReader, self).__init__(
            sample_rate, sample_time, num_channel, **k)
        self._serial = serial.Serial()

    def start(self, port=None, baudrate=115200, *a, **k):
        if self.started:
            return self.resume()
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
        return super(SerialReader, self).start(*a, **k)

    def _hook_after(self):
        self._serial.close()

    def _data_fetch(self):
        data = self._serial.read_until().strip().split(',')
        return np.array(data, self._dtype), time.time() - self.start_time


class ADS1299SPIReader(BaseReader):
    '''
    Read data through SPI connection with ADS1299.
    This Reader is only used on ARM. It depends on class ADS1299_API.
    '''
    __metaclass__ = Singleton
    name = 'ADS1299 SPI reader'
    API = ADS1299_API

    def __init__(self, sample_rate=250, sample_time=2, num_channel=1,
                 measure_impedance=False, enable_bias=True, API=None, **k):
        k.setdefault('input_source', 'normal')
        super(ADS1299SPIReader, self).__init__(
            sample_rate, sample_time, num_channel, **k)
        self.enable_bias = enable_bias
        self.measure_impedance = measure_impedance
        self._api = (API or self.API)()

    def __del__(self):
        Singleton.remove(self.__class__)

    def set_channel(self, ch, en):
        if self._api.set_channel(ch, get_boolean(en)) is None:
            logger.error(self.name + ' invalid channel {}'.format(ch))
            return False
        logger.debug('{} channel {} {}'.format(
            self.name, ch, 'enabled' if en else 'disabled'))
        return True

    @property
    def enable_bias(self):
        '''Whether to enable BIAS output on BIAS pin'''
        return self._api.enable_bias

    @enable_bias.setter
    def enable_bias(self, value):
        self._api.enable_bias = value

    @property
    def measure_impedance(self):
        '''Whether to measure impedance in Ohm or raw signal in Volt'''
        return self._api.measure_impedance

    @measure_impedance.setter
    def measure_impedance(self, value):
        self._api.measure_impedance = value

    def set_sample_rate(self, rate, time=None):
        if self._api.set_sample_rate(rate) is None:
            logger.error(self.name + ' invalid sample rate {}'.format(rate))
            return False
        return super(ADS1299SPIReader, self).set_sample_rate(rate, time)

    @property
    def input_source(self):
        return ensure_unicode(self._mp_input_source.value)

    @input_source.setter
    def input_source(self, src):
        if self._api.set_input_source(src) is None:
            logger.error(self.name + ' invalid input source {}'.format(src))
            return False
        self._mp_input_source.value = ensure_bytes(src)
        logger.info(self.name + ' input source set to {}'.format(src))
        return True

    def start(self, device=None, *a, **k):
        if self.started:
            return self.resume()
        # 1. find avalable spi devices
        logger.debug(self.name + ' finding available spi devices... ')
        device = device or find_spi_devices()
        self._api.open(device)
        self._api.start(self.sample_rate)
        logger.debug(self.name + ' `/dev/spidev%d-%d` opened.' % device)
        return super(ADS1299SPIReader, self).start(*a, **k)

    def _hook_after(self):
        self._api.close()

    def _data_fetch(self):
        return self._api.read(), time.time() - self.start_time


class ESP32SPIReader(ADS1299SPIReader):
    '''
    Read data through SPI connection with onboard ESP32.
    This Reader is only used on ARM. It depends on class ESP32_API.
    '''
    name = 'ESP32 SPI reader'
    API = ESP32_API


class SocketTCPReader(BaseReader):
    '''
    A reader that recieve data from specific host and port through TCP socket.
    '''
    name = 'Socket TCP reader'

    def __init__(self, sample_rate=250, sample_time=2, num_channel=1, **k):
        super(SocketTCPReader, self).__init__(
            sample_rate, sample_time, num_channel, **k)

    def start(self, *a, **k):
        if self.started:
            return self.resume()
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
        self._client_size = self.num_channel * self._dtype.itemsize  # in bytes
        return super(SocketTCPReader, self).start(*a, **k)

    def _hook_after(self):
        '''
        Keep in mind that socket `client` is continously receiving from server
        in other process/thread, so directly close client is dangerous because
        client may be blocking that process/thread by client.recv(n). We need
        to let server socket close the connection.
        '''
        self._client.send('shutdown')
        try:
            self._client.shutdown(socket.SHUT_RDWR)
            self._client.close()
        except socket.error:
            pass

    def _data_fetch(self):
        data = self._client.recv(self._client_size)
        return np.frombuffer(data, self._dtype), time.time() - self.start_time


class SocketUDPReader(SocketTCPReader):
    '''Socket UDP client, data receiver. Under development.'''
    name = 'Socket UDP reader'

    def __init__(self, sample_rate=250, sample_time=2, num_channel=1, **k):
        # sample_rate, sample_time, num_channel, name=None
        # input_source=None, send_pylsl=False, datatype=None
        super(SocketUDPReader, self).__init__(
            sample_rate, sample_time, num_channel)
        raise NotImplementedError


# THE END
