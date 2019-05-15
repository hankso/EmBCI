#!/usr/bin/env python
# coding=utf-8
#
# File: WiFi/__init__.py
# Author: Hankso
# Webpage: https://github.com/hankso
# Time: Tue 18 Sep 2018 01:55:03 CST

'''

'''

# built-in
import os
import subprocess

# requirements.txt: network: bottle
import bottle

from embci.configs import BASEDIR
from embci.utils import config_logger
logger = config_logger(__name__)
del config_logger

from .backend import (wifi_accesspoints, wifi_status,
                      wifi_connect, wifi_disconnect, wifi_forget,
                      wifi_enable, wifi_disable)

__dir__ = os.path.dirname(os.path.abspath(__file__))

wifi = bottle.Bottle()


# =============================================================================
# WiFi Basic API
#
@wifi.get('/')
def api_index():
    bottle.redirect('index.html')


@wifi.get('/<filename:path>')
def api_static(filename):
    return bottle.static_file(filename, root=__dir__)


@wifi.get('/upgrade')
def api_upgrade():
    pwd = os.getcwd()
    os.chdir(BASEDIR)
    try:
        #  st = subprocess.check_output(['git', 'status'])
        msg = subprocess.check_output(['git', 'pull'])
    except subprocess.CalledProcessError as e:
        msg = e.output
    os.chdir(pwd)
    return {'status': True, 'msg': msg}


# =============================================================================
# WiFi Service API
#
@wifi.get('/hotspots')
def api_list_hotspots():
    return {'list': wifi_accesspoints()}


@wifi.post('/connect')
def api_connect():
    ssid = bottle.request.forms.get('ssid')
    user = bottle.request.forms.get('user')
    psk = bottle.request.forms.get('psk')
    logger.debug(bottle.request.forms.items())
    rst, msg = wifi_connect(ssid, user, psk)
    return {'status': rst, 'msg': msg}


@wifi.get('/disconnect')
def api_disconnect():
    ssid = bottle.request.query.get('ssid')
    rst, msg = wifi_disconnect(ssid)
    return {'status': rst, 'msg': msg}


@wifi.get('/forget')
def api_forget():
    ssid = bottle.request.query.get('ssid')
    rst, msg = wifi_forget(ssid)
    return {'status': rst, 'msg': msg}


@wifi.route('/control')
def api_control():
    for key in bottle.request.query:
        if key == 'action':
            action = bottle.request.query.get('action')
            if action == 'enable':
                rst, err = wifi_enable()
            elif action == 'disable':
                rst, err = wifi_disable()
            else:
                bottle.abort(400, 'Invalid action `{}`!'.format(action))
            if rst is False:
                bottle.abort(500, err)


@wifi.route('/status')
def api_status():
    return {
        'wifi_state': 'enabled' if wifi_status() else 'disabled',
        'connection': {}
    }


# =============================================================================
# provide an object named `application` for Apache + mod_wsgi and embci.apps
#
application = wifi
__all__ = ['application']
# THE END
