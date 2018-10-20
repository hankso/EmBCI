#!/usr/bin/env python
# coding=utf-8
'''
File: reset_esp.py
Author: Hankso
Web: http://github.com/hankso
Time: Thu 02 Aug 2018 10:21:59 AM UTC
'''

import os
import sys

__dir__ = os.path.dirname(os.path.abspath(__file__))
BASEDIR = os.path.abspath(os.path.join(__dir__, '../../'))
sys.path.append(BASEDIR)
from embci.common import reset_esp

# OPi GPIO19
en = 19
# OPi GPIO18
boot = 18

if __name__ == '__main__':
    reset_esp(
        flash=('flash' in sys.argv),
        en_pin=en,
        boot_pin=boot)
