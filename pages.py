from PyQt5 import QtGui
from PyQt5.QtWidgets import (QWidget, QPushButton, QLabel, QVBoxLayout, QVBoxLayout, QMessageBox, QErrorMessage, QScrollArea)
from PyQt5.QtCore import pyqtSignal, pyqtSlot, QSize, Qt

import resource
from progress import ProgressBar

imageSize = 300

class BasePage(QWidget):
    finished = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.nextEnabled = True
        self.previousEnabled = True
        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)

    @pyqtSlot()
    def onEnter(self):
        pass

    @pyqtSlot()
    def onExit(self):
        pass

class StartPage(BasePage):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.previousEnabled = False

        title = QLabel("Welcome to SmartDrive MX2+ Programming")
        picture = QLabel(self)
        picture.setPixmap(QtGui.QPixmap(resource.path('images/mx2+.jpg')).scaled(QSize(imageSize, imageSize), Qt.KeepAspectRatio))

        self.layout.addWidget(title)
        self.layout.addWidget(picture)

    @pyqtSlot()
    def onEnter(self):
        super().finished.emit()

class BootloaderSwitchesPage(BasePage):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        title = QLabel("Configure Bootloader Programming")
        cableLabel = QLabel("Plug in the programming cables to the SmartDrive as shown below.")
        cablePicture = QLabel(self)
        cablePicture.setPixmap(QtGui.QPixmap(resource.path('images/cable.jpg')).scaled(QSize(imageSize, imageSize), Qt.KeepAspectRatio))
        switchesLabel = QLabel("Set the MX2+ DIP switches for bootloader programming as shown below.")
        switchesPicture = QLabel(self)
        switchesPicture.setPixmap(QtGui.QPixmap(resource.path('images/bootloaderProgramming.jpg')).scaled(QSize(imageSize, imageSize), Qt.KeepAspectRatio))

        self.layout.addWidget(title)
        self.layout.addWidget(cableLabel)
        self.layout.addWidget(cablePicture)
        self.layout.addWidget(switchesLabel)
        self.layout.addWidget(switchesPicture)

    @pyqtSlot()
    def onEnter(self):
        super().finished.emit()

class BootloaderPage(BasePage):
    start = pyqtSignal()
    stop = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.nextEnabled = False

        title = QLabel("Programming Bootloader")
        self.progressBar = ProgressBar()
        self.startButton = QPushButton("Start")
        self.startButton.clicked.connect(self.onStart)
        self.startButton.show()
        self.stopButton = QPushButton("Stop")
        self.stopButton.clicked.connect(self.onStop)
        self.stopButton.hide()

        self.layout.addWidget(title)
        self.layout.addWidget(self.progressBar)
        self.layout.addWidget(self.startButton)
        self.layout.addWidget(self.stopButton)

    @pyqtSlot(str)
    def onBootloaderFailed(self, status):
        msg = status.replace('\n','<br>')
        QMessageBox.critical(self, 'Bootloader Programming Failure',
                             msg, QMessageBox.Ok, QMessageBox.Ok)
        self.onStop()

    @pyqtSlot()
    def onBootloaderFinished(self):
        self.stopButton.hide()
        self.nextEnabled = True
        self.progressBar.setProgress(100, 'Bootloader Programming Complete!')
        super().finished.emit()

    @pyqtSlot(int, str)
    def onProgressUpdate(self, percent, status):
        self.progressBar.setProgress(percent, status)

    @pyqtSlot()
    def onStart(self):
        self.start.emit()
        self.startButton.hide()
        self.stopButton.show()

    @pyqtSlot()
    def onStop(self):
        self.stop.emit()
        self.startButton.show()
        self.stopButton.hide()

class FirmwareSwitchesPage(BasePage):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        title = QLabel("Configure Firmware Programming")
        switchesLabel = QLabel("Set the MX2+ DIP switches for firmware programming as shown below.")
        switchesPicture = QLabel(self)
        switchesPicture.setPixmap(QtGui.QPixmap(resource.path('images/firmwareProgramming.jpg')).scaled(QSize(imageSize, imageSize), Qt.KeepAspectRatio))

        self.layout.addWidget(title)
        self.layout.addWidget(switchesLabel)
        self.layout.addWidget(switchesPicture)

    @pyqtSlot()
    def onEnter(self):
        super().finished.emit()

class FirmwarePage(BasePage):
    start = pyqtSignal()
    stop = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.nextEnabled = False

        title = QLabel("Programming Firmware")
        self.progressBar = ProgressBar()
        self.startButton = QPushButton("Start")
        self.startButton.clicked.connect(self.onStart)
        self.startButton.show()
        self.stopButton = QPushButton("Stop")
        self.stopButton.clicked.connect(self.onStop)
        self.stopButton.hide()

        self.layout.addWidget(title)
        self.layout.addWidget(self.progressBar)
        self.layout.addWidget(self.startButton)
        self.layout.addWidget(self.stopButton)

    @pyqtSlot(str)
    def onFirmwareFailed(self, status):
        msg = status.replace('\n','<br>')
        QMessageBox.critical(self, 'MX2+ Firmware Programming Failure',
                             msg, QMessageBox.Ok, QMessageBox.Ok)
        self.onStop()

    @pyqtSlot()
    def onFirmwareFinished(self):
        self.stopButton.hide()
        self.nextEnabled = True
        self.progressBar.setProgress(100, 'Firmware Programming Complete!')
        super().finished.emit()

    @pyqtSlot(int, str)
    def onProgressUpdate(self, percent, status):
        self.progressBar.setProgress(percent, status)

    @pyqtSlot()
    def onStart(self):
        self.start.emit()
        self.startButton.hide()
        self.stopButton.show()

    @pyqtSlot()
    def onStop(self):
        self.stop.emit()
        self.startButton.show()
        self.stopButton.hide()

class EndPage(BasePage):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.nextEnabled = False

        title = QLabel("Set the MX2+ DIP switches for running the firmware as shown below.")
        picture = QLabel(self)
        picture.setPixmap(QtGui.QPixmap(resource.path('images/runMX2+.jpg')).scaled(QSize(imageSize, imageSize), Qt.KeepAspectRatio))

        self.layout.addWidget(title)
        self.layout.addWidget(picture)

    @pyqtSlot()
    def onEnter(self):
        super().finished.emit()

