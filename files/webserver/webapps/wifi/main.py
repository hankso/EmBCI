#!/usr/bin/env python
# -*- coding: utf8 -*-
# built-in
import os
import sys

__dir__ = os.path.dirname(os.path.abspath(__file__))
__file__ = os.path.basename(__file__)
path = os.path.abspath(os.path.join(__dir__, '../../../../'))
if path not in sys.path:
    sys.path.append(path)

# from __dir__/../../../../
from embci.common import find_wifi_hotspots

from bottle import request, redirect, run, static_file, Bottle
wifi = Bottle()


#
# routes
#


@wifi.get('/')
def main():
    redirect('login.html')


@wifi.get('/<filename:path>')
def static(filename):
    return static_file(filename, root=__dir__)


@wifi.get('/hotspots')
def get_wifi():
    wifi_list = find_wifi_hotspots()
    for wifi in wifi_list:
        del wifi.bitrates, wifi.channel, wifi.mode, wifi.noise
        l, h = map(float, wifi.pop('quality').split('/'))
        wifi.signal = int(l / h * 10)
        t = wifi.encryption_type
        if t:
            wifi.encryption_type = t.upper()
    return {'list': wifi_list}


@wifi.post('hotspots')
def post_wifi():
    # TODO: connect to a wifi
    ssid = request.forms.ssid
    psk = request.forms.psk
    print('connecting to hotspot {} with {}'.format(ssid, psk))
    return


#
# provide an object named `application` for Apache + mod_wsgi
#

application = wifi


if __name__ == '__main__':
    os.chdir(__dir__)
    run(wifi, host='0.0.0.0', port=80, reloader=True)

#  vim: set ts=4 sw=4 tw=0 et ft=python :
