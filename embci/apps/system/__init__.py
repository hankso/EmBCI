#!/usr/bin/env python3
# coding=utf-8
#
# File: apps/system/__init__.py
# Authors: Hank <hankso1106@gmail.com>
# Create: 2019-06-21 20:49:57

'''
- [ ] Host documentation locally
- Debug
    - [x] View log online
    - [ ] Data management (user reports, saved mat data etc.)
    - [ ] Online JS <=> IPython terminal
- System
    - [x] shutdown & reboot
    - [ ] service control: start | restart | status | stop

System commands API

You can reboot / shutdown the device.
'''

import os
import re
import subprocess

import bottle

from embci.configs import DIR_BASE, DIR_LOG

__basedir__ = os.path.dirname(os.path.abspath(__file__))
__logview__ = os.path.join(__basedir__, 'views', 'logview.html')
system = bottle.Bottle()


@system.route('/')
def system_index():
    return {'doc': ['<p>%s</p>' % msg.strip() for msg in __doc__.split('\n')]}


def system_exec(cmd):
    '''This will block the caller thread until the command terminate'''
    proc = subprocess.Popen(
        cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    # Python 3 only
    #  with proc:
    #      code, output = proc.returncode, proc.stdout.read()
    proc.wait()
    return proc.returncode, proc.stdout.read()


@system.route('/debug')
def system_debug():
    return 'Not implemented yet. # TODO: js terminal'


@system.route('/log/<filename:path>')
def system_logfiles(filename, logview=False):
    res = bottle.static_file(filename, DIR_LOG)
    if res.status_code == 200 and bottle.request.query.get('logview', logview):
        return bottle.template(__logview__, body=res.body.read())
    return res


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
    code, output = system_exec('git -C %s pull' % DIR_BASE)
    if code != 0:
        return 'Update failed!\n' + output
    if k.get('reboot', False):
        return system_reboot()
    return 'Update success!\n' + output


@system.route('/battery')
def system_battery():
    '''Example of ESP32 return value: `Battery level: 98%`'''
    from embci.drivers.esp32 import send_message_esp32
    ret = send_message_esp32('battery')
    level = re.findall(r'(\d+)%', ret)
    if level:
        return level[0]
    bottle.abort(500, 'Can not read battery level')

# provide an object named `application` for Apache + mod_wsgi and embci.webui
#  application = system
#  __all__ = ['application']
# THE END
