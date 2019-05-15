#!/usr/bin/env python
# coding=utf-8
#
# File: apps/recorder/__main__.py
# Author: Hankso
# Webpage: https://github.com/hankso
# Time: Thu 14 Mar 2019 16:40:56 CST

# built-in
import sys
import shlex
import signal
import logging
import traceback

from embci.io import PylslReader as Reader
from embci.utils import config_logger, input
from . import Recorder, logger

HELP = '''
Type command and hit return to:
# TODO: write help message for embci.apps.recorder
'''

reader = Reader(sample_time=2, num_channel=8)
recorder = Recorder(reader)


def exit(*a, **k):
    logger.debug('exiting...')
    recorder.cmd(username=None)
    recorder.cmd('close')


def main(args=sys.argv[1:]):
    reader.start(method='thread', kwargs={'type': 'Reader Outlet'})
    signal.signal(signal.SIGHUP, exit)
    signal.signal(signal.SIGTERM, exit)

    if '-v' in args:
        args.pop(args.index('-v'))
        config_logger(logger, logging.DEBUG, addhdlr=False)
    recorder.start()
    if len(args):
        recorder.cmd(username=args[0])
    else:
        recorder.pause()

    try:
        while recorder.status != 'closed':
            try:
                command = input(timeout=3, flist=[sys.stdin, ])
                cmd = shlex.split(command)
            except Exception:
                continue
            if not cmd:
                continue
            logger.info('Received cmd: `%s`' % command)
            if len(cmd) == 1:
                recorder.cmd(cmd[0])
            elif len(cmd) == 2:
                recorder.cmd(**{cmd[0]: cmd[1]})
            else:
                logger.error('Invalid cmd: `%s`' % command)
    except KeyboardInterrupt:
        pass
    except Exception:
        logger.error(traceback.format_exc())
    finally:
        logger.debug('Main thread listening for commands terminated.')
        if recorder.status != 'closed':
            exit()


if __name__ == '__main__':
    sys.exit(main())
