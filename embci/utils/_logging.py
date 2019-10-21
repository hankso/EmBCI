#!/usr/bin/env python3
# coding=utf-8
#
# File: EmBCI/embci/utils/_logging.py
# Authors: Hank <hankso1106@gmail.com>
# Create: 2019-07-27 14:25:06

# built-in
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
import os
import sys
import logging
import traceback
from logging import Logger, Formatter

# requirements.txt: necessary: six
from six import PY2, PY3
from six.moves import StringIO

from ..configs import LOGFORMAT, DATEFORMAT
from ..constants import TERMINAL_COLOR2VALUE
from ._resolve import get_caller_globals
from . import ensure_unicode, NameSpace

__all__ = ['EmBCILogger', 'LoggerStream', 'TempLogLevel', 'config_logger']


# =============================================================================
# Wrapping default logging.Logger with a new `findCaller`

class EmBCILogger(Logger):
    __doc__ = Logger.__doc__ + '\nPython 2 & 3 compatiable.'
    __srcfiles__ = [
        logging._srcfile,
        os.path.abspath(__file__).replace('.pyc', '.py'),
    ]

    def findCaller(self, stack_info=False):
        '''
        Some little hacks here to ensure LoggerStream wrapped instance
        log with correct lineno, filename and funcname. Support py2 & 3.
        '''
        f = sys._getframe(3) if hasattr(sys, '_getframe') else None
        rv = ('(unknown file)', 0, '(unknown function)', None)
        while hasattr(f, "f_code"):
            co = f.f_code
            fn = os.path.normcase(os.path.abspath(co.co_filename))
            if fn in self.__srcfiles__:
                f = f.f_back
                continue
            if PY2:
                rv = (co.co_filename, f.f_lineno, co.co_name)
            elif PY3 and not stack_info:
                rv = (co.co_filename, f.f_lineno, co.co_name, None)
            else:
                self.__stackio__ = getattr(self, '__stackio__', StringIO())
                self.__stackio__.write(u'Stack (most recent call last):\n')
                traceback.print_stack(f, file=self.__stackio__)
                sinfo = self.__stackio__.getvalue().rstrip('\n')
                self.__stackio__.truncate(0)
                self.__stackio__.seek(0)
                rv = (co.co_filename, f.f_lineno, co.co_name, sinfo)
            break
        return rv


#  logging.setLoggerClass(EmBCILogger)


class EmBCIFormatter(Formatter):
    '''
    Python 2 & 3 compatiable with colorful output support.
    Python 2 currently support %-formatting and str.format.
    '''
    __doc__ += Formatter.__doc__

    LEVEL2COLOR = {
        logging.DEBUG:    'white',
        logging.INFO:     'yellow',
        logging.WARNING:  'orange',
        logging.ERROR:    'bb-red',
        logging.CRITICAL: 'red'
    }

    def __init__(self, fmt=None, datefmt=DATEFORMAT, style='{', useColor=True):
        if PY2:
            if fmt is None:
                fmt, style = '{message}', '{'
            if style not in '%{':
                raise ValueError('Style must be one of: `%`, `{`')
            self._style = style
            Formatter.__init__(self, ensure_unicode(fmt), datefmt)
        else:
            Formatter.__init__(self, fmt, datefmt, style)
        self._useColor = useColor
        if self._useColor:
            if 'start' not in self._fmt:
                self._fmt = '{start}' + self._fmt
            if 'reset' not in self._fmt:
                self._fmt += '{reset}'

    def usesTime(self):
        if PY2:
            return 'asctime' in self._fmt
        else:
            return self._style.usesTime()

    _robj = NameSpace()

    def formatMessage(self, record):
        self._robj.__dict__.clear()
        self._robj.__dict__.update(record.__dict__)
        if self._useColor:
            c = self.LEVEL2COLOR.get(record.levelno, 'white')
            self._robj.start = TERMINAL_COLOR2VALUE[c]
            self._robj.__dict__.update(TERMINAL_COLOR2VALUE)
        if PY2:
            self._robj.name = ensure_unicode(self._robj.name)
            if self._style == '%':
                return self._fmt % self._robj.__dict__
            else:
                return self._fmt.format(**self._robj.__dict__)
        else:
            return self._style.format(self._robj)

    def format(self, record):
        record.message = record.getMessage()
        if self.usesTime():
            record.asctime = self.formatTime(record, self.datefmt)
        s = self.formatMessage(record)
        if record.exc_info and not record.exc_text:
            record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            s = s.rstrip('\n') + '\n' + ensure_unicode(record.exc_text)
        if getattr(record, 'stack_info', None):
            s = s.rstrip('\n') + '\n' + record.stack_info
        return s


# =============================================================================
# A useful Logger configuration entry

def config_logger(name=None, level=logging.INFO, format=LOGFORMAT, **kwargs):
    '''
    Create / config a `Logger` with current namespace's `__name__`.

    Parameters
    ----------
    name : str or instance of Logger, optional
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
    if isinstance(name, (type('string'), type(None))):
        name = name or get_caller_globals(1).get('__name__')
        tmp = Logger.manager.loggerClass
        Logger.manager.setLoggerClass(EmBCILogger)
        logger = logging.getLogger(name)
        Logger.manager.loggerClass = tmp
    elif isinstance(name, Logger):
        logger = name
    else:
        raise TypeError('Invalid name of logger: {}'.format(name))

    logger.setLevel(level)

    datefmt   = kwargs.pop('datefmt', DATEFORMAT)
    style     = kwargs.pop('style', '{')
    addhdlr   = kwargs.pop('addhdlr', True)
    hdlrlevel = kwargs.pop('hdlrlevel', None)
    filename  = kwargs.pop('filename', None)

    if filename is not None:
        filename = os.path.abspath(os.path.expanduser(filename))
        filedir = os.path.dirname(filename)
        if not os.path.exists(filedir):
            os.makedirs(filedir, 0o775)
        hdlr = kwargs.pop('handler', logging.FileHandler)
        hdlr = hdlr(filename, mode=kwargs.pop('filemode', 'a'), **kwargs)
    else:
        hdlr = kwargs.pop('handler', logging.StreamHandler)
        if hdlr is logging.StreamHandler:
            hdlr = hdlr(kwargs.pop('stream', sys.stdout), **kwargs)
        else:
            hdlr = hdlr(**kwargs)
    hdlr.setLevel(hdlrlevel or hdlr.level)

    formatter = EmBCIFormatter(format, datefmt, style, not filename)
    hdlr.setFormatter(formatter)
    if addhdlr:
        logger.addHandler(hdlr)
    else:
        logger.handlers = [hdlr]
    return logger


# =============================================================================
# Some logging utilities

class LoggerStream(object):
    '''
    Wrapping `Logger` instance into a file-like object.

    Parameters
    ----------
    logger : instance of Logger
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
    '''
    Context manager to temporarily change log level and auto set back.

    Parameters
    ----------
    logger : instance of Logger
        Logger whose level will be temporarily changed.
    level : int | str
        Log level that logging.Logger accept. Default 'INFO' (20).

    Examples
    --------
    >>> logger = embci.utils.config_logger(level='INFO')
    >>> with TempLogLevel(logger, 'WARNING'):
    ...     logger.info('there will be no info')
    ...     logger.warning('logger is set to warning level')
    logger is set to warning level

    With no logger specified, __name__ of current frame will be used to
    resolve the logger.
    >>> print(globals()['__name__'])
    embci.utils._logging
    >>> with TempLogLevel(level='DEBUG') as logger:
    ...     logger.info('logger level is set to DEBUG, so this message exist')
    ...     print(logger.name, logger.parent.name, logger.parent.parent.name)
    logger level is set DEBUG, so this message exist
    ('_logging', 'utils', 'embci')

    Also, you can simply input log level without keyword:
    >>> TempLogLevel('DEBUG')._level == TempLogLevel(level='DEBUG')._level
    True
    '''
    __slots__ = ('_logger', '_level')

    def __init__(self, logger=None, level='INFO'):
        if not isinstance(logger, Logger):
            level, logger = logger, None
        self._logger = logger or logging.getLogger(
            get_caller_globals(1)['__name__'])
        self._level = logging._checkLevel(level)
        if self._level == self._logger.level:
            self._level ^= self._level
        else:
            self._level ^= self._logger.level

    def __enter__(self):
        self._logger.setLevel(self._level ^ self._logger.level)
        return self._logger

    def __exit__(self, *a):
        self._logger.setLevel(self._level ^ self._logger.level)


# THE END
