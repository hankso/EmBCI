#!/usr/bin/env python3
# coding=utf-8
#
# File: EmBCI/embci/configs.py
# Authors: Hank <hankso1106@gmail.com>
# Create: 2019-02-26 17:42:06

'''
Everything about configuration. When imported, this module will automatically
load configs from local configuration files.
'''

# built-in
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
import os
import sys
import tempfile

# requirements.txt: necessary: six
from six import string_types
from six.moves import configparser

from . import __basedir__
__module__ = sys.modules[__name__]  # reference to this module


# =============================================================================
# Default configuration

# example: [CRITICAL 12:10:22 embci.webui:__init__:445] abort!
# py2 doesn't support string.format() style
LOGFORMAT2 = (
    '[%(levelname)s %(asctime)s.%(msecs)03.0f %(name)s.%(module)s:%(lineno)d]'
    ' %(message)s'
)
# example: (RED)[C 12:26:33 embci.webui:__init__:445](RED) abort!
LOGFORMAT = (
    '{start}'
    '[{levelname[0]} {asctime}.{msecs:03.0f} {name}.{module}:{lineno}]'
    '{reset}'
    ' {message}'
)
DATEFORMAT = '%H:%M:%S'

WEBUI_HOST = '0.0.0.0'
WEBUI_PORT = 80

DIR_ENSURE_EXIST = True
DIR_SRC = __basedir__
DIR_BASE = os.path.dirname(__basedir__)  # Suppose `embci` is not installed yet
DIR_DOC = os.path.join(DIR_BASE, 'docs')
if os.name == 'nt':
    DIR_PID = os.path.expanduser('~/.embci/pid')
    DIR_LOG = os.path.expanduser('~/.embci/log')
else:
    # Normal location for pidfiles of root user is `/run`, while non-root
    # users can put pidfiles under /run/user/${UID}
    DIR_PID = (
        '/run/' if os.getuid() == 0 else '/run/user/%d/' % os.getuid()
    ) + 'embci'
    DIR_LOG = '/var/log/embci'
DIR_TMP = tempfile.gettempdir()


# =============================================================================
# Update runtime configurations from config files.
# If `embci` has been installed by pip, `DIR_BASE` should be overwritten
# by real path configured in default config files.

DEFAULT_CONFIG_FILES = list(filter(os.path.exists, [
    os.path.join(DIR_BASE, 'files/service/embci.conf'),
    (os.path.expandvars('${APPDATA}/embci.conf') if os.name == 'nt'
     else '/etc/embci/embci.conf'),
    os.path.expanduser('~/.embci/embci.conf')
]))

cp = configparser.ConfigParser()
cp.optionxform = str
cp.read(DEFAULT_CONFIG_FILES)

# DO NOT use `globals().update(cp.items)` here. It may cause recursive loop
for _ in cp.sections():
    __module__.__dict__.update(cp.items(_))

__module__.__dict__.setdefault('DIR_DATA', os.path.join(DIR_BASE, 'data'))
__module__.__dict__.setdefault('DIR_TEST', os.path.join(DIR_BASE, 'tests'))

if str(DIR_ENSURE_EXIST).lower() in ['true', 'yes', 'y', '1']:
    DIRS = set(filter(lambda _: _.startswith('DIR_'), __module__.__dict__))
    for DIR in DIRS.difference(['DIR_ENSURE_EXIST', ]):
        DIR = getattr(__module__, DIR)
        if not isinstance(DIR, string_types) or os.path.exists(DIR):
            continue
        try:
            os.makedirs(DIR, 0o775)
        except OSError as e:
            sys.stderr.write('Cannot make directory `%s`: %s' % (DIR, e))
    del DIR, DIRS

try:
    del (
        os, sys, tempfile, cp, configparser, string_types,
        absolute_import, division, print_function
    )
except NameError:
    pass

settings = {
    key: value
    for key, value in __module__.__dict__.items() if key[0].isupper()
}
