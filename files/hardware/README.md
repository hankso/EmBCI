# EmBCI Shield

## Board Connection
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

## Electrodes
Passive electrodes have no inbuit circuitry. You may need paste/gel between it and subject's skin/scalp for better signal. Electrodes can be round or needle metal things coated with special alloys, for example gold, tin and silver. Ag / AgCl are supposed to be best.

Comparing to passive electrodes, active electrodes work by putting a unity-gain amplifier right next to the electrode up on the scalp. This greatly improves the signal quality and avoids the skin preparation like conductive paste and gel.

A brief history of active eletrodes:
- Jarek Foltynski created the initial designs and prototypes. [link](http://bioera.net/ae/)
- Joerg Hansmann refined the v2 circuit design.
- Ian Vincent introduced the idea of using multiple-pin electrodes which can pass through the hair easily.
- Joe Street created a modified design using power cells instead of requiring power from ADC board. [link](http://openeeg.sourceforge.net/doc/hw/joe_ae/)
- Jim Peters constructed a version of Joerg's design. [link](http://uazu.net/eeg/ae.html)
- Pedro Ortega created a simplified version without the shielding/guarding. [link](http://www.dcc.uchile.cl/~peortega/ae/)
