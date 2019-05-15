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
Want to integrate an user interface into your application? `EmBCI` provides you a easy-extenable web-based one! Simply create a [`bottle`](https://bottlepy.org/docs/dev/) loadable HTTPServer to handle HTTP requests and assign this server object to a variable named `application` in `__init__.py`. And that's all! Just leave all other jobs to `embci.webui` subapps auto-loader.

## Note
- bottle loadable HTTPServer means:
    - bottle built-in HTTP development servers based on `bottle.ServerAdapter`
    - [paste](http://pythonpaste.org/), [fapws3](https://github.com/william-os4y/fapws3), [bjoern](https://github.com/jonashaag/bjoern), [gae](https://developers.google.com/appengine/), [cherrypy](http://www.cherrypy.org/)... run `python -c "import bottle; print(bottle.server_names)"` to see more supported servers.
    - any other [WSGI](http://www.wsgi.org/) capable HTTP server

- URL of user apps will be `http://${EmBCI_WEBUI_HOST}/apps/${MyApp}`. If your server will respond "helloworld" when `index.html` is requested, you will see the "helloworld" string by `GET http://${EmBCI_WEBUI_HOST}/apps/${MyApp}/index.html`

- Neccessary files used in web application must be added to correct folder, such as `js/*` and `css/*`. You can use either local resources or embci.webui global resources, for example:
    - use syntax `<script src="js/common.js"></script>` to access file at `${MyApp}/js/common.js`.
    - use syntax `<img src="/images/logo.png" alt="EmBCI logo">` to access file at `${embci.webui.__dir__}/images/logo.png`.

## Example of bottle built-in server
```python
# content of NewApp/__init__.py
import os
import bottle
__dir__ = os.path.dirname(os.path.abspath(__file__))

@bottle.route('/index.html')
def index(name):
    name = bottle.request.get_cookie('name', 'new_guest')
    if name == 'new_guest':
        bottle.respond.set_cookie('name', 'asdf')
    return bottle.template(os.path.join(__dir__, 'index.html'), name=name)

application = bottle.default_app()
```

```html
# content of NewApp/index.html
<html>
<head>
    <meta charset="utf-8">
    <title>example</title>
</head>
<body>Hello {{name}}! Welcome to my WebApp!</body>
</html>
```

Result of accessing URL `http://${EmBCI_WEBUI_HOST}/apps/newapp/index.html` will be string `Hello new_guest! Welcome to my WebApp!`



## Example of
```python
# content of MyApp/server.py


# content of MyApp/__init__.py
from .server import server as application
```
