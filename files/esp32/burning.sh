#!/bin/bash
#
# EmBCI
# Script used to flash ESP32 firmware
#
# On-shield ESP32 is directly connected to OrangePi UART by pin RX && TX only.
# Without DTR/DSR connection, arm can NOT soft reset ESP32. USB-to-TTL converter
# on many ESP32 development board will support this feature, but on EmBCI shield
# we have to reset ESP32 by GPIO EN && BOOT.
#

if (( $EUID != 0 )); then
    echo "run as root please"
    exit
fi


# reset esp to flash mode, wait for burning
./reset_esp.py flash

# burn firmware with esptool.py ( offered by Espressif Pte. Ltd. )
./esptool.py \
    --chip esp32 \
    --port /dev/ttyS1 \
    --baud 115200 \
    --before no_reset \
    --after no_reset \
    write_flash -z \
    --flash_mode dio \
    --flash_freq 80m \
    --flash_size detect \
    0x1000  ./firmware/bootloader.bin \
    0x8000  ./firmware/default.bin \
    0xe000  ./firmware/boot_app0.bin \
    0x10000 ./firmware/ESP32_Sandbox.ino.bin

# reset esp to normal mode
./reset_esp.py
