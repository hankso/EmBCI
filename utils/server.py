#!/usr/bin/env python
# -*- coding: utf8 -*-

import bottle
import time


@bottle.route('/')
def display():
    return (bottle.request.__repr__() + '\n' +
            time.strftime('%a,%b %d %H:%M:%S %Y', time.localtime()))


@bottle.route('/aaa')
def test():
    return 'subpage aaa~'

application = bottle.default_app()
