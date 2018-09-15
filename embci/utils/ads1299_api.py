#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Wed Apr  4 01:37:15 2018

@author: hank
"""
# built-in
import os
import time
import struct
import select
import unittest
import multiprocessing

# pip install numpy, spidev, gpio4
import spidev
import numpy as np
from gpio4 import SysfsGPIO

from ..common import time_stamp
from ..utils.HTMLTestRunner import HTMLTestRunner
from embci import BASEDIR

__dir__ = os.path.dirname(os.path.abspath(__file__))
__filename__ = os.path.basename(__file__)


# ADS1299 Pin mapping
# PIN_PWRDN       = 2 # pin PA02
# PIN_START       = 3 # pin PA03
# PIN_DRDY        = 6 # pin PA06 only for ads1299 direct connection
PIN_DRDY        = 7 # pin PA07 only for esp32 spi buffer
# PIN_RESET       = 7 # pin PA07
# ADS1299 Registers
REG_CONFIG1     = 0x01
REG_CONFIG2     = 0x02
REG_CONFIG3     = 0x03
REG_CHnSET_BASE = 0x05
REG_BIAS_SENSP  = 0x0D
REG_BIAS_SENSN  = 0x0E
REG_LOFF_SENSP  = 0x0F
REG_MISC        = 0x15
# ADS1299 Commands
WAKEUP          = 0x02
STANDBY         = 0x04
RESET           = 0x06
START           = 0x08
STOP            = 0x0A
RDATAC          = 0x10
SDATAC          = 0x11
RDATA           = 0x12
RREG            = 0x20
WREG            = 0x40
# ADS1299 Sample data rate dict, set REG_CONFIG1 to this value
SAMPLE_RATE = {
    250:        0b110,
    500:        0b101,
    1000:       0b100,
    2000:       0b011,
    4000:       0b010,
    8000:       0b001,
    16000:      0b000,
}
# ADS1299 channel data input sources
INPUT_SOURCE = {
    'normal':   0b000,
    'shorted':  0b001,
    'MVDD':     0b011,
    'temper':   0b100,
    'test':     0b101,
}
# OrangePi supported spidev max_speed_hz: 100MHz divided by 1, 2, 3, ... n
SUGGESTED_MSH = np.int32([
    100e6, 50e6, 33.33e6, 25e6, 20e6, 12.5e6, 11.11e6, 10e6,
    5e6, 4e6, 3.33e6, 3.03e6, 2.5e6, 2e6, 1e6,
    8e5, 5e5, 4e5, 3.33e5, 2.5e5, 2e5, 1e5])



class ADS1299_API(spidev.SpiDev):
    '''
    There is a module named RaspberryPiADS1299 to communicate will ADS1299
    within Python through spidev. But it is not well written. Actually it's
    un-pythonic at all. Hard to understand, hard to use.
    So I rewrite it with spidev and SysfsGPIO(Unlike RPi.GPIO, SysfsGPIO
    works on both RaspberryPI, BananaPi, OrangePi and any hardware running
    Linux, theoretically).

    Methods
    -------
        open: open device
        start: start Read DATA Continuously mode, you must call open first
        close: close device
        read_raw: return raw 8-channel * 3 = 24 bytes data
        read: return parsed np.ndarray data with shape of (8,)
        write: transfer bytes list to ads1299
        write_register: write one register with index and value
        write_registers: write series registers with start index and values
        set_input_source: choose one source from available:
            normal: normal electrode input
            shorted: input shorted, to measure noise
            MVDD: supply measurement
            temper: temperature sensor
            test: test signal(internal or external generated test square wave)
        do_measure_impedance: property, set it to True or False:
            >>> ads = ADS1299_API()
            >>> ads.open((0, 0))
            >>> ads.do_measure_impedance = True
            >>> ads.read() # this will return impedance value of each channel
        do_enable_bias: property, set it to True or False

    Attention
    ---------
    In spidev, SpiDev().mode indicate mode of device that it connect to(avr/ads1299),
    NOT the mode of device where python code run(PC/Raspi/esp32/etc.)

    So, ads1299 accept data from DIN at raising edge and transfer data out from DOUT
    to OrangePi as falling edge. set mode to 0b10 (CPOL=1 & CPHA=0)

    Notes
    -----
    Because ADS1299_API inherits spidev.SpiDev, methods list of instance may be
    pretty confusing, you can compare them by following table:
        ADS1299_API                       | spidev.SpiDev
        ----------------------------------+-------------------------------------
        open(device, max_speed_hz)        | open(bus, device)
        start(sample_rate)                | max_speed_hz = 1e6
        close()                           | close()
        read()                            | readbytes(len)
        write(byte_array)                 | writebytes(byte_array)
        read_register(reg)                | bits_per_word = 8
        read_registers(reg, num)          | mode = 0 # number in [0, 1, 2, 3]
        write_register(reg, byte)         | xfer(byte_array)
        write_registers(reg, byte_array)  | xfer2(byte_array)
        set_sample_rate(rate)             | cshigh = True|False
        set_input_source(src)             | threewire = True|False
        do_enable_bias = True|False       | loop = True|False
        do_measure_impedance = True|False | lsbfirst = True|False
                                          | fileno
    '''
    def __init__(self, scale=4.5/24/2**24):
        self.scale = float(scale)
        self._DRDY = SysfsGPIO(PIN_DRDY)
        # self._PWRDN = SysfsGPIO(PIN_PWRDN)
        # self._RESET = SysfsGPIO(PIN_RESET)
        # self._START = SysfsGPIO(PIN_START)

        self._lock = multiprocessing.Lock()
        self._opened = False
        self._started = False
        self._enable_bias = False
        self._measure_impedance = False

    def open(self, dev, max_speed_hz=12500000):
        '''
        connect to user space SPI interface `/dev/spidev*.*`
        param `dev` must be tuple/list, e.g. (1, 0) means `/dev/spidev1.0`
        '''
        assert not self._opened, 'already used spidev{}.{}'.format(*self._dev)
        super(ADS1299_API, self).open(dev[0], dev[1])
        msh = int(max_speed_hz)
        if msh not in SUGGESTED_MSH:
            msh = SUGGESTED_MSH[(SUGGESTED_MSH - max_speed_hz).argmin()]
            print('[ADS1299 API] max speed of spidev set to %dHz' % msh)
        self.max_speed_hz = msh
        self.mode = 2
        self._dev = dev
        # self._START.export = True
        # self._START.direction = 'out'
        # self._START.value = 0
        self._DRDY.export = True
        self._DRDY.direction = 'in'

        # BUG: fixed
        # a SysfsGPIO must be read at least once first
        # to make it can be polled then
        self._DRDY.value

        self._DRDY.edge = 'falling'
        self._epoll = select.epoll()
        self._epoll.register(self._DRDY, select.EPOLLET | select.EPOLLPRI)
        self._opened = True

    def start(self, sample_rate):
        '''
        Before device power up, all digital and analog inputs must be low.
        At the time of power up, keep all of these signals low until the
        power supplies have stabilized.
        '''
        assert self._opened, 'you need to open a spi device first'
        if self._started:
            return

        #
        # power up
        #

        # self._PWRDN.value=1 # we pull it up to high
        # self._RESET.value=1
        self.write(RESET)

        # wait for tPOR(2**18*666.0/1e9 = 0.1746) and tBG(assume 0.83)
        time.sleep(0.17+0.83)

        # device wakes up in RDATAC mode, send SDATAC
        # command so registers can be written
        self.write(SDATAC)

        #
        # configure_registers_before_streaming
        #

        # common setting
        self.write_register(REG_CONFIG1, 0b10010000 | SAMPLE_RATE[sample_rate])
        self.write_register(REG_CONFIG2, 0b11010000)
        self.write_register(REG_CONFIG3, 0b11100000)
        self.write_register(REG_MISC, 0b00100000)
        self.write_registers(REG_CHnSET_BASE, [0b01100000] * 8)

        # self._START.value = 1
        self.write(START)
        time.sleep(1)

        #
        # start streaming data
        #

        self.write(RDATAC)
        self._started = True

    def close(self):
        if self._opened:
            self.write(SDATAC)
            self.write(STOP)
            super(ADS1299_API, self).close()
            self._epoll.unregister(self._DRDY)
            self._DRDY.export = False
            # self._START.export = False
            # self._PWRDN.export = False
            # self._RESET.export = False

    def set_sample_rate(self, rate):
        assert self._started
        if rate not in SAMPLE_RATE:
            print('[ADS1299 API] choose one from supported rate!')
            print(' | '.join(SAMPLE_RATE.keys()))
            return
        rate = SAMPLE_RATE[rate]
        self.write(SDATAC)
        v = self.read_register(REG_CONFIG1)
        self.write_register(REG_CONFIG1, v & ~0b111 | rate)
        self.write(RDATAC)
        return rate

    def set_input_source(self, src):
        assert self._started
        if src not in INPUT_SOURCE:
            print('[ADS1299 API] choose one from supported source!')
            print(' | '.join(INPUT_SOURCE.keys()))
            return
        src = INPUT_SOURCE[src]
        self.write(SDATAC)
        vs = self.read_registers(REG_CHnSET_BASE, 8)
        vs = [(v & ~0b111 | src) for v in vs]
        self.write_registers(REG_CHnSET_BASE, vs)
        self.write(RDATAC)

    @property
    def enable_bias(self):
        return self._enable_bias

    @enable_bias.setter
    def enable_bias(self, boolean):
        assert self._started
        self.write(SDATAC)
        if boolean is True:
            self.write_register(REG_BIAS_SENSP, 0b11111111)
            self.write_register(REG_BIAS_SENSN, 0b11111111)
            self.write_register(REG_CONFIG3, 0b11101100)
        elif boolean is False:
            self.write_register(REG_BIAS_SENSP, 0b00000000)
            self.write_register(REG_BIAS_SENSN, 0b00000000)
            self.write_register(REG_CONFIG3, 0b11100000)
        self._enable_bias = boolean
        self.write(RDATAC)

    @property
    def measure_impedance(self):
        return self._measure_impedance

    @measure_impedance.setter
    def measure_impedance(self, boolean):
        assert self._started
        self.write(SDATAC)
        vs = self.read_registers(REG_CHnSET_BASE, 8)
        vs = [v & ~(0b111 << 4) for v in vs]
        if boolean is True:
            self.write_register(REG_LOFF_SENSP, 0b11111111)
            self.write_registers(REG_CHnSET_BASE, vs)
        elif boolean is False:
            self.write_register(REG_LOFF_SENSP, 0b00000000)
            self.write_registers(REG_CHnSET_BASE, [v | 0b110 << 4 for v in vs])
        self._measure_impedance = boolean
        self.write(RDATAC)

    def read(self, *args, **kwargs):
        '''
        Read chunk bytes from ADS1299 and decode them into `float32` number
        '''
        assert self._started
        # ======================================================================
        # method No.1
        # ======================================================================
        # while (time.time() - self.last_time) < 1.0 / self.sample_rate:
        #     pass
        # self.last_time = time.time()

        # ======================================================================
        # method No.2
        # ======================================================================
        # while self._DRDY.value == 1:
        #     pass

        # ======================================================================
        # mwthod No.3
        # ======================================================================
        self._epoll.poll()  # this will block until interrupt on DRDY detected

        num = self.write([0x00] * 27)[3:]
        byte = ''
        for i in range(8):
            # tmp = chr(num[3*i+2]) + chr(num[3*i+1]) + chr(num[3*i]) # use time: 4.3us
            tmp = struct.pack('3B', num[3*i+2], num[3*i+1], num[3*i]) # use time: 1.3us
            byte += tmp + ('\xff' if num[3*i] > 127 else '\x00')
        return np.frombuffer(byte, np.int32) * self.scale

    def write(self, byte_array):
        '''
        Write byte list to ADS1299 through SPI and return value list
        '''
        if not isinstance(byte_array, list):
            byte_array = [byte_array]
        with self._lock:
            value = self.xfer2(byte_array)
        return value

    def write_register(self, reg, byte):
        '''Write register `reg` with value `byte`'''
        self.write([reg | WREG, 0x00, byte])

    def write_registers(self, reg, byte_array):
        '''Write registers start from `reg` with values `byte_array`'''
        self.write([reg | WREG, len(byte_array) - 1] + byte_array)

    def read_register(self, reg):
        '''Read single register at `reg`'''
        self.write(SDATAC)
        value = self.write([RREG | reg, 0x00, 0x00])[2]
        self.write(RDATAC)
        return value

    def read_registers(self, reg, num):
        '''Read `num` registers start from `reg`'''
        self.write(SDATAC)
        value = self.write([RREG | reg, num - 1] + [0] * num)[2:]
        self.write(RDATAC)
        return value



# ESP32_SPI_BUFFER Commands
# same as ADS1299
RESET           = 0x06
START           = 0x08
STOP            = 0x0A
RREG            = 0x20
WREG            = 0x40
# virtual registers, only used between ARM and ESP32
REG_SR          = 0x50  # sample_rate
REG_IS          = 0x52  # input_source
REG_BIAS        = 0x54  # enable_bias
REG_INPEDANCE   = 0x56  # measure_impedance


class ESP32_API(ADS1299_API):
    '''
    Because we only use ESP32 as SPI buffer, its SPI interface
    is implemented similar with ADS1299.
    So define this API class in submodule `ads1299_api.py`
    '''
    def __init__(self, n_batch=32, scale=4.5/24/2**24):
        self.n_batch = n_batch

        # we send `nBatchs * 4Bytes * 8chs` 0x00
        # first 4Bytes is reserved for command to control ESP32
        # [cmd cmd cmd cmd 0x00 0x00 0x00 0x00 ... 0x00]
        self._tosend = 4 * 8 * self.n_batch * [0x00]
        self._data_format = '%dB' % len(self._tosend)
        self._cmd_queue = multiprocessing.Queue()
        self._data_buffer = []
        self._last_time = time.time()

        super(ESP32_API, self).__init__(scale)

    def start(self, sample_rate):
        '''
        Before device power up, all digital and analog inputs must be low.
        At the time of power up, keep all of these signals low until the
        power supplies have stabilized.
        '''
        assert self._opened, 'you need to open a spi device first'
        if self._started:
            return
        self._started = True
        self.set_sample_rate(sample_rate)

    def close(self):
        self._cmd_queue.close()
        self._data_buffer = []
        if self._opened:
            super(ADS1299_API, self).close()
            self._epoll.unregister(self._DRDY)
            self._DRDY.export = False

    def read(self, *args, **kwargs):
        assert self._started

        if not self._cmd_queue.empty():
            cmd = self._cmd_queue.get()
            self.write(cmd + self._tosend[len(cmd):])
            self._data_buffer = []
            return np.zeros(8, np.float32)

        if not len(self._data_buffer):
            # spidev lib is written in C language, where value of list will be
            # changed in-situ. Because we want self._tosend keep as [0x00] *n,
            # self._tosend cannot be used directly in self.xfer[2]. Here we pass
            # a new list same as self._tosend created by slicing itself.
            data = struct.pack(self._data_format, *self.write(self._tosend[:]))
            data = np.frombuffer(data, np.int32).reshape(self.n_batch, 8)
            self._data_buffer = list(data * self.scale)

        while (time.time() - self._last_time) < (1.0 / self._sample_rate):
            pass
        self._last_time = time.time()
        return self._data_buffer.pop(0)

    def write(self, byte_array):
        self._epoll.poll()
        return super(ESP32_API, self).write(byte_array)

    def write_register(self, reg, byte):
        '''Write register `reg` with value `byte`'''
        self._cmd_queue.put([WREG, reg, byte])

    def write_registers(self, reg, byte_array):
        '''Write registers start from `reg` with values `byte_array`'''
        self._cmd_queue.put([WREG, reg] + list(byte_array))

    def read_register(self, reg):
        '''Read single register at `reg`'''
        self._cmd_queue.put([RREG, reg])

    def read_registers(self, reg, num):
        '''Read `num` registers start from `reg`'''
        self._cmd_queue.put([RREG, reg] + list(range(num)))

    def set_sample_rate(self, rate):
        assert self._started
        if rate not in SAMPLE_RATE:
            print('[ESP32 API] choose one from supported rate!')
            print(' | '.join(SAMPLE_RATE.keys()))
            return
        self.write_register(REG_SR, SAMPLE_RATE[rate])
        return rate

    def set_input_source(self, src):
        assert self._started
        if src not in INPUT_SOURCE:
            print('[ESP32 API] choose one from supported source!')
            print(' | '.join(INPUT_SOURCE.keys()))
            return
        self.write_register(REG_IS, INPUT_SOURCE[src])

    @property
    def enable_bias(self):
        return self._enable_bias

    @enable_bias.setter
    def enable_bias(self, boolean):
        assert self._started
        self.write_register(REG_BIAS, int(boolean))
        self._enable_bias = boolean

    @property
    def measure_impedance(self):
        return self._measure_impedance

    @measure_impedance.setter
    def measure_impedance(self, boolean):
        assert self._started
        self.write_register(REG_INPEDANCE, int(boolean))
        self._measure_impedance = boolean


#
# testing
#


class _testADS(unittest.TestCase):
    def setUp(self):
        '''Initialization before test.'''
        self._ads = ADS1299_API()
        self._ads.open((0, 0))  # /dev/spidev0.0
        self._ads.start(sample_rate=250)

    def tearDown(self):
        '''Close API before exit'''
        self._ads.close()

    def test_1_read_data(self):
        '''Read group data'''
        print(self._ads.read(10))

    def test_2_read_register(self):
        '''Read chip ID from register 0x00'''
        ID = self._ads.read_register(0x00)
        print('ID: ' + bin(ID))
        self.assertEqual(0b00011110, ID & 0x1F)

    def test_3_test_signal(self):
        '''Set input source to internal generated test signal'''
        self._ads.set_input_source('test')
        print('Test signal:')
        for i in range(10):
            print('{} {}'.format(time.time(), self._ads.read()))
            time.sleep(0.5)
        self._ads.set_input_source('normal')

    def test_4_do_enable_bias(self):
        '''Read signal after bias enabled'''
        tmp = self._ads.do_enable_bias
        self._ads.do_enable_bias = True
        print(self._ads.read())
        self._ads.do_enable_bias = tmp

    def test_5_do_measure_impedance(self):
        '''Set measure source to impedance'''
        tmp = self._ads.do_measure_impedance
        self._ads.do_measure_impedance = True
        print(self._ads.read())
        self._ads.do_measure_impedance = tmp


class _testESP(_testADS):
    def setUp(self):
        from common import Serial_ESP32_commander
        self._c = Serial_ESP32_commander(baud=115200)
        self._c.start('/dev/ttyS1')
        self._esp = ESP32_API(self._c)
        self._esp.open((0, 1))  # /dev/spidev0.1
        self._esp.start(sample_rate=500)
        self._ads = self._esp

    def tearDown(self):
        self._c.close()
        self._esp.close()


if __name__ == '__main__':
    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(_testADS))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(_testESP))
    filename = os.path.join(BASEDIR, 'files/test/test-%s.html' % __file__)
    with open(filename, 'w') as f:
        HTMLTestRunner(stream=f,
                       title='%s Test Report' % __name__,
                       description='generated at ' + time_stamp(),
                       verbosity=2).run(suite)
