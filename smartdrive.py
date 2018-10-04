import re
import time
import serial
import sys
from PyQt5.QtCore import QObject, QProcess, pyqtSignal, pyqtSlot

import resource
from packet import Packet

class SmartDrive(QObject):
    totalLPC21ISPLength = 574

    invalidFirmware = pyqtSignal(str)

    bootloaderStatus = pyqtSignal(int, str)
    bootloaderFinished = pyqtSignal()
    bootloaderFailed = pyqtSignal(str)

    firmwareStatus = pyqtSignal(int, str)
    firmwareFinished = pyqtSignal()
    firmwareFailed = pyqtSignal(str)

    stopSignal = pyqtSignal()

    def __init__(self, port, fwFileName=None, transmitDelay=0.001):
        super().__init__()
        self.transmitDelay = transmitDelay
        self.portName = port
        self.isProgramming = False
        self.fw = None
        self.fwFileName = None

        if fwFileName is not None:
            self.onFirmwareFileSelected(fwFileName)

        self.bootloaderPercent = 0
        self.bootloaderState = ''
        self.firmwarePercent = 0
        self.firmwareState = ''
        self.bootloaderProcess = None

    @staticmethod
    def versionBytesToString(vBytes):
        v = sum(vBytes)
        if v >= 0xFF or v <= 0x00:
            return 'unknown'
        else:
            return '{}.{}'.format((v & 0xF0) >> 4, v & 0x0F)

    @pyqtSlot(str)
    def onPortSelected(self, portName):
        self.portName = portName

    @pyqtSlot(str)
    def onFirmwareFileSelected(self, fwFileName):
        self.fw = None
        self.version = 'unknown'
        self.crc = 'unknown'
        self.fwCheckSum = 0
        self.fwFileName = fwFileName
        if fwFileName is None or len(fwFileName) == 0:
            msg = "Please select a MX2+ OTA file!"
            self.invalidFirmware.emit(msg)
            return

        # open the firmware file
        try:
            f = open(self.fwFileName, 'rb')
        except Exception as error:
            msg = "Couldn't open firmware file '{}'!\n{}".format(self.fwFileName, error)
            self.invalidFirmware.emit(msg)
            return
        else:
            with f:
                fileData = bytearray(f.read())
        self.version = self.versionBytesToString(fileData[0:4])
        if self.version != 'unknown':
            self.fw = fileData
            self.fwCheckSum = self.fw[4:8]
            self.crc = ''.join('{:02x}'.format(x) for x in self.fwCheckSum)
        else:
            msg = "Invalid OTA file '{}'!\nPlease select a valid MX2+ OTA file!".format(
                self.fwFileName
            )
            self.invalidFirmware.emit(msg)

    def checkPort(self):
        '''Returns true if we have a valid port, false otherwise'''
        if self.portName is None or len(self.portName) <= 0:
            return False

        # open the port
        try:
            port = serial.Serial(port=self.portName,
                                 baudrate=38400,
                                 bytesize=serial.EIGHTBITS,
                                 parity=serial.PARITY_NONE,
                                 stopbits=serial.STOPBITS_ONE,
                                 timeout=1)
        except Exception as error:
            return False
        else:
            # close the port so lpc21isp can use it
            port.close()
        return True

    @pyqtSlot()
    def programBootloader(self):
        if not self.checkPort():
            self.bootloaderFailed.emit(
                "Couldn't open serial port '{}'".format(self.portName)
            )
            return

        self.isProgramming = True
        self.lpc21ispOutput = ''
        self.bootloaderPercent = 0
        self.bootloaderState = ''

        # lpc21isp process
        self.bootloaderProcess = QProcess()
        self.bootloaderProcess.readyReadStandardOutput.connect(self.onBootloaderDataReady)
        self.bootloaderProcess.readyReadStandardError.connect(self.onBootloaderErrorReady)
        self.bootloaderProcess.finished.connect(self.onLPC21ISPFinished)
        self.stopSignal.connect(self.bootloaderProcess.kill)

        program = resource.path('exes/lpc21isp')
        if sys.platform.startswith('win'):
            program += '.exe'
        args = [
            "-wipe",
            resource.path("firmwares/ota-bootloader.hex"),
            self.portName,
            "38400",  # baudrate
            "12000"   # crystal frequency on board
        ]
        self.bootloaderProcess.start(program, args)

    def onBootloaderDataReady(self):
        data = str(self.bootloaderProcess.readAllStandardOutput(), 'utf-8')
        self.lpc21ispOutput += data
        percent, state = self.parseLPC21ISPOutput()
        self.bootloaderStatus.emit(percent, state)

    def onBootloaderErrorReady(self):
        data = str(self.bootloaderProcess.readAllStandardError(), 'utf-8')
        print("STDERR:",data)
        self.lpc21ispOutput += data
        percent, state = self.parseLPC21ISPOutput()
        self.bootloaderStatus.emit(percent, state)

    def onLPC21ISPFinished(self, code, status):
        if code == 0:
            self.bootloaderStatus.emit(100, 'Bootloader complete')
            self.bootloaderFinished.emit()
        elif self.isProgramming:
            self.bootloaderStatus.emit(0, 'Bootloader failed.')
            self.bootloaderFailed.emit("Bootloader failed: {}: {}".format(code, status))
        else:
            self.bootloaderStatus.emit(0, 'Bootloader stopped.')
        self.bootloaderProcess = None
        self.isProgramming = False

    def parseLPC21ISPOutput(self):
        data = self.lpc21ispOutput
        # TODO: regex here to determine status and percent
        m = re.split(r'Sector \d: (\.+)', self.lpc21ispOutput, re.M)
        if len(m) > 1:
            percent = len(''.join(m[1:-1]).replace('\n','')) / self.totalLPC21ISPLength * 100
        else:
            percent = 0
        status = m[0].split('\n')[-1]
        if len(status) == 0:
            status = "Writing new firmware."
        return percent, status

    @pyqtSlot()
    def stop(self):
        self.isProgramming = False
        self.stopSignal.emit()

    @pyqtSlot()
    def programFirmware(self):
        if not self.checkPort():
            self.firmwareFailed.emit(
                "Couldn't open serial port '{}'".format(self.portName)
            )
            return

        if self.fw is None or len(self.fw) <= 0:
            self.firmwareFailed.emit("Please select MX2+ firmware file!")
            return

        # init variables
        self.isProgramming = True
        self.firmwarePercent = 0
        self.firmwareState = ''
        size = len(self.fw)
        haveRecvReady = False
        port = serial.Serial(port=self.portName,
                             baudrate=115200,
                             bytesize=serial.EIGHTBITS,
                             parity=serial.PARITY_NONE,
                             stopbits=serial.STOPBITS_ONE,
                             timeout=1)

        # wait for ready
        self.firmwareStatus.emit(0, 'Waiting for Bootloader Ready')
        while not haveRecvReady:
            # send start
            p = Packet(Packet.command, Packet.otaStart, [Packet.smartDrive])
            port.flushInput();
            port.write(p.data)

            # receive ota ready
            respData = bytearray(port.read(Packet.otaReadyLength))
            resp = Packet(data=respData)
            if resp.isValid(Type=Packet.command, SubType=Packet.otaReady):
                haveRecvReady = True
            else:
                time.sleep(0.5)

            if not self.isProgramming:
                break

        if not self.isProgramming:
            port.close()
            return

        # send firmware data
        for i in range(0, size, 16):
            if not self.isProgramming:
                break
            length = min(size - i, 16)
            fwData = self.fw[i:(i+length)]
            p = Packet(Packet.ota, Packet.smartDrive, fwData)
            port.write(p.data)
            self.firmwareStatus.emit(100 * i/size, 'Sending MX2+ Firmware')
            time.sleep(self.transmitDelay)

        if not self.isProgramming:
            port.close()
            return

        # send stop
        self.firmwareStatus.emit(100, 'Rebooting MX2+')
        p = Packet(Packet.command, Packet.otaStop, [Packet.smartDrive])
        port.write(p.data)

        # close the port
        port.close()

        # let everyone know we're finished
        self.isProgramming = False
        self.firmwareFinished.emit()
