#!/usr/bin/env python3
# coding=utf-8
#
# File: Speller/__main__.py
# Authors: Hank <hankso1106@gmail.com>
# Create: 2019-08-27 23:07:27

import os
import sys

from . import application, __basedir__

from embci.webui import webui_static_host, main_debug

if __name__ == '__main__':
    webui_static_host(
        application, '/srv/<filename:path>',
        os.path.abspath(os.path.join(__basedir__, '../recorder'))
    )
    sys.exit(main_debug(application))
