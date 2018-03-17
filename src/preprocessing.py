#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Wed Feb 28 10:56:36 2018

@author: Song Tian Cheng
@page:   https://github.com/rotom407

@author: Hank
@page:   https://github.com/hankso
"""
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
                              nperseg=nperseg, noverlap=noverlap)[2])

def fft(X, sample_rate, *args, **kwargs):
    pass

def bandwidth_filter(X, sample_rate, min_freq, max_freq, *args, **kwargs):
    pass

def PSD(X, sample_rate, *args, **kwargs):
    pass


class Processer(object):
    def __init__(self, sample_rate, sample_time):
        '''
        A collection of all available signal preprocessing methods.
        Use this class to offer default params for each fucntion.
        
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
# =============================================================================
#         self.preprocessers = []
#         
#     def __getstate__(self):
#         '''
#         make instance of this class picklable
#         '''
#         pass
#     
#     def process(self, data):
#         for func_str in self.preprocessers:
#             data = self.__getattribute__(func_str)(data)
#         return data
#     
#     def add_preprocesser(self, func):
#         self.preprocessers += [func]
# =============================================================================
        
        
    def remove_DC(self, X):
        return remove_DC(X)
    
    def notch(self, X):
        return notch(X, self._fs, Q=40, Hz=50)

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

    def fft(self, X):
        return fft(X, self._fs)
    
    def bandwidth_filter(self, X):
        return bandwidth_filter(X, self._fs, min_freq=10, max_freq=450)
    
    def PSD(self, X):
        return PSD(X, self._fs)
    
    
if __name__ == '__main__':
    p = Processer(250, 2)