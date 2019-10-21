#!/usr/bin/env python3
# coding=utf-8
#
# File: EmBCI/embci/utils/_looptask.py
# Authors: Hank <hankso1106@gmail.com>
# Create: 2019-09-24 12:52:14

# built-in
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
import re
import time
import atexit
import functools
import threading
import traceback

from . import logger, ensure_unicode, get_boolean

__all__ = [
    'LoopTaskMixin', 'LoopTaskInThread', 'SkipIteration',
    'find_task_by_name', 'find_tasks_by_class'
]

_tasks = []


def _ensure_tasks_closed():
    '''
    In case of exiting Python without calling `LoopTaskMixin.close`, this
    function will be called by `atexit`. NOT for runtime usage.
    '''
    while _tasks:
        try:
            task = _tasks.pop()
            if task.started:
                logger.debug('close %s at exit' % task)
                task.close()
        except Exception:
            pass
            traceback.print_exc()
atexit.register(_ensure_tasks_closed)                              # noqa: E305


def find_task_by_name(name, cls=None, arr=None):
    if cls is not None:
        arr = find_tasks_by_class(cls, arr)
    arr = arr if arr is not None else _tasks
    maybe = set()
    for task in arr:
        for attr in ['name', '__name__']:
            if not hasattr(task, attr):
                continue
            n = getattr(task, attr)
            if n == name:
                return task
            elif name in n:
                maybe.add(task)
    return list(maybe)[0] if maybe else None


def find_tasks_by_class(cls, arr=None):
    arr = arr if arr is not None else _tasks
    return list(filter(lambda task: issubclass(task.__class__, cls), arr))


class SkipIteration(Exception):
    '''Exception used inside LoopTask to skip current iteration/loop.'''
    pass


class LoopTaskMixin(object):
    '''
    Establish a task to execute a function looply. Stream control methods are
    integrated, such as `start`, `pause`, `resume`, `close`, etc.

    Attributes
    ----------
    __flag_pause__ : Event
    __flag_close__ : Event
    __started__ : bool
        Read-only attribute by `self.started`
    __status__ : bytes
        Read-only attribute by `self.status`

    Examples
    --------
    >>> class Clock(LoopTaskMixin):
    ...     def loop_before(self):  # optional function
    ...         print('this is a simple clock')
    ...     def loop_after(self):  # optional function
    ...         print('clock end')
    ...     def loop_display_time(self, name):
    ...         print('{}: {}'.format(name, time.time()))
    ...         time.sleep(1)
    ...     def start(self):
    ...         if LoopTaskMixin.start(self) is False:
    ...             return 'this clock is already started'
    ...         self.loop(
    ...             func=self.loop_display_time, args=('MyClock', ),
    ...             before=self.loop_before, after=self.loop_after)
    >>> c = Clock()
    >>> c.start()
    this is a simple clock
    MyClock: 1556458048.83
    MyClock: 1556458049.83
    MyClock: 1556458050.83
    ^C (KeyboardInterrupt Ctrl-C)
    clock end

    Notes
    -----
    A mixin class should not be used directly. The `LoopTaskMixin.__init__`
    is used primarily for testing. But if you need to subclass this Mixin and
    use your own __init__, remember to call `LoopTaskMixin.__init__(self)` or
    `super(YOUR_CLASS, self).__init__()`. Or simply config the attributes
    correctly.

    See Also
    --------
    embci.utils.LoopTaskInThread
    embci.io.readers.BaseReader
    '''
    __name_pattern__ = re.compile(r'^LoopTask_(\d+)')

    def __init__(self):
        self.__flag_pause__ = threading.Event()
        self.__flag_close__ = threading.Event()
        self.__started__ = False
        self.__status__ = b'closed'  # use bytes for c_char_p compatiable

    def __new__(cls, *a, **k):
        obj = object.__new__(cls)
        ids = {
            int(cls.__name_pattern__.findall(task.__name__)[0])
            for task in _tasks if cls.__name_pattern__.match(task.__name__)
        }
        obj.__name__ = 'LoopTask_{:d}'.format(
            list(set(range(len(ids) + 1)).difference(ids))[0])
        _tasks.append(obj)
        return obj

    @property
    def name(self):
        return self.__name__

    @property
    def status(self):
        '''`status` of the loopTask is read-only'''
        return ensure_unicode(self.__status__)

    @property
    def started(self):
        '''`started` of the loopTask is read-only'''
        return self.__started__

    def start(self, *a, **k):
        if self.started:
            if self.status == 'paused':
                self.resume()
            return False
        self.__flag_pause__.set()
        self.__flag_close__.clear()
        self.__started__ = True
        self.__status__ = b'started'
        self.start_time = time.time()
        try:
            self.hook_before()
        except Exception:
            logger.error(traceback.format_exc())
            self.close()
            return False
        return True

    def close(self):
        if not self.started:
            return False
        try:
            self.hook_after()
        except Exception:
            logger.error(traceback.format_exc())
        self.__flag_close__.set()
        self.__flag_pause__.clear()
        # you can restart this task now
        self.__started__ = False
        self.__status__ = b'closed'
        return True

    def restart(self, *args, **kwargs):
        if self.started:
            self.close()
        return self.start(*args, **kwargs)

    def pause(self):
        if not self.started or self.status == 'paused':
            return False
        self.__flag_pause__.clear()
        self.__status__ = b'paused'
        return True

    def resume(self):
        if self.status != 'paused':
            return False
        self.__flag_pause__.set()
        self.__status__ = b'resumed'
        return True

    def hook_before(self):
        '''Hook function executed outside self.loop after start.'''
        pass

    def hook_after(self):
        '''Hook function executed outside self.loop before close.'''
        pass

    def loop_before(self):
        '''Hook function executed inside self.loop before loop task.'''
        pass

    def loop_after(self):
        '''Hook function executed inside self.loop after loop task.'''
        pass

    def loop(self, func, args=(), kwargs={}):
        try:
            assert callable(func), 'Loop function `%s` is not callable' % func
            self.loop_before()
        except Exception:
            logger.error(traceback.format_exc())
            return self.close()
        try:
            while not self.__flag_close__.is_set():
                if self.__flag_pause__.wait(2):
                    try:
                        func(*args, **kwargs)
                    except SkipIteration as e:
                        logger.warning(e)
                self.loop_actions()
        except KeyboardInterrupt:
            logger.info('KeyboardInterrupt detected.')
        except Exception:
            logger.error(traceback.format_exc())
        try:
            self.loop_after()
        except Exception:
            logger.error(traceback.format_exc())
        if self.started:
            self.close()

    def loop_actions(self):
        '''
        Hook function called inside self.loop in each iteration. May be
        overridden by a subclass / Mixin to implement any code that needs
        to be run even SkipIteration error is raised.
        '''
        pass


class LoopTaskInThread(threading.Thread, LoopTaskMixin):
    '''
    Execute a function looply in a Thread, which can be paused, resumed, even
    restarted. This is an example usage of class `embci.utils.LoopTaskMixin`.

    Examples
    --------
    >>> task = LoopTaskInThread(lambda: time.sleep(1) or print(time.time()))
    >>> repr(task)
    <LoopTaskInThread(LoopFunc: <lambda>, initial daemon 139679343671040)>
    >>> task.start()
    True
    1556458048.83
    1556458049.83
    1556458050.83
    >>> task.pause(), task.pause()
    (True, False)  # can not pause an already paused task
    >>> task.close()

    Notes
    -----
    KeyboardInterrupt is raised when SIGINT(2) is detected in default signal
    handler. But this only happens in the main thread, according to Python doc
    on module `signal`:
        Python signal handlers are always executed in the main Python thread,
        even if the signal was received in another thread. This means that
        signals can’t be used as a means of inter-thread communication.

    That means one can NOT stop a LoopTaskInThread by Ctrl-C when it is set as
    non-daemon no matter whether the main thread has stopped or not. It even
    can't be closed by LoopTask GC :func:`_ensure_tasks_closed` because python
    will never reach the end point to call exit functions. **So you MUST
    remember to close(stop) the loop task manually.**

    See Also
    --------
    embci.utils.LoopTaskMixin
    embci.io.readers.BaseReader
    '''

    def __init__(self, func, before=None, after=None, args=(), kwargs={}, **k):
        '''
        Parameters
        ----------
        func : callable object
            The function to be looply executed. But note that the return
            value of function will be omitted.
        before : callable object, optional
            Hook function executed before loop task.
        after : callable object, optional
            Hook function executed after loop task.
        args : tuple, optional
            Positional arguemnts for invocation of loop function.
        kwargs : dict, optional
            Keyword arguments for loop function invocation.
        name : str, optional
            User specified task name. Defaults to function's name.
        daemon : bool, optional
            Whether to mark the task thread as daemonic.
        '''
        if callable(before):
            self.loop_before = before
        if callable(after):
            self.loop_after = after
        self._floop_ = func
        self._fargs_, self._fkwargs_ = args, kwargs
        k.setdefault('name', 'LoopFunc(%s)' % getattr(func, '__name__', None))
        k.setdefault('daemon', True)
        self._init_thread_ = functools.partial(self._init_thread_, **k)
        self._init_thread_()
        LoopTaskMixin.__init__(self)

    def _init_thread_(self, daemon, **kwargs):
        '''Call this function to re-init thread'''
        threading.Thread.__init__(self, **kwargs)
        self.daemon = get_boolean(daemon)  # python 2 & 3 compatiable
        self._thread_inited_ = True

    def __repr__(self):
        extra = ''
        if self.daemon:
            extra += ' daemon'
        if self.ident is not None:
            extra += ' %s' % self.ident
        return '<{name} {status}{extra}>'.format(
            name=self.name, status=self.status, extra=extra)

    def start(self):
        return LoopTaskMixin.start(self)

    def hook_before(self):
        if not self._thread_inited_:
            self._init_thread_()
        threading.Thread.start(self)

    def hook_after(self):
        self._thread_inited_ = False

    def run(self):
        self.loop(self._floop_, self._fargs_, self._fkwargs_)
        logger.debug('{} stopped.'.format(self))


# THE END
