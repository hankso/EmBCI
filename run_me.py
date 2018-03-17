#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Sun Mar  4 20:04:34 2018

@author: hank
"""
from __future__ import print_function
import time

import sys
sys.path += ['./src', './utils']

from classifier import Models
from frame import sEMG
#from IO import Serial_reader as Reader
from IO import Pylsl_reader as Reader
from common import check_input

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
    
    username = check_input('Hi! Please offer your username: ', answer={})
    
    reader = Reader(sample_rate, sample_time, username, n_channels)
    reader.start()
    model  = Models(sample_rate, sample_time, model_name='Default')

    try:
        sEMG(username, reader, model)
    except KeyboardInterrupt:
        reader.stop()
# =============================================================================
#     except SystemExit as e:
#         print(e)
# =============================================================================

    print('loging out...')
    time.sleep(3)