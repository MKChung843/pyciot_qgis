# -*- coding: utf-8 -*-
"""
/***************************************************************************
 PyCIOTDialog
                                 A QGIS plugin
 This is a plugin which can get the data from CIOT
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                             -------------------
        begin                : 2023-08-23
        git sha              : $Format:%H$
        copyright            : (C) 2023 by Yu-Shen Cheng (Timmy)
        email                : timmyabc10@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import os

from qgis.PyQt import uic
from qgis.PyQt import QtWidgets
from qgis.PyQt.QtWidgets import QDialog, QFileDialog, QMessageBox, QProgressBar
from qgis.PyQt.QtCore import pyqtSlot, QThreadPool, Qt
from qgis.core import Qgis
from PyQt5.QtWidgets import QApplication,QPushButton,QLabel,QComboBox,QFileDialog
from .pyciot_downloader import PyCIOTRequest


# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'pyciot_qgis_dialog_base.ui'))


class PyCIOTDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, iface, startX, startY, endX, endY, parent=None):
        """Constructor."""
        super(PyCIOTDialog, self).__init__(parent)
        # Set up the user interface from Designer through FORM_CLASS.
        # After self.setupUi() you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)

        self.iface = iface

        self.setCoordinates(startX, startY, endX, endY)
        self.textEdit.setReadOnly(True)

        self.threadpool = QThreadPool()

        self.process = 0
        self.totalProcess = 0
        self.plugin_dir = os.path.dirname(__file__)

    def setCoordinates(self, startX, startY, endX, endY):
        if startX < endX:
            minLong = startX
            maxLong = endX
        else:
            minLong = endX
            maxLong = startX

        if startY < endY:
            minLat = startY
            maxLat = endY
        else:
            minLat = endY
            maxLat = startY

        self.wEdit.setText(str(minLong))
        self.sEdit.setText(str(minLat))
        self.eEdit.setText(str(maxLong))
        self.nEdit.setText(str(maxLat))


    @pyqtSlot()
    def on_Browse_clicked(self):
        filename = QFileDialog.getExistingDirectory (self, "Select output folder ","")
        name = str(filename)
        self.SAVE_FOLDER.setText(name)

    @pyqtSlot()
    def on_button_box_accepted(self):
        self.air = self.getAirSource()
        self.water = self.getWaterSource()
        self.weather = self.getWeatherSource()
        self.video = self.getVideoSource()
        self.earthquake = self.getQuakeSource()
        self.totalProcess = len(self.air) + len(self.water) + len(self.weather) + len(self.video) + len(self.earthquake)

        # Initiating processing
        pyciotRequest = PyCIOTRequest(self.air,self.water,self.weather,self.video,self.earthquake,self.SAVE_FOLDER.text(),self.iface)
        pyciotRequest.setParameters(self.wEdit.text(), self.sEdit.text(), self.eEdit.text(), self.nEdit.text())
        # Connecting end signal
        pyciotRequest.signals.processFinished.connect(self.processFinished)
        pyciotRequest.signals.processReported.connect(self.processReported)
        pyciotRequest.signals.noDataReported.connect(self.noDataReported)
        pyciotRequest.signals.errorOccurred.connect(self.errorOccurred)
        pyciotRequest.signals.userCanceled.connect(self.userCanceled)
        # Setting the progress bar
        # << Updated by SIGMOÉ
        self.msgBar = self.iface.messageBar()
        self.progressMessageBar = self.msgBar.createMessage('Downloading data...')
        # >>
        self.progressBar = QProgressBar()
        self.progressBar.setAlignment(Qt.AlignLeft|Qt.AlignVCenter)
        self.progressMessageBar.layout().addWidget(self.progressBar)
        self.iface.messageBar().pushWidget(self.progressMessageBar, Qgis.Info)
        self.progressBar.setRange(0, 0)
        self.progressMessageBar.destroyed.connect(pyciotRequest.signals.cancel)
        # Starting process
        self.threadpool.start(pyciotRequest)

    @pyqtSlot(str)
    def errorOccurred(self, message):
        QMessageBox.warning(self, 'Fatal!', message)
        self.msgBar.clearWidgets()
        self.close()

    @pyqtSlot()
    def userCanceled(self):
        QMessageBox.warning(self, 'Info!', 'Process canceled by user!')
        self.close()

    @pyqtSlot(int)
    def processReported(self, process):
        self.progressBar.setRange(0, self.totalProcess)
        self.process = process
        self.progressBar.setValue(self.process)

    @pyqtSlot(str)
    def noDataReported(self, message):
        self.progressMessageBar.setText(message)

    @pyqtSlot(str)
    def processFinished(self, message):
        self.progressBar.setRange(0, self.totalProcess)
        self.progressBar.setValue(self.totalProcess)
        self.progressMessageBar.setText('Downloaded Finish !!!')

        #if self.checkBox.isChecked():
        #    # << Updated by SIGMOÉ
        #    # Add each OSM layer with specific style
        #    lyr_types = [
        #                ['multipolygons', 'polygon'],
        #                ['multilinestrings', 'line'], 
        #                ['lines', 'line'],
        #                ['points', 'point']
        #               ]
        #    for lt in lyr_types:
        #        lyr = self.iface.addVectorLayer(self.filenameEdit.text()+'|layername='+lt[0], 'osm', 'ogr')
        #        style = "styles/osm_mapnik_" + lt[1] + ".qml"
        #        qml_file = os.path.join(self.plugin_dir, style)
        #        lyr.loadNamedStyle(qml_file)
        #    # >>
        for i in self.air:
            filename = i.replace(":","_")
            if not os.path.isfile(os.path.join(self.SAVE_FOLDER.text(),filename+".shp")): continue
            self.iface.addVectorLayer(os.path.join(self.SAVE_FOLDER.text(),filename+".shp"), i, "ogr")

        for i in self.water:
            filename = i.replace(":","_")
            if not os.path.isfile(os.path.join(self.SAVE_FOLDER.text(),filename+".shp")): continue
            self.iface.addVectorLayer(os.path.join(self.SAVE_FOLDER.text(),filename+".shp"), i, "ogr")

        QMessageBox.warning(self, 'Info!', message)
        # << Updated by SIGMOÉ
        self.msgBar.clearWidgets()
        # >>
        self.close()

    def getAirSource(self):
        source = []
        if self.OBS_EPA.isChecked(): source.append("OBS:EPA")
        if self.OBS_EPA_IOT.isChecked(): source.append("OBS:EPA_IoT")
        if self.OBS_AS_IOT.isChecked(): source.append("OBS:AS_IoT")
        if self.OBS_MOST_IOT.isChecked(): source.append("OBS:MOST_IoT")
        if self.OBS_NCNU_IOT.isChecked(): source.append("OBS:NCNU_IoT")
        return source
    
    def getWaterSource(self):
        source = []
        if self.WATER_LEVEL_WRA_RIVER.isChecked(): source.append("WATER_LEVEL:WRA_RIVER")
        if self.WATER_LEVEL_WRA_GROUNDWATER.isChecked(): source.append("WATER_LEVEL:WRA_GROUNDWATER")
        if self.WATER_LEVEL_WRA2_DRAINAGE.isChecked(): source.append("WATER_LEVEL:WRA2_DRAINAGE")
        if self.WATER_LEVEL_IA_POND.isChecked(): source.append("WATER_LEVEL:IA_POND")
        if self.WATER_LEVEL_IA_IRRIGATION.isChecked(): source.append("WATER_LEVEL:IA_IRRIGATION")
        if self.GATE_WRA.isChecked(): source.append("GATE:WRA")
        if self.GATE_WRA2.isChecked(): source.append("GATE:WRA2")
        if self.GATE_IA.isChecked(): source.append("GATE:IA")
        if self.PUMPING_WRA2.isChecked(): source.append("PUMPING:WRA2")
        if self.PUMPING_TPE.isChecked(): source.append("PUMPING:TPE")
        if self.FLOODING_WRA.isChecked(): source.append("FLOODING:WRA")
        if self.FLOODING_WRA2.isChecked(): source.append("FLOODING:WRA2")
        return source

    def getWeatherSource(self):
        source = []
        if self.GENERAL_CWB.isChecked(): source.append("GENERAL:CWB")
        if self.GENERAL_CWB_IOT.isChecked(): source.append("GENERAL:CWB_IoT")
        if self.RAINFALL_CWB.isChecked(): source.append("RAINFALL:CWB")
        if self.RAINFALL_WRA.isChecked(): source.append("RAINFALL:WRA")
        if self.RAINFALL_WRA2.isChecked(): source.append("RAINFALL:WRA2")
        if self.RAINFALL_IA.isChecked(): source.append("RAINFALL:IA")
        if self.IMAGE_CWB.isChecked(): source.append("IMAGE:CWB")
        return source

    def getVideoSource(self):
        source = []
        if self.IMAGE_EPA.isChecked(): source.append("IMAGE:EPA")
        if self.IMAGE_WRA.isChecked(): source.append("IMAGE:WRA")
        if self.IMAGE_COA.isChecked(): source.append("IMAGE:COA")
        return source
    
    def getQuakeSource(self):
        source = []
        if self.EARTHQUAKE.isChecked(): source.append("EARTHQUAKE:CWB+NCREE")
        return source
        
