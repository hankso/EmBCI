#!/usr/bin/env python
# coding=utf-8
'''
File: reset-waiting-for-download.py
Author: Hankso
Web: http://github.com/hankso
Time: Thu 02 Aug 2018 10:21:59 AM UTC
'''

import sys; sys.path += ['../../utils']
import time
from gpio4 import SysfsGPIO


en = SysfsGPIO(19)
en.export = True
boot = SysfsGPIO(18)
boot.export = True

# press boot
print('[ESP_Reset] boot value = 0')
boot.direction = 'out'
boot.value = 0

# press reset
print('[ESP_Reset] enable value = 0')
en.direction = 'out'
en.value = 0

time.sleep(0.1)

# release reset
print('[ESP_Reset] enable value = 1')
en.value = 1

time.sleep(0.4)

# release boot
print('[ESP_Reset] boot value = 1')
boot.value = 1


boot.export = False
en.export = False
