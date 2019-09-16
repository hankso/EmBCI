#!/usr/bin/env python3
# coding=utf-8
#
# File: apps/recorder/base.py
# Authors: Hank <hankso1106@gmail.com>
# Create: 2019-04-29 18:27:21

'''`embci.apps.recorder.Recorder` is defined in this source file.'''

# built-in
import time
import warnings
import traceback

# requirements.txt: network: bottle
# requirements.txt: data: numpy
import bottle
import numpy as np

from embci.io import create_data_dict, save_data
from embci.utils import LoopTaskInThread

from . import logger

application = bottle.Bottle()


class Recorder(LoopTaskInThread):
    def __init__(self, reader, username=None, *args, **kwargs):
        self._data_buffer = []
        self._event_list = []
        self.reader = reader
        self._username = username
        logger.info('Recorder initialized on {}.'.format(self.reader))
        super(Recorder, self).__init__(self._recording, daemon=True)
        self.cmd(*args, **kwargs)

    def restart(self):
        warnings.warn('`restart` is not allowed, use `pause` instead!')

    def close(self):
        if not super(Recorder, self).close():
            return False
        self.save()
        self.clear()
        return True

    def clear(self):
        self._data_buffer.clear()
        self._event_list.clear()

    def get_data(self):
        # num_channel x time_series
        data = np.concatenate(self._data_buffer, axis=-1)
        del self._data_buffer[:]
        return data

    def save(self):
        if not len(self._data_buffer):
            logger.debug('no data available in buffer for current user')
            return
        if self.username is not None:
            data = self.get_data()
            save_data(self.username, create_data_dict(
                data, label='record', sample_rate=self.reader.sample_rate))
        else:
            del self._data_buffer[:]

    @property
    def event(self):
        if len(self._event_list):
            return self._event_list[-1]
        return (0, 0)

    @event.setter
    def event(self, e):
        self._event_list.append(
            (time.time() - self.reader.start_time, int(e))
        )
        logger.debug('add event {1} at {0}'.format(*self.event))

    @property
    def username(self):
        return self._username

    @username.setter
    def username(self, name):
        if name == self._username:
            return
        self.pause()
        time.sleep(0.5)
        self.save()
        if name.title() in ['None', '-', ' ']:
            self._username = None
            logger.info('username cleared, recorder paused')
        else:
            self._username = name
            self.resume()
            logger.info('username set to {}'.format(name))

    def _merge_events(self, times):
        last_index = 0
        events = []
        while self._event_list:
            t, event = self._event_list.pop(0)
            index = abs(times - t).argmin()
            if index == last_index != 0:
                events[-1] |= event
            else:
                events += [0] * (index - last_index) + [event]
            last_index = index and (index - 1)
        return np.pad(events, (0, len(times) - len(events))).reshape(1, -1)

    def _recording(self):
        if (
            self.username is None or
            not self.started or
            not self.reader.is_streaming()
        ):
            time.sleep(0.5)
            return
        while self.reader._index > 5:
            time.sleep(0.001)
        data = self.reader._data.copy()
        time.sleep(0.5)
        events = self._merge_events(data[-1])
        self._data_buffer.append(np.concatenate((data, events)))
        logger.info('Recording {:.2f}s - {:.2f}s for `{}`{}'.format(
            data[-1, 5], data[-1, -1], self.username,
            events.any() and ' with %d events' % np.count_nonzero(events) or ''
        ))

    def cmd(self, *args, **kwargs):
        '''
        Positional arguments specifies method to be executed with no params.
        Keyword arguments specifies attribute's name and value to be set.
        '''
        try:
            for mth in args:
                if mth.startswith('_'):
                    continue
                method = getattr(self, mth, None)
                if callable(method):
                    rst = method()
                    logger.debug('execute {}: return {}'.format(mth, rst))
                else:
                    logger.error('unknown cmd {}'.format(mth))
            for key in kwargs:
                if key.startswith('_'):
                    continue
                if hasattr(self, key):
                    value = kwargs[key]
                    setattr(self, key, value)
                    logger.debug('set {} to {}'.format(key, value))
                else:
                    logger.error('unknown cmd {}'.format(key))
        except Exception:
            logger.error(traceback.format_exc())

# THE END
