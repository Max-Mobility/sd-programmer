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

    status = pyqtSignal(int, str)
    deviceInfo = pyqtSignal(str, str, str)

    listFinished = pyqtSignal()
    getFinished = pyqtSignal()
    firmwareFinished = pyqtSignal()

    failed = pyqtSignal(str)
    stopSignal = pyqtSignal()

    def __init__(self, fwFileName=None):
        super().__init__()
        self.isProgramming = False
        self.fwFileName = None
        self.serial = None
        self.licenseKey = None
        self.address = None

        if fwFileName is not None:
            self.onFirmwareFileSelected(fwFileName)

        self.firmwarePercent = 0
        self.firmwareState = ''

        self.listProcess = None
        self.getProcess = None
        self.firmwareProcess = None

        
        self.listFinished.connect(self.getDeviceInfo)
        self.getFinished.connect(self.programFirmware)

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
    def start(self):
        '''Determines if there is a valid cc-debugger attached to the system'''
        self.firmwarePercent = 0
        self.status.emit(0, '')
        self.resetDeviceInfo()

        # BleUpdate process
        self.isProgramming = True
        self.listOutput = ''
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
        self.listOutput += data
        found, state = self.parseListOutput()
        self.status.emit(0, state)

    def onListErrorReady(self):
        data = str(self.listProcess.readAllStandardError(), 'utf-8')
        print("STDERR:",data)
        self.listOutput += data
        found, state = self.parseListOutput()
        self.status.emit(0, state)

    def onListFinished(self, code, status):
        found, state = self.parseListOutput()
        if code == 0 and found:
            self.status.emit(0, 'Found CC-Debugger')
            self.listFinished.emit()
        elif self.isProgramming:
            self.status.emit(0, 'Could not find CC-Debugger, check to make sure it is plugged in and drivers are installed.')
            self.failed.emit("Could not find CC-Debugger.")
        else:
            self.listStatus.emit(0, 'Stopped.')
            self.listFinished.emit()
        self.listProcess = None

    def parseListOutput(self):
        data = self.listOutput
        # TODO: regex here to determine status and percent
        m = re.search(r'CC Debugger', self.listOutput, re.M)
        if m is not None:
            return True, 'Found CC-Debugger'
        else:
            return False, 'No CC-Debugger Found'

    def resetDeviceInfo(self):
        # reset device info
        self.serial = None
        self.licenseKey = None
        self.address = None
        self.deviceInfo.emit(self.serial, self.licenseKey, self.address)

    @pyqtSlot()
    def getDeviceInfo(self):
        '''Gets the MAC Address and License Key from the Device before proramming'''
        self.resetDeviceInfo()

        # BleUpdate process
        self.isProgramming = True
        self.getOutput = ''
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
        self.getOutput += data
        gotData, state = self.parseGetOutput()
        self.status.emit(0, state)

    def onGetErrorReady(self):
        data = str(self.getProcess.readAllStandardError(), 'utf-8')
        print("STDERR:",data)
        self.getOutput += data
        gotData, state = self.parseGetOutput()
        self.status.emit(0, state)

    def onGetFinished(self, code, status):
        gotData, state = self.parseGetOutput()
        if code == 0 and gotData:
            self.status.emit(0, 'Got Device Info')
            self.getFinished.emit()
        elif self.isProgramming:
            self.status.emit(0, 'Could not get dvice info:\n' + state + '\nMake sure SmartDrive is on and the CC-Debugger light is GREEN')
            self.failed.emit("Could not get device info")
        else:
            self.status.emit(0, 'Get stopped.')
        self.getProcess = None

    def parseGetOutput(self):
        data = self.getOutput
        # TODO: regex here to determine status and percent
        if len(data) > 1:
            error = re.search(r'error', self.getOutput, re.M)
            if error is not None:
                return False, self.getOutput
            s = re.search(r'Serial number\s*:\s*([\d\w]+)', self.getOutput, re.M)
            a = re.search(r'Address\s*:\s*([\d:\w]+)', self.getOutput, re.M)
            l = re.search(r'License key\s*:\s*([\d\w]+)', self.getOutput, re.M)
            if a is not None and l is not None and s is not None:
                self.serial = s[1]
                self.address = a[1]
                self.licenseKey = l[1]
                self.deviceInfo.emit(self.serial, self.licenseKey, self.address)
                return True, 'Got device info.'
        return False, 'Could not get device info.'

    @pyqtSlot()
    def programFirmware(self):
        self.firmwarePercent = 0
        self.status.emit(0, 'Programming SmartDrive Bluetooth')

        # BleUpdate process
        self.isProgramming = True
        self.updateOutput = ''
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
        self.updateOutput = data
        percent, state = self.parseUpdateOutput()
        self.status.emit(percent, state)

    def onFirmwareErrorReady(self):
        data = str(self.firmwareProcess.readAllStandardError(), 'utf-8')
        print("STDERR:",data)
        self.updateOutput += data
        percent, state = self.parseUpdateOutput()
        self.status.emit(percent, state)

    def onFirmwareFinished(self, code, status):
        if code == 0:
            self.status.emit(100, 'SmartDrive Bluetooth complete')
            self.firmwareFinished.emit()
        elif self.isProgramming:
            self.status.emit(0, 'SmartDrive Bluetooth failed.')
            self.failed.emit("SmartDrive Bluetooth failed: {}: {}".format(code, status))
        else:
            self.status.emit(0, 'Stopped.')
            self.firmwareFinished.emit()
        self.firmwareProcess = None
        self.isProgramming = False

    def parseUpdateOutput(self):
        data = self.updateOutput
        # TODO: regex here to determine status and percent
        m = re.search(r'([\d]+)', self.updateOutput, re.M)
        if m is not None:
            percent = int(m.group(1))
        else:
            percent = 0
        status = "Writing SmartDrive Bluetooth Firmware."
        return percent, status

    @pyqtSlot()
    def stop(self):
        self.resetDeviceInfo()

        self.isProgramming = False
        self.stopSignal.emit()
