#!/usr/bin/env python
# coding=utf-8
#
# File: EmBCI/tests/test_processing.py
# Author: Hankso
# Webpage: https://github.com/hankso
# Time: Sun 24 Feb 2019 23:24:12 CST

'''Running test will `python test_processing.py` is suggested.'''

import numpy as np
import pytest

pytest.skip('not implemented yet.', allow_module_level=True)

from embci.processing import SignalInfo

signal = SignalInfo(500)
data = np.random.random((2, 8, 1024))


def test_detrend(random_data):
    # TODO: test with plt.plot(); plt.save_fig()
    data = signal.detrend(data)
    data


def test_notch(self):
    # TODO: test notch with ploting result
    data = self.signal.notch(self.data)
    data


def test_fft(self):
    freq, amp = self.signal.fft(self.data)
    print('after FFT shape: {}'.format(amp.shape))


def test_stft(self):
    freq, time, amp = self.signal.stft(self.data)
    print('after STFT shape: {}'.format(amp.shape))


if __name__ == '__main__':
    from . import run_test_with_unittest
    funcs = []
    for func in [_ for _ in globals() if _.startswith('test_')]:
        func = globals()[func]
        if isinstance(func, type(run_test_with_unittest)):
            funcs.append(func)
    run_test_with_unittest(*funcs)
