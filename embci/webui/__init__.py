#!/usr/bin/env python3
# coding=utf-8
#
# File: EmBCI/embci/webui/__init__.py
# Authors: Hank <hankso1106@gmail.com>
# Create: 2018-09-14 21:51:46

'''Web-based User Interface of EmBCI'''

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# requirements.txt: network: gevent
from gevent import monkey
monkey.patch_all(select=False, thread=False)
del monkey

# built-in
import os
import sys
import socket
import logging
import functools
import importlib
import traceback
from logging.handlers import RotatingFileHandler

# requirements.txt: network: bottle, gevent, gevent-websocket
import bottle
from gevent.pywsgi import WSGIServer
from geventwebsocket.handler import WebSocketHandler

from ..utils import (
    argparse, config_logger, get_config,
    get_host_addr, get_free_port, get_caller_globals,
    LockedFile, LoggerStream, AttributeDict, AttributeList, BoolString
)
from ..configs import DIR_PID, DIR_LOG
from .. import version


# =============================================================================
# constants & objects
#
__basedir__  = os.path.dirname(os.path.abspath(__file__))
__port__     = get_config('WEBUI_PORT', 80, type=int)
__host__     = get_host_addr(get_config('WEBUI_HOST', '0.0.0.0'))
__index__    = os.path.join(__basedir__, 'index.html')
__pidfile__  = os.path.join(DIR_PID, 'webui.pid')
root         = bottle.Bottle()
logger       = logging.getLogger(__name__)
subapps      = AttributeList()
masked       = set()
LOGDIRS      = set([DIR_LOG, ])
SNIPDIRS     = set([os.path.join(__basedir__, 'snippets'), ])
DEFAULT_ICON = '/images/icon2.png'


# =============================================================================
# routes
#
@root.route('/')
def webui_root():
    bottle.redirect('/index.html')


@root.route('/index.html')
@bottle.view(__index__)
def webui_index():
    return webui_appinfo()


@root.route('/appinfo')
def webui_appinfo():
    if BoolString(bottle.request.query.get('reload')):
        mount_apps()
    apps = []
    for app in subapps:
        appd = app.copy(dict)
        appd.pop('obj')
        apps.append(appd)
    return {'subapps': apps}


@root.route('/snippets/<filename:path>')
def webui_snippets(filename):
    for root in SNIPDIRS:
        if os.path.exists(os.path.join(root, filename)):
            return bottle.static_file(filename, root)
    bottle.abort(404, 'File does not exist.')


@root.route('/log/<filename:path>')
def webui_logfiles(filename):
    for root in LOGDIRS:
        if os.path.exists(os.path.join(root, filename)):
            return bottle.static_file(filename, root)
    bottle.abort(404, 'File does not exist.')


def webui_static_factory(*dirs):
    '''
    Useful function to serve static files under many directorys.

    Examples
    --------
    >>> from embci.webui import webui_static_factory
    >>> @bottle.route('/static/<filename>')
    ... def static_files(filename):
    ...     return webui_static_factory('./src', '/srv', '/var/www')(filename)

    You can also bind callback function by:
    >>> bottle.route('/static/<filename>', 'GET', webui_static_factory('/srv'))
    '''
    dirs = set(dirs).union({__basedir__})
    def static_files(*fn, **fns):                                  # noqa: E306
        if fn or fns:
            fn = (fn and fn[0]) or (fns and fns.popitem()[1])
        else:
            raise ValueError('Function called without a filename.')
        for root in dirs:
            if os.path.exists(os.path.join(root, fn)):
                return bottle.static_file(fn, root)
        return bottle.HTTPError(404, 'File does not exist.')
    return static_files


root.route('/<filename:path>', 'GET', webui_static_factory())


# =============================================================================
# functions
#
def mount_apps(applist=subapps):
    '''
    Mount subapps from:
    0. default settings of `applist`
    1. list of masked apps from commmand line (runtime)
    2. embci.apps.__all__
    3. application folders under `/path/to/embci/apps/`
    '''
    import embci.apps

    for appname in masked:
        if appname in applist.name:
            continue
        applist.append(AttributeDict(
            name=appname, obj=None, path='', hidden=True,
            loader='masked from embci.webui.__main__'
        ))

    for appname in embci.apps.__all__:
        try:
            appmod = getattr(embci.apps, appname)
            if appmod is None:           # This app has been masked
                raise AttributeError
            apppath = os.path.abspath(appmod.__path__[0])
            if apppath in applist.path:  # Different app names of same path
                continue
            appname = getattr(appmod, 'APPNAME', appname)
            if appname in applist.name:  # Same app name of different paths
                continue
            appobj = appmod.application
        except AttributeError:
            logger.debug('Load `application` object from app `{}` failed. '
                         'Check out `embci.apps.__doc__`.'.format(appname))
            if appname in applist.name:
                continue
            applist.append(AttributeDict(
                name=appname, obj=None, path='', hidden=True,
                loader='masked from embci.apps.__all__'
            ))
        else:
            applist.append(AttributeDict(
                name=appname, obj=appobj, path=apppath,
                loader='loaded by embci.apps.__all__',
                hidden=getattr(appmod, 'HIDDEN', False),
            ))

    for appfolder in os.listdir(embci.apps.__basedir__):
        if appfolder[0] in ['_', '.']:
            continue
        apppath = os.path.join(embci.apps.__basedir__, appfolder)  # abspath
        if not os.path.isdir(apppath):
            continue
        if apppath in applist.path:
            continue
        # If use `import {appname}` and `embci/apps/{appname}` can not be
        # successfully imported (lack of "__init__.py" for example), python
        # will then try to import {appname} from other paths in sys.path.
        # So here we use `importlib.import_module("embci.apps.{appname}")`
        try:
            appmod = importlib.import_module('embci.apps.' + appfolder)
            appname = getattr(appmod, 'APPNAME', appfolder)
            if appname in applist.name:
                continue
            appobj = appmod.application
        except (ImportError, AttributeError):
            pass
        except Exception:
            logger.info('Load app `{}` failed!'.format(appname))
            logger.error(traceback.format_exc())
        else:
            applist.append(AttributeDict(
                name=appname, obj=appobj, path=apppath,
                loader='loaded by embci.apps.__basedir__',
                hidden=getattr(appmod, 'HIDDEN', False),
            ))

    for app in applist:
        if app.obj is None:  # skip masked apps
            continue
        app.target = '/apps/' + app.name.lower()
        root.mount(app.target, app.obj)
        logger.debug('link `{target}` to `{name}`'.format(**app))
        app.icon = os.path.join(app.path, 'icon.png')
        if not os.path.exists(app.icon):
            app.icon = DEFAULT_ICON
        snippets = os.path.join(app.path, 'snippets')
        if os.path.exists(snippets):
            app.snippets = snippets
            SNIPDIRS.add(snippets)
    return applist


class GeventWebsocketServer(bottle.ServerAdapter):
    '''Gevent websocket server using local logger.'''
    def run(self, app):
        _logger = self.options.get('logger', logger)
        server = WSGIServer(
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


def serve_forever(host, port, app=root, **k):
    try:
        bottle.run(app, GeventWebsocketServer, host, port, quiet=True, **k)
    except KeyboardInterrupt:
        pass
    except Exception:
        logger.error(traceback.format_exc())


def make_parser():
    parser = argparse.ArgumentParser(prog=__name__, description=(
        'Network based user interface of EmBCI embedded system. '
        'Default listen on http://{}:{}. Address can be specified by user.'
    ).format(__host__, __port__))
    parser.add_argument('--host', default=__host__, type=str, help='hostname')
    parser.add_argument('--port', default=__port__, type=int, help='port num')
    parser.add_argument('--exclude', nargs='*', help='subapp names to skip')
    parser.add_argument(
        '-v', '--verbose', default=0, action='count',
        help='output more information, -vv for deeper details')
    parser.add_argument(
        '-l', '--log', type=str, dest='logfile',
        help='log output to a file instead of stdout')
    parser.add_argument(
        '-p', '--pid', default=__pidfile__, dest='pidfile',
        help='pid file used for EmBCI WebUI, default `%s`' % __pidfile__)
    parser.add_argument(
        '--newtab', default=True, type=BoolString,
        help='boolean, whether to open webpage of WebUI in browser')
    parser.add_argument('-V', '--version', action='version', version=version())
    return parser


def make_parser_debug(host, port):
    parser = argparse.ArgumentParser(prog=__name__, description=(
        'Debugging application loader for WebUI of EmBCI embedded system. '
        'Default listen on http://{}:{}. Address can be specified by user.'
    ).format(host, port or 0))
    parser.add_argument('--host', default=host, type=str, help='hostname')
    parser.add_argument('--port', default=port, type=int, help='port num')
    parser.add_argument(
        '-v', '--verbose', default=0, action='count',
        help='output more information, -vv for deeper details')
    parser.add_argument(
        '--newtab', default=False, type=BoolString,
        help='boolean, whether to open webpage of WebUI in browser')
    parser.add_argument('-V', '--version', action='version', version=version())
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


def main(args=None):
    global __host__, __port__, __pidfile__
    parser = make_parser()
    args = parser.parse_args(args or sys.argv[1:])

    # ensure host address and port number legal
    try:
        __host__ = args.host.replace('localhost', '127.0.0.1')
        __host__ = socket.inet_ntoa(socket.inet_aton(__host__))
    except socket.error:
        parser.error("argument --host: invalid address: '%s'" % args.host)
    try:
        __port__ = args.port
        s = socket.socket()
        s.bind((__host__, __port__))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    except (socket.error, OSError) as e:
        parser.error("arguemnt --port: %s: '%s'" % (e, args.port))
    finally:
        s.close()

    # config logger with loglevel by counting number of -v
    level = max(logging.WARN - args.verbose * 10, 10)
    if args.logfile is not None:
        LOGDIRS.add(os.path.dirname(os.path.abspath(args.logfile)))
        kwargs = {
            'filename': args.logfile,
            'handler': functools.partial(
                RotatingFileHandler, maxBytes=100 * 2**10, backupCount=5)
        }
    else:
        kwargs = {'stream': sys.stdout}
    config_logger(logger, level, **kwargs)

    # mask apps from command line
    masked.update(args.exclude or [])
    mount_apps(subapps)

    __pidfile__ = args.pidfile
    pidfile = LockedFile(__pidfile__, pidfile=True)
    pidfile.acquire()

    addr = 'http://%s:%d/' % (args.host, args.port)
    logger.info('Listening on : ' + addr)
    logger.info('Hit Ctrl-C to quit.\n')
    if args.newtab:
        open_webpage(addr)

    logger.info('Using PIDFILE: {}'.format(pidfile))
    serve_forever(__host__, __port__, logger=logger)
    pidfile.release()


def main_debug(app=None, host='127.0.0.1', port=None, args=None):
    app = app or get_caller_globals(1).get('application')
    if app is None:
        raise RuntimeError('No available application to serve.')
    args = make_parser_debug(host, port).parse_args(args or sys.argv[1:])
    level = logging.DEBUG if args.verbose else logging.INFO
    logger = config_logger('debug', level)
    args.port = args.port or get_free_port(args.host)
    addr = 'http://%s:%d/' % (args.host, args.port)
    logger.info('Listening on : ' + addr)
    logger.info('Hit Ctrl-C to quit.\n')
    if args.newtab:
        open_webpage(addr)
    serve_forever(args.host, args.port, app, debug=True, logger=logger)


# THE END
