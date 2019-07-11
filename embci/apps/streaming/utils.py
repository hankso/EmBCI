#!/usr/bin/env python
# coding=utf-8
#
# File: apps/streaming/utils.py
# Author: Hankso
# Webpage: https://github.com/hankso
# Time: Mon 08 Jul 2019 21:58:56 CST

'''__doc__'''

# built-in
import time

# requirements.txt: necessary: pyzmq
import zmq

from embci.utils import strtypes, ensure_bytes, ensure_unicode

from . import CMD_ADDR


CONT = zmq.Context()


def producer():
    q = CONT.socket(zmq.REP)
    # TODO: embci.apps.streaming: use random port number
    #  globals()['CMD_PORT'] = q.bind_to_random_port()
    #  globals()['CMD_ADDR'] = 'tcp://{}:{}'.format(CMD_HOST, CMD_PORT)
    q.bind(CMD_ADDR)
    return q


def consumer():
    '''multiple consumers will share the same context'''
    q = CONT.socket(zmq.REQ)
    q.connect(CMD_ADDR)
    return q


def send_message(cmd_or_args):
    if not cmd_or_args:
        return ''
    if isinstance(cmd_or_args, (list, tuple)):
        cmd = ' '.join([str(arg) for arg in cmd_or_args])
    elif not isinstance(cmd_or_args, strtypes):
        cmd = str(cmd_or_args)
    else:
        cmd = cmd_or_args
    q = consumer()
    q.send(ensure_bytes(cmd))
    time.sleep(0.2)
    ret = q.recv()
    q.close()
    return ensure_unicode(ret)
