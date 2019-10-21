# coding=utf-8

'''
Embedded Brain Computer Interface (EmBCI)
TODO: short description for embci
'''

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
import os

__basedir__   = os.path.dirname(os.path.abspath(__file__))
__title__     = 'EmBCI'
__summary__   = 'EmBCI software Python packages'
__url__       = 'https://github.com/hankso/EmBCI'
__author__    = 'Hankso and individual contributors'
__email__     = 'hankso1106@gmail.com'
__version__   = '0.2.3'
__date__      = '2019.10.22'
__license__   = 'MIT'
__copyright__ = 'Copyright 2017-2019 Hankso and individual contributors'
__keywords__  = (
    'Brain-Computer-Interface '
    'Human-Machine-Interfaces '
    'Bio-Informatics '
    'Biosignal-Analysis '
    'Medical-Apps-Prototyping '
    'Embedded-Platform '
)


def version():
    return '{} {} ({})'.format(__title__, __version__, __date__)


from . import utils
from . import configs
from . import io
from . import processing
from . import viz
from .testing import test

__all__ = ('io', 'viz', 'utils', 'configs', 'processing', 'test')

try:
    del os, absolute_import, division, print_function
except NameError:
    pass
