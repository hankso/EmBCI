#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# File: EmBCI/embci/viz/__init__.py
# Author: Hankso
# Webpage: https://github.com/hankso
# Time: Thu 22 Mar 2018 08:26:16 CST

'''Visualization.'''

from ..utils import config_logger
logger = config_logger()
del config_logger

from .screen import *
from .plots import *
from .qt import *
