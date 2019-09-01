#!/usr/bin/env python3
# coding=utf-8
#
# File: WiFi/__main__.py
# Authors: Hank <hankso1106@gmail.com>
# Create: 2019-05-06 01:36:25

import bottle
from . import application

if __name__ == '__main__':
    bottle.run(application)
