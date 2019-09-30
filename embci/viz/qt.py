#!/usr/bin/env python3
# coding=utf-8
#
# File: EmBCI/embci/viz/qt.py
# Authors: Hank <hankso1106@gmail.com>
# Create: 2019-02-07 22:07:42

'''Graphic User Interface utilities based on Matplotlib and QT framework.'''

# built-in
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
import time
import traceback

# requirements.txt: data: numpy
# requirements.txt: optional: matplotlib, opencv-python
import numpy as np
try:
    import cv2
except ImportError:
    cv2 = None
try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None

from ..processing import SignalInfo

# TODO: BCI streamviewer


def plot_data_matplotlib(data, sample_rate, sample_time, actionname):
    if plt is None: return  # noqa: E701
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
        f = np.linspace(0, sample_rate // 2, amp.shape[0])
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
        amp = 2.0 * abs(np.fft.rfft(d)) / len(d)
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


def plot_data_opencv(data, sample_rate=256, win_width=400,
                     imgsize=(200, 400), color=(255, 180, 120)):
    if cv2 is None: return  # noqa: E701
    if imgsize[1] < win_width:
        raise RuntimeError('frame width is smaller than'
                           ' data win length, too narrow.')
    h, w = imgsize
    x = np.linspace(0, len(data) / sample_rate, 1 / sample_rate)
    y = np.atleast_1d(data)
    y = np.pad(
        h / 2 - y / y.max() * (h / 2 * 0.95),
        (0, win_width + 1 - len(y) if len(y) <= win_width else 0),
        'constant', constant_values=(0, 0))
    try:
        for i in range(len(y) - win_width):
            _x = x[i:i + win_width] - x[i]
            _y = y[i:i + win_width]
            _x = _x / max(_x) * (w * 0.95) + w * 0.025
            pts = np.array([_x, _y]).T
            img = cv2.polylines(
                np.zeros(imgsize).astype(np.int8),
                pts.astype(np.int32), False, 255, 1)
            cv2.imshow('win', img)
            if cv2.waitKey(1000 / sample_rate) in [10, 32, 112]:
                while cv2.waitKey() not in [10, 32, 112]:  # enter | space | p
                    pass
    except Exception:
        traceback.print_exc()
    while cv2.waitKey() not in [27, 113]:  # esc | q
        cv2.imshow('win', img)
    cv2.destroyWindow('win')


__all__ = []

# THE END
