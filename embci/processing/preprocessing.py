#!/usr/bin/env python
# coding=utf-8
#
# File: EmBCI/embci/processing/preprocessing.py
# Author: Hankso
# Webpage: https://github.com/hankso
# Time: Wed 28 Feb 2018 11:05:15 CST

# built-in
import traceback

# requirements.txt: data-processing: numpy, scipy
# requirements.txt: necessary: decorator
import numpy as np
import scipy.signal
from decorator import decorator

from . import timed, freqd
from ..io.readers import BaseReader


@decorator
def check_shape(func, self, X, *a, **k):
    if isinstance(X, tuple):
        return func(self, X, *a, **k)
    if isinstance(X, BaseReader):
        X._data = func(self, X._data, *a, **k)
        return X

    # 1D array
    # Input:  1 x window_size
    # Output: result_shape
    # 2D array
    # Input:  n_channel x window_size
    # Output: result_shape
    X = np.atleast_2d(X)
    if X.ndim == 2:
        return func(self, X, *a, **k)

    # 3D array
    # Input:  n_sample x n_channel x window_size
    # Output: n_sample x result_shape
    elif X.ndim == 3:
        return np.array([func(self, sample, *a, **k) for sample in X])

    # 3D+
    # Input: ... x n_sample x n_channel x window_size
    else:
        raise ValueError(
            'Input data shape {} is not supported.\n'.format(X.shape) +
            'Please offer time series (window_size) 1D data, '
            '(n_channel x window_size) 2D data or '
            '(n_sample x n_channel x window_size) 3D data.')


def copy_doc(source):
    def caller(target):
        doc = '\n' + (target.__doc__ or '')
        target.__doc__ = (source.__doc__ or '' + doc).strip()
        return target
    return caller


class SignalInfo(object):
    '''
    This class provides access to a set of time and frequency domain
    signal processing algorithms applying on time-series data.

    Input data usually be buffered with a shape as:
        n_channel x window_size
    where window_size = sample_rate * sample_time
    '''
    def __init__(self, sample_rate):
        self.sample_rate = sample_rate

        # aliases
        self.avr = self.average
        self.var = self.variance
        self.std = self.standard_deviation
        self.cov = self.covariance

        # filter state
        self._b = {}
        self._a = {}
        self._zi = {}

    @check_shape
    def average(self, X):
        '''The most simple feature: average of each channel'''
        return np.average(X, axis=-1).reshape(-1, 1)

    @check_shape
    def rectification_mean(self, X):
        '''Average of rectified signal(absolute value)'''
        return np.average(abs(X), axis=-1).reshape(-1, 1)

    @check_shape
    def variance(self, X):
        '''
        Calculate variance along last axis. Variance measures the `variety` of
        the signal,

        Returns
        -------
        average( (X-average(X)) ** 2 )
        also known as follows in statistics
            DX = E(X-EX)**2 = EX**2 - (EX)**2
        '''
        return np.var(X, axis=-1).reshape(-1, 1)

    @check_shape
    def standard_deviation(self, X):
        '''
        Standard deviation is a measure of the spread of a distribution(signal)
        std(X) = sqrt(var(X))
        '''
        return np.sqrt(self.var(X))

    @check_shape
    def skewness(self, X):
        '''
        Skewness's definition from wiki:
            In probability theory and statistics, skewness is a measure of the
            asymmetry of the probability distribution of a real-valued random
            variable about its mean. The skewness value can be positive or
            negative, or undefined.

        Returns
        -------
        average( (X-average(X)) ** 3 ) / (std(X)) ** 3
        also as
            E(X-EX)**3 / (DX)**(3/2)
        '''
        return self.avr((X - self.avr(X))**3) / self.var(X)**1.5

    @check_shape
    def kurtosis(self, X):
        '''
        Kurtosis's definition from wiki:
            In probability theory and statistics, kurtosis is a measure of the
            "tailedness" of the probability distribution of a real-valued
            random variable.

        Returns
        -------
        average( (X-average(X)) ** 4 ) / (std(X)) ** 4
        also as
            E(X-EX)**4 / (DX)**2
        '''
        return self.avr((X - self.avr(X))**4) / self.var(X)**2

    @check_shape
    def covariance(self, X):
        '''
        Covariance shows the level of which two random variables vary together.
        Here it represent how much two channel time-series EEG data have
        similar changing trend. This might be useful when to handle
        Motion Imaginary EEG data where FP3 and FP4 series vary

        Input shape:  X n_channel x window_size
        Output shape: C n_channel x n_channel
        Meaning:      C[i, j] = similar level of i_channel and j_channel
                      C[i, i] = similar level of i_channel itself
        '''
        return np.cov(X)

    @check_shape
    def correlation_coefficient(self, X):
        '''
        This is samiliar to covariance. The relationship between correlation
        coefficient and covariane is that
            CORR[i, j] = C[i, j] / sqrt(C[i, i] * C[j, j])
        Values of R are between -1 and 1.
        '''
        return np.corrcoef(X)

    @check_shape
    def bandpass(self, X, low, high, order=5,
                 sample_rate=None, register=False):
        nyq = float(sample_rate or self.sample_rate) / 2
        b, a = scipy.signal.butter(order, (low / nyq, high / nyq), 'band')
        if register:
            # store params for real-time filtering
            zi = scipy.signal.lfilter_zi(b, a) * np.average(np.abs(X))
            self._b['band'], self._a['band'], self._zi['band'] = b, a, zi
        return scipy.signal.lfilter(b, a, X)

    def bandpass_realtime(self, x):
        '''
        sample_rate, b, a, and low/high param are all registed by calling
        `SignalInfo.Bandpass_Filter(X, low, high, order, sample_rate)` and
        will be updated by recalling `Bandpass_Filter`
        '''
        assert self._b.get('band') is not None, 'call `bandpass` first!'
        x, self._zi['band'] = scipy.signal.lfilter(
            self._b['band'], self._a['band'],
            np.atleast_1d(x), zi=self._zi['band'])
        return x

    @check_shape
    def notch(self, X, Hz=50, Q=10, sample_rate=None, register=False):
        '''
        Input shape:  n_channel x window_size
        Output shape: n_channel x window_size
        sample_rate: in Hz unit
        Q: Quality factor
        Hz: target frequence to be notched
        '''
        nyq = float(sample_rate or self.sample_rate) / 2
        if register:
            self._b['notch'], self._a['notch'], self._zi['notch'] = [], [], []
        for b, a in [scipy.signal.iirnotch(freq / nyq, Q)
                     for freq in np.arange(Hz, nyq, Hz)]:
            if register:
                # save params
                self._b['notch'].append(b)
                self._a['notch'].append(a)
                self._zi['notch'].append(
                    scipy.signal.lfilter_zi(b, a) * np.average(np.abs(X)))
            # convolve filter with data
            X = scipy.signal.lfilter(b, a, X, axis=-1)
        return X

    def notch_realtime(self, x):
        '''
        Realtime online notch filter,
        Refer to `bandpass_realtime` for more info.
        '''
        assert self._b.get('notch') is not None, 'call `notch` first!'
        zis, self._zi['notch'] = self._zi['notch'], []
        x = np.atleast_1d(x)
        for b, a, zi in zip(self._b['notch'], self._a['notch'], zis):
            x, zi = scipy.signal.lfilter(b, a, x, zi=zi)
            self._zi['notch'].append(zi)
        return x

    @check_shape
    @copy_doc(freqd.autocorrelation)
    def autocorr(self, X):
        return freqd.autocorrelation(X)

    @check_shape
    @copy_doc(timed.root_mean_square)
    def rms(self, X):
        return timed.root_mean_square(X)

    @check_shape
    @copy_doc(freqd.Fast_Fourier_Transform)
    def fft(self, X, sample_rate=None, *a, **k):
        return freqd.Fast_Fourier_Transform(
            X, sample_rate or self.sample_rate, *a, **k)

    def fft_amp_only(self, *a, **k):
        return self.fft(*a, **k)[1]

    @check_shape
    @copy_doc(freqd.Hilbert_Huang_Transform)
    def hht(self, X, sample_rate=None, *a, **k):
        return freqd.Hilbert_Huang_Transform(
            X, sample_rate or self.sample_rate, *a, **k)

    @check_shape
    @copy_doc(freqd.Discret_Wavelet_Transform)
    def dwt(self, X, *a, **k):
        return freqd.Discret_Wavelet_Transform(X, *a, **k)

    @check_shape
    @copy_doc(freqd.Continuous_Wavelet_Transform)
    def cwt(self, X, scales, sample_rate=None, *a, **k):
        return freqd.Continuous_Wavelet_Transform(
            X, scales, sample_rate or self.sample_rate, *a, **k)

    @check_shape
    @copy_doc(freqd.Short_Time_Fourier_Transfrom)
    def stft(self, X, sample_rate=None, *a, **k):
        return freqd.Short_Time_Fourier_Transfrom(
            X, sample_rate or self.sample_rate, *a, **k)

    def stft_amp_only(self, *a, **k):
        return self.stft(*a, **k)[2]

    @check_shape
    @copy_doc(freqd.Wavelet_Decomposition)
    def wavedec(self, X, *a, **k):
        k['sample_rate'] = k.get('sample_rate', self.sample_rate)
        return freqd.Wavelet_Decomposition(X, *a, **k)

    @check_shape
    @copy_doc(timed.baseline)
    def baseline(self, X, smooth=10000.0, p=0.5, niter=10):
        return timed.baseline(X, smooth, p, niter)

    @check_shape
    @copy_doc(timed.envelop)
    def envelop(self, X, method=1):
        return timed.envelop(X, method)

    @check_shape
    @copy_doc(timed.detrend)
    def detrend(self, X, method=1):
        return timed.detrend(X, method)

    @check_shape
    @copy_doc(timed.smooth)
    def smooth(self, X, *a, **k):
        return timed.smooth(X, *a, **k)

    @check_shape
    @copy_doc(timed.synclike)
    def synclike(self, X):
        return timed.synclike(X)


def preprocess(*methods):
    '''
    This is a decorator factory used to register preprocessing methods
    to be executed before feature extraction functions.
    '''
    @decorator
    def caller(func, self, *a, **k):
        '''Decorator to execute all registered preprocess methods'''
        if not hasattr(func, 'pre'):
            func.pre = True
        if not func.pre:
            return func(self, *a, **k)
        a = list(a)
        for method in methods:
            kw = None
            if isinstance(method, list):
                if len(method) == 1:
                    method = method[0]
                elif len(method) == 2:
                    method, kw = method
                else:
                    raise ValueError('unknowen params' + str(method))
            try:
                a[0] = getattr(self.si, method)(a[0], **(kw or {}))
            except Exception:
                traceback.print_exc()
        return func(self, *a, **k)
    return caller


class Features(object):
    def __init__(self, sample_rate=500):
        self.si = SignalInfo(sample_rate)
        self.sample_rate = sample_rate

    def disable_preprocess(self, func):
        if isinstance(func, str):
            func = getattr(self, func)
        func.pre = False

    def enable_preprocess(self, func):
        if isinstance(func, str):
            func = getattr(self, func)
        func.pre = True

    @preprocess('notch', 'detrend', 'envelop',
                ['smooth', {'window_length': 15}])
    def tremor(self, data, distance=25):
        d = distance or (self.sample_rate / 10)

        # # peaks on raw data
        # upper, lower = data.copy(), -data.copy()
        # upper[data < 0] = lower[data > 0] = 0

        # peaks on envelops
        #  data = self.si.envelop(data)

        # smooth
        #  data = self.si.smooth(data, 15)[0]  # combine neighboor peaks

        # # peaks of upper and lower seperately
        # u_peaks, u_height = scipy.signal.find_peaks(data, (0, None), None, d)
        # l_peaks, l_height = scipy.signal.find_peaks(data, (None, 0), None, d)
        # intervals = np.hstack((np.diff(u_peaks), np.diff(l_peaks)))
        # heights = np.hstack((u_height['peak_heights'],
        #                      l_height['peak_heights']))

        # peaks of both upper and lower
        data[data < data.max() / 4] = 0  # filter misleading extramax peaks
        peaks, heights = scipy.signal.find_peaks(data, 0, distance=d)
        intervals = np.diff(peaks)
        heights = heights['peak_heights']

        return (self.sample_rate / np.average(intervals),
                1000 * np.average(heights))

    @preprocess()
    def stiffness(self, data, lowpass=10.0):
        b, a = scipy.signal.butter(4, 10.0 / self.sample_rate)
        return 1000 * self.si.rms(scipy.signal.lfilter(b, a, data, -1))

    @preprocess(['notch'],
                ['envelop', {'method': 1}],
                ['smooth', {'window_length': 10}])
    def movement(self, data):
        return 1000 * np.average(data)

    def energy(self, X, low=2, high=15, sample_rate=None):
        '''
        Intergrate of energy on frequency duration (low, high)
        '''
        if isinstance(X, tuple) and len(X) == 2:
            freq, amp = X
        else:
            freq, amp = self.si.fft(X, sample_rate or self.sample_rate)
        dt = float(freq[1] - freq[0])
        amp = amp[:, int(low / dt):int(high / dt)]**2
        return np.sum(amp, 1) * dt

    def find_max_amp(self, X, low, high, sample_rate=None):
        '''
        Extract peek between frequency duration (n_min, n_max)
        '''
        if isinstance(X, tuple) and len(X) == 2:
            freq, amp = X
        else:
            freq, amp = self.si.fft(X, sample_rate or self.sample_rate)
        dt = float(freq[1] - freq[0])
        amp = amp[:, int(low / dt):int(high / dt)]**2
        return np.array([np.argmax(amp, 1) * dt + low, np.max(amp, 1)])


# THE END
