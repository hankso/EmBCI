#!/usr/bin/env python
# coding=utf-8
'''
File: server.py
Author: Hankso
Web: http://github.com/hankso
Time: Fri Sep 14 21:51:46 2018
'''

import os
import sys
import time
import importlib

__dir__ = os.path.dirname(os.path.abspath(__file__))
__file__ = os.path.basename(__file__)

from bottle import Bottle, static_file, redirect, response, run
from bottle.ext.websocket import GeventWebSocketServer
root = Bottle()

# mount sub-applications
app_dir = os.path.join(__dir__, 'apps')
sys.path.append(app_dir)
for app_name in os.listdir(app_dir):
    # chdir everytime before importing even sys.path contains target folder
    # because some module may call `os.chdir` when imported
    os.chdir(app_dir)
    # In order to keep compatiable with Apache mod_wsgi module, offer an
    # bottle.Bottle instance named `application` in each python source file.
    application = importlib.import_module(app_name).application
    root.mount('/apps/{}'.format(app_name), application)
    root.mount('/apps/{}/'.format(app_name), application)
    print('links /apps/{}/* to sub-route {} @ {}'.format(
        app_name, app_name, application))
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


if __name__ == '__main__':
    run(app=root, host='0.0.0.0', port=80, server=GeventWebSocketServer)
