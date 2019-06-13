#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# File: EmBCI/embci/__init__.py
# Author: Hankso
# Webpage: https://github.com/hankso

'''
EmBCI(Embedded Brain Computer Interface)
TODO: short description for embci
'''

from __future__ import absolute_import, unicode_literals
import os


__dir__ = os.path.dirname(os.path.abspath(__file__))
__title__ = 'EmBCI'
__summary__ = 'EmBCI software Python packages'
__url__ = 'https://github.com/hankso/EmBCI'
__author__ = 'Hankso and individual contributors'
__email__ = 'hankso1106@gmail.com'
__version__ = '0.1.5'
__license__ = 'MIT'
__copyright__ = 'Copyright 2019 Hankso and individual contributors'
__keywords__ = (
    'Brain-Computer-Interface '
    'Human-Machine-Interfaces '
    'Bio-Informatics '
    'Biosignal-Analysis '
    'Medical-Apps-Prototyping '
    'Embedded-Platform '
)

from . import io
from . import viz
from . import utils
from . import configs
from . import processing
from .testing import test

try:
    del os, absolute_import, unicode_literals
except NameError:
    pass

__all__ = (
    'io', 'viz', 'utils', 'configs', 'processing', 'test'
)
