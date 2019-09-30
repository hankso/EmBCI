#!/usr/bin/env python3
# coding=utf-8
#
# File: apps/streaming/utils.py
# Authors: Hank <hankso1106@gmail.com>
# Create: 2019-07-08 21:58:56

# built-in
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
import time

# requirements.txt: necessary: pyzmq, six
import zmq
from six import string_types

from embci.utils import ensure_bytes, ensure_unicode

from . import CMD_ADDR


context = zmq.Context()
producer = None


def get_producer():
    global producer
    if producer is not None:
        return producer
    producer = context.socket(zmq.REP)
    try:
        producer.bind(CMD_ADDR)
    except zmq.ZMQError as e:
        # TODO: embci.apps.streaming: bind_to_random_port when addr in use?
        raise e
    else:
        return producer


def get_consumer():
    '''multiple consumers will share the same context'''
    c = context.socket(zmq.REQ)
    c.connect(CMD_ADDR)
    return c


def send_message(cmd_or_args, delay=0.2):
    if not cmd_or_args:
        return ''
    if isinstance(cmd_or_args, (list, tuple)):
        cmd = ' '.join([str(arg) for arg in cmd_or_args])
    elif not isinstance(cmd_or_args, string_types):
        cmd = str(cmd_or_args)
    else:
        cmd = cmd_or_args
    c = get_consumer()
    c.send(ensure_bytes(cmd))
    if cmd in ['exit', 'quit']:
        ret = ''
    else:
        time.sleep(delay)
        ret = c.recv()
    c.close()
    return ensure_unicode(ret)
