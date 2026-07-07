# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin ok

 ROTATE command to rotate objects

                              -------------------
        begin                : 2013-09-27
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
from qgis.core import QgsPointXY, NULL
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtGui import QIcon


from .qad_rotate_maptool import Qad_rotate_maptool_ModeEnum, Qad_rotate_maptool
from .qad_generic_cmd import QadCommandClass
from ..qad_msg import QadMsg
from ..qad_getpoint import QadGetPointDrawModeEnum
from ..qad_textwindow import QadInputTypeEnum, QadInputModeEnum
from .qad_ssget_cmd import QadSSGetClass
from ..qad_entity import QadCacheEntitySet, QadCacheEntitySetIterator, QadEntityTypeEnum
from .. import qad_utils
from .. import qad_layer
from .. import qad_label
from ..qad_dim import QadDimStyles, QadDimEntity, appendDimEntityIfNotExisting
from ..qad_multi_geom import fromQadGeomToQgsGeom


# Class that manages the ROTATE command
class QadROTATECommandClass(QadCommandClass):

   def instantiateNewCmd(self):
      """instantiates a new command of the same type"""
      return QadROTATECommandClass(self.plugIn)

   def getName(self):
      return QadMsg.translate("Command_list", "ROTATE")

   def getEnglishName(self):
      return "ROTATE"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runROTATECommand)

   def getIcon(self):
      return QIcon(":/plugins/qad/icons/rotate.svg")

   def getNote(self):
      # set the explanatory notes of the command
      return QadMsg.translate("Command_ROTATE", "Rotates objects around a base point.")

   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      self.SSGetClass = QadSSGetClass(plugIn)
      self.SSGetClass.onlyEditableLayers = True
      self.cacheEntitySet = QadCacheEntitySet()
      self.basePt = None
      self.copyFeatures = False
      self.Pt1ReferenceAng = None
      self.ReferenceAng = 0
      self.Pt1NewAng = None

   def __del__(self):
      QadCommandClass.__del__(self)
      del self.SSGetClass


   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      if self.step == 0: # when you are in the entity selection phase
         return self.SSGetClass.getPointMapTool()
      else:
         if (self.plugIn is not None):
            if self.PointMapTool is None:
               self.PointMapTool = Qad_rotate_maptool(self.plugIn)
            return self.PointMapTool
         else:
            return None


   def getCurrentContextualMenu(self):
      if self.step == 0: # when you are in the entity selection phase
         return None # return self.SSGetClass.getCurrentContextualMenu()
      else:
         return self.contextualMenu


   # ============================================================================
   # rotate
   # ============================================================================
   def rotate(self, entity, basePt, angle, openForm):
      # check if the entity belongs to a dimensioning style
      if entity.whatIs() == "ENTITY":
         # rotate the geometry of the entity
         qadGeom = entity.getQadGeom().copy() # I copy it
         qadGeom.rotate(basePt, angle)
         f = entity.getFeature()
         f.setGeometry(fromQadGeomToQgsGeom(qadGeom, entity.layer))

         if len(entity.rotFldName) > 0:
            rotValue = f.attribute(entity.rotFldName)
            rotValue = 0 if rotValue is None or rotValue == NULL else qad_utils.toRadians(rotValue) # the rotation is in degrees in the feature field
            rotValue = rotValue + angle
            f.setAttribute(entity.rotFldName, qad_utils.toDegrees(qad_utils.normalizeAngle(rotValue)))

         if self.copyFeatures == False:
            # plugin, layer, feature, refresh, check_validity
            if qad_layer.updateFeatureToLayer(self.plugIn, entity.layer, f, False, False) == False:
               return False
         else:
            # plugin, layer, features, coordTransform, refresh, check_validity
            if qad_layer.addFeatureToLayer(self.plugIn, entity.layer, f, None, False, False, openForm) == False:
               return False
      elif entity.whatIs() == "DIMENTITY":
         newDimEntity = QadDimEntity(entity) # I copy it
         # rotate the dimension
         if self.copyFeatures == False:
            if dimEntity.deleteToLayers(self.plugIn) == False:
               return False
         newDimEntity.rotate(basePt, angle)
         if newDimEntity.addToLayers(self.plugIn) == False:
            return False

      return True


   def RotateGeoms(self, angle):
      self.plugIn.beginEditCommand("Feature rotated", self.cacheEntitySet.getLayerList())

      dimElaboratedList = [] # list of dimensions already processed
      entityIterator = QadCacheEntitySetIterator(self.cacheEntitySet)
      openForm = True if self.cacheEntitySet.count() == 1 else False

      for entity in entityIterator:
         qadGeom = entity.getQadGeom() # this is how I initialize the qad info
         # check if the entity belongs to a dimensioning style
         dimEntity = QadDimStyles.getDimEntity(entity)
         if dimEntity is not None:
            if appendDimEntityIfNotExisting(dimElaboratedList, dimEntity) == False: # dimension already processed
               continue
            entity = dimEntity

         if self.rotate(entity, self.basePt, angle, openForm) == False:
            self.plugIn.destroyEditCommand()
            return

      self.plugIn.endEditCommand()


   def waitForRotation(self):
      # set the map tool
      self.getPointMapTool().setMode(Qad_rotate_maptool_ModeEnum.BASE_PT_KNOWN_ASK_FOR_ROTATION_PT)

      keyWords = QadMsg.translate("Command_ROTATE", "Copy") + "/" + \
                 QadMsg.translate("Command_ROTATE", "Reference")
      prompt = QadMsg.translate("Command_ROTATE", "Specify rotation angle or [{0}] <{1}>: ").format(keyWords, \
               str(qad_utils.toDegrees(self.plugIn.lastRot)))

      englishKeyWords = "Copy" + "/" + "Reference"
      keyWords += "_" + englishKeyWords
      # is preparing to wait for a point, a real number or enter or a keyword
      # msg, inputType, default, keyWords, no check
      self.waitFor(prompt, QadInputTypeEnum.POINT2D | QadInputTypeEnum.ANGLE | QadInputTypeEnum.KEYWORDS, \
                   self.plugIn.lastRot, \
                   keyWords, QadInputModeEnum.NONE)

      self.step = 3


   def waitForReferenceRot(self):
      # set the map tool
      self.getPointMapTool().setMode(Qad_rotate_maptool_ModeEnum.ASK_FOR_FIRST_PT_REFERENCE_ANG)

      msg = QadMsg.translate("Command_ROTATE", "Specify reference angle <{0}>: ")
      # is preparing to wait for a point or Enter or a keyword
      # msg, inputType, default, keyWords, no check
      self.waitFor(msg.format(str(qad_utils.toDegrees(self.plugIn.lastReferenceRot))), \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.ANGLE, \
                   self.plugIn.lastReferenceRot, \
                   "")
      self.step = 4


   def waitForNewReferenceRot(self):
      # set the map tool
      self.getPointMapTool().setMode(Qad_rotate_maptool_ModeEnum.BASE_PT_KNOWN_ASK_FOR_NEW_ROTATION_PT)

      keyWords = QadMsg.translate("Command_ROTATE", "Points")
      if self.plugIn.lastNewReferenceRot == 0:
         angle = self.plugIn.lastRot
      else:
         angle = self.plugIn.lastNewReferenceRot
      prompt = QadMsg.translate("Command_ROTATE", "Specify new angle or [{0}] <{1}>: ").format(keyWords, str(qad_utils.toDegrees(angle)))

      englishKeyWords = "Points"
      keyWords += "_" + englishKeyWords
      # is preparing to wait for a point or Enter or a keyword
      # msg, inputType, default, keyWords, no check
      self.waitFor(prompt, \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.ANGLE | QadInputTypeEnum.KEYWORDS, \
                   angle, \
                   keyWords)
      self.step = 6


   def run(self, msgMapTool = False, msg = None):
      if self.plugIn.canvas.mapSettings().destinationCrs().isGeographic():
         self.showMsg(QadMsg.translate("QAD", "\nThe coordinate reference system of the project must be a projected coordinate system.\n"))
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
      # RUOTA OGGETTI
      elif self.step == 1:
         if self.SSGetClass.entitySet.count() == 0:
            return True # end command
         self.cacheEntitySet.appendEntitySet(self.SSGetClass.entitySet)

         # set the map tool
         self.getPointMapTool().setMode(Qad_rotate_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_BASE_PT)

         # is preparing to wait for a point
         self.waitForPoint(QadMsg.translate("Command_ROTATE", "Specify base point: "))

         self.step = 2
         return False

      # =========================================================================
      # RESPONSE TO THE BASE POINT REQUEST (from step = 1)
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

         self.basePt = QgsPointXY(value)

         self.getPointMapTool().basePt = self.basePt
         self.getPointMapTool().cacheEntitySet = self.cacheEntitySet
         # prepares to wait for the rotation angle
         self.waitForRotation()

         return False

      # =========================================================================
      # RESPONSE TO THE SECOND POINT REQUEST FOR ROTATION ANGLE (from step = 2)
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

         if type(value) == unicode:
            if value == QadMsg.translate("Command_ROTATE", "Copy") or value == "Copy":
               self.copyFeatures = True
               self.showMsg(QadMsg.translate("Command_ROTATE", "\nRotation of a copy of the selected objects."))
               # prepares to wait for the rotation angle
               self.waitForRotation()
            elif value == QadMsg.translate("Command_ROTATE", "Reference") or value == "Reference":
               # is preparing to wait for the reference angle
               self.waitForReferenceRot()
         elif type(value) == QgsPointXY or type(value) == float: # if the rotation angle has been entered
            if type(value) == QgsPointXY: # if the rotation angle has been entered with a dot
               angle = qad_utils.getAngleBy2Pts(self.basePt, value)
            else:
               angle = qad_utils.toRadians(value)
            self.plugIn.setLastRot(angle)

            self.RotateGeoms(angle)
            return True # end command

         return False

      # =========================================================================
      # RESPONSE TO THE FIRST POINT REQUEST FOR REFERENCE ROTATION ANGLE (from step = 3)
      elif self.step == 4: # after waiting for a point or a real number the command is restarted
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

         if type(value) == float: # if the rotation angle has been entered
            self.ReferenceAng = qad_utils.toRadians(value)
            self.getPointMapTool().ReferenceAng = self.ReferenceAng
            # is preparing to wait for the new corner
            self.waitForNewReferenceRot()

         elif type(value) == QgsPointXY: # if the rotation angle has been entered with a dot
            self.Pt1ReferenceAng = QgsPointXY(value)
            self.getPointMapTool().Pt1ReferenceAng = self.Pt1ReferenceAng
            # set the map tool
            self.getPointMapTool().setMode(Qad_rotate_maptool_ModeEnum.FIRST_PT_KNOWN_ASK_FOR_SECOND_PT_REFERENCE_ANG)
            # is preparing to wait for a point
            self.waitForPoint(QadMsg.translate("Command_ROTATE", "Specify second point: "))
            self.step = 5

         return False

      # =========================================================================
      # RESPONSE TO THE SECOND POINT REQUEST FOR REFERENCE ROTATION ANGLE (from step = 4)
      elif self.step == 5: # after waiting for a point or a real number the command is restarted
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

         angle = qad_utils.getAngleBy2Pts(self.Pt1ReferenceAng, value)
         self.ReferenceAng = angle
         self.getPointMapTool().ReferenceAng = self.ReferenceAng
         # is preparing to wait for the new corner
         self.waitForNewReferenceRot()

         return False

      # =========================================================================
      # RESPONSE TO THE SECOND POINT REQUEST FOR NEW ROTATION ANGLE (from step = 4 and 5)
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

         if type(value) == unicode:
            if value == QadMsg.translate("Command_ROTATE", "Points") or value == "Points":
               # set the map tool
               self.getPointMapTool().setMode(Qad_rotate_maptool_ModeEnum.ASK_FOR_FIRST_NEW_ROTATION_PT)
               # is preparing to wait for a point
               self.waitForPoint(QadMsg.translate("Command_ROTATE", "Specify first point: "))
               self.step = 7
         elif type(value) == QgsPointXY or type(value) == float: # if the rotation angle has been entered
            if type(value) == QgsPointXY: # if the rotation angle has been entered with a dot
               angle = qad_utils.getAngleBy2Pts(self.basePt, value)
            else:
               angle = qad_utils.toRadians(value)

            angle = angle - self.ReferenceAng
            self.plugIn.setLastRot(angle)
            self.RotateGeoms(angle)
            return True # end command

         return False

      # =========================================================================
      # RESPONSE TO THE FIRST POINT REQUEST FOR NEW ROTATION ANGLE (from step = 6)
      elif self.step == 7: # after waiting for a point or a real number the command is restarted
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

         self.Pt1NewAng = value
         # set the map tool
         self.getPointMapTool().Pt1NewAng = self.Pt1NewAng
         self.getPointMapTool().setMode(Qad_rotate_maptool_ModeEnum.FIRST_PT_KNOWN_ASK_FOR_SECOND_NEW_ROTATION_PT)
         # is preparing to wait for a point
         self.waitForPoint(QadMsg.translate("Command_ROTATE", "Specify second point: "))
         self.step = 8

         return False

      # =========================================================================
      # RESPONSE TO THE SECOND POINT REQUEST FOR NEW ROTATION ANGLE (from step = 7)
      elif self.step == 8: # after waiting for a point or a real number the command is restarted
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

         angle = qad_utils.getAngleBy2Pts(self.Pt1NewAng, value)

         angle = angle - self.ReferenceAng
         self.plugIn.setLastRot(angle)
         self.RotateGeoms(angle)
         return True # end command


# Class that manages the ROTATE command for grips
class QadGRIPROTATECommandClass(QadCommandClass):


   def instantiateNewCmd(self):
      """instantiates a new command of the same type"""
      return QadGRIPROTATECommandClass(self.plugIn)


   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      self.cacheEntitySet = QadCacheEntitySet()
      self.basePt = QgsPointXY()
      self.skipToNextGripCommand = False
      self.copyEntities = False
      self.nOperationsToUndo = 0
      self.Pt1ReferenceAng = None
      self.ReferenceAng = 0


   def __del__(self):
      QadCommandClass.__del__(self)


   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      if (self.plugIn is not None):
         if self.PointMapTool is None:
            self.PointMapTool = Qad_rotate_maptool(self.plugIn)
         return self.PointMapTool
      else:
         return None


   # ============================================================================
   # setSelectedEntityGripPoints
   # ============================================================================
   def setSelectedEntityGripPoints(self, entitySetGripPoints):
      # list of entityGripPoints with selected grip points
      self.cacheEntitySet.clear()

      for entityGripPoints in entitySetGripPoints.entityGripPoints:
         self.cacheEntitySet.appendEntity(entityGripPoints.entity)

      self.getPointMapTool().cacheEntitySet = self.cacheEntitySet


   # ============================================================================
   # rotate
   # ============================================================================
   def rotate(self, entity, basePt, angle, rotFldName):
      # entity = entity to rotate
      # basePt = base point
      # angle = rotation angle in degrees
      # check if the entity belongs to a dimensioning style
      if entity.whatIs() == "ENTITY":
         # rotate the geometry of the entity
         qadGeom = entity.getQadGeom().copy() # I copy it
         qadGeom.rotate(basePt, angle)
         f = entity.getFeature()
         f.setGeometry(fromQadGeomToQgsGeom(qadGeom, entity.layer))

         if len(entity.rotFldName) > 0:
            rotValue = f.attribute(entity.rotFldName)
            rotValue = 0 if rotValue is None or rotValue == NULL else qad_utils.toRadians(rotValue) # the rotation is in degrees in the feature field
            rotValue = rotValue + angle
            f.setAttribute(entity.rotFldName, qad_utils.toDegrees(qad_utils.normalizeAngle(rotValue)))

         if self.copyEntities == False:
            # plugin, layer, feature, refresh, check_validity
            if qad_layer.updateFeatureToLayer(self.plugIn, entity.layer, f, False, False) == False:
               return False
         else:
            # plugin, layer, features, coordTransform, refresh, check_validity
            if qad_layer.addFeatureToLayer(self.plugIn, entity.layer, f, None, False, False) == False:
               return False

      elif entity.whatIs() == "DIMENTITY":
         # stretch the dimension
         if self.copyEntities == False:
            if entity.deleteToLayers(self.plugIn) == False:
               return False
         newDimEntity = QadDimEntity(entity) # I copy it
         newDimEntity.rotate(basePt, angle)
         if newDimEntity.addToLayers(self.plugIn) == False:
            return False

      return True


   # ============================================================================
   # rotateFeatures
   # ============================================================================
   def rotateFeatures(self, angle):
      self.plugIn.beginEditCommand("Feature rotated", self.cacheEntitySet.getLayerList())

      entityIterator = QadCacheEntitySetIterator(self.cacheEntitySet)
      for entity in entityIterator:
         qadGeom = entity.getQadGeom() # this is how I initialize the qad info
         # check if the entity belongs to a dimensioning style
         dimEntity = QadDimStyles.getDimEntity(entity)
         if dimEntity is not None:
            if appendDimEntityIfNotExisting(dimElaboratedList, dimEntity) == False: # dimension already processed
               continue
            entity = dimEntity

         if self.rotate(entity, self.basePt, angle) == False:
            self.plugIn.destroyEditCommand()
            return

      self.plugIn.endEditCommand()
      self.nOperationsToUndo = self.nOperationsToUndo + 1


   # ============================================================================
   # waitForRotatePoint
   # ============================================================================
   def waitForRotatePoint(self):
      self.step = 1
      self.plugIn.setLastPoint(self.basePt)
      # set the map tool
      self.getPointMapTool().basePt = self.basePt
      self.getPointMapTool().setMode(Qad_rotate_maptool_ModeEnum.BASE_PT_KNOWN_ASK_FOR_NEW_ROTATION_PT)

      keyWords = QadMsg.translate("Command_GRIPROTATE", "Base point") + "/" + \
                 QadMsg.translate("Command_GRIPROTATE", "Copy") + "/" + \
                 QadMsg.translate("Command_GRIPROTATE", "Undo") + "/" + \
                 QadMsg.translate("Command_GRIPROTATE", "Reference") + "/" + \
                 QadMsg.translate("Command_GRIPROTATE", "eXit")

      prompt = QadMsg.translate("Command_GRIPROTATE", "Specify rotation angle or [{0}]: ").format(keyWords)

      englishKeyWords = "Base point" + "/" + "Copy" + "/" + "Undo" + "/" + "Reference" + "/" + "eXit"
      keyWords += "_" + englishKeyWords
      # is preparing to wait for a point, a real number or enter or a keyword
      # msg, inputType, default, keyWords, no check
      self.waitFor(prompt, QadInputTypeEnum.POINT2D | QadInputTypeEnum.ANGLE | QadInputTypeEnum.KEYWORDS, \
                   None, \
                   keyWords, QadInputModeEnum.NONE)


   # ============================================================================
   # waitForBasePt
   # ============================================================================
   def waitForBasePt(self):
      self.step = 2
      # set the map tool
      self.getPointMapTool().setMode(Qad_rotate_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_BASE_PT)

      # is preparing to wait for a point
      self.waitForPoint(QadMsg.translate("Command_GRIPROTATE", "Specify base point: "))


   def waitForReferenceRot(self):
      # set the map tool
      self.getPointMapTool().setMode(Qad_rotate_maptool_ModeEnum.ASK_FOR_FIRST_PT_REFERENCE_ANG)

      msg = QadMsg.translate("Command_GRIPROTATE", "Specify reference angle <{0}>: ")
      # is preparing to wait for a point or Enter or a keyword
      # msg, inputType, default, keyWords, no check
      self.waitFor(msg.format(str(qad_utils.toDegrees(self.plugIn.lastReferenceRot))), \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.ANGLE, \
                   self.plugIn.lastReferenceRot, \
                   "")
      self.step = 3


   # ============================================================================
   # run
   # ============================================================================
   def run(self, msgMapTool = False, msg = None):
      if self.plugIn.canvas.mapSettings().destinationCrs().isGeographic():
         self.showMsg(QadMsg.translate("QAD", "\nThe coordinate reference system of the project must be a projected coordinate system.\n"))
         return True # end command

      # =========================================================================
      # OBJECT SELECTION REQUEST
      if self.step == 0: # start of command
         if self.cacheEntitySet.isEmpty(): # there are no objects to rotate
            return True
         self.showMsg(QadMsg.translate("Command_GRIPROTATE", "\n** ROTATE **\n"))
         # is preparing to wait for a rotation point
         self.waitForRotatePoint()
         return False

      # =========================================================================
      # RESPONSE TO THE REQUEST FOR A ROTATION POINT
      elif self.step == 1:
         ctrlKey = False
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if while selecting a point
            # Another plugin was activated which deactivated Qad
            # so the command that returns here has been reactivated without the map tool
            # has selected a point
            if self.getPointMapTool().point is None: # the map tool was activated without a dot
               if self.getPointMapTool().rightButton == True: # if used with the right mouse button
                  value = None
               else:
                  self.setMapTool(self.getPointMapTool()) # I reactivate the map tool
                  return False
            else:
               value = self.getPointMapTool().point

            ctrlKey = self.getPointMapTool().ctrlKey
         else: # the dot comes as a parameter of the function
            value = msg

         if type(value) == unicode:
            if value == QadMsg.translate("Command_GRIPROTATE", "Base point") or value == "Base point":
               # is preparing to wait for the base point
               self.waitForBasePt()
            elif value == QadMsg.translate("Command_GRIPROTATE", "Copy") or value == "Copy":
               # Copy entities leaving the originals unchanged
               self.copyEntities = True
               # is preparing to wait for a rotation point
               self.waitForRotatePoint()
            elif value == QadMsg.translate("Command_GRIPROTATE", "Undo") or value == "Undo":
               if self.nOperationsToUndo > 0:
                  self.nOperationsToUndo = self.nOperationsToUndo - 1
                  self.plugIn.undoEditCommand()
               else:
                  self.showMsg(QadMsg.translate("QAD", "\nThe command has been canceled."))
               # is preparing to wait for a rotation point
               self.waitForRotatePoint()
            elif value == QadMsg.translate("Command_GRIPROTATE", "Reference") or value == "Reference":
               # is preparing to wait for the reference angle
               self.waitForReferenceRot()
            elif value == QadMsg.translate("Command_GRIPROTATE", "eXit") or value == "eXit":
               return True # end command
         elif type(value) == QgsPointXY or type(value) == float: # if the rotation angle has been entered
            if type(value) == QgsPointXY: # if the rotation angle has been entered with a dot
               angle = qad_utils.getAngleBy2Pts(self.basePt, value)
            else:
               angle = qad_utils.toRadians(value)
            angle = angle - self.ReferenceAng
            self.plugIn.setLastRot(angle)

            if ctrlKey:
               self.copyEntities = True

            self.rotateFeatures(angle)

            if self.copyEntities == False:
               return True

            # is preparing to wait for a rotation point
            self.waitForRotatePoint()

         else:
            if self.copyEntities == False:
               self.skipToNextGripCommand = True
            return True # end command

         return False


      # =========================================================================
      # RESPONSE TO THE BASE POINT REQUEST (from step = 1)
      elif self.step == 2: # after waiting for a point
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if while selecting a point
            # Another plugin was activated which deactivated Qad
            # so the command that returns here has been reactivated without the map tool
            # has selected a point
            if self.getPointMapTool().point is None: # the map tool was activated without a dot
               if self.getPointMapTool().rightButton == True: # if used with the right mouse button
                  pass # opzione di default "spostamento"
               else:
                  self.setMapTool(self.getPointMapTool()) # I reactivate the map tool
                  return False

            value = self.getPointMapTool().point
         else: # the dot comes as a parameter of the function
            value = msg

         if type(value) == QgsPointXY: # if the base point has been entered
            self.basePt.set(value.x(), value.y())
            # set the map tool
            self.getPointMapTool().basePt = self.basePt

         # is preparing to wait for a rotation point
         self.waitForRotatePoint()

         return False


      # =========================================================================
      # RESPONSE TO THE FIRST POINT REQUEST FOR REFERENCE ROTATION ANGLE (from step = 1)
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

         if type(value) == float: # if the rotation angle has been entered
            self.ReferenceAng = qad_utils.toRadians(value)
            self.getPointMapTool().ReferenceAng = self.ReferenceAng
            # is preparing to wait for a rotation point
            self.waitForRotatePoint()

         elif type(value) == QgsPointXY: # if the rotation angle has been entered with a dot
            self.Pt1ReferenceAng = QgsPointXY(value)
            self.getPointMapTool().Pt1ReferenceAng = self.Pt1ReferenceAng
            # set the map tool
            self.getPointMapTool().setMode(Qad_rotate_maptool_ModeEnum.FIRST_PT_KNOWN_ASK_FOR_SECOND_PT_REFERENCE_ANG)
            # is preparing to wait for a point
            self.waitForPoint(QadMsg.translate("Command_GRIPROTATE", "Specify second point: "))
            self.step = 4

         return False

      # =========================================================================
      # RESPONSE TO THE SECOND POINT REQUEST FOR NEW ROTATION ANGLE (from step = 3)
      elif self.step == 4: # after waiting for a point or a real number the command is restarted
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

         if type(value) == QgsPointXY or type(value) == float: # if the rotation angle has been entered
            if type(value) == QgsPointXY: # if the rotation angle has been entered with a dot
               self.ReferenceAng = qad_utils.getAngleBy2Pts(self.Pt1ReferenceAng, value)
            else:
               self.ReferenceAng = qad_utils.toRadians(value)
            self.getPointMapTool().ReferenceAng = self.ReferenceAng

         # is preparing to wait for a rotation point
         self.waitForRotatePoint()

         return False

