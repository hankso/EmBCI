#!/usr/bin/env python
# -*- coding: utf8 -*-

# from ./
from bottle import get, post, request, default_app


@get('/')
def get_wifi_list():
    return {'list': ['wifi1', 'wifi2', 'wifi3']}


@post('/')
def try_connect_wifi():
    # TODO: connect to a wifi
    ssid = request.forms.ssid
    psk = request.forms.passwd
    print('connecting to hotspot {} with {}'.format(ssid, psk))
    return

application = default_app()

#  vim: set ts=4 sw=4 tw=0 et ft=python :
