Reference to DBus API of NetworkManager
---------------------------------------

org.freedesktop.NetworkManager.AccessPoint:
    Properties:
        Flags: NM_802_11_AP_FLAGS
        WpaFlags: NM_802_11_AP_SEC
        RsnFlags: NM_802_11_AP_SEC
        Ssid: Name string of access point
        Frequency: in MHz
        HwAddress: BSSID of the access point
        Mode: NM_802_11_MODE
        MaxBitrate: in Kb/s
        Strength: signal quality in percent (0-100)
        LastSeen: timestamp in CLOCK_BOOTTIME seconds of the last found


org.freedesktop.NetworkManager.Device:
    Methods:
        Reapply(connection, version_id, flags=0):
            update the configuration of the connection without deactivating it
        GetAppliedConnection(flags=0) => (settings, version_id)
        Disconnect: disconnect a device and set autoconnect to False
        Delete: delete a device from NetworkManager and remove the interface
    Signals:
        StateChanged(new_state, old_state, reason):
            new_state, old_state: NM_DEVICE_STATE
            reason: NM_DEVICE_STATE_REASON
    Properties:
        Udi: universal device identifier
        Interface: name of devices's interface, like `wlan0` or `enp3s0`
        Driver
        DriverVersion
        FirmwareVersion
        Capabilities: NM_DEVICE_CAP
        State: NM_DEVICE_STATE
        StateReason => (state, reason): NM_DEVICE_STATE, NM_DEVICE_STATE_REASON
        ActiveConnection => currently applied connection and device
        Ip4Config
        Ip6Config
        Dhcp4Config
        Dhcp6Config
        Managed: whether this device is managed by NetworkManager
        Autoconnect
        DeviceType: NM_DEVICE_TYPE
        AvailableConnections => array of connections
        PhysicalPortId
        Mtu: maximum transmission unit
        Metered: NM_METERED
        LldpNeighbors => array of LLDP netghbors
        Real
        Ip4Connectivity: NM_CONNECTIVITY
        Ip6Connectivity: NM_CONNECTIVITY


org.freedesktop.NetworkManager.Device.Wireless:
    Methods:
        GetAllAccessPoints: list all access points
        RequestScan(a{sv} options): scan result at DBus.Properties.LastScan
    Signals:
        AccessPointAdded(access_point)
        AccessPointRemoved(access_point)
    Properties:
        HwAddress: active hardware address (mac address)
        PermHwAddress: permanent hardware address (mac address)
        Mode: NM_802_11_MODE
        Bitrate: in Kb/s
        AccessPoints: list of access points
        ActiveAccessPoint: current applied access point
        WirelessCapabilities: NM_WIFI_DEVICE_CAP


org.freedesktop.NetworkManager.Settings:
    Methods:
        ListConnections => array of connections
        GetConnectionByUuid(uuid) => connection
        AddConnection(settings_and_secrets)
        AddConnectionUnsaved(settings_and_secrets)
        LoadConnections(filename) => (status, failures)
        ReloadConnections: reload connection files from disk
        SaveHostname(hostname)
    Signals:
        NewConnection(connection)
        ConnectionRemoved(connection)
    Properties:
        Connections => array of connections
        Hostname
        CanModify: whether you can add or modify connections


org.freedesktop.NetworkManager.Settings.Connection:
    Methods:
        Update(properties)
        UpdateUnsaved(properties): Update without immediately save
        Delete
        GetSettings => settings
        GetSecrets([setting_name]) => secrets
        ClearSecrtes
        Save: save unsaved updates by `UpdateUnsaved`
        Update2
    Signals:
        Updated
        Removed
    Properties:
        Unsaved
        Flags: NM_SETTINGS_CONENCTION_FLAG
        Filename: file that stores the connection if it is saved


org.freedesktop.NetworkManager.Connection.Active:
    Properties:
        Connection => connection
        SpecificObject => access point
        Id => connection.GetSettings()['connection']['id']
        Uuid => connection.GetSettings()['connection']['uuid']
        Type => connection.GetSettings()['connection']['type']
        Devices => array of devices
        State: NM_ACTIVE_CONNECTION
        StateFlags: NM_ACTIVATION_STATE_FLAG
        Default
        Default6
        Ip4Config
        Ip6Config
        Dhcp4Config
        Dhcp6Config
        Vpn: whether this active connection is a VPN connection
        Master: path to the master device if the connection is a slave


org.freedesktop.NetworkManager.Ip4Config:
    Properties:
        AddressData => array of {'address': '0.0.0.0', 'prefix': 24}
        Gateway
        RouteData
        Nameservers => array of nameserver addresses
        NameserverData
        Domains
        Searches
        DnsOptions
        DnsPriority
        WinsServers
        WinsServerData


org.freedesktop.NetworkManager:
    Methods:
        Reload
        GetDevices => array of devices without placeholders
        GetAllDevices => array of all devices
        GetDeviceByIpIface(interface_name)
        ActivateConnection(connection, device, specific_object='/')
        AddAndActivateConnection(settings, device, specific_object='/')
        DeactivateConnection(active_connection)
        Sleep(bool): let NetworkManager daemon sleep or wake
        Enable(bool): whether managed interfaces are enabled/disabled
        GetPermissions => dict of permissions: bool
        SetLogging(level domains): level is ERR|WARN|INFO|DEBUG|TRACE|OFF|KEEP
        GetLogging => (level, domains)
        CheckConnectivity => NM_CONNECTIVITY
        CheckpointCreate(devices, rollback_timeout, flags):
            flags: NM_CHECKPOINT_CREATE_FLAG
        CheckpointDestroy(checkpoint)
        CheckpointRollback(checkpoint)
        CheckpointAdjustRollbackTimeout(checkpoint, timeout)
    Signals:
        CheckPermissions
        StateChanged(state)
        DeviceAdded(device)
        DeviceRemoved(device)
    Properties:
        Devices
        AllDevices
        Checkpoints
        NetworkingEnabled
        WirelessEnabled: writable
        WirelessHardwareEnabled
        WwanEnbaled: writable
        WwanHardwareEnbaled
        WimaxEnabled: writable
        WimaxHardwareEnabled
        ActiveConnections => array of active connections
        PrimaryConnection
        PrimaryConnectionType
        Metered: NM_METERED
        ActivatingConnection
        Startup
        Version
        Capabilities: NM_CAPABILITY
        State: NM_STATE
        Connectivity: NM_CONNECTIVITY
        ConnectivityCheckAvailable
        ConnectivityCheckEnabled: writable
        GlobalDnsConfiguration: writable
