#!/usr/bin/env python
# coding=utf-8
'''
File: EmBCI/embci/webui/webapps/wifi/__init__.py
Author: Hankso
Web: http://github.com/hankso
Time: Tue 18 Sep 2018 01:55:03 CST
'''
# built-in
import re
import os
import sys
import binascii

# requirements.txt: drivers: wifi
from wifi import Scheme

__dir__ = os.path.dirname(os.path.abspath(__file__))
__file__ = os.path.basename(__file__)
path = os.path.abspath(os.path.join(__dir__, '../../../../'))
if path not in sys.path:
    sys.path.append(path)

# from __dir__/../../../../
from embci.common import find_wifi_hotspots

from bottle import request, redirect, run, static_file, Bottle

wifi = Bottle()
wifi_list = []
interface = 'wlan0'
Scheme = Scheme.for_file('/tmp/interface.embci')


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
    # TODO: status: connected | disconnected | connecting
    #  saved = Scheme.all()
    global wifi_list
    wifi_list = find_wifi_hotspots(interface)
    for wifi in wifi_list:
        del wifi.bitrates, wifi.channel, wifi.mode, wifi.noise
        l, h = [float(i) for i in wifi.pop('quality').split('/')]
        wifi.signal = int(l / h * 10)
        if wifi.encryption_type is not None:
            wifi.encryption_type = wifi.encryption_type.upper()
        # convert u'\\xe5\\x93\\x88' to u'\u54c8' (for example)
        wifi.ssid = re.sub(r'\\x([0-9a-fA-F]{2})',
                           lambda m: binascii.a2b_hex(m.group(1)),
                           wifi.ssid.encode('utf8')).decode('utf8')
    return {'list': wifi_list}


@wifi.post('/hotspots')
def post_wifi():
    # if not has psk
    #     return Scheme.find(interface, essid)
    # elif forget:
    #     find and delete
    # else:
    #     try connect
    essid = request.forms.essid
    scheme = Scheme.for_cell(interface, essid,
                             wifi_list[wifi_list.ssid.index(essid)],
                             request.forms.psk)
    scheme.save()
    scheme.activate()
    return


#
# provide an object named `application` for Apache + mod_wsgi
#

application = wifi
__all__ = ['application']


if __name__ == '__main__':
    os.chdir(__dir__)
    run(wifi, host='0.0.0.0', port=80, reloader=True)
