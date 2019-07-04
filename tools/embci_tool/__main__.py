#!/usr/bin/env python
# coding=utf-8
#
# File: EmBCI/tools/embci_tool/__main__.py
# Author: Hankso
# Webpage: https://github.com/hankso
# Time: Wed 03 Jul 2019 17:21:59 CST

'''__doc__'''

import bottle

from . import system

from embci.utils import get_config

if __name__ == '__main__':
    host = get_config('EMBCITOOL_HOST', '0.0.0.0')
    port = get_config('EMBCITOOL_PORT', 9998)
    bottle.run(system, host=host, port=port)
