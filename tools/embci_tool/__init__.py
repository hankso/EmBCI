#!/usr/bin/env python
# coding=utf-8
#
# File: EmBCI/tools/embci_tool/__init__.py
# Author: Hankso
# Webpage: https://github.com/hankso
# Time: Fri 21 Jun 2019 20:49:57 CST

'''
- [ ] Host documentation locally
- Debug
    - [ ] View log online
    - [ ] Data management (user reports, saved mat data etc.)
    - [ ] Online JS <=> IPython terminal
- System
    - [x] shutdown & reboot
    - [ ] service control: start | restart | status | stop

System commands API

You can reboot / shutdown the device.

# TODO: doc here
'''

import re
import subprocess

import bottle

from embci.configs import BASEDIR
from embci.utils.esp32_api import send_message_esp32

application = system = bottle.Bottle()


@system.route('/')
def system_index():
    return ''.join(['<p>%s</p>' % msg.strip() for msg in __doc__.split('\n')])


def system_exec(cmd):
    '''This will block the caller thread until the command terminate'''
    # TODO: modify to return immediately even without result output
    proc = subprocess.Popen(
        cmd, shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT)
    output = proc.communicate()[0]
    return proc.poll(), output


@system.route('/debug')
def system_debug():
    return 'Not implemented yet. # TODO: js terminal'


@system.route('/shutdown')
def system_shutdown():
    code, output = system_exec('/bin/sh -c "sleep 1; shutdown -P now" &')
    if code != 0:
        return 'Cannot shutdown: ' + output
    return 'Shutting down'


@system.route('/reboot')
def system_reboot():
    code, output = system_exec('/bin/sh -c "sleep 1; shutdown -r now" &')
    if code != 0:
        return 'Cannot reboot: ' + output
    return 'Rebooting'


@system.route('/update')
def system_update(*a, **k):
    code, output = system_exec('git -C %s pull' % BASEDIR)
    if code != 0:
        return 'Update failed!\n' + output
    if k.get('reboot', False):
        return system_reboot()
    return 'Update success!\n' + output


@system.route('/battery')
def system_battery():
    '''Example of ESP32 return value: `Battery level: 98%`'''
    ret = send_message_esp32('battery')
    level = re.findall(r'(\d+)%', ret)
    if level:
        return level[0]
    bottle.abort(500, 'Can not read battery level')

# THE END
