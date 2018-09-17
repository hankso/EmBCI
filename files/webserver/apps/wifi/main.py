#!/usr/bin/env python
# -*- coding: utf8 -*-
import os
#  import sys

__dir__ = os.path.dirname(os.path.abspath(__file__))
__file__ = os.path.basename(__file__)
os.chdir(__dir__)

#  sys.path.append(os.path.abspath(os.path.join(__dir__, '../../')))
from bottle import request, Bottle
wifi = Bottle()


@wifi.get('/')
def get_wifi_list():
    return {'list': ['wifi1', 'wifi2', 'wifi3']}


@wifi.post('/')
def try_connect_wifi():
    # TODO: connect to a wifi
    ssid = request.forms.ssid
    psk = request.forms.passwd
    print('connecting to hotspot {} with {}'.format(ssid, psk))
    return

application = wifi

#  vim: set ts=4 sw=4 tw=0 et ft=python :
