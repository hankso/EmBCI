#!/usr/bin/env python3
# coding=utf-8
#
# File: EmBCI/embci/utils/__init__.py
# Authors: Hank <hankso1106@gmail.com>
# Create: 2018-02-27 16:03:02

# built-in
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
import os
import sys
import copy
import math
import time
import fcntl
import select
import random
import string
import logging
import platform
import tempfile
import threading
import traceback
from collections import MutableMapping, MutableSequence

# requirements.txt: data: numpy
# requirements.txt: necessary: decorator, six
# requirements.txt: optional: argparse
import numpy as np
from decorator import decorator
from six import string_types, PY2
from six.moves import StringIO, configparser
try:
    # Built-in argparse is provided >= 2.7 but argparse
    # is maintained as a separate package now
    import argparse
    import packaging.version as ver
    if ver.parse(argparse.__version__) < ver.parse("1.4.0"):
        raise ImportError
except ImportError:
    del argparse
    from . import argparse                                         # noqa: W611
    try:
        del ver
    except NameError:
        pass

from .. import constants, configs

__doc__ = 'Some utility functions and classes.'
__basedir__ = os.path.dirname(os.path.abspath(__file__))


# =============================================================================
# Constants

# save 0, 1, 2 files so that TempStream will not replace these variables.
stdout, stderr, stdin = sys.stdout, sys.stderr, sys.stdin

# example for mannualy create a logger
logger = logging.getLogger(__name__)
hdlr = logging.StreamHandler(stdout)
if PY2:
    hdlr.setFormatter(logging.Formatter(configs.LOGFORMAT2))
else:
    hdlr.setFormatter(logging.Formatter(configs.LOGFORMAT, style='{'))
logger.handlers = [hdlr]
logger.setLevel(logging.INFO)
del hdlr
# you can use embci.utils._logging.config_logger instead, which is better

if sys.version_info > (3, 0):
    allstr = (bytes, str,)                                         # noqa: E602
else:
    allstr = (basestring,)                                         # noqa: E602

from ..testing import PytestRunner
test = PytestRunner(__name__)
del PytestRunner


# =============================================================================
# Utilities

def debug_helper(v, name=None):
    name = name or get_caller_globals(1)['__name__']
    logging.getLogger(name).setLevel('DEBUG' if get_boolean(v) else 'INFO')


def debug(v=True):
    debug_helper(v)


def null_func(*a, **k):
    return


def mapping(a, low=None, high=None, t_low=0, t_high=255):
    '''
    Mapping data to new array values all in duartion [low, high]

    Returns
    -------
    out : ndarray

    Examples
    --------
    >>> a = [0, 1, 2.5, 4.9, 5]
    >>> mapping(a, 0, 5, 0, 1024)
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


class NameSpace(object):
    def __init__(self, **kwargs):
        for attr, value in kwargs.items():
            setattr(self, attr, value)

    def __eq__(self, other):
        if not isinstance(other, NameSpace):
            raise NotImplementedError
        return vars(self) == vars(other)

    def __ne__(self, other):
        if not isinstance(other, NameSpace):
            raise NotImplementedError
        return not (self == other)

    def __contains__(self, key):
        return key in self.__dict__


class AttributeDict(MutableMapping):
    '''
    Get items like JavaScript way, i.e. by attributes.

    Notes
    -----
    When getting an attribute of the object, method `__getattribute__` will
    be called:
             d.xxx
        <==> getattr(d, xxx)
        <==> d.__getattribute__('xxx') + d.__getattr__('xxx')
    >>> d = dict(name='bob')
    >>> d.clear  # d.__getattribute__('clear')
    <function clear>

    If the object doesn't have that attribute, `__getattribute__` will fail
    and then `__getattr__` will be called. If `__getattr__` fails too, python
    will raise `AttributeError`.
    >>> d = {'name': 'bob', 'age': 20}
    >>> d.name
    AttributeError: 'dict' object has no attribute 'name'

    Getting an item from a dict can be achieved by calling __getitem__:
        d.get(key) <==> return d[key] or default
        d[key] <==> d.__getitem__(key)
    >>> d['age']
    KeyError: 'age'
    >>> d.__getitem__('age')
    KeyError: 'age'
    >>> d.get('age', 100)
    100

    Default `dict.__getattr__` is not defined. Here we link it to `dict.get`.
    After modification, attributes like `pop`, `keys` can be accessed by
    `__getattribute__` and items can be accessed by `__getattr__`
    and `__getitem__`.

    Examples
    --------
    >>> d = AttributeDict({'name': 'bob', 'age': 20})
    >>> d.keys  # call d.__getattribute__('keys')
    <function keys>
    >>> d.name  # call d.__getattr__('name'), i.e. d.get('name', None)
    'bob'
    >>> d['age']  # call d.__getitem__('age')
    20

    An element tree can be easily constructed by cascading `AttributeDict`
    and `list` or `AttributeList`.

    >>> bob = AttributeDict({'name': 'bob', 'age': 20, 'id': 1})
    >>> tim = AttributeDict({'name': 'tim', 'age': 30, 'id': 2})
    >>> l = AttributeList([tim, bob])
    >>> alice = AttributeDict(name='alice', age=40, id=3, friends=l)
    >>> alice.friends.name == ['bob', 'tim']
    True
    >>> alice['friends', 2] == tim
    True
    >>> tim.friends = AttributeList([bob, alice])
    >>> alice['friends', 2, 'friends', 3] == alice
    True
    '''

    def __init__(self, *a, **k):
        # do not directly use self.__dict__
        recursive = k.pop('__recursive__', True)
        self.__mapping__ = dict(*a, **k)
        if recursive:
            for key, value in self.__mapping__.items():
                if isinstance(value, dict):
                    self.__mapping__[key] = AttributeDict(value)
                if isinstance(value, list):
                    self.__mapping__[key] = AttributeList(value)

    def __getitem__(self, items):
        if isinstance(items, tuple):
            for item in items:
                if self is None:
                    logger.error('Invalid key {}'.format(item))
                    break
                self = self.__getitem__(item)
            return self
        # items: None | str | int
        if items is None or items not in self.__mapping__:
            if isinstance(items, string_types):
                if items == 'id':
                    return None
                elif items[0] == items[-1] == '_':
                    # get rid of some ipython magics
                    return None
            if self.__mapping__:
                logger.warning('Choose key from {}'.format(list(self.keys())))
            else:
                logger.warning('Invalid key {}'.format(items))
            return
        return self.__mapping__.__getitem__(items)

    def __setitem__(self, key, value):
        self.__mapping__.__setitem__(key, value)

    def __delitem__(self, key):
        self.__mapping__.__delitem__(key)

    __getattr__ = __getitem__

    def __setattr__(self, attr, value):
        if attr[0] == attr[-1] == '_':
            super(AttributeDict, self).__setattr__(attr, value)
        else:
            self.__mapping__.__setitem__(attr, value)

    def __delattr__(self, attr):
        if attr[0] == attr[-1] == '_':
            super(AttributeDict, self).__delattr__(attr)
        else:
            self.__mapping__.__delitem__(attr)

    def __contains__(self, key):
        return (key in self.__mapping__)

    def __nonzero__(self):
        return bool(self.__mapping__)

    def __hash__(self):
        return id(self)

    def __eq__(self, other):
        if not isinstance(other, (dict, MutableMapping)):
            return False
        return dict(self.items()) == dict(other.items())

    def __str__(self):
        return self.__mapping__.__str__()

    def __repr__(self):
        return '<%s %s at 0x%x>' % (typename(self), self, id(self))

    def __iter__(self):
        return self.__mapping__.__iter__()

    def __len__(self):
        return len(self.__mapping__)

    def __copy__(x):
        return x.__class__(x.__mapping__)

    def __deepcopy__(self, memo, cls=None):
        if '__cls__' not in memo:
            memo['__cls__'] = cls or self.__class__
        dct = {}
        for key in self:
            # key may be tuple|int|string...(all hashable objects)
            key = copy.deepcopy(key, memo)
            try:
                # value may be unhashable objects without a __deepcopy__ method
                dct[key] = copy.deepcopy(self[key], memo)
            except Exception:
                logger.debug(traceback.format_exc())
                dct[key] = self[key]
        return memo['__cls__'](dct)

    def copy(self, cls=None):
        '''
        A copy of self. Class of returned instance can be specified by the
        optional second argument `cls`, default current class.

        Examples
        --------
        >>> type(AttributeDict(a=1, b=2))
        embci.utils.AttributeDict
        >>> type(AttributeDict(a=1, b=2).copy())
        embci.utils.AttributeDict
        >>> type(AttributeDict(a=1, b=2).copy(dict))
        dict
        >>> def generate_list(a, b):
                print('elements: ', a, b)
                return [a, b]
        >>> type(AttributeDict(a=1, b=2).copy(generate_list))
        elements: 1, 2
        [1, 2]
        '''
        return (cls or self.__class__)(**self.__mapping__)

    def deepcopy(self, cls=None):
        return self.__deepcopy__({}, cls or self.__class__)

    def get(self, key, default=None):
        'D.get(k[,d]) -> D[k] if k in D, else d.  d defaults to None.'
        try:
            return self.__mapping__[key]
        except KeyError:
            return default

    def pop(self, key, default=None):
        try:
            value = self.__mapping__.pop(key)
        except KeyError:
            return default
        else:
            return value


class AttributeList(MutableSequence):
    '''
    Get elements in list by attributes of them. It works much like a jQuery
    init list. In this list, elements with an `id` attribute can be selected
    by normal __getitem__ way.

    Examples
    --------
    >>> l = AttributeList([
        {'name': 'bob', 'age': 16},
        {'name': 'alice', 'age': 20},
        {'name': 'tim', 'age': 22}
    ])
    >>> l.name
    ['bob', 'alice', 'tim']
    >>> l.age
    [16, 20, 22]

    >>> l2 = AttributeList([
        {'id': 999, 'name': 'dot'},
        {'id': 1, 'name': 'line'}
        {'id': 2, 'name': 'rect'}
    ])
    >>> l2[999]
    {'id': 999, 'name': 'dot'}
    >>> l2[0]  # if `id` selector failed, normal list indexing is used
    {'id': 999, 'name': 'dot'}

    >>> l2[-2] == l2[1]  # minus number is regarded as index
    True
    '''

    def __init__(self, *a, **k):
        recursive = k.pop('__recursive__', True)
        self.__sequence__ = list(*a, **k)
        if recursive:
            for n, element in enumerate(self.__sequence__):
                if isinstance(element, list):
                    self.__sequence__[n] = AttributeList(element)
                if isinstance(element, dict):
                    self.__sequence__[n] = AttributeDict(element)

    def __new__(cls, *a, **k):
        return super(AttributeList, cls).__new__(cls)

    def __getitem__(self, items):
        if isinstance(items, tuple):
            for item in items:
                if self is None:
                    logger.error('Invalid index {}'.format(item))
                    break
                self = self.__getitem__(item)
            return self
        # items: None | -int | +int | slice
        if isinstance(items, int):
            if items >= 0:
                if items in self.id:  # this will call self.__getattr__('id')
                    items = self.id.index(items)
                elif items > len(self):
                    return None
            return self.__sequence__.__getitem__(items)
        elif isinstance(items, slice):
            return self.__class__(self.__sequence__.__getitem__(items))
        elif items is None:
            if self:
                logger.warning('Choose index from {}'.format(self.id))
            else:
                logger.warning('Invalid index {}'.format(items))
        else:  # unsupported type, like string | dict | tuple ...
            pass
        return None

    def __setitem__(self, index, value):
        self.__sequence__.__setitem__(index. value)

    def __delitem__(self, index):
        self.__sequence__.__delitem__(index)

    def __getattr__(self, attr):
        try:
            return self.__sequence__.__getattr__(attr)
        except AttributeError:
            return [getattr(e, attr, None) for e in self.__sequence__]

    def __contains__(self, element):
        if hasattr(element, 'id') and element.id in self.id:
            return True
        return element in self.__sequence__

    def __nonzero__(self):
        return bool(self.__sequence__)

    def __len__(self):
        return self.__sequence__.__len__()

    def insert(self, index, value):
        self.__sequence__.insert(index, value)

    def __str__(self):
        return self.__sequence__.__str__()

    def __repr__(self):
        return '<%s %s at 0x%x>' % (typename(self), self, id(self))

    def __iter__(self):
        return self.__sequence__.__iter__()

    def index(self, element):
        if element not in self:
            return -1
        if hasattr(element, 'id') and element.id in self.id:
            return self.id.index(element.id)
        return self.__sequence__.index(element)

    def pop(self, index=-1, default=None):
        if index in self.id:
            index = self.id.index(index)
        if index == -1:
            return default
        return self.__sequence__.pop(index)

    def remove(self, element):
        self.pop(self.index(element))

    def __copy__(x):
        return x.__class__(x.__sequence__)

    def __deepcopy__(self, memo, cls=None):
        if '__cls__' not in memo:
            memo['__cls__'] = cls or self.__class__
        lst = []
        for element in self:
            try:
                lst.append(copy.deepcopy(element, memo))
            except Exception:
                logger.debug(traceback.format_exc())
                lst.append(element)
        return memo['__cls__'](lst)

    def copy(self, cls=None):
        '''
        Instance method to make a shallow or deep copy of self.

        See Also
        --------
        AttributeDict.copy
        '''
        return (cls or self.__class__)(self.__sequence__)

    def deepcopy(self, cls=None):
        return self.__deepcopy__({}, cls or self.__class__)


class BoolString(str):
    '''
    Create a real boolean string. Boolean table can be replaced.

    Notes
    -----
    `bool(s)` will always return `True` if length of `s` is non-zero.
    This class is derived from `str` and make its instances real boolean.

    Examples
    --------
    >>> bool(BoolString('True'))
    True
    >>> bool(BoolString('False'))
    False
    >>> bool(BoolString('Yes'))
    True
    >>> bool(BoolString('Nop', table={'Nop': False}))
    False
    '''
    def __nonzero__(self, table=constants.BOOLEAN_TABLE):
        return get_boolean(self, table)

    __bool__ = __nonzero__


def timestamp(ctime=None, fmt='%Y-%m-%dT%H:%M:%SZ'):
    '''Default ISO time string format'''
    return time.strftime(fmt, time.localtime(ctime))


def ensure_unicode(*a):
    '''
    ensure_unicode(s0, s1, ..., sn) ==> (u0, u1, ..., un)

    In python version prior to 3.0:
          object
            |
            |
        basestring
           /   \\
          /     \\
        str[1] unicode
    str: 8-bits 0-255 char string
    unicode: represent any char in any alphabet heading with u''

    In python3:
          object
           /  \\
          /    \\
        bytes  str
    bytes: 8-bits 0-255 char string heading with b''
    str: unicode string

    Reference: 1. `bytes` is an alias of str in python2(bytes <==> str)
    '''
    a = list(a)
    for n, i in enumerate(a):
        if not isinstance(i, allstr):
            i = str(i)
        if isinstance(i, bytes):     # py2 str or py3 bytes
            a[n] = i.decode('utf8')  # py2 unicode or py3 str
            # a[n] = u'{}'.format(a[n])
    return a[0] if len(a) == 1 else a


def ensure_bytes(*a):
    a = list(a)
    for n, i in enumerate(a):
        if not isinstance(i, allstr):
            i = str(i)
        if not isinstance(i, bytes):  # py2 unicode or py3 str
            a[n] = i.encode('utf8')   # py2 str or py3 bytes
            # a[n] = b'{}'.format(a[n])
    return a[0] if len(a) == 1 else a


def format_size(*a, **k):
    '''
    Turn number of bytes into human-readable str. Bytes are abbrivated in
    upper case, while bits use lower case. Only keyword arguments are accepted
    because any positional arguments will be regarded as a size in bytes.

    Parameters
    ----------
    units : array of str
        Default 'Bytes', 'KB', 'MB', 'GB', 'TB', 'PB'.
    decimals : array of int
        Default 0, 1, 2, 2, 2, 2. Estimated result: 10 Bytes, 1.0 KB, 1.12 MB,
        1.23 GB, 1.34 TB, 1.45 PB.
    base : int
        Default 1024, can be set to 1000.
    inbits : bool
        Whether convert output to bits.

    Examples
    --------
    >>> format_size(2**10 - 1)
    u'1023 B'
    >>> format_size(2**10)
    u'1.0 KB'
    >>> format_size(1024 * 1024, base=1000, decimals=10)
    u'1.048576 MB'
    >>> format_size(2**30, inbits=True)
    u'8.00 Gb'
    '''
    base = k.pop('base', 1024)
    inbits = k.pop('inbits', False)
    units = k.pop('units', [
        'b', 'Kb', 'Mb', 'Gb', 'Tb', 'Pb'
    ] if inbits else [
        'B', 'KB', 'MB', 'GB', 'TB', 'PB'
    ])
    decimals = k.pop('decimals', [
        0,   3,    4,    4,    4,    7
    ] if inbits else [
        0,   1,    2,    2,    2,    4
    ])
    if not isinstance(decimals, (tuple, list)):
        decimals = [decimals, ] * len(units)

    a = list(map(float, a))
    for n, num in enumerate(a):
        if num == 0:
            a[n] = '0 Byte'
        else:
            if inbits:
                num *= 8
            exponent = min(int(math.log(num, base)), len(units) - 1)
            a[n] = ('{:.%sf} {}' % decimals[exponent]).format(
                num / (base ** exponent), units[exponent])
    return a[0] if len(a) == 1 else a


def get_boolean(v, table=constants.BOOLEAN_TABLE):
    '''convert string to boolean'''
    t = str(v).lower()
    if t not in table:
        raise ValueError('Invalid boolean value: {}'.format(v))
    return table[t]


def typename(obj):
    return type(obj).__name__


def random_id(length=8, choices=string.ascii_lowercase+string.digits):
    '''Generate a random ID composed of digits and lower ASCII characters.'''
    return ''.join([random.choice(choices) for _ in range(length)])


def validate_filename(*fns):
    '''Validate inputted filename according to system.'''
    fns = list(fns)
    for i, fn in enumerate(fns):
        name = ''.join([
            char for char in fn
            if char in constants.VALID_FILENAME_CHARACTERS
        ])
        if (
            platform.system() in ['Linux', 'Java'] and
            name in constants.INVALID_FILENAMES_UNIX
        ) or (
            platform.system() == 'Windows' and
            name in constants.INVALID_FILENAMES_WIN
        ):
            fns[i] = ''
        else:
            fns[i] = name
    return fns[0] if len(fns) == 1 else fns


def load_configs(fn=None, *fns):
    '''
    Read configuration files and return an AttributeDict.

    Examples
    --------
    This function accepts arbitrary arugments, i.e.:
        - one or more filenames
        - one list of filenames
    >>> load_configs('~/.embci/embci.conf')
    >>> load_configs('/etc/embci.conf', '~/.embci/embci.conf', 'no-exist')
    >>> load_configs(['/etc/embci.conf', '~/.embci/embci.conf'], 'no-exist')

    Notes
    -----
    Configurations priority(from low to high)::
        On Unix-like system:
            project config file: "${EmBCI}/files/service/embci.conf"
             system config file: "/etc/embci/embci.conf"
               user config file: "~/.embci/embci.conf"
        On Windows system:
            project config file: "${EmBCI}/files/service/embci.conf"
             system config file: "${APPDATA}/embci.conf"
               user config file: "${USERPROFILE}/.embci/embci.conf"
    '''
    config = configparser.ConfigParser()
    config.optionxform = str
    if not isinstance(fn, (tuple, list)):
        fn = [fn]
    for fn in [
        _ for _ in set(fn).union(fns)
        if fn is not None and isinstance(_, string_types) and os.path.exists(_)
    ] or configs.DEFAULT_CONFIG_FILES:
        logger.debug('loading config file: `%s`' % fn)
        if fn not in config.read(fn):
            logger.warn('Cannot load config file: `%s`' % fn)
    # for python2 & 3 compatibility, use config.items and config.sections
    return AttributeDict({
        section: dict(config.items(section))
        for section in config.sections()
    })


def get_config(key, default=None, type=None, configfiles=None, section=None):
    '''
    Get configurations from environment variables or config files.
    EmBCI use `INI-Style <https://en.wikipedia.org/wiki/INI_file>`_
    configuration files with extention of `.conf`.

    Parameters
    ----------
    key : str
    default : optional
        Return `default` if key is not in configuration files or environ,
    type : function | class | None, optional
        Convert function to be applied on the result, such as int or bool.
    configfiles : str | list of str, optional
        Configuration filenames.
    section : str | None, optional
        Section to search for key. Default None, search for each section.

    Notes
    -----
    Configuration resolving priority (from low to high):
    - system configuration files (loaded in embci.configs)
    - specified configuration file[s] (by argument `configfiles`)
    - environment variables (os.environ)

    See Also
    --------
    `configparser <https://en.wikipedia.org/wiki/INI_file>`_
    '''
    value = getattr(configs, key, default)
    if configfiles is not None:
        cfg = load_configs(configfiles)
        if section is not None and key in cfg.get(section, {}):
            value = cfg[section][key]
        else:
            for d in cfg.values():
                value = d.get(key, value)
    value = os.getenv(key, value)
    return type(value) if type is not None else value


class SingletonMeta(type):
    '''
    Metaclass used to create Singleton classes.

    Examples
    --------
    >>> from embci.utils import SingletonMeta, Singleton
    >>> class Test2(object):                          # Python 2 only
            __metaclass__ = Singleton
    >>> class Test3(object, metaclass=SingletonMeta)  # Python 3 only
            pass

    >>> class Test(object, Singleton)                 # Python 2 & 3
            def __init__(self, *a, **k):
                self.args = a
                self.kwargs = k
    >>> Test()
    <__main__.Test at 0x7f3e09e99390>
    >>> Test()
    <__main__.Test at 0x7f3e09e99390>
    >>> Test() == Test()
    True

    Instance can be re-initalized by providing argument `reinit`:
    >>> Test(1, 2, 3).args
    (1, 2, 3)
    >>> Test(2, 3, 4).args
    (1, 2, 3)
    >>> vars(Test(2, 3, 4, reinit=True, verbose=logging.INFO))
    {'args': (2, 3, 4), 'kwargs': {'verbose': 20}}
    '''
    __instances__ = {}

    def __new__(cls, cls_name, cls_bases, cls_dict, *a, **k):
        # Returned class's __call__ method will be overwritten by
        # cls.__call__ if it's a subclass of this metaclass.
        return type.__new__(cls, cls_name, cls_bases, cls_dict)

    def __call__(cls, *a, **k):
        if cls not in cls.__instances__:
            instance = super(SingletonMeta, cls).__call__(*a, **k)
            cls.__instances__[cls] = instance
        elif k.pop('reinit', False):
            cls.__instances__[cls].__init__(*a, **k)
        return cls.__instances__[cls]

    @classmethod
    def clear(cls):
        cls.__instances__.clear()

    @classmethod
    def remove(cls, v):
        if v in cls.__instances__:
            cls.__instances__.pop(v)


Singleton = SingletonMeta('Singleton', (object, ), {})


# =============================================================================
# Decorators

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
        '''
        Create file directory if not exists.
        Write current process's id to file if it's used as a PIDFILE.
        '''
        self.path = os.path.abspath(filename or tempfile.mktemp())
        self.file_obj = None
        k.setdefault('autoclean', True)
        k.setdefault('pidfile', False)
        for key in k:
            if key not in self.__dict__:
                self.__dict__[key] = k[key]

    def acquire(self):
        '''Lock the file object with fcntl.flock'''
        if self.file_obj is None or self.file_obj.closed:
            d = os.path.dirname(self.path)
            if not os.path.exists(d):
                os.makedirs(d, 0o775)
            #  self.file_obj = os.fdopen(
            #      os.open(self.path, os.O_CREAT | os.O_RDWR))
            self.file_obj = open(self.path, 'a+')  # 'a' will not truncate file
        try:
            fcntl.flock(self.file_obj, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except IOError:
            self.file_obj.close()
            self.file_obj = None
            raise RuntimeError('file `%s` has been used!' % self.path)
        if self.pidfile:
            self.file_obj.truncate(0)
            self.file_obj.seek(0)
            self.file_obj.write(str(os.getpid()))
            self.file_obj.flush()
        return self.file_obj

    def release(self, *a, **k):
        if self.file_obj is None:
            return
        #  if not self.file_obj.closed:
        #      fcntl.flock(self.file_obj, fcntl.LOCK_UN)
        self.file_obj.close()
        self.file_obj = None
        if not self.autoclean or not os.path.exists(self.path):
            return
        try:
            os.remove(self.path)
            logger.debug('Locked file `%s` removed.' % self.path)
        except OSError:
            pass

    __enter__ = acquire
    __exit__  = release

    def __repr__(self):
        return '<{}({}locked) {}>'.format(
            typename(self), 'un' if self.file_obj is None else '', self.path)

    def __del__(self):
        '''Ensure file released when garbage collection of instance.'''
        try:
            self.release()
        except (AttributeError, TypeError):
            pass


class TempStream(object):
    '''
    Context manager to temporarily mask streams like stdout/stderr/stdin.

    Examples
    --------
    You can redirect standard output to a file just like shell command
    `$ python test.py > /var/log/foo.log`:

    >>> with TempStream(stdout='/var/log/foo.log'):
            print('bar', file=sys.stdout)
    >>> open('var/log/foo.log').read()
    bar

    If no target stream (file-like object) specified, a StringIO buffer is
    used to collect message from origin stream. All string from buffers will
    be saved in an AttributeDict and returned for easier usage.

    >>> # mask stdout and stderr to a string buffer
    >>> with TempStream('stdout', 'stderr') as ts:
            print('hello', file=sys.stdout, end='')
            print('error', file=sys.stderr)
    >>> type(ts)
    embci.utils.AttributeDict
    >>> str(ts)
    "{'stderr': 'error\\n', 'stdout': 'hello'}"
    >>> ts.stdout + ' ' + ts['stderr']
    'hello error\n'
    '''
    _disabled = False
    _target = {
        'stdout': sys.stdout,
        'stderr': sys.stderr,
        'stdin':  sys.stdin
    }

    def __init__(self, *args, **kwargs):
        self._replace = {}
        self._savepos = {}
        self._message = AttributeDict()
        for arg in args:
            if arg not in kwargs:
                kwargs[arg] = None
        for name, stream in kwargs.items():
            if name not in ['stdout', 'stderr', 'stdin']:
                logger.error('Invalid stream name: `{}`'.format(name))
                continue
            if stream is None:
                stream = StringIO()
            elif isinstance(stream, string_types):
                stream = open(stream, 'w+')
            elif not hasattr(stream, 'write'):
                raise TypeError('Invalid stream: `{}`'.format(stream))
            self._replace[name] = stream
            self._savepos[stream] = 0

    def enable(self):
        assert not self._disabled, 'Cannot re-enable a disabled TempStream'
        # replace origin streams with new streams
        for name, stream in self._replace.items():
            setattr(sys, name, stream)
        return self._message

    def disable(self, *a):
        for name, stream in self._replace.items():
            # recover origin stream
            setattr(sys, name, self._target[name])
            # check if new stream is one of origins
            if stream in self._target.values():
                continue
            # fetch message as string from new streams
            self._message[name] = self.get_string(stream)
            stream.close()
        self._disabled = True

    def get_string(self, stream=None, clean=False):
        '''
        Current stream position is saved so that next time it will read from
        where it left this time without cleaning.
        '''
        if stream is None:
            for name, stream in self._replace.items():
                self._message[name] = self.get_string(stream, clean=True)
            return self._message
        elif stream in self._replace:
            stream = self._replace[stream]
        elif stream not in self._replace.values():
            raise ValueError('Not masked stream: `{}`'.format(stream))
        stream.flush()
        # Get current cursor position
        pos = stream.tell()
        # Move cursor to last position
        stream.seek(self._savepos[stream] if not clean else 0)
        msg = stream.read()
        # Default it will not clean the buffer
        if clean:
            stream.truncate(0)
            pos = 0
        stream.seek(pos)
        self._savepos[stream] = pos
        return msg

    @classmethod
    def disable_all(cls):
        cls._disabled = True

    __enter__ = enable
    __exit__ = disable


class CachedProperty(object):
    '''
    Descriptor class to construct a property that is only computed once and
    then replaces itself as an ordinary attribute. Deleting the attribute
    resets the property.
    '''
    def __init__(self, func):
        self.__func = func
        self.__name = func.__name__
        self.__doc__ = getattr(func, '__doc__')

    def __get__(self, obj, cls):
        if obj is None:
            return self
        obj.__dict__[self.__name] = self.__func(obj)
        return getattr(obj, self.__name)


@decorator
def verbose(func, *args, **kwargs):
    '''
    Add support to any callable functions or methods to change verbose level
    by specifying keyword argument `verbose='LEVEL'`.

    Verbose level can be int or bool or one of `logging` defined string
    ['NOTSET', 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']

    Examples
    --------
    >>> @verbose
    ... def echo(s):
    ...     logger.info(s)
    >>> echo('set log level to warning', verbose='WARN')
    >>> echo('set log level to debug', verbose='DEBUG')
    set log level to debug
    >>> echo('mute message', verbose=False)  # equals to verbose=ERROR
    >>> echo('max verbose', verbose=True)    # equals to verbose=NOTSET
    max verbose
    >>> echo('default level', verbose=None)  # do not change verbose level

    Notes
    -----
    Verbose level may comes from ways listed below (sorted by prority),
    which also means this function can be used under these situations.

    1. class default verbosity
    >>> class Testing(object):
    ...     def __init__(self):
    ...         self.verbose = 'INFO'
    ...     @verbose
    ...     def echo(self, s, verbose=None):
    ...         # verbose = verbose or self.verbose
    ...         logger.info(s)

    2. default argument
    >>> @verbose
        def echo(s, verbose=True):
            logger.info(s)
    >>> echo('hello')
    hello

    3. positional argument
    >>> echo('hello', None)

    4. keyword argument
    >>> echo('hello', verbose=False)
    '''
    level = None
    argnames, defaults = get_func_args(func)

    if len(argnames) and argnames[0] in ('self', 'cls'):
        level = getattr(args[0], 'verbose', level)                # situation 1
    if 'verbose' in argnames:
        idx = argnames.index('verbose')
        try:
            level = defaults[idx - len(argnames)]                 # situation 2
        except IndexError:
            pass  # default not defined in function
        try:
            level = args[idx]                                     # situation 3
        except IndexError:
            pass  # verbose not provided by user
    level = kwargs.pop('verbose', level)                          # situation 4

    if isinstance(level, bool):
        level = 'ERROR' if level else 'NOTSET'
    if level is None:
        return func(*args, **kwargs)
    with TempLogLevel(level):
        return func(*args, **kwargs)


def duration(sec, name=None, warning=None):
    '''
    Want to looply execute some function every specific time duration?
    You may use this deocrator factory.

    Parameters
    ----------
    sec : int
        Minimum duration of executing function in seconds.
    name : str, optional
        Identify task name. Default use id(function).
    warning : str, optional
        Warn message to display if function is called too frequently.

    Examples
    --------
    >>> @duration(3, '__main__.testing', warning='cant call so frequently!')
    ... def testing(s):
    ...     print('time: %.1fs, %s' % (time.clock(), s))

    >>> while 1:
    ...     time.sleep(1)
    ...     testing('now you are executing testing function')
    ...
    time: 32.2s, now you are executing testing function
    cant call so frequently! # time: 33.2s
    cant call so frequently! # time: 34.2s
    time: 35.2s, now you are executing testing function
    cant call so frequently! # time: 36.2s
    cant call so frequently! # time: 37.2s
    ...
    '''
    time_dict = {}

    @decorator
    def wrapper(func, *args, **kwargs):
        _name = name or id(func)
        if _name not in time_dict:
            time_dict[_name] = time.time()
            return func(*args, **kwargs)
        if (time.time() - time_dict[_name]) < sec:
            if warning:
                logger.warning(warning)
            return
        else:
            time_dict[_name] = time.time()
            return func(*args, **kwargs)
    return wrapper


def embedded_only(reason='Skip execution on current platform', retval=None):
    @decorator
    def wrapper(func, *args, **kwargs):
        if platform.machine() in ['arm', 'aarch64']:
            return func(*args, **kwargs)
        else:
            logger.warning('%s: `%s`' % (reason, platform.platform()))
            return retval
    return wrapper


# =============================================================================
# I/O

#  class TimeoutException(TimeoutError):  # py3 only, use this after 2020.1.1
class TimeoutException(Exception):
    def __init__(self, msg=None, sec=None, src=None):
        self.src, self.sec, self.msg = self.args = (src, sec, msg)

    def __repr__(self):
        return 'Timeout{timeout}{message}{source}'.format(
            timeout = self.sec and '({}s)'.format(self.sec) or '',
            message = self.msg and ': %s' % str(self.msg) or '',
            source  = self.src and ' within `%s`.' % self.src or ''
        )


def input(prompt=None, timeout=None, flist=[sys.stdin]):
    '''
    input([prompt[, timeout[, flist]]]) -> string

    Read from a list of file-like objects (default only from sys.stdin)
    and return raw string as python2 function `raw_input` do.

    The optional second argument specifies a timeout in seconds. Both int
    and float is accepted. If timeout, an error will be thrown out.

    This function is PY2/3 & Linux/Windows compatible (On Windows, only
    sockets are supported; on Unix, all file descriptors can be used.)
    '''
    #  if os.name == 'nt':
    #      from builtins import input
    #      return input(prompt)

    if prompt is not None:
        stdout.write(prompt)
        stdout.flush()
    if not isinstance(flist, (tuple, list)):
        flist = [flist]
    try:
        rlist, _, _ = select.select(flist, [], [], timeout)
    except select.error:
        rlist = []
    except (KeyboardInterrupt, EOFError):
        raise KeyboardInterrupt
    if not rlist:
        msg = 'read from {} failed'.format(
            flist[0] if len(flist) == 1 else flist)
        raise TimeoutException(msg, timeout, 'embci.utils.input')
    f = os.fdopen(rlist[0]) if isinstance(rlist[0], int) else rlist[0]
    for method in ['readline', 'read', 'recv']:
        if not hasattr(f, method):
            continue
        return getattr(f, method)().rstrip('\n')
    raise TypeError('Cannot read from `%s`' % f)


def check_input(prompt, answer={'y': True, 'n': False, '': True},
                timeout=60, times=3):
    '''
    This function is to guide user make choices.

    Examples
    --------
    >>> check_input('This will call pip and try install pycnbi. [Y/n] ',
                    {'y': True, 'n': False})
    [1/3] This will call pip and try install pycnbi. [Y/n] 123
    Invalid input `123`! Choose from [ y | n ]
    [2/3] This will call pip and try install pycnbi. [Y/n] y
    # return True
    '''
    k = list(answer.keys())
    t = 1
    while t <= times:
        try:
            rst = input('[%d/%d] ' % (t, times) + prompt, timeout / times)
        except TimeoutException:
            continue
        if not k:
            if not rst:
                if input('nothing read, confirm? ([Y]/n) ', 60).lower() == 'n':
                    continue
            return rst
        elif rst in k:
            return answer[rst]
        print('Invalid input `%s`! Choose from [ %s ]' % (rst, ' | '.join(k)))
        t += 1
    return ''


def mkuserdir(func):
    '''
    Create user folder at ${DIR_DATA}/${username} if it doesn't exists.

    Examples
    --------
    When used as a decorator, it will automatically detect arguments of wrapped
    function to get the specified `username` argument and create its folder.
    >>> @mkuserdir
    ... def save_user_data(username):
    ...     path = os.path.join(DIR_DATA, username, 'data-1.csv')
    ...     write_data_to_csv(path, data)
    >>> save_user_data('bob')   # folder ${DIR_DATA}/bob is already created
    >>> save_user_data('jack')  # write_data_to_csv don't need to care this

    Or use it with username directly:
    >>> mkuserdir('john')
    >>> os.listdir(DIR_DATA)
    ['example', 'bob', 'jack', 'john']
    '''
    if callable(func):
        def param_collector(*a, **k):
            if a and isinstance(a[0], string_types):
                username = a[0]
            else:
                username = k.get('username')
            if username is not None:
                mkuserdir(username)
            else:
                logger.warning(
                    'Username is not detected, `%s` decorator abort.' % func)
                if a or k:
                    logger.debug('args: {}, kwargs: {}'.format(a, k))
            return func(*a, **k)
        param_collector.__doc__ = func.__doc__
        return param_collector
    elif isinstance(func, string_types):
        user = ensure_unicode(func)
        path = os.path.join(configs.DIR_DATA, user)
        if os.path.exists(path):
            logger.debug('User %s\'s folder at %s exist,' % (user, path))
        else:
            os.makedirs(path, 0o775)
            logger.debug('User %s\'s folder at %s created.' % (user, path))
        return
    raise TypeError('function or string wanted, but got `%s`' % typename(user))


@verbose
def virtual_serial(verbose=logging.INFO, timeout=120):
    '''
    Generate a pair of virtual serial port at /dev/pts/*.
    Super useful when debugging without a real UART device.

    Parameters
    ----------
    verbose : bool | int
        Logging level or boolean specifying whether print serial I/O data
        count infomation to terminal. Default logging.INFO.
    timeout : int
        Virtual serial connection will auto-break to save system resources
        after waiting until timeout. -1 specifying never timeout. Default is
        120 seconds (2 mins).

    Returns
    -------
    flag_close : threading.Event
        Set flag by `flag_close.set` to manually terminate the virtual
        serial connection.
    port1 : str
        Master serial port.
    port2 : str
        Slave serial port.

    Examples
    --------
    >>> flag = virtual_serial(timeout=-1)[0]

    Suppose it's /dev/pts/0 <==> /dev/pts/1
    >>> s = serial.Serial('/dev/pts/1',115200)
    >>> m = serial.Serial('/dev/pts/0',115200)
    >>> s.write('hello?\\n')
    7
    >>> m.read_until()
    'hello?\\n'
    >>> flag.set()
    '''
    master1, slave1 = os.openpty()
    master2, slave2 = os.openpty()
    port1, port2 = os.ttyname(slave1), os.ttyname(slave2)
    # RX1 TX1 RX2 TX2 counter
    count = np.zeros(4)
    logger.info('[Visual Serial] Pty opened!')
    logger.info('Port1: %s\tPort2: %s' % (port1, port2))

    def echo(flag_close):
        while not flag_close.isSet():
            rlist = select.select([master1, master2], [], [], 2)[0]
            if not rlist:
                continue
            for master in rlist:
                msg = os.read(master, 1024)
                if master == master1:
                    logger.debug('[{} --> {}] {}'.format(port1, port2, msg))
                    count[1] += len(msg)
                    count[2] += os.write(master2, msg)
                elif master == master2:
                    logger.debug('[{} --> {}] {}'.format(port2, port1, msg))
                    count[3] += len(msg)
                    count[0] += os.write(master1, msg)
            logger.debug('\rRX1: %s\tTX1: %s\tRX2: %s\tTX2: %s'
                         % tuple(format_size(*count)))
        logger.info('[Virtual Serial] shutdown...')
    flag_close = threading.Event()
    t = threading.Thread(target=echo, args=(flag_close,))
    t.setDaemon(True)
    t.start()
    if timeout > 0:
        killer = threading.Timer(timeout, lambda *a: flag_close.set())
        killer.setDaemon(True)
        killer.start()
    return flag_close, port1, port2


# =============================================================================
# Local Modules

from ._looptask import *                                           # noqa: W401

from ._logging import *                                            # noqa: W401
from ._logging import TempLogLevel, config_logger
logger = config_logger(logger, addhdlr=False)

from ._resolve import *                                            # noqa: W401
from ._resolve import get_func_args, get_caller_globals

from ._json import *                                               # noqa: W401

from ._event import *                                              # noqa: W401

# THE END
