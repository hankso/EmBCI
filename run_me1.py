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

# from ./utils
from common import check_input, Signal_Info
from visualization import Screen_GUI

#from IO import ADS1299_reader as Reader
from IO import Fake_data_generator as Reader

from IO import Screen_commander as Commander


menu = {
    'line': [], 'rectf': [], 'circle': [], 'img': [], 'point': [], 'rect': [], 'circlef': [],
    'text': [
        {'s': '\u5317\u4eac\u68cb\u5f08\u79d1\u6280\u6709\u9650\u516c\u53f8', 'y': 0, 'id': 0, 'x': 30, 'c': 3},
        {'s': '\u5317\u4eac\u68cb\u5f08\u79d1\u6280\u6709\u9650\u516c\u53f8', 'y': 0, 'id': 1, 'x': 31, 'c': 3},
        {'s': 'DBS\u53ef\u89c6\u5316\u8c03\u53c2\u4eea', 'y': 40, 'id': 2, 'x': 45, 'c': 15},
        {'s': '\u91c7 \u6837 \u7387', 'y': 68, 'id': 3, 'x': 10, 'c': 15},
        {'s': '\u91c7\u6837\u65f6\u957f', 'y': 88, 'id': 4, 'x': 10, 'c': 15},
        {'s': '\u9009\u62e9\u4efb\u52a1', 'y': 108, 'id': 5, 'x': 10, 'c': 15},
        {'s': '\u6ce2\u5f62\u663e\u793a', 'y': 108, 'id': 6, 'x': 130, 'c': 15},
        {'s': ' 250 Hz ', 'y': 65, 'id': 7, 'x': 130, 'c': 15},
        {'s': ' 3.00 s ', 'y': 85, 'id': 8, 'x': 130, 'c': 15}]
}

def minus_sample_rate(bt):
    sample_rate_range['i'] -= 1
    sample_rate_range['i'] %= len(sample_rate_range['a'])
    for text in s.widget['text']:
        if text['id'] == 7:
            text['s'] = ' %3d Hz ' % sample_rate_range['a']['i']
    
def plus_sample_rate(bt):
    sample_rate_range['i'] += 1
    sample_rate_range['i'] %= len(sample_rate_range['a'])
    for text in s.widget['text']:
        if text['id'] == 7:
            text['s'] = ' %3d Hz ' % sample_rate_range['a']['i']

def minus_sample_time(bt):
    sample_time_range['n'] -= sample_time_range['step']
    if sample_time_range['n'] < sample_time_range['r'][0]:
        sample_time_range['n'] = sample_time_range['r'][1]
    for text in s.widget['text']:
        if text['id'] == 8:
            text['s'] = ' %1.2f s ' % sample_time_range['n']

def plus_sample_time(bt):
    sample_time_range['n'] += sample_time_range['step']
    if sample_time_range['n'] > sample_time_range['r'][1]:
        sample_time_range['n'] = sample_time_range['r'][0]
    for text in s.widget['text']:
        if text['id'] == 8:
            text['s'] = ' %1.2f s ' % sample_time_range['n']
        
def prev_jobs(bt):
    jobs_list['i'] -= 1
    jobs_list['i'] %= len(jobs_list['a'])
    for text in s.widget['text']:
        if text['id'] == 6:
            text['s'] = jobs_list['a']['i']
    for bt in s.widget['button']:
        if bt['id'] == 6:
            bt['callback'] = jobs_list['job_callback']['i']

def next_jobs(bt):
    jobs_list['i'] += 1
    jobs_list['i'] %= len(jobs_list['a'])
    for text in s.widget['text']:
        if text['id'] == 6:
            text['s'] = jobs_list['a']['i']
    for bt in s.widget['button']:
        if bt['id'] == 6:
            bt['callback'] = jobs_list['job_callback']['i']
        
def display_waveform(bt):
    # store old widget
    tmp = s.widget.copy()
    n_channel = 2
    color = np.arange(1, 1 + n_channel)
    scale = np.repeat(100, n_channel)
    area = [0, 40, 220, 144]
    for element in s.widget:
        s.widget[element] = []
    # start and stop flag
    flag_close = threading.Event()
    # plot page widgets
    s.draw_text(32, 20, '波形显示', c=2) # 0
    s.draw_button(156, 20, '返回', callback=lambda x, y: flag_close.set())
    s.draw_text(4, 145, '4-6Hz最大峰值') # 1
    s.draw_text(156, 145, '@') # 2
    s.draw_text(108, 145, '      ', c=1) # 3
    s.draw_text(164, 145, '      ', c=1) # 4
    s.render()
    data = np.zeros((area[2], n_channel))
    ch_height = (area[3] - area[1] - 1)/n_channel
    bias = [area[1] + ch_height/2 + ch_height*ch \
            for ch in range(n_channel)]
    x = 0
    while not flag_close.isSet():
        # first clear current line
        s._c.send('line', x1=x, y1=area[1], x2=x, y2=area[3], c=0)
        # update channel data list
        data[x] = (s.r.ch_data[:n_channel]*scale).astype(np.int) + bias
        # then draw current point
        for i in range(n_channel):
            s._c.send('point', x=x, y=data[x][i], c=color[i])
        # update x axis index
        x = x + 1 if (x + 1) < area[2] else 0
    # recover old widget
    s.widget = tmp.copy()
    s.render()
    
def display_info():
    # store old widget
    tmp = s.widget.copy()
    last_time = time.time()
    si = Signal_Info()
    if (time.time() - last_time) > 1:
        last_time = time.time()
        amp, fre = s.widget['text'][3:5]
        s._c.send('text', x=amp['x'], y=amp['y'], s=amp['s'], c=0)
        s._c.send('text', x=fre['x'], y=fre['y'], s=fre['s'], c=0)
        f, a = si.peek_extract(s.r.get_data(),
                               4, 6, s.r.sample_rate)[0, 0]
        amp['s'] = '%3.3f' % a
        fre['s'] = '%1.2fHz' % f
        print(amp['s'], fre['s'])
        s._c.send('text', x=amp['x'], y=amp['y'], s=amp['s'], c=amp['c'])
        s._c.send('text', x=fre['x'], y=fre['y'], s=fre['s'], c=fre['c'])
    # recover old widget
    s.widget = tmp.copy()
    s.render()

menu.update({
    'button': [
        {'x1': 108, 'x2': 126, 'x': 110, 'cr': 2, 'y2': 81, 'y1': 63, 'y': 65, 'ct': 13, 'callback': minus_sample_rate, 's': '\uff0d', 'id': 0, 'ca': 1},
        {'x1': 108, 'x2': 126, 'x': 110, 'cr': 2, 'y2': 101, 'y1': 83, 'y': 85, 'ct': 13, 'callback': minus_sample_time, 's': '\uff0d', 'id': 1, 'ca': 1},
        {'x1': 196, 'x2': 214, 'x': 198, 'cr': 2, 'y2': 81, 'y1': 63, 'y': 65, 'ct': 13, 'callback': plus_sample_rate, 's': '\uff0b', 'id': 2, 'ca': 1},
        {'x1': 196, 'x2': 214, 'x': 198, 'cr': 2, 'y2': 101, 'y1': 83, 'y': 85, 'ct': 13, 'callback': plus_sample_time, 's': '\uff0b', 'id': 3, 'ca': 1},
        {'x1': 108, 'x2': 126, 'x': 110, 'cr': 2, 'y2': 121, 'y1': 103, 'y': 105, 'ct': 13, 'callback': prev_jobs, 's': '\u2190', 'id': 4, 'ca': 1},
        {'x1': 196, 'x2': 214, 'x': 198, 'cr': 2, 'y2': 121, 'y1': 103, 'y': 105, 'ct': 13, 'callback': next_jobs, 's': '\u2192', 'id': 5, 'ca': 1},
        {'x1': 52, 'x2': 86, 'x': 54, 'cr': 6, 'y2': 164, 'y1': 146, 'y': 148, 'ct': 15, 'callback': display_waveform, 's': '\u5f00\u59cb', 'id': 6, 'ca': 1},
        {'x1': 92, 'x2': 126, 'x': 94, 'cr': 6, 'y2': 164, 'y1': 146, 'y': 148, 'ct': 15, 'callback': None, 's': '\u5173\u673a', 'id': 7, 'ca': 1},
        {'x1': 132, 'x2': 166, 'x': 134, 'cr': 6, 'y2': 164, 'y1': 146, 'y': 148, 'ct': 15, 'callback': None, 's': '\u91cd\u542f', 'id': 8, 'ca': 1}]
})


if __name__ == '__main__':
    username = 'test'
    try:
        print('username: ' + username)
    except NameError:
        username = check_input('Hi! Please offer your username: ', answer={})
        
    sample_rate_range = {'a': [100, 250, 500], 'i': 1}
    sample_time_range = {'r': (0.5, 5.0), 'n': 3.0, 'step': 0.1}
    jobs_list = {'a': ['波形显示', '显示信息'], 'i': 0,
                 'job_callback': [display_waveform,
                                  display_info]}
    
    s = Screen_GUI()