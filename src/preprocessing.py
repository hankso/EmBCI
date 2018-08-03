#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Wed Feb 28 10:56:36 2018

@author: Song Tian Cheng
@page:   https://github.com/rotom407

@author: hank
@page:   https://github.com/hankso
"""
import os
import sys; sys.path += ['../utils']
import IO


# pip install numpy, scipy, pywavelets, pyhht
# apt install python-tk
# note1:
#     `apt install python-pywt` is recommended because pywavelets need to be
#     compiled with gcc and so on. The package name may be `python-pywavelets`
#     or `python-wavelets` or `python-pywt`
# note2:
#     pyhht relies on python-tk(as well as other dependences), so install it
#     by apt install or pip install
import numpy as np
import pywt
import scipy
from scipy import signal, sparse, interpolate as ip
import pyhht

__dir__ = os.path.dirname(os.path.abspath(__file__))
__filename__ = os.path.basename(__file__)



class Signal_Info(object):
    '''
    I am learning how to handle EEG data, which can be collected by varieties
    of hardwares such as Mindset(Neurosky) and Epoc(Emotiv), etc.

    This class is used for extracting features from input time series data.

    Input data usually be buffered with a shape as:
        n_channel x window_size, where window_size = sample_rate * sample_time
    '''
    def __init__(self, sample_rate):
        self._fs = sample_rate

        # alias
        self.avr = self.Average
        self.var = self.Variance
        self.std = self.Standard_Deviation
        self.cov = self.Covariance
        self.rms = self.Root_Mean_Square

        self.remove_DC = self.Detrend
        self.bandpass = self.Bandpass_Filter

        self.fft = self.Fast_Fourier_Transform
        self.hht = self.Hilbert_Huang_Transform
        self.dwt = self.Discret_Wavelet_Transform
        self.cwt = self.Continuous_Wavelet_Transform
        self.stft = self.Short_Time_Fourier_Transfrom
        self.wavedec = self.Wavelet_Decomposition


    def _check_shape(func):
        def param_collector(self, X, *args, **kwargs):
            if isinstance(X, tuple):
                return func(self, X, *args, **kwargs)
            if isinstance(X, IO._basic_reader):
                X._data = param_collector(self, X._data, *args, **kwargs)
                return X
            if not isinstance(X, np.ndarray):
                X = np.array(X)

            # simple 1D time series
            # Input:  window_size
            # Resize: n_channel x window_size
            # Output: result_shape
            if len(X.shape) == 1:
                return func(self, X.reshape(1, -1), *args, **kwargs)

            # 2D array
            # Input:  n_channel x window_size
            # Output: result_shape
            elif len(X.shape) == 2:
                return func(self, X, *args, **kwargs)

            # 3D array
            # Input:  n_sample x n_channel x window_size
            # Output: n_sample x result_shape
            elif len(X.shape) == 3:
                return np.array([func(self, sample, *args, **kwargs) \
                                 for sample in X])

            # 3D+
            # Input: ... x n_sample x n_channel x window_size
            else:
                raise RuntimeError(('Input data shape {} is not supported.\n'
                                    'Please offer time series (window_size) 1D'
                                    ' data, (n_channel x window_size) 2D data '
                                    'or (n_sample x n_channel x window_size) '
                                    '3D data.').format(X.shape))
        param_collector.__doc__ = func.__doc__
        param_collector.__name__ = func.__name__
        return param_collector

    @_check_shape
    def Average(self, X):
        '''The most simple feature: average of each channel'''
        return np.average(X, axis=-1).reshape(-1, 1)

    @_check_shape
    def Rectification_mean(self, X):
        '''Average of rectified signal(absolute value)'''
        return np.average(abs(X), axis=-1).reshape(-1, 1)

    @_check_shape
    def Variance(self, X):
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

    @_check_shape
    def Standard_Deviation(self, X):
        '''
        Standard deviation is a measure of the spread of a distribution(signal)
        std(X) = sqrt(var(X))
        '''
        return np.sqrt(self.var(X))

    @_check_shape
    def Skewness(self, X):
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
        return (self.avr((X-self.avr(X))**3) /
                self.var(X)**1.5)

    @_check_shape
    def Kurtosis(self, X):
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
        return (self.avr((X-self.avr(X))**4) /
                self.var(X)**2)

    @_check_shape
    def Covariance(self, X):
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

    @_check_shape
    def Correlation_Coefficient(self, X):
        '''
        This is samiliar to covariance. The relationship between correlation
        coefficient and covariane is that
            R[i, j] = C[i, j] / sqrt(C[i, i] * C[j, j])
        Values of R are between -1 and 1.
        '''
        return np.corrcoef(X)

    @_check_shape
    def Autocorrelation(self, X):
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
        return rst[:, rst.shape[1]/2:]

    @_check_shape
    def Root_Mean_Square(self, X):
        return np.sqrt(np.mean(np.square(X), -1).reshape(-1, 1))

    @_check_shape
    def Detrend(self, X):
        '''
        remove DC part of raw signal
        '''
        return signal.detrend(X, axis=-1)

    @_check_shape
    def baseline(self, X, smooth=1e4, p=0.5, niter=10):
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
        D = sparse.diags([1,-2,1],[0,-1,-2], shape=(L , L-2))
        tmp = smooth * D.dot(D.transpose())
        for ch in X:
            w = np.ones(L)
            for i in np.arange(niter):
                W = sparse.spdiags(w, 0, L, L)
                z = sparse.linalg.spsolve(W + tmp, w * ch)
                w = p * (ch > z) + (1 - p) * (ch < z)
            rst += [z]
        return np.array(rst)

    @_check_shape
    def Bandpass_Filter(self, X, sample_rate=None):
        return X
        sample_rate  = sample_rate or self._fs
        # return bandwidth_filter(X, self._fs, min_freq=10, max_freq=450)

    @_check_shape
    def notch(self, X, sample_rate=None, Q=60, Hz=50, *args, **kwargs):
        '''
        Input shape:  n_channel x window_size
        Output shape: n_channel x window_size
        sample_rate: in Hz unit
        Q: Quality factor
        Hz: target frequence to be notched
        '''
        sample_rate = sample_rate or self._fs
        for b, a in [signal.iirnotch( float(fs)/(sample_rate/2), Q ) \
                     for fs in np.arange(Hz, sample_rate/2, Hz)]:
            X = scipy.signal.filtfilt(b, a, X, axis=-1)
        return X

    @_check_shape
    def smooth(self, X, window_length=50, method=1):
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
        1 np.convolve(np.ones(n)/n | wavelet): this is filtering way
        2 pyhht.EMD | scipy.signal.hilbert: this is decomposition way
        3 RMS(root-mean-square): Calculate rms value on a moving window on
          source signal and use it as point of new signal. The result is
          exactly same as method 1.
        '''
        assert method in [1, 2, 3]
        if method == 1:
            filters = np.ones(window_length) / float(window_length)
            rst = np.array([np.convolve(ch, filters) for ch in X])
        elif method == 2:
            pass
        else:
            l = X.shape[1]
            rst = np.zeros(X.shape)
            for i in range(l):
                wl = max(0, i-window_length)
                wh = min(l, i+window_length)
                rst[:, i] = self.rms(X[:, wl:wh])[:, 0]
        return rst


    @_check_shape
    def envelop(self, X, method=2):
        '''
        There are two ways to get envelop of a signal.
        1 Hilbert Transform
        2 Interpolation of all relative extrema: scipy.signal.argrelextrema,
        Default is the last one, which is a modified version of
        `pyhht.utils.get_envelops` to support multi-channel time-series data.

        Notes
        -----
        The difference between interpolation and curve fitting is that when you
        fit a curve with points, these points may not be on result curve. But
        the advantage of interpolation is that it will predict values based on
        points beside them. So points will be exactly on result curve.
        In scipyinterpolate module, there are many choices to interpolate by
        points, here we use scipyinterpolate.spl* methods, because it's
        relatively fast and the result is nice.
        '''
        if method == 1:
            return abs(scipy.signal.hilbert(X, axis=-1))
        elif method == 2:
            nch, wsize = X.shape
            t = np.arange(nch)
            maxs = scipy.signal.argrelextrema(X, np.greater, axis=-1)[0]
            mins = scipy.signal.argrelextrema(X, np.less, axis=-1)[0]
            maxs = np.concatenate(([[0]]*nch, maxs, [[wsize-1]]*nch))
            mins = np.concatenate(([[0]]*nch, mins, [[wsize-1]]*nch))
            rst = np.array(
                    [[ip.splev(t, ip.splrep(t[maxs[i]], X[i][maxs[i]])),
                      ip.splev(t, ip.splrep(t[mins[i]], X[i][mins[i]]))]
                     for i in np.arange(nch)])
            return rst


    @_check_shape
    def Fast_Fourier_Transform(self, X, sample_rate=None, resolution=1):
        '''
        People use FT(Fourier Transform) to extract frequency domain
        info from time domain data in mathmatic questions. But when
        processing signals, DFT(Discret Fourier Transform) is a more
        practice way for computer calculation. And FFT(Fast discret
        Fourier Transform) is much more commonly used because it is
        better at handling time-varying signals(you can add windows).

        There are four steps to get useful result of fft:
            1. raw = np.fft.fft(X), here raw is a complex ndarray
            2. amp = np.abs(raw[:num/2]), remove latter half of raw
               and convert rest data into real number.
               Result of fft is symmetric in the real part.
            3. samples = len(X) and raw /= samples
            4. Remove Nyquist point, that is:
               if samples is odd number, amp*=2 except first point(freq=0)
               if samples is even number, amp*=2 except first and last points

        Parameters
        ----------
        X:           raw data with shape of n_channels x window_size
        sample_rate: sample rate of signal, always known as `fs`
        resolution:  number of points that between two Hz, default 1 point/Hz.
                     Assuming sample_rate is 300Hz, X.shape is (5, 1500),
                     which means sample_time is 5s. If resolution is 3,
                     the result of fft will be of shape (5, 450).
                     rst = fft(X, 300, 3)
                     rst[30] ==> amp of 10.0000Hz
                     rst[31] ==> amp of 10.3333Hz
                     rst[32] ==> amp of 10.6666Hz
                     rst[33] ==> amp of 11.0000Hz

        Returns
        -------
        freq: np.linspace(0, sample_rate/2, length)
        amp:  np.ndarray, n_channel x length
        where length = sample_rate/2*resolution
        '''
        sample_rate = sample_rate or self._fs
        n = sample_rate * resolution
        amp = 2 * abs(np.fft.rfft(X, int(n), axis=-1)) / float(X.shape[1])
        amp[:, 0] /= 2
        if X.shape[1] % 2:
            amp[:, -1] /= 2
        freq = np.linspace(0, sample_rate/2, amp.shape[1]-1)
        return freq, amp[:, :-1]


    @_check_shape
    def fft_amp_only(self, X, sample_rate, resolution=1, *a, **k):
        '''
        Fast Fourier Transform
        Input shape:  n_channel x window_size
        Output shape: n_channel x window_size/2

        Returns
        -------
        amp
        '''
        return self.fft(X, sample_rate, resolution)[1]

    @_check_shape
    def Short_Time_Fourier_Transfrom(self, X, sample_rate=None,
                                     nperseg=None, noverlap=None):
        '''
        Short Time Fourier Transform.
        Input shape:  n_channel x window_size
        Output shape: n_channel x freq x time
        freq = int(1.0 + math.floor( float(nperseg) / 2 ) )
        time = int(1.0 + math.ceil(float(X.shape[-1]) / (nperseg - noverlap)))

        Returns
        -------
        freq, time, amp
        '''
        # you mustn't normalize because amptitude difference between
        # channels is also important infomation for classification
        #                0           1         2      3
        # pxx.shape: n_sample x n_channels x freq x time
        #                0        2      3         1
        # target:    n_sample x freq x time x n_channels
        sample_rate = sample_rate or self._fs
        nperseg = nperseg or int(sample_rate / 5.0)
        noverlap = noverlap or int(sample_rate / 5.0 * 0.67)
        f, t, amp = signal.stft(X, sample_rate, 'hann', nperseg, noverlap)
        return f, t, np.abs(amp)

    @_check_shape
    def stft_amp_only(self, X, sample_rate=None,
                      nperseg=None, noverlap=None, *a, **k):
        '''
        Short Time Fourier Transform.
        Input shape:  n_channel x window_size
        Output shape: n_channel x freq x time

        Returns
        -------
        amp
        '''
        return self.stft(X, sample_rate, nperseg, noverlap)[2]


    @_check_shape
    def Discret_Wavelet_Transform(self, X, wavelet=None):
        '''
        The nature of DWT is to send raw signal S into one pair of filters,
        high pass filter H and low pass filter L, which are actually the
        wavelet you choose. Next, convolve S with H and L, thus generating two
        filtered signal Sh and Sl with length of ( len(S) + len(H) - 1 )
        Then, downsample Sh and Sl and cut off len(H)/2 points at each end of
        signals to avoid distortion( Sh = Sh[len(H)/2 : -len(H)/2] ).
        That's all! What we get now is entirely high-freq part and low-freq
        part of raw signal, and this process is the DWT in my understanding.

                 high pass  downsampling +--------+
               +---< H >-------< 2! >----+ Sh(cD) |
               |   filter                +--------+
        +---+  |
        | S +--+
        +---+  |
               | low pass   downsampling +--------+
               +---< L >-------< 2! >----+ Sl(cA) |
                   filter                +--------+

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

    @_check_shape
    def convolve_fft(self, X, filters):
        '''
        Multiplication on frequency domain is convolve on time domain.

        2018.7.20:
            Well, after some trying, this function act to be useful only when
            X is very long. But Numpy can't convolve on 2D mat and fft and
            multiply can. So convolve2d_fft is good. Enjoy!
        '''
        assert X.shape[1] == filters.shape[1]
        m, n = X.shape
        f1 = np.fft.fft(X, axis=-1)
        f2 = np.fft.fft(filters, axis=-1)
        return np.real(np.fft.ifft(f1 * f2))

    @_check_shape
    def convolve2d_fft(self, X, filters):
        '''
        see convolve_fft for details
        '''
        assert X.shape == filters.shape
        m, n = X.shape
        f1 = np.fft.fft2(X)
        f2 = np.fft.fft2(filters)
        return np.real(np.fft.ifft2(f1 * f2))

    @_check_shape
    def Continuous_Wavelet_Transform(self, X, scales, sample_rate=None,
                                     wavelet=None, use_scipy_signal=True):
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
            wavelets = [wavelet(min(10 * scale, X.shape[1]), scale) \
                        for scale in scales]
        else:
            int_psi, x = pywt.integrate_wavelet(wavelet, precision=10)
            wavelets = []
            for scale in scales:
                j = np.floor(
                        np.arange(scale*(x[-1]-x[0])+1) / scale / (x[1]-x[0]))
                wavelets += [int_psi[ j[j < len(int_psi)].astype(int) ][::-1]]

        # convolve
        coef = np.array([[np.convolve(ch, w, mode='same') for w in wavelets] \
                         for ch in X])
        if use_scipy_signal:
            freq = None
        else:
            coef = - np.sqrt(scales).reshape(len(scales), 1) * np.diff(coef)
            freq = (pywt.central_frequency(wavelet, 10) / scales *
                    (sample_rate or self._fs))
        return coef, freq

    @_check_shape
    def Wavelet_Decomposition(self, X, wavelet=None, use_cwt=False,
                              sample_rate=None, scales=None):
        '''
        While the difference between a wavelet decomposition and a wavelet
        transform is that decomposing is multilevel and transform is single
        level:
            wavedec(level=n) <==> dwt * n
        dwt returns cA1 and cD1
        wavedec returns cAn cDn cDn-1 ... cD1
        '''
        if use_cwt:
            c, f = self.cwt(X, (scales or 10), sample_rate,
                            (wavelet or signal.ricker))
        else:
            if wavelet not in pywt.wavelist():
                wavelet = 'haar'
            return pywt.wavedec(X, wavelet)

    @_check_shape
    def Hilbert_Huang_Transform(self, X, sample_rate=None):
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
        Difference between two hilbert in scipy
        1 scipy.fftpack.hilbert(x) ==> y
        2 scipy.signal.hilbert(x) ==> x + iy
          y is hilbert tranform of x, this result is known as analytic signal

        scipy.signal.hilbert(x) = x + scipy.fftpack.hilbert(x) * j
        '''
        imfs = np.array([pyhht.EMD(ch).decompose() for ch in X])
        analytic_signal = signal.hilbert(imfs, axis=-1)
        inst_phase_wrapped = np.angle(analytic_signal)
        inst_phase = np.unwrap(inst_phase_wrapped, axis=-1)
        inst_freq = (np.diff(inst_phase, axis=-1) / (2 * np.pi) *
                     (sample_rate or self._fs))
        return inst_freq

    @_check_shape
    def sync_like(self, X):
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
        pass

    @_check_shape
    def find_max_amp(self, X, low, high, sample_rate):
        '''
        Extract peek between frequency duration (n_min, n_max)
        '''
        if isinstance(X, tuple) and len(X) == 2:
            freq, amp = X
        else:
            freq, amp = self.fft(X, sample_rate)
        dt = float(freq[1] - freq[0])
        amp = amp[:, int(low/dt):int(high/dt)]**2
        return np.array([np.argmax(amp, 1) * dt + low, np.max(amp, 1)])

    @_check_shape
    def energy(self, X, low, high, sample_rate=None):
        '''
        Intergrate of energy on frequency duration (low, high)
        '''
        if isinstance(X, tuple) and len(X) == 2:
            freq, amp = X
        else:
            freq, amp = self.fft(X, (sample_rate or self._fs))
        dt = float(freq[1] - freq[0])
        amp = amp[:, int(low/dt):int(high/dt)]**2
        return np.sum(amp, 1) * dt

    @_check_shape
    def energy_time_duration(self, reader, low, high, duration):
        '''
        calculate energy density of time duration
        '''
        import time, threading
        energy_sum = np.zeros(reader.n_channel)
        sample_rate = reader.sample_rate
        stop_flag = threading.Event()
        def _sum(flag, eng):
            start_time = time.time()
            while not flag.isSet():
                if (time.time() - start_time) > duration:
                    break
                eng += self.energy(reader.data_frame, low, high,  sample_rate)
            eng /= time.time() - start_time
        threading.Thread(target=_sum, args=(stop_flag, energy_sum)).start()
        return stop_flag, energy_sum

    @_check_shape
    def energy_spectrum(self, X):
        '''

        '''
        pass

    @_check_shape
    def scalogram(self, X, sample_rate=None):
        rst = self.cwt(X,
                       scale=np.arange(1, 31),
                       sample_rate=(sample_rate or self._fs),
                       wavelet=signal.ricker,
                       use_scipy_signal=True)
        '''
        plt.imshow(
                rst, extent=[-1, 1, 1, 31], cmap='PRGn', aspect='auto',
                vmax=abs(rst).max(), vmin=-abs(rst).max())
        '''
        return rst

    @_check_shape
    def power_spectrum(self, X, sample_rate=None, method = 2):
        '''
        There are two kinds of defination of power spectrum(PS hereafter).
        1. PS = fft(autocorrelation(X))
           This is Winner-Khintchine defination
        2. PS = abs(fft(X))**2 / sample_time
           It is known that
               'P = W / S'
           (power equals to energy divided by time duration), and
           'abs(fft(X))**2' is known as energy spectrum. But here we use
               'psd = fft**2 / freq-duration'
           unit of psd will be 'W/Hz' instead of 'W/s'

        Parameters
        ----------
        X: array
        sample_rate: number

        Returns
        -------
        freq, power
        '''
        sample_rate = sample_rate or self._fs
        if method == 1:
            pass

        elif method == 2:
            freq, amp = self.fft(X, sample_rate)
            return freq, amp**2 / (freq[1] - freq[0])






if __name__ == '__main__':
    s = Signal_Info(500)

    # fake data with shape of (10 samples x 8 channels x 1024 window_size)
    X = np.random.random((10, 8, 1024))
    print('create data with shape {}'.format(X.shape))
    print('after remove DC shape {}'.format(s.remove_DC(X).shape))
    print('after notch shape {}'.format(s.notch(X).shape))
    print('after fft shape {}'.format(s.fft(X).shape))
    print('after stft shape {}'.format(s.stft(X).shape))
