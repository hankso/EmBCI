#!/usr/bin/env python
# coding=utf-8
#
# File: EmBCI/tests/test_utils.py
# Author: Hankso
# Webpage: https://github.com/hankso
# Time: Mon 25 Feb 2019 22:34:40 CST
from __future__ import print_function
import os
import logging

from . import embeddedonly

from embci.configs import BASEDIR, DATADIR
from embci.utils import (
    get_boolean, get_label_dict, get_func_args, load_configs, mkuserdir,
    LoggerStream, TempStream, TempLogLevel, Singleton,
    serialize, deserialize, create_logger
)

logger = create_logger()


def test_serialization():
    def bar():
        '''
        this function will be `embci.utils.bar` after
        deserialization with `method` set to `json`.
        '''
        pass
    assert deserialize(serialize(bar)).__doc__ == bar.__doc__
    assert deserialize(serialize(bar, 'json'), 'json').__doc__ == bar.__doc__


def test_singleton():
    class Foo(object):
        __metaclass__ = Singleton
    assert Foo() == Foo()


def test_temploglevel():
    with TempLogLevel(logging.ERROR):
        with TempStream('stdout') as stream:
            logger.warn('foo')
        assert not stream.stdout
        with TempStream('stdout') as stream:
            logger.error('bar')
        assert stream.stdout


def test_duration():
    pass


def test_mkuserdir(username, clean_user_dir):
    userdir = os.path.join(DATADIR, username)

    @mkuserdir
    def foo(username):
        pass
    foo(username)
    assert os.path.exists(userdir)
    os.rmdir(userdir)


def test_loggerstream(tmpdir, test_msg='some testing meaasge...'):
    with TempStream('stdout') as msg1:
        logger.warn(test_msg)
    with TempStream('stdout') as msg2:
        print(test_msg, file=LoggerStream(logger, logging.WARN), end='')
    assert msg1.stdout == msg2['stdout']

    tmpfile = tmpdir.join('logfile')
    with TempStream(stdout=str(tmpfile)):
        LoggerStream(logger, logging.DEBUG).writelines(['a', 'b', 'c'])
    assert tmpfile.read() == ''
    tmpfile.remove()


def test_get_func_args():
    assert get_func_args(lambda: None) == ([], ())
    assert get_func_args(lambda x, y=1, verbose=None, *a, **k: None) == (
        ['x', 'y', 'verbose'], (1, None)
    )


def test_load_configs():
    assert load_configs(
        os.path.join(BASEDIR, 'files/service/embci.conf')
    ).get('Path', {}).get('BASEDIR') == '/usr/share/embci'


def test_get_boolean():
    assert (
        get_boolean('True') and
        get_boolean('yes') and
        not get_boolean('No') and
        not get_boolean('off') and
        get_boolean('1')
    )


def test_get_label_dict(clean_user_dir, username):
    label_dict, summary = get_label_dict(username)
    assert label_dict == {}
    # DO NOT test outputs, because it may be changed in the future.
    #  assert 'There are 0 actions with 0 data recorded' in summary


@embeddedonly
def test_get_self_ip_addr():
    from embci.utils import get_self_ip_addr
    assert get_self_ip_addr() not in ['10.0.0.1', '127.0.0.1']
