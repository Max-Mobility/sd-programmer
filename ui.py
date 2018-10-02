import glob
import sys
import serial
from PyQt5 import QtGui
from PyQt5.QtWidgets import (QWidget, QProgressBar, QPushButton, QLabel, QCheckBox, QComboBox, QApplication, QMainWindow, QStyleFactory, QTextEdit, QDesktopWidget, QMessageBox, QVBoxLayout, QHBoxLayout, QSplitter)
from PyQt5.QtCore import QProcess, QBasicTimer, Qt

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
        self.port = None
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

        self.btn = QPushButton('Start', self)
        self.btn.clicked.connect(self.start)

        self.timer = QBasicTimer()
        self.step = 0

        # main controls
        self.mainWidget = QWidget()
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.pbar)
        self.layout.addWidget(self.btn)
        self.mainWidget.setLayout(self.layout)

        # console output
        self.output = QTextEdit()
        self.output.readOnly = True

        # lpc21isp process
        self.bootloaderProcess = QProcess()
        self.bootloaderProcess.readyRead.connect(self.bootloaderDataReady)

        self.splitter = QSplitter(Qt.Vertical)
        self.splitter.addWidget(self.mainWidget)
        self.splitter.addWidget(self.output)
        self.output.hide()

        self.setCentralWidget(self.splitter)
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

    # functions for controlling the bootloader
    def timerEvent(self, e):
        if self.step >= 100:
            self.timer.stop()
            self.btn.setText('Finished')
            return
        self.step = self.step + 1
        self.pbar.setValue(self.step)

    def start(self):
        if self.timer.isActive():
            self.bootloaderProcess.close()
            self.timer.stop()
            self.output.clear()
            self.btn.setText('Start')
            self.output.hide()
        else:
            self.step = 0
            self.output.show()
            program = './exes/lpc21isp'
            args = [
                "-wipe",
                "../ota-bootloader/src/ota-bootloader.hex",
                self.port,
                "38400",
                "12000"
            ]
            self.bootloaderProcess.start(program, args)
            self.timer.start(100, self)
            self.btn.setText('Stop')

    def bootloaderDataReady(self):
        data = str(self.bootloaderProcess.readAll(), 'utf-8')

        cursor = self.output.textCursor()
        cursor.movePosition(cursor.End)
        cursor.insertText(data)
        self.output.ensureCursorVisible()

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
