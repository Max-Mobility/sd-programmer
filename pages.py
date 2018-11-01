from PyQt5 import QtGui
from PyQt5.QtWidgets import (QWidget, QPushButton, QLabel, QVBoxLayout, QVBoxLayout, QMessageBox, QErrorMessage, QScrollArea, QSizePolicy)
from PyQt5.QtCore import pyqtSignal, pyqtSlot, QSize, Qt

import resource
from progress import ProgressBar

class BasePage(QWidget):
    finished = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self._pager = None
        self.nextEnabled = True
        self.previousEnabled = True
        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        self.setSizePolicy(QSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored))

        self.setStyleSheet("QLabel {font: 20pt}")

        self.labels = []

    @pyqtSlot()
    def onEnter(self):
        pass

    def setPager(self, pager):
        self._pager = pager

    def getButtonHeight(self):
        if self._pager is not None:
            return self._pager.getButtonHeight()
        else:
            return 100

    @pyqtSlot()
    def onExit(self):
        pass

    def getPictureSize(self):
        s = self.size() - QSize(0, self.getButtonHeight())
        for l in self.labels:
            s -= QSize(0, l.size().height())
        return QSize(max(400, s.width()), max(400, s.height()))

class StartPage(BasePage):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.previousEnabled = False

        self.pixMap = QtGui.QPixmap(resource.path('images/cable.jpg'))

        title = QLabel("Welcome to SmartDrive MX2+ Programming")
        cableLabel = QLabel("Plug in the programming cables to the SmartDrive as shown below.\nMake sure the SmartDrive is OFF.")
        cableLabel.setWordWrap(True)
        self.labels = [title, cableLabel]
        self.cablePicture = QLabel(self)
        #self.cablePicture.setPixmap(self.pixMap.scaled(self.getPictureSize(), Qt.KeepAspectRatio))
        self.cablePicture.setPixmap(self.pixMap.scaledToHeight(self.getPictureSize().height()))

        self.layout.addWidget(title)
        self.layout.addWidget(cableLabel)
        self.layout.addWidget(self.cablePicture)

    @pyqtSlot()
    def onEnter(self):
        super().finished.emit()

    def resizeEvent(self, event):
        i = self.layout.indexOf(self.cablePicture)
        self.layout.removeWidget(self.cablePicture)
        self.cablePicture.setParent(None)
        self.cablePicture = QLabel(self)
        #self.cablePicture.setPixmap(self.pixMap.scaled(self.getPictureSize(), Qt.KeepAspectRatio))
        self.cablePicture.setPixmap(self.pixMap.scaledToHeight(self.getPictureSize().height()))
        self.layout.insertWidget(i, self.cablePicture)

class BootloaderPage(BasePage):
    start = pyqtSignal()
    stop = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.nextEnabled = False

        title = QLabel("Programming Bootloader")
        switchesLabel = QLabel("Set the MX2+ DIP switches for bootloader programming as shown below.\nThen power-cycle the SmartDrive.")
        switchesLabel.setWordWrap(True)
        self.pixMap = QtGui.QPixmap(resource.path('images/bootloaderProgramming.jpg'))

        self.progressBar = ProgressBar()
        self.startButton = QPushButton("Start")
        self.startButton.clicked.connect(self.onStart)
        self.startButton.show()
        self.stopButton = QPushButton("Stop")
        self.stopButton.clicked.connect(self.onStop)
        self.stopButton.hide()

        self.labels = [title, switchesLabel, self.progressBar, self.startButton, self.stopButton]

        self.switchesPicture = QLabel(self)
        self.switchesPicture.setPixmap(self.pixMap.scaledToHeight(self.getPictureSize().height()))

        self.layout.addWidget(title)
        self.layout.addWidget(switchesLabel)
        self.layout.addWidget(self.switchesPicture)
        self.layout.addWidget(self.progressBar)
        self.layout.addWidget(self.startButton)
        self.layout.addWidget(self.stopButton)

    def resizeEvent(self, event):
        i = self.layout.indexOf(self.switchesPicture)
        self.layout.removeWidget(self.switchesPicture)
        self.switchesPicture.setParent(None)
        self.switchesPicture = QLabel(self)
        self.switchesPicture.setPixmap(self.pixMap.scaledToHeight(self.getPictureSize().height()))
        self.layout.insertWidget(i, self.switchesPicture)

    @pyqtSlot()
    def reset(self):
        self.onStop()
        self.progressBar.setProgress(0, '')
        self.nextEnabled = False

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

class FirmwarePage(BasePage):
    start = pyqtSignal()
    stop = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.nextEnabled = False

        self.pixMap = QtGui.QPixmap(resource.path('images/firmwareProgramming.jpg'))

        title = QLabel("Programming Firmware")
        self.progressBar = ProgressBar()
        self.startButton = QPushButton("Start")
        self.startButton.clicked.connect(self.onStart)
        self.startButton.show()
        self.stopButton = QPushButton("Stop")
        self.stopButton.clicked.connect(self.onStop)
        self.stopButton.hide()

        switchesLabel = QLabel("Set the MX2+ DIP switches for firmware programming as shown below.\nThen power-cycle the SmartDrive.")
        switchesLabel.setWordWrap(True)

        self.labels = [title, self.progressBar, self.startButton, self.stopButton]

        self.switchesPicture = QLabel(self)
        self.switchesPicture.setPixmap(self.pixMap.scaledToHeight(self.getPictureSize().height()))

        self.layout.addWidget(title)
        self.layout.addWidget(switchesLabel)
        self.layout.addWidget(self.switchesPicture)
        self.layout.addWidget(self.progressBar)
        self.layout.addWidget(self.startButton)
        self.layout.addWidget(self.stopButton)

    def resizeEvent(self, event):
        i = self.layout.indexOf(self.switchesPicture)
        self.layout.removeWidget(self.switchesPicture)
        self.switchesPicture.setParent(None)
        self.switchesPicture = QLabel(self)
        self.switchesPicture.setPixmap(self.pixMap.scaledToHeight(self.getPictureSize().height()))
        self.layout.insertWidget(i, self.switchesPicture)

    @pyqtSlot()
    def reset(self):
        self.onStop()
        self.progressBar.setProgress(0, '')
        self.nextEnabled = False

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

class BLEPage(BasePage):
    begin = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.nextEnabled = False

        self.pixMap = QtGui.QPixmap(resource.path('images/ble.jpg'))

        title = QLabel("Now program the SmartDrive Bluetooth Firmware.")
        title.setWordWrap(True)

        bleInstructions = QLabel("The program will open when you press 'Begin'.\nPress the 'Info' button and ensure it DOES NOT turn RED.\nThen press the 'Update' button.\nWhen it has finished, press 'Next'")
        bleInstructions.setWordWrap(True)

        self.beginButton = QPushButton("Begin")
        self.beginButton.clicked.connect(self.onBegin)

        self.labels = [title, bleInstructions]

        self.picture = QLabel(self)
        self.picture.setPixmap(self.pixMap.scaledToHeight(self.getPictureSize().height()))

        self.layout.addWidget(title)
        self.layout.addWidget(bleInstructions)
        self.layout.addWidget(self.picture)
        self.layout.addWidget(self.beginButton)

    @pyqtSlot()
    def onBegin(self):
        self.begin.emit()
        self.nextEnabled = True
        super().finished.emit()

    def resizeEvent(self, event):
        i = self.layout.indexOf(self.picture)
        self.layout.removeWidget(self.picture)
        self.picture.setParent(None)
        self.picture = QLabel(self)
        self.picture.setPixmap(self.pixMap.scaledToHeight(self.getPictureSize().height()))
        self.layout.insertWidget(i, self.picture)

class EndPage(BasePage):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.nextEnabled = False

        self.pixMap = QtGui.QPixmap(resource.path('images/runMX2+.jpg'))

        title = QLabel("Set the MX2+ DIP switches for running the firmware as shown below. \nThen power-cycle the SmartDrive.")
        title.setWordWrap(True)

        self.labels = [title]

        self.picture = QLabel(self)
        self.picture.setPixmap(self.pixMap.scaledToHeight(self.getPictureSize().height()))

        self.layout.addWidget(title)
        self.layout.addWidget(self.picture)

    def resizeEvent(self, event):
        i = self.layout.indexOf(self.picture)
        self.layout.removeWidget(self.picture)
        self.picture.setParent(None)
        self.picture = QLabel(self)
        self.picture.setPixmap(self.pixMap.scaledToHeight(self.getPictureSize().height()))
        self.layout.insertWidget(i, self.picture)

    @pyqtSlot()
    def onEnter(self):
        super().finished.emit()

