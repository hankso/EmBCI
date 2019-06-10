#!/usr/bin/env python
# coding=utf-8
#
# File: DBS/globalvars.py
# Author: Hankso
# Webpage: https://github.com/hankso
# Time: Wed 24 Apr 2019 16:49:57 CST

'''
Global variables that can be accessed across whole DBS apps are defined here.
'''

from embci.io import PylslReader as Reader
from embci.io import SocketTCPServer as Server
from embci.processing import SignalInfo
from embci.apps.recorder import Recorder
from embci.utils import AttributeDict

reader = Reader(sample_time=5, num_channel=8)
server = Server()
signalinfo = SignalInfo(reader.sample_rate)
recorder = Recorder(reader)

import os
__dir__ = os.path.dirname(os.path.abspath(__file__))
del os

# a container that can hold all parameters
pt = param_tree = AttributeDict()

pt.notch = rtnotch = True
pt.detrend = rtdetrend = True
pt.bandpass = rtbandpass = AttributeDict({'low': 4, 'high': 10})

pt.batch_size = 50  # send 8x50 data as a chunk
pt.fft_resolution = 4  # points/Hz
pt.fft_range = 50  # 0-50Hz
pt.scale_list = AttributeDict(a=tuple(pow(4, x) for x in range(-3, 10)), i=3)
pt.channel_range = AttributeDict(r=(0, 8), n=0)
