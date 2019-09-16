#!/usr/bin/env python3
# coding=utf-8
#
# File: EmBCI/embci/testing.py
# Authors: Hank <hankso1106@gmail.com>
# Create: 2019-03-16 16:03:14

'''__doc__'''

# built-in
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
import re
import os
import sys
import glob
import importlib
import traceback

from six import string_types

from .configs import DIR_TEST, DIR_SRC


def test(modname=None):
    return PytestRunner(modname)() == 0


def list_tests():
    raise


class PytestRunner(object):
    '''
    Load and run tests with ``pytest``. It can:
    - test all tests of specific package ('tests/pkg_name/test_*.py')
    - test all tests of specific module ('tests/test_modname.py')
    - test all tests under DIR_TEST ('tests/*')

    Parameters
    ----------
    mod_or_dir : str or list of str, optional
        Module names or path of tests directory or test files.
        If not provided(defualt), run all tests under `embci.configs.DIR_TEST`.

    Examples
    --------
    >>> test = PytestRunner('embci.utils')
    >>> print(test)
    Test path:
            /home/hank/Git/EmBCI/tests/utils/test_utils.py
    Module path:
            /home/hank/Git/EmBCI/embci/utils
    >>> test()
    pytest result of tests...
    >>> print(PytestRunner('embci.drivers'))
    Test path:
            /home/hank/Git/EmBCI/tests/drivers/test_ili9341.py
            /home/hank/Git/EmBCI/tests/drivers/test_ads1299.py
    Module path:
            /home/hank/Git/EmBCI/embci/drivers
    '''
    def __init__(self, mod_or_dir=None):
        if not mod_or_dir:
            self.testpath = [DIR_TEST]
            self.modpath = [DIR_SRC]
            return
        if isinstance(mod_or_dir, string_types):
            names = [mod_or_dir]
        elif isinstance(mod_or_dir, (tuple, list)):
            names = list(mod_or_dir)
        else:
            try:
                names = [mod_or_dir.__name__]
            except AttributeError:
                raise TypeError('Invalid name type: `{0.__class__.__name__}`'
                                .format(mod_or_dir))
        self.testpath = []
        self.modpath = []
        for name in names:
            testfiles = self.get_testfiles(name)
            if not testfiles:
                continue
            self.testpath.extend(testfiles)
            modpath = self.get_modpath(name)
            if modpath:
                self.modpath.append(modpath)
        self.testpath = list(set(self.testpath))
        self.modpath = list(set(self.modpath))

    def __repr__(self):
        msg = 'Test path:'
        if self.testpath:
            msg += '\n'
            for path in self.testpath:
                msg += '\t%s\n' % path
        else:
            msg += '\t None\n'
        msg += 'Module path:'
        if self.modpath:
            msg += '\n'
            for path in self.modpath:
                msg += '\t%s\n' % path
        else:
            msg += '\t None\n'
        return msg

    def get_testfiles(self, mod_or_dir):
        if os.path.exists(mod_or_dir):  # path name
            path = os.path.abspath(mod_or_dir)
        else:                           # module name
            modname = mod_or_dir.replace('embci.', '').replace('.', '/')
            modname = re.sub(r'^test(_?)', '', modname)
            if not modname:
                return []
            path = os.path.join(DIR_TEST, modname)
        if os.path.isdir(path):
            return glob.glob(os.path.join(path, 'test_*.py'))
        elif os.path.isfile(path):
            return [path]
        else:
            d, f = os.path.split(path)
            return glob.glob(os.path.join(d, 'test_%s.py' % f))

    def get_modpath(self, mod_or_dir):
        if os.path.exists(mod_or_dir):
            return ''
        modname = mod_or_dir
        if modname in sys.modules:
            mod = sys.modules[modname]
        else:
            if not modname.startswith('embci'):
                modname = 'embci.' + modname
            try:
                mod = importlib.import_module(modname)
            except ImportError:
                return ''
        modpath = getattr(mod, '__path__', os.path.dirname(mod.__file__))
        if isinstance(modpath, list):
            modpath = modpath[0]
        return os.path.abspath(modpath)

    def __call__(self, verbose=0, extras=None, coverage=False, doctest=False):
        try:
            import pytest
        except ImportError:
            raise RuntimeError('`pytest` is not installed yet.')

        if not self.testpath:
            print('No tests found.')
            return 0

        args = ['-l']
        if verbose:
            args += ['-' + 'v' * verbose]
        if coverage:
            args += ['--cov=' + _ for _ in self.modpath]
        if extras is not None:
            args += list(extras)
        args += ['--pyargs'] + self.testpath

        try:
            return pytest.main(args)
        except SystemExit as e:
            return e.code
        except Exception:
            traceback.print_exc()
        return 0
