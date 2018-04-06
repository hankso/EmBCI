# Required modules
simply run

`sudo pip install -r ./requirements.txt`

or

`sudo pip3 install -r ./requirements.txt`

This program is py2 && py3 compatiable after 2018.03.23 modification(theorically...)

# How to use
`python2 run_me.py` or `python3 run_me.py`


# Connection
- Communicate with [ADS1299](http://www.ti.com/product/ADS1299) through SPI
interface on OrangePi pin `CS/PA13`, `CLK/PA14`, `MOSI/PA15` and `MISO/PA16`

- On shield Atmega328P(Arduino Uno/Nano) is connected to `UART2_TX/PA00` and
`UART2_RX/PA01`

- Control SSD1306 0.96' OLED screen by SPI or ILI9325 2.3' LCD screen through
on shield Arduino by serial

- Broadcast collected raw data from ADS1299 to wifi port 9999(default) by TCP
socket, there are two ways to grab data from network
    - Connect OrangePi to your LAN wifi network and check its IP address, you
    can login to router(e.g. TP-Link @ `192.168.1.1`) or use any other methods
    to get OrangePi IP address.
    - Set OrangePi as a wifi hotpot, connect your PC/laptop/phone to this
    network and this way OrangePi IP address will be `192.169.0.1`(usually)


## Get data from matlab
- Make sure orangepi and your PC are in same LAN
- Here's an example script to fetch data through socket in matlab

```Matlab
% socket server on orangepi default listen on port 9999.
client = tcpclient('192.168.10.10', 9999)

% 8-channel float32 data --> 8_ch * 32_bits / 8_bits = 32 bytes data
data = client.read(32)

% unpack bytes into float32(single)
data = typecast(data, 'single')

% here data is 1x8 vector
```


# Project structure
|    folder    |    description    |
| :----------- | :---------------- |
|     data     | save biosignal data with label in each subfoler named by username |
|    models    | save trained models with weight for each user |
|     src      | preprocessing algorithms, classifiers and frameworks |
|    test      | testing new ideas |
|    utils     | common functions, gym clients, data IO, etc. |
|   run_me.py  | bootloader script of program |


# Supported gyms
Currently we only support two environments
- plane-war-game: written by [@buaawyz](https://github.com/buaawyz),
[installation guide](https://github.com/hankso/gym_plane_python),
run `python main.py` first and then `from gyms import PlaneClient as Client`
- torcs-car-game: see more details at [gym_torcs](https://github.com/ugo-nama-kun/gym_torcs)

# Packages on orangepi zero plus
backports-abc==0.5
backports.shutil-get-terminal-size==1.0.0
backports.weakref==1.0rc1
BeautifulSoup==3.2.1
bleach==1.5.0
certifi==2018.1.18
chardet==2.3.0
configparser==3.5.0
cycler==0.9.0
decorator==4.0.6
entrypoints==0.2.3
enum34==1.1.6
funcsigs==1.0.2
functools32==3.2.3.post2
html5lib==0.9999999
ipykernel==4.8.2
ipython==5.5.0
ipython-genutils==0.2.0
ipywidgets==7.1.2
Jinja2==2.10
joblib==0.9.4
jsonschema==2.6.0
jupyter==1.0.0
jupyter-client==5.2.2
jupyter-console==5.2.0
jupyter-core==4.4.0
Keras==2.1.4
Markdown==2.6.11
MarkupSafe==1.0
matplotlib==1.5.1
mistune==0.8.3
mne==0.15.2
mock==2.0.0
nbconvert==5.3.1
nbformat==4.4.0
notebook==5.4.0
numpy==1.11.0
pandas==0.17.1
pandocfilters==1.4.2
pathlib2==2.3.0
pbr==3.1.1
pexpect==4.4.0
pickleshare==0.7.4
Pillow==3.1.2
prompt-toolkit==1.0.15
protobuf==3.5.1
ptyprocess==0.5.2
Pygments==2.2.0
pyparsing==2.0.3
pysqlite==1.0.1
python-dateutil==2.4.2
pytz==2014.10
PyYAML==3.12
pyzmq==15.2.0
qtconsole==4.3.1
requests==2.9.1
scandir==1.7
scikit-learn==0.17
scipy==0.17.0
Send2Trash==1.5.0
simplegeneric==0.8.1
singledispatch==3.4.0.3
six==1.10.0
tensorflow==1.2.1
terminado==0.8.1
testpath==0.3.1
tornado==4.5.3
traitlets==4.3.2
urllib3==1.13.1
wcwidth==0.1.7
Werkzeug==0.14.1
widgetsnbextension==3.1.4
yolk3k==0.9
