#!/usr/bin/env python3
# coding=utf-8
#
# File: apps/streaming/base.py
# Authors: Hank <hankso1106@gmail.com>
# Create: 2019-07-08 21:56:47

# built-in
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
import os
import sys
import shlex
import signal
import platform
import traceback

# requirements.txt: necessary: pyzmq
import zmq

from embci.drivers.ads1299 import INPUT_SOURCES
from embci.utils import (
    get_boolean, argparse,
    TempStream, LoopTaskInThread, Singleton
)

if platform.machine() in ['arm', 'aarch64']:       # running on embedded device
    from embci.io import ESP32SPIReader as Reader
else:                                              # running on computer
    from embci.io import FakeDataGenerator as Reader

from . import logger, CMD_ADDR, CMD_HELP, CMD_USAGE
from .utils import get_producer


# =============================================================================
# Defaults

SCTL = ['start', 'pause', 'resume', 'close', 'restart']
sample_rate = 500
bias_output = True
input_source = 'normal'
measure_impedance = False
stream_control = 'start'
reader = Reader(sample_rate, sample_time=1, num_channel=8, send_pylsl=True)


# =============================================================================
# argparse parser & callback functions

def summary(args):
    ret = 'Status:\n'
    ret += 'sample_rate:\t{:.2f}/{} Hz\n'.format(
        reader.realtime_samplerate, sample_rate)
    ret += 'bias_output:\t{}\n'.format(
        'enabled' if bias_output else 'disabled')
    ret += 'input_source:\t{}\n'.format(input_source)
    ret += 'stream_control:\t{}\n'.format(reader.status)
    ret += 'impedance:\t{}\n'.format(
        'enabled' if measure_impedance else 'disabled')
    return ret


def _subcommand(args):
    if args.param is not None:
        func = globals()['_set_' + args.subcmd]
        try:
            func(args.param)
        except Exception:
            return ''.join(traceback.format_exception(*sys.exc_info()))
        globals()[args.subcmd] = args.param
        return 'Set `{subcmd}` to `{param}`'.format(**vars(args))
    else:
        return globals()[args.subcmd]


def _set_sample_rate(param):
    '''TODO: doc here'''
    reader.set_sample_rate(param)


def _set_bias_output(param):
    reader.enable_bias = param


def _set_input_source(param):
    reader.input_source = param


def _set_stream_control(param):
    getattr(reader, param)()


def _set_measure_impedance(param):
    reader.measure_impedance = param


def _set_channel(args):
    if args.action is None:
        return 'Not implemented yet: get channel status'
    reader.set_channel(args.channel, args.action)
    return 'Channel {} set to {}'.format(args.channel, args.action)


def make_parser():
    parser = argparse.ArgumentParser(
        prog=__name__, add_help=False, usage='<command> [-h] [param]',
        description='', epilog=' \n%s\n%s' % (CMD_HELP, CMD_USAGE),
        formatter_class=argparse.RawDescriptionHelpFormatter)
    subparsers = parser.add_subparsers(
        prog='', title='Stream commands are', metavar='')

    # Command: set channel
    sparser = subparsers.add_parser(
        'set_channel', aliases=['ch'], epilog=_set_channel.__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        help='Enable/disable specific channel')
    sparser.add_argument('channel', type=int)
    sparser.add_argument('action', nargs='?', type=get_boolean)
    sparser.set_defaults(func=_set_channel)

    # Command: sample rate
    sparser = subparsers.add_parser(
        'sample_rate', aliases=['rate'], epilog=_set_sample_rate.__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        help='Set/get data stream sample rate')
    sparser.add_argument(
        'param', nargs='?', type=int, help='sample per second (in Hz)',
        choices=[250, 500, 1000, 2000, 4000, 8000, 16000])
    sparser.set_defaults(func=_subcommand, subcmd='sample_rate')

    # Command: bias output
    sparser = subparsers.add_parser(
        'bias_output', aliases=['bias'], epilog=_set_bias_output.__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        help='Generate signal on BIAS')
    sparser.add_argument('param', nargs='?', type=get_boolean)
    sparser.set_defaults(func=_subcommand, subcmd='bias_output')

    # Command: input source
    sparser = subparsers.add_parser(
        'input_source', aliases=['in'], epilog=_set_input_source.__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        help='Select ADS1299 input source')
    sparser.add_argument('param', nargs='?', choices=INPUT_SOURCES.keys())
    sparser.set_defaults(func=_subcommand, subcmd='input_source')

    # Command: stream control
    sparser = subparsers.add_parser(
        'stream_ctrl', aliases=['st'], epilog=_set_stream_control.__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        help='Control data stream status')
    sparser.add_argument('param', nargs='?', choices=SCTL)
    sparser.set_defaults(func=_subcommand, subcmd='stream_control')

    # Command: measure impedance
    sparser = subparsers.add_parser(
        'impedance', aliases=['ipd'],
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=_set_measure_impedance.__doc__,
        help='Measure impedance of channels')
    sparser.add_argument('param', nargs='?', type=get_boolean)
    sparser.set_defaults(func=_subcommand, subcmd='measure_impedance')

    #  subparsers = parser.add_subparsers(
    #      prog='', title='Task commands are', metavar='')

    # Command: summary
    subparsers.add_parser(
        'summary', aliases=['info'], help='Summary of current stream status'
    ).set_defaults(func=summary)

    # Command: help
    subparsers.add_parser(
        'help',  help='Show this help message and do nothing'
    ).set_defaults(func=lambda args: parser.format_help())

    # Command: exit
    subparsers.add_parser(
        'exit', help='Terminate this task (BE CAREFUL!)'
    ).set_defaults(func=lambda args: os.kill(os.getpid(), signal.SIGINT))

    return parser


class REPL(LoopTaskInThread):
    __metaclass__ = Singleton
    _tempstream = TempStream('stderr', 'stdout')
    _argparser = make_parser()

    def __init__(self, *args, **kwargs):
        super(REPL, self).__init__(self._repl, *args, **kwargs)

    def loop_before(self):
        self.reply = get_producer()
        self.poller = zmq.Poller()
        self.poller.register(self.reply, zmq.POLLIN)  # | zmq.POLLOUT)
        logger.info('Listening on `{}`'.format(CMD_ADDR))
        # parser will print error & help info to sys.stderr & sys.stdout
        # so redirect them to socket.send
        self._tempstream.enable()
        # note: logging is not influenced because it saves stdout when imported

    def _repl(self):
        try:
            # 1 waiting for command
            if not self.poller.poll(timeout=1000):
                return

            # 2 parse and execute command
            ret = self.parse_one_cmd(self.reply.recv()).strip()

            # 3 return result of command
            self.reply.send(str(ret or '') + '\n')
        except zmq.ZMQError as e:
            logger.info('ZMQ socket error: {}'.format(e))
        except KeyboardInterrupt as e:
            raise e  # self.loop will stop this task

    def loop_after(self):
        self._tempstream.disable()
        self.reply.close()
        del self.reply, self.poller
        logger.info('ZMQ command listener thread terminated.')

    def parse_one_cmd(self, cmd):
        cmd = shlex.split(cmd)
        try:
            args = self._argparser.parse_args(cmd)
        except SystemExit:
            # handle parse error
            if not cmd:
                return ''
            return self.stdinfo()
        else:
            # execute command
            ret = args.func(args)
            log = self.stdinfo(clean=False)
            if log:
                ret += '\n' + log
            return ret

    def stdinfo(self, clean=True):
        return '\n'.join([
            self._tempstream.get_string('stdout', clean),
            self._tempstream.get_string('stderr', clean)
        ])


# =============================================================================
# ZMQ & JSONRPC interface

def main():
    # Keep repl thread alive when the main thread ended. This will be set to
    # True if RPC service is implemented and occupy main thread
    repl = REPL(daemon=False)

    def exit(*a):
        repl.close()
        # rpcserver.close()

    signal.signal(signal.SIGHUP, exit)   # user log out
    signal.signal(signal.SIGINT, exit)   # Ctrl-C or kill -2
    signal.signal(signal.SIGTERM, exit)  # kill -15 by default

    logger.debug('Start streaming.')
    logger.debug('Starting {}'.format(reader))
    logger.info(CMD_HELP.rstrip())

    reader.start(method='thread')
    repl.start()

    # block main thread, will be replaced by RPC serve_forever
    while repl.isAlive():
        repl.join(3)

    # Let reader occupy main thread is not a good idea because `reader`
    # can't handle SIGTERM and SIGINT properly as `repl` does. So this
    # method is not suggested.
    #  REPL(daemon=True).start()
    #  reader.start(method='block')


# THE END
