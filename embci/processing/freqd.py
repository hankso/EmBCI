#!/usr/bin/env python
# coding=utf-8
#
# File: EmBCI/embci/processing/freqd.py
# Author: Hankso
# Webpage: https://github.com/hankso
# Author: Song Tian Cheng
# Webpage: https://github.com/rotom407
# Time: Wed 28 Feb 2018 10:56:36 CST

'''Frequency Domain Digital Signal Processing and Features'''


# requirements.txt: data-processing: numpy, scipy
# requirements.txt: necessary: pywavelets, pyhht
# requirements.txt: necessary: decorator
# TODO: rewrite python-pywt
# apt-install.list: python-tk
# note1:
#     `apt install python-pywt` is recommended because pywavelets need to be
#     compiled with gcc and so on. The package name may be `python-pywavelets`
#     or `python-wavelets` or `python-pywt`
# note2:
#     pyhht relies on python-tk(as well as other dependences), so install it
#     by apt install or pip install
import pywt
import pyhht
import numpy as np
import scipy

from .timed import autocorrelation


def Fast_Fourier_Transform(X, sample_rate=500, resolution=1, *a, **k):
    '''
    People use FT(Fourier Transform) to extract frequency domain
    info from time domain data in mathmatic questions. But when
    processing signals, DFT(Discret Fourier Transform) is a more
    practice way for computer calculation. And FFT(Fast discret
    Fourier Transform) is much more commonly used because it is
    better at handling time-varying signals(you can add windows).

    There are four steps to get useful result of fft.
    1. raw = np.fft.fft(X), here raw is a complex ndarray
    2. amp = np.abs(raw[:num / 2]), remove latter half of raw and
        convert the rest data into real number. Result of fft is
        symmetric in the real part.
    3. samples = len(X) and raw /= samples
    4. Remove Nyquist point, that is:
        if samples is odd number, amp *= 2 except first point(freq=0)
        if samples is even number, amp *= 2 except first and last points

    Parameters
    ----------
    X : array-like
        raw data with shape of n_channels x window_size
    sample_rate : int
        sample rate of signal, always known as `fs`
    resolution : number
        number of points to calculate within one Hz, default is 1 point/Hz.
        Assuming resolution is 3 and `rst = fft(X, None, 3)`, then
            rst[30] is amp of 10.0000Hz
            rst[31] is amp of 10.3333Hz
            rst[32] is amp of 10.6666Hz
            rst[33] is amp of 11.0000Hz

    Returns
    -------
    freq : ndarray
        freq = np.linspace(0, sample_rate / 2, length)
    amp : ndarray
        2D array with a shape of n_channel x length
        length = sample_rate / 2 * resolution
    '''
    n = sample_rate * resolution
    amp = 2 * abs(np.fft.rfft(X, int(n), axis=-1)) / float(X.shape[1])
    amp[:, 0] /= 2
    if X.shape[1] % 2:
        amp[:, -1] /= 2
    freq = np.linspace(0, sample_rate / 2, amp.shape[1] - 1)
    return freq, amp[:, :-1]


def Short_Time_Fourier_Transfrom(X, sample_rate=500, nperseg=None,
                                 noverlap=None, *a, **k):
    '''
    Short Time Fourier Transform.
    Input shape:  n_channel x window_size
    Output shape: n_channel x freq x time
    freq = int(1.0 + math.floor( float(nperseg) / 2 ) )
    time = int(1.0 + math.ceil(float(X.shape[-1]) / (nperseg - noverlap)))

    Returns
    -------
    out : tuple
        (freq, time, amp)
    '''
    #                0           1         2      3
    # pxx.shape: n_sample x n_channels x freq x time
    #                0        2      3         1
    # target:    n_sample x freq x time x n_channels
    f, t, amp = scipy.signal.stft(
        X, sample_rate, 'hann',
        nperseg=nperseg or int(sample_rate / 5.0),
        noverlap=noverlap or int(sample_rate / 5.0 * 0.67))
    return f, t, np.abs(amp)


def Discret_Wavelet_Transform(X, wavelet=None, *a, **k):
    '''
    The nature of DWT is to send raw signal S into one pair of filters,
    high pass filter H and low pass filter L, which are actually the
    wavelet you choose. Next, convolve S with H and L, thus generating
    two filtered signal Sh and Sl with length of ( len(S) + len(H) - 1 )
    Then, downsample Sh and Sl and cut off len(H) / 2 points at each end
    of signals to avoid distortion( Sh = Sh[len(H) / 2 : -len(H) / 2] ).
    That's all! What we get now is entirely high-freq part and low-freq
    part of raw signal, and this process is the DWT in my understanding.

                high pass     downsampling  +--------+
            +====>[ H ]=========>[ 2! ]====>+ Sh(cD) |
            |     filter                    +--------+
    +---+   |
    | S +==>+
    +---+   |
            |    low pass     downsampling  +--------+
            +====>[ L ]=========>[ 2! ]====>+ Sl(cA) |
                  filter                    +--------+

    Sometimes DWT is called FWT as well, which stands for Fast-WT. Indeed,
    DWT is really really fast and efficient. By constructing special QMFs
    the corresponding DWT can be computed via filtering and downsampling,
    which is the state-of-the-art algorithm to compute DWTs today. You do
    not need the scaling function to compute the DWT, it is just an
    implementation detail that FWT process.

    P.S. Sh, Sl is more known as cD(detailed coefficients vector) and
    cA(approximate coefficients vector) in some tutorials.
    '''
    if wavelet not in pywt.wavelist():
        wavelet = 'haar'
    return pywt.dwt(X, wavelet)


def convolve_fft(X, filters):
    '''
    Multiple on frequency domain is convolve on time domain.
    '''
    assert X.shape[1] == filters.shape[1]
    m, n = X.shape
    f1 = np.fft.fft(X, axis=-1)
    f2 = np.fft.fft(filters, axis=-1)
    return np.real(np.fft.ifft(f1 * f2))


def convolve2d_fft(X, filters):
    '''
    See Also
    --------
    convolve_fft
    '''
    assert X.shape == filters.shape
    m, n = X.shape
    f1 = np.fft.fft2(X)
    f2 = np.fft.fft2(filters)
    return np.real(np.fft.ifft2(f1 * f2))


def Continuous_Wavelet_Transform(X, scales, sample_rate=500, wavelet=None,
                                 use_scipy_signal=True, *a, **k):
    '''
    Unforturnately it's a very misleading terminology here to name it by
    Continuous Wavelet Transform. Actually, in engineering, both cwt and
    dwt are digital, point-by-point transform algorithums that can easily
    implemented on a computer. If two mathematicians talk about CWT, it
    really mean Continuous-WT. But here, CWT just misleading people.

    A cwt is a discret operation as well as dwt. The difference is how they
    convolve signal with wavelet. CWT will convolve signal with wavelet
    moveing foreward point-by-point while DWT moves window-by-window. When
    decomposition level grows, wavelet need to be expanded in length. CWT
    wavelet length will be 2, 3, 4, 5, ... and DWT will be 2, 4, 8, ...
    '''
    # check params
    if np.isscalar(scales):
        scales = np.arange(1, scales + 1)
    scales = np.array(scales)
    assert 0 not in scales
    if not use_scipy_signal and wavelet not in pywt.wavelist():
        wavelet = 'morl'

    # prepare wavelets
    if use_scipy_signal:
        wavelets = [wavelet(min(10 * scale, X.shape[1]), scale)
                    for scale in scales]
    else:
        int_psi, x = pywt.integrate_wavelet(wavelet, precision=10)
        wavelets = []
        for scale in scales:
            j = np.arange(scale * (x[-1] - x[0]) + 1)
            j = np.floor(j / scale / (x[1] - x[0]))
            wavelets.append(int_psi[np.int32(j[j < len(int_psi)])][::-1])

    # convolve
    coef = np.array([[np.convolve(ch, w, mode='same') for w in wavelets]
                     for ch in X])
    if use_scipy_signal:
        freq = None
    else:
        coef = - np.sqrt(scales).reshape(len(scales), 1) * np.diff(coef)
        freq = (pywt.central_frequency(wavelet, 10) / scales * sample_rate)
    return coef, freq


def Wavelet_Decomposition(X, wavelet=None, use_cwt=False, sample_rate=None,
                          scales=None, *a, **k):
    '''
    While the difference between a wavelet decomposition and a wavelet
    transform is that decomposing is multilevel and transform is single
    level:
        wavedec(level=n) <==> dwt * n
    dwt returns cA1 and cD1
    wavedec returns cAn cDn cDn-1 ... cD1
    '''
    if use_cwt:
        c, f = cwt(X, (scales or 10), sample_rate,
                   (wavelet or scipy.signal.ricker))
    else:
        if wavelet not in pywt.wavelist():
            wavelet = 'haar'
        return pywt.wavedec(X, wavelet)


def Hilbert_Huang_Transform(X, sample_rate=500, *a, **k):
    '''
    HHT(Hilbert Huang Transform) is a method to extract signal information
    on both time and frequency domain, it performs Empirical Mode
    Decomposition(EMD) and Hilbert transform based Signal Analysis.
    First raw signal will be decomposed into Intrinsic Mode Functions(IMFs)
    based on algorithm presented by Huang et al. in 1998. IMFs are actually
    components of raw signal within different frequency durations.
    Comparing to samiliar decomposition algrithm Wavelet Transform, EMD
    generates much precies result both in time domain and frenqucy domain.
    HSA can compute instant frenquency of IMFs, thus outputing time-freq
    spectrum.

    +---+   EMD   +------+    HSA    +--------------------+
    | S +---------+ IMFs +-----------+ Freq-Time spectrum |
    +---+         +------+           +--------------------+

    Notes
    -----
    Difference between two hilbert in scipy:
        scipy.signal.hilbert(x) = x + scipy.fftpack.hilbert(x) * j

    1. scipy.fftpack.hilbert(x) ==> y
    2. scipy.signal.hilbert(x) ==> x + yj
        y is hilbert tranform of x, this result is called analytic signal
    '''
    imfs = np.array([pyhht.EMD(ch).decompose() for ch in X])
    analytic_signal = scipy.signal.hilbert(imfs, axis=-1)
    inst_phase_wrapped = np.angle(analytic_signal)
    inst_phase = np.unwrap(inst_phase_wrapped, axis=-1)
    return np.diff(inst_phase, axis=-1) / (2 * np.pi) * sample_rate


def Energy_Spectrum(X):
    '''
    '''
    raise NotImplementedError


def Scalogram(X, sample_rate=None, *a, **k):
    rst = cwt(X, np.arange(1, 31), sample_rate, scipy.signal.ricker, True)
    '''
    plt.imshow(
            rst, extent=[-1, 1, 1, 31], cmap='PRGn', aspect='auto',
            vmax=abs(rst).max(), vmin=-abs(rst).max())
    '''
    return rst


def Power_Spectrum(X, sample_rate=None, method=2, *a, **k):
    '''
    There are two kinds of defination of power spectrum(PS hereafter).
    1. PS = fft(autocorrelation(X))
        This is Winner-Khintchine defination
    2. PS = abs(fft(X))**2 / sample_time
        This one is `P = W / S` defination (power equals to energy
        divided by time duration), and 'W = abs(fft(X))**2' is known
        as energy spectrum.
    But here we implement
        PS = fft**2 / freq-duration
    Unit of PSD(Power Spectral Density) will be 'W / Hz' instead of 'W / s'

    Parameters
    ----------
    X : array-like
    sample_rate : number, optional

    Returns
    -------
    freq, power
    '''
    if method == 1:
        return fft(autocorrelation(X), sample_rate)
    elif method == 2:
        freq, amp = fft(X, sample_rate)
        return freq, amp**2 / (freq[1] - freq[0])


# =============================================================================
# alias

fft = Fast_Fourier_Transform
stft = Short_Time_Fourier_Transfrom
hht = Hilbert_Huang_Transform
cwt = Continuous_Wavelet_Transform
dwt = Discret_Wavelet_Transform
wavedec = Wavelet_Decomposition

# THE END
