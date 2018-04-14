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
import socket
import threading

# pip install pyserial, pylsl, numpy
import pylsl
from serial.tools.list_ports import comports
import numpy as np

# In python3 reduce need to be imported while python2 not
if sys.version_info.major == 3:
    from functools import reduce

# from ./
from signal_info import Signal_Info
signal_info = Signal_Info()

def energy_time_duration(reader, low, high, duration):
    '''
    一段时间内某频段的能量总和
    calculate energy density of time duration
    '''
    def _run(flag):
        start_time = time.time()
        reader.info = np.array([0.0] * reader.n_channel)
        while not flag.isSet():
            time.sleep(duration)
            reader.info += np.array(signal_info.energy(reader.channel_data(),
                                                       low, high,
                                                       reader.sample_rate))
        dt = time.time() - start_time
#        reader.info /= dt
    stop_flag = threading.Event()
    threading.Thread(target=_run, args=(stop_flag, )).start()
    return stop_flag

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
    # In python2 raw_input return str and input retrun eval(str)
    if sys.version_info.major == 2:
        input = raw_input
    k = list(answer.keys())
    while times:
        times -= 1
        rst = input(prompt)
        
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
        print('Invalid %s! Choose from [ "%s" ]' % (rst, '" | "'.join(k)))
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



class Timer(object):
    '''
    Want to looply execute some function every specific time duration?
    You may use this class.
    
    There is only one method(static) in this class:
        
        duration(name, time_in_sec, warning='.')
        
    name is a str id of the function, you can name it whatever you want but
    just make it distinguishable, and the second param is time duration in
    second.
    
    Example
    =======
    >>> @Timer.duration('testing', 3, warning='cant call me so frequently!')
    ... def testing(foo):
    ...     print(foo)
    
    >>> while 1:
    ...     time.sleep(1)
    ...     testing('now you are executing testing function')
    now you are executing testing function
    cant call me so frequently!
    cant call me so frequently!
    now you are executing testing function
    cant call me so frequently!
    cant call me so frequently!
    ...
    '''
    last_time_dict = {}
    @staticmethod
    def duration(name, time_in_sec, warning=''):
        if name not in Timer.last_time_dict:
            Timer.last_time_dict[name] = time.time()
        def decorator(func):
            def wrapper(*args, **kwargs):
                if (time.time() - Timer.last_time_dict[name]) < time_in_sec:
                    print(warning, end='')
                    return None
                else:
                    Timer.last_time_dict[name] = time.time()
                    return func(*args, **kwargs)
            return wrapper
        return decorator


def get_self_ip_addr(self):
    '''
    Create a UDP socket which can broadcast data packages even there is no
    listeners. So this socket can actually connect to any hosts you offer 
    even they are unreachable. Here use '8.8.8.8' google public DNS addr.
    '''
    try:
        tmp_s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        tmp_s.connect(('8.8.8.8', 1))
        host, port = tmp_s.getsockname()
    except:
        host = '127.0.0.1'
    finally:
        tmp_s.close()
        return host
        

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
    t = 0.0
    while t < 10*times:
        print('\r[%s>%s] %.2f%%' % ('='*int(t),
                                  ' '*int(10*times-t-1),
                                  10.0*t/times), end='')
        t += 0.1*times
        time.sleep(times/100.0)
    print('\r[{}] finished'.format('='*10*times))
        


# TODO 11: interesting function copied from package `mne`, modify it for our usage
# =============================================================================
# def sys_info(fid=None, show_paths=False):
#     """Print the system information for debugging.
# 
#     This function is useful for printing system information
#     to help triage bugs.
# 
#     Parameters
#     ----------
#     fid : file-like | None
#         The file to write to. Will be passed to :func:`print()`.
#         Can be None to use :data:`sys.stdout`.
#     show_paths : bool
#         If True, print paths for each module.
# 
#     Examples
#     --------
#     Running this function with no arguments prints an output that is
#     useful when submitting bug reports::
# 
# import mne
# mne.sys_info() # doctest: +SKIP
#         Platform:      Linux-4.2.0-27-generic-x86_64-with-Ubuntu-15.10-wily
#         Python:        2.7.10 (default, Oct 14 2015, 16:09:02)  [GCC 5.2.1 20151010]
#         Executable:    /usr/bin/python
# 
#         mne:           0.12.dev0
#         numpy:         1.12.0.dev0+ec5bd81 {lapack=mkl_rt, blas=mkl_rt}
#         scipy:         0.18.0.dev0+3deede3
#         matplotlib:    1.5.1+1107.g1fa2697
# 
#         sklearn:       0.18.dev0
#         nibabel:       2.1.0dev
#         mayavi:        4.3.1
#         pycuda:        2015.1.3
#         skcuda:        0.5.2
#         pandas:        0.17.1+25.g547750a
# 
#     """  # noqa: E501
#     ljust = 15
#     out = 'Platform:'.ljust(ljust) + platform.platform() + '\n'
#     out += 'Python:'.ljust(ljust) + str(sys.version).replace('\n', ' ') + '\n'
#     out += 'Executable:'.ljust(ljust) + sys.executable + '\n\n'
#     old_stdout = sys.stdout
#     capture = StringIO()
#     try:
#         sys.stdout = capture
#         np.show_config()
#     finally:
#         sys.stdout = old_stdout
#     lines = capture.getvalue().split('\n')
#     libs = []
#     for li, line in enumerate(lines):
#         for key in ('lapack', 'blas'):
#             if line.startswith('%s_opt_info' % key):
#                 libs += ['%s=' % key +
#                          lines[li + 1].split('[')[1].split("'")[1]]
#     libs = ', '.join(libs)
#     version_texts = dict(pycuda='VERSION_TEXT')
#     for mod_name in ('mne', 'numpy', 'scipy', 'matplotlib', '',
#                      'sklearn', 'nibabel', 'mayavi', 'pycuda', 'skcuda',
#                      'pandas'):
#         if mod_name == '':
#             out += '\n'
#             continue
#         out += ('%s:' % mod_name).ljust(ljust)
#         try:
#             mod = __import__(mod_name)
#         except Exception:
#             out += 'Not found\n'
#         else:
#             version = getattr(mod, version_texts.get(mod_name, '__version__'))
#             extra = (' (%s)' % op.dirname(mod.__file__)) if show_paths else ''
#             if mod_name == 'numpy':
#                 extra = ' {%s}%s' % (libs, extra)
#             out += '%s%s\n' % (version, extra)
#     print(out, end='', file=fid)
# =============================================================================



if __name__ == '__main__':
    os.chdir('../')
    username = 'test'
    first_use()
    record_animate(5)
    print('time stamp: ' + time_stamp())
# =============================================================================
#     print(find_ports())
#     print(find_outlets('testing'))
# =============================================================================
    print(get_label_list(username)[1])
    pass
