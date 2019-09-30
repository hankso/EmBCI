#!/usr/bin/env python3
# coding=utf-8
#
# File: Speller/model.py
# Authors: Hank <hankso1106@gmail.com>
# Create: 2019-09-01 15:00:49

'''Keras compatiable models using TRCA-backend are implemented here'''

# built-in
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
import time

# requirements.txt: data: numpy, scipy
import scipy.signal as signal
import numpy as np

from embci.utils import TempStream
with TempStream(stderr=None):
    from keras.utils.generic_utils import Progbar

# =============================================================================
# constants

NUM_TARGET  = 40   # number of targets (int)
NUM_SUBBAND = 5    # number of sub-bands (int)
CHEBY_RP    = 0.4  # maximum ripple allowed in the passband (float)
CHEBY_GPASS = 3    # maximum loss in the passband (dB)
CHEBY_GSTOP = 40   # minimum attenuation in the stopband (dB)
CHEBY_FMIN  = 6    # minimum frequency of sub-bands (Hz)
CHEBY_FSTEP = 8    # sub-band width in frequency (Hz)
CHEBY_FMAX  = 90   # maximum frequency of sub-bands (Hz)
CHEBY_FEDGE = 10   # edge frequency for maximum frequency of sub-bands (Hz)
CHEBY_EDGE  = 6    # edge frequency between passband and stopband (Hz)


class Model(object):
    def __init__(self, reader, ntarget=NUM_TARGET, nsubband=NUM_SUBBAND, **k):
        self.sample_rate = reader.sample_rate
        self.num_channel = reader.num_channel
        self.num_sample  = reader.window_size
        self.num_subband = nsubband
        self.num_target  = ntarget

        self.weights = np.zeros((
            self.num_target, self.num_subband, self.num_channel
        ))

    @classmethod
    def from_config(cls, cfg):
        cfg.setdefault('')
        return cls(**cfg)

    def update_config(self, cfg):
        for attr, value in cfg.items():
            if not attr.startswith('_'):
                setattr(self, attr, value)

    def get_config(self):
        pass

    @property
    def num_target(self):
        return self._target_num

    @num_target.setter
    def num_target(self, v):
        if not isinstance(v, int):
            raise TypeError('Expect int but receive: `%s`' % type(v).__name__)
        self._target_num = v
        self._target_coef = np.zeros((
            self.num_target, self.num_subband,
            self.num_channel, self.num_sample
        ))

    @property
    def num_subband(self):
        return self._subband_num

    @num_subband.setter
    def num_subband(self, v):
        if not isinstance(v, int):
            raise TypeError('Expect int but receive: `%s`' % type(v).__name__)
        elif v < 0 or v > CHEBY_FMAX // CHEBY_FSTEP:
            raise ValueError('Invalid sub-band number: %s' % v)
        self._subband_num = v
        self._subband_coef = np.arange(1, v + 1) ** -1.25 + 0.25
        self._subband_freq_set()

    def _subband_freq_set(self, v=None):
        if v is not None:
            self._subband_freq = v
        else:
            tmp = np.arange(CHEBY_FMIN, CHEBY_FMAX, CHEBY_FSTEP)
            self._subband_freq = np.vstack([
                tmp, tmp - np.array([2, 4] + [CHEBY_EDGE] * (len(tmp) - 2))
            ])
        self._subband_param_set()

    def _subband_param_set(self, v=None):
        '''
        Design sub-band filter params. Also you can set value of
        self._subband_param directly by providing an array by `v`.
        '''
        if v is not None:
            self._subband_param = v
        else:
            nyq = self.sample_rate // 2
            self._subband_param = [
                # calc order and natural frequency of the filter: N & Wn
                signal.cheb1ord(
                    [fp / nyq, CHEBY_FMAX / nyq],
                    [fs / nyq, (CHEBY_FMAX + CHEBY_FEDGE) / nyq],
                    gpass=CHEBY_GPASS, gstop=CHEBY_GSTOP)
                for fp, fs in self._subband_freq.T
            ]
        self._subband_filter_set()

    def _subband_filter_set(self, v=None):
        '''Generate Chebyshov I Type IIR filters. Or set to value `v`.'''
        self._subband_filter = v or [
            # calculate numerator/denominator: B & A
            signal.cheby1(n, CHEBY_RP, wn, 'bandpass')
            for n, wn in self._subband_param
        ]

    def preprocess(self, data):
        nyq = self.sample_rate // 2
        N, Wn = signal.buttord([7 / nyq, 90 / nyq], [6 / nyq, 92 / nyq], 3, 40)
        B, A = signal.butter(N, Wn, 'bandpass')
        return signal.lfilter(B, A, data)

    def plot_subband_freqresp(self):
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            return
        for idx, (b, a) in enumerate(self._subband_filter):
            w, h = signal.freqz(b, a)
            w, h = w / np.pi * self.sample_rate / 2, 20 * np.log10(abs(h))
            plt.plot(w, h, label='subband %d' % idx)
        plt.title('Frequency response of sub-band filters used in TRCA')
        plt.xlabel('Frequency [Hz]')
        plt.ylabel('Amplitude [dB]')
        plt.ylim(-100, 20); plt.legend(loc=1); plt.grid()  # noqa: E702
        plt.show()

    def train(self, X):
        '''X should be of shape: n_target x n_channel x n_sample x n_trial'''
        X = np.array(X, ndmin=4)
        if X.shape[:3] != (self.num_target, self.num_channel, self.num_sample):
            raise ValueError('Invalid dataset of shape: {}'.format(X.shape))
        bar = Progbar(target=self.num_target, interval=2)
        for target in range(self.num_target):
            # shape: n_channel x n_sample x n_trial
            data = X[target]
            bar.add(0.25)
            time.sleep(0.1)
            for sb in range(self.num_subband):
                # shape: n_channel x n_sample x n_trial
                sbdata = self.subband(data, sb)
                self._target_coef[target, sb] = np.mean(sbdata, axis=-1)
                bar.add(0.25 / self.num_subband)
                time.sleep(0.1)
                # shape: n_trial x n_channel x n_sample
                tsbdata = sbdata.transpose(2, 0, 1)
                # calc covariance between trials of data on each channel
                # Method 1: by dot multiply
                centered = tsbdata - tsbdata.mean(axis=-1, keepdims=True)
                S = np.sum([
                    np.dot(centered[idx1], centered[idx2].T)
                    for idx1 in range(tsbdata.shape[0] - 1)
                    for idx2 in range(idx1 + 1, tsbdata.shape[0])
                ])
                bar.add(0.25 / self.num_subband)
                # Method 2: by np.cov
                #  nch = self.num_channel
                #  S = np.sum([
                #      np.cov(tsbdata[idx1], tsbdata[idx2])[:nch, nch:]
                #      for idx1 in range(tsbdata.shape[0] - 1)
                #      for idx2 in range(idx1 + 1, tsbdata.shape[0])
                #  ])
                # shape: n_channel x (n_sample*n_trial)
                Q = np.cov(np.concatenate(sbdata, axis=-1))
                value, vector = np.linalg.eig(np.dot(np.linalg.inv(Q), S))
                self.weights[target, sb] = vector[:, 0]
                bar.add(0.25 / self.num_subband)
        bar.update(self.num_target)

    def save(self):
        pass

    def predict(self, X, ensemble=False, *a, **k):
        '''X should be of shape: n_target/n_trial x n_channel x n_sample'''
        X = np.atleast_3d(X)
        assert X.shape[1:] == (self.num_channel, self.num_sample)
        rst = []
        for idx, trial in enumerate(X):
            rst.append(self.predict_one_trial(trial, ensemble))
        return np.array(rst)

    def predict_one_trial(self, X, ensemble=False):
        '''X should be of shape: n_channel x n_sample'''
        # `rou` holds results of shape: n_target x n_subband
        rou = np.zeros((self.num_target, self.num_subband))
        for target in range(self.num_target):
            for sb in range(self.num_subband):
                # trained data shape: n_channel x n_sample
                trained_data = self._target_coef[target, sb]
                # test data shape: n_channel x n_sample
                test_data = self.subband(X, sb)
                if ensemble:
                    # w should be of shape: n_target x n_channel matrix
                    w = self.weights[:, sb, :]
                else:
                    # w should be of shape: 1 x n_channel vector
                    w = self.weights[target, sb, :].reshape(1, -1)
                rou[target, sb] = np.corrcoef(
                    np.dot(w, test_data), np.dot(w, trained_data)
                )[0, 1]
        return np.dot(rou, self._subband_coef)  # n_target vector

    def subband_all(self, data):
        '''data shape: [n_target x] n_channel x n_sample [x n_trial]'''
        return data

    def subband(self, data, sb):
        b, a = self._subband_filter[sb]
        return signal.filtfilt(b, a, data, axis=-1, padlen=0)

    def summary(self):
        pass

# THE END
