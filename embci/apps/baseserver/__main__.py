#!/usr/bin/env python3
# coding=utf-8
#
# File: apps/baseserver/__main__.py
# Authors: Hank <hankso1106@gmail.com>
# Create: 2019-09-14 16:20:25

import sys

from embci.webui import webui_static_host, main_debug

from . import application

if __name__ == '__main__':
    webui_static_host(application, '/srv')
    sys.exit(main_debug(application, port=8080))
