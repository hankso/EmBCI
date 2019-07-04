#!/usr/bin/env python
# coding=utf-8
#
# File: EmBCI/embci/apps/__init__.py
# Author: Hankso
# Webpage: https://github.com/hankso
# Time: Sun 03 Mar 2019 21:57:59 CST

'''__doc__'''

import os

__dir__ = os.path.dirname(os.path.abspath(__file__))


# TODO: load apps config file and mask them here.
# For example, app named `aaa` will be masked but `example` will NOT.
aaa = None

# If subapps has attr `APPNAME`, it will be displayed on HTML instead of
# subapp folder name. Or you can change the module (app) name by specifing
# it in `__all__`
from . import example as Example
from . import WiFi; WiFi.APPNAME = 'Network'

# If subapps has attr `HIDDEN` (bool), this will control whether the app will
# be display on HTML (embci.webui still can correctly load it).
from . import auth; auth.HIDDEN = True

__all__ = ['Example', 'WiFi', 'aaa', 'auth']

del os
