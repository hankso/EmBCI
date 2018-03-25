#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Tue Feb 27 16:03:02 2018

@author: hank
"""
# built-in
from __future__ import print_function
import time
import os
import sys

# pip install pyserial, pylsl
import pylsl
from serial.tools.list_ports import comports


# In python2 raw_input return str and input retrun eval(str)
if sys.version_info.major == 2:
    input = raw_input
# In python3 reduce need to be imported while python2 not
else:
    from functools import reduce
    

def check_dir(func):
    '''
    check if user folder exist before saving data etc.
    '''

    def wrapper(*args, **kwargs):
        if not args:
            print('This wrapper may be used in wrong place.')
        elif not isinstance(args[0], str):
            print('This wrapper may be used in wrong place.')
        elif not os.path.exists('./data/' + args[0]): # args[0] is username
            os.mkdir('./data/' + args[0])
            os.mkdir('./models/' + args[0])
        return func(*args, **kwargs)
    return wrapper


def check_input(prompt, answer={'y': True, 'n': False, '': True}, times=3):
    '''
    输出prompt，提示用户输入选择，并判断输入是否有效，比如运行一个命令之前

    This function is to guide user make choices.

    Example
    -------
        >>> check_input('This will call pip and try install pycnbi. [Y/n] ',
                        {'y': True, 'n': False})
        This will call pip and try install pycnbi. [Y/n] 123
        Invalid argument! Choose from [y|n]

        This will call pip and try install pycnbi. [Y/n] y
        (return True)
    '''
    k = list(answer.keys())
    while times:
        times -= 1
        rst = input(prompt).lower()
        
        # answer == {}, maybe user want raw_input str returned
        if not k:
            if not rst:
                if input('nothing input, confirm? [Y/n] ').lower() == 'n':
                    times += 1
                    continue
            return rst
        
        # answer != {}, check keys
        if rst in k:
            return answer[rst]
        print('Invalid argument! Choose from [ "%s" ]' % '" | "'.join(k))
    return ''


def time_stamp(localtime=None, fm='%Y%m%d-%H:%M:%S'):
    return time.strftime(fm, localtime if localtime else time.localtime())


def first_use():
    '''
    初次使用时的用户引导输出
    '''
    print('Welcome!\nIt seems this is the first time you use this Bio-Signal '
          'recognizing program.\nYou need to record some action data first.\n'
          'Then next time you do that action again it will be recognized.\n'
          'Now start recording.', end='')
    return check_input('Check all electrodes and ensure they are '
                       'stable in right position, are they? ')


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
        dv = [stream.name() for stream in stream_list]
        ds = [stream.type() for stream in stream_list]
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
            port = port_list[0]
        else:
            dv = [port.device for port in port_list]
            ds = [port.description for port in port_list]
            prompt = ('Please choose one from all available ports:\n    ' +
                      '\n    '.join([i+' - '+j for i, j in zip(dv, ds)]) +
                      '\nport name: ')
            port = check_input(prompt, answer={i: i for i in dv})
            port = port_list[dv.index(port)]
        if port:
            print('Select port {} -- {}'.format(port.device,
                                                port.description))
            return port.device
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


@check_dir
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
    paths = [i[:-4] for i in os.listdir('./data/' + username)]
    if len(paths) == 0:
        label_list = {}
    elif len(paths) == 1:
        label_list = {paths[0].split('-')[0]: 1}
    else:
        label_list = reduce(_combine_action, paths)

    a, n = len(label_list), sum(label_list.values())
    summary = (
        '\nThere are %d actions with %d data recorded.\n    ' % (a, n) +
        '\n    '.join([k + '\t\t%d' % label_list[k] for k in label_list])
    )
    return label_list, summary


def record_animate(times):
    while times > 0:
        times -= 1
        time.sleep(1)
        print('=', end='')
    # TODO: not implemented


if __name__ == '__main__':
    os.chdir('../')
    username = 'test'
    first_use()
    record_animate(5)
    print('time stamp: ' + time_stamp())
    print(find_ports())
    print(find_outlets('testing'))
    print(get_label_list(username)[1])
    pass
