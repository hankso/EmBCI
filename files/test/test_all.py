import os
from embci import BASEDIR
os.chdir(BASEDIR)

from embci.utils.HTMLTestRunner import HTMLTestRunner
suite = unittest.TestSuite()

