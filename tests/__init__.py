#!/usr/bin/env python3
# coding=utf-8
#
# File: EmBCI/tests/__init__.py
# Authors: Hank <hankso1106@gmail.com>
# Create: 2019-02-20 19:06:39

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

Package layout::

    setup.py
    embci/
        __init__.py
        foo.py
        utils/
            bar.py
        ...
    tests/
        __init__.py
        test_foo.py
        utils/
            test_bar.py
        ...
'''

# built-in
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
import os
import time
import types
import unittest
import platform

# requirements.txt: testing: pytest
import pytest

from embci.utils import get_caller_globals
from embci.configs import DIR_TEST


embeddedonly = pytest.mark.skipif(
    platform.platform() not in ['arm', 'aarch64'],
    reason='Only test it on embedded device.'
)


class EmBCITestCase(unittest.TestCase):
    pass


def main():
    pass


def test_with_unittest(*args):
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    for arg in args:
        if isinstance(arg, type) and issubclass(arg, unittest.TestCase):
            suite.addTests(loader.loadTestsFromTestCase(arg))
        elif isinstance(arg, str):
            suite.addTests(loader.loadTestsFromName(arg))
        elif isinstance(arg, types.ModuleType):
            suite.addTests(loader.loadTestsFromModule(arg))
        elif callable(arg):
            class tmp(EmBCITestCase):
                def test_func(self, func=arg):
                    return func()
            suite.addTests(loader.loadTestsFromTestCase(tmp))
        else:
            print('Invalid unittest object: {}'.format(arg))
    try:
        from HtmlTestRunner import HTMLTestRunner
    except ImportError:
        unittest.TextTestRunner().run(suite)
    else:
        func_caller = get_caller_globals(1)['__name__'].split('.')[-1]
        report_file = os.path.join(DIR_TEST, '%s.html' % func_caller)
        with open(report_file, 'w') as f:
            HTMLTestRunner(
                stream=f, title='%s Test Report' % func_caller, verbosity=2,
                description='generated at ' + time.ctime()).run(suite)
        print('Test result at: ' + report_file)


# THE END
