#!/usr/bin/python
import time
import glob
import sys
import os

import argparse
# for spawning lpc21isp process
from multiprocessing import Process, Queue
# for progress bar:
from tqdm import tqdm

from ui import Programmer
from PyQt5.QtWidgets import QApplication

# baudrate for lpc21isp: 38400
# baudrate for mx2+ FW:  115200

def main():
    app = QApplication(sys.argv)
    p = Programmer()
    sys.exit(app.exec_())
    return

if __name__ == "__main__":
    main()

