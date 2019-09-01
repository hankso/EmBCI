#!/usr/bin/env python3
# coding=utf-8
#
# File: EmBCI/path/to/template.py
# Authors: Hank <hankso1106@gmail.com>
#          Jack Ma <MJ at example.com>
# Create: 2019-08-26 01:07:20
#
# ChangeLog:
#   1.
#   2.
#
# TODO:
#   1.
#   2.

'''__doc__'''

# built-in
import os
import sys

# requirements.txt: necessary: six
from six.moves import StringIO

from embci.configs import DIR_BASE


def foo():
    return os, sys, StringIO, DIR_BASE


# THE END
