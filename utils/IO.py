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
import threading
import socket

# pip install numpy, scipy, serial, mne
import scipy.io as sio
import numpy as np
import serial
import pylsl
import mne

# from ./
from common import check_dir, check_input, get_label_list, Timer
from common import record_animate, get_self_ip_addr
from common import find_ports, find_outlets
from gyms import TorcsEnv
from gyms import PlaneClient
from gpio4 import SysfsGPIO
from ads1299_api import ADS1299_API


@check_dir
def save_data(username,
              data,
              label,
              sample_rate,
              print_summary=False,
              save_fif=False):
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
    
    fn = './data/%s/%s.mat'%(username, '-'.join([label, num]))
    sio.savemat(fn, {label: data}, do_compression=True)
    print('{} data save to {}'.format(data.shape, fn))
    
    if save_fif:
        if not os.path.exists('./data/fif'):
            os.mkdir('./data/fif')
        if not os.path.exists('./data/fif/' + username):
            os.mkdir('./data/fif/' + username)
        for sample in data:
            fn = './data/fif/%s/%s-raw.fif.gz' % (username,
                                                  '-'.join([label, num]))
            num += 1
            info = mne.create_info(ch_names=sample.shape[0], sfreq=sample_rate)
            mne.io.RawArray(sample, info).save(fn, verbose=0)
            print('{} data save to {}'.format(sample.shape, fn))

    if print_summary:
        print(get_label_list(username)[1])


@check_dir
def load_data(username, print_summary=True):
    '''
    读取./data/username文件夹下的所有数据，返回三维数组

    Output shape: n_samples x n_channel x window_size
    '''
    if not os.listdir('./data/' + username):
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
        for fn in os.listdir('./data/' + username):  # action_num
            if fn.startswith(action_name) and fn.endswith('.mat'):
                file_path = './data/%s/%s' % (username, fn)
                dat = sio.loadmat(file_path)[action_name]
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
        record_animate(reader.sample_time)
        try:
            if action_name and '-' not in action_name:
                # input shape: 1 x n_channel x window_size

                #==========================================================
                save_data(username,
                          reader.get_data(),
                          action_name,
                          reader.sample_rate,
                          print_summary=True)
                #==========================================================

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
    def __init__(self, sample_rate, sample_time, n_channel):
        # basic stream reader information
        self.sample_rate = sample_rate
        self.sample_time = sample_time
        self.n_channel = n_channel
        self.window_size = sample_rate * sample_time
        
        # channels are defined here
        self.ch_list = ['time'] + ['channel%d' % i for i in range(n_channel)]
        self.buffer = {ch: [] for ch in self.ch_list}

        # use these flags to controll the data streaming thread
        self.streaming = False
        self._flag_pause = threading.Event()
        self._flag_close = threading.Event()
        
        # info pipe
        self.info = [0] * 10
        self._started = False

    def start(self):
        '''
        rewrite this to start buffing data from different sources
        '''
        raise NotImplementedError('not implemented yet')
        
    def close(self):
        self._flag_close.set()
        self.streaming = False

    def pause(self):
        self._flag_pause.clear()
        self.streaming = False
        
    def resume(self):
        self._flag_pause.set()
        self.streaming = True
        
    @property
    def real_sample_rate(self):
        try:
            tmp = self.buffer['time'][-10:]
            return 10.0/(tmp[-1] - tmp[0])
        except:
            return 0
    
    @property
    def ch_data(self):
        return [self.buffer[ch][-1] for ch in self.ch_list[1:]]
    
    def get_data(self, size=None):
        if size is None:
            size = self.window_size
        return np.array([self.buffer[ch][-size:] \
                         for ch in self.ch_list[1:]])\
                .reshape(1, self.n_channel, self.window_size)
    
    def isOpen(self):
        return not self._flag_close.isSet()
    

class Files_reader(_basic_reader):
    '''
    Read date from mat, fif, csv... file and simulate as a common data reader
    '''
    _num = 1
    def __init__(self,
                 filename,
                 sample_rate=256,
                 sample_time=2,
                 n_channel=1):
        super(Files_reader, self).__init__(sample_rate, sample_time, n_channel)
        self.filename = filename
        self._name = '[Files reader %d] ' % Files_reader._num
        Files_reader._num += 1
    
    def start(self):
        if self._started:
            return
        print(self._name + 'reading data file...')
        while 1:
            try:
                if self.filename.endswith('.mat'):
                    actionname = os.path.basename(self.filename).split('-')[0]
                    self._data = sio.loadmat(self.filename)[actionname][0]
                    self._data = self._data.reshape(self.n_channel,
                                self.sample_rate * self.sample_time).T
                    self._generator = self._get_data_generator()
                    break
                elif self.filename.endswith('.fif'):
                    raise NotImplemented
            except IOError:
                self.filename = check_input(('No such file! Please check and '
                                             'input file name: '), {})
            except ValueError:
                print(self._name + 'Bad data shape {}!'.format(self._data.shape))
                print(self._name + 'Abort...')
                return
                
        self._start_time = time.time()
        self._thread = threading.Thread(target=self._read_data)
        self._thread.setDaemon(True)
        self._thread.start()
        self._flag_pause.set()
        self.streaming = True
        self._started = True
        
    def _get_data_generator(self):
        for i in self._data:
            yield i
        
    def _read_data(self):
        try:
            while not self._flag_close.isSet():
                self._flag_pause.wait()
                time.sleep(1.0/self.sample_rate)
                d, t = self._generator.next(), time.time()
                d = [t - self._start_time] + list(d)
                for i, ch in enumerate(self.ch_list):
                    self.buffer[ch].append(d[i])
                    if len(self.buffer[ch]) > self.window_size:
                        self.buffer[ch].pop(0)
        except Exception as e:
            print(self._name + str(e))
        finally:
            print(self._name + 'stop fetching data...')
            print(self._name + 'shut down.')
    
    

class Pylsl_reader(_basic_reader):
    '''
    Connect to a data stream on localhost:port and read data into buffer.
    There should be at least one stream available.
    '''
    _num = 1
    def __init__(self,
                 sample_rate=256,
                 sample_time=2,
                 n_channel=1,
                 servername=None):
        super(Pylsl_reader, self).__init__(sample_rate, sample_time, n_channel)
        self._servername = servername
        self._name = '[Pylsl reader %d] ' % Pylsl_reader._num
        Pylsl_reader._num += 1
        
    def start(self):
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
            return
        # 1. find available streaming info and build an inlet 
        print(self._name + 'finding availabel outlets...')
        info = find_outlets(self._servername)
        if info.channel_count() < self.n_channel:
            raise RuntimeError(('You want %d channel data but only %d channels'
                                ' is offered by pylsl stream outlet you select'
                                '.') % (self.n_channel, info.channel_count()))
        max_buflen = (self.sample_time if info.nominal_srate() != 0 else \
                      int(self.window_size/100) + 1)
        self._inlet = pylsl.StreamInlet(info, max_buflen=max_buflen)
        self._start_time = info.created_at()
        
        # 2. start streaming thread to fetch data into buffer continuously
        self._thread = threading.Thread(target=self._read_data)
        self._thread.setDaemon(True)
        self._thread.start()
        
        # 3. set flags
        self._flag_pause.set()
        self.streaming = True
        self._started = True
    
    def _read_data(self):
        try:
            while not self._flag_close.isSet():
                self._flag_pause.wait()
                d, t = self._inlet.pull_sample()
                d = [t - self._start_time] + d[1:self.n_channel + 1]
                for i, ch in enumerate(self.ch_list):
                    self.buffer[ch].append(d[i])
                    if len(self.buffer[ch]) > self.window_size:
                        self.buffer[ch].pop(0)
        except Exception as e:
            print(self._name + str(e))
        finally:
            print(self._name + 'stop fetching data...')
            self._inlet.close_stream()
            print(self._name + 'pylsl reader shut down.')
    
    def isOpen(self):
        '''
        use inlet status as reader open flag
        '''
        try:
            self._inlet.open_stream(0.01)
            return True
        except:
            return False
    

class Serial_reader(_basic_reader):
    '''
    Connect to a serial port and fetch data into buffer.
    There should be at least one port available.
    '''
    _num = 1
    def __init__(self,
                 sample_rate=256,
                 sample_time=2,
                 n_channel=1,
                 baudrate=115200,
                 send_to_pylsl=False):
        super(Serial_reader, self).__init__(sample_rate, sample_time, n_channel)
        self._serial = serial.Serial(baudrate=baudrate)
        self._name = '[Serial reader %d] ' % Serial_reader._num
        Serial_reader._num += 1
        self._send_to_pylsl = send_to_pylsl
        
    def start(self):
        if self._started:
            return
        # 1. find serial port and connect to it
        print(self._name + 'finding availabel ports...')
        port = find_ports()
        self._serial.port = port
        self._serial.open()
        self._start_time = time.time()
        
        # 2. start main thread
        # here we only need to check one time whether send_to_pylsl is set
        # if put this work in thread, it will be checked thousands times.
        if self._send_to_pylsl:
            self.outlet = pylsl.StreamOutlet(pylsl.StreamInfo('Serial_reader',
                                                              'unknown',
                                                              self.n_channel,
                                                              self.sample_rate,
                                                              'float32', port))
            self._thread = threading.Thread(target=self._read_data_send_pylsl)
        else:
            self._thread = threading.Thread(target=self._read_data)
        self._thread.setDaemon(True)
        self._thread.start()
        
        # 3. set pause flag and streaming flag
        self._flag_pause.set()
        self.streaming = True
        self._started = True

    def _read_data(self):
        try:
            while not self._flag_close.isSet():
                self._flag_pause.wait()
                d = self._serial.read_until().strip().split(',')
                d = [time.time() - self._start_time] + d[:self.n_channel]
                for i, ch in enumerate(self.ch_list):
                    self.buffer[ch].append(float(d[i]))
                    if len(self.buffer[ch]) > self.window_size:
                        self.buffer[ch].pop(0)
        except Exception as e:
            print(self._name + str(e))
        finally:
            print(self._name + 'stop fetching data...')
            self._serial.close()
            print(self._name + 'serial reader shut down.')
            
    def _read_data_send_pylsl(self):
        try:
            while not self._flag_close.isSet():
                self._flag_pause.wait()
                d = self._serial.read_until().strip().split(',')
                d = [time.time() - self._start_time] + [float(i) for i in \
                                                        d[:self.n_channel]]
                for i, ch in enumerate(self.ch_list):
                    self.buffer[ch].append(float(d[i]))
                    if len(self.buffer[ch]) > self.window_size:
                        self.buffer[ch].pop(0)
                self.outlet.push_sample(d[1:])
        except Exception as e:
            print(self._name + str(e))
        finally:
            print(self._name + 'stop fetching data...')
            self._serial.close()
            print(self._name + 'serial reader shut down.')
        
    def isOpen(self):
        return self._serial.isOpen()


class ADS1299_reader(_basic_reader):
    '''
    Read data from SPI connection with ADS1299.
    This class is only used on ARM. It depends on module `spidev` and `gpio3`
    '''
    _num = 1
    def __init__(self,
                 sample_rate=500,
                 sample_time=2,
                 n_channel=8,
                 send_to_pylsl=True,
                 device=(1, 0)):
        super(ADS1299_reader, self).__init__(sample_rate, sample_time, n_channel)
        self._name = '[ADS1299 reader %d] ' % ADS1299_reader._num
        ADS1299_reader._num += 1
        
        self._send_to_pylsl = send_to_pylsl
        
        self._ads = ADS1299_API(sample_rate)
        
        self.device = device
        
    def start(self):
        if self._started:
            return
        # 1. find avalable spi devices
        print(self._name + 'finding available spi devices... ', end='')
        dev = self._ads.open(self.device, max_speed_hz=1000000)
        print('spi%d-%d' % dev)
        self._ads.start()
        self._start_time = time.time()
        
        # 2. start main thread
        # here we only need to check one time whether send_to_pylsl is set
        # if put this work in thread, it will be checked thousands times.
        if self._send_to_pylsl:
            self.outlet = pylsl.StreamOutlet(pylsl.StreamInfo('SPI_reader',
                                                              'unknown',
                                                              self.n_channel,
                                                              self.sample_rate,
                                                              'float32',
                                                              'spi%d-%d '%dev))
            self._thread = threading.Thread(target=self._read_data_send_pylsl)
        else:
            self._thread = threading.Thread(target=self._read_data)
        self._thread.setDaemon(True)
        self._thread.start()
        
        # 3. set pause flag and streaming flag
        self._flag_pause.set()
        self.streaming = True
        self._started = True
    
    def _read_data(self):
        try:
            while not self._flag_close.isSet():
                self._flag_pause.wait()
                d = list(self._ads.read())
                d = [time.time() - self._start_time] + d[:self.n_channel]
                dat = []
                for i, ch in enumerate(self.ch_list):
                    self.buffer[ch].append(d[i])
                    dat += [d[i]]
                    if len(self.buffer[ch]) > self.window_size:
                        self.buffer[ch].pop(0)
        except Exception as e:
            print(self._name + str(e))
        finally:
            print(self._name + 'stop fetching data...')
            self._ads.close()
            print(self._name + 'SPI reader shut down.')
    
    def _read_data_send_pylsl(self):
        try:
            while not self._flag_close.isSet():
                self._flag_pause.wait()
                d = list(self._ads.read())
                d = [time.time() - self._start_time] + d[:self.n_channel]
                for i, ch in enumerate(self.ch_list):
                    self.buffer[ch].append(d[i])
                    if len(self.buffer[ch]) > self.window_size:
                        self.buffer[ch].pop(0)
                self.outlet.push_sample(d[1:])
        except Exception as e:
            print(self._name + str(e))
        finally:
            print(self._name + 'stop fetching data...')
            self._ads.close()
            print(self._name + 'SPI reader shut down.')
            


class Socket_reader(_basic_reader):
    '''
    Maybe socket client is a more proper name but this is also easy to 
    understand. Read data from socket.
    '''
    _num = 1
    def __init__(self,
                 sample_rate=250,
                 sample_time=2,
                 n_channel=8):
        super(Socket_reader, self).__init__(sample_rate, sample_time, n_channel)
        self._name = '[Socket reader %d] ' % Socket_reader._num
        Socket_reader._num += 1
        
        # TCP IPv4 socket connection
        self._client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
    def start(self):
        if self._started:
            return
        # 1. IP addr and port are offered by user, connect to that host:port
        print(self._name + 'configuring addr... input "quit" to abort')
        while 1:
            r = check_input(('please input an address in format "host,port"\n'
                             '>>> 192.168.0.1:8888 (example)\n>>> '), {})
            if r == 'quit':
                raise SystemExit(self._name + 'mannually exit')
            try:
                host, port = r.split(':')
                assert int(port) > 0
                socket.inet_aton(host)
                break
            except:
                print(self._name + 'invalid addr!')
        self._client.connect((host, int(port)))
        self._start_time = time.time()
        
        # 2. read data in another thread
        self._thread = threading.Thread(target=self._read_data)
        self._thread.setDaemon(True)
        self._thread.start()
        
        # 3. set pause flag and streaming flag
        self._flag_pause.set()
        self.streaming = True
        self._started = True
    
    def _read_data(self):
        try:
            while not self._flag_close.isSet():
                self._flag_pause.wait()
                # 8-channel float32 data = 8*32bits = 32bytes
                # d is np.ndarray with a shape of (8, 1)
                d = np.frombuffer(self._client.recv(32), np.float32)
                d = [time.time() - self._start_time] + list(d)[:self.n_channel]
                for i, ch in enumerate(self.ch_list):
                    self.buffer[ch].append(d[i])
                    if len(self.buffer[ch]) > self.window_size:
                        self.buffer[ch].pop(0)
        except IndexError:
            print('Maybe server send out data too fast, and '
                  'this client cannot keep up to it.')
        except Exception as e:
            print(self._name + str(e))
        finally:
            print(self._name + 'stop fetching data...')
            self._client.close()
            print(self._name + 'Socket reader shut down.')
    

class Socket_server(object):
    '''
    Send data to socket host:port, default to 0.0.0.0:9999
    '''
    _num = 1
    def __init__(self, host='0.0.0.0', port=9999):
# =============================================================================
#         if host is None:
#             host = get_self_ip_addr()
# =============================================================================
            
        self._name = '[Socket server %d] ' % Socket_server._num
        self.connections = []
        Socket_server._num += 1
        
        # TCP IPv4 socket connection
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.bind((host, port))
        self._server.listen(5)
        self._server.settimeout(1)
        print(self._name + 'binding socket server at %s:%d' % (host, port))
        
        # handle connection in a seperate thread
        self._flag_close = threading.Event()
        self._thread = threading.Thread(target=self._manage_connections)
        self._thread.setDaemon(True)
        self._thread.start()
    
    def _manage_connections(self):
        while not self._flag_close.isSet():
            # accept connection, wait for 1 second
            try:
                con, addr = self._server.accept()
                print(self._name + 'accept client from {}:{}'.format(
                        *con.getpeername()))
                self.connections += [con]
            except:
                pass
            
            # clear closed connections, each one cost 1 second
            for i, con in zip(range(len(self.connections)), self.connections):
                try:
                    con.settimeout(1)
                    if con.recv(1024) == '':
                        print(self._name + 'lost client from {}:{}'.format(
                                *con.getpeername()))
                        con.close()
                        self.connections.pop(i)
                except:
                    pass
    
    def send(self, data):
        for con in self.connections:
            con.sendall(data.tobytes())
            
    def close(self):
        print(self._name + 'stop broadcasting data...')
        self._flag_close.set()
        for con in self.connections:
            con.close()
        self._server.close()
        print(self._name + 'Socket server shut down.')

    def has_listener(self):
        return len(self.connections)


class Fake_data_generator(_basic_reader):
    def __init__(self, sample_rate=250, sample_time=3, n_channel=8):
        super(Fake_data_generator, self).__init__(sample_rate, sample_time, n_channel)
        self._name = '[Fake data generator] '
        
    def start(self):
        if self._started:
            return
        print(self._name + 'establishing pylsl outlet...')
        self.outlet = pylsl.StreamOutlet(pylsl.StreamInfo(
                'fake_data_generator',
                'unknown',
                self.n_channel,
                self.sample_rate,
                'float32',
                'used for debugging'))
        self._start_time = time.time()
        self._thread = threading.Thread(target=self._read_data_send_pylsl)
        self._thread.setDaemon(True)
        self._thread.start()
        self._flag_pause.set()
        self.streaming = True
        self._started = True
        
    def _read_data_send_pylsl(self):
        try:
            while not self._flag_close.isSet():
                self._flag_pause.wait()
                time.sleep(0.9/self.sample_rate)
                d = [time.time() - self._start_time] + list(np.random.random(self.n_channel))
                for i, ch in enumerate(self.ch_list):
                    self.buffer[ch].append(d[i])
                    if len(self.buffer[ch]) > self.window_size:
                        self.buffer[ch].pop(0)
                self.outlet.push_sample(d[1:])
        except Exception as e:
            print(self._name + str(e))
        finally:
            print(self._name + 'stop generating data...')
            print(self._name + 'fake data generator shut down.')


        
class _basic_commander(object):
    def __init__(self, command_dict):
        self._command_dict = command_dict
        try:
            print('[Command Dict] %s' % command_dict['_desc'])
        except:
            print('[Command Dict] current command dict does not have a '
                  'key named _desc to describe itself. pls add it.')
        
    def start(self):
        raise NotImplemented('you can not use this class')
        
    def send(self, key, *args, **kwargs):
        raise NotImplemented('you can not use this class')
        
    def write(self, key, *args, **kwargs):
        '''
        wrapper for usage of `print(cmd, file=commander)`
        '''
        self.send(key, *args, **kwargs)
        
    def close(self):
        raise NotImplemented('you can not use this class')
    


class Torcs_commander(_basic_commander):
    '''
    Send command to TORCS(The Open Race Car Simulator)
    You can output predict result from classifier to the 
    game to control race car(left, right, throttle, brake...)
    '''
    _num = 1
    def __init__(self, command_dict = {}):
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



# action_class : command_str
plane_command_dict = {
        'left':'3',
        'right':'4',
        'up':'1',
        'down':'2',
        'disconnect':'9',
        '_desc': ("plane war game support command : "
                  "left, right, up, down, disconnect")
}

class Plane_commander(_basic_commander):
    '''
    Send command to plane war game.
    Controlling plane with `left`, `right`, `up` and `down`.
    '''
    def __init__(self, command_dict=plane_command_dict):
        super(Plane_commander, self).__init__(command_dict)
        
    def start(self):
        self.client = PlaneClient()
    
    @Timer.duration('Plane_commander', 1)
    def send(self, key, *args, **kwargs):
        if key not in self._command_dict:
            print(self._name + 'Wrong command {}! Abort.'.format(key))
            return
        self.client.send(self._command_dict[key])
        return self._command_dict[key]
    
    def close(self):
        pass



class Pylsl_commander(_basic_commander):
    '''
    Send predict result to pylsl as an online command stream
    '''
    _num = 1
    def __init__(self, command_dict={'_desc':'send command to pylsl'}):
        super(Pylsl_commander, self).__init__(command_dict)
        self._name = '[Pylsl commander %d] ' % Pylsl_commander._num
        Pylsl_commander._num += 1
        
    def start(self):
        self.outlet = pylsl.StreamOutlet(pylsl.StreamInfo('Pylsl_commander',
                                                          'predict result',
                                                          1, 0.0, 'string',
                                                          'pylsl commander'))
    
    @Timer.duration('Pylsl commander', 0)
    def send(self, key, *args, **kwargs):
        if not isinstance(key, str):
            raise RuntimeError(self._name + ( 'only accept str but got type {}'
                                              .format(type(key)) ) )
        self.outlet.push_sample([key])
        
    def close(self):
        pass



command_dict_glove_box = {
        'thumb':'1',
        'index':'2',
        'middle':'3',
        'ring':'5',
        'little':'4',
        'grab-all':'6',
        'relax':'7',
        'grab':'8',
        'thumb-index':'A',
        'thumb-middle':'B',
        'thumb-ring':'C',
        'thumb-little':'D',
        '_desc': ("This is a dict for glove box version 1.0.\n"
                  "Support command:\n\t"
                  "thumb, index, middle, ring\n\t"
                  "little, grab-all, relax, grab\n"),
}

class Serial_commander(_basic_commander):
    _num =  1
    def __init__(self, baudrate=9600,
                 command_dict=command_dict_glove_box,
                 CR = True, LF = True):
        super(Serial_commander, self).__init__(command_dict)
        self._serial = serial.Serial(baudrate=baudrate)
        self._CR = CR
        self._LF = LF
        self._name = '[Serial commander %d] ' % Serial_commander._num
        Serial_commander._num += 1
        
    def start(self, port=None):
        print(self._name + 'finding availabel ports...')
        self._serial.port = port if port else find_ports()
        self._serial.open()
    
    @Timer.duration('Serial_commander', 5)
    def send(self, key, *args, **kwargs):
        if key not in self._command_dict:
            print(self._name + ' Wrong command {}! Abort.'.format(key))
            return
        self._serial.write(self._command_dict[key])
        if self._CR:
            self._serial.write('\r')
        if self._LF:
            self._serial.write('\n')
        return self._command_dict[key]
    
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
                  "text     | x, y, s\n")
}

command_dict_arduino_screen_v2 = {
        'points': ['P{:c}{}', 0.1],
        'point':  ['D{:c}{}', 0.05],
        'text':   ['S{:c}{:s}', 0.1],
        'clear':  ['C', 0.5],
        '_desc': ("Arduino-controlled ILI9325D 2.3' 220x176 LCD screen v1.0:\n"
                  "Commands | Args\n"
                  "points   | len(pts), bytearray([y for x, y in pts])\n"
                  "point    | len(pts), bytearray(np.array(pts, np.uint8).reshape(-1))\n"
                  "text     | len(str), str\n"
                  "clear    | no args, clear screen\n"),
}

command_dict_uart_screen_v1 = {
        'point':  ['PS({x},{y},{c});\r\n', 0.4/220],
        'line':   ['PL({x1},{y1},{x2},{y2},{c});\r\n', 4.0/220],
        'circle': ['CIR({x},{y},{r},{c});\r\n', 3.0/220],
        'circlef':['CIRF({x},{y},{r},{c});\r\n', 8.0/220],
        'rect':   ['BOX({x1},{y1},{x2},{y2},{c});\r\n', 3.0/220],
        'rectf':  ['BOXF({x1},{y1},{x2},{y2},{c});\r\n', 15.0/220],
        'text':   ['DC16({x},{y},{s},{c});\r\n', 15.0/220],
        'dir':    ['DIR({:d});\r\n', 3.0/220],
        'clear':  ['CLR(0);\r\n', 12.0/220],
        '_desc': ("UART-controlled Winbond 2.3' 220x176 LCD screen:\n"
                  "Commands | Args\n"
                  "point    | x, y, c\n"
                  "line     | x1, y1, x2, y2, c\n"
                  "circle   | x, y, r, c\n"
                  "circlef  | x, y, r, c, filled circle\n"
                  "rect     | x1, y1, x2, y2, c\n"
                  "rectf    | x1, y1, x2, y2, c, filled rectangle\n"
                  "text     | x, y, s(string), c(color)\n"
                  "dir      | one num, 0 means vertical, 1 means horizental\n"
                  "clear    | clear screen will black\n")
}

class Screen_commander(Serial_commander):
    def __init__(self, baudrate=115200, 
                 command_dict=command_dict_arduino_screen_v2):
        super(Screen_commander, self).__init__(baudrate, command_dict)
        self._name = self._name[:-2] + ' for screen' + self._name[-2:]
        
#    @Timer.duration('Screen_commander', 1.0/25.0)
    def send(self, key, *args, **kwargs):
        if key not in self._command_dict:
            print(self._name + 'Wrong command {}! Abort.'.format(key))
            return
        try:
            cmd, delay = self._command_dict[key]
            cmd = cmd.format(*args, **kwargs)
            self._serial.write(cmd)
            time.sleep(delay)
            return cmd
        except IndexError:
            print(self._name + 'unmatch key {} and params {}!'.format(
                    self._command_dict[key], args))
    
    def close(self):
        time.sleep(1.0/25.0)
        self.send('clear')
        self._serial.close()
        


def ADS1299_to_Socket(ads, server):
    last_time = time.time()
    while 1:
        while (time.time() - last_time) < 1.0/ads.sample_rate:
            pass
        last_time = time.time()
        server.send(ads.read())


if __name__ == '__main__':
    os.chdir('../')
    username = 'test'
    data, label, action_dict = load_data(username)
    save_data(username, data, 'testing', 250, print_summary=True)
    os.system('rm ./data/%s/testing*' % username)
# =============================================================================
#     commander = Serial_commander(9600, command_dict=glove_box_command_dict_v1)
#     commander.start()
#     commander.send('thumb')
# =============================================================================
# =============================================================================
#     
#     # openbci 8-channel 250Hz
#     s = Serial_reader(250, 5, 1)
#     s.start()
#     p = Pylsl_reader(servername='OpenBCI_EEG', sample_rate=250, sample_time=2, n_channel=2)
#     p.start()
# =============================================================================
    pass