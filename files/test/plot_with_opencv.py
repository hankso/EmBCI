'''
Ploting elements
Hank within EmBCI
'''

import matplotlib.pyplot as plt
import numpy as np
import cv2
import time


def cv2_plot_raw(x, y, sample_rate=256, win_width=400,
                 imgsize=(200, 400), color=(255, 180, 120)):
    if len(x) != len(y):
        raise RuntimeError('x and y must be 1-D list or numpy.array'
                           ' with same length!')
    if imgsize[1] < win_width:
        raise RuntimeError('frame width is smaller than'
                           ' data win length, too narrow.')
    h, w = imgsize
    try:
        y = np.pad(h/2.0 - np.array(y)/float(max(y))*(h/2.0*0.95),
                   (0, win_width+1-len(y) if len(y) <= win_width else 0),
                   'constant', constant_values=(0, 0))
        for i in range(len(y) - win_width):
            t = np.array(x)[i:i+win_width] - x[i]
            t = t/float(max(t))*(w*0.95) + w*0.025
            img = cv2.polylines(np.zeros(imgsize).astype(np.int8),
                                [np.array(zip(t, y[i:i+win_width]), np.int32)],
                                False, 255, 1)
            cv2.imshow('win', img)
            if cv2.waitKey(1000/sample_rate) in [10, 32, 112]:
                while cv2.waitKey() not in [10, 32, 112]:
                    pass
    except Exception as e:
        print(e)
    finally:
        while cv2.waitKey() not in [113, 27]:
            cv2.imshow('win', img)
        cv2.destroyWindow('win')


def plot_raw(x, y, sample_rate=256, win_width=100):
    data = {'time': x, 'raw': y}
    b = float(win_width)/sample_rate/8
    t = data['time'][-win_width:]
    plt.cla()
    if len(t) > win_width:
        plt.xlim(t[0] - b, t[-1] + b)
    else:
        plt.xlim(min(t) - b, max(t) + b)
    plt.plot(t, data['raw'][-win_width:])
    plt.show()


if __name__ == '__main__':
    filepath = './raw_data_20171217-14:10:32.csv'
    csv = np.loadtxt(filepath, delimiter=',')
    try:
        cv2_plot_raw(csv[:, 0][:], csv[:, 1][:])
        #  plt.ion()
        #  time.sleep(1)
        #  for i in range(csv.shape[0]-100):
        #      plot_raw(csv[i:i+100, 0], csv[i:i+100, 1])
        #  plt.close()
    except Exception as e:
        print(e)
