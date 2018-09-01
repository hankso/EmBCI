import os
import sys
filepath = os.path.dirname(os.path.abspath(__file__))
filepath = os.path.join(filepath, '../utils')
if filepath not in sys.path:
    sys.path.append(filepath)

# from ../utils/server.py
from server import application
