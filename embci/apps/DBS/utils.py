#!/usr/bin/env python
# coding=utf-8
#
# File: DBS/utils.src
# Author: Hankso
# Webpage: https://github.com/hankso
# Time: Mon 04 Mar 2019 17:06:43 CST

'''__doc__'''

# built-in
from __future__ import unicode_literals
import os

# requirements.txt: optional: reportlab
# requirements.txt: data-processing: scipy, numpy
try:
    from reportlab.pdfbase import ttfonts, pdfmetrics
    from reportlab.pdfgen import canvas
    _reportlib_ = True
except ImportError:
    _reportlib_ = False
import scipy.signal
import numpy as np

from embci.configs import BASEDIR, DATADIR
from embci.utils import mkuserdir, time_stamp, LoopTaskInThread
from .globalvars import reader, signalinfo, server, pt

DEFAULT_FONT = os.path.join(BASEDIR, 'files/fonts/yahei_mono.ttf')


@mkuserdir
def generate_pdf(username, **kwargs):
    if _reportlib_ is False:
        return {}
    # load font
    fontpath = kwargs.get('fontpath', DEFAULT_FONT)
    fontname = os.path.splitext(os.path.basename(fontpath))[0]
    if fontname not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(ttfonts.TTFont(fontname, fontpath))
    pdfpath = os.path.join(
        username, kwargs.get('filename', time_stamp() + '.pdf'))
    # plot on empty pdf
    c = canvas.Canvas(os.path.join(DATADIR, pdfpath), bottomup=0)
    c.setFont(fontname, 30)
    c.drawString(65, 80, u'天坛医院DBS术后调控肌电报告单')
    c.setFontSize(20)
    c.line(30, 120, 580, 120)
    str1 = (u'姓名: {username:^8s}  性别: {gender:>2s}  '
            u'年龄: {age:>3s}  病号ID: {id}')
    c.drawString(35, 150, str1.format(username=username, **kwargs))
    c.line(30, 165, 580, 165)
    c.line(30, 710, 580, 710)
    str2 = (u'改善率   震颤： {tr:4.1f}%    '
            u'僵直： {sr:4.1f}%    运动： {mr:4.1f}%')
    c.drawString(35, 740, str2.format(**kwargs))
    c.line(30, 755, 580, 755)
    c.drawImage(os.path.join(DATADIR, kwargs['img_pre']), 32, 190)
    c.drawImage(os.path.join(DATADIR, kwargs['img_post']), 32, 450)
    c.setFontSize(24)
    c.drawString(360, 250, u'术前')
    c.drawString(360, 510, u'术后')
    c.setFontSize(18)
    c.drawString(380, 290, u'震颤： {:7.4f}Hz'.format(kwargs['tb']))
    c.drawString(380, 320, u'僵直： {:7.4f}'.format(kwargs['sb']))
    c.drawString(380, 350, u'运动： {:7.4f}'.format(kwargs['mb']))
    c.drawString(380, 550, u'震颤： {:7.4f}Hz'.format(kwargs['ta']))
    c.drawString(380, 580, u'僵直： {:7.4f}'.format(kwargs['sa']))
    c.drawString(380, 610, u'运动： {:7.4f}'.format(kwargs['ma']))
    c.drawString(35, 795, u'医师签字：')
    c.setFontSize(15)
    c.drawString(450, 800, 'Powered by Cheitech')
    c.save()
    return {'pdfpath': pdfpath}


def calc_coef(data):
    data = signalinfo.notch(data)
    stiffness = signalinfo.rms(data - signalinfo.smooth(data, 3))[0, 0]
    data = signalinfo.smooth(signalinfo.detrend(data), 10)
    b, a = scipy.signal.butter(
        4, (4.0 / reader.sample_rate, 45.0 / reader.sample_rate), 'bandpass')
    data = scipy.signal.lfilter(b, a, data, -1)
    data = signalinfo.envelop(data)[0]
    movement = np.average(data)
    data[data < data.max() / 4] = 0
    peaks, heights = scipy.signal.find_peaks(data, 0, distance=40)
    peaks = np.concatenate(([0], peaks))
    tremor = reader.sample_rate / np.average(np.diff(peaks))
    heights = np.average(heights['peak_heights']) * 1000
    return [tremor, stiffness * 1000, movement * 1000]
    # u_peaks, u_height = scipy.signal.find_peaks(data, (0, None), None, d)
    # l_peaks, l_height = scipy.signal.find_peaks(data, (None, 0), None, d)
    # intervals = np.hstack((np.diff(u_peaks), np.diff(l_peaks)))
    # heights = np.hstack((u_height['peak_heights'],
    #                      l_height['peak_heights']))


class WebSocketMulticaster(LoopTaskInThread):
    def __init__(self):
        self.ws_list = []
        self.data_list = []
        LoopTaskInThread.__init__(self, self.send_data)

    def send_data(self):
        while len(self.data_list) < pt.batch_size:
            data = process_realtime(reader.data_channel)
            server.multicast(data)
            self.data_list.append(data)
        data = np.float32(self.data_list).T
        if pt.detrend and reader.input_source != 'test':
            data = signalinfo.detrend(data)
        data = data[pt.channel_range.n]
        data = data * pt.scale_list.a[pt.scale_list.i]
        data = bytearray(data)
        for ws in self.ws_list:
            ws.send(data)
        self.data_list = []

    def add(self, ws):
        # pre-check on websocket
        self.ws_list.append(ws)


distributor = WebSocketMulticaster()


def process_register(data, pt=pt):
    signalinfo.notch(data, register=True)
    signalinfo.bandpass(data, pt.bandpass.get('low', 4),
                        pt.bandpass.get('high', 10), register=True)


def process_realtime(data, pt=pt):
    if pt.notch:
        data = signalinfo.notch_realtime(data)
    if pt.bandpass:
        data = signalinfo.bandpass_realtime(data)
    return data


def process_fullarray(data, pt=pt):
    if pt.notch:
        data = signalinfo.notch(data)
    if pt.bandpass:
        data = signalinfo.bandpass(data, **pt.bandpass)
    return data

# THE END
