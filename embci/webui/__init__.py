#!/usr/bin/env python
# coding=utf-8
'''
File: EmBCI/embci/webui/__init__.py
Author: Hankso
Web: http://github.com/hankso
Time: Fri Sep 14 21:51:46 2018
'''
from __future__ import absolute_import, division, print_function

# built-in
import os
import sys
import time
import importlib
import traceback

# requirements.txt: network: bottle, bottle-websocket
# requirements.txt: optional: argparse
# deprecated: necessary: mod_wsgi(cooperate with Apache server)
from bottle import Bottle, static_file, redirect, response, run
from bottle.ext.websocket import GeventWebSocketServer
try:
    import argparse
    from packaging import version
    assert version.parse(argparse.__version__) >= version.parse("1.4.0")
except:
    from embci.utils import argparse as argparse

from embci.common import LockedFile

__dir__ = os.path.dirname(os.path.abspath(__file__))
__webapps__ = os.path.join(__dir__, 'webapps')
__file__ = os.path.basename(__file__)

root = Bottle()

NAME = '[EmBCI WebUI] '


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


def mount_subapps():
    if __dir__ not in sys.path:
        sys.path.insert(0, __dir__)
    for name in os.listdir(__webapps__):
        if not os.path.isdir(os.path.join(__webapps__, name)):
            continue
        # If webapps/{name} can not be successfully imported (lack of
        # "webapps/{name}/__init__.py" for example), python will then
        # try to import module {name} from other paths in sys.path.
        # So here we use `import_module(webapps.{name})` instead of
        # `__import__(name)`
        try:
            app = importlib.import_module('webapps.' + name).application
        except:
            traceback.print_exc()
            continue
        root.mount('/apps/{}'.format(name), app)
        root.mount('/apps/{}/'.format(name), app)
        print(NAME + 'link /apps/{}/* to sub-app {}'.format(name, app))


def serve_forever(port=80):
    try:
        run(app=root, host='0.0.0.0', port=port, server=GeventWebSocketServer)
    except KeyboardInterrupt:
        pass
    except:
        traceback.print_exc()


def main(arg):
    parser = argparse.ArgumentParser(
        prog='embci.webui',
        description=('WebUI of EmBCI embedded system. This service default '
                     'listen on http://localhost, one can change port to a '
                     'specific one'))
    parser.add_argument('-p', '--pid', default='/run/embci/webui.pid',
                        help=('pid file of embci-webui process, default use '
                              '/run/embci/webui.pid'))
    parser.add_argument('-P', '--port', default=80, type=int,
                        help='port that webservice will listen on')
    args = parser.parse_args(arg)

    mount_subapps()

    # Open embci webpage if not run by root user
    if os.getuid() != 0:
        try:
            from webbrowser import open_new_tab
            open_new_tab("http://localhost:%d" % args.port)
        except Exception:
            pass

    with LockedFile(args.pid, pidfile=True):
        #  print('Using PIDFILE: ' + args.pid)
        serve_forever(args.port)
