#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# File: EmBCI/embci/io.py
# Author: Hankso
# Webpage: https://github.com/hankso
# Time: Tue 06 Mar 2018 20:45:20 CST

# built-in
from __future__ import print_function
import os
import re
import sys
import time
import mmap
import socket
import select
import warnings
import threading
import traceback
import multiprocessing as mp
from ctypes import c_bool, c_char_p, c_uint8, c_uint16, c_float

# requirements.txt: data-processing: numpy, scipy, pylsl
# requirements.txt: bio-signal: mne
# requirements.txt: drivers: pyserial
import numpy as np
import scipy.io
import scipy.signal
import pylsl
import mne
import serial

from .utils import (mkuserdir, check_input, get_label_dict, ensure_unicode,
                    find_serial_ports, find_pylsl_outlets, find_spi_devices,
                    config_logger, duration,
                    LockedFile, TempStream, Singleton)
from .gyms import TorcsEnv, PlaneClient
from .utils.ads1299_api import ADS1299_API
from .utils.esp32_api import ESP32_API
from .constants import command_dict_null, command_dict_plane
from .configs import DATADIR

# ============================================================================
# constants

__dir__ = os.path.dirname(os.path.abspath(__file__))
logger = config_logger()


# ============================================================================
# save and load utilities

def create_data_dict(data, label='default', sample_rate=500, suffix=None):
    '''
    Create a data_dict that can be saved by function `save_data`.

    Parameters
    ----------
    data : ndarray | array list | instance of mne.Raw[Array]
        2d or 3d array with a shape of [n_sample x ]num_channel x window_size
    label : str
        Action name, data label. Char '-' is not suggested in label.
    sample_rate : int
        Sample rate of data, default set to 500Hz.
    suffix : str
        Currently supported formats are MATLAB-style '.mat'(default),
        MNE-style '.fif[.gz]' and raw text '.csv'.

    Returns
    -------
    data_dict : dict
        {'data': array, 'label': str, 'sample_rate': int, ...}
    '''
    data_dict = {
        'label': str(label),
        'sample_rate': int(sample_rate)
    }
    if suffix is not None:
        data_dict['suffix'] = str(suffix)

    if isinstance(data, mne.io.BaseRaw):
        data_dict['info'] = data.info
        data_dict['sample_rate'] = data.info['sfreq']
        # 1 x num_channel x window_size
        data = data.get_data()[np.newaxis, :, :]
    elif data.ndim == 1:
        # 1 x 1 x window_size
        data = data[np.newaxis, np.newaxis, :]
    elif data.ndim == 2:
        # 1 x num_channel x window_size
        data = data[np.newaxis]
    elif data.ndim > 3:
        raise ValueError('data array with too many dimensions')

    data_dict['data'] = data
    return data_dict


@mkuserdir
def save_data(username, data_dict, suffix='.mat', summary=False):
    '''
    Save data into ${DATADIR}/${username}/${label}-${num}.${suffix}

    Parameters
    ----------
    username : str
    data_dict : dict
        created by function create_data_dict(data, label, format, sample_rate)
    suffix : str
        Currently supported formats are MATLAB-style '.mat'(default),
        MNE-style '.fif[.gz]' and raw text '.csv'. Format setting in
        data_dict will overwrite this argument.
    summary : bool
        Whether to print summary of currently saved data, default `False`.

    Examples
    --------
    >>> data = np.random.rand(8, 1000) # 8chs x 4sec x 250Hz data
    >>> save_data('test', create_data_dict(data, 'random_data', 250))
    (8, 1000) data saved to ${DATADIR}/test/random_data-1.mat

    >>> raw = mne.io.RawArray(data, mne.create_info(8, 250))
    >>> save_data('test', create_data_dict(raw, format='fif.gz'))
    (8, 1000) data saved to ${DATADIR}/test/default-1.fif.gz
    '''
    try:
        label = data_dict['label']
        sample_rate = data_dict['sample_rate']
    except Exception as e:
        raise TypeError('{} {}\n`data_dict` object created by function '
                        '`create_data_dict` is suggested.'.format(
                            e.__class__.__name__.lower(), e.args[0]))

    # scan how many data files already there
    label_dict = get_label_dict(username)[0]
    num = label_dict.get(label, 0) + 1
    suffix = data_dict.pop('suffix', suffix)
    # function create_data_dict maybe offer mne.Info object
    info = data_dict.pop(
        'info', mne.create_info(data_dict['data'].shape[1], sample_rate))
    data = data_dict.pop('data', [])

    for sample in data:
        fn = os.path.join(
            DATADIR, username, '{}-{}{}'.format(label, num, suffix))
        num += 1
        try:
            if suffix == '.mat':
                data_dict['data'] = sample
                scipy.io.savemat(fn, data_dict, do_compression=True)
            elif suffix == '.csv':
                np.savetxt(fn, sample, delimiter=',')
            elif suffix in ['.fif', '.fif.gz']:
                # mute mne.io.BaseRaw.save info from stdout and stderr
                with TempStream(stdout=None, stderr=None):
                    mne.io.RawArray(sample, info).save(fn)
            else:
                raise ValueError('format `%s` is not supported.' % suffix)

            logger.info('Save {} data to {}'.format(sample.shape, fn))
        except Exception:
            if os.path.exists(fn):
                os.remove(fn)
            num -= 1
            logger.warn('Save {} failed.\n{}'.format(
                fn, traceback.format_exc()))

    if summary:
        print(get_label_dict(username)[1])


def load_label_data(username, label='default'):
    '''
    Load all data files that match ${DATADIR}/${username}/${label}-*.*

    Parameters
    ----------
    username : str
    label : str

    Returns
    -------
    data_list : list
    '''
    data_list = []
    userdir = os.path.join(DATADIR, username)
    for fn in sorted(os.listdir(userdir)):
        if not fn.startswith(label):
            continue
        name, suffix = os.path.splitext(fn)
        if suffix == '.gz':
            name, suffix = os.path.splitext(name)
        fn = os.path.join(userdir, fn)
        try:
            if suffix == '.mat':
                data = scipy.io.loadmat(fn)['data']
                if data.ndim != 2:
                    raise IOError('data file {} not support'.format(fn))
            elif suffix == '.csv':
                data = np.loadtxt(fn, np.float32, delimiter=',')
            elif suffix == '.fif':
                with TempStream(stdout=None, stderr=None):
                    #  data = mne.io.RawFIF(fn).get_data()
                    data = mne.io.RawFIF(fn, preload=True)._data
            else:
                raise ValueError('format `%s` is not supported.' % suffix)
            data_list.append(data)
            logger.info('Load {} data from {}'.format(data.shape, fn))
        except Exception:
            logger.warn('Load {} failed.\n{}'.format(
                fn, traceback.format_exc()))
    return data_list


@mkuserdir
def load_data(username, pick=None, summary=True):
    '''
    Load all data files under directory ${DATADIR}/${username}

    Parameters
    ----------
    username : str
    pick : str | list or tuple of str | regex pattern | function
        load data files whose label name:
        equal to | inside | match | return True by appling `pick`
    summary : bool
        whether to print summary of currently saved data, default `False`.

    Returns
    -------
    out : tuple
        (data_array, label_list)
    data_array : ndarray
        3D array with a shape of n_samples x num_channel x window_size
    label_list : list
        String list with a length of n_samples. Each element indicate
        label(action name) of corresponding data sample.

    Examples
    --------
    >>> data, label = load_data('test')
    >>> data.shape, label
    ((5, 8, 1000), ['default', 'default', 'default', 'right', 'left'])

    >>> _, _ = load_data('test', pick=('left', 'right'), summary=True)
    There are 3 actions with 5 data recorded.
      * default        3
        default-1.fif.gz
        default-2.fif.gz
        default-3.mat
      * right          1
        right-1.mat
      * left           1
        left-1.fif
    There are 2 actions with 2 data loaded.
      + left     1
      + right    1
    '''
    data_array = []
    label_list = []
    action_dict, msg = get_label_dict(username)

    def filterer(action):
        if isinstance(pick, str):
            return action == pick
        if isinstance(pick, (tuple, list)):
            return action in pick
        if isinstance(pick, re._pattern_type):
            return bool(pick.match(action))
        if callable(pick):
            return pick(action)
        return True

    actions = filter(filterer, action_dict)
    for action in actions:
        data_list = load_label_data(username, action)
        data_array.extend(data_list)
        label_list.extend([action] * len(data_list))

    if summary:
        msg += '\nThere are {} actions with {} data loaded.'.format(
            len(actions), len(data_array))
        if len(data_array):
            maxname = max([len(_) for _ in actions]) + 4
            msg += ('\n  + ' + '\n  + '.join(
                [action.ljust(maxname) + str(label_list.count(action))
                 for action in actions]))
        print(msg.strip())

    if len(data_array):
        data_array = np.array(data_array)
    # data_array: n_samples x num_channel x window_size
    # label_list: n_samples
    return data_array, label_list


def save_action(username, reader, action_list=['relax', 'grab']):
    '''
    引导用户存储一段数据并给数据打上标签，需要username和reader数据流对象

    username: where will data be saved to
    reader:   where does data come from
    '''
    print('\nYou have to finish each action in {} seconds.'.format(
        reader.sample_time))
    rst = check_input(('How many times you would like to record for each '
                       'action?(empty to abort): '), {}, times=999)
    if not rst:
        return
    try:
        num = int(rst)
    except ValueError:
        return
    label_list = get_label_dict(username)[0]
    name_list = action_list * num
    np.random.shuffle(name_list)
    for i in range(len(action_list) * num):
        action_name = name_list.pop()
        print('action name: %s, start recording in 2s' % action_name)
        time.sleep(2)
        try:
            if action_name and '-' not in action_name:
                # input shape: 1 x num_channel x window_size
                save_data(username, reader.data_frame, action_name,
                          reader.sample_rate, print_summary=True)
                # update label_list
                if action_name in label_list:
                    label_list[action_name] += 1
                else:
                    label_list[action_name] = 1
            print('')
            time.sleep(2)
        except AssertionError:
            sys.exit('initialization failed')
        except Exception as e:
            print(e)
            continue
    return label_list


# ============================================================================
# stream readers and commanders

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


class ReaderIOMixin(object):
    def set_sample_rate(self, sample_rate, sample_time=None):
        self.sample_rate = sample_rate
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
        if hasattr(self, '_process'):
            alive = self._process.is_alive()
        elif hasattr(self, '_thread'):
            alive = self._thread.is_alive()
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
    def data_channel(self):
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
        if isinstance(items, (slice, int)):
            return self.data_frame[items]
        else:
            raise TypeError('indices must be `int` or `slice`, not '
                            '{0.__class__.__name__}'.format(items))

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
        if method == 'thread':
            self._thread = threading.Thread(target=self._stream_data)
            self._thread.setDaemon(True)
            self._thread.start()
        elif method == 'process':
            self._process = mp.Process(target=self._stream_data)
            self._process.daemon = True
            self._process.start()
        elif method == 'block':
            self._stream_data()
        else:
            raise RuntimeError('unknown method {}'.format(method))

    def _stream_data(self):
        #  signal.signal(signal.SIGINT, signal.SIG_IGN)
        try:
            self._pidfile.acquire()
            while not self._flag_close.is_set():
                self._flag_pause.wait()
                self._save_data_in_buffer()
        except Exception:
            logger.error(traceback.format_exc())
        finally:
            self.close()
            self._pidfile.release()
            logger.debug(self.name + ' stop streaming data')

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

    def __init__(self, sample_time=2, num_channel=None, *a, **k):
        self.name = '[Pylsl reader %d]' % PylslReader.__num__
        PylslReader.__num__ += 1
        self.sample_time = sample_time
        self.num_channel = num_channel
        self._started = False

    def start(self, info=None, *a, **k):
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
        info = info or find_pylsl_outlets(*a, **k)
        nch = info.channel_count()
        self.input_source = '{} @ {}'.format(info.name(), info.source_id())
        self.num_channel = self.num_channel or nch
        if nch < self.num_channel:
            logger.info(
                '{} You want {} channels data but only {} is provided by '
                'the pylsl outlet `{}`. Change num_channel to {}'.format(
                    self.name, self.num_channel, nch, info.name(), nch))
            self.num_channel = nch
        super(PylslReader, self).__init__(
            info.nominal_srate() or 250, self.sample_time, self.num_channel,
            self.name)
        max_buflen = (self.sample_time if info.nominal_srate() != 0
                      else int(self.window_size / 100) + 1)
        self._inlet = pylsl.StreamInlet(info, max_buflen=max_buflen)

        # 2. start streaming process to fetch data into buffer continuously
        self._start_time = info.created_at()
        super(PylslReader, self).start(*a, **k)

    def close(self):
        super(PylslReader, self).close()
        time.sleep(0.2)
        self._inlet.close_stream()

    def _save_data_in_buffer(self):
        d, t = self._inlet.pull_sample()
        self._data[:-1, self._index] = d[1:(self.num_channel + 1)]
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
    Read data from SPI connection with ADS1299.
    This class is only used on ARM. It depends on class ADS1299_API
    '''
    __metaclass__ = Singleton
    name = '[ADS1299 SPI reader]'
    API = ADS1299_API

    def __init__(self, sample_rate=250, sample_time=2, num_channel=1,
                 send_to_pylsl=False, *a, **k):
        '''
        Parameters
        ----------
        '''
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
    Read data from SPI connection with onboard ESP32.
    This class is only used on ARM.
    '''
    __metaclass__ = Singleton
    name = '[ESP32 SPI reader]'
    API = ESP32_API


class SocketTCPReader(BaseReader):
    '''
    Socket TCP client, data reciever.
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
            r = check_input((
                'Please input an address "host:port".\n'
                'Type `quit` to abort.\n'
                '> 192.168.0.1:8888 (example)\n> '), {})
            if r == 'quit':
                raise SystemExit(self.name + ' mannually exit')
            host, port = r.replace('localhost', '127.0.0.1').split(':')
            if int(port) <= 0:
                logger.error('port must be positive num')
                continue
            try:
                socket.inet_aton(host)  # check if host is valid string
                break
            except socket.error:
                logger.error(self.name + ' invalid addr!')
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
        # stop data streaming process/thread
        super(SocketTCPReader, self).close()
        # notice server to shutdown
        self._client.send('shutdown')
        # wait for msg, server will sendback `shutdown` twice to
        # ensure stop process/thread securely
        self._client.recv(10)
        # send shutdown signal to release system resource and close socket
        self._client.shutdown(socket.SHUT_RDWR)
        self._client.close()

    def _save_data_in_buffer(self):
        # 8-channel float32 data = 8*32bits = 32bytes
        # d is np.ndarray with a shape of (8, 1)
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


class SocketTCPServer(object):
    '''
    Socket TCP server on host:port, default to 0.0.0.0:9999
    Data sender.
    '''
    __num__ = 1

    def __init__(self, host='0.0.0.0', port=9999):
        self.name = '[Socket server %d]' % SocketTCPServer.__num__
        SocketTCPServer.__num__ += 1
        self._conns = []
        self._addrs = []
        # TCP IPv4 socket connection
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.bind((host, port))
        self._server.listen(5)
        self._server.settimeout(0.5)
        self._flag_close = threading.Event()
        logger.debug('{} binding socket server at {}:{}'.format(
            self.name, host, port))

    def start(self):
        self._flag_close.clear()
        self._thread = threading.Thread(target=self._manage_connections)
        self._thread.setDaemon(True)
        self._thread.start()

    def _manage_connections(self):
        while not self._flag_close.is_set():
            # manage all connections and wait for new client
            rst, _, _ = select.select([self._server] + self._conns, [], [], 3)
            if not rst:
                continue
            s = rst[0]
            # new connection
            if s is self._server:
                con, addr = self._server.accept()
                con.settimeout(0.5)
                logger.debug('{} accept client from {}:{}'.format(
                    self.name, *addr))
                self._conns.append(con)
                self._addrs.append(addr)
            # some client maybe closed
            elif s in self._conns:
                msg = s.recv(4096)
                addr = self._addrs[self._conns.index(s)]
                # client sent some data
                if msg not in ['shutdown', '']:
                    logger.info('{} recv `{}` from {}:{}'.format(
                        self.name, msg, *addr))
                    continue
                # client shutdown and we should clear correspond server
                try:
                    s.sendall('shutdown')
                    s.shutdown(socket.SHUT_RDWR)
                except socket.error:
                    logger.error(traceback.format_exc())
                finally:
                    s.close()
                self._conns.remove(s)
                self._addrs.remove(addr)
                logger.debug('{} lost client from {}:{}'.format(
                    self.name, *addr))
        logger.debug(self.name + ' socket manager terminated')

    def send(self, data):
        data = data.tobytes()
        try:
            for con in self._conns:
                con.sendall(data)
        except socket.error:
            pass

    def close(self):
        self._flag_close.set()
        for con in self._conns:
            con.close()
        logger.debug(self.name + ' Socket server shut down.')

    def has_listeners(self):
        return len(self._conns)


class BaseCommander(object):
    name = '[embci.io.Commander]'
    _command_dict = command_dict_null

    def __init__(self, command_dict=None, name=None, *a, **k):
        self.name = name or self.name
        self._command_dict = command_dict or self._command_dict
        try:
            logger.debug('[Command Dict] %s' % self._command_dict['_desc'])
        except KeyError:
            logger.warn('[Command Dict] current command dict does not have a '
                        'key named _desc to describe itself. please add it.')
        # alias `write` to make instance a file-like object
        self.write = self.send
        self.flush = self.seek = self.truncate = lambda *a, **k: None

    def start(self):
        raise NotImplementedError('you can not directly use this class')

    def send(self, key, *args, **kwargs):
        raise NotImplementedError('you can not directly use this class')

    def get_command(self, cmd, warning=True):
        if cmd not in self._command_dict:
            if warning:
                logger.warn('{} command {} is not supported'.format(
                    self.name, cmd))
            return
        return self._command_dict[cmd]

    def close(self):
        raise NotImplementedError('you can not directly use this class')


class TorcsCommander(BaseCommander):
    '''
    Send command to TORCS (The Open Race Car Simulator)
    You can output predict result from classifier to the
    game to control race car(left, right, throttle, brake...)
    '''
    __num__ = 1

    def __init__(self, *a, **k):
        super(TorcsCommander, self).__init__(
            name='[Torcs commander %d]' % TorcsCommander.__num__)
        TorcsCommander.__num__ += 1

    def start(self):
        logger.debug(self.name + ' initializing TORCS...')
        self.env = TorcsEnv(vision=True, throttle=False, gear_change=False)
        self.env.reset()

    @duration(1, 'TorcsCommander')
    def send(self, key, prob, *args, **kwargs):
        cmd = [abs(prob) if key == 'right' else -abs(prob)]
        logger.debug(self.name + ' sending cmd {}'.format(cmd))
        self.env.step(cmd)
        return cmd

    def close(self):
        self.env.end()


class PlaneCommander(BaseCommander):
    '''
    Send command to plane war game. Control plane with commands
    [`left`, `right`, `up` and `down`].
    '''
    __singleton__ = True
    name = '[Plane commander]'

    def __init__(self, command_dict=command_dict_plane):
        if PlaneCommander.__singleton__ is False:
            raise RuntimeError('There is already one ' + self.name)
        super(PlaneCommander, self).__init__(command_dict)
        PlaneCommander.__singleton__ = False

    def start(self):
        self.client = PlaneClient()

    @duration(1, 'PlaneCommander')
    def send(self, key, *args, **kwargs):
        ret = self.get_command(key)
        if ret is None:
            return
        self.client.send(ret[0])
        time.sleep(ret[1])
        return ret[0]

    def close(self):
        self.client.close()


class PylslCommander(BaseCommander):
    '''
    Broadcast string[s] by pylsl.StreamOutlet as an online command stream.
    '''
    __num__ = 1

    def __init__(self, command_dict=None, name=None):
        super(PylslCommander, self).__init__(
            command_dict,
            name or '[Pylsl commander %d]' % PylslCommander.__num__)
        PylslCommander.__num__ += 1

    def start(self, name=None, source=None):
        '''
        Initialize and start pylsl outlet.

        Parameters
        ----------
        name : str, optional
            Name describes the data stream or session name.
        source : str
            Source specifies an unique identifier of the device or
            data generator, such as serial number or MAC.

        Examples
        --------
        >>> c = PylslCommander(name='pylsl commander 2')
        >>> c.start('result of recognition', 'EmBCI Hardware Re.A7.1221')
        >>> pylsl.resolve_bypred("contains('recognition')")
        [<pylsl.pylsl.StreamInfo instance at 0x7f3e82d8c3b0>]
        '''
        self._outlet = pylsl.StreamOutlet(
            pylsl.StreamInfo(
                name or self.name, type='predict result',
                channel_format='string', source_id=source or self.name))

    def send(self, key, *args, **kwargs):
        if not isinstance(key, str):
            raise TypeError('{} only accept str but got {}: {}'.format(
                self.name, type(key), key))
        self._outlet.push_sample([ensure_unicode(key)])

    def close(self):
        del self._outlet


class SerialCommander(BaseCommander):
    __num__ = 1

    def __init__(self, command_dict=None, name=None):
        super(SerialCommander, self).__init__(
            command_dict,
            name or '[Serial Commander %d]' % SerialCommander.__num__)
        self._command_lock = threading.Lock()
        self._command_serial = serial.Serial()
        SerialCommander.__num__ += 1

    def start(self, port=None, baudrate=9600):
        self._command_serial.port = port or find_serial_ports()
        self._command_serial.baudrate = baudrate
        self._command_serial.open()

    def send(self, key, *args, **kwargs):
        ret = self.get_command(key)
        if ret is None:
            return
        with self._command_lock:
            self._command_serial.write(ret[0])
            time.sleep(ret[1])
        return ret[0]

    def close(self):
        self._command_serial.close()

    def reconnect(self):
        try:
            self._command_serial.close()
            time.sleep(1)
            self._command_serial.open()
            logger.info(self.name + ' reconnect success.')
        except serial.serialutil.SerialException:
            logger.error(self.name + ' reconnect failed.')


# THE END
