from pyCIOT.data import *
from future import standard_library
standard_library.install_aliases()
from builtins import str
import urllib.request, urllib.error, urllib.parse
from qgis.PyQt.QtCore import QObject, pyqtSignal, pyqtSlot, QRunnable
from PyQt5.QtCore import QVariant
from qgis.core import QgsFields,QgsField,QgsVectorFileWriter,QgsWkbTypes,QgsCoordinateReferenceSystem,QgsGeometry,QgsPointXY,QgsFeature
import time
import sys
import os

class Signals(QObject):
    processFinished = pyqtSignal(str)
    errorOccurred = pyqtSignal(str)
    processReported = pyqtSignal(int)
    userCanceled = pyqtSignal()
    noDataReported = pyqtSignal(str)

    def __init__(self, thread):
        super(Signals, self).__init__()

        self.thread = thread

    @pyqtSlot()
    def cancel(self):
        self.thread.stop()

class PyCIOTRequest(QRunnable):
    def __init__(self, air_source, water_source, weather_source, video_source, quake_source, folder, iface):
        super(PyCIOTRequest, self).__init__()
        self.signals = Signals(self)
        self.air_source = air_source
        self.water_source = water_source
        self.weather_source = weather_source
        self.video_source = video_source
        self.quake_source = quake_source
        self.folder = folder
        self.minLong = 0
        self.minLat = 0
        self.maxLong = 0
        self.maxLat = 0
        self.iface = iface
        self.stopped = False

    def stop(self):
        self.stopped = True

    def setParameters(self, minLong, minLat, maxLong, maxLat):
        self.minLong = float(minLong)
        self.minLat = float(minLat)
        self.maxLong = float(maxLong)
        self.maxLat = float(maxLat)


    def selectStation(self, stations):
        return [station for station in stations if self.minLat <= station["location"]["latitude"] <= self.maxLat and self.minLong <= station["location"]["longitude"] <= self.maxLong]


    def saveFile(self,datas, source:str, AirOrWaterData:bool):
        if(len(datas) == 0):
            self.signals.noDataReported.emit(source+" no data found")
            return
        layerFields = QgsFields()
        layerFields.append(QgsField('Name', QVariant.String))
        for value in datas[0]['data']:
            if AirOrWaterData:
                layerFields.append(QgsField(value['name'], QVariant.Double))
            else:
                layerFields.append(QgsField(value['name'], QVariant.String))
        source = source.replace(":","_")
        savefile = os.path.join(self.folder,source+".shp")

        writer = QgsVectorFileWriter(savefile, 
                                        'UTF-8', 
                                        layerFields,
                                        QgsWkbTypes.MultiPoint,
                                        QgsCoordinateReferenceSystem("EPSG:4326"),
                                        'ESRI Shapefile')
        
        for data in datas:
            feat = QgsFeature()
            feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(data["location"]["longitude"],data["location"]["latitude"])))
            attributes = [data['name']]
            for value in data['data']:
                attributes.append(str(value['values'][0]['value']))
            feat.setAttributes(attributes)
            writer.addFeature(feat)
        
        del(writer)
            





    def run(self):
        if self.folder == "" or self.folder == None: self.signals.errorOccurred.emit("No save Folders.")
        elif type(self.minLong) != float or type(self.minLat) != float or type(self.maxLat) != float or type(self.maxLong) != float:
            self.signals.errorOccurred.emit("Select boundary error.")
        else:
            processCounter = 0
            for source in self.air_source:
                data = Air().get_data(src=source)
                print(data)
                data = self.selectStation(data)
                print(data)
                self.saveFile(data,source,True)
                processCounter += 1
                self.signals.processReported.emit(processCounter)

            for source in self.water_source:
                data = Water().get_data(src=source)
                data = self.selectStation(data)
                self.saveFile(data,source,True)
                processCounter += 1
                self.signals.processReported.emit(processCounter)

            for source in self.weather_source:
                data = Weather().get_data(src=source)
                data = self.selectStation(data)
                self.saveFile(data,source,False)
                processCounter += 1
                self.signals.processReported.emit(processCounter)

            for source in self.video_source:
                data = CCTV().get_data(src=source)
                data = self.selectStation(data,False)
                self.saveFile(data,source)
                processCounter += 1
                self.signals.processReported.emit(processCounter)

            for source in self.quake_source:
                data = Quake().get_data(src=source)
                data = self.selectStation(data,False)
                self.saveFile(data,source)
                processCounter += 1
                self.signals.processReported.emit(processCounter)

            self.signals.processFinished.emit('Success, the file has been downloaded!')