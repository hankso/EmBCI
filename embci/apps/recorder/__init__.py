#!/usr/bin/env python3
# coding=utf-8
#
# File: apps/recorder/__init__.py
# Authors: Hank <hankso1106@gmail.com>
# Create: 2019-03-15 07:04:20

'''
Why you need a recorder?
------------------------
In technique details, readers in EmBCI are designed as realtime data streams,
which means:
    1. A stream has a source, but the source may be various (there are
       PylslReader, TCPReader, SPIReader etc.)
    2. It is not suggested for user to fetch the same data twice - if not
       saved(recorded), data will finally flow away.

Readers are just abstraction on data sources, but they don't know when to
start or stop saving data to files on disk. On embedded devices, storage space
is usually not enough.

Develop target of subapp `recorder`
-----------------------------------
- [x] Recorder should support start, pause, resume, stop
- [x] Recorder should support change of username
- [x] Let command listener occupy main thread
- [x] Record both data, timestamp, and event

This file will make recorder a module and provide class `Recorder`
'''

from embci.utils import config_logger
logger = config_logger(__name__)
del config_logger

from .base import Recorder  # noqa: W611
