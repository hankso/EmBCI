#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Fri Apr  6 02:41:27 2018

@author: hank
"""

import sys, os; sys.path += ['../src']
import matplotlib.pyplot as plt
import scipy.io as sio
import numpy as np
import time
from preprocessing import Processer

# data shape: 1 x n_channel x window_size
filename = '../data/test/relax-1.mat'
actionname = os.path.basename(filename).split('-')[0]
data = sio.loadmat(filename)[actionname]
data = data[0]
p = Processer(250, 2)

for ch, d in enumerate(data):
    plt.figure('ch_%d' % ch)
    
    plt.subplot(321)
    plt.title('raw data')
    plt.plot(d, linewidth=0.5)
    
    plt.subplot(323)
    plt.title('remove_DC and notch')
    plt.plot(p.notch(p.remove_DC(d))[0, 0], linewidth=0.5)
    
    plt.subplot(325)
    plt.title('after fft')
    plt.plot(p.fft(p.notch(p.remove_DC(data)))[1][0, 0], linewidth=0.5)
    
    plt.subplot(343)
    plt.title('after stft')
    f, t, amp = p.stft(p.remove_DC(p.notch(d)))
    plt.pcolormesh(t, f, np.log10(amp[0, 0]))
    highest_col = [col[1] for col in sorted(zip(np.sum(amp[0, 0], axis=0),
                                                range(len(t))))[-3:]]
    
    plt.plot((t[highest_col], t[highest_col]),
             (0, f[-1]), 'r')
    plt.ylabel('Freq / Hz')
    plt.xlabel('Time / s')
    
    plt.subplot(344)
    plt.title('Three Max Amptitude'.format(t[highest_col]))
    for i in highest_col:
        plt.plot(amp[0, 0, :, i], label='time: {}s'.format(t[i]), linewidth=0.5)
        plt.legend()
    
    plt.subplot(324)
    t = time.time()
    plt.psd(d, Fs=250, label='raw', linewidth=0.5)
    plt.psd(p.remove_DC(p.notch(d))[0, 0], Fs=250, label='filter', linewidth=0.5)
    plt.legend()
    plt.title('normal PSD -- used time: %.3fms' % (1000*(time.time()-t)))
    
    plt.subplot(326)
    t = time.time()
    
    plt.title('optimized PSD -- used time: %.3fms' % (1000*(time.time()-t)))
    