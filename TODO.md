
### Documents
- This page & README
- EmBCI lib docs

> Documentation is like sex: when it is good, it is very, very good; and when 
it is bad, it is better than nothing. - Dick B.

### Hardware Design
- ESP32
    - Serial connection higher baudrate (like 921600)
    - Act as a portable WiFi card: WiFi-echo (through Serial/I2C)
- PCB shielding cases
- 3-axis acceleration chip
- Layout
    - Move amplifier to bottom, USB cable to left edge and power button to left-upper corner.
    - Move power management components to the back of ESP32.

### Apps
- [ ] Auth: authentication before accessing websocket
- [ ] apps.system: automatic updating through WiFi & git-server

### Application
- Sign language sEMG recognition
- Motor Imagery
