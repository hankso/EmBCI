#!/usr/bin/env python3
# coding=utf-8
#
# File: apps/recorder/__main__.py
# Authors: Hank <hankso1106@gmail.com>
# Create: 2019-03-14 16:40:56

# built-in
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
import sys
import shlex
import traceback

from embci.io import LSLReader as Reader
from embci.utils import input, TimeoutException
from . import Recorder, logger, debug

HELP = '''
This file provides a command line interface for user to control a recorder on
default LabStreamingLayer reader.

Type command and hit return to:
# TODO: write help message for `python -m embci.apps.recorder`
'''

reader = Reader()
recorder = Recorder(reader)


def exit(*a, **k):
    logger.debug('exiting...')
    recorder.cmd(username=None)
    recorder.cmd('close')
    reader.close()


def main(args=sys.argv[1:]):
    reader.start(method='thread', type='Reader Outlet')

    if '-v' in args:
        args.remove('-v')
        debug(True)
    recorder.start()
    recorder.cmd(username=(args[0] if len(args) else None))

    while recorder.started:
        try:
            command = input('>>> ')
            cmd = shlex.split(command)
            if not cmd:
                continue
            logger.info('Received cmd: `%s`' % command)
            if len(cmd) == 1:
                recorder.cmd(cmd[0])
            elif len(cmd) == 2:
                recorder.cmd(**{cmd[0]: cmd[1]})
            else:
                logger.error('Invalid cmd: `%s`' % command)
        except TimeoutException:
            pass
        except KeyboardInterrupt:
            break
        except Exception:
            logger.error(traceback.format_exc())
            break
    print('\n')
    logger.debug('Main thread listening for commands terminated.')
    exit()


if __name__ == '__main__':
    sys.exit(main())
