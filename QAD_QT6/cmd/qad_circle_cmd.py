# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 CIRCLE command to draw a circle

                              -------------------
        begin                : 2013-05-22
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
from qgis.core import QgsWkbTypes, QgsPointXY, QgsGeometry
from qgis.PyQt.QtGui import QIcon


from .. import qad_layer
from .. import qad_utils
from .qad_circle_maptool import Qad_circle_maptool, Qad_circle_maptool_ModeEnum
from .qad_generic_cmd import QadCommandClass
from ..qad_msg import QadMsg
from ..qad_textwindow import QadInputModeEnum, QadInputTypeEnum
from ..qad_geom_relations import *
from ..qad_multi_geom import *
from ..qad_circle_fun import *
from ..qad_getpoint import QadGetPointDrawModeEnum
from ..qad_snapper import QadSnapTypeEnum


# Class that manages the CIRCLE command
class QadCIRCLECommandClass(QadCommandClass):

   def instantiateNewCmd(self):
      """instantiates a new command of the same type"""
      return QadCIRCLECommandClass(self.plugIn)

   def getName(self):
      return QadMsg.translate("Command_list", "CIRCLE")

   def getEnglishName(self):
      return "CIRCLE"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runCIRCLECommand)

   def getIcon(self):
      return QIcon(":/plugins/qad/icons/circle.svg")

   def getNote(self):
      # set the explanatory notes of the command
      return QadMsg.translate("Command_CIRCLE", "Draws a circle by many methods.")

   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      # if this flag = True the command is used within another command to draw a circle
      # which will not be saved on a layer
      self.virtualCmd = False
      self.rubberBandBorderColor = None
      self.rubberBandFillColor = None
      self.centerPt = None
      self.radius = None
      self.area = 100

   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      if (self.plugIn is not None):
         if self.PointMapTool is None:
            self.PointMapTool = Qad_circle_maptool(self.plugIn)
            self.PointMapTool.setRubberBandColor(self.rubberBandBorderColor, self.rubberBandFillColor)
         return self.PointMapTool
      else:
         return None

   def setRubberBandColor(self, rubberBandBorderColor, rubberBandFillColor):
      self.rubberBandBorderColor = rubberBandBorderColor
      self.rubberBandFillColor = rubberBandFillColor
      if self.PointMapTool is not None:
         self.PointMapTool.setRubberBandColor(self.rubberBandBorderColor, self.rubberBandFillColor)

   def run(self, msgMapTool = False, msg = None):
      self.isValidPreviousInput = True # to manage the command also in macros

      if self.plugIn.canvas.mapSettings().destinationCrs().isGeographic():
         self.showMsg(QadMsg.translate("QAD", "\nThe coordinate reference system of the project must be a projected coordinate system.\n"))
         return True # end command

      currLayer = None
      if self.virtualCmd == False: # if you really want to save the circle in a layer
         # the current layer must be editable and of type line or polygon
         currLayer, errMsg = qad_layer.getCurrLayerEditable(self.plugIn.canvas, [QgsWkbTypes.LineGeometry, QgsWkbTypes.PolygonGeometry])
         if currLayer is None:
            self.showErr(errMsg)
            return True # end command
         self.getPointMapTool().layer = currLayer

      # =========================================================================
      # FIRST POINT or CENTER REQUEST
      if self.step == 0: # start of command
         # set the map tool
         self.getPointMapTool().setMode(Qad_circle_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_CENTER_PT)
         keyWords = QadMsg.translate("Command_CIRCLE", "3Points") + "/" + \
                    QadMsg.translate("Command_CIRCLE", "2POints") + "/" + \
                    QadMsg.translate("Command_CIRCLE", "Ttr (tangent tangent radius)")
         prompt = QadMsg.translate("Command_CIRCLE", "Specify the center point of the circle or [{0}]: ").format(keyWords)

         englishKeyWords = "3Points" + "/" + "2POints" + "/" + "Ttr (tangent tangent radius)"
         keyWords += "_" + englishKeyWords
         # is preparing to wait for a point or Enter or a keyword
         # msg, inputType, default, keyWords, no check
         self.waitFor(prompt, \
                      QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                      None, \
                      keyWords, QadInputModeEnum.NONE)

         self.step = 1
         return False

      # =========================================================================
      # RESPONSE TO CENTER REQUEST
      elif self.step == 1: # after waiting for a point or Enter or a keyword the command is restarted
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if while selecting a point
            # Another plugin was activated which deactivated Qad
            # so the command that returns here was reactivated without the map tool
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

         if value is None:
            if self.plugIn.lastPoint is not None:
               value = self.plugIn.lastPoint
            else:
               return True # end command

         if type(value) == unicode:
            if value == QadMsg.translate("Command_CIRCLE", "3Points") or value == "3Points":
               # set the map tool
               self.getPointMapTool().setMode(Qad_circle_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_FIRST_PT)
               # is preparing to wait for a point
               self.waitForPoint(QadMsg.translate("Command_CIRCLE", "Specify first point on the circle: "))
               self.step = 4
            elif value == QadMsg.translate("Command_CIRCLE", "2POints") or value == "2POints":
               # set the map tool
               self.getPointMapTool().setMode(Qad_circle_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_FIRST_DIAM_PT)
               # is preparing to wait for a point
               self.waitForPoint(QadMsg.translate("Command_CIRCLE", "Specify first end of the circle diameter: "))
               self.step = 7
            elif value == QadMsg.translate("Command_CIRCLE", "Ttr (tangent tangent radius)") or \
                 value == "Ttr (tangent tangent radius)":
               # set the map tool
               self.getPointMapTool().setMode(Qad_circle_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_FIRST_TAN)
               # is preparing to wait for a point
               self.waitForPoint(QadMsg.translate("Command_CIRCLE", "Specify first tangent element of the circle: "))
               self.step = 9
         elif type(value) == QgsPointXY: # if the center of the circle has been entered
            self.centerPt = value
            self.plugIn.setLastPoint(value)

            # set the map tool
            self.getPointMapTool().centerPt = self.centerPt
            self.getPointMapTool().setMode(Qad_circle_maptool_ModeEnum.CENTER_PT_KNOWN_ASK_FOR_RADIUS)

            keyWords = QadMsg.translate("Command_CIRCLE", "Diameter") + "/" + \
                       QadMsg.translate("Command_CIRCLE", "Area")
            prompt = QadMsg.translate("Command_CIRCLE", "Specify the circle radius or [{0}]: ").format(keyWords)

            englishKeyWords = "Diameter" + "/" + "Area"
            keyWords += "_" + englishKeyWords
            # is preparing to wait for a point or a keyword
            # msg, inputType, default, keyWords, positive values
            self.waitFor(prompt, \
                         QadInputTypeEnum.POINT2D | QadInputTypeEnum.FLOAT | QadInputTypeEnum.KEYWORDS, \
                         None, \
                         keyWords, \
                         QadInputModeEnum.NOT_ZERO | QadInputModeEnum.NOT_NEGATIVE)

            self.step = 2

         return False

      # =========================================================================
      # ANSWER TO THE REQUEST RADIUS OR DIAMETER OR AREA
      elif self.step == 2: # after waiting for a point or a keyword the command is restarted
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

         if type(value) == unicode:
            if value == QadMsg.translate("Command_CIRCLE", "Diameter") or value == "Diameter":
               # set the map tool
               self.getPointMapTool().setMode(Qad_circle_maptool_ModeEnum.CENTER_PT_KNOWN_ASK_FOR_DIAM)
               # is preparing to wait for a point or a real number
               # msg, inputType, default, keyWords, positive values
               self.waitFor(QadMsg.translate("Command_CIRCLE", "Specify the circle diameter: "), \
                            QadInputTypeEnum.POINT2D | QadInputTypeEnum.FLOAT, \
                            None, \
                            "", \
                            QadInputModeEnum.NOT_NULL | QadInputModeEnum.NOT_ZERO | QadInputModeEnum.NOT_NEGATIVE)
               self.step = 3
            elif value == QadMsg.translate("Command_CIRCLE", "Area") or value == "Area":
               msg = QadMsg.translate("Command_CIRCLE", "Enter circle area in current unit <{0}>: ")
               # is preparing to wait for a real number
               # msg, inputType, default, keyWords, positive values
               self.waitFor(msg.format(str(self.area)), QadInputTypeEnum.FLOAT, \
                            self.area, "", \
                            QadInputModeEnum.NOT_NULL | QadInputModeEnum.NOT_ZERO | QadInputModeEnum.NOT_NEGATIVE)
               self.getPointMapTool().setMode(Qad_circle_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_CENTER_PT)
               self.step = 13
         elif type(value) == QgsPointXY or type(value) == float: # if the radius of the circle has been entered
            if type(value) == QgsPointXY: # if the radius of the circle with a point has been entered
               self.radius = qad_utils.getDistance(self.centerPt, value)
            else:
               self.radius = value

            self.plugIn.setLastRadius(self.radius)

            circle = QadCircle()
            if circle.set(self.centerPt, self.radius) is not None:
               geom = circle.asGeom(currLayer.wkbType())
               if geom is not None:
                  if self.virtualCmd == False: # if you really want to save the circle in a layer
                     qad_layer.addGeomToLayer(self.plugIn, currLayer, self.mapToLayerCoordinates(currLayer, geom))
                  return True # end command

            keyWords = QadMsg.translate("Command_CIRCLE", "Diameter") + "/" + \
                       QadMsg.translate("Command_CIRCLE", "Area")
            prompt = QadMsg.translate("Command_CIRCLE", "Specify the circle radius or [{0}]: ").format(keyWords)

            englishKeyWords = "Diameter" + "/" + "Area"
            keyWords += "_" + englishKeyWords
            # is preparing to wait for a point or a keyword
            # msg, inputType, default, keyWords, positive values
            self.waitFor(prompt, \
                         QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                         None, \
                         keyWords, QadInputModeEnum.NOT_ZERO | QadInputModeEnum.NOT_NEGATIVE)
            self.isValidPreviousInput = False # to manage the command also in macros
         return False

      # =========================================================================
      # RESPONSE TO THE RIM DIAMETER REQUEST (from step = 2)
      elif self.step == 3: # after waiting for a point or a real number the command is restarted
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

         if type(value) == QgsPointXY: # if a point has been inserted
            self.radius = qad_utils.getDistance(self.centerPt, value) / 2
         elif type(value) == float: # if a real number has been entered
            self.radius = value / 2

         self.plugIn.setLastRadius(self.radius)

         circle = QadCircle()
         if circle.set(self.centerPt, self.radius) is not None:
            geom = circle.asGeom(currLayer.wkbType())
            if geom is not None:
               if self.virtualCmd == False: # if you really want to save the circle in a layer
                  qad_layer.addGeomToLayer(self.plugIn, currLayer, self.mapToLayerCoordinates(currLayer, geom))
               return True # end command

         # is preparing to wait for a point or a real number
         # msg, inputType, default, keyWords, positive values
         self.waitFor(QadMsg.translate("Command_CIRCLE", "Specify the circle diameter: "), \
                      QadInputTypeEnum.POINT2D | QadInputTypeEnum.FLOAT, \
                      None, \
                      "", \
                      QadInputModeEnum.NOT_NULL | QadInputModeEnum.NOT_ZERO | QadInputModeEnum.NOT_NEGATIVE)
         self.isValidPreviousInput = False # to manage the command also in macros
         return False

      # =========================================================================
      # RESPONSE TO THE REQUEST FOR THE FIRST POINT OF THE CIRCLE (from step = 1)
      elif self.step == 4: # after waiting for a point the command restarts
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

            snapTypeOnSel = self.getPointMapTool().snapTypeOnSelection
            value = self.getPointMapTool().point
            entity = self.getPointMapTool().entity
         else: # the dot comes as a parameter of the function
            value = msg
            snapTypeOnSel = QadSnapTypeEnum.NONE

         # if a point has been selected with the TAN_DEF mode it is a deferred point
         if snapTypeOnSel == QadSnapTypeEnum.TAN_DEF and entity.isInitialized():
            self.firstPt = None
            self.firstPtTan = value

            # the function returns a list with
            # (<minimum distance>
            #  <nearest point>
            #  <nearest geometry index>
            #  <index of the nearest sub-geometry>
            #   if closed geometry is polyline type the list also contains
            #  <index of the closest sub-geometry part>
            #  <"to the left of" if the point is to the left of the part (< 0 -> left, > 0 -> right)
            # )
            # part closest to the self.firstPtTan point
            result = getQadGeomClosestPart(entity.getQadGeom(), self.firstPtTan)
            # I duplicate the geometry of the part
            self.firstGeomTan = getQadGeomPartAt(entity.getQadGeom(), result[2], result[3], result[4]).copy()

            # set the map tool
            self.getPointMapTool().setMode(Qad_circle_maptool_ModeEnum.FIRST_PT_KNOWN_ASK_FOR_SECOND_PT)
         else: # otherwise it is an explicit point
            self.firstPt = value
            self.plugIn.setLastPoint(value)
            # set the map tool
            self.getPointMapTool().firstPt = self.firstPt
            self.getPointMapTool().setMode(Qad_circle_maptool_ModeEnum.FIRST_PT_KNOWN_ASK_FOR_SECOND_PT)

         # is preparing to wait for a point
         self.waitForPoint(QadMsg.translate("Command_CIRCLE", "Specify second point on the circle: "))

         self.step = 5
         return False

      # =========================================================================
      # RESPONSE TO THE REQUEST FOR THE SECOND POINT OF THE CIRCLE (from step = 4)
      elif self.step == 5:  # after waiting for a point the command restarts
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

            snapTypeOnSel = self.getPointMapTool().snapTypeOnSelection
            value = self.getPointMapTool().point
            entity = self.getPointMapTool().entity
         else: # the dot comes as a parameter of the function
            value = msg
            snapTypeOnSel = QadSnapTypeEnum.NONE

         # if a point has been selected with the TAN_DEF mode it is a deferred point
         if snapTypeOnSel == QadSnapTypeEnum.TAN_DEF and entity.isInitialized():
            self.secondPt = None
            self.secondPtTan = value

            # the function returns a list with
            # (<minimum distance>
            #  <nearest point>
            #  <nearest geometry index>
            #  <index of the nearest sub-geometry>
            #   if closed geometry is polyline type the list also contains
            #  <index of the closest sub-geometry part>
            #  <"to the left of" if the point is to the left of the part (< 0 -> left, > 0 -> right)
            # )
            # part closest to the self.secondPtTan point
            result = getQadGeomClosestPart(entity.getQadGeom(), self.secondPtTan)
            # I duplicate the geometry of the part
            self.secondGeomTan = getQadGeomPartAt(entity.getQadGeom(), result[2], result[3], result[4]).copy()
            # set the map tool
            self.getPointMapTool().setMode(Qad_circle_maptool_ModeEnum.FIRST_SECOND_PT_KNOWN_ASK_FOR_THIRD_PT)
         else: # otherwise it is an explicit point
            self.secondPt = value
            self.plugIn.setLastPoint(value)
            # set the map tool
            self.getPointMapTool().secondPt = self.secondPt
            self.getPointMapTool().setMode(Qad_circle_maptool_ModeEnum.FIRST_SECOND_PT_KNOWN_ASK_FOR_THIRD_PT)

         # is preparing to wait for a point
         self.waitForPoint(QadMsg.translate("Command_CIRCLE", "Specify the third point on the circle: "))

         self.step = 6
         return False

      # =========================================================================
      # RESPONSE TO THE REQUEST FOR THE THIRD POINT OF THE CIRCLE (from step = 5)
      elif self.step == 6:  # after waiting for a point the command restarts
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

            snapTypeOnSel = self.getPointMapTool().snapTypeOnSelection
            value = self.getPointMapTool().point
            entity = self.getPointMapTool().entity
         else: # the dot comes as a parameter of the function
            value = msg
            snapTypeOnSel = QadSnapTypeEnum.NONE

         # if a point has been selected with the TAN_DEF mode it is a deferred point
         if snapTypeOnSel == QadSnapTypeEnum.TAN_DEF and entity.isInitialized():
            self.thirdPt = None
            self.thirdPtTan = value

            # the function returns a list with
            # (<minimum distance>
            #  <nearest point>
            #  <nearest geometry index>
            #  <index of the nearest sub-geometry>
            #   if closed geometry is polyline type the list also contains
            #  <index of the closest sub-geometry part>
            #  <"to the left of" if the point is to the left of the part (< 0 -> left, > 0 -> right)
            # )
            # part closest to the self.secondPtTan point
            result = getQadGeomClosestPart(entity.getQadGeom(), self.thirdPtTan)
            # I duplicate the geometry of the part
            self.thirdGeomTan = getQadGeomPartAt(entity.getQadGeom(), result[2], result[3], result[4]).copy()
         else: # otherwise it is an explicit point
            self.thirdPt = value
            self.plugIn.setLastPoint(value)

         circle = None
         if self.firstPt is None: # if the first point is defined with a deferred point
            if self.secondPt is None: # if the second point is defined with a deferred point
               if self.thirdPt is None: # if the third point is defined with a deferred point
                  circle = circleFrom3TanPts(self.firstGeomTan, self.firstPtTan, \
                                             self.secondGeomTan, self.secondPtTan, \
                                             self.thirdGeomTan, self.thirdPtTan)
               else: # if the third point is defined with an explicit point
                  circle = circleFrom1IntPt2TanPts(self.thirdPt, self.firstGeomTan, self.firstPtTan,
                                                   self.secondGeomTan, self.secondPtTan)
            else: # if the second point is defined with an explicit point
               if self.thirdPt is None: # if the third point is defined with a deferred point
                  circle = circleFrom1IntPt2TanPts(self.secondPt, self.firstGeomTan, self.firstPtTan,
                                                   self.thirdGeomTan, self.thirdPtTan)
               else: # if the third point is defined with an explicit point
                  circle = circleFrom2IntPts1TanPt(self.secondPt, self.thirdPt, \
                                                   self.firstGeomTan, self.firstPtTan)
         else: # if the first point is defined with an explicit point
            if self.secondPt is None: # if the second point is defined with a deferred point
               if self.thirdPt is None: # if the third point is defined with a deferred point
                  circe = circleFrom1IntPt2TanPts(self.firstPt, self.secondGeomTan, self.secondPtTan,
                                                  self.thirdGeomTan, self.thirdPtTan)
               else: # if the third point is defined with an explicit point
                  circe = circleFrom2IntPts1TanPt(self.firstPt, self.thirdPt, \
                                                  self.secondGeomTan, self.secondPtTan)
            else: # if the second point is defined with an explicit point
               if self.thirdPt is None: # if the third point is defined with a deferred point
                  circle = circleFrom2IntPts1TanPt(self.firstPt, self.secondPt, \
                                                   self.thirdGeomTan, self.thirdPtTan)
               else: # if the third point is defined with an explicit point
                  circle = circleFrom3Pts(self.firstPt, self.secondPt, value)

         if circle is not None:
            self.centerPt = circle.center
            self.radius = circle.radius

            geom = circle.asGeom(currLayer.wkbType())
            if geom is not None:
               if self.virtualCmd == False: # if you really want to save the circle in a layer
                  qad_layer.addGeomToLayer(self.plugIn, currLayer, self.mapToLayerCoordinates(currLayer, geom))
               return True # end command

         # is preparing to wait for a point
         self.waitForPoint(QadMsg.translate("Command_CIRCLE", "Specify the third point on the circle: "))
         self.isValidPreviousInput = False # to manage the command also in macros
         return False

      # =========================================================================
      # RESPONSE TO THE REQUEST FOR THE FIRST DIAM END OF THE CIRCLE (from step = 1)
      elif self.step == 7:  # after waiting for a point the command restarts
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

            snapTypeOnSel = self.getPointMapTool().snapTypeOnSelection
            value = self.getPointMapTool().point
            entity = self.getPointMapTool().entity
         else: # the dot comes as a parameter of the function
            value = msg
            snapTypeOnSel = QadSnapTypeEnum.NONE

         # if a point has been selected with the TAN_DEF mode it is a deferred point
         if snapTypeOnSel == QadSnapTypeEnum.TAN_DEF and entity.isInitialized():
            self.firstDiamPt = None
            self.firstDiamPtTan = value
            result = getQadGeomClosestPart(entity.getQadGeom(), self.firstDiamPtTan)
            # I duplicate the geometry of the part
            self.firstDiamGeomTan = getQadGeomPartAt(entity.getQadGeom(), result[2], result[3], result[4]).copy()
            # set the map tool
            self.getPointMapTool().setMode(Qad_circle_maptool_ModeEnum.FIRST_DIAM_PT_KNOWN_ASK_FOR_SECOND_DIAM_PT)
         else: # otherwise it is an explicit point
            self.firstDiamPt = value
            # set the map tool
            self.getPointMapTool().firstDiamPt = self.firstDiamPt
            self.getPointMapTool().setMode(Qad_circle_maptool_ModeEnum.FIRST_DIAM_PT_KNOWN_ASK_FOR_SECOND_DIAM_PT)

         # is preparing to wait for a point
         self.waitForPoint(QadMsg.translate("Command_CIRCLE", "Specify second end of the circle diameter: "))

         self.step = 8
         return False

      # =========================================================================
      # RESPONSE TO THE REQUEST FOR THE SECOND END DIAM OF THE CIRCLE (from step = 7)
      elif self.step == 8:  # after waiting for a point the command restarts
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

            snapTypeOnSel = self.getPointMapTool().snapTypeOnSelection
            value = self.getPointMapTool().point
            entity = self.getPointMapTool().entity
         else: # the dot comes as a parameter of the function
            value = msg
            snapTypeOnSel = QadSnapTypeEnum.NONE

         # if a point has been selected with the TAN_DEF mode it is a deferred point
         if snapTypeOnSel == QadSnapTypeEnum.TAN_DEF and entity.isInitialized():
            self.secondDiamPt = None
            self.secondDiamPtTan = value
            result = getQadGeomClosestPart(entity.getQadGeom(), self.secondDiamPtTan)
            # I duplicate the geometry of the part
            self.secondDiamGeomTan = getQadGeomPartAt(entity.getQadGeom(), result[2], result[3], result[4]).copy()
         else: # otherwise it is an explicit point
            self.secondDiamPt = value

         circle = None
         if self.firstDiamPt is None: # if the diameter is defined with the first deferred point
            if self.secondDiamPt is None: # the diameter is defined with the second deferred point
               circle = circleFromDiamEnds2TanPts(self.firstDiamGeomTan, self.firstDiamPtTan, \
                                                  self.secondDiamGeomTan, self.secondDiamPtTan)
            else: # if the diameter is defined with the second explicit point
               circle = circleFromDiamEndsPtTanPt(self.secondDiamPt, self.firstDiamGeomTan, self.firstDiamPtTan)
         else: # if the diameter is defined with the first explicit point
            if self.secondDiamPt is None: # the diameter is defined with the second deferred point
               circle = circleFromDiamEndsPtTanPt(self.firstDiamPt, self.secondDiamGeomTan, self.secondDiamPtTan)
            else: # if the diameter is defined with the second explicit point
               circle = QadCircle().fromDiamEnds(self.firstDiamPt, self.secondDiamPt)

         if circle is not None:
            self.centerPt = circle.center
            self.radius = circle.radius

            geom = circle.asGeom(currLayer.wkbType())
            if geom is not None:
               if self.virtualCmd == False: # if you really want to save the circle in a layer
                  qad_layer.addGeomToLayer(self.plugIn, currLayer, self.mapToLayerCoordinates(currLayer, geom))
               return True # end command

         # is preparing to wait for a point
         self.waitForPoint(QadMsg.translate("Command_CIRCLE", "Specify second end of the circle diameter: "))
         self.isValidPreviousInput = False # to manage the command also in macros
         return False


      # =========================================================================
      # RESPONSE TO THE FIRST TANGENT REQUEST (from step = 1)
      elif self.step == 9: # after waiting for a point the command restarts
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

            entity = self.getPointMapTool().entity
         else: # the dot comes as a parameter of the function
            # is preparing to wait for a point
            self.waitForPoint(QadMsg.translate("Command_CIRCLE", "Specify first tangent element of the circle: "))
            self.isValidPreviousInput = False # to manage the command also in macros
            return False

         if not entity.isInitialized(): # if an entity has not been selected
            # is preparing to wait for a point
            self.waitForPoint(QadMsg.translate("Command_CIRCLE", "Specify first tangent element of the circle: "))
            self.isValidPreviousInput = False # to manage the command also in macros
            return False

         result = getQadGeomClosestPart(entity.getQadGeom(), self.getPointMapTool().point)
         g = getQadGeomPartAt(entity.getQadGeom(), result[2], result[3], result[4])
         gType = g.whatIs()
         if gType != "LINE" and gType != "ARC" and gType != "CIRCLE":
            self.showErr(QadMsg.translate("Command_CIRCLE", "\nSelect a circle, an arc or a line."))
            # is preparing to wait for a point
            self.waitForPoint(QadMsg.translate("Command_CIRCLE", "Specify first tangent element of the circle: "))
            self.isValidPreviousInput = False # to manage the command also in macros
            return False

         self.tanPt1 = self.getPointMapTool().point
         # I duplicate the geometry of the part
         self.tanGeom1 = g.copy()

         # set the map tool
         self.getPointMapTool().tanGeom1 = self.tanGeom1
         self.getPointMapTool().tanPt1 = self.tanPt1
         self.getPointMapTool().setMode(Qad_circle_maptool_ModeEnum.FIRST_TAN_KNOWN_ASK_FOR_SECOND_TAN)

         # is preparing to wait for a point
         self.waitForPoint(QadMsg.translate("Command_CIRCLE", "Specify second tangent element of the circle: "))
         self.step = 10
         return False

      # =========================================================================
      # RESPONSE TO THE SECOND TANGENT REQUEST (from step = 9)
      elif self.step == 10: # after waiting for a point the command restarts
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

            entity = self.getPointMapTool().entity
         else: # the dot comes as a parameter of the function
            # is preparing to wait for a point
            self.waitForPoint(QadMsg.translate("Command_CIRCLE", "Specify second tangent element of the circle: "))
            self.isValidPreviousInput = False # to manage the command also in macros
            return False

         if not entity.isInitialized(): # if an entity has not been selected
            # is preparing to wait for a point
            self.waitForPoint(QadMsg.translate("Command_CIRCLE", "Specify second tangent element of the circle: "))
            self.isValidPreviousInput = False # to manage the command also in macros
            return False

         result = getQadGeomClosestPart(entity.getQadGeom(), self.getPointMapTool().point)
         g = getQadGeomPartAt(entity.getQadGeom(), result[2], result[3], result[4])
         gType = g.whatIs()
         if gType != "LINE" and gType != "ARC" and gType != "CIRCLE":
            self.showErr(QadMsg.translate("Command_CIRCLE", "\nSelect a circle, an arc or a line."))
            # is preparing to wait for a point
            self.waitForPoint(QadMsg.translate("Command_CIRCLE", "Specify second tangent element of the circle: "))
            self.isValidPreviousInput = False # to manage the command also in macros
            return False

         self.tanPt2 = self.getPointMapTool().point
         # I duplicate the geometry of the part
         self.tanGeom2 = g.copy()

         # set the map tool
         self.getPointMapTool().tanGeom2 = self.tanGeom2
         self.getPointMapTool().tanPt2 = self.tanPt2
         self.getPointMapTool().setMode(Qad_circle_maptool_ModeEnum.FIRST_SECOND_TAN_KNOWN_ASK_FOR_RADIUS)

         # is preparing to wait for a point or a real number
         # msg, inputType, default, keyWords, positive values
         msg = QadMsg.translate("Command_CIRCLE", "Specify the circle radius <{0}>: ")
         self.waitFor(msg.format(str(self.plugIn.lastRadius)), \
                      QadInputTypeEnum.POINT2D | QadInputTypeEnum.FLOAT, \
                      self.plugIn.lastRadius, "", \
                      QadInputModeEnum.NOT_ZERO | QadInputModeEnum.NOT_NEGATIVE)
         self.step = 11
         return False

      # =========================================================================
      # RESPONSE TO RADIUS REQUEST (from step = 10)
      elif self.step == 11: # after waiting for a point or a real number the command is restarted
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
            self.startPtForRadius = value

            # set the map tool
            self.getPointMapTool().startPtForRadius = self.startPtForRadius
            self.getPointMapTool().setMode(Qad_circle_maptool_ModeEnum.FIRST_SECOND_TAN_FIRSTPTRADIUS_KNOWN_ASK_FOR_SECONDPTRADIUS)

            # is preparing to wait for a point
            self.waitForPoint(QadMsg.translate("Command_CIRCLE", "Specify second point: "))
            self.step = 12
            return False
         else:
            self.plugIn.setLastRadius(value)

            circle = circleFrom2TanPtsRadius(self.tanGeom1, self.tanPt1, \
                                             self.tanGeom2, self.tanPt2, value)
            if circle is not None:
               geom = circle.asGeom(currLayer.wkbType())
               if geom is not None:
                  self.centerPt = circle.center
                  self.radius = circle.radius
                  if self.virtualCmd == False: # if you really want to save the circle in a layer
                     qad_layer.addGeomToLayer(self.plugIn, currLayer, self.mapToLayerCoordinates(currLayer, geom))
               else:
                  self.showMsg(QadMsg.translate("Command_CIRCLE", "\nThe circle doesn't exist."))
            else:
               self.showMsg(QadMsg.translate("Command_CIRCLE", "\nThe circle doesn't exist."))

            return True # end command

      # =========================================================================
      # RESPONSE TO THE REQUEST SECOND POINT OF THE RAY (from step = 11)
      elif self.step == 12: # after waiting for a point the command restarts
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

         self.radius = qad_utils.getDistance(self.startPtForRadius, value)
         self.plugIn.setLastRadius(self.radius)

         circle = circleFrom2TanPtsRadius(self.tanGeom1, self.tanPt1, \
                                           self.tanGeom2, self.tanPt2, self.radius)
         if circle is not None:
            geom = circle.asGeom(currLayer.wkbType())
            if geom is not None:
               self.centerPt = circle.center
               self.radius = circle.radius
               if self.virtualCmd == False: # if you really want to save the circle in a layer
                  qad_layer.addGeomToLayer(self.plugIn, currLayer, self.mapToLayerCoordinates(currLayer, geom))
            else:
               self.showMsg(QadMsg.translate("Command_CIRCLE", "\nThe circle doesn't exist."))
         else:
            self.showMsg(QadMsg.translate("Command_CIRCLE", "\nThe circle doesn't exist."))
         return True # end command

      # =========================================================================
      # RESPONSE TO THE CIRCLE AREA REQUEST (from step = 2)
      elif self.step == 13: # after waiting for a number the command is restarted
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if while selecting a point
            # Another plugin was activated which deactivated Qad
            # so the command that returns here has been reactivated without the map tool
            # has selected a point
            if self.getPointMapTool().point is None: # the map tool was activated without a dot
               if self.getPointMapTool().rightButton != True: # if NOT used the right mouse button
                  self.setMapTool(self.getPointMapTool()) # I reactivate the map tool
                  return False

            value = self.getPointMapTool().point
         else: # the dot comes as a parameter of the function
            value = msg

         if type(value) == float: # the area was entered
            self.area = value

            circle = QadCircle().fromCenterArea(self.centerPt, self.area)
            if circle is not None:
               self.radius = circle.radius
               self.plugIn.setLastRadius(self.radius)
               geom = circle.asGeom(currLayer.wkbType())
               if geom is not None:
                  if self.virtualCmd == False: # if you really want to save the circle in a layer
                     qad_layer.addGeomToLayer(self.plugIn, currLayer, self.mapToLayerCoordinates(currLayer, geom))
                  return True # end command

         self.isValidPreviousInput = False # to manage the command also in macros
         return False
