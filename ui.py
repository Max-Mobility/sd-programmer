import glob
import sys
import serial
import serial.tools.list_ports
from PyQt5 import QtGui
from PyQt5.QtWidgets import (QWidget, QPushButton, QLabel, QComboBox, QApplication, QMainWindow, QStyleFactory, QDesktopWidget, QMessageBox, QErrorMessage, QFileDialog, QSplitter, QScrollArea)
from PyQt5.QtCore import QFileInfo, QFile, QProcess, QTimer, QBasicTimer, Qt, QObject, QRunnable, QThread, QThreadPool, pyqtSignal

import resource
import pages
from pager import Pager
from smartdrive import SmartDrive

from action import\
    Action

def listSerialPorts():
    """ Lists serial port names

        :raises EnvironmentError:
            On unsupported or unknown platforms
        :returns:
            A list of the serial ports available on the system
    """
    portDesc = ''
    if sys.platform.startswith('win'):
        portDesc = 'USB Serial Port'
    elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        portDesc = 'TTL232R-3V3'
    elif sys.platform.startswith('darwin'):
        portDesc = 'TTL232R-3V3'
    else:
        raise EnvironmentError('Unsupported platform')

    ports = list(serial.tools.list_ports.comports())
    result = []
    for p in ports:
        if portDesc in p.description:
            try:
                s = serial.Serial(p.device)
                s.close()
                result.append(p.device)
            except (OSError, serial.SerialException) as inst:
                print(inst)
                pass

    return result

class Programmer(QMainWindow):
    def __init__(self):
        super().__init__()

        self.port = None
        self.sdthread = None
        self.sdbtthread = None
        self.smartDrive = None
        self.fwFileName = None
        self.bleFileName = None
        self.initUI()
        self.initSD()

    def initUI(self):
        QApplication.setStyle(QStyleFactory.create('Cleanlooks'))

        self.setStyleSheet("QLabel {font: 15pt} QPushButton {font: 15pt}")
        self.setWindowTitle('Programmer')

        # Create the actions for the program
        exitAction = Action(resource.path('icons/toolbar/exit.png'), 'Exit Programmer', self)
        exitAction.setShortcut('Ctrl+Q')
        exitAction.setStatusTip('Exit application')
        exitAction.triggered.connect(self.close)

        refreshAction = Action(resource.path('icons/toolbar/refresh.png'), 'Refresh Serial Ports', self)
        refreshAction.setShortcut('Ctrl+R')
        refreshAction.setStatusTip('Refresh Serial Port List')
        refreshAction.triggered.connect(self.refreshPorts)

        openAction = Action(resource.path('icons/toolbar/open.png'), 'Select MX2+ Firmware', self)
        openAction.setStatusTip('Open MX2+ OTA File.')
        openAction.setShortcut('Ctrl+O')
        openAction.triggered.connect(self.onOpenFirmwareFile)

        openBleAction = Action(resource.path('icons/toolbar/open.png'), 'Select BLE Firmware', self)
        openBleAction.setStatusTip('Open BLE Project File.')
        openBleAction.setShortcut('Ctrl+B')
        openBleAction.triggered.connect(self.onOpenBLEProject)

        aboutAction = Action(resource.path('icons/toolbar/about.png'), 'About', self)
        aboutAction.setStatusTip('About MX2+ Programmer')
        aboutAction.triggered.connect(self.about)

        switchInfoAction = Action(resource.path('icons/toolbar/info.png'), 'DIP Switch Info', self)
        switchInfoAction.setStatusTip('MX2+ DIP Switch Info')
        switchInfoAction.triggered.connect(self.showSwitchInfo)

        bleInfoAction = Action(resource.path('icons/toolbar/info.png'), 'BLE Programmer Info', self)
        bleInfoAction.setStatusTip('BLE Programmer Info')
        bleInfoAction.triggered.connect(self.showBLEInfo)

        # Create the widgets for the program (embeddable in the
        # toolbar or elsewhere)
        self.port_selector = QComboBox(self)
        self.refreshPorts()
        self.port_selector.activated[str].connect(self.changePort)

        # Set up the Menus for the program
        self.menubar_init()
        self.menubar_add_menu('&File')
        self.menu_add_action('&File', exitAction)
        self.menu_add_action('&File', refreshAction)
        self.menu_add_action('&File', openAction)
        self.menu_add_action('&File', openBleAction)

        self.menubar_add_menu('&Help')
        self.menu_add_action('&Help', aboutAction)
        self.menu_add_action('&Help', switchInfoAction)
        self.menu_add_action('&Help', bleInfoAction)

        # Set up the toolbars for the program
        self.toolbar_init()
        self.toolbar_create('toolbar1')
        self.toolbar_add_action('toolbar1', exitAction)

        self.toolbar_add_separator('toolbar1')
        self.toolbar_add_action('toolbar1', refreshAction)
        self.toolbar_add_widget('toolbar1', QLabel(' Serial Port: '))
        self.toolbar_add_widget('toolbar1', self.port_selector)

        self.toolbar_add_separator('toolbar1')
        self.toolbar_add_action('toolbar1', openAction)

        self.toolbar_add_widget('toolbar1', QLabel(' MX2+ Version: '))
        self.firmwareLabel = QLabel('<b><i>unknown</i></b>')
        self.toolbar_add_widget('toolbar1', self.firmwareLabel)

        self.toolbar_add_widget('toolbar1', QLabel(' crc: '))
        self.crcLabel = QLabel('<b><i>unknown</i></b>')
        self.toolbar_add_widget('toolbar1', self.crcLabel)

        self.toolbar_add_separator('toolbar1')
        self.toolbar_add_action('toolbar1', openBleAction)
        self.toolbar_add_widget('toolbar1', QLabel(' BLE: '))
        self.bleLabel = QLabel('<b><i>unknown</i></b>')
        self.toolbar_add_widget('toolbar1', self.bleLabel)

        # main UI
        self.startPage = pages.StartPage()
        self.bootloaderPage = pages.BootloaderPage()
        self.firmwarePage = pages.FirmwarePage()
        self.blePage = pages.BLEPage()
        self.endPage = pages.EndPage()

        self.pager = Pager()
        self.pager.addPage(self.startPage)
        self.pager.addPage(self.bootloaderPage)
        self.pager.addPage(self.firmwarePage)
        self.pager.addPage(self.blePage)
        self.pager.addPage(self.endPage)

        # main controls
        '''
        self.scrollArea = QScrollArea(self)
        self.scrollArea.setWidget(self.pager)
        self.scrollArea.setWidgetResizable(True)
        self.setCentralWidget(self.scrollArea)
        '''
        self.setCentralWidget(self.pager)
        self.setGeometry(0, 0, 1200, 1000)
        self.center()
        self.show()
        #self.setFixedSize(self.size())

        # force the user to select OTA file
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.onOpenFirmwareFile)
        self.timer.start(500)

        # force the user to select project.bgproj file
        self.timer2 = QTimer()
        self.timer2.setSingleShot(True)
        self.timer2.setInterval(500)
        self.timer2.timeout.connect(self.onOpenBLEProject)
        self.timer.timeout.connect(self.timer2.start)

    def initSD(self):
        # manage the smartdrive thread
        self.sdthread = QThread()
        # create the smartdrive
        self.smartDrive = SmartDrive(self.port)
        # move the smartdrive to the thread
        self.smartDrive.moveToThread(self.sdthread)

        # manage the smartdrive bluetooth thread
        self.sdbtthread = QThread()
        # create the smartdrive bluetooth
        self.smartDriveBluetooth = SmartDriveBluetooth()
        # move the smartdrive to the thread
        self.smartDriveBluetooth.moveToThread(self.sdbtthread)

        # wire up all the events
        self.port_selector.currentIndexChanged[str].connect(self.smartDrive.onPortSelected)

        self.smartDrive.invalidFirmware.connect(self.onInvalidFirmwareFile)

        # bootloader page
        self.smartDrive.bootloaderStatus.connect(self.bootloaderPage.onProgressUpdate)
        self.smartDrive.bootloaderFailed.connect(self.bootloaderPage.onBootloaderFailed)
        self.smartDrive.bootloaderFinished.connect(self.bootloaderPage.onBootloaderFinished)
        self.bootloaderPage.start.connect(self.smartDrive.programBootloader)
        self.bootloaderPage.stop.connect(self.smartDrive.stop)
        self.bootloaderPage.finished.connect(self.pager.onNext)

        # smartdrive page
        self.smartDrive.firmwareStatus.connect(self.firmwarePage.onProgressUpdate)
        self.smartDrive.firmwareFinished.connect(self.firmwarePage.onFirmwareFinished)
        self.smartDrive.firmwareFailed.connect(self.firmwarePage.onFirmwareFailed)
        self.firmwarePage.start.connect(self.smartDrive.programFirmware)
        self.firmwarePage.stop.connect(self.smartDrive.stop)
        self.firmwarePage.finished.connect(self.pager.onNext)

        # ble page
        self.blePage.begin.connect(self.onStartBle)
        self.smartDriveBluetooth.status.connect(self.blePage.onProgressUpdate)
        self.smartDriveBluetooth.firmwareFinished.connect(self.blePage.onFirmwareFinished)
        self.smartDriveBluetooth.failed.connect(self.blePage.onFirmwareFailed)
        self.blePage.start.connect(self.smartDriveBluetooth.start)
        self.blePage.stop.connect(self.smartDriveBluetooth.stop)
        self.blePage.finished.connect(self.pager.onNext)

        self.endPage.finished.connect(self.bootloaderPage.reset)
        self.endPage.finished.connect(self.firmwarePage.reset)
        self.endPage.finished.connect(self.blePage.reset)
        # start the SD thread
        self.sdthread.start()
        # start the SDBT thread
        self.sdbtthread.start()

    # Functions for serial port control
    def refreshPorts(self):
        self.serial_ports = listSerialPorts()
        self.port_selector.clear()
        self.port_selector.addItems(self.serial_ports)
        if self.port is None and len(self.serial_ports):
            self.port = self.serial_ports[0]
        if self.port is not None and len(self.serial_ports):
            self.port_selector.setCurrentIndex(
                self.serial_ports.index(self.port)
            )
        else:
            self.port_selector.setCurrentIndex(-1)

    def changePort(self, newPort):
        if newPort != self.port:
            self.port = newPort

    # functions for selecting the MX2+ firmware file
    def onStartBle(self):
        if self.bleFileName is not None:
            resource.open(self.bleFileName)

    def onInvalidFirmwareFile(self, err):
        QMessageBox.critical(
            self, 'OTA File Error', err.replace('\n', '<br>'),
            QMessageBox.Ok, QMessageBox.Ok)

    def onOpenFirmwareFile(self):
        fname, _ = QFileDialog.getOpenFileName(
            self,
            'Select MX2+ Firmware OTA File',
            '',
            'OTA Files (*.ota)',
            options=QFileDialog.Options()
        )
        if fname is not None and len(fname) > 0:
            self.fwFileName = fname
            self.smartDrive.onFirmwareFileSelected(self.fwFileName)
            self.firmwareLabel.setText('<b><i>{}</i></b>'.format(self.smartDrive.version))
            self.crcLabel.setText('<b><i>{}</i></b>'.format(self.smartDrive.crc))

    def onOpenBLEProject(self):
        fname, _ = QFileDialog.getOpenFileName(
            self,
            'Select SmartDrive BLE Project File',
            '',
            'BGPROJ Files (*.bgproj)',
            options=QFileDialog.Options()
        )
        if fname is not None and len(fname) > 0:
            self.bleFileName = fname
            self.bleLabel.setText('<b><i>{}</i></b>'.format(self.bleFileName))

    # functions for controlling the programming
    def stop(self):
        self.smartDrive.stop()
        self.sdthread.quit()
        self.sdthread.wait()
        self.smartDriveBluetooth.stop()
        self.sdbtthread.quit()
        self.sdbtthread.wait()

    # general functions
    def about(self):
        msg = '''
SmartDrive MX2+ Programmer

This program walks the user through the programming process for the software on the SmartDrive MX2+.

It allows the user to select the serial port on which they've connected the SmartDrive, as well as the specific firmware file they wish to upload to the SmartDrive.
        '''
        QMessageBox.information(
            self, 'About', msg.replace('\n', '<br>'),
            QMessageBox.Ok, QMessageBox.Ok)

    def showSwitchInfo(self):
        msg = '''
1. Required for programming bootloader
2. Required for programming SmartDrive
3. Cleans the SmartDrive EEPROM
4. UNUSED
5. Locks the settings on the SD to what they are at that time (or what is saved in the SD EEPROM)
6. UNUSED
7. Limit the max speed to 6 km/h
8. Force boot into bootloader for bluetooth OTA programming (DEBUGGING ONLY)
        '''
        QMessageBox.information(
            self, 'DIP Switch Info', msg.replace('\n', '<br>'),
            QMessageBox.Ok, QMessageBox.Ok)

    def showBLEInfo(self):
        msg = '''
To program the SmartDrive bluetooth chip you must have BLE SW Update tool installed. Once it is installed, you will need to tell the tool where 'bgbuild.exe' is located on your system. To do this, press the 'BGBuild' menu button in the TOP LEFT of the BLE SW Update Tool and press 'Select manually...' - the bgbuild.exe should be in the folder 'C:\\Bluegiga\\ble-1.5.0-137\\bin'
        '''
        QMessageBox.information(
            self, 'BLE Programming Info', msg.replace('\n', '<br>'),
            QMessageBox.Ok, QMessageBox.Ok)

    # window functions
    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def closeEvent(self, event):
        reply = QMessageBox.question(
            self, 'Quit',
            'Sure you want to quit?', QMessageBox.Yes |
            QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            self.stop()
            event.accept()
        else:
            event.ignore()

    from menubar import \
        menubar_init, \
        menubar_add_menu, \
        menu_add_action

    from toolbar import \
        toolbar_init, \
        toolbar_create, \
        toolbar_add_action, \
        toolbar_add_widget, \
        toolbar_add_separator, \
        toolbar_remove

    from action import \
        action_init, \
        action_create

    from context_menu import \
        context_menu_init, \
        context_menu_create, \
        context_menu_add_action
