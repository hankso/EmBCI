#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Sun Mar  4 20:04:34 2018

@author: hank
"""
# built-in
from __future__ import print_function
import time

from embci.common import check_input
from embci.classifier import Models
from embci.frame import Matplotlib_Plot_Info
#  from embci.frame import sEMG_Recognition

# from embci.IO import Serial_reader as Reader
# from embci.IO import ADS1299_reader as Reader
from embci.IO import Fake_data_generator as Reader

# from embci.IO import Screen_commander as Commander
# from embci.IO import Pylsl_commander as Commander
from embci.IO import Plane_commander as Commander


if __name__ == '__main__':

    # myo
    sample_rate = 512
    sample_time = 3
    n_channels = 1

# =============================================================================
#     # OpenBCI 250Hz 2s 500samples 2channel
#     sample_rate = 250
#     sample_time = 2
#     n_channels  = 2
# =============================================================================

    username = 'test'
    try:
        print('username: ' + username)
    except NameError:
        username = check_input('Hi! Please offer your username: ', answer={})

    # start reading data, it's in a seperate thread, stop by `reader.close()`
    reader = Reader(sample_rate, sample_time, n_channels)
    reader.start()

    # available classification models see Models.supported_models
    model = Models(sample_rate, sample_time, model_type='Default')

    # control glove-box or plane-war-game or torcs-car-game
    commander = Commander()
    commander.start()

    # sEMG_Recognition(username, reader, model, commander)
    Matplotlib_Plot_Info(reader, commander)

    print('loging out...')
    time.sleep(1)
