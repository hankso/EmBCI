#!/usr/bin/env python
# coding=utf-8
#
# File: apps/example/__init__.py
# Author: Hankso
# Webpage: http://github.com/hankso
# Time: Tue 18 Sep 2018 01:55:03 CST

import time

from bottle import request, response, run, Bottle
example = Bottle()


@example.route('/')
def hello():
    last_time = request.get_cookie('time')
    response.set_cookie(
        'time', time.strftime('%a,%b %d %H:%M:%S %Y', time.localtime()))
    if last_time:
        return 'I am NOT dead~\nWelcome back, last visited at ' + last_time
    else:
        return 'I am NOT dead~'


application = example
__all__ = ['application']


def main():
    run(example, host='0.0.0.0', port=8080)
