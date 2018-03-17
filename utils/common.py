#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Tue Feb 27 16:03:02 2018

@author: hank
"""
from __future__ import print_function
from serial.tools.list_ports import comports
import time
import os
import sys
import pylsl
import matplotlib
import matplotlib.pyplot as plt


def check_input(prompt, answer={'y': True, 'n': False, '': True}, times=3):
    '''
    输出prompt，提示用户输入选择，并判断输入是否有效，比如运行一个命令之前

    This function is to let user input answer.

    Example
    -------
        >>> check_input('This will call pip and try install pycnbi. [Y/n] ',
                        {'y': True, 'n': False})
        This will call pip and try install pycnbi. [Y/n] 123
        Invalid argument! Choose from [y|n]

        This will call pip and try install pycnbi. [Y/n] y
        (return True)
    '''
    k = answer.keys()
    while times:
        times -= 1
        rst = raw_input(prompt)
        if not k:
            if rst:
                return rst
            else:
                if raw_input('you entered nothing, confirm? [Y/n]') == 'y':
                    return None
                else:
                    continue
        if rst in k:
            return answer[rst]
        print('Invalid argument!', end='')
        if k:
            print('Choose from [ "%s" ]' % '" | "'.join(k))
    return None


def time_stamp(localtime=None, fm='%Y%m%d-%H:%M:%S'):
    if localtime is None:
        localtime = time.localtime()
    return time.strftime(fm, localtime)


def first_use():
    '''
    初次使用时的用户引导输出
    '''
    print('Welcome! It seems this is the first time you'
          ' use this EMG recognizing system. We need to'
          'collect some data from you. It may take a while...\n'
          'You can record any number of actions you want. '
          'And next time you do that again we will recognize it.'
          '\nNow start recording.', end='')
    return check_input('Check all electrodes and ensure they '
                       'are stable in right position, are they? ')


def find_outlets(name, **kwargs):
    '''
    寻找已经存在的pylsl注册的stream
    '''
    if name is None:
        stream_list = pylsl.resolve_stream()
    else:
        stream_list = pylsl.resolve_byprop('name', name, minimum=0, timeout=5)
    while not len(stream_list):
        if not len(kwargs):
            sys.exit('No stream available! Abort.')
        prop, value = kwargs.popitem()
        stream_list += pylsl.resolve_byprop(prop, value, minimum=0, timeout=5)
    if len(stream_list) == 1:
        stream = stream_list[0]
    else:
        dv = map(lambda x: x.name, stream_list)
        ds = map(lambda x: x.type, stream_list)
        prompt = ('Please choose one from all available streams:\n    ' +
                  '\n    '.join(['%d %s - %s' % (i, j, k) \
                                 for i, j, k in enumerate(zip(dv, ds))]) +
                  '\nstream name: ')
        stream = check_input(prompt, answer={i: stream_list[i] \
                                             for i in range(len(stream_list))})
    if stream:
        print(('Select stream {name} -- {chs} channel {type_num} {fmt} data '
               'from {source} on server {host}').format(
                       name = stream.name(),
                       chs = stream.channel_count(),
                       type_num = stream.type(),
                       fmt = stream.channel_format(),
                       source = stream.source_id(),
                       host = stream.hostname()))
        return stream
    sys.exit('No stream available! Abort.')
    

def find_ports(timeout=5):
    '''
    利用check_input和serial.tools.list_ports.comports寻找当前电脑上的串口
    如果有多个可用的串口，提示用户选择一个

    This fucntion will guide user to choose one port
    '''
    # scan for all available serial ports
    while timeout > 0:
        timeout -= 1
        if len(comports()) == 0:
            time.sleep(1)
            continue
        port_list = comports()
        if len(port_list) == 1:
            port = port_list[0].device
        else:
            dv = map(lambda x: x.device, port_list)
            ds = map(lambda x: x.description, port_list)
            prompt = ('Please choose one from all available ports:\n    ' +
                      '\n    '.join([i+' - '+j for i, j in zip(dv, ds)]) +
                      '\nport name: ')
            port = check_input(prompt, answer={i: i for i in dv})
        if port:
            print('Select port {} -- {}'.format(port_list[0].device,
                                                port_list[0].description))
            return port
        else:
            break
    sys.exit('No port available! Abort.')


def _combine_action(d1, d2):
    ''' only used in get_label_list '''
    if type(d1) is not dict:
        d1 = d1.split('-')[:2]
        d2 = d2.split('-')[:2]
        return {d1[0]: 2} if d1[0] == d2[0] else \
               {d1[0]: 1, d2[0]: 1}
    if type(d1) is dict:
        d2 = d2.split('-')[:2]
        if d2[0] in d1:
            d1[d2[0]] += 1
        else:
            d1[d2[0]] = 1
    return d1


def get_label_list(username):
    '''
    扫描./data/username文件夹下的数据，列出存储的数据和数量

    This function is used to count all saved data.
    Return label_list, e.g.:
    {
         'left': 16,
         'right': 21,
         'thumb_cross': 10,
         ...
    }
    '''
    if not os.path.exists('./data/' + username):
        os.mkdir('./data/' + username)
    paths = [i[:-4] for i in os.listdir('./data/' + username)]
    if len(paths) == 0:
        label_list = {}
    elif len(paths) == 1:
        label_list = {paths[0].split('-')[0]: 1}
    else:
        label_list = reduce(_combine_action, paths)

    # 去掉logging数据
    for label in label_list.keys():
        if label.startswith('logging'):
            label_list.pop(label)

    a, n = len(label_list), sum(label_list.values())
    summary = (
        'There are %d actions with %d data recorded.\n    ' % (a, n) +
        '\n    '.join([k + '\t\t%d' % v for k, v in label_list.iteritems()])
    )
    return label_list, summary


class Plotter():
    def __init__(self, where_to_plot=None, n_channel=1):
        '''
        Plot multichannel streaming data on a figure ,
        or in a window if it is offered.
        Param:
            where_to_plot can be a matplotlib figure or a list of axes.
            default None, to create a new figure and split it into n_channels
            window, one for each window
        '''
        if where_to_plot == None:
            self.figure = plt.figure()
            for i in xrange(n_channel):
                self.figure.add_axes((0, i*(1.0/n_channel),
                                      1, 1.0/n_channel),
                                     facecolor='black')
            self.axes = self.figure.axes
            
        elif type(where_to_plot) == matplotlib.figure.Figure:
            if not len(where_to_plot.axes):
                for i in xrange(n_channel):
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
        # clear all axes
        for a in self.axes:
            a.cla()
    
    def plot(self, data):
        '''
        only update line data to save time
        '''
        shape = data.shape()
        if len(shape) == 3:
            # n_sample x n_channel x window_size
            for i, ch in enumerate(data[0]):
                if len(self.axes[i].lines):
                    self.axes[i].lines[0].set_ydata(ch)
                else:
                    self.axes[i].plot(ch)
        elif len(shape) == 4:
            # n_sample x n_channel x freq x time
            for i, img in enumerate(data[0]):
                if len(self.axes[i].images):
                    self.axes[i].images[0].set_data(img)
                else:
                    self.axes[i].imshow(ch)
        return data


if __name__ == '__main__':
# =============================================================================
#     os.chdir('../')
#     username = 'test'
# =============================================================================
# =============================================================================
#     first_use()
# =============================================================================
# =============================================================================
#     print(time_stamp())
# =============================================================================
# =============================================================================
#     print(find_ports())
# =============================================================================
# =============================================================================
#     print(find_outlets('testing'))
# =============================================================================
# =============================================================================
#     print(get_label_list(username)[1])
# =============================================================================
    pass
