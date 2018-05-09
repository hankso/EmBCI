#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Thu Apr 26 19:27:13 2018

@author: hank
"""
# built-in
from __future__ import print_function
import sys, time, threading, numpy as np
sys.path += ['./src', './utils']
from functools import partial

# from ./utils
from common import check_input, Signal_Info, mapping
from visualization import Screen_GUI

from IO import ADS1299_reader as Reader
#from IO import Fake_data_generator as Reader
from IO import Socket_server

menu = {
    'line': [], 'rectf': [], 'circle': [], 'img': [], 'point': [], 'rect': [], 'circlef': [],
    'text': [
        {'s': '\xb1\xb1\xbe\xa9\xc6\xe5\xde\xc4\xbf\xc6\xbc\xbc\xd3\xd0\xcf\xde\xb9\xab\xcb\xbe', 'y': 0, 'id': 0, 'x': 30, 'x1': 30, 'x2': 190, 'y1': 0, 'y2': 16, 'c': 3, },
        {'s': '\xb1\xb1\xbe\xa9\xc6\xe5\xde\xc4\xbf\xc6\xbc\xbc\xd3\xd0\xcf\xde\xb9\xab\xcb\xbe', 'y': 0, 'id': 1, 'x': 31, 'x1': 31, 'x2': 191, 'y1': 0, 'y2': 16, 'c': 3},
        {'s': 'DBS\xbf\xc9\xca\xd3\xbb\xaf\xb5\xf7\xb2\xce\xd2\xc7', 'y': 40, 'id': 2, 'x': 45,   'x1': 45, 'x2': 165, 'y1': 40, 'y2': 56, 'c': 15},
        {'s': '\xb2\xc9 \xd1\xf9 \xc2\xca', 'y': 68, 'id': 3, 'x': 10,   'x1': 10, 'x2': 74, 'y1': 68, 'y2': 84, 'c': 15},
        {'s': '\xb2\xc9\xd1\xf9\xca\xb1\xb3\xa4', 'y': 88, 'id': 4, 'x': 10, 'x1': 10, 'x2': 74, 'y1': 88, 'y2': 104, 'c': 15},
        {'s': '\xd1\xa1\xd4\xf1\xc8\xce\xce\xf1', 'y': 108, 'id': 5, 'x': 10, 'x1': 10, 'x2': 74, 'y1': 108, 'y2': 124, 'c': 15},
        {'s': '\xb2\xa8\xd0\xce\xcf\xd4\xca\xbe', 'y': 108, 'id': 6, 'x': 130, 'x1': 130, 'x2': 194, 'y1': 108, 'y2': 124, 'c': 15},
        {'s': ' 250 Hz ', 'y': 65, 'id': 7, 'x': 130, 'x1': 130, 'x2': 194, 'y1': 65, 'y2': 81, 'c': 15},
        {'s': ' 3.00 s ', 'y': 85, 'id': 8, 'x': 130, 'x1': 130, 'x2': 194, 'y1': 85, 'y2': 101, 'c': 15}]
}


def minus_sample_rate(x, y, bt):
    rate_list['i'] -= 1
    rate_list['i'] %= len(rate_list['a'])
    for text in s.widget['text']:
        if text['id'] == 7:
            text['s'] = ' %3d Hz ' % rate_list['a'][rate_list['i']]
            s.render(name='text', num=7)


def plus_sample_rate(*args, **kwargs):
    rate_list['i'] += 1
    rate_list['i'] %= len(rate_list['a'])
    for text in s.widget['text']:
        if text['id'] == 7:
            text['s'] = ' %3d Hz ' % rate_list['a'][rate_list['i']]
            s.render(name='text', num=7)


def minus_sample_time(*args, **kwargs):
    time_range['n'] -= time_range['step']
    if time_range['n'] < time_range['r'][0]:
        time_range['n'] = time_range['r'][1]
    for text in s.widget['text']:
        if text['id'] == 8:
            text['s'] = ' %1.2f s ' % time_range['n']
            s.render(name='text', num=8)


def plus_sample_time(*args, **kwargs):
    time_range['n'] += time_range['step']
    if time_range['n'] > time_range['r'][1]:
        time_range['n'] = time_range['r'][0]
    for text in s.widget['text']:
        if text['id'] == 8:
            text['s'] = ' %1.2f s ' % time_range['n']
            s.render(name='text', num=8)


def prev_jobs(*args, **kwargs):
    jobs_list['i'] -= 1
    jobs_list['i'] %= len(jobs_list['a'])
    for text in s.widget['text']:
        if text['id'] == 6:
            text['s'] = jobs_list['a'][jobs_list['i']]
            s.render(name='text', num=6)
    for bt in s.widget['button']:
        if bt['id'] == 6:
            bt['callback'] = jobs_list['job_callback'][jobs_list['i']]


def next_jobs(*args, **kwargs):
    jobs_list['i'] += 1
    jobs_list['i'] %= len(jobs_list['a'])
    for text in s.widget['text']:
        if text['id'] == 6:
            text['s'] = jobs_list['a'][jobs_list['i']]
            s.render(name='text', num=6)
    for bt in s.widget['button']:
        if bt['id'] == 6:
            bt['callback'] = jobs_list['job_callback'][jobs_list['i']]


def minus_scale(*args, **kwargs):
    scale_list['i'] -= 1
    scale_list['i'] %= len(scale_list['a'])
    for text in s.widget['text']:
        if text['id'] == 3:
            text['s'] = '%7d ' % scale_list['a'][scale_list['i']]
            s.render(name='text', num=3)


def plus_scale(*args, **kwargs):
    scale_list['i'] += 1
    scale_list['i'] %= len(scale_list['a'])
    for text in s.widget['text']:
        if text['id'] == 3:
            text['s'] = '%7d ' % scale_list['a'][scale_list['i']]
            s.render(name='text', num=3)


def minus_n_channel(*args, **kwargs):
    channel_range['n'] -= channel_range['step']
    if channel_range['n'] < channel_range['r'][0]:
        channel_range['n'] = channel_range['r'][1]
    for text in s.widget['text']:
        if text['id'] == 5:
            text['s'] = '   %2d   ' % channel_range['n']
            s.render(name='text', num=5)


def plus_n_channel(*args, **kwargs):
    channel_range['n'] += channel_range['step']
    if channel_range['n'] > channel_range['r'][1]:
        channel_range['n'] = channel_range['r'][0]
    for text in s.widget['text']:
        if text['id'] == 5:
            text['s'] = '   %2d   ' % channel_range['n']
            s.render(name='text', num=5)


def range_callback(e, operate='plus', name='text', fm=None, num=None, *args, **kwargs):
    if operate == 'plus':
        e['n'] += e['step']
        if e['n'] > e['r'][1]:
            e['n'] = e['r'][0]
    elif operate == 'minus':
        e['n'] -= e['step']
        if e['n'] < e['r'][0]:
            e['n'] = e['r'][1]
    if name and num:
        for i in s.widget[name]:
            if i['id'] == num:
                i['s'] = fm.format(e['n']) if fm else str(e['n'])
                s.render(name=name, num=num)
                
def list_callback(e, operate='next', name='text', fm=None, num=None, *args, **kwargs):
    if operate == 'next':
        e['i'] += 1
    elif operate == 'prev':
        e['i'] -= 1
    e['i'] %= len(e['a'])
    if name and num:
        for i in s.widget[name]:
            if i['id'] == num:
                i['s'] = fm.format(e['a'][e['i']]) if fm else str(e['a'][e['i']])
                s.render(name=name, num=num)


def display_waveform(*args, **kwargs):
    # construct reader
    sample_rate = rate_list['a'][rate_list['i']]
    sample_time = time_range['n']
    n_channel = channel_range['a'][channel_range['i']]
    if not hasattr(s, 'reader'):
        s.reader = Reader(sample_rate, sample_time, n_channel, send_to_pylsl=False)
    s.reader.start()
    color = np.arange(1, 1 + n_channel)
    area = [0, 40, 220, 176]

    # store old widget
    tmp = s.widget.copy()
    for element in s.widget:
        s.widget[element] = []

    # start and stop flag
    flag_close = threading.Event()
    s.clear()

    # plot page widgets
    s.draw_text(5, 1, '波形显示', c=2) # 0
    s.draw_text(4, 1, '波形显示', c=2) # 1
    s.draw_button(5, 18, '返回上层', callback=lambda *a, **k: flag_close.set())
    s.draw_rectangle(72, 0, 219, 35, c=5)
    s.draw_text(74, 1, '幅度') # 2
    s.draw_button(112, 1, '－', callback=minus_scale)
    s.draw_text(134, 1, '%7d ' % scale_list['a'][scale_list['i']]) # 3
    s.draw_button(202, 1, '＋', callback=plus_scale)
    s.draw_text(74, 18, '通道') # 4
    s.draw_button(112, 18, '－', callback=minus_n_channel)
    s.draw_text(134, 18, '   %2d   ' % channel_range['a'][channel_range['i']]) # 5
    s.draw_button(202, 18, '＋', callback=plus_n_channel)
    data = np.zeros((area[2] - area[0], n_channel))
    ch_height = (area[3] - area[1] - 1)/n_channel
    bias = [area[1] + ch_height/2 + ch_height*ch \
            for ch in range(n_channel)]

    # start plotting!
    try:
        x = 0
        while not flag_close.isSet():
            # first clear current line
            s._c.send('line', x1=x, y1=area[1], x2=x, y2=area[3], c=0)
            # update channel data list
            d = s.reader.channel_data[:n_channel]
            d *= scale_list['a'][scale_list['i']]
            data[x] = d.astype(np.int) + bias
            # then draw current point
            for i in range(n_channel):
                if data[x][i] < area[3] and data[x][i] > area[1]:
                    s._c.send('line', x1=x, x2=x, c=color[i],
                              y1=data[(x-1)%area[2]][i], y2=data[x][i])
            # update x axis index
            x = x + 1 if (x + 1) < area[2] else 0
        print('[Display Waveform] terminating...')
    except Exception as e:
        print(e)
    finally:
        # recover old widget
        s.widget = tmp
        s.reader.pause()
        s.render()


def display_info(x, y, bt):
    # construct reader
    sample_rate = rate_list['a'][rate_list['i']]
    sample_time = time_range['n']
    n_channel = 2
    si = Signal_Info()
    if not hasattr(s, 'reader'):
        s.reader = Reader(sample_rate, sample_time, n_channel, send_to_pylsl=False)
    s.reader.start()

    # store old widget
    tmp = s.widget.copy()
    for element in s.widget:
        s.widget[element] = []

    # start and stop flag
    flag_close = threading.Event()
    s.clear()

    # plot page widgets
    s.draw_button(145, 0, '返回上层', callback=lambda *a, **k: flag_close.set())
    s.draw_button(2, 0, '↑', callback=partial(range_callback, f1_range, 'plus', fm='{:2d}', num=0))
    s.draw_text(2, 16, ' 4', c=3) # 0
    s.draw_button(2, 32, '↓', callback=partial(range_callback, f1_range, 'minus', fm='{:2d}', num=0))
    s.draw_text(18, 16, '-') # 1
    s.draw_button(26, 0, '↑', callback=partial(range_callback, f2_range, 'plus', fm='{:2d}', num=0))
    s.draw_text(26, 16, ' 6', c=3) # 2
    s.draw_button(26, 32, '↓', callback=partial(range_callback, f2_range, 'minus', fm='{:2d}', num=0))
    s.draw_text(42, 16, '最大峰值:') # 3
    s.draw_text(114, 16, '     ', c=1) # 4
    s.draw_text(154, 16, '@') # 5
    s.draw_text(162, 16, '     ', c=1) # 6
    s.draw_text(202, 16, 'Hz') # 7
    s.draw_text(42, 32, '1-30Hz频段能量和:') # 8
    s.draw_text(178, 32, '     ', c=1) # 9
    s.draw_text(2, 48, '1-125最大峰值:') # 10
    s.draw_text(114, 48, '     ', c=1) # 11
    s.draw_text(154, 48, '@') # 12
    s.draw_text(162, 48, '     ', c=1) # 13
    s.draw_text(202, 48, 'Hz') # 14
    r_amp = s.widget['text'][4]
    r_fre = s.widget['text'][6]
    energy30 = s.widget['text'][9]
    a_amp = s.widget['text'][11]
    a_fre = s.widget['text'][13]
    area = [0, 50, 220, 176]

    # start display!
    last_time = time.time()
    try:
        while not flag_close.isSet():
            if (time.time() - last_time) > 0.5:
                last_time = time.time()
                data = s.reader.buffer[current_ch_list['a'][current_ch_list['i']]]
                x, y = si.fft(data, sample_rate)
                # get peek of specific duration of signal
                f, a = si.peek_extract((x, y), f1_range['n'], f2_range['n'], sample_rate)[0]
                r_amp['s'] = '%5.3f' % a
                r_fre['s'] = '%5.2f' % f
                s.render(name='text', num=4)
                s.render(name='text', num=6)
                # get peek of all
                f, a = si.peek_extract((x, y), 1, sample_rate/2, sample_rate)[0]
                a_amp['s'] = '%5.3f' % a
                a_fre['s'] = '%5.2f' % f
                s.render(name='text', num=11)
                s.render(name='text', num=13)
                # get energy info
                e = si.energy((x ,y), 1, 30, sample_rate)[0]
                energy30['s'] = '%5.3f' % e
                s.render(name='text', num=9)
                # draw amp-freq graph
                s.clear(*area)
                y = mapping(y[0][:area[2]-area[0]], low=area[3], high=area[1])
                for x in range(1, len(y)):
                    if y[x] != y[x-1]:
                        s._c.send('line', x1=x, x2=x, y1=int(y[x]), y2=int(y[x-1]))
                    else:
                        s._c.send('point', x=x, y=int(y[x]))
    except Exception as e:
        print(e)
    finally:
        # recover old widget
        s.widget = tmp
        s.reader.pause()
        s.render()


menu.update({
    'button': [
        {'x1': 108, 'x2': 126, 'x': 110, 'cr': 2, 'y2': 81, 'y1': 63, 'y': 65, 'ct': 13, 'callback': minus_sample_rate, 's': '\xa3\xad', 'id': 0, 'ca': 1},
        {'x1': 108, 'x2': 126, 'x': 110, 'cr': 2, 'y2': 101, 'y1': 83, 'y': 85, 'ct': 13, 'callback': minus_sample_time, 's': '\xa3\xad', 'id': 1, 'ca': 1},
        {'x1': 196, 'x2': 214, 'x': 198, 'cr': 2, 'y2': 81, 'y1': 63, 'y': 65, 'ct': 13, 'callback': plus_sample_rate, 's': '\xa3\xab', 'id': 2, 'ca': 1},
        {'x1': 196, 'x2': 214, 'x': 198, 'cr': 2, 'y2': 101, 'y1': 83, 'y': 85, 'ct': 13, 'callback': plus_sample_time, 's': '\xa3\xab', 'id': 3, 'ca': 1},
        {'x1': 108, 'x2': 126, 'x': 110, 'cr': 2, 'y2': 121, 'y1': 103, 'y': 105, 'ct': 13, 'callback': prev_jobs, 's': '\xa1\xfb', 'id': 4, 'ca': 1},
        {'x1': 196, 'x2': 214, 'x': 198, 'cr': 2, 'y2': 121, 'y1': 103, 'y': 105, 'ct': 13, 'callback': next_jobs, 's': '\xa1\xfa', 'id': 5, 'ca': 1},
        {'x1': 52, 'x2': 86, 'x': 54, 'cr': 6, 'y2': 164, 'y1': 146, 'y': 148, 'ct': 15, 'callback': display_waveform, 's': '\xbf\xaa\xca\xbc', 'id': 6, 'ca': 1},
        {'x1': 92, 'x2': 126, 'x': 94, 'cr': 6, 'y2': 164, 'y1': 146, 'y': 148, 'ct': 15, 'callback': None, 's': '\xb9\xd8\xbb\xfa', 'id': 7, 'ca': 1},
        {'x1': 132, 'x2': 166, 'x': 134, 'cr': 6, 'y2': 164, 'y1': 146, 'y': 148, 'ct': 15, 'callback': None, 's': '\xd6\xd8\xc6\xf4', 'id': 8, 'ca': 1}]
})


if __name__ == '__main__':
    username = 'test'
    try:
        print('username: ' + username)
    except NameError:
        username = check_input('Hi! Please offer your username: ', answer={})

    rate_list = {'a': [100, 250, 500], 'i': 1}
    time_range = {'r': (0.5, 5.0), 'n': 3.0, 'step': 0.1}
    jobs_list = {'a': ['\xb2\xa8\xd0\xce\xcf\xd4\xca\xbe',
                       '\xcf\xd4\xca\xbe\xd0\xc5\xcf\xa2'],
                 'i': 0,
                 'job_callback': [display_waveform, display_info]}
    scale_list = {'a': [10, 100, 200, 500, 1000, 2000, 5000, 10000], 'i': 4}
    channel_range = {'r': (1, 8), 'n': 1, 'step': 1}
    current_ch_list = {'a': ['channel_%d' % i for i in range(8)], 'i': 0}
    f1_range = {'r': (1, 30), 'n': 4, 'step': 1}
    f2_range = {'r': (1, 30), 'n': 6, 'step': 1}

    server = Socket_server()
    s = Screen_GUI(screen_port='/dev/ttyS1')
# =============================================================================
#     s.display_logo('./files/LOGO.bmp')
# =============================================================================
    s.widget = menu
    s.render()
