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


# =============================================================================
# constants

NUM_SUBBAND = 5    # number of sub-bands (int)
CHEBY_RP    = 0.4  # maximum ripple allowed in the passband (float)
CHEBY_GPASS = 3    # maximum loss in the passband (dB)
CHEBY_GSTOP = 40   # minimum attenuation in the stopband (dB)
CHEBY_FMIN  = 6    # minimum frequency of sub-bands (Hz)
CHEBY_FSTEP = 8    # sub-band width in frequency (Hz)
CHEBY_FMAX  = 90   # maximum frequency of sub-bands (Hz)
CHEBY_FEDGE = 10   # edge frequency for maximum frequency of sub-bands (Hz)
CHEBY_EDGE  = 6    # edge frequency between passband and stopband (Hz)

_default_params = dict(
    srate=250, nchannel=8, nsample=0.5*250, targets=np.arange(8, 16, 0.2)
)


class Model(object):
    def __init__(self, srate, nchannel, nsample, targets,
                 nsubband=NUM_SUBBAND, **k):
        self._config = {
            'srate':    int(srate),
            'nchannel': int(nchannel),
            'nsample':  int(nsample),
            'ntarget':  len(targets),
            'targets':  list(targets),
        }
        self.nsubband = nsubband
        self.update_config(self._config, **k)

    @classmethod
    def from_config(cls, cfg):
        return cls(**cfg)

    def update_config(self, cfg=None, **cfgs):
        if cfg is not None:
            if not isinstance(cfg, dict):
                raise TypeError('Invalid config dict: `{}`'.format(cfg))
            cfgs.update(cfg)
        for attr, value in cfgs.items():
            setattr(self, attr, value)
        self._config['ntarget'] = len(self._config['targets'])
        self._trained = np.zeros((
            self.ntarget, self.nsubband, self.nchannel, self.nsample
        ))
        self._refdata = np.ones((
            self.ntarget, 2 * self.nchannel, self.nsample
        ))
        self._refdata_set()
        self._weights = np.ones((self.ntarget, self.nsubband, self.nchannel))
        self._model_trained = False

    def get_config(self):
        dct = self._config.copy()
        if self._model_trained:
            dct['_weights'] = self._weights.copy()
            dct['_trained'] = self._trained.copy()
        return dct

    def __getattr__(self, attr):
        try:
            return self._config[attr]
        except KeyError as e:
            raise AttributeError(*e.args)

    def __setattr__(self, attr, value):
        if not attr.startswith('_') and attr in self._config:
            self._config[attr] = value
        else:
            object.__setattr__(self, attr, value)

    @property
    def nsubband(self):
        return self._subband_num

    @nsubband.setter
    def nsubband(self, v):
        if v < 0 or v > CHEBY_FMAX // CHEBY_FSTEP:
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
            nyq = self.srate // 2
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

    def _refdata_set(self, freqs=None):
        '''
        Reference data used in FilterBank CCA.
        Parameters
        ----------
        freqs : list
            frequency of each target
        '''
        x = np.arange(0, self.nsample) / self.srate
        for n, freq in enumerate(freqs or self.targets):
            for ch in range(self.nchannel):
                self._refdata[n, 2*ch:2*(ch + 1)] = [
                    np.sin(2 * np.pi * x * (ch + 1) * freq),
                    np.cos(2 * np.pi * x * (ch + 1) * freq)
                ]

    def preprocess(self, data):
        nyq = self.srate // 2
        N, Wn = signal.buttord([7 / nyq, 90 / nyq], [5 / nyq, 98 / nyq], 3, 40)
        B, A = signal.butter(N, Wn, 'bandpass')
        return signal.lfilter(B, A, data, -1)

    def resize(self, data):
        data = np.atleast_2d(data)
        assert data.ndim == 2, str(data.shape)
        nch, nsp = data.shape
        if nch > self.nchannel or nsp > self.nsample:
            data = data[:self.nchannel, :self.nsample]
        elif nch < self.nchannel or nsp < self.nsample:
            pad_width = [(0, self.nchannel - nch), (0, self.nsample - nsp)]
            data = np.pad(data, pad_width=pad_width, mode='constant')
        print('model.resize', (nch, nsp), data.shape)
        return data

    def plot_subband_freqresp(self):
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            return
        for idx, (b, a) in enumerate(self._subband_filter):
            w, h = signal.freqz(b, a)
            w, h = w / np.pi * self.srate / 2, 20 * np.log10(abs(h))
            plt.plot(w, h, label='subband %d' % idx)
        plt.title('Frequency response of sub-band filters used in TRCA')
        plt.xlabel('Frequency [Hz]')
        plt.ylabel('Amplitude [dB]')
        plt.ylim(-100, 20); plt.legend(loc=1); plt.grid()          # noqa: E702
        plt.show()

    def train(self, X, callback=None):
        '''X should be of shape: n_target x n_channel x n_sample x n_trial'''
        X = np.array(X, ndmin=4)
        if X.shape[:3] != (self.ntarget, self.nchannel, self.nsample):
            raise ValueError('Invalid dataset of shape: {}'.format(X.shape))
        callback = callback or self.train_callback_default
        callback(0)
        for target in range(self.ntarget):
            # shape: n_channel x n_sample x n_trial
            data = X[target]
            callback(0.25 / self.ntarget)
            time.sleep(0.1)
            for sb in range(self.nsubband):
                # shape: n_trial x n_channel x n_sample
                sbdata = self.subband(data.transpose(2, 0, 1), sb)
                # shape: n_channel x n_sample
                self._trained[(target, sb)] = np.mean(sbdata, axis=0)
                callback(0.25 / self.nsubband / self.ntarget)
                time.sleep(0.01)
                # calc covariance between trials of data on each channel
                # Method 1: by dot multiply
                centered = sbdata - sbdata.mean(axis=-1, keepdims=True)
                # shape: [n_trial*n_trial-1] x n_channel x n_channel
                S = np.sum([
                    # shape: n_channel x n_channel
                    np.dot(centered[idx1], centered[idx2].T)
                    for idx1 in range(sbdata.shape[0])
                    for idx2 in range(sbdata.shape[0])
                    if idx1 != idx2
                ], axis=0)
                callback(0.25 / self.nsubband / self.ntarget)
                time.sleep(0.01)
                # Method 2: by covariance
                #  nch = self.nchannel
                #  S = np.sum([
                #      np.cov(tsbdata[idx1], tsbdata[idx2])[:nch, nch:]
                #      for idx1 in range(sbdata.shape[0])
                #      for idx2 in range(sbdata.shape[0])
                #      if idx1 != idx2
                #  ])
                # shape: n_channel x (n_sample*n_trial)
                UX = np.concatenate(sbdata, axis=-1)
                # shape: n_channel x n_channel
                Q = np.dot(UX, UX.T)
                value, vector = np.linalg.eig(np.dot(np.linalg.inv(Q), S))
                self._weights[(target, sb)] = vector[:, 0]
                callback(0.25 / self.nsubband / self.ntarget)
        callback(1)
        self._model_trained = True

    def predict(self, X, ensemble=False, *a, **k):
        '''X should be of shape: n_target/n_trial x n_channel x n_sample'''
        X = np.atleast_3d(X)
        assert X.shape[1:] == (self.nchannel, self.nsample), str(X.shape)
        result = []
        for idx, trial in enumerate(X):
            if self._model_trained:
                rst = self.predict_one_trca(trial, ensemble)
            else:
                rst = self.predict_one_fbcca(trial)
            rst -= rst.min()
            rst /= rst.sum()
            if rst.max() < 1.3 / self.ntarget:
                rst = -1
            else:
                rst = rst.argmax()
            result.append(rst)
        return np.array(result)

    def predict_one_trca(self, X, ensemble=False):
        '''X should be of shape: n_channel x n_sample'''
        assert X.shape == (self.nchannel, self.nsample)
        # `rou` holds results of shape: n_subband x n_target
        rou = np.zeros((self.nsubband, self.ntarget))
        for sb in range(self.nsubband):
            # test data shape: n_channel x n_sample
            test_data = self.subband(X, sb)
            for target in range(self.ntarget):
                # trained data shape: n_channel x n_sample
                trained_data = self._trained[target, sb]
                if ensemble:
                    # w should be of shape: 1 x n_channel matrix
                    w = self._weights[:, sb, :].mean(0, keepdims=True)
                else:
                    # w should be of shape: 1 x n_channel vector
                    w = self._weights[target, sb, :].reshape(1, -1)
                rou[sb, target] = np.corrcoef(
                    np.dot(w, test_data), np.dot(w, trained_data)
                ).diagonal(1)
        return np.dot(rou.T, self._subband_coef)  # n_target vector

    def predict_one_fbcca(self, X):
        '''X should be of shape: n_channel x n_sample'''
        assert X.shape == (self.nchannel, self.nsample)
        if not hasattr(self, '_cca'):
            from sklearn.cross_decomposition import CCA
            # first canonical correlation coefficience
            self._cca = CCA(n_components=1)
        # `rou` holds results of shape: n_subband x n_target
        rou = np.zeros((self.nsubband, self.ntarget))
        for sb in range(self.nsubband):
            # test data shape: n_channel x n_sample
            test_data = self.subband(X, sb)
            for target in range(self.ntarget):
                # reference data shape: (n_channel*2) x n_sample
                ref_data = self._refdata[target]
                # calculate the first canonical correlation coefficience
                u, v = self._cca.fit_transform(test_data.T, ref_data.T)
                rou[(sb, target)] = np.corrcoef(u.T, v.T).diagonal(1)
        return np.dot(rou.T, self._subband_coef)  # n_target vector

    def subband(self, arr, sb):
        '''data shape: [[n_target x] n_trial x] n_channel x n_sample'''
        assert arr.shape[-2:] == (self.nchannel, self.nsample), str(arr.shape)
        b, a = self._subband_filter[sb]
        return signal.filtfilt(b, a, arr, axis=-1, padlen=0)

    def save(self):
        return self

    def load(self, fn):
        return self

    def information_transfer_rate(self, acc, num=None, ts=None):
        acc = float(acc)
        num = num or self.ntarget
        ts = ts or (self.srate / self.nsample)
        if acc < 0 or 1 < acc:
            raise ValueError('Valid accuracy should be [0, 1]: %f' % acc)
        elif acc < (1 / num):
            itr = 0
        elif acc == 1:
            itr = np.log2(num)
        else:
            itr = np.log2(num * acc**acc * ((1 - acc) / (num - 1))**(1 - acc))
        return itr * 60 / ts

    def train_callback_default(self, v):
        if v in [0, 1]:
            self._value = v
        elif 0 < v < 1:
            self._value += v
        print('\rTraining: %.2f%%' % (self._value * 100), end='')

    def train_callback_progbar(self, v):
        if not hasattr(self, '_bar'):
            if 'Progbar' not in globals():
                from embci.utils import TempStream
                with TempStream(stderr=None):
                    from keras.utils.generic_utils import Progbar
            self._bar = Progbar(target=self.ntarget, interval=2)
        if v in [0, 1]:
            self._bar.update(v * self.ntarget)
        elif 0 < v < 1:
            self._bar.add(v * self.ntarget)
        else:
            pass


# THE END
