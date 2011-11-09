# -*- coding: utf-8 -*-

import logging, serial, os
if os.name == "posix":
    import glob
from PyQt4.QtGui import QDialog, QPushButton, QComboBox, QLabel, QStackedWidget, QHBoxLayout, QVBoxLayout, QWidget, QMessageBox
from PyQt4.QtCore import QTimer, pyqtSlot, QProcess

from pyfirmata import Board
from pyfirmata.boards import BOARDS

logger = logging.getLogger(__name__)

class SelectPortDlg(QDialog):

    def __init__(self, parent=None):
        logging.debug("Port selection dialog created")
        super(SelectPortDlg, self).__init__(parent)
        statusLbl = QLabel("Programando el Arduino...")
        self.connectBtn = QPushButton("&Conectar")
        self.programBtn = QPushButton("&Programar")
        exitBtn = QPushButton("Salir")
        multiLbl = QLabel("&Selecciona la placa:")
        self.portsCmb = QComboBox()
        multiLbl.setBuddy(self.portsCmb)
        
        self.stackedWidget = QStackedWidget()
        mainWidget = QWidget()
        mainLayout = QHBoxLayout()
        mainLayout.addWidget(multiLbl)
        mainLayout.addWidget(self.portsCmb)
        mainWidget.setLayout(mainLayout)
        self.stackedWidget.addWidget(mainWidget)
        progWidget = QWidget()
        progLayout = QHBoxLayout()
        progLayout.addWidget(statusLbl)
        progLayout.addStretch()
        progWidget.setLayout(progLayout)
        self.stackedWidget.addWidget(progWidget)
        
        buttonLayout = QHBoxLayout()
        buttonLayout.addWidget(self.connectBtn)
        buttonLayout.addWidget(self.programBtn)
        buttonLayout.addStretch()
        buttonLayout.addWidget(exitBtn)
        
        layout = QVBoxLayout()
        layout.addWidget(self.stackedWidget)
        layout.addLayout(buttonLayout)
        self.setLayout(layout)
        
        self.linux = True if os.name == "posix" else False
        self.boards = list()
        self.board = None
        self.programBtn.clicked.connect(self.programBoard)
        self.portsCmb.currentIndexChanged[int].connect(self.updatePorts)
        self.connectBtn.clicked.connect(self.connectBoard)
        exitBtn.clicked.connect(self.reject)
        self.setWindowTitle(u"Iniciando comunicación")
        self.updatePorts(True)

    @pyqtSlot()
    def updatePorts(self, force=False):
        # FIXME: Program button gets focus when opening QComboBox
        if self.portsCmb.currentText() != "Actualizar" and not force:
            return
        logger.debug("Searching available serial ports")
        self.connectBtn.setEnabled(False)
        self.programBtn.setEnabled(False)
        ports = list()
        if self.linux:
            ports += glob.glob("/dev/ttyACM*") + glob.glob("/dev/ttyUSB*")
        for i in xrange(256):
            try:
                s = serial.Serial(i)
                ports.append(s.portstr)
                s.close()
            except serial.SerialException:
                pass
        logger.debug("Found %d serial port(s): %s", len(ports), ports)
        if not len(ports):
            ports = [""]
        self.portsCmb.clear()
        self.portsCmb.addItems(ports)
        self.portsCmb.addItem("Actualizar")
        if self.portsCmb.currentText() != "":
            self.connectBtn.setEnabled(True)
            self.programBtn.setEnabled(True)
            self.connectBtn.setFocus()

    @pyqtSlot()
    def connectBoard(self):
        try:
            logging.debug("Connecting to Arduino board on port "+self.portsCmb.currentText())
            board = Board(self.portsCmb.currentText(), BOARDS['arduino'])
        except ValueError, e:
            logger.warning(e)
            QMessageBox.warning(self, u"!Atención¡", unicode(e))
            self.updatePorts(True)
        except TypeError, e:
            logger.debug(e)
            QMessageBox.warning(self, u"!Atención¡", unicode(e))
            self.updatePorts(True)
        else:
            logging.debug("Using Arduino board on port "+board.sp.portstr)
            self.board = board
            self.accept()

    @pyqtSlot()
    def programBoard(self):
        self.connectBtn.setEnabled(False)
        self.programBtn.setEnabled(False)
        self.stackedWidget.setCurrentIndex(1)
        logging.debug("Programming Arduino board on "+self.portsCmb.currentText())
        if self.linux:
            # We suppose avrdude 5.10 or newer is already installed
            config = "/etc/avrdude.conf"
            executable = "/usr/bin/avrdude"
        else:
            executable = "avrdude"
            config = "avrdude.conf"
        os.chdir("./avrdude") # TODO: do this correctly
        self.program = QProcess()
        # avrdude reference: http://www.ladyada.net/learn/avr/avrdude.html
        self.program.start(executable+" -q -V -C "+config+" -p atmega328p -c arduino -P "+self.portsCmb.currentText()+" -b 115200 -D -U flash:w:StandardFirmata.hex:i")
        self.program.finished.connect(self.programFinished)

    @pyqtSlot()
    def programFinished(self):
        output = unicode(self.program.readAllStandardError())
        if output.find("flash written") == -1: # avrdude: xxxx bytes of flash written
            if output.find("Expected signature") != -1: # avrdude: Expected signature for ATMEGA328P is 1E 95 0F
                error = u"La placa conectada no tiene un chip compatible."
            elif output.find("resp=0x00") != -1: # avrdude: stk500_getsync(): not in sync: resp=0x00
                error = u"No parece que haya ninguna placa conectada al puerto."
            elif output.find("ser_send()") != -1: # ser_send(): write error: sorry no info avail
                error = u"Se produjo un error durante la comunicación con la placa.\nAsegúrate de que está correctamente conectada."
            elif output.find("ser_open()") != -1: # ser_send(): write error: sorry no info avail
                error = u"El puerto no existe. Asegúrate de que está correctamente conectada."
            else:
                error = u"Se produjo un error al programar la placa.\nComprueba el conexionado."
            QMessageBox.warning(self, u"¡Atención!", error)
            logging.warning("An error ocurred: "+error)
        else:
            logging.debug("Programmed successfully")
        os.chdir("..")
        self.updatePorts(True)
        self.connectBtn.setEnabled(True)
        self.programBtn.setEnabled(True)
        self.connectBtn.setFocus()
        self.stackedWidget.setCurrentIndex(0)

    def getBoard(self):
        return self.board