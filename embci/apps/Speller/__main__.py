#!/usr/bin/env python3
# coding=utf-8
#
# File: Speller/__main__.py
# Authors: Hank <hankso1106@gmail.com>
# Create: 2019-08-27 23:07:27

import os
import sys

from . import application, __basedir__

from embci.webui import webui_static_factory, main_debug

if __name__ == '__main__':
    idx = [r.name for r in application.routes].index('srv')
    application.routes[idx].callback = webui_static_factory(
        os.path.abspath(os.path.join(__basedir__, '../recorder'))
    )
    sys.exit(main_debug(application))
