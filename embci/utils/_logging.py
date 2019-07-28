#!/usr/bin/env python
# coding=utf-8
#
# File: EmBCI/embci/utils/_logging.py
# Author: Hankso
# Webpage: https://github.com/hankso
# Time: Sat 27 Jul 2019 14:25:06 CST

# built-in
import os
import sys
import inspect
import logging

from six.moves import StringIO

from ..configs import LOGFORMAT
from ._resolve import get_caller_globals


# =============================================================================
# Wrapping default logging.Logger with a new `findCaller`

class Logger(logging.Logger):
    __doc__ = logging.Logger.__doc__
    __srcfiles__ = [
        logging._srcfile,
        os.path.abspath(__file__).replace('.pyc', '.py'),
    ]

    def findCaller(self, rv=("(unknown file)", 0, "(unknown function)")):
        '''
        Some little hacks here to ensure LoggerStream wrapped instance
        log with correct lineno, filename and funcname.
        '''
        f = inspect.currentframe()
        while hasattr(f, "f_code"):
            co = f.f_code
            fn = os.path.normcase(os.path.abspath(co.co_filename))
            if fn not in self.__srcfiles__:
                rv = (co.co_filename, f.f_lineno, co.co_name)
                break
            f = f.f_back
        return rv


logging.Logger = Logger
logging.setLoggerClass(Logger)


# =============================================================================
# A useful logging.Logger configuration entry

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
    hdlrlevel = kwargs.pop('hdlrlevel', None)
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
    hdlr.setLevel(hdlrlevel or hdlr.level)
    hdlr.setFormatter(format)
    if addhdlr:
        logger.addHandler(hdlr)
    else:
        logger.handlers = [hdlr]
    return logger


# =============================================================================
# Some logging utilities

class LoggerStream(object):
    '''
    Wrapping `logging.Logger` instance into a file-like object.

    Parameters
    ----------
    logger : logging.Logger
        Logger that will be masked to a stream.
    level : int
        Log level that :method:`write` will use, default logger's level.
    '''
    __slots__ = ('_logger', '_level', '_string')

    def __init__(self, logger, level=None):
        if level is None:
            level = logger.level
        self._level = logging._checkLevel(level)
        self._logger = logger
        self._string = StringIO()  # a file must can be read

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


class TempLogLevel(object):
    '''Context manager to temporarily change log level and auto set back.'''
    def __init__(self, level):
        self._logger = logging.getLogger(get_caller_globals(1)['__name__'])
        self._old_level = self._logger.level
        self._level = logging._checkLevel(level)

    def __enter__(self):
        self._logger.setLevel(self._level)
        return self._logger

    def __exit__(self, *a):
        self._logger.setLevel(self._old_level)


# THE END
