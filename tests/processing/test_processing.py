#!/usr/bin/env python3
# coding=utf-8
#
# File: EmBCI/tests/test_processing.py
# Authors: Hank <hankso1106@gmail.com>
# Create: 2019-02-24 23:24:12
#
# TODO:
#   test signalinfo.detrend with plt.plot(); plt.save_fig()
#   test notch with ploting result

'''Running test with `python test_processing.py` is suggested.'''

# built-in
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# requirements.txt: testing: pytest
# requirements.txt: data: numpy
import pytest
import numpy as np

pytest.skip('not implemented yet.', allow_module_level=True)

from embci.processing import SignalInfo

signal = SignalInfo(500)
data = np.random.random((2, 8, 1024))


def test_detrend():
    signal.detrend(data.copy())


def test_notch():
    signal.notch(data.copy())


def test_fft():
    freq, amp = signal.fft(data.copy())
    print('after FFT shape: {}'.format(amp.shape))


def test_stft():
    freq, time, amp = signal.stft(data.copy())
    print('after STFT shape: {}'.format(amp.shape))


if __name__ == '__main__':
    from .. import test_with_unittest
    funcs = []
    for func in [_ for _ in globals() if _.startswith('test_')]:
        func = globals()[func]
        if callable(func):
            funcs.append(func)
    test_with_unittest(*funcs)
