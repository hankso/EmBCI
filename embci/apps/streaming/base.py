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
import sys
import time
import shlex
import signal
import platform
import traceback
from pydoc import getdoc

# requirements.txt: necessary: pyzmq
import zmq

from embci.drivers.ads1299 import INPUT_SOURCES
from embci.utils import (
    get_boolean, argparse,
    TempStream, LoopTaskInThread, Singleton, NameSpace, jsonrpc
)

if platform.machine() in ['arm', 'aarch64']:       # running on embedded device
    from embci.io import ESP32SPIReader as Reader
else:                                              # running on computer
    from embci.io import FakeDataGenerator as Reader

from . import logger, STM_HOST, CMD_ADDR, RPC_ADDR, RPC_PORT, EPILOG
from .utils import get_producer


# =============================================================================
# Defaults

SCTL = ['start', 'pause', 'resume', 'close', 'restart']
sample_rate = 500
bias_output = True
input_source = 'normal'
measure_impedance = False
stream_control = 'start'
reader = None


# =============================================================================
# argparse parser, RPC server and callback functions

def summary(*args):
    '''Summary of current stream status'''
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


def exit(*args):
    '''Terminate this task (BE CAREFUL!)'''
    try:
        reader.close()
        repl.close(); time.sleep(1)  # wait for poller's timeout   # noqa: E702
        server.server_close()
    except Exception:
        logger.error(traceback.format_exc())


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
    '''
    example:
    >>> sample_rate
    500
    >>> sample_rate 250
    Set sample_rate to 250
    >>> rate // alias of sample_rate
    250
    '''
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
    '''
    Raw signal quality will be better if useless channels are disabled.
    Suppose you use only CH1-CH7 and left CH8 suspended in the air, you can
    directly disable CH8 by:
    >>> channel 7 false // index of CH8 is 7
    Channel 7 set to False
    >>> channel 0 True|true|On|on|1
    Channel 0 set to True
    '''
    if args.action is None:
        return 'Not implemented yet: get channel status'
    reader.set_channel(args.channel, args.action)
    return 'Channel {} set to {}'.format(args.channel, args.action)


def make_parser():
    parser = argparse.ArgumentParser(
        prog=__name__, add_help=False, usage='<command> [-h] [param]',
        description='', epilog=(
            'See `<command> -h` for more help on each command.\n' + EPILOG
        ), formatter_class=argparse.RawDescriptionHelpFormatter)
    subparsers = parser.add_subparsers(
        prog='', title='Stream commands are', metavar='')

    # Command: sample rate
    sparser = subparsers.add_parser(
        'sample_rate', aliases=['rate'], epilog=getdoc(_set_sample_rate),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        help='Set/get data stream sample rate')
    sparser.add_argument(
        'param', nargs='?', type=int, help='sample per second (in Hz)',
        choices=[250, 500, 1000, 2000, 4000, 8000, 16000])
    sparser.set_defaults(func=_subcommand, subcmd='sample_rate')

    # Command: bias output
    sparser = subparsers.add_parser(
        'bias_output', aliases=['bias'], epilog=getdoc(_set_bias_output),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        help='Generate signal on BIAS')
    sparser.add_argument('param', nargs='?', type=get_boolean)
    sparser.set_defaults(func=_subcommand, subcmd='bias_output')

    # Command: input source
    sparser = subparsers.add_parser(
        'input_source', aliases=['in'], epilog=getdoc(_set_input_source),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        help='Select ADS1299 input source')
    sparser.add_argument('param', nargs='?', choices=INPUT_SOURCES.keys())
    sparser.set_defaults(func=_subcommand, subcmd='input_source')

    # Command: stream control
    sparser = subparsers.add_parser(
        'stream_ctrl', aliases=['sct'], epilog=getdoc(_set_stream_control),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        help='Control data stream status')
    sparser.add_argument('param', nargs='?', choices=SCTL)
    sparser.set_defaults(func=_subcommand, subcmd='stream_control')

    # Command: measure impedance
    sparser = subparsers.add_parser(
        'impedance', aliases=['ipd'], epilog=getdoc(_set_measure_impedance),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        help='Measure impedance of channels')
    sparser.add_argument('param', nargs='?', type=get_boolean)
    sparser.set_defaults(func=_subcommand, subcmd='measure_impedance')

    # Command: set channel
    sparser = subparsers.add_parser(
        'set_channel', aliases=['ch'], epilog=getdoc(_set_channel),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        help='Enable/disable specific channel')
    sparser.add_argument('channel', type=int)
    sparser.add_argument('action', nargs='?', type=get_boolean)
    sparser.set_defaults(func=_set_channel)

    #  subparsers = parser.add_subparsers(
    #      prog='', title='Task commands are', metavar='')

    # Command: summary
    subparsers.add_parser(
        'summary', aliases=['info'], help=summary.__doc__
    ).set_defaults(func=summary)

    # Command: help
    subparsers.add_parser(
        'help',  help='Show this help message and do nothing'
    ).set_defaults(func=lambda args: parser.format_help())

    # Command: exit
    subparsers.add_parser('exit', help=exit.__doc__).set_defaults(func=exit)

    return parser


def make_server():
    server = jsonrpc.JSONRPCServer(
        (STM_HOST, RPC_PORT), bind_and_activate=False)
    server.register_introspection_functions()

    def helper(name):
        def pass_args(*args):
            cmd = name + ' ' + ' '.join(map(str, args))
            return repl.parse_one_cmd(cmd).strip()
        pass_args.__doc__ = globals()['_set_' + name].__doc__
        return pass_args
    server.register_function(helper('sample_rate'), 'sample_rate')
    server.register_function(helper('bias_output'), 'bias_output')
    server.register_function(helper('input_source'), 'input_source')
    server.register_function(helper('stream_control'), 'stream_control')
    server.register_function(helper('measure_impedance'), 'measure_impedance')
    server.register_function(lambda channel, *args: _set_channel(NameSpace(
        channel = channel, action = args and args[0] or None
    )), 'set_channel')
    server.register_function(summary, 'summary')
    server.register_function(exit, 'exit')
    return server


class REPL(LoopTaskInThread, Singleton):
    argparser = make_parser()

    def __init__(self, *args, **kwargs):
        self._tempstream = TempStream('stderr', 'stdout')
        super(REPL, self).__init__(self._repl, *args, **kwargs)

    def loop_before(self):
        self.reply = get_producer()
        self.poller = zmq.Poller()
        self.poller.register(self.reply, zmq.POLLIN)  # | zmq.POLLOUT)
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
            cmd = self.reply.recv().decode('utf8')
            ret = self.parse_one_cmd(cmd).strip()

            # 3 return result of command
            self.reply.send(ret.encode('utf8'))
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
            args = self.argparser.parse_args(cmd)
        except SystemExit:
            # handle parse error
            if not cmd:
                return ''
            return self.stdinfo()
        else:
            # execute command
            ret = args.func(args)
            log = self.stdinfo(clean=False)
            return str(ret) + (log and ('\n' + log) or '')

    def stdinfo(self, clean=True):
        return '\n'.join([
            self._tempstream.get_string('stdout', clean),
            self._tempstream.get_string('stderr', clean)
        ])


# =============================================================================
# ZMQ & JSONRPC interface

def main():
    global reader, repl, server
    reader = Reader(sample_rate, sample_time=1, num_channel=8, send_pylsl=True)
    server = make_server()
    repl = REPL()
    try:
        assert reader.start(method='thread'), 'Cannot start {}'.format(reader)
    except Exception:
        logger.error(traceback.format_exc())
        return exit() or 1
    try:
        repl.start()
        server.server_bind()
        server.server_activate()
    except Exception as e:
        logger.error(e)
    else:
        logger.info(EPILOG)
        logger.info('{} listening on `{}`'.format(repl, CMD_ADDR))
        logger.info('{} listening on `{}`'.format(server, RPC_ADDR))
        logger.info('Data stream {} started'.format(reader))

    signal.signal(signal.SIGHUP, exit)   # user log out
    signal.signal(signal.SIGTERM, exit)  # kill -15 by default

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info('RPC server stopped.')
    except Exception:
        logger.error(traceback.format_exc())
    finally:
        exit()

    # Let reader occupy main thread is not a good idea because `reader`
    # can't handle SIGTERM and SIGINT properly as `repl` does. So this
    # method is not suggested.
    #  REPL(daemon=True).start()
    #  reader.start(method='block')


# THE END
