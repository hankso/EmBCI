## 0.2.1 [2019-09-15]
- Add `from __future__ import absolute_import, division, print_function` to each module.
- Use ``//`` for floor division and ``/`` for float division.
- [WebUI] HTML snippets loader support keywords arguments by setting attributes like ``data-foo="bar"``. Add webui debug application runner and pick random port.
- [Drivers] Add package `embci.drivers`. Move `embci.utils.xxx_api` to `embci.drivers.xxx` as hardware APIs.
- [Utils] Add `get_free_port` to resolve an avaiable port number. Support event sending and receiving by EventIO system implemented at `embci.utils._event`
- [Speller] Subapp SSVEP mind-typing constructed. Will be tested soon.
- [Recorder] Add snippet `div#recorder` in `recorder-box.html`.

## 0.2.0 [2019-09-01]
- [Apps] Project `DBS` is removed from EmBCI and will be maintained by a business company.
- [Apps] Remove `DisplaySPI` and add subapp `DisplayWeb`.
- [Utils] Move `minimize` as standalone function. Logger stack info py 2 & 3 compatiable. Add `validate_filename` & `Namespace`.
- [Utils] Add `obfuscation` to distribute python code in dynamic linked library format.
- [JSONRPC] Add `NoExist` type and support for multiple instance registration.
- [WebUI] Add package `Numjs`. Rename `xxxDIR` to `DIR_xxx` and `__dir__` to `__basedir__`. Support refresh/rescan subapps at runtime.
- [WebUI] Support preventing subapps from loading by command line arguments `python -m embci.webui --exclude app1 app2`
- [Tools] Move `embci_tool` to `embci.apps.system`. Add template.py for python source files.
- [Setup.py] Load requirements.txt from absolute path.
- [configs] Load from configuration files when imported and export a dict at `embci.configs.settings`. Set `ENSURE_DIR_EXIST = True` in conf files if you want to create necessary directories.
- [io] Readers now get new valid name automatically by searching pidfiles. Add `hook_before` and `hook_after`.

## 0.1.6 [2019-07-04]
- [WebUI] Add supports for HTML snippets & navbar.html & bottom.html.
- [WebUI] Resolve battery level from ESP32 and render it to navbar.
- [ESP32] Support set/get Channel/DataSource/Gain/Impedance/SampleRate/Bias.
- [ESP32] Add second order IIR realtime filter and use looply-level-detection instead of interrupt.
- [Apps] Add subapp `auth`.
- [DBS] Hide DBS.utils source code with `Cython` and `GCC`. Add `libdbs_<py>_<arch>.so`.
- [DBS] New UI composed of 8 channels realtime & single channel frequency display
- [Record] Integrate recording interface to DBS HTML.
- [Streaming] Add function `send_message_streaming` for communicating from other process.

## 0.1.5 [2019-5-01]
- [DBS] Hide source code of data-processing algorithms with pre-compiled binary files.
- [Apps] Sub-app `WiFi` implemented as a web-based client of freedesktop NetworkManager, working on wireless card `AP6212` at STA+AP mode.
- [Apps] Support updating OTA (On-The-Air) by simple `git pull`.
- [WebUI] Upgrade `jQuery` to v3.4.1 and `Bootstrap` to v4.3.
- [WebUI] Immegrate from `glyphicon` to `font-awesome`.

## 0.1.4 [2019-3-23]
- [Doc] Add basic documentations.
- [Apps] Rename and move lots of DisplaySPI datafiles.
- [Apps] Add project `Speller`.
- [EmBCI] Add `PytestRunner` and func `test` in each module for runtime testing.
- [ESP32] New feature: turn into sleep mode to reduce power consumption.

## 0.1.3 [2019-3-11]
- [DBS] Change from `ESP32SPIReader` to `PylslReader` in embci.apps.DBS.
- [DBS] Save userinfo as cache to client(browser) for accessing report PDF.
- [Apps] Make data-streaming an individual task @ `embci.apps.streaming`.
- [Utils] Change `find_wifi_hotspots` output to type of `AttributeDict`.
- [WebUI] Move GeventWebsocketServer `log` to `logger` to log requests properly.
