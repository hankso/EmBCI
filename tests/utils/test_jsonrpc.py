#!/usr/bin/env python3
# coding=utf-8
#
# File: EmBCI/tests/utils/test_jsonrpc.py
# Authors: Hank <hankso1106@gmail.com>
# Create: 2019-07-28 14:53:18
#
# TODO:
#   test jsonrpc client

# built-in
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
import os

import embci.utils.jsonrpc as jsonrpc


def test_server():
    server = jsonrpc.JSONRPCServer(('localhost', 0))
    server.register_introspection_functions()
    server.register_function(sum)
    server.register_instance(os)


def test_client():
    pass
