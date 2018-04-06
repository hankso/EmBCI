# 用户使用说明
- 开机自动运行主程序
- 屏幕显示波形以及一些信息
- 如果想要orangepi自动连接wifi，需在开机前提供一个无密码的wifi，或者使用orangepi作为
热点让电脑连接




# 开发人员往这儿看
## 安装所需模块
命令行运行 `pip install -r requirements.txt`

python2或3都是兼容的

## 运行程序
`run_me.py`为程序入口，也就是引导文件，该文件调用src和utils里面的各种函数，创建
`reader`, `model`, `commander` 等对象，用于获取数据，训练/分类模型，和控制外围设备，
将这些对象传入实验范式的框架，`src/frame.py`中提供了`sEMG`, `SSVEP`, `P300`,
`Motor Imaginary`, `TGAM_relax`等框架

## 开机自动运行控制
[corn](https://en.wikipedia.org/wiki/Cron)

## 给arduino编程
`sudo apt-get install avr-gcc avrdude`

[guide1](https://github.com/kcuzner/avrdude)

[guide2](http://kevincuzner.com/2013/05/27/raspberry-pi-as-an-avr-programmer/)

## 将orangepi作为wifi热点
[树莓派是这样做的](http://www.raspberry-projects.com/pi/software_utilities/wifi-access-point)

[配置/etc/network/interfaces的问题](https://unix.stackexchange.com/questions/128439/good-detailed-explanation-of-etc-network-interfaces-syntax)