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

from ..utils import (
    ensure_unicode, ensure_bytes, find_serial_ports, duration,
    LoopTaskInThread, Singleton
)
from ..constants import command_dict_null, command_dict_plane
from . import logger

__all__ = ['SocketTCPServer'] + [
    _ + 'Commander' for _ in ('Torcs', 'Plane', 'LSL', 'Serial')
]


# TODO: embci.io.commander: valid_name
def validate_commandername(name):
    return name


class BaseCommander(object):
    name = '[embci.io.Commander]'
    cmd_dict = command_dict_null

    def __init__(self, cmd_dict=None, name=None, *a, **k):
        self.name = validate_commandername(name or self.__class__.name)
        self.cmd_dict = cmd_dict or self.cmd_dict
        try:
            logger.debug('[Command Dict] %s' % self.cmd_dict['_desc'])
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
        if cmd not in self.cmd_dict:
            if warning:
                logger.warning('{} command {} is not supported'.format(
                    self.name, cmd))
            return
        return self.cmd_dict[cmd]

    def close(self):
        raise NotImplementedError('you can not directly use this class')


class TorcsCommander(BaseCommander):
    '''
    Send command to TORCS (The Open Race Car Simulator). You can output
    predict result from classifier to the game to control race car like turn
    left, turn right, throttle, brake etc.
    '''
    name = 'TorcsCommander'

    def start(self):
        from ..gyms import TorcsEnv
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


class PlaneCommander(BaseCommander, Singleton):
    '''
    Send command to plane war game. Control plane with commands
    [`left`, `right`, `up` and `down`].
    '''
    name = 'PlaneCommander'
    cmd_dict = command_dict_plane

    def start(self):
        from ..gyms import PlaneClient
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


class LSLCommander(BaseCommander):
    '''
    Broadcast string[s] by pylsl.StreamOutlet as an online command stream.
    '''
    name = 'LSLCommander'

    def start(self, name=None, type='Result', source=None):
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
        >>> c = LSLCommander(name='pylsl commander 2')
        >>> c.start('result of recognition', 'EmBCI Hardware Re.A7.1221')
        >>> pylsl.resolve_bypred("contains('recognition')")
        [<pylsl.pylsl.StreamInfo instance at 0x7f3e82d8c3b0>]
        '''
        self._outlet = pylsl.StreamOutlet(pylsl.StreamInfo(
            name or self.name, type=type, channel_count=1,
            channel_format='string', source_id=source or self.name))

    def send(self, key, *args, **kwargs):
        self._outlet.push_sample([ensure_unicode(key), ])

    def close(self):
        del self._outlet


class SerialCommander(BaseCommander):
    name = 'SerialCommander'

    def __init__(self, *a, **k):
        super(SerialCommander, self).__init__(*a, **k)
        self._command_lock = threading.Lock()
        self._command_serial = serial.Serial()

    def start(self, port=None, baudrate=9600):
        self._command_serial.port = port or find_serial_ports()
        self._command_serial.baudrate = baudrate
        self._command_serial.open()

    def send(self, key, *args, **kwargs):
        ret = self.get_command(key)
        if ret is None:
            return
        with self._command_lock:
            self._command_serial.write(ensure_bytes(ret[0]))
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
    Socket TCP server on host:port, default to 0.0.0.0:0. A data broadcaster.
    '''
    def __init__(self, host='0.0.0.0', port=0):
        self.host, self.port = host, port
        self._conns, self._addrs = [], []
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        LoopTaskInThread.__init__(self, self.manager)

    def __repr__(self):
        return '<%s 0x%x>' % (LoopTaskInThread.__repr__(self)[1:-1], id(self))

    def hook_before(self):
        self._server.bind((self.host, self.port))
        self._server.listen(5)
        self._server.settimeout(0.5)
        self.host, self.port = self._server.getsockname()
        logger.info('{} socket server is listening on {}:{}'.format(
            self.name, self.host, self.port))

    def handle_client(self, sock):
        addr = self.getaddr(sock)
        msg = sock.recv(4096).decode('utf8').strip()
        # client sent some data
        if msg not in ['shutdown', '']:
            logger.info('{} recv {} from {}:{}'.format(self.name, msg, *addr))
            if hasattr(sock, 'onmessage'):
                try:
                    sock.onmessage(msg)
                except Exception:
                    logger.error(traceback.format_exc())
            return
        # client shutdown and we should clear correspond server
        try:
            sock.sendall(b'shutdown')
            sock.shutdown(socket.SHUT_RDWR)
        except socket.error:
            pass
        except Exception:
            logger.error(traceback.format_exc())
        finally:
            sock.close()
        self.remove(sock, addr)

    def manager(self):
        '''
        This loop task does following things to manage connections:
            1. wait for new clients and add them into a list
            2. remove closed clients
            3. recieve msg from all clients and run callback functions
        '''
        rlist, _, _ = select.select([self._server] + self._conns, [], [], 3)
        if not rlist:
            return
        if rlist[0] is self._server:  # new connection
            con, addr = self._server.accept()
            con.settimeout(0.5)
            self.add(con, addr)
        else:                         # some client maybe closed
            self.handle_client(rlist[0])

    def send(self, con, data):
        try:
            con.sendall(data)
        except socket.error:
            pass

    def multicast(self, data):
        data = ensure_bytes(data)
        for con in self._conns:
            self.send(con, data)

    def hook_after(self):
        for con in self._conns:
            con.close()
        self._server.close()
        logger.debug(self.name + ' Socket server shut down.')

    def has_listeners(self):
        return len(self._conns)

    def getaddr(self, sock):
        if sock in self._conns:
            return self._addrs[self._conns.index(sock)]
        return sock.getpeername()

    def add(self, sock, addr=None):
        if sock in self._conns:
            return
        try:
            addr = addr or self.getaddr(sock)
        except Exception:
            return
        self._conns.append(sock)
        self._addrs.append(addr)
        logger.debug('{} add client from {}:{}'.format(self.name, *addr))

    def remove(self, sock, addr=None):
        if sock not in self._conns:
            return
        try:
            addr = addr or self.getaddr(sock)
        except Exception:
            return
        self._conns.remove(sock)
        self._addrs.remove(addr)
        logger.debug('{} lost client from {}:{}'.format(self.name, *addr))


# THE END
