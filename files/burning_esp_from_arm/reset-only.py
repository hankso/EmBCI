#!/usr/bin/env python
# coding=utf-8
'''
File: reset-only.py
Author: Hankso
Web: http://github.com/hankso
Time: Thu 02 Aug 2018 10:21:59 AM UTC
'''

import sys; sys.path += ['../../utils']
import time
from gpio4 import SysfsGPIO


en = SysfsGPIO(19)
en.export = True
en.direction = 'out'
en.value = 0
time.sleep(0.2)
en.value = 1
time.sleep(1)
en.export = False
