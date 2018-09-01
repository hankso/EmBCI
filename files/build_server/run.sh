#
# run this script to build server on Orange Pi Zero Plus(2)
#
# hankso
# email: 3080863354@qq.com
# page: https://github.com/hankso
#


if (( $EUID != 0  )); then
    echo "run as root please"
    exit
fi


#
# config apache2
#
# Apache2 is used to host server and load python bottle programs to generate
# dynamic html for clients(user's web browser)
#

# sites conf
SITE=/etc/apache2/sites-available/000-default.conf
mv $SITE $SITE.bak
cp 0-sites.conf $SITE

# server files
mkdir -p /var/www/pyemg
cp src/* /var/www/pyemg/

# other configs
a2enmod macro
service apache2 restart



#
# config hostapd
#
# Hostapd will turn WiFi chip into AP(Access Point) mode, thus you can
# find this available hotspot on your PC/mobile devices.
#

# hostapd.conf
HOSTAPD=/etc/apache2/hostapd.conf
mv $HOSTAPD $HOSTAPD.bak
cp 1-hostapd.conf $HOSTAPD
echo 'DAEMON_CONF="/etc/hostapd.conf"' >> /etc/default/hostapd
service hostapd restart



#
# config dhcpd
#
# Dhcpd can automatically select and distribute an IP address to devices that 
# connect to this WiFi hotspot, unless they are set to a static IP manually
#

# interface config wlan0 static ip 
INTF=/etc/network/interfaces
mv $INTF $INTF.bak
cp 2-interfaces $INTF
ifdown wlan0 && ifup wlan0

# dhcp daemon
DHCP=/etc/dhcp/dhcpd.conf
mv $DHCP $DHCP.bak
cp 3-dhcpd.conf $DHCP

# dhcp server
DHCPSERVER=/etc/default/isc-dhcp-server
mv $DHCPSERVER $DHCPSERVER.bak
cp 4-isc-dhcp-server $DHCPSERVER
service isc-dhcp-server restart



#
# config dnsmasq
#
DNS=/etc/dnsmasq.conf
mv $DNS $DNS.bak
cp 5-dnsmasq.conf $DNS
service dnsmasq restart



echo "All configuration done!"
