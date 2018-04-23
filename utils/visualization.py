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

# pip install matplotlib, numpy, scipy, pyserial, PIL
#import matplotlib
#import matplotlib.pyplot as plt
import numpy as np
import scipy.io as sio
import serial
from PIL import Image

# from ../src
from preprocessing import Processer
from common import mapping
from signal_info import Signal_Info
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
        plt.title('normal PSD -- used time: %.3fms' % (1000*(time.time()-t)))
        
        plt.subplot(326)
        t = time.time()
        
        plt.title('optimized PSD -- used time: %.3fms' % (1000*(time.time()-t)))


class Screen_GUI(object):
    '''
    GUI of UART controlled 2.3' LCD screen
    '''
    _color_map = {'black': 0, 'red': 1, 'green': 2, 'blue': 3, 'yellow': 4,
                  'cyan': 5, 'purple': 6, 'gray': 7, 'grey': 8, 'brown': 9,
                  'orange': 13, 'pink': 14, 'white': 15}
    widget = {'point':[], 'line':[], 'circle':[], 'circlef':[],
              'rect':[], 'rectf':[], 'text':[], 'button':[], 'img':[]}
    def __init__(self, reader,
                 touch_screen_port='/dev/ttyS2',
                 screen_port='/dev/ttyS1'):
        self.r = reader
        # commander init
        self._c = Screen_commander(baudrate=115200,
                                   command_dict=command_dict_uart_screen_v1)
        self._c.start(screen_port)
        self._c.send('dir', 1) # set screen vertical
        
        self._e = {'point': 3, 'line': 1, 'circle': 1, 'circlef': 1,
                   'rect': 6, 'rectf': 0, 'text': 15, 'press': 1}
        # touch screen listener init
        self._t = serial.Serial(touch_screen_port, 115200)
        self._flag_close = threading.Event()
        self._touch_thread = threading.Thread(target=self._handle_touch_screen)
        self._touch_thread.setDaemon(True)
        # these codes only used to display `Cheitech co.` LOGO.
        self._display_logo()
        self.load_layout()
        self.render()
        self._touch_thread.start()
    
    def draw_img(self, x, y, img):
        num = 0 if not len(self.widget['img']) \
                else (self.widget['img'][-1]['id'] + 1)
        img = np.array(img, np.uint8)
        self.widget['img'].append({'x1': x, 'y1': y, 'x2': x + img.shape[1],
                   'y2': y + img.shape[0], 'data': img, 'id': num,
                   'shape': img.shape})
        
    def draw_button(self, x, y, s, callback=None, ct=None, cr=None, ca=None):
        num = 0 if not len(self.widget['button']) \
                else (self.widget['button'][-1]['id'] + 1)
        text = map(lambda c: ord(c) > 255, unicode(s))
        # English use 8 pixels and Chinese use 16 pixels(GBK encoding)
        w = text.count(False)*8 + text.count(True)*16
        h = 16
        ct = self._e['text'] if ct == None else ct
        cr = self._e['rect'] if cr == None else cr
        ca = self._e['press'] if ca == None else ca
        callback = (lambda x, y : (x, y)) if callback == None else callback
        self.widget['button'].append({
                'x1': max(x-2, 0), 'y1': max(y-2, 0), 'x2': x + w, 'y2': y + h,
                'x': x, 'y': y, 's': s.encode('gbk'), 'callback': callback,
                'id': num, 'ct': ct, 'cr': cr, 'ca': ca})
    
    def draw_point(self, x, y, c=None):
        num = 0 if not len(self.widget['point']) \
                else (self.widget['point'][-1]['id'] + 1)
        c = self._e['point'] if c == None else c
        self.widget['point'].append({'x': x, 'y': y, 'id': num, 'c': c})
        
    def draw_line(self, x1, y1, x2, y2, c=None):
        num = 0 if not len(self.widget['line']) \
                else (self.widget['line'][-1]['id'] + 1)
        c = self._e['line'] if c == None else c
        self.widget['line'].append({'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2,
                   'id': num, 'c': c})
        
    def draw_rectangle(self, x1, y1, x2, y2, c=None, fill=False):
        name = 'rectf' if fill else 'rect'
        num = 0 if not len(self.widget[name]) \
                else (self.widget[name][-1]['id'] + 1)
        c = self._e[name] if c == None else c
        self.widget[name].append({'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2,
                 'id': num, 'c': c})
            
    def draw_circle(self, x, y, r, c=None, fill=False):
        name = 'circlef' if fill else 'circle'
        num = 0 if not len(self.widget[name]) \
                else (self.widget[name][-1]['id'] + 1)
        c = self._e[name] if c == None else c
        self.widget[name].append({'x': x, 'y': y, 'r': r, 'id': num, 'c': c})
        
    def draw_text(self, x, y, s, c=None):
        num = 0 if not len(self.widget['text']) \
                else (self.widget['text'][-1]['id'] + 1)
        c = self._e['text'] if c == None else c
        self.widget['text'].append({'x': x, 'y': y,
                   's': unicode(s).encode('gbk'), 'id': num, 'c': c})
            
    def remove_element(self, name=None, num=None):
        if name not in self.widget:
            print('no candidates for this widget `{}`'.format(name))
            print('choose one from ' + ' | '.join(self.widget.keys()))
            return
        ids = map(lambda x: x['id'], self.widget[name])
        try:
            self.widget[name].pop(ids.index(num))
            self.render()
        except ValueError:
            print('no candidates for this {}:`{}`'.format(name, num))
            print('choose one from ' + ' | '.join([str(i) for i in ids]))
    
    def move_element(self, name, num, x, y):
        ids = map(lambda x: x['id'], self.widget[name])
        e = self.widget[name][ids.index(num)]
        try:
            e['x'] += x; e['y'] += y
        except KeyError:
            e['x1'] += x; e['x2'] += x; e['y1'] += y; e['y2'] += y
        finally:
            self.render()
    
    def save_layout(self):
        for i in self.widget['button']:
            i['callback'] = None
            i['s'] = i['s'].decode('gbk')
        for i in self.widget['text']:
            i['s'] = i['s'].decode('gbk')
        for i in self.widget['img']:
            i['data'] = i['data'].tobytes()
        with open('../files/layout.json', 'w') as f:
            json.dump(self.widget, f)
        
    def load_layout(self):
        with open('../files/layout.json', 'r') as f:
            tmp = json.load(f)
        for i in tmp['button']:
            i['s'] = i['s'].encode('gbk')
            i['callback'] = (lambda x, y : (x, y)) \
                            if i['callback'] == None else i['callback']
        for i in tmp['text']:
            i['s'] = i['s'].encode('gbk')
        for i in self.widget['img']:
            i['data'] = np.frombuffer(i['data'], np.uint8).reshape(i['shape'])
        self.widget.update(tmp)
        
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
        '''
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
                    for x in range(img['x2'] - img['x1']):
                        for y in range(img['y2'] - img['y1']):
                            if img['data'][y, x]:
                                self._c.send('point',
                                             x=img['x1'] + x, y=img['y1'] + y,
                                             c=img['data'][y, x])
            else:
                for element in self.widget[element_name]:
                    self._c.send(element_name, **element)
        
    def _handle_touch_screen(self):
        while not self._flag_close.isSet():
            index = self._t.read_until().strip().split(',')
            if index:
                x, y = int(index[0]), int(index[1])
                print('[Touch Screen] touch point at %d, %d at %.3f' \
                      % (x, y, time.time()))
                for bt in self.widget['button']:
                    if x > bt['x1'] and x < bt['x2'] \
                    and y > bt['y1'] and y < bt['y2']:
                        self._c.send('rect', x1=bt['x1'], y1=bt['y1'],
                                     x2=bt['x2'], y2=bt['y2'], c=bt['ca'])
                        time.sleep(0.3)
                        self._c.send('rect', x1=bt['x1'], y1=bt['y1'],
                                     x2=bt['x2'], y2=bt['y2'], c=bt['cr'])
                        time.sleep(0.2)
                        bt['callback'](x, y)
        print('[Touch Screen] exiting...')
    
    def _display_logo(self):
        img = np.array(Image.open('../files/LOGO.bmp').resize((219, 85)))
        self.draw_img(0, 45, 15*(img[:,:,3] != 0))
        self.draw_text(62, 148, '任意点击开始')
        self.clear()
        self.render()
        self._t.flushInput()
        self._t.read_until()
        self.remove_element('img', 0)
        self.remove_element('text', 0)
        
    def clear(self, x1=None, y1=None, x2=None, y2=None):
        if None in [x1, y1, x2, y2]:
            self._c.send('clear')
        else:
            self._c.send('rectf', x1=x1, y1=y1, x2=x2, y2=y2, c=0)
            
    def close(self):
        self._c.close()
        self._flag_close.set()
        self._t.write('\xff\xff\xff\xff') # send close signal
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
    
    def plot_waveform(self, x, y, n_channel=1, scale=100):
        n_channel = min(n_channel, self.r.n_channel)
        self.color = np.arange(1, 1 + n_channel)
        self.scale = np.repeat(scale, n_channel)
        self.area = [0, 40, 220, 144]
        # store old widget
        self.tmp = self.widget.copy()
        for element in self.widget:
            self.widget[element] = []
        # start and stop flag
        flag_close = threading.Event()
        # plot page widgets
        self.draw_text(32, 20, '波形显示', c=2) # 0
        self.draw_button(156, 20, '返回',
                         callback=lambda x, y: flag_close.set())
        self.draw_text(4, 145, '4-6Hz最大峰值') # 1
        self.draw_text(156, 145, '@') # 2
        self.draw_text(108, 145, '      ', c=1) # 3
        self.draw_text(164, 145, '      ', c=1) # 4
        self.render()
        data = np.zeros((self.area[2], n_channel))
        ch_height = (self.area[3] - self.area[1] - 1)/n_channel
        bias = [self.area[1] + ch_height/2 + ch_height*ch \
                for ch in range(n_channel)]
        si = Signal_Info()
        x = 0
        last_time = time.time()
        while not flag_close.isSet():
            if (time.time() - last_time) > 1:
                last_time = time.time()
                amp, fre = self.widget['text'][3:5]
                self._c.send('text', x=amp['x'], y=amp['y'], s=amp['s'], c=0)
                self._c.send('text', x=fre['x'], y=fre['y'], s=fre['s'], c=0)
                f, a = si.peek_extract(self.r.get_data(),
                                       4, 6, self.r.sample_rate)[0, 0]
                amp['s'] = '%3.3f' % a
                fre['s'] = '%1.2fHz' % f
                print(amp['s'], fre['s'])
                self._c.send('text', x=amp['x'], y=amp['y'], s=amp['s'], c=amp['c'])
                self._c.send('text', x=fre['x'], y=fre['y'], s=fre['s'], c=fre['c'])
                
            # first delete last point
            for i in range(n_channel):
                self._c.send('point', x=x, y=data[x][i], c=0)
            # update channel data list
            data[x] = (self.r.ch_data[:n_channel]*self.scale).astype(np.int) + bias
            # then draw current point
            for i in range(n_channel):
                self._c.send('point', x=x, y=data[x][i], c=self.color[i])
            # update x axis index
            x = x + 1 if (x + 1) < self.area[2] else 0
        # recover old widget
        self.widget = self.tmp.copy()
        del self.tmp, self.color, self.scale, self.area
        self.render()


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