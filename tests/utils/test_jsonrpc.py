#!/usr/bin/env python
# coding=utf-8
#
# File: EmBCI/tests/utils/test_jsonrpc.py
# Author: Hankso
# Webpage: https://github.com/hankso
# Time: Sun 28 Jul 2019 14:53:18 CST

import embci.utils.jsonrpc as jsonrpc

server = jsonrpc.JSONRPCServer(('localhost', 8080))
server.register_introspection_functions()
