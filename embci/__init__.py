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

__dir__ = os.path.dirname(os.path.abspath(__file__))
__file__ = os.path.basename(__file__)

BASEDIR = os.path.abspath(os.path.join(__dir__, '../'))
DATADIR = os.path.join(BASEDIR, 'data')

if sys.version_info.major == 2:
    input = raw_input
    unicode = unicode
    reduce = reduce
elif sys.version_info.major == 3:
    input = input
    unicode = lambda x: x
    from functools import reduce

import io
import preprocess
import visualization
import common
import frame
#  import classifier

#  __all__ = ['preprocess', 'io', 'classifier', 'visualization',
#             'common', 'gyms', 'utils']
