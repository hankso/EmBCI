#!/usr/bin/env python
# coding=utf-8
#
# File: apps/streaming/__init__.py
# Author: Hankso
# Webpage: https://github.com/hankso
# Time: Sun 10 Mar 2019 03:56:49 CST

'''__doc__'''

# built-in
from __future__ import print_function
import os
import sys
import time
import signal
import platform
import traceback
import threading

# requirements.txt: necessary: pyzmq, six
# requirements.txt: optional: argparse
import zmq
from six import StringIO
try:
    # built-in argparse is provided >= 2.7
    # and argparse is maintained as a separate package now
    import argparse
    from packaging import version
    if version.parse(argparse.__version__) < version.parse("1.4.0"):
        raise ImportError
except ImportError:
    from embci.utils import argparse as argparse

if platform.machine() in ['arm', 'aarch64']:
    from embci.io import ESP32SPIReader as Reader
else:
    from embci.io import FakeDataGenerator as Reader
from embci.utils.ads1299_api import INPUT_SOURCES
from embci.utils import get_boolean


# =============================================================================
# Global variables
#
__dir__ = os.path.dirname(os.path.abspath(__file__))

STREAM_CONTROLS = ['start', 'pause', 'resume', 'close', 'restart']
LISTEN_PORT = 9997
TASK = '[{}] '.format(__name__)
FLAG = threading.Event()

HELP = '''
Task data-streaming started by {filename} script in EmBCI. Streaming
controller interface will listen on `tcp://localhost:{port}`, from
which users can set data capturing params at runtime. One can send
commands to the controller powered by PyZMQ from other processes.
'''.format(filename=__name__, port=LISTEN_PORT)

EPILOG = '''
Examples:
    >>> import zmq
    >>> c = zmq.Context()
    >>> q = c.socket(zmq.REQ)
    >>> q.connect('tcp://localhost:9997')
    >>> while 1:
    ...     q.send(raw_input('console@E01:$ '))
    ...     print(q.recv())
    console@E01:$ enable_bias
    True
    console@E01:$ enable_bias False
    console@E01:$ enable_bias
    False

See `<command> -h` for more information on each command.
'''


# =============================================================================
# Defaults
#
sample_rate = 500
bias_output = True
input_source = 'normal'
measure_impedance = False
stream_control = 'start'

reader = Reader(sample_rate, sample_time=1, num_channel=8, send_to_pylsl=True)


# =============================================================================
# Callback functions
#
def summary(args):
    ret = 'Status:\n'
    ret += 'sample_rate:\t{}/{} Hz\n'.format(
        reader.realtime_samplerate, sample_rate)
    ret += 'bias_output:\t{}\n'.format(
        'enabled' if bias_output else 'disabled')
    ret += 'input_source:\t{}\n'.format(input_source)
    ret += 'stream_control:\t{}ed\n'.format(reader.status)
    ret += 'measure_impedance:\t{}\n'.format(
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
    reader.set_input_source(param)


def _set_stream_control(param):
    getattr(reader, param)()


def _set_measure_impedance(param):
    reader.measure_impedance = param


def init_parser():
    parser = argparse.ArgumentParser(
        prog=__name__, description=HELP, epilog=EPILOG, add_help=False,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        usage='<command> [-h] [param]')
    subparsers = parser.add_subparsers(
        prog='', title='Support commands are', metavar='')

    # Command: summary
    subparsers.add_parser(
        'summary', aliases=['info'], help='summary of current stream status'
    ).set_defaults(func=summary)

    # Command: help
    subparsers.add_parser(
        'help', aliases=['h'], help='show this help message and exit'
    ).set_defaults(func=lambda args: parser.format_help())

    # Command: sample rate
    sparser = subparsers.add_parser(
        'sample_rate', aliases=['rate'], epilog=_set_sample_rate.__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        help='data stream sample rate')
    sparser.add_argument('param', nargs='?',
                         choices=[250, 500, 1000], type=int)
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
    sparser.add_argument('param', nargs='?', choices=STREAM_CONTROLS)
    sparser.set_defaults(func=_subcommand, subcmd='stream_control')

    # Command: measure impedance
    sparser = subparsers.add_parser(
        'measure_impedance', aliases=['ipd'],
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=_set_measure_impedance.__doc__,
        help='Measure impedance of channels')
    sparser.add_argument('param', nargs='?', type=get_boolean)
    sparser.set_defaults(func=_subcommand, subcmd='measure_impedance')

    # Command: exit
    subparsers.add_parser(
        'exit', help='terminate this task!!!'
    ).set_defaults(func=lambda args: FLAG.set())

    return parser


def repl(flag_term):
    reply = zmq.Context().socket(zmq.REP)
    reply.bind('tcp://127.0.0.1:%d' % LISTEN_PORT)
    print(TASK + 'Listening on tcp://localhost:%d' % LISTEN_PORT)
    poller = zmq.Poller()
    poller.register(reply, zmq.POLLIN)

    # parser will print error & help info to sys.stderr & sys.stdout
    # so redirect them to socket.send
    parser = init_parser()
    time.sleep(0.5)
    stderr, stdout = sys.stderr, sys.stdout
    msg = sys.stderr = sys.stdout = StringIO()

    while not flag_term.isSet():
        try:
            # 1 waiting for command
            if not poller.poll(timeout=500):
                continue
            cmd = [_.strip() for _ in reply.recv().split()]

            # 2 parse commands
            ret = ''
            try:
                args = parser.parse_args(cmd)
            except SystemExit:
                # handle parse error
                if cmd:
                    ret = msg.getvalue()
                    msg.truncate(0)
            else:
                # execute command
                ret = args.func(args)

            # 3 return result of command
            if ret is None:
                # exit will return None
                break
            reply.send(str(ret) + '\n')
        except zmq.ZMQError:
            print(TASK + 'zmq socket error', file=stdout)
        except KeyboardInterrupt:
            FLAG.set()
        except Exception:
            traceback.print_exc(file=stdout)
    sys.stderr, sys.stdout = stderr, stdout
    time.sleep(0.5)
    reply.close()
    reader.close()
    print(TASK + 'Controller thread terminated.')


def main(arg):
    # TODO: embci.apps.streaming: pick random port number
    # task can safely exit if killed by `kill command` or `user log out`
    signal.signal(signal.SIGTERM, lambda *a: FLAG.set())
    signal.signal(signal.SIGHUP, lambda *a: FLAG.set())

    print(TASK + 'Start streaming.')
    print(HELP + EPILOG)
    print(TASK + 'Starting {}'.format(reader))

    # let REPL occupy main thread
    reader.start(method='thread')
    repl(FLAG)

    # Let reader occupy main thread is not a good idea because `reader`
    # can't handle SIGTERM and SIGINT properly as `repl` does. So this
    # method is not suggested.
    #  threading.Thread(target=repl, args=(FLAG)).start()
    #  reader.start(method='block')


# THE END
