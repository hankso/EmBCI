#!/usr/bin/env python
# coding=utf-8
#
# File: DBS/__init__.py
# Author: Hankso
# Webpage: http://github.com/hankso
# Time: Tue 18 Sep 2018 01:55:03 CST

# built-in
import os
import time
import platform
import traceback

# requirements.txt: network: bottle, gevent, gevent-websocket
# requirements.txt: data-processing: numpy, pylsl, scipy
from gevent import monkey
monkey.patch_all(select=False, thread=False)
from geventwebsocket import WebSocketError
import bottle
from bottle import abort, request
import numpy as np
import scipy.signal

from embci.configs import DATADIR
from embci.processing import Features
if platform.machine() in ['arm', 'aarch64']:
    from embci.io import ESP32SPIReader as Reader
else:
    from embci.io import FakeDataGenerator as Reader
# TODO: use files/service/E01data-streaming and PylslReader
from embci.io import SocketTCPServer as Server
from embci.viz import plot_waveform
from embci.utils import config_logger, get_boolean, time_stamp


# =============================================================================
# constants
#
__dir__ = os.path.dirname(os.path.abspath(__file__))
__status__ = os.path.join(__dir__, 'status.html')
__report__ = os.path.join(__dir__, 'report.html')

batch_size = 50  # send 8x50 data as a chunk
sample_rate = 500  # Hz
fft_resolution = 4  # points/Hz
fft_points = fft_resolution * 25  # 0-25Hz
x_freq = np.arange(0, 25, 1.0 / fft_resolution)[np.newaxis, :]  # 0, 1/4Hz ...
scale_list = {'a': [pow(10, x) for x in range(-2, 8)], 'i': 2}  # amp scale
channel_range = {'r': (0, 8), 'n': 0}  # current displayed channel

dbs = bottle.Bottle()
logger = config_logger()
reader = Reader(sample_rate, sample_time=5, num_channel=8)
feature = Features(sample_rate)
server = Server()
server.start()

rtnotch = True
rtdetrend = True
rtbandpass = {'low': 4, 'high': 10}
saved_data = {}


# =============================================================================
# General API
#
from .utils import generate_pdf


@dbs.route('/')
def app_index():
    bottle.redirect('display.html')


@dbs.route(r'/<filename:re:(\w)+\.html>')
def app_static_html(filename):
    return bottle.static_file(filename, root=__dir__)


@dbs.route('/report/download/<path:path>')
def app_static_files(path):
    download = path.endswith('.pdf') and path.replace('/', '-')
    return bottle.static_file(path, root=DATADIR, download=download)


@dbs.route('/report')
def app_report(k={}):
    # get user informations: id, name, gender etc.
    for key in request.query:
        k[key] = request.query.getunicode(key)
    try:
        username = k['username']
    except KeyError:
        abort(500, 'lack of info `username`')

    # get user's sEMG data and calculate coefficients
    if saved_data.get('frame_post') is None:
        #  abort(500, 'Save two frame of data before generating report!')
        logger.warn('[Generate Report PDF] using random data')
        data_before = np.random.randn(1, reader.window_size)
        data_after = np.random.randn(1, reader.window_size)
    else:
        data_before = saved_data['frame_pre'][saved_data['channel_pre']]
        data_after = saved_data['frame_post'][saved_data['channel_post']]
    k['tb'], k['sb'], k['mb'] = tb, sb, mb = data_get_coef(data_before)
    k['ta'], k['sa'], k['ma'] = ta, sa, ma = data_get_coef(data_after)
    tr, sr, mr = abs(ta - tb) / ta, abs(sa - sb) / sa, abs(ma - mb) / ma
    k['tr'], k['sr'], k['mr'] = tr, sr, mr = 100 * np.array([tr, sr, mr])

    # generate data waveform image
    data_before = feature.si.notch(data_before)
    data_before = feature.si.bandpass(data_before, **rtbandpass)
    data_after = feature.si.notch(data_after)
    data_after = feature.si.bandpass(data_after, **rtbandpass)
    try:
        img_pre = os.path.join(username, 'img_{}.png'.format(time_stamp()))
        plot_waveform(data_before).save(os.path.join(DATADIR, img_pre))
        logger.info('[Plot Waveform] image %s saved.' % img_pre)
        img_post = os.path.join(username, 'img_{}.png'.format(time_stamp()))
        plot_waveform(data_after).save(os.path.join(DATADIR, img_post))
        logger.info('[Plot Waveform] image %s saved.' % img_post)
    except Exception:
        logger.error(traceback.format_exc())
        k['img_pre'], k['img_post'] = 'test/pre.png', 'test/post.png'
    else:
        k['img_pre'], k['img_post'] = img_pre, img_post

    # generate and save user's report PDF to ${DATADIR}/${username}
    pdfpath = generate_pdf(**k).get('pdfpath', 'test/asdf.pdf')
    logger.info('[Generate Report PDF] pdf %s saved!' % pdfpath)

    k['pdf_url'] = 'report/download/{}'.format(pdfpath.encode('utf8'))
    k['img_pre_url'] = 'report/download/{}'.format(img_pre.encode('utf8'))
    k['img_post_url'] = 'report/download/{}'.format(img_post.encode('utf8'))
    return bottle.template(__report__, **k)


# =============================================================================
# Data accessing API
#
@dbs.route('/data/websocket')
def data_get_websocket():
    ws = request.environ.get('wsgi.websocket')
    if reader.status == 'closed':
        data_stream_start()
    elif reader.status == 'paused':
        data_stream_resume()
    env = ws.environ
    logger.debug(
        'websocket @ {REMOTE_ADDR}:{REMOTE_PORT} {REQUEST_METHOD} '
        '"{SERVER_NAME}:{SERVER_PORT}{PATH_INFO}" from {HTTP_USER_AGENT}'
        .format(**env))
    data_list = []
    try:
        while 1:
            while len(data_list) < batch_size:
                data = reader.data_channel
                if rtnotch:
                    data = feature.si.notch_realtime(data)
                if rtbandpass:
                    data = feature.si.bandpass_realtime(data)
                server.send(np.array(data))
                data_list.append(data)
            data = np.float32(data_list).T[channel_range['n']]
            if rtdetrend and getattr(reader, 'input_source', 'None') != 'test':
                data = feature.si.detrend(data)
            scale = scale_list['a'][scale_list['i']]
            logger.debug(scale)
            data = data[0] * scale
            ws.send(bytearray(data))
            data_list = []
    except WebSocketError:
        pass
    except Exception:
        logger.error(traceback.format_exc())
    finally:
        ws.close()
        data_stream_pause()
    logger.debug(
        'websocket @ {REMOTE_ADDR}:{REMOTE_PORT} closed'.format(**env))


@dbs.route('/data/freq')
def data_get_freq():
    # y_amp: 1ch x length
    y_amp = feature.si.fft_amp_only(
        reader.data_frame[channel_range['n']],
        resolution=fft_resolution)[:, :fft_points]
    return {'data': np.concatenate((x_freq, y_amp)).T.tolist()}


@dbs.route('/data/coef')
def data_get_coef(data=None):
    data = feature.si.notch(data or reader.data_frame[channel_range['n']])
    b, a = scipy.signal.butter(4, 10.0 / feature.sample_rate, btype='lowpass')
    stiffness = feature.si.rms(
        scipy.signal.lfilter(b, a, feature.si.detrend(data), -1))[0]
    data = feature.si.envelop(data)
    data = feature.si.smooth(data, 12)
    movement = np.average(data)
    data = feature.si.detrend(data)[0]
    data[data < data.max() / 4] = 0
    peaks, heights = scipy.signal.find_peaks(data, 0, distance=25)
    peaks = np.concatenate(([0], peaks))
    tremor = feature.sample_rate / (np.average(np.diff(peaks)) + 1)
    # javascript: use json to mimic a fake array
    return {'0': tremor, '1': stiffness[0] * 1000, '2': movement * 1000}


@dbs.route('/data/status')
def data_get_status():
    msg = []
    msg.append('Realtime Detrend state: ' + ('ON' if rtdetrend else 'OFF'))
    msg.append('Realtime Notch state: ' + ('ON' if rtnotch else 'OFF'))
    msg.append('Realtime Bandpass state: ' + ('OFF' if not rtbandpass else
               '{low}Hz-{high}Hz').format(**rtbandpass))
    msg.append('Data saved for action: {}'.format(saved_data.keys() or None))
    msg.append('Current input source: ' + reader.input_source)
    msg.append('Current amplify scale: %dx' % scale_list['a'][scale_list['i']])
    msg.append('Current channel num: CH{}'.format(channel_range['n'] + 1))
    msg.append('Current Sample rate: {}Hz'.format(reader.sample_rate))
    msg.append('ADS1299 BIAS output: {}'.format(
        getattr(reader, 'enable_bias', None)))
    msg.append('ADS1299 Measure Impedance: {}'.format(
        getattr(reader, 'measure_impedance', None)))
    return bottle.template(__status__, messages=msg)


# =============================================================================
# Stream control API
#
@dbs.route('/data/start')
def data_stream_start():
    reader.start('process', 'starts-with(source_id, "spi")')
    time.sleep(2)
    feature.si.bandpass(reader.data_frame, register=True, **rtbandpass)
    feature.si.notch(reader.data_frame, register=True)
    return 'data stream started'


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


# =============================================================================
# Configs IO
#
@dbs.route('/data/scale')
def data_config_scale():
    scale = request.query.get('scale')
    if scale is None:
        return scale_list
    length = len(scale_list['a'])
    if scale.isdigit():
        scale = int(scale)
        if scale in range(length):
            scale_list['i'] = int(scale)
            bottle.redirect('status')
        abort(500, ('<p>Invalid scale `{}`! Set scale within '
                    '[{}, {})</p>').format(scale, 0, length))
    elif scale.lower() == 'minus':
        scale_list['i'] = (scale_list['i'] - 1) % length
    elif scale.lower() == 'plus':
        scale_list['i'] = (scale_list['i'] + 1) % length
    else:
        abort(500, ('<p>Invalid operation `{}`! Choose one from '
                    '`minus` | `plus`</p>').format(scale))
    bottle.redirect('status')


@dbs.route('/data/channel')
def data_config_channel():
    channel = request.query.get('channel')
    if channel is None:
        return channel_range
    if channel.isdigit() and int(channel) in range(*channel_range['r']):
        channel_range['n'] = int(channel)
    else:
        abort(500, ('<p>Invalid channel `{}`! Must be int within [{}, {})</p>'
                    .format(channel, *channel_range['r'])))
    bottle.redirect('status')


@dbs.route('/data/filter')
def data_config_filter():
    global rtbandpass, rtnotch
    low, high = request.query.get('low'), request.query.get('high')
    notch = request.query.get('notch')
    rst = ''
    if notch is not None:
        if notch.lower() == 'true':
            rtnotch = True
        elif notch.lower() == 'false':
            rtnotch = False
            rst += '<p>Realtime notch filter state: OFF</p>'
        else:
            abort(500, 'Invalid notch state! Choose one of `true` | `false`')
    if None not in [low, high]:
        try:
            low, high = float(low), float(high)
        except ValueError:
            abort(500, 'Invalid bandpass argument! Only accept number.')
        if low == high == 0:
            rtbandpass = {}
            rst += '<p>Realtime bandpass filter state: OFF</p>'
        elif high < low or low < 0:
            abort(500, 'Invalid bandpass argument! 0 < Low < High.')
        else:
            rtbandpass = {'low': low, 'high': high}
            feature.si.bandpass(reader.data_frame, low, high, register=True)
            rst += ('<p>Realtime bandpass filter param: '
                    'low {}Hz -- high {}Hz</p>').format(low, high)
    if rst:
        return rst
    bottle.redirect('status')


@dbs.route('/data/config')
def data_config_misc():
    error = []
    for key in request.query:
        handler = globals().get('config_' + key)
        if handler is None:
            abort(500, '<p>Invalid key `{}`!</p>'.format(key))
        try:
            rst = handler(request.query.get(key))
        except Exception:  # handler un-handled errors
            logger.error(traceback.format_exc())
        else:
            if rst:
                error.append(rst)
    if error:
        abort(500, '\n'.join(['<p>{}</p>'.format(_) for _ in error]))
    bottle.redirect('status')


def config_save(save):
    save = save.lower()
    if save == 'before':
        saved_data['frame_pre'] = reader.data_frame
        saved_data['channel_pre'] = channel_range['n']
    elif save == 'after':
        if saved_data.get('frame_pre') is None:
            return ('Invalid save command! Save data with param '
                    '`before` first. Then save with param `after`')
        saved_data['frame_post'] = reader.data_frame
        saved_data['channel_post'] = channel_range['n']
    else:
        return ('Invalid save param: `{}`! '.format(save) +
                'Choose one from `before` | `after`')


def config_source(source):
    if not reader.set_input_source(source):
        return 'Invalid source `{}`!'.format(source)


def config_freq(freq):
    if freq.isdigit() and int(freq) in [250, 500, 1000]:
        reader.set_sample_rate(int(freq))
        reader.restart()
    else:
        return ('Invalid sample rate `{}`! '.format(freq) +
                'Choose one from `250` | `500` | `1000`')


def config_detrend(detrend):
    global rtdetrend
    try:
        rtdetrend = get_boolean(detrend)
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


# offer application object for Apache2
application = dbs
__all__ = ['application']
# THE END
