#!/usr/bin/env python3
# coding=utf-8
#
# File: EmBCI/embci/processing/__init__.py
# Authors: Hank <hankso1106@gmail.com>
# Create: 2019-02-24 22:52:42

'''Data processing'''

from ..utils import config_logger
logger = config_logger()
del config_logger

from ..testing import PytestRunner
test = PytestRunner(__name__)
del PytestRunner

from .preprocessing import *                                       # noqa: W401
