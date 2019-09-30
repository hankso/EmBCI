#!/usr/bin/env python3
# coding=utf-8
#
# File: EmBCI/embci/drivers/ads1299.py
# Authors: Hank <hankso1106@gmail.com>
# Create: 2018-05-23 02:16:40

'''
ADS1299 API
-----------
There is a python package named **RaspberryPiADS1299** available for
communicating with chip ADS1299 through spidev. But this package is not well
written. So I rewrite the interface with `spidev` and `SysfsGPIO`
(unlike RPi.GPIO, SysfsGPIO works on both RaspberryPI, BananaPi, OrangePi and
any hardware running Linux).
'''

# built-in
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
import time
import struct
import select
try:
    from multiprocessing import Lock
except ImportError:
    from threading import Lock

# requirements.txt: necessary: decorator
# requirements.txt: data: numpy
# requirements.txt: drivers: spidev, gpio4
import spidev
import numpy as np
from gpio4 import SysfsGPIO
from decorator import decorator

# =============================================================================
# ADS1299 Pin Configuration

# PIN_PWRDN = 2  # pin PA02
# PIN_START = 3  # pin PA03
PIN_DRDY = 6  # pin PA06 only for ads1299 direct connection
# PIN_RESET = 7  # pin PA07


# =============================================================================
# ADS1299 Registers & Commands & Constants

REG_CONFIG1     = 0x01  # noqa: E221
REG_CONFIG2     = 0x02  # noqa: E221
REG_CONFIG3     = 0x03  # noqa: E221
REG_CHnSET_BASE = 0x05  # noqa: E221
REG_BIAS_SENSP  = 0x0D  # noqa: E221
REG_BIAS_SENSN  = 0x0E  # noqa: E221
REG_LOFF_SENSP  = 0x0F  # noqa: E221
REG_MISC        = 0x15  # noqa: E221

CMD_WAKEUP      = 0x02  # noqa: E221
CMD_STANDBY     = 0x04  # noqa: E221
CMD_RESET       = 0x06  # noqa: E221
CMD_START       = 0x08  # noqa: E221
CMD_STOP        = 0x0A  # noqa: E221
CMD_RDATAC      = 0x10  # noqa: E221
CMD_SDATAC      = 0x11  # noqa: E221
CMD_RDATA       = 0x12  # noqa: E221
CMD_RREG        = 0x20  # noqa: E221
CMD_WREG        = 0x40  # noqa: E221

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
INPUT_SOURCES = {
    'normal':   0b000,
    'shorted':  0b001,
    'mvdd':     0b011,
    'temper':   0b100,
    'test':     0b101,
}

# OrangePi supported spidev max_speed_hz: 100MHz divided by 1, 2, 3, ... n
SUGGESTED_MSH = np.int32([
    100e6, 50e6, 33.33e6, 25e6, 20e6, 12.5e6, 11.11e6, 10e6,
    50e5,  40e5, 33.33e5, 25e5, 20e5, 12.5e5, 11.11e5, 10e5,
    8e5, 5e5, 4e5, 3.33e5, 2.5e5, 2e5, 1.25e5, 1e5
])


# =============================================================================
# ADS1299 API is a sub-class of spidev.SpiDev

@decorator
def ensure_start(func, self, *a, **k):
    assert self._started
    return func(self, *a, **k)


class ADS1299_API(spidev.SpiDev):
    '''
    Methods
    -------
    open              -- Open device
    start             -- Start Read DATA Continuously, must `open` first
    close             -- Close device
    read              -- Return parsed np.ndarray data with shape of (8,)
    read_raw          -- Return raw 8-channel * 3 = 24 bytes data
    write             -- Send bytes array to ADS1299
    write_register    -- Write one register with index and value
    write_registers   -- Write multiple registers with start index and values
    measure_impedance -- Property, set it to True or False
    enable_bias       -- Property, set it to True or False
    set_sample_rate   -- Rate can be 250 | 500 | 1k | 2k | 4k | 8k | 16k Hz
    set_input_source  -- Choose one source from available:
        normal:  Normal electrode input
        shorted: Input shorted, to measure noise
        mvdd:    Supply measurement MVDD
        temper:  Temperature sensor
        test:    Test signal(internal or external generated square wave)

    Examples
    --------
    First establish connection to ADS1299 @ **/dev/spi0.1**, sample rate is 1k
    >>> ads = ADS1299_API()
    >>> ads.open((0, 0))
    >>> ads.start(1000)
    >>> ads.measure_impedance
    False
    >>> ads.read()
    array([1.234e-3, ...])  # raw data

    Then you can set to measure impedance mode.
    >>> ads.measure_impedance = True
    >>> ads.read()
    array([1.234, ...])  # this will return impedance value of each channel

    Attention
    ---------
    Ads1299 accept data from DIN at raising edge and transfer data out from
    DOUT to OrangePi at falling edge. Set SPI mode to 0b10 (CPOL=1 & CPHA=0)

    Notes
    -----
    Because ADS1299_API inherits spidev.SpiDev, methods list of instance may be
    pretty confusing, you can compare them by following table:
    +----------------------------------+-----------------------------------+
    | ADS1299_API                      | spidev.SpiDev                     |
    +==================================+===================================+
    | open(device, max_speed_hz)       | open(bus, device)                 |
    | start(sample_rate)               | max_speed_hz = 1e6                |
    | close()                          | close()                           |
    | read()                           | readbytes(len)                    |
    | write(byte_array)                | writebytes(byte_array)            |
    | read_register(reg)               | bits_per_word = 8                 |
    | read_registers(reg, num)         | mode = 0 # number in [0, 1, 2, 3] |
    | write_register(reg, byte)        | xfer(byte_array)                  |
    | write_registers(reg, byte_array) | xfer2(byte_array)                 |
    | set_sample_rate(rate)            | cshigh = True | False             |
    | set_input_source(src)            | threewire = True | False          |
    | enable_bias = True | False       | loop = True | False               |
    | measure_impedance = True | False | lsbfirst = True | False           |
    |                                  | fileno                            |
    +----------------------------------+-----------------------------------+
    '''

    def __init__(self, scale=4.5/24/2**24, *a, **k):
        self.scale = float(scale)
        self._DRDY = SysfsGPIO(PIN_DRDY)
        # self._PWRDN = SysfsGPIO(PIN_PWRDN)
        # self._RESET = SysfsGPIO(PIN_RESET)
        # self._START = SysfsGPIO(PIN_START)

        self._lock = Lock()
        self._opened = False
        self._started = False
        self._enable_bias = False
        self._measure_impedance = False

    def open(self, dev, mode=2, max_speed_hz=12500000):
        '''
        Connect to user space SPI interface `/dev/spidev*.*`.

        Parameters
        ----------
        dev : tuple or list
            BUS and CS number, e.g. (1, 0) means `/dev/spidev1.0`.
        mode : int
            SPI mode, default 2 (0b10: CPOL=1 & CPHA=0).
        max_speed_hz : int
            SPI CLK speed in Hertz, default to 12.5MHz.
        '''
        assert not self._opened, 'already used spidev{}.{}'.format(*self._dev)
        super(ADS1299_API, self).open(dev[0], dev[1])
        msh = int(max_speed_hz)
        if msh not in SUGGESTED_MSH:
            msh = SUGGESTED_MSH[abs(SUGGESTED_MSH - max_speed_hz).argmin()]
            print('[ADS1299 API] max speed of spidev set to %dHz' % msh)
        self.max_speed_hz = msh
        self.mode = mode
        self._dev = tuple(dev)
        # self._START.export = True
        # self._START.direction = 'out'
        # self._START.value = 0
        self._DRDY.export = True
        self._DRDY.direction = 'in'

        # TODO: bugfix
        # a SysfsGPIO must be read at least once first then it can be polled
        self._DRDY.value

        self._DRDY.edge = 'falling'
        self._epoll = select.epoll()
        self._epoll.register(self._DRDY, select.EPOLLET)
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

        #  Power up chip
        # self._PWRDN.value=1  # we pull it up to high on PCB
        self.write(CMD_RESET)  # same as self._RESET.value=1
        #  wait for tPOR(2**18 * 666.0 / 1e9 = 0.1746) and tBG(assume 0.8254)
        time.sleep(1)
        #  Chip wakes up at RDATAC mode. Send SDATAC then config registers.
        self.write(CMD_SDATAC)

        # Configure ADS1299 registers
        self.write_register(REG_CONFIG1, 0b10010000 | SAMPLE_RATE[sample_rate])
        self.write_register(REG_CONFIG2, 0b11010000)
        self.write_register(REG_CONFIG3, 0b11100000)
        self.write_register(REG_MISC, 0b00100000)
        self.write_registers(REG_CHnSET_BASE, [0b01100000] * 8)
        self.write(CMD_START)  # same as self._START.value = 1
        time.sleep(1)

        # Start streaming data
        self.write(CMD_RDATAC)
        self._started = True

    def close(self):
        if not self._opened:
            return
        self.write(CMD_SDATAC)
        self.write(CMD_STOP)
        super(ADS1299_API, self).close()
        self._started = False
        self._epoll.unregister(self._DRDY)
        self._DRDY.export = False
        # self._START.export = False
        # self._PWRDN.export = False
        # self._RESET.export = False
        self._opened = False

    @ensure_start
    def set_sample_rate(self, rate):
        if rate not in SAMPLE_RATE:
            print('[ADS1299 API] choose one from supported rate!')
            print(' | '.join(list(SAMPLE_RATE.keys())))
            return
        rate = SAMPLE_RATE[rate]
        self.write(CMD_SDATAC)
        v = self.read_register(REG_CONFIG1)
        self.write_register(REG_CONFIG1, v & ~0b111 | rate)
        self.write(CMD_RDATAC)
        return rate

    @ensure_start
    def set_input_source(self, src):
        if src not in INPUT_SOURCES:
            print('[ADS1299 API] choose one from supported source!')
            print(' | '.join(list(INPUT_SOURCES.keys())))
            return
        src = INPUT_SOURCES[src]
        self.write(CMD_SDATAC)
        vs = self.read_registers(REG_CHnSET_BASE, 8)
        vs = [(v & ~0b111 | src) for v in vs]
        self.write_registers(REG_CHnSET_BASE, vs)
        self.write(CMD_RDATAC)
        return src

    @ensure_start
    def set_channel(self, ch, en=True):
        if ch < 0 or ch > 8:
            return
        raise NotImplementedError
        # TODO: drivers.ads1299 set channel enable/disable

    @property
    def enable_bias(self):
        return self._enable_bias

    @enable_bias.setter
    @ensure_start
    def enable_bias(self, boolean):
        self.write(CMD_SDATAC)
        if boolean is True:
            self.write_register(REG_BIAS_SENSP, 0b11111111)
            self.write_register(REG_BIAS_SENSN, 0b11111111)
            self.write_register(REG_CONFIG3, 0b11101100)
        elif boolean is False:
            self.write_register(REG_BIAS_SENSP, 0b00000000)
            self.write_register(REG_BIAS_SENSN, 0b00000000)
            self.write_register(REG_CONFIG3, 0b11100000)
        self._enable_bias = boolean
        self.write(CMD_RDATAC)

    @property
    def measure_impedance(self):
        return self._measure_impedance

    @measure_impedance.setter
    @ensure_start
    def measure_impedance(self, boolean):
        self.write(CMD_SDATAC)
        vs = self.read_registers(REG_CHnSET_BASE, 8)
        vs = [v & ~(0b111 << 4) for v in vs]
        if boolean is True:
            self.write_register(REG_LOFF_SENSP, 0b11111111)
            self.write_registers(REG_CHnSET_BASE, vs)
        elif boolean is False:
            self.write_register(REG_LOFF_SENSP, 0b00000000)
            self.write_registers(REG_CHnSET_BASE, [v | 0b110 << 4 for v in vs])
        self._measure_impedance = boolean
        self.write(CMD_RDATAC)

    @ensure_start
    def read(self, *args, **kwargs):
        '''Read chunk bytes from ADS1299 and decode into `float32` array'''
        #  Rev.1
        # while (time.time() - self.last_time) < 1.0 / self.sample_rate:
        #     time.sleep(0)
        # self.last_time = time.time()

        #  Rev.2
        # while self._DRDY.value == 1:
        #     time.sleep(0)

        #  Rev.3
        self._epoll.poll()  # this will block until interrupt on DRDY detected

        num = self.write([0x00] * 27)[3:]
        byte = ''
        for i in range(8):
            # tmp = chr(num[3 * i + 2]) + chr(num[3 * i + 1]) + chr(num[3 * i])
            # use time: 4.3us
            tmp = struct.pack('3B', num[3 * i + 2], num[3 * i + 1], num[3 * i])
            # use time: 1.3us
            byte += tmp + ('\xff' if num[3 * i] > 127 else '\x00')
        return np.frombuffer(byte, np.int32) * self.scale, time.time()

    def write(self, byte_array):
        '''Write bytes array to ADS1299 through SPI and return value list.'''
        if not isinstance(byte_array, list):
            byte_array = list(byte_array)
        with self._lock:
            value = self.xfer2(byte_array)
        return value

    def write_register(self, reg, byte):
        '''Write register `reg` with value `byte`'''
        self.write([reg | CMD_WREG, 0x00, byte])

    def write_registers(self, reg, byte_array):
        '''Write registers start from `reg` with values `byte_array`'''
        self.write([reg | CMD_WREG, len(byte_array) - 1] + byte_array)

    @ensure_start
    def read_register(self, reg):
        '''Read single register at `reg`'''
        self.write(CMD_SDATAC)
        value = self.write([CMD_RREG | reg, 0x00, 0x00])[2]
        self.write(CMD_RDATAC)
        return value

    @ensure_start
    def read_registers(self, reg, num):
        '''Read `num` registers start from `reg`'''
        self.write(CMD_SDATAC)
        value = self.write([CMD_RREG | reg, num - 1] + [0] * num)[2:]
        self.write(CMD_RDATAC)
        return value


def voltage_to_celsius(raw):
    return (raw * 1e6 - 145300) / 490 + 25


# THE END
