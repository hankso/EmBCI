#!/usr/bin/env python
# coding=utf-8
#
# File: WiFi/backend/wifi_backend.py
# Author: Hankso
# Webpage: https://github.com/hankso
# Time: Sun 05 May 2019 10:19:16 CST

'''
Python-wifi Backend
-------------------
Network backend using package `python-wifi` (wrapping Debian `ifupdown`)

This module provides standard methods including:
    - wifi_accesspoints
    - wifi_connect
    - wifi_disconnect
    - wifi_enable
    - wifi_disable
'''

# built-in
import re
import binascii

# requirements.txt: optional: wifi
import wifi

from embci.utils import AttributeList, AttributeDict


def wifi_accesspoints(interface=None):
    '''
    Scan wifi hotspots with specific interface and return results as list of
    JS dict. If interface doesn't exists or scan failed (permission denied),
    return empty list []. Example of an access point:
    {
        'ssid': u'TP-Link_XXXX',
        'frequency': '5.805 GHz',
        'mac_address': 'B0:F9:63:24:35:C2',
        'mode': 'Master',
        'encrypted': True,
        'encryption_type': ['WPA2'],
        'signal': -45,
        'quality': '50/70',
        'maxbitrate': '54 Mb/s',
        'obj': <wifi.scan.Cell at 0x7f881501afd0>
        # 'channel': 161,
        # 'noise': None,
    }
    '''
    if interface is None:
        ifs = []
        try:
            with open('/proc/net/wireless', 'r') as f:
                ifs += [re.findall(r'wl\w+', line)
                        for line in f.readlines() if '|' not in line]
            with open('/proc/net/dev', 'r') as f:
                ifs += [re.findall(r'wl\w+', line)
                        for line in f.readlines() if '|' not in line]
        except IOError:
            pass
        interfaces = list(set([_[0] for _ in ifs if _]))
    elif isinstance(interface, (tuple, list)):
        interfaces = list(set[interface])
    else:
        interfaces = [str(interface)]
    cells = AttributeList()
    for interface in interfaces:
        try:
            cells.extend([
                AttributeDict(vars(c)) for c in wifi.Cell.all(interface)
                if c.address not in cells.address
            ])
        except wifi.exceptions.InterfaceError:
            pass
    cells = sorted(cells, key=lambda cell: cell.signal, reverse=True)
    unique = AttributeList()
    for cell in cells:
        if cell.ssid in unique.ssid:
            continue
        cell.mac_address     = cell.pop('address', ':'.join(['00'] * 6))
        cell.strength        = cell.pop('signal', -100)
        cell.maxbitrate      = cell.pop('bitrates', ['0 Mb/s'])[-1]
        cell.encryption_type = [cell.encryption_type.upper()]
        # convert u'\\xe5\\x93\\x88' to u'\u54c8' (for example)
        cell.ssid = re.sub(r'\\x([0-9a-fA-F]{2})',
                           lambda m: binascii.a2b_hex(m.group(1)),
                           cell.ssid.encode('utf8')).decode('utf8')
        cell.pop('noise')
        cell.pop('channel')
        unique.append(cell)
    return unique


def wifi_connect(ssid, psk=None):
    # if not has psk
    #     return Scheme.find(interface, essid)
    # elif forget:
    #     find and delete
    # else:
    #     try connect
    #  essid = bottle.request.forms.essid
    # Scheme = Scheme.for_file('/tmp/interface.embci')
    #  scheme = Scheme.for_cell(interface, essid,
    #                           wifi_list[wifi_list.ssid.index(essid)],
    #                           bottle.request.forms.psk)
    #  scheme.save()
    #  scheme.activate()
    return (False, 'not implemented yet')


def wifi_disconnect(ssid=None):
    return (False, 'not implemented yet')


def wifi_enable():
    return (False, 'not implemented yet')


def wifi_disable():
    return (False, 'not implemented yet')


# THE END
