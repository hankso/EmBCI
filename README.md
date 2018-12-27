## EmBCI
EmBCI is Embedded Brain Computer Interface, a bio-signal acquisition and processing platform.

It's composed of a **Hardware**, a **Python library** and a **Linux Service Interface**.

## Hardware

## Python lib

## Service

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
