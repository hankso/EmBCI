#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Created on Wed May 20 17:40:36 2017

@author: hank


          SYNC*2|len|signal|spectrum| delta  | theta  | lalpha | halpha | lbeta  | hbeta  | lgamma | hgamma |atten|medit|checksum
Package : aa aa |20 |02 c8 |83 18   |0c 32 82|0b 61 76|01 06 a9|00 7b 4a|02 86 b3|03 2f 52|01 e7 e1|12 11 c2|04 00|05 00|0d

          SYNC*2|len|RawData| Raw |checksum
Raw Data: aa aa |04 |80 02  |f8 00|85

"""

from __future__ import print_function
import serial, os, sys, time, logging, matplotlib.pyplot as plt, numpy as np

class TGAM_Reader(object):
    def __init__(self,
                 port = 'scan',
                 baudrate = 115200,
                 test = False,
                 parsed_by_mcu = False,
                 logger = logging.getLogger()):

        # pre-defined flags
        self._FLAG_SYNC       = 0xAA
        self._FLAG_SYNC_      = 0xEA
        self._FLAG_Signal     = 0x02
        self._FLAG_Attention  = 0x04
        self._FLAG_Meditation = 0x05
        self._FLAG_Blink      = 0x16
        self._FLAG_Excode     = 0x55
        self._FLAG_Length     = 0x7F
        self._FLAG_RawData    = 0x80
        self._FLAG_Spectrum   = 0x83

        # raw,       time
        # _time,     signal
        # delta,     theta
        # l_alpha,   h_alpha
        # l_beta,    h_beta
        # l_gamma,   h_gamma
        # attention, meditation
        self.data = dict(time = [],
                         _time = [],
                         raw = [],
                         signal = [],
                         delta = [],
                         theta = [],
                         lalpha = [],
                         halpha = [],
                         lbeta = [],
                         hbeta = [],
                         lgamma = [],
                         hgamma = [],
                         atten = [],
                         medit = [])
        #self._win_data = {}
        #self._win_data.update(self.data)

        self.logger = logger
        self.baudrate = baudrate
        self._sample_rate = 512
        self._throw_packages = 0
        self._mode = 'test' if test else ('mcu' if parsed_by_mcu else 'run')

        while 1:
            try:
                self.serial =  serial.Serial(port if port != 'scan' \
                                   			 	  else self._find_port(),
                              				 self.baudrate)
                self.logger.debug('Successfully load serial. Start reading...')
                self._r = self.serial.read
                break
            except IOError as e:
                self._mode = 'closed'
                self.logger.error(e)
                break
            except:
                self.logger.error('Failed open serial.')
                port = 'scan'
                time.sleep(3)

    def start(self):
        '''
        Start reading data into self.data.
        '''
        if self._mode == 'test':
            self.logger.warn('TEST mode!')
            try:
                while 1: print(self._r().encode('hex'), end = ' ')
            except KeyboardInterrupt:
                self.logger.error('Keyboard interrupt detected')

        elif self._mode == 'run':
            time.sleep(1)
            self.logger.warn('RUN mode!')

            self._start_time = time.time()
            log_file = 'raw_data_%s.csv' % time.strftime('%Y%m%d-%H:%M:%S')
            self.csv_log = open(log_file, 'w')
            self.csv_log.write('Time, Raw\n')
            self._buff = []
            while 1:
                try:
                    #================
                    self._read_port()
                    if len(self._buff) == 4:
                        self.csv_log.write('%f, %d\n'%(self.data['time'][-1],
                                                       self.data['raw'][-1]))
                    self._parse_buffer()
                    print(','.join(self.data[ch] \
                    	           for ch in self.data.keys() \
                    			   if ch is not '_time'))
                    #================
                except KeyboardInterrupt:
                    self.logger.error('Keyboard interrupt detected')
                    break
                except Exception as e:
                    self.logger.error(e)
            self.csv_log.close()

        elif self._mode == 'mcu':
            time.sleep(1)
            self.logger.warn('MCU mode!')
            while 1:
                try:
                    #===================
                    self._buff = self.serial.readline()[:-2].split(',')
                    self._parse_buffer()
                    self.plot(self.data)
                    #===================
                except KeyboardInterrupt:
                    self.logger.error('Keyboard interrupt detected')
                    break
                except Exception as e:
                    self.logger.error(e)
            self.plot(self.data)

        if self._mode != 'closed': self.serial.close()
        self.logger.error('Terminated...')

    def _read_port(self):
        '''
        Alias self._r = self.serial.read
        '''
        while self.serial.is_open:
            # 两个连续校验头 0xAA
            # '\xaa' is a 8-bit char, which can be proved by chr(170)='\xaa'
            # and we can convert it from char to int with ord()
            if ord(self._r()) != self._FLAG_SYNC: continue
            #log.debug('First sync detected.')
            if ord(self._r()) != self._FLAG_SYNC: continue
            #log.debug('Second sync detected.')

            # 防止数据中出现 0xAA 被误认为校验头，下一字再验证一下
            while 1:
                plength = ord(self._r())
                if plength != self._FLAG_SYNC: break
            if plength > self._FLAG_SYNC: continue

            # 读取数据
            self._buff = []
            for _ in range(plength):
                self._buff.append(ord(self._r()))

            # 校验 checksum 判断是否丢包
            if ~ sum(self._buff) & 0xFF == ord(self._r()): break
            else:
                self.logger.error('Throw package: ' + str(self._buff))
                self._throw_packages += 1

    def _parse_buffer(self):
        if len(self._buff) == 2:
            self.data['raw'] += [int(self._buff[1])]
            self.data['time'] += [int(self._buff[0])]

        elif len(self._buff) == 4:
            self.data['raw'] += [np.int16(self._buff[2] << 8 | self._buff[3])]
            self.data['time'] += [time.time() - self._start_time]

        elif len(self._buff) == 12:
            for i, name in enumerate(['_time', 'signal', \
                    'delta', 'theta', 'lalpha', 'halpha', \
                    'lbeta', 'hbeta', 'lgamma', 'hgamma', \
                    'atten', 'medit']):
                self.data[name] += [int(self._buff[i])]

        elif len(self._buff) == 32:
            self.data['signal'] += [self._buff[1]]
            t = self._buff[4:]
            for temp in ['delta', 'theta', 'lalpha', 'halpha', \
                         'lbeta','hbeta', 'lgamma', 'hgamma']:
                self.data[temp] += [np.int16(t[0]<<16 | t[1]<<8 | t[2])]
                t = t[3:]
            self.data['atten'] += [t[1]]
            self.data['medit'] += [t[3]]
            self.data['_time'] += [time.time() - self._start_time]

    def _find_port(self):
        port_list = []
        temp = ['COM'+str(_) for _ in xrange(32)] \
        	   if os.name != 'posix' else \
               ['/dev/'+_ for _ in os.listdir('/dev/') \
               	if 'USB' in _ or 'rfcomm' in _]
        for port in temp:
            try:
                s = serial.Serial(port)
                if s.is_open:
                    port_list.append(port)
                    s.close()
            except:
                continue
        if port_list:
            if len(port_list) == 1:
                self.logger.warn('Port %s selected'%port_list[0])
                return port_list[0]
            self.logger.error('Please choose one from all available ports ')
            self.logger.error(' | '.join(port_list))
            while 1:
                port = raw_input('Port name: ')
                if port in port_list:
                    self.logger.warn('Port %s selected'%port)
                    return port
                else:
                    self.logger.error('Invalid input!')
        raise IOError('No port available! Abort.')

    def plot(self, data, max_win_length = 100):
        '''
        raw,       time
        _time,     signal
        delta,     theta
        l_alpha,   h_alpha
        l_beta,    h_beta
        l_gamma,   h_gamma
        attention, meditation
        '''
        plt.cla()
        plt.pause(0.0010)
        plt.title('throw packages: %d'%self._throw_packages)
        # print('big package at '+str(time.time() - self._start_time))
# =============================================================================
#         plt.subplot(211)
#         plt.ylim(-1.5, 1.5)
#         plt.xlim(data['_time'][-1] - 1.01*max_win_length,
#                  data['_time'][-1] + 1)
#         for channel in ['delta','theta','lalpha','halpha','lbeta',
#                         'hbeta','lgamma','hgamma','atten','medit']:
#             plt.plot(data['_time'][-max_win_length:],
#                      self.mapping(data[channel][-max_win_length:], (-1,1)))
# =============================================================================

        plt.subplot(212)
        b = float(max_win_length)/self._sample_rate/8
        t = data['time'][-max_win_length:]
        if len(t) > max_win_length:
            plt.xlim(  t[0] - b,  t[-1] + b)
        else:
            plt.xlim(min(t) - b, max(t) + b)
        plt.plot(t, data['raw'][-max_win_length:])
        plt.show()

if __name__ == '__main__':
    logging.basicConfig(level=logging.NOTSET, format='%(message)s')
    logger = logging.getLogger()
    logger.handlers[0].setLevel(logging.DEBUG)  # msg output to terminal
    fh = logging.FileHandler('TGAM_reader.log') # msg logged to file
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter('%(asctime)s: %(filename)-10s [line:%(lineno)3d] %(name)-5s %(levelname)-8s: %(message)s'))
    while len(logger.handlers) > 1: logger.handlers.pop()
    logger.addHandler(fh)

    r = TGAM_Reader(baudrate = 115200,
                    test = True if sys.argv[-1]=='True' else False,
                    parsed_by_mcu = False,
                    logger = logger)
    r.start()

    logging.shutdown()
