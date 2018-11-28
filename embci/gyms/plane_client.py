#!/usr/bin/env python
# -*- coding=utf-8 -*-

"""
file: client.py
socket client
"""

import socket
import sys

class Client:
    def __init__(self):    
        try:
            self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.s.connect(('127.0.0.1', 6666))
        except socket.error as msg:
            print (msg)
            sys.exit(1)
        #print (self.s.recv(1024))
    def send(self,data):  
        #while 1:
            #data = input('please input work: ')
            #data = 
        self.s.send(str.encode(data))
        print (self.s.recv(1024))
        #if data == 'exit':
            #break
        #self.s.close()
        
