#!/usr/bin/env python
# coding=utf-8
#
# File: EmBCI/embci/apps/__main__.py
# Author: Hankso
# Webpage: https://github.com/hankso
# Time: Tue 05 Mar 2019 17:01:42 CST

'''Provide an app doc CLI interface by typing in `python -m embci.apps`'''

HELP = '''`embci.apps` comes with an [example project](example). It's a good
place to start developing your own app. Also there are some basic subapps under
`embci.apps` folder. Once you've found a similar project like yours, copy the
project folder and go through the source code, modify them and build yours.
'''

subapps = [
    ("recorder", "Record and save stream data into `.mat` or `.fif` file"),
    ("streaming", "Create a global data-stream as a data broadcaster"),
    ("WiFi", "Search, display and connect to WiFi hotspots through WebUI"),
    ("sEMG", "Hand gesture recognition by classification on sEMG bio-signal"),
    ("Speller", "SSVEP-based mind-typing system(**under-developing**)"),
]

if __name__ == "__main__":
    print(HELP)
    for app, info in subapps:
        print("{}: {}".format(app, info))

# THE END
