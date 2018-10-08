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

# requirements.txt: necessary: numpy, scipy, bottle, pylsl, pillow
# requirements.txt: necessary: gevent, bottle-websocket, geventwebsocket
from gevent import monkey
monkey.patch_all(select=False)
import scipy
import numpy as np
from bottle import abort, request, redirect, run, static_file, template, Bottle
from bottle.ext.websocket import websocket, GeventWebSocketServer
from geventwebsocket import WebSocketError
from PIL import Image, ImageDraw
from reportlab.pdfbase import ttfonts, pdfmetrics
from reportlab.pdfgen import canvas

__dir__ = os.path.dirname(os.path.abspath(__file__))
__file__ = os.path.basename(__file__)
path = os.path.abspath(os.path.join(__dir__, '../../../../'))
if path not in sys.path:
    sys.path.append(path)

# from __dir__/../../../../
from embci import BASEDIR, DATADIR
from embci.common import mkuserdir, time_stamp
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

username = 'test'
sample_rate = 500
freq_resolution = 4
length = freq_resolution * 25  # 0-25Hz
x_freq = np.arange(100.0).reshape(1, 100) / freq_resolution
batch_size = 50
channel_range = {'r': (0, 8), 'n': 0}
scale_list = {'a': [pow(10, x) for x in range(10)], 'i': 2}
rainbow = [
    0x0000FF, 0xFFFF00, 0xFF00FF, 0x00FFFF,
    0x00FF00, 0xFF0000, 0x800080, 0xFFA00A,
    0x808080
]
data_save = {
    'tremor_pre': [], 'tremor_post': [],
    'stiff_pre': [], 'stiff_post': [],
    'move_pre': [], 'move_post': []
}


#
# instances
#

#
#  import pylsl
#  inlet = pylsl.StreamInlet(pylsl.resolve_stream()[0])
#
dbs = Bottle()

reader = Reader(sample_rate, sample_time=1, n_channel=8)
reader.enable_bias = True
reader.start()
feature = Features(sample_rate)
bandpass_realtime = (4, 10)
feature.si.bandpass(reader.data_frame, register=True,
                    low=bandpass_realtime[0], high=bandpass_realtime[1])
notch_realtime = True
feature.si.notch(reader.data_frame, register=True)

ws_lock = threading.Lock()


#
# Functions
#

@mkuserdir
def generate_pdf(username, id=0, gender=u'男', age=20, length=500, channel=0,
                 frame_pre=None, frame_post=None, font='Mono', colors=rainbow,
                 fontname=os.path.join(BASEDIR, 'files/fonts/yahei_mono.ttf'),
                 img_size=(300, 200), **ka):
    k = {}
    k['username'] = username = username.decode('utf8')
    k['gender'] = gender = gender.decode('utf8')
    k['age'], k['id'] = age, id = int(age), id.decode('utf8')
    k['length'] = length = reader.window_size
    if frame_pre is None or frame_post is None:
        print('using random data ~')
        frame_pre = np.random.rand(channel, length)
        frame_post = np.random.rand(channel, length)
    k['tb'], k['sb'], k['mb'] = tb, sb, mb = calc_ch_coefs(frame_pre[channel])
    k['ta'], k['sa'], k['ma'] = ta, sa, ma = calc_ch_coefs(frame_post[channel])
    tr, sr, mr = abs(ta - tb) / ta, abs(sa - sb) / sa, abs(ma - mb) / ma
    k['tr'], k['sr'], k['mr'] = tr, sr, mr = map(int, [100*tr, 100*sr, 100*mr])
    # prepare pngs
    data_x = np.arange(length)
    canvas_size = (length, int(float(length) / img_size[0] * img_size[1]))
    img_pre = Image.new('RGB', canvas_size, 'white')
    draw_pre = ImageDraw.Draw(img_pre)
    img_post = Image.new('RGB', canvas_size, 'white')
    draw_post = ImageDraw.Draw(img_post)
    # preprocess raw data
    to_plot = []
    for d in [frame_pre.copy(), frame_post.copy()]:
        d = feature.si.notch(d[:, :length])
        d = feature.si.bandpass(d, ka.get('low', 5), ka.get('high', 15))
        d /= abs(d).max()  # normalize data to [-1, 1]
        d *= canvas_size[1] / 2  # resize to [-half_height, +half_height]
        d += canvas_size[1] / 2  # resize to [0, img_height]
        d[:, 0] = d[:, -1] = 0  # set first and end point to zero
        # to_plot[i] = d
        # save each channel(2018.9.30)
        to_plot.append(channel * [None] + [d[channel]])
        # save one channel(2018.10.2)
    # generate pngs
    # for ch in range(reader.n_channel):  # plot each channel(2018.9.30)
    for ch in [channel]:  # plot specific channel(2018.10.2)
        draw_pre.polygon(
            map(tuple, np.vstack((data_x, to_plot[0][ch])).T),
            outline=colors[ch])
        draw_post.polygon(
            map(tuple, np.vstack((data_x, to_plot[1][ch])).T),
            outline=colors[ch])
    imgpre = os.path.join(username, 'img_pre_' + time_stamp() + '.png')
    img_pre = img_pre.resize((img_size[0] + 4, img_size[1] + 4), 1)
    img_pre = img_pre.crop((2, 2, img_size[0] + 2, img_size[1] + 2))
    img_pre.transpose(1).save(os.path.join(DATADIR, imgpre))
    imgpost = os.path.join(username, 'img_post_' + time_stamp() + '.png')
    img_post = img_post.resize((img_size[0] + 4, img_size[1] + 4), 1)
    img_post = img_post.crop((2, 2, img_size[0] + 2, img_size[1] + 2))
    img_post.transpose(1).save(os.path.join(DATADIR, imgpost))
    # load font
    if font not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(ttfonts.TTFont(font, fontname))
    # render pdf
    pdfname = os.path.join(username, ka.get('filename', time_stamp() + '.pdf'))
    c = canvas.Canvas(os.path.join(DATADIR, pdfname), bottomup=0)
    c.setFont(font, 30)
    c.drawString(65, 80, u'天坛医院DBS术后调控肌电报告单')
    c.setFontSize(20)
    c.line(30, 120, 580, 120)
    c.drawString(
        35, 150, u'姓名: {:4.12s}  性别: {:1.2s}  年龄: {:3d}  病号ID: {}'.format(
            username, gender, age, id))
    c.line(30, 165, 580, 165)
    c.line(30, 710, 580, 710)
    c.drawString(
        35, 740, u'改善率   震颤： {:3d}%    僵直： {:3d}%    运动： {:3d}%'.format(
            tr, sr, mr))
    c.line(30, 755, 580, 755)
    c.drawImage(os.path.join(DATADIR, imgpre), 32, 190)
    c.drawImage(os.path.join(DATADIR, imgpost), 32, 450)
    c.setFontSize(24)
    c.drawString(360, 250, u'术前')
    c.drawString(360, 510, u'术后')
    c.setFontSize(18)
    c.drawString(380, 290, u'震颤： {:7.4f}Hz'.format(tb))
    c.drawString(380, 320, u'僵直： {:7.4f}'.format(sb))
    c.drawString(380, 350, u'运动： {:7.4f}'.format(mb))
    c.drawString(380, 550, u'震颤： {:7.4f}Hz'.format(ta))
    c.drawString(380, 580, u'僵直： {:7.4f}'.format(sa))
    c.drawString(380, 610, u'运动： {:7.4f}'.format(ma))
    c.drawString(35, 795, u'医师签字：')
    c.setFontSize(15)
    c.drawString(450, 800, 'Powered by Cheitech')
    c.save()
    print('[Generate Report PDF] pdf %s saved!' % pdfname)
    k['imgpre'], k['imgpost'], k['pdfname'] = imgpre, imgpost, pdfname
    return k


def calc_ch_coefs(data, distance=25):
    data = feature.si.notch(data)
    b, a = scipy.signal.butter(4, 10.0 / sample_rate, btype='lowpass')
    stiffness = feature.si.rms(
        scipy.signal.lfilter(b, a, feature.si.detrend(data), -1))[0]
    data = feature.si.envelop(data)
    data = feature.si.smooth(data, 12)
    movement = np.average(data)
    data = feature.si.detrend(data)[0]
    data[data < data.max() / 4] = 0
    peaks, heights = scipy.signal.find_peaks(data, 0, distance=distance)
    peaks = np.concatenate(([0], peaks))
    tremor = sample_rate / (np.average(np.diff(peaks)) + 1)
    return tremor, stiffness[0] * 1000, movement * 1000


#
# General API
#


@dbs.route('/')
def main():
    redirect('display.html')


@dbs.route('/<filename:re:\w+\.html>')
def static_html(filename):
    return static_file(filename, root=__dir__)


@dbs.route('/report/download/<pdfpath:path>')
def static_pdf(pdfpath):
    filename = pdfpath.replace('/', '-')
    return static_file(pdfpath, root=DATADIR, download=filename)


@dbs.route('/report')
def report():
    d = request.query.dict.copy()
    for key in d:
        d[key] = d[key][-1]
    if 'frame_pre' not in data_save:
        abort(500, 'Save two frame of data before generating report!')
    d.update(data_save)
    kwargs = generate_pdf(**d)
    pdfname = kwargs.pop('pdfname', 'test/asdf.pdf')
    imgpre = kwargs.pop('imgpre', 'test/pre.png')
    imgpost = kwargs.pop('imgpost', 'test/post.png')
    kwargs['pdf_url'] = 'report/download/{}'.format(pdfname.encode('utf8'))
    kwargs['img_pre_url'] = os.path.join(DATADIR, imgpre)
    kwargs['img_post_url'] = os.path.join(DATADIR, imgpost)
    with open(os.path.join(__dir__, 'report.html'), 'r') as f:
        return template(f.read(), **kwargs)


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
            if notch_realtime:
                data = feature.si.notch_realtime(data)
            if bandpass_realtime:
                data = feature.si.bandpass_realtime(data)
            data_list.append(data)
            if len(data_list) >= batch_size:
                data = np.float32(data_list)[:, channel_range['n']]
                if reader.input_source == 'normal':
                    data = feature.si.detrend(data)[0]
                data = data * scale_list['a'][scale_list['i']]
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
    global bandpass_realtime, notch_realtime
    low, high = request.query.get('low'), request.query.get('high')
    notch = request.query.get('notch')
    rst = ''
    if notch is not None:
        if notch.lower() == 'true':
            notch_realtime = True
            rst += '<p>Realtime notch filter state: ON</p>'
        elif notch.lower() == 'false':
            notch_realtime = False
            rst += '<p>Realtime notch filter state: OFF</p>'
        else:
            abort(500, 'Invalid notch state! Choose one of `true` | `false`')
    if None not in [low, high]:
        try:
            low, high = float(low), float(high)
        except:
            abort(500, 'Invalid bandpass argument! Only number is accepted.')
        if low == high == 0:
            bandpass_realtime = None
            rst += '<p>Realtime bandpass filter state: OFF</p>'
        elif high < low or low < 0:
            abort(500, 'Invalid bandpass argument!')
        else:
            bandpass_realtime = (low, high)
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
    t, s, m = calc_ch_coefs(reader.data_frame[channel_range['n']])
    return {'0': t, '1': s, '2': m}  # js: use json to mimic a fake array


@dbs.route('/data/save')
def data_save_frame():
    action = request.query.get('action', 'before').lower()
    if action == 'before':
        data_save['frame_pre'] = reader.data_frame
        data_save['channel'] = channel_range['n']
    elif action == 'after':
        if data_save.get('frame_pre') is None:
            abort(500, ('Save data with `action=before` first! Only after '
                        'then can you save data with `action=after`'))
        data_save['frame_post'] = reader.data_frame
    else:
        abort(500, 'Invalid param action! Choose one from `before` | `after`')
    return 'Data saved for action: ' + action


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
    return 'set scale to {}'.format(scale_list['a'][scale_list['i']])


@dbs.route('/data/source')
def test_signal():
    src = request.query.get('input_source', 'normal')
    reader.set_input_source(src)
    return 'set input source to {}'.format(reader.input_source)


# offer application object for Apache2
application = dbs
__all__ = ['application']


if __name__ == '__main__':
    os.chdir(__dir__)
    #  server = WSGIServer(('0.0.0.0', 80), dbs,
    #                      handler_class=WebSocketHandler)
    #  server.serve_forever()
    run(app=dbs, host='0.0.0.0', port=80, reloader=True,
        server=GeventWebSocketServer)
