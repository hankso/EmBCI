.. image:: https://raw.github.com/hankso/EmBCI/master/files/images/logo-blue.png
   :alt: EmBCI LOGO
   :align: center
   :target: https://hankso.github.io/EmBCI

-------

.. image:: https://img.shields.io/travis/hankso/EmBCI/master.svg?label=Travis%20CI
   :alt: Travis CI
   :target: https://travis-ci.org/hankso/EmBCI

.. #image:: https://img.shields.io/codecov/c/github/hankso/EmBCI.svg
   :alt: Codecov
   :target: https://codecov.io/gh/hankso/EmBCI

.. image:: https://img.shields.io/github/languages/top/hankso/EmBCI.svg
   :alt: GitHub top language
   :target: https://hankso.github.io/EmBCI

.. image:: https://img.shields.io/github/languages/code-size/hankso/EmBCI.svg
   :alt: GitHub code size in bytes
   :target: https://github.com/hankso/EmBCI/archive/master.zip

.. image:: https://img.shields.io/github/license/hankso/EmBCI.svg
   :alt: GitHub License
   :target: https://opensource.org/licenses/MIT

.. #image:: https://img.shields.io/github/release/hankso/EmBCI.svg
   :alt: GitHub release
   :target: https://github.com/hankso/EmBCI/releases

.. image:: https://img.shields.io/pypi/v/EmBCI.svg
   :alt: PyPI Version
   :target: https://pypi.org/project/EmBCI/

.. image:: https://img.shields.io/pypi/pyversions/EmBCI.svg
   :alt: Python Version
   :target: https://pypi.org/project/EmBCI/

.. #image:: https://img.shields.io/pypi/status/EmBCI.svg
   :alt: PyPI Status
   :target: https://pypi.org/project/EmBCI/

.. image:: https://img.shields.io/github/tag-date/hankso/EmBCI.svg
   :alt: GitHub tag
   :target: https://github.com/hankso/EmBCI/tags

.. #image:: https://img.shields.io/github/stars/hankso/EmBCI.svg?style=social
   :alt: GitHub stars
   :target: https://github.com/hankso/EmBCI/stargazers




Welcome to the EmBCI!
=====================
English | `中文 <https://github.com/hankso/EmBCI/blob/master/README_zh.md>`_

**EmBCI** is fully open source on Github since release v.0.2.3!

This README file is only a quick start. Check out full documentation `here <https://hankso.github.io/EmBCI>`_.

**EmBCI** is still under developing. Any contributions are welcomed.

.. Contents::

.. - `What is EmBCI?`_
.. - `Features`_
.. - `Hardware support`_
.. - `Software support`_
..     - `Requirements`_
..     - `Installation`_
.. - `Linux service interface`_
.. - `Configuration`_
.. - `Documentation`_
.. - `Files outline`_
.. - `Supported gyms`_
.. - `License`_
.. - `Useful links`_



What is EmBCI?
==============
**EmBCI** is the abbreviation of **Embedded Brain-Computer Interface**, a bio-signal acquisition and processing platform.

It is composed of a high precision, wearable, 8-channel bio-signal measuring hardware and a signal processing python library optimized for embedded devices.

Users can quickly develop their own applications based on EmBCI. And EmBCI comes with some interesting apps, `check out here`__!

__ `embci.apps`_



Features
========
- **Fast prototyping**: EmBCI provide lots of data streaming and IO interfaces. Build your app within 100 lines of code!
- **Signal processing**: baseline-correction, denoising, time-frequency algorithms, and many many more.
- **Multiple Biosignal**: support EEG, EMG, ECG... We implemented gesture-recognition based on sEMG and SSVEP Speller based on EEG in the same platform.
- **It's embedded**: 40mm x 40mm wearable device, small but powerful, get rid of PC!
- **WiFi connection**: data visualization, files management, visual stimulus keyboard and more Web UI applications are accessable by simply connect to a hotspots.



Hardware support
================

``EmBCI Shield`` is a PCB board designed to measure, denoise, buffer and transfer bio-signals.
Currently, the stable version is ``EmBCI Shield Rev.A7``.

It integrates:

- ADS1299_ from `Texas Instruments <http://www.ti.com/product/ADS1299/description>`_:
    Low-noise 8-Channels 24-Bits ADC for Biopotential Measurements

- ESP32_ from `Espressif <https://www.espressif.com/en/products/hardware/esp32/overview>`_:
    Tensilica Xtensa Dual-core 32-Bits Processor with WiFi and Bluetooth

- Power management chips and others

`EmBCI Shield`__ can also be used as extension board.

__ `files/hardware`_

.. README will be included in docs/readme.rst, so use absolute URL here
.. _ADS1299:  https://github.com/hankso/EmBCI/blob/master/tools/ADS1299-Datasheet.pdf
.. _ESP32:    https://github.com/hankso/EmBCI/tree/master/files/esp32



Software support
================
Requirements
------------
- on embedded linux: wifi, serial, sysgpio, spidev
- on others platforms: wifi, serial/usb


Installation
------------
Install from pypi
+++++++++++++++++
:code:`pip install embci`

Install from source
+++++++++++++++++++
.. code:: bash

    git clone --depth=1 -b release https://github.com/hankso/EmBCI.git
    cd EmBCI
    sudo python -m pip install -r ./requirements.txt
    python setup.py build && sudo python setup.py install

Developer mode
++++++++++++++
For those who want to build their applications based on EmBCI, you may want to install ``embci`` in developer mode with:

.. code:: bash

    git clone -b master https://github.com/hankso/EmBCI.git && cd EmBCI
    sudo python -m pip install --editable .

Then you can code and test your app.

EmBCI provides lots of useful input/output interfaces including an extendible WebUI so that one can easily implement applications. See `embci.io`_, `embci.webui`_ and `embci.apps`_ for more information.

Platform specifics
++++++++++++++++++
On ``arm`` and ``aarch64`` embedded Linux platforms, ``setup.py`` will also install Linux service configuration files.

To autostart EmBCI applications at boot on PC and other systems, you have to `config autorun manually`__.

__ `files/service`_


Extra files
-----------
TODO: only install the package is not enough


Linux service interface
=======================
EmBCI has a Linux Service interface to work properly on embedded devices.

Both ``System-V style`` scripts and ``System D service manager`` scripts are provided.

See `files/service`_ for more details.



Configuration
=============
EmBCI use `INI-Style <https://en.wikipedia.org/wiki/INI_file>`_ configuration files with an extention ``.conf``.

Here's an example::

    # File: EmBCI/files/service/embci.conf
    # Lines beginning with '#' or ';' are ignored and will be used as comments.

    [Path]
    DIR_BASE = /usr/share/embci

    [Platform]
    HARDWARE = Rev.A7
    BOARD = Orange Pi Zero Plus 2

    [GPIO]
    PIN_ESP32_DRDY = PD11
    PIN_ILI9341_DC = PA02

    [Network]
    WEBUI_HOST = 0.0.0.0
    WEBUI_PORT = 8080


When you type :code:`import embci`, it will automatically search for configuration files and load them into ``embci.configs`` with following priority(from low to high)::

    project config file: "${EmBCI}/files/service/embci.conf"
     system config file: "/etc/embci/embci.conf"
       user config file: "~/.embci/embci.conf"

On Windows system::

    project config file: "${EmBCI}/files/service/embci.conf"
     system config file: "${APPDATA}/embci.conf"
       user config file: "${USERPROFILE}/.embci/embci.conf"

See `docs/Configurations`_ for more details.

.. _docs/Configurations:  https://embci.readthedocs.io/en/latest/configurations.html



Documentation
=============
Get full documentation `here <https://hankso.github.io/EmBCI>`_.



Files outline
=============
+-------------------+-------------------------------------------------------+
| Folder            | Description                                           |
+===================+=======================================================+
| `embci`_          | Data-processing algorithms, IO, WebUI and frameworks  |
+-------------------+-------------------------------------------------------+
| `embci.apps`_     | Basic applications and an example app project         |
+-------------------+-------------------------------------------------------+
| `embci.gyms`_     | Output classification result to gyms to control games |
+-------------------+-------------------------------------------------------+
| `embci.io`_       | Stream Readers/Commanders, data save/load functions   |
+-------------------+-------------------------------------------------------+
| `embci.utils`_    | Miscellaneous tools: useful decorators and functions  |
+-------------------+-------------------------------------------------------+
| `embci.viz`_      | Visualization: SPIScreen, Matplotlib, and Qt          |
+-------------------+-------------------------------------------------------+
| `embci.webui`_    | Web-based User Interface                              |
+-------------------+-------------------------------------------------------+
| `files/avr`       | On shield ``Atmega328P`` firmware (**Deprecated**)    |
+-------------------+-------------------------------------------------------+
| `files/esp32`_    | On shield ``ESP32`` firmware and burning tools        |
+-------------------+-------------------------------------------------------+
| `files/cases`_    | 3D models files in ``SolidWorks`` and ``STL`` format  |
+-------------------+-------------------------------------------------------+
| `files/hardware`_ | ``EmBCI Shield`` files in ``Eagle`` format            |
+-------------------+-------------------------------------------------------+
| `files/service`_  | Linux service configurations                          |
+-------------------+-------------------------------------------------------+

.. _files/esp32:     https://github.com/hankso/EmBCI/tree/master/files/esp32
.. _files/cases:     https://github.com/hankso/EmBCI/tree/master/files/cases
.. _files/hardware:  https://github.com/hankso/EmBCI/tree/master/files/hardware
.. _files/service:   https://github.com/hankso/EmBCI/tree/master/files/service

.. _embci:        https://github.com/hankso/EmBCI/blob/master/embci/__init__.py
.. _embci.apps:   https://github.com/hankso/EmBCI/tree/master/embci/apps
.. _embci.gyms:   https://github.com/hankso/EmBCI/tree/master/embci/gyms
.. _embci.io:     https://github.com/hankso/EmBCI/tree/master/embci/io
.. _embci.utils:  https://github.com/hankso/EmBCI/tree/master/embci/utils
.. _embci.viz:    https://github.com/hankso/EmBCI/tree/master/embci/viz
.. _embci.webui:  https://github.com/hankso/EmBCI/tree/master/embci/webui



Supported gyms
==============
Currently two environments have been implemented to use mind-control results to control movement. See `embci.gyms`_ for more.

Plane war game
--------------
Written by @ `buaawyz <https://github.com/buaawyz>`_.
See game `installation <https://github.com/hankso/gym_plane_python>`_ guide.

Run :code:`python main.py` first and then :code:`from gyms import PlaneClient as Client`


TORCS car game
--------------
See more at `gym_torcs <https://github.com/ugo-nama-kun/gym_torcs>`_. And `embci.io`_.TorcsCommander.



License
=======
MIT license. See `LICENSE.txt`_

.. _LICENSE.txt:  https://github.com/hankso/EmBCI/blob/master/LICENSE.txt



Useful links
============
- `Awesome-BCI <https://github.com/NeuroTechX/awesome-bci>`_
- `OpenBCI <https://github.com/openbci>`_
- `OpenViBE <http://openvibe.inria.fr/>`_
- `EEGLAB <http://sccn.ucsd.edu/eeglab/>`_
- `BCILAB <https://sccn.ucsd.edu/wiki/BCILAB>`_
