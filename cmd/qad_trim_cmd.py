# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 TRIM command to trim or extend graphical objects

                              -------------------
        begin                : 2013-07-15
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
from qgis.core import QgsWkbTypes, QgsFeature, QgsPointXY, QgsGeometry
from qgis.PyQt.QtGui import QIcon


from ..qad_point import QadPoint
from ..qad_getpoint import QadGetPointDrawModeEnum, QadGetPointSelectionModeEnum
from ..qad_textwindow import QadInputTypeEnum, QadInputModeEnum
from .qad_pline_cmd import QadPLINECommandClass
from .qad_rectangle_cmd import QadRECTANGLECommandClass
from .qad_generic_cmd import QadCommandClass
from ..qad_msg import QadMsg
from .. import qad_utils
from .. import qad_layer
from .qad_ssget_cmd import QadSSGetClass
from ..qad_dim import QadDimStyles
from ..qad_extend_trim_fun import extendQadGeometry, trimQadGeometry
from ..qad_entity import QadEntitySet, getSelSet, QadLayerEntitySetIterator
from ..qad_variables import QadVariables
from ..qad_multi_geom import fromQadGeomToQgsGeom, setQadGeomAt
from ..qad_geom_relations import getQadGeomClosestPart, QadIntersections


# Class that manages the TRIM command
class QadTRIMCommandClass(QadCommandClass):

   def instantiateNewCmd(self):
      """instantiates a new command of the same type"""
      return QadTRIMCommandClass(self.plugIn)

   def getName(self):
      return QadMsg.translate("Command_list", "TRIM")

   def getEnglishName(self):
      return "TRIM"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runTRIMCommand)

   def getIcon(self):
      return QIcon(":/plugins/qad/icons/trim.svg")

   def getNote(self):
      # set the explanatory notes of the command
      return QadMsg.translate("Command_TRIM", "Trims (or extends) objects to meet the edges of other objects.")

   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      self.SSGetClass = QadSSGetClass(plugIn)
      self.PLINECommand = None
      self.RECTANGLECommand = None
      self.entitySet = QadEntitySet() # entities to trim or extend
      self.limitEntitySet = QadEntitySet() # entities that act as limits
      self.edgeMode = QadVariables.get(QadMsg.translate("Environment variables", "EDGEMODE"))
      self.defaultValue = None # used to manage the right mouse button
      self.nOperationsToUndo = 0

   def __del__(self):
      QadCommandClass.__del__(self)


   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      if self.step == 3: # when you are in the line drawing phase
         return self.PLINECommand.getPointMapTool(drawMode)
      elif self.step == 4: # when you are drawing a rectangle
         return self.RECTANGLECommand.getPointMapTool(drawMode)
      else:
         return QadCommandClass.getPointMapTool(self, drawMode)


   def getCurrentContextualMenu(self):
      if self.step == 3: # when you are in the line drawing phase
         return self.PLINECommand.getCurrentContextualMenu()
      elif self.step == 4: # when you are drawing a rectangle
         return self.RECTANGLECommand.getCurrentContextualMenu()
      else:
         return self.contextualMenu


   # ============================================================================
   # trimFeatures
   # ============================================================================
   def trimFeatures(self, geom, toExtend):
      # geom is in map coordinates
      LineTempLayer = None
      self.plugIn.beginEditCommand("Feature extended" if toExtend else "Feature trimmed", \
                                   self.entitySet.getLayerList())

      for limitLayerEntitySet in self.entitySet.layerEntitySetList:
         layer = limitLayerEntitySet.layer

         entityIterator = QadLayerEntitySetIterator(limitLayerEntitySet)
         for entity in entityIterator:
            # for each entity of the layer
            f = entity.getFeature()
            if f is None:
               continue

            qadGeom = entity.getQadGeom()
            if qadGeom is None:
               continue

            if geom.whatIs() == "POINT":
               # the function returns a list with
               # (<minimum distance>
               #  <nearest point>
               #  <nearest geometry index>
               #  <index of the nearest sub-geometry>
               #  <index of the closest sub-geometry part>
               #  <"to the left of" if the point is to the left of the part with the following values:
               #  - < 0 = left (for line, arc or ellipse arc) or inside (for circles, ellipses)
               #  - > 0 = right (for line, arc or ellipse arc) or outside (for circles, ellipses)
               # )
               result = getQadGeomClosestPart(qadGeom, geom)
               intPts = [result[1]]
            else:
               intPts = QadIntersections.twoGeomObjects(qadGeom, geom)

            for intPt in intPts:
               if toExtend:
                  newGeom = extendQadGeometry(qadGeom, intPt, \
                                              self.limitEntitySet, self.edgeMode)
                  if newGeom is not None:
                     # update the feature with the extended geometry
                     extendedFeature = QgsFeature(f)
                     # I transform the geometry into the layer crs
                     extendedFeature.setGeometry(fromQadGeomToQgsGeom(newGeom, layer))
                     # plugin, layer, feature, refresh, check_validity
                     if qad_layer.updateFeatureToLayer(self.plugIn, layer, extendedFeature, False, False) == False:
                        self.plugIn.destroyEditCommand()
                        return
               else: # trim
                  result = trimQadGeometry(qadGeom, intPt, \
                                           self.limitEntitySet, self.edgeMode)
                  if result is not None:
                     line1 = result[0]
                     line2 = result[1]
                     atGeom = result[2]
                     atSubGeom = result[3]
                     if layer.geometryType() == QgsWkbTypes.LineGeometry:
                        newQadGeom = setQadGeomAt(qadGeom, line1, atGeom, atSubGeom)
                        if newQadGeom is None:
                           self.plugIn.destroyEditCommand()
                           return

                        trimmedFeature1 = QgsFeature(f)
                        # I transform the geometry into the layer crs
                        trimmedFeature1.setGeometry(fromQadGeomToQgsGeom(newQadGeom, layer))
                        # plugin, layer, feature, refresh, check_validity
                        if qad_layer.updateFeatureToLayer(self.plugIn, layer, trimmedFeature1, False, False) == False:
                           self.plugIn.destroyEditCommand()
                           return
                        if line2 is not None:
                           trimmedFeature2 = QgsFeature(f)
                           # I transform the geometry into the layer crs
                           trimmedFeature2.setGeometry(fromQadGeomToQgsGeom(line2, layer))
                           # plugin, layer, feature, coordTransform, refresh, check_validity
                           if qad_layer.addFeatureToLayer(self.plugIn, layer, trimmedFeature2, None, False, False, False) == False:
                              self.plugIn.destroyEditCommand()
                              return

                     else:
                        # add the lines in the temporary layers of QAD
                        if LineTempLayer is None:
                           LineTempLayer = qad_layer.createQADTempLayer(self.plugIn, QgsWkbTypes.LineGeometry)
                           self.plugIn.addLayerToLastEditCommand("Feature trimmed", LineTempLayer)

                        lineGeoms = [line1]
                        if line2 is not None:
                           lineGeoms.append(line2)

                        # I transform the geometry into that of temporary layers
                        # plugIn, pointGeoms, lineGeoms, polygonGeoms, coord, refresh
                        if qad_layer.addGeometriesToQADTempLayers(self.plugIn, None, lineGeoms, None, None, False) == False:
                           self.plugIn.destroyEditCommand()
                           return

                        if delQadGeomAt(qadGeom, atGeom, atSubGeom) == False or updGeom.isEmpty(): # da delete
                           # plugin, layer, feature id, refresh
                           if qad_layer.deleteFeatureToLayer(self.plugIn, layer, f.id(), False) == False:
                              self.plugIn.destroyEditCommand()
                              return
                        else:
                           trimmedFeature1 = QgsFeature(f)
                           # I transform the geometry into the layer crs
                           trimmedFeature1.setGeometry(fromQadGeomToQgsGeom(qadGeom, layer))
                           # plugin, layer, feature, refresh, check_validity
                           if qad_layer.updateFeatureToLayer(self.plugIn, layer, trimmedFeature1, False, False) == False:
                              self.plugIn.destroyEditCommand()
                              return

      self.plugIn.endEditCommand()
      self.nOperationsToUndo = self.nOperationsToUndo + 1


   # ============================================================================
   # waitForObjectSel
   # ============================================================================
   def waitForObjectSel(self):
      self.step = 2
      # set the map tool
      self.getPointMapTool().setSelectionMode(QadGetPointSelectionModeEnum.ENTITY_SELECTION_DYNAMIC)
      # only editable linear layers that do not belong to dimensions
      layerList = []
      for layer in qad_utils.getVisibleVectorLayers(self.plugIn.canvas): # All vector layers visible
         if layer.geometryType() == QgsWkbTypes.LineGeometry and layer.isEditable():
            if len(QadDimStyles.getDimListByLayer(layer)) == 0:
               layerList.append(layer)

      self.getPointMapTool().layersToCheck = layerList
      self.getPointMapTool().setDrawMode(QadGetPointDrawModeEnum.NONE)
      self.getPointMapTool().onlyEditableLayers = True

      keyWords = QadMsg.translate("Command_TRIM", "Fence") + "/" + \
                 QadMsg.translate("Command_TRIM", "Crossing") + "/" + \
                 QadMsg.translate("Command_TRIM", "Edge") + "/" + \
                 QadMsg.translate("Command_TRIM", "Undo")
      prompt = QadMsg.translate("Command_TRIM", "Select the object to trim or shift-select to extend or [{0}]: ").format(keyWords)

      englishKeyWords = "Fence" + "/" + "Crossing" + "/" + "Edge" + "/" + "Undo"
      keyWords += "_" + englishKeyWords
      # is preparing to wait for a point or Enter or a keyword
      # msg, inputType, default, keyWords, no check
      self.waitFor(prompt, \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                   None, \
                   keyWords, QadInputModeEnum.NONE)


   # ============================================================================
   # run
   # ============================================================================
   def run(self, msgMapTool = False, msg = None):
      if self.plugIn.canvas.mapSettings().destinationCrs().isGeographic():
         self.showMsg(QadMsg.translate("QAD", "\nThe coordinate reference system of the project must be a projected coordinate system.\n"))
         return True # end command

      # =========================================================================
      # OBJECT SELECTION REQUEST LIMITS
      if self.step == 0: # start of command
         CurrSettingsMsg = QadMsg.translate("QAD", "\nCurrent settings: ")
         if self.edgeMode == 0: # 0 = no extension
            CurrSettingsMsg = CurrSettingsMsg + QadMsg.translate("Command_TRIM", "Edge = No extend")
         else:
            CurrSettingsMsg = CurrSettingsMsg + QadMsg.translate("Command_TRIM", "Edge = Extend")

         self.showMsg(CurrSettingsMsg)
         self.showMsg(QadMsg.translate("Command_TRIM", "\nSelect trim limits..."))

         if self.SSGetClass.run(msgMapTool, msg) == True:
            # selection completed
            self.step = 1
            return self.run(msgMapTool, msg)

      # =========================================================================
      # RESPONSE TO OBJECT SELECTION LIMITS
      elif self.step == 1:
         self.limitEntitySet.set(self.SSGetClass.entitySet)

         if self.limitEntitySet.count() == 0:
            return True # end command

         # is preparing to wait for the selection of objects to extend/cut
         self.waitForObjectSel()
         return False

      # =========================================================================
      # RESPONSE TO THE SELECTION OF OBJECTS TO EXTEND
      elif self.step == 2:
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
            else:
               value = self.getPointMapTool().point
         else: # the dot comes as a parameter of the function
            value = msg

         if type(value) == unicode:
            if value == QadMsg.translate("Command_TRIM", "Fence") or value == "Fence":
               # Select all objects that intersect a polyline
               self.PLINECommand = QadPLINECommandClass(self.plugIn)
               # if this flag = True the command is used within another command to draw a line
               # which will not be saved on a layer
               self.PLINECommand.virtualCmd = True
               self.PLINECommand.run(msgMapTool, msg)
               self.step = 3
               return False
            elif value == QadMsg.translate("Command_TRIM", "Crossing") or value == "Crossing":
               # Select all objects that intersect a rectangle
               self.RECTANGLECommand = QadRECTANGLECommandClass(self.plugIn)
               # if this flag = True the command is used within another command to draw a line
               # which will not be saved on a layer
               self.RECTANGLECommand.virtualCmd = True
               self.RECTANGLECommand.run(msgMapTool, msg)
               self.step = 4
               return False
            elif value == QadMsg.translate("Command_TRIM", "Edge") or value == "Edge":
               # To extend an object also using extensions of reference objects
               # see EDGEMODE variable
               keyWords = QadMsg.translate("Command_TRIM", "Extend") + "/" + \
                          QadMsg.translate("Command_TRIM", "No extend")
               if self.edgeMode == 0: # 0 = no extension
                  self.defaultValue = QadMsg.translate("Command_TRIM", "No extend")
               else:
                  self.defaultValue = QadMsg.translate("Command_TRIM", "Extend")
               prompt = QadMsg.translate("Command_TRIM", "Specify an extension mode [{0}] <{1}>: ").format(keyWords, self.defaultValue)

               englishKeyWords = "Extend" + "/" + "No extend"
               keyWords += "_" + englishKeyWords
               # is preparing to wait for enter or a keyword
               # msg, inputType, default, keyWords, no check
               self.waitFor(prompt, \
                            QadInputTypeEnum.KEYWORDS, \
                            self.defaultValue, \
                            keyWords, QadInputModeEnum.NONE)
               self.step = 5
               return False
            elif value == QadMsg.translate("Command_TRIM", "Undo") or value == "Undo":
               if self.nOperationsToUndo > 0:
                  self.nOperationsToUndo = self.nOperationsToUndo - 1
                  self.plugIn.undoEditCommand()
               else:
                  self.showMsg(QadMsg.translate("QAD", "\nThe command has been canceled."))
         elif type(value) == QgsPointXY: # if a point has been selected
            self.entitySet.clear()
            if self.getPointMapTool().entity.isInitialized():
               self.entitySet.addEntity(self.getPointMapTool().entity)
               ToExtend = True if self.getPointMapTool().shiftKey == True else False
               self.trimFeatures(QadPoint().set(value), ToExtend)
            else:
               # I searc if there are entities at the point indicated considering
               # only editable linear layers that do not belong to dimensions
               layerList = []
               for layer in qad_utils.getVisibleVectorLayers(self.plugIn.canvas): # All vector layers visible
                  if layer.geometryType() == QgsWkbTypes.LineGeometry and layer.isEditable():
                     if len(QadDimStyles.getDimListByLayer(layer)) == 0:
                        layerList.append(layer)

               result = qad_utils.getEntSel(self.getPointMapTool().toCanvasCoordinates(value),
                                            self.getPointMapTool(), \
                                            QadVariables.get(QadMsg.translate("Environment variables", "PICKBOX")), \
                                            layerList)
               if result is not None:
                  feature = result[0]
                  layer = result[1]
                  point = result[2]
                  self.entitySet.addEntity(QadEntity().set(layer, feature.id()))
                  self.trimFeatures(QadPoint().set(value), False)
         else:
            return True # end command

         # is preparing to wait for the selection of objects to extend/cut
         self.waitForObjectSel()

         return False

      # =========================================================================
      # RESPONSE TO THE POINT REQUEST FOR INTERCEPTION MODE (from step = 2)
      elif self.step == 3: # after waiting for a point the command restarts
         if self.PLINECommand.run(msgMapTool, msg) == True:
            if self.PLINECommand.polyline.qty() > 0:
               if msgMapTool == True: # if the polyline comes from a graphic selection
                  ToExtend = True if self.getPointMapTool().shiftKey == True else False
               else:
                  ToExtend = False

               # I searc for all the geometries passing through the polyline skipping the point and polygon layers
               # and considering only editable layers
               self.entitySet = getSelSet("F", self.getPointMapTool(), self.PLINECommand.polyline.asPolyline(), \
                                                    None, False, True, False, \
                                                    True)
               self.trimFeatures(self.PLINECommand.polyline, ToExtend)
            del self.PLINECommand
            self.PLINECommand = None

            # is preparing to wait for the selection of objects to extend/cut
            self.waitForObjectSel()
            self.getPointMapTool().refreshSnapType() # update the snapType which can be varied from the pline map tool

         return False

      # =========================================================================
      # RESPONSE TO THE POINT REQUEST FOR INTERSECT MODE (from step = 2)
      elif self.step == 4: # after waiting for a point the command restarts
         if self.RECTANGLECommand.run(msgMapTool, msg) == True:
            if self.RECTANGLECommand.polyline.qty() > 0:
               if msgMapTool == True: # if the polyline comes from a graphic selection
                  ToExtend = True if self.getPointMapTool().shiftKey == True else False
               else:
                  ToExtend = False

               # I searc for all the geometries passing through the polyline skipping the point and polygon layers
               # and considering only editable layers
               self.entitySet = getSelSet("F", self.getPointMapTool(), self.RECTANGLECommand.polyline.asPolyline(), \
                                                    None, False, True, False, \
                                                    True)
               self.trimFeatures(self.RECTANGLECommand.polyline, ToExtend)
            del self.RECTANGLECommand
            self.RECTANGLECommand = None

            # is preparing to wait for the selection of objects to extend/cut
            self.waitForObjectSel()
            self.getPointMapTool().refreshSnapType() # update the snapType which can be varied from the rectangle map tool
         return False

      # =========================================================================
      # RESPONSE TO EXTENSION TYPE REQUEST (from step = 2)
      elif self.step == 5: # after waiting for a point or a real number the command is restarted
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if while selecting a point
            # Another plugin was activated which deactivated Qad
            # so the command that returns here has been reactivated without the map tool
            # has selected a point
            if self.getPointMapTool().rightButton == True: # if used with the right mouse button
               value = self.defaultValue
            else:
               self.setMapTool(self.getPointMapTool()) # I reactivate the map tool
               return False
         else: # the value comes as a function parameter
            value = msg

         if type(value) == unicode:
            if value == QadMsg.translate("Command_TRIM", "No extend") or value == "No extend":
               self.edgeMode = 0
               QadVariables.set(QadMsg.translate("Environment variables", "EDGEMODE"), self.edgeMode)
               QadVariables.save()
               # is preparing to wait for the selection of objects to extend/cut
               self.waitForObjectSel()
            elif value == QadMsg.translate("Command_TRIM", "Extend") or value == "Extend":
               self.edgeMode = 1
               QadVariables.set(QadMsg.translate("Environment variables", "EDGEMODE"), self.edgeMode)
               QadVariables.save()
               # is preparing to wait for the selection of objects to extend/cut
               self.waitForObjectSel()

         return False
