import glob
import sys
import serial
from PyQt5 import QtGui
from PyQt5.QtWidgets import (QWidget, QProgressBar, QPushButton, QLabel, QCheckBox, QComboBox, QApplication, QMainWindow, QStyleFactory, QTextEdit, QDesktopWidget, QMessageBox, QVBoxLayout, QHBoxLayout, QSplitter)
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

        self.pbar = QProgressBar(self)
        self.pbar.setGeometry(0,0,100, 10)

        self.pLabel = QLabel("")

        self.btn = QPushButton('Start', self)
        self.btn.clicked.connect(self.start)

        # main controls
        self.mainWidget = QWidget()
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.pbar)
        self.layout.addWidget(self.pLabel)
        self.layout.addWidget(self.btn)
        self.mainWidget.setLayout(self.layout)

        self.setCentralWidget(self.mainWidget)
        self.center()
        self.show()

    # Functions for serial port control
    def refreshPorts(self):
        print("Refreshing serial ports")
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
            print("Changing from {} to {}".format(self.port, newPort))
            self.port = newPort

    def onBootloaderState(self, percent, state):
        self.pbar.setValue(percent / 2)
        self.pLabel.setText(state)

    def onFirmwareState(self, percent, state):
        self.pbar.setValue(50 + percent / 2)
        self.pLabel.setText(state)

    def onBootloaderFinished(self):
        pass

    def onFirmwareFinished(self):
        pass

    def onCancel(self):
        pass

    # functions for controlling the bootloader
    def start(self):
        if self.port is None:
            return
        if self.smartDrive is not None and self.smartDrive.isProgramming:
            self.btn.setText('Start')
            self.smartDrive.stop()
        else:
            self.btn.setText('Stop')
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
            self.smartDrive.bootloaderFinished.connect(self.smartDrive.programFirmware)
            self.smartDrive.bootloaderFinished.connect(self.onBootloaderFinished)
            self.smartDrive.firmwareStatus.connect(self.onFirmwareState)
            self.smartDrive.firmwareFinished.connect(self.onFirmwareFinished)
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
