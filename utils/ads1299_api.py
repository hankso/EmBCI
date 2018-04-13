#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Wed Apr  4 01:37:15 2018

@author: hank
"""
# built-in
import time
import struct

# pip install numpy, spidev
import spidev
import numpy as np

# ADS1299 Pin mapping
PIN_DRDY        = 97
PIN_PWRDN       = 98
PIN_RESET       = 99
# ADS1299 Registers
REG_CONFIG1     = 0x01
REG_CONFIG2     = 0x02
REG_CONFIG3     = 0x03
REG_CHnSET_BASE = 0x05
REG_MISC        = 0x15
REG_BIAS_SENSP  = 0x0D
REG_BIAS_SENSN  = 0x0E
# ADS1299 Commands
WAKEUP          = 0x02
STANDBY         = 0x04
RESET           = 0x06
START           = 0x08
STOP            = 0x0A
RDATAC          = 0x10
SDATAC          = 0x11
RDATA           = 0x12
# ADS1299 Sample rate value dict
SR_DICT = {
    250:          0x96,
    500:          0x95,
    1000:         0x94,
    2000:         0x93,
}


class ADS1299_API(object):
    '''
    There is a module named RaspberryPiADS1299 to communicate will ADS1299 
    within Python through spidev. But it is not well written. Actually it's
    un-pythonic at all. Hard to understand, hard to use.
    So I rewrite it with spidev and SysfsGPIO(instead of RPi.GPIO, SysfsGPIO
    works on both RaspberryPI, BananaPi, OrangePi and any hardware running 
    Linux, theoretically).
    
    Methods
    -------
        open: open device
        start: start Read DATA Continuously mode, you must call open first
        close: close device
        read_raw: return raw 8-channel * 3 = 24 bytes data
        read: return parsed np.ndarray data with shape of (8,)
        write: transfer one byte to ads1299
        write_register: write one register with index and value
        write_registers: write series registers with start index and values
    '''
    def __init__(self,
                 sample_rate=500,
                 bias_enabled=False,
                 test_mode=False,
                 scale=5.0/24/2**24):
#        self.spi = spi.SPI_SysfsGPIO(13, 14, 15, 16)
        self.spi = spidev.SpiDev()
        
        self.scale = scale
        self._sample_rate = sample_rate
        self._bias_enabled = bias_enabled
        self._test_mode = test_mode
        self._opened = False
        
    def open(self, dev, max_speed_hz=10000000):
        self.spi.open(dev[0], dev[1])
        self.spi.max_speed_hz = max_speed_hz
        self._opened = True
#        self._DRDY = gpio4.SysfsGPIO(PIN_DRDY)
#        self._PWRDN = gpio4.SysfsGPIO(PIN_PWRDN)
#        self._RESET = gpio4.SysfsGPIO(PIN_RESET)
        return dev
        
    def start(self):
        '''
        Before device power up, all digital and analog inputs must be low. 
        At the time of power up, keep all of these signals low until the 
        power supplies have stabilized.
        '''
        assert self._opened
        #======================================================================
        # power up
        #======================================================================
        
        #self._PWRDN.value=1
        # we tie it high
        
        #self._RESET.value=1
        self.write(RESET)
        
        # wait for tPOR(2**18*666.0/1e9 = 0.1746) and tBG(assume 0.83)
        time.sleep(0.17+0.83)
        
        self.write(START)
        time.sleep(1)
        
        # device wakes up in RDATAC mode, send SDATAC 
        # command so registers can be written
        self.write(SDATAC)
        
        #======================================================================
        # configure_registers_before_streaming
        #======================================================================
        
        # common setting
        self.write_register(REG_CONFIG1, SR_DICT[self._sample_rate])
        self.write_register(REG_CONFIG3, 0xE0)
        self.write_register(REG_BIAS_SENSP, 0x00)
        self.write_register(REG_BIAS_SENSN, 0x00)
        
        # test mode setting
        if self._test_mode:
            self.write_register(REG_CONFIG2, 0xD0)
            self.write_registers(REG_CHnSET_BASE, [0x65] * 8)
        
        # normal mode setting
        else:
            self.write_register(REG_CONFIG2, 0xC0)
            self.write_register(REG_MISC, 0x20)
            self.write_registers(REG_CHnSET_BASE, [0x60] * 8)
            if self._bias_enabled:
                self.write_register(REG_BIAS_SENSP, 0b11111111)
                self.write_register(REG_BIAS_SENSN, 0b11111111)
                self.write_register(REG_CONFIG3, 0xEC)
        
        #======================================================================
        # start streaming data
        #======================================================================
        self.write(RDATAC)
        
    def close(self):
        if self._opened:
            self.write(SDATAC)
            self.spi.close()
#            self._DRDY.close()
#            self._PWRDN.close()
#            self._RESET.close()

    def read_raw(self):
        '''
        Return list with length 3 + 8_ch * 3_bytes = 27 uint8
        '''
        return self.spi.xfer2([0x00] * (27))
    
    def read(self):
        num = self.read_raw()[3:]
        byte = ''
        for i in range(8):
            tmp = struct.pack('3B', num[3*i+2], num[3*i+1], num[3*i])
            byte += tmp + ('\xff' if num[3*i] > 127 else '\x00')
        return np.frombuffer(byte, np.int32).astype(np.float32) * self.scale
    
    def write(self, byte):
        self.spi.xfer2([byte])
        
    def write_register(self, reg, byte):
        self.spi.xfer2([reg|0x40, 0x00, byte])
        
    def write_registers(self, start_reg, byte_array):
        self.spi.xfer2([start_reg|0x40, len(byte_array) - 1] + byte_array)

        
        
        
        
        
        
