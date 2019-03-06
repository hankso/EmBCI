# EmBCI Hardware

# Connection
- Communicate with [ADS1299](http://www.ti.com/product/ADS1299) through SPI
interface on OrangePi pin `CS/PA13`, `CLK/PA14`, `MOSI/PA15` and `MISO/PA16`

- On shield Atmega328P(Arduino Uno/Nano) is connected to `UART2_TX/PA00` and
`UART2_RX/PA01`

- Control SSD1306 0.96' OLED screen by SPI or ILI9325 2.3' LCD screen through
on shield Arduino by serial

- Broadcast collected raw data from ADS1299 to wifi port 9999(default) by TCP
socket, there are two ways to grab data from network
    - Connect OrangePi to your LAN wifi network and check its IP address, you
    can login to router(e.g. TP-Link @ `192.168.1.1`) or use any other methods
    to get OrangePi IP address.
    - Set OrangePi as a wifi hotpot, connect your PC/laptop/phone to this
    network and this way OrangePi IP address will be `192.169.0.1`(usually)
