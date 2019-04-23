# File: EmBCI/files/esp32/Makefile
# Author: hank
# Webpage: https://github.com/hankso
# Time: Tue 23 Apr 2019 19:35:05 UTC
#
# ESP32 Makefile used in EmBCI
#
# On-shield ESP32 is directly connected to OrangePi UART with RX && TX only.
# Without DTR/DSR connection, arm can NOT soft reset ESP32. USB-to-TTL converter
# on many ESP32 development board will support this feature, but here we have
# to use `reset_esp.py` to reset ESP32 by GPIO EN && BOOT.

ifneq ($(shell whoami), root)
$(error "run as root please")
endif

#################################################################################
# variables
#
ROOTDIR    := $(patsubst %/,%, $(dir $(abspath $(MAKEFILE_LIST))))
TOOLDIR    := $(realpath $(ROOTDIR)/../../tools)
BURNING    := $(TOOLDIR)/esptool.py
RESET_ESP  := $(TOOLDIR)/reset_esp.py
BINDIR     := $(ROOTDIR)/firmware

# MONITOR    = screen -h 200
MONITOR    := python -m serial.tools.miniterm --rts 0 --dtr 0 --raw

FIRMWARE   := \
	0x1000  $(BINDIR)/bootloader.bin \
	0x8000  $(BINDIR)/default.bin \
    0xe000  $(BINDIR)/boot_app0.bin \
    0x10000 $(BINDIR)/ESP32_Sandbox.ino.bin

ifneq ($(findstring Orange Pi Zero Plus 2, \
		$(shell cat /etc/armbian-release 2> /dev/null)), )
PORT       = /dev/ttyS2
else
PORT       = /dev/ttyS1
endif
BAUD       = 115200

#################################################################################
# flags
#
ESP_FALG   := --chip auto --before no_reset --after no_reset
ESP_FLAG   += --port ${PORT} --baud $(BAUD)

FLASH_FLAG := --compress --flash_freq 80m --flash_mode dio --flash_size detect

#################################################################################
# targets
#
.PHONY: all flash monitor sleep wakeup reset

all: help

compile:
	@echo "not implemented yet"

clean:
	@echo "not implemented yet"

flash:
	@$(RESET_ESP) flash         # reset esp to flash mode, wait for burning
	@$(BURNING) $(ESP_FLAG) write_flash $(FLASH_FLAG) $(FIRMWARE)
	@$(RESET_ESP)               # reset esp to normal mode

monitor:
	@$(MONITOR) $(PORT) $(BAUD)

sleep:
	@echo "not implemented yet"

wakeup:
	@echo "not implemented yet"

reset:
	@$(RESET_ESP)

help:
	@echo "Welcome to EmBCI-ESP32 burning Makefile. Some useful targets:"
	@echo ""
	@echo "make all - Build app, bootloader, partition table"
	@echo "make flash - Flash app, bootloader, partition table to Onshield ESP32"
	@echo "make monitor - Use \`miniterm.py/screen\` as monitor on serial"
	@echo "make reset - Hard reset of ESP32 by pulsing on BOOT PIN"
	@echo "make sleep - Turn ESP32 into sleep mode"
	@echo "make wakeup - Wake up ESP32 from ultra low power (sleep) mode"
	@echo ""
	@echo "See \`EmBCI/files/esp32/README.md\` for more."

# @echo "make clean - Remove all build output"
# @echo "make compile - Remove all build output"
