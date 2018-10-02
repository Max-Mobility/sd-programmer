import re
import time
import serial
import sys
from PyQt5.QtCore import QObject, QProcess, pyqtSignal, pyqtSlot

from packet import Packet

class SmartDrive(QObject):
    totalLPC21ISPLength = 574
    bootloaderStatus = pyqtSignal(int, str)
    bootloaderFinished = pyqtSignal()
    bootloaderFailed = pyqtSignal(str)

    firmwareStatus = pyqtSignal(int, str)
    firmwareFinished = pyqtSignal()
    firmwareFailed = pyqtSignal(str)

    stopSignal = pyqtSignal()

    def __init__(self, port, fw, transmitDelay=0.001):
        super().__init__()
        self.transmitDelay=transmitDelay
        self.isProgramming = False
        self.portName = port
        self.fw = fw
        self.bootloaderPercent = 0
        self.bootloaderState = ''
        self.firmwarePercent = 0
        self.firmwareState = ''
        self.bootloaderProcess = None

    @pyqtSlot()
    def programBootloader(self):
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

        program = './exes/lpc21isp'
        if sys.platform.startswith('win'):
            program += '.exe'
        args = [
            "-wipe",
            "./firmwares/ota-bootloader.hex",
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
        else:
            self.bootloaderFailed.emit("Bootloader failed: {}: {}".format(code, status))
        self.bootloaderProcess = None

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
        self.stopSignal.emit()
        self.isProgramming = False

    @pyqtSlot()
    def programFirmware(self):
        # init variables
        self.firmwarePercent = 0
        self.firmwareState = ''
        size = len(self.fw)
        haveRecvReady = False
        if not self.isProgramming:
            return
        # open the port
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
                pass

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
