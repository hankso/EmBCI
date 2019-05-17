#!/usr/bin/env python
# coding=utf-8
#
# File: DBS/__init__.py
# Author: Hankso
# Webpage: http://github.com/hankso
# Time: Tue 18 Sep 2018 01:55:03 CST

# built-in
import os
import copy
import time
import shlex
import base64
import traceback

# requirements.txt: network: bottle, gevent, gevent-websocket
# requirements.txt: data-processing: numpy, pylsl
from gevent import monkey
monkey.patch_all(select=False, thread=False)
from geventwebsocket import WebSocketError
import bottle
import numpy as np

import embci
import embci.webui
from .globalvars import reader, signalinfo, server, recorder, pt, __dir__
from .utils import (generate_pdf, calc_coef,
                    process_register, process_realtime, process_fullarray)


# =============================================================================
# constants
#
HELP = '''
- report
    - [x] generate colored image of signal
    - [x] generate PDF and protect it behind a token
- websocket
    - [x] Raw data multicast
    - [ ] Authentication before accessing websocket
- coefficients
    - [ ] energy and freq of tremor
    - [ ] energy of stiffness
    - [x] movement
- visualization
    - [ ] display 8-chs signal simultaneously in single chart
    - [x] coeffs and freq domain amp
- console
    - [x] realtime data status
    - [x] parameters setting
- update
    - [ ] connect to WiFi/proxy/git-server
    - [x] software updating
'''

__status__ = os.path.join(__dir__, 'status.html')
__report__ = os.path.join(__dir__, 'report.html')
__display__ = os.path.join(__dir__, 'display.html')

dbs = bottle.Bottle()
logger = embci.utils.config_logger('apps.DBS')
x_freq = np.arange(0, pt.fft_range, 1.0 / pt.fft_resolution)[None, :]

saved_data = {}


# =============================================================================
# General API
#
@dbs.route('/')
def app_index():
    data_stream_init()
    data_stream_start()
    bottle.redirect('display.html')


@dbs.route('/report.html')
@bottle.view(__report__, username='default')
def app_report_html():
    username = bottle.request.get_cookie('name')
    token = bottle.request.get_cookie(
        'report', secret=base64.b64encode(username))
    if token is None:
        bottle.abort(408, 'Cache expired or user\'s report not generated yet!')
    return embci.utils.deserialize(base64.b64decode(token))


@dbs.route('/report/download/<path:path>')
def app_download_files(path):
    download = path.endswith('.pdf') and path.replace('/', '-')
    return bottle.static_file(path, embci.configs.DATADIR, download=download)


@dbs.route('/report')
def app_generate_pdf(k={}):
    # get user informations: id, name, gender etc.
    for key in bottle.request.query:
        k[key] = bottle.request.query.getunicode(key)
    try:
        username = k['username']
    except KeyError:
        bottle.abort(400, 'lack of info `username`')

    # get user's sEMG data and calculate coefficients
    if 'frame_post' not in saved_data or 'frame_pre' not in saved_data:
        # bottle.abort(400, 'Save two frame of data before generating report!')
        logger.warning('[Generate Report PDF] using random data')
        data_pre = np.random.randn(1, reader.window_size)
        data_post = np.random.randn(1, reader.window_size)
        pt_pre = pt_post = pt
    else:
        data_pre = saved_data['frame_pre'][saved_data['channel_pre']]
        data_post = saved_data['frame_post'][saved_data['channel_post']]
        pt_pre = saved_data['pt_pre']
        pt_post = saved_data['pt_post']
    k['tb'], k['sb'], k['mb'] = tb, sb, mb = calc_coef(data_pre)
    k['ta'], k['sa'], k['ma'] = ta, sa, ma = calc_coef(data_post)
    tr, sr, mr = abs(ta - tb) / ta, abs(sa - sb) / sa, abs(ma - mb) / ma
    k['tr'], k['sr'], k['mr'] = tr, sr, mr = 100 * np.array([tr, sr, mr])

    # generate data waveform image
    dataf_pre = process_fullarray(data_pre.copy(), pt_pre)
    dataf_post = process_fullarray(data_post.copy(), pt_post)
    try:
        embci.utils.mkuserdir(lambda *a: None)(username)  # make user folder
        img_pre = os.path.join(
            username, 'img_pre_{}.png'.format(embci.utils.time_stamp()))
        embci.viz.plot_waveform(dataf_pre).save(
            os.path.join(embci.configs.DATADIR, img_pre))
        logger.debug('[Plot Waveform] image %s saved.' % img_pre)
        img_post = os.path.join(
            username, 'img_post_{}.png'.format(embci.utils.time_stamp()))
        embci.viz.plot_waveform(dataf_post).save(
            os.path.join(embci.configs.DATADIR, img_post))
        logger.debug('[Plot Waveform] image %s saved.' % img_post)
    except IOError:
        logger.error(traceback.format_exc())
        k['img_pre'], k['img_post'] = 'test/pre.png', 'test/post.png'
    else:
        k['img_pre'], k['img_post'] = img_pre, img_post

    # generate and save user's report PDF to ${DATADIR}/${username}
    pdfpath = generate_pdf(**k).get('pdfpath', 'test/asdf.pdf')
    logger.debug('[Generate Report PDF] pdf %s saved!' % pdfpath)
    np.savez_compressed(
        os.path.join(embci.configs.DATADIR, username,
                     'data_{}'.format(embci.utils.time_stamp())),
        spre=data_pre, spost=data_post, ppre=dataf_pre, ppost=dataf_post)

    k['pdf_url'] = 'report/download/{}'.format(pdfpath.encode('utf8'))
    k['img_pre_url'] = 'report/download/{}'.format(img_pre.encode('utf8'))
    k['img_post_url'] = 'report/download/{}'.format(img_post.encode('utf8'))
    token = base64.b64encode(embci.utils.serialize(k))
    bottle.response.set_cookie('name', username)
    # Anti-XSS(Cross Site Scripting): HttpOnly + Escape(TODO)
    bottle.response.set_cookie(
        'report', token,
        secret=base64.b64encode(username.encode('utf8')),
        max_age=60, httponly=True)


@dbs.route('/recorder/<attr>')
def app_recorder_attr(attr):
    if not hasattr(recorder, attr):
        bottle.abort(400, 'Unknown attribute `{}`'.format(attr))
    return str(getattr(recorder, attr))


@dbs.route('/<filename:path>')
def app_static_files(filename):
    for rootdir in [__dir__, embci.webui.__dir__]:
        if os.path.exists(os.path.join(rootdir, filename)):
            return bottle.static_file(filename, rootdir)
    return bottle.HTTPError(404, 'File does not exist.')


# =============================================================================
# Data accessing API
#
@dbs.route('/data/websocket')
def data_get_websocket():
    ws = bottle.request.environ.get('wsgi.websocket')
    if reader.status == 'closed':
        data_stream_init()
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
            while len(data_list) < pt.batch_size:
                data = process_realtime(reader.data_channel)
                server.multicast(data)
                data_list.append(data)
            data = np.float32(data_list).T[pt.channel_range.n]
            if pt.detrend and reader.input_source != 'test':
                data = signalinfo.detrend(data)
            data = data[0] * pt.scale_list.a[pt.scale_list.i]
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
    # y_amp: nch x length
    y_amp = signalinfo.fft_amp_only(
        signalinfo.detrend(reader.data_frame[pt.channel_range.n]),
        resolution=pt.fft_resolution)[:]  # this maybe multi-channels
    y_amp = y_amp[:, 0:pt.fft_range * pt.fft_resolution]
    return {'data': np.concatenate((x_freq, y_amp)).T.tolist()}


@dbs.route('/data/coef')
def data_get_coef(data=None):
    return {'data': calc_coef(reader.data_frame[pt.channel_range.n])}


@dbs.route('/data/status')
@bottle.view(__status__)
def data_get_status(pt=pt):
    msg = [
        '********************* Parameters tree **********************',
        'Realtime Detrend state: ' + ('ON' if pt.detrend else 'OFF'),
        'Realtime Notch state: ' + ('ON' if pt.notch else 'OFF'),
        'Realtime Bandpass state: ' + str(pt.bandpass or 'OFF'),
        'Current amplify scale: %fx' % pt.scale_list.a[pt.scale_list.i],
        'Current channel num: CH{}'.format(pt.channel_range.n + 1),
        '*********************** Session data ***********************',
        'Data saved for action: {}'.format(saved_data.keys() or None),
        '******************** Reader information ********************',
        'Current input source: ' + reader.input_source,
        'Current Sample rate: {}Hz'.format(reader.sample_rate),
        'ADS1299 BIAS output: {}'.format(
            getattr(reader, 'enable_bias', None)),
        'ADS1299 Measure Impedance: {}'.format(
            getattr(reader, 'measure_impedance', None)),
    ]
    return {'messages': msg}


# =============================================================================
# Stream control API
#
def data_stream_init():
    reader.start(method='process',
                 args=('starts-with(source_id, "spi")'),
                 kwargs={'type': 'Reader Outlet'})
    time.sleep(1.5)
    signalinfo.sample_rate = reader.sample_rate
    recorder.start()
    server.start()
    process_register(reader.data_frame)


@dbs.route('/data/start')
def data_stream_start():
    if not reader.start():
        return 'data stream already started'
    time.sleep(1.5)
    process_register(reader.data_frame)
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
    scale = bottle.request.query.get('scale')
    if scale is None:
        return pt.scale_list
    length = len(pt.scale_list.a)
    if scale.isdigit():
        scale = int(scale)
        if scale in range(length):
            pt.scale_list.i = int(scale)
            return
        bottle.abort(400, 'Invalid scale `{}`! Set scale within [{}, {})'
                          .format(scale, 0, length))
    elif scale.lower() == 'minus':
        pt.scale_list.i = (pt.scale_list.i - 1) % length
    elif scale.lower() == 'plus':
        pt.scale_list.i = (pt.scale_list.i + 1) % length
    else:
        bottle.abort(400, 'Invalid operation `{}`! '
                          'Choose one from `minus` | `plus`'.format(scale))


@dbs.route('/data/channel')
def data_config_channel():
    channel = bottle.request.query.get('channel')
    if channel is None:
        return pt.channel_range
    if channel.isdigit() and int(channel) in range(*pt.channel_range.r):
        pt.channel_range.n = int(channel)
    else:
        bottle.abort(400, 'Invalid channel `{}`! Must be int within [{}, {})'
                          .format(channel, *pt.channel_range.r))


@dbs.route('/data/filter')
def data_config_filter():
    low = bottle.request.query.get('low')
    high = bottle.request.query.get('high')
    notch = bottle.request.query.get('notch')
    rst = ''
    if notch is not None:
        if notch.lower() == 'true':
            pt.notch = True
        elif notch.lower() == 'false':
            pt.notch = False
            rst += 'Realtime notch filter state: OFF<br>'
        else:
            bottle.abort(400, 'Invalid notch `{}`! '
                              'Choose one of `true` | `false`'.format(notch))
    if None not in [low, high]:
        try:
            low, high = float(low), float(high)
        except ValueError:
            bottle.abort(400, 'Invalid bandpass argument! Only accept number.')
        if low == high == 0:
            pt.bandpass.clear()
            rst += 'Realtime bandpass filter state: OFF<br>'
        elif high < low or low < 0:
            bottle.abort(400, 'Invalid bandpass argument! 0 < Low < High.')
        else:
            pt.bandpass.low, pt.bandpass.high = low, high
            signalinfo.bandpass(reader.data_frame, low, high, register=True)
            rst += ('Realtime bandpass filter param: '
                    'low {}Hz -- high {}Hz<br>').format(low, high)
    if rst:
        return rst


@dbs.route('/data/config')
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


def config_save(save):
    save = save.lower()
    if save == 'before':
        saved_data['frame_pre'] = reader.data_frame
        saved_data['channel_pre'] = pt.channel_range.n
        saved_data['pt_pre'] = copy.deepcopy(pt)
    elif save == 'after':
        if saved_data.get('frame_pre') is None:
            return ('Invalid save command! Save data with param '
                    '`before` first. Then save with param `after`')
        saved_data['frame_post'] = reader.data_frame
        saved_data['channel_post'] = pt.channel_range.n
        saved_data['pt_post'] = copy.deepcopy(pt)
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


def config_recorder(command):
    cmd = shlex.split(command)
    if len(cmd) == 1:
        recorder.cmd(cmd[0])
    elif len(cmd) == 2:
        recorder.cmd(**{cmd[0]: cmd[1]})
    else:
        return 'Invalid command: {}'.format(command)
    time.sleep(0.5)


# offer application object for Apache2 and embci.webui
application = dbs
__all__ = ['application']
# THE END
