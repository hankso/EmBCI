#!/usr/bin/env python3
# coding=utf-8
#
# File: apps/system/__main__.py
# Authors: Hank <hankso1106@gmail.com>
# Create: 2019-07-03 17:21:59

'''__doc__'''

import bottle

from . import system

from embci.utils import get_config

if __name__ == '__main__':
    host = get_config('EMBCITOOL_HOST', '0.0.0.0')
    port = get_config('EMBCITOOL_PORT', 9998)
    bottle.run(system, host=host, port=port)
