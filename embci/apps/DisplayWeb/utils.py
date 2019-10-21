#!/usr/bin/env python3
# coding=utf-8
#
# File: DisplayWeb/utils.py
# Authors: Hank <hankso1106@gmail.com>
# Create: 2019-03-04 17:06:43

'''__doc__'''

# built-in
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
import base64

# requirements.txt: network: bottle
import bottle

from embci.utils import serialize, deserialize, ensure_bytes, ensure_unicode

from .globalvars import signalinfo, pt


def process_register(data, pt=pt):
    signalinfo.notch(data, pt.notch or 50, register=True)
    low, high = pt.bandpass.get('low', 4), pt.bandpass.get('high', 40)
    signalinfo.bandpass(data, low, high, register=True)


def process_realtime(data, pt=pt):
    if pt.notch:
        data = signalinfo.notch_realtime(data)
    if pt.bandpass:
        data = signalinfo.bandpass_realtime(data)
    return data


def process_fullarray(data, pt=pt):
    if pt.notch:
        data = signalinfo.notch(data, Hz=pt.notch)
    if pt.bandpass:
        data = signalinfo.bandpass(data, **pt.bandpass)
    return data


def set_token(data, username='user', key='token', max_age=60):
    token = base64.b64encode(serialize(data))
    secret = base64.b64encode(ensure_bytes(username))
    bottle.response.set_cookie('name', ensure_unicode(username))
    bottle.response.set_cookie(
        key, token, secret=secret, max_age=max_age, httponly=True)
    return data


def check_token(key='token'):
    username = bottle.request.get_cookie('name')
    secret = base64.b64encode(ensure_bytes(username))
    token = bottle.request.get_cookie(key, secret=secret)
    if token is None:
        bottle.abort(408, 'Cache expired or user\'s report not generated yet!')
    return deserialize(bottle.html_escape(base64.b64decode(token)))


# THE END
