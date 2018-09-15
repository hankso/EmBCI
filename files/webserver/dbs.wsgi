#!/usr/bin/env python
# -*- coding: utf8 -*-

import os
import time
import subprocess

# from ./
from bottle import request, route, static_file, default_app


__dir__ = os.path.dirname(os.path.abspath(__file__))
__filename__ = os.path.basename(__file__)


'''
Functions
'''


def generate_pdf():
    pass


'''
General API
'''


@route('/')
def main():
    return '{}\n{}'.format(
        request, time.strftime('%a,%b %d %H:%M:%S %Y', time.localtime()))


@route('/<filename:re:*\.html>')
def display(filename):
    return static_file(filename, root='.')


@route('/debug')
def debug():
    subprocess.Popen(["nohup", "jupyter-notebook"])
    return '<a href="http://hankso.com:9999">调试模式</a>'


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
                       root=os.path.join(__dir__, '../../data'),
                       download=pdfname.replace('/', '-'))


'''
Data control API
'''


@route('/data/freq')
def data_get_freq():
    #  ch = 0
    #  data = reader.data_frame[ch]
    #  return np.fft(data)
    return


@route('/data/freq/<num>')
def data_set_freq(num):
    if num in [250, 500, 1000]:
        #  reader.set_sample_rate(num)
        pass


@route('/data/coef')
def data_get_coef():
    #  return tremor(data), stiffness(data), movement(data)
    return


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
