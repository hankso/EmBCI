#!/usr/bin/env python
# coding=utf-8
'''
File: reset-waiting-for-download.py
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

if __name__ == '__main__':
    if 'flash' in sys.argv:
        reset_esp(flash=True)
    else:
        reset_esp()
