# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin ok

 MIRROR command to mirror objects

                              -------------------
        begin                : 2013-12-11
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
from qgis.PyQt.QtGui import QIcon
from qgis.core import QgsPointXY, NULL


from .. import qad_label
from .. import qad_layer
from .. import qad_utils
from .qad_mirror_maptool import Qad_mirror_maptool, Qad_mirror_maptool_ModeEnum
from .qad_generic_cmd import QadCommandClass
from ..qad_msg import QadMsg
from ..qad_getpoint import QadGetPointDrawModeEnum
from ..qad_textwindow import QadInputTypeEnum, QadInputModeEnum
from .qad_ssget_cmd import QadSSGetClass
from ..qad_entity import QadEntityTypeEnum, QadCacheEntitySet, QadCacheEntitySetIterator
from ..qad_multi_geom import fromQadGeomToQgsGeom
from ..qad_dim import QadDimStyles, appendDimEntityIfNotExisting, QadDimEntity

# Class that manages the MIRROR command
class QadMIRRORCommandClass(QadCommandClass):

   def instantiateNewCmd(self):
      """instantiates a new command of the same type"""
      return QadMIRRORCommandClass(self.plugIn)

   def getName(self):
      return QadMsg.translate("Command_list", "MIRROR")

   def getEnglishName(self):
      return "MIRROR"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runMIRRORCommand)

   def getIcon(self):
      return QIcon(":/plugins/qad/icons/mirror.svg")

   def getNote(self):
      # set the explanatory notes of the command
      return QadMsg.translate("Command_MIRROR", "Creates a mirrored copy of selected objects.")

   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      self.SSGetClass = QadSSGetClass(plugIn)
      self.SSGetClass.onlyEditableLayers = True
      self.cacheEntitySet = QadCacheEntitySet()
      self.firstMirrorPt = QgsPointXY()
      self.secondMirrorPt = QgsPointXY()
      self.copyFeatures = True

   def __del__(self):
      QadCommandClass.__del__(self)
      del self.SSGetClass


   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      if self.step == 0: # when you are in the entity selection phase
         return self.SSGetClass.getPointMapTool()
      else:
         if (self.plugIn is not None):
            if self.PointMapTool is None:
               self.PointMapTool = Qad_mirror_maptool(self.plugIn)
            return self.PointMapTool
         else:
            return None


   def getCurrentContextualMenu(self):
      if self.step == 0: # when you are in the entity selection phase
         return None # return self.SSGetClass.getCurrentContextualMenu()
      else:
         return self.contextualMenu


   # ============================================================================
   # scale
   # ============================================================================
   def mirror(self, entity, mirrorPt, angle, openForm):

      # check if the entity belongs to a dimensioning style
      if entity.whatIs() == "ENTITY":
         # mirror the geometry of the entity
         qadGeom = entity.getQadGeom().copy() # I copy it
         qadGeom.mirror(mirrorPt, angle)
         f = entity.getFeature()
         f.setGeometry(fromQadGeomToQgsGeom(qadGeom, entity.layer))

         if len(entity.rotFldName) > 0:
            rotValue = f.attribute(entity.rotFldName)
            rotValue = 0 if rotValue is None or rotValue == NULL else qad_utils.toRadians(rotValue) # the rotation is in degrees in the feature field
            ptDummy = qad_utils.getPolarPointByPtAngle(mirrorPt, rotValue, 1)
            ptDummy = qad_utils.mirrorPoint(ptDummy, mirrorPt, angle)
            rotValue = qad_utils.getAngleBy2Pts(mirrorPt, ptDummy)
            f.setAttribute(entity.rotFldName, qad_utils.toDegrees(qad_utils.normalizeAngle(rotValue)))

         if self.copyFeatures == False:
            # plugin, layer, feature, refresh, check_validity
            if qad_layer.updateFeatureToLayer(self.plugIn, entity.layer, f, False, False) == False:
               return False
         else:
            # plugin, layer, features, coordTransform, refresh, check_validity
            if qad_layer.addFeatureToLayer(self.plugIn, entity.layer, f, None, False, False, openForm) == False:
               return False
      else:
         # mirror the share
         if self.copyFeatures == False:
            if entity.deleteToLayers(self.plugIn) == False:
               return False
         newDimEntity = QadDimEntity(entity) # I copy it
         newDimEntity.mirror(mirrorPt, angle)
         if newDimEntity.addToLayers(self.plugIn) == False:
            return False

      return True


   # ============================================================================
   # mirrorGeoms
   # ============================================================================
   def mirrorGeoms(self):
      self.plugIn.beginEditCommand("Feature mirrored", self.cacheEntitySet.getLayerList())

      angle = qad_utils.getAngleBy2Pts(self.firstMirrorPt, self.secondMirrorPt)

      dimElaboratedList = [] # list of dimensions already processed
      openForm = True if self.cacheEntitySet.count() == 1 else False
      entityIterator = QadCacheEntitySetIterator(self.cacheEntitySet)
      for entity in entityIterator:
         qadGeom = entity.getQadGeom() # this is how I initialize the qad info
         # check if the entity belongs to a dimensioning style
         dimEntity = QadDimStyles.getDimEntity(entity)
         if dimEntity is not None:
            if appendDimEntityIfNotExisting(dimElaboratedList, dimEntity) == False: # dimension already processed
               continue
            entity = dimEntity

         if self.mirror(entity, self.firstMirrorPt, angle, openForm) == False:
            self.plugIn.destroyEditCommand()
            return

      self.plugIn.endEditCommand()


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
      # SPECCHIA OGGETTI
      elif self.step == 1:
         if self.SSGetClass.entitySet.count() == 0:
            return True # end command
         self.cacheEntitySet.appendEntitySet(self.SSGetClass.entitySet)

         # set the map tool
         self.getPointMapTool().cacheEntitySet = self.cacheEntitySet
         self.getPointMapTool().setMode(Qad_mirror_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_FIRST_PT)

         # is preparing to wait for a point
         self.waitForPoint(QadMsg.translate("Command_MIRROR", "Specify first point of mirror line: "), None, QadInputModeEnum.NOT_NULL)
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
                  # is preparing to wait for a point
                  self.waitForPoint(QadMsg.translate("Command_MIRROR", "Specify first point of mirror line: "), None, QadInputModeEnum.NOT_NULL)
                  return False
               else:
                  self.setMapTool(self.getPointMapTool()) # I reactivate the map tool
                  return False

            value = self.getPointMapTool().point
         else: # the dot comes as a parameter of the function
            value = msg

         self.firstMirrorPt.set(value.x(), value.y())

         # set the map tool
         self.getPointMapTool().firstMirrorPt = self.firstMirrorPt
         self.getPointMapTool().setMode(Qad_mirror_maptool_ModeEnum.FIRST_PT_KNOWN_ASK_FOR_SECOND_PT)

         # is preparing to wait for a point
         self.waitForPoint(QadMsg.translate("Command_MIRROR", "Specify second point of mirror line: "), None, QadInputModeEnum.NOT_NULL)
         self.step = 3

         return False

      # =========================================================================
      # RESPONSE TO THE SECOND POINT REQUEST FOR MIRROR (from step = 2)
      elif self.step == 3: # after waiting for a point the command restarts
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if while selecting a point
            # Another plugin was activated which deactivated Qad
            # so the command that returns here has been reactivated without the map tool
            # has selected a point
            if self.getPointMapTool().point is None: # the map tool was activated without a dot
               if self.getPointMapTool().rightButton == True: # if used with the right mouse button
                  # is preparing to wait for a point
                  self.waitForPoint(QadMsg.translate("Command_MIRROR", "Specify second point of mirror line: "), None, QadInputModeEnum.NOT_NULL)
               else:
                  self.setMapTool(self.getPointMapTool()) # I reactivate the map tool
                  return False

            value = self.getPointMapTool().point
         else: # the dot comes as a parameter of the function
            value = msg

         if qad_utils.ptNear(self.firstMirrorPt, value):
            self.showMsg(QadMsg.translate("Command_MIRROR", "\nThe points must be different."))
            # is preparing to wait for a point
            self.waitForPoint(QadMsg.translate("Command_MIRROR", "Specify second point of mirror line: "), None, QadInputModeEnum.NOT_NULL)
            return False

         self.secondMirrorPt.set(value.x(), value.y())

         keyWords = QadMsg.translate("QAD", "Yes") + "/" + \
                    QadMsg.translate("QAD", "No")
         if self.copyFeatures == False:
            default = QadMsg.translate("QAD", "Yes")
         else:
            default = QadMsg.translate("QAD", "No")
         prompt = QadMsg.translate("Command_MIRROR", "Erase source objects ? [{0}] <{1}>: ").format(keyWords, default)

         englishKeyWords = "Yes" + "/" + "No"
         keyWords += "_" + englishKeyWords
         # is preparing to wait for enter or a keyword
         # msg, inputType, default, keyWords, no check
         self.waitFor(prompt, \
                      QadInputTypeEnum.KEYWORDS, \
                      default, \
                      keyWords, QadInputModeEnum.NONE)
         self.getPointMapTool().setMode(Qad_mirror_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_FIRST_PT)
         self.step = 4

         return False


      # =========================================================================
      # RESPONSE TO THE SOURCE OBJECT DELETE REQUEST (from step = 3)
      elif self.step == 4: # after waiting for a point or a real number the command is restarted
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if while selecting a point
            # Another plugin was activated which deactivated Qad
            # so the command that returns here has been reactivated without the map tool
            # has selected a point
            if self.getPointMapTool().rightButton == True: # if used with the right mouse button
               value = QadMsg.translate("QAD", "No")
            else:
               self.setMapTool(self.getPointMapTool()) # I reactivate the map tool
               return False
         else: # the value comes as a function parameter
            value = msg

         if type(value) == unicode:
            if value == QadMsg.translate("QAD", "Yes") or value == "Yes":
               self.copyFeatures = False
            elif value == QadMsg.translate("QAD", "No") or value == "No":
               self.copyFeatures = True

            self.mirrorGeoms()
            return True # end command

         return False




# Class that manages the MIRROR command for grips
class QadGRIPMIRRORCommandClass(QadCommandClass):

   def instantiateNewCmd(self):
      """instantiates a new command of the same type"""
      return QadMIRRORCommandClass(self.plugIn)


   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      self.cacheEntitySet = QadCacheEntitySet()
      self.basePt = QgsPointXY()
      self.secondMirrorPt = QgsPointXY()
      self.skipToNextGripCommand = False
      self.copyEntities = False
      self.nOperationsToUndo = 0

   def __del__(self):
      QadCommandClass.__del__(self)


   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      if (self.plugIn is not None):
         if self.PointMapTool is None:
            self.PointMapTool = Qad_mirror_maptool(self.plugIn)
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
   # mirror
   # ============================================================================
   def mirror(self, entity, mirrorPt, angle):
      # entity = entity to mirror
      # pt1 and pt2 = line of symmetry
      # rotFldName = table field that stores the rotation
      # check if the entity belongs to a dimensioning style
      if entity.whatIs() == "ENTITY":
         # mirror the geometry of the entity
         qadGeom = entity.getQadGeom().copy() # I copy it
         qadGeom.mirror(mirrorPt, angle)
         f = entity.getFeature()
         f.setGeometry(fromQadGeomToQgsGeom(qadGeom, entity.layer))

         if len(entity.rotFldName) > 0:
            rotValue = f.attribute(entity.rotFldName)
            rotValue = 0 if rotValue is None or rotValue == NULL else qad_utils.toRadians(rotValue) # the rotation is in degrees in the feature field
            ptDummy = qad_utils.getPolarPointByPtAngle(mirrorPt, rotValue, 1)
            ptDummy = qad_utils.mirrorPoint(ptDummy, mirrorPt, angle)
            rotValue = qad_utils.getAngleBy2Pts(mirrorPt, ptDummy)
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
         # mirror the share
         if self.copyEntities == False:
            if entity.deleteToLayers(self.plugIn) == False:
               return False
         newDimEntity = QadDimEntity(entity) # I copy it
         newDimEntity.mirror(mirrorPt, angle)
         if newDimEntity.addToLayers(self.plugIn) == False:
            return False

      return True


   # ============================================================================
   # mirrorGeoms
   # ============================================================================
   def mirrorGeoms(self):
      self.plugIn.beginEditCommand("Feature mirrored", self.cacheEntitySet.getLayerList())

      angle = qad_utils.getAngleBy2Pts(self.firstMirrorPt, self.secondMirrorPt)

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

         if self.mirror(entity, self.firstMirrorPt, angle, openForm) == False:
            self.plugIn.destroyEditCommand()
            return


      self.plugIn.endEditCommand()
      self.nOperationsToUndo = self.nOperationsToUndo + 1


   # ============================================================================
   # waitForMirrorPoint
   # ============================================================================
   def waitForMirrorPoint(self):
      self.step = 1
      self.plugIn.setLastPoint(self.basePt)
      # set the map tool
      self.getPointMapTool().firstMirrorPt = self.basePt
      self.getPointMapTool().setMode(Qad_mirror_maptool_ModeEnum.FIRST_PT_KNOWN_ASK_FOR_SECOND_PT)

      keyWords = QadMsg.translate("Command_GRIPMIRROR", "Base point") + "/" + \
                 QadMsg.translate("Command_GRIPMIRROR", "Copy") + "/" + \
                 QadMsg.translate("Command_GRIPMIRROR", "Undo") + "/" + \
                 QadMsg.translate("Command_GRIPMIRROR", "eXit")

      prompt = QadMsg.translate("Command_GRIPMIRROR", "Specify second point or [{0}]: ").format(keyWords)

      englishKeyWords = "Base point" + "/" + "Copy" + "/" + "Undo" + "/" + "eXit"
      keyWords += "_" + englishKeyWords
      # is preparing to wait for a point, a real number or enter or a keyword
      # msg, inputType, default, keyWords, no check
      self.waitFor(prompt, QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                   None, \
                   keyWords, QadInputModeEnum.NONE)


   # ============================================================================
   # waitForBasePt
   # ============================================================================
   def waitForBasePt(self):
      self.step = 2
      # set the map tool
      self.getPointMapTool().setMode(Qad_mirror_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_FIRST_PT)
      # is preparing to wait for a point
      self.waitForPoint(QadMsg.translate("Command_GRIPROTATE", "Specify base point: "))


   def run(self, msgMapTool = False, msg = None):
      if self.plugIn.canvas.mapSettings().destinationCrs().isGeographic():
         self.showMsg(QadMsg.translate("QAD", "\nThe coordinate reference system of the project must be a projected coordinate system.\n"))
         return True # end command

      # =========================================================================
      # OBJECT SELECTION REQUEST
      if self.step == 0: # start of command
         if self.cacheEntitySet.isEmpty(): # there are no objects to rotate
            return True
         self.showMsg(QadMsg.translate("Command_GRIPMIRROR", "\n** MIRROR **\n"))
         # is preparing to wait for the second mirror point
         self.waitForMirrorPoint()

      # =========================================================================
      # RESPONSE TO THE SECOND POINT REQUEST FOR MIRROR
      elif self.step == 1: # after waiting for a point the command restarts
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

            ctrlKey = self.getPointMapTool().ctrlKey
            value = self.getPointMapTool().point
         else: # the dot comes as a parameter of the function
            value = msg

         if type(value) == unicode:
            if value == QadMsg.translate("Command_GRIPMIRROR", "Base point") or value == "Base point":
               # is preparing to wait for the base point
               self.waitForBasePt()
            elif value == QadMsg.translate("Command_GRIPMIRROR", "Copy") or value == "Copy":
               # Copy entities leaving the originals unchanged
               self.copyEntities = True
               # is preparing to wait for the second mirror point
               self.waitForMirrorPoint()
            elif value == QadMsg.translate("Command_GRIPMIRROR", "Undo") or value == "Undo":
               if self.nOperationsToUndo > 0:
                  self.nOperationsToUndo = self.nOperationsToUndo - 1
                  self.plugIn.undoEditCommand()
               else:
                  self.showMsg(QadMsg.translate("QAD", "\nThe command has been canceled."))
               # is preparing to wait for the second mirror point
               self.waitForMirrorPoint()
            elif value == QadMsg.translate("Command_GRIPMIRROR", "eXit") or value == "eXit":
               return True # end command
         elif type(value) == QgsPointXY: # if the second point has been inserted
            if qad_utils.ptNear(self.basePt, value):
               self.showMsg(QadMsg.translate("Command_GRIPMIRROR", "\nThe points must be different."))
               # is preparing to wait for the second mirror point
               self.waitForMirrorPoint()
               return False

            self.secondMirrorPt.set(value.x(), value.y())

            if ctrlKey:
               self.copyEntities = True

            self.mirrorGeoms()

            if self.copyEntities == False:
               return True

            # is preparing to wait for the second mirror point
            self.waitForMirrorPoint()

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

         # is preparing to wait for the second mirror point
         self.waitForMirrorPoint()

         return False
