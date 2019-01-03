#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Tue Feb 27 16:03:02 2018

@author: hank
"""
# built-in
from __future__ import print_function, unicode_literals
import time
import re
import os
import sys
import glob
import fcntl
import select
import socket
import tempfile
import threading
import traceback
import configparser
from builtins import input
from functools import reduce

# requirements.txt: drivers: pyserial, wifi
# requirements.txt: data-processing: pylsl, numpy, scipy
import pylsl
from serial.tools.list_ports import comports
import numpy as np
import wifi

from embci import DATADIR
#  from embci import _load_config as load_config

__dir__ = os.path.dirname(os.path.abspath(__file__))
__file__ = os.path.basename(__file__)

BOOLEANS = {
    u'0': False, u'1': True,
    u'No': False, u'Yes': True,
    u'Off': False, u'On': True,
    u'False': False, u'True': True,
    u'None': None,
}


class abyi_dict(dict):
    '''
    Get attributes like JavaScript way, i.e. by keys

    Examples
    --------
    >>> d = {'name': 'bob', 'age': 20, 'gender': 'male'}
    >>> d.keys  # calling d.__getattributes___('keys')
    ['name', 'age', 'gender']

    __getattributes__ is called everytime you want to get an attribute of
    the instance, but when attribute doesn't actually exist, __getattributes__
    failed and then __getattr__ is called. If __getattr__ is not defined,
    python will raise AttributeError. Here we define __getattr__ = dict.get
    >>> d.name  # call d.__getattr__('name'), i.e. d.get('name', None)
    'bob'
    >>> d.age, d.weight
    (20, None)
    '''
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__
    __str__ = dict.__str__
    __repr__ = dict.__repr__


class ibya_list(list):
    '''
    Get items in list by attributes of them

    Examples
    --------
    >>> l = [{'name': 'bob'}, {'name': 'alice'}, {'name': 'tim'}]
    >>> l.name
    ['bob', 'alice', 'tim']
    '''
    def __getattr__(self, attr):
        try:
            return list.__getattr__(self, attr)
        except AttributeError:
            return [getattr(e, attr) for e in self]


def mapping(a, low=None, high=None, t_low=0, t_high=255):
    '''
    Mapping data to new array values all in duartion [low, high]

    Return
    ------
    np.array

    Example
    -------
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


def mkuserdir(func):
    '''
    check if user folder exist before saving data etc.
    '''
    def wrapper(*a, **k):
        if a and isinstance(a[0], (bytes, str)):
            username = ensure_unicode(a[0])
        elif 'username' in k:
            username = k.get('username')
        else:
            print('Decorator may be used in wrong place.')
            print('args: {}, kwargs: {}'.format(a, k))
            return func(*a, **k)
        path = os.path.join(DATADIR, username)
        if not os.path.exists(path):
            try:
                os.makedirs(path)
            except:
                pass
        return func(*a, **k)
    return wrapper


def check_input(prompt, answer={'y': True, 'n': False, '': True}, times=3):
    '''
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
    print('Welcome!\nIt seems this is the first time you use this Bio-Signal '
          'recognizing program.\nYou need to record some action data first.\n'
          'Then next time you do that action again it will be recognized.\n'
          'Now start recording.', end='')
    return check_input('Check all electrodes and ensure they are '
                       'stable in right position, are they? ')


def find_pylsl_outlets(name=None, **kwargs):
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
                  '\n    '.join(['%d %s - %s' % (i, j, k)
                                 for i, (j, k) in enumerate(zip(dv, ds))]) +
                  '\nstream num(default 0): ')
        answer = {str(i): stream for i, stream in enumerate(stream_list)}
        answer[''] = stream_list[0]
        try:
            stream = check_input(prompt, answer)
        except KeyboardInterrupt:
            sys.exit('No stream available! Abort.')
    if stream:
        print(('Select stream `{name}` -- {chs} channel {type_num} {fmt} data '
               'from {source} on server {host}').format(
                   name=stream.name(),
                   chs=stream.channel_count(),
                   type_num=stream.type(),
                   fmt=stream.channel_format(),
                   source=stream.source_id(),
                   host=stream.hostname()))
        return stream
    sys.exit('No stream available! Abort.')


def find_serial_ports(timeout=3):
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
            tmp = [(port.device, port.description) for port in port_list]
            prompt = ('Please choose one from all available ports:\n    ' +
                      '\n    '.join(['%d %s - %s' % (i, dv, ds)
                                     for i, (dv, ds) in enumerate(tmp)]) +
                      '\nport num(default 0): ')
            answer = {str(i): port for i, port in enumerate(port_list)}
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
                  '\n    '.join(['%d %s' % (i, dev)
                                 for i, dev in enumerate(dev_list)]) +
                  '\ndevice num(default 0): ')
        answer = {str(i): dev for i, dev in enumerate(dev_list)}
        answer[''] = dev_list[0]
        try:
            device = check_input(prompt, answer)
        except KeyboardInterrupt:
            sys.exit('No divice available! Abort.')
    if device:
        print('Select device `{}`'.format(device))
        return device
    sys.exit('No divice available! Abort.')


def find_gui_layouts(dir):
    '''If no layouts found, return None.'''
    layout_list = glob.glob(os.path.join(dir, 'layout*.pcl'))
    layout_list.sort(reverse=True)
    if len(layout_list) == 0:
        return
    elif len(layout_list) == 1:
        layout = layout_list[0]
    else:
        prompt = ('Please choose one from all available layouts:\n    ' +
                  '\n    '.join(['%d %s' % (i, os.path.basename(j))
                                 for i, j in enumerate(layout_list)]) +
                  '\nlayout num(default 0): ')
        answer = {str(i): layout for i, layout in enumerate(layout_list)}
        answer[''] = layout_list[0]
        try:
            layout = check_input(prompt, answer)
        except KeyboardInterrupt:
            return
    print('Select layout `{}`'.format(layout))
    return layout


def find_wifi_hotspots(interface=None):
    '''
    scan wifi hotspots with specific interface and return results as list of
    JS dict, if interface doesn't exists or scan failed(permission denied),
    return empty list [].
    '''
    if interface is not None:
        interfaces = [interface]
    else:
        try:
            with open('/proc/net/wireless', 'r') as f:
                rsts = [re.findall('wl\w+', line)
                        for line in f.readlines() if '|' not in line]
        except:
            traceback.print_exc()
            with open('/proc/net/dev', 'r') as f:
                rsts = [re.findall('wl\w+', line)
                        for line in f.readlines() if '|' not in line]
        interfaces = [rst[0] for rst in rsts if rst]
    cells = ibya_list()
    for interface in interfaces:
        try:
            cells.extend([
                c for c in wifi.Cell.all(interface)
                if c.address not in cells.address
            ])
        except wifi.exceptions.InterfaceError:
            pass
        except:
            traceback.print_exc()
    unique = reduce(lambda l, c: l if c.ssid in l.ssid else (l.append(c) or l),
                    cells, ibya_list([]))
    unique.sort(key=lambda cell: cell.signal, reverse=True)
    # `ibya_list([abyi_dict(c) for c in cells.__dict__])` will not work
    # because cells.__dict__ is cells's __dict__ but not cells' __dict__
    return ibya_list([abyi_dict(vars(c)) for c in unique])


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
            #         info = '\rPort1 RX %dB  TX %dB  Lost from Port2 %dB' \
            #             % (count[0], count[1], count[3]-count[0])
            #     else:
            #         info = '\rPort1 RX %.2fkB TX %.2fkB Lost from Port2 %dB'\
            #             % (count[0]/1024, count[1]/1024, count[3]-count[0])
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

        def func_collector(func):
            def param_collector(*args, **kwargs):
                if (time.time() - Timer.last_time_dict[name]) < time_in_sec:
                    print(warning, end='')
                    return None
                else:
                    Timer.last_time_dict[name] = time.time()
                    return func(*args, **kwargs)
            return param_collector
        return func_collector


def get_self_ip_addr():
    '''
    Create a UDP socket which can broadcast data packages even there is no
    listeners. So this socket can actually connect to any hosts you offer
    even they are unreachable. Here connect to '8.8.8.8' google public DNS
    server addr.
    '''
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 8))
        host, port = s.getsockname()
    except:
        host = socket.gethostbyname(socket.gethostname())
    finally:
        s.shutdown(socket.SHUT_RDWR)
        s.close()
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


@mkuserdir
def get_label_list(username):
    '''
    This function is used to count all saved data.
    Return label_list, e.g.:
    {
         'left': 16,
         'right': 21,
         'thumb_cross': 10,
         ...
    }
    '''
    userpath = os.path.join(DATADIR, username)
    paths = [i[:-4] for i in os.listdir(userpath)]
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


def get_boolean(v, table=BOOLEANS):
    '''convert string to boolean'''
    t = str(v).title()
    if t not in table:
        raise ValueError('Invalid boolean value: {}'.format(v))
    return table[t]


class Boolean_str(str):
    '''
    Create a boolean string. `bool(s)` will not always return `True` if length
    of `s` is not zero. `bool()` will really convert string to boolean.

    Example
        >>> bool(Boolean_str('True'))
        True
        >>> bool(Boolean_str('False'))
        False
        >>> bool(Boolean_str('Yes'))
        True

    Boolean table can be replaced.
    '''
    def __nonzero__(self, table=BOOLEANS):
        return get_boolean(self, table)

    __bool__ = __nonzero__


def ensure_unicode(*a):
    rst = []
    for i in a:
        if isinstance(i, bytes):
            i = i.decode('utf8')
        rst.append(u'{}'.format(i))
    return rst


class LockedFile(object):
    '''
    Context manager for creating temp & auto-recycled & locked files

    Here's something to be decleared on locking a file:
    1. fcntl.lockf() most of the time implemented as a wrapper around the
       fcntl() locking calls, which bound to processes, not file descriptors.
    2. fcntl.flock() locks are bound to file descriptors, not processes.
    3. On at least some systems, fcntl.LOCK_EX can only be used if the file
       descriptor refers to a file opened for writing.
    4. fcntl locks will be released after file is closed or by fcntl.LOCK_UN.
    '''
    def __init__(self, filename=None, *a, **k):
        self.file_obj = None
        self.path = os.path.abspath(filename or tempfile.mkstemp()[1])
        if k.get('pidfile'):
            self._pidfile = True

    def acquire(self):
        d = os.path.dirname(self.path)
        if not os.path.exists(d):
            os.makedirs(d)
        #  self.file_obj = os.fdopen(
        #      os.open(self.path, os.O_CREAT | os.O_RDWR))
        self.file_obj = open(self.path, 'a+')  # 'a' will not truncate file
        try:
            fcntl.flock(self.file_obj, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except IOError:
            raise RuntimeError('file `%s` has been used!' % self.path)
        self.file_obj.truncate(0)
        if hasattr(self, '_pidfile'):
            self.file_obj.write(str(os.getpid()))
            self.file_obj.flush()
        return self.file_obj

    def release(self):
        try:
            self.file_obj.close()
        except:
            pass
        os.remove(self.path)

    def __enter__(self):
        return self.acquire()

    def __exit__(self, exc_type=None, exc_value=None, exc_tb=None):
        self.release()


def load_config(file='/etc/embci.conf'):
    file = str(file)
    if not os.path.exists(file):
        raise IOError("No such file: '%s'" % file)
    config = configparser.ConfigParser()
    config.optionxform = str
    if config.read(file) != [file]:
        raise IOError("Cannot open file: '%s'" % file)
    return config


# TODO: include them into a tester
#  if __name__ == '__main__':
#      print(vars(get_config()))
#      username = 'test'
#      first_use()
#      print('time stamp: ' + time_stamp())
#      print(get_label_list(username)[1])
