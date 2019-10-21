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
    - [x] Data management (user reports, saved mat data etc.)
    - [x] Online JS <=> IPython terminal (redirect to Jupyter server)
- System
    - [x] shutdown & reboot
    - [ ] service control: start | restart | status | stop

System commands API

You can reboot / shutdown the device.
'''

# built-in
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
import os
import re
import time
import subprocess

# requirements.txt: network: bottle
import bottle

from embci.utils import embedded_only, config_logger

__basedir__ = os.path.dirname(os.path.abspath(__file__))
system = bottle.Bottle()
logger = config_logger()


@system.route('/')
def system_index():
    return '\n'.join(['<p>%s</p>' % s.strip() for s in __doc__.split('\n')])


def system_exec(cmd, block=True):
    '''This will block the caller thread until the command terminate'''
    proc = subprocess.Popen(
        cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    # Python 3 only
    #  with proc:
    #      code, output = proc.returncode, proc.stdout.read()
    if not block:
        return -1, ''
    return proc.wait(), proc.stdout.read().decode('utf8')


@system.route('/debug')
def system_debug():
    if 'jupyter-notebook' not in system_exec('ps ux | grep jupyter')[1]:
        logger.debug('Trying to start Jupyter Notebook process...')
        from embci.utils import get_config, get_host_addr
        WEBUI_HOST = get_host_addr(get_config('WEBUI_HOST', '0.0.0.0'))
        HOST = get_config('NOTEBOOK_HOST', WEBUI_HOST)
        PORT = get_config('NOTEBOOK_PORT', 1106, type=int)
        code, ret = system_exec('jupyter-notebook --help')
        if code:
            return 'Cannot start Jupyter Notebook server: %s' % ret
        cmd = ('jupyter-notebook --no-browser --allow-root -y '
               '--ip=%s --port=%d' % (HOST, PORT))
        logger.debug('Executing command: `%s`' % cmd)
        system_exec('/bin/sh -c "%s" &' % cmd, False)
        time.sleep(3)
        url = 'http://{}:{}'.format(HOST, PORT)
    else:
        code, ret = system_exec('jupyter-notebook list')
        servers = ret.split('\n')[1:]
        if code or not servers:
            return 'No valid server info: `%s`' % ret
        logger.debug('Current alive server: ' + servers[0])
        url = servers[0].split(' ')[0]
    bottle.redirect(url)


@system.route('/shutdown')
@embedded_only('API `shutdown` only supports embedded device')
def system_shutdown():
    code, ret = system_exec('/bin/sh -c "sleep 1; shutdown -P now" &', False)
    if code > 0:
        return 'Cannot shutdown: ' + ret
    return 'Shutting down'


@system.route('/reboot')
@embedded_only('API `reboot` only supports embedded device')
def system_reboot():
    code, ret = system_exec('/bin/sh -c "sleep 1; shutdown -r now" &', False)
    if code > 0:
        return 'Cannot reboot: ' + ret
    return 'Rebooting'


@system.route('/update')
def system_update(*a, **k):
    from embci.configs import DIR_BASE
    code, output = system_exec('git -C %s pull' % DIR_BASE)
    if code != 0:
        return 'Update failed!\n' + output
    if k.get('reboot', False):
        return system_reboot()
    return 'Update success!\n' + output


@system.route('/battery')
@embedded_only('API `battery` depends on ESP32 and embedded device', retval=0)
def system_battery():
    '''Example of ESP32 return value: `Battery level: 98%`'''
    from embci.drivers.esp32 import send_message_esp32
    ret = send_message_esp32('battery')
    if not re.match(r'(\d+)%', ret):
        bottle.abort(500, 'Can not read battery level')
    return re.findall(r'(\d+)%', ret)[0]


# provide an object named `application` for Apache + mod_wsgi and embci.webui
application = system
__all__ = ['application']
# THE END
