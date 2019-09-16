#!/usr/bin/env python3
# coding=utf-8
#
# File: DisplayWeb/__init__.py
# Authors: Hank <hankso1106@gmail.com>
# Create: 2019-08-16 03:46:24

'''
Visualization on webpage through WiFi.

- websocket
    - [x] Raw data multicast
    - [ ] Authentication before accessing websocket
- visualization
    - [x] Display 8-chs signal simultaneously in single chart
    - [x] Hide or show each channel
    - [ ] Adjust frequency domain amp and range
    - [x] Generate resource and protect it behind a token
- configs
    - [x] Realtime data status
    - [x] Parameters setting
'''

# built-in
import os
import time
import shlex
import traceback

# requirements.txt: network: bottle
# requirements.txt: data: numpy, pylsl
import bottle
import numpy as np

import embci
from embci.webui import __basedir__ as __webui_basedir__
from embci.apps.streaming import send_message_streaming

from .globalvars import (
    reader, server, recorder, signalinfo, logger,
    pt, __basedir__
)
from .utils import process_register, minimize, distributor

__status__ = os.path.join(__basedir__, 'status.html')
__display__ = os.path.join(__basedir__, 'display.html')

display = application = bottle.Bottle()
inited = False


# =============================================================================
# General API

@display.route('/')
def app_index():
    global inited
    if not inited:
        app_reader_control('init')
        inited = True
    bottle.redirect('display.html')


@display.route('/server', template=(__status__))
def app_server_info():
    msg = [
        ['Address', '{}:{}'.format(server.host, server.port)],
    ]
    return {'messages': msg}


@display.route('/recorder/<attr>')
def app_recorder_attr(attr):
    if not hasattr(recorder, attr):
        bottle.abort(400, 'Unknown attribute `{}`'.format(attr))
    return str(getattr(recorder, attr))


@display.route('/reader/<method>')
def app_reader_control(method):
    if method in ['init', 'start']:
        try:
            rst = reader.start(
                'starts-with(source_id, "spi")', type='Reader Outlet',
                method='process')
        except Exception:
            logger.error(traceback.format_exc())
            bottle.abort(500, 'Cannot start data stream reader.')
        if not rst:
            return 'data stream already started'
        time.sleep(1.5)
        process_register(reader.data_frame)
        if method == 'init':
            signalinfo.sample_rate = reader.sample_rate
            distributor.start()
            recorder.start()
            server.start()
        return 'data stream started'
    elif method in ['pause', 'resume', 'close', 'restart']:
        getattr(reader, method)()
        return 'data stream ' + reader.status
    if not hasattr(reader, method):
        bottle.abort(400, 'Unknown method `{}`'.format(method))
    func = getattr(reader, method)
    if not callable(func):
        bottle.abort(400, 'Cannot execute method `{}`'.format(method))
    return str(func())


@display.route('/<filename:path>')
def app_static_files(filename):
    '''
    In order to support DBS run standalone (without embci.webui app-loader),
    embci.webui.__basedir__ is added in v0.1.5
    '''
    for rootdir in [__basedir__, __webui_basedir__]:
        if os.path.exists(os.path.join(rootdir, filename)):
            return bottle.static_file(filename, rootdir)
    return bottle.HTTPError(404, 'File does not exist.')


# =============================================================================
# Data accessing API

@display.route('/data/websocket')
def data_get_websocket():
    '''
    Example of environment variables: {
        'SERVER_NAME': '127.0.0.1',
        'SERVER_PORT': '8080',
        'REMOTE_ADDR': '10.139.27.55',
        'REMOTE_PORT': '52158',
        ...
        'REQUEST_METHOD': 'GET',
        'HTTP_ORIGIN': 'http://127.0.0.1:8080',
        'SCRIPT_NAME': '/apps/displayweb',
        'PATH_INFO': '/data/websocket',
        'QUERY_STRING': '',
        'GATEWAY_INTERFACE': 'CGI/1.1',
        ...
        'wsgi.input': <gevent.pywsgi.Input object>,
        'wsgi.version': (1, 0),
        'wsgi.run_once': False,
        'wsgi.url_scheme': 'http',
        'wsgi.multithread': False,
        'wsgi.multiprocess': False,
        'wsgi.websocket': <geventwebsocket.websocket.WebSocket object>,
        'wsgi.websocket_version': '13',
        'wsgi.errors': <logger object>,
    }
    '''
    app_reader_control('start')
    ws = bottle.request.environ.get('wsgi.websocket')
    distributor.add(ws)
    ADDR = '{REMOTE_ADDR}:{REMOTE_PORT}'.format(**ws.environ)
    logger.info('[websocket] {REQUEST_METHOD} {PATH_INFO} from {ADDR}'
                .format(ADDR=ADDR, **ws.environ))
    while not ws.closed:
        time.sleep(1)
    logger.info('[websocket] {ADDR} closed'.format(ADDR=ADDR))


@display.route('/data/freq')
def data_get_freq():
    # y_amp: nch x length
    y_amp = signalinfo.fft_amp_only(
        signalinfo.detrend(reader.data_frame[pt.channel_range.n]),
        resolution=pt.fft_resolution)[:]  # this maybe multi-channels
    y_amp = y_amp[:, 0:pt.fft_range * pt.fft_resolution] * 1000
    x_freq = np.arange(0, pt.fft_range, 1.0 / pt.fft_resolution).reshape(1, -1)
    return minimize(np.concatenate((x_freq, y_amp)).T.tolist())


@display.route('/data/status', template=(__status__))
def data_get_status(pt=pt):
    msg = [
        ['SPLITBAR', 'Parameters tree'],
        ['Realtime Detrend (baseline)', 'ON' if pt.detrend else 'OFF'],
        ['Realtime Notch Filter', 'ON' if pt.notch else 'OFF'],
        ['Realtime Bandpass Filter', pt.bandpass or 'OFF'],
        ['Current Amplify Scale', '%.4fx' % pt.scale_list.a[pt.scale_list.i]],
        ['Current Frequent Channel', 'CH%d' % (pt.channel_range.n + 1)],
        ['SPLITBAR', 'Session data'],
        ['Parameter Tree', pt],
        ['SPLITBAR', 'Reader information'],
        ['Current Input Source', reader.input_source],
        ['Current Sample Rate (FS)', str(reader.sample_rate) + 'Hz'],
        ['ADS1299 BIAS Output', getattr(reader, 'enable_bias', None)],
        ['ADS1299 Impedance', getattr(reader, 'measure_impedance', None)],
    ]
    return {'messages': msg}


# =============================================================================
# Configs IO

@display.route('/data/scale')
def data_config_scale():
    scale = bottle.request.query.get('scale')
    length = len(pt.scale_list.a)
    if scale is None:
        pass
    elif scale.isdigit():
        if int(scale) in range(length):
            pt.scale_list.i = int(scale)
        else:
            bottle.abort(400, 'Invalid scale `{}`! Set scale within [{}, {})'
                         .format(scale, 0, length))
    elif scale.lower() == 'minus':
        pt.scale_list.i = (pt.scale_list.i - 1) % length
    elif scale.lower() == 'plus':
        pt.scale_list.i = (pt.scale_list.i + 1) % length
    else:
        bottle.abort(400, 'Invalid operation `{}`! Must be number within '
                          '[{}, {}) or one of `minus` | `plus`'
                          .format(scale, 0, length))
    return pt.scale_list.copy(dict)


@display.route('/data/channel')
def data_config_channel():
    action = bottle.request.query.get('action', '')
    channel = bottle.request.query.get('channel')
    if action != '' and channel is not None:
        return send_message_streaming(['set_channel', channel, action])
    if channel is None:
        pass
    elif channel.isdigit() and int(channel) in range(*pt.channel_range.r):
        pt.channel_range.n = int(channel)
    else:
        bottle.abort(400, 'Invalid channel `{}`! Must be int within [{}, {})'
                          .format(channel, *pt.channel_range.r))
    return pt.channel_range.copy(dict)


@display.route('/data/filter')
def data_config_filter():
    rst = []
    notch = bottle.request.query.get('notch')
    if notch is not None:
        try:
            pt.notch = embci.utils.get_boolean(notch)
            rst.append('Realtime notch filter state: {}'.format(
                'ON' if pt.notch else 'OFF'))
        except ValueError:
            bottle.abort(400, traceback.format_exc())
    low = bottle.request.query.get('low')
    high = bottle.request.query.get('high')
    if None not in [low, high]:
        try:
            low, high = float(low), float(high)
        except ValueError:
            bottle.abort(400, 'Invalid bandpass argument! Only accept number.')
        if low == high == 0:
            pt.bandpass.clear()
            rst.append('Realtime bandpass filter state: OFF')
        elif high < low or low < 0:
            bottle.abort(400, 'Invalid bandpass argument! 0 < Low < High.')
        else:
            pt.bandpass.low = max(1, low)
            pt.bandpass.high = min(reader.sample_rate // 2 - 1, high)
            process_register(reader.data_frame, pt)
            rst.append('Realtime bandpass filter param: {low}Hz -- {high}Hz'
                       .format(**pt.bandpass))
    if rst:
        return minimize(rst)


@display.route('/data/config')
def data_config_misc():
    error = []
    for key in bottle.request.query:
        handler = globals().get('config_' + key)
        if handler is None:
            bottle.abort(400, 'Invalid key `{}`!'.format(key))
        try:
            rst = handler(bottle.request.query.get(key))
        except Exception:  # handler un-handled errors
            logger.error(traceback.format_exc())
        else:
            if rst:
                error.append(rst)
    if error:
        bottle.abort(500, '\n'.join(['<p>{}</p>'.format(_) for _ in error]))


def config_source(source):
    reader.input_source = source
    #  return 'Invalid source `{}`!'.format(source)


def config_freq(freq):
    if freq.isdigit() and int(freq) in [250, 500, 1000]:
        reader.set_sample_rate(int(freq))
        reader.restart()
    else:
        return ('Invalid sample rate `{}`! '.format(freq) +
                'Choose one from `250` | `500` | `1000`')


def config_detrend(detrend):
    try:
        pt.detrend = embci.utils.get_boolean(detrend)
    except ValueError:
        return ('Invalid detrend `{}`! '.format(detrend) +
                'Choose one from `True` | `False`')


def config_bias(bias):
    try:
        reader.enable_bias = embci.utils.get_boolean(bias)
    except ValueError:
        return ('Invalid bias `{}`! ' +
                'Choose one from `True` | `False`').format(bias)


def config_impedance(impedance):
    try:
        reader.measure_impedance = embci.utils.get_boolean(impedance)
    except ValueError:
        return ('Invalid impedance: `{}`! '.format(impedance) +
                'Choose one from `True` | `False`')


def config_fftfreq(fftfreq):
    if fftfreq.isdigit() and 0 < int(fftfreq) < reader.sample_rate // 2:
        pt.fft_range = int(fftfreq)
    else:
        return ('Invalid FFT frequency `{}`!' +
                'Choose a positive number from [0-{}]'.format(
                    fftfreq, reader.sample_rate // 2))


def config_recorder(command):
    cmd = shlex.split(command)
    if len(cmd) == 1:
        recorder.cmd(cmd[0])
    elif len(cmd) == 2:
        recorder.cmd(**{cmd[0]: cmd[1]})
    else:
        return 'Invalid command: {}'.format(command)
    time.sleep(0.5)


def main():
    from embci.webui import main_debug
    main_debug(application)


__all__ = ['application']
# THE END
