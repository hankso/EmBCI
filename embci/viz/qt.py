#!/usr/bin/env python
# coding=utf-8
#
# File: EmBCI/embci/viz/qt.py
# Author: Hankso
# Webpage: https://github.com/hankso
# Time: Thu 07 Feb 2019 22:07:42 CST

'''Graphic User Interface utilities based on Matplotlib and QT framework.'''

# built-in
import time

# requirements.txt: data-processing: numpy
# requirements.txt: optional: matplotlib
import numpy as np
try:
    import matplotlib.pyplot as plt
    _NO_PLT_ = False
except ImportError:
    _NO_PLT_ = True

from ..processing import SignalInfo

# TODO: pybci streamviewer


def view_data_with_matplotlib(data, sample_rate, sample_time, actionname):
    if _NO_PLT_:
        return
    plt.ion()
    if not isinstance(data, np.ndarray):
        data = np.array(data)
    if data.ndim != 2:
        raise
    p = SignalInfo(sample_rate)
    for ch, d in enumerate(data):
        plt.figure('%s_%d' % (actionname, ch))

        plt.subplot(321)
        plt.title('raw data')
        plt.plot(d, linewidth=0.5)

        plt.subplot(323)
        plt.title('remove_DC and notch')
        plt.plot(p.notch(d)[0], linewidth=0.5)

        plt.subplot(325)
        plt.title('after fft')
        plt.plot(p.fft(p.notch(p.remove_DC(data)))[0], linewidth=0.5)

        plt.subplot(343)
        plt.title('after stft')
        amp = p.stft(p.remove_DC(p.notch(d)))[0]
        f = np.linspace(0, sample_rate / 2, amp.shape[0])
        t = np.linspace(0, sample_time, amp.shape[1])
        plt.pcolormesh(t, f, np.log10(amp))
        highest_col = [col[1] for col in sorted(zip(np.sum(amp, axis=0),
                                                    range(len(t))))[-3:]]
        plt.plot((t[highest_col], t[highest_col]),
                 (0, f[-1]), 'r')
        plt.ylabel('Freq / Hz')
        plt.xlabel('Time / s')

        plt.subplot(344)
        plt.title('Three Max Amptitude'.format(t[highest_col]))
        for i in highest_col:
            plt.plot(amp[:, i], linewidth=0.5,
                     label='time: {:.2f}s'.format(t[i]))
        plt.legend()

        plt.subplot(324)
        t = time.time()
        plt.psd(p.remove_DC(p.notch(d))[0], Fs=250,
                label='filtered', linewidth=0.5)
        plt.legend()
        used_time = 1000 * (time.time() - t)
        plt.title('normal PSD -- used time: %.3fms' % used_time)

        d = p.remove_DC(p.notch(d))[0]
        plt.subplot(326)
        t = time.time()
        amp = 2 * abs(np.fft.rfft(d)) / float(len(d))
        # amp[0] *= 1e13
        plt.plot(10 * np.log10(amp * amp)[::12],
                 linewidth=0.5,
                 label='unfiltered')
        used_time = 1000 * (time.time() - t)
        plt.title('optimized PSD -- used time: %.3fms' % used_time)
        plt.legend()
        plt.grid()
        plt.xlabel('Frequency')
        plt.ylabel('dB/Hz')


__all__ = []

# THE END
