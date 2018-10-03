import glob
import sys
import serial
from PyQt5 import QtGui
from PyQt5.QtWidgets import (QWidget, QPushButton, QLabel, QComboBox, QApplication, QMainWindow, QStyleFactory, QDesktopWidget, QMessageBox, QErrorMessage, QFileDialog, QSplitter, QScrollArea)
from PyQt5.QtCore import QFileInfo, QFile, QProcess, QBasicTimer, Qt, QObject, QRunnable, QThread, QThreadPool, pyqtSignal

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

class Programmer(QMainWindow):
    def __init__(self):
        super().__init__()

        self.port = None
        self.thread = None
        self.smartDrive = None
        self.fwFileName = None
        self.initUI()
        self.initSD()

    def initUI(self):
        QApplication.setStyle(QStyleFactory.create('Cleanlooks'))
        self.setStyleSheet('''QToolTip {
                           background-color: black;
                           color: white;
                           border: black solid 1px
                           }''')
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

        openAction = Action(resource.path('icons/toolbar/open.png'), 'Select Firmware', self)
        openAction.setStatusTip('Open MX2+ OTA File.')
        openAction.setShortcut('Ctrl+O')
        openAction.triggered.connect(self.onOpenFirmwareFile)

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

        # Set up the toolbars for the program
        self.toolbar_init()
        self.toolbar_create('toolbar1')
        self.toolbar_add_action('toolbar1', exitAction)
        self.toolbar_add_separator('toolbar1')
        self.toolbar_add_action('toolbar1', refreshAction)
        self.toolbar_add_widget('toolbar1', QLabel('Serial Port: '))
        self.toolbar_add_widget('toolbar1', self.port_selector)
        self.toolbar_add_separator('toolbar1')
        self.toolbar_add_action('toolbar1', openAction)
        self.toolbar_add_widget('toolbar1', QLabel('MX2+ Firmware: '))
        self.firmwareLabel = QLabel()
        self.toolbar_add_widget('toolbar1', self.firmwareLabel)

        # main UI
        self.startPage = pages.StartPage()
        self.bootloaderSwitchesPage = pages.BootloaderSwitchesPage()
        self.bootloaderPage = pages.BootloaderPage()
        self.firmwareSwitchesPage = pages.FirmwareSwitchesPage()
        self.firmwarePage = pages.FirmwarePage()
        self.endPage = pages.EndPage()

        self.pager = Pager()
        self.pager.addPage(self.startPage)
        self.pager.addPage(self.bootloaderSwitchesPage)
        self.pager.addPage(self.bootloaderPage)
        self.pager.addPage(self.firmwareSwitchesPage)
        self.pager.addPage(self.firmwarePage)
        self.pager.addPage(self.endPage)

        # main controls
        '''
        self.scrollArea = QScrollArea(self)
        self.scrollArea.setWidget(self.pager)
        self.scrollArea.setWidgetResizable(True)
        self.setCentralWidget(self.scrollArea)
        '''
        self.setCentralWidget(self.pager)
        #self.setGeometry(300, 300, 800, 600)
        self.center()
        self.show()

    def initSD(self):
        # manage the smartdrive thread
        self.thread = QThread()
        # create the smartdrive
        self.smartDrive = SmartDrive(self.port)
        # move the smartdrive to the thread
        self.smartDrive.moveToThread(self.thread)
        # wire up all the events
        self.port_selector.activated[str].connect(self.smartDrive.onPortSelected)

        self.smartDrive.bootloaderStatus.connect(self.bootloaderPage.onProgressUpdate)
        self.smartDrive.bootloaderFailed.connect(self.bootloaderPage.onBootloaderFailed)
        self.smartDrive.bootloaderFinished.connect(self.bootloaderPage.onBootloaderFinished)
        self.bootloaderPage.start.connect(self.smartDrive.programBootloader)
        self.bootloaderPage.stop.connect(self.smartDrive.stop)

        self.smartDrive.firmwareStatus.connect(self.firmwarePage.onProgressUpdate)
        self.smartDrive.firmwareFinished.connect(self.firmwarePage.onFirmwareFinished)
        self.smartDrive.firmwareFailed.connect(self.firmwarePage.onFirmwareFailed)
        self.firmwarePage.start.connect(self.smartDrive.programFirmware)
        self.firmwarePage.stop.connect(self.smartDrive.stop)
        # start the thread
        self.thread.start()

    # Functions for serial port control
    def refreshPorts(self):
        self.serial_ports = listSerialPorts()
        self.port_selector.clear()
        self.port_selector.addItems(self.serial_ports)
        if self.port is not None and self.port in self.serial_ports:
            self.port_selector.setCurrentIndex(
                self.serial_ports.index(self.port)
            )
        else:
            self.port_selector.setCurrentIndex(-1)

    def changePort(self, newPort):
        if newPort != self.port:
            self.port = newPort

    def invalidFirmwareFile(self, err):
        msg = err.replace('\n', '<br>')
        QMessageBox.critical(self, 'Bad Firmware File', msg, QMessageBox.Ok, QMessageBox.Ok)

    # functions for selecting the MX2+ firmware file
    def onOpenFirmwareFile(self):
        self.fwFileName, _ = QFileDialog.getOpenFileName(
            self,
            'Select MX2+ Firmware OTA File',
            '',
            'OTA Files (*.ota)',
            options=QFileDialog.Options()
        )
        self.smartDrive.onFirmwareFileSelected(self.fwFileName)
        labelText = "<b><i>{}</i></b>".format(QFileInfo(QFile(self.fwFileName)).fileName())
        self.firmwareLabel.setText(labelText)

    # functions for controlling the programming
    def stop(self):
        self.smartDrive.stop()
        self.thread.quit()
        self.thread.wait()

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
