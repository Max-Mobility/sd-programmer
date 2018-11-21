import re
import time
import serial
import sys
from PyQt5.QtCore import QObject, QProcess, pyqtSignal, pyqtSlot

import resource

class SmartDriveBluetooth(QObject):
    invalidFirmware = pyqtSignal(str)
    listError = pyqtSignal(str)
    getError = pyqtSignal(str)
    updateError = pyqtSignal(str)

    listStatus = pyqtSignal(int, str)
    listFinished = pyqtSignal()
    listFailed = pyqtSignal(str)

    getStatus = pyqtSignal(int, str)
    getFinished = pyqtSignal()
    getFailed = pyqtSignal(str)

    firmwareStatus = pyqtSignal(int, str)
    firmwareFinished = pyqtSignal()
    firmwareFailed = pyqtSignal(str)

    stopSignal = pyqtSignal()

    def __init__(self, fwFileName=None):
        super().__init__()
        self.isProgramming = False
        self.fwFileName = None

        if fwFileName is not None:
            self.onFirmwareFileSelected(fwFileName)

        self.firmwarePercent = 0
        self.firmwareState = ''

        self.listProcess = None
        self.getProcess = None
        self.firmwareProcess = None

    @pyqtSlot(str)
    def onFirmwareFileSelected(self, fwFileName):
        self.fw = None
        self.fwFileName = None
        if fwFileName is None or len(fwFileName) == 0:
            msg = "Please select a SmartDrive Bluetooth FW file!"
            self.invalidFirmware.emit(msg)
            return
        self.fwFileName = fwFileName

    @pyqtSlot()
    def debuggerConnected(self):
        '''Returns true if we have a valid cc-debugger connected, false otherwise'''
        # BleUpdate process
        self.listProcess = QProcess()
        self.listProcess.readyReadStandardOutput.connect(self.onListDataReady)
        self.listProcess.readyReadStandardError.connect(self.onListErrorReady)
        self.listProcess.finished.connect(self.onListFinished)
        self.stopSignal.connect(self.listProcess.kill)

        program = resource.path('exes/BleUpdate-1.3.9/bleupdate-cli.exe')
        args = [
            "list"
        ]
        self.listProcess.start(program, args)

    def onListDataReady(self):
        data = str(self.listProcess.readAllStandardOutput(), 'utf-8')
        self.bleUpdateOutput += data
        percent, state = self.parseListOutput()
        self.listStatus.emit(percent, state)

    def onListErrorReady(self):
        data = str(self.listProcess.readAllStandardError(), 'utf-8')
        print("STDERR:",data)
        self.bleUpdateOutput += data
        percent, state = self.parseListOutput()
        self.listStatus.emit(percent, state)

    def onListFinished(self, code, status):
        if code == 0:
            self.listStatus.emit(100, 'List complete')
            self.listFinished.emit()
        elif self.isProgramming:
            self.listStatus.emit(0, 'List failed.')
            self.listFailed.emit("List failed: {}: {}".format(code, status))
        else:
            self.listStatus.emit(0, 'List stopped.')
        self.listProcess = None
        self.isProgramming = False
        self.listFinished.emit()

    def parseListOutput(self):
        data = self.bleUpdateOutput
        # TODO: regex here to determine status and percent
        m = re.split(r'Sector \d: (\.+)', self.bleUpdateOutput, re.M)
        if len(m) > 1:
            percent = len(''.join(m[1:-1]).replace('\n','')) / self.totalBleUpdateLength * 100
        else:
            percent = 0
        status = m[0].split('\n')[-1]
        if len(status) == 0:
            status = "Writing new firmware."
        return percent, status

    @pyqtSlot()
    def getDeviceInfo(self):
        '''Gets the MAC Address and License Key from the Device before proramming'''
        # BleUpdate process
        self.getProcess = QProcess()
        self.getProcess.readyReadStandardOutput.connect(self.onGetDataReady)
        self.getProcess.readyReadStandardError.connect(self.onGetErrorReady)
        self.getProcess.finished.connect(self.onGetFinished)
        self.stopSignal.connect(self.getProcess.kill)

        program = resource.path('exes/BleUpdate-1.3.9/bleupdate-cli.exe')
        args = [
            "get"
        ]
        self.getProcess.start(program, args)

    def onGetDataReady(self):
        data = str(self.getProcess.readAllStandardOutput(), 'utf-8')
        self.bleUpdateOutput += data
        percent, state = self.parseGetOutput()
        self.getStatus.emit(percent, state)

    def onGetErrorReady(self):
        data = str(self.getProcess.readAllStandardError(), 'utf-8')
        print("STDERR:",data)
        self.bleUpdateOutput += data
        percent, state = self.parseGetOutput()
        self.getStatus.emit(percent, state)

    def onGetFinished(self, code, status):
        if code == 0:
            self.getStatus.emit(100, 'Get complete')
            self.getFinished.emit()
        elif self.isProgramming:
            self.getStatus.emit(0, 'Get failed.')
            self.getFailed.emit("Get failed: {}: {}".format(code, status))
        else:
            self.getStatus.emit(0, 'Get stopped.')
        self.getProcess = None
        self.isProgramming = False
        self.getFinished.emit()

    def parseGetOutput(self):
        data = self.bleUpdateOutput
        # TODO: regex here to determine status and percent
        m = re.split(r'Sector \d: (\.+)', self.bleUpdateOutput, re.M)
        if len(m) > 1:
            percent = len(''.join(m[1:-1]).replace('\n','')) / self.totalBleUpdateLength * 100
        else:
            percent = 0
        status = m[0].split('\n')[-1]
        if len(status) == 0:
            status = "Writing new firmware."
        return percent, status

    @pyqtSlot()
    def programFirmware(self):
        self.isProgramming = True
        self.bleUpdateOutput = ''
        self.firmwarePercent = 0
        self.firmwareState = ''
        self.firmwareStatus.emit(0, '')

        # BleUpdate process
        self.firmwareProcess = QProcess()
        self.firmwareProcess.readyReadStandardOutput.connect(self.onFirmwareDataReady)
        self.firmwareProcess.readyReadStandardError.connect(self.onFirmwareErrorReady)
        self.firmwareProcess.finished.connect(self.onFirmwareFinished)
        self.stopSignal.connect(self.firmwareProcess.kill)

        program = resource.path('exes/BleUpdate-1.3.9/bleupdate-cli.exe')
        args = [
            "update",
            resource.path(self.fwFileName),
        ]
        self.firmwareProcess.start(program, args)

    def onFirmwareDataReady(self):
        data = str(self.firmwareProcess.readAllStandardOutput(), 'utf-8')
        self.bleUpdateOutput += data
        percent, state = self.parseUpdateOutput()
        self.firmwareStatus.emit(percent, state)

    def onFirmwareErrorReady(self):
        data = str(self.firmwareProcess.readAllStandardError(), 'utf-8')
        print("STDERR:",data)
        self.bleUpdateOutput += data
        percent, state = self.parseUpdateOutput()
        self.firmwareStatus.emit(percent, state)

    def onFirmwareFinished(self, code, status):
        if code == 0:
            self.firmwareStatus.emit(100, 'Firmware complete')
            self.firmwareFinished.emit()
        elif self.isProgramming:
            self.firmwareStatus.emit(0, 'Firmware failed.')
            self.firmwareFailed.emit("Firmware failed: {}: {}".format(code, status))
        else:
            self.firmwareStatus.emit(0, 'Firmware stopped.')
        self.firmwareProcess = None
        self.isProgramming = False
        self.firmwareFinished.emit()

    def parseUpdateOutput(self):
        data = self.bleUpdateOutput
        # TODO: regex here to determine status and percent
        m = re.split(r'Sector \d: (\.+)', self.bleUpdateOutput, re.M)
        if len(m) > 1:
            percent = len(''.join(m[1:-1]).replace('\n','')) / self.totalBleUpdateLength * 100
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
