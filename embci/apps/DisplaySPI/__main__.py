#!/usr/bin/env python
# coding=utf-8
#
# File: EmBCI/embci/apps/DisplaySPI/__main__.py
# Author: Hankso
# Webpage: https://github.com/hankso
# Time: Thu 26 Apr 2018 19:27:13 CST

'''__doc__'''

# built-in
from __future__ import print_function
import os
import time
import threading
import functools
import subprocess
from functools import partial

# requirements.txt: optional: ipython==5.7.0, reportlab
# requirements.txt:
try:
    import IPython
    _NO_IPYTHON_ = False
except ImportError:
    _NO_IPYTHON_ = True
import numpy as np
from scipy import signal
from PIL import Image, ImageDraw
from reportlab.pdfbase import ttfonts, pdfmetrics
from reportlab.pdfgen import canvas

from embci.common import check_input, time_stamp, mkuserdir
from embci.processing import SignalInfo
from embci.viz import SPIScreenGUI as Screen_GUI
from embci.io import ESP32SPIReader as Reader, SocketTCPServer
from embci.constants import (
    RGB565_BLUE, RGB565_GREEN, RGB565_CYAN,
    RGB565_RED, RGB565_MAGENTA, RGB565_YELLOW,
    RGB565_WHITE, RGB565_PURPLE, RGB565_ORANGE,
    RGB565_GREY, RGB888_BLUE, RGB888_GREEN, RGB888_CYAN,
    RGB888_RED, RGB888_MAGENTA, RGB888_YELLOW,
    RGB888_PURPLE, RGB888_ORANGE, RGB888_GREY
)


__dir__ = os.path.dirname(os.path.abspath(__file__))
__icon__ = functools.partial(os.path.join, __dir__, 'icons')


ILI9341_Rainbow = [
    RGB565_BLUE, RGB565_YELLOW, RGB565_MAGENTA, RGB565_CYAN,
    RGB565_GREEN, RGB565_RED, RGB565_PURPLE, RGB565_ORANGE, RGB565_GREY]
RGB_Rainbow = [
    RGB888_BLUE, RGB888_YELLOW, RGB888_MAGENTA, RGB888_CYAN,
    RGB888_GREEN, RGB888_RED, RGB888_PURPLE, RGB888_ORANGE, RGB888_GREY]


def shutdown(*a, **k):
    for flag in flag_list:
        flag[1].set()
    s.close()
    reader.close()
    os.system('shutdown now')


def exit_program(*a, **k):
    for flag in flag_list:
        flag[1].set()
    s.empty_widget()
    s1 = 'Debug Mode'
    w, h = s.getsize(s1, size=25)
    s.draw_text((s.width-w)/2, (s.height-h)/2, s1, 'red')
    time.sleep(2)
    s.close()
    server.close()
    reader.close()


def reboot(*a, **k):
    for flag in flag_list:
        flag[1].set()
    s.close()
    reader.close()
    os.system('reboot')


@mkuserdir
def generate_pdf(username=u'三到四字', gender=u'男', id=0, age=20,
                 fontname='Mono', fontpath='files/fonts/yahei_mono.ttf',
                 **k):
    if fontname not in pdfmetrics.getRegisteredFontNames():
        font = ttfonts.TTFont(fontname, fontpath)
        pdfmetrics.registerFont(font)
    pdfname = os.path.join(__dir__, 'data', username,
                           k.get('filename', time_stamp() + '.pdf'))
    c = canvas.Canvas(pdfname, bottomup=0)
    c.setFont(fontname, 30)
    c.drawString(65, 80, u'天坛医院DBS术后调控肌电报告单')
    c.setFontSize(20)
    c.line(30, 120, 580, 120)
    c.drawString(35, 150,
                 (u'姓名:  {}  '
                  u'性别:  {}  '
                  u'年龄:  {:3d}  '
                  u'病号ID:  {:5d}  ').format(username, gender, age, id))
    c.line(30, 165, 580, 165)
    c.line(30, 710, 580, 710)
    c.drawString(35, 740, u'改善率    震颤： 80%    僵直： 80%    运动： 80%')
    c.line(30, 755, 580, 755)
    c.drawImage('aaa1.png', 35, 190)
    c.drawImage('./aaa1.png', 35, 450)
    c.setFontSize(24)
    c.drawString(360, 250, u'术前')
    c.drawString(360, 510, u'术后')
    c.setFontSize(18)
    c.drawString(380, 290, u'震颤： 12.345Hz')
    c.drawString(380, 320, u'僵直： 123.45')
    c.drawString(380, 350, u'运动： 10.0s')
    c.drawString(380, 550, u'震颤： 12.345Hz')
    c.drawString(380, 580, u'僵直： 123.45')
    c.drawString(380, 610, u'运动： 10.0s')
    c.drawString(35, 795, u'医师签字：                     Powered by Cheitech')
    c.save()
    print('pdf %s saved!' % pdfname)


def update(*a, **k):
    try:
        output = subprocess.check_output('git pull', shell=True,
                                         stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        print('Update failed!' + str(e))
        s.freeze_frame()
        # TODO: draw element to show update failed
        s.recover_frame()
    else:
        # TODO: draw element to show update done
        print('Update success!\n' + output + '\nRebooting now...')
        reboot()


scale_list = {'a': [100, 200, 500,
                    1000, 2000, 5000,
                    10000, 20000, 50000,
                    100000, 200000, 500000,
                    1000000, 2000000, 5000000,
                    10000000],
              'i': 2}

channel_range = {'r': (0, 7), 'n': 0, 'step': 1}


page_list = {'a': ['./files/layouts/layout-DBS-page%d.pcl' % i
                   for i in range(6)],
             'i': 0}


def range_callback(r, operate, prev=None, after=None, *a, **k):
    if prev is not None:
        prev(*a, **k)
    if operate == 'plus':
        r['n'] += r['step']
        if r['n'] > r['r'][1]:
            r['n'] = r['r'][0]
    elif operate == 'minus':
        r['n'] -= r['step']
        if r['n'] < r['r'][0]:
            r['n'] = r['r'][1]
    else:
        return
    if after is not None:
        after(*a, **k)


def list_callback(l, operate, prev=None, after=None, *a, **k):
    if prev is not None:
        prev(*a, **k)
    if operate == 'next':
        l['i'] += 1
    elif operate == 'prev':
        l['i'] -= 1
    else:
        return
    l['i'] %= len(l['a'])
    if after is not None:
        after(*a, **k)


#                    flag_pause         flag_close
flag_list = [(threading.Event(), threading.Event()),  # page0
             (threading.Event(), threading.Event()),  # page1
             (threading.Event(), threading.Event()),  # page2
             (threading.Event(), threading.Event()),  # page3
             (threading.Event(), threading.Event()),  # page4
             (threading.Event(), threading.Event())]  # page5


def change_page(*a, **k):
    time.sleep(0.5)
    page_num = page_list['i']
    s.load_layout(page_list['a'][page_num], extend=False)
    for id in callback_list[page_num]:
        s.widget['button', id]['callback'] = callback_list[page_num][id]
    flag_list[page_num][0].set()
    flag_list[page_num][1].clear()
    func = globals().get('page%d_daemon' % page_num)
    if func is not None:
        threading.Thread(target=func, args=flag_list[page_num]).start()


def change_channel(*a, **k):
    s.widget['text', 15]['s'] = 'CH%d' % channel_range['n']
    s.render('text', 15)


def change_scale(*a, **k):
    scale = scale_list['a'][scale_list['i']]
    exp = int(np.log10(scale))
    s.widget['text', 16]['s'] = '%de%d' % (scale/10**exp, exp)
    s.render('text', 16)


test_dict = dict.fromkeys([(1, i) for i in range(2, 10)] +
                          [(4, i) for i in range(2,  8)])


def reverse_status(*a, **k):
    name = (page_list['i'], k['bt']['id'])
    test_dict[name] = not test_dict[name]


prev = partial(list_callback, l=page_list, operate='prev', after=change_page,
               prev=lambda *a, **k: flag_list[page_list['i']][1].set())
next = partial(list_callback, l=page_list, operate='next', after=change_page,
               prev=lambda *a, **k: flag_list[page_list['i']][1].set())


callback_list = [
    # page0
    # id of button: callback function
    {0: shutdown, 1: next, 2: update, 3: exit_program},
    # page1
    {0: prev, 1: next,
     2: reverse_status, 3: reverse_status,
     4: reverse_status, 5: reverse_status,
     6: reverse_status, 7: reverse_status,
     8: reverse_status, 9: reverse_status},
    # page2
    {0: prev, 1: next,
     2: partial(range_callback, r=channel_range,
                operate='minus', after=change_channel),
     3: partial(range_callback, r=channel_range,
                operate='plus', after=change_channel),
     4: partial(list_callback, l=scale_list,
                operate='next', after=change_scale),
     5: partial(list_callback, l=scale_list,
                operate='prev', after=change_scale)},
    # page3
    {0: prev, 1: next},
    # page4
    {0: prev, 1: next,
     2: reverse_status, 3: reverse_status, 4: reverse_status,
     5: reverse_status, 6: reverse_status, 7: reverse_status},
    # page5
    {0: prev, 1: next, 2: generate_pdf}]


def page1_daemon(flag_pause, flag_close, fps=0.8, thres=0):
    print('turn to page1')
    img_red = Image.open(__icon__('4@300x-8.png')).resize((21, 21))
    img_red = np.array(img_red.convert('RGBA'))
    img_green = Image.open(__icon__('5@300x-8.png')).resize((21, 21))
    img_green = np.array(img_green.convert('RGBA'))
    reader._esp.do_measure_impedance = True
    reader.data_channel
    last_time = time.time()
    last_status = [False] * 8
    while not flag_close.isSet():
        while (time.time() - last_time) < 1.0/fps:
            time.sleep(0.05)
        last_time = time.time()
        flag_pause.wait()
        data = reader.data_channel
        for i in np.arange(8):
            if test_dict[(1, i+2)]:
                s.widget['button', i+2]['s'] = '{:.1e}'.format(data[i])
                s.render('button', i+2)
                if data[i] > thres and not last_status[i]:
                    s.widget['img', i+5]['img'] = img_green
                    s.render('img', i+5)
                    last_status[i] = True
                elif data[i] < thres and last_status[i]:
                    s.widget['img', i+5]['img'] = img_red
                    s.render('img', i+5)
                    last_status[i] = False
    reader._esp.do_measure_impedance = False
    print('leave page1')


def page2_daemon(flag_pause, flag_close, step=1, low=1.5, high=80.0,
                 area=[39, 45, 290, 179], center=112):
    print('turn to page2')
    change_scale()
    line = np.ones((2, area[2]), np.uint16) * center
    data = reader.data_frame
    si.bandpass(data, low, high, register=True)
    si.notch(data, register=True)
    while not flag_close.isSet():
        flag_pause.wait()
        ch = channel_range['n']
        scale = scale_list['a'][scale_list['i']]
        c = ILI9341_Rainbow[ch]
        s._ili.draw_rectf(area[0], area[1],
                          area[0]+step*3, area[3], RGB565_WHITE)
        s.widget['text', 17]['s'] = u'%5.1fs\u2191' % \
            (time.time() - reader._start_time)
        s.render('text', 17)
        for x in np.arange(area[0], area[2], step, dtype=int):
            if flag_close.isSet():
                break
            d = reader.data_channel
            server.send(d)
            data = d[ch]
            filtered = si.bandpass_realtime(si.notch_realtime(data))
            data = center - np.array([data, filtered]) * scale
            line[:, x] = np.uint16(np.clip(data, area[1], area[3]))
            yraw, yflt = line[:, x-step:x+1]
            _x = min((x + step*4), area[2])
            s._ili.draw_line(_x, area[1], _x, area[3], RGB565_WHITE)
            if yraw[0] == yraw[1]:
                s._ili.draw_point(x, yraw[0], RGB565_GREY)
            else:
                s._ili.draw_line(x, yraw.min(), x, yraw.max(), RGB565_GREY)
            if yflt[0] == yflt[1]:
                s._ili.draw_point(x, yflt[0], c)
            else:
                s._ili.draw_line(x, yflt.min(), x, yflt.max(), c)
    print('leave page2')


def page3_daemon(flag_pause, flag_close, fps=0.6, area=[26, 56, 153, 183]):
    print('turn to page3')
    last_time = time.time()
    x = np.linspace(0, reader.sample_time, reader.window_size)
    sin_sig = 1e-3 * np.sin(2*np.pi*32*x).reshape(1, -1)
    x = np.arange(127).reshape(1, -1)
    blank = np.zeros((127, 127, 4), np.uint8)
    while not flag_close.isSet():
        flag_pause.wait()
        if (time.time() - last_time) < 1.0/fps:
            continue
        last_time = time.time()
        ch = channel_range['n']
        c = RGB_Rainbow[ch]
        d = reader.data_frame
        server.send(d)
        d = si.notch(d[ch])
        s.widget['text', 23]['s'] = '%.2f' % movement_coef(d)
        s.render('text', 23)
        d = si.detrend(d)
        amp = si.fft(sin_sig + d, resolution=4)[1][:, :127]
        amp[0, -1] = amp[0, 0] = 0
        amp = np.concatenate((x, 127 * (1 - amp / amp.max()))).T
        img = Image.fromarray(blank)
        ImageDraw.Draw(img).polygon(map(tuple, amp), outline=c)
        s._ili.draw_rectf(*area, c=RGB565_WHITE)
        s._ili.draw_img(area[0], area[1], np.uint8(img))
        s.widget['text', 21]['s'] = '%.2f' % tremor_coef(d)[0]
        s.render('text', 21)
        s.widget['text', 22]['s'] = '%.2f' % stiffness_coef(d)
        s.render('text', 22)
    print('leave page3')


def page4_daemon(flag_pause, flag_close, fps=0.8):
    print('turn to page4')
    start_time = [None, None]
    last_time = time.time()
    while not flag_close.isSet():
        flag_pause.wait()
        if (time.time() - last_time) < 1.0/fps:
            continue
        last_time = time.time()
        ch = channel_range['n']
        d = si.notch(si.detrend(reader[ch]))
        for i in np.arange(2, 8):
            if test_dict[(4, i)]:
                if i % 3 == 2:
                    freq = tremor_coef(d)[0]
                    s.widget['button', i]['s'] = '  %5.1f ' % freq
                    s.render('button', i)
                elif i % 3 == 0:
                    stiff = stiffness_coef(d)
                    s.widget['button', i]['s'] = '  %5.1f ' % stiff
                    s.render('button', i)
                else:
                    if not start_time[(i-2)/3]:
                        start_time[(i-2)/3] = time.time()
                    t = time.time() - start_time[(i-2)/3]
                    s.widget['button', i]['s'] = '  %4.1fs ' % t
                    s.render('button', i)
            elif i % 3 == 1 and start_time[(i-2)/3]:
                start_time[(i-2)/3] = None
        for i in np.arange(21, 24):
            if not test_dict[(4, i-19)] and not test_dict[(4, i-16)]:
                continue
            b, a = s.widget['button', i-19, 's'], s.widget['button', i-16, 's']
            if 'test' in b or 'test' in a:
                continue
            try:
                b, a = float(b[:-2]), float(a[:-2])
                s.widget['text', i]['s'] = '%.2d%%' % (abs(b - a) / b * 100)
                s.render('text', i)
            except ValueError:
                pass
    print('leave page4')


def tremor_coef(data, ch=0, distance=25):
    data = si.smooth(si.envelop(data), 15)[0]
    data[data < data.max() / 4] = 0
    peaks, heights = signal.find_peaks(data, 0, distance=si.sample_rate/10)
    peaks = np.concatenate(([0], peaks))
    return (si.sample_rate / (np.average(np.diff(peaks)) + 1),
            1000 * np.average(heights['peak_heights']))


def stiffness_coef(data, ch=0):
    b, a = signal.butter(4, 10.0/si.sample_rate, btype='lowpass')
    return 1000 * si.rms(signal.lfilter(b, a, data, -1))


def movement_coef(data, ch=0):
    data = si.smooth(si.envelop(data), 10)[0]
    return 1000 * np.average(data)


if __name__ == '__main__':
    username = 'test'
    try:
        print('username: ' + username)
    except NameError:
        username = check_input('Hi! Please offer your username: ', answer={})

    # reset_esp()

    reader = Reader(sample_rate=500, sample_time=2, num_channel=8)
    reader.start()
    server = SocketTCPServer()
    server.start()
    si = SignalInfo(500)
    s = Screen_GUI()
    change_page()
    if _NO_IPYTHON_:
        s.start_touch_screen('/dev/ttyS1')
    else:
        s.start_touch_screen('/dev/ttyS1', block=False)
        IPython.embed()
