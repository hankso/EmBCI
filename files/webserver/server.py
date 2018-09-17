#!/usr/bin/env python
# coding=utf-8
'''
File: server.py
Author: Hankso
Web: http://github.com/hankso
Time: Fri Sep 14 21:51:46 2018
'''

import os
import time
import importlib

__dir__ = os.path.dirname(os.path.abspath(__file__))
__file__ = os.path.basename(__file__)

from bottle import Bottle, static_file, redirect, response
root = Bottle()

# mount sub-applications
os.chdir(os.path.join(__dir__, 'apps'))
for app_name in os.listdir('.'):
    root.mount('/apps/{}'.format(app_name),
               importlib.import_module('{}.main'.format(app_name)).application)
    print('mount /apps/{} to {}/main.py:app'.format(app_name, app_name))
    os.chdir(os.path.join(__dir__, 'apps'))
os.chdir(__dir__)


@root.route('/')
def main():
    redirect('/index.html')


@root.route('/<filename:path>')
def static(filename):
    return static_file(filename=filename, root=__dir__)


@root.route('/debug')
def debug():
    response.set_cookie(
        'last_debug', time.strftime('%a,%b %d %H:%M:%S %Y', time.localtime()))
    redirect('http://hankso.com:9999')
