.. image:: https://raw.github.com/hankso/EmBCI/master/files/icons/logo.jpg

-------

.. image:: https://img.shields.io/travis/hankso/EmBCI/master.svg?label=Travis%20CI
    :alt: Travis (.org) branch
    :target: https://travis-ci.org/hankso/EmBCI

.. #image:: https://img.shields.io/codecov/c/github/hankso/EmBCI.svg
    :alt: codecov
    :target: https://codecov.io/gh/hankso/EmBCI

.. image:: https://img.shields.io/github/languages/top/hankso/EmBCI.svg
    :alt: GitHub top language

.. image:: https://img.shields.io/github/languages/code-size/hankso/EmBCI.svg
    :alt: GitHub code size in bytes
    :target: https://github.com/hankso/EmBCI/archive/master.zip

.. image:: https://img.shields.io/github/license/hankso/EmBCI.svg
    :alt: GitHub - License
    :target: https://opensource.org/licenses/MIT

.. #image:: https://img.shields.io/github/release/hankso/EmBCI.svg
    :alt: GitHub release
    :target: https://github.com/hankso/EmBCI/releases

.. image:: https://img.shields.io/pypi/v/EmBCI.svg
    :alt: PyPI - Version
    :target: https://pypi.org/project/EmBCI/

.. image:: https://img.shields.io/pypi/pyversions/EmBCI.svg
    :alt: Python Version
    :target: https://pypi.org/project/EmBCI/

.. #image:: https://img.shields.io/pypi/status/EmBCI.svg
    :alt: PyPI - Status
    :target: https://pypi.org/project/EmBCI/

.. image:: https://img.shields.io/github/tag-date/hankso/EmBCI.svg
    :alt: GitHub tag (latest by date)
    :target: https://github.com/hankso/EmBCI/tags

.. #image:: https://img.shields.io/github/stars/hankso/EmBCI.svg?style=social
    :alt: GitHub stars

.. default-role:: code



Welcome to the EmBCI!
=====================
This README file is only a quick start.
Check out full documentation `here <https://embci.readthedocs.io/en/latest>`_.

**EmBCI** is still under developing. Any contributions are welcomed.

**EmBCI** was held on a **gitlab private repo** before. It's fully opened now. Happy Open Source!



Contents
========
- `What is EmBCI?`_
- `Hardware support`_
- `Software support`_
    - `Requirements`_
    - `Installation`_
- `Linux service interface`_
- `Configuration`_
- `Documentation`_
- `Files outline`_
- `Supported gyms`_
- `License`_
- `Useful links`_



What is EmBCI?
==============
**EmBCI** is the abbreviation of **Embedded Brain-Computer Interface**, a bio-signal acquisition and processing platform.

Why do you need **EmBCI**?

- **Fast prototyping** with lots of data streaming and IO interfaces.
- **Signal processing** : baseline-correction, denoising, time-frequency algorithms, and many more.
- **Biosignal features** : SSVEP, P300, MotorImagery, sEMG-Recognition etc.
- **It's embedded**! 40mm x 40mm wearable device, small but powerful, get rid of PC!



Hardware support
================

`EmBCI Shield` is a PCB board designed to measure, denoise, buffer and transfer bio-signals.
Currently, the stable version is `EmBCI Shield Rev.A7`.

It integrates:

- `ADS1299`_ from `Texas Instruments`_:
    Low-noise 8-Channels 24-Bits ADC for Biopotential Measurements

- `ESP32`_ from `Espressif`_:
    Tensilica Xtensa Dual-core 32-Bits Processor with WiFi and Bluetooth

- Power management chips and others

`EmBCI Shield`__ can also be used as extension board.

__ `files/hardware`_
.. _ADS1299:            /blob/master/tools/ADS1299-Datasheet.pdf
.. _Texas Instruments:  http://www.ti.com/product/ADS1299/description
.. _ESP32:              /tree/master/files/esp32
.. _Espressif:          https://www.espressif.com/en/products/hardware/esp32/overview



Software support
================

Requirements
------------
On embedded Linux
+++++++++++++++++
- sysgpio
- spidev
- wifi
- serial


On others platforms
+++++++++++++++++++
- wifi
- serial


Installation
------------
Install from pypi (suggested)
+++++++++++++++++++++++++++++
:code:`pip install embci`


Install from source
+++++++++++++++++++
.. code:: bash

    git clone -b release https://github.com/hankso/EmBCI.git && cd EmBCI
    sudo python -m pip install -r ./requirements.txt
    python setup.py build && sudo python setup.py install


Developer mode
++++++++++++++
For those who want to build their applications based on **EmBCI**, you may want to install `embci` in developer mode with:

.. code:: bash

    git clone -b master https://github.com/hankso/EmBCI.git && cd EmBCI
    sudo python -m pip install --editable .

Then you can code and test your app.

**EmBCI** provides lots of useful input/output interfaces including an extendible WebUI so that one can easily implement applications. See `embci.io`_, `embci.webui`_ and `embci.apps`_ for more information.


Platform specifics
++++++++++++++++++
On `arm` and `aarch64` embedded Linux platforms, `setup.py` will also install Linux service configuration files.

To autostart `EmBCI applications` at boot on PC and other systems, you have to `config autorun manually`__.

__ _files/service



Linux service interface
=======================
**EmBCI** has a `Linux Service` interface to work properly on embedded devices.

Both `System-V style` scripts and `System D and Service Manager` scripts are provided.

See `files/service`_ for more details.



Configuration
=============
**EmBCI** use `INI-Style <https://en.wikipedia.org/wiki/INI_file>`_ configuration files with an extention `.conf`.

Here's an example::

    # file: EmBCI/files/service/embci.conf
    # Lines beginning with '#' or ';' are ignored and will be used as comments.

    [Path]
    BASEDIR = /usr/share/embci

    [Platform]
    HARDWARE = Rev.A7
    BOARD = Orange Pi Zero Plus 2

    [GPIO]
    PIN_ESP32_DRDY = PD11
    PIN_ILI9341_DC = PA02

    [Network]
    WEBUI_HOST = 0.0.0.0
    WEBUI_PORT = 8080


When you type `import embci`, it will automatically search for configuration files and load them into `embci.configs` with following priority(from low to high)::

    project config file: "${EmBCI}/files/service/embci.conf"
     system config file: "/etc/embci/embci.conf"
       user config file: "~/.embci/embci.conf"

On Windows system::

    project config file: "${EmBCI}/files/service/embci.conf"
     system config file: "${APPDATA}/embci.conf"
       user config file: "${USERPROFILE}/.embci/embci.conf"

See `docs/Configurations`_ for more details.

.. _docs/Configurations: https://embci.readthedocs.io/en/latest/Configurations.html



Documentation
=============
Get full documentation `here <https://embci.readthedocs.io/en/latest>`_.



Files outline
=============
+-------------------+-------------------------------------------------------+
| Folder            | Description                                           |
+===================+=======================================================+
| `embci`_          | Data-processing algorithms, IO, WebUI and frameworks  |
+-------------------+-------------------------------------------------------+
| `files/avr`_      | On shield `Atmega328P` firmware (Deprecated)          |
+-------------------+-------------------------------------------------------+
| `files/esp32`_    | On shield `ESP32` firmware and burning tools          |
+-------------------+-------------------------------------------------------+
| `files/cases`_    | 3D models files in `SolidWorks` and `OpenSCAD` format |
+-------------------+-------------------------------------------------------+
| `files/layouts`_  | Saved SPI-Screen GUI layouts                          |
+-------------------+-------------------------------------------------------+
| `files/hardware`_ | `EmBCI Shield` files in `Altium Designer` format      |
+-------------------+-------------------------------------------------------+
| `files/service`_  | Linux service configurations                          |
+-------------------+-------------------------------------------------------+

.. _LICENSE.txt:    https://github.com/hankso/EmBCI/blob/master/LICENSE.txt
..  _files/avr:      https://github.com/hankso/EmBCI/tree/master/files/avr
.. _files/esp32:    https://github.com/hankso/EmBCI/tree/master/files/esp32
.. _files/cases:    https://github.com/hankso/EmBCI/tree/master/files/cases
.. _files/layouts:  https://github.com/hankso/EmBCI/tree/master/files/layouts
.. _files/hardware: https://github.com/hankso/EmBCI/tree/master/files/hardware
.. _files/service:  https://github.com/hankso/EmBCI/tree/master/files/service

.. _embci:          https://github.com/hankso/EmBCI/tree/master/embci/__init__.py
.. _embci.io:       https://github.com/hankso/EmBCI/tree/master/embci/io.py
.. _embci.apps:     https://github.com/hankso/EmBCI/tree/master/embci/apps
.. _embci.gyms:     https://github.com/hankso/EmBCI/tree/master/embci/gyms
.. _embci.webui:    https://github.com/hankso/EmBCI/tree/master/embci/webui



Supported gyms
==============
Currently only two environments are implemented to output mind-control results.
See `embci.gyms`_ for more.


Plane war game
--------------
Written by @ buaawyz_. See `game installation`_ guide.

Run `python main.py` first and then `from gyms import PlaneClient as Client`


TORCS car game
--------------
See more at gym_torcs_. And `embci.io`_.TorcsCommander.

.. _buaawyz:           https://github.com/buaawyz
.. _game installation: https://github.com/hankso/gym_plane_python
.. _gym_torcs:         https://github.com/ugo-nama-kun/gym_torcs



License
=======
MIT license. See `LICENSE.txt`_



Useful links
============
- `Awesome-BCI <https://github.com/NeuroTechX/awesome-bci>`_
- `OpenBCI <https://github.com/openbci>`_
- `OpenViBE <http://openvibe.inria.fr/>`_
- Matlab toolboxes
    - `EEGLAB <http://sccn.ucsd.edu/eeglab/>`_
    - `BCILAB <https://sccn.ucsd.edu/wiki/BCILAB>`_
