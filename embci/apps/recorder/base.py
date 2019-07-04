#!/usr/bin/env python
# coding=utf-8
#
# File: apps/recorder/base.py
# Author: Hankso
# Webpage: https://github.com/hankso
# Time: Mon 29 Apr 2019 18:27:21 CST

'''`embci.apps.recorder.Recorder` is defined in this source file.'''

# built-in
import time
import logging
import warnings
import traceback

# requirements.txt: data-processing: numpy
import numpy as np

from embci.io import create_data_dict, save_data
from embci.utils import LoopTaskInThread

logger = logging.getLogger('.'.join(__name__.split('.')[:-1]))


class Recorder(LoopTaskInThread):
    def __init__(self, reader, username=None, *a, **k):
        self.buffer = []
        self.events = []
        self.reader = reader
        self.username = username
        self.start_time = self.reader._start_time
        super(Recorder, self).__init__(self.recording, daemon=True)
        logger.info('Recorder inited on {}.'.format(self.reader))
        self.cmd(*a, **k)

    def restart(self):
        warnings.warn('`restart` is not allowed on {}, use `pause` instead!'
                      .format(self))

    def close(self):
        logger.debug('Closing recorder {}'.format(self))
        if not super(Recorder, self).close():
            return
        self.save()
        self.buffer = []
        logger.debug('Recorder {} closed.'.format(self))

    stop = close

    def recording(self):
        if not self.username:
            time.sleep(0.5)
            return
        if not self.started or not self.reader.streaming:
            return
        while self.reader._index > 5:
            time.sleep(0.01)
        data = self.reader._data.copy()
        time.sleep(0.5)
        event = []
        last_index = 0
        for t, e in self.events:
            index = abs(data[-1] - t).argmin()
            event += [0] * (index - last_index) + [e]
            last_index = index and (index - 1)
        event = np.array([event + [0] * (data.shape[1] - len(event))])
        self.buffer.append(np.concatenate((data, event)))
        logger.info('Recording {:.2f}s - {:.2f}s with {} events for `{}`'
                    .format(data[-1, 1], data[-1, -1],
                            len(self.events), self.username))
        self.events = []

    def cmd(self, *a, **k):
        if 'event' in k:
            self.events.append(
                (time.time() - self.start_time, k.pop('event')))
            logger.debug('add event {} at {}'.format(*self.events[-1]))
        if 'username' in k:
            username = str(k.pop('username'))
            if username == self.username:
                pass
            elif username.title() in ['None', '-', ' ']:
                self.pause()
                time.sleep(0.5)
                self.save()
                self.username = None
                logger.info('username cleared')
            else:
                self.pause()
                time.sleep(0.5)
                self.save()
                self.username = username
                self.resume()
                logger.info('username set to {}'.format(self.username))
        try:
            for act in a:
                attr = getattr(self, act, None)
                if callable(attr):
                    logger.debug('executing {}'.format(act))
                    attr()
                else:
                    logger.error('unknown cmd {}'.format(act))
            for key in k:
                if hasattr(self, key):
                    setattr(self, key, k[key])
                    logger.debug('setting {} to {}'.format(key, k[key]))
                else:
                    logger.error('unknown cmd {}'.format(key))
        except Exception:
            logger.error(traceback.format_exc())

    def clear(self):
        self.buffer = []
        self.events = []

    def save(self):
        if not len(self.buffer):
            return
        if self.username is None:
            return
        data_dict = create_data_dict(
            np.concatenate(self.buffer, -1),  # num_channel x time_series
            label='record', sample_rate=self.reader.sample_rate)
        save_data(self.username, data_dict)
        self.buffer = []

# THE END
