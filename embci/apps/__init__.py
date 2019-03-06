#!/usr/bin/env python
# coding=utf-8
#
# File: EmBCI/embci/apps/__init__.py
# Author: Hankso
# Webpage: https://github.com/hankso
# Time: Sun 03 Mar 2019 21:57:59 CST

'''__doc__'''

import os

__dir__ = os.path.dirname(os.path.abspath(__file__))

from . import example
from . import WiFi

__all__ = ['example', 'WiFi']

del os
