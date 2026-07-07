# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin ok

 MOVE command to move objects

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
from qgis.PyQt.QtGui import QIcon
from qgis.core import QgsPointXY


from .qad_move_maptool import Qad_move_maptool_ModeEnum, Qad_move_maptool
from .qad_generic_cmd import QadCommandClass
from ..qad_msg import QadMsg
from ..qad_getpoint import QadGetPointDrawModeEnum
from ..qad_textwindow import QadInputTypeEnum, QadInputModeEnum
from .qad_ssget_cmd import QadSSGetClass
from ..qad_entity import QadCacheEntitySet, QadEntityTypeEnum, QadCacheEntitySetIterator

from .. import qad_utils
from .. import qad_layer
from ..qad_dim import QadDimStyles, QadDimEntity, appendDimEntityIfNotExisting
from ..qad_multi_geom import fromQadGeomToQgsGeom

# Class that manages the MOVE command
class QadMOVECommandClass(QadCommandClass):

   def instantiateNewCmd(self):
      """instantiates a new command of the same type"""
      return QadMOVECommandClass(self.plugIn)

   def getName(self):
      return QadMsg.translate("Command_list", "MOVE")

   def getEnglishName(self):
      return "MOVE"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runMOVECommand)

   def getIcon(self):
      return QIcon(":/plugins/qad/icons/move.svg")

   def getNote(self):
      # set the explanatory notes of the command
      return QadMsg.translate("Command_MOVE", "Moves the selected objects.")

   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      self.SSGetClass = QadSSGetClass(plugIn)
      self.SSGetClass.onlyEditableLayers = True
      self.cacheEntitySet = QadCacheEntitySet()
      self.basePt = QgsPointXY()

   def __del__(self):
      QadCommandClass.__del__(self)
      del self.SSGetClass

   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      if self.step == 0: # when you are in the entity selection phase
         return self.SSGetClass.getPointMapTool()
      else:
         if (self.plugIn is not None):
            if self.PointMapTool is None:
               self.PointMapTool = Qad_move_maptool(self.plugIn)
            return self.PointMapTool
         else:
            return None


   def getCurrentContextualMenu(self):
      if self.step == 0: # when you are in the entity selection phase
         return None # return self.SSGetClass.getCurrentContextualMenu()
      else:
         return self.contextualMenu


   # ============================================================================
   # move
   # ============================================================================
   def move(self, entity, offsetX, offsetY):
      # check if the entity belongs to a dimensioning style
      if entity.whatIs() == "ENTITY":
         # I move the geometry of the entity
         qadGeom = entity.getQadGeom().copy() # I copy it
         qadGeom.move(offsetX, offsetY)
         f = entity.getFeature()
         f.setGeometry(fromQadGeomToQgsGeom(qadGeom, entity.layer))
         # plugin, layer, feature, refresh, check_validity
         if qad_layer.updateFeatureToLayer(self.plugIn, entity.layer, f, False, False) == False:
            return False
      elif entity.whatIs() == "DIMENTITY":
         if entity.deleteToLayers(self.plugIn) == False: return False # old dimension
         newDimEntity = QadDimEntity(entity) # I copy it
         if newDimEntity.move(offsetX, offsetY) == False: return False # I move the dimension
         if newDimEntity.addToLayers(self.plugIn) == False: # recreate a new dimension
            return False

      return True


   # ============================================================================
   # moveGeoms
   # ============================================================================
   def moveGeoms(self, newPt):
      offsetX = newPt.x() - self.basePt.x()
      offsetY = newPt.y() - self.basePt.y()

      self.plugIn.beginEditCommand("Feature moved", self.cacheEntitySet.getLayerList())

      dimElaboratedList = [] # list of dimensions already processed
      entityIterator = QadCacheEntitySetIterator(self.cacheEntitySet)

      for entity in entityIterator:
         qadGeom = entity.getQadGeom() # this is how I initialize the qad info
         # check if the entity belongs to a dimensioning style
         dimEntity = QadDimStyles.getDimEntity(entity)
         if dimEntity is not None:
            if appendDimEntityIfNotExisting(dimElaboratedList, dimEntity) == False: # dimension already processed
               continue
            entity = dimEntity

         if self.move(entity, offsetX, offsetY) == False:
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
      # SPOSTA OGGETTI
      elif self.step == 1:
         if self.SSGetClass.entitySet.count() == 0:
            return True # end command
         self.cacheEntitySet.appendEntitySet(self.SSGetClass.entitySet)

         # set the map tool
         self.getPointMapTool().cacheEntitySet = self.cacheEntitySet
         self.getPointMapTool().setMode(Qad_move_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_BASE_PT)

         keyWords = QadMsg.translate("Command_MOVE", "Displacement")
         prompt = QadMsg.translate("Command_MOVE", "Specify base point or [{0}] <{0}>: ").format(keyWords)

         englishKeyWords = "Displacement"
         keyWords += "_" + englishKeyWords
         # is preparing to wait for a point or Enter or a keyword
         # msg, inputType, default, keyWords, no check
         self.waitFor(prompt, \
                      QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                      None, \
                      keyWords, QadInputModeEnum.NONE)
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
                  pass # opzione di default "spostamento"
               else:
                  self.setMapTool(self.getPointMapTool()) # I reactivate the map tool
                  return False

            value = self.getPointMapTool().point
         else: # the dot comes as a parameter of the function
            value = msg

         if value is None or type(value) == unicode:
            self.basePt.set(0, 0)
            self.getPointMapTool().basePt = self.basePt
            self.getPointMapTool().setMode(Qad_move_maptool_ModeEnum.BASE_PT_KNOWN_ASK_FOR_MOVE_PT)
            # is preparing to wait for a point
            msg = QadMsg.translate("Command_MOVE", "Specify the displacement fom the origin point 0,0 <{0}, {1}>: ")
            # msg, inputType, default, keyWords, no check
            self.waitFor(msg.format(str(self.plugIn.lastOffsetPt.x()), str(self.plugIn.lastOffsetPt.y())), \
                         QadInputTypeEnum.POINT2D, \
                         self.plugIn.lastOffsetPt, \
                         "", QadInputModeEnum.NONE)
            self.step = 4
         elif type(value) == QgsPointXY: # if the base point has been entered
            self.basePt.set(value.x(), value.y())

            # set the map tool
            self.getPointMapTool().basePt = self.basePt
            self.getPointMapTool().setMode(Qad_move_maptool_ModeEnum.BASE_PT_KNOWN_ASK_FOR_MOVE_PT)

            # is preparing to wait for a point or Enter or a keyword
            # msg, inputType, default, keyWords, no check
            self.waitFor(QadMsg.translate("Command_MOVE", "Specify the second point or <use first point as displacement from the origin point 0,0>: "), \
                         QadInputTypeEnum.POINT2D, \
                         None, \
                         "", QadInputModeEnum.NONE)
            self.step = 3

         return False

      # =========================================================================
      # RESPONSE TO THE SECOND POINT REQUEST FOR MOVEMENT (from step = 2)
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

         if value is None:
            newPt = QgsPointXY(self.basePt.x() * 2, self.basePt.y() * 2)
            self.moveGeoms(newPt)
         elif type(value) == QgsPointXY: # if the movement with a point has been inserted
            self.moveGeoms(value)

         return True # end command

      # =========================================================================
      # RESPONSE TO THE MOVEMENT POINT REQUEST (from step = 2)
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

         self.plugIn.setLastOffsetPt(value)
         self.moveGeoms(value)
         return True


# Class that manages the MOVE command for grips
class QadGRIPMOVECommandClass(QadCommandClass):


   def instantiateNewCmd(self):
      """instantiates a new command of the same type"""
      return QadGRIPMOVECommandClass(self.plugIn)


   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      self.cacheEntitySet = QadCacheEntitySet()
      self.basePt = QgsPointXY()
      self.skipToNextGripCommand = False
      self.copyEntities = False
      self.nOperationsToUndo = 0


   def __del__(self):
      QadCommandClass.__del__(self)


   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      if (self.plugIn is not None):
         if self.PointMapTool is None:
            self.PointMapTool = Qad_move_maptool(self.plugIn)
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
   # move
   # ============================================================================
   def move(self, entity, offsetX, offsetY, openForm = True):
      # check if the entity belongs to a dimensioning style
      if entity.whatIs() == "ENTITY":
         # I move the geometry of the entity
         qadGeom = entity.getQadGeom().copy() # I copy it
         qadGeom.move(offsetX, offsetY)
         f = entity.getFeature()
         f.setGeometry(fromQadGeomToQgsGeom(qadGeom, entity.layer))
         if self.copyEntities == False:
            # plugin, layer, feature, refresh, check_validity
            if qad_layer.updateFeatureToLayer(self.plugIn, entity.layer, f, False, False) == False:
               return False
         else:
            # plugin, layer, features, coordTransform, refresh, check_validity
            if qad_layer.addFeatureToLayer(self.plugIn, entity.layer, f, None, False, False, openForm) == False:
               return False
      elif entity.whatIs() == "DIMENTITY":
         # stretch the dimension
         if self.copyEntities == False:
            if entity.deleteToLayers(self.plugIn) == False:
               return False
         newDimEntity = QadDimEntity(entity) # I copy it
         newDimEntity.move(offsetX, offsetY)
         if newDimEntity.addToLayers(self.plugIn) == False:
            return False

      return True


   # ============================================================================
   # moveFeatures
   # ============================================================================
   def moveFeatures(self, newPt):
      offsetX = newPt.x() - self.basePt.x()
      offsetY = newPt.y() - self.basePt.y()

      self.plugIn.beginEditCommand("Feature moved", self.cacheEntitySet.getLayerList())

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

         if self.move(entity, offsetX, offsetY, openForm) == False:
            self.plugIn.destroyEditCommand()
            return

      self.plugIn.endEditCommand()
      self.nOperationsToUndo = self.nOperationsToUndo + 1


   # ============================================================================
   # waitForMovePoint
   # ============================================================================
   def waitForMovePoint(self):
      self.step = 1
      self.plugIn.setLastPoint(self.basePt)
      # set the map tool
      self.getPointMapTool().basePt = self.basePt
      self.getPointMapTool().setMode(Qad_move_maptool_ModeEnum.BASE_PT_KNOWN_ASK_FOR_MOVE_PT)

      keyWords = QadMsg.translate("Command_GRIPMOVE", "Base point") + "/" + \
                 QadMsg.translate("Command_GRIPMOVE", "Copy") + "/" + \
                 QadMsg.translate("Command_GRIPMOVE", "Undo") + "/" + \
                 QadMsg.translate("Command_GRIPMOVE", "eXit")

      prompt = QadMsg.translate("Command_GRIPMOVE", "Specify move point or [{0}]: ").format(keyWords)

      englishKeyWords = "Base point" + "/" + "Copy" + "/" + "Undo" + "/" + "eXit"
      keyWords += "_" + englishKeyWords
      # is preparing to wait for a point or Enter or a keyword
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
      self.getPointMapTool().setMode(Qad_move_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_BASE_PT)

      # is preparing to wait for a point
      self.waitForPoint(QadMsg.translate("Command_GRIPMOVE", "Specify base point: "))


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
         if self.cacheEntitySet.isEmpty(): # there are no objects to move
            return True
         self.showMsg(QadMsg.translate("Command_GRIPMOVE", "\n** MOVE **\n"))
         # is preparing to wait for a moving point
         self.waitForMovePoint()
         return False

      # =========================================================================
      # RESPONSE TO REQUEST FOR A MOVEMENT POINT
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
            if value == QadMsg.translate("Command_GRIPMOVE", "Base point") or value == "Base point":
               # is preparing to wait for the base point
               self.waitForBasePt()
            elif value == QadMsg.translate("Command_GRIPMOVE", "Copy") or value == "Copy":
               # Copy entities leaving the originals unchanged
               self.copyEntities = True
               # is preparing to wait for a moving point
               self.waitForMovePoint()
            elif value == QadMsg.translate("Command_GRIPMOVE", "Undo") or value == "Undo":
               if self.nOperationsToUndo > 0:
                  self.nOperationsToUndo = self.nOperationsToUndo - 1
                  self.plugIn.undoEditCommand()
               else:
                  self.showMsg(QadMsg.translate("QAD", "\nThe command has been canceled."))
               # is preparing to wait for a moving point
               self.waitForMovePoint()
            elif value == QadMsg.translate("Command_GRIPMOVE", "eXit") or value == "eXit":
               return True # end command
         elif type(value) == QgsPointXY: # if a point has been selected
            if ctrlKey:
               self.copyEntities = True

            self.moveFeatures(value)

            if self.copyEntities == False:
               return True
            # is preparing to wait for a stretching point
            self.waitForMovePoint()

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

         # is preparing to wait for a moving point
         self.waitForMovePoint()

         return False
