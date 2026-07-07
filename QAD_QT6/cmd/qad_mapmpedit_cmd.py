# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin OK

 MAPMPEDIT command to edit an existing polygon

                              -------------------
        begin                : 2016-04-05
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


from qgis.PyQt.QtGui import QIcon
from qgis.core import QgsCoordinateTransform, QgsGeometry, QgsProject, QgsFeature


from .qad_generic_cmd import QadCommandClass
from ..qad_getpoint import *
from .qad_pline_cmd import QadPLINECommandClass
from .qad_ssget_cmd import QadSSGetClass
from ..qad_msg import QadMsg
from ..qad_textwindow import *
from .. import qad_utils
from .. import qad_layer
from .qad_entsel_cmd import QadEntSelClass
from ..qad_geom_relations import getQadGeomClosestVertex


# ===============================================================================
# QadMAPMPEDITCommandOpTypeEnum class.
# ===============================================================================
class QadMAPMPEDITCommandOpTypeEnum():
   UNION        = 1 # unione tra poligoni
   INTERSECTION = 2 # intersection between polygons
   DIFFERENCE   = 3 # differenza tra poligoni


# Class that handles the MAPMPEDIT command
class QadMAPMPEDITCommandClass(QadCommandClass):

   def instantiateNewCmd(self):
      """instantiates a new command of the same type"""
      return QadMAPMPEDITCommandClass(self.plugIn)

   def getName(self):
      return QadMsg.translate("Command_list", "MAPMPEDIT")

   def getEnglishName(self):
      return "MAPMPEDIT"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runMAPMPEDITCommand)

   def getIcon(self):
      return QIcon(":/plugins/qad/icons/mapmpedit.svg")

   def getNote(self):
      # set the explanatory notes of the command
      return QadMsg.translate("Command_MAPMPEDIT", "Modifies existing polygon.")

   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)

      self.poligonEntity = QadEntity()

      self.SSGetClass = QadSSGetClass(plugIn)
      self.SSGetClass.onlyEditableLayers = False
      self.SSGetClass.checkDimLayers = False # I discard the dimensions

      self.entSelClass = None

      self.currAtGeom = None
      self.currAtSubGeom = None

      self.nOperationsToUndo = 0

   def __del__(self):
      QadCommandClass.__del__(self)
      del self.SSGetClass
      self.poligonEntity.deselectOnLayer()

   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      if self.step == 1 or self.step == 4: # when you are in the entity selection phase
         return self.entSelClass.getPointMapTool(drawMode)
      elif self.step == 3 or self.step == 5 or \
           self.step == 6 or self.step == 7 or self.step == 8: # when you are in the entity group selection phase
         return self.SSGetClass.getPointMapTool()
      else:
         return QadCommandClass.getPointMapTool(self, drawMode)


   def getCurrentContextualMenu(self):
      if self.step == 1 or self.step == 4: # when you are in the entity selection phase
         return self.entSelClass.getCurrentContextualMenu()
      elif self.step == 3 or self.step == 5 or \
           self.step == 6 or self.step == 7 or self.step == 8: # when you are in the entity group selection phase
         return None # return self.SSGetClass.getCurrentContextualMenu()
      else:
         return self.contextualMenu


   def reinitSSGetClass(self):
      checkPointLayer = self.SSGetClass.checkPointLayer
      del self.SSGetClass
      self.SSGetClass = QadSSGetClass(self.plugIn)
      self.SSGetClass.onlyEditableLayers = False
      self.SSGetClass.checkDimLayers = False # I discard the dimensions
      self.SSGetClass.checkPointLayer = checkPointLayer


   # ============================================================================
   # setCurrentSubGeom
   # ============================================================================
   def setCurrentSubGeom(self, entSelClass):
      """Sets the current subgeometry"""
      self.currAtGeom = None
      self.currAtSubGeom = None

      # I verify that an entity has been selected
      if entSelClass.entity.isInitialized() == False:
         self.showMsg(QadMsg.translate("QAD", "No geometries in this position."))
         return False
      # I verify that it has been selected through a point
      # (to understand which subgeometry has been selected)
      if entSelClass.point is None: return False
      # I verify that the same polygon that is to be modified has been selected
      if self.poligonEntity != entSelClass.entity:
         self.showMsg(QadMsg.translate("Command_MAPMPEDIT", "The boundary doesn't belong to the selected polygon."))
         return False

      qadGeom = entSelClass.entity.getQadGeom()

      # the function returns a list with
      # (<minimum distance>
      # <nearest vertex point>
      # <nearest geometry index>
      # <index of the nearest sub-geometry>
      # <index of the closest sub-geometry part>
      # <nearest vertex index>
      result = getQadGeomClosestVertex(qadGeom, entSelClass.point)
      self.currAtGeom = result[2]
      self.currAtSubGeom = result[3]

      return True


   # ============================================================================
   # addEntitySetToPolygon
   # ============================================================================
   def addEntitySetToPolygon(self, entitySet, removeOriginals = False):
      """Adds the entity set to the polygon to be modified"""
      geom = self.poligonEntity.getGeometry()
      layerList = []
      layerList.append(self.poligonEntity.layer)

      for layerEntitySet in entitySet.layerEntitySetList:
         layer = layerEntitySet.layer
         if layer.geometryType() != QgsWkbTypes.PolygonGeometry and layer.geometryType() != QgsWkbTypes.LineGeometry:
            self.showMsg(QadMsg.translate("QAD", "Invalid object."))
            return False

         if removeOriginals: layerList.append(layer)
         coordTransform = QgsCoordinateTransform(layer.crs(), self.poligonEntity.layer.crs(), QgsProject.instance())

         for featureId in layerEntitySet.featureIds:
            # if the feature is that of polygonEntity it is an error
            if layer.id() == self.poligonEntity.layerId() and featureId == self.poligonEntity.featureId:
               self.showMsg(QadMsg.translate("QAD", "Invalid object."))
               return False

            f = layerEntitySet.getFeature(featureId)
            # I transform the geometry into the crs of the layer of the polygon to be modified
            geomToAdd = f.geometry()
            geomToAdd.transform(coordTransform)

            # if the polygon is contained in the geometry to be added
            if geomToAdd.contains(geom):
               # I reduce the geometry to points or polylines
               simplifiedGeoms = qad_utils.asPointOrPolyline(geom)
               # must be a ringless polygon
               if len(simplifiedGeoms) != 1 or \
                 (simplifiedGeoms[0].isMultipart() == True or simplifiedGeoms[0].type() != QgsWkbTypes.LineGeometry):
                  self.showMsg(QadMsg.translate("QAD", "Invalid object."))
                  return False
               points = simplifiedGeoms[0].asPolyline() # vector of points
               # add an island
               if geomToAdd.addRing(points) != 0: # 0 in case of success
                  self.showMsg(QadMsg.translate("QAD", "Invalid object."))
                  return False
               del geom
               geom = QgsGeometry.fromPolygonXY(geomToAdd.asPolygon())
            else: # if the polygon is not contained in the geometry to be added
               # I reduce the geometry to points or polylines
               simplifiedGeoms = qad_utils.asPointOrPolyline(geomToAdd)
               for simplifiedGeom in simplifiedGeoms:
                  # if the geometry to be added is contained in the polygon
                  if geom.contains(simplifiedGeom):
                     points = simplifiedGeom.asPolyline() # vector of points
                     # add an island
                     if geom.addRing(points) != 0: # 0 in case of success
                        self.showMsg(QadMsg.translate("QAD", "Invalid object."))
                        return False
                  else:
                     # add a part
                     if geom.addPartGeometry(simplifiedGeom) != QgsGeometry.Success:
                        self.showMsg(QadMsg.translate("QAD", "Invalid object."))
                        return False

      f = self.poligonEntity.getFeature()
      f.setGeometry(geom)

      layerList = entitySet.getLayerList()
      layerList.append(self.poligonEntity.layer)

      self.plugIn.beginEditCommand("Feature edited", layerList)

      # plugin, layer, feature, refresh, check_validity
      if qad_layer.updateFeatureToLayer(self.plugIn, self.poligonEntity.layer, f, False, False) == False:
         self.plugIn.destroyEditCommand()
         return False

      if removeOriginals:
         for layerEntitySet in entitySet.layerEntitySetList:
            if qad_layer.deleteFeaturesToLayer(self.plugIn, layerEntitySet.layer, layerEntitySet.featureIds, False) == False:
               self.plugIn.destroyEditCommand()
               return

      self.plugIn.endEditCommand()
      self.nOperationsToUndo = self.nOperationsToUndo + 1

      return True


   # ============================================================================
   # delCurrentSubGeomToPolygon
   # ============================================================================
   def delCurrentSubGeomToPolygon(self):
      """Delete the current sub-geometry from the polygon to be modified"""
      geom = self.poligonEntity.getGeometry()

      # the position is expressed with a list (<main object index> [<secondary object index>])
      part = self.currAtGeom
      if self.currAtSubGeom > 0:
         ring = self.currAtSubGeom
         if geom.deleteRing(ring, part) == False: # delete an island (Ring 0 is outer ring and can't be deleted)
            self.showMsg(QadMsg.translate("QAD", "Invalid object."))
            return False
      else:
         if geom.deletePart(part) == False: # delete a part
            self.showMsg(QadMsg.translate("QAD", "Invalid object."))
            return False

      f = self.poligonEntity.getFeature()
      f.setGeometry(geom)

      self.plugIn.beginEditCommand("Feature edited", self.poligonEntity.layer)

      # plugin, layer, feature, refresh, check_validity
      if qad_layer.updateFeatureToLayer(self.plugIn, self.poligonEntity.layer, f, False, False) == False:
         self.plugIn.destroyEditCommand()
         return False

      self.plugIn.endEditCommand()
      self.nOperationsToUndo = self.nOperationsToUndo + 1


   # ============================================================================
   # unionIntersSubtractEntitySetToPolygon
   # ============================================================================
   def unionIntersSubtractEntitySetToPolygon(self, entitySet, opType, removeOriginals = False):
      """
      Unisce o interseca i poligoni di entitySet al poligono corrente
      """
      geom = self.poligonEntity.getGeometry()
      layerList = []
      layerList.append(self.poligonEntity.layer)

      geomList = []
      geomList.append(geom)
      for layerEntitySet in entitySet.layerEntitySetList:
         del geomList[:]
         layer = layerEntitySet.layer
         coordTransform = QgsCoordinateTransform(layer.crs(), self.poligonEntity.layer.crs(), QgsProject.instance())

         if layer.geometryType() == QgsWkbTypes.PolygonGeometry:
            for featureId in layerEntitySet.featureIds:
               # if the feature is that of polygonEntity it is an error
               if layer.id() == self.poligonEntity.layerId() and featureId == self.poligonEntity.featureId:
                  self.showMsg(QadMsg.translate("QAD", "Invalid object."))
                  return False
               f = layerEntitySet.getFeature(featureId)
               # I transform the geometry into the crs of the layer of the polygon to be modified
               geomToAdd = f.geometry()

               geomToAdd.transform(coordTransform)

               if opType == QadMAPMPEDITCommandOpTypeEnum.UNION: geom = geom.combine(geomToAdd)
               elif opType == QadMAPMPEDITCommandOpTypeEnum.INTERSECTION: geom = geom.intersection(geomToAdd)
               elif opType == QadMAPMPEDITCommandOpTypeEnum.DIFFERENCE: geom = geom.difference(geomToAdd)

               if geom is None:
                  self.showMsg(QadMsg.translate("QAD", "Invalid object."))
                  return False

               if removeOriginals and layer.id() != self.poligonEntity.layerId():
                  layerList.append(layer)

         elif layer.geometryType() == QgsWkbTypes.LineGeometry:
            for featureId in layerEntitySet.featureIds:
               f = layerEntitySet.getFeature(featureId)
               # I transform the geometry into the crs of the layer of the polygon to be modified
               geomToAdd = f.geometry()
               geomToAdd.transform(coordTransform)
               # I reduce the geometry to points or polylines
               simplifiedGeoms = qad_utils.asPointOrPolyline(geomToAdd)
               for simplifiedGeom in simplifiedGeoms:
                  if simplifiedGeoms.isMultipart() == True or simplifiedGeoms.type() != QgsWkbTypes.LineGeometry:
                     self.showMsg(QadMsg.translate("QAD", "Invalid object."))
                     return False
                  points = simplifiedGeom.asPolyline() # vector of points

                  if len(points) < 4 or points[0] != points[-1]: # closed polyline with at least 4 points (first and last equal)
                     self.showMsg(QadMsg.translate("QAD", "Invalid object."))
                     return False
                  geomToAdd = QgsGeometry.fromPolygonXY([points])

                  if opType == QadMAPMPEDITCommandOpTypeEnum.UNION: geom = geom.combine(geomToAdd)
                  elif opType == QadMAPMPEDITCommandOpTypeEnum.INTERSECTION: geom = geom.intersection(geomToAdd)
                  elif opType == QadMAPMPEDITCommandOpTypeEnum.DIFFERENCE: geom = geom.difference(geomToAdd)

                  if geom is None or geom.type() != QgsWkbTypes.PolygonGeometry:
                     self.showMsg(QadMsg.translate("QAD", "Invalid object."))
                     return False

               if removeOriginals: layerList.append(layer)
         else:
            self.showMsg(QadMsg.translate("QAD", "Invalid object."))
            return False

      f = self.poligonEntity.getFeature()
      f.setGeometry(geom)

      self.plugIn.beginEditCommand("Feature edited", layerList)

      # plugin, layer, feature, refresh, check_validity
      if qad_layer.updateFeatureToLayer(self.plugIn, self.poligonEntity.layer, f, False, False) == False:
         self.plugIn.destroyEditCommand()
         return False

      if removeOriginals:
         for layerEntitySet in entitySet.layerEntitySetList:
            if qad_layer.deleteFeaturesToLayer(self.plugIn, layerEntitySet.layer, layerEntitySet.featureIds, False) == False:
               self.plugIn.destroyEditCommand()
               return

      self.plugIn.endEditCommand()
      self.nOperationsToUndo = self.nOperationsToUndo + 1

      return True


   # ============================================================================
   # convexHullEntitySetToPolygon
   # ============================================================================
   def convexHullEntitySetToPolygon(self, entitySet, removeOriginals = False):
      """modifies the current polygon so that it includes all the geometry points of the entitySet"""
      layerList = []
      layerList.append(self.poligonEntity.layer)
      pointsForConvexHull = []

      for layerEntitySet in entitySet.layerEntitySetList:
         layer = layerEntitySet.layer
         coordTransform = QgsCoordinateTransform(layer.crs(), self.poligonEntity.layer.crs(), QgsProject.instance())

         for featureId in layerEntitySet.featureIds:
            f = layerEntitySet.getFeature(featureId)
            # I transform the geometry into the crs of the layer of the polygon to be modified
            geom = f.geometry()
            geom.transform(coordTransform)

            # I reduce the geometry to points or polylines
            simplifiedGeoms = qad_utils.asPointOrPolyline(geom)
            for simplifiedGeom in simplifiedGeoms:
               gType = simplifiedGeom.type()
               if simplifiedGeom.isMultipart() == False and simplifiedGeom.isMultipart() == False:
                  pointsForConvexHull.extend(simplifiedGeom.asPolyline())
               else:
                  pointsForConvexHull.append(simplifiedGeom.asPoint())

            if removeOriginals and layer.id() != self.poligonEntity.layerId():
               layerList.append(layer)

      geom = QgsGeometry.fromMultiPointXY(pointsForConvexHull)
      geom = geom.convexHull()
      if geom is None:
         self.showMsg(QadMsg.translate("QAD", "Invalid object."))
         return False

      f = self.poligonEntity.getFeature()
      f.setGeometry(geom)

      self.plugIn.beginEditCommand("Feature edited", layerList)

      # plugin, layer, feature, refresh, check_validity
      if qad_layer.updateFeatureToLayer(self.plugIn, self.poligonEntity.layer, f, False, False) == False:
         self.plugIn.destroyEditCommand()
         return False

      if removeOriginals:
         for layerEntitySet in entitySet.layerEntitySetList:
            if qad_layer.deleteFeaturesToLayer(self.plugIn, layerEntitySet.layer, layerEntitySet.featureIds, False) == False:
               self.plugIn.destroyEditCommand()
               return

      self.plugIn.endEditCommand()
      self.nOperationsToUndo = self.nOperationsToUndo + 1

      return True


   # ============================================================================
   # dividePolygon
   # ============================================================================
   def splitPolygon(self, splitLine, createNewEntities):
      """divides the current polygon using a polyline with vertices in <plineVertices> in order to generate new entities or not"""
      layerList = []
      layerList.append(self.poligonEntity.layer)

      splitLineTransformed = self.mapToLayerCoordinates(self.poligonEntity.layer, splitLine)
      f = self.poligonEntity.getFeature()
      oldGeom = f.geometry()
      result, newGeoms, topologyTestPts = oldGeom.splitGeometry(splitLineTransformed, False) # Set to true if you want to split a feature, otherwise set to false to split parts

      if result != QgsGeometry.Success or len(newGeoms) == 0:
         self.showMsg(QadMsg.translate("QAD", "Invalid object."))
         return False

      f.setGeometry(oldGeom)
      self.plugIn.beginEditCommand("Feature edited", layerList)
      # plugin, layer, feature, refresh, check_validity
      if qad_layer.updateFeatureToLayer(self.plugIn, self.poligonEntity.layer, f, False, False) == False:
         self.plugIn.destroyEditCommand()
         return False

      if len(newGeoms) > 0:
         newfeatures =[]
         if createNewEntities:
            for newGeom in newGeoms:
               newfeature = QgsFeature(f)
               newfeature.setGeometry(newGeom)
               newfeatures.append(newfeature)

            # plugin, layer, features, coordTransform, refresh, check_validity
            if qad_layer.addFeaturesToLayer(self.plugIn, self.poligonEntity.layer, newfeatures, None, False, False) == False:
               self.plugIn.destroyEditCommand()
               return
         else:
            for newGeom in newGeoms:
               if oldGeom.addPartGeometry(newGeom) != QgsGeometry.Success:
                  return False
            f.setGeometry(oldGeom)

            # plugin, layer, feature, refresh, check_validity
            if qad_layer.updateFeatureToLayer(self.plugIn, self.poligonEntity.layer, f, False, False) == False:
               self.plugIn.destroyEditCommand()
               return False
      self.nOperationsToUndo = self.nOperationsToUndo + 1

      self.plugIn.endEditCommand()

      return True



   # ============================================================================
   # waitForEntsel
   # ============================================================================
   def waitForEntsel(self, msgMapTool, msg):
      if self.entSelClass is not None:
         del self.entSelClass
      self.step = 1
      self.entSelClass = QadEntSelClass(self.plugIn)
      self.entSelClass.msg = QadMsg.translate("Command_MAPMPEDIT", "Select polygon: ")
      # I discard the selection of points and polylines
      self.entSelClass.checkPointLayer = False
      self.entSelClass.checkLineLayer = False
      self.entSelClass.checkPolygonLayer = True
      self.entSelClass.checkDimLayers = False
      self.entSelClass.onlyEditableLayers = True

      self.entSelClass.run(msgMapTool, msg)


   # ============================================================================
   # WaitForMainMenu
   # ============================================================================
   def WaitForMainMenu(self):
      self.poligonEntity.selectOnLayer(False)
      keyWords = QadMsg.translate("Command_MAPMPEDIT", "Add") + "/" + \
                 QadMsg.translate("Command_MAPMPEDIT", "dElete") + "/" + \
                 QadMsg.translate("Command_MAPMPEDIT", "Union") + "/" + \
                 QadMsg.translate("Command_MAPMPEDIT", "Substract") + "/" + \
                 QadMsg.translate("Command_MAPMPEDIT", "Intersect") + "/" + \
                 QadMsg.translate("Command_MAPMPEDIT", "split Objects") + "/" + \
                 QadMsg.translate("Command_MAPMPEDIT", "split Parts") + "/" + \
                 QadMsg.translate("Command_MAPMPEDIT", "iNclude objs")
      englishKeyWords = "Add" + "/" + "dElete" + "/" + "Union" + "/" + "Substract" + "/" + "Intersect" "/" + \
                        "split Objects" + "/" + "split Parts" + "/" + "iNclude objs"

      if self.nOperationsToUndo > 0: # if there is something that can be undone
         keyWords = keyWords + "/" +  QadMsg.translate("Command_MAPMPEDIT", "unDo")
         englishKeyWords = englishKeyWords + "/" + "unDo"

      keyWords = keyWords + "/" + QadMsg.translate("Command_MAPMPEDIT", "eXit")
      englishKeyWords = englishKeyWords + "/" + "eXit"

      default = QadMsg.translate("Command_MAPMPEDIT", "eXit")

      prompt = QadMsg.translate("Command_MAPMPEDIT", "Enter an option [{0}] <{1}>: ").format(keyWords, default)

      self.step = 2
      self.getPointMapTool().setSelectionMode(QadGetPointSelectionModeEnum.NONE)
      self.getPointMapTool().setDrawMode(QadGetPointDrawModeEnum.NONE)

      keyWords += "_" + englishKeyWords
      # is preparing to wait for enter or a keyword
      # msg, inputType, default, keyWords, no check
      self.waitFor(prompt, \
                   QadInputTypeEnum.KEYWORDS, \
                   None, \
                   keyWords, QadInputModeEnum.NONE)
      return False


   # ============================================================================
   # waitForBoundary
   # ============================================================================
   def waitForBoundary(self, msgMapTool, msg):
      if self.entSelClass is not None:
         del self.entSelClass
      self.entSelClass = QadEntSelClass(self.plugIn)
      self.entSelClass.msg = QadMsg.translate("Command_MAPMPEDIT", "Select boundary: ")
      # I discard the selection of points and polylines
      self.entSelClass.checkPointLayer = False
      self.entSelClass.checkLineLayer = False
      self.entSelClass.checkPolygonLayer = True
      self.entSelClass.checkDimLayers = False
      self.entSelClass.onlyEditableLayers = True

      self.entSelClass.run(msgMapTool, msg)


   def run(self, msgMapTool = False, msg = None):
      if self.plugIn.canvas.mapSettings().destinationCrs().isGeographic():
         self.showMsg(QadMsg.translate("QAD", "\nThe coordinate reference system of the project must be a projected coordinate system.\n"))
         return True # end command

      if self.step == 0:
         self.waitForEntsel(msgMapTool, msg) # select the polygon to modify
         return False # continua

      # =========================================================================
      # RESPONSE TO THE POLYGON SELECTION TO MODIFY
      elif self.step == 1:
         if self.entSelClass.run(msgMapTool, msg) == True:
            if self.entSelClass.entity.isInitialized():
               self.poligonEntity.set(self.entSelClass.entity.layer, self.entSelClass.entity.featureId)
               layer = self.entSelClass.entity.layer
               self.poligonEntity.deselectOnLayer()
               self.WaitForMainMenu()
            else:
               if self.entSelClass.canceledByUsr == True: # end command
                  return True
               self.showMsg(QadMsg.translate("QAD", "No geometries in this position."))
               self.waitForEntsel(msgMapTool, msg)

         return False # continua

      # =========================================================================
      # RESPONSE TO THE MAIN MENU REQUEST
      elif self.step == 2: # after waiting for an option the command is restarted
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

            self.WaitForMainMenu()
            return False
         else: # the option comes as a function parameter
            value = msg

         self.poligonEntity.deselectOnLayer()

         if value == QadMsg.translate("Command_MAPMPEDIT", "Add") or value == "Add":
            self.SSGetClass.checkPointLayer = False # I discard the point
            self.SSGetClass.run(msgMapTool, msg)
            self.step = 3
            return False
         elif value == QadMsg.translate("Command_MAPMPEDIT", "dElete") or value == "Delete":
            self.waitForBoundary(msgMapTool, msg)
            self.step = 4
            return False
         elif value == QadMsg.translate("Command_MAPMPEDIT", "Union") or value == "Union":
            self.SSGetClass.checkPointLayer = False # discard point layers
            self.SSGetClass.run(msgMapTool, msg)
            self.step = 5
            return False
         elif value == QadMsg.translate("Command_MAPMPEDIT", "Substract") or value == "Substract":
            self.SSGetClass.checkPointLayer = False # discard point layers
            self.SSGetClass.run(msgMapTool, msg)
            self.step = 6
            return False
         elif value == QadMsg.translate("Command_MAPMPEDIT", "Intersect") or value == "Intersect":
            self.SSGetClass.checkPointLayer = False # discard point layers
            self.SSGetClass.run(msgMapTool, msg)
            self.step = 7
            return False
         elif value == QadMsg.translate("Command_MAPMPEDIT", "split Objects") or value == "split Objects":
            # Draws a polyline dividing the polygon
            self.PLINECommand = QadPLINECommandClass(self.plugIn)
            # if this flag = True the command is used within another command to draw a line
            # which will not be saved on a layer
            self.PLINECommand.virtualCmd = True
            self.PLINECommand.run(msgMapTool, msg)
            self.step = 9
            return False
         elif value == QadMsg.translate("Command_MAPMPEDIT", "split Parts") or value == "split Parts":
            # Draws a polyline dividing the polygon
            self.PLINECommand = QadPLINECommandClass(self.plugIn)
            # if this flag = True the command is used within another command to draw a line
            # which will not be saved on a layer
            self.PLINECommand.virtualCmd = True
            self.PLINECommand.run(msgMapTool, msg)
            self.step = 10
            return False
         elif value == QadMsg.translate("Command_MAPMPEDIT", "iNclude objs") or value == "iNclude objs":
            self.SSGetClass.checkPointLayer = True # include point layers
            self.SSGetClass.run(msgMapTool, msg)
            self.step = 8
            return False
         elif value == QadMsg.translate("Command_MAPMPEDIT", "unDo") or value == "unDo":
            if self.nOperationsToUndo > 0:
               self.nOperationsToUndo = self.nOperationsToUndo - 1
               self.plugIn.undoEditCommand()
            else:
               self.showMsg(QadMsg.translate("QAD", "\nThe command has been canceled."))
         elif value == QadMsg.translate("Command_MAPMPEDIT", "eXit") or value == "eXit":
            return True # end command
         else:
            return True # end command

         self.WaitForMainMenu()
         return False

      # =========================================================================
      # RESPONSE TO THE ADD MODE REQUEST (from step = 2)
      elif self.step == 3:
         if self.SSGetClass.run(msgMapTool, msg) == True:
            if self.SSGetClass.entitySet.count() > 0:
               self.addEntitySetToPolygon(self.SSGetClass.entitySet)
            self.reinitSSGetClass()
            self.WaitForMainMenu()
         return False

      # =========================================================================
      # RESPONSE TO THE DELETE MODE REQUEST (from step = 2)
      elif self.step == 4:
         if self.entSelClass.run(msgMapTool, msg) == True:
            if self.setCurrentSubGeom(self.entSelClass) == True:
               self.delCurrentSubGeomToPolygon()
               self.WaitForMainMenu()
               return False
            else:
               if self.entSelClass.canceledByUsr == True: # end entity selection
                  self.WaitForMainMenu()
               else:
                  self.waitForBoundary(msgMapTool, msg)
         return False # continua

      # =========================================================================
      # RESPONSE TO THE UNION MODE REQUEST (from step = 2)
      elif self.step == 5: # after waiting for an entity the command restarts
         if self.SSGetClass.run(msgMapTool, msg) == True:
            if self.SSGetClass.entitySet.count() > 0:
               self.unionIntersSubtractEntitySetToPolygon(self.SSGetClass.entitySet, QadMAPMPEDITCommandOpTypeEnum.UNION)
            self.reinitSSGetClass()
            self.WaitForMainMenu()
         return False # continua

      # =========================================================================
      # RESPONSE TO THE SUBTRACT MODE REQUEST (from step = 2)
      elif self.step == 6: # after waiting for an entity the command restarts
         if self.SSGetClass.run(msgMapTool, msg) == True:
            if self.SSGetClass.entitySet.count() > 0:
               self.unionIntersSubtractEntitySetToPolygon(self.SSGetClass.entitySet, QadMAPMPEDITCommandOpTypeEnum.DIFFERENCE)
            self.reinitSSGetClass()
            self.WaitForMainMenu()
         return False # continua

      # =========================================================================
      # RESPONSE TO THE INTERSECT MODE REQUEST (from step = 2)
      elif self.step == 7: # after waiting for an entity the command restarts
         if self.SSGetClass.run(msgMapTool, msg) == True:
            if self.SSGetClass.entitySet.count() > 0:
               self.unionIntersSubtractEntitySetToPolygon(self.SSGetClass.entitySet, QadMAPMPEDITCommandOpTypeEnum.INTERSECTION)
            self.reinitSSGetClass()
            self.WaitForMainMenu()
         return False # continua

      # =========================================================================
      # RESPONSE TO THE INCLUDE OBJS MODE REQUEST (from step = 2)
      elif self.step == 8: # after waiting for an entity the command restarts
         if self.SSGetClass.run(msgMapTool, msg) == True:
            if self.SSGetClass.entitySet.count() > 0:
               self.convexHullEntitySetToPolygon(self.SSGetClass.entitySet)
            self.reinitSSGetClass()
            self.WaitForMainMenu()
         return False # continua

      # =========================================================================
      # RESPONSE TO DIVISION LINE REQUEST (from step = 2)
      elif self.step == 9: # after waiting for a point the command restarts
         if self.PLINECommand.run(msgMapTool, msg) == True:
            self.showMsg("\n")
            self.splitPolygon(self.PLINECommand.polyline.asPolyline(), True)
            del self.PLINECommand
            self.PLINECommand = None
            self.WaitForMainMenu()
         return False

      # =========================================================================
      # RESPONSE TO DIVISION LINE REQUEST (from step = 2)
      elif self.step == 10: # after waiting for a point the command restarts
         if self.PLINECommand.run(msgMapTool, msg) == True:
            self.showMsg("\n")
            self.splitPolygon(self.PLINECommand.polyline.asPolyline(), False)
            del self.PLINECommand
            self.PLINECommand = None
            self.WaitForMainMenu()
         return False
