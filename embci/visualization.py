#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Thu Mar 22 08:26:16 2018

@author: hank
"""
# built-in
import time
import sys
import os
import threading
import pickle
import select

# requirements.txt: data-processing: numpy, scipy
# requirements.txt: drivers: pyserial
# requirements.txt: necessary: pillow, decorator
# requirements.txt: optional: matplotlib
try:
    import matplotlib.pyplot as plt
    _NO_PLT_ = False
except:
    _NO_PLT_ = True
import numpy as np
import scipy.io as sio
import serial
from PIL import Image
from decorator import decorator

from .common import time_stamp, find_gui_layouts
from .io import Serial_Screen_commander, command_dict_uart_screen_v1
from .io import SPI_Screen_commander
from .preprocess import Signal_Info
from embci import DATADIR

__dir__ = os.path.dirname(os.path.abspath(__file__))
__file__ = os.path.basename(__file__)


def view_data_with_matplotlib(data, sample_rate, sample_time, actionname):
    if _NO_PLT_:
        return
    plt.ion()
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
            plt.plot(amp[:, i], linewidth=0.5,
                     label='time: {:.2f}s'.format(t[i]))
        plt.legend()

        plt.subplot(324)
        t = time.time()
        plt.psd(p.remove_DC(p.notch(d))[0], Fs=250,
                label='filtered', linewidth=0.5)
        plt.legend()
        used_time = 1000 * (time.time() - t)
        plt.title('normal PSD -- used time: %.3fms' % used_time)

        d = p.remove_DC(p.notch(d))[0]
        plt.subplot(326)
        t = time.time()
        amp = 2 * abs(np.fft.rfft(d)) / float(len(d))
        # amp[0] *= 1e13
        plt.plot(10*np.log10(amp*amp)[::12], linewidth=0.5, label='unfiltered')
        used_time = 1000 * (time.time() - t)
        plt.title('optimized PSD -- used time: %.3fms' % used_time)
        plt.legend()
        plt.grid()
        plt.xlabel('Frequency')
        plt.ylabel('dB/Hz')


# TODO: use decorator to make it a real decorator
def _pre_draw_check(name):
    '''This function is a decorator factory that return a decorator'''
    #
    #  def func_collector(func):
    #      '''This will get function to be executed'''
    #      def param_collector(self, *a, **k):
    #          '''This will get params from user'''
    #          # some code here
    #      param_collector.__doc__ = func.__doc__
    #      param_collector.__name__ = func.__name__
    #      return param_collector
    #  return func_collector
    #

    @decorator
    def caller(func, self, *a, **k):
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

        # FIXME: You cannot modify variable `name` from `_pre_draw_check`
        # inside this function! It will warn that local variable `name` is
        # not defined yet. I still dont know why. So I use `static` to
        # store `name` temporarily.
        static = name + ('f' if ('fill' in k and k['fill']) else '')
        num = (0 if not len(self.widget[static])
               else (self.widget[static][-1]['id'] + 1))
        k['name'] = static
        k['id'] = num
        # transfer params from user and name & num
        # it will overload name=None and num=None(default)
        # in conclusion:
        #     user provide param *a and **k
        #     this wrapper modify them and generate new *a, **k
        #     real function finally recieve new *a, **k, and defaults
        func(self, *a, **k)
        if k.get('render', True):
            self.render(element=static, id=num)
    return caller


class element_dict(dict):
    def __getitem__(self, items):
        if not isinstance(items, tuple):
            if items is None or items not in self \
               and not items.startswith('_') and self:
                keys = list(self.keys())
                print('choose one from `%s`' % '` | `'.join(map(str, keys)))
                return None
            return dict.__getitem__(self, items)
        for item in items:
            if self is None:
                print('Invalid index {}'.format(item))
                break
            self = self.__getitem__(item)
        return self
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__
    __str__ = dict.__str__
    __repr__ = dict.__repr__


class element_list(list):
    def __getitem__(self, items):
        if not isinstance(items, tuple):
            id = items
            if isinstance(id, int) and id < 0:
                return list.__getitem__(self, id)
            ids = [e['id'] for e in self]
            if id in ids:
                return list.__getitem__(self, ids.index(id))
            if len(ids):
                print('choose one from `%s`' % '` | `'.join(map(str, ids)))
            else:
                print('no elements in this list now')
            return None
        for item in items:
            if self is None:
                print('Invalid index {}'.format(item))
                break
            self = self.__getitem__(item)
        return self
    __str__ = list.__str__
    __repr__ = list.__repr__

    def index(self, element):
        return element['id']

    def pop(self, id):
        ids = [e['id'] for e in self]
        return list.pop(self, ids.index(id))

    def remove(self, element):
        self.pop(self.index(element))


class Serial_Screen_GUI(Serial_Screen_commander):
    '''
    GUI of UART controlled 2.3' LCD screen
    '''
    _element_color = {
        'bg': 'white', 'press': ['red', 'cyan'],
        'point': 'blue', 'line': 'red', 'circle': 'red', 'circlef': 'red',
        'round': 'yellow', 'roundf': 'cyan', 'rect': 'pink', 'rectf': 'orange',
        'round_rect': 'purple', 'round_rectf': 'purple', 'text': 'black'}
    widget = element_dict({
        'point': element_list(), 'text': element_list(), 'img': element_list(),
        'button': element_list(), 'line': element_list(),
        'circle': element_list(), 'circlef': element_list(),
        'round': element_list(), 'roundf': element_list(),
        'rect': element_list(), 'rectf': element_list(),
        'round_rect': element_list(), 'round_rectf': element_list()})

    def __init__(self, port='/dev/ttyS2', baud=115200, width=220, height=176,
                 command_dict=command_dict_uart_screen_v1, *args, **kwargs):
        super(Serial_Screen_GUI, self).__init__(baud, command_dict)
        self._name = self._name[:-2] + ' @ GUI' + self._name[-2:]
        self._encoding = 'gbk'
        self.start(port)  # set serial screen port
        self.send('dir', 1)  # set screen vertical
        self.width, self.height = width, height

        self._touch_started = False
        self._cali_matrix = np.array([[0.2969, 0.2238], [-53.2104, -22.8996]])
        self.touch_sensibility = 4

    def __repr__(self):
        info, max_len = '', 12
        for key in self.widget:
            id_str = ', '.join(map(str, [e['id'] for e in self.widget[key]]))
            info += ' {:11s} | {}\n'.format(key, id_str if id_str else None)
            max_len = max(max_len, len(id_str))
        info = ('<{}at {}\n'.format(self._name, hex(id(self))) +
                ' Touch Screen started: {}\n\n'.format(self._touch_started) +
                ' Widget summary:\n elements    | id\n ------------+' +
                '-' * max_len + '\n') + info + '>'
        return info

    def start_touch_screen(self, port='/dev/ttyS2', baud=115200, block=False):
        self._touch = serial.Serial(port, baud)
        self._touch.flushInput()
        self._flag_close = threading.Event()
        self._flag_pause = threading.Event()
        self._flag_pause.set()
        self._read_lock = threading.Lock()
        self._read_epoll = select.epoll()
        self._read_epoll.register(self._touch, select.EPOLLIN)
        self._last_touch = time.time()
        self._callback_threads = []
        self._touch_thread = threading.Thread(target=self._handle_touch)
        self._touch_thread.setDaemon(True)
        self._touch_thread.start()
        self._touch_started = True
        if block:
            # block current thread(usually main thread) by looply sleep, until
            # `self.close` is called or `self._flag_close` is set.
            while not self._flag_close.isSet():
                time.sleep(5)

    def calibration_touch_screen(self, *a, **k):
        if not self._touch_started:
            print('[Screen GUI] touch screen not initialized yet!')
            return
        self._flag_pause.clear()  # pause _handle_touch thread
        self.freeze_frame()
        self.touch_sensibility = 1
        self._cali_matrix = np.array([[1, 1], [0, 0]])
        s = 'touch calibration'
        w, h = self.getsize(s, size=20)
        self.draw_text((self.width - w)/2, (self.height - h)/2, s, c='green')
        # points where to be touched
        pts = np.array([[20, 20],
                        [self.width-20, 20],
                        [20, self.height-20],
                        [self.width-20, self.height-20]])
        # points where user touched
        ptt = np.zeros((4, 2))
        try:
            for i in range(4):
                print('[Calibration] this will be %d/4 points' % (i+1))
                self.draw_circle(pts[i][0], pts[i][1], 4, 'blue')
                ptt[i] = self._get_touch_point()
                print('[Calibration] touch at {}, {}'.format(*ptt[i]))
                self.draw_circle(pts[i][0], pts[i][1], 2, 'green', fill=True)
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
            self._flag_pause.set()  # resume _handle_touch thread

    @_pre_draw_check('img')
    def draw_img(self, x, y, img, bg=None, **k):
        if not isinstance(img, np.ndarray):
            img = np.array(img, np.uint8)
        if len(img.shape) == 2:
            img = np.repeat(img[:, :, np.newaxis], 3, axis=2)
        assert len(img.shape) == 3, 'Invalid image shape {}!'.format(img.shape)
        self.widget['img'].append(element_dict({
            'id': k['id'], 'bg': bg, 'x': x, 'y': y, 'img': img,
            'x1': x, 'y1': y, 'x2': x + img.shape[1], 'y2': y + img.shape[0]}))

    @_pre_draw_check('button')
    def draw_button(self, x, y, s, size=16, font=None, callback=None,
                    ct=None, color_text=None, cr=None, color_rect=None, **k):
        '''
        draw button on current frame
        params:
            x, y: left upper point of button text
            s: button text string
            callback: callback function, default None
            color_text | ct: color of text
            color_rect | cr color of outside rect
        '''
        w, h = self.getsize(s, size, font)
        if sys.version_info.major == 2 and not isinstance(s, unicode):
            s = s.decode('utf8')
            if self._encoding != 'utf8':
                s = s.encode(self._encoding)
        self.widget['button'].append(element_dict({
            'id': k['id'], 'font': font,
            'x1': max(x - 1, 0), 'y1': max(y - 1, 0),
            'x2': min(x + w + 1, self.width - 1),
            'y2': min(y + h + 1, self.height - 1),
            'x': x, 'y': y, 's': s, 'size': size,
            'ct': ct or color_text or self._element_color['text'],
            'cr': cr or color_rect or self._element_color['rect'],
            'callback': callback or self._default_callback}))

    @_pre_draw_check('point')
    def draw_point(self, x, y, c=None, **k):
        self.widget['point'].append(element_dict({
            'x1': x, 'y1': y, 'x2': x, 'y2': y, 'x': x, 'y': y,
            'id': k['id'], 'c': c or self._element_color['point']}))

    @_pre_draw_check('line')
    def draw_line(self, x1, y1, x2, y2, c=None, **k):
        self.widget['line'].append(element_dict({
            'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2,
            'id': k['id'], 'c': c or self._element_color['line']}))

    @_pre_draw_check('rect')
    def draw_rect(self, x1, y1, x2, y2, c=None, fill=False, **k):
        self.widget[k['name']].append(element_dict({
            'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2,
            'id': k['id'], 'c': c or self._element_color[k['name']]}))

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
        self.widget[k['name']].append(element_dict({
            'x': x, 'y': y, 'r': r, 'm': m,
            'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2,
            'id': k['id'], 'c': c or self._element_color[k['name']]}))

    @_pre_draw_check('round_rect')
    def draw_round_rect(self, x1, y1, x2, y2, r, c=None, fill=False, **k):
        self.widget[k['name']].append(element_dict({
            'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2, 'r': r,
            'id': k['id'], 'c': c or self._element_color[k['name']]}))

    @_pre_draw_check('circle')
    def draw_circle(self, x, y, r, c=None, s=0, e=360, fill=False, **k):
        self.widget[k['name']].append(element_dict({
            'x1': x - r, 'y1': y - r, 'x2': x + r, 'y2': y + r,
            'x': x, 'y': y, 'r': r, 's': s, 'e': e,
            'id': k['id'], 'c': c or self._element_color[k['name']]}))

    @_pre_draw_check('text')
    def draw_text(self, x, y, s, c=None, size=16, font=None, **k):
        w, h = self.getsize(s, size, font)
        if sys.version_info.major == 2 and not isinstance(s, unicode):
            s = s.decode('utf8')
            if self._encoding != 'utf8':
                s = s.encode(self._encoding)
        self.widget['text'].append(element_dict({
            'x': x, 'y': y, 's': s, 'size': size,
            'x1': x, 'y1': y, 'font': font,
            'x2': min(x + w, self.width - 1),
            'y2': min(y + h, self.height - 1),
            'id': k['id'], 'c': c or self._element_color['text']}))

    def render(self, element=None, id=None, *a, **k):
        '''Render elements stored in self.widget to screen'''
        try:
            # render one element
            if None not in [element, id]:
                e = self.widget[element, id]
                if e is None:
                    return
                self.clear(**e)  # clear specific element
                if element == 'button':
                    e['c'] = e['ct']
                    self.send('text', **e)
                    if e['cr'] != 'None':
                        e['c'] = e['cr']
                        self.send('rect', **e)
                else:
                    self.send(element, **e)
            # render all
            else:
                self.clear()  # clear all
                for element in self.widget.keys():
                    if element == 'button':
                        for bt in self.widget[element]:
                            bt['c'] = bt['ct']
                            self.send('text', **bt)
                            if bt['cr'] != 'None':
                                bt['c'] = bt['cr']
                                self.send('rect', **bt)
                    else:
                        for e in self.widget[element]:
                            self.send(element, **e)
        except Exception as e:
            print(self._name + 'render error: {}'.format(e))

    def display_img(self, filename_or_img, *a, **k):
        if isinstance(filename_or_img, str):
            img = Image.open(filename_or_img)
        elif isinstance(filename_or_img, np.ndarray):
            img = Image.fromarray(filename_or_img)
        elif Image.isImageType(filename_or_img):
            img = filename_or_img
        else:
            return
        self.freeze_frame()
        # adjust img size
        w, h = img.size
        if float(w) / h >= float(self.width) / self.height:
            img = img.resize((self.width, int(float(self.width)/w*h)))
        else:
            img = img.resize((int(float(self.height)/h*w), self.height))
        # place it on center of the frame
        w, h = img.size
        self.draw_img((self.width-w)/2, (self.height-h)/2, np.uint8(img))
        # add guide text
        s1 = u'\u4efb\u610f\u70b9\u51fb\u5f00\u59cb'
        w, h = self.getsize(s1, size=18)[0]
        w, h = (self.width-w)/2, self.height - 2*h - 2
        self.draw_text(w, h, s1, 'red', 18)
        s2 = 'click to start'
        w, h = self.getsize(s2, size=18)[0]
        w, h = (self.width-w)/2, self.height - 1*h - 1
        self.draw_text(w, h, s2, 'red', 18)
        # touch screen to continue
        if self._touch_started:
            self._flag_pause.clear()
            with self._read_lock:
                self._touch.flushInput()
                self._read_epoll.poll()
                self._touch.read_all()
            self._flag_pause.set()
        else:
            time.sleep(2)
        self.recover_frame()

    def move_element(self, element=None, id=None, x=0, y=0, *a, **k):
        e = self._get_element_from_name_and_id(element, id)
        if e is None:
            return
        if 'x' in e:
            e['x'] += x
            e['y'] += y
        if 'x1' in e:
            e['x1'] += x
            e['x2'] += x
            e['y1'] += y
            e['y2'] += y
        self.render()

    def remove_element(self, element=None, id=None, render=True, *a, **k):
        e = self._get_element_from_name_and_id(element, id)
        if e is None:
            return
        self.widget[element].remove(e)
        if render:
            self.render()

    def save_layout(self, dir_or_file, *a, **k):
        '''
        save current layout(texts, buttons, any elements) in a pickle file
        '''
        if os.path.exists(dir_or_file):
            if os.path.isdir(dir_or_file):
                name = os.path.join(dir_or_file,
                                    'layout-%s.pcl' % time_stamp())
            elif os.path.isfile(dir_or_file):
                name = dir_or_file
        else:
            dir = os.path.basename(dir_or_file),
            if not os.path.exits(dir) or not os.path.isdir(dir):
                return
            name = dir_or_file
        # prepare data
        tmp = element_dict(self.widget.copy())
        for e in tmp['button']:
            e['callback'] = None
        if self._encoding != 'utf8':
            # text string is stored as str in self.widget
            # convert it to unicode to pickle
            for e in tmp['text'] + tmp['button']:
                e['s'] = e['s'].decode('gbk')
        with open(name, 'w') as f:
            pickle.dump(tmp, f)
        print(self._name + 'saved layout `{}`'.format(name))

    def load_layout(self, dir_or_file, extend=True, render=True, *a, **k):
        '''
        Read in a layout from file
        Param `extend` determines whether to extend current layout by
        loaded layout, or to replace current layout with loaded layout
        '''
        if not os.path.exists(dir_or_file):
            print(self._name + 'invalid dir or layout file name')
            return
        layout = dir_or_file
        if os.path.isdir(dir_or_file):
            layout = find_gui_layouts(dir_or_file)
            if layout is None:
                print(self._name + 'no available layout in ' + dir_or_file)
                return
        try:
            with open(layout, 'r') as f:
                tmp = pickle.load(f)
        except Exception as e:
            print(self._name + 'load layout `' + layout + '` error: %s' % e)
            return
        if self._encoding != 'utf8':
            # text string is stored as unicode in layout file
            # convert it to correct encoding after pickle
            for e in tmp['text'] + tmp['button']:
                e['s'] = e['s'].encode(self._encoding)
        for key in self.widget:
            elements = [element_dict(e) for e in tmp[key]]
            if extend:
                self.widget[key].extend(elements)
            else:
                self.widget[key] = element_list(elements)
        if render:
            self.render()

    def freeze_frame(self, *a, **k):
        '''save current frame buffer in background'''
        self._tmp = (element_dict(self.widget.copy()), self.touch_sensibility)
        for key in self.widget:
            self.widget[key] = element_list([])
        self.clear()

    def recover_frame(self, *a, **k):
        '''recover lastest frame buffer from background'''
        if hasattr(self, '_tmp') and self._tmp:
            self.widget, self.touch_sensibility = self._tmp
            self.render()

    @staticmethod
    def _default_callback(x, y, bt):
        '''default button callback'''
        print('[Touch Screen] touch button {} - `{}` at ({}, {}) at {}'.format(
            bt['id'], bt['s'], x, y, time_stamp()))

    def _get_element_from_name_and_id(self, element=None, id=None):
        elements = [key for key in self.widget.keys() if self.widget[key]]
        if len(elements) == 0:
            print('Empty widget bucket now. Nothing to remove!')
            return
        if element not in elements:
            print('Choose one from `%s`' % '` | `'.join(map(str, elements)))
            return
        return self.widget[element, id]

    def _get_touch_point(self):
        '''
        parse touch screen data to get point index(with calibration)
        '''
        while not self._flag_close.isSet():
            with self._read_lock:
                self._touch.flushInput()
                self._read_epoll.poll()
                raw = self._touch.read_until().strip()
            if (time.time() - self._last_touch) > 1.0 / self.touch_sensibility:
                self._last_touch = time.time()
                try:
                    yxp = raw.split(',')
                    if len(yxp) == 3:
                        pt = self._cali_matrix[1] + \
                            [int(yxp[1]), int(yxp[0])] * self._cali_matrix[0]
                        # print('[Touch Screen] touch at {}, {}'.format(*pt))
                        return abs(pt)
                    else:
                        print('[Touch Screen] Invalid input %s' % raw)
                except:
                    continue
        return 0, 0

    def _handle_touch(self):
        while not self._flag_close.isSet():
            self._flag_pause.wait()
            x, y = self._get_touch_point()
            for bt in self.widget['button']:
                if x > bt['x1'] and x < bt['x2'] and \
                   y > bt['y1'] and y < bt['y2']:
                    if bt['ct'] != self._element_color['press'][0]:
                        c = self._element_color['press'][0]
                    else:
                        c = self._element_color['press'][1]
                    bt['c'] = c
                    self.send('text', **bt)
                    if bt['cr'] != 'None':
                        self.send('rect', **bt)
                    time.sleep(0.3)
                    bt['c'] = bt['ct']
                    self.send('text', **bt)
                    if bt['cr'] != 'None':
                        bt['c'] = bt['cr']
                        self.send('rect', **bt)
                    if bt['callback'] is not None:
                        thread = threading.Thread(
                            target=bt['callback'],
                            kwargs={'x': x, 'y': y, 'bt': bt})
                        thread.start()
                        self._callback_threads.append(thread)
        print('[Touch Screen] exiting...')

    def empty_widget(self, *a, **k):
        for key in self.widget:
            self.widget[key] = element_list([])
        self.clear()

    def clear(self, x1=None, y1=None, x2=None, y2=None, bg=None, *a, **k):
        if None in [x1, y1, x2, y2]:
            self.send('clear', c=(bg or self._element_color['bg']))
        else:
            self.send('rectf', c=(bg or self._element_color['bg']),
                      x1=min(x1, x2), y1=min(y1, y2),
                      x2=max(x1, x2), y2=max(y1, y2))

    def close(self, *a, **k):
        super(Serial_Screen_GUI, self).close()
        if self._touch_started:
            self._flag_close.set()
            try:
                self._touch.write('\xaa\xaa\xaa\xaa')  # send close signal
                time.sleep(0.5)
            except:
                pass
            finally:
                self._touch.close()
        time.sleep(0.5)


class SPI_Screen_GUI(SPI_Screen_commander, Serial_Screen_GUI):
    '''
    SPI_Screen_GUI` inherits `SPI_Screen_commander` and `Serial_Screen_GUI`.
    It will establish SPI connection by initing `SPI_Screen_commander`.
    We don't initialize `Serial_Screen_GUI`(i.e. no serial connection will
    be built) but instance of `SPI_Screen_commander` will has GUI control
    methods offered by `Serial_Screen_GUI`. Some of functions is device
    independent.

    Methods Outline:
        Inherit from `SPI_Screen_commander`:
            start, send, write(alias of send), close, getsize
        Inherit from `Serial_Screen_GUI`:
            draw_img, draw_buttom, draw_point, draw_line, draw_rect,
            draw_round, draw_round_rect, draw_circle, draw_text,
            render, display_img, calibration_touch_screen, clear,
            save_layout, load_layout, freeze_frame, recover_frame,
            remove_element, move_element,
        Inherit from `Serial_Screen_commander`:
            start, send, close, getsize --> all overloaded
            check_key --> useless
    '''
    def __init__(self, spi_device=(0, 1), *a, **k):
        super(SPI_Screen_GUI, self).__init__(spi_device)
        self._name = self._name[:-2] + ' @ GUI' + self._name[-2:]
        self._encoding = 'utf8'
        self.start()

        self._touch_started = False
        self._cali_matrix = np.array([[0.1911, -0.1490], [-22.0794, 255.0536]])
        self.touch_sensibility = 4

    def close(self):
        super(SPI_Screen_GUI, self).close()
        if self._touch_started:
            # `_flag_close` and `_flag_pause` are
            # defined in `start_touch_screen`
            self._flag_close.set()
            self._touch.close()
        time.sleep(1)


if __name__ == '__main__':
    #  plt.ion()
    #  fake_data = np.random.random((1, 8, 1000))
    #  print(fake_data.shape)
    #  p = Plotter(window_size = 1000, n_channel=8)
    #  p.plot(fake_data)

    filename = os.path.join(DATADIR, 'test/left-1.mat')
    actionname = os.path.basename(filename)
    data = sio.loadmat(filename)[actionname.split('-')[0]][0]
    sample_rate = 500
    sample_time = 6
    view_data_with_matplotlib(data, sample_rate, sample_time, actionname)

    #  c = Screen_commander(command_dict=command_dict_uart_screen_v1)
    #  c.start()
    #  time.sleep(1)
    #  print( 'setting screen vertical: {}'.format(c.send('dir', 1)) )
    #
    #  data = np.sin(np.linspace(0, 6*np.pi, 600))
    #  data = np.repeat(data.reshape(1, 600), 8, axis=0)
    #  try:
    #      while 1:
    #          screen_plot_one_channel(c, data, width=220, height=76)
    #          screen_plot_multichannels(c, data, range(8))
    #          print('new screen!')
    #  except KeyboardInterrupt:
    #      c.close()
