# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin ok

 SCALE command to scale objects

                              -------------------
        begin                : 2013-10-01
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


from ..qad_entity import QadCacheEntitySet, QadCacheEntitySetIterator, QadEntityTypeEnum
from .qad_scale_maptool import Qad_scale_maptool_ModeEnum, Qad_scale_maptool
from .qad_generic_cmd import QadCommandClass
from ..qad_msg import QadMsg
from ..qad_getpoint import QadGetPointDrawModeEnum
from ..qad_textwindow import QadInputTypeEnum, QadInputModeEnum
from .qad_ssget_cmd import QadSSGetClass
from .. import qad_utils
from .. import qad_layer
from .. import qad_label
from ..qad_dim import QadDimStyles, appendDimEntityIfNotExisting, QadDimEntity
from ..qad_multi_geom import fromQadGeomToQgsGeom


# Class that manages the SCALE command
class QadSCALECommandClass(QadCommandClass):

   def instantiateNewCmd(self):
      """instantiates a new command of the same type"""
      return QadSCALECommandClass(self.plugIn)

   def getName(self):
      return QadMsg.translate("Command_list", "SCALE")

   def getEnglishName(self):
      return "SCALE"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runSCALECommand)

   def getIcon(self):
      return QIcon(":/plugins/qad/icons/scale.svg")

   def getNote(self):
      # set the explanatory notes of the command
      return QadMsg.translate("Command_SCALE", "Enlarges or reduces selected objects.")

   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      self.SSGetClass = QadSSGetClass(plugIn)
      self.SSGetClass.onlyEditableLayers = True
      self.cacheEntitySet = QadCacheEntitySet()
      self.basePt = None
      self.copyFeatures = False
      self.Pt1ReferenceLen = None
      self.ReferenceLen = 1
      self.Pt1NewLen = None

   def __del__(self):
      QadCommandClass.__del__(self)
      del self.SSGetClass


   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      if self.step == 0: # when you are in the entity selection phase
         return self.SSGetClass.getPointMapTool()
      else:
         if (self.plugIn is not None):
            if self.PointMapTool is None:
               self.PointMapTool = Qad_scale_maptool(self.plugIn)
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
   def scale(self, entity, basePt, scale, openForm = True):
      # check if the entity belongs to a dimensioning style
      if entity.whatIs() == "ENTITY":
         # I move the geometry of the entity
         qadGeom = entity.getQadGeom().copy() # I copy it
         qadGeom.scale(basePt, scale)
         f = entity.getFeature()
         f.setGeometry(fromQadGeomToQgsGeom(qadGeom, entity.layer))

         sizeFldName = None
         if entity.isTextualLayer:
            # if the text height depends on only one field
            sizeFldNames = qad_label.get_labelSizeFieldNames(entity.layer)
            if len(sizeFldNames) == 1 and len(sizeFldNames[0]) > 0:
               sizeFldName = sizeFldNames[0]
         elif entity.isSymbolLayer:
            # if the scale depends on a field
            sizeFldName = qad_layer.get_symbolScaleFieldName(entity.layer)
            if len(sizeFldName) == 0:
               sizeFldName = None

         if sizeFldName is not None:
            sizeValue = f.attribute(sizeFldName)
            if sizeValue is None or sizeValue == NULL:
               sizeValue = 1
            sizeValue = sizeValue * scale
            f.setAttribute(sizeFldName, sizeValue)

         if self.copyFeatures == False:
            # plugin, layer, feature, refresh, check_validity
            if qad_layer.updateFeatureToLayer(self.plugIn, entity.layer, f, False, False) == False:
               self.plugIn.destroyEditCommand()
               return False
         else:
            # plugin, layer, features, coordTransform, refresh, check_validity
            if qad_layer.addFeatureToLayer(self.plugIn, entity.layer, f, None, False, False, openForm) == False:
               self.plugIn.destroyEditCommand()
               return False
      elif entity.whatIs() == "DIMENTITY":
         if self.copyFeatures == False:
            if dimEntity.deleteToLayers(self.plugIn) == False:
               return False
         newDimEntity = QadDimEntity(entity) # I copy it
         newDimEntity.scale(basePt, scale)
         if newDimEntity.addToLayers(self.plugIn) == False:
            return False

      return True


   # ============================================================================
   # scaleGeoms
   # ============================================================================
   def scaleGeoms(self, scale):
      self.plugIn.beginEditCommand("Feature scaled", self.cacheEntitySet.getLayerList())

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

         if self.scale(entity, self.basePt, scale, openForm) == False:
            self.plugIn.destroyEditCommand()
            return

      self.plugIn.endEditCommand()


   def waitForScale(self):
      # set the map tool
      self.getPointMapTool().setMode(Qad_scale_maptool_ModeEnum.BASE_PT_KNOWN_ASK_FOR_SCALE_PT)

      keyWords = QadMsg.translate("Command_SCALE", "Copy") + "/" + \
                 QadMsg.translate("Command_SCALE", "Reference")
      default = self.plugIn.lastScale
      prompt = QadMsg.translate("Command_SCALE", "Specify scale factor or [{0}] <{1}>: ").format(keyWords, str(default))

      englishKeyWords = "Copy" + "/" + "Reference"
      keyWords += "_" + englishKeyWords
      # is preparing to wait for a point or Enter or a keyword
      # msg, inputType, default, keyWords, positive values
      self.waitFor(prompt, \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.FLOAT | QadInputTypeEnum.KEYWORDS, \
                   default, \
                   keyWords, QadInputModeEnum.NOT_ZERO | QadInputModeEnum.NOT_NEGATIVE)
      self.step = 3


   def waitForReferenceLen(self):
      # set the map tool
      self.getPointMapTool().setMode(Qad_scale_maptool_ModeEnum.ASK_FOR_FIRST_PT_REFERENCE_LEN)

      msg = QadMsg.translate("Command_SCALE", "Specify reference length <{0}>: ")
      # is preparing to wait for a point or Enter
      # msg, inputType, default, keyWords, positive values
      self.waitFor(msg.format(str(self.plugIn.lastReferenceLen)), \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.FLOAT, \
                   self.plugIn.lastReferenceLen, \
                   "", QadInputModeEnum.NOT_ZERO | QadInputModeEnum.NOT_NEGATIVE)
      self.step = 4


   def waitForNewReferenceLen(self):
      # set the map tool
      self.getPointMapTool().setMode(Qad_scale_maptool_ModeEnum.BASE_PT_KNOWN_ASK_FOR_NEW_LEN_PT)

      keyWords = QadMsg.translate("Command_SCALE", "Points")
      if self.plugIn.lastNewReferenceLen == 0:
         default = self.plugIn.lastScale
      else:
         default = self.plugIn.lastNewReferenceLen
      prompt = QadMsg.translate("Command_SCALE", "Specify new length or [{0}] <{1}>: ").format(keyWords, str(default))

      englishKeyWords = "Points"
      keyWords += "_" + englishKeyWords
      # is preparing to wait for a point or Enter or a keyword
      # msg, inputType, default, keyWords, positive values
      self.waitFor(prompt, \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.FLOAT | QadInputTypeEnum.KEYWORDS, \
                   default, \
                   keyWords, QadInputModeEnum.NOT_ZERO | QadInputModeEnum.NOT_NEGATIVE)
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
         self.getPointMapTool().setMode(Qad_scale_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_BASE_PT)

         # is preparing to wait for a point
         self.waitForPoint(QadMsg.translate("Command_SCALE", "Specify base point: "))

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
         # prepares to wait for the ladder
         self.waitForScale()

         return False

      # =========================================================================
      # RESPONSE TO THE REQUEST SECOND POINT PER SCALE (from step = 2)
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
            if value == QadMsg.translate("Command_SCALE", "Copy") or value == "Copy":
               self.copyFeatures = True
               self.showMsg(QadMsg.translate("Command_SCALE", "\nScale of a copy of the selected objects."))
               # prepares to wait for the ladder
               self.waitForScale()
            elif value == QadMsg.translate("Command_SCALE", "Reference") or value == "Reference":
               # is preparing to wait for the reference length
               self.waitForReferenceLen()
         elif type(value) == QgsPointXY or type(value) == float: # if the scale has been inserted
            if type(value) == QgsPointXY: # if the scale with a point has been entered
               if value == self.basePt:
                  self.showMsg(QadMsg.translate("QAD", "\nThe value must be positive and not zero."))
                  # is preparing to wait for a point
                  self.waitForScale()
                  return False

               scale = qad_utils.getDistance(self.basePt, value)
            else:
               scale = value
            self.plugIn.setLastScale(scale)

            self.scaleGeoms(scale)
            return True # end command

         return False

      # =========================================================================
      # RESPONSE TO THE FIRST POINT REQUEST FOR REFERENCE LENGTH (from step = 3)
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

         if type(value) == float: # if the length has been entered
            self.ReferenceLen = value
            self.getPointMapTool().ReferenceLen = self.ReferenceLen
            # is preparing to wait for the new length
            self.waitForNewReferenceLen()

         elif type(value) == QgsPointXY: # if the scale with a point has been entered
            self.Pt1ReferenceLen = QgsPointXY(value)
            self.getPointMapTool().Pt1ReferenceLen = self.Pt1ReferenceLen
            # set the map tool
            self.getPointMapTool().setMode(Qad_scale_maptool_ModeEnum.FIRST_PT_KNOWN_ASK_FOR_SECOND_PT_REFERENCE_LEN)
            # is preparing to wait for a point
            self.waitForPoint(QadMsg.translate("Command_SCALE", "Specify second point: "))
            self.step = 5

         return False

      # =========================================================================
      # RESPONSE TO THE SECOND POINT REQUEST FOR REFERENCE LENGTH (from step = 4)
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

         if self.Pt1ReferenceLen == value:
            self.showMsg(QadMsg.translate("QAD", "\nThe value must be positive and not zero."))
            # is preparing to wait for a point
            self.waitForPoint(QadMsg.translate("Command_SCALE", "Specify second point: "))
            return False

         length = qad_utils.getDistance(self.Pt1ReferenceLen, value)
         self.ReferenceLen = length
         self.getPointMapTool().ReferenceLen = self.ReferenceLen
         # is preparing to wait for the new length
         self.waitForNewReferenceLen()

         return False

      # =========================================================================
      # RESPONSE TO THE SECOND POINT REQUEST FOR NEW LENGTH (from step = 4 and 5)
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
            if value == QadMsg.translate("Command_SCALE", "Points") or value == "Points":
               # set the map tool
               self.getPointMapTool().setMode(Qad_scale_maptool_ModeEnum.ASK_FOR_FIRST_NEW_LEN_PT)
               # is preparing to wait for a point
               self.waitForPoint(QadMsg.translate("Command_SCALE", "Specify first point: "))
               self.step = 7
         elif type(value) == QgsPointXY or type(value) == float: # if the length has been entered
            if type(value) == QgsPointXY: # if the length has been entered with a point
               if value == self.basePt:
                  self.showMsg(QadMsg.translate("QAD", "\nThe value must be positive and not zero."))
                  # is preparing to wait for a point
                  self.waitForNewReferenceLen()
                  return False

               length = qad_utils.getDistance(self.basePt, value)
            else:
               length = value

            scale = length / self.ReferenceLen
            self.plugIn.setLastScale(scale)
            self.scaleGeoms(scale)
            return True # end command

         return False

      # =========================================================================
      # RESPONSE TO THE FIRST POINT REQUEST FOR NEW LENGTH (from step = 6)
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

         self.Pt1NewLen = value
         # set the map tool
         self.getPointMapTool().Pt1NewLen = self.Pt1NewLen
         self.getPointMapTool().setMode(Qad_scale_maptool_ModeEnum.FIRST_PT_KNOWN_ASK_FOR_SECOND_NEW_LEN_PT)
         # is preparing to wait for a point
         self.waitForPoint(QadMsg.translate("Command_SCALE", "Specify second point: "))
         self.step = 8

         return False

      # =========================================================================
      # RESPONSE TO THE SECOND POINT REQUEST FOR NEW LENGTH (from step = 7)
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

         if value == self.Pt1NewLen:
            self.showMsg(QadMsg.translate("QAD", "\nThe value must be positive and not zero."))
            # is preparing to wait for a point
            self.waitForPoint(QadMsg.translate("Command_SCALE", "Specify second point: "))
            return False

         length = qad_utils.getDistance(self.Pt1NewLen, value)

         scale = length / self.ReferenceLen
         self.plugIn.setLastScale(scale)
         self.scaleGeoms(scale)
         return True # end command


# Class that manages the SCALE command for grips
class QadGRIPSCALECommandClass(QadCommandClass):


   def instantiateNewCmd(self):
      """instantiates a new command of the same type"""
      return QadGRIPSCALECommandClass(self.plugIn)


   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      self.cacheEntitySet = QadCacheEntitySet()
      self.basePt = QgsPointXY()
      self.skipToNextGripCommand = False
      self.copyEntities = False
      self.nOperationsToUndo = 0
      self.Pt1ReferenceLen = None
      self.ReferenceLen = 1
      self.Pt1NewLen = None
      self.__referenceLenMode = False

   def __del__(self):
      QadCommandClass.__del__(self)

   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      if (self.plugIn is not None):
         if self.PointMapTool is None:
            self.PointMapTool = Qad_scale_maptool(self.plugIn)
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
   # scale
   # ============================================================================
   def scale(self, entity, basePt, scale, sizeFldName, openForm = True):
      # entity = entity to scale
      # basePt = base point
      # scale = fattore di scala
      # sizeFldName = table field that stores the scale
      # check if the entity belongs to a dimensioning style
      if entity.whatIs() == "ENTITY":
         # I move the geometry of the entity
         qadGeom = entity.getQadGeom().copy() # I copy it
         qadGeom.scale(basePt, scale)
         f = entity.getFeature()
         f.setGeometry(fromQadGeomToQgsGeom(qadGeom, entity.layer))

         sizeFldName = None
         if entity.isTextualLayer:
            # if the text height depends on only one field
            sizeFldNames = qad_label.get_labelSizeFieldNames(entity.layer)
            if len(sizeFldNames) == 1 and len(sizeFldNames[0]) > 0:
               sizeFldName = sizeFldNames[0]
         elif entity.isSymbolLayer:
            # if the scale depends on a field
            sizeFldName = qad_layer.get_symbolScaleFieldName(entity.layer)
            if len(sizeFldName) == 0:
               sizeFldName = None

         if sizeFldName is not None:
            sizeValue = f.attribute(sizeFldName)
            if sizeValue is None or sizeValue == NULL:
               sizeValue = 1
            sizeValue = sizeValue * scale
            f.setAttribute(sizeFldName, sizeValue)

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
         newDimEntity.scale(basePt, scale)
         if newDimEntity.addToLayers(self.plugIn) == False:
            return False


   def scaleFeatures(self, scale):
      self.plugIn.beginEditCommand("Feature scaled", self.cacheEntitySet.getLayerList())

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

         if self.scale(entity, self.basePt, scale, openForm) == False:
            self.plugIn.destroyEditCommand()
            return

      self.plugIn.endEditCommand()
      self.nOperationsToUndo = self.nOperationsToUndo + 1


   def waitForScale(self):
      self.getPointMapTool().basePt = self.basePt
      keyWords = QadMsg.translate("Command_GRIPSCALE", "Base point") + "/" + \
                 QadMsg.translate("Command_GRIPSCALE", "Copy") + "/" + \
                 QadMsg.translate("Command_GRIPSCALE", "Undo") + "/" + \
                 QadMsg.translate("Command_GRIPSCALE", "Reference") + "/" + \
                 QadMsg.translate("Command_GRIPSCALE", "eXit")

      default = self.plugIn.lastScale
      if self.__referenceLenMode:
         # set the map tool
         self.getPointMapTool().setMode(Qad_scale_maptool_ModeEnum.BASE_PT_KNOWN_ASK_FOR_NEW_LEN_PT)
         if self.plugIn.lastNewReferenceLen > 0:
            default = self.plugIn.lastNewReferenceLen
         prompt = QadMsg.translate("Command_GRIPSCALE", "Specify new length or [{0}]: ").format(keyWords)
      else:
         # set the map tool
         self.getPointMapTool().setMode(Qad_scale_maptool_ModeEnum.BASE_PT_KNOWN_ASK_FOR_SCALE_PT)
         prompt = QadMsg.translate("Command_GRIPSCALE", "Specify scale factor or [{0}]: ").format(keyWords)

      englishKeyWords = "Base point" + "/" + "Copy" + "/" + "Undo" + "/" + "Reference" + "/" + "eXit"
      keyWords += "_" + englishKeyWords
      # is preparing to wait for a point or Enter or a keyword
      # msg, inputType, default, keyWords, positive values
      self.waitFor(prompt, \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.FLOAT | QadInputTypeEnum.KEYWORDS, \
                   None, \
                   keyWords, QadInputModeEnum.NOT_ZERO | QadInputModeEnum.NOT_NEGATIVE)
      self.step = 1


   # ============================================================================
   # waitForBasePt
   # ============================================================================
   def waitForBasePt(self):
      self.step = 2
      # set the map tool
      self.getPointMapTool().setMode(Qad_scale_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_BASE_PT)

      # is preparing to wait for a point
      self.waitForPoint(QadMsg.translate("Command_GRIPSCALE", "Specify base point: "))


   def waitForReferenceLen(self):
      self.__referenceLenMode = True
      # set the map tool
      self.getPointMapTool().setMode(Qad_scale_maptool_ModeEnum.ASK_FOR_FIRST_PT_REFERENCE_LEN)

      msg = QadMsg.translate("Command_GRIPSCALE", "Specify reference length <{0}>: ")
      # is preparing to wait for a point or Enter
      # msg, inputType, default, keyWords, positive values
      self.waitFor(msg.format(str(self.plugIn.lastReferenceLen)), \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.FLOAT, \
                   self.plugIn.lastReferenceLen, \
                   "", QadInputModeEnum.NOT_ZERO | QadInputModeEnum.NOT_NEGATIVE)
      self.step = 3


   def run(self, msgMapTool = False, msg = None):
      if self.plugIn.canvas.mapSettings().destinationCrs().isGeographic():
         self.showMsg(QadMsg.translate("QAD", "\nThe coordinate reference system of the project must be a projected coordinate system.\n"))
         return True # end command

      # =========================================================================
      # OBJECT SELECTION REQUEST
      if self.step == 0: # start of command
         if self.cacheEntitySet.isEmpty(): # there are no objects to rotate
            return True
         self.showMsg(QadMsg.translate("Command_GRIPSCALE", "\n** SCALE **\n"))
         # prepares to wait for the ladder
         self.waitForScale()
         return False

      # =========================================================================
      # RESPONSE TO THE SCALE FACTOR REQUEST
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
            if value == QadMsg.translate("Command_GRIPSCALE", "Base point") or value == "Base point":
               # is preparing to wait for the base point
               self.waitForBasePt()
            elif value == QadMsg.translate("Command_GRIPSCALE", "Copy") or value == "Copy":
               # Copy entities leaving the originals unchanged
               self.copyEntities = True
               # prepares to wait for the ladder
               self.waitForScale()
            elif value == QadMsg.translate("Command_GRIPSCALE", "Undo") or value == "Undo":
               if self.nOperationsToUndo > 0:
                  self.nOperationsToUndo = self.nOperationsToUndo - 1
                  self.plugIn.undoEditCommand()
               else:
                  self.showMsg(QadMsg.translate("QAD", "\nThe command has been canceled."))
               # prepares to wait for the ladder
               self.waitForScale()
            elif value == QadMsg.translate("Command_GRIPSCALE", "Reference") or value == "Reference":
               # is preparing to wait for the reference length
               self.waitForReferenceLen()
            elif value == QadMsg.translate("Command_GRIPSCALE", "eXit") or value == "eXit":
               return True # end command
         elif type(value) == QgsPointXY or type(value) == float: # if the scale has been inserted
            if type(value) == QgsPointXY: # if the scale with a point has been entered
               if value == self.basePt:
                  self.showMsg(QadMsg.translate("QAD", "\nThe value must be positive and not zero."))
                  # is preparing to wait for a point
                  self.waitForScale()
                  return False

               scale = qad_utils.getDistance(self.basePt, value)
            else:
               scale = value

            if self.__referenceLenMode == True: # scale represents the new reference distance
               scale = scale / self.ReferenceLen

            self.plugIn.setLastScale(scale)

            if ctrlKey:
               self.copyEntities = True

            self.scaleFeatures(scale)

            if self.copyEntities == False:
               return True

            # prepares to wait for the ladder
            self.waitForScale()

         else:
            if self.copyEntities == False:
               self.skipToNextGripCommand = True
            return True # end command

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
         # prepares to wait for the ladder
         self.waitForScale()

         return False


      # =========================================================================
      # RESPONSE TO THE FIRST POINT REQUEST FOR REFERENCE LENGTH (from step = 1)
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

         if type(value) == float: # if the length has been entered
            self.ReferenceLen = value
            self.getPointMapTool().ReferenceLen = self.ReferenceLen
            # is preparing to wait for the new length
            self.waitForScale()

         elif type(value) == QgsPointXY: # if the scale with a point has been entered
            self.Pt1ReferenceLen = QgsPointXY(value)
            self.getPointMapTool().Pt1ReferenceLen = self.Pt1ReferenceLen
            # set the map tool
            self.getPointMapTool().setMode(Qad_scale_maptool_ModeEnum.FIRST_PT_KNOWN_ASK_FOR_SECOND_PT_REFERENCE_LEN)
            # is preparing to wait for a point
            self.waitForPoint(QadMsg.translate("Command_GRIPSCALE", "Specify second point: "))
            self.step = 4

         return False

      # =========================================================================
      # RESPONSE TO THE SECOND POINT REQUEST FOR REFERENCE LENGTH (from step = 4)
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

         if self.Pt1ReferenceLen == value:
            self.showMsg(QadMsg.translate("QAD", "\nThe value must be positive and not zero."))
            # is preparing to wait for a point
            self.waitForPoint(QadMsg.translate("Command_GRIPSCALE", "Specify second point: "))
            return False

         length = qad_utils.getDistance(self.Pt1ReferenceLen, value)
         self.ReferenceLen = length
         self.getPointMapTool().ReferenceLen = self.ReferenceLen
         # is preparing to wait for the new length
         self.waitForScale()

         return False
