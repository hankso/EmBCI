#!/usr/bin/env python3
# coding=utf-8
#
# File: EmBCI/tests/utils/test_utils.py
# Authors: Hank <hankso1106@gmail.com>
# Create: 2019-02-25 22:34:40

# built-in
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
import os
import time
import logging

# requirements.txt: necessary: six
from six.moves import StringIO

from .. import embeddedonly

from embci.configs import DIR_BASE, DIR_DATA
from embci.utils import (
    get_boolean, get_func_args, load_configs, get_config, mkuserdir,
    LoggerStream, TempLogLevel, Singleton,
    serialize, deserialize, config_logger, duration, validate_filename
)

logmsg = StringIO()
# redirect logging stream to a StringIO so that we can check log messages
logger = config_logger(level=logging.INFO, format='%(message)s', stream=logmsg)


def get_log_msg(f=logmsg):
    msg = f.getvalue(); f.truncate(0); f.seek(0)  # noqa: E702
    return msg.strip()


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
        logger.warning('foo')
        assert get_log_msg() == ''
        logger.error('bar')
        assert get_log_msg() == 'bar'


def test_duration():
    @duration(1.5, '%s.test_duration' % __name__)
    def echo(msg):
        '''this function only can be called every 1.5 second'''
        logger.info(msg)
    # first time
    echo(__file__)
    assert get_log_msg() == __file__
    # too frequently, `echo` will not run
    echo(__file__)
    assert get_log_msg() == ''
    time.sleep(1.5)
    echo(__file__)
    assert get_log_msg() == __file__


def test_mkuserdir(username, clean_userdir):
    @mkuserdir
    def foo(username):
        pass
    clean_userdir()
    foo(username=username)
    assert os.path.exists(os.path.join(DIR_DATA, username))
    clean_userdir()


def test_loggerstream(test_msg='some testing meaasge...'):
    logger.warning(test_msg)
    msg1 = get_log_msg()
    print(test_msg, file=LoggerStream(logger, logging.WARN), end='')
    msg2 = get_log_msg()
    assert msg1 == msg2
    LoggerStream(logger, logging.DEBUG).writelines(['a', 'b', 'c'])
    assert get_log_msg() == ''  # logger.level is logging.INFO


def test_get_func_args():
    assert get_func_args(lambda: None) == ([], ())
    assert get_func_args(lambda x, y=1, verbose=None, *a, **k: None) == (
        ['x', 'y', 'verbose'], (1, None)
    )


def test_load_configs():
    assert load_configs(
        os.path.join(DIR_BASE, 'files/service/embci.conf')
    ).get('Network', {}).get('WEBUI_HOST') == '10.0.0.1'


def test_get_config():
    assert get_config('WEBUI_PORT', type=float) == 80.0


def test_validate_filename():
    assert validate_filename('.<>:"/\\|?*()[]') == '.()[]'
    if os.name == 'posix':
        assert validate_filename('.') == ''
        assert validate_filename('..') == ''
    elif os.name == 'nt':
        assert validate_filename('COM5') == ''
        assert validate_filename('CON') == ''


def test_get_boolean():
    assert (
        get_boolean('True') and
        get_boolean('yes') and
        not get_boolean('No') and
        not get_boolean('off') and
        get_boolean('1')
    )


@embeddedonly
def test_get_host_addr():
    from embci.utils import get_host_addr
    assert get_host_addr() not in ['10.0.0.1', '127.0.0.1']
