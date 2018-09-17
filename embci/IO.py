#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Tue Mar  6 20:45:20 2018

@author: hank
"""
# built-in
from __future__ import print_function
import os
import sys
import time
import mmap
import signal
import socket
import select
import unittest
import threading
import multiprocessing
from ctypes import c_uint16

# pip install numpy, scipy, serial, mne, spidev, pylsl
import scipy
import numpy as np
import serial
import pylsl
#  import mne

from .common import mkuserdir, check_input, get_label_list, Timer
from .common import time_stamp, virtual_serial
from .common import find_ports, find_outlets, find_spi_devices
from .gyms import TorcsEnv
from .gyms import PlaneClient
from .utils.ads1299_api import ADS1299_API, ESP32_API
from .utils.ili9341_api import ILI9341_API, rgb24to565
from .utils.HTMLTestRunner import HTMLTestRunner
from .preprocessing import Signal_Info
from embci import BASEDIR, unicode

__dir__ = os.path.dirname(os.path.abspath(__file__))
__file__ = os.path.basename(__file__)


@mkuserdir
def save_data(username, data, label, sample_rate,
              print_summary=False, save_fif=False):
    '''
    保存数据的函数，传入参数为username,data,label(这一段数据的标签)
    可以用print_summary=True输出已经存储的数据的label及数量

    Input data shape
    ----------------
        n_sample x n_channel x window_size

    data file name:
        ${DIR}/data/${username}/${label}-${num}.${surfix}
    current supported format is 'mat'(default) and 'fif'(set save_fif=True)
    '''
    # check data format and shape
    if not isinstance(data, np.ndarray):
        data = np.array(data)
    if len(data.shape) != 3:
        raise IOError('Invalid data shape{}, n_sample x n_channel x '
                      'window_size is recommended!'.format(data.shape))

    label_list = get_label_list(username)[0]
    num = '1' if label not in label_list else str(label_list[label] + 1)

    fn = os.path.join(BASEDIR, 'data', username, '%s-%s.mat' % (label, num))
    scipy.io.savemat(fn,
                     {label: data, 'sample_rate': sample_rate},
                     do_compression=True)
    print('{} data saved to {}'.format(data.shape, fn))

    #  if save_fif:
    #      for sample in data:
    #          fn = './data/fif/%s/%s-raw.fif.gz' % (username,
    #                                                '-'.join([label, num]))
    #          num += 1
    #          info = mne.create_info(ch_names=sample.shape[0],
    #                                 sfreq=sample_rate)
    #          mne.io.RawArray(sample, info).save(fn, verbose=0)
    #          print('{} data save to {}'.format(sample.shape, fn))

    if print_summary:
        print(get_label_list(username)[1])


@mkuserdir
def load_data(username, print_summary=True):
    '''
    读取./data/username文件夹下的所有数据，返回三维数组

    Output shape: n_samples x n_channel x window_size
    '''
    userpath = os.path.join(BASEDIR, 'data', username)
    if not os.listdir(userpath):
        check_input(('There is no data available for this user, please save '
                     'some first, continue? '))
        return np.array([]), np.array([]), {}

    # here we got an auto-sorted action name list
    # label_list  {'left': left_num, ... , 'up': up_num, ...}
    # action_dict {'left': 10, ... , 'up': 15, ...}
    # label       [10] * left_num + ... + [15] * up_num + ...
    label_list = get_label_list(username)[0]
    action_dict = {n: a for n, a in enumerate(label_list)}

    # data  n_action*action_num*n_samples x n_channel x window_size
    # label n_action*action_num*n_samples x 1
    data = []
    label = []
    for n, action_name in enumerate(label_list):  # n_action
        for fn in os.listdir(userpath):  # action_num
            if fn.startswith(action_name) and fn.endswith('.mat'):
                file_path = os.path.join(userpath, fn)
                dat = scipy.io.loadmat(file_path)[action_name]
                if len(dat.shape) != 3:
                    print('Invalid data shape{}, '
                          'n_sample x n_channel x window_size is recommended! '
                          'Skip file {}.'.format(data.shape, file_path))
                    continue
                label += dat.shape[0] * [n]  # n_samples
                data = np.stack([s for s in data] + [s for s in dat])

    if print_summary:
        print(get_label_list(username)[1])
    return np.array(data), np.array(label), action_dict


def save_action(username, reader, action_list=['relax', 'grab']):
    '''
    引导用户存储一段数据并给数据打上标签，需要username和reader数据流对象

    username: where will data be saved to
    reader:   where does data come from
    '''
    print(('\nYou have to finish each action in '
           '{} seconds.').format(reader.sample_time))
    rst = check_input(('How many times you would like to record for each '
                       'action?(empty to abort): '), {}, times=999)
    if not rst:
        return
    try:
        num = int(rst)
    except ValueError:
        return
    label_list = get_label_list(username)[0]
    name_list = action_list * num
    np.random.shuffle(name_list)
    for i in range(len(action_list) * num):
        action_name = name_list.pop()
        print('action name: %s, start recording in 2s' % action_name)
        time.sleep(2)
        try:
            if action_name and '-' not in action_name:
                # input shape: 1 x n_channel x window_size
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


class _basic_reader(object):
    def __init__(self, sample_rate, sample_time, n_channel, name=None):
        # basic stream reader information
        self.sample_rate = sample_rate
        self.sample_time = sample_time
        self.n_channel = n_channel
        self.window_size = int(sample_rate * sample_time)
        self._name = name if name is not None else ' reader%s  ' % time_stamp()

        # channels are defined here
        self.ch_list = ['ch%d' % i for i in range(1, n_channel + 1)] + ['time']

        # maintain a FIFO-loop queue to store data
        # self._data = np.zeros((n_channel + 1, self.window_size), np.float32)
        self._data = None
        self._index_mp_value = multiprocessing.Value(c_uint16, 0)
        self._ch_last_index = self._fr_last_index = self._index_mp_value.value
        self._started = False

        # use these flags to controll the data streaming thread
        self._flag_pause = multiprocessing.Event()
        self._flag_close = multiprocessing.Event()
        # self._flag_pause = threading.Event()
        # self._flag_close = threading.Event()

    def start(self, block=False, method='process'):
        self._flag_pause.set()
        self._flag_close.clear()
        self._data_file = '/tmp/mmap_%s' % self._name[1:-2].replace(' ', '_')
        self._f = open(self._data_file, 'w+')
        self._f.write('\x00' * 4 * (self.n_channel + 1) * self.window_size)
        self._f.flush()
        self._m = mmap.mmap(self._f.fileno(), 0)
        self._data = np.ndarray(shape=(self.n_channel + 1, self.window_size),
                                dtype=np.float32, buffer=self._m)
        self._start_time = time.time()
        self._started = True
        if block:
            self._stream_data()
            return
        elif method == 'process':
            self._process = multiprocessing.Process(target=self._stream_data)
            self._process.daemon = True
            self._process.start()
        elif method == 'thread':
            self._thread = threading.Thread(target=self._stream_data)
            self._thread.setDaemon(True)
            self._thread.start()
        else:
            raise RuntimeError('unknown method {}'.format(method))

    def _stream_data(self):
        #  signal.signal(signal.SIGINT, signal.SIG_IGN)
        try:
            while not self._flag_close.is_set():
                self._flag_pause.wait()
                self._save_data_in_buffer()
        except NotImplementedError:
            print(self._name + 'cannot use this class directly')
        except Exception as e:
            print(self._name + '{}: {}'.format(type(e), e))
            self.close()
        finally:
            print(self._name + 'stop streaming data...')
            print(self._name + 'shut down.')

    def _save_data_in_buffer(self):
        raise NotImplementedError('not implemented yet!')

    def close(self):
        assert self._started, 'Not started yet!'
        self._flag_close.set()
        time.sleep(0.5)
        self._data = self._data.copy()  # remove reference to old data buffer
        self._m.close()
        self._f.close()
        if os.path.exists(self._data_file):
            os.remove(self._data_file)
        self._started = False  # you can re-start this reader now, enjoy~~

    def restart(self):
        if self._started:
            self.close()
        self._flag_close.clear()
        self._flag_pause.set()
        self.start()

    def pause(self):
        self._flag_pause.clear()

    def resume(self):
        self._flag_pause.set()

    @property
    def _index(self):
        return self._index_mp_value.value

    @_index.setter
    def _index(self, value):
        self._index_mp_value.value = value

    @property
    def is_streaming(self):
        if hasattr(self, '_process'):
            tmp = self._process.is_alive()
        elif hasattr(self, '_thread'):
            tmp = self._thread.is_alive()
        return self._started and tmp and self._flag_pause.is_set()

    @property
    def real_time_sample_rate(self):
        try:
            t1, t2 = (self._index - 1) % self.window_size, self._index
            return self.window_size / (self._data[-1, t1] - self._data[-1, t2])
        except:
            return 0

    @property
    def data_channel(self):
        if self.is_streaming:
            t = time.time()
            while self._ch_last_index == self._index:
                if (time.time() - t) > (10.0 / self.sample_rate):
                    print(self._name + 'there maybe error reading data')
                    break
            self._ch_last_index = self._index
        return self._data[:-1, (self._ch_last_index - 1) % self.window_size]

    @property
    def data_frame(self):
        if self.is_streaming:
            t = time.time()
            while self._fr_last_index == self._index:
                if (time.time() - t) > (2.0 / self.sample_rate):
                    print(self._name + 'there maybe error reading data')
                    break
            self._fr_last_index = self._index
        return np.concatenate((
            self._data[:-1, self._fr_last_index:],
            self._data[:-1, :self._fr_last_index]), -1)

    def __getitem__(self, items):
        if isinstance(items, tuple):
            for item in items:
                self = self.__getitem__(item)
            return self
        if isinstance(items, str) and items in vars(Signal_Info):
            return getattr(Signal_Info(self.sample_rate), items)(self)
        if isinstance(items, (slice, int)):
            return self._data[items]
        else:
            print(self._name + 'unknown preprocessing method %s' % items)
            return self


class Fake_data_generator(_basic_reader):
    '''Generate random data, same as any Reader defined in IO.py'''
    _num = 1

    def __init__(self, sample_rate=250, sample_time=2, n_channel=1,
                 send_to_pylsl=False, *a, **k):
        super(Fake_data_generator, self).__init__(sample_rate,
                                                  sample_time,
                                                  n_channel)
        self._name = '[Fake data generator %d] ' % Fake_data_generator._num
        self._send_to_pylsl = send_to_pylsl
        Fake_data_generator._num += 1

    def start(self, *a, **k):
        if self._started:
            self.resume()
            return
        if self._send_to_pylsl:
            print(self._name + 'establishing pylsl outlet...')
            self._outlet = pylsl.StreamOutlet(
                pylsl.StreamInfo(
                    'fake_data_generator', 'unknown', self.n_channel,
                    self.sample_rate, 'float32', 'used for debugging'))
        super(Fake_data_generator, self).start(*a, **k)

    def _save_data_in_buffer(self):
        time.sleep(1.0 / self.sample_rate)
        d = np.random.rand(self.n_channel) / 10
        self._data[:-1, self._index] = d[:self.n_channel]
        self._data[-1, self._index] = time.time() - self._start_time
        self._index = (self._index + 1) % self.window_size
        if self._send_to_pylsl:
            self._outlet.push_sample(d)


class Files_reader(_basic_reader):
    '''
    Read data from mat, fif, csv... file and simulate as a common data reader
    '''
    _num = 1

    def __init__(self, filename, sample_rate=250, sample_time=2, n_channel=1,
                 *a, **k):
        super(Files_reader, self).__init__(sample_rate, sample_time, n_channel)
        self.filename = filename
        self._name = '[Files reader %d] ' % Files_reader._num
        Files_reader._num += 1

    def start(self, *a, **k):
        if self._started:
            self.resume()
            return
        # 1. try to open data file and load data into RAM
        print(self._name + 'reading data file...')
        while not os.path.exists(self.filename):
            self.filename = check_input(
                'No such file! Please check and input correct file name: ', {})
        try:
            if self.filename.endswith('.mat'):
                actionname = os.path.basename(self.filename).split('-')[0]
                mat = scipy.io.loadmat(self.filename)
                data = mat[actionname][0]
                sample_rate = mat.get('sample_rate', None)
                print(self._name + 'load data with shape of {} @ {}Hz'.format(
                    data.shape, sample_rate))
                assert len(data.shape) == 2, 'Invalid data shape!'
                n = data.shape[0]
                if n < self.n_channel:
                    print('{}change n_channel to {}'.format(self._name, n))
                    self.n_channel = n
                    self._data = self._data[:(n + 1)]
                if sample_rate and sample_rate != self.sample_rate:
                    print('{}resample source data to {}Hz'.format(
                        self._name, self.sample_rate))
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
            print(self._name + '{}: {}'.format(type(e), e))
            print(self._name + 'Abort...')
            return

        # 2. get ready to stream data
        super(Files_reader, self).start(*a, **k)

    def _get_data_g(self, data):
        for line in data:
            time.sleep(1.0 / self.sample_rate)
            if (yield line) == 'quit':
                break

    def _save_data_in_buffer(self):
        d = self._get_data.next()
        self._data[:-1, self._index] = d[:self.n_channel]
        self._data[-1, self._index] = time.time() - self._start_time
        self._index = (self._index + 1) % self.window_size


class Pylsl_reader(_basic_reader):
    '''
    Connect to a data stream on localhost:port and read data into buffer.
    There should be at least one stream available.
    '''
    _num = 1

    def __init__(self, sample_rate=250, sample_time=2, n_channel=1, *a, **k):
        super(Pylsl_reader, self).__init__(sample_rate, sample_time, n_channel)
        self._name = '[Pylsl reader %d] ' % Pylsl_reader._num
        Pylsl_reader._num += 1

    def start(self, servername=None, *a, **k):
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
        print(self._name + 'finding availabel outlets...  ', end='')
        info = find_outlets(servername)
        print('`%s` opened' % info.source_id)
        n = info.channel_count()
        if n < self.n_channel:
            print(('{}You want {} channel data but only {} channels is offered'
                   ' by pylsl stream outlet you select. Change n_channel to {}'
                   '').format(self._name, self.n_channel, n, n))
            self.n_channel = n
            self._data = self._data[:(n + 1)]
        max_buflen = (self.sample_time if info.nominal_srate() != 0
                      else int(self.window_size / 100) + 1)
        self._inlet = pylsl.StreamInlet(info, max_buflen=max_buflen)

        # 2. start streaming process to fetch data into buffer continuously
        self._start_time = info.created_at()
        super(Pylsl_reader, self).start(*a, **k)

    def close(self):
        self._inlet.close_stream()
        super(Pylsl_reader, self).close()

    def _save_data_in_buffer(self):
        d, t = self._inlet.pull_sample()
        self._data[:-1, self._index] = d[1:(self.n_channel + 1)]
        self._data[-1, self._index] = t - self._start_time
        self._index = (self._index + 1) % self.window_size


class Serial_reader(_basic_reader):
    '''
    Connect to a serial port and fetch data into buffer.
    There should be at least one port available.
    '''
    _num = 1

    def __init__(self, sample_rate=250, sample_time=2, n_channel=1,
                 baudrate=115200, send_to_pylsl=False, *a, **k):
        super(Serial_reader, self).__init__(sample_rate,
                                            sample_time,
                                            n_channel)
        self._serial = serial.Serial(baudrate=baudrate)
        self._name = '[Serial reader %d] ' % Serial_reader._num
        self._send_to_pylsl = send_to_pylsl
        Serial_reader._num += 1

    def start(self, port=None, *a, **k):
        if self._started:
            self.resume()
            return
        # 1. find serial port and connect to it
        print(self._name + 'finding availabel ports... ', end='')
        port = port if port is not None else find_ports()
        self._serial.port = port
        self._serial.open()
        print('`%s` opened.' % port)
        n = len(self._serial.read_until().strip().split(','))
        if n < self.n_channel:
            print(('{}You want {} channel data but only {} channels is offered'
                   ' by serial port you select. Change n_channel to {}'
                   '').format(self._name, self.n_channel, n, n))
            self.n_channel = n
            self._data = self._data[:(n + 1)]
        # 2. start get data process
        # here we only need to check one time whether send_to_pylsl is set
        # if put this work in thread, it will be checked thousands times.
        if self._send_to_pylsl:
            self._outlet = pylsl.StreamOutlet(
                pylsl.StreamInfo(
                    'Serial_reader', 'unknown', self.n_channel,
                    self.sample_rate, 'float32', self._serial.port))
        super(Serial_reader, self).start(*a, **k)

    def close(self):
        self._serial.close()
        super(Serial_reader, self).close()

    def _save_data_in_buffer(self):
        d = np.array(self._serial.read_until().strip().split(','), np.float32)
        self._data[:-1, self._index] = d[:self.n_channel]
        self._data[-1, self._index] = time.time() - self._start_time
        self._index = (self._index + 1) % self.window_size
        if self._send_to_pylsl:
            self._outlet.push_sample(d)


class ADS1299_reader(_basic_reader):
    '''
    Read data from SPI connection with ADS1299.
    This class is only used on ARM. It depends on class ADS1299_API
    '''
    _singleton = True

    def __init__(self, sample_rate=250, sample_time=2, n_channel=1,
                 send_to_pylsl=False, *a, **k):
        if ADS1299_reader._singleton is False:
            raise RuntimeError('There is already one ADS1299 reader.')
        super(ADS1299_reader, self).__init__(sample_rate,
                                             sample_time,
                                             n_channel)
        self._name = '[ADS1299 SPI reader] '
        self._send_to_pylsl = send_to_pylsl
        self._ads = ADS1299_API(sample_rate)

        self.set_input_source = self._ads.set_input_source
        self.enable_bias = self._ads.enable_bias
        self.measure_inpedance = self._ads.measure_impedance

        ADS1299_reader._singleton = False

    def __del__(self):
        ADS1299_reader._singleton = True
        del self

    def set_sample_rate(self, rate):
        rst = self._ads.set_sample_rate(rate)
        if rst is not None:
            self.sample_rate = rate
            self.window_size = self.sample_rate * self.sample_time
            print(self._name + ('sample rate set to {}, you may want to '
                                'restart reader now').format(rst))
            return
        print(self._name + 'invalid sample rate {}'.format(rate))

    def start(self, device=(0, 0), *a, **k):
        if self._started:
            self.resume()
            return
        # 1. find avalable spi devices
        print(self._name + 'finding available spi devices... ', end='')
        device = device if device is not None else find_spi_devices()
        self._ads.open(device)
        self._ads.start(self.sample_rate)
        print('`spi%d-%d` opened.' % device)
        # 2. start get data process
        if self._send_to_pylsl:
            self._outlet = pylsl.StreamOutlet(
                pylsl.StreamInfo(
                    'SPI_reader', 'unknown', self.n_channel,
                    self.sample_rate, 'float32', 'spi%d-%d ' % device))
        super(ADS1299_reader, self).start(*a, **k)

    def close(self):
        self._ads.close()
        super(ADS1299_reader, self).close()

    def _save_data_in_buffer(self):
        d = self._ads.read()
        self._data[:-1, self._index] = d[:self.n_channel]
        self._data[-1, self._index] = time.time() - self._start_time
        self._index = (self._index + 1) % self.window_size
        if self._send_to_pylsl:
            self._outlet.push_sample(d)


class ESP32_SPI_reader(ADS1299_reader):
    '''
    Read data from SPI connection with onboard ESP32.
    This class is only used on ARM.
    '''
    _singleton = True

    def __init__(self, sample_rate=250, sample_time=2, n_channel=1,
                 send_to_pylsl=False, *a, **k):
        if ESP32_SPI_reader._singleton is False:
            raise RuntimeError('There is already one ESP32 SPI reader.')
        super(ADS1299_reader, self).__init__(sample_rate,
                                             sample_time,
                                             n_channel)
        self._name = '[ESP32 SPI reader] '
        self._send_to_pylsl = send_to_pylsl
        self._ads = self._esp = ESP32_API()

        self.set_input_source = self._esp.set_input_source
        self.enable_bias = self._esp.enable_bias
        self.measure_impedance = self._esp.measure_impedance
        ESP32_SPI_reader._singleton = False

    def __del__(self):
        ESP32_SPI_reader._singleton = True
        del self


class Socket_TCP_reader(_basic_reader):
    '''
    Socket TCP client, data reciever.
    '''
    _num = 1

    def __init__(self, sample_rate=250, sample_time=2, n_channel=1, *a, **k):
        super(Socket_TCP_reader, self).__init__(sample_rate,
                                                sample_time,
                                                n_channel)
        self._name = '[Socket TCP reader %d] ' % Socket_TCP_reader._num
        Socket_TCP_reader._num += 1

    def start(self, *a, **k):
        if self._started:
            self.resume()
            return
        # 1. IP addr and port are offered by user, connect to that host:port
        print(self._name + 'configuring addr... input "quit" to abort')
        while 1:
            r = check_input(('please input an address in format "host,port"\n'
                             '>>> 192.168.0.1:8888 (example)\n>>> '), {})
            if r == 'quit':
                raise SystemExit(self._name + 'mannually exit')
            host, port = r.replace('localhost', '127.0.0.1').split(':')
            if int(port) <= 0:
                print('port must be positive num')
                continue
            try:
                socket.inet_aton(host)  # check if host is valid string
                break
            except socket.error:
                print(self._name + 'invalid addr!')
        # TCP IPv4 socket connection
        self._client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._client.connect((host, int(port)))
        # 2. read data in another thread
        super(Socket_TCP_reader, self).start(*a, **k)

    def close(self):
        '''
        Keep in mind that socket `client` is continously receiving from server
        in other process/thread, so directly close client is dangerous because
        client may be blocking that process/thread by client.recv(n). We need
        to let server socket close the connection.
        '''
        # stop data streaming process/thread
        super(Socket_TCP_reader, self).close()
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
        self._data[:-1, self._index] = d[:self.n_channel]
        self._data[-1, self._index] = time.time() - self._start_time
        self._index = (self._index + 1) % self.window_size


class Socket_UDP_reader(_basic_reader):
    '''
    Socket UDP client, data receiver.
    '''
    _num = 1

    def __init__(self, sample_rate=250, sample_time=2, n_channel=1, *a, **k):
        super(Socket_UDP_reader, self).__init__(sample_rate,
                                                sample_time,
                                                n_channel)
        self._name = '[Socket UDP reader %d] ' % Socket_UDP_reader._num
        Socket_UDP_reader._num += 1

    def start(self, *a, **k):
        pass

    def close(self):
        pass

    def _save_data_in_buffer(self):
        # 8-channel float32 data = 8*32bits = 32bytes
        # d is np.ndarray with a shape of (8, 1)
        d = np.frombuffer(self._client.recv(32), np.float32)
        self._data[:-1, self._index] = d[:self.n_channel]
        self._data[-1, self._index] = time.time() - self._start_time
        self._index = (self._index + 1) % self.window_size


class Socket_TCP_server(object):
    '''
    Socket TCP server on host:port, default to 0.0.0.0:9999
    Data sender.
    '''
    _num = 1

    def __init__(self, host='0.0.0.0', port=9999):
        # if host is None:
        #     host = get_self_ip_addr()
        self._name = '[Socket server %d] ' % Socket_TCP_server._num
        self._conns = []
        self._addrs = []
        Socket_TCP_server._num += 1
        # TCP IPv4 socket connection
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.bind((host, port))
        self._server.listen(5)
        self._server.settimeout(0.5)
        self._flag_close = threading.Event()
        print(self._name + 'binding socket server at %s:%d' % (host, port))

    def start(self):
        # handle connection in a seperate thread
        self._flag_close.clear()
        self._thread = threading.Thread(target=self._manage_connections)
        self._thread.setDaemon(True)
        self._thread.start()

    def _manage_connections(self):
        while not self._flag_close.is_set():
            # manage all connections and wait for new client
            rst = select.select([self._server] + self._conns, [], [], 3)
            if not rst[0]:
                continue
            s = rst[0][0]
            # new connection
            if s is self._server:
                con, addr = self._server.accept()
                con.settimeout(0.5)
                print('{}accept client from {}:{}'.format(self._name, *addr))
                self._conns.append(con)
                self._addrs.append(addr)
            # some client maybe closed
            elif s in self._conns:
                t = s.recv(4096)
                addr = self._addrs[self._conns.index(s)]
                # client shutdown and we should clear correspond server
                if t in ['shutdown', '']:
                    try:
                        s.sendall('shutdown')
                        s.shutdown(socket.SHUT_RDWR)
                        s.close()
                    except:
                        s.close()
                    finally:
                        pass
                    self._conns.remove(s)
                    self._addrs.remove(addr)
                    print('{}lost client from {}:{}'.format(self._name, *addr))
                # client sent some data
                else:
                    print('{}recv {} from {}:{}'.format(self._name, t, *addr))
        print(self._name + 'socket manager say goodbye to you ;-)')

    def send(self, data):
        data = data.tobytes()
        try:
            for con in self._conns:
                con.sendall(data)
        except:
            pass

    def close(self):
        self._flag_close.set()
        print(self._name + 'stop broadcasting data...')
        for con in self._conns:
            con.close()
        # self._server.close()
        print(self._name + 'Socket server shut down.')

    def has_listeners(self):
        return len(self._conns)


command_dict_plane = {
    'left':       ['3', 0.5],
    'right':      ['4', 0.5],
    'up':         ['1', 0.5],
    'down':       ['2', 0.5],
    'disconnect': ['9', 0.5],
    '_desc':     ("plane war game support command : "
                  "left, right, up, down, disconnect")}

command_dict_glove_box = {
    'thumb':        ['1', 0.5],
    'index':        ['2', 0.5],
    'middle':       ['3', 0.5],
    'ring':         ['5', 0.5],
    'little':       ['4', 0.5],
    'grab-all':     ['6', 0.5],
    'relax':        ['7', 0.5],
    'grab':         ['8', 0.5],
    'thumb-index':  ['A', 0.5],
    'thumb-middle': ['B', 0.5],
    'thumb-ring':   ['C', 0.5],
    'thumb-little': ['D', 0.5],
    '_desc':       ("This is a dict for glove box version 1.0.\n"
                    "Support command:\n\t"
                    "thumb, index, middle, ring\n\t"
                    "little, grab-all, relax, grab\n")}

command_dict_arduino_screen_v1 = {
    'point':  ['#0\r\n{x},{y}\r\n', 0.5],
    'line':   ['#1\r\n{x1},{y1},{x2},{y2}\r\n', 0.5],
    'circle': ['#2\r\n{x},{y},{r}\r\n', 0.5],
    'rect':   ['#3\r\n{x1},{y1},{x2},{y2}\r\n', 0.5],
    'text':   ['#4\r\n{x},{y},{s}\r\n', 0.5],
    'clear':  ['#5\r\n', 1.0],
    '_desc': ("Arduino-controlled SSD1306 0.96' 128x64 OLED screen v1.0:\n"
              "you need to pass in args as `key`=`value`(dict)\n\n"
              "Commands | args\n"
              "point    | x, y\n"
              "line     | x1, y1, x2, y2\n"
              "circle   | x, y, r\n"
              "rect     | x1, y1, x2, y2\n"
              "text     | x, y, s\n")}

command_dict_arduino_screen_v2 = {
    'points': ['P{:c}{}', 0.1],
    'point':  ['D{:c}{}', 0.05],
    'text':   ['S{:c}{:s}', 0.1],
    'clear':  ['C', 0.5],
    '_desc': ("Arduino-controlled ILI9325D 2.3' 220x176 LCD screen v1.0:\n"
              "Commands | Args\n"
              "points   | len(pts), bytearray([y for x, y in pts])\n"
              "point    | len(pts), bytearray(np.uint8(pts).reshape(-1))\n"
              "text     | len(str), str\n"
              "clear    | no args, clear screen\n")}

command_dict_uart_screen_v1 = {
    'point':   ['PS({x},{y},{c});\r\n', 0.38/220],
    'line':    ['PL({x1},{y1},{x2},{y2},{c});\r\n', 3.5/220],
    'circle':  ['CIR({x},{y},{r},{c});\r\n', 3.0/220],
    'circlef': ['CIRF({x},{y},{r},{c});\r\n', 8.0/220],
    'rect':    ['BOX({x1},{y1},{x2},{y2},{c});\r\n', 3.0/220],
    'rrect':   ['BOX({x1},{y1},{x2},{y2},{c});\r\n', 3.0/220],
    'rectf':   ['BOXF({x1},{y1},{x2},{y2},{c});\r\n', 15.0/220],
    'rrectf':  ['BOXF({x1},{y1},{x2},{y2},{c});\r\n', 15.0/220],
    'text':    ['DC16({x},{y},{s},{c});\r\n', 15.0/220],
    'dir':     ['DIR({:d});\r\n', 3.0/220],
    'clear':   ['CLR(0);\r\n', 10.0/220],
    '_desc':  ("UART-controlled Winbond 2.3' 220x176 LCD screen:\n"
               "Commands | Args\n"
               "point    | x, y, c\n"
               "line     | x1, y1, x2, y2, c\n"
               "circle   | x, y, r, c\n"
               "circlef  | x, y, r, c, filled circle\n"
               "rect     | x1, y1, x2, y2, c\n"
               "rectf    | x1, y1, x2, y2, c, filled rectangle\n"
               "text     | x, y, s(string), c(color)\n"
               "dir      | one num, 0 means vertical, 1 means horizental\n"
               "clear    | clear screen will black\n")}

command_dict_esp32 = {
    'start':     ['', 0.2],
    'write':     ['', 0.3],
    'writereg':  ['', 0.5],
    'writeregs': ['', 0.5],
    'readreg':   ['', 0.5],
    'readregs':  ['', 0.5],
    '_desc':    ("This dict is used to commucate with onboard ESP32.\n"
                 "Supported command:\n\t"
                 "start: init ads1299 and start RDATAC mode\n\t"
                 "write: nothing\n\t"
                 "writereg: write single register\n\t"
                 "writeregs: write a list of registers\n\t"
                 "readreg: read single register\n\t"
                 "readregs: read a list of registers\n\t")}


class _basic_commander(object):
    def __init__(self, command_dict):
        self._command_dict = command_dict
        self._name = '[basic commander] '
        try:
            print('[Command Dict] %s' % command_dict['_desc'])
        except:
            print('[Command Dict] current command dict does not have a '
                  'key named _desc to describe itself. please add it.')

    def start(self):
        raise NotImplementedError('you can not directly use this class')

    def send(self, key, *args, **kwargs):
        raise NotImplementedError('you can not directly use this class')

    write = send

    def check_key(self, key):
        if key not in self._command_dict:
            print(self._name + 'Wrong command {}! Abort.'.format(key))
            return

    def close(self):
        raise NotImplementedError('you can not directly use this class')


class Torcs_commander(_basic_commander):
    '''
    Send command to TORCS(The Open Race Car Simulator)
    You can output predict result from classifier to the
    game to control race car(left, right, throttle, brake...)
    '''
    _num = 1

    def __init__(self, command_dict={}, *args, **kwargs):
        super(Torcs_commander, self).__init__(command_dict)
        self._name = '[Torcs commander %d] ' % Torcs_commander._num
        Torcs_commander._num += 1

    def start(self):
        print(self._name + 'initializing TORCS...')
        self.env = TorcsEnv(vision=True, throttle=False, gear_change=False)
        self.env.reset()

    @Timer.duration('Torcs_commander', 1)
    def send(self, key, prob, *args, **kwargs):
        cmd = [abs(prob) if key == 'right' else -abs(prob)]
        print(self._name + 'sending cmd {}'.format(cmd))
        self.env.step(cmd)
        return cmd

    def close(self):
        self.env.end()


class Plane_commander(_basic_commander):
    '''
    Send command to plane war game.
    Controlling plane with `left`, `right`, `up` and `down`.
    '''
    _singleton = True

    def __init__(self, command_dict=command_dict_plane):
        if Plane_commander._singleton is False:
            raise RuntimeError('There is already one Plane Commander.')
        super(Plane_commander, self).__init__(command_dict)
        self._name = '[Plane commander] '
        Plane_commander._singleton = False

    def start(self):
        self.client = PlaneClient()

    @Timer.duration('Plane_commander', 1)
    def send(self, key, *args, **kwargs):
        self.check_key(key)
        cmd, delay = self._command_dict[key]
        self.client.send(cmd)
        time.sleep(delay)
        return cmd

    def close(self):
        pass


class Pylsl_commander(_basic_commander):
    '''
    Send predict result to pylsl as an online command stream
    '''
    _num = 1

    def __init__(self, command_dict={'_desc': 'send command to pylsl'}):
        super(Pylsl_commander, self).__init__(command_dict)
        self._name = '[Pylsl commander %d] ' % Pylsl_commander._num
        Pylsl_commander._num += 1

    def start(self):
        self._outlet = pylsl.StreamOutlet(
            pylsl.StreamInfo(
                'Pylsl_commander', 'predict result', 1,
                0.0, 'string', 'pylsl commander'))

    @Timer.duration('Pylsl commander', 0)
    def send(self, key, *args, **kwargs):
        if isinstance(key, str):
            self._outlet.push_sample([key])
            return
        raise RuntimeError(self._name +
                           'only accept str but got {}'.format(type(key)))

    def close(self):
        pass


class Serial_commander(_basic_commander):
    _lock = threading.Lock()
    _num = 1

    def __init__(self, baudrate=9600,
                 command_dict=command_dict_glove_box,
                 CR=True, LF=True):
        super(Serial_commander, self).__init__(command_dict)
        self._serial = serial.Serial(baudrate=baudrate)
        self._CR = CR
        self._LF = LF
        self._name = '[Serial commander %d] ' % Serial_commander._num
        Serial_commander._num += 1

    def start(self, port=None):
        print(self._name + 'finding availabel ports... ', end='')
        port = port if port else find_ports()
        self._serial.port = port
        self._serial.open()
        print('`%s` opened.' % port)

    @Timer.duration('Serial_commander', 5)
    def send(self, key, *args, **kwargs):
        self.check_key(key)
        cmd, delay = self._command_dict[key]
        with self._lock:
            self._serial.write(cmd)
            if self._CR:
                self._serial.write('\r')
            if self._LF:
                self._serial.write('\n')
            time.sleep(delay)
        return cmd

    def close(self):
        self._serial.close()

    def reconnect(self):
        try:
            self._serial.close()
            time.sleep(1)
            self._serial.open()
            print(self._name + 'reconnect success.')
        except:
            print(self._name + 'reconnect failed.')


class _convert_24bit_to_15():
    def __getitem__(self, v):
        if isinstance(v, int) and v <= 0xFFFFFF and v >= 0:
            return int(float(v) / 0xFFFFFF * 15)
        raise KeyError('')


class Serial_Screen_commander(Serial_commander):
    _color_map = {
        str: {
            'black': 0, 'red': 1, 'green': 2, 'blue': 3, 'yellow': 4,
            'cyan': 5, 'purple': 6, 'gray': 7, 'grey': 8, 'brown': 9,
            'orange': 13, 'pink': 14, 'white': 15},
        int: {}}

    def __init__(self, baud=115200, command_dict=command_dict_uart_screen_v1):
        super(Serial_Screen_commander, self).__init__(baud, command_dict)
        self._name = self._name[:-2] + ' for screen' + self._name[-2:]

    def send(self, key, *a, **k):
        self.check_key(key)
        if key == 'img':
            self._plot_img_point_by_point(k)
            return 'img'
        cmd, delay = self._command_dict[key]
        if 'c' in k:
            assert type(k['c']) in self._color_map, 'c only can be str or int'
            try:
                k['c'] = self._color_map[type(k['c'])][k['c']]
            except KeyError:
                raise ValueError('Unsupported color: {}'.format(k['c']))
        try:
            cmd = cmd.format(*a, **k)
        except IndexError:
            print(self._name +
                  'unmatch key {} - {} and params {}!'.format(key, cmd, a))
        with self._lock:
            self._serial.write(cmd)
        time.sleep(delay)
        return cmd

    def _plot_img_point_by_point(self, e):
        img = e['img'].copy()
        x1, y1, x2, y2 = e['x1'], e['y1'], e['x2'], e['y2']
        if len(img.shape) == 3:
            img = img[:, :, 0]
        cmd, delay = self._command_dict['point']
        with self._lock:
            for x, y in [(x, y) for x in range(x2-x1) for y in range(y2-y1)]:
                if img[y, x] > 15:
                    continue
                tosend = cmd.format(x=e['x1'] + x, y=e['y1'] + y, c=img[y, x])
                self._serial.write(tosend)
                time.sleep(delay)

    def close(self):
        self.send('clear', c='black')
        super(Serial_Screen_commander, self).close()

    def getsize(self, s, size=None, font=None):
        '''
        Get width and height of string `s` with `size` and `font`
        Returns
        -------
        w, h: tuple | None
            size in pixel
        s: str | None
            string in correct encoding
        font_path: str | None
            If param `font` offered, check whether font exist. If font file not
            exists or supported, return None.
        '''
        # Although there is already `# -*- coding: utf-8 -*-` above,
        # we'd better explicitly use utf-8 to decode string in py2.
        # py3 default use utf-8 coding, which is really really nice.
        if sys.version_info.major == 2 and not isinstance(s, unicode):
            s = s.decode('utf8')
        # Serial Screen use 8 pixels for English characters and 16 pixels for
        # Chinese characters(GBK encoding)
        en_zh = [ord(char) > 255 for char in s]
        return en_zh.count(False)*8 + en_zh.count(True)*16, 16


class _convert_24bit_to_565():
    def __getitem__(self, v):
        if isinstance(v, int) and v <= 0xFFFFFF and v >= 0:
            return rgb24to565(v)
        raise KeyError('')


class SPI_Screen_commander(_basic_commander):
    _color_map = {
        str: {
            'black': [0x00, 0x00], 'blue': [0x00, 0x1F], 'purple': [0x41, 0x2B],
            'green': [0x07, 0xE0], 'cyan': [0x07, 0xFF], 'yellow': [0xFF, 0xE0],
            'white': [0xFF, 0xFF], 'pink': [0xF8, 0x1F], 'orange': [0xEC, 0xAF],
            'red': [0xF8, 0x00]},
        int: _convert_24bit_to_565()}
    _singleton = True

    def __init__(self, spi_device, width=None, height=None):
        if SPI_Screen_commander._singleton is False:
            raise RuntimeError('There is already one SPI Screen Commander.')
        self._ili = ILI9341_API(spi_device, width=width, height=height)
        self._ili.setfont(os.path.join(BASEDIR, 'files/fonts/yahei_mono.ttf'))
        self._name = '[SPI screen commander] '
        self.width, self.height = width, height
        self._command_dict = {}  # this is a fake commander so leave it empty
        SPI_Screen_commander._singleton = False

    def getsize(self, s, size=None, font=None):
        '''
        get
        Returns
        -------
        w, h: tuple | None
            size in pixel
        s: str | None
            string in correct encoding
        font_path: str | None
            If param `font` offered, check whether font exist. If font file not
            exists or supported, return None.
        '''
        if sys.version_info.major == 2 and not isinstance(s, unicode):
            s = s.decode('utf8')
        if size is not None:
            self._ili.setsize(size)
        if font is not None and os.path.exist(font):
            font_backup = self._ili.font.path
            try:
                self._ili.setfont(font)
                w, h = self._ili.font.getsize(s)
                return w/2, h/2
            except:
                self._ili.setfont(font_backup)
        w, h = self._ili.font.getsize(s)
        return w/2, h/2

    def start(self):
        self._ili.start()
        self.width, self.height = self._ili.width, self._ili.height

    def send(self, key, *a, **k):
        '''
        Never inherit API class, just use it. Because funcitons with same
        names may conflict with each other!
        super(aaa, self).bbb() is not a good idea.
        '''
        if 'c' in k:
            assert type(k['c']) in self._color_map, 'c only can be str or int'
            try:
                k['c'] = self._color_map[type(k['c'])][k['c']]
            except KeyError:
                raise ValueError('Unsupported color: {}'.format(k['c']))
        # if 'bg' in k and k['bg'] is not None:
        #     assert type(k['bg']) in self._color_map, 'bg can be str or int'
        #     try:
        #         k['bg'] = self._color_map[type(k['bg'])][k['bg']]
        #         k['bg'] = list(ILI9341_API.rgb565to888(*k['bg']))
        #     except NameError:
        #         raise ValueError('Unsupported bg color: {}'.format(k['bg']))
        if hasattr(self._ili, 'draw_' + key):
            getattr(self._ili, 'draw_' + key)(*a, **k)
        elif hasattr(self._ili, key):
            getattr(self._ili, key)(*a, **k)
        else:
            print(self._name + 'No such key `{}`!'.format(key))

    def close(self):
        self._ili.close()


class _testReader(unittest.TestCase):
    def setUp(self):
        print('=' * 80)
        self.username = 'test'
        self._r = Fake_data_generator(sample_rate=10,
                                      sample_time=2,
                                      n_channel=8)
        self._r.start()
        print('=' * 80)

    def tearDown(self):
        print('=' * 80)
        self._r.close()
        print('=' * 80)

    def test_1_test_reader(self):
        '''
        test Fake_data_generator reader
        '''
        print('=' * 80)
        print('Is streaming: {}'.format(self._r.is_streaming))
        print('Real sample_rate: {}'.format(self._r.real_sample_rate))
        for i in range(5):
            print(self._r.data_channel)
        self._r.pause()
        self._r.resume()
        print(self._r.data_frame)
        print('=' * 80)

    def test_2_load_data(self):
        '''
        try to load all data of user `test`
        '''
        print('=' * 80)
        data, label, action_dict = load_data(self.username)
        print('load data with shape of {}'.format(data.shape))
        print('label: {}'.format(label))
        print('action_dict: {}'.format(action_dict))

    def test_3_save_data(self):
        '''
        then save into one file and delete it
        '''
        print('=' * 80)
        data = np.zeros((1, 8, 250))
        save_data(self.username, data, 'aabbcc', 250, print_summary=True)
        datafile = os.path.join(BASEDIR, 'data', self.username, 'aabbcc*')
        os.system('rm ' + datafile)
        print('=' * 80)


class _testCommander(unittest.TestCase):
    def setUp(self):
        self.stop = virtual_serial()
        self._c = Serial_Screen_commander()
        self._c.start()

    def tearDown(self):
        self.stop.set()
        self._c.close()

    def test_draw_circle(self):
        self._c.send('circle', 10, 20, 5, 'black')


if __name__ == '__main__':
    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(_testReader))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(_testCommander))
    filename = os.path.join(BASEDIR, 'files/test/test-%s.html' % __file__)
    with open(filename, 'w') as f:
        HTMLTestRunner(stream=f,
                       title='%s Test Report' % __name__,
                       description='generated at ' + time_stamp(),
                       verbosity=2).run(suite)
