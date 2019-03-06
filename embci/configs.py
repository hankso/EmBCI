#!/usr/bin/env python
# coding=utf-8
#
# File: EmBCI/embci/configs.py
# Author: Hankso
# Webpage: https://github.com/hankso
# Time: Tue 26 Feb 2019 17:42:06 CST

'''Configures.'''

import os
try:
    import ConfigParser as configparser
except ImportError:
    import configparser

from . import __dir__

DEFAULT_CONFIG_FILES = [
    _ for _ in [(os.path.expandvars('${APPDATA}/embci.conf')
                 if os.name == 'nt' else '/etc/embci/embci.conf'),
                os.path.expanduser('~/.embci/embci.conf')]
    if os.path.exists(_)]


# =============================================================================
# Misc
#
# example:  CRITICAL:embci.webui:__init__.py:1234: abort!
LOGFORMAT = ('%(levelname)s:%(name)s:%(filename)s:%(lineno)d: %(message)s')


# =============================================================================
# Paths
#
SRCDIR = __dir__
BASEDIR = os.path.dirname(__dir__)  # Suppose `embci` is not installed yet.
if os.name == 'nt':
    PIDDIR = os.path.expanduser('~/.embci/pid')
    LOGDIR = os.path.expanduser('~/.embci/log')
else:
    PIDDIR = '/run/embci'
    LOGDIR = '/var/log/embci'

# Update runtime configurations from config files.
# If `embci` has been installed by pip, `BASEDIR` should be overwritten
# by real path configured in default config files.
cp = configparser.ConfigParser()
cp.optionxform = str
cp.read(DEFAULT_CONFIG_FILES)
for _ in cp.sections():
    globals().update(cp.items(_))

DATADIR = globals().get('DATADIR', os.path.join(BASEDIR, 'data'))
TESTDIR = globals().get('TESTDIR', os.path.join(BASEDIR, 'tests'))

del os, cp, configparser
