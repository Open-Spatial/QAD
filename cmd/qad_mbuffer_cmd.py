# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin ok

 MBUFFER command to create objects generated from buffers on other objects

                              -------------------
        begin                : 2013-09-19
        copyright            : iiiii
        email                : hhhhh
        developers           : bbbbb aaaaa ggggg
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


# Import the PyQt and QGIS libraries
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui  import *
from qgis.core import *


from ..qad_getpoint import QadGetPointDrawModeEnum
from .qad_mbuffer_maptool import Qad_mbuffer_maptool, Qad_mbuffer_maptool_ModeEnum
from .qad_generic_cmd import QadCommandClass
from ..qad_msg import QadMsg
from ..qad_textwindow import *
from .qad_ssget_cmd import QadSSGetClass
from ..qad_entity import *
from .. import qad_utils
from .. import qad_layer
from ..qad_dim import QadDimStyles
from ..qad_mbuffer_fun import buffer
from ..qad_multi_geom import fromQadGeomToQgsGeom


# Class that manages the MBUFFER command
class QadMBUFFERCommandClass(QadCommandClass):

   def instantiateNewCmd(self):
      """instantiates a new command of the same type"""
      return QadMBUFFERCommandClass(self.plugIn)

   def getName(self):
      return QadMsg.translate("Command_list", "MBUFFER")

   def getEnglishName(self):
      return "MBUFFER"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runMBUFFERCommand)

   def getIcon(self):
      return QIcon(":/plugins/qad/icons/mbuffer.svg")

   def getNote(self):
      # set the explanatory notes of the command
      return QadMsg.translate("Command_MBUFFER", "Creates polygons by buffering selected objects.")

   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      # if this flag = True the command is used within another command to draw a buffer
      # which will not be saved on a layer
      self.virtualCmd = False
      self.rubberBandBorderColor = None
      self.rubberBandFillColor = None
      self.SSGetClass = QadSSGetClass(plugIn)
      self.entitySet = QadEntitySet()
      self.width = 0
      self.segments = self.plugIn.segments # the number of segments for curve approximation

   def __del__(self):
      QadCommandClass.__del__(self)
      del self.SSGetClass


   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      if self.step == 0: # when you are in the entity selection phase
         return self.SSGetClass.getPointMapTool()
      else:
         if (self.plugIn is not None):
            if self.PointMapTool is None:
               self.PointMapTool = Qad_mbuffer_maptool(self.plugIn)
               self.PointMapTool.setRubberBandColor(self.rubberBandBorderColor, self.rubberBandFillColor)
            return self.PointMapTool
         else:
            return None


   def getCurrentContextualMenu(self):
      if self.step == 0: # when you are in the entity selection phase
         return None # return self.SSGetClass.getCurrentContextualMenu()
      else:
         return self.contextualMenu


   def setRubberBandColor(self, rubberBandBorderColor, rubberBandFillColor):
      self.rubberBandBorderColor = rubberBandBorderColor
      self.rubberBandFillColor = rubberBandFillColor
      if self.PointMapTool is not None:
         self.PointMapTool.setRubberBandColor(self.rubberBandBorderColor, self.rubberBandFillColor)


   def AddGeoms(self, currLayer):
      bufferGeoms = []

      for layerEntitySet in self.entitySet.layerEntitySetList:
         entityIterator = QadLayerEntitySetIterator(layerEntitySet)
         for entity in entityIterator:
            bufferedQadGeom = buffer(entity.getQadGeom(), self.width)
            if bufferedQadGeom is not None:
               # I transform the geometry into the layer crs
               bufferGeoms.append(fromQadGeomToQgsGeom(bufferedQadGeom, currLayer))

      self.plugIn.beginEditCommand("Feature buffered", currLayer)

      # filter features by type
      pointGeoms, lineGeoms, polygonGeoms = qad_utils.filterGeomsByType(bufferGeoms, \
                                                                        currLayer.geometryType())
      # add the geometries of the correct type
      if currLayer.geometryType() == QgsWkbTypes.LineGeometry:
         polygonToLines = []
         # I reduce geometries into lines
         for g in polygonGeoms:
            lines = qad_utils.asPointOrPolyline(g)
            for l in lines:
               if l.type() == QgsWkbTypes.LineGeometry:
                   polygonToLines.append(l)
         # plugin, layer, geoms, coordTransform, refresh, check_validity
         if qad_layer.addGeomsToLayer(self.plugIn, currLayer, polygonToLines, None, False, False) == False:
            self.plugIn.destroyEditCommand()
            return

         del polygonGeoms[:] # I empty the list

      # plugin, layer, geoms, coordTransform, refresh, check_validity
      if qad_layer.addGeomsToLayer(self.plugIn, currLayer, bufferGeoms, None, False, False) == False:
         self.plugIn.destroyEditCommand()
         return

      if pointGeoms is not None and len(pointGeoms) > 0:
         PointTempLayer = qad_layer.createQADTempLayer(self.plugIn, QgsWkbTypes.PointGeometry)
         self.plugIn.addLayerToLastEditCommand("Feature buffered", PointTempLayer)

      if lineGeoms is not None and len(lineGeoms) > 0:
         LineTempLayer = qad_layer.createQADTempLayer(self.plugIn, QgsWkbTypes.LineGeometry)
         self.plugIn.addLayerToLastEditCommand("Feature buffered", LineTempLayer)

      if polygonGeoms is not None and len(polygonGeoms) > 0:
         PolygonTempLayer = qad_layer.createQADTempLayer(self.plugIn, QgsWkbTypes.PolygonGeometry)
         self.plugIn.addLayerToLastEditCommand("Feature buffered", PolygonTempLayer)

      # add the waste in the temporary layers of QAD
      # I transform the geometry into that of temporary layers
      # plugIn, pointGeoms, lineGeoms, polygonGeoms, coord, refresh
      if qad_layer.addGeometriesToQADTempLayers(self.plugIn, pointGeoms, lineGeoms, polygonGeoms, \
                                                currLayer.crs(), False) == False:
         self.plugIn.destroyEditCommand()
         return

      self.plugIn.endEditCommand()


   def run(self, msgMapTool = False, msg = None):
      if self.plugIn.canvas.mapSettings().destinationCrs().isGeographic():
         self.showMsg(QadMsg.translate("QAD", "\nThe coordinate reference system of the project must be a projected coordinate system.\n"))
         return True # end command

      currLayer = None
      if self.virtualCmd == False: # if you really want to save the polyline in a layer
         # the current layer must be editable and of type line or polygon
         currLayer, errMsg = qad_layer.getCurrLayerEditable(self.plugIn.canvas, [QgsWkbTypes.LineGeometry, QgsWkbTypes.PolygonGeometry])
         if currLayer is None:
            self.showErr(errMsg)
            return True # end command

         # the current layer must not belong to dimensions
         dimStyleList = QadDimStyles.getDimListByLayer(currLayer)
         if len(dimStyleList) > 0:
            dimStyleNames = ""
            for i in range(0, len(dimStyleList), 1):
               if i > 0:
                  dimStyleNames += ", "
               dimStyleNames += dimStyleList[i].name
            errMsg = QadMsg.translate("QAD", "\nCurrent layer is a layer referenced to {0} dimension style and it is not valid.\n")
            self.showErr(errMsg.format(dimStyleNames))
            return True # end command

      # =========================================================================
      # OBJECT SELECTION REQUEST
      if self.step == 0: # start of command
         if self.SSGetClass.run(msgMapTool, msg) == True:
            # selection completed
            self.step = 1
            self.getPointMapTool().refreshSnapType() # update the snapType which can be varied from the entity selection map tool
            return self.run(msgMapTool, msg)

      # =========================================================================
      # BUFFER OGGETTI
      elif self.step == 1:
         self.entitySet.set(self.SSGetClass.entitySet)

         if self.entitySet.count() == 0:
            return True # end command

         # set the map tool
         self.getPointMapTool().setMode(Qad_mbuffer_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_FIRST_PT)
         if currLayer is not None:
            self.getPointMapTool().geomType = QgsWkbTypes.LineGeometry if currLayer.geometryType() == QgsWkbTypes.LineGeometry else QgsWkbTypes.PolygonGeometry

         # is preparing to wait for a point or a real number
         # msg, inputType, default, keyWords, positive values
         msg = QadMsg.translate("Command_MBUFFER", "Specify the buffer length <{0}>: ")
         self.waitFor(msg.format(str(self.plugIn.lastRadius)), \
                      QadInputTypeEnum.POINT2D | QadInputTypeEnum.FLOAT, \
                      self.plugIn.lastRadius, "", \
                      QadInputModeEnum.NOT_NULL | QadInputModeEnum.NOT_ZERO | QadInputModeEnum.NOT_NEGATIVE)

         self.step = 2
         return False

      # =========================================================================
      # RESPONSE TO THE WIDTH REQUEST (from step = 1)
      elif self.step == 2: # after waiting for a point or a real number the command is restarted
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if while selecting a point
            # Another plugin was activated which deactivated Qad
            # so the command that returns here has been reactivated without the map tool
            # has selected a point
            if self.getPointMapTool().point is None: # the map tool was activated without a dot
               if self.getPointMapTool().rightButton == True: # if used with the right mouse button
                  return True # end command
               else:
                  self.setMapTool(self.getPointMapTool()) # I reactivate the map tool
                  return False

            value = self.getPointMapTool().point
         else: # the dot comes as a parameter of the function
            value = msg

         if type(value) == QgsPointXY:
            self.startPtForBufferWidth = value

            # set the map tool
            self.getPointMapTool().startPtForBufferWidth = self.startPtForBufferWidth
            self.getPointMapTool().entitySet.set(self.entitySet)
            self.getPointMapTool().segments = self.segments
            self.getPointMapTool().setMode(Qad_mbuffer_maptool_ModeEnum.FIRST_PT_ASK_FOR_BUFFER_WIDTH)

            # is preparing to wait for a point
            self.waitForPoint(QadMsg.translate("Command_MBUFFER", "Specify second point: "), None, QadInputModeEnum.NOT_NULL)
            self.step = 3
            return False
         else:
            self.width = value
            self.plugIn.setLastRadius(self.width)

            if self.virtualCmd == False: # if you really want to save buffers in a layer
               self.AddGeoms(currLayer)

            return True # end command

      # =========================================================================
      # RESPONSE TO THE SECOND POINT REQUEST OF THE BUFFER WIDTH (from step = 2)
      elif self.step == 3: # after waiting for a point the command restarts
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if while selecting a point
            # Another plugin was activated which deactivated Qad
            # so the command that returns here has been reactivated without the map tool
            # has selected a point
            if self.getPointMapTool().point is None: # the map tool was activated without a dot
               if self.getPointMapTool().rightButton == True: # if used with the right mouse button
                  return True # end command
               else:
                  self.setMapTool(self.getPointMapTool()) # I reactivate the map tool
                  return False

            value = self.getPointMapTool().point
         else: # the dot comes as a parameter of the function
            value = msg

         self.width = qad_utils.getDistance(self.startPtForBufferWidth, value)
         self.plugIn.setLastRadius(self.width)

         if self.virtualCmd == False: # if you really want to save buffers in a layer
            self.AddGeoms(currLayer)

         return True # end command