#!/usr/bin/env python3
# coding=utf-8
#
# File: EmBCI/embci/io/readers.py
# Authors: Hank <hankso1106@gmail.com>
# Create: 2018-03-06 20:48:40

'''
Readers represent data streams that can be started, paused, resumed and closed.
The source of streams can be various, for example:
    - Local files (.csv, .mat, .fif, etc.)
    - Network TCP/UDP sockets
    - Hardware interfaces like UART(serials) and SPI
    - Lab-streaming-layer (LSL)
    - Or even randomly generated data

Known bugs:
    1. It's not suggested to use some API across multiprocessing because the
    underlying codes may register some value/attribute/configs on specific
    process. For example, a LSL inlet cannot be used in different processes.
'''

# built-in
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
import os
import re
import time
import mmap
import socket
import warnings
import threading
import multiprocessing as mp
from ctypes import c_bool, c_char_p, c_uint8, c_uint16, c_float

# requirements.txt: data: numpy, scipy, pylsl
# requirements.txt: drivers: pyserial
import numpy as np
import scipy.io
import scipy.signal
import pylsl
import serial

from ..utils import (
    ensure_unicode, ensure_bytes, get_boolean, format_size,
    validate_filename, random_id, check_input,
    find_serial_ports, find_pylsl_outlets, find_spi_devices,
    LockedFile, Singleton, LoopTaskMixin, SkipIteration
)
from ..drivers.ads1299 import ADS1299_API
from ..drivers.esp32 import ESP32_API
from ..configs import DIR_PID, DIR_TMP
from . import logger

__all__ = ['validate_readername', 'FakeDataGenerator', ] + [
    _ + 'Reader' for _ in (
        'Files', 'LSL', 'Serial',
        'ADS1299SPI', 'ESP32SPI',
        'SocketTCP', 'SocketUDP',
    )
]

# =============================================================================
# Reader MixIn and utilities

_name_reader_pattern = re.compile(r'^(\w+)_(\d+)\.pid$')
def validate_readername(name):                                     # noqa: E302
    '''
    Find suitable name for reader instance in syntax of::
        {ReaderName} {ID}
    '''
    name = ''.join([
        c for c in validate_filename(name) if c not in '()[]'
    ]) or ('Reader ' + random_id(8))
    name = name.replace(' ', '_').replace('.', '_')
    exist_files = [
        _name_reader_pattern.findall(fn)[0]
        for fn in os.listdir(DIR_PID)
        if _name_reader_pattern.match(fn)
    ]
    ids = [int(i) for n, i in exist_files if n == name]
    return '%s_%d' % (name, list(set(range(len(ids) + 1)).difference(ids))[0])


class RStMixin(object):
    def is_streaming(self):
        if hasattr(self, '_task'):
            alive = self._task.is_alive()
        else:
            alive = False
        return alive and self.started and self.status != 'paused'

    @property
    def realtime_samplerate(self):
        if not self.is_streaming():
            return 0
        # 1. frequency of last point
        #  idx = self._index - 1
        #  dt = self._data[-1, idx] - self._data[-1, idx - 1]
        #  return 1 / dt if dt else 0

        # 2. averaged frequency of last frame
        idx = self._index
        dT = self._data[-1, idx - 1] - self._data[-1, idx]
        return self.window_size / dT if dT else 0

    def __getitem__(self, items):
        # TODO: May integret data processing algorithm in readers
        #  if isinstance(items, tuple):
        #      for item in items:
        #          self = self[item]
        #      return self
        return self._data[items]

    def __repr__(self):
        if not hasattr(self, 'status'):
            st, msg = 'not initialized', ''
        else:
            st = self.status
            msg = ' {}Hz, {}CHs, {:.2f}Sec'.format(
                self.sample_rate, self.num_channel, self.sample_time)
            if self.status != 'closed':
                msg += ', ' + format_size(self._data.nbytes)
        return '<%s (%s)%s at 0x%x>' % (self.name, st, msg, id(self))


class RIOMixin(object):
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
            # TODO: change info and re-configure self._data etc. at runtime.
            #  self.restart()
        return True

    def set_channel_num(self, num_channel):
        self.num_channel = int(num_channel)
        self.channels = ['ch%d' % i for i in range(1, num_channel + 1)]
        self.channels += ['time']
        if self.status in ['started', 'resumed']:
            warnings.warn('Runtime channel num changing is not suggested.')
            #  self.restart()
            return False
        return True

    @property
    def data_channel(self):
        '''Pick num_channel x 1 fresh data from buffer.'''
        return self.data_channel_t[:-1]

    @property
    def data_channel_t(self):
        '''Pick (num_channel + time_channel) x 1 fresh data from buffer.'''
        if self.is_streaming():
            t = time.time()
            while self._lasti[0] == self._index:
                time.sleep(0)
                if (time.time() - t) > (10.0 / self.sample_rate):
                    logger.warning(self.name + ' read data timeout')
                    break
            self._lasti[0] = self._index
        data, idx = self._data.copy(), self._lasti[0] - 1
        return data[:, idx]

    @property
    def data_frame(self):
        '''Pick num_channel x window_size from buffer.'''
        return self.data_frame_t[:-1]

    @property
    def data_frame_t(self):
        '''Pick (num_channel + time_channel) x window_size from buffer.'''
        if self.is_streaming():
            t = time.time()
            while self._lasti[1] == self._index:
                time.sleep(0)
                if (time.time() - t) > (10.0 / self.sample_rate):
                    logger.warning(self.name + ' read data timeout')
                    break
            self._lasti[1] = self._index
        data, idx = self._data.copy(), self._lasti[1]
        return np.concatenate((data[:, idx:], data[:, :idx]), -1)

    @property
    def data_all(self):
        '''
        Pick (num_channel + time_channel) x window_size from buffer.
        Start from where index equals to 0.
        '''
        if self.is_streaming():
            t = time.time()
            while self._index or self._lasti[2] == self._data[-1, self._index]:
                if self._index < self.window_size // 2:
                    time.sleep(self.sample_time * 0.4)
                else:
                    time.sleep(0)
                if (time.time() - t) > 10 * self.sample_time:
                    logger.warning(self.name + ' read data timeout')
                    break
            self._lasti[2] = self._data[-1, self._index]
        data, idx = self._data.copy(), self._index
        return np.concatenate((data[:, idx:], data[:, :idx]), -1)


class RCompatMixin(object):
    '''Methods defined here are for compatibility between all Readers.'''
    def set_channel(self, ch, en):
        print('Reader setting: {}, {}'.format(ch, en))

    #  enable_bias = False
    #  measure_impedance = False

    def _check_num_channel(self, nch):
        if nch < self.num_channel:
            logger.warning(
                '{} You want {} channels data but only {} is provided by `{}`.'
                .format(self.name, self.num_channel, nch, self.input_source))
        elif nch > self.num_channel:
            nch = self.num_channel or nch
        if nch != self.num_channel:
            logger.info('Change num_channel to %d' % nch)
            self.set_channel_num(nch)

    def _check_sample_rate(self, nfs):
        if (nfs - self.sample_rate) / self.sample_rate > 0.3:
            logger.warning('Unstable sample rate: {:.2f}/{:.2f} Hz'.format(
                nfs, self.sample_rate))
        # TODO: set sample_rate


class BaseReader(LoopTaskMixin, RIOMixin, RCompatMixin, RStMixin):
    name = 'embci.io.Reader'
    _dtype = np.dtype('float32')

    def __new__(cls, *a, **k):
        obj = LoopTaskMixin.__new__(cls)
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
        self.name = validate_readername(name or self.__class__.name)
        self._dtype = np.dtype(datatype or self._dtype)
        if get_boolean(send_pylsl):
            if self._dtype.name not in pylsl.pylsl.string2fmt:
                raise ValueError('Invalid data type: %s' % self._dtype)
            self._lsl_outlet_info = pylsl.StreamInfo(
                name=self.__class__.name, type='Reader Outlet',
                channel_count=self.num_channel, nominal_srate=self.sample_rate,
                channel_format=self._dtype.name, source_id=self.name
            )
            self._lsl_outlet = pylsl.StreamOutlet(self._lsl_outlet_info)
            logger.debug(self.name + ' pylsl outlet established')
            self._loop_args = (self._loop_func_lsl, )
        else:
            self._loop_args = (self._loop_func, )

        # Locked file used to share data among processes
        pidfn = os.path.join(DIR_PID, self.name + '.pid')
        mmapfn = os.path.join(DIR_TMP, 'mmap_' + self.name)
        self._file_pid = LockedFile(pidfn, pidfile=True)
        self._file_data = LockedFile(mmapfn)
        self._data = np.zeros(
            (self.num_channel + 1, self.window_size), self._dtype)

        # Indexs used to output data
        # 0:Channel 1:Frame 2:All 3-5: NotUsed
        self._lasti = [self._index] * 5

    def start(self, method='process', *a, **k):
        if not LoopTaskMixin.start(self):
            return False

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
        # in case that restarted with smaller window_size
        self._index = 0

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
        self._task.daemon = True  # LoopTask manager will close readers safely
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
        return True

    def _loop_func_lsl(self):
        data, ts = self._data_fetch()
        self._lsl_outlet.push_sample(data, ts)
        self._data_save(data, ts)

    def _loop_func(self):
        data, ts = self._data_fetch()
        self._data_save(data, ts)

    def _data_fetch(self):
        raise NotImplementedError(self.name + ' cannot use this directly')

    def _data_save(self, data, ts):
        data = data[:self.num_channel]
        self._data[:len(data), self._index] = data
        self._data[-1, self._index] = ts
        self._index = (self._index + 1) % self.window_size


# =============================================================================
# Readers on different input sources

class FakeDataGenerator(BaseReader):
    '''Generate random data.'''
    name = 'FDGen'

    def __init__(self, sample_rate=250, sample_time=2, num_channel=1, **k):
        k.setdefault('input_source', 'random')
        super(FakeDataGenerator, self).__init__(
            sample_rate, sample_time, num_channel, **k)

    def _data_fetch(self):
        time.sleep(0.9 / self.sample_rate)
        data = (np.random.rand(self.num_channel) - 0.5) / 100
        return data, time.time() - self.start_time


class FilesReader(BaseReader):
    '''Read data from file and simulate as a common data reader.'''

    def __init__(self, filename,
                 sample_rate=250, sample_time=2, num_channel=1, **k):
        if not os.path.exist(filename):
            raise ValueError('Data file not exist: `%s`' % filename)
        k.setdefault('input_source', filename)
        k.setdefault('name', filename + '.Reader')
        super(FilesReader, self).__init__(
            sample_rate, sample_time, num_channel, **k)

    def hook_before(self):
        '''try to open data file and load data into RAM'''
        logger.debug(self.name + ' reading data file ' + self.input_source)
        if self.input_source.endswith('.mat'):
            actionname = os.path.basename(self.input_source).split('-')[0]
            mat = scipy.io.loadmat(self.input_source)
            data = mat[actionname][0]
            sample_rate = mat.get('sample_rate', None)
            logger.debug('{} load data with shape of {}@{}Hz'.format(
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


class LSLReader(BaseReader):
    '''
    Connect to a data stream on localhost:port and read data into buffer.
    There should be at least one stream available.
    '''
    name = 'LSLReader'

    def __init__(self, sample_rate=250, sample_time=2, num_channel=0, **k):
        k['send_pylsl'] = False
        super(LSLReader, self).__init__(
            sample_rate, sample_time, num_channel, **k)

    def start(self, *a, **k):
        '''
        Here we take window_size(sample_rate x sample_time) as max_buflen
        '''
        if self.started:
            return self.resume()
        # 1. find available streaming information
        logger.debug(self.name + ' finding availabel outlets...  ')
        if a and isinstance(a[0], pylsl.StreamInfo):
            info = a[0]
        elif 'info' in k:
            info = k.pop('info')
        else:
            info = find_pylsl_outlets(*a, **k)
        self._lsl_inlet_info = info
        # 2. start streaming task to fetch data into buffer continuously
        #  self.start_time = info.created_at()
        return super(LSLReader, self).start(**k)

    def hook_before(self):
        fs = self._lsl_inlet_info.nominal_srate()
        if fs not in [self.sample_rate, pylsl.IRREGULAR_RATE]:
            self.set_sample_rate(fs)
        nch = self._lsl_inlet_info.channel_count()
        self._check_num_channel(nch)
        maxbuf = int(self.sample_time if fs else (self.window_size // 100 + 1))
        self._lsl_inlet = pylsl.StreamInlet(self._lsl_inlet_info, maxbuf)
        self.input_source = '{}@{}'.format(
            self._lsl_inlet_info.name(), self._lsl_inlet_info.source_id())

    def hook_after(self):
        time.sleep(0.2)
        self._lsl_inlet.close_stream()

    def _data_fetch(self):
        '''LSL Inlet may buffer data. So do NOT use absolute time.'''
        data, ts = self._lsl_inlet.pull_sample(5)
        if data is None:
            raise SkipIteration('bad data from %s' % self._lsl_inlet)
        #  return data, time.time() - self.start_time
        return data, ts + self._lsl_inlet.time_correction()


class SerialReader(BaseReader):
    '''
    Connect to a serial port and fetch data into buffer.
    There should be at least one port available.
    '''
    name = 'SerialReader'

    def __init__(self, sample_rate=250, sample_time=2, num_channel=1, **k):
        super(SerialReader, self).__init__(
            sample_rate, sample_time, num_channel, **k)
        self._serial = serial.Serial()

    def start(self, port=None, baudrate=115200, *a, **k):
        if self.started:
            return self.resume()
        self._serial.port = port or find_serial_ports()
        self._serial.baudrate = baudrate
        return super(SerialReader, self).start(**k)

    def hook_before(self):
        self._serial.open()
        self.input_source = 'Serial@{}'.format(self._serial.port)
        logger.debug(self.name + ' `%s` opened.' % self.input_source)
        self._check_num_channel(len(self._data_fetch()[0]))

    def hook_after(self):
        self._serial.close()

    def _data_fetch(self):
        #  data = self._serial.read_until().decode('utf-8')
        #  data = [i.strip() for i in data.split(',')]
        #  data = np.array([float(i) for i in data if i], self._dtype)
        data = np.loadtxt(self._serial, self._dtype, delimiter='.')
        return data, time.time() - self.start_time


class ADS1299SPIReader(BaseReader):
    '''
    Read data through SPI connection with ADS1299.
    This Reader is only used on ARM. It depends on class ADS1299_API.
    '''
    __metaclass__ = Singleton
    API = ADS1299_API
    name = 'ADS1299Reader'

    def __init__(self, sample_rate=250, sample_time=2, num_channel=1,
                 measure_impedance=False, enable_bias=True, API=None, **k):
        self._api = (API or self.API)()
        k.setdefault('input_source', 'normal')
        super(ADS1299SPIReader, self).__init__(
            sample_rate, sample_time, num_channel, **k)
        self.enable_bias = enable_bias
        self.measure_impedance = measure_impedance

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
        self._api._dev = device and tuple(device) or find_spi_devices()
        return super(ADS1299SPIReader, self).start(**k)

    def hook_before(self):
        self._api.open(self._api._dev)
        self._api.start(self.sample_rate)
        logger.info(self.name + ' `/dev/spidev%d-%d` opened.' % self._api._dev)
        #  self._check_num_channel()

    def hook_after(self):
        self._api.close()

    def _data_fetch(self):
        return self._api.read()


class ESP32SPIReader(ADS1299SPIReader):
    '''
    Read data through SPI connection with onboard ESP32.
    This Reader is only used on ARM. It depends on class ESP32_API.
    '''
    API = ESP32_API
    name = 'ESP32Reader'


class SocketTCPReader(BaseReader):
    '''
    A reader that recieve data from specific host and port through TCP socket.
    '''
    name = 'SocketTCPReader'

    def __init__(self, sample_rate=250, sample_time=2, num_channel=1, **k):
        super(SocketTCPReader, self).__init__(
            sample_rate, sample_time, num_channel, **k)
        self._client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def hook_before(self):
        # IP addr and port are offered by user, connect to host:port
        logger.debug(self.name + ' configure IP address')
        extra = ''
        for i in range(5):
            rst = check_input((
                extra + 'Please input an address "host:port".\n'
                'Type `quit` to abort.\n'
                '> 192.168.0.1:8888 (example)\n> '
            ), {}).replace('localhost', '127.0.0.1')
            extra = ''
            if rst in ['quit', '']:
                raise RuntimeError(self.name + ' manual exit.')
            try:
                if ':' not in rst:
                    host, port = rst, 80
                else:
                    host, port = rst.split(':')
                socket.inet_aton(host)  # check if host is valid string
                port = int(port)
                assert port > 0
            except socket.error:
                extra = self.name + ' Invalid host: `%s`\n' % host
                continue
            except (ValueError, AssertionError):
                extra = self.name + ' Invalid port: `%s`\n' % port
                continue
            else:
                break
        else:
            raise RuntimeError(self.name + ' five times failed.')
        # TCP IPv4 socket connection
        self._client.connect((host, port))
        self._client_size = 512 * self._dtype.itemsize
        self.input_source = '{}:{}'.format(host, port)
        self._check_num_channel(len(self._data_fetch()[0]))
        self._client_size = self.num_channel * self._dtype.itemsize

    def hook_after(self):
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
    name = 'SocketUDPReader'

    def __init__(self, sample_rate=250, sample_time=2, num_channel=1, **k):
        # sample_rate, sample_time, num_channel, name=None
        # input_source=None, send_pylsl=False, datatype=None
        super(SocketUDPReader, self).__init__(
            sample_rate, sample_time, num_channel, **k)
        raise NotImplementedError


# THE END
