#!/usr/bin/env python
# coding=utf-8
#
# File: apps/recorder/__init__.py
# Author: Hankso
# Webpage: https://github.com/hankso
# Time: Fri 15 Mar 2019 07:04:20 CST

'''
Develop target of subapp `recorder`:
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
