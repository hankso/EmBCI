#!/usr/bin env python
# -*- coding: utf8 -*-
import os
import time

__dir__ = os.path.dirname(os.path.abspath(__file__))
__file__ = os.path.basename(__file__)
os.chdir(__dir__)

from bottle import request, response, Bottle
test = Bottle()


@test.route('/')
def hello():
    last_time = request.get_cookie('time')
    response.set_cookie(
        'time', time.strftime('%a,%b %d %H:%M:%S %Y', time.localtime()))
    if last_time:
        return 'I am NOT dead~\nWelcome back, last visited at ' + last_time
    else:
        return 'I am NOT dead~'

application = test

#  vim: set ts=4 sw=4 tw=79 et ft=python :
