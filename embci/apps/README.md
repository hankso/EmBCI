# EmBCI Applications
EmBCI suppport

# Getting started
`embci.apps` comes with an [example project](example). It's a good place to start developing your own app. Also there are some basic subapps under `embci.apps` folder. Once you've found a similar project like yours, copy the project folder and go through the source code, modify them and build yours.
- [recorder](recorder): Record and save stream data into `.mat` or `.fif` file
- [streaming](streaming): Create a global data-stream as a data broadcaster
- [WiFi](WiFi): Search, display and connect to WiFi hotspots through WebUI, mostly used on `ARM`
- [sEMG](sEMG): Hand gesture recognition by classification on sEMG bio-signal
- [Speller](Speller): SSVEP-based mind-typing system(**under-developing**)

# WebUI
Want to integrate an user interface into your application? `EmBCI` provides you a easy-extenable web-based one! Simply create a `bottle` loadable HTTPServer to handle HTTP requests and assign this server object to variable `application`. That's all! Then just leave other jobs to the `embci.webui subapps auto-loader`.

## Note
- `bottle` loadable HTTPServer means:
    - bottle built-in HTTP development servers based on `bottle.ServerAdapter`
    - [paste](http://pythonpaste.org/), [fapws3](https://github.com/william-os4y/fapws3), [bjoern](https://github.com/jonashaag/bjoern), [gae](https://developers.google.com/appengine/), [cherrypy](http://www.cherrypy.org/)... see `bottle.server_names` for more.
    - any other [WSGI](http://www.wsgi.org/) capable HTTP server

- URL of user apps will be `http://${EmBCI_WEBUI_HOST}/apps/${MyApp}`

- Neccessary files used in web application must be added to correct folder, such as `js/*` and `css/*`. You can use either local resources or embci.webui global resources, for example:
    - use syntax `<script src="js/common.js"></script>` to access file at `${MyApp}/js/common.js`.
    - use syntax `<img src="/images/logo.png" alt="EmBCI logo">` to access file at `${embci.webui.__dir__}/images/logo.png`.

## Example of bottle built-in server
```python
# content of MyApp/__init__.py
import os
import bottle
__dir__ = os.path.dirname(os.path.abspath(__file__))

@bottle.route('/index.html')
def index(name):
    return bottle.static_file('index.html', root=__dir__)

application = bottle.default_app()
```

## Example of
```python
# content of MyApp/server.py


# content of MyApp/__init__.py
from .server import server as application
```
