#!/usr/bin env python
# -*- coding: utf8 -*-

import time

# from ./
from bottle import route, request, response, default_app


@route('/')
def hello():
    last_time = request.get_cookie('time')
    response.set_cookie(
        'time', time.strftime('%a,%b %d %H:%M:%S %Y', time.localtime()))
    if last_time:
        return 'I am NOT dead~\nWelcome back, last visited at ' + last_time
    else:
        return 'I am NOT dead~'

application = default_app()

#  vim: set ts=4 sw=4 tw=79 et ft=python :
