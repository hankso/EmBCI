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
from six.moves import configparser

from . import __basedir__
__module__ = sys.modules[__name__]  # reference to this module


# =============================================================================
# Default configuration

# example:  CRITICAL:embci.webui:__init__.py:1234: abort!
LOGFORMAT = '%(levelname)s:%(name)s:%(filename)s:%(lineno)d: %(message)s'

WEBUI_HOST = '0.0.0.0'
WEBUI_PORT = 80

ENSURE_DIR_EXIST = False
DIR_SRC = __basedir__
DIR_BASE = os.path.dirname(__basedir__)  # Suppose `embci` is not installed yet
if os.name == 'nt':
    DIR_PID = os.path.expanduser('~/.embci/pid')
    DIR_LOG = os.path.expanduser('~/.embci/log')
else:
    DIR_PID = '/run/embci'
    DIR_LOG = '/var/log/embci'
DIR_TMP = tempfile.gettempdir()


# =============================================================================
# Update runtime configurations from config files.
# If `embci` has been installed by pip, `DIR_BASE` should be overwritten
# by real path configured in default config files.

DEFAULT_CONFIG_FILES = [
    _ for _ in [
        os.path.join(DIR_BASE, 'files/service/embci.conf'),
        (os.path.expandvars('${APPDATA}/embci.conf')
         if os.name == 'nt' else '/etc/embci/embci.conf'),
        os.path.expanduser('~/.embci/embci.conf')
    ] if os.path.exists(_)]

cp = configparser.ConfigParser()
cp.optionxform = str
cp.read(DEFAULT_CONFIG_FILES)

# DO NOT use `globals().update(cp.items)` here. It may cause recursive loop
for section in cp.sections():
    __module__.__dict__.update(cp.items(section))

__module__.__dict__.setdefault('DIR_DATA', os.path.join(DIR_BASE, 'data'))
__module__.__dict__.setdefault('DIR_TEST', os.path.join(DIR_BASE, 'tests'))

if ENSURE_DIR_EXIST:
    for DIR in __module__.__dict__:
        if not DIR.startswith('DIR_'):
            continue
        DIR = getattr(__module__, DIR)
        if not isinstance(DIR, str):
            continue
        try:
            os.makedirs(DIR, 0o775)
        except OSError as e:
            sys.stderr.write('Cannot make directory `%s`: %s' % (DIR, e))

try:
    del (
        os, sys, tempfile, cp, section, configparser,
        absolute_import, division, print_function
    )
except NameError:
    pass

settings = {
    key: value
    for key, value in globals().items() if key[0].isupper()
}
