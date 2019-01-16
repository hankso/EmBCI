## EmBCI
EmBCI is Embedded Brain Computer Interface, a bio-signal acquisition and processing platform.

It's composed of a **Hardware**, a **Python library** and a **Linux Service Interface**.

## Hardware

## Python lib

## Service
EmBCI has a `Linux` service interface to work properly on embedded devices.

More details at [files/service](files/service).


## Install
### Debian & Ubuntu & Windows
`pip install embci` **(to be implemented, not working now)**

### Install from source
```bash
git clone git@github.com:hankso/EmBCI.git && cd EmBCI
sudo python -m pip install -r ./requirements.txt
python setup.py build && sudo python setup.py install
```

This program is py2 && py3 compatiable.

## Output Interface
### Get data from matlab
- Here we use Orange Pi + EmBCI Shield Rev.A7
- Make sure Orange Pi and your PC are in same LAN
- Here's an example script to fetch data through socket in `Matlab`

```Matlab
% socket server on orangepi default listen on port 9999.
client = tcpclient('192.168.10.10', 9999)

% 8-channel float32 data --> 8_ch * 32_bits / 8_bits = 32 bytes data
data = client.read(32)

% unpack bytes into float32(single)
data = typecast(data, 'single')

% here data is 1x8 vector
data
```

## Project structure
|    folder     |    description    |
| :------------ | :---------------- |
|    embci      | Preprocessing algorithms, classifiers, WebUI and frameworks |
|   files/avr   | On shield Atmega328P firmware |
|  files/esp32  | On shield ESP32 firmware and burning tools |
| files/layouts | Saved SPI-Screen GUI layouts in `python-pickle` format |
| files/service | Linux service files |


## TODOs
### Documents
- This page & README
- embci lib docs

### Hardware Design
- ESP32
    - Serial connection higher baudrate (like 921600)
    - Act as a portable WiFi card: WiFi-echo (through Serial/I2C)
    - Change command interface from SPI to Serial
- ADS1299 better de-noising
- PCB shielding cases

### Algorithums
- SSVEP & P300
- ERP/EDP
- Motor Imagery

### Application
- Parkinson DBS treatment recovery
- Online SSVEP mind-typing
- Sign language sEMG recognition
