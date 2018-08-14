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
import glob
import select
import socket
import threading

# pip install pyserial, pylsl, numpy, scipy
import pylsl
from serial.tools.list_ports import comports
import numpy as np


__dir__ = os.path.dirname(os.path.abspath(__file__))
__filename__ = os.path.basename(__file__)



# In python3 reduce need to be imported while python2 not
if sys.version_info.major == 3:
    from functools import reduce


def mapping(a, low=None, high=None, t_low=0, t_high=255):
    '''
    Mapping data to new array values all in duartion [low, high]

    Return
    ======
    np.array

    Example
    =======
    >>> a = [0, 1, 2.5, 4.9, 5]
    >>> b = mapping(a, 0, 5, 0, 1024)
    >>> a
    [0, 1, 2.5, 4.9, 5]
    >>> b
    array([   0.  ,  204.8 ,  512.  , 1003.52, 1024.  ], dtype=float32)
    '''
    a = np.array(a, np.float32)
    if low is None:
        low = a.min()
    if high is None:
        high = a.max()
    if low == high:
        return t_low
    return (a - low) / (high - low) * (t_high - t_low) + t_low


def check_dir(func):
    '''
    check if user folder exist before saving data etc.
    '''
    def wrapper(*a, **k):
        if a and isinstance(a[0], str) and not os.path.exists('./data/' + a[0]):
            os.mkdir('./data/' + a[0])
            os.mkdir('./model/' + a[0])
        else:
            print('This wrapper may be used in wrong place.')
        return func(*a, **k)
    return wrapper


def check_input(prompt, answer={'y': True, 'n': False, '': True}, times=3):
    '''
    输出prompt，提示用户输入选择，并判断输入是否有效，比如运行一个命令之前

    This function is to guide user make choices.

    Example
    -------
        >>> check_input('This will call pip and try install pycnbi. [Y/n] ',
                        {'y': True, 'n': False})
        [1/3] This will call pip and try install pycnbi. [Y/n] 123
        Invalid argument! Choose from [ y | n ]
        [2/3] This will call pip and try install pycnbi. [Y/n] y
        # return True
    '''
    # In python2 raw_input return `str` and input retrun `eval(str)`
    if sys.version_info.major == 2:
        input = raw_input
    k = list(answer.keys())
    t = 0
    while t < times:
        t += 1
        rst = input('[%d/%d] ' % (t, times) + prompt)
        # answer == {}, maybe user want raw_input str returned
        if not k:
            if not rst:
                if input('nothing input, confirm? [Y/n] ').lower() == 'n':
                    t -= 1
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


def find_outlets(name=None, **kwargs):
    '''If no wanted pylsl stream outlets found, exit python'''
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
                                 for i, (j, k) in enumerate(zip(dv, ds))]) +
                  '\nstream num(default 0): ')
        answer = {str(i):stream for i, stream in enumerate(stream_list)}
        answer[''] = stream_list[0]
        try:
            stream = check_input(prompt, answer)
        except KeyboardInterrupt:
            sys.exit('No stream available! Abort.')
    if stream:
        print(('Select stream `{name}` -- {chs} channel {type_num} {fmt} data '
               'from {source} on server {host}').format(
                    name = stream.name(),
                    chs = stream.channel_count(),
                    type_num = stream.type(),
                    fmt = stream.channel_format(),
                    source = stream.source_id(),
                    host = stream.hostname()))
        return stream
    sys.exit('No stream available! Abort.')


def find_ports(timeout=3):
    '''
    This fucntion will guide user to choose one port. Wait `timeout` seconds
    for devices to be detected. If no ports found, return None
    '''
    # scan for all available serial ports
    while timeout > 0:
        timeout -= 1
        if len(comports()) == 0:
            time.sleep(1)
            print('[Find port] rescanning available ports')
            continue
        port_list = comports()
        if len(port_list) == 1:
            port = port_list[0]
        else:
            dv = [port.device for port in port_list]
            ds = [port.description for port in port_list]
            prompt = ('Please choose one from all available ports:\n    ' +
                      '\n    '.join(['%d %s - %s' % (i, j, k) \
                                     for i, (j, k) in enumerate(zip(dv, ds))]) +
                      '\nport num(default 0): ')
            answer = {str(i):port for i, port in enumerate(port_list)}
            answer[''] = port_list[0]
            port = check_input(prompt, answer)
        if port:
            print('Select port `{}` -- {}'.format(port.device,
                                                port.description))
            return port.device
        else:
            break


def find_spi_devices():
    '''If there is no spi devices, exit python'''
    dev_list = glob.glob('/dev/spidev*')
    if len(dev_list) == 0:
        device = None
    elif len(dev_list) == 1:
        device = dev_list[0]
    else:
        prompt = ('Please choose one from all available devices:\n    ' +
                  '\n    '.join(['%d %s' % (i, dev) \
                                 for i, dev in enumerate(dev_list)]) +
                  '\ndevice num(default 0): ')
        answer = {str(i):dev for i, dev in enumerate(dev_list)}
        answer[''] = dev_list[0]
        try:
            device = check_input(prompt, answer)
        except KeyboardInterrupt:
            sys.exit('No divice available! Abort.')
    if device:
        print('Select device `{}`'.format(device))
        return device
    sys.exit('No divice available! Abort.')


def find_layouts(dir):
    '''If no layouts found, return None.'''
    layout_list = glob.glob(os.path.join(dir, 'layout*.pcl'))
    layout_list.sort(reverse=True)
    if len(layout_list) == 0:
        return
    elif len(layout_list) == 1:
        layout = layout_list[0]
    else:
        prompt = ('Please choose one from all available layouts:\n    ' +
                  '\n    '.join(['%d %s' % (i, os.path.basename(j)) \
                                 for i, j in enumerate(layout_list)]) +
                  '\nlayout num(default 0): ')
        answer = {str(i):layout for i, layout in enumerate(layout_list)}
        answer[''] = layout_list[0]
        try:
            layout = check_input(prompt, answer)
        except KeyboardInterrupt:
            return
    print('Select layout `{}`'.format(layout))
    return layout


def virtual_serial():
    '''
    Generate a pair of virtual serial port at /dev/pts/*.
    Super useful when debugging without a real UART device.
    e.g.:
        /dev/pts/0 <--> /dev/pts/1
        s = serial.Serial('/dev/pts/1',115200)
        m = serial.Serial('/dev/pts/0',115200)
        s.write('hello?\\n')
        m.read_until() ==> 'hello?\\n'
    '''
    master1, slave1 = os.openpty()
    master2, slave2 = os.openpty()
    port1, port2 = os.ttyname(slave1), os.ttyname(slave2)

    #       RX1 TX1 RX2 TX2
    count = [0., 0., 0., 0.]

    print('Pty opened!\nPort1: %s\nPort2: %s' % (port1, port2))
    def echo(flag_close):
        while not flag_close.isSet():
            readable = select.select([master1, master2], [], [], 1)
            # if readable:
            #     if c.max() < 1024:
            #         info = '\rPort1 RX %dB  TX %dB  Lost from Port2 %dB' % \
            #             (count[0], count[1], count[3]-count[0])
            #     else:
            #         info = '\rPort1 RX %.2fkB TX %.2fkB Lost from Port2 %dB' % \
            #             (count[0]/1024, count[1]/1024, count[3]-count[0])
            #     sys.stdout.write(info); sys.stdout.flush()
            for master in readable[0]:
                msg = os.read(master, 1024)
                if master == master1:
                    print('[{} --> {}] {}'.format(port1, port2, msg))
                    count[1] += len(msg)
                    count[2] += os.write(master2, msg)
                elif master == master2:
                    print('[{} --> {}] {}'.format(port2, port1, msg))
                    count[3] += len(msg)
                    count[0] += os.write(master1, msg)
        print('[Virtual Serial] shutdown...')
    flag_close = threading.Event()
    t = threading.Thread(target=echo, args=(flag_close,))
    t.setDaemon(True)
    t.start()
    return flag_close


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


def get_self_ip_addr():
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
    '''use python lib `progressbar`'''
    # TODO
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
    # print(find_ports())
    # print(find_outlets('testing'))
    print(get_label_list(username)[1])
    pass
