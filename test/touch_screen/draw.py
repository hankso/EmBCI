# -*- coding: utf-8 -*-

import sys
sys.path += ['../../utils']

from IO import Screen_commander, command_dict_uart_screen_v1



if __name__ == '__main__':
    c = Screen_commander(command_dict=command_dict_uart_screen_v1)
    c.start()
    try:
        pass
    except KeyboardInterrupt:
        pass
    finally:
        c.close()