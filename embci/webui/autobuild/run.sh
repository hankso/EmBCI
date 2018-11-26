#
# This script is used to config network on Orange Pi Zero Plus [2]
#
# Author: Hankso
# Email: 3080863354@qq.com
# Page: https://github.com/hankso
#


if (( $EUID != 0  )); then
    echo "run as root please"
    exit
fi

BOARD=".opi0+2"

targets=(
    # "/etc/apache2/sites-available/000-default.conf"
    "/etc/network/interfaces"
    "/etc/hostapd.conf"
    # "/etc/hostapd.conf"
    # "/etc/default/isc-dhcp-server"
    "/etc/dnsmasq.conf"
)


files=( 
    # "0-sites.conf${BOARD}"
    "1-interfaces"
    "2-hostapd.conf"
    # "3-dhcpd.conf"
    # "4-isc-dhcp-server"
    "5-dnsmasq.conf"
)

for index in "${!targets[@]}"
do
    target=${targets[$index]}
    target_t=$target.$(date +"%Y%m%d")
    file=${files[$index]}${BOARD}
    if [ -e ${target} ]; then
        mv $target $target_t 2> /dev/null
        echo "move $target to $target_t "

        cp $file $target 2> /dev/null
        echo "copy $file as $target"
    fi
done


# mod_wsgi-express install-module
# echo "LoadModule wsgi_module $(mod_wsgi-express module-location)" > /etc/apache2/mods-available/wsgi.load
# a2enmod macro wsgi
# service apache2 restart

ifdown -v wlan0 && ifup -v wlan0

service networking restart

service hostapd restart

service dnsmasq restart

echo "All configuration done!"
