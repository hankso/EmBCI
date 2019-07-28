#!/usr/bin/env python
# coding=utf-8
#
# File: EmBCI/embci/tests/test_io.py
# Author: Hankso
# Webpage: https://github.com/hankso
# Time: Wed 06 Feb 2019 01:26:32 CST

from __future__ import print_function
import os
import time
import warnings
import threading

# requirements.txt: testing: pytest
# requirements.txt: drivers: pyserial
import pytest
import serial
import pylsl


# =============================================================================
# functions
#
from embci.configs import DATADIR
from embci.io import save_data, load_data, create_data_dict, get_label_dict


def test_save_data(username, random_data, clean_userdir):
    clean_userdir()
    data_dict = create_data_dict(random_data, 'testing', 500)
    assert 'sample_rate' in data_dict
    save_data(username, data_dict, suffix='.mat')
    assert os.path.exists(os.path.join(DATADIR, username, 'testing-1.mat'))
    assert os.path.exists(os.path.join(DATADIR, username, 'testing-2.mat'))


def test_load_data(username, random_data, clean_userdir):
    data, label = load_data(username)
    assert 'testing' == label[0] == label[1]
    assert (random_data == data).all()
    clean_userdir()


def test_get_label_dict(clean_userdir, username):
    label_dict, summary = get_label_dict(username)
    assert label_dict == {}
    # DO NOT test outputs, because it may be changed in the future.
    #  assert 'There are 0 actions with 0 data recorded' in summary
    clean_userdir()


# =============================================================================
# Readers
#
from embci.io import FakeDataGenerator as Reader
from embci.utils import find_pylsl_outlets


@pytest.fixture(scope='module')
def reader():
    reader = Reader(
        sample_rate=500, sample_time=2, num_channel=8, send_to_pylsl=True)
    reader.start()
    yield reader
    reader.close()


def test_reader_status(reader):
    assert reader.status == 'started'
    assert reader.is_streaming()


def test_stream_control(reader):
    reader.pause()
    assert reader.status == 'paused'
    assert reader.is_streaming() is False
    reader.resume()
    assert reader.status == 'resumed'
    assert reader.is_streaming() is True


def test_reader_data(reader):
    assert reader.data_channel.shape == (8,)
    assert reader.data_frame.shape == (8, 1000)


def test_reader_pylsl(reader):
    info = find_pylsl_outlets(source_id=reader.name)
    assert isinstance(info, pylsl.StreamInfo)


def test_set_sample_rate(reader):
    reader.pause()
    assert reader.set_sample_rate(250)
    reader.restart()
    time.sleep(3)  # reader need some time to stablize the sample_rate
    assert abs(reader.realtime_samplerate - 250) < 80


# =============================================================================
# Commanders
#
from embci.io import SerialCommander
from embci.utils import virtual_serial


@pytest.fixture(scope='module')
def obj(request):
    flag_stop, port1, port2 = virtual_serial(verbose=False)
    cmder = SerialCommander({
        '_desc': 'command dict used for testing commander',
        'action1': ('asdf', 0),
        'action3': ('this is action3', 1),
        'nodelay': ('nodelay', ),
    })
    cmder.start(port1, 115200)
    slave = serial.Serial(port2, 115200)

    request.addfinalizer(flag_stop.set)
    request.addfinalizer(cmder.close)
    request.addfinalizer(slave.close)

    class objs:
        serial = slave
        commander = cmder
    return objs


def test_get_command(obj):
    with warnings.catch_warnings():
        assert obj.commander.get_command('foo') is None


def test_send_command(obj):
    assert obj.commander.send('action1') == 'asdf'
    time.sleep(0.5)
    assert obj.serial.read_all() == 'asdf'


def test_send_wait(obj):
    '''Method `send` will acquire lock and wait for specific seconds.'''
    # send command twice
    threading.Thread(
        target=obj.commander.send, args=('action3',)).start()
    threading.Thread(
        target=obj.commander.send, args=('action3',)).start()
    # receive first command
    time.sleep(0.5)
    assert obj.serial.read_all() == 'this is action3'
    # receive nothing, commander is still waiting
    assert obj.serial.read_all() == ''
    time.sleep(1)
    # receive second command
    assert obj.serial.read_all() == 'this is action3'


def test_write_method(obj):
    try:
        print('nodelay', file=obj.commander)
    except Exception as e:
        assert isinstance(e, IndexError)


# TODO: test Socket***Reader, Socket***Server
# TODO: test PylslCommader, PylslReader
