# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin OK

 POLYGON command to draw a regular polygon

                              -------------------
        begin                : 2014-11-17
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
from ..qad_polyline import QadPolyline
from .qad_polygon_maptool import Qad_polygon_maptool_ModeEnum, Qad_polygon_maptool
from .qad_generic_cmd import QadCommandClass
from ..qad_msg import QadMsg
from ..qad_textwindow import QadInputTypeEnum, QadInputModeEnum
from .. import qad_utils
from .. import qad_layer


# Class that manages the POLYGON command
class QadPOLYGONCommandClass(QadCommandClass):

   def instantiateNewCmd(self):
      """instantiates a new command of the same type"""
      return QadPOLYGONCommandClass(self.plugIn)

   def getName(self):
      return QadMsg.translate("Command_list", "POLYGON")

   def getEnglishName(self):
      return "POLYGON"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runPOLYGONCommand)

   def getIcon(self):
      return QIcon(":/plugins/qad/icons/polygon.svg")

   def getNote(self):
      # set the explanatory notes of the command
      return QadMsg.translate("Command_POLYGON", "Draws a regular polygon.")

   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      # if this flag = True the command is used within another command to draw a rectangle
      # which will not be saved on a layer
      self.virtualCmd = False
      self.centerPt = None
      self.firstEdgePt = None
      self.polyline = QadPolyline()
      self.sideNumber = self.plugIn.lastPolygonSideNumber
      self.constructionModeByCenter = self.plugIn.lastPolygonConstructionModeByCenter
      self.area = 100

   def __del__(self):
      QadCommandClass.__del__(self)

   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      if (self.plugIn is not None):
         if self.PointMapTool is None:
            self.PointMapTool = Qad_polygon_maptool(self.plugIn)
         return self.PointMapTool
      else:
         return None


   def addPolygonToLayer(self, layer):
      geom = self.polyline.asGeom(layer.wkbType())
      if geom is not None:
         qad_layer.addGeomToLayer(self.plugIn, layer, self.mapToLayerCoordinates(layer, geom))


   # ============================================================================
   # WaitForSideNumber
   # ============================================================================
   def WaitForSideNumber(self):
      self.step = 1
      prompt = QadMsg.translate("Command_POLYGON", "Enter number of sides <{0}>: ")
      self.waitForInt(prompt.format(str(self.sideNumber)), self.sideNumber, \
                      QadInputModeEnum.NOT_ZERO | QadInputModeEnum.NOT_NEGATIVE)

   # ============================================================================
   # WaitForCenter
   # ============================================================================
   def WaitForCenter(self):
      self.step = 2
      self.getPointMapTool().setMode(Qad_polygon_maptool_ModeEnum.ASK_FOR_CENTER_PT)

      keyWords = QadMsg.translate("Command_POLYGON", "Edge")
      prompt = QadMsg.translate("Command_POLYGON", "Specify center of polygon or [{0}]: ").format(keyWords)

      englishKeyWords = "Edge"
      keyWords += "_" + englishKeyWords
      # is preparing to wait for a point or Enter
      #                        msg, inputType,              default, keyWords, no check
      self.waitFor(prompt, \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                   None, keyWords, QadInputModeEnum.NONE)

   # ============================================================================
   # WaitForInscribedCircumscribedOption
   # ============================================================================
   def WaitForInscribedCircumscribedOption(self):
      self.step = 3
      keyWords = QadMsg.translate("Command_POLYGON", "Inscribed in circle") + "/" + \
                 QadMsg.translate("Command_POLYGON", "Circumscribed about circle") + "/" + \
                 QadMsg.translate("Command_POLYGON", "Area")
      prompt = QadMsg.translate("Command_POLYGON", "Enter an option [{0}] <{1}>: ").format(keyWords, \
                                                                                           self.constructionModeByCenter)

      englishKeyWords = "Inscribed in circle" + "/" + "Circumscribed about circle" + "/" + "Area"
      keyWords += "_" + englishKeyWords
      # is preparing to wait for a keyword
      # msg, inputType, default, keyWords, positive values
      self.waitFor(prompt, QadInputTypeEnum.KEYWORDS, \
                   self.constructionModeByCenter, \
                   keyWords, QadInputModeEnum.NONE)

   # ============================================================================
   # WaitForRadius
   # ============================================================================
   def WaitForRadius(self, layer):
      self.step = 4
      if layer is not None:
         self.getPointMapTool().geomType = layer.geometryType()
      self.getPointMapTool().setMode(Qad_polygon_maptool_ModeEnum.CENTER_PT_KNOWN_ASK_FOR_RADIUS)

      # is preparing to wait for a point or a real number
      # msg, inputType, default, keyWords, positive values
      prompt = QadMsg.translate("Command_CIRCLE", "Specify the circle radius <{0}>: ")
      self.waitFor(prompt.format(str(self.plugIn.lastRadius)), \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.FLOAT, \
                   self.plugIn.lastRadius, "", \
                   QadInputModeEnum.NOT_ZERO | QadInputModeEnum.NOT_NEGATIVE)

   # ============================================================================
   # WaitForFirstEdgePt
   # ============================================================================
   def WaitForFirstEdgePt(self):
      self.step = 5
      # set the map tool
      self.getPointMapTool().setMode(Qad_polygon_maptool_ModeEnum.ASK_FOR_FIRST_EDGE_PT)
      # is preparing to wait for a point
      self.waitForPoint(QadMsg.translate("Command_POLYGON", "Specify the first point of the edge: "))

   # ============================================================================
   # WaitForSecondEdgePt
   # ============================================================================
   def WaitForSecondEdgePt(self, layer):
      self.step = 6
      self.getPointMapTool().firstEdgePt = self.firstEdgePt

      if layer is not None:
         self.getPointMapTool().geomType = layer.geometryType()

      # set the map tool
      self.getPointMapTool().setMode(Qad_polygon_maptool_ModeEnum.FIRST_EDGE_PT_KNOWN_ASK_FOR_SECOND_EDGE_PT)
      # is preparing to wait for a point
      self.waitForPoint(QadMsg.translate("Command_POLYGON", "Specify the second point of the edge: "))

   # ============================================================================
   # WaitForArea
   # ============================================================================
   def WaitForArea(self):
      self.step = 7

      msg = QadMsg.translate("Command_POLYGON", "Enter the polygon area in current units <{0}>: ")
      # is preparing to wait for a real number
      # msg, inputType, default, keyWords, positive values
      self.waitFor(msg.format(str(self.area)), QadInputTypeEnum.FLOAT, \
                   self.area, "", \
                   QadInputModeEnum.NOT_ZERO | QadInputModeEnum.NOT_NEGATIVE)


   # ============================================================================
   # run
   # ============================================================================
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

      # =========================================================================
      # NUMBER OF SIDES OF THE POLYGON REQUESTED
      if self.step == 0: # start of command
         self.WaitForSideNumber()
         return False

      # =========================================================================
      # RESPONSE TO THE REQUEST FOR THE NUMBER OF SIDES OF THE POLYGON (from step = 0)
      elif self.step == 1: # after waiting for a point the command restarts
         if msgMapTool == True: # the point comes from a graphic selection
            if self.getPointMapTool().rightButton == True: # if used with the right mouse button
               value = self.sideNumber
            else:
               return False
         else: # the dot comes as a parameter of the function
            value = msg

         if type(value) == int:
            if value < 3:
               self.showErr(QadMsg.translate("Command_POLYGON", "\nEnter an integer greater than 2."))
            else:
               self.sideNumber = value
               self.getPointMapTool().sideNumber = self.sideNumber
               self.plugIn.setLastPolygonSideNumber(self.sideNumber)
               self.WaitForCenter()
         else:
            self.WaitForSideNumber()

         return False # continua


      # =========================================================================
      # RESPONSE TO THE POLYGON CENTER REQUEST (from step = 1)
      elif self.step == 2: # after waiting for a point the command restarts
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if while selecting a point
            # Another plugin was activated which deactivated Qad
            # so the command that returns here has been reactivated without the map tool
            # has selected a point
            if self.getPointMapTool().point is None: # the map tool was activated without a dot
               if self.getPointMapTool().rightButton == True: # if used with the right mouse button
                  self.WaitForCenter()
                  return False
               else:
                  self.setMapTool(self.getPointMapTool()) # I reactivate the map tool
                  return False

            value = self.getPointMapTool().point
         else: # the dot comes as a parameter of the function
            value = msg

         if type(value) == unicode:
            if value == QadMsg.translate("Command_POLYGON", "Edge") or value == "Edge":
               self.WaitForFirstEdgePt()
         elif type(value) == QgsPointXY:
            self.centerPt = value
            self.getPointMapTool().centerPt = self.centerPt
            self.WaitForInscribedCircumscribedOption()

         return False # continua

      # =========================================================================
      # RESPONSE TO THE REQUEST FOR INSCRIBED OR RESTRICTED POLYGON (from step = 2)
      elif self.step == 3:
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if while selecting a point
            # Another plugin was activated which deactivated Qad
            # so the command that returns here has been reactivated without the map tool
            # has selected a point
            if self.getPointMapTool().point is None: # the map tool was activated without a dot
               if self.getPointMapTool().rightButton == True: # if used with the right mouse button
                  value = self.constructionModeByCenter
               else:
                  self.setMapTool(self.getPointMapTool()) # I reactivate the map tool
                  return False
            else:
               value = self.getPointMapTool().point
         else: # the keyword comes as a function parameter
            value = msg

         if type(value) == unicode:
            self.constructionModeByCenter = value
            self.plugIn.setLastPolygonConstructionModeByCenter(self.constructionModeByCenter)
            self.getPointMapTool().constructionModeByCenter = self.constructionModeByCenter
            if self.constructionModeByCenter == QadMsg.translate("Command_POLYGON", "Area") or self.constructionModeByCenter == "Area":
               self.WaitForArea()
            else:
               self.WaitForRadius(currLayer)

         return False # end command

      # =========================================================================
      # RESPONSE TO BEAM REQUEST (from step = 3)
      elif self.step == 4:
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

         if type(value) == QgsPointXY or type(value) == float: # if the radius of the circle has been entered
            if type(value) == QgsPointXY: # if the radius of the circle with a point has been entered
               self.radius = qad_utils.getDistance(self.centerPt, value)
               ptStart = value
            else:
               self.radius = value
               ptStart = None

            self.plugIn.setLastRadius(self.radius)

            if self.constructionModeByCenter == QadMsg.translate("Command_POLYGON", "Inscribed in circle") or \
               self.constructionModeByCenter == "Inscribed in circle":
               mode = True
            else:
               mode = False

            self.polyline.getPolygonByNsidesCenterRadius(self.sideNumber, self.centerPt, self.radius, mode, ptStart)

            if self.virtualCmd == False: # if you really want to save buffers in a layer
               self.addPolygonToLayer(currLayer)
            return True

         return False # end command


      # =========================================================================
      # RESPONSE TO THE REQUEST FOR THE FIRST POINT OF THE EDGE (from step = 2)
      elif self.step == 5: # after waiting for a point the command restarts
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
            self.firstEdgePt = value
            self.WaitForSecondEdgePt(currLayer)

         return False

      # =========================================================================
      # RESPONSE TO THE REQUEST FOR THE SECOND POINT OF THE EDGE (from step = 5)
      elif self.step == 6: # after waiting for a point or a real number the command is restarted
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
            self.polyline.getPolygonByNsidesEdgePts(self.sideNumber, self.firstEdgePt, value)

            if self.virtualCmd == False: # if you really want to save buffers in a layer
               self.addPolygonToLayer(currLayer)
            return True

         return False


      # =========================================================================
      # RESPONSE TO THE RANGE AREA REQUEST (from step = 3)
      elif self.step == 7: # after waiting for a real number the command is restarted
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if while selecting a point
            # Another plugin was activated which deactivated Qad
            # so the command that returns here has been reactivated without the map tool
            # has selected a point
            if self.getPointMapTool().point is None: # the map tool was activated without a dot
               if self.getPointMapTool().rightButton == True: # if used with the right mouse button
                  value = self.area
               else:
                  self.setMapTool(self.getPointMapTool()) # I reactivate the map tool
                  return False
            else:
               return False
         else: # the dot comes as a parameter of the function
            value = msg

         if type(value) == float: # the area was entered
            self.polyline.getPolygonByNsidesArea(self.sideNumber, self.centerPt, value)

            if self.virtualCmd == False: # if you really want to save buffers in a layer
               self.addPolygonToLayer(currLayer)
            return True

         return False
