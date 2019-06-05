#!/usr/bin/env python
# coding=utf-8
#
# File: apps/system/__init__.py
# Author: Hankso
# Webpage: https://github.com/hankso
# Time: Fri 07 Jun 2019 13:28:28 CST

'''System commands API'''

import os
import subprocess

import bottle

from embci.configs import BASEDIR


@bottle.route('/')
def system_index():
    return 'You can reboot / shutdown the device. TODO: doc'


@bottle.route('/debug')
def system_debug():
    bottle.redirect('http://10.0.0.1:9999')


@bottle.route('/shutdown')
def system_shutdown():
    os.system('$(sleep 2; shutdown -P now) &')
    return 'Shutting down'


@bottle.route('/reboot')
def system_reboot():
    os.system('$(sleep 2; shutdown -r now) &')
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


application = bottle.app()
