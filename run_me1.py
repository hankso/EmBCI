#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Thu Apr 26 19:27:13 2018

@author: hank
"""
# built-in
from __future__ import print_function
import os, sys, time, threading
sys.path += ['./src', './utils']
from functools import partial

# pip install ipython, numpy
import IPython
import numpy as np

# from ./utils
from common import check_input, Signal_Info, mapping
from gpio4 import SysfsGPIO
from preprocessing import Processer
from visualization import Screen_GUI
from IO import ADS1299_reader as Reader
from IO import Socket_server


def shutdown(*args, **kwargs):
    s.close()
    server.close()
    os.system('shutdown now')
    

def reboot(*args, **kwrags):
    s.close()
    server.close()
    os.system('reboot')
    

def range_callback(e, operate='plus', name='text', fm=None, num=None, *args, **kwargs):
    if operate == 'plus':
        e['n'] += e['step']
        if e['n'] > e['r'][1]:
            e['n'] = e['r'][0]
    elif operate == 'minus':
        e['n'] -= e['step']
        if e['n'] < e['r'][0]:
            e['n'] = e['r'][1]
    if name != None and num != None:
        for i in s.widget[name]:
            if i['id'] == num:
                i['s'] = fm.format(e['n']) if fm else str(e['n'])
                s.render(name=name, num=num)
                
def list_callback(e, operate='next', name='text', fm=None, num=None, cb=False, *args, **kwargs):
    if operate == 'next':
        e['i'] += 1
    elif operate == 'prev':
        e['i'] -= 1
    e['i'] %= len(e['a'])
    if name != None and num != None:
        for i in s.widget[name]:
            if i['id'] == num:
                i['s'] = fm.format(e['a'][e['i']]) if fm else str(e['a'][e['i']])
                s.render(name=name, num=num)
        if cb:
            for i in s.widget['button']:
                if i['id'] == num:
                    i['callback'] = e['callback'][e['i']]


def display_waveform(*args, **kwargs):
    # construct reader
    sample_rate = rate_list['a'][rate_list['i']]
    sample_time = time_range['n']
    n_channel = channel_range['n']
    p = Processer(sample_rate, sample_time)
    if not hasattr(s, 'reader'):
        s.reader = Reader(sample_rate, sample_time, n_channel, send_to_pylsl=False)
    s.reader.start()
    color = np.arange(1, 1 + n_channel)
    area = [0, 40, 219, 175]

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
    s.draw_button(5, 19, '返回上层', callback=lambda *a, **k: flag_close.set())
    s.draw_rectangle(72, 0, 219, 35, c=5)
    s.draw_text(74, 1, '幅度') # 2
    s.draw_button(112, 2, '－', partial(list_callback, e=scale_list,
                                       operate='prev', fm='{:8d} ', num=3))
    s.draw_text(134, 1, '%8d' % scale_list['a'][scale_list['i']]) # 3
    s.draw_button(202, 2, '＋', partial(list_callback, e=scale_list,
                                       operate='next', fm='{:8d} ', num=3))
    s.draw_text(74, 18, '通道') # 4
    s.draw_button(112, 19, '－', partial(range_callback, e=channel_range,
                                        operate='minus', fm='   {:2d}   ', num=5))
    s.draw_text(134, 18, '   %2d   ' % channel_range['n']) # 5
    s.draw_button(202, 19, '＋', partial(range_callback, e=channel_range,
                                        operate='plus', fm='   {:2d}   ', num=5))
    data = np.zeros((area[2] - area[0], n_channel))
    data[:, :] = area[1]
    ch_height = (area[3] - area[1] - 1)/n_channel
    bias = [area[1] + ch_height/2 + ch_height*ch \
            for ch in range(n_channel)]

    # start plotting!
    try:
        while 1:
            for x in range(1, area[2]):
                assert not flag_close.isSet()
                # update channel data list
                d = p.remove_DC(s.reader.frame_data)[0, :n_channel, -1] # AC data
                d = bias - d * scale_list['a'][scale_list['i']]
                server.send(d)
                d[d>area[3]] = area[3]; d[d<area[1]] = area[1]
                data[x] = d.astype(np.int)
                # first clear current line
                s._write_lock.acquire()
                s._c.send('line', x1=x, y1=area[1], x2=x, y2=area[3], c=0)
                # then draw current point
                for i in range(n_channel):
                    if data[x][i] != data[x-1][i]:
                        s._c.send('line', x1=x, x2=x, y1=data[x-1][i],
                                  y2=data[x][i], c=color[i])
                    else:
                        s._c.send('point', x=x, y=data[x][i], c=color[i])
                s._write_lock.release()
    except AssertionError:
        pass
    except Exception as e:
        print('[Display Waveform] error: ', end='')
        print(e)
    finally:
        print('[Display Waveform] terminating...')
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
    p = Processer(sample_rate, sample_time)
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
    s.draw_button(187, 1, '返回', callback=lambda *a, **k: flag_close.set())
    s.draw_button(2, 0, '↑', partial(range_callback, e=f1_range,
                                      operate='plus', fm='{:2d}', num=0))
    s.draw_text(0, 17, ' 4', c=3) # 0
    s.draw_button(2, 36, '↓', partial(range_callback, e=f1_range,
                                       operate='minus', fm='{:2d}', num=0))
    s.draw_text(16, 17, '-') # 1
    s.draw_button(26, 0, '↑', partial(range_callback, e=f2_range,
                                       operate='plus', fm='{:2d}', num=2))
    s.draw_text(24, 17, ' 6', c=3) # 2
    s.draw_button(26, 36, '↓', partial(range_callback, e=f2_range,
                                        operate='minus', fm='{:2d}', num=2))
    s.draw_text(44, 0, '幅度') # 3
    s.draw_button(78, 1, '－', partial(list_callback, e=scale_list,
                                       operate='prev', fm='{:8d}', num=4))
    s.draw_text(96, 0, '%8d ' % scale_list['a'][scale_list['i']]) # 4
    s.draw_button(168, 1, '＋', partial(list_callback, e=scale_list,
                                        operate='next', fm='{:8d}', num=4))
    s.draw_text(40, 18, '最大峰值') # 5
    s.draw_text(104, 18, '       ', c=1) # 6 7*8=56
    s.draw_text(163, 18, '     ', c=1) # 7 5*8=40
    s.draw_text(203, 18, 'Hz') # 8
    s.draw_text(43, 34, '1-30Hz能量和') # 9
    s.draw_text(139, 34, '          ', c=1) # 10 10*8=80
    s.draw_text(0, 53, '1-125最大峰值') # 11
    s.draw_text(104, 53, '       ', c=1) # 12 7*8=56
    s.draw_text(163, 53, '     ', c=1) # 13 5*8=40
    s.draw_text(203, 53, 'Hz') # 14
    
    r_amp = s.widget['text'][6]
    r_fre = s.widget['text'][7]
    egy30 = s.widget['text'][10]
    a_amp = s.widget['text'][12]
    a_fre = s.widget['text'][13]
    area = [0, 70, 219, 175]

    # start display!
    last_time = time.time()
    try:
        while not flag_close.isSet():
            if (time.time() - last_time) > 0.5:
                last_time = time.time()
                data = s.reader.buffer[current_ch_list['a'][current_ch_list['i']]]
                x, y = si.fft(p.notch(p.remove_DC(data)), sample_rate)
                # get peek of specific duration of signal
                f, a = si.peek_extract((x, y), f1_range['n'], f2_range['n'], sample_rate)[0]
                r_amp['s'] = '%.1e' % a
                r_fre['s'] = '%5.2f' % f
                # get peek of all
                f, a = si.peek_extract((x, y), 1, sample_rate/2, sample_rate)[0]
                a_amp['s'] = '%.1e' % a
                a_fre['s'] = '%5.1f' % f
                a_f_m = f
                # get energy info
                e = si.energy((x ,y), 1, 30, sample_rate)[0]
                egy30['s'] = '%.4e' % e
                # draw amp-freq graph
                s.clear(*area)
                y = area[3] - y * scale_list['z'][scale_list['i']]
                server.send(y)
                for x in range( 1, min(area[2], len(y)) ):
                    s._write_lock.acquire()
                    if y[x] != y[x-1]:
                        s._c.send('line', x1=x, x2=x, y1=int(y[x-1]),
                                  y2=int(y[x]), c=3)
                    else:
                        s._c.send('point', x=x, y=int(y[x]), c=3)
                    s._write_lock.release()
                s._c.send('line', x1=int(f), y1=area[1], x2=int(a_f_m), y2=area[3], c=1)
                # render elements
                s.render(name='text', num=6)
                s.render(name='text', num=7)
                s.render(name='text', num=10)
                s.render(name='text', num=12)
                s.render(name='text', num=13)
    except Exception as e:
        print('[Display Info] error: ', end='')
        print(e)
    finally:
        # recover old widget
        s.widget = tmp
        s.reader.pause()
        s.render()



rate_list = {'a': [100, 250, 500], 'i': 1}

time_range = {'r': (0.5, 5.0), 'n': 3.0, 'step': 0.1}

jobs_list = {'a': ['\xb2\xa8\xd0\xce\xcf\xd4\xca\xbe',
                   '\xcf\xd4\xca\xbe\xd0\xc5\xcf\xa2'],
             'i': 0,
             'callback': [display_waveform, display_info]}

scale_list = {'a': [10, 100, 500, 1000, 2000, 5000, 10000, 50000, 100000, 1000000], 'i': 6}

channel_range = {'r': (1, 8), 'n': 1, 'step': 1}

current_ch_list = {'a': ['channel%d' % i for i in range(8)], 'i': 0}

f1_range = {'r': (1, 30), 'n': 4, 'step': 1}

f2_range = {'r': (1, 30), 'n': 6, 'step': 1}

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
        {'s': ' 3.00 s ', 'y': 85, 'id': 8, 'x': 130, 'x1': 130, 'x2': 194, 'y1': 85, 'y2': 101, 'c': 15}],
    'button': [
        {'x1': 108, 'x2': 126, 'x': 110, 'cr': 2, 'y2': 81, 'y1': 63, 'y': 65,
         'ct': 13, 's': '\xa3\xad', 'id': 0, 'ca': 1, 
         'callback': partial(list_callback, e=rate_list, operate='prev', fm=' {:3d} Hz ', num=7)},
        {'x1': 108, 'x2': 126, 'x': 110, 'cr': 2, 'y2': 101, 'y1': 83, 'y': 85,
         'ct': 13, 's': '\xa3\xad', 'id': 1, 'ca': 1,
         'callback': partial(range_callback, e=time_range, operate='minus', fm=' {:1.2f} s ', num=8)},
        {'x1': 196, 'x2': 214, 'x': 198, 'cr': 2, 'y2': 81, 'y1': 63, 'y': 65,
         'ct': 13, 's': '\xa3\xab', 'id': 2, 'ca': 1,
         'callback': partial(list_callback, e=rate_list, operate='next', fm=' {:3d} Hz ', num=7)},
        {'x1': 196, 'x2': 214, 'x': 198, 'cr': 2, 'y2': 101, 'y1': 83, 'y': 85,
         'ct': 13, 's': '\xa3\xab', 'id': 3, 'ca': 1,
         'callback': partial(range_callback, e=time_range, operate='plus', fm=' {:1.2f} s ', num=8)},
        {'x1': 108, 'x2': 126, 'x': 110, 'cr': 2, 'y2': 121, 'y1': 103, 'y': 105,
         'ct': 13, 's': '\xa1\xfb', 'id': 4, 'ca': 1,
         'callback': partial(list_callback, e=jobs_list, operate='prev', num=6, cb=True)},
        {'x1': 196, 'x2': 214, 'x': 198, 'cr': 2, 'y2': 121, 'y1': 103, 'y': 105,
         'ct': 13, 's': '\xa1\xfa', 'id': 5, 'ca': 1,
         'callback': partial(list_callback, e=jobs_list, operate='next', num=6, cb=True)},
        {'x1': 52, 'x2': 86, 'x': 54, 'cr': 6, 'y2': 164, 'y1': 146, 'y': 148,
         'ct': 15, 's': '\xbf\xaa\xca\xbc', 'id': 6, 'ca': 1,
         'callback': display_waveform},
        {'x1': 92, 'x2': 126, 'x': 94, 'cr': 6, 'y2': 164, 'y1': 146, 'y': 148,
         'ct': 15, 'callback': shutdown, 's': '\xb9\xd8\xbb\xfa', 'id': 7, 'ca': 1},
        {'x1': 132, 'x2': 166, 'x': 134, 'cr': 6, 'y2': 164, 'y1': 146, 'y': 148,
         'ct': 15, 'callback': reboot, 's': '\xd6\xd8\xc6\xf4', 'id': 8, 'ca': 1}]
}


if __name__ == '__main__':
    username = 'test'
    try:
        print('username: ' + username)
    except NameError:
        username = check_input('Hi! Please offer your username: ', answer={})
        
    reset_avr = SysfsGPIO(10) # PA10
    reset_avr.export = True
    reset_avr.direction = 'out'
    reset_avr.value = 0
    time.sleep(1)
    reset_avr.value = 1
    time.sleep(1)
    
    try:
        s = Screen_GUI(screen_port='/dev/ttyS1')
        server = Socket_server()
        s.start_touch_screen('/dev/ttyS2')
#        stop = virtual_serial()
#        s.start_touch_screen('/dev/pts/0')
#        s1 = serial.Serial('/dev/pts/1', 115200)
        s.display_logo('./files/LOGO.bmp')
        s.widget = menu
        s.render()
#        IPython.embed()
        while 1:
            time.sleep(100)
    except KeyboardInterrupt:
        print('keyboard interrupt shutdown')
    except SystemExit:
        print('touch screen shutdown')
    except Exception:
        IPython.embed()
    finally:
        s.close()
#        s1.close()
#        stop.set()
        server.close()