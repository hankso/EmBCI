#!/usr/bin/env python
# -*- coding: utf8 -*-

import bottle
import time


@bottle.route('/')
def hello():
    last_time = bottle.request.get_cookie('time')
    bottle.response.set_cookie(
        'time', time.strftime('%a,%b %d %H:%M:%S %Y', time.localtime()))
    if last_time:
        return 'Welcome back! Last time visited at ' + last_time
    else:
        return 'Welcome! I am alive.'

application = bottle.default_app()
