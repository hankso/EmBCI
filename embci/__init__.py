#!/usr/bin/env python
# -*- coding: utf8 -*-

'''
EmBCI(Embedded Brain Computer Interface)

author: hank
mail: 3080863354@qq.com
page: https://github.com/hankso
project page: https://gitlab.com/hankso/pyemg
'''
import os
import sys

__all__ = []

__dir__ = os.path.dirname(os.path.abspath(__file__))
__file__ = os.path.basename(__file__)

BASEDIR = os.path.abspath(os.path.join(__dir__, '../'))

if sys.version_info.major == 2:
    input == raw_input
elif sys.version_info.major == 3:
    unicode = None
    from functools import reduce
