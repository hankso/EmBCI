#!/usr/bin/env python3
# coding=utf-8
#
# File: apps/recorder/base.py
# Authors: Hank <hankso1106@gmail.com>
# Create: 2019-04-29 18:27:21

'''`embci.apps.recorder.Recorder` is defined in this source file.'''

# built-in
import time
import pydoc
import warnings
import traceback
import threading

# requirements.txt: network: bottle
# requirements.txt: data: numpy
import bottle
import numpy as np

from embci.io import (
    create_data_dict, valid_name_datafile,
    save_trials, save_chunks
)
from embci.utils import LoopTaskInThread, Event, find_task_by_name

from . import logger


# =============================================================================
# Recorder[s] & management

class Recorder(LoopTaskInThread):
    '''See more at embci.apps.recorder.__doc__'''

    def __init__(self, reader, username=None, event_merge=True, chunk=True,
                 buffer_size=10*2**20, *a, **k):
        '''
        Parameters
        ----------
        reader : Reader
            Instance of embci.io.readers representing a data stream.
        username : str, optional
            All saved data will be under ${DIR_DATA}/${username}
        event_merge : bool, optional
            Whether to merge events into buffered data as an `Event Channel`
            when saving data or save events seperately. Default False.
        data_chunk : bool | int, optional
            Whether to buffer a chunk of data or one sample/point of data
            each time. Positive integer value indicates number of chunks.
            Default True (one chunk).
        buffer_size : int, optional
            Data buffer size in Bytes. Recorder will auto-save data into
            file when it exceeds this value. Default 10MB.
        '''
        self.reader        = reader
        self._username     = username
        self._buffer_event = []
        self._buffer_data  = []
        self._data_chunk   = 0
        self._data_lock    = threading.Lock()
        self._time_correct = reader.start_time

        super(Recorder, self).__init__(self._recording, daemon=True)
        self.name          = 'Recorder_' + reader.name
        self.chunk         = chunk
        self.buffer_size   = buffer_size
        self.event_merge   = event_merge
        self.cmd(*a, **k)

    def start(self):
        '''Start recorder thread.'''
        if not super(Recorder, self).start():
            return False
        logger.debug('Recorder started on {}.'.format(self.reader))
        if self.username is None:
            self.pause()
            logger.debug('Auto-paused for none username.')
        return True

    def close(self):
        '''Close/stop recorder.'''
        if not super(Recorder, self).close():
            return False
        self.save()
        logger.debug('Recorder %s closed' % self.name)
        return True

    def restart(self):
        '''`restart` is not allowed on recorder, use `pause` instead!'''
        warnings.warn(self.restart.__doc__)

    def pause(self):
        '''Paused recorder will do nothing but it's still alive.'''
        if not super(Recorder, self).pause():
            return False
        if self.chunk and self.username:
            logger.debug('Recorder %s waiting for final chunk' % self.name)
            time.sleep(self.reader.sample_time)
        return True

    def resume(self):
        '''Only paused recorder can be resumed. Otherwise, return False.'''
        if self.username is None:
            return False
        return super(Recorder, self).resume()

    def clear(self):
        '''Clear all buffer of recorder.'''
        del self._buffer_data[:]
        del self._buffer_event[:]

    def is_recording(self):
        '''Return whether recorder is recording.'''
        return (
            self.reader.is_streaming()
            and self.started
            and self.status != 'paused'
        )

    @property
    def buffer_length(self):
        return len(self._buffer_data)

    @property
    def buffer_nbytes(self):
        if self.buffer_length:
            return self._buffer_data[0].nbytes * self.buffer_length
        return 0

    @property
    def event(self):
        if len(self._buffer_event):
            return self._buffer_event[-1]
        return (0, 0)

    @event.setter
    def event(self, e):
        if not isinstance(e, int):
            e = Event.check_event(e)
        if not self.is_recording():
            logger.warning('Add event when not recording')
        self._buffer_event.append((e, time.time() - self._time_correct))
        logger.info('Add event {0} at {1}'.format(*self.event))

    @property
    def username(self):
        return self._username

    @username.setter
    def username(self, name):
        if name == self._username:
            return
        old = self.status not in ['paused', 'closed']
        if old:
            self.pause()
        if self._username is not None:
            self.save()
        else:
            self.clear()
        _, name = valid_name_datafile(str(name), checkname=True)
        if name.title() in ['None', '-', '_', '']:
            self._username = None
            logger.info('username cleared, recorder paused')
        else:
            self._username = name
            logger.info('username set to {}'.format(name))
            if old:
                self.resume()
        self._reset_datafile()

    @property
    def chunk(self):
        return self._data_chunk

    @chunk.setter
    def chunk(self, v):
        v = int(v)
        if self.chunk == v:
            return
        old = self.status not in ['paused', 'closed']
        if old:
            self.pause()
        self.save()
        self._data_chunk = v
        if old:
            self.resume()
        self._reset_datafile()

    def _reset_datafile(self):
        if not self.username:
            return
        if hasattr(self, '_data_fobj'):
            self._data_fobj.close()
        if self.chunk:
            fn = valid_name_datafile(self.username, self.name)[0]
            self._data_fobj = open(fn + '.mat', 'a+b')

    def _data_get(self):
        # num_channel x time_series
        if self._buffer_data:
            data = np.concatenate(self._buffer_data, axis=-1)
            del self._buffer_data[:]
        else:
            data = np.array([[]])
        return data

    def _event_get(self, ts=None):
        if ts is None:
            # 2 x n_event: CH1 event code; CH2 event timestamp
            events = np.array([
                [int(event), t] for event, t in self._buffer_event
            ]).T
        else:
            # 1 x n_times: event code merged according to timestamp
            events = []
            for event, t in self._buffer_event:
                if not (ts[0] <= t <= ts[-1]):
                    logger.warning(
                        'event marked out of timestamp range'
                        '{}, {} in {}-{}'.format(event, t, ts[0], ts[-1])
                    )
                    continue
                index = abs(ts - t).argmin()
                events += [0] * (index - len(events)) + [int(event)]
                if len(events) == len(ts):
                    break
                elif len(events) > len(ts):
                    logger.error('this will never happen (theoretically)')
                    logger.error('\n{} {}'.format(events, ts))
                    raise RuntimeError
            events = np.pad(events, (0, len(ts) - len(events)), 'constant')
        del self._buffer_event[:]
        return events

    @property
    def data_all(self):
        '''Get all data and events from buffer.'''
        try:
            data = self._data_get()
            if not self.event_merge and self.chunk:
                return {'raw': data, 'event': self._event_get()}
            else:
                events = self._event_get(data[-1])
                data = np.concatenate((data[:-1], events[None, :], data[-1:]))
                return {'raw': data}
        except Exception:
            logger.error(traceback.format_exc())
            self.clear()
            return {}

    def save(self):
        '''Flush data from buffer to file according to chunk.'''
        with self._data_lock:  # avoid multi-call from different thread/process
            if not len(self._buffer_data):
                logger.debug('No data in buffer for user `%s`' % self.username)
                return False
            if self.username is None:
                self.clear()
                return False
            if self.chunk:
                data = self.data_all
                if not data:
                    return False
                save_chunks(self._data_fobj, create_data_dict(
                    data, self.name, sample_rate=self.reader.sample_rate
                ), append=True)
            else:
                logger.warning(
                    'Saving trial data is not suggested, you may want to '
                    'record chunks of data? Set recorder.chunk to '
                    'True or positive integer.'
                )
                data = self.data_all['raw']
                save_trials(self.username, create_data_dict(
                    data, self.name, sample_rate=self.reader.sample_rate))
            return True

    def _recording(self):
        if not self.reader.is_streaming():
            return time.sleep(1)
        if self.chunk:
            for i in range(self.chunk):
                raw = self.reader.data_all
                if not self.is_recording():
                    break
                self._buffer_data.append(raw)
            if self.buffer_nbytes > self.buffer_size:
                self.save()
        else:
            for i in range(5):
                raw = self.reader.data_channel_t.reshape(-1, 1)
                self._buffer_data.append(raw)
        self._time_correct = time.time() - raw[-1, -1]

    def cmd(self, *args, **kwargs):
        '''
        Positional arguments specifies method to be executed with no params,
        or the attribute whose value will be returned. Keyword arguments
        specifies attribute's name and value to be set.
        '''
        for mth in args:
            if not mth:
                continue
            if mth.startswith('_') or not hasattr(self, mth):
                logger.error('Invalid cmd: {}'.format(mth))
                continue
            attr = getattr(self, mth)
            if callable(attr):
                try:
                    rst = attr()
                except Exception:
                    rst = traceback.format_exc()
                logger.debug('Execute method {}: `{}`'.format(mth, rst))
                return rst
            else:
                logger.debug('Attribute value {}: `{}`'.format(mth, attr))
                return attr
        for key, value in kwargs.items():
            if not key:
                continue
            if key.startswith('_') or not hasattr(self, key):
                logger.error('Invalid cmd {}'.format(key))
                continue
            try:
                setattr(self, key, value)
            except Exception:
                logger.error(traceback.format_exc())
            else:
                value = getattr(self, key)
                logger.debug('Attribute value {}: `{}`'.format(key, value))

    def _help_attrs(self):
        return [
            (i, getattr(self, i))
            for i in set(self.__dict__).union(Recorder.__dict__)
            .difference(['cmd', 'data_all']).union(['name', 'ident'])
            if not i.startswith('_')
        ]

    def summary(self):
        '''Display a list of attributes and values of object.'''
        val = []
        for name, attr in self._help_attrs():
            if callable(attr):
                continue
            val.append((name, attr))
        ml = max(map(len, [i[0] for i in val]))
        return '\n'.join(['%s: %s' % (k.ljust(ml), v) for k, v in val])

    def usage(self):
        '''Display a list of brief help on methods of object.'''
        msg = []
        for name, attr in self._help_attrs():
            if not callable(attr):
                continue
            doc = pydoc.getdoc(attr).replace('\n', ' ') or 'Unknown'
            msg.append((name, doc))
        ml = max(map(len, [i[0] for i in msg]))
        return '\n'.join(['%s: %s' % (k.ljust(ml), v) for k, v in msg])

    def help(self):
        '''Show this help message.'''
        msg, val = [], []
        for name, attr in self._help_attrs():
            if callable(attr):
                doc = pydoc.getdoc(attr).replace('\n', ' ') or 'Unknown'
                msg.append((name, doc))
            else:
                val.append((name, attr))
        ml = max(map(len, [i[0] for i in msg + val]))
        return (
            'Help on embci.apps.recorder.base.Recorder:\n' +
            '\n'.join(['%s : %s' % (k.ljust(ml), v) for k, v in msg]) +
            '\n' + '-' * 80 + '\n' +
            '\n'.join(['%s : %s' % (k.ljust(ml), v) for k, v in val])
        )


# =============================================================================
# Network interface

application = rec = bottle.Bottle()


@rec.route('/')
def rec_manager():
    pass


@rec.route('/init')
def rec_init():
    global reader, recorder
    from embci.io import LSLReader
    reader = LSLReader()
    reader.start()
    recorder = Recorder(reader)
    recorder.start()


@rec.route('/update')
def rec_update():
    pass


@rec.route('/<name>')
def rec_command_k(name, **kwargs):
    recorder = find_task_by_name(name, Recorder)
    if recorder is None:
        bottle.abort(400, 'Recorder `%s` does not exist')
    kwargs = kwargs or bottle.request.query


@rec.route('/<name>/<cmd>')
def rec_command_a(name, cmd=None, *args):
    recorder = find_task_by_name(name, Recorder)
    if recorder is None:
        bottle.abort(400, 'Recorder `%s` does not exist')
    args = [cmd or (args and args[0] or '')]


# THE END
