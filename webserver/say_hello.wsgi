import os
import sys
filepath = os.path.dirname(os.path.abspath(__file__))
filepath = os.path.join(filepath, '../files/test/')
if filepath not in sys.path:
    sys.path.append(filepath)

# from ../files/test/bottle_say_hello.py
from bottle_say_hello import application
