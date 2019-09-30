#!/usr/bin/env python3
# coding=utf-8
#
# File: EmBCI/embci/utils/_resolve.py
# Authors: Hank <hankso1106@gmail.com>
# Create: 2019-07-18 18:25:37

# built-in
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
import re
import os
import time
import glob
import socket
import inspect
import warnings

# requirements.txt: drivers: pyserial
# requirements.txt: data: pylsl
from serial.tools.list_ports import comports
import pylsl

from . import check_input, logger

__all__ = [
    'find_pylsl_outlets', 'find_serial_ports',
    'find_spi_devices', 'find_gui_layouts',
    'get_host_addr', 'get_free_port',
    'get_caller_globals', 'get_caller_modname',
    'get_func_args',
]


def find_pylsl_outlets(v=None, **kwargs):                          # noqa: C901
    '''
    This function is easier to use than func `pylsl.resolve_stream`.

    Examples
    --------
    >>> find_pylsl_outlets()   # same as pylsl.resolve_streams()
    >>> find_pylsl_outlets(1)  # same as pylsl.resolve_streams(timeout=1)

    >>> find_pylsl_outlets('type', 'EEG')  # Invalid
    >>> find_pylsl_outlets("type='EEG'")   # pylsl.resolve_bypred("type='EEG'")
    >>> find_pylsl_outlets(type='EEG')    # pylsl.resolve_byprop('type', 'EEG')

    If no wanted pylsl stream outlets found, ``RuntimeError`` will be raised.
    '''
    timeout = v if isinstance(v, (int, float)) else kwargs.pop('timeout', 1)
    keys = set(kwargs.keys()).intersection({
        'name', 'type', 'channel_count', 'nominal_srate',
        'channel_format', 'source_id'
    })

    if isinstance(v, str):
        infos = pylsl.resolve_bypred(v, 0, timeout)
    elif not keys:
        infos = pylsl.resolve_streams(timeout)
    else:
        infos = []
    for key in keys:
        infos += pylsl.resolve_byprop(key, kwargs[key], 0, timeout)

    streams = dict()
    for info in infos:
        if info.uid() not in streams:
            streams[info.uid()] = info
    stream_list = list(streams.values())

    if len(stream_list) == 0:
        raise RuntimeError('No stream available! Abort.')
    elif len(stream_list) == 1:
        stream = stream_list[0]
    else:
        # Display stream as: $No $Name $Type - $CHx$Format $SourceID
        prompt = (
            'Please choose one from all available streams:\n    ' +
            '\n    '.join([
                '{:2d} {:s}({:s}) CH{:d}x{:s} - `{}`@ {}'.format(
                    n, s.name(), s.type(), s.channel_count(),
                    pylsl.pylsl.fmt2type[s.channel_format()]._type_,
                    s.source_id() and '`%s` ' % s.source_id() or '',
                    s.hostname()
                ) for n, s in enumerate(stream_list)
            ]) + '\nstream num (default 0): '
        )
        answer = {str(i): stream_list[i] for i in range(len(stream_list))}
        answer[''] = stream_list[0]
        try:
            stream = check_input(prompt, answer)
            if stream == '':
                stream = answer[stream]
        except KeyboardInterrupt:
            raise RuntimeError('No stream selected! Abort.')
    logger.info('Using stream `{}`({}) `{}`@ {}'.format(
        stream.name(), stream.type(), stream.source_id(), stream.hostname()))
    return stream


def find_serial_ports(timeout=3):
    '''
    This fucntion will guide user to choose one port. Wait `timeout` seconds
    for devices to be detected. If no ports found, return None.
    '''
    # scan for all available serial ports
    NAME = '[Find Serial Ports] '
    port = None
    while timeout > 0:
        timeout -= 1
        port_list = comports()
        if len(port_list) == 0:
            time.sleep(1)
            logger.debug(
                '{}rescanning available ports... {}'.format(NAME, timeout))
            continue
        elif len(port_list) == 1:
            port = port_list[0]
        else:
            tmp = [(port.device, port.description) for port in port_list]
            prompt = (
                '{}Please choose one from all available ports:\n    ' +
                '\n    '.join(['%d %s - %s' % (i, dv, ds)
                               for i, (dv, ds) in enumerate(tmp)]) +
                '\nport num(default 0): '
            ).format(NAME)
            answer = {str(i): port for i, port in enumerate(port_list)}
            answer[''] = port_list[0]
            port = check_input(prompt, answer)
    if not port:
        raise RuntimeError(NAME + 'No serail port available! Abort.')
    logger.info('{}Select port `{}` -- {}'
                .format(NAME, port.device, port.description))
    return port.device


def find_spi_devices():
    '''If there is no spi devices, exit python'''
    NAME = '[Find SPI Devices] '
    dev_list = glob.glob('/dev/spidev*')
    if len(dev_list) == 0:
        device = None
    elif len(dev_list) == 1:
        device = dev_list[0]
    else:
        prompt = ('{}Please choose one from all available devices:\n    ' +
                  '\n    '.join(['%d %s' % (i, dev)
                                 for i, dev in enumerate(dev_list)]) +
                  '\ndevice num(default 0): ').format(NAME)
        answer = {str(i): dev for i, dev in enumerate(dev_list)}
        answer[''] = dev_list[0]
        try:
            device = check_input(prompt, answer)
        except KeyboardInterrupt:
            raise RuntimeError(NAME + 'No divice available! Abort.')
    if not device:
        raise RuntimeError(NAME + 'No divice available! Abort.')
    dev = (re.findall(r'/dev/spidev([0-9])\.([0-9])', device) or [(0, 0)])[0]
    logger.info('{}Select device `{}` -- BUS: {}, CS: {}'
                .format(NAME, device, *dev))
    return int(dev[0]), int(dev[1])


def find_gui_layouts(dir):
    '''If no layouts found, return None.'''
    NAME = '[Find GUI Layouts] '
    layout_list = glob.glob(os.path.join(dir, 'layout*.pcl'))
    layout_list.sort(reverse=True)
    if len(layout_list) == 0:
        return
    elif len(layout_list) == 1:
        layout = layout_list[0]
    else:
        prompt = ('{}Please choose one from all available layouts:\n    ' +
                  '\n    '.join(['%d %s' % (i, os.path.basename(j))
                                 for i, j in enumerate(layout_list)]) +
                  '\nlayout num(default 0): ').format(NAME)
        answer = {str(i): layout for i, layout in enumerate(layout_list)}
        answer[''] = layout_list[0]
        try:
            layout = check_input(prompt, answer)
        except KeyboardInterrupt:
            return
    logger.info('{}Select layout `{}`'.format(NAME, layout))
    return layout


def get_host_addr(default='127.0.0.1'):
    '''
    UDP socket can connect to any hosts even they are unreachable, or
    broadcast data even there are no listeners. Here create an UDP socket
    and connect to '8.8.8.8:80' google public DNS server to resolve self
    host address.
    '''
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        host, _ = s.getsockname()
    except socket.error:
        host = default
    finally:
        s.close()
    return host


def get_free_port(host=''):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind((host, 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        host, port = s.getsockname()
    except socket.error as e:
        raise e
    finally:
        s.close()
    return port


def get_caller_globals(depth=0):
    '''
    Only support `CPython` implemention. Use with cautious!

    Parameters
    ----------
    depth : int
        Extra levels outer than caller frame, default 0.

    Examples
    --------
    >>> a = 1
    >>> get_caller_globals()['a']
    1

    and if you run by commandline:
        python -c "import embci; print(embci.utils.get_caller_globals())"
    {'__builtins__': <module '__builtin__' (built-in)>, '__name__': '__main__',
    'embci': <module 'embci' from 'embci/__init__.pyc'>, '__doc__': None,
    '__package__': None}

    See Also
    --------
    sys._getframe([depth])
    '''
    # f = sys._getframe(1)
    f = inspect.currentframe()
    if f is None:
        warnings.warn(RuntimeWarning('Only CPython implements stack frame.'))
        return globals()
    for i in range(depth + 1):
        if f.f_back is None:
            warnings.warn(RuntimeWarning(
                'No outer frame of {} at depth {}!'.format(f, i)))
            return f.f_globals
        f = f.f_back
    return f.f_globals


def get_caller_modname():
    return get_caller_globals(1)['__name__']


if hasattr(inspect, 'signature'):
    def get_func_args(func, kwonlywarn=True):                       # noqa E301
        # In python3.5+ inspect.getargspec & inspect.getfullargspec are
        # deprecated. inspect.signature is suggested to use, but it needs
        # some extra steps to fetch our wanted info
        args, defaults = [], []
        for name, param in inspect.signature(func).parameters.items():
            if kwonlywarn and param.kind is param.KEYWORD_ONLY:
                warnings.warn(
                    "Keyword only arguments are not suggested in functions, "
                    "because it keeps your script from python2 and 3 "
                    "compatibility.\nKeyword only `{}` in function `{}`"
                    .format(param, func))
            if param.kind not in [param.VAR_POSITIONAL, param.VAR_KEYWORD]:
                args.append(param.name)
                if param.default is not param.empty:
                    defaults.append(param.default)
        return args, tuple(defaults)

elif hasattr(inspect, 'getfullargspec'):
    def get_func_args(func, kwonlywarn=True):                       # noqa E301
        # python3.0-3.5 use inspect.getfullargspec
        argspec = inspect.getfullargspec(func)
        if kwonlywarn and argspec.kwonlyargs:
            warnings.warn(
                "Keyword only arguments are not suggested in functions, "
                "because it keeps your script from python2 and 3 "
                "compatibility.\nKeyword only `{}` in function `{}`"
                .format(argspec.kwonlyargs, func))
        return argspec.args or [], argspec.defaults or ()

else:
    def get_func_args(func):                                        # noqa E301
        # python2.7-3.0 use inspect.getargspec
        argspec = inspect.getargspec(func)
        if inspect.ismethod(func) and argspec.args[0] in ['self', 'cls']:
            argspec.args.pop(0)
        return argspec.args or [], argspec.defaults or ()

get_func_args.__doc__ = '''
Get names and default values of a function's arguments.

Returns
-------
names : list
defaults : tuple

Examples
--------
>>> get_func_args(lambda x, y=1, verbose=None, *a, **k: None)
(['x', 'y', 'verbose'], (1, None))
>>> get_func_args(get_func_args)
(['func', 'kwonlywarn'], (True, ))
'''
