#!/usr/bin/env python
# coding=utf-8
#
# File: apps/streaming/__init__.py
# Author: Hankso
# Webpage: https://github.com/hankso
# Time: Sun 10 Mar 2019 03:56:49 CST

'''
Task Streaming
--------------
Data streaming task is defined at `embci.apps.streaming`.
It provides a `pylsl` data stream available on this machine. Multiple clients
can connect to this stream and fetch realtime data from it simultaneously.
The default data input of this stream is ESP32 MCU on EmBCI Hardware (embedded
system), while fake data generator is used on PC platform. Because each clients
may apply different processing algorithums on their fetched data, such as
denoising or component analysis, data output of this stream is raw data
(i.e. without any preprocessing).

Communication
-------------
Two interface is provided to access the control of this task:
    - JSON-RPC
    - ZMQ + python-argparse

JSON Remote Procedure Call (JSON-RPC) is an excellent protocal for
interprocess communication both locally and through network.
But the second method is of higher priority. In this task ZMQ and argparse
are used cooperatively to construct a command-recieve-and-execute server.
Comparing to JSON-RPC, ZMQ also support local or remote TCP request (and many
more mechanisms like PGM, IPC and In-proc). Argparse can provide a neat help
output and error handle interface, as well as support to subcommands.

ZMQ is more suggested if you want to communicate with this task from
C++/Python/Java or even command line. And JSON-RPC is suitable for web users
in case someone want to control the task from webpage using JavaScript.
'''


from embci.utils import config_logger
logger = config_logger(format='%(message)s')
del config_logger

from embci.utils import get_config
CMD_HOST = get_config('STREAMING_CMD_HOST', '0.0.0.0')
CMD_PORT = int(get_config('STREAMING_CMD_PORT', 9997))
RPC_HOST = get_config('STREAMING_RPC_HOST', '0.0.0.0')
RPC_PORT = int(get_config('STREAMING_RPC_PORT', 9996))
del get_config

CMD_ADDR = 'tcp://{}:{}'.format(CMD_HOST, CMD_PORT)
RPC_ADDR = 'Not implemented yet'

CMD_HELP = '''
ZMQ Address
-----------
ZMQ interface is listening on `{addr}`, from wich users can set
parameters of data stream at runtime.
'''.format(addr=CMD_ADDR)

RPC_HELP = '''
JSON-RPC Port
-------------
Not implemented yet.
'''

CMD_USAGE = '''
Examples:
    >>> import zmq
    >>> c = zmq.Context()
    >>> q = c.socket(zmq.REQ)
    >>> q.connect('{addr}')
    >>> while 1:
    ...     q.send(raw_input('console@E01:$ '))
    ...     print(q.recv())
    console@E01:$ bias_output
    True
    console@E01:$ bias_output False # Choose one from ON|off|False|true|1|0
    console@E01:$ bias_output
    False

Or you can use:
    >>> from embci.apps.streaming import send_message_streaming
    >>> while 1:
    ...     cmd = raw_input('> ')
    ...     rst = send_message_streaming(cmd)
    ...     print(rst)
    > summary
    Status:
    sample_rate:    499/500 Hz
    bias_output:    enabled
    input_source:   normal
    stream_control: paused
    impedance:      disabled

See `<command> -h` for more information on each command.
'''.format(addr=CMD_ADDR)


__doc__ = '\n'.join([__doc__, CMD_HELP, RPC_HELP])

import os
__dir__ = os.path.dirname(os.path.abspath(__file__))
del os

from .utils import send_message as send_message_streaming
__all__ = ['send_message_streaming']
