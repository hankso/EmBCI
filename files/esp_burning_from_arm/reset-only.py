#!/usr/bin/env python
# coding=utf-8
'''
File: reset-only.py
Author: Hankso
Web: http://github.com/hankso
Time: Thu 02 Aug 2018 10:21:59 AM UTC
'''
import time
from gpio4 import SysfsGPIO

en = SysfsGPIO(19)
en.export = True

print('[ESP_Reset] enable value = 0')
en.direction = 'out'
en.value = 0

time.sleep(0.2)

print('[ESP_Reset] enable value = 1')
en.value = 1
time.sleep(1)

print('[ESP_Reset] soft reset done!')

en.export = False
