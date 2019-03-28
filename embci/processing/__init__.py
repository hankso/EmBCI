#!/usr/bin/env python
# coding=utf-8
#
# File: EmBCI/embci/processing/__init__.py
# Author: Hankso
# Webpage: https://github.com/hankso
# Time: Sun 24 Feb 2019 22:52:42 CST

'''Data processing'''

from ..utils import config_logger
logger = config_logger()
del config_logger

from ..testing import PytestRunner
test = PytestRunner(__name__)
del PytestRunner

from .preprocessing import *
from .motorimagery import *
from .ssvep import *
from .p300 import *
