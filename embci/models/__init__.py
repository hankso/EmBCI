#!/usr/bin/env python3
# coding=utf-8
#
# File: EmBCI/embci/models/__init__.py
# Authors: Hank <hankso1106@gmail.com>
#          Tong-Qing JING <ASDF>
# Create: 2018-02-27 22:59:33

'''Models are defined here'''

from ..utils import config_logger
logger = config_logger(__name__)
del config_logger

from . import base                                                 # noqa: W611
from .network import *                                             # noqa: W401
from .others import *                                              # noqa: W401
