#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Thu Mar 22 08:26:16 2018

@author: hank
"""
# built-in
import time
import sys, os; sys.path += ['../src']

# pip install matplotlib, numpy, scipy
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import scipy.io as sio

# from ../src
from preprocessing import Processer

class Plotter():
    def __init__(self, window_size, where_to_plot=None, n_channel=1):
        '''
        Plot multichannel streaming data on a figure ,
        or in a window if it is offered.
        Param:
            where_to_plot can be a matplotlib figure or a list of axes.
            Default None to create a new figure and split it into n_channels
            window, one for each window
        '''
        if where_to_plot == None:
            self.figure = plt.figure()
            for i in range(n_channel):
                self.figure.add_axes((0, i*(1.0/n_channel),
                                      1, 1.0/n_channel),
                                     facecolor='black')
            self.axes = self.figure.axes
            
        elif type(where_to_plot) == matplotlib.figure.Figure:
            if not len(where_to_plot.axes):
                for i in range(n_channel):
                    where_to_plot.add_axes((0, i*(1.0/n_channel),
                                            1, 1.0/n_channel),
                                           facecolor='black')
            self.figure, self.axes = where_to_plot, where_to_plot.axes
            
        elif type(where_to_plot) in [matplotlib.axes.Axes,
                                     matplotlib.axes.Subplot]:
            self.figure, self.axes = where_to_plot.figure, [where_to_plot]
            
        elif type(where_to_plot) == list and len(where_to_plot):
            if type(where_to_plot[0]) in [matplotlib.axes.Axes,
                                          matplotlib.axes.Subplot]:
                self.figure = where_to_plot[0].figure
                self.axes = where_to_plot
                
        else:
            raise RuntimeError(('Unknown type param where_to_plot: {}\n'
                                'matplotlib.figure.Figure or list of axes'
                                'is recommended.').format(type(where_to_plot)))
        # clear all axes and create the line
        for a in self.axes:
            a.cla()
            a.plot(np.zeros(window_size))
    
    def plot(self, data):
        '''
        Axes are initialized in constructor.
        This function only update line data, which is faster than plt.plot()
        '''
        shape = data.shape
        
        # n_sample x n_channel x window_size
        if len(shape) == 3:
            for i, ch in enumerate(data[0]):
                self.axes[i].lines[0].set_ydata(ch)
                    
        # n_sample x n_channel x freq x time
        elif len(shape) == 4:
            for i, img in enumerate(data[0]):
                    self.axes[i].images[0].set_data(img)
                    
        # Return data in case of using Plotter.plot as callback function
        return data



def view_data_with_matplotlib(data, actionname, p=Processer(250, 2)):
    for ch, d in enumerate(data):
        plt.figure('%s_%d' % (actionname, ch))
        
        plt.subplot(321)
        plt.title('raw data')
        plt.plot(d[0], linewidth=0.5)
        
        plt.subplot(323)
        plt.title('remove_DC and notch')
        plt.plot(p.notch(p.remove_DC(d))[0, 0], linewidth=0.5)
        
        plt.subplot(325)
        plt.title('after fft')
        plt.plot(p.fft(p.notch(p.remove_DC(data)))[1][0, 0], linewidth=0.5)
        
        plt.subplot(343)
        plt.title('after stft')
        f, t, amp = p.stft(p.remove_DC(p.notch(d)))
        plt.pcolormesh(t, f, np.log10(amp[0, 0]))
        highest_col = [col[1] for col in sorted(zip(np.sum(amp[0, 0], axis=0),
                                                    range(len(t))))[-3:]]
        
        plt.plot((t[highest_col], t[highest_col]),
                 (0, f[-1]), 'r')
        plt.ylabel('Freq / Hz')
        plt.xlabel('Time / s')
        
        plt.subplot(344)
        plt.title('Three Max Amptitude'.format(t[highest_col]))
        for i in highest_col:
            plt.plot(amp[0, 0, :, i], label='time: {}s'.format(t[i]), linewidth=0.5)
            plt.legend()
        
        plt.subplot(324)
        t = time.time()
    #    plt.psd(d, Fs=250, label='raw', linewidth=0.5)
        plt.psd(p.remove_DC(p.notch(d))[0, 0], Fs=250, label='filter', linewidth=0.5)
        plt.legend()
        plt.title('normal PSD -- used time: %.3fms' % (1000*(time.time()-t)))
        
        plt.subplot(326)
        t = time.time()
        
        plt.title('optimized PSD -- used time: %.3fms' % (1000*(time.time()-t)))



if __name__ == '__main__':
    plt.ion()
    fake_data = np.random.random((1, 8, 1000))
    print(fake_data.shape)
    p = Plotter(window_size = 1000, n_channel=8)
    p.plot(fake_data)

    # data shape: 1 x n_channel x window_size
    filename = '../data/test/grab-1.mat'
    actionname = os.path.basename(filename)
    data = sio.loadmat(filename)[actionname.split('-')[0]]
    p = Processer(250, 2)
    view_data_with_matplotlib(data, actionname)