#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# File: EmBCI/embci/__init__.py
# Author: Hankso
# Webpage: https://github.com/hankso

'''
Embedded Brain Computer Interface (EmBCI)
TODO: short description for embci
'''

from __future__ import absolute_import
import os

__basedir__ = os.path.dirname(os.path.abspath(__file__))
__title__ = 'EmBCI'
__summary__ = 'EmBCI software Python packages'
__url__ = 'https://github.com/hankso/EmBCI'
__author__ = 'Hankso and individual contributors'
__email__ = 'hankso1106@gmail.com'
__version__ = '0.2.0'
__date__ = '2019.09.01'
__license__ = 'MIT'
__copyright__ = 'Copyright 2017-2019 Hankso and individual contributors'
__keywords__ = (
    'Brain-Computer-Interface '
    'Human-Machine-Interfaces '
    'Bio-Informatics '
    'Biosignal-Analysis '
    'Medical-Apps-Prototyping '
    'Embedded-Platform '
)


def version():
    return '{} {} ({})'.format(__title__, __version__, __date__)


from . import io
from . import viz
from . import utils
from . import configs
from . import processing
from .testing import test

try:
    del os, absolute_import
except NameError:
    pass

__all__ = ('io', 'viz', 'utils', 'configs', 'processing', 'test')
