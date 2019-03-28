#!/bin/bash
#
# EmBCI
# Script used to flash ESP32 firmware
#
# On-shield ESP32 is directly connected to OrangePi UART with RX && TX only.
# Without DTR/DSR connection, arm can NOT soft reset ESP32. USB-to-TTL converter
# on many ESP32 development board will support this feature, but here we have
# to reset ESP32 by GPIO EN && BOOT.
#

if (( $EUID != 0 )); then
    echo "run as root please"
    exit
fi

DIR=`dirname ${BASH_SOURCE[0]}`
FDIR=${DIR}/firmware
RESET=${DIR}/reset_esp.py

# reset esp to flash mode, wait for burning
${RESET} flash

# select ESP32 serial port
[[ -f /etc/armbian-release ]] && source /etc/armbian-release
if [[ `grep "Orange Pi Zero Plus 2" /etc/armbian-release` ]]; then
    PORT=/dev/ttyS2
else
    PORT=/dev/ttyS1
fi

# burn firmware with esptool.py ( offered by Espressif Pte. Ltd. )
${DIR}/esptool.py \
    --chip esp32 \
    --port ${PORT} \
    --baud 500000 \
    --before no_reset \
    --after no_reset \
    write_flash -z \
    --flash_mode dio \
    --flash_freq 80m \
    --flash_size detect \
    0x1000  ${FDIR}/bootloader.bin \
    0x8000  ${FDIR}/default.bin \
    0xe000  ${FDIR}/boot_app0.bin \
    0x10000 ${FDIR}/ESP32_Sandbox.ino.bin

# reset esp to normal mode
${RESET}
