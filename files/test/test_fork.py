import os
import time
parent_pid = os.getpid()

a = range(10)
os.fork()

if os.getpid() == parent_pid:
    print('this is in main process~')
    while 1:
        time.sleep(2)
        a[0] += 10
else:
    print('this is in child process, parent_pid: {}'.format(os.getppid()))
    while 1:
        time.sleep(1)
        print(time.ctime(), a)

