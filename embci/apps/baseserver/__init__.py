#!/usr/bin/env python3
# coding=utf-8
#
# File: apps/baseserver/__init__.py
# Authors: Hank <hankso1106@gmail.com>
# Create: 2019-09-14 16:17:15

import os
import bottle

from embci.webui import webui_static_factory, main_debug
__basedir__ = os.path.dirname(os.path.abspath(__file__))
application = bottle.Bottle()
application.route('/<filename:path>', 'GET', webui_static_factory(
    __basedir__, os.path.abspath(os.path.join(__basedir__, '../recorder'))
))


@application.route('/')
def base_root():
    bottle.redirect('index.html')


def main():
    main_debug(host='127.0.0.1', port=8080)


__all__ = ('application', )
