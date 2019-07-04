
## 0.1.6 [2019-07-04]
- [WebUI] Add supports for HTML snippets & navbar.html & bottom.html.
- [WebUI] Resolve battery level from ESP32 and render it to navbar.
- [ESP32] Support set/get Channel/DataSource/Gain/Impedance/SampleRate/Bias.
- [ESP32] Add second order IIR realtime filter and use looply-level-detection instead of interrupt.
- [Apps] Add subapp `auth`.
- [DBS] Hide DBS.utils source code with `Cython` and `GCC`. Add `libdbs_<py>_<arch>.so`.
- [DBS] New UI composed of 8 channels realtime & single channel frequency display
- [Record] Integrate recording interface to DBS HTML.
- [Streaming] Add function `send_message_streaming` for communicating from other process

## 0.1.5 [2019-5-01]
- [DBS] Hide source code of data-processing algorithms with pre-compiled binary files.
- [Apps] Sub-app `WiFi` implemented as a web-based client of freedesktop NetworkManager, working on wireless card `AP6212` at STA+AP mode.
- [Apps] Support updating OTA (On-The-Air) by simple `git pull`.
- [WebUI] Upgrade `jQuery` to v3.4.1 and `Bootstrap` to v4.3.
- [WebUI] Immegrate from `glyphicon` to `font-awesome`

## 0.1.4 [2019-3-23]
- [Doc] Add basic documentations.
- [Apps] Rename and move lots of DisplaySPI datafiles.
- [Apps] Add project `Speller`.
- [EmBCI] Add `PytestRunner` and func `test` in each module for runtime testing.
- [ESP32] New feature: turn into sleep mode to reduce power consumption.

## 0.1.3 [2019-3-11]
- [DBS] Change from `ESP32SPIReader` to `PylslReader` in embci.apps.DBS .
- [DBS] Save userinfo as cache to client(browser) for accessing report PDF.
- [Apps] Make data-streaming a seperate task @ embci.apps.streaming.
- [Utils] Change `find_wifi_hotspots` output to type of `AttributeDict`.
- [WebUI] Move GeventWebsocketServer `log` to `logger` to log requests properly.
