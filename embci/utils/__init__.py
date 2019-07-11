#!/usr/bin/env python
# coding=utf-8
#
# File: EmBCI/embci/utils/__init__.py
# Author: Hankso
# Webpage: https://github.com/hankso
# Time: Tue 27 Feb 2018 16:03:02 CST

# built-in
from __future__ import print_function, absolute_import, unicode_literals
import os
import re
import sys
import copy
import math
import json
import zlib
import glob
import time
import types
import fcntl
import select
import socket
import inspect
import marshal
import logging
import tempfile
import warnings
import importlib
import threading
import traceback
from collections import MutableMapping, MutableSequence
try:
    import ConfigParser as configparser
except ImportError:
    import configparser

# requirements.txt: drivers: pyserial
# requirements.txt: data-processing: pylsl, numpy
# requirements.txt: necessary: decorator, six, dill
from serial.tools.list_ports import comports
import pylsl
import numpy as np
from decorator import decorator
from six import StringIO
import dill

from ..constants import BOOLEAN_TABLE
from ..configs import DATADIR, LOGFORMAT, DEFAULT_CONFIG_FILES
import embci.configs


# =============================================================================
# CONSTANTS

__doc__ = 'Some utility functions and classes.'
__dir__ = os.path.dirname(os.path.abspath(__file__))

# save 0,1,2 files so that TempStream will not replace these variables.
stdout, stderr, stdin = sys.stdout, sys.stderr, sys.stdin

# example for mannualy create a logger
logger = logging.getLogger(__name__)
hdlr = logging.StreamHandler(stdout)
hdlr.setFormatter(logging.Formatter(LOGFORMAT))
logger.handlers = [hdlr]
logger.setLevel(logging.WARN)
del hdlr
# you can use config_logger instead, which is better

if sys.version_info > (3, 0):
    strtypes = (bytes, str)  # noqa: E602
else:
    strtypes = (basestring)  # noqa: E602

from ..testing import PytestRunner
test = PytestRunner(__name__)
del PytestRunner


# =============================================================================
# UTILITIES

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
            if isinstance(items, strtypes) and items[0] == items[-1] == '_':
                # get rid of some ipython magics
                return
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
            raise NotImplementedError
        return dict(self.items()) == dict(other.items())

    def __str__(self):
        return self.__mapping__.__str__()

    def __repr__(self):
        return '<{}.{} {} at {}>'.format(
            self.__module__, self.__class__.__name__,
            str(self), hex(id(self))
        )

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
        ids = self.id
        if hasattr(element, 'id') and getattr(element, 'id', -1) in ids:
            return True
        elif element in ids:
            return True
        for e in self:
            if e == element:
                return True
        return False

    def __nonzero__(self):
        return bool(self.__sequence__)

    def __len__(self):
        return self.__sequence__.__len__()

    def insert(self, index, value):
        self.__sequence__.insert(index, value)

    def __str__(self):
        return self.__sequence__.__str__()

    def __repr__(self):
        return '<{}.{} {} at {}>'.format(
            self.__module__, self.__class__.__name__, str(self), hex(id(self))
        )

    def __iter__(self):
        return self.__sequence__.__iter__()

    def index(self, element):
        if element not in self:
            #  raise ValueError("'{}' is not in list".format(element))
            return -1
        ids = self.id
        if hasattr(element, 'id') and getattr(element, 'id', -1) in ids:
            return ids.index(element.id)
        elif element in ids:
            return ids.index(element)
        for n, e in enumerate(self.__sequence__):
            if e == element:
                return n

    def pop(self, element, default=None):
        index = self.index(element)
        if index == -1:
            return default
        return self.__sequence__.pop(index)

    def remove(self, element):
        self.pop(element)

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
    def __nonzero__(self, table=BOOLEAN_TABLE):
        return get_boolean(self, table)

    __bool__ = __nonzero__


class JSONEncoder(json.JSONEncoder):
    '''
    This class is a dirty fix to make JSONEncoder support custom jsonifying
    of nested and inherited default types such as dict, list and tuple etc.
    By overwriting method `json.JSONEncoder.iterencode`, it changed default
    behaviour on types inside tuple `self.masked`.

    More at [this page](https://stackoverflow.com/questions/16405969/).
    '''
    item_separator = ','
    key_separator = ': '
    masked = ()

    def __init__(self, *a, **k):
        if 'ensure_ascii' not in k:
            k['ensure_ascii'] = False
        if 'sort_keys' not in k:
            k['sort_keys'] = True
        if 'indent' not in k:
            k['indent'] = 4
        super(JSONEncoder, self).__init__(*a, **k)

    def _floatstr(self, o, _inf=float('inf')):
        if o != o:
            text = 'NaN'
        elif abs(o) is _inf:
            text = {_inf: 'Infinity', -_inf: '-Infinity'}[o]
        else:
            return repr(o)
        if not self.allow_nan:
            raise ValueError('Out of range float values are not JSON'
                             'compliant: ' + repr(o))
        return text

    def _encoder(self, o):
        if self.encoding != 'utf-8' and isinstance(o, strtypes):
            o = o.decode(self.encoding)
        if self.ensure_ascii:
            return json.encoder.encode_basestring_ascii(o)
        else:
            return json.encoder.encode_basestring(o)

    def _isinstance(self, o, cls):
        if isinstance(o, self.masked):
            return False
        return isinstance(o, cls)

    def iterencode(self, o, _one_shot=False):
        return json.encoder._make_iterencode(
            {} if self.check_circular else None, self.default, self._encoder,
            self.indent, self._floatstr, self.key_separator,
            self.item_separator, self.sort_keys, self.skipkeys,
            _one_shot=False, isinstance=self._isinstance)(o, 0)


class MiscJsonEncoder(JSONEncoder):
    '''
    Extend default json.JSONEncoder with many more features.

    Supported types:
    - function
        1 builtin_function_or_method - dill
        2 instancemethod - dill
        3 function.func_code - marshal
    - numpy.ndarray
    - subclass of MutableMapping and MutableSequence
    - subclass of default supported types like dict and list etc.(see notes)

    Notes
    -----
    If you want to extend this class to support more types of object,
    1 add the type into class's `masked` tuple
    2 overwrite `default` or define `jsonify_xxx_hook`

    >>> class Test(MiscJsonEncoder):
            def __init__(self):
                self.masked += (MyClass, )
                super(Test, self).__init__()
            def default(self, o):
                if isinstance(o, MyClass):
                    return jsonify_MyClass(o)
                return super(Test, self).default(o)

    or you can define `jsonify_xxx_hook`(object type in lower case!)

    >>> class Test(MiscJsonEncoder):
            masked = MiscJsonEncoder.masked + (MyClass, )
            def jsonify_myclass_hook(self, o):
                return jsonify_MyClass(o)

    then you can use it as normal json encoder

    >>> Test().masked
    [builtin_function_or_method,
     function,
     instancemethod,
     numpy.ndarray,
     embci.utils.AttributeDict,
     embci.utils.AttributeList,
     bytearray,
     __main__.MyClass]
    >>> Test().encode(MyClass()) ==> string
    '''
    bytearray_encoding = 'cp437'
    masked = (
        types.BuiltinFunctionType, types.FunctionType, types.MethodType,
        np.ndarray, AttributeDict, AttributeList, bytearray
    )

    def default(self, o):
        if callable(o):
            o_type = 'function'
        else:
            o_type = getattr(type(o), '__name__', 'unknown').lower()
        try:
            return getattr(self, 'jsonify_%s_hook' % o_type)(o)
        except AttributeError:
            return super(MiscJsonEncoder, self).default(o)

    def jsonify_function_hook(self, o):
        try:
            fstr = marshal.dumps(o.func_code)
        except ValueError:
            fstr = dill.dumps(o)
        return {
            '__callable__': bytearray(fstr),
            '__module__': o.__module__,
            '__class__': o.__class__.__name__,
            '__name__': o.__name__
        }

    def jsonify_attributedict_hook(self, o):
        return {'__module__': o.__module__,
                '__class__': o.__class__.__name__,
                'object': o.copy(dict)}

    def jsonify_attributelist_hook(self, o):
        return {'__module__': o.__module__,
                '__class__': o.__class__.__name__,
                'object': o.copy(list)}

    def jsonify_ndarray_hook(self, o):
        return {'__ndarray__': bytearray(o.tobytes()),
                'shape': o.shape,
                'dtype': str(o.dtype)}

    def jsonify_bytearray_hook(self, o):
        o = zlib.compress(str(o), 9)
        return {'__bytearray__': o.decode(self.bytearray_encoding),
                'encoding': self.bytearray_encoding}


class MiscJsonDecoder(json.JSONDecoder):
    '''
    JSON string decoder. :method:`unjsonify_xxx_hook` should handle
    all exception and always return object or None.

    See Also
    --------
    MiscJsonEncoder
    '''
    def __init__(self, *a, **k):
        super(MiscJsonDecoder, self).__init__(
            encoding='utf8', object_hook=self.object_hook)

    _hook_pattern = re.compile(r'unjsonify_(\w)+_hook')

    @property
    def decode_hooks(self):
        return [hook_name for hook_name in MiscJsonDecoder.__dict__
                if self._hook_pattern.match(hook_name)]

    def object_hook(self, dct):
        '''
        This function will be used by method `decode` to convert
        dict into object. It is the last step of unjsonify.
        '''
        for hook in self.decode_hooks:
            try:
                obj = getattr(self, hook)(dct)
            except KeyError:
                continue
            except Exception:
                logger.error(traceback.format_exc())
            else:
                if obj is not None:
                    return obj
        return dct

    def unjsonify_bytearray_hook(self, dct):
        return zlib.decompress(dct['__bytearray__'].encode(dct['encoding']))

    def unjsonify_ndarray_hook(self, dct):
        return np.frombuffer(
            dct['__ndarray__'],
            np.dtype(dct['dtype'])
        ).reshape(*dct['shape'])

    def unjsonify_instance_hook(self, dct):
        module = importlib.import_module(dct['__module__'])
        try:
            cls = getattr(module, dct['__class__'])
        except AttributeError:
            return
        else:
            return cls(dct['object'])

    def unjsonify_callable__hook(self, dct):
        fstr = dct['__callable__']
        try:
            fcode = marshal.loads(fstr)
        except ValueError:
            return dill.loads(fstr)
        else:
            fname = dct['__name__'].encode('utf8')
            return types.FunctionType(fcode, globals(), fname)


class LoopTaskMixin(object):
    '''
    Establish a task to execute a function looply. Stream control methods are
    integrated, such as `start`, `pause`, `resume`, `close`, etc.

    Examples
    --------
    >>> class Clock(LoopTaskMixin):
            def loop_before(self):  # optional function
                print('this is a simple clock')
            def loop_after(self):  # optional function
                print('clock end')
            def loop_display_time(self, name):
                print("{}: {}".format(name, time.time()))
                time.sleep(1)
            def start(self):
                if LoopTaskMixin.start(self) is False:
                    return 'this clock is already started'
                self.loop(func=self.loop_display_time, args=('MyClock', ),
                          before=self.loop_before, after=self.loop_after)
    >>> c = Clock()
    >>> c.start()
    this is a simple clock
    MyClock: 1556458048.83
    MyClock: 1556458049.83
    MyClock: 1556458050.83
    ^C (KeyboardInterrupt Ctrl+C)
    clock end

    See Also
    --------
    embci.utils.LoopTaskInThread
    embci.io.readers.BaseReader
    '''
    def __init__(self):
        '''
        A mixin class should not be used directly. This __init__ is only
        for testing. If you need to subclass this Mixin and use your own
        __init__, remember to call LoopTaskMixin.__init__(self) or config
        the properties correctly.
        '''
        self.__flag_pause__ = threading.Event()
        self.__flag_close__ = threading.Event()
        self.__started__ = False
        self.__status__ = b'closed'  # use bytes for c_char_p compatiable

    @property
    def status(self):
        '''Status of the loopTask is read-only'''
        return ensure_unicode(self.__status__)

    @property
    def started(self):
        '''Started of the loopTask is read-only'''
        return self.__started__

    def start(self, *a, **k):
        if self.started:
            if self.status == 'paused' and self.__flag_pause__.is_set():
                return self.resume()
            else:
                return False
        self.__flag_pause__.set()
        self.__flag_close__.clear()
        self.__started__ = True
        self.__status__ = b'started'
        self._start_time = time.time()
        return True

    def close(self):
        if not self.started:
            return False
        self.__flag_close__.set()
        self.__flag_pause__.clear()
        # you can restart this task now
        self.__started__ = False
        self.__status__ = b'closed'
        return True

    def restart(self, *args, **kwargs):
        if self.started:
            self.close()
        self.start(*args, **kwargs)
        return True

    def pause(self):
        if not self.started:
            return False
        self.__flag_pause__.clear()
        self.__status__ = b'paused'
        return True

    def resume(self):
        if not self.started:
            return False
        self.__flag_pause__.set()
        self.__status__ = b'resumed'
        return True

    def loop(self, func, args=(), kwargs={}, before=None, after=None):
        try:
            if before is not None:
                before()
            while not self.__flag_close__.is_set():
                if self.__flag_pause__.wait(2):
                    func(*args, **kwargs)
        except KeyboardInterrupt:
            logger.info('KeyboardInterrupt detected.')
        except Exception:
            logger.error(traceback.format_exc())
        finally:
            self.close()
            if after is not None:
                after()


class LoopTaskInThread(threading.Thread, LoopTaskMixin):
    def __init__(self, func=None, daemon=True, *a, **k):
        self.__tdaemon, self.__targs, self.__tkwargs = daemon, a, k
        self.__init_thread()  # you can call this function to reinit thread
        self._func_ = func
        self._before_ = k.pop('before', None)
        self._after_ = k.pop('after', None)
        self.name = self._name = 'Loop Task on {}'.format(
            getattr(self._func_, 'func_name', self._name))
        LoopTaskMixin.__init__(self)

    def __init_thread(self):
        threading.Thread.__init__(self, *self.__targs, **self.__tkwargs)
        self.setDaemon(self.__tdaemon)

    def start(self):
        if not self.started:
            threading.Thread.start(self)
        return LoopTaskMixin.start(self)

    def close(self):
        if not LoopTaskMixin.close(self):
            return 'already closed task'
        # TODO: LoopTaskInThread: make Thread restartable

    def run(self):
        try:
            self.loop(self._func_, before=self._before_, after=self._after_)
        finally:
            logger.info('{} stopped.'.format(self))


def time_stamp(localtime=None, fmt='%Y%m%d-%H:%M:%S'):
    return time.strftime(fmt, localtime or time.localtime())


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
        if not isinstance(i, strtypes):
            raise TypeError('cannot convert non-string type `{}` to unicode'
                            .format(type(i).__name__))
        if isinstance(i, bytes):     # py2 str or py3 bytes
            a[n] = i.decode('utf8')  # py2 unicode or py3 str
            # a[n] = u'{}'.format(a[n])
    if len(a) == 1:
        return a[0]
    return a


def ensure_bytes(*a):
    a = list(a)
    for n, i in enumerate(a):
        if not isinstance(i, strtypes):
            raise TypeError('cannot convert non-string type `{}` to bytes'
                            .format(type(i).__name__))
        if not isinstance(i, bytes):  # py2 unicode or py3 str
            a[n] = i.encode('utf8')   # py2 str or py3 bytes
            # a[n] = b'{}'.format(a[n])
    return a[0] if len(a) == 1 else a


def format_size(*a, **k):
    '''
    Turn number of bytes into human-readable str.

    Examples
    --------
    >>> format_size(2**10 - 1)
    u'1023 bytes'
    >>> format_size(2**10)
    u'1.0 kB'
    >>> format_size(1024 * 1024)
    u'1.00 MB'

    See Also
    --------
    mne.utils.sizeof_fmt
    '''
    a = list(a)
    units = ['bytes', 'kB', 'MB', 'GB', 'TB', 'PB']
    decimals = k.get('decimals', [0, 1, 2, 2, 2, 2])
    if not isinstance(decimals, (tuple, list)):
        decimals = [decimals] * len(units)
    for n, num in enumerate(a):
        if num == 0:
            a[n] = '0 bytes'
        elif num == 1:
            a[n] = '1 byte'
        elif num > 1:
            exponent = min(int(math.log(num, 1024)), len(units) - 1)
            a[n] = ('{:.%sf} {}' % decimals[exponent]).format(
                float(num) / 1024 ** exponent, units[exponent])
    if len(a) == 1:
        return a[0]
    return a


def serialize(obj, method='dill'):
    if method == 'dill':
        return dill.dumps(obj)
    elif method == 'json':
        return MiscJsonEncoder().encode(obj)
    elif method == 'minimize':
        return MiscJsonEncoder(indent=None, separators=(',', ':')).encode(obj)
    else:
        raise ValueError('serialization method `%s` is not supported' % method)


def deserialize(string, method='dill'):
    if method == 'dill':
        return dill.loads(string)
    elif method in ['json', 'minimize']:
        return MiscJsonDecoder().decode(string)
    else:
        raise ValueError('serialization method `%s` is not supported' % method)


class Singleton(type):
    '''
    Singleton metaclass

    Examples
    --------
    >>> class Test(object):  # py2 & py3
            __metaclass__ = Singleton
            def __init__(self, *a, **k):
                self.a = a
                self.k = k

    >>> class Test(object, metaclass=Singleton):  # py3 only
            pass

    >>> Test()
    <__main__.Test at 0x7f3e09e99390>
    >>> Test()
    <__main__.Test at 0x7f3e09e99390>
    >>> Test() == Test() == _
    True

    Instance can be re-initalized by providing argument `reinit`:
    >>> Test(1, 2, 3).a
    (1, 2, 3)
    >>> Test(2, 3, 4).a
    (1, 2, 3)
    >>> vars(Test(2, 3, 4, reinit=True, verbose=logging.INFO))
    {'a': (2, 3, 4), 'k': {'verbose': 20}}
    '''
    __instances__ = {}

    def __init__(self, *a, **k):
        # Do nothing. For future extension.
        pass

    def __new__(cls, cls_name, cls_bases, cls_dict, *a, **k):
        # Returned class's __call__ method will be overwritten by
        # cls.__call__ if it's a subclass of this metaclass.
        return type.__new__(cls, cls_name, cls_bases, cls_dict)

    def __call__(cls, *a, **k):
        if cls not in cls.__instances__:
            cls.__instances__[cls] = super(Singleton, cls).__call__(*a, **k)
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


# =============================================================================
# DECORATORS

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
        self.path = os.path.abspath(filename or tempfile.mkstemp()[1])
        d = os.path.dirname(self.path)
        if not os.path.exists(d):
            os.makedirs(d)
        #  self.file_obj = os.fdopen(
        #      os.open(self.path, os.O_CREAT | os.O_RDWR))
        self.file_obj = open(self.path, 'a+')  # 'a' will not truncate file
        if k.get('pidfile', False):
            self.file_obj.truncate(0)
            self.file_obj.seek(0)
            self.file_obj.write(str(os.getpid()))
            self.file_obj.flush()
        k.setdefault('autoclean', True)
        self.__dict__.update(k)

    def acquire(self):
        '''Lock the file object with fcntl.flock'''
        try:
            fcntl.flock(self.file_obj, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except IOError:
            raise RuntimeError('file `%s` has been used!' % self.path)
        return self.file_obj

    def release(self, *a, **k):
        self.file_obj.close()
        if not self.autoclean or not os.path.exists(self.path):
            return
        try:
            os.remove(self.path)
            logger.debug('Locked file `%s` removed.' % self.path)
        except OSError:
            pass

    __enter__ = acquire
    __exit__  = release

    def __str__(self):
        return '<{0.__class__.__name__} {1}>'.format(self, self.path)

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
            elif isinstance(stream, strtypes):
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


class TempLogLevel(object):
    '''
    Context manager to temporarily change log level and auto set back.
    '''

    def __init__(self, level):
        self._logger = logging.getLogger(get_caller_globals(1)['__name__'])
        self._old_level = self._logger.level
        if isinstance(level, str):
            level = level.upper()
        self._level = level

    def __enter__(self):
        self._logger.setLevel(self._level)
        return self._logger

    def __exit__(self, *a):
        self._logger.setLevel(self._old_level)


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
        def echo(s):
            logger.info(s)
    >>> echo('set log level to warning', verbose='WARN')
    >>> echo('set log level to debug', verbose='DEBUG')
    set log level to debug
    >>> echo('mute message', verbose=False)  # equals to verbose=ERROR
    >>> echo('max verbose', verbose=True)    # equals to verbose=NOTSET
    max verbose
    >>> echo('default level', verbose=None)  # do not change verbose level

    Notes
    -----
    Verbose level may comes from(sorted by prority):

    1. default argument
    >>> @verbose
        def echo(s, verbose=True):
            logger.info(s)
    >>> echo('hello')
    hello

    2. class default
    >>> @verbose
        def echo(self, s, verbose=None):
            verbose = verbose or self.verbose
            logger.info(s)

    3. positional argument
    >>> echo('hello', None)

    4. keyword argument
    >>> echo('hello', verbose=False)

    All above will be overwritten by specifying `verbose` argument.
    '''
    level = None
    argnames, defaults = get_func_args(func)
    if 'verbose' in argnames:
        idx = argnames.index('verbose')
        try:
            level = defaults[idx - len(argnames)]         # situation 1
        except IndexError:
            pass  # default not defined in function
        try:
            level = args[idx]                             # situation 3
        except IndexError:
            pass  # verbose not provided by user
    if level is None and len(argnames) and argnames[0] == 'self':
        level = getattr(args[0], 'verbose', level)        # situation 2
    level = kwargs.pop('verbose', level)                  # situation 4
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


# =============================================================================
# I/O

class TimeoutException(Exception):
    def __init__(self, msg=None, sec=None, src=None):
        self.msg = msg
        self.src = src
        self.sec = sec

    def __str__(self):
        msg = 'Timeout'
        if self.src is not None:
            msg += ': {} wait for too long'.format(self.src)
        if self.sec is not None:
            msg += ' ({} seconds)'.format(self.sec)
        if self.msg is not None:
            msg += ', {}'.format(self.msg)
        return msg


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
    # from builtins import input
    # return input(propmt)

    if prompt is not None:
        stdout.write(prompt)
        stdout.flush()
    if not isinstance(flist, (tuple, list)):
        flist = [flist]
    try:
        rlist, _, _ = select.select(flist, [], [], timeout)
    except select.error:
        rlist = []
    if not rlist:
        msg = 'read from {} failed'.format(flist)
        raise TimeoutException(msg, timeout, '`input`')
    if isinstance(rlist[0], int):
        rlist[0] = os.fdopen(rlist[0])
    return rlist[0].readline().rstrip('\n')


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
            rst = input('[%d/%d] ' % (t, times) + prompt,
                        timeout=(float(timeout) / times))
        except TimeoutException:
            break
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


@decorator
def mkuserdir(func, *a, **k):
    '''Create user folder at ${DATADIR}/${username} if it doesn't exists.'''
    if a and isinstance(a[0], strtypes):
        username = ensure_unicode(a[0])
    elif 'username' in k:
        username = k.get('username')
    else:
        logger.warning(
            'Username is not provided, `{}` decorator abort.'.format(func))
        if a or k:
            logger.debug('args: {}, kwargs: {}'.format(a, k))
        return func(*a, **k)
    path = os.path.join(DATADIR, username)
    if not os.path.exists(path):
        os.makedirs(path)
    return func(*a, **k)


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
        after waiting until timeout. -1 specifing never timeout. Default is
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


def config_logger(name=None, level=logging.INFO, format=LOGFORMAT, **kwargs):
    '''
    Create/config a `logging.Logger` with current namespace's `__name__`.

    Parameters
    ----------
    name : str or logging.Logger, optional
        Name of logger. Default `__name__` of function caller's module.
    level : int or str, optional
        Logging level. Default `logging.INFO`, i.e. 20.
    format : str, optional
        Format string for handlers. Default `embci.configs.LOGFORMAT`

    And more in `kwargs` will be parsed as logging.basicConfig do.

    Notes
    -----
    Do not wrap or call `config_logger` indirectly, because it will always
    execute on direct caller's __name__, e.g.:
    >>> # content of foo.py
    >>> def do_config_logger():
            return config_logger()

    >>> # content of bar.py
    >>> from foo import do_config_logger
    >>> l1 = do_config_logger()
    >>> l2 = config_logger()
    >>> print('logger from foo.py: %s, from bar.py: %s' % (l1.name, l2.name))
    logger from foo.py: foo, from bar.py: bar

    See Also
    --------
    logging.basicConfig
    '''
    if isinstance(name, logging.getLoggerClass()):
        logger = name
    else:
        logger = logging.getLogger(name or get_caller_globals(1)['__name__'])
    logger.setLevel(level)
    format = logging.Formatter(format, kwargs.pop('datefmt', None))
    addhdlr = kwargs.pop('addhdlr', True)
    hdlrlevel = kwargs.pop('hdlrlevel', level)
    filename = kwargs.pop('filename', None)
    if filename is not None:
        filename = os.path.abspath(os.path.expanduser(filename))
        filedir = os.path.dirname(filename)
        if not os.path.exists(filedir):
            os.makedirs(filedir)
        hdlr = kwargs.pop('handler', logging.FileHandler)
        hdlr = hdlr(filename, mode=kwargs.pop('filemode', 'a'), **kwargs)
    else:
        hdlr = kwargs.pop('handler', logging.StreamHandler)
        if hdlr is logging.StreamHandler:
            hdlr = hdlr(kwargs.pop('stream', sys.stdout), **kwargs)
        else:
            hdlr = hdlr(**kwargs)
    hdlr.setLevel(hdlrlevel)
    hdlr.setFormatter(format)
    if addhdlr:
        logger.addHandler(hdlr)
    else:
        logger.handlers = [hdlr]
    return logger


class LoggerStream(object):
    '''
    Wrap `logging.Logger` instance into a file-like object.

    Parameters
    ----------
    logger : logging.Logger
        Logger that will be masked to a stream.
    level : int
        Log level :method:`write` will use, default `logging.INFO` (20).
    '''
    __slots__ = ('_logger', '_level', '_string')

    def __init__(self, logger, level=logging.INFO):
        self._logger = logger
        self._oldcaller = logger.findCaller
        logger.findCaller = self.findCaller
        self._level = level
        self._string = StringIO()  # a file must can be read

    def findCaller(self, rv=("(unknown file)", 0, "(unknown function)")):
        '''
        Some little hacks here to ensure LoggerStream wrapped instance
        log with correct lineno, filename and funcname.
        '''
        f = inspect.currentframe()
        srcfiles = [
            logging._srcfile,
            os.path.abspath(__file__).replace('.pyc', '.py')
        ]
        while hasattr(f, "f_code"):
            co = f.f_code
            fn = os.path.normcase(os.path.abspath(co.co_filename))
            if fn not in srcfiles:
                rv = (co.co_filename, f.f_lineno, co.co_name)
                break
            f = f.f_back
        return rv

    def __getattr__(self, attr):
        try:
            return getattr(self._logger, attr)
        except AttributeError:
            return getattr(self._string, attr)

    def __setattr__(self, attr, value):
        if attr in LoggerStream.__slots__:
            object.__setattr__(self, attr, value)
        else:
            setattr(self._logger, attr, value)

    def __delattr__(self, attr):
        delattr(self._logger, attr)

    def write(self, msg):
        self._logger.log(self._level, msg.strip())
        self._string.write(msg + '\n')

    def writelines(self, lines):
        for line in lines:
            self.write(line)

    @property
    def level(self):
        return self._level

    @level.setter
    def level(self, level):
        self._level = logging._checkLevel(level)


# =============================================================================
# RESOLVING

def find_pylsl_outlets(*args, **kwargs):  # noqa: C901
    '''
    This function is easier to use than func `pylsl.resolve_stream`.

    Examples
    --------
    >>> find_pylsl_outlets()
    >>> # same as pylsl.resolve_streams()
    >>> find_pylsl_outlets(1)
    >>> # same as pylsl.resolve_streams(timeout=1)

    >>> find_pylsl_outlets('type', 'EEG_Data')  # Error
    >>> find_pylsl_outlets("type='EEG_Data'")  # Good
    >>> # same as pylsl.resolve_bypred("type='EEG_Data'")
    >>> find_pylsl_outlets(type='EEG_Data')
    >>> # same as pylsl.resolve_byprop('type', 'EEG_Data')

    If no wanted pylsl stream outlets found, `sys.exit` will be
    called to exit python.
    '''
    timeout = kwargs.pop('timeout', 1)
    NAME = '[Find Pylsl Outlets] '
    if not args:
        if kwargs:
            stream_list = []
        else:
            stream_list = pylsl.resolve_streams(timeout)
    elif isinstance(args[0], (int, float)):
        timeout = args[0]
        stream_list = pylsl.resolve_streams(timeout)
    elif isinstance(args[0], str):
        stream_list = pylsl.resolve_bypred(args[0], 0, timeout)
    else:
        stream_list = []
    for key in set(kwargs).intersection({
            'name', 'type', 'channel_count', 'nominal_srate',
            'channel_format', 'source_id'}):
        stream_list += pylsl.resolve_byprop(key, kwargs[key], 0, timeout)
    if len(stream_list) == 0:
        if kwargs.get('exit', True):
            sys.exit(NAME + 'No stream available! Abort.')
        return []
    elif len(stream_list) == 1:
        stream = stream_list[0]
    else:
        dv = [stream.name() for stream in stream_list]
        ds = [stream.type() for stream in stream_list]
        prompt = (
            '{}Please choose one from all available streams:\n    ' +
            '\n    '.join(['%d %s - %s' % (i, j, k)
                           for i, (j, k) in enumerate(zip(dv, ds))]) +
            '\nstream num(default 0): ').format(NAME)
        answer = {str(i): stream for i, stream in enumerate(stream_list)}
        answer[''] = stream_list[0]
        try:
            stream = check_input(prompt, answer, timeout)
        except KeyboardInterrupt:
            stream = None
    if not stream:
        if kwargs.get('exit', True):
            sys.exit(NAME + 'No stream available! Abort.')
        return []
    logger.info(
        '{}Select stream `{}` -- {} channel {} {} data from {} on server {}'
        .format(
            NAME, stream.name(), stream.channel_count(), stream.type(),
            stream.channel_format(), stream.source_id(), stream.hostname()))
    return stream


def find_serial_ports(timeout=3):
    '''
    This fucntion will guide user to choose one port. Wait `timeout` seconds
    for devices to be detected. If no ports found, return None
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
        sys.exit(NAME + 'No serail port available! Abort.')
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
            sys.exit(NAME + 'No divice available! Abort.')
    if not device:
        sys.exit(NAME + 'No divice available! Abort.')
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


def get_self_ip_addr(default='127.0.0.1'):
    '''
    UDP socket can connect to any hosts even they are unreachable, or
    broadcast data even there are no listeners. Here create an UDP socket
    and connect to '8.8.8.8:80' google public DNS server to resolve self
    IP address.
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


@mkuserdir
def get_label_dict(username):
    '''
    Count all saved data files under user's directory that match a pattern:
    ${DATADIR}/${username}/${label}-${num}.${suffix}

    Returns
    -------
    out : tuple
        label_dict and summary string

    Examples
    --------
    >>> get_label_dict('test')
    ({
         'left': 16,
         'right': 21,
         'thumb_cross': 10,
    }, 'There are 3 actions with 47 records.\\n')
    '''
    label_dict = {}
    name_dict = {}
    for filename in sorted(os.listdir(os.path.join(DATADIR, username))):
        fn, ext = os.path.splitext(filename)
        if ext == '.gz':
            fn, ext = os.path.splitext(fn)
        if ext not in ['.mat', '.fif', '.csv'] or '-' not in fn:
            continue
        label, num = fn.split('-')
        if label in label_dict:
            label_dict[label] += 1
            name_dict[label].append(filename)
        else:
            label_dict[label] = 1
            name_dict[label] = [filename]

    # construct a neat summary report
    summary = '\nThere are {} actions with {} data recorded.'.format(
        len(label_dict), sum(label_dict.values()))
    if label_dict:
        maxname = max([len(_) for _ in label_dict]) + 8
        summary += (
            '\n  * ' + '\n  * '.join([k.ljust(maxname) + str(label_dict[k]) +
                                      '\n    ' + '\n    '.join(name_dict[k])
                                      for k in label_dict]))
    return label_dict, summary


def get_boolean(v, table=BOOLEAN_TABLE):
    '''convert string to boolean'''
    t = str(v).title()
    if t not in table:
        raise ValueError('Invalid boolean value: {}'.format(v))
    return table[t]


def load_configs(*fns):
    '''
    Configurations priority(from low to high):
    - On Unix-like system:
        project config file: "${EmBCI}/files/service/embci.conf"
         system config file: "/etc/embci/embci.conf"
           user config file: "~/.embci/embci.conf"
    - On Windows system:
        project config file: "${EmBCI}/files/service/embci.conf"
         system config file: "${APPDATA}/embci.conf"
           user config file: "${USERPROFILE}/.embci/embci.conf"
    '''
    fns = ensure_unicode(*(fns or DEFAULT_CONFIG_FILES))
    # fns: [] | ufilename | [ufilename, ...]
    if not isinstance(fns, list):
        fns = [fns]
    config = configparser.ConfigParser()
    config.optionxform = str
    loaded = config.read(fns)
    for fn in fns:
        if fn not in loaded:
            raise IOError("Cannot load config file: '%s'" % fn)
    # for python2 & 3 compatible, use config.items and config.sections
    return {section: dict(config.items(section))
            for section in config.sections()}


def get_config(key, default=None, section=None, fn=None):
    '''
    Get configurations from environment variables or config files.
    EmBCI use `INI-Style <https://en.wikipedia.org/wiki/INI_file>`_
    configuration files with extention of `.conf`.

    Parameters
    ----------
    key : str
    default : str | None, optional
        Return `default` if key is not in configuration files or environ,
    section : str | None, optional
        Section to search for key. Default None, search for each section.

    See Also
    --------
    `configparser <https://en.wikipedia.org/wiki/INI_file>`_
    '''
    if key in os.environ:
        return os.getenv(key)
    if key in dir(embci.configs):
        return getattr(embci.configs, key)
    configs = load_configs(fn) if fn else load_configs()
    if section is not None and key in configs.get(section, {}):
        return configs[section][key]
    for d in configs.values():
        if key in d:
            return d[key]
    return default


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
        warnings.warn(RuntimeWarning(
            'Only CPython implement stack frame supports.'))
        return globals()
    for i in range(depth + 1):
        if f.f_back is None:
            warnings.warn(RuntimeWarning(
                'No outer frame of {} at depth {}!'.format(f, i)))
            return f.f_globals
        f = f.f_back
    return f.f_globals


if hasattr(inspect, 'signature'):
    def get_func_args(func, kwonlywarn=True):  # noqa E301
        # In python3.5+ inspect.getargspec & inspect.getfullargspec are
        # deprecated. inspect.signature is suggested to use, but it needs
        # some extra steps to fetch our wanted info
        args, defaults = [], []
        for name, param in inspect.signature(func).parameters:
            if kwonlywarn and param.kind is param.kwonlyargs:
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
    def get_func_args(func, kwonlywarn=True):  # noqa E301
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
    def get_func_args(func):  # noqa E301
        # python2.7-3.0 use inspect.getargspec
        argspec = inspect.getargspec(func)
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

# THE END
