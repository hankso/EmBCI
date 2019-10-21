#!/usr/bin/env python3
# coding=utf-8
#
# File: apps/streaming/__init__.py
# Authors: Hank <hankso1106@gmail.com>
# Create: 2019-03-10 03:56:49

'''
Task Streaming
--------------
Data streaming task is defined at `embci.apps.streaming`.
It provides a `pylsl` data stream available on this machine. Multiple clients
can connect to this stream and fetch realtime data from it simultaneously.
The default data input of this stream is ESP32 MCU on EmBCI Hardware (embedded
system), but fake data generator is used on PC platform. Because each clients
may need to apply different processing algorithums on their fetched data,
such as denoising or component analysis. This stream provides raw data from
amplifier and ADC.

Communication
-------------
Two interfaces are available for communicating with this task:
    - JSON-RPC
    - ZMQ + python-argparse

JSON Remote Procedure Call (JSON-RPC) is an excellent protocal for
interprocess communication both locally and through network. However, the
second method is more suggested. In this task ZMQ and argparse are used
cooperatively to construct a command-recieve-and-execute server.
Comparing to JSON-RPC, ZMQ also support local or remote TCP request (and many
more mechanisms like PGM, IPC and In-proc). Argparse can provide a neat help
output and error handle interface, as well as support to subcommands.

ZMQ is preferred if you want to interact with this task from C++/Python/Java
or even command line. JSON-RPC is suitable for web users in case someone want
to control the task from webpage using JavaScript.
'''


from embci.utils import config_logger
logger = config_logger(__name__)
del config_logger

from embci.utils import get_config
STM_HOST = get_config('STREAMING_HOST', '0.0.0.0')
CMD_PORT = get_config('STREAMING_CMD_PORT', 9997, type=int)
RPC_PORT = get_config('STREAMING_RPC_PORT', 9996, type=int)
del get_config

CMD_ADDR = 'tcp://{}:{}'.format(STM_HOST, CMD_PORT)
RPC_ADDR = 'http://{}:{}'.format(STM_HOST, RPC_PORT)

HELP = '''
ZMQ interface is listening on `{}`, from wich users can set
parameters of data stream at runtime. RPC server binds to `{}`.
'''.format(CMD_ADDR, RPC_ADDR)

CMD_USAGE = '''
ZMQ Example
-----------
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

Or you can use function `streaming.send_message_streaming`, which accepts a
string as command and return a string as result:

>>> from embci.apps.streaming import send_message_streaming
>>> while 1:
...     print(send_message_streaming(raw_input('$ ')))
$ summary
Status:
sample_rate:    499/500 Hz
bias_output:    enabled
input_source:   normal
stream_control: paused
impedance:      disabled
$ stream_control resume
'''.format(addr=CMD_ADDR)

RPC_USAGE = '''
RPC Example
-----------
You can use RPC service in JavaScript like:
> var request = {{
      method: 'system.describe',  // cascaded function name
      params: ['all'],            // parameters are optional
      id: '0xdeadbeef',           // id may be omitted
      jsonrpc: 2.0,               // see JSON-RPC Specification for version
  }};
> jQuery.ajax({{
      url: '{addr}',
      method: 'POST',                 // or type: 'POST'
      crossDomain: true,              // enable CORS ajax request
      data: JSON.stringify(request),  // must pass data in string
      dataType: 'json',               // response format
      success: obj => console.log('Result', obj.result || obj.error),
      error: (xhr, status, error) => console.error(error)
  }});

In Python, you can use client class provided by embci.utils.jsonrpc.
>>> from embci.utils import jsonrpc
>>> client = jsonrpc.JSONRPCClient('{addr}')
>>> client.stream_control('close')
>>> client.measure_impedance('true')
>>> print(client.summary())
Status:
sample_rate:    500/500 Hz
bias_output:    enabled
input_source:   normal
stream_control: closed
impedance:      enabled
>>> print(jsonrpc.__doc__)  # for more help message on JSON-RPC
'''.format(addr=RPC_ADDR)

EPILOG = HELP + CMD_USAGE + RPC_USAGE

__doc__ += EPILOG

from .utils import send_message as send_message_streaming

__all__ = ['send_message_streaming']
