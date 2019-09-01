#!/usr/bin/env python3
# coding=utf-8
#
# File: DisplayWeb/globalvars.py
# Authors: Hank <hankso1106@gmail.com>
# Create: 2019-04-24 16:49:57

'''Global variables that can be accessed across whole apps.'''

import os
__basedir__ = os.path.dirname(os.path.abspath(__file__))
del os

from embci.io import PylslReader as Reader
from embci.io import SocketTCPServer as Server
from embci.processing import SignalInfo
from embci.apps.recorder import Recorder
from embci.utils import AttributeDict, config_logger

reader = Reader(sample_time=5, num_channel=8)
server = Server()
signalinfo = SignalInfo(reader.sample_rate)
recorder = Recorder(reader)
logger = config_logger('.'.join(__name__.split('.')[:-1]))

# a container that can hold all parameters
pt = paramtree = AttributeDict()

pt.notch = rtnotch = False
pt.detrend = rtdetrend = True
pt.bandpass = rtbandpass = AttributeDict({})

pt.batch_size = 50                                     # chunk data size 8 x 50
pt.scale_list = AttributeDict(a=tuple(pow(4, x) for x in range(-3, 10)), i=5)
pt.channel_range = AttributeDict(r=(0, 8), n=0)

pt.fft_resolution = 4                                  # points number per Hz
pt.fft_range = 50                                      # 0 - 50Hz
