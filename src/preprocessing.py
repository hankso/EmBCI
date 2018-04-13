#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Wed Feb 28 10:56:36 2018

@author: Song Tian Cheng
@page:   https://github.com/rotom407

@author: hank
@page:   https://github.com/hankso
"""

# pip install numpy, scipy
import numpy as np
import scipy.signal as signal


def remove_DC(X, *args, **kwargs):
    '''
    Input shape:  n_sample x n_channel x window_size
    Output shape: n_sample x n_channel x window_size
    '''
    return signal.detrend(X, axis=-1)

def notch(X, sample_rate, Q, Hz, *args, **kwargs):
    '''
    Input shape:  n_sample x n_channel x window_size
    Output shape: n_sample x n_channel x window_size
    
    Q: Quality factor
    Hz: target frequence to be notched
    '''
    for b, a in [signal.iirnotch( float(fs)/(sample_rate/2), Q ) \
                 for fs in np.arange(Hz, sample_rate/2, Hz)]:
        X = signal.filtfilt(b, a, X)
    return X

def stft(X, sample_rate, nperseg, noverlap, *args, **kwargs):
    '''
    Short Term Fourier Transform.
    Input shape:  n_sample x n_channel x window_size
    Output shape: n_sample x n_channel x freq x time
    freq = int(1.0 + math.floor( float(nperseg) / 2 ) )
    time = int(1.0 + math.ceil( float(X.shape[-1]) / (nperseg - noverlap) ) )
    '''
    return np.abs(signal.stft(X, fs=sample_rate,
                              nperseg=nperseg,
                              noverlap=noverlap)[2])

def fft(X, sample_rate, *args, **kwargs):
    '''
    Fast Fourier Transform
    Input shape:  n_sample x n_channel x window_size
    Output shape: n_sample x n_channel x window_size/2
    
    Returns
    -------
    freq: frequence bin list, with a length same as amp
    amp:  amptitude of each frequence bin, you can plot
          with plt.plot(freq, amp[0, 0]) to get Amp-Freq img.
    '''
    amp = 2 * abs(np.fft.rfft(X)) / float(len(X))
    amp[:, :, 0] /= 2
    if amp.shape[-1] % 2:
        amp[:, :, -1] /= 2
    freq= np.linspace(0, sample_rate/2, amp.shape[-1])
    return freq, amp

def bandwidth_filter(X, sample_rate, min_freq, max_freq, *args, **kwargs):
    pass

def PSD(X, sample_rate, *args, **kwargs):
    '''
    Power Spectrum Density
    Input shape:  n_sample x n_channel x window_size
    Output shape: n_sample x n_channel x window_size/2
    PSD: np.conjugate(amp) * amp
    Magnitude: np.absolute(amp)
    Angle, Phase: np.angle(amp)
    '''
    tmp = np.fft.fft(X)
    tmp *= np.conjugate(tmp)
    return tmp


class Processer(object):
    def __init__(self, sample_rate, sample_time):
    
    
        '''
        A collection of all available signal preprocessing methods.
        Use this class to offer default params for each fucntion.
        
        # TODO 8: Fix this pickle problem
        
        This class contains two main methods:
            add_preprocesser -- you can input a built-in or user defined
                function to add it to self.preprocessers, examples:
                p = Processer()
                p.add_preprocesser(p.notch)
                p.add_preprocesser(p.fft)
                p.add_preprocesser(numpy.average)
            process -- call this method to preprocess the data with all 
                preprocessers
        
        To make a class whose instance picklable(which is usually not),
        we must define __getstate__ method to return something picklable.
        This is elegant enough but not suitable here. So function
        more detail at https://docs.python.org/2/library/pickle.html
        '''
        
        
        self._fs = sample_rate
        self._ws = sample_rate * sample_time
        
    def check_shape(func):
        def wrapper(self, X):
            if type(X) is not np.ndarray:
                X = np.array(X)
            # simple 1D time series.
            # Input: windowsize
            if len(X.shape) == 1:
                return func(self, X.reshape(1, 1, -1))
            # 2D array
            # Input: n_channel x window_size
            elif len(X.shape) == 2:
                return func(self, X.reshape(1, X.shape[0], X.shape[1]))
            # 3D array
            # Input: n_sample x n_channel x window_size
            elif len(X.shape) == 3:
                return func(self, X)
            # 3D+
            # Input: ... x n_sample x n_channel x window_size
            else:
                raise RuntimeError(('Input data shape {} is not supported.\n'
                                    'Please offer time series 1D data, or '
                                    '(n_channel x window_size) 2D data or '
                                    '(n_sample x n_channel x window_size) '
                                    '3D data.').format(X.shape))
        return wrapper
        
    @check_shape
    def remove_DC(self, X):
        return remove_DC(X)
    
    @check_shape
    def notch(self, X):
        return notch(X, self._fs, Q=50, Hz=50)

    @check_shape
    def stft(self, X):
        # you mustn't normalize because amptitude difference between
        # channels is also important infomation for classification
        #                0           1         2      3
        # pxx.shape: n_sample x n_channels x freq x time
        #                0        2      3         1
        # target:    n_sample x freq x time x n_channels
        nperseg = int(self._fs / 5)
        noverlap = int(self._fs / 5 * 0.67)
        return stft(X, self._fs, nperseg, noverlap)

    @check_shape
    def fft(self, X):
        return fft(X, self._fs)

    @check_shape    
    def bandwidth_filter(self, X):
        return bandwidth_filter(X, self._fs, min_freq=10, max_freq=450)

    @check_shape    
    def PSD(self, X):
        return PSD(X, self._fs)
    
    
if __name__ == '__main__':
    p = Processer(250, 2)
    
    # fake data with shape of (10 samples x 8 channels x 1024 window_size)
    X = np.random.random((10, 8, 1024))
    print('create data with shape {}'.format(X.shape))
    print('after remove DC shape {}'.format(p.remove_DC(X).shape))
    print('after notch shape {}'.format(p.notch(X).shape))
    print('after fft shape {}'.format(p.fft(X)[1].shape))
    print('after stft shape {}'.format(p.stft(X)[2].shape))
    print('after psd shape {}'.format(p.PSD(X).shape))