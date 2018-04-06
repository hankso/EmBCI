#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Wed Apr  4 01:37:15 2018

@author: hank
"""
# built-in
import time

# pip install spidev, numpy
import spidev
import numpy as np

# from ./
import gpio4

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
RDATAC          = 0x10
SDATAC          = 0x11

# ADS1299 Sample rate value
SR_DICT = {
    250: 0x06,
    500: 0x05,
    1000: 0x04,
    2000: 0x03,
}


class ADS1299(object):
    '''
    There is a module named RaspberryPiADS1299 to communicate will ADS1299 
    within Python through spidev. But it is not well written. Actually it's
    un-pythonic at all. Hard to understand, hard to use.
    So I rewrite it with spidev and SysfsGPIO(instead of RPi.GPIO, SysfsGPIO
    works on both RaspberryPI, BananaPi, OrangePi and any hardware running 
    Linux).
    
    Methods
    -------
        asd
        asd
        asd
    '''
    def __init__(self,
                 n_channel=8,
                 sample_rate=500,
                 bias_enabled=False,
                 test_mode=False):
        self.spi = spidev.SpiDev()
        self._n_channel = n_channel
        self._sample_rate = sample_rate
        self._bias_enabled = bias_enabled
        self._test_mode = test_mode
        
    def open(self, max_speed_hz=10e6, dev=(0, 0)):
        self.spi.open(dev[0], dev[1])
        self.spi.max_speed_hz = max_speed_hz
        self.spi.mode = 0b01
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
        # power up
        self._PWRDN.value=1
        self._RESET.value=1
        
        # wait for tPOR(2**18*666.0/1e9 = 0.1746) and tBG(assume 0.83)
        time.sleep(0.17+0.83)
        
        # pulse at RESET
        self._RESET.value=0
        time.sleep(2.0*666.0/1e9)
        self._RESET.value=1
        
        # wait for 18*666.0/1e9 second
        time.sleep(1.2e-5)
        
        # device wakes up in RDATAC mode, send SDATAC 
        # command so registers can be written
        self.write(SDATAC)
        
        #===========================================
        self._configure_registers_before_streaming()
        #===========================================
        
        # start streaming data
        self.write(RDATAC)
            
    def close(self):
        self.write(SDATAC)
        self.spi.close()
#        self._DRDY.close()
#        self._PWRDN.close()
#        self._RESET.close()
        
    def _configure_registers_before_streaming(self):
        '''
        @page 70 of ADS1299 datasheet
        '''
        # common setting
        self.write_register(REG_CONFIG1, 0x90|SR_DICT[self._sample_rate])
        self.write_register(REG_CONFIG3, 0xE0)
        self.write_register(REG_BIAS_SENSP, 0x00)
        self.write_register(REG_BIAS_SENSN, 0x00)
        
        # test mode setting
        if self._test_mode:
            self.write_register(REG_CONFIG2, 0xD0)
            self.write_registers(REG_CHnSET_BASE, [0x65] * 8)
        
        # normal setting
        else:
            self.write_register(REG_CONFIG2, 0xC0)
            self.write_register(REG_MISC, 0x20)
            self.write_registers(REG_CHnSET_BASE, [0x60] * 8)
            if self._bias_enabled:
                value = int('1' * self._n_channel, 2)
                self.write_register(REG_BIAS_SENSP, value)
                self.write_register(REG_BIAS_SENSN, value)
                self.write_register(REG_CONFIG3, 0xEC)
    
    def read_raw(self):
        return self.spi.xfer2([0x00] * (3 + self._n_channel * 3))[3:]
    
    def read(self):
        raw = self.spi.xfer2([0x00] * (3 + self._n_channel * 3))[3:]
        new = ''
        for i in range(self._n_channel):
            if raw[3*i] > 127:
                new += '\xff' + raw[3*i:3*i+3]
            else:
                new += '\x00' + raw[3*i:3*i+3]
        return np.frombuffer(new, np.float32)
    
    def write(self, byte):
        self.spi.xfer2([byte])
        
    def write_register(self, reg, byte):
        self.spi.xfer2([reg|0x40, 0x00, byte])
        
    def write_registers(self, start_reg, byte_array):
        self.spi.xfer2([start_reg|0x40, len(byte_array) - 1] + byte_array)

        
        
        
        
        
        