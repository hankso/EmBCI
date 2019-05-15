#!/usr/bin/env python
# coding=utf-8
#
# File: EmBCI/embci/webui/__init__.py
# Author: Hankso
# Webpage: http://github.com/hankso
# Time: Fri 14 Sep 2018 21:51:46 CST

'''
webui
'''

# built-in
from __future__ import absolute_import
import os
import sys
import logging
import functools
import importlib
import traceback
from logging.handlers import RotatingFileHandler

# requirements.txt: network: bottle, gevent, gevent-websocket
# requirements.txt: optional: argparse
import bottle
import gevent
from geventwebsocket.handler import WebSocketHandler
try:
    import argparse
    from packaging import version
    if version.parse(argparse.__version__) >= version.parse("1.4.0"):
        raise ImportError
except ImportError:
    from ..utils import argparse as argparse

from ..utils import LockedFile, LoggerStream, AttributeDict, AttributeList
from ..utils import get_self_ip_addr, config_logger, get_config, get_boolean
from ..configs import PIDDIR
import embci.apps


# =============================================================================
# constants
#
__dir__ = os.path.dirname(os.path.abspath(__file__))
__port__ = int(get_config('WEBUI_PORT', 80))
__host__ = get_self_ip_addr(get_config('WEBUI_HOST', '0.0.0.0'))
__appsdir__ = os.path.join(__dir__, '../apps')
__pidfile__ = os.path.join(PIDDIR, 'webui.pid')
DEFAULT_ICON = '/images/icon2.png'
root = bottle.Bottle()
logger = logging.getLogger(__name__)
subapps = AttributeList()


# =============================================================================
# routes
#
@root.route('/')
def index_r():
    bottle.redirect('/index.html')


@root.route('/index.html')
def index():
    kwargs = {
        'subapps': [app for app in subapps if app.obj is not None],
    }
    return bottle.template(os.path.join(__dir__, 'index.html'), **kwargs)


@root.route('/<filename:path>')
def static(filename):
    return bottle.static_file(filename=filename, root=__dir__)


@root.route('/reload')
def reload():
    # TODO: runtime refresh/rescan subapps
    #  mount_subapps()
    bottle.abort(500, 'Not implemented yet!')


@root.route('/debug')
def debug():
    bottle.redirect('http://{}:9999'.format(__host__))


# =============================================================================
# functions
#
def mount_subapps(applist=subapps):
    '''
    Mount subapps from:
    1. default settings of `applist`
    2. embci.apps.__all__
    3. application folders under `/path/to/embci/apps/`
    '''
    for appname in embci.apps.__all__:
        if appname in applist.name:
            continue
        try:
            appmod = getattr(embci.apps, appname)
            appname = getattr(appmod, 'APPNAME', appname)
            appobj = appmod.application
        except AttributeError:
            logger.warn('Load `application` object from app `{}` failed. '
                        'Check out `embci.apps.__doc__`.'.format(appname))
            applist.append(AttributeDict(name=appname, obj=None))
        else:
            applist.append(AttributeDict(
                name=appname, obj=appobj, target='/apps/' + appname.lower(),
                icon=os.path.join(appmod.__path__[0], 'icon.png')))

    for appname in os.listdir(embci.apps.__dir__):
        if appname in applist.name:
            continue
        if appname[0] in ['_', '.']:
            continue
        if not os.path.isdir(os.path.join(embci.apps.__dir__, appname)):
            continue
        # If use `import {appname}` and `embci/apps/{appname}` can not be
        # successfully imported (lack of "__init__.py" for example), python
        # will then try to import {appname} from other paths in sys.path.
        # So here we use `importlib.import_module("embci.apps.{appname}")`
        try:
            appmod = importlib.import_module('embci.apps.' + appname)
            appname = getattr(appmod, 'APPNAME', appname)
            appobj = appmod.application
        except (ImportError, AttributeError):
            pass
        else:
            applist.append(AttributeDict(
                name=appname, obj=appobj, target='/apps/' + appname.lower(),
                icon=os.path.join(appmod.__path__[0], 'icon.png')))

    for app in applist:
        if app.obj is None:  # skip masked apps
            continue
        root.mount(app.target, app.obj)
        logger.info('link {} to subapp {}'.format(app.target, app.obj))
        if not os.path.exists(app.icon):
            app.icon = DEFAULT_ICON
    return applist


class GeventWebsocketServer(bottle.ServerAdapter):
    '''Gevent websocket server using local logger.'''
    def run(self, app):
        _logger = self.options.get('logger', logger)
        server = gevent.pywsgi.WSGIServer(
            listener=(self.host, self.port),
            application=app,
            # Fix WebSocketHandler log_request, see more below:
            #  log=LoggerStream(_logger, logging.DEBUG),
            error_log=LoggerStream(_logger, logging.ERROR),
            handler_class=WebSocketHandler)
        # WebSocketHandler use `server.logger.info`
        # instead of `server.log.debug`
        server.logger = _logger
        server.serve_forever()


def serve_forever(app=root, host=__host__, port=__port__, **k):
    try:
        bottle.run(app, GeventWebsocketServer, host, port, quiet=True, **k)
    except KeyboardInterrupt:
        pass
    except Exception:
        logger.error(traceback.format_exc())


def make_parser():
    parser = argparse.ArgumentParser(prog=__name__, description=(
        'Network based user interface of EmBCI embedded system. '
        'Default listen on http://{}:{}. '
        'Address can be specified by user.').format(__host__, __port__))
    parser.add_argument(
        '-v', '--verbose', default=0, action='count',
        help='be verbose, -vv for more details')
    parser.add_argument(
        '-l', '--log', default=None, type=str,
        help='log output to a file instead of stdout')
    parser.add_argument(
        '-p', '--pid', default=__pidfile__, type=str,
        help='pid file used for EmBCI WebUI, default `%s`' % __pidfile__)
    parser.add_argument(
        '--host', default=__host__, type=str, help='webpage address')
    parser.add_argument(
        '--port', default=__port__, type=int, help='port number')
    parser.add_argument(
        '--newtab', default=True, type=get_boolean,
        help='boolean, whether to open webpage of WebUI in browser')
    # TODO: webui: add `--exclude` to mask sub-apps to prevent from loading
    return parser


def open_webpage(addr):
    '''open embci-webui page if not run by root user'''
    if os.getuid() == 0:
        return
    try:
        from webbrowser import open_new_tab
        open_new_tab(addr)
    except Exception:
        pass


def main(arg):
    parser = make_parser()
    args = vars(parser.parse_args(arg))

    # ensure host address legal
    from socket import inet_aton, inet_ntoa, error
    try:
        args['host'] = inet_ntoa(inet_aton(
            args.get('host', __host__).replace('localhost', '127.0.0.1')
        ))
    except error:
        parser.error("argument --host: invalid address: '%s'" % args['host'])

    # config logger with loglevel by counting number of -v
    level = max(logging.WARN - args.get('verbose', 0) * 10, 10)
    if args.get('log') is not None:
        kwargs = {
            'filename': args['log'],
            'handler': functools.partial(
                RotatingFileHandler, maxBytes=100 * 2**10, backupCount=5)
        }
    else:
        kwargs = {'stream': sys.stdout}
    config_logger(logger, level, **kwargs)
    args['logger'] = logger

    # load and mount subapps
    mount_subapps()

    pidfile = LockedFile(args.get('pid', __pidfile__), pidfile=True)
    pidfile.acquire()
    logger.info('Using PIDFILE: {}'.format(pidfile))

    addr = 'http://%s:%d/' % (args['host'], args['port'])
    logger.info('Listening on : ' + addr)
    logger.info('Hit Ctrl-C to quit.\n')
    if args.pop('newtab'):
        open_webpage(addr)

    serve_forever(**args)
    pidfile.release()
