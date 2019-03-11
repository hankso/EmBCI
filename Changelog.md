
## EmBCI-0.1.3 [2019-3-11]
- [DBS] Change from `ESP32SPIReader` to `PylslReader` in embci.apps.DBS .
- [DBS] Save userinfo as cache to client(browser) for accessing report PDF.
- [Apps] Make data-streaming a seperate task @ embci.apps.streaming.
- [Utils] Change `find_wifi_hotspots` output to type of `AttributeDict`.
- [WebUI] Move GeventWebsocketServer `log` to `logger` to log requests properly.
