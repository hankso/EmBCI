#!/usr/bin/env python3
# coding=utf-8
#
# File: EmBCI/embci/apps/__main__.py
# Authors: Hank <hankso1106@gmail.com>
# Create: 2019-03-05 17:01:42

from . import __doc__

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
    print(__doc__)
    print(HELP)
    for app, info in subapps:
        print("{}: {}".format(app, info))
    print('See `README.md` for more information.')

# THE END
