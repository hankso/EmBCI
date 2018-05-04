# 用户使用说明
- 开机自动运行主程序 `只在PC上测试了，使用crontab是个很好的办法`
- 屏幕显示波形以及一些信息 `GUI写有初始Menu，选择任务比如显示波形，显示信息，等等，关于ScreenGUI的一切使用可以看 utils/visualization.py 里面的 Screen_GUI 类，比较简易的实现GUI功能，按钮绑定回调函数，run_me1.py就是示例`
- 如果想要orangepi自动连接wifi，需在开机前提供一个无密码的wifi，或者使用orangepi作为热点让电脑连接

## 开机自动运行控制
[cron](https://en.wikipedia.org/wiki/Cron)

# 开发人员往这儿看
## 安装所需模块
命令行运行 `pip install -r requirements.txt`

python2或3都是兼容的

`2018.05.04 最近更新比较多，还没有考虑兼容的问题，目前都是基于python2的，orangepi上配置的是py2的环境`

在orangepi上，用户名为hank，密码gaohanlin
- 在/home/hank/programes/MyBCI里面`git pull`一下跟进最新更新
- sudo ipython 密码gaohanlin
- run run_me1.py即可看到GUI，需要手动调用 `s.start_touch_screen(port=avr_port(default '/dev/ttyS2' on OPi))` ARM才会开始接受AVR发出的触摸屏信号
- 目前run_me1.py里面有了显示信息和显示波形两个功能，还需要添加下面几个功能
    - `通过触摸屏调节波形放大倍数scale（写好了，未测试）`
    - `显示频谱，从 utils/common.py 里面的 Signal_Info 类实现了各种频域信息的提取`
    - `GUI好好排版一下`

## 运行程序
`run_me.py`为程序入口，也就是引导文件，该文件调用src和utils里面的各种函数，创建
`reader`, `model`, `commander` 等对象，用于获取数据，训练/分类模型，和控制外围设备，
将这些对象传入实验范式的框架，`src/frame.py`中提供了`sEMG`, `SSVEP`, `P300`,
`Motor Imaginary`, `TGAM_relax`等框架，需要进一步完善


## 给arduino编程
`sudo apt-get install avr-gcc avrdude arduino-mk`

[guide1](https://github.com/kcuzner/avrdude)

[guide2](http://kevincuzner.com/2013/05/27/raspberry-pi-as-an-avr-programmer/)

## 将orangepi作为wifi热点
[树莓派是这样做的](http://www.raspberry-projects.com/pi/software_utilities/wifi-access-point)

[配置/etc/network/interfaces的问题](https://unix.stackexchange.com/questions/128439/good-detailed-explanation-of-etc-network-interfaces-syntax)