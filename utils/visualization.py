#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Thu Mar 22 08:26:16 2018

@author: hank
"""
# built-in
import time
import sys, os; sys.path += ['../src']
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
from common import mapping, time_stamp, check_input, Signal_Info
from IO import Screen_commander, command_dict_uart_screen_v1

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
        plt.psd(p.remove_DC(p.notch(d))[0], Fs=250, label='filter', linewidth=0.5)
        plt.legend()
        plt.title('optimized PSD -- used time: %.3fms' % (1000*(time.time()-t)))

class Screen_GUI(object):
    '''
    GUI of UART controlled 2.3' LCD screen
    '''
    _color_map = {'black': 0, 'red': 1, 'green': 2, 'blue': 3, 'yellow': 4,
                  'cyan': 5, 'purple': 6, 'gray': 7, 'grey': 8, 'brown': 9,
                  'orange': 13, 'pink': 14, 'white': 15}
    _e = {'point': 3, 'line': 1, 'circle': 1, 'circlef': 1,
          'rect': 6, 'rectf': 0, 'text': 15, 'press': 1}
    widget = {'point':[], 'line':[], 'circle':[], 'circlef':[],
              'rect':[], 'rectf':[], 'text':[], 'button':[], 'img':[]}
    def __init__(self, screen_port='/dev/ttyS1', screen_baud=115200,
                 command_dict=None):
        if command_dict is None:
            command_dict = command_dict_uart_screen_v1
        self._c = Screen_commander(screen_baud, command_dict)
        self._c.start(screen_port)
        self._c.send('dir', 1) # set screen vertical
        self._touch_started = False

    def start_touch_screen(self, port='/dev/ttyS2', baud=115200):
        self.touch_sensibility = 20
        self._t = serial.Serial(port, baud)
        self._flag_close = threading.Event()
        self._flag_pause = threading.Event()
        self._flag_pause.set()
        self._read_lock = threading.Lock()
        self._last_touch_time = time.time()
        self._cali_matrix = np.array([[1, 1], [0, 0]])
        self._touch_thread = threading.Thread(target=self._handle_touch_screen)
        self._touch_thread.setDaemon(True)
        self._touch_thread.start()
        self._touch_started = True
        self._callback_threads = []

    def draw_img(self, x, y, img, render=True):
        num = 0 if not len(self.widget['img']) \
                else (self.widget['img'][-1]['id'] + 1)
        img = np.array(img, np.uint8)
        self.widget['img'].append({'data': img, 'id': num, 'shape': img.shape,
            'x1': x, 'y1': y, 'x2': x + img.shape[1], 'y2': y + img.shape[0]})
        if render:
            self.render(name='img', num=num)

    def draw_button(self, x, y, s, callback=None,
                    ct=None, cr=None, ca=None, render=True):
        num = 0 if not len(self.widget['button']) \
                else (self.widget['button'][-1]['id'] + 1)
        # Although there is already `# -*- coding: utf-8 -*-` at file start
        # we'd better explicitly use utf-8 to decode every string in Py2.
        # Py3 default use utf-8 coding, which is really really nice.
        s = s.decode('utf8')
        # English use 8 pixels and Chinese use 16 pixels(GBK encoding)
        en_zh = [ord(char) > 255 for char in s]
        w = en_zh.count(False)*8 + en_zh.count(True)*16
        h = 16
        ct = self._e['text']  if ct == None else ct
        cr = self._e['rect']  if cr == None else cr
        ca = self._e['press'] if ca == None else ca
        cb = self._default_button_callback if callback == None else callback
        self.widget['button'].append({'id': num, 'ct': ct, 'cr': cr, 'ca': ca,
                'x1': max(x-2, 0), 'y1': max(y-2, 0), 'x2': x + w, 'y2': y + h,
                'x': x, 'y': y, 's': s.encode('gbk'), 'callback': cb})
        if render:
            self.render(name='button', num=num)

    def draw_point(self, x, y, c=None, render=True):
        num = 0 if not len(self.widget['point']) \
                else (self.widget['point'][-1]['id'] + 1)
        c = self._e['point'] if c == None else c
        self.widget['point'].append({'x': x, 'y': y, 'id': num, 'c': c})
        if render:
            self.render(name='point', num=num)

    def draw_line(self, x1, y1, x2, y2, c=None, render=True):
        num = 0 if not len(self.widget['line']) \
                else (self.widget['line'][-1]['id'] + 1)
        c = self._e['line'] if c == None else c
        self.widget['line'].append({'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2,
                   'id': num, 'c': c})
        if render:
            self.render(name='line', num=num)

    def draw_rectangle(self, x1, y1, x2, y2, c=None, fill=False, render=True):
        name = 'rectf' if fill else 'rect'
        num = 0 if not len(self.widget[name]) \
                else (self.widget[name][-1]['id'] + 1)
        c = self._e[name] if c == None else c
        self.widget[name].append({'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2,
                 'id': num, 'c': c})
        if render:
            self.render(name=name, num=num)

    def draw_circle(self, x, y, r, c=None, fill=False, render=True):
        name = 'circlef' if fill else 'circle'
        num = 0 if not len(self.widget[name]) \
                else (self.widget[name][-1]['id'] + 1)
        c = self._e[name] if c == None else c
        self.widget[name].append({'x': x, 'y': y, 'r': r, 'id': num, 'c': c,
                   'x1': x - r, 'y1': y - r, 'x2': x + r, 'y2': y + r})
        if render:
            self.render(name=name, num=num)

    def draw_text(self, x, y, s, c=None, render=True):
        num = 0 if not len(self.widget['text']) \
                else (self.widget['text'][-1]['id'] + 1)
        s = s.decode('utf8')
        en_zh = [ord(char) > 255 for char in s]
        w = en_zh.count(False)*8 + en_zh.count(True)*16
        h = 16
        c = self._e['text'] if c == None else c
        self.widget['text'].append({'x': x, 'y': y, 'id': num, 'c': c,
                   'x1': x, 'y1': y, 'x2': x + w, 'y2': y + h,
                   's': s.encode('gbk')})
        if render:
            self.render(name='text', num=num)

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

    def save_layout(self):
        # text string is storaged as gbk in self.widget
        # convert it to utf8 to jsonify
        tmp = self.widget.copy()
        for i in tmp['button']:
            i['callback'] = None
            i['s'] = i['s'].decode('gbk')
        for i in tmp['text']:
            i['s'] = i['s'].decode('gbk')
        for i in tmp['img']:
            i['data'] = i['data'].tobytes()
        with open('../files/layout-%s.json' % time_stamp(), 'w') as f:
            json.dump(tmp, f)

    def load_layout(self):
        while 1:
            prompt = 'choose one from ' + ' | '.join([os.path.basename(i) \
                    for i in glob.glob('../files/layout*.json')])
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
            i['s'] = i['s'].encode('gbk')
            i['callback'] = self._default_button_callback \
                            if i['callback'] == None else i['callback']
        for i in tmp['text']:
            i['s'] = i['s'].encode('gbk')
        for i in self.widget['img']:
            i['data'] = np.frombuffer(i['data'], np.uint8).reshape(i['shape'])
        self.widget.update(tmp)
        self.render()
    
    def _default_button_callback(self, x, y, bt):
        print('[Touch Screen] touch button %d - %s at %d, %d at %.3f' \
                  % (bt['id'], bt['s'], x, y, time.time()))

    def render(self, *args, **kwargs):
        '''
        clear sequence:
        +--------------+
        |33334444411111|
        |33334444411111|
        |3333+---+11111|
        |3333|img|11111|
        |3333+---+11111|
        |22222222211111|
        |22222222211111|
        +--------------+

        render params:
        name: element name, one of ['circle', 'circlef', 'img', 'point',
                                    'button', 'text', 'line', 'rectf', 'rect']
        num: element id
        '''
        try:
            if 'name' and 'num' in kwargs: # render an element
                ids = [i['id'] for i in self.widget[kwargs['name']]]
                e = self.widget[kwargs['name']][ids.index(kwargs['num'])]
                self.clear(**e)
                if kwargs['name'] == 'button':
                    self._c.send('text', x=e['x'], y=e['y'],
                                 s=e['s'], c=e['ct'])
                    self._c.send('rect', x1=e['x1'], y1=e['y1'],
                                 x2=e['x2'], y2=e['y2'], c=e['cr'])
                elif kwargs['name'] == 'img':
                    self._plot_img(e)
                else:
                    self._c.send(kwargs['name'], **e)
            else: # render all
                if len(self.widget['img']):
                    img = self.widget['img'][0]
                    self.clear(img['x2'], 0, 219, 175) # clear 1
                    self.clear(0, img['y2'], max(img['x2']-1, 0), 175) # clear 2
                    self.clear(0, 0, max(img['x1']-1, 0), max(img['y2']-1, 0)) # clear 3
                    self.clear(img['x1'], 0, max(img['x2']-1, 0), max(img['y1']-1, 0)) # clear 4
                else:
                    self.clear(*args, **kwargs) # clear all
                for element_name in self.widget.keys():
                    if element_name == 'button':
                        for bt in self.widget[element_name]:
                            self._c.send('text', x=bt['x'], y=bt['y'],
                                         s=bt['s'], c=bt['ct'])
                            self._c.send('rect', x1=bt['x1'], y1=bt['y1'],
                                         x2=bt['x2'], y2=bt['y2'], c=bt['cr'])
                    elif element_name == 'img':
                        for img in self.widget['img']:
                            self._plot_img(img)
                    else:
                        for element in self.widget[element_name]:
                            self._c.send(element_name, **element)
        except Exception as e:
            print(e)

    def _plot_img(self, img):
        '''
        render img by plotting each point
        (I know this is super slow but let us use it now)
        #TODO 10: speed up img display
        '''
        for x in range(img['x2'] - img['x1']):
            for y in range(img['y2'] - img['y1']):
                if img['data'][y, x]:
                    self._c.send('point', x=img['x1'] + x, y=img['y1'] + y,
                                 c=img['data'][y, x])

    def calibration_touch_screen(self):
        if not self._touch_started:
            print('[Screen GUI] touch screen not initialized yet!')
            return
        self._flag_pause.clear() # pause _handle_touch_screen thread
        tmp = (self.widget.copy(), self.touch_sensibility)
        for element in self.widget:
            self.widget[element] = []
        self.touch_sensibility = 1
        self._cali_matrix = np.array([[1, 1], [0, 0]])
        self.clear()
        self.draw_text(78, 80, '屏幕校准', c=self._color_map['green'])
        self.draw_text(79, 80, '屏幕校准', c=self._color_map['green'])
        # points where to be touched
        pts = np.array([[10, 10], [210, 10], [10, 165], [210, 165]])
        # points where user touched
        ptt = np.zeros((4, 2))
        try:
            for i in range(4):
                self.draw_circle(pts[i][0], pts[i][1], 4, render=True,
                                 c=self._color_map['blue'])
                ptt[i] = self._get_touch_point()
                self.draw_circle(pts[i][0], pts[i][1], 2, render=True,
                                 c=self._color_map['blue'], fill=True)
            print(ptt, pts)
            self._cali_matrix = np.array([
                    np.polyfit(ptt[:, 0], pts[:, 0], 1),
                    np.polyfit(ptt[:, 1], pts[:, 1], 1)]).T
        except Exception as e:
            print(e)
        finally:
            self.widget, self.touch_sensibility = tmp
            self.render()
            self._flag_pause.set() # resume _handle_touch_screen thread

    def _get_touch_point(self):
        '''
        parse touch screen data to get point index(with calibration)
        '''
        while 1:
            self._read_lock.acquire()
            raw = self._t.read_until().strip()
            x_y_p = raw.split(',')
            self._read_lock.release()
            print(raw)
            if len(x_y_p) == 3:
                try:
                    pt = np.array([ int(x_y_p[0]), int(x_y_p[1]) ])
                    if (time.time() - self._last_touch_time) > \
                    1.0/self.touch_sensibility:
                        self._last_touch_time = time.time()
                        return pt * self._cali_matrix[0] + self._cali_matrix[1]
                except:
                    continue
            else:
                print('[Touch Screen] Invalid input %s' % raw)

    def _handle_touch_screen(self):
        while not self._flag_close.isSet():
            self._flag_pause.wait()
            x, y = self._get_touch_point()
            for bt in self.widget['button']:
                if x > bt['x1'] and x < bt['x2'] \
                and y > bt['y1'] and y < bt['y2']:
                    print(x, y, bt['id'])
                    self._c.send('rect', x1=bt['x1'], y1=bt['y1'],
                                 x2=bt['x2'], y2=bt['y2'], c=bt['ca'])
                    time.sleep(0.3)
                    self._c.send('rect', x1=bt['x1'], y1=bt['y1'],
                                 x2=bt['x2'], y2=bt['y2'], c=bt['cr'])
                    time.sleep(0.2)
                    if bt['callback'] is None:
                        self._default_button_callback(x, y, bt)
                    else:
                        self._callback_threads.append(threading.Thread(
                                target=bt['callback'], args=(x, y, bt, )))
                        self._callback_threads[-1].start()
        print('[Touch Screen] exiting...')

    def display_logo(self, filename):
        tmp = self.widget.copy()
        for element in self.widget:
            self.widget[element] = []
        self.clear()
        img = np.array(Image.open(filename).resize((219, 85)))
        self.draw_img(0, 45, 15*(img[:,:,3] != 0))
        self.draw_text(62, 143, '任意点击开始')
        self.draw_text(54, 159, 'click to start')
        if self._touch_started:
            self._flag_pause.clear()
            self._t.flushInput()
            self._t.read_until()
            self._flag_pause.set()
        else:
            time.sleep(1)
        self.widget = tmp
        self.render()

    def clear(self, x1=None, y1=None, x2=None, y2=None, *args, **kwargs):
        if None in [x1, y1, x2, y2]:
            self._c.send('clear')
        else:
            self._c.send('rectf', x1=x1, y1=y1, x2=x2, y2=y2,
                         c=self._color_map['black'])

    def close(self):
        self._c.close()
        if self._touch_started:
            self._flag_close.set()
            self._t.write('\xaa\xaa\xaa\xaa') # send close signal
            time.sleep(1)
            self._t.close()

    def update_element_color(self, element, color):
        if element not in self._e:
            print('no candidates for this element `{}`'.format(element))
            print('choose one from ' + ' | '.join(self.list_elements()))
            return
        if color not in self._color_map:
            print('Invalid color name `{}`'.format(color))
            print('choose one from ' + ' | '.join(self.list_colors()))
            return
        self._e[element] = self._color_map[color]

    def list_colors(self):
        return self._color_map.keys()

    def list_elements(self):
        return self._e.keys()

if __name__ == '__main__':
#    plt.ion()
#    fake_data = np.random.random((1, 8, 1000))
#    print(fake_data.shape)
#    p = Plotter(window_size = 1000, n_channel=8)
#    p.plot(fake_data)
# =============================================================================
#
# =============================================================================
#    filename = '../data/test/grab-2.mat'
#    actionname = os.path.basename(filename)
#    data = sio.loadmat(filename)[actionname.split('-')[0]][0]
#    sample_rate=500; sample_time=6
#    view_data_with_matplotlib(data, sample_rate, sample_time, actionname)
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
