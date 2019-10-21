#!/usr/bin/env python3
# coding=utf-8
#
# File: apps/recorder/__main__.py
# Authors: Hank <hankso1106@gmail.com>
# Create: 2019-03-14 16:40:56

'''
This file provides a command line interface for user to control a recorder on
default LabStreamingLayer reader. It works like a command line version
LabRecorder(LSL Recorder App) but saves data into MATLAB(.mat) format.

Type `python -m embci.apps.recorder` and hit return to start this program.
Append '-v' if you need verbose log output. You can manipulate the recorder
by command like below:
    >>> username
    None
    >>> username testing
    username set to testing
    >>> username
    testing
    >>> status
    paused
    >>> resume
    True
    >>> summary
    buffer_length : 4
    buffer_max    : 7340032
    buffer_nbytes : 16000
    chunk         : 1
    status        : resumed
    username      : testing
    ...

Type `help` for more information.
'''

# built-in
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
import sys
import signal
import traceback


from . import logger, debug
from .base import globalvars, Recorder


def exit(*a, **k):
    try:
        globalvars.recorder.close()
        globalvars.reader.close()
    except Exception:
        traceback.print_exc()


def main_cli(args=sys.argv[1:]):
    from embci.utils import input, TimeoutException
    from embci.io import LSLReader

    reader = globalvars.reader = LSLReader()
    try:
        reader.start(method='thread')
    except RuntimeError:
        return 0
    else:
        recorder = globalvars.recorder = Recorder(reader)
        recorder.start()

    signal.signal(signal.SIGHUP, exit)
    signal.signal(signal.SIGALRM, exit)
    signal.signal(signal.SIGTERM, exit)
    recorder.username = args and args[0] or None

    while recorder.started:
        try:
            command = input('>>> ')
            logger.debug('Received command: `%s`' % command)
            print(recorder.cmd(command) or '')
        except TimeoutException:
            pass
        except KeyboardInterrupt:
            break
        except Exception:
            logger.error(traceback.format_exc())
            break
    exit()
    logger.debug('\nMain thread listening for commands terminated.')


def main_webui():
    from . import application
    from embci.webui import webui_static_host, main_debug
    webui_static_host(application, '/srv')
    try:
        main_debug(application)
    except Exception:
        logger.error(traceback.format_exc())
        return 1
    else:
        return 0
    finally:
        exit()


if __name__ == '__main__':
    if '-h' in sys.argv or '--help' in sys.argv:
        print(__doc__)
        sys.exit(0)
    if '-v' in sys.argv:
        sys.argv.remove('-v')
        debug(True)
    if 'server' in sys.argv:  # this option is only used for debugging
        sys.argv.remove('server')
        main = main_webui
    else:
        main = main_cli
    sys.exit(main())
