#!/usr/bin/env python3
# coding=utf-8
#
# File: EmBCI/embci/viz/plots.py
# Authors: Hank <hankso1106@gmail.com>
# Create: 2019-03-06 01:42:02

'''Plotting using Python Image Library (PIL).'''

# built-in
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# requirements.txt: data: scipy, numpy
# requirements.txt: necessary: pillow
import numpy as np
from PIL import Image, ImageDraw

rainbow = [
    0x0000FF, 0xFFFF00, 0xFF00FF, 0x00FFFF,
    0x00FF00, 0xFF0000, 0x800080, 0xFFA00A,
    0x808080
]


def plot_waveform(data, channel=None, colors=rainbow, imgsize=(300, 200),
                  *a, **k):
    '''
    Plot signal waveform on PIL.Image and return im object.

    Parameters
    ----------
    data : array-like
    channel : int or tuple of int or None
    '''
    data = np.atleast_2d(data).copy()
    if data.ndim >= 3:
        raise ValueError('Invalid data shape: `{}`'.format(data.shape))
    length = data.shape[1]
    x = np.arange(length)

    if isinstance(channel, (tuple, list)):
        channel = list(channel)
    elif channel is None:
        channel = range(data.shape[0])
    elif isinstance(channel, int):
        channel = [channel]
    else:
        raise TypeError('Invalid channel type: `{}`'
                        .format(type(channel).__name__))

    canvas_size = (length, int(length / imgsize[0] * imgsize[1]))
    img = Image.new('RGB', canvas_size, 'white')
    draw = ImageDraw.Draw(img)
    for n in channel:
        y = data[n]
        y /= abs(y).max()        # normalize data to [-1, 1]
        y *= canvas_size[1] / 2  # resize to [-half_height, +half_height]
        y += canvas_size[1] / 2  # resize to [0, canvas_height]
        y[0] = y[-1] = 0         # set first and end point to zero
        toplot = [tuple(_) for _ in np.vstack((x, y)).T]
        draw.line(toplot, colors[n], width=(length // 500))

    img = img.resize((imgsize[0] + 4, imgsize[1] + 4), Image.ANTIALIAS)
    img = img.crop((2, 2, imgsize[0] + 2, imgsize[1] + 2)).transpose(1)
    return img


__all__ = ['plot_waveform']
# THE END
