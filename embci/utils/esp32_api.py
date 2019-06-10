#!/usr/bin/env python
# coding=utf-8
#
# File: EmBCI/embci/utils/esp32_api.py
# Author: Hankso
# Webpage: https://github.com/hankso
# Time: Mon 18 Feb 2019 15:25:56 CST

'''
ESP32 ADS1299 SPI Buffer API
'''

# built-in
import time
import struct
from multiprocessing import Queue

# requirements.txt: data-processing: numpy
import numpy as np

from .ads1299_api import ADS1299_API, ensure_start, SAMPLE_RATE, INPUT_SOURCES

# =============================================================================
# ESP32 Pin mapping
#
PIN_DRDY = 6  # pin PA06 for esp32 on orangepi zero plus 2

# =============================================================================
# ESP32 Commands: only used on EmBCI hardware
#
RESET    = 0x06  # noqa: E221
START    = 0x08  # noqa: E221
STOP     = 0x0A  # noqa: E221
RREG     = 0x20  # noqa: E221
WREG     = 0x40  # noqa: E221

# =============================================================================
# ESP32 Virtual Registers: only used with ESP32 firmware support
#
REG_SR   = 0x50  # noqa: E221  sample_rate
REG_IS   = 0x52  # noqa: E221  input_source
REG_BIAS = 0x54  # noqa: E221  enable_bias
REG_IMP  = 0x56  # noqa: E221  measure_impedance
REG_CH   = 0x58  # noqa: E221  enable / disable channel


class ESP32_API(ADS1299_API):
    '''
    Communicator to EmBCI Hardware on-shield ESP32 chip. Drop in replacement
    of ADS1299_API. Get source file and compiled firmware for ESP32 at
    https://github.com/hankso/EmBCI#Hardware.

    See Also
    --------
    embci.utils.ads1299_api.ADS1299_API
    '''
    def __init__(self, n_batch=32, scale=4.5/24/2**24, *a, **k):
        self.n_batch = n_batch

        # send `nBatchs * 4Bytes * 8chs` 0x00
        # first 4Bytes is reserved for command to control ESP32
        # [cmd cmd cmd cmd 0x00 0x00 0x00 0x00 ... 0x00]
        self._tosend = 4 * 8 * self.n_batch * [0x00]
        self._data_format = '%dB' % len(self._tosend)
        self._cmd_queue = Queue()
        self._data_buffer = []
        self._last_time = time.time()

        super(ESP32_API, self).__init__(scale)

    def open(self, dev, mode=0, max_speed_hz=12.5e6):
        '''ESP32 SPI mode set to 0b00 (CPOL=0 & CPHA=0)'''
        super(ESP32_API, self).open(dev, mode, max_speed_hz)

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
        if not self._opened:
            return
        self._data_buffer = []
        super(ADS1299_API, self).close()
        self._started = False
        self._epoll.unregister(self._DRDY)
        self._DRDY.export = False
        self._opened = False

    @ensure_start
    def read(self, *args, **kwargs):
        if not self._cmd_queue.empty():
            cmd = self._cmd_queue.get()
            self.write(cmd + self._tosend[len(cmd):])
            self._data_buffer = []
            return np.zeros(8, np.float32)

        if not len(self._data_buffer):
            # spidev lib is written in C language, where value of list will be
            # changed in-situ. Because we want self._tosend keep as [0x00] * n,
            # self._tosend cannot be directly used in self.xfer[2]. Here we
            # send a new list created by slicing self._tosend.
            data = struct.pack(self._data_format, *self.write(self._tosend[:]))
            data = np.frombuffer(data, np.int32).reshape(self.n_batch, 8)
            self._data_buffer = list(data * self.scale)

        while (time.time() - self._last_time) < (0.9 / self._sample_rate):
            time.sleep(0)
        self._last_time = time.time()
        return self._data_buffer.pop(0)

    @ensure_start
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
        '''
        Only for compatibility with ADS1299_API. Use ESP32 UART
        Command-Line-Interface instead:
            `miniterm.py /dev/tty** 115200`
        or
            `screen /dev/tty** 115200`
        '''
        pass

    def read_registers(self, reg, num):
        '''
        Only for compatibility with ADS1299_API. Use ESP32 UART
        Command-Line-Interface instead:
            `miniterm.py /dev/tty** 115200`
        or
            `screen /dev/tty** 115200`
        '''
        pass

    def set_sample_rate(self, rate):
        if rate not in SAMPLE_RATE:
            print('[ESP32 API] choose one from supported rate!')
            print(' | '.join(list(SAMPLE_RATE.keys())))
            return
        self.write_register(REG_SR, SAMPLE_RATE[rate])
        self._sample_rate = rate
        return rate

    def set_input_source(self, src):
        if src not in INPUT_SOURCES:
            print('[ESP32 API] choose one from supported source!')
            print(' | '.join(list(INPUT_SOURCES.keys())))
            return
        self.write_register(REG_IS, INPUT_SOURCES[src])
        return src

    def set_channel(self, ch, en=True):
        if ch < 0 or ch > 8:
            return False
        self.write_register(REG_CH, 1 if en else 0)
        return True

    @property
    def enable_bias(self):
        return self._enable_bias

    @enable_bias.setter
    def enable_bias(self, boolean):
        self.write_register(REG_BIAS, int(boolean))
        self._enable_bias = boolean

    @property
    def measure_impedance(self):
        return self._measure_impedance

    @measure_impedance.setter
    def measure_impedance(self, boolean):
        self.write_register(REG_IMP, int(boolean))
        self._measure_impedance = boolean


# THE END
