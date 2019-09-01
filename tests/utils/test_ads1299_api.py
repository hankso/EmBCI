#!/usr/bin/env python
# coding=utf-8
#
# File: EmBCI/tests/utils/test_ads1299.py
# Author: Hankso
# Webpage: https://github.com/hankso
# Time: Wed 06 Feb 2019 01:42:11 CST

import time

from embci.utils.ads1299_api import ADS1299_API
from embci.utils.esp32_api import ESP32_API
from .. import EmBCITestCase, embeddedonly


@embeddedonly
class TestADS(EmBCITestCase):
    API = ADS1299_API
    DEV = (0, 0)  # /dev/spidev0.0
    FS = 250

    def setUp(self):
        '''Initialization before test.'''
        self._api = self.API()
        self._api.open(self.DEV)
        self._api.start(sample_rate=self.FS)

    def tearDown(self):
        '''Close API before exit'''
        self._api.close()

    def test_1_read_data(self):
        '''Read group data'''
        print(self._api.read(10))

    def test_2_read_register(self):
        '''Read chip ID from register 0x00'''
        ID = self._api.read_register(0x00)
        print('ID: ' + bin(ID))
        self.assertEqual(0b00011110, ID & 0x1F)

    def test_3_test_signal(self):
        '''Set input source to internal generated test signal'''
        self._api.set_input_source('test')
        print('Test signal:')
        for i in range(10):
            print('{} {}'.format(time.time(), self._api.read()))
            time.sleep(0.5)
        self._api.set_input_source('normal')

    def test_4_enable_bias(self):
        '''Read signal after bias enabled'''
        tmp, self._api.enable_bias = self._ads.enable_bias, True
        print(self._api.read())
        self._api.enable_bias = tmp

    def test_5_measure_impedance(self):
        '''Set measure source to impedance'''
        tmp, self._api.measure_impedance = self._ads.measure_impedance, True
        print(self._api.read())
        self._api.measure_impedance = tmp


@embeddedonly
class TestESP(TestADS):
    API = ESP32_API
    DEV = (1, 0)  # /dev/spidev1.0
    FS = 500


if __name__ == '__main__':
    from .. import test_with_unittest
    test_with_unittest(TestADS, TestESP)
