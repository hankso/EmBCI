#!/usr/bin/env python
# coding=utf-8
'''
File: __init__.py
Author: Hankso
Web: http://github.com/hankso
Time: Tue 18 Sep 2018 01:55:03 CST
'''
# built-in
import os
import sys
import time
import platform
import threading
import traceback

# requirements.txt: necessary: numpy, scipy, bottle, pylsl
# requirements.txt: necessary: gevent, bottle-websocket, geventwebsocket
from gevent import monkey
monkey.patch_all(select=False)
import scipy
import numpy as np
from bottle import abort, request, redirect, run, static_file, Bottle
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
if platform.machine() in ['arm', 'aarch64']:
    from embci.common import reset_esp
    reset_esp()
    from embci.io import ESP32_SPI_reader as Reader
else:
    from embci.io import Fake_data_generator as Reader


#
# constants
#

sample_rate = 500
freq_resolution = 4
length = freq_resolution * 25  # 0-25Hz
x_freq = np.arange(100.0).reshape(1, 100) / freq_resolution
batch_size = 50
channel_range = {'r': (0, 8), 'n': 0}
scale_list = {'a': [pow(10, x) for x in range(10)], 'i': 3}


#
# instances
#

#
#  import pylsl
#  inlet = pylsl.StreamInlet(pylsl.resolve_stream()[0])
#
dbs = Bottle()

reader = Reader(sample_rate, n_channel=8)
reader.start(method='thread')

feature = Features(sample_rate)
realtime_bandpass = (4, 10)
feature.si.bandpass(reader.data_frame,
                    low=realtime_bandpass[0],
                    high=realtime_bandpass[1],
                    register=True)
realtime_notch = True
feature.si.notch(reader.data_frame, register=True)

ws_lock = threading.Lock()


#
# Functions
#


def generate_pdf():
    pass


def tremor_coef(data, distance=25):
    data[data < data.max() / 4] = 0
    peaks, heights = scipy.signal.find_peaks(data, 0, distance=distance)
    peaks = np.concatenate(([0], peaks))
    return feature.si.sample_rate / (np.average(np.diff(peaks)) + 1)


#
# General API
#


@dbs.route('/')
def main():
    redirect('display.html')


@dbs.route('/<filename:re:\w+\.html>')
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


@dbs.route('/data/websocket', apply=[websocket])
def ws_handler(ws):
    ws_lock.acquire()
    print(('websocket @ {REMOTE_ADDR}:{REMOTE_PORT} {REQUEST_METHOD} '
           '"{SERVER_NAME}:{SERVER_PORT}{PATH_INFO}" from {HTTP_USER_AGENT}'
           ).format(**ws.environ))
    data_list = []
    try:
        while 1:
            #  data = inlet.pull_sample()[0]
            #  time.sleep(0)
            # after 2018.9.22 modified embci.io._basic_reader.data_channel
            # now will call time.sleep(0) to give away context control
            data = reader.data_channel
            if realtime_notch:
                data = feature.si.notch_realtime(data)
            if realtime_bandpass:
                data = feature.si.bandpass_realtime(data)
            data_list.append(data)
            if len(data_list) >= batch_size:
                data = np.float32(data_list)[:, channel_range['n']]
                data = data * scale_list['a'][scale_list['i']]
                #  print(time.time())
                ws.send(bytearray(data))
                data_list = []
    except WebSocketError:
        print(('websocket @ {REMOTE_ADDR}:{REMOTE_PORT} closed'
               ).format(**ws.environ))
    except:
        traceback.print_exc()
    finally:
        #  ws.close()
        pass
    ws_lock.release()


@dbs.route('/data/stop')
def data_stream_stop():
    reader.close()
    return 'data stream stoped'


@dbs.route('/data/pause')
def data_stream_pause():
    reader.pause()
    return 'data stream paused'


@dbs.route('/data/resume')
def data_stream_resume():
    reader.resume()
    return 'data stream resumed'


@dbs.route('/data/filter')
def data_stream_filter():
    global realtime_bandpass, realtime_notch
    low, high = request.query.get('low'), request.query.get('high')
    notch = request.query.get('notch')
    rst = ''
    if notch is not None:
        if notch.lower() == 'true':
            realtime_notch = True
            rst += '<p>Realtime notch filter state: ON</p>'
        elif notch.lower() == 'false':
            realtime_notch = False
            rst += '<p>Realtime notch filter state: OFF</p>'
        else:
            abort(500, 'Invalid notch state! Choose one of `true` | `false`')
    if None not in [low, high]:
        try:
            low, high = float(low), float(high)
        except:
            abort(500, 'Invalid bandpass argument! Only number is accepted.')
        if low == high == 0:
            realtime_bandpass = None
            rst += '<p>Realtime bandpass filter state: OFF</p>'
        elif high < low or low < 0:
            abort(500, 'Invalid bandpass argument!')
        else:
            realtime_bandpass = (low, high)
            feature.si.bandpass(reader.data_frame, low, high, register=True)
            rst += ('<p>Realtime bandpass filter param: '
                    'low {}Hz -- high {}Hz</p>').format(low, high)
    return rst if rst else 'No changes is made'


@dbs.route('/data/freq')
def data_get_freq():
    # y_amp: 1ch x length
    y_amp = feature.si.fft_amp_only(
        reader.data_frame[channel_range['n']],
        resolution=freq_resolution)[:, :length]
    return {'data': np.concatenate((x_freq, y_amp)).T.tolist()}


@dbs.route('/data/freq/<num>')
def data_set_freq(num):
    if num in [250, 500, 1000]:
        reader.set_sample_rate(num)
        reader.restart()
        return('set sample_rate to {}'.format(num))
    return 'Invalid number! Set sample rate within (250, 500, 1000)'


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
            '1': stiffness[0] * 1000,
            '2': movement * 1000}


@dbs.route('/data/channel')
def data_get_channel():
    return channel_range


@dbs.route('/data/channel/<num:int>')
def data_set_channel(num):
    if num in range(*channel_range['r']):
        channel_range['n'] = num
        return 'set channel to CH{}'.format(num + 1)
    abort(500, ('Invalid number! '
                'Set channel within [{}, {}]'.format(*channel_range['r'])))


@dbs.route('/data/scale')
def data_get_scale():
    return scale_list


@dbs.route('/data/scale/<op>')
def data_set_scale(op):
    r = (0, len(scale_list['a']))
    try:
        num = int(op)
        if num in range(len(scale_list['a'])):
            scale_list['i'] = num
        else:
            abort(500, 'Invalid number! Set scale within [{}, {}]'.format(**r))
    except:
        if op == 'minus':
            scale_list['i'] = (scale_list['i'] - 1) % r[1]
        elif op == 'plus':
            scale_list['i'] = (scale_list['i'] + 1) % r[1]
        else:
            abort(500, 'Invalid operation! Choose one of `minus` | `plus`')
    return('set scale to {}'.format(scale_list['a'][scale_list['i']]))


# offer application object
application = dbs
__all__ = ['application']


if __name__ == '__main__':
    os.chdir(__dir__)
    #  server = WSGIServer(('0.0.0.0', 80), dbs,
    #                      handler_class=WebSocketHandler)
    #  server.serve_forever()
    run(app=dbs, host='0.0.0.0', port=80, reloader=True,
        server=GeventWebSocketServer)
