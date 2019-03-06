#!/usr/bin/env python
# coding=utf-8
#
# File: EmBCI/tests/__init__.py
# Author: Hankso
# Webpage: https://github.com/hankso
# Time: Wed 20 Feb 2019 19:06:39 CST

'''
EmBCI tests

Support:
    A. cd /path/to/EmBCI && pytest
    B. cd /path/to/EmBCI && python setup.py test

Keeping tests separate from source codes has following benefits:
    1. Tests can run on an installed version after package is installed
    2. Tests can run on editable installed version after `pip install -e`
    3. Tests can run on local version without installing package. `pytest`
       will add current directory into `sys.path`

layout:
    setup.py
    embci/
        ...
    tests/
        __init__.py
        test_foo.py
        ...
'''

import os
import time
import types
import unittest
import platform

import pytest

from embci.configs import TESTDIR


embeddedonly = pytest.mark.skipif(
    platform.platform() not in ['arm', 'aarch64'],
    reason='Only test it on embedded device.'
)


class EmBCITestCase(unittest.TestCase):
    pass


def main():
    pass


def run_test_with_unittest(*args):
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    for arg in args:
        if isinstance(arg, type) and issubclass(arg, unittest.TestCase):
            suite.addTests(loader.loadTestsFromTestCase(arg))
        if isinstance(arg, str):
            suite.addTests(loader.loadTestsFromName(arg))
        if isinstance(arg, types.ModuleType):
            suite.addTests(loader.loadTestsFromModule(arg))
    try:
        from HtmlTestRunner import HTMLTestRunner
    except ImportError:
        suite.run()
    else:
        func_caller = os.path.splitext(globals()['__name__'])[-1].strip('.')
        # caller_path = os.path.dirname(os.path.abspath(globals()['__file__']))
        report_file = os.path.join(TESTDIR, '%s.html' % func_caller)
        with open(report_file, 'w') as f:
            HTMLTestRunner(
                stream=f, title='%s Test Report' % func_caller, verbosity=2,
                description='generated at ' + time.ctime()).run(suite)
        print('Test result at: ' + report_file)


# THE END
