from PyQt5 import QtGui
from PyQt5.QtWidgets import (QWidget, QProgressBar, QLabel, QVBoxLayout)
from PyQt5.QtCore import pyqtSignal, pyqtSlot

class ProgressBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        lay = QVBoxLayout(self)

        self.bar = QProgressBar()
        self.bar.setGeometry(0,0, 100, 10)

        self.label = QLabel()
        self.label.setWordWrap(True)

        lay.addWidget(self.bar)
        lay.addWidget(self.label)

    @pyqtSlot(int, str)
    def setProgress(self, percent, text):
        self.bar.setValue(percent)
        self.label.setText(text)
