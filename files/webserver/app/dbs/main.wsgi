#!/usr/bin/env python
# -*- coding: utf8 -*-

import os
import sys
import time
import threading

import numpy as np

__dir__ = os.path.dirname(os.path.abspath(__file__))
__file__ = os.path.basename(__file__)
os.chdir(__dir__)

from bottle import route, request, response, redirect, static_file, default_app

sys.path.append(os.path.abspath(os.path.join(__dir__, '../../../../')))
from embci import BASEDIR
from embci.IO import Fake_data_generator, Socket_server
from embci.common import time_stamp

reader = Fake_data_generator(sample_rate=500, n_channel=8)
reader.start(method='thread')
server = Socket_server()
server.start()


def echo(flag_pause, flag_stop):
    with open('python.log', 'a') as f:
        f.write(time_stamp() + 'start thread\n')
    while not flag_stop.isSet():
        flag_pause.wait()
        server.send(reader.data_channel)
    flag_stop.clear()
    flag_pause.set()
    server.close()
    with open('python.log', 'a') as f:
        f.write(time_stamp() + 'echo done!\n')
flag_stop = threading.Event()
flag_pause = threading.Event()
flag_pause.set()
threading.Thread(target=echo, args=(flag_pause, flag_stop,)).start()


#
# Functions
#


def generate_pdf():
    pass


#
# General API
#

@route('/')
def main():
    redirect('/app/dbs/display.html')


@route('/<filename:path>')
def display(filename):
    return static_file(filename,
                       root=os.path.join(BASEDIR, 'files/webserver/app/dbs'))


@route('/debug')
def debug():
    response.set_cookie(
        'last_debug', time.strftime('%a,%b %d %H:%M:%S %Y', time.localtime()))
    redirect('http://hankso.com:9999')


# generate report
@route('/report')
def report():
    global username
    username = request.query.name
    generate_pdf()
    return 'report content: asdf && /path/to/pdf/to/download'


@route('/report/download/<pdfname>')
def download(pdfname):
    return static_file(pdfname,
                       root=os.path.join(BASEDIR, 'data'),
                       download=pdfname.replace('/', '-'))


#
# Data control API
#


@route('/data/stop')
def stop_streaming():
    flag_stop.set()


@route('/data/pause')
def data_stream_pause():
    flag_pause.clear()


@route('/data/resume')
def data_stream_resume():
    flag_pause.set()


@route('/data/freq')
def data_get_freq():
    #  ch = 0
    #  data = reader.data_frame[ch]
    #  return np.fft(data)
    return {'data': [[x, y] for x, y in zip(np.arange(100) / 4.0,
                                            np.random.random(100))]}


@route('/data/freq/<num>')
def data_set_freq(num):
    if num in [250, 500, 1000]:
        #  reader.set_sample_rate(num)
        pass


@route('/data/coef')
def data_get_coef():
    # TODO: embed coef algorithm
    return {'0': np.random.random(),  # tremor
            '1': np.random.random(),  # stiffness
            '2': np.random.random()}  # movement


@route('/data/channel')
def data_get_channel():
    return


@route('/data/channel/<num>')
def data_set_channel(num):
    #  channel
    return


@route('/data/scale')
def data_get_scale():
    return


@route('/data/scale/<num>')
def data_set_scale(num):
    #  scale
    return


# offer application object
application = default_app()

#  vim: set ts=4 sw=4 tw=79 et ft=python :
