#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Sun Mar  4 20:04:34 2018

@author: hank
"""
# built-in
from __future__ import print_function
import time
import sys
sys.path += ['./src', './utils']

# from ./utils
from classifier import Models
from frame import sEMG
from common import check_input
# =============================================================================
# from data_socket import Serial_reader as Reader
# =============================================================================
from data_socket import Pylsl_reader as Reader

from data_socket import Serial_commander as Commander
# =============================================================================
# from data_socket import Plane_commander as Commander
# =============================================================================



if __name__ == '__main__':
    
# =============================================================================
#     # myo
#     sample_rate = 512
#     sample_time = 3
#     n_channels  = 1
# =============================================================================
    
    # OpenBCI 250Hz 2s 500samples 2channel
    sample_rate = 250
    sample_time = 2
    n_channels  = 2
    
    
    
    window_size = sample_rate * sample_time
    try:
        print('username: ' + username)
    except NameError:
        username = check_input('Hi! Please offer your username: ', answer={})
    
    # start reading data from socket(bluetooth@serial or pylsl@localhost:port)
    # it's in a seperate thread, stop recording by `reader.do_stop()`
    reader = Reader(sample_rate, sample_time, username, n_channels)
    reader.start()
    
    # available classification models see Models.supported_models
    model  = Models(sample_rate, sample_time, model_type='Default')
    
    # control glove-box or plane-war-game or torcs-car-game
    commander = Commander()
    commander.start()

    try:
        sEMG(username, reader, model, commander)
    except KeyboardInterrupt:
        reader.do_stop()

    print('loging out...')
    time.sleep(3)