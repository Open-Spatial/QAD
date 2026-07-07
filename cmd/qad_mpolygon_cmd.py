# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin ok

 MPOLYGON command to draw a polygon

                              -------------------
        begin                : 2013-09-18
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
from qgis.core import QgsGeometry, QgsWkbTypes
from qgis.PyQt.QtGui import QIcon


from .qad_generic_cmd import QadCommandClass
from .qad_pline_cmd import QadPLINECommandClass
from ..qad_msg import QadMsg
from ..qad_getpoint import QadGetPointDrawModeEnum
from ..qad_multi_geom import *
from .. import qad_layer


# Class that manages the MPOLYGON command
class QadMPOLYGONCommandClass(QadCommandClass):

   def instantiateNewCmd(self):
      """instantiates a new command of the same type"""
      return QadMPOLYGONCommandClass(self.plugIn)

   def getName(self):
      return QadMsg.translate("Command_list", "MPOLYGON")

   def getEnglishName(self):
      return "MPOLYGON"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runMPOLYGONCommand)

   def getIcon(self):
      return QIcon(":/plugins/qad/icons/mpolygon.svg")

   def getNote(self):
      # set the explanatory notes of the command
      return QadMsg.translate("Command_MPOLYGON", "Draws a polygon by many methods.\nA Polygon is a closed sequence of straight line segments,\narcs or a combination of two.")

   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      # if this flag = True the command is used within another command to draw a polygon
      # which will not be saved on a layer
      self.virtualCmd = False
      self.rubberBandBorderColor = None
      self.rubberBandFillColor = None
      self.PLINECommand = None

   def __del__(self):
      QadCommandClass.__del__(self)
      if self.PLINECommand is not None:
         del self.PLINECommand


   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      if self.PLINECommand is not None:
         return self.PLINECommand.getPointMapTool(drawMode)
      else:
         return QadCommandClass.getPointMapTool(self, drawMode)


   def getCurrentContextualMenu(self):
      if self.PLINECommand is not None:
         return self.PLINECommand.getCurrentContextualMenu()
      else:
         return self.contextualMenu


   def setRubberBandColor(self, rubberBandBorderColor, rubberBandFillColor):
      self.rubberBandBorderColor = rubberBandBorderColor
      self.rubberBandFillColor = rubberBandFillColor
      if self.PLINECommand is not None:
         self.PLINECommand.setRubberBandColor(rubberBandBorderColor, rubberBandFillColor)


   def run(self, msgMapTool = False, msg = None):
      if self.plugIn.canvas.mapSettings().destinationCrs().isGeographic():
         self.showMsg(QadMsg.translate("QAD", "\nThe coordinate reference system of the project must be a projected coordinate system.\n"))
         return True # end command

      if self.virtualCmd == False: # if you really want to save the polyline in a layer
         currLayer, errMsg = qad_layer.getCurrLayerEditable(self.plugIn.canvas, QgsWkbTypes.PolygonGeometry)
         if currLayer is None:
            self.showErr(errMsg)
            return True # end command

      # =========================================================================
      # FIRST POINT REQUEST FOR OBJECT SELECTION
      if self.step == 0:
         self.PLINECommand = QadPLINECommandClass(self.plugIn, True)
         self.PLINECommand.setRubberBandColor(self.rubberBandBorderColor, self.rubberBandFillColor)
         self.PLINECommand.setCapturePrompts(getattr(self, "capturePromptOverrides", {}))
         self.PLINECommand.setCaptureFinishOnPointCount(getattr(self, "captureFinishOnPointCount", None))
         self.PLINECommand.setCaptureSelectionSteps(getattr(self, "captureSelectionSteps", []))
         # if this flag = True the command is used within another command to draw a line
         # which will not be saved on a layer
         self.PLINECommand.virtualCmd = True
         self.PLINECommand.asToolForMPolygon = True # for polygon type rubberband
         self.PLINECommand.run(msgMapTool, msg)
         self.step = 1
         return False # continua

      # =========================================================================
      # RESPONSE TO THE POINT REQUEST (from step = 0 or 1)
      elif self.step == 1: # after waiting for a point the command restarts
         if self.PLINECommand.run(msgMapTool, msg) == True:
            if self.PLINECommand.polyline.qty() >= 2: # if there are at least 2 sections
               polyline = self.PLINECommand.polyline.copy() # I copy the polyline
               # if the polyline is not closed
               if polyline.isClosed() == False:
                  polyline.append(QadLine().set(polyline.getEndPt(), polyline.getStartPt())) # I close it with a straight segment
               if self.virtualCmd == False: # if you really want to save the polyline in a layer
                  geom = polyline.asGeom(currLayer.wkbType())
                  if geom is not None:
                     if qad_layer.addGeomToLayer(self.plugIn, currLayer, self.mapToLayerCoordinates(currLayer, geom), None, True, True, True) == False:
                        self.showMsg(QadMsg.translate("Command_MPOLYGON", "\nPolygon not valid.\n"))
                        del polyline
            else:
               self.showMsg(QadMsg.translate("Command_MPOLYGON", "\nPolygon not valid.\n"))

            return True # end

         return False

   def capturedGeometries(self, target_wkb_type = None):
      """Return the captured MPOLYGON geometry in map coordinates."""
      if self.PLINECommand is None or self.PLINECommand.polyline.qty() < 2:
         return []

      polyline = self.PLINECommand.polyline.copy()
      try:
         if polyline.isClosed() == False:
            polyline.append(QadLine().set(polyline.getEndPt(), polyline.getStartPt()))
         wkb_type = target_wkb_type if target_wkb_type is not None else QgsWkbTypes.Polygon
         geom = polyline.asGeom(wkb_type)
         return [QgsGeometry(geom)] if geom is not None else []
      finally:
         del polyline

   def capturedSelections(self):
      if self.PLINECommand is None:
         return []
      return self.PLINECommand.capturedSelections()
