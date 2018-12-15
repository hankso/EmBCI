#
#  EmBCI(Embedded Brain Computer Interface)
#
#  mail: 3080863354@qq.com
#  page: https://github.com/hankso
#  project page: https://gitlab.com/hankso/EmBCI
#

from __future__ import absolute_import, unicode_literals
import os
import sys
import configparser

__dir__ = os.path.dirname(os.path.abspath(__file__))
__file__ = os.path.basename(__file__)

BASEDIR = os.path.abspath(os.path.join(__dir__, '../'))
DATADIR = os.path.join(BASEDIR, 'data')


def _load_config(file='/etc/embci.conf'):
    file = str(file)
    if not os.path.exists(file):
        raise IOError("No such file: '%s'" % file)
    config = configparser.ConfigParser()
    config.optionxform = str
    if config.read(file) != [file]:
        raise IOError("Cannot open file: '%s'" % file)
    return config

try:
    _config = _load_config()
    _NO_CONFIG_ = False
    for section in _config:
        globals().update(_config[section])
except:
    _NO_CONFIG_ = True


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
    'webui', 'classifier')
