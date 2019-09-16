#!/usr/bin/env python3
# coding=utf-8
#
# File: WiFi/backend/__init__.py
# Authors: Hank <hankso1106@gmail.com>
# Create: 2019-05-04 00:10:32

'''
Backend interface:
    wifi_accesspoints([interface]) =>
    [
        # python-wifi backend example
        {
            'ssid': u'TP-Link_XXXX',
            'frequency': ['5.805GHz'],
            'mac_address': 'B0:F9:63:24:35:C2',
            'mode': 'Master',
            'encrypted': True,
            'encryption_type': ['WPA2'],
            'signal': -45,
            'quality': '50/70',
            'maxbitrate': '54 Mb/s',
            'saved': False,
            'status': 'Disconnected',
            # 'channel': 161,
            # 'noise': None,
            'obj': <wifi.scan.Cell at 0x7f881501afd0>
        },
        # python-networkmanager backend example
        {
            'ssid': u'BUAA-Mobile',
            'frequency': ['2.462GHz'],
            'mac_address': '70:BA:EF:D2:49:52',
            'mode': 'infra',
            'encrypted': True,
            'encryption_type': ['key_mgmt_psk', 'pair_ccmp']
            'strength': -39,
            'quality': '30/70',
            'maxbitrate': '54 Mb/s',
            'saved': True,
            'status': 'Obtaining IP address',
            # 'lastseen': 1325821,
            'obj': <NetworkManager.AccessPoint at 0x7f8815045748>
        },
        ...
    ]

    wifi_connect(ssid[, psk]) => (True/False, reason)

    wifi_disconnect([ssid]) => (True/False, reason)

    wifi_enable => (True/False, reason)

    wifi_disable => (True/False, reason)

    wifi_forget => (True/False, reason)

    wifi_status => True/False
'''

__targets__ = [
    'wifi_' + _ for _ in [
        'accesspoints', 'connect', 'disconnect', 'forget',
        'enable', 'disable', 'status',
    ]
]


# built-in
import sys
import logging
import importlib
import traceback

__all__ = []
__backends__ = [
    {
        'name': 'python-networkmanager',
        'requires': ['NetworkManager', 'dbus'],
        'module': 'nm_backend'
    },
    {
        'name': 'python-wifi',
        'requires': ['wifi'],
        'module': 'wifi_backend'
    },
]
__module__ = sys.modules[__name__]  # reference to current module
logger = logging.getLogger('.'.join(__name__.split('.')[:-1]))

for bd in __backends__:
    try:
        for req in bd['requires']:
            importlib.import_module(req)
    except ImportError:
        continue
    __backend__ = __name__ + '.' + bd['module']
    try:
        mod = importlib.import_module(__backend__)
    except ImportError:
        logger.warning('Importing `%s` failed.' % __backend__)
        logger.error(traceback.format_exc())
        continue
    logger.debug('Using %s backend from %s.' % (bd['name'], __backend__))

    # =========================================================================
    # runtime `from .xxx_backend import *`
    #
    if not hasattr(mod, '__all__'):
        mod.__all__ = __targets__
    # method 1
    try:
        for entry in mod.__all__:
            setattr(__module__, entry, getattr(mod, entry))
    except AttributeError:
        logger.error(
            'Invalid backend %s. Missing entry `%s`.' % (bd['name'], entry))
        continue
    else:
        break

    # method 2
    # TODO: WiFi.backend: importlib.__import__ doesn't support relative import
    #  importlib.__import__(bd['module'], globals(), locals(), mod.__all__)

for entry in __all__:
    if not hasattr(__module__, entry):
        raise RuntimeError('Cannot load backend. Terminate.')

try:
    del sys, logging, importlib, __module__, bd, mod, req, entry
except NameError:
    pass

# THE END