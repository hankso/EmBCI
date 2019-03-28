#!/usr/bin/env python
# coding=utf-8
#
# File: reset_esp.py
# Author: Hankso
# Webpage: https://github.com/hankso
# Time: Thu 02 Aug 2018 10:21:59 AM UTC

import sys
import time

from gpio4 import SysfsGPIO


def reset_esp(flash=False, en_pin=19, boot_pin=18):
    '''
    Reset on-shield ESP32 by pull down enable pin.
    Check README for pins out detail.
    '''
    rst = SysfsGPIO(en_pin)
    rst.export = True
    boot = SysfsGPIO(boot_pin)
    boot.export = True

    # press reset
    print('[ESP Reset] enable value = 0')
    rst.direction = 'out'
    rst.value = 0

    if flash:
        # press boot
        print('[ESP Reset] boot value = 0')
        boot.direction = 'out'
        boot.value = 0

    time.sleep(0.2)

    # release reset
    print('[ESP Reset] enable value = 1')
    rst.value = 1
    time.sleep(0.3)

    if flash:
        # release boot
        print('[ESP Reset] boot value = 1')
        boot.value = 1

    print('[ESP Reset] soft reset done!')
    boot.export = False
    rst.export = False
    time.sleep(1.5)


if __name__ == '__main__':
    reset_esp(flash=('flash' in sys.argv))
