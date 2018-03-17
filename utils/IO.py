#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Tue Mar  6 20:45:20 2018

@author: hank
"""
import time
import serial
import threading
import scipy.io as sio
import numpy as np
import os
import sys
import pylsl

from common import check_input, get_label_list
from common import find_ports, find_outlets


# =============================================================================
# def 
# =============================================================================


def save_data(username,
              data,
              label,
              summary=False):
    '''
    保存数据的函数，传入参数为username,data,label(这一段数据的标签)
    可以用summary=True打印输出已经存储的数据的label及数量

    Input data shape
    ----------------
        n_sample x n_channel x window_size

    data name format:
        ${DIR}/data/${username}/${label}-${num}.${surfix}
    '''
    if not os.path.exists('./data/' + username):
        os.mkdir('./data/' + username)

    # check data format and shape
    if not isinstance(data, np.ndarray):
        data = np.array(data)
    if len(data.shape) != 3:
        raise IOError('Invalid data shape{}, n_sample x n_channel x '
                      'window_size is recommended!'.format(data.shape))

    label_list = get_label_list(username)[0]
    num = '1' if label not in label_list else str(label_list[label] + 1)
    fn = './data/%s/%s.mat' % (username, '-'.join([label, num]))

    print('{} data save to '.format(data.shape) + fn)
    sio.savemat(fn, {label: data}, do_compression=True)

    #==========================================================================

    # TODO: data save('.fif')

    #==========================================================================

    if summary:
        print(get_label_list(username)[1])


def load_data(username, summary=True):
    '''
    读取./data/username文件夹下的所有数据，返回三维数组

    Output shape: n_samples x n_channel x window_size
    '''
    if not os.path.exists('./data/' + username):
        os.mkdir('./data/' + username)
    assert os.listdir('./data/' + username)

    # here we got a auto-sorted action name list
    # label_list {'action0': action_num, 'action1': action_num, ...}
    # action_dict {'action0': 0, 'action1': 1, ...}
    # label [0, 0, 0, ... , 1, 1, 1, ...]
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
                    print('Invalid data shape{}, n_sample x n_channel x '
                          'window_size is recommended!'.format(data.shape))
                    continue
                data = np.stack([s for s in data] + [s for s in dat])
                label += dat.shape[0] * [n]  # n_samples

    #==========================================================================

    # TODO: data load('.fif')

    #==========================================================================

    if summary:
        print(get_label_list(username)[1])
    return np.array(data), np.array(label), action_dict


def save_action(username, reader):
    '''
    引导用户存储一段数据并给数据打上标签，需要username和数据流对象

    username: where will data be saved to, i.e. which folder
    reader:   where does data come from
    '''
    label_list = get_label_list(username)[0]
    while check_input('Start record action? [Y/n] '):
        time.sleep(reader.sample_time)
        try:
            # reader.buffer is a dict
            action_data = [reader.buffer[ch][-reader.window_size:] \
                           for ch in reader.ch_list if ch is not 'time']
            action_name = check_input(("Input action name or nothing to abort"
                                       "('-' is not allowed in the name): "),
                                      answer={})

            if action_name and '-' not in action_name:
                # input shape: 1 x n_channel x window_size
                action_data = np.array(action_data)
                action_data = action_data.reshape(1,
                                                  reader.n_channel,
                                                  reader.window_size)

                #==========================================================
                save_data(username, action_data, action_name, summary=True)
                #==========================================================

                # update label_list
                if action_name in label_list:
                    label_list[action_name] += 1
                else:
                    label_list[action_name] = 1

        except AssertionError:
            sys.exit('initialization failed')
        except Exception as e:
            print(e)
            continue
    return label_list


class _basic_reader(object):
    def __init__(self, sample_rate, sample_time, username, n_channel):
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
        self._flag_stop  = threading.Event()

    def start(self):
        '''
        rewrite this to start buffing data from different sources
        '''
        raise NotImplementedError('not implemented yet')

    def isOpen(self):
        return self.streaming

    def do_pause(self):
        self._flag_pause.clear()
        self.streaming = False
        
    def do_start(self):
        self._flag_pause.set()
        self.streaming = True

    def do_stop(self):
        self._flag_stop.set()
        self.streaming = False
        

class Pylsl_reader(_basic_reader):
    '''
    Connect to a data stream on localhost:port and read data into buffer.
    There should be at least one stream available.
    '''
    def __init__(self,
                 sample_rate=256,
                 sample_time=2,
                 username='test',
                 n_channel=1,
                 servername=None):
        super(Pylsl_reader, self).__init__(sample_rate,
                                           sample_time,
                                           username,
                                           n_channel)
        self._servername = servername
        
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
        # 1. find available streaming info and build an inlet 
        info = find_outlets(self._servername)
        if info.channel_count() < self.n_channel:
            raise RuntimeError(('you want %d channels data but only %d channel'
                               ' is offered by pylsl stream outlet') % (
                                       self.n_channel,
                                       info.channel_count()))
        max_buflen = (self.sample_time if info.nominal_srate() != 0 else \
                      int(self.window_size/100) + 1)
        self._inlet = pylsl.StreamInlet(info, max_buflen=max_buflen)
        self._start_time = info.created_at()
        
        # 2. start streaming thread to fetch data into buffer continuously
        self._thread = threading.Thread(target=self._read_data)
        self._thread.setDaemon(True)
        self._thread.start()
        
        # 3. set flags(default pause flag is set, clear it)
        self.do_start()
        self.streaming = True
    
    def _read_data(self):
        try:
            while 1:
                self._flag_pause.wait()
                if self._flag_stop.isSet():
                    raise RuntimeError('stop recording...')
                    
                #==============================================================
                d, t = self._inlet.pull_sample()
                d = [t - self._start_time] + d[:self.n_channel]
                for i, ch in enumerate(self.ch_list):
                    self.buffer[ch].append(d[i])
                    if len(self.buffer[ch]) > self.window_size:
                        self.buffer[ch].pop(0)
                #==============================================================

        except Exception as e:
            print('[pylsl reader] {}'.format(e))
            print('pylsl client shut down.')
        finally:
            self._inlet.close_stream()
    
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
    def __init__(self,
                 sample_rate=256,
                 sample_time=2,
                 username='test',
                 n_channel=1,
                 baudrate=115200,
                 send_to_pylsl=False):
        super(Serial_reader, self).__init__(sample_rate,
                                            sample_time,
                                            username,
                                            n_channel)
        self._serial = serial.Serial(baudrate=baudrate)
        self._send_to_pylsl = send_to_pylsl
        
    def start(self):
        # 1. find serial port and connect to it
        port = find_ports()
        self._serial.port = port
        self._serial.open()
        self._start_time = time.time()
        if self._send_to_pylsl:
            info = pylsl.StreamInfo('Serial_reader', 'unknown', self.n_channel,
                                    self.sample_rate, 'float32', port)
            self.outlet = pylsl.StreamOutlet(info, max_buflen=self.sample_time)
        
        # 2. start main thread
        # here we only need to check one time whether send_to_pylsl is set
        # if put this work in thread, it will be checked thousands times.
        if self._send_to_pylsl:
            self._thread = threading.Thread(target=self._read_data_send_pylsl)
        else:
            self._thread = threading.Thread(target=self._read_data)
        self._thread.setDaemon(True)
        self._thread.start()
        
        # 3. set pause flag and streaming flag
        self.do_start()
        self.streaming = True

    def _read_data(self):
        try:
            while 1:
                self._flag_pause.wait()
                if self._flag_stop.isSet():
                    raise RuntimeError('stop recording...')
                    
                #==============================================================
                d = self._serial.read_until().strip().split(',')
                d = [time.time() - self._start_time] + d[:self.n_channel]
                for i, ch in enumerate(self.ch_list):
                    self.buffer[ch].append(float(d[i]))
                    if len(self.buffer[ch]) > self.window_size:
                        self.buffer[ch].pop(0)
                #==============================================================
                
        except Exception as e:
            print('[Serial reader] {}'.format(e))
            print('serial client shut down.')
        finally:
            self._serial.close()
            
    def _read_data_send_pylsl(self):
        try:
            while 1:
                self._flag_pause.wait()
                if self._flag_stop.isSet():
                    raise RuntimeError('stop recording...')
                    
                #==============================================================
                d = self._serial.read_until().strip().split(',')
                d = [time.time() - self._start_time] + d[:self.n_channel]
                dat = []
                for i, ch in enumerate(self.ch_list):
                    self.buffer[ch].append(float(d[i]))
                    dat += [float(d[i])]
                    if len(self.buffer[ch]) > self.window_size:
                        self.buffer[ch].pop(0)
                self.outlet.push_sample(dat[1:])
                #==============================================================
                
        except Exception as e:
            print('[Serial reader] {}'.format(e))
            print('serial client shut down.')
        finally:
            self._serial.close()
        
    def isOpen(self):
        return self._serial.isOpen()



if __name__ == '__main__':
# =============================================================================
#     os.chdir('../')
# =============================================================================
# =============================================================================
#     username = 'test'
# =============================================================================
# =============================================================================
#     data, label, action_dict = load_data(username, summary=True)
# =============================================================================
# =============================================================================
#     save_data(username, data, 'testing', summary=True)
# =============================================================================
    
    # openbci 8-channel 250Hz
# =============================================================================
#     s = Serial_reader(250, 5, username, 1, log=True)
#     s.run()
# =============================================================================
# =============================================================================
#     p = Pylsl_reader('OpenBCI_EEG', sample_rate=250, sample_time=2, n_channel=2)
#     p.run()
# =============================================================================
    pass