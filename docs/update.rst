Updating Guide
==============

Hardware firmware update
------------------------
See a detail document on how to update ESP32 firmware `here <hardware/esp32.html>`_.

Python package update
---------------------
The most common and easist way to update package is by :code:`git pull`. EmBCI master(release) branch is hosted on `Github <https://github.com/hankso/EmBCI>`_ and develop branch is on `Gitlab <https://gitlab.com/hankso/EmBCI>`_.

In each EmBCI device, the main package is located at :code:`/root/EmBCI` as a local git repository. Currently EmBCI is installed in editable mode (:code:`pip install -e /root/EmBCI`), since there are frequently updates and bugfixs. It will be installed to :code:`/usr/local/lib/` in next stable release.

Preparation
+++++++++++
- Make sure your computer and EmBCI are in same network.
- Assume the IP address of EmBCI is 10.0.0.1 and PC is 10.0.0.100.

Steps
+++++
1. On your computer, use :code:`SSH` to login to EmBCI.

.. code:: sh

    ssh root@10.0.0.1

2. Then update the package.
2.1) If you have this python package cloned on your PC, sync it from computer.

.. code:: sh

    # on computer
    git clone --depth=1 -b master https://github.com/hankso/EmBCI.git
    # on OrangePi
    cd /root/EmBCI && git pull user@10.0.0.100:/path/to/EmBCI

2.2) Or you have to provide network access to OrangePi and sync EmBCI directly from Github. For example, setup your computer as a Squid proxy (``Squid@Linux / SquidMan@MacOS`` is a caching proxy for the Web supporting HTTP, HTTPS and FTP). Also Imfirewall/Ultrasurf can be used on Windows to establish a proxy server.

.. code:: sh

    # on computer
    squid -a 3128  # proxy server listening on 10.0.0.100:3128
    # on OrangePi
    cd /root/EmBCI && git config http.proxy http://10.0.0.100:3128
    git remove add github https://github.com/hankso/EmBCI.git
    git pull --depth=1 github master
    git config --unset http.proxy  # remember to reset the proxy address

3. Restart EmBCI program on OrangePi to check if it runs correctly.

.. code:: sh

    killall python
    bash /root/autostart.sh

4. Reboot the device. This time EmBCI will autostart programs.
