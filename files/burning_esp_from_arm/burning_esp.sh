./reset-waiting-for-download.py
./esptool.py --chip esp32 --port /dev/ttyS1 --baud 115200 --before no_reset --after no_reset write_flash -z --flash_mode dio --flash_freq 80m --flash_size detect 0xe000 boot_app0.bin 0x1000 bootloader.bin 0x10000 ESP32_Sandbox.bin 0x8000 default.bin
./reset-only.py
