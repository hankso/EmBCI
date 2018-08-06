#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Thu Mar 22 08:26:16 2018

@author: hank
"""
# built-in
import time
import sys; sys.path += ['../src']
import os
import threading
import json
import glob
import pickle
if sys.version_info.major == 2:
    _py_2_ = True
else:
    _py_2_ = False

# pip install matplotlib, numpy, scipy, pyserial, PIL
#  import matplotlib
#  import matplotlib.pyplot as plt
import numpy as np
import scipy.io as sio
import serial
from PIL import Image

# from ../src
from preprocessing import Signal_Info
from common import time_stamp, check_input, find_layouts
from IO import Serial_Screen_commander, command_dict_uart_screen_v1
from IO import SPI_Screen_commander

__dir__ = os.path.dirname(os.path.abspath(__file__))
__filename__ = os.path.basename(__file__)


class Plotter():
    def __init__(self, window_size, where_to_plot=None, n_channel=1):
        '''
        Plot multichannel streaming data on a figure ,
        or in a window if it is offered.
        Param:
            where_to_plot can be a matplotlib figure or a list of axes.
            Default None to create a new figure and split it into n_channels
            window, one for each window
        '''
        if where_to_plot == None:
            self.figure = plt.figure()
            for i in range(n_channel):
                self.figure.add_axes((0, i*(1.0/n_channel),
                                      1, 1.0/n_channel),
                                     facecolor='black')
            self.axes = self.figure.axes

        elif type(where_to_plot) == matplotlib.figure.Figure:
            if not len(where_to_plot.axes):
                for i in range(n_channel):
                    where_to_plot.add_axes((0, i*(1.0/n_channel),
                                            1, 1.0/n_channel),
                                           facecolor='black')
            self.figure, self.axes = where_to_plot, where_to_plot.axes

        elif type(where_to_plot) in [matplotlib.axes.Axes,
                                     matplotlib.axes.Subplot]:
            self.figure, self.axes = where_to_plot.figure, [where_to_plot]

        elif type(where_to_plot) == list and len(where_to_plot):
            if type(where_to_plot[0]) in [matplotlib.axes.Axes,
                                          matplotlib.axes.Subplot]:
                self.figure = where_to_plot[0].figure
                self.axes = where_to_plot

        else:
            raise RuntimeError(('Unknown type param where_to_plot: {}\n'
                                'matplotlib.figure.Figure or list of axes'
                                'is recommended.').format(type(where_to_plot)))
        # clear all axes and create the line
        for a in self.axes:
            a.cla()
            a.plot(np.zeros(window_size))

    def plot(self, data):
        '''
        Axes are initialized in constructor.
        This function only update line data, which is faster than plt.plot()
        '''
        shape = data.shape

        # n_sample x n_channel x window_size
        if len(shape) == 3:
            for i, ch in enumerate(data[0]):
                self.axes[i].lines[0].set_ydata(ch)

        # n_sample x n_channel x freq x time
        elif len(shape) == 4:
            for i, img in enumerate(data[0]):
                    self.axes[i].images[0].set_data(img)

        # Return data in case of using Plotter.plot as callback function
        return data


def view_data_with_matplotlib(data, sample_rate, sample_time, actionname):
    import matplotlib.pyplot as plt; plt.ion()
    if not isinstance(data, np.ndarray):
        data = np.array(data)
    if len(data.shape) != 2:
        raise
    p = Signal_Info(sample_rate)
    for ch, d in enumerate(data):
        plt.figure('%s_%d' % (actionname, ch))

        plt.subplot(321)
        plt.title('raw data')
        plt.plot(d, linewidth=0.5)

        plt.subplot(323)
        plt.title('remove_DC and notch')
        plt.plot(p.notch(d)[0], linewidth=0.5)

        plt.subplot(325)
        plt.title('after fft')
        plt.plot(p.fft(p.notch(p.remove_DC(data)))[0], linewidth=0.5)

        plt.subplot(343)
        plt.title('after stft')
        amp = p.stft(p.remove_DC(p.notch(d)))[0]
        f = np.linspace(0, sample_rate/2, amp.shape[0])
        t = np.linspace(0, sample_time, amp.shape[1])
        plt.pcolormesh(t, f, np.log10(amp))
        highest_col = [col[1] for col in sorted(zip(np.sum(amp, axis=0),
                                                    range(len(t))))[-3:]]
        plt.plot((t[highest_col], t[highest_col]),
                 (0, f[-1]), 'r')
        plt.ylabel('Freq / Hz')
        plt.xlabel('Time / s')

        plt.subplot(344)
        plt.title('Three Max Amptitude'.format(t[highest_col]))
        for i in highest_col:
            plt.plot(amp[:, i], label='time: {:.2f}s'.format(t[i]), linewidth=0.5)
        plt.legend()

        plt.subplot(324)
        t = time.time()
        plt.psd(p.remove_DC(p.notch(d))[0], Fs=250, label='filtered', linewidth=0.5)
        plt.legend()
        plt.title('normal PSD -- used time: %.3fms' % (1000*(time.time()-t)))

        d = p.remove_DC(p.notch(d))[0]
        plt.subplot(326)
        t = time.time()
        amp = 2 * abs(np.fft.rfft(d)) / float(len(d))
        # amp[0] *= 1e13
        plt.plot(10*np.log10(amp*amp)[::12], linewidth=0.5, label='unfiltered')
        plt.title('optimized PSD -- used time: %.3fms' % (1000*(time.time()-t)))
        plt.legend()
        plt.grid()
        plt.xlabel('Frequency')
        plt.ylabel('dB/Hz')


class element_dict(dict):
    def __getitem__(self, items):
        if not isinstance(items, tuple):
            if items not in self and not items.startswith('_') and self:
                print('choose one from `%s`' % '` | `'.join(self.keys()))
                return None
            return dict.__getitem__(self, items)
        for item in items:
            if self is None:
                print('Invalid index {}'.format(item))
                break
            self = self.__getitem__(item)
        return self
    __getattr__ = __getitem__
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__
    __str__ = dict.__str__
    __repr__ = dict.__repr__

class element_list(list):
    def __getitem__(self, id):
        ids = [e.id for e in self]
        if id in ids:
            return list.__getitem__(self, ids.index(id))
        if len(ids):
            print('choose one from `%s`' % '` | `'.join(ids))
        else:
            print('no elements in this list now')
        return None


class Serial_Screen_GUI(Serial_Screen_commander):
    '''
    GUI of UART controlled 2.3' LCD screen
    '''
    _element_color = {
        'point': 'blue', 'line': 'red', 'circle': 'red', 'circlef': 'red',
        'round': 'yellow', 'roundf': 'cyan', 'rect': 'pink', 'rectf': 'orange',
        'round_rect': 'purple', 'round_rectf': 'purple', 'text': 'black',
        'press': 'red', 'bg': 'white'}
    widget = element_dict({'point': element_list(),
        'text': element_list(), 'img': element_list(),
        'button': element_list(), 'line': element_list(),
        'circle': element_list(), 'circlef': element_list(),
        'round': element_list(), 'roundf': element_list(),
        'rect': element_list(), 'rectf': element_list(),
        'round_rect': element_list(), 'round_rectf': element_list()})
    def __init__(self, port='/dev/ttyS2', baud=115200, width=220, height=176,
                 command_dict=command_dict_uart_screen_v1, *args, **kwargs):
        super(Serial_Screen_GUI, self).__init__(baud, command_dict)
        self._name = self._name[:-2] + ' @ GUI' + self._name[-2:]
        self.start(port)  # set serial screen port
        self.send('dir', 1)  # set screen vertical
        self.width, self.height = width, height
        self._touch_started = False
        self.touch_sensibility = 4

    def __str__(self):
        info, max_len = '', 0
        for key in self.widget:
            id_str = ', '.join([e.id for e in self.widget[key]])
            info += ' {:11s} | {}'.format(key, id_str)
            max_len = max(max_len, len(id_str))
        s = ('<{} @ {}\n {}\n'.format(self._name, hex(id(self)), self.__doc__) +
             ' Touch Screen started: {}\n\n'.format(self._touch_started) +
             ' Widget summary:\n elements    | id\n ------------+' +
             '-' * max_len)
        return s + info + '>'

    def start_touch_screen(self, port='/dev/ttyS2', baud=115200):
        self._t = serial.Serial(port, baud)
        self._flag_close = threading.Event()
        self._flag_pause = threading.Event()
        self._flag_pause.set()
        self._read_lock = threading.Lock()
        self._last_touch_time = time.time()
        self._cali_matrix = np.array([[0.2969, 0.2238], [-53.2104, -22.8996]])
        self._touch_thread = threading.Thread(target=self._handle_touch_screen)
        self._touch_thread.setDaemon(True)
        self._touch_thread.start()
        self._touch_started = True
        self._callback_threads = []

    def _pre_draw_check(name):
        '''This decorator can not be used directly'''
        def func_collector(func):
            '''This will get function to be executed'''
            def param_collector(self, *a, **k):
                '''This will get params from user'''
                a = list(a)
                if name in ['point', 'text', 'img', 'button']:
                    a[0] = max(min(a[0], self.width - 1), 0)
                    a[1] = max(min(a[1], self.height - 1), 0)
                elif name in ['circle', 'round']:
                    a[0] = max(min(a[0], self.width - 2), 1)
                    a[1] = max(min(a[1], self.height - 2), 1)
                    right, down = self.width - 1 - a[0], self.height - 1 - a[1]
                    a[2] = max(min(a[0], a[1], right, down, a[2]), 0)
                elif name in ['rect', 'round_rect']:
                    a[0], a[2] = min(a[0], a[2]), max(a[0], a[2])
                    a[1], a[3] = min(a[1], a[3]), max(a[1], a[3])
                    a[0] = max(min(a[0], self.width - 1), 0)
                    a[1] = max(min(a[1], self.height - 1), 0)
                    a[2] = max(min(a[2], self.width - 1), a[0])
                    a[3] = max(min(a[3], self.height - 1), a[1])
                elif name in ['line']:
                    a[0] = max(min(a[0], self.width - 1), 0)
                    a[1] = max(min(a[1], self.height - 1), 0)
                    a[2] = max(min(a[2], self.width - 1), 0)
                    a[3] = max(min(a[3], self.height - 1), 0)
                '''
                # TODO: fix this question
                You cannot modify variable `name` from `_pre_draw_check` inside
                this function! It will warn that local variable `name` is not
                defined yet. I still dont know why. So I use `static` to store
                `name` temporarily.
                '''
                static = name + ('f' if ('fill' in k and k['fill']) else '')
                num = 0 if not len(self.widget[static]) \
                        else (self.widget[static][-1]['id'] + 1)
                k['name'] = static
                k['num'] = num
                # transfer params from user and name & num
                # it will overload name=None and num=None(default)
                # in conclusion:
                #     user provide param *a and **k
                #     this wrapper modify them and generate new *a, **k
                #     real function finally recieve new *a, **k, and defaults
                func(self, *a, **k)
                if 'render' not in k or ('render' in k and k['render']):
                    self.render(**k)
            param_collector.__doc__ = func.__doc__
            param_collector.__name__ = func.__name__
            return param_collector
        return func_collector

    @_pre_draw_check('img')
    def draw_img(self, x, y, img, bg=None, **k):
        if not isinstance(img, np.ndarray):
            img = np.array(img, np.uint8)
        if len(img.shape) == 2:
            img = np.repeat(img[:,:,np.newaxis], 3, axis=2)
        assert len(img.shape) == 3, 'Invalid image shape {}!'.format(img.shape)
        self.widget['img'].append(element_dict({'id': k['num'], 'bg': bg,
            'x': x, 'y': y, 'img': img, 'x1': x, 'y1': y,
            'x2': x + img.shape[1], 'y2': y + img.shape[0]}))

    @_pre_draw_check('button')
    def draw_button(self, x, y, s,
                    size=16, cb=None, ct=None, cr=None, ca=None, **k):
        '''
        draw button on current frame
        params:
            x, y: left upper point of button text
            s: button text string
            cb: callback function, default None
            ct: color of text
            cr: color of outside rect
            ca: color of outside rect when button is pressed
        '''
        # Although there is already `# -*- coding: utf-8 -*-` at file start
        # we'd better explicitly use utf-8 to decode every string in Py2.
        # Py3 default use utf-8 coding, which is really really nice.
        s = s.decode('utf8')
        # English use 8 pixels and Chinese use 16 pixels(GBK encoding)
        if 'Serial' in self._name:
            en_zh = [ord(char) > 255 for char in s]
            w = en_zh.count(False)*8 + en_zh.count(True)*16
            h = 16
            s = s.encode('gbk')
        elif 'SPI' in self._name:
            w, h = self.getsize(s)
        self.widget['button'].append(element_dict({'id': k['num'],
            'x1': max(x - 1, 0), 'y1': max(y - 1, 0),
            'x2': min(x + w + 1, self.width - 1),
            'y2': min(y + h + 1, self.height - 1),
            'x': x, 'y': y, 's': s, 'size': size,
            'ct': ct or self._element_color['text'],
            'cr': cr or self._element_color['rect'],
            'ca': ca or self._element_color['press'],
            'callback': cb or self._default_callback}))

    @_pre_draw_check('point')
    def draw_point(self, x, y, c=None, **k):
        self.widget['point'].append(element_dict({'id': k['num'],
            'x1': x, 'y1': y, 'x2': x, 'y2': y, 'x': x, 'y': y,
            'c': c or self._element_color['point']}))

    @_pre_draw_check('line')
    def draw_line(self, x1, y1, x2, y2, c=None, **k):
        self.widget['line'].append(element_dict({'id': k['num'],
            'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2,
            'c': c or self._element_color['line']}))

    @_pre_draw_check('rect')
    def draw_rect(self, x1, y1, x2, y2, c=None, fill=False, **k):
        self.widget[k['name']].append(element_dict({'id': k['num'],
            'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2,
            'c': c or self._element_color[k['name']]}))

    @_pre_draw_check('round')
    def draw_round(self, x, y, r, m, c=None, fill=False, **k):
        if m == 0:
            x1, y1, x2, y2 = x, y, x + r, y + r
        elif m == 1:
            x1, y1, x2, y2 = x - r, y, x, y + r
        elif m == 2:
            x1, y1, x2, y2 = x - r, y - r, x, y
        elif m == 3:
            x1, y1, x2, y2 = x, y - r, x + r, y
        self.widget[k['name']].append(element_dict({'id': k['num'],
            'x': x, 'y': y, 'r': r, 'm': m,
            'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2,
            'c': c or self._element_color[k['name']]}))

    @_pre_draw_check('round_rect')
    def draw_round_rect(self, x1, y1, x2, y2, r, c=None, fill=False, **k):
        self.widget[k['name']].append(element_dict({'id': k['num'],
            'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2, 'r': r,
            'c': c or self._element_color[k['name']]}))

    @_pre_draw_check('circle')
    def draw_circle(self, x, y, r, c=None, s=0, e=360, fill=False, **k):
        self.widget[k['name']].append(element_dict({'id': k['num'],
            'x1': x - r, 'y1': y - r, 'x2': x + r, 'y2': y + r,
            'x': x, 'y': y, 'r': r, 's': s, 'e': e,
            'c': c or self._element_color[k['name']]}))

    @_pre_draw_check('text')
    def draw_text(self, x, y, s, c=None, size=16, **k):
        s = s.decode('utf8')
        if 'Serial' in self._name:
            en_zh = [ord(char) > 255 for char in s]
            w = en_zh.count(False)*8 + en_zh.count(True)*16
            h = 16
            s = s.encode('gbk')
        elif 'SPI' in self._name:
            self.setsize(size)
            w, h = self.getsize(s)
        self.widget['text'].append(element_dict({'id': k['num'],
            'x': x, 'y': y, 's': s,
            'x1': x, 'y1': y, 'size': size,
            'x2': min(x + w, self.width - 1),
            'y2': min(y + h, self.height - 1),
            'c': c or self._element_color['text']}))

    def remove_element(self, element=None, id=None, render=True):
        elements = [key for key in self.widget.keys() if self.widget[key]]
        if len(elements) == 0:
            print('Empty widget bucket now. Nothing to remove!')
            return
        if element not in elements:
            print('Choose one from `%s`' % '` | `'.join(elements))
            return
        e = self.widget[element, id]
        if e is not None:
            self.widget[element].remove(e)
            if render:
                self.render()

    def move_element(self, element=None, id=None, x=0, y=0):
        e = self.widget[element, id]
        if e is None:
            return
        if 'x' in e:
            e['x'] += x; e['y'] += y
        if 'x1' in e:
            e['x1'] += x; e['x2'] += x; e['y1'] += y; e['y2'] += y
        self.widget[element, id] = e
        self.render()

    def save_layout(self, dir):
        '''
        save current layout(texts, buttons, any elements) in a json file
        '''
        # text string is storaged as gbk in self.widget
        # convert it to utf8 to jsonify
        tmp = self.widget.copy()
        for e in tmp['button']:
            e['callback'] = None
        if 'Serial' in self._name:
            for e in tmp['text'] + tmp['button']:
                e['s'] = e['s'].decode('gbk')
        with open(os.path.join(dir, 'layout-%s.pcl' % time_stamp()), 'w') as f:
            pickle.dump(tmp, f)

    def load_layout(self, dir, render=True):
        '''read in a layout from file'''
        layout = find_layouts(dir)
        if layout is None:
            print(self._name + 'no available layout files in dir ' + dir)
            return
        try:
            with open(layout, 'r') as f:
                tmp = pickle.load(f)
        except Exception as e:
            print(self._name + 'load layout `' + layout + '` error: %s' % e)
            return
        if 'Serial' in self._name:
            for e in tmp['text'] + tmp['button']:
                e['s'] = e['s'].encode('gbk')
        for e in self.widget:
            self.widget[e] += tmp[e]
        if render:
            self.render()

    def freeze_frame(self):
        '''save current frame buffer in background'''
        self._tmp = (self.widget.copy(), self.touch_sensibility)
        for e in self.widget:
            self.widget[e] = []
        self.clear()

    def recover_frame(self):
        '''recover lastest frame buffer from background'''
        if self._tmp:
            self.widget, self.touch_sensibility = self._tmp
            self.render()

    def _default_callback(self, x, y, bt):
        '''default button callback'''
        print('[Touch Screen] touch button %d - %s at %d, %d at %.3f' \
                  % (bt['id'], bt['s'], x, y, time.time()))

    def render(self, name=None, num=None, *a, **k):
        try:
            if None not in [name, num]: # render an element
                ids = [i['id'] for i in self.widget[name]]
                e = self.widget[name][ids.index(num)]
                self.clear(**e)
                if name == 'button':
                    e['c'] = e['ct']; self.send('text', **e)
                    if e['cr'] is not None:
                        e['c'] = e['cr']; self.send('rect', **e)
                elif name == 'img' and 'Serial' in self._name:
                    self._plot_point_by_point(e)
                else:
                    self.send(name, **e)
            else: # render all
                self.clear() # clear all
                for name in self.widget.keys():
                    if name == 'button':
                        for bt in self.widget[name]:
                            bt['c'] = bt['ct']; self.send('text', **bt)
                            if bt['cr'] is not None:
                                bt['c'] = bt['cr']; self.send('rect', **bt)
                    elif name == 'img' and 'Serial' in self._name:
                        for e in self.widget['img']:
                            self._plot_point_by_point(e)
                    else:
                        for e in self.widget[name]:
                            self.send(name, **e)
        except Exception as e:
            print(e)

    def _plot_point_by_point(self, e):
        img = e['img'].copy()
        if len(img.shape) == 3:
            img = img[:,:,0]
        for x in range(e['x2'] - e['x1']):
            for y in range(e['y2'] - e['y1']):
                if img[y, x]:
                    self.send('point', c=e['img'][y, x],
                              x=e['x1'] + x, y=e['y1'] + y)

    def calibration_touch_screen(self):
        if not self._touch_started:
            print('[Screen GUI] touch screen not initialized yet!')
            return
        self._flag_pause.clear() # pause _handle_touch_screen thread
        self.freeze_frame()
        self.touch_sensibility = 1
        self._cali_matrix = np.array([[1, 1], [0, 0]])
        self.draw_text(78, 80, '屏幕校准', c='green')
        self.draw_text(79, 80, '屏幕校准', c='green')
        # points where to be touched
        pts = np.array([[10, 10], [210, 10], [10, 165], [210, 165]])
        # points where user touched
        ptt = np.zeros((4, 2))
        try:
            for i in range(4):
                print('[Calibration] this will be %d/4 points' % (i+1))
                self.draw_circle(pts[i][0], pts[i][1], 4, 'blue')
                ptt[i] = self._get_touch_point()
                print('[Calibration] touch at {}, {}'.format(*ptt[i]))
                self.draw_circle(pts[i][0], pts[i][1], 2, 'blue', fill=True)
            self._cali_matrix = np.array([
                    np.polyfit(ptt[:, 0], pts[:, 0], 1),
                    np.polyfit(ptt[:, 1], pts[:, 1], 1)]).T
            print(('[Screen GUI] calibration done!\nTarget point:\n{}\n'
                   'Touched point:\n{}\ncalibration result matrix:\n{}\n'
                   '').format(ptt, pts, self._cali_matrix))
        except Exception as e:
            print(e)
        finally:
            self.recover_frame()
            self._flag_pause.set() # resume _handle_touch_screen thread

    def display_logo(self, filename):
        self.freeze_frame()
        img = Image.open(filename)
        # adjust img size
        w, h = img.size
        if float(w) / h >= float(self.width) / self.height:
            img = img.resize((self.width, int(float(self.width)/w*h)))
        else:
            img = img.resize((int(float(self.height/h*w)), self.height))
        # place it on center of the frame
        w, h = img.size
        self.draw_img((self.width-w)/2, (self.height-h)/2,
                      np.array(img, dtype=np.uint8), render=False)
        # add guide text
        s1 = '任意点击开始'
        w, h = self.getsize(s1)
        self.draw_text((self.width-w)/2, self.height - 2*h - 2, s1, render=False)
        s2 = 'click to start'
        w, h = self.getsize(s2)
        self.draw_text((self.width-w)/2, self.height - 1*h - 1, s2, render=False)
        self.render()
        # touch screen to continue
        if self._touch_started:
            self._flag_pause.clear()
            with self._read_lock:
                self._t.flushInput()
                self._t.read_until()
            self._flag_pause.set()
        else:
            time.sleep(1)
        self.recover_frame()

    def _get_touch_point(self):
        '''
        parse touch screen data to get point index(with calibration)
        '''
        while 1:
            with self._read_lock:
                self._t.flushInput()
                raw = self._t.read_until().strip()
            if (time.time() - self._last_touch_time) > 1.0/self.touch_sensibility:
                self._last_touch_time = time.time()
                try:
                    yxp = raw.split(',')
                    if len(yxp) == 3:
                        pt = self._cali_matrix[1] + \
                             [int(yxp[1]), int(yxp[0])] * self._cali_matrix[0]
                        print('[Touch Screen] touch at {}, {}'.format(*pt))
                        return abs(pt)
                    else:
                        print('[Touch Screen] Invalid input %s' % raw)
                except:
                    continue

    def _handle_touch_screen(self):
        while not self._flag_close.isSet():
            self._flag_pause.wait()
            x, y = self._get_touch_point()
            for bt in self.widget['button']:
                if x>bt['x1'] and x<bt['x2'] and y>bt['y1'] and y<bt['y2']:
                    if bt['ca'] is not 'None':
                        bt['c'] = bt['ca']; self.send('rect', **bt)
                        time.sleep(0.3)
                        bt['c'] = bt['cr']; self.send('rect', **bt)
                    if bt['callback'] is not None:
                        thread = threading.Thread(
                            target=bt['callback'],
                            kwargs={'x': x, 'y': y, 'bt':bt})
                        thread.start()
                        self._callback_threads.append(thread)
        print('[Touch Screen] exiting...')

    def clear(self, x1=None, y1=None, x2=None, y2=None, *a, **k):
        if None in [x1, y1, x2, y2]:
            self.send('clear', c=self._element_color['bg'])
        else:
            self.send('rectf', c=self._element_color['bg'],
                      x1=min(x1, x2), y1=min(y1, y2),
                      x2=max(x1, x2), y2=max(y1, y2))

    def close(self):
        super(Serial_Screen_GUI, self).close()
        if self._touch_started:
            self._flag_close.set()
            try:
                self._t.write('\xaa\xaa\xaa\xaa') # send close signal
                time.sleep(1)
            except:
                pass
            finally:
                self._t.close()


class SPI_Screen_GUI(SPI_Screen_commander, Serial_Screen_GUI):
    '''
    Because I don't want to write additional samiliar functions with
    `Serial_Screen_GUI` for `SPI_Screen_GUI`, `SPI_Screen_GUI` inherits
    `SPI_Screen_commander` and `Serial_Screen_GUI`.
    It will construct spi connection by initing `SPI_Screen_commander`.
    Although we don't initialize `Serial_Screen_GUI`(i.e. no serial connection
    will be built) when instantiating an object of `SPI_Screen_GUI`, it can get
    access to GUI control functions offered by `Serial_Screen_GUI`.

    Methods Outline:
        Inherit from `SPI_Screen_commander`:
            start, send, write, close, setfont, setsize, getsize
        Inherit from `Serial_Screen_GUI`:
            draw_img, draw_buttom, draw_point,
            draw_line, draw_rect, draw_round,
            draw_round_rect, draw_circle, draw_text,
            render, display_logo, calibration_touch_screen, clear,
            save_layout, load_layout,
            freeze_frame, recover_frame,
            remove_element, move_element,
        Inherit from `Serial_Screen_commander`:
            start(overload), send(overload), write(overload), close(overload),
            check_key
    '''
    def __init__(self, spi_device=(0, 1), *a, **k):
        super(SPI_Screen_GUI, self).__init__(spi_device)
        self._name = self._name[:-2] + ' @ GUI' + self._name[-2:]
        self.start()
        self._touch_started = False
        self.touch_sensibility = 4

    def close(self):
        super(SPI_Screen_GUI, self).close()
        if self._touch_started:
            # `_flag_close` and `_flag_pause` are defined in `start_touch_screen`
            self._flag_close.set()
            try:
                self._t.write('\xaa\xaa\xaa\xaa') # send close signal
                time.sleep(1)
            except:
                pass
            finally:
                self._t.close()



if __name__ == '__main__':
#    plt.ion()
#    fake_data = np.random.random((1, 8, 1000))
#    print(fake_data.shape)
#    p = Plotter(window_size = 1000, n_channel=8)
#    p.plot(fake_data)
# =============================================================================
#
# =============================================================================
    filename = '../data/test/left-1.mat'
    actionname = os.path.basename(filename)
    data = sio.loadmat(filename)[actionname.split('-')[0]][0]
    sample_rate=500; sample_time=6
    view_data_with_matplotlib(data, sample_rate, sample_time, actionname)
# =============================================================================
#
# =============================================================================
#    c = Screen_commander(command_dict=command_dict_uart_screen_v1)
#    c.start()
#    time.sleep(1)
#    print( 'setting screen vertical: {}'.format(c.send('dir', 1)) )
#
#    data = np.sin(np.linspace(0, 6*np.pi, 600))
#    data = np.repeat(data.reshape(1, 600), 8, axis=0)
#    try:
#        while 1:
#            screen_plot_one_channel(c, data, width=220, height=76)
#            screen_plot_multichannels(c, data, range(8))
#            print('new screen!')
#    except KeyboardInterrupt:
#        c.close()
# =============================================================================
#
# =============================================================================
    pass
