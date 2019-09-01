#!/usr/bin/env python3
# coding=utf-8
#
# File: SignalInfo/__init__.py
# Authors: Hank <hankso1106@gmail.com>
# Create: 2019-02-19 01:07:14

'''Display/draw information of streaming data.'''

import numpy as np
import matplotlib.pyplot as plt

from ...processing import SignalInfo

__all__ = ()

# TODO: make matplotlib plot info a class


def main(reader, commander):
    si = SignalInfo(reader.sample_rate)
    display_ch = 'channel0'
    try:
        fig, axes = plt.subplots(nrows=3, ncols=2)
        data = reader.buffer[display_ch]
        # display raw data
        axes[0, 0].plot(data, linewidth=0.5)
        axes[0, 0].set_title('Raw data')
        line_raw = axes[0, 0].lines[0]
        # display time series data after notch and remove_DC
        data = si.detrend(si.notch(data))
        axes[0, 1].plot(data[0])
        axes[0, 1].set_title('after notch and remove DC')
        line_wave = axes[0, 1].lines[0]
        # display amp-freq data after fft
        axes[1, 0].plot(np.log10(si.fft_amp_only(data)[0]))
        axes[1, 0].set_title('channel data after FFT')
        line_fft = axes[1, 0].lines[0]
        # display PSD
        axes[1, 1].plot(np.log10(si.power_spectrum(data)[0]))
        axes[1, 1].set_title('Power Spectrum Density')
        line_psd = axes[1, 1].lines[0]
        # display 2D array after stft
        axes[2, 0].imshow(np.log10(si.stft_amp_only(data)[0]))
        axes[2, 0].set_title('after STFT')
        img_stft = axes[2, 0].images[0]
        # display signal info
        axes[2, 1].text(0.5, 0.75, '4-6Hz has max energy %f at %fHz' % (0, 0),
                        size=10, ha='center', va='center', color='r')
        axes[2, 1].text(0.5, 0.25, '4-10Hz sum of energy is %f' % 0,
                        size=10, ha='center', va='center', color='r')
        axes[2, 1].set_title('signal info')
        axes[2, 1].set_axis_off()
        text_p = axes[2, 1].texts[0]
        text_s = axes[2, 1].texts[1]

        fs = reader.sample_rate
        while 1:
            data = reader.buffer[display_ch]
            line_raw.set_ydata(data)
            data = si.detrend(si.notch(data))
            line_wave.set_ydata(data[0])
            line_fft.set_ydata(np.log10(si.fft_amp_only(data)[0]))
            line_psd.set_ydata(np.log10(si.power_spetrum(data)[0]))
            img_stft.set_data(np.log10(si.stft_amp_only(data)[0]))
            text_p.set_text('4-6Hz has max energy %f at %fHz' %
                            si.find_max_amp(data, 4, 6, fs)[0][::-1])
            text_s.set_text('4-10Hz sum of energy is %f' %
                            si.energy(data, 4, 10, fs)[0])
            plt.show()
            plt.pause(0.1)

    except KeyboardInterrupt:
        reader.close()
        commander.close()


# THE END
