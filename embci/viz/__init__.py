#!/usr/bin/env python3
# coding=utf-8
#
# File: EmBCI/embci/viz/__init__.py
# Authors: Hank <hankso1106@gmail.com>
# Create: 2018-03-22 08:26:16

'''Visualization'''

from ..utils import config_logger
logger = config_logger()
del config_logger

from .screen import *                                              # noqa: W401
from .plots import *                                               # noqa: W401
from .qt import *                                                  # noqa: W401
