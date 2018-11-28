#!/usr/bin/env python
# coding=utf-8
'''
File: EmBCI/embci/webui/__main__.py
Author: Hankso
Web: http://github.com/hankso
Time: Mon Nov 26 16:50:46 2018
'''
# built-in
import os
import sys
import argparse

from . import PORT, PIDFILE, serve_forever


def main():
    global PIDFILE, PORT
    parser = argparse.ArgumentParser(
        prog='embci.webui',
        description=('WebUI of EmBCI embedded system. This service default '
                     'listen on http://localhost:{}, one can change port '
                     'to a specific one').format(PORT))
    parser.add_argument('-p', '--pid', default=PIDFILE,
                        help=('pid file of embci-webui process, default use '
                              '/run/embci/webui.pid'))
    parser.add_argument('-P', '--port', default=PORT, type=int,
                        help='port that webservice will listen on')
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

    # Open embci webpage if not run by root user
    if os.getuid() != 0:
        try:
            from webbrowser import open_new_tab
            open_new_tab("http://localhost:%d" % PORT)
        except Exception:
            pass

    serve_forever(port=args.port)

    # Remove PIDFILE
    if os.path.exists(PIDFILE):
        try:
            os.system('rm {} 2>/dev/null'.format(PIDFILE))
        except:
            pass

if __name__ == '__main__':
    sys.exit(main())
