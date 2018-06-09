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
from preprocessing import Processer
from common import time_stamp, check_input
from IO import Serial_Screen_commander, command_dict_uart_screen_v1
from IO import SPI_Screen_commander

__dir__ = os.path.dirname(os.path.abspath(__file__))


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
    p = Processer(sample_rate, sample_time)
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


class Serial_Screen_GUI(Serial_Screen_commander):
    '''
    GUI of UART controlled 2.3' LCD screen
    '''
    _element_color = {
        'point': 'blue', 'line': 'red', 'circle': 'red', 'circlef': 'red',
        'round': 'yellow', 'roundf': 'cyan', 'rect': 'pink', 'rectf': 'orange',
        'round_rect': 'purple', 'round_rectf': 'purple', 'text': 'white',
        'press': 'red'}
    widget = {
        'point': [], 'line': [], 'circle': [], 'circlef': [],
        'round':[], 'roundf':[], 'rect':[], 'rectf':[],
        'round_rect': [], 'round_rectf': [], 'text':[], 'button':[], 'img':[]}
    def __init__(self, port='/dev/ttyS2', baud=115200, width=220, height=176,
                 command_dict=command_dict_uart_screen_v1, *args, **kwargs):
        super(Serial_Screen_GUI, self).__init__(baud, command_dict)
        self._name = self._name[:-2] + ' @ GUI' + self._name[-2:]
        self.start(port)  # set serial screen port
        self.send('dir', 1)  # set screen vertical
        self.width, self.height = width, height
        self.write_lock = threading.Lock()
        self._touch_started = False
        self.touch_sensibility = 4

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
        def func_collector(func):  # this get function to be executed
            def param_collector(self, *a, **k):  # this get params from user
                '''
                Attention!
                You cannot modify variable `name` from `_pre_draw_check` inside
                this function! It will warn that local variable `name` is not
                defined yet. I still dont know why. So I use `static` to store
                `name` temporarily.
                # TODO: search this question
                '''
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
                # pre-processing
                static = name + ('f' if ('fill' in k and k['fill']) else '')
                num = 0 if not len(self.widget[static]) \
                        else (self.widget[static][-1]['id'] + 1)
                k['name'] = static
                k['num'] = num
                # transfer params from user and name & num
                # it will overload name=None and num=None(default)
                # in conclusion:
                #     user provide param *a and **k
                #     wrapper modify them and generate new *a, **k
                #     real function finally recieve *a, **k, and defaults
                func(self, *a, **k)
                if 'render' not in k or ('render' in k and k['render'] is True):
                    self.render(**k)
            return param_collector
        return func_collector

    @_pre_draw_check('img')
    def draw_img(self, x, y, img, **k):
        if not isinstance(img, np.ndarray):
            img = np.array(img, np.uint8)
        if 'Serial' in self._name and len(img.shape) > 2:
            img = img[:, :, 0]
        if 'SPI' in self._name:
            if len(img.shape) == 2:
                img = img[:, :, np.newaxis]
            if img.shape[-1] > 3:
                img = img[:, :, :3]
        self.widget['img'].append({'data': img, 'id': k['num'],
            'x1': x, 'y1': y, 'x2': x + img.shape[1], 'y2': y + img.shape[0]})

    @_pre_draw_check('button')
    def draw_button(self, x, y, s, size=16, cb=None, ct=None, cr=None, ca=None, **k):
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
        self.widget['button'].append({
            'x1': max(x - 1, 0), 'y1': max(y - 1, 0),
            'x2': min(x + w + 1, self.width - 1),
            'y2': min(y + h + 1, self.height - 1),
            'x': x, 'y': y, 's': s, 'id': k['num'], 'size': size,
            'ct': self._element_color['text']  if ct is None else ct,
            'cr': self._element_color['rect']  if cr is None else cr,
            'ca': self._element_color['press'] if ca is None else ca,
            'callback': self._default_callback if cb is None else cb})

    @_pre_draw_check('point')
    def draw_point(self, x, y, c=None, **k):
        self.widget['point'].append({
            'x1': x, 'y1': y, 'x2': x, 'y2': y, 'x': x, 'y': y, 'id': k['num'],
            'c': self._element_color['point'] if c is None else c})

    @_pre_draw_check('line')
    def draw_line(self, x1, y1, x2, y2, c=None, **k):
        self.widget['line'].append({
            'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2, 'id': k['num'],
            'c': self._element_color['line'] if c is None else c})

    @_pre_draw_check('rect')
    def draw_rect(self, x1, y1, x2, y2, c=None, fill=False, **k):
        self.widget[k['name']].append({
            'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2, 'id': k['num'],
            'c': self._element_color[k['name']] if c is None else c})

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
        self.widget[k['name']].append({
            'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2,
            'x': x, 'y': y, 'r': r, 'm': m, 'id': k['num'],
            'c': self._element_color[k['name']] if c is None else c})

    @_pre_draw_check('round_rect')
    def draw_round_rect(self, x1, y1, x2, y2, r, c=None, fill=False, **k):
        self.widget[k['name']].append({
            'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2, 'r': r, 'id': k['num'],
            'c': self._element_color[k['name']] if c is None else c})

    @_pre_draw_check('circle')
    def draw_circle(self, x, y, r, c=None, s=0, e=360, fill=False, **k):
        self.widget[k['name']].append({
            'x1': x - r, 'y1': y - r, 'x2': x + r, 'y2': y + r,
            'x': x, 'y': y, 'r': r, 's': s, 'e': e, 'id': k['num'],
            'c': self._element_color[k['name']] if c is None else c})

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
        self.widget['text'].append({
            'x1': x, 'y1': y,
            'x2': min(x + w, self.width - 1), 'y2': min(y + h, self.height - 1),
            'x': x, 'y': y, 's': s, 'id': k['num'], 'size': size,
            'c': self._element_color['text'] if c is None else c})

    def remove_element(self, name=None, num=None, render=True):
        if not sum([len(i) for i in self.widget.values()]):
            print('No elements now!')
            return
        if name not in self.widget:
            if name is not None:
                print('No candidates for this element `{}`'.format(name))
            print('Choose one from ' + ' | '.join(self.widget.keys()))
            return
        if not len(self.widget[name]):
            print('No %s elements now!' % name)
            return
        ids = [str(i['id']) for i in self.widget[name]]
        if str(num) not in ids:
            if num is not None:
                print('no candidates for this {}:`{}`'.format(name, num))
            print('choose one from ' + ' | '.join(ids))
            return
        self.widget[name].pop(ids.index(str(num)))
        if render:
            self.render()

    def move_element(self, name, num, x, y):
        ids = [i['id'] for i in self.widget[name]]
        e = self.widget[name][ids.index(num)]
        try:
            e['x'] += x; e['y'] += y
        except KeyError:
            e['x1'] += x; e['x2'] += x; e['y1'] += y; e['y2'] += y
        finally:
            self.render()

    def save_layout(self, directory):
        '''
        save current layout(texts, buttons, any elements) in a json file
        '''
        # text string is storaged as gbk in self.widget
        # convert it to utf8 to jsonify
        tmp = self.widget.copy()
        for i in tmp['button']:
            i['callback'] = None
            if 'Serial' in self._name:
                i['s'] = i['s'].decode('gbk')
        for i in tmp['text']:
            if 'Serial' in self._name:
                i['s'] = i['s'].decode('gbk')
        for i in tmp['img']:
            i['data'] = i['data'].tobytes()
        with open(directory + 'layout-%s.json' % time_stamp(), 'w') as f:
            json.dump(tmp, f)

    def load_layout(self, directory):
        '''read in a layout from file'''
        while 1:
            prompt = 'choose one from ' + ' | '.join([os.path.basename(i) \
                    for i in glob.glob(directory + 'layout*.json')])
            try:
                with open(check_input(prompt, {}), 'r') as f:
                    tmp = json.load(f)
            except KeyboardInterrupt:
                print('Abort')
                return
            except:
                print('error!')
        # json.load returns unicode
        for i in tmp['button']:
            if 'Serial' in self._name:
                i['s'] = i['s'].encode('gbk')
            i['callback'] = self._default_callback \
                            if i['callback'] == None else i['callback']
        for i in tmp['text']:
            if 'Serial' in self._name:
                i['s'] = i['s'].encode('gbk')
        for i in self.widget['img']:
            w, h = i['x2'] - i['x1'], i['y2'] - i['y1']
            i['data'] = np.frombuffer(i['data'], np.uint8).reshape(h, w)
        self.widget.update(tmp)
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
        with self.write_lock:
            try:
                if None not in [name, num]: # render an element
                    ids = [i['id'] for i in self.widget[name]]
                    e = self.widget[name][ids.index(num)]
                    self.clear(**e)
                    if name == 'button':
                        e['c'] = e['ct']; self.send('text', **e)
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
        for x in range(e['x2'] - e['x1']):
            for y in range(e['y2'] - e['y1']):
                if e['data'][y, x]:
                    self.send('point', c=e['data'][y, x],
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
        img = Image.open(filename).resize((219, 85))
        self.draw_img(0, 45, np.array(img, dtype=np.uint8))
        self.draw_text(62, 143, '任意点击开始')
        self.draw_text(54, 159, 'click to start')
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
                if x > bt['x1'] and x < bt['x2'] \
                and y > bt['y1'] and y < bt['y2']:
                    with self.write_lock:
                        bt['c'] = bt['ca']
                        self.send('rect', **bt)
                        time.sleep(0.3)
                        bt['c'] = bt['cr']
                        self.send('rect', **bt)
                        time.sleep(0.2)
                    self._callback_threads.append(threading.Thread(
                            target=bt['callback'],
                            kwargs={'x': x, 'y': y, 'bt':bt}))
                    self._callback_threads[-1].start()
        print('[Touch Screen] exiting...')

    def clear(self, x1=None, y1=None, x2=None, y2=None, *a, **k):
        if None in [x1, y1, x2, y2]:
            self.send('clear', *a, **k)
        else:
            self.send('rectf', x1=min(x1, x2), y1=min(y1, y2),
                      x2=max(x1, x2), y2=max(y1, y2), c='black')

    def close(self):
        with self.write_lock:
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
        Serial_Screen_commander:
            start, send, write, close, check_key
        Serial_Screen_GUI:
            calibration_touch_screen, clear, remove_element, move_element,
            draw_img, draw_buttom, draw_point, draw_line, draw_rect, draw_round,
            draw_round_rect, draw_circle, draw_text, render, display_logo,
            save_layout, load_layout, freeze_frame, recover_frame
        SPI_Screen_commander:
            start, send, write, close, setfont, setsize, getsize
            # it will overload conflict functions from Serial_Screen_commander
    '''
    def __init__(self, spi_device=(0, 1), *a, **k):
        super(SPI_Screen_GUI, self).__init__(spi_device)
        self._name = self._name[:-2] + ' @ GUI' + self._name[-2:]
        self.start()
        self.write_lock = threading.Lock()
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
