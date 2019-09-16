#!/usr/bin/env python3
# coding=utf-8
#
# File: EmBCI/embci/io/commanders.py
# Authors: Hank <hankso1106@gmail.com>
# Create: 2018-03-06 21:02:35

'''Commanders'''

# built-in
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
import time
import socket
import select
import threading
import traceback

# requirements.txt: data: pylsl
# requirements.txt: drivers: pyserial
import pylsl
import serial

from ..utils import (ensure_unicode, find_serial_ports, duration,
                     LoopTaskInThread)
from ..gyms import TorcsEnv, PlaneClient
from ..constants import command_dict_null, command_dict_plane
from . import logger

__all__ = [
    _ + 'Commander' for _ in (
        'Torcs', 'Plane', 'Pylsl', 'Serial'
    )
]
__all__ += ['SocketTCPServer']

# TODO: embci.io.commander: valid_name


class BaseCommander(object):
    name = '[embci.io.Commander]'
    _command_dict = command_dict_null

    def __init__(self, command_dict=None, name=None, *a, **k):
        self.name = name or self.name
        self._command_dict = command_dict or self._command_dict
        try:
            logger.debug('[Command Dict] %s' % self._command_dict['_desc'])
        except KeyError:
            logger.warning(
                '[Command Dict] current command dict does not have a '
                'key named _desc to describe itself. please add it.')
        # alias `send` as `write` to make instances file-like object
        self.write = self.send

    def start(self):
        raise NotImplementedError('you can not directly use this class')

    def send(self, key, *args, **kwargs):
        raise NotImplementedError('you can not directly use this class')

    flush, read = lambda: None, lambda *a: ''
    seek = truncate = tell = lambda *a: 0

    def get_command(self, cmd, warning=True):
        if cmd not in self._command_dict:
            if warning:
                logger.warning('{} command {} is not supported'.format(
                    self.name, cmd))
            return
        return self._command_dict[cmd]

    def close(self):
        raise NotImplementedError('you can not directly use this class')


class TorcsCommander(BaseCommander):
    '''
    Send command to TORCS (The Open Race Car Simulator)
    You can output predict result from classifier to the
    game to control race car(left, right, throttle, brake...)
    '''
    __num__ = 1

    def __init__(self, *a, **k):
        super(TorcsCommander, self).__init__(
            name='[Torcs commander %d]' % TorcsCommander.__num__)
        TorcsCommander.__num__ += 1

    def start(self):
        logger.debug(self.name + ' initializing TORCS...')
        self.env = TorcsEnv(vision=True, throttle=False, gear_change=False)
        self.env.reset()

    @duration(1, 'TorcsCommander')
    def send(self, key, prob, *args, **kwargs):
        cmd = [abs(prob) if key == 'right' else -abs(prob)]
        logger.debug(self.name + ' sending cmd {}'.format(cmd))
        self.env.step(cmd)
        return cmd

    def close(self):
        self.env.end()


class PlaneCommander(BaseCommander):
    '''
    Send command to plane war game. Control plane with commands
    [`left`, `right`, `up` and `down`].
    '''
    __singleton__ = True
    name = '[Plane commander]'

    def __init__(self, command_dict=command_dict_plane):
        if PlaneCommander.__singleton__ is False:
            raise RuntimeError('There is already one ' + self.name)
        super(PlaneCommander, self).__init__(command_dict)
        PlaneCommander.__singleton__ = False

    def start(self):
        self.client = PlaneClient()

    @duration(1, 'PlaneCommander')
    def send(self, key, *args, **kwargs):
        ret = self.get_command(key)
        if ret is None:
            return
        self.client.send(ret[0])
        time.sleep(ret[1])
        return ret[0]

    def close(self):
        self.client.close()


class PylslCommander(BaseCommander):
    '''
    Broadcast string[s] by pylsl.StreamOutlet as an online command stream.
    '''
    __num__ = 1

    def __init__(self, command_dict=None, name=None):
        super(PylslCommander, self).__init__(
            command_dict,
            name or '[Pylsl commander %d]' % PylslCommander.__num__)
        PylslCommander.__num__ += 1

    def start(self, name=None, source=None):
        '''
        Initialize and start pylsl outlet.

        Parameters
        ----------
        name : str, optional
            Name describes the data stream or session name.
        source : str
            Source specifies an unique identifier of the device or
            data generator, such as serial number or MAC.

        Examples
        --------
        >>> c = PylslCommander(name='pylsl commander 2')
        >>> c.start('result of recognition', 'EmBCI Hardware Re.A7.1221')
        >>> pylsl.resolve_bypred("contains('recognition')")
        [<pylsl.pylsl.StreamInfo instance at 0x7f3e82d8c3b0>]
        '''
        self._outlet = pylsl.StreamOutlet(
            pylsl.StreamInfo(
                name or self.name, type='predict result',
                channel_format='string', source_id=source or self.name))

    def send(self, key, *args, **kwargs):
        if not isinstance(key, str):
            raise TypeError('{} only accept str but got {}: {}'.format(
                self.name, type(key), key))
        self._outlet.push_sample([ensure_unicode(key)])

    def close(self):
        del self._outlet


class SerialCommander(BaseCommander):
    __num__ = 1

    def __init__(self, command_dict=None, name=None):
        super(SerialCommander, self).__init__(
            command_dict,
            name or '[Serial Commander %d]' % SerialCommander.__num__)
        self._command_lock = threading.Lock()
        self._command_serial = serial.Serial()
        SerialCommander.__num__ += 1

    def start(self, port=None, baudrate=9600):
        self._command_serial.port = port or find_serial_ports()
        self._command_serial.baudrate = baudrate
        self._command_serial.open()

    def send(self, key, *args, **kwargs):
        ret = self.get_command(key)
        if ret is None:
            return
        with self._command_lock:
            self._command_serial.write(ret[0])
            time.sleep(ret[1])
        return ret[0]

    def close(self):
        self._command_serial.close()

    def reconnect(self):
        try:
            self._command_serial.close()
            time.sleep(1)
            self._command_serial.open()
            logger.info(self.name + ' reconnect success.')
        except serial.serialutil.SerialException:
            logger.error(self.name + ' reconnect failed.')


class SocketTCPServer(LoopTaskInThread):
    '''
    Socket TCP server on host:port, default to 0.0.0.0:0
    Data sender.
    '''
    __num__ = 1

    def __init__(self, host='0.0.0.0', port=0):
        self._conns = []
        self._addrs = []
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        LoopTaskInThread.__init__(self, self._manage_connections)
        # Reset name of this Thread
        self.name = '[Socket server %d]' % SocketTCPServer.__num__
        SocketTCPServer.__num__ += 1
        self._server.bind((host, port))
        self._server.listen(5)
        self._server.settimeout(0.5)
        self.host, self.port = self._server.getsockname()
        logger.info('{} binding socket server at {}:{}'.format(
            self.name, self.host, self.port))

    def _manage_connections(self):
        '''
        This loop task does following things to manage connections:
            1. wait for new clients and add them into a list
            2. remove closed clients
            3. recieve msg from all clients and run callback functions
        '''
        rlist, _, _ = select.select([self._server] + self._conns, [], [], 3)
        if not rlist:
            return
        # new connection
        if rlist[0] is self._server:
            con, addr = self._server.accept()
            con.settimeout(0.5)
            logger.debug('{} accept client from {}:{}'.format(
                self.name, *addr))
            self._conns.append(con)
            self._addrs.append(addr)
        # some client maybe closed
        elif rlist[0] in self._conns:
            con, addr = rlist[0], self.getaddr(rlist[0])
            msg = con.recv(4096)
            # client sent some data
            if msg not in ['shutdown', '']:
                logger.info('{} recv `{}` from {}:{}'.format(
                    self.name, msg, *addr))
                if hasattr(con, 'onmessage'):
                    try:
                        con.onmessage(msg)
                    except Exception:
                        logger.error(traceback.format_exc())
                return
            # client shutdown and we should clear correspond server
            try:
                con.sendall('shutdown')
                con.shutdown(socket.SHUT_RDWR)
            except socket.error:
                pass
            except Exception:
                logger.error(traceback.format_exc())
            finally:
                con.close()
            self._conns.remove(con)
            self._addrs.remove(addr)
            logger.debug('{} lost client from {}:{}'.format(
                self.name, *addr))

    def send(self, con, data):
        try:
            con.sendall(data)
        except socket.error:
            pass

    def multicast(self, data):
        data = bytearray(data)
        for con in self._conns:
            self.send(data, con)

    def close(self):
        for con in self._conns:
            con.close()
        LoopTaskInThread.close(self)
        logger.debug(self.name + ' Socket server shut down.')

    def has_listeners(self):
        return len(self._conns)

    def getaddr(self, sock):
        if sock in self._conns:
            return self._addrs[self._conns.index(sock)]
        return sock.getpeername()

    def add(self, sock):
        # TODO: ensure socket open and get addr
        addr = self.getaddr(sock)
        self._conns.append(sock)
        self._addrs.append(addr)


# THE END
