#!/usr/bin/env python3
# coding=utf-8
#
# File: apps/streaming/__main__.py
# Authors: Hank <hankso1106@gmail.com>
# Create: 2019-03-10 04:06:40

import sys
from .base import main

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
