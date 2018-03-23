#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Thu Mar 22 08:26:16 2018

@author: hank
"""
# pip install matplotlib
import matplotlib
import matplotlib.pyplot as plt

class Plotter():
    def __init__(self, where_to_plot=None, n_channel=1):
        '''
        Plot multichannel streaming data on a figure ,
        or in a window if it is offered.
        Param:
            where_to_plot can be a matplotlib figure or a list of axes.
            default None, to create a new figure and split it into n_channels
            window, one for each window
        '''
        if where_to_plot == None:
            self.figure = plt.figure()
            for i in xrange(n_channel):
                self.figure.add_axes((0, i*(1.0/n_channel),
                                      1, 1.0/n_channel),
                                     facecolor='black')
            self.axes = self.figure.axes
            
        elif type(where_to_plot) == matplotlib.figure.Figure:
            if not len(where_to_plot.axes):
                for i in xrange(n_channel):
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
        # clear all axes
        for a in self.axes:
            a.cla()
    
    def plot(self, data):
        '''
        only update line data to save time
        '''
        shape = data.shape()
        if len(shape) == 3:
            # n_sample x n_channel x window_size
            for i, ch in enumerate(data[0]):
                if len(self.axes[i].lines):
                    self.axes[i].lines[0].set_ydata(ch)
                else:
                    self.axes[i].plot(ch)
        elif len(shape) == 4:
            # n_sample x n_channel x freq x time
            for i, img in enumerate(data[0]):
                if len(self.axes[i].images):
                    self.axes[i].images[0].set_data(img)
                else:
                    self.axes[i].imshow(ch)
        return data

if __name__ == '__main__':
    p = Plotter(n_channel=8)