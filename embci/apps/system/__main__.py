#!/usr/bin/env python3
# coding=utf-8
#
# File: apps/system/__main__.py
# Authors: Hank <hankso1106@gmail.com>
# Create: 2019-07-03 17:21:59

from . import system
from embci.webui import main_debug as main

if __name__ == '__main__':
    main(system)
