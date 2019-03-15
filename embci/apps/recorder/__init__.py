#!/usr/bin/env python
# coding=utf-8
#
# File: apps/recorder/__init__.py
# Author: Hankso
# Webpage: https://github.com/hankso
# Time: Fri 15 Mar 2019 07:04:20 CST

# built-in
import sys
import time
import signal
import warnings
import traceback
from threading import Thread

# requirements.txt: data-processing: numpy
import numpy as np

import embci
from embci.io import PylslReader as Reader
from embci.io import StreamControlMixin


'''
- Recorder support start, pause, resume, stop
- Recorder support change username
- Command listener use main thread
- Record both data, timestamp, and event
'''

reader = Reader(sample_time=2, num_channel=8)
logger = embci.utils.config_logger()


class Recorder(Thread, StreamControlMixin):
    def __init__(self, *a, **k):
        self.cmd(**k)
        StreamControlMixin.__init__(self)
        Thread.__init__(self, target=self.loop, args=(self.recording,),
                        kwargs={})
        self.buffer = []
        self.events = []
        self.start_time = reader._start_time

    def start(self):
        Thread.start(self)
        StreamControlMixin.start(self)

    def restart(self):
        warnings.warn('`restart` is not allowed on {}, use `pause` instead!'
                      .format(self))

    def recording(self):
        while reader._index > 5:
            if self._flag_close.is_set():
                return
            time.sleep(0.001)
        data = reader._data.copy()
        time.sleep(0.5)
        event = []
        last_index = 0
        for t, e in self.events:
            index = abs(data[-1] - t).argmin()
            event += [0] * (index - last_index) + [e]
            last_index = index and (index - 1)
        event = np.array([event + [0] * (data.shape[1] - len(event))])
        self.buffer.append(np.concatenate((data, event)))
        logger.info('Recording {:.2f}s - {:.2f}s with {} events'
                    .format(data[-1, 1], data[-1, -1], len(self.events)))
        self.events = []

    def cmd(self, *a, **k):
        if 'event' in k:
            self.events.append(
                (time.time() - self.start_time, k.pop('event')))
            logger.debug('add event {} at {}'.format(*self.events[-1]))
        if 'username' in k:
            self.pause()
            self.save()
            self.username = k.pop('username')
            self.resume()
            logger.debug('username set to {}'.format(self.username))
        try:
            for act in a:
                attr = getattr(self, act)
                if callable(attr):
                    attr()
                    logger.debug('executing {}'.format(act))
            for key in k:
                if hasattr(self, key):
                    setattr(self, key, k[key])
                    logger.debug('setting {} to {}'.format(key, k[key]))
        except Exception:
            logger.error(traceback.format_exc())

    def close(self):
        StreamControlMixin.close(self)
        self.save()

    stop = close

    def save(self):
        if not len(self.buffer):
            return
        if not getattr(self, 'username', ''):
            return
        data_dict = embci.io.create_data_dict(
            np.concatenate(self.buffer, -1),  # num_channel x time_series
            label='record', sample_rate=reader.sample_rate)
        embci.io.save_data(self.username, data_dict)
        self.buffer = []


recorder = Recorder()


def exit(*a, **k):
    recorder.cmd('close')


def main(args=sys.argv[1:]):
    signal.signal(signal.SIGHUP, exit)
    signal.signal(signal.SIGTERM, exit)
    reader.start(method='thread', kwargs={'type': 'Reader Outlet'})
    if len(args):
        recorder.cmd(username=args[0])
    recorder.start()
    try:
        while 1:
            try:
                cmd = embci.utils.input(timeout=3)
            except Exception:
                continue
            if not cmd:
                continue
            logger.info('received cmd {}'.format(cmd))
            cmd = cmd.split(' ')
            if len(cmd) == 1:
                recorder.cmd(cmd[0])
            elif len(cmd) == 2:
                cmd = {cmd[0]: cmd[1]}
                recorder.cmd(**cmd)
            else:
                logger.error('Invalid command `{}`'.format(cmd))
    except KeyboardInterrupt:
        pass
    except Exception:
        logger.error(traceback.format_exc())
    finally:
        exit()


# THE END
