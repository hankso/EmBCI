Network IO
==========
Get data from matlab
--------------------
- Here we use Orange Pi + EmBCI Shield Rev.A7,
- Make sure Orange Pi and your PC are in same LAN,
- Example to fetch data through socket in `Matlab`.

.. code:: matlab

    % socket server on orangepi default listen on port 9999.
    client = tcpclient('192.168.10.10', 9999)

    % 8-channel float32 data --> 8_ch * 32_bits / 8_bits = 32 bytes data
    data = client.read(32)

    % unpack bytes into float32(single)
    data = typecast(data, 'single')

    % data is 1x8 vector
    data


Get data with Reader
--------------------
- EmBCI python package provide two network data reader:
    - `embci.io.SocketTCPReader`
    - `embci.io.SocketUDPReader`
- Example to fetch data through socket in `Python`.

.. code:: python

    >>> import embci
    >>> sample_rate = 500  # this has to match sample rate of out data stream
    >>> sample_time = 2  # buffer 2 seconds of data
    >>> num_channel = 8  # if out data stream only provide 6 channels, change it
    >>> reader = embci.io.SocketTCPReader(sample_rate, sample_time, num_channel)
    >>> reader.start()
    Please input an address in format "host,port".
    Type `quit` to abort.
    > 192.168.0.1:8888 (example)
    > 10.0.0.1:80
    >>> reader
    <started - Socket TCP Reader 1: 500Hz, 8chs, 2.0sec, at 0xdeadbeef>
