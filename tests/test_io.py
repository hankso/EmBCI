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

# requirements.txt: data-processing: numpy
# requirements.txt: testing: pytest
# requirements.txt: driver: pyserial
import numpy as np
import pytest
import serial
import pylsl


# =============================================================================
# functions
#
from embci.configs import DATADIR
from embci.io import save_data, load_data, create_data_dict


@pytest.fixture(scope='module')
def random_data(username, request):
    request.addfinalizer(lambda clean_user_dir: None)
    return np.random.randn(2, 8, 1024)


@pytest.mark.usefixtures('clean_user_dir')
def test_save_data(username, random_data):
    data_dict = create_data_dict(random_data, 'testing', 500)
    assert 'sample_rate' in data_dict
    save_data(username, data_dict, suffix='.mat')
    assert os.path.exists(os.path.join(DATADIR, username, 'testing-1.mat'))
    assert os.path.exists(os.path.join(DATADIR, username, 'testing-2.mat'))


def test_load_data(username, random_data):
    data, label = load_data(username)
    assert 'testing' == label[0] == label[1]
    assert (random_data == data).all()


# =============================================================================
# Readers
#
from embci.io import FakeDataGenerator as Reader
from embci.utils import find_pylsl_outlets


@pytest.fixture(scope='module')
def reader():
    reader = Reader(
        sample_rate=500, sample_time=2, n_channel=8, send_to_pylsl=True)
    reader.start()
    yield reader
    reader.close()


def test_reader_status(reader):
    assert reader.status == 'started'
    assert reader.is_streaming
    assert abs(reader.realtime_samplerate - 500) < 50


def test_stream_control(reader):
    reader.pause()
    assert reader.status == 'paused'
    assert reader.is_streaming is False
    reader.resume()
    assert reader.status == 'resumed'
    assert reader.is_streaming is True


def test_reader_data(reader):
    assert reader.data_channel.shape == (8, )
    assert reader.data_frame.shape == (8, 1000)


def test_reader_pylsl(reader):
    info = find_pylsl_outlets(source_id=reader.name)
    assert isinstance(info, pylsl.StreamInfo)


def test_set_sample_rate(reader):
    assert reader.set_sample_rate(250)
    reader.restart()
    assert abs(reader.realtime_samplerate - 250) < 50


# =============================================================================
# Commanders
#
from . import EmBCITestCase
from embci.io import SerialCommander
from embci.utils import virtual_serial


#  @pytest.fixture
#  def self(scope='module'):
#      flag_stop, port1, port2 = virtual_serial(verbose=False)
#      commander = SerialCommander({
#          '_desc': 'command dict used for testing commander',
#          'action1': ('action-{}', 0),
#          'action2': ('action-{}{}', 0),
#          'action3': ('this is action3', 1),
#          'nodelay': ('nodelay', ),
#      })
#      commander.start(port1, 115200)
#      slave = serial.Serial(port2, 115200)
#
#      class objs:
#          serial = slave,
#          commander = commander
#      yield objs
#
#      slave.close()
#      commander.close()
#      flag_stop.set()


class TestSerialCommander(EmBCITestCase):
    def setUp(self):
        self.flag_stop, port1, port2 = virtual_serial(verbose=False)
        self.commander = SerialCommander({
            '_desc': 'command dict used for testing commander',
            'action1': ('asdf', 0),
            'action3': ('this is action3', 1),
            'nodelay': ('nodelay', ),
        })
        self.commander.start(port1, 115200)
        self.serial = serial.Serial(port2, 115200)

    def tearDown(self):
        self.serial.close()
        self.commander.close()
        self.flag_stop.set()

    def test_get_command(self):
        with warnings.catch_warnings():
            self.assertEqual(self.commander.get_command('foo'), None)

    def test_send_command(self):
        self.assertEqual('asdf', self.commander.send('action1'))
        time.sleep(0.5)
        self.assertEqual(self.serial.read_all(), 'asdf')

    def test_send_wait(self):
        '''Method `send` will acquire lock and wait for specific seconds.'''
        # send command twice
        threading.Thread(
            target=self.commander.send, args=('action3',)).start()
        threading.Thread(
            target=self.commander.send, args=('action3',)).start()
        # receive first command
        time.sleep(0.5)
        self.assertEqual(self.serial.read_all(), 'this is action3')
        # receive nothing, commander is still waiting
        self.assertEqual(self.serial.read_all(), '')
        time.sleep(1)
        # receive second command
        self.assertEqual(self.serial.read_all(), 'this is action3')

    def test_write_method(self):
        self.assertRaises(
            IndexError, lambda: print('nodelay', file=self.commander))


# TODO: test Socket***Reader, Socket***Server
# TODO: test PylslCommader, PylslReader
