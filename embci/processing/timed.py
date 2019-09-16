#!/usr/bin/env python3
# coding=utf-8
#
# File: EmBCI/embci/processing/freqd.py
# Authors: Hank <hankso1106@gmail.com>
#          Tian-Cheng SONG <https://github.com/rotom407>
# Create: 2018-02-28 10:56:36

'''Time Domain Digital Signal Processing and Features'''

# built-in
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# requirements.txt: data: numpy, scipy
import numpy as np
import scipy.signal
import scipy.sparse
import scipy.interpolate

__all__ = ('autocorrelation')


def autocorrelation(X):
    '''
    numpy.correlation(a, v, mode='solid') works by convolving `a` with
    reverse of `v` and the result will be clipped by the `mode`.
    np.correlation will do correlation where
        -np.inf < t < np.inf
    and normal autocorrelation will do it where
        0 <= t < np.inf
    So the last half of np.correlation result will be the good one.
    '''
    rst = np.array([np.correlate(ch, ch, mode='same') for ch in X])
    return rst[:, (rst.shape[1] // 2):]


def root_mean_square(X):
    '''Root Mean Square'''
    return np.sqrt(np.mean(np.square(X), -1).reshape(-1, 1))


def baseline(X, smooth=1e4, p=0.5, niter=10):
    '''
    This is python version implementation of `Asymmetric Least Squares
    Smoothing` by P. Eilers and H. Boelens in 2005. The paper is free and
    you can find it on google. It's modified for better performance. Origin
    answer can be found at https://stackoverflow.com/question/29156532/
    The interesting thing is, when set p to 1 or 0, the result is actually
    corresponding upper and lower envelop of the signal.
    '''
    rst = []
    L = X.shape[1]
    D = scipy.sparse.diags([1, -2, 1], [0, -1, -2], shape=(L, L - 2))
    tmp = smooth * D.dot(D.transpose())
    for ch in X:
        w = np.ones(L)
        for i in np.arange(niter):
            W = scipy.sparse.spdiags(w, 0, L, L)
            z = scipy.sparse.linalg.spsolve(W + tmp, w * ch)
            w = p * (ch > z) + (1 - p) * (ch < z)
        rst += [z]
    return np.array(rst)


def envelop(X, method=1):
    '''
    There are two ways to get envelop of a signal.

    1. Hilbert Transform
    2. Interpolation of all relative extrema: scipy.signal.argrelextrema,

    Default is the last one, which is a modified version of
    `pyhht.utils.get_envelops` to support multi-channel time-series data.

    Notes
    -----
    The difference between interpolation and curve fitting is that when
    you fit a curve with points, these points may not be on result curve.
    But the advantage of interpolation is that it will predict values
    based on points beside them. So points will be exactly on result curve.
    In scipy.interpolate module, there are many choices to interpolate by
    points, here we use scipy.interpolate.spl* methods, because it's
    relatively fast and the result is nice.
    '''
    if method == 1:
        return abs(scipy.signal.hilbert(X, axis=-1))
    elif method == 2:
        nch, wsize = X.shape
        # find indexs of max values
        maxs = [scipy.signal.argrelmax(ch)[-1] for ch in X]
        mins = [scipy.signal.argrelmin(ch)[-1] for ch in X]
        # index lists should start with 0 & end with wsize - 1
        maxs = [np.concatenate(([0], ms, [wsize - 1])) for ms in maxs]
        mins = [np.concatenate(([0], ms, [wsize - 1])) for ms in mins]
        rst = []
        t = np.arange(wsize)
        for ch in np.arange(nch):
            # construct curve with points (index, value)
            maxd = scipy.interpolate.splrep(t[maxs[ch]], X[ch][maxs[ch]])
            mind = scipy.interpolate.splrep(t[mins[ch]], X[ch][mins[ch]])
            # interpolate points between above indexs
            rst.append([scipy.interpolate.splev(t, maxd),
                        scipy.interpolate.splev(t, mind)])
        return np.array(rst)


def detrend(X, method=1):
    '''
    remove DC part of raw signal
    '''
    if method == 1:
        return scipy.signal.detrend(
            X, axis=-1, bp=np.arange(0, X.shape[1], 200))
    elif method == 2:
        return X - baseline(X)


def smooth(X, window_length=50, method=1):
    '''
    Smoothing a wave/signal may be achieved through many different ways.

    Parameters
    ----------
    X : array_like
        with shape of n_channel x window_size
    window_length : number
        length of window used to cut raw data down, default 20
    method : int
        see Notes for details, defualt 1.

    Notes
    -----
    1. convolve with (np.ones(n) / n) or wavelet: this is filtering way
    2. pyhht.EMD or scipy.signal.hilbert: this is decomposition way
    3. RMS(root-mean-square): Calculate rms value on a moving window on
        source signal and use it as point of new signal. The result is
        exactly same as method 1.
    '''
    if method == 1:
        filters = np.ones(window_length) / window_length
        rst = np.array([np.convolve(ch, filters, mode='same') for ch in X])
    elif method == 2:
        # TODO: pyhht.EMD smoothing
        raise NotImplementedError
    else:
        cols = X.shape[1]
        rst = np.zeros(X.shape)
        for i in range(cols):
            wl = max(0, i - window_length)
            wh = min(cols, i + window_length)
            rst[:, i] = root_mean_square(X[:, wl:wh])[:, 0]
    return rst


def synclike(X):
    '''
    Sychronization likelihood is the method to abstract a state vector
    from a time-series data. This vector is distinguishable in state space,
    thus representing current state(raw data pattern).
    In a time interval, if state vectors of each frequency ranges (α|β|γ..)
    of each channels are similar, we can say sync_level of this people is
    high at present and vice versa. It has been discovered that many kinds
    of nervous diseases are related to out-sync of brain activities, such
    as Alzheimer's Disease. By comparing state vector we can tell how
    synchronous the subject's brain is.
    '''
    raise

# THE END
