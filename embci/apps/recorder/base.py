#!/usr/bin/env python3
# coding=utf-8
#
# File: apps/recorder/base.py
# Authors: Hank <hankso1106@gmail.com>
# Create: 2019-04-29 18:27:21

'''`embci.apps.recorder.Recorder` is defined in this source file.'''

# built-in
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
import time
import pydoc
import shlex
import traceback
import threading

# requirements.txt: data: numpy
import numpy as np

from embci.io import (
    create_data_dict, validate_datafile,
    save_trials, save_chunks
)
from embci.utils import (
    get_boolean, timestamp,
    LoopTaskInThread, Event, CachedProperty, NameSpace
)

from . import logger

globalvars = NameSpace()


class Recorder(LoopTaskInThread):
    '''See more at embci.apps.recorder.__doc__'''

    def __init__(self, reader, username=None, chunk=True, event_merge=True,
                 buffer_max=7*2**20, *a, **k):
        '''
        Parameters
        ----------
        reader : Reader
            Instance of embci.io.readers representing a data stream.
        username : str, optional
            All saved data will be under ${DIR_DATA}/${username}
        chunk : bool | int, optional
            Whether to buffer a chunk of data or one sample/point of data
            each time. Positive integer value indicates number of chunks.
            Default True (one chunk).
        event_merge : bool, optional
            Whether to merge events into buffered data as an `Event Channel`
            when saving data or save events seperately. Default False.
        buffer_max : int, optional
            Data buffer maximum size in Bytes. Recorder will auto-save data
            into file when it exceeds this value. Default 7MB.
        '''
        self._username     = None
        self._buffer_event = []
        self._buffer_data  = []
        self._buffer_max   = 0
        self._buffer_chunk = 0
        self._event_merge  = False
        self._data_lock    = threading.Lock()
        self._time_correct = reader.start_time
        self._reader       = reader

        super(Recorder, self).__init__(self._recording, daemon=True)

        self.created_at  = timestamp(fmt='%y%m%d%H%M%S')
        self.name        = 'Rec_' + self._reader.name + '_' + self.created_at
        self.username    = username
        self.buffer_max  = buffer_max
        self.event_merge = event_merge
        self.chunk       = chunk

        self.cmd(*a, **k)

    def start(self):
        '''Start recorder thread.'''
        return super(Recorder, self).start()

    def close(self):
        '''Close/stop recorder.'''
        return super(Recorder, self).close()

    def loop_before(self):
        '''Hook function executed after start and before looping.'''
        logger.debug('Recorder %s started on %s.' % (self.name, self._reader))
        self.name = 'Rec_' + self._reader.name + '_' + self.created_at
        if self.username is None:
            self.pause()
            logger.debug('Auto-paused for none username.')
        else:
            logger.debug('Recorder %s waiting for time correction' % self.name)
            time.sleep(10 / self._reader.sample_rate)

    def loop_after(self):
        '''Hook function executed after looping but before close.'''
        self.save()
        if hasattr(self, '_data_fobj'):
            self._data_fobj.close()
        logger.debug('Recorder %s closed.' % self.name)

    def restart(self):
        '''
        Restart is not allowed on recorder, use `pause` instead!
        This function maps to data stream's restart to re-select input source.
        '''
        self._reader.restart()

    def pause(self):
        '''Paused recorder will do nothing but it's still alive.'''
        if not super(Recorder, self).pause():
            return False
        if self.username:
            logger.debug('Recorder %s waiting for final chunk' % self.name)
            if self.chunk:
                time.sleep(self._reader.sample_time * 1.10)
            else:
                time.sleep(self._reader.sample_time * 0.11)
        return True

    def resume(self):
        '''Only paused recorder can be resumed. Otherwise, return False.'''
        if self.username is None:
            return False
        if not super(Recorder, self).resume():
            return False
        logger.debug('Recorder %s waiting for time correction' % self.name)
        time.sleep(10 / self._reader.sample_rate)
        logger.debug('Recorder %s resumed' % self.name)
        return True

    def clear(self):
        '''Clear all buffer of recorder.'''
        del self._buffer_data[:]
        del self._buffer_event[:]

    def is_recording(self):
        '''Return whether recorder is recording.'''
        return (
            self._reader.is_streaming()
            and self.started
            and self.status != 'paused'
            and self.username is not None
        )

    @property
    def stream(self):
        return repr(self._reader)

    @property
    def source(self):
        return self._reader.input_source

    @property
    def buffer_length(self):
        return len(self._buffer_data)

    @property
    def buffer_nbytes(self):
        if self.buffer_length:
            return self._buffer_data[0].nbytes * self.buffer_length
        return 0

    #  @property
    #  def buffer_ratio(self):
    #      return self.buffer_nbytes / self.buffer_max

    @property
    def buffer_max(self):
        return self._buffer_max

    @buffer_max.setter
    def buffer_max(self, v):
        self._buffer_max = int(v)

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
        logger.info('Add event {0} at {1}'.format(*self._buffer_event[-1]))

    @property
    def chunk(self):
        return self._buffer_chunk

    @chunk.setter
    def chunk(self, v):
        v = int(v)
        if self._buffer_chunk == v:
            return
        old = self.status not in ['paused', 'closed']
        if old:
            self.pause()
        self.save()
        self._buffer_chunk = v
        if old:
            self.resume()
        self._reset_datafile()

    @property
    def event_merge(self):
        return self._event_merge

    @event_merge.setter
    def event_merge(self, v):
        self._event_merge = get_boolean(v)

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
        _, name = validate_datafile(str(name), checkname=True)
        if name.title() in ['None', '-', '_', '']:
            self._username = None
            logger.info('username cleared, recorder paused')
        else:
            self._username = name
            logger.info('username set to {}'.format(name))
            if old:
                self.resume()
        self._reset_datafile()

    def _reset_datafile(self):
        if not self.username:
            return
        if hasattr(self, '_data_fobj'):
            self._data_fobj.close()
        if self.chunk:
            fn = validate_datafile(self.username, self.name)[0]
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
            while self._buffer_event:
                event, t = self._buffer_event.pop(0)
                if not (ts[0] <= t <= ts[-1]):
                    logger.warning('event marked out of range ({} {}) in {}-{}'
                                   .format(event, t, ts[0], ts[-1]))
                    continue
                index = abs(ts - t).argmin()
                events += [0] * (index - len(events)) + [int(event)]
                if len(events) == len(ts):
                    self._buffer_event and logger.warning(
                        'event ignored: {}'.format(self._buffer_event)
                    )
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
            assert data.size
            if not self.event_merge and self.chunk:
                return {'raw': data, 'event': self._event_get(), 'key': 'raw'}
            else:
                events = self._event_get(data[-1])
                data = np.concatenate((data[:-1], events[None, :], data[-1:]))
                return {'raw': data, 'key': 'raw'}
        except AssertionError:
            pass
        except Exception:
            logger.error(traceback.format_exc())
        self.clear()
        return None

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
                    data, self.name, sample_rate=self._reader.sample_rate
                ), append=True)
            else:
                logger.warning(
                    'Saving trial data is not suggested, you may want to '
                    'record chunks of data? Set recorder.chunk to '
                    'True or positive integer.'
                )
                data = self.data_all['raw']
                save_trials(self.username, create_data_dict(
                    data, self.name, sample_rate=self._reader.sample_rate))
            return True

    def _recording(self):
        if not self.is_recording():
            return time.sleep(0.5)
        raw = self._reader.data_channel_t.reshape(-1, 1)
        t1 = raw[-1, 0]
        self._time_correct = time.time() - t1
        if self.chunk:
            for i in range(self.chunk):
                raw = self._reader.data_all
                self._buffer_data.append(raw)
                if not self.is_recording():
                    break
            if self.buffer_nbytes > self.buffer_max:
                self.save()
        else:
            self._buffer_data.append(raw)
            for i in range(self._reader.window_size // 10):
                raw = self._reader.data_channel_t.reshape(-1, 1)
                self._buffer_data.append(raw)
        t2 = raw[-1, -1]
        #  self._time_correct = time.time() - t2
        logger.debug('Recording data from %.3f - %.3f' % (t1, t2))

    def cmd(self, *args, **kwargs):
        '''
        Positional arguments specifies method to be executed with no params,
        or the attribute whose value will be returned. Keyword arguments
        specifies attribute's name and value to be set.

        Examples
        --------
        >>> recorder.cmd('close')  // recorder.close()
        >>> recorder.cmd('status')  // recorder.status
        'closed'
        >>> recorder.cmd('start', 'status')  // reccorder.start() + status
        'started'
        >>> recorder.cmd('chunk 5')  // recorder.cmd(chunk=5)
        '5'
        >>> recorder.cmd(chunk=4, **{'event_merge': True})
        {'chunk': 4, 'event_merge': 'True'}
        >>> recorder.chunk = 4; recorder.event_merge = True  // same as above

        Returns
        -------
        None | object(attribute value or method result) | dict
        '''
        results = {}
        args = list(args)
        for cmd in args[:]:
            mth = shlex.split(str(cmd))
            if len(mth) < 1 or len(mth) > 2:
                logger.error('Invalid command: `{}`'.format(cmd))
                continue
            elif len(mth) == 2:
                kwargs.setdefault(mth[0], mth[1])
                args.remove(cmd)
                continue
            else:
                mth = mth[0]
            if mth.startswith('_') or not hasattr(self, mth):
                logger.error('Invalid method/attribute: `{}`'.format(mth))
                continue
            attr = getattr(self, mth)
            if callable(attr):
                try:
                    rst = attr()
                except Exception:
                    rst = traceback.format_exc()
                logger.debug('Execute method {}: `{}`'.format(mth, rst))
            else:
                rst = attr
                logger.debug('Attribute value {}: `{}`'.format(mth, attr))
            results[mth] = str(rst)
        for key, value in kwargs.items():
            if key.startswith('_') or not hasattr(self, key):
                logger.error('Invalid attribute: `{}`'.format(key))
                continue
            attr = getattr(self, key)
            if callable(attr):
                logger.error('Cannot set value of method: `{}`'.format(attr))
                continue
            try:
                setattr(self, key, value)
            except Exception:
                logger.error(traceback.format_exc())
            else:
                value = getattr(self, key)
                logger.debug('Attribute value {}: `{}`'.format(key, value))
                results[key] = str(value)
        if (len(args) + len(kwargs)) != len(results) or len(results) > 1:
            return results
        return results and list(results.values())[0] or None

    @CachedProperty
    def _help_names(self):
        return [
            i for i in set(self.__dict__).union(Recorder.__dict__)
            .difference(['cmd', 'data_all'])
            .union(['name', 'ident', 'status'])
            if not i.startswith('_')
        ]

    @property
    def _help_attrs(self):
        return [(i, getattr(self, i)) for i in self._help_names]

    def summary(self):
        '''Display a list of attributes and values of object.'''
        val = []
        for name, attr in self._help_attrs:
            if callable(attr):
                continue
            val.append((name, attr))
        ml = max(map(len, [i[0] for i in val]))
        return '\n'.join([
            '%s : %s' % (k.ljust(ml), v)
            for k, v in sorted(val)
        ])

    def usage(self):
        '''Display a list of brief help on methods of object.'''
        msg = []
        for name, attr in self._help_attrs:
            if not callable(attr):
                continue
            doc = pydoc.getdoc(attr).replace('\n', ' ') or 'Unknown'
            msg.append((name, doc))
        ml = max(map(len, [i[0] for i in msg]))
        return '\n'.join([
            '%s : %s' % (k.ljust(ml), v)
            for k, v in sorted(msg)
        ])

    def help(self):
        '''Show this help message.'''
        msg, val = [], []
        for name, attr in self._help_attrs:
            if callable(attr):
                doc = pydoc.getdoc(attr).replace('\n', ' ') or 'Unknown'
                msg.append((name, doc))
            else:
                val.append((name, attr))
        ml = max(map(len, [i[0] for i in msg + val]))
        return (
            'Help on embci.apps.recorder.base.Recorder:\n' +
            '\n'.join(['%s : %s' % (k.ljust(ml), v) for k, v in sorted(msg)]) +
            '\n' + '-' * 80 + '\n' +
            '\n'.join(['%s : %s' % (k.ljust(ml), v) for k, v in sorted(val)])
        )


# THE END
