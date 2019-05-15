#!/usr/bin/env python
# coding=utf-8
#
# File: DBS/__main__.py
# Author: Hankso
# Webpage: https://github.com/hankso
# Time: Tue 05 Mar 2019 02:07:51 CST

import sys

if __name__ == '__main__' and 'obfuscate' in sys.argv:
    import os
    import re
    import marshal
    __dir__ = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(__dir__, 'utils.src'), 'r') as f:
        codes = [line for line in f.readlines()
                 if not re.match(r'^\n|( *#)', line)]
    code = compile(''.join(codes), 'utils.py', 'exec')
    with open(os.path.join(__dir__, 'utils.bin'), 'w') as f:
        marshal.dump(code, f)
    print('Code of `utils.bin` has been updated!')
    sys.exit(0)


import bottle
from embci.webui import GeventWebsocketServer
from . import application, logger


def main():
    #  import logging
    #  import gevent.pywsgi
    #  from embci.utils import LoggerStream
    #  from geventwebsocket.handler import WebSocketHandler
    #  server = gevent.pywsgi.WSGIServer(
    #      listener=('0.0.0.0', 80), application=dbs,
    #      log=LoggerStream(logger, logging.DEBUG),
    #      error_log=LoggerStream(logger, logging.ERROR),
    #      handler_class=WebSocketHandler)
    #  server.serve_forever()
    bottle.run(application, host='0.0.0.0', port=8080,
               server=GeventWebsocketServer, logger=logger)


if __name__ == '__main__':
    sys.exit(main())
