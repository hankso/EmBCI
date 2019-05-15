#!/usr/bin/env python
# coding=utf-8
#
# File: WiFi/__main__.py
# Author: Hankso
# Webpage: https://github.com/hankso
# Time: Mon 06 May 2019 01:36:25 CST

import sys
import bottle
from . import application


if __name__ == '__main__':
    sys.exit(bottle.run(application, host='0.0.0.0', port=8080))
