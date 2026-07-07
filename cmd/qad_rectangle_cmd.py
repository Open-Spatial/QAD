# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin OK

 RECTANGLE command to draw a rectangle

                              -------------------
        begin                : 2013-12-02
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
from qgis.core import QgsWkbTypes, QgsPointXY
from qgis.PyQt.QtGui import QIcon


from ..qad_polyline import QadPolyline
from ..qad_getpoint import QadGetPointDrawModeEnum
from .qad_rectangle_maptool import Qad_rectangle_maptool_ModeEnum, Qad_rectangle_maptool
from .qad_generic_cmd import QadCommandClass
from ..qad_msg import QadMsg
from ..qad_textwindow import QadInputTypeEnum, QadInputModeEnum
from .. import qad_utils
from .. import qad_layer
from .qad_getdist_cmd import QadGetDistClass
from .qad_getangle_cmd import QadGetAngleClass


# Class that manages the RECTANGLE command
class QadRECTANGLECommandClass(QadCommandClass):

   def instantiateNewCmd(self):
      """instantiates a new command of the same type"""
      return QadRECTANGLECommandClass(self.plugIn)

   def getName(self):
      return QadMsg.translate("Command_list", "RECTANGLE")

   def getEnglishName(self):
      return "RECTANGLE"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runRECTANGLECommand)

   def getIcon(self):
      return QIcon(":/plugins/qad/icons/rectangle.svg")

   def getNote(self):
      # set the explanatory notes of the command
      return QadMsg.translate("Command_RECTANGLE", "Creates a rectangle.")

   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      # if this flag = True the command is used within another command to draw a rectangle
      # which will not be saved on a layer
      self.virtualCmd = False
      self.firstCorner = None
      self.gapType = 0 # 0 = Angoli retti; 1 = Raccorda i segmenti; 2 = Cima i segmenti
      self.gapValue1 = 0 # if gapType = 1 -> radius of curvature; if gapType = 2 -> first trimming distance
      self.gapValue2 = 0 # if gapType = 2 -> second trimming distance
      self.area = 100
      self.dim1 = 10
      self.rot = 0
      self.polyline = QadPolyline()

      self.GetDistClass = None
      self.GetAngleClass = None
      self.defaultValue = None # used to manage the right mouse button

   def __del__(self):
      QadCommandClass.__del__(self)
      if self.GetDistClass is not None:
         del self.GetDistClass
      if self.GetAngleClass is not None:
         del self.GetAngleClass


   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      # when you are in the distance request phase
      if self.step == 3 or self.step == 4 or self.step == 5 or \
         self.step == 8 or self.step == 9 or self.step == 10 or self.step == 11:
         return self.GetDistClass.getPointMapTool()
      # when the rotation request is in progress
      elif self.step == 13:
         return self.GetAngleClass.getPointMapTool()
      else:
         if (self.plugIn is not None):
            if self.PointMapTool is None:
               self.PointMapTool = Qad_rectangle_maptool(self.plugIn)
            return self.PointMapTool
         else:
            return None


   def getCurrentContextualMenu(self):
      # when you are in the distance request phase
      if self.step == 3 or self.step == 4 or self.step == 5 or \
         self.step == 8 or self.step == 9 or self.step == 10 or self.step == 11:
         return self.GetDistClass.getCurrentContextualMenu()
      # when the rotation request is in progress
      elif self.step == 13:
         return self.GetAngleClass.getCurrentContextualMenu()
      else:
         return self.contextualMenu


   def addRectangleToLayer(self, layer):
      vertices = self.polyline.asPolyline()
      if layer.geometryType() == QgsWkbTypes.LineGeometry:
         qad_layer.addLineToLayer(self.plugIn, layer, vertices)
      elif layer.geometryType() == QgsWkbTypes.PolygonGeometry:
         qad_layer.addPolygonToLayer(self.plugIn, layer, vertices)


   # ============================================================================
   # WaitForFirstCorner
   # ============================================================================
   def WaitForFirstCorner(self):
      self.step = 1
      self.getPointMapTool().setMode(Qad_rectangle_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_FIRST_CORNER)

      keyWords = QadMsg.translate("Command_RECTANGLE", "Chamfer") + "/" + \
                 QadMsg.translate("Command_RECTANGLE", "Fillet")
      prompt = QadMsg.translate("Command_RECTANGLE", "Specify first corner or [{0}]: ").format(keyWords)

      englishKeyWords = "Chamfer" + "/" + "Fillet"
      keyWords += "_" + englishKeyWords
      # is preparing to wait for a point or Enter
      #                        msg, inputType,              default, keyWords, no check
      self.waitFor(prompt, \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                   None, keyWords, QadInputModeEnum.NONE)

   # ============================================================================
   # WaitForSecondCorner
   # ============================================================================
   def WaitForSecondCorner(self, layer):
      self.step = 2
      self.getPointMapTool().rot = self.rot
      self.getPointMapTool().gapType = self.gapType
      self.getPointMapTool().gapValue1 = self.gapValue1
      self.getPointMapTool().gapValue2 = self.gapValue2
      self.getPointMapTool().setMode(Qad_rectangle_maptool_ModeEnum.FIRST_CORNER_KNOWN_ASK_FOR_SECOND_CORNER)
      if layer is not None:
         self.getPointMapTool().geomType = layer.geometryType()

      keyWords = QadMsg.translate("Command_RECTANGLE", "Area") + "/" + \
                 QadMsg.translate("Command_RECTANGLE", "Dimensions") + "/" + \
                 QadMsg.translate("Command_RECTANGLE", "Rotation")
      prompt = QadMsg.translate("Command_RECTANGLE", "Specify other corner or [{0}]: ").format(keyWords)

      englishKeyWords = "Area" + "/" + "Dimensions" + "/" + "Rotation"
      keyWords += "_" + englishKeyWords
      # is preparing to wait for a point or Enter
      #                        msg, inputType,              default, keyWords, no check
      self.waitFor(prompt, \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                   None, keyWords, QadInputModeEnum.NONE)

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
      # FIRST POINT REQUEST
      if self.step == 0: # start of command
         self.WaitForFirstCorner()
         return False

      # =========================================================================
      # RESPONSE TO THE REQUEST OF THE FIRST POINT OF THE RECTANGLE (from step = 0)
      elif self.step == 1: # after waiting for a point the command restarts
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if while selecting a point
            # Another plugin was activated which deactivated Qad
            # so the command that returns here has been reactivated without the map tool
            # has selected a point
            if self.getPointMapTool().point is None: # the map tool was activated without a dot
               if self.getPointMapTool().rightButton == True: # if used with the right mouse button
                  self.showMsg(QadMsg.translate("Command_RECTANGLE", "Window not correct."))
                  self.WaitForFirstCorner()
                  return False
               else:
                  self.setMapTool(self.getPointMapTool()) # I reactivate the map tool
                  return False

            value = self.getPointMapTool().point
         else: # the dot comes as a parameter of the function
            value = msg

         if type(value) == unicode:
            if value == QadMsg.translate("Command_RECTANGLE", "Chamfer") or value == "Chamfer":
               if self.GetDistClass is not None:
                  del self.GetDistClass
               self.GetDistClass = QadGetDistClass(self.plugIn)
               prompt = QadMsg.translate("Command_RECTANGLE", "Specify first chamfer distance for rectangle <{0}>: ")
               self.GetDistClass.msg = prompt.format(str(self.gapValue1))
               self.GetDistClass.dist = self.gapValue1
               self.GetDistClass.inputMode = QadInputModeEnum.NOT_NEGATIVE
               self.step = 4
               self.GetDistClass.run(msgMapTool, msg)
            elif value == QadMsg.translate("Command_RECTANGLE", "Fillet") or value == "Fillet":
               if self.GetDistClass is not None:
                  del self.GetDistClass
               self.GetDistClass = QadGetDistClass(self.plugIn)
               prompt = QadMsg.translate("Command_RECTANGLE", "Specify rectangle fillet radius <{0}>: ")
               self.GetDistClass.msg = prompt.format(str(self.gapValue1))
               self.GetDistClass.dist = self.gapValue1
               self.GetDistClass.inputMode = QadInputModeEnum.NOT_NEGATIVE
               self.step = 3
               self.GetDistClass.run(msgMapTool, msg)
         elif type(value) == QgsPointXY:
            self.firstCorner = value
            self.getPointMapTool().firstCorner = self.firstCorner
            self.WaitForSecondCorner(currLayer)

         return False # continua


      # =========================================================================
      # RESPONSE TO THE REQUEST OF THE SECOND POINT OF THE RECTANGLE (from step = 1)
      elif self.step == 2: # after waiting for a point the command restarts
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if while selecting a point
            # Another plugin was activated which deactivated Qad
            # so the command that returns here has been reactivated without the map tool
            # has selected a point
            if self.getPointMapTool().point is None: # the map tool was activated without a dot
               if self.getPointMapTool().rightButton == True: # if used with the right mouse button
                  self.showMsg(QadMsg.translate("Command_RECTANGLE", "Window not correct."))
                  self.WaitForSecondCorner(currLayer)
                  return False
               else:
                  self.setMapTool(self.getPointMapTool()) # I reactivate the map tool
                  return False

            value = self.getPointMapTool().point
         else: # the dot comes as a parameter of the function
            value = msg

         if type(value) == unicode:
            if value == QadMsg.translate("Command_RECTANGLE", "Area") or value == "Area":
               msg = QadMsg.translate("Command_RECTANGLE", "Enter rectangle area in current units <{0}>: ")
               # is preparing to wait for a real number
               # msg, inputType, default, keyWords, positive values
               self.waitFor(msg.format(str(self.area)), QadInputTypeEnum.FLOAT, \
                            self.area, "", \
                            QadInputModeEnum.NOT_ZERO | QadInputModeEnum.NOT_NEGATIVE)
               self.getPointMapTool().setMode(Qad_rectangle_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_FIRST_CORNER)

               self.step = 6
            elif value == QadMsg.translate("Command_RECTANGLE", "Dimensions") or value == "Dimensions":
               if self.GetDistClass is not None:
                  del self.GetDistClass
               self.GetDistClass = QadGetDistClass(self.plugIn)
               prompt = QadMsg.translate("Command_RECTANGLE", "Specify length for rectangle <{0}>: ")
               self.GetDistClass.msg = prompt.format(str(self.dim1))
               self.GetDistClass.dist = self.dim1
               self.step = 10
               self.GetDistClass.run(msgMapTool, msg)
            elif value == QadMsg.translate("Command_RECTANGLE", "Rotation") or value == "Rotation":
               keyWords = QadMsg.translate("Command_RECTANGLE", "Points")
               self.defaultValue = self.rot
               prompt = QadMsg.translate("Command_RECTANGLE", "Specify rotation angle or [{0}] <{1}>: ").format(keyWords, str(qad_utils.toDegrees(self.rot)))

               englishKeyWords = "Points"
               keyWords += "_" + englishKeyWords
               # is preparing to wait for a point or a real number
               # msg, inputType, default, keyWords, non-null values
               self.waitFor(prompt, \
                            QadInputTypeEnum.POINT2D | QadInputTypeEnum.FLOAT | QadInputTypeEnum.KEYWORDS, \
                            self.rot, keyWords)
               self.getPointMapTool().setMode(Qad_rectangle_maptool_ModeEnum.FIRST_CORNER_KNOWN_ASK_FOR_ROTATION)

               self.step = 12
         elif type(value) == QgsPointXY:
            self.polyline.getRectByCorners(self.firstCorner, value, self.rot, \
                                           self.gapType, self.gapValue1, self.gapValue2)

            if self.virtualCmd == False: # if you really want to save buffers in a layer
               self.addRectangleToLayer(currLayer)
            return True

         return False # continua

      # =========================================================================
      # RESPONSE TO THE CURVATURE RADIUS REQUEST (from step = 1)
      elif self.step == 3:
         if self.GetDistClass.run(msgMapTool, msg) == True:
            if self.GetDistClass.dist is not None:
               self.gapValue1 = self.GetDistClass.dist
               if self.gapValue1 == 0:
                  self.gapType = 0 # 0 = Angoli retti
               else:
                  self.gapType = 1 # 1 = Raccorda i segmenti

            self.WaitForFirstCorner()
            self.getPointMapTool().refreshSnapType() # update the snapType which can be varied from the distance map tool
         return False # end command

      # =========================================================================
      # RESPONSE TO THE FIRST TRIM DISTANCE REQUEST (from step = 1)
      elif self.step == 4:
         if self.GetDistClass.run(msgMapTool, msg) == True:
            if self.GetDistClass.dist is not None:
               self.gapValue1 = self.GetDistClass.dist

               if self.GetDistClass is not None:
                  del self.GetDistClass
               self.GetDistClass = QadGetDistClass(self.plugIn)
               prompt = QadMsg.translate("Command_RECTANGLE", "Specify second chamfer distance for rectangle <{0}>: ")
               self.GetDistClass.msg = prompt.format(str(self.gapValue2))
               self.GetDistClass.dist = self.gapValue2
               self.GetDistClass.inputMode = QadInputModeEnum.NOT_NEGATIVE
               self.step = 5
               self.GetDistClass.run(msgMapTool, msg)
            else:
               self.WaitForFirstCorner()
               self.getPointMapTool().refreshSnapType() # update the snapType which can be varied from the distance map tool
         return False # end command

      # =========================================================================
      # RESPONSE TO THE SECOND TRIM DISTANCE REQUEST (from step = 1)
      elif self.step == 5:
         if self.GetDistClass.run(msgMapTool, msg) == True:
            if self.GetDistClass.dist is not None:
               self.gapValue2 = self.GetDistClass.dist
               if self.gapValue1 == 0 or self.gapValue2 == 0:
                  self.gapType = 0 # 0 = Angoli retti
               else:
                  self.gapType = 2 # 2 = Cima i segmenti

            self.WaitForFirstCorner()
            self.getPointMapTool().refreshSnapType() # update the snapType which can be varied from the distance map tool
         return False # end command

      # =========================================================================
      # RESPONSE TO THE RECTANGLE AREA REQUEST (from step = 2)
      elif self.step == 6: # after waiting for a point the command restarts
         keyWords = QadMsg.translate("Command_RECTANGLE", "Length") + "/" + \
                    QadMsg.translate("Command_RECTANGLE", "Width")
         englishKeyWords = "Length" + "/" + "Width"

         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if while selecting a point
            # Another plugin was activated which deactivated Qad
            # so the command that returns here has been reactivated without the map tool
            # has selected a point
            if self.getPointMapTool().point is None: # the map tool was activated without a dot
               if self.getPointMapTool().rightButton == True: # if used with the right mouse button
                  self.defaultValue = QadMsg.translate("Command_RECTANGLE", "Length")
                  prompt = QadMsg.translate("Command_RECTANGLE", "Calcolate the rectangle dimensions based on [{0}] <{1}>: ").format(keyWords, self.defaultValue)

                  keyWords += "_" + englishKeyWords
                  # is preparing to wait for a keyword
                  # msg, inputType, default, keyWords, positive values
                  self.waitFor(prompt, QadInputTypeEnum.KEYWORDS, \
                               self.defaultValue, \
                               keyWords, QadInputModeEnum.NONE)

                  self.step = 7
                  return False
               else:
                  self.setMapTool(self.getPointMapTool()) # I reactivate the map tool
                  return False

            value = self.getPointMapTool().point
         else: # the dot comes as a parameter of the function
            value = msg

         if type(value) == float: # the area was entered
            self.area = value
            self.defaultValue = QadMsg.translate("Command_RECTANGLE", "Length")
            prompt = QadMsg.translate("Command_RECTANGLE", "Calcolate the rectangle dimensions based on [{0}] <{1}>: ").format(keyWords, self.defaultValue)

            keyWords += "_" + englishKeyWords
            # is preparing to wait for a keyword
            # msg, inputType, default, keyWords, positive values
            self.waitFor(prompt, QadInputTypeEnum.KEYWORDS, \
                         self.defaultValue, \
                         keyWords, QadInputModeEnum.NONE)
            self.step = 7
         return False

      # =========================================================================
      # RESPONSE TO THE MODE REQUEST (LENGTH / WIDTH) GIVEN THE AREA (from step = 6)
      elif self.step == 7: # after waiting for a point or a real number the command is restarted
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if while selecting a point
            # Another plugin was activated which deactivated Qad
            # so the command that returns here has been reactivated without the map tool
            # has selected a point
            if self.getPointMapTool().point is None: # the map tool was activated without a dot
               if self.getPointMapTool().rightButton == True: # if used with the right mouse button
                  value = self.defaultValue
                  return True # end command
               else:
                  self.setMapTool(self.getPointMapTool()) # I reactivate the map tool
                  return False
            else:
               return False
         else: # the dot comes as a parameter of the function
            value = msg

         if value == QadMsg.translate("Command_RECTANGLE", "Length") or value == "Length":
            if self.GetDistClass is not None:
               del self.GetDistClass
            self.GetDistClass = QadGetDistClass(self.plugIn)
            prompt = QadMsg.translate("Command_RECTANGLE", "Enter length for rectangle <{0}>: ")
            self.GetDistClass.msg = prompt.format(str(self.dim1))
            self.GetDistClass.dist = self.dim1
            self.step = 8
            self.GetDistClass.run(msgMapTool, msg)
         elif value == QadMsg.translate("Command_RECTANGLE", "Width") or value == "Width":
            if self.GetDistClass is not None:
               del self.GetDistClass
            self.GetDistClass = QadGetDistClass(self.plugIn)
            prompt = QadMsg.translate("Command_RECTANGLE", "Enter width for rectangle <{0}>: ")
            self.GetDistClass.msg = prompt.format(str(self.dim1))
            self.GetDistClass.dist = self.dim1
            self.step = 9
            self.GetDistClass.run(msgMapTool, msg)

         return False

      # =========================================================================
      # RESPONSE TO THE REQUEST FOR RECTANGLE LENGTH GIVEN THE AREA (from step = 7)
      elif self.step == 8:
         if self.GetDistClass.run(msgMapTool, msg) == True:
            if self.GetDistClass.dist is not None:
               self.polyline.getRectByAreaAndLength(self.firstCorner, self.area, self.GetDistClass.dist, \
                                                    self.rot, self.gapType, self.gapValue1, self.gapValue2)

               if self.virtualCmd == False: # if you really want to save buffers in a layer
                  self.addRectangleToLayer(currLayer)
               return True # end command
         return False

      # =========================================================================
      # RESPONSE TO THE REQUEST FOR RECTANGLE WIDTH GIVEN THE AREA (from step = 7)
      elif self.step == 9:
         if self.GetDistClass.run(msgMapTool, msg) == True:
            if self.GetDistClass.dist is not None:
               self.polyline.getRectByAreaAndWidth(self.firstCorner, self.area, self.GetDistClass.dist, \
                                                   self.rot, self.gapType, self.gapValue1, self.gapValue2)
               if self.virtualCmd == False: # if you really want to save buffers in a layer
                  self.addRectangleToLayer(currLayer)
               return True # end command
         return False

      # =========================================================================
      # RESPONSE TO THE RECTANGLE LENGTH REQUEST (from step = 2)
      elif self.step == 10:
         if self.GetDistClass.run(msgMapTool, msg) == True:
            if self.GetDistClass.dist is not None:
               self.dim1 = self.GetDistClass.dist

            if self.GetDistClass is not None:
               del self.GetDistClass
            self.GetDistClass = QadGetDistClass(self.plugIn)
            prompt = QadMsg.translate("Command_RECTANGLE", "Enter width for rectangle <{0}>: ")
            self.GetDistClass.msg = prompt.format(str(self.dim1))
            self.GetDistClass.dist = self.dim1
            self.step = 11
            self.GetDistClass.run(msgMapTool, msg)

         return False

      # =========================================================================
      # RESPONSE TO THE RECTANGLE WIDTH REQUEST (from step = 10)
      elif self.step == 11:
         if self.GetDistClass.run(msgMapTool, msg) == True:
            if self.GetDistClass.dist is not None:
               self.polyline.getRectByCornerAndDims(self.firstCorner, self.dim1, self.GetDistClass.dist, \
                                                    self.rot, self.gapType, self.gapValue1, self.gapValue2)
               if self.virtualCmd == False: # if you really want to save buffers in a layer
                  self.addRectangleToLayer(currLayer)
               return True # end command
         return False

      # =========================================================================
      # RESPONSE TO THE RECTANGLE ROTATION REQUEST (from step = 2)
      elif self.step == 12: # after waiting for a point the command restarts
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if while selecting a point
            # Another plugin was activated which deactivated Qad
            # so the command that returns here has been reactivated without the map tool
            # has selected a point
            if self.getPointMapTool().point is None: # the map tool was activated without a dot
               if self.getPointMapTool().rightButton == True: # if used with the right mouse button
                  value = self.defaultValue
               else:
                  self.setMapTool(self.getPointMapTool()) # I reactivate the map tool
                  return False
            else:
               value = self.getPointMapTool().point
         else: # the dot comes as a parameter of the function
            value = msg

         if type(value) == unicode:
            if value == QadMsg.translate("Command_RECTANGLE", "Points") or value == "Points":
               # prepares to wait for the rotation angle
               if self.GetAngleClass is not None:
                  del self.GetAngleClass
               self.GetAngleClass = QadGetAngleClass(self.plugIn)
               self.GetAngleClass.msg = QadMsg.translate("Command_RECTANGLE", "Specify first point: ")
               self.GetAngleClass.angle = self.rot
               self.step = 13
               self.GetAngleClass.run(msgMapTool, msg)
         elif type(value) == QgsPointXY:
            self.rot = qad_utils.getAngleBy2Pts(self.firstCorner, value)
            self.WaitForSecondCorner(currLayer)
         elif type(value) == float:
            self.rot = qad_utils.toRadians(value)
            self.WaitForSecondCorner(currLayer)

         return False # continua

      # =========================================================================
      # RESPONSE TO THE RECTANGLE ROTATION REQUEST (from step = 12)
      elif self.step == 13:
         if self.GetAngleClass.run(msgMapTool, msg) == True:
            if self.GetAngleClass.angle is not None:
               self.rot = self.GetAngleClass.angle
               self.plugIn.setLastRot(self.rot)
               self.WaitForSecondCorner(currLayer)
               self.getPointMapTool().refreshSnapType() # update the snapType which can be varied by the rotation map tool
