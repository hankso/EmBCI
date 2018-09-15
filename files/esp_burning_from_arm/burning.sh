if (( $EUID !=0  )); then
    echo "run as root please"
    exit
fi

# reset esp to flash mode, waiting for burning
./reset-esp.py flash

# burn firmware by esptool.py ( offered by Espressif Pte. Ltd. )
cd firmware
../esptool.py \
    --chip esp32 \
    --port /dev/ttyS1 \
    --baud 115200 \
    --before no_reset \
    --after no_reset write_flash \
    -z \
    --flash_mode dio \
    --flash_freq 80m \
    --flash_size detect \
    0xe000 boot_app0.bin \
    0x1000 bootloader.bin \
    0x8000 default.bin \
    0x10000 ESP32_Sandbox.ino.bin
cd ../

# reset esp to normal mode
./reset-esp.py
