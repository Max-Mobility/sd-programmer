#!/usr/bin/python
import serial
import time
import sys
import os

import argparse
# for spawning lpc21isp process
from multiprocessing import Process, Queue
# for progress bar:
from tqdm import tqdm

from packet import Packet, Header

def main():
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

    try:
        f = open(filename, 'rb')
    except Exception as error:
        print "ERROR: Couldn't open file {}".format(filename)
        return -1
    else:
        with f:
            fileData = bytearray(f.read())

    fileSize = os.path.getsize(filename)
    print 'Size:     {}'.format(fileSize)
    print 'Version:  {:02x}'.format(version)
    fwCheckSum = checkSum(fileData, fileSize, 0xFFFFFFFF)
    print 'CheckSum: {:02x}'.format(fwCheckSum)

    try:
        ser = serial.Serial(port=port,
                            baudrate=baudRate,
                            bytesize=bytesize,
                            parity=parity,
                            stopbits=stopbits,
                            timeout=timeout)
    except Exception as error:
        print "ERROR: Couldn't open serial port {}".format(port)
        return -1
    else:
        with ser:
            haveRecvReady = False
            while not haveRecvReady:
                # send start
                p = Packet(command, otaStart, [smartDrive])
                ser.flushInput();
                ser.write(p.data)

                # receive ota ready
                resp = bytearray(ser.read(otaReadyLength))
                if not checkOTAReady(resp):
                    print 'No "OTA Ready" received.'
                else:
                    haveRecvReady = True

            # send header
            p = Header(version, fwCheckSum)
            ser.write(p.data)

            # send firmware data
            for i in range(0, fileSize, 16):
                length = min(fileSize - i, 16)
                fwData = fileData[i:(i+length)]
                p = Packet(ota, smartDrive, fwData)
                ser.write(p.data)
                time.sleep(transmitDelay)

            # send stop
            p = Packet(command, otaStop, [smartDrive])
            ser.write(p.data)

if __name__ == "__main__":
    main()

