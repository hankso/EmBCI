#!/usr/bin/env python
# coding=utf-8
'''
File: EmBCI/embci/webui/__init__.py
Author: Hankso
Web: http://github.com/hankso
Time: Fri Sep 14 21:51:46 2018
'''
from __future__ import absolute_import, division, print_function

import os
import sys
import time
import importlib
import traceback

__dir__ = os.path.dirname(os.path.abspath(__file__))
__file__ = os.path.basename(__file__)

# requirements.txt: network: bottle, bottle-websocket
# deprecated: necessary: mod_wsgi(cooperate with Apache server)
from bottle import Bottle, static_file, redirect, response, run
from bottle.ext.websocket import GeventWebSocketServer
root = Bottle()

PORT = 80
PIDFILE = '/run/embci/webui.pid'


@root.route('/')
def index():
    redirect('/index.html')


@root.route('/<filename:path>')
def static(filename):
    return static_file(filename=filename, root=__dir__)


@root.route('/debug')
def debug():
    response.set_cookie(
        'last_debug', time.strftime('%a,%b %d %H:%M:%S %Y', time.localtime()))
    redirect('http://hankso.com:9999')


def serve_forever(port=PORT):
    # mount sub-applications
    if __dir__ not in sys.path:
        sys.path.append(__dir__)
    app_dir = os.path.join(__dir__, 'webapps')
    for name in os.listdir(app_dir):
        if not os.path.isdir(os.path.join(app_dir, name)):
            continue
        # In order to keep compatiable with Apache mod_wsgi module, offer an
        # bottle.Bottle instance named `application` in each packages
        app = importlib.import_module('webapps.' + name).application
        root.mount('/apps/{}'.format(name), app)
        root.mount('/apps/{}/'.format(name), app)
        print('link /apps/{}/* to sub-app {} @ {}'.format(name, name, app))
    print('link /* to root-app main @ {}'.format(root))

    try:
        run(app=root, host='0.0.0.0', port=port, server=GeventWebSocketServer)
    except KeyboardInterrupt:
        pass
    except:
        traceback.print_exc()
