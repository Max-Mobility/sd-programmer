import glob
import sys
import serial
from PyQt5 import QtGui
from PyQt5.QtWidgets import (QWidget, QProgressBar, QPushButton, QLabel, QCheckBox, QComboBox, QApplication, QMainWindow, QStyleFactory, QTextEdit, QDesktopWidget, QMessageBox, QErrorMessage, QVBoxLayout, QHBoxLayout, QSplitter)
from PyQt5.QtCore import QProcess, QBasicTimer, Qt, QObject, QRunnable, QThread, QThreadPool, pyqtSignal

import resource
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
        self.initUI()

    def initUI(self):
        QApplication.setStyle(QStyleFactory.create('Cleanlooks'))
        self.setStyleSheet('''QToolTip {
                           background-color: black;
                           color: white;
                           border: black solid 1px
                           }''')
        self.setGeometry(300, 300, 800, 600)
        self.setWindowTitle('Programmer')

        # Create the actions for the program
        exitAction = Action(resource.path('icons/toolbar/exit.png'), 'Exit', self)
        exitAction.setShortcut('Ctrl+Q')
        exitAction.setStatusTip('Exit application')
        exitAction.triggered.connect(self.close)

        refreshAction = Action(resource.path('icons/toolbar/refresh.png'), 'Refresh', self)
        refreshAction.setShortcut('Ctrl+R')
        refreshAction.setStatusTip('Refresh Serial Port List')
        refreshAction.triggered.connect(self.refreshPorts)

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

        # Set up the toolbars for the program
        self.toolbar_init()
        self.toolbar_create('toolbar1')
        self.toolbar_add_action('toolbar1', exitAction)
        self.toolbar_add_widget('toolbar1', self.port_selector)
        self.toolbar_add_action('toolbar1', refreshAction)

        # main UI
        self.pbar = QProgressBar(self)
        self.pbar.setGeometry(0,0,100, 10)
        # progress bar label
        self.pLabel = QLabel("")

        self.startButton = QPushButton('Start', self)
        self.startButton.clicked.connect(self.start)
        self.stopButton = QPushButton('Stop', self)
        self.stopButton.clicked.connect(self.stop)
        self.stopButton.hide()

        # UI for when the user needs to flip the DIP switches
        self.actionLabel = QLabel("")
        self.actionLabel.hide()
        self.actionButton = QPushButton('', self)
        self.actionButton.clicked.connect(self.performAction)
        self.actionButton.hide()

        self.begin()

        # main controls
        self.mainWidget = QWidget()
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.pbar)
        self.layout.addWidget(self.pLabel)
        self.layout.addWidget(self.actionLabel)
        self.layout.addWidget(self.actionButton)
        self.layout.addWidget(self.startButton)
        self.layout.addWidget(self.stopButton)
        self.mainWidget.setLayout(self.layout)

        self.setCentralWidget(self.mainWidget)
        self.center()
        self.show()

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

    # updating the display
    def updateProgressBar(self):
        self.pbar.setValue((self.bootloaderPercent + self.firmwarePercent) / 2.0)

    # callbacks from smartdrive programming state signals
    def onBootloaderState(self, percent, state):
        self.bootloaderPercent = percent
        self.updateProgressBar()
        self.pLabel.setText(state)

    def onFirmwareState(self, percent, state):
        self.firmwarePercent = percent
        self.updateProgressBar()
        self.pLabel.setText(state)

    def onBootloaderFinished(self):
        self.showAction(
            'Set the DIP switches to Firmware Programming',
            'Press when DIP switches are set.'
        )
        self.actionButton.clicked.connect(self.smartDrive.programFirmware)

    def onBootloaderFailed(self, status):
        msg = self.smartDrive.lpc21ispOutput.replace('\n','<br>')
        QMessageBox.critical(self, 'Bootloader Programming Failure',
                             msg, QMessageBox.Ok, QMessageBox.Ok)
        self.stop()

    def onFirmwareFailed(self, status):
        msg = status.replace('\n','<br>')
        QMessageBox.critical(self, 'MX2+ Firmware Programming Failure',
                             msg, QMessageBox.Ok, QMessageBox.Ok)
        self.stop()

    def onFirmwareFinished(self):
        msg = 'MX2+ firmware successfully programmed!'
        QMessageBox.information(self, 'Success', msg, QMessageBox.Ok, QMessageBox.Ok)
        self.stop()

    # functions for controlling the programming
    def showAction(self, labelText, buttonText):
        self.actionLabel.setText(labelText)
        self.actionLabel.show()
        self.actionButton.setText(buttonText)
        self.actionButton.show()

    def performAction(self):
        self.actionLabel.hide()
        self.actionButton.hide()

    def hideAll(self):
        self.pbar.hide()
        self.pLabel.hide()
        self.startButton.hide()
        self.stopButton.hide()
        self.actionLabel.hide()
        self.actionButton.hide()

    def stop(self):
        if self.smartDrive is not None and self.smartDrive.isProgramming:
            self.smartDrive.stop()
        self.hideAll()
        self.begin()

    def begin(self):
        self.hideAll()
        self.showAction(
            'Set the DIP switches to Bootloader Programming',
            'Press when DIP switches are set.'
        )
        self.actionButton.clicked.connect(self.startAvailable)

    def startAvailable(self):
        self.hideAll()
        self.startButton.show()
        self.actionButton.clicked.disconnect(self.startAvailable)

    def start(self):
        if self.port is None:
            err_dialog = QErrorMessage(self)
            err_dialog.showMessage('You must select a valid serial port!')
            return
        # reset all progrees and update the progress bar
        self.bootloaderPercent = 0
        self.firmwarePercent = 0
        self.updateProgressBar()
        # since we've started, hide the start button and show the stop button
        self.hideAll()
        self.stopButton.show()
        self.pbar.show()
        self.pLabel.show()
        # manage the smartdrive thread
        if self.thread is not None:
            self.thread.quit()
            self.thread.wait()
        self.thread = QThread()
        # open the firmware file
        try:
            f = open('./firmwares/MX2+.15.ota', 'rb')
        except Exception as error:
            print("ERROR: Couldn't open file {}".format(filename))
            return
        else:
            with f:
                fileData = bytearray(f.read())
        # create the smartdrive
        self.smartDrive = SmartDrive(self.port, fileData)
        # move the smartdrive to the thread
        self.smartDrive.moveToThread(self.thread)
        # wire up all the events
        self.smartDrive.bootloaderStatus.connect(self.onBootloaderState)
        self.smartDrive.bootloaderFailed.connect(self.onBootloaderFailed)
        self.smartDrive.bootloaderFailed.connect(self.thread.quit)
        self.smartDrive.bootloaderFinished.connect(self.onBootloaderFinished)

        self.smartDrive.firmwareStatus.connect(self.onFirmwareState)
        self.smartDrive.firmwareFinished.connect(self.onFirmwareFinished)
        self.smartDrive.firmwareFinished.connect(self.thread.quit)
        self.smartDrive.firmwareFailed.connect(self.onFirmwareFailed)
        self.smartDrive.firmwareFailed.connect(self.thread.quit)
        self.thread.started.connect(self.smartDrive.programBootloader)
        # start the thread
        self.thread.start()

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
        toolbar_remove

    from action import \
        action_init, \
        action_create

    from context_menu import \
        context_menu_init, \
        context_menu_create, \
        context_menu_add_action
