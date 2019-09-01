#!/usr/bin/env python3
# coding=utf-8
#
# File: DisplayWeb/utils.py
# Authors: Hank <hankso1106@gmail.com>
# Create: 2019-03-04 17:06:43

'''__doc__'''

# built-in
import base64
import traceback

# requirements.txt: network: bottle, gevent-websocket
# requirements.txt: data-processing: numpy
import bottle
import geventwebsocket
import numpy as np

from embci.utils import (                                          # noqa: W611
    serialize, deserialize, minimize,
    ensure_bytes, ensure_unicode,
    LoopTaskInThread
)

from .globalvars import reader, server, signalinfo, logger, pt


class WebSocketMulticaster(LoopTaskInThread):
    def __init__(self, paramtree):
        self.ws_list = []
        self.data_list = []
        self.pt = paramtree
        LoopTaskInThread.__init__(self, self._data_multicast)

    def _data_fetch(self):
        data = process_realtime(reader.data_channel, self.pt)
        server.multicast(data)
        return data

    def _data_cache(self):
        while len(self.data_list) < self.pt.batch_size:
            self.data_list.append(self._data_fetch())
        data = np.float32(self.data_list).T
        del self.data_list[:]
        if self.pt.detrend and reader.input_source != 'test':
            data = signalinfo.detrend(data)
        # data = data[self.pt.channel_range.n]
        data = data * self.pt.scale_list.a[self.pt.scale_list.i]
        return bytearray(data)

    def _data_multicast(self):
        data = self._data_cache()
        for ws in self.ws_list[:]:
            if not self._data_send(ws, data):
                self.remove(ws)

    def _data_send(self, ws, data, binary=True):
        try:
            ws.send(data, binary)
            return True
        except geventwebsocket.websocket.WebSocketError:
            ws.close()
        except Exception:
            logger.error(traceback.format_exc())
        return False

    def add(self, ws):
        if not isinstance(ws, geventwebsocket.websocket.WebSocket):
            raise TypeError('Invalid websocket. Must be gevent-websocket.')
        if ws.closed:
            raise ValueError('Websocket %s is already closed.' % ws)
        self.ws_list.append(ws)

    def remove(self, ws):
        if ws not in self.ws_list:
            return
        self.ws_list.remove(ws)


distributor = WebSocketMulticaster(pt)


def process_register(data, pt=pt):
    signalinfo.notch(data, register=True)
    signalinfo.bandpass(
        data, pt.bandpass.get('low', 4), pt.bandpass.get('high', 10),
        register=True
    )


def process_realtime(data, pt=pt):
    if pt.notch:
        data = signalinfo.notch_realtime(data)
    if pt.bandpass:
        data = signalinfo.bandpass_realtime(data)
    return data


def process_fullarray(data, pt=pt):
    if pt.notch:
        data = signalinfo.notch(data)
    if pt.bandpass:
        data = signalinfo.bandpass(data, **pt.bandpass)
    return data


def set_token(data, username='user', key='token', max_age=60):
    token = base64.b64encode(serialize(data))
    secret = base64.b64encode(ensure_bytes(username))
    bottle.response.set_cookie('name', ensure_unicode(username))
    # Anti-XSS(Cross Site Scripting): HttpOnly + Escape(TODO)
    bottle.response.set_cookie(
        key, token, secret=secret, max_age=max_age, httponly=True)
    return data


def check_token(key='token'):
    username = bottle.request.get_cookie('name')
    secret = base64.b64encode(ensure_bytes(username))
    token = bottle.request.get_cookie(key, secret=secret)
    if token is None:
        bottle.abort(408, 'Cache expired or user\'s report not generated yet!')
    return deserialize(base64.b64decode(token))

# THE END
