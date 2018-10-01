#!/usr/bin/python
import serial
import time
import glob
import sys
import os

import argparse
# for spawning lpc21isp process
from multiprocessing import Process, Queue
# for progress bar:
from tqdm import tqdm

from packet import Packet, Header

# baudrate for lpc21isp: 38400
# baudrate for mx2+ FW:  115200

def serial_ports():
    """ Lists serial port names

        :raises EnvironmentError:
            On unsupported or unknown platforms
        :returns:
            A list of the serial ports available on the system
    """
    if sys.platform.startswith('win'):
        ports = ['COM%s' % (i + 1) for i in range(256)]
    elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        # this excludes your current terminal "/dev/tty"
        ports = glob.glob('/dev/tty[A-Za-z]*')
    elif sys.platform.startswith('darwin'):
        ports = glob.glob('/dev/tty.*')
    else:
        raise EnvironmentError('Unsupported platform')

    result = []
    for port in ports:
        try:
            s = serial.Serial(port)
            s.close()
            result.append(port)
        except (OSError, serial.SerialException):
            pass
    return result

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

    # have ui which contains
    # * selector for COM Port
    # * button for starting process
    # * display of lpc21isp output
    # * progress display
    # * alert display

    try:
        f = open(filename, 'rb')
    except Exception as error:
        print("ERROR: Couldn't open file {}".format(filename))
        return -1
    else:
        with f:
            fileData = bytearray(f.read())

    fileSize = os.path.getsize(filename)
    fwCheckSum = checkSum(fileData, fileSize, 0xFFFFFFFF)

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
                    pass
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

