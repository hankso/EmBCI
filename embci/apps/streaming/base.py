#!/usr/bin/env python
# coding=utf-8
#
# File: apps/streaming/base.py
# Author: Hankso
# Webpage: https://github.com/hankso
# Time: Mon 08 Jul 2019 21:56:47 CST

# built-in
from __future__ import print_function
import sys
import shlex
import signal
import platform
import traceback

# requirements.txt: necessary: pyzmq
# requirements.txt: optional: argparse
import zmq
try:
    # built-in argparse is provided >= 2.7
    # and argparse is maintained as a separate package now
    import argparse
    from packaging import version
    if version.parse(argparse.__version__) < version.parse("1.4.0"):
        raise ImportError
except ImportError:
    from embci.utils import argparse as argparse

from embci.utils.ads1299_api import INPUT_SOURCES
from embci.utils import get_boolean, TempStream, LoopTaskMixin, Singleton

if platform.machine() in ['arm', 'aarch64']:
    from embci.io import ESP32SPIReader as Reader
else:
    from embci.io import FakeDataGenerator as Reader

from . import logger, CMD_ADDR, CMD_HELP, CMD_USAGE
from .utils import producer


# =============================================================================
# Defaults

SCTL = ['start', 'pause', 'resume', 'close', 'restart']
reader = repl = None
sample_rate = 500
bias_output = True
input_source = 'normal'
measure_impedance = False
stream_control = 'start'


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


def exit():
    repl.close()


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
    reader.set_input_source(param)


def _set_stream_control(param):
    getattr(reader, param)()


def _set_measure_impedance(param):
    reader.measure_impedance = param


def _set_channel(args):
    if args.action is None:
        return 'Not implemented yet: get channel status'
    reader.set_channel(args.param, args.action)
    return 'Channel {} set to {}'.format(args.param, args.action)


def init_parser():
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
    sparser.add_argument('ch', type=int)
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
    ).set_defaults(func=exit)

    return parser


class REPL(LoopTaskMixin):
    __metaclass__ = Singleton
    _tempstream = TempStream('stderr', 'stdout')

    def _stdinfo(self, clean=True):
        return '\n'.join([
            self._tempstream.get_string('stdout', clean),
            self._tempstream.get_string('stderr', clean)
        ])

    def start(self):
        if not super(REPL, self).start():
            return False
        self.loop(self.repl, (), {}, self.before, self.after)

    def before(self):
        self.parser = init_parser()
        self.reply = producer()
        self.poller = zmq.Poller()
        self.poller.register(self.reply, zmq.POLLIN)  # | zmq.POLLOUT)
        logger.info('Listening on `{}`'.format(CMD_ADDR))
        # parser will print error & help info to sys.stderr & sys.stdout
        # so redirect them to socket.send
        self._tempstream.enable()
        # note: logging is not influenced because it saves stdout when imported

    def after(self):
        try:
            reader.close()
        except Exception:
            pass
        self._tempstream.disable()
        self.reply.close()
        del self.parser, self.reply, self.poller
        logger.info('Stopping reader {}'.format(reader))
        logger.info('ZMQ command listener thread terminated.')

    def repl(self):
        try:
            # 1 waiting for command
            if not self.poller.poll(timeout=500):
                return

            # 2 parse and execute command
            ret = self.parse_one_cmd(self.reply.recv()).strip()

            # 3 return result of command
            if ret in ['exit', 'quit']:
                self.close()
                return
            else:
                self.reply.send(str(ret or '') + '\n')
        except zmq.ZMQError as e:
            logger.info('ZMQ socket error: {}'.format(e))
        except KeyboardInterrupt as e:
            raise e  # self.loop default will stop this task
        except Exception:
            logger.error(traceback.format_exc())

    def parse_one_cmd(self, cmd, rst=''):
        cmd = shlex.split(cmd)
        try:
            args = self.parser.parse_args(cmd)
        except SystemExit:
            # handle parse error
            if not cmd:
                return ''
            return self._stdinfo()
        else:
            # execute command
            ret = args.func(args)
            log = self._stdinfo(clean=False)
            if log:
                ret += '\n' + log
            return ret


def main(arg):
    # BUG: embci.apps.streaming: python3 pylsl cannot create outlet?
    globals()['reader'] = reader = Reader(
        sample_rate, sample_time=1,
        num_channel=8, send_to_pylsl=True)
    globals()['repl'] = repl = REPL()

    # task can safely exit if killed by `kill command` or `user log out`
    signal.signal(signal.SIGTERM, lambda *a: repl.close())
    signal.signal(signal.SIGHUP, lambda *a: repl.close())

    logger.debug('Start streaming.')
    logger.debug('Starting {}'.format(reader))
    logger.info(CMD_HELP + CMD_USAGE)

    # let REPL occupy main thread
    reader.start(method='thread')
    repl.start()

    # Let reader occupy main thread is not a good idea because `reader`
    # can't handle SIGTERM and SIGINT properly as `repl` does. So this
    # method is not suggested.
    #  threading.Thread(target=repl.start).start()
    #  reader.start(method='block')

# THE END
