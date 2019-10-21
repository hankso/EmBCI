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
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
import os
import time
import traceback

# requirements.txt: network: bottle, gevent-websocket
# requirements.txt: data: numpy, pylsl
import bottle
import geventwebsocket
import numpy as np

from embci.utils import (
    get_boolean, minimize, null_func, config_logger,
    LoopTaskInThread
)
from embci.apps.streaming import send_message_streaming
from embci.apps.recorder import Recorder
from embci.io import LSLReader as Reader

from .globalvars import server, signalinfo, pt
from .utils import process_register, process_fullarray, process_realtime

__basedir__ = os.path.dirname(os.path.abspath(__file__))
__status__ = os.path.join(__basedir__, 'status.html')
__display__ = os.path.join(__basedir__, 'display.html')

display = bottle.Bottle()
logger = config_logger(__name__)


# =============================================================================
# General API

def app_init():
    global app_init, reader, recorder, distributor
    reader = Reader(sample_time=5, num_channel=8)
    app_reader_control('init')
    recorder = Recorder(reader)
    recorder.start()
    distributor = WebSocketMulticaster(pt)
    distributor.start()
    server.start()
    app_init = null_func


@display.route('/')
def app_index():
    app_init()
    bottle.redirect('display.html')


@display.route('/server', template=(__status__))
def app_server_info():
    msg = [
        ['Address', '{}:{}'.format(server.host, server.port)],
    ]
    return {'messages': msg}


@display.route('/reader/<method>')
def app_reader_control(method):
    if method in ['init', 'start']:
        try:
            rst = reader.start(type='Reader Outlet', method='process')
        except Exception:
            logger.error(traceback.format_exc())
            bottle.abort(500, 'Cannot start data stream reader.')
        if not rst:
            return 'data stream already started'
        signalinfo.sample_rate = reader.sample_rate
        process_register(reader.data_all)
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


@display.route('/recorder/<command>')
def app_recorder_hook(command):
    return recorder.cmd(command)


@display.route('/srv/<filename:path>')
def app_nonexist(filename):
    return bottle.HTTPError(404, 'File does not exist.')


@display.route('/<filename:path>')
def app_static_files(filename):
    if os.path.exists(os.path.join(__basedir__, filename)):
        return bottle.static_file(filename, __basedir__)
    bottle.redirect('/srv/' + filename)


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
    data = signalinfo.detrend(reader.data_frame[pt.channel_range.n])
    y_amp = signalinfo.fft_amp_only(
        process_fullarray(data),
        resolution=pt.fft_resolution
    )[:]  # this maybe multi-channels
    y_amp = y_amp[:, 0:pt.fft_range * pt.fft_resolution] * 1000
    x_freq = np.arange(0, pt.fft_range, 1.0 / pt.fft_resolution).reshape(1, -1)
    return minimize(np.concatenate((x_freq, y_amp)).T.tolist())


@display.route('/data/status', template=(__status__))
def data_get_status(pt=pt):
    msg = [
        ['SPLITBAR', 'Parameters tree'],
        ['Realtime Detrend (baseline)', 'ON' if pt.detrend else 'OFF'],
        ['Realtime Notch Filter', pt.notch or 'OFF'],
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
            freq = int(notch)
        except ValueError:
            try:
                pt.notch = get_boolean(notch)
            except ValueError:
                bottle.abort(400, 'Invalid notch value: %s' % notch)
        else:
            pt.notch = freq
        rst.append('Realtime notch filter state: {}'.format(pt.notch or 'OFF'))
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
        pt.detrend = get_boolean(detrend)
    except ValueError:
        return ('Invalid detrend `{}`! '.format(detrend) +
                'Choose one from `True` | `False`')


def config_bias(bias):
    try:
        reader.enable_bias = get_boolean(bias)
    except ValueError:
        return ('Invalid bias `{}`! ' +
                'Choose one from `True` | `False`').format(bias)


def config_impedance(impedance):
    try:
        reader.measure_impedance = get_boolean(impedance)
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


# =============================================================================
# Distributor used for multicasting

class WebSocketMulticaster(LoopTaskInThread):
    def __init__(self, paramtree):
        self.ws_list = []
        self.pt = paramtree
        LoopTaskInThread.__init__(self, self._data_multicast)

    def _data_fetch(self):
        data = process_realtime(reader.data_channel, self.pt)
        server.multicast(data)
        return data

    def _data_cache(self):
        cached_data = []
        while len(cached_data) < self.pt.batch_size:
            cached_data.append(self._data_fetch())
        data = np.float32(cached_data).T  # n_channel x n_batch_size
        if self.pt.detrend and reader.input_source != 'test':
            data = signalinfo.detrend(data)
        # data = data[self.pt.channel_range.n]
        # TODO: displayweb: scale matrix can amp each channel differently
        data = data * self.pt.scale_list.a[self.pt.scale_list.i]
        return bytearray(data)

    def _data_multicast(self):
        '''Cache and multicast data continuously if there are ws clients.'''
        if not self.ws_list:
            return time.sleep(1)
        data = self._data_cache()
        for ws in self.ws_list[:]:
            if not self.data_send(ws, data):
                self.remove(ws)

    def data_send(self, ws, data, binary=True):
        try:
            ws.send(data, binary)
            return True
        except geventwebsocket.websocket.WebSocketError:
            ws.close()
        except Exception:
            logger.error(traceback.format_exc())
        return False

    def add(self, ws):
        if not isinstance(ws, geventwebsocket.websocket.WebSocket):
            raise TypeError('Invalid websocket. Must be gevent-websocket.')
        if ws.closed:
            raise ValueError('Websocket %s is already closed.' % ws)
        self.ws_list.append(ws)

    def remove(self, ws):
        if ws not in self.ws_list:
            return
        self.ws_list.remove(ws)


APPNAME = 'Visualization'
application = display
__all__ = ['application']
# THE END
