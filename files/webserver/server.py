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
with open(os.path.join(__dir__, 'run.pid'), 'w') as f:
    f.write(' {}'.format(os.getpid()))

from bottle import Bottle, static_file, redirect, response, run
from bottle.ext.websocket import GeventWebSocketServer
root = Bottle()

# mount sub-applications
if __dir__ not in sys.path:
    sys.path.append(__dir__)
app_dir = os.path.join(__dir__, 'webapps')
for name in os.listdir(app_dir):
    if os.path.isfile(os.path.join(app_dir, name)):
        continue
    # In order to keep compatiable with Apache mod_wsgi module, offer an
    # bottle.Bottle instance named `application` in each python source file.
    app = importlib.import_module('webapps.' + name).application
    root.mount('/apps/{}'.format(name), app)
    root.mount('/apps/{}/'.format(name), app)
    print('links /apps/{}/* to sub-app {} @ {}'.format(name, name, app))
    #  # chdir everytime before importing even sys.path contains target folder
    #  # because some module may call `os.chdir` when imported
    #  os.chdir(__dir__)


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
    print('links /* to main app root @ {}'.format(root))
    run(app=root, host='0.0.0.0', port=80, server=GeventWebSocketServer)
