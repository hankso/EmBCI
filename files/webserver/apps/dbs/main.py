#!/usr/bin/env python
# -*- coding: utf8 -*-

import os
import sys
import threading

import numpy as np

__dir__ = os.path.dirname(os.path.abspath(__file__))
__file__ = os.path.basename(__file__)
os.chdir(__dir__)

from bottle import request, redirect, static_file, Bottle
from bottle.ext.websocket import websocket
dbs = Bottle()

sys.path.append(os.path.abspath(os.path.join(__dir__, '../../../../')))
from embci import BASEDIR
from embci.IO import ESP32_SPI_reader as Reader

reader = Reader(sample_rate=500, n_channel=8)
reader.start(method='thread')

flag_stop = threading.Event()
flag_pause = threading.Event()
flag_pause.set()


#
# Functions
#


def generate_pdf():
    pass


#
# General API
#

@dbs.route('/')
def main():
    redirect('display.html')


@dbs.route('/data', apply=[websocket])
def handler(ws):
    while 1:
        ws.send(reader.data_channel)
    print('lost connection')


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


@dbs.route('/data/freq')
def data_get_freq():
    #  ch = 0
    #  data = reader.data_frame[ch]
    #  return np.fft(data)
    return {'data': [[x, y] for x, y in zip(np.arange(100) / 4.0,
                                            np.random.random(100))]}


@dbs.route('/data/freq/<num>')
def data_set_freq(num):
    if num in [250, 500, 1000]:
        reader.set_sample_rate(num)
        reader.restart()


@dbs.route('/data/coef')
def data_get_coef():
    return {'0': np.random.random(),  # tremor
            '1': np.random.random(),  # stiffness
            '2': np.random.random()}  # movement


@dbs.route('/data/channel')
def data_get_channel():
    return


@dbs.route('/data/channel/<num>')
def data_set_channel(num):
    #  channel
    return


@dbs.route('/data/scale')
def data_get_scale():
    return


@dbs.route('/data/scale/<num>')
def data_set_scale(num):
    #  scale
    return


# offer application object
application = dbs

if __name__ == '__main__':
    #  server = WSGIServer(('0.0.0.0', 80), dbs, handler_class=WebSocketHandler)
    #  server.serve_forever()
    pass

#  vim: set ts=4 sw=4 tw=79 et ft=python :
