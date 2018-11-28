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
import argparse
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


def serve_forever():
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
        run(app=root, host='0.0.0.0', port=PORT, server=GeventWebSocketServer)
    except KeyboardInterrupt:
        pass
    except:
        traceback.print_exc()


def main():
    global PIDFILE
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--pid', default=PIDFILE,
                        help='pid file of embci-webserver process')
    args = parser.parse_args()

    # Create PIDFILE
    PIDFILE = os.path.abspath(args.pid)
    try:
        os.makedirs(os.path.dirname(PIDFILE))
        with open(PIDFILE, 'w') as f:
            f.write(' {} '.format(os.getpid()))
        print('Using PIDFILE: ' + PIDFILE)
    except:
        pass

    # Open embci webpage
    try:
        from webbrowser import open_new_tab
        open_new_tab("http://localhost:%d" % PORT)
    except Exception:
        pass

    serve_forever()

    # Remove PIDFILE
    if os.path.exists(PIDFILE):
        try:
            os.system('rm {} 2>/dev/null'.format(PIDFILE))
        except:
            pass

if __name__ == '__main__':
    main()
