#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Thu Mar 22 09:25:36 2018

@author: hank
"""
# built-in
from __future__ import print_function
import os
import time
import threading

# pip install pyserial, pylsl
import serial
import pylsl

# from ./
from common import find_ports, find_outlets
# =============================================================================
# from gyms import TorcsEnv
# =============================================================================
# =============================================================================
# from gyms import PlaneClient
# =============================================================================




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
        
class _basic_commander(object):
    def __init__(self, command_dict):
        self._command_dict = command_dict
        self._last_time = time.time()
        
    def _time_duration(time):
        def decorator(func):
            def wrapper(self, *args, **kwargs):
                if (time.time() - self._last_time) < time:
                    print('.', end='')
                    return None
                else:
                    self._last_time = time.time()
                    return func(self, *args, **kwargs)
            return wrapper
        return decorator
        
    def start(self):
        raise NotImplemented('you can not use this class')
        
    def send(self, action_name):
        raise NotImplemented('you can not use this class')
        
    def write(self, action_name):
        '''
        wrapper for usage of `print(cmd, file=commander)`
        '''
        self.send(action_name)
        
    def close(self):
        raise NotImplemented('you can not use this class')
        

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
        print('[Pylsl reader] finding availabel outlets...')
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
                d = [t - self._start_time] + d[1:self.n_channel + 1]
                for i, ch in enumerate(self.ch_list):
                    self.buffer[ch].append(d[i])
                    if len(self.buffer[ch]) > self.window_size:
                        self.buffer[ch].pop(0)
                #==============================================================

        except Exception as e:
            print('[Pylsl reader] {}'.format(e))
            print('[Pylsl reader] pylsl client shut down.')
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
        print('[Serial reader] finding availabel ports...')
        port = find_ports()
        self._serial.port = port
        self._serial.open()
        self._start_time = time.time()
        if self._send_to_pylsl:
            info = pylsl.StreamInfo('Serial_reader', 'unknown', self.n_channel,
                                    self.sample_rate, 'float32', port)
            self.outlet = pylsl.StreamOutlet(info)
        
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
            print('[Serial reader] serial client shut down.')
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
            print('[Serial reader] serial client shut down.')
        finally:
            self._serial.close()
        
    def isOpen(self):
        return self._serial.isOpen()
    
    
# =============================================================================
# class Torcs_commander(_basic_commander):
#     def __init__(self, command_dict = {}):
#         super(Torcs_commander, self).__init__(command_dict)
#         
#     def start(self):
#         print('[Torcs commander] initializing TORCS...')
#         self.env = TorcsEnv(vision=True, throttle=False, gear_change=False)
#         self.env.reset()
#     
# # =============================================================================
# #     # TODO: set time duration
# #     @_time_duration(1)
# # =============================================================================
#     def send(self, key, prob, *args, **kwargs):
#         cmd = [abs(prob) if key == 'right' else -abs(prob)]
#         print('[Torcs commander] sending cmd {}'.format(cmd))
#         self.env.step(cmd)
#         return cmd
#     
#     def write(self, key):
#         self.send(key)
#         
#     def close(self):
#         self.env.end()
# 
# # action_class : command_str
# plane_command_dict = {
#         'left':'3',
#         'right':'4',
#         'up':'1',
#         'down':'2',
#         'disconnect':'9'
# }
# 
# 
# class Plane_commander(_basic_commander):
#     def __init__(self, command_dict=plane_command_dict):
#         super(Plane_commander, self).__init__(command_dict)
#         
#     def start(self):
#         self.client = PlaneClient()
#     
#     def send(self, key, *args, **kwargs):
#         if key not in self._command_dict:
#             print('Wrong command key! Abort.')
#             return
#         self.client.send(self._command_dict[key])
#         return self._command_dict[key]
#     
#     def close(self):
#         pass
# =============================================================================

# action_class : command_str
glove_box_command_dict_v1 = {
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
        'thumb-little':'D'
}


class Serial_commander(_basic_commander):
    def __init__(self, baudrate=9600,
                 command_dict=glove_box_command_dict_v1,
                 CR = True, LF = True):
        super(Serial_commander, self).__init__(command_dict)
        self._serial = serial.Serial(baudrate=baudrate)
        self._CR = CR
        self._LF = LF
        self._last_time = time.time()
        
    def start(self):
        print('[Serial commander] finding availabel ports...')
        self._serial.port = find_ports()
        self._serial.open()
    
    def send(self, key, *args, **kwargs):
        if (time.time() - self._last_time) < 5:
            return None
        self._last_time = time.time()
        if key not in self._command_dict:
            print('Wrong command key! Abort.')
            return
        self._serial.write(self._command_dict[key])
        if self._CR:
            self._serial.write('\r')
        if self._LF:
            self._serial.write('\n')
        return self._command_dict[key]
    
    def close(self):
        self._serial.close()
    
    def isOpen(self):
        return self._serial.isOpen()
    
    def reconnect(self):
        try:
            self._serial.close()
            time.sleep(1)
            self._serial.open()
            print('[Serial commander] reconnect success.')
        except:
            print('[Serial commander] reconnect failed.')
            


if __name__ == '__main__':
    username = 'test'
    
    commander = Serial_commander(9600, command_dict=glove_box_command_dict_v1)
    commander.start()
    commander.send('thumb')
# =============================================================================
#     
#     # openbci 8-channel 250Hz
#     s = Serial_reader(250, 5, username, 1)
#     s.start()
#     p = Pylsl_reader('OpenBCI_EEG', sample_rate=250, sample_time=2, n_channel=2)
#     p.start()
# =============================================================================
