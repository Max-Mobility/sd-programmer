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

    # TODO: replace these with config options in GUI
    port = options.port
    baudRate = options.baudRate
    filename = options.filename
    version  = options.version
    transmitDelay = options.transmitDelay
    timeout  = options.timeout

    stopbits      = serial.STOPBITS_ONE
    bytesize      = serial.EIGHTBITS
    parity        = serial.PARITY_NONE

    # have ui which contains
    # * selector for COM Port
    # * button for starting process
    # * display of lpc21isp output
    # * progress display
    # * alert display

    try:
        ser = serial.Serial(port=port,
                            baudrate=baudRate,
                            bytesize=bytesize,
                            parity=parity,
                            stopbits=stopbits,
                            timeout=timeout)
    except Exception as error:
        print("ERROR: Couldn't open serial port {}".format(port))
        return -1

if __name__ == "__main__":
    main()

