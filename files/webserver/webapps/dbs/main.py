#!/usr/bin/env python
# -*- coding: utf8 -*-
# built-in
import os
import sys
import platform
import threading
import traceback

# requirements.txt: necessary: numpy, scipy, bottle
# requirements.txt: necessary: bottle-websocket, geventwebsocket
import scipy
import numpy as np
from bottle import request, redirect, static_file, Bottle, run
from bottle.ext.websocket import websocket, GeventWebSocketServer
from geventwebsocket import WebSocketError

__dir__ = os.path.dirname(os.path.abspath(__file__))
__file__ = os.path.basename(__file__)
path = os.path.abspath(os.path.join(__dir__, '../../../../'))
if path not in sys.path:
    sys.path.append(path)

# from __dir__/../../../../
from embci import BASEDIR
from embci.preprocess import Features
if 'arm' in platform.platform():
    from embci.IO import ESP32_SPI_reader as Reader
else:
    from embci.IO import Fake_data_generator as Reader


#
# constents
#

sample_rate = 500
freq_resolution = 4
length = freq_resolution * 25  # 0-25Hz
x_freq = np.arange(100.0).reshape(1, 100) / freq_resolution
batch_size = 50

dbs = Bottle()
reader = Reader(sample_rate, n_channel=8)
feature = Features(sample_rate)
reader.start(method='thread')
flag_stop = threading.Event()
flag_pause = threading.Event()
flag_pause.set()
channel_range = {'r': (0, 7), 'n': 0}
scale_list = {'a': [pow(10, x) for x in range(10)], 'i': 3}


#
# Functions
#


def generate_pdf():
    pass


def tremor_coef(data, distance=25):
    data[data < data.max() / 4] = 0
    peaks, heights = scipy.signal.find_peaks(data, 0, distance=distance)
    peaks = np.concatenate(([0], peaks))
    return (feature.si.sample_rate / (np.average(np.diff(peaks)) + 1),
            1000 * np.average(heights['peak_heights']))


#
# General API
#

@dbs.route('/')
def main():
    redirect('display.html')


@dbs.route('/data', apply=[websocket])
def handler(ws):
    print('websocket connection')
    data_list = []
    try:
        while 1:
            data = reader.data_channel[channel_range['n']]
            data = feature.si.notch_realtime(data)
            data_list.append(data)
            if len(data_list) >= batch_size:
                ws.send(bytearray(data_list))
                data_list = []
    except WebSocketError:
        print('websocket closed')
    except:
        traceback.print_exc()
    finally:
        ws.close()


@dbs.route('/<filename:path>')
def display(filename):
    return static_file(filename, root=__dir__)


@dbs.route('/report')
def report():
    global username
    username = request.query.name
    generate_pdf()
    return 'report content: asdf && /path/to/pdf/to/download'


@dbs.route('/report/download/<pdfname>')
def download(pdfname):
    return static_file(pdfname,
                       root=os.path.join(BASEDIR, 'data'),
                       download=pdfname.replace('/', '-'))


#
# Data control API
#


@dbs.route('/data/stop')
def stop_streaming():
    flag_stop.set()


@dbs.route('/data/pause')
def data_stream_pause():
    flag_pause.clear()


@dbs.route('/data/resume')
def data_stream_resume():
    flag_pause.set()


@dbs.route('/data/filter')
def realtime_filter():
    pass


@dbs.route('/data/freq')
def data_get_freq():
    # y_amp: 1ch x length
    y_amp = feature.si.fft_amp_only(reader.data_frame[channel_range['n']],
                                    resolution=freq_resolution)[0, :length]
    return {'data': np.concatenate((x_freq, y_amp)).T.tolist()}


@dbs.route('/data/freq/<num>')
def data_set_freq(num):
    if num in [250, 500, 1000]:
        reader.set_sample_rate(num)
        reader.restart()


@dbs.route('/data/coef')
def data_get_coef():
    data = reader.data_frame[channel_range['n']]

    data = feature.si.notch(data)

    b, a = scipy.signal.butter(
        4, 10.0 / feature.si.sample_rate, btype='lowpass')
    stiffness = feature.si.rms(scipy.signal.lfilter(
        b, a, feature.si.detrend(data), -1))[0]

    data = feature.si.envelop(data)
    data = feature.si.smooth(data, 12)

    movement = np.average(data)

    return {'0': tremor_coef(feature.si.detrend(data)[0]),
            '1': stiffness * 1000,
            '2': movement * 1000}


@dbs.route('/data/channel')
def data_get_channel():
    return channel_range


@dbs.route('/data/channel/<num:int>')
def data_set_channel(num):
    num = int(num) - 1
    if num in range(channel_range['r']):
        channel_range['n'] = num


@dbs.route('/data/scale')
def data_get_scale():
    return scale_list


@dbs.route('/data/scale/<num:int>')
def data_set_scale(num):
    num = int(num)
    if num > 0 and num < len(scale_list['a']):
        scale_list['i'] = num


# offer application object
application = dbs

if __name__ == '__main__':
    os.chdir(__dir__)
    run(app=dbs, host='0.0.0.0', port=80, reloader=True,
        server=GeventWebSocketServer)

# vim: set ts=4 sw=4 tw=79 et ft=python :
