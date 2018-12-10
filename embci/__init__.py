#
#  EmBCI(Embedded Brain Computer Interface)
#
#  mail: 3080863354@qq.com
#  page: https://github.com/hankso
#  project page: https://gitlab.com/hankso/EmBCI
#

from __future__ import absolute_import, division, print_function
import os
import sys
from functools import reduce

__dir__ = os.path.dirname(os.path.abspath(__file__))
__file__ = os.path.basename(__file__)

BASEDIR = os.path.abspath(os.path.join(__dir__, '../'))
DATADIR = os.path.join(BASEDIR, 'data')

if sys.version_info.major == 2:
    input = raw_input

    unicode = unicode

elif sys.version_info.major == 3:
    input = input

    def unicode(*a, **k):
        return a, k


from . import preprocess
from . import io
from . import visualization
from . import common
from . import gyms
from . import frame
from . import webui
from . import classifier

__title__ = 'EmBCI'
__summary__ = 'EmBCI software Python packages'
__url__ = 'https://github.com/hankso/EmBCI'
__author__ = 'Hankso and individual contributors'
__email__ = 'hank1106@buaa.edu.cn'

__version__ = '0.1.2'

__license__ = ''
__copyright__ = 'Copyright 2018 Hankso and individual contributors'

__all__ = (
    'preprocess', 'io', 'visualization', 'common', 'gyms', 'utils', 'frame',
    'webui', 'classifier', 'input', 'unicode', 'reduce',
    '__title__', '__summary__', '__url__', '__author__', '__email__',
    '__version__', '__license__', '__copyright__',
)
