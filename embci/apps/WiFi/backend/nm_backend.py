#!/usr/bin/env python3
# coding=utf-8
#
# File: WiFi/backend/nm_backend.py
# Authors: Hank <hankso1106@gmail.com>
# Create: 2019-05-05 10:31:15

'''
NetworkManager
--------------
Network backend using package `python-networkmanager` which is based on
`org.freedesktop.NetworkManager` and `org.freedesktop.DBus`.

This module provides standard methods including:

    - wifi_accesspoints
    - wifi_connect
    - wifi_disconnect
    - wifi_enable
    - wifi_disable


.. note::
    This program only support manipulation on default wireless card (phy0)
    and interface (wlan0/wlxnxn), which means neither double wireless
    card (phy1...) nor extra interfaces (wlan1...) will be managed.
'''

# built-in
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
import copy
import uuid
import functools

# requirements.txt: optional: python-networkmanager, dbus
import dbus
import NetworkManager

from embci.utils import (AttributeList, AttributeDict,
                         ensure_unicode, get_boolean)

nm = NetworkManager.NetworkManager


def get_device_by_iface(name='wl', dtype=NetworkManager.NM_DEVICE_TYPE_WIFI):
    try:
        return nm.GetDeviceByIpIface(name)
    except Exception:
        pass

    for dev in nm.GetAllDevices():
        if dev.DeviceType == dtype and dev.Interface.startswith(name):
            return dev


wlan0 = get_device_by_iface()
if wlan0 is None:
    raise ImportError(__file__ + ' No valid wireless network device.')


STATE_STATUS_MAPPING = {
    'unknown': 'Failed',
    'unmanaged': 'Failed',
    'unavailable': 'Failed',
    'prepare': 'Connecting',
    'config': 'Connecting',
    'ip_config': 'Obtaining IP address',
    'ip_check': 'Obtaining IP address',
    'deactivating': 'Disconnecting',
    'disconnected': 'Disconnected',
    'activated': 'Connected',
}


def get_dev_status(dev=wlan0):
    state = DEV_STATE(dev.State)[0]
    return STATE_STATUS_MAPPING.get(state, 'Unknown')


def parse_flags(prefix='', *flags):
    if isinstance(flags, int):
        flags = [flags]
    flags = list(set(flags))

    flag_list = []
    for flag in flags:
        # parse single number, e.g. 0x02
        try:
            flag_list.append(NetworkManager.const(prefix, flag))
        except ValueError:
            if flag is None:
                continue
        else:
            continue

        # parse multiple bits, e.g. 0b01010010
        bit = 0
        while flag:
            if flag & 0b1:
                try:
                    flag_list.append(NetworkManager.const(prefix, 1 << bit))
                except ValueError:
                    pass
            flag >>= 1
            bit += 1
    return [flag for flag in set(flag_list)]


AP_SEC = functools.partial(parse_flags, '802_11_AP_SEC')
AP_MODE = functools.partial(parse_flags, '802_11_MODE')
AP_FLAGS = functools.partial(parse_flags, '802_11_AP_FLAGS')
DEV_STATE = functools.partial(parse_flags, 'DEVICE_STATE')


def wireless_card_info():
    devices = AttributeList(nm.GetAllDevices())
    devices.DeviceType.index(NetworkManager.NM_DEVICE_TYPE_WIFI)
    devices.State.index(NetworkManager.NM_DEVICE_STATE_ACTIVATED)


def wireless_interface_info():
    pass


basic_connection = {
    '802-11-wireless': {
        #  'band': 'b',  # a for 5GHz and bg for 2.4GHz
        #  'channel': 0,
        'mode': 'infrastructure',  # infrastructure|adhoc|ap
        'security': '802-11-wireless-security',  # deprecated, for compat only
        'ssid': None,
        'mac-address': None,  # wlan0.HwAddress
    },
    '802-11-wireless-security': {
        #  'auth-alg': '',  # open|shared|leap
        #  'key-mgmt': '',  # none(WEP)|ieee8021x(Dynamic WEP)|sae(SAE)|
        #                   # wpa-none(Ad-Hoc WPA-PSK)|wpa-psk(infra WPA-PSK)|
        #                   # wpa-eap(WPA-Enterprise)
        #  'psk': '',  # for wpa-psk, [hash|64 hex char] of actual key
        #  'leap-username': '',  # for auth-alg=leap & key-mgmt=ieee8021x
        #  'leap-password': '',  # for auth-alg=leap & key-mgmt=ieee8021x
        #  'pairwise': [],  # tkip|ccmp
        #  'proto': [],  # wpa|rsn
    },
    '802-1x': {
        #  'ca-cert': b'',  # CA certificate for eap below
        #  'ca-cert-password': ''
        #  'eap': [],  # leap|md5|tls|peap|ttls|pwd|fast
        #  'identity': '',  # UTF8 for EAP authentication methods
        #  'password': '',  # UTF8 for EAP authentication methods
    },
    'connection': {
        'id': None,
        'interface-name': None,  # wlan0.Interface
        'type': '802-11-wireless',  # 802-3-ethernet|802-11-wireless ...
        'uuid': None,
    },
    'ipv4': {'method': 'auto'},
    'ipv6': {'method': 'auto'},
}


def gen_none(con, **k):
    con['802-11-wireless-security']['auth-alg'] = 'open'
    con['802-11-wireless-security']['key-mgmt'] = 'none'
    return con


def gen_key_mgmt_psk(con, pwd, **k):
    con['802-11-wireless-security']['key-mgmt'] = 'wpa-psk'
    con['802-11-wireless-security']['psk'] = pwd
    return con


def gen_key_mgmt_802_1x(con, user, pwd, **k):
    con['802-11-wireless-security']['auth-alg'] = 'open'
    con['802-11-wireless-security']['key-mgmt'] = 'wpa-eap'
    con['802-1x'] = {
        'eap': ['peap'], 'identity': user, 'password': pwd,
        'phase2-auth': 'mschapv2',
    }
    return con


def gen_key_mgmt_sae(con, user, pwd, **k):
    raise NotImplementedError
    return con


def add_connection(ssid, user=None, pwd=None, **k):
    ap = get_accesspoint_by_ssid(ssid)
    dev = k.get('dev', wlan0)
    if ap.encrypted and pwd is None:
        raise ValueError('Password is needed for access point `%s`.' % ssid)

    con = copy.deepcopy(basic_connection)
    con['connection'].update({
        'uuid': str(uuid.uuid4()), 'id': ssid, 'interface-name': dev.Interface,
    })
    con['802-11-wireless'].update({
        'ssid': ssid, 'mac-address': dev.HwAddress,
    })

    for flag in ap.encryption_type:
        try:
            hdlr = globals().get('gen_' + flag)
            if hdlr is not None:
                con = hdlr(con, ssid=ssid, user=user, pwd=pwd, **k)
        except ValueError as e:
            return (False, str(e))
        except Exception:
            continue

    NetworkManager.Settings.AddConnection(con)
    return (True, 'OK')


def update_connection(ssid, user=None, pwd=None, **k):
    con = get_connection_by_ssid(ssid)
    if con is None:
        return add_connection(ssid, user, pwd, **k)
    ap = get_accesspoint_by_ssid(ssid)
    if ap.encrypted and pwd is None:
        raise ValueError('Password is needed for access point `%s`.' % ssid)

    dev = k.get('dev', con.device) or wlan0
    con['802-11-wireless']['mac-address'] = dev.HwAddress
    con['802-11-wireless']['seen-bssids'] = []
    con['connection']['interface-name'] = dev.Interface

    for flag in ap.encryption_type:
        try:
            hdlr = globals().get('gen_' + flag)
            if hdlr is not None:
                con = hdlr(con, ssid=ssid, user=user, pwd=pwd, **k)
        except ValueError as e:
            return (False, str(e))
        except Exception:
            continue

    con.pop('device', None)
    con.pop('active', None)
    con.pop('active_connection', None)
    con.pop('obj').Update(con.deepcopy(dict))
    return (True, 'OK')


def list_connections():
    '''
    example of a connection:
    {
        '802-11-wireless': {
            'mode': 'infrastructure',
            'security': '802-11-wireless-security',
            'ssid': 'TP-LINK_xxxx',
            'mac-address': '00:00:00:00:00:00',
        },
        '802-11-wireless-security': {
            'auth-alg': 'open',
            'key-mgmt': 'ieee8021x',
        },
        '802-1x': {'identity': 'username', 'password': 'password'},
        'connection': {
            'id': 'TP-LINK_xxxx',
            'interface-name': 'wlp2s0',
            'type': '802-11-wireless',
            'uuid': '9debed9f-ff63-452f-917d-d5c2331e2568',
        },
        'ipv4': {'method': 'auto'},
        'ipv6': {'method': 'auto'},
        'obj': <NetworkManager.Connection at 0x7f8814e87eb8>,
        'device': <NetworkManager.Wireless at 0x7f8815053be0>,
        'active': True,
        'active_connection':
            <NetworkManager.ActiveConnection at 0x7f3496e6e2d0>,
    }
    '''
    active_ssids = {
        ac.Connection.GetSettings()['connection']['id']: ac
        for ac in nm.ActiveConnections
    }

    cons = AttributeList()
    for con in NetworkManager.Settings.ListConnections():
        con_d = AttributeDict(con.GetSettings(), obj=con)
        if con_d.connection.get('read-only') is True:
            continue
        for key, section in con.GetSecrets().items():
            con_d[key].update(section)
        con_d.active = con_d.connection.id in active_ssids
        con_d.active_connection = active_ssids.get(con_d.connection.id)
        con_d.device = get_device_by_iface(dtype={
            '802-11-wireless': NetworkManager.NM_DEVICE_TYPE_WIFI,
            '802-3-ethernet': NetworkManager.NM_DEVICE_TYPE_ETHERNET,
            'gsm': NetworkManager.NM_DEVICE_TYPE_MODEM,
        }.get(con_d.connection.type, con_d.connection.type)) or wlan0
        cons.append(con_d)
    return cons


def get_connection_by_ssid(ssid):
    for con in list_connections():
        if con.connection.id == ssid:
            return con


def wifi_connections():
    lst = []
    for con in list_connections():
        con.pop('device')
        con.pop('obj')
        lst.append(con.deepcopy(dict))
    return lst


def list_accesspoints(interface=None):
    '''
    example of a hotspot(accesspoint):
    {
        'ssid': u'BUAA-Mobile',
        'frequency': ['2.462 GHz'],
        'mac_address': '70:BA:EF:D2:49:52',
        'mode': 'infra',
        'encrypted': True,
        'encryption_type': ['key_mgmt_psk', 'pair_ccmp']
        'strength': -39,
        'quality': '30/70',
        'maxbitrate': '54 Mb/s',
        'saved': True,
        'status': 'Disconnected'
        # 'lastseen': 1325821,
        'obj': <NetworkManager.AccessPoint at 0x7f8815045748>
    }
    '''
    if interface is not None:
        dev = get_device_by_iface(interface) or wlan0
    else:
        dev = wlan0

    con_ssids = [con.connection.id for con in list_connections()]
    aps = AttributeList()
    for ap in sorted(dev.GetAccessPoints(), key=lambda ap: -ap.Strength):
        ap_d = AttributeDict(obj=ap)
        for attr in ap.properties:
            ap_d[attr.lower()] = getattr(ap, attr)
        ap_d.ssid        = ensure_unicode(ap_d.get('ssid', 'Unknown'))
        ap_d.saved       = ap_d.ssid in con_ssids
        ap_d.frequency   = ['%.3f GHz' % (ap_d.get('frequency', 0) / 1000.0)]
        ap_d.maxbitrate  = '%d Mb/s' % int(ap_d.get('maxbitrate', 0) / 1000.0)
        ap_d.mac_address = ap_d.pop('hwaddress', ':'.join(['00'] * 6))
        ap_d.mode        = AP_MODE(ap_d.get('mode', 2))[0]
        ap_d.strength    = int(ap_d.get('strength', 0) * 0.7)  # 0 ~ 70
        ap_d.quality     = '%d/70' % ap_d.strength
        ap_d.strength    = ap_d.strength - 100  # -100 ~ -30, unit: dB
        ap_d.encrypted   = AP_FLAGS(ap_d.pop('flags', 0))[0] != 'none'
        ap_d.encryption_type = AP_SEC(
            ap_d.pop('wpaflags'), ap_d.pop('rsnflags'))
        if 'none' in ap_d.encryption_type:
            ap_d.encryption_type.remove('none')
        if ap_d.ssid == getattr(dev.ActiveAccessPoint, 'Ssid', ''):
            ap_d.status = get_dev_status(dev)
        else:
            ap_d.status = 'Disconnected'
        ap_d.pop('lastseen')
        if ap_d.ssid in aps.ssid:
            target = aps[aps.ssid.index(ap_d.ssid) - len(aps)]
            target.frequency = sorted(set(  # ordered unique list
                target.frequency + ap_d.frequency
            ))
            if int(target.maxbitrate[:-5]) < int(ap_d.maxbitrate[:-5]):
                target.maxbitrate = ap_d.maxbitrate
        else:
            aps.append(ap_d)
    return aps


def get_accesspoint_by_ssid(ssid):
    for ap in list_accesspoints():
        if ap.ssid == ssid:
            return ap


# =============================================================================
# APIs
#
def wifi_accesspoints(interface=None):
    lst = []
    for ap in list_accesspoints(interface):
        ap.pop('obj')
        lst.append(ap.deepcopy(dict))
    return lst


def wifi_connect(ssid, user=None, pwd=None, **k):
    if wifi_status() is False:
        #  wifi_enable()
        return (False, 'WiFi disabled')
    if get_connection_by_ssid(ssid) is None:
        add_connection(ssid, user, pwd, **k)
    elif user is not None or pwd is not None:
        update_connection(ssid, user, pwd, **k)
    con = get_connection_by_ssid(ssid)
    dev = k.get('dev', con.device) or wlan0  # proi: arg > conn > default
    status = get_dev_status(dev)
    if status == 'Connected':
        dev.Disconnect()
    elif status == 'Disconnected':
        pass
    else:
        return (False, status)
    ac = nm.ActivateConnection(con.obj, dev, '/')
    #  return (ac in nm.ActiveConnections, 'Connected')
    return (ac.Connection == con.obj, 'Connected')


def wifi_disconnect(ssid, **k):
    con = get_connection_by_ssid(ssid)
    if con is None:
        return (False, 'Connection on `{}` not saved yet.'.format(ssid))
    if not con.active:
        return (False, 'Not connected to `{}` yet.'.format(ssid))
    try:
        nm.DeactivateConnection(con.active_connection)
        dev = con.device or k.get('dev', wlan0)  # proi: conn > arg > default
        dev.Disconnect()
    except Exception as e:
        return (False, str(e))
    return (True, 'Disconnected from `{}`'.format(ssid))


def wifi_forget(ssid, **k):
    con = get_connection_by_ssid(ssid)
    if con is None:
        return (False, 'Connection on `{}` not saved yet.'.format(ssid))
    try:
        con.obj.Delete()
    except Exception as e:
        return (False, str(e))
    return (True, 'Connection settings of `{}` deleted.'.format(ssid))


def wifi_toggle(boolean):
    boolean = get_boolean(boolean)
    try:
        nm.Enable(boolean)
    except dbus.exceptions.DBusException as e:
        if e.get_dbus_name() != \
                'org.freedesktop.NetworkManager.AlreadyEnabledOrDisabled':
            return (False, str(e))
        return (True, 'already ' + ('enabled' if boolean else 'disabled'))
    return (wifi_status(boolean), 'success')


wifi_enable = functools.partial(wifi_toggle, True)
wifi_disable = functools.partial(wifi_toggle, False)


def wifi_status(action=None):
    if action in [True, 'on', 'ON', 'On']:
        return (
            nm.WirelessHardwareEnabled and
            nm.WirelessEnabled and
            nm.NetworkingEnabled
        ) is True
    elif action in [False, 'off', 'OFF', 'Off']:
        return (
            nm.WirelessEnabled or
            nm.NetworkingEnabled
        ) is False
    else:
        return nm.WirelessEnabled


# THE END
