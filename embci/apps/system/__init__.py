#!/usr/bin/env python
# coding=utf-8
#
# File: apps/system/__init__.py
# Author: Hankso
# Webpage: https://github.com/hankso
# Time: Fri 07 Jun 2019 13:28:28 CST

'''System commands API'''

import os
import re
import subprocess

import bottle

from embci.configs import BASEDIR
from embci.utils.esp32_api import send_message_esp32


@bottle.route('/')
def system_index():
    return 'You can reboot / shutdown the device. # TODO: doc'


@bottle.route('/debug')
def system_debug():
    return 'Not implemented yet. # TODO: js terminal'


@bottle.route('/shutdown')
def system_shutdown():
    print('Executing command: shutdown -P now')
    print('Result: {}'.format(os.system('$(sleep 2; shutdown -P now) &')))
    return 'Shutting down'


@bottle.route('/reboot')
def system_reboot():
    print('Executing command: shutdown -r now')
    print('Result: {}'.format(os.system('$(sleep 2; shutdown -r now) &')))
    return 'Rebooting'


@bottle.route('/update')
def system_update(*a, **k):
    try:
        output = subprocess.check_output(
            'git -C %s pull' % BASEDIR,
            shell=True, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        return 'Update failed!\n' + str(e)
    else:
        if k.get('reboot', False):
            system_reboot()
        return 'Update success!\n' + output


@bottle.route('/battery')
def system_battery():
    '''Example of ESP32 return value: `Battery level: 98%`'''
    ret = send_message_esp32('battery')
    level = re.findall(r'(\d+)%', ret)
    if level:
        return level[0]
    bottle.abort(500, 'Can not read battery level')


application = bottle.app()
