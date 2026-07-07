# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 JOIN and DISJOIN command to aggregate and disaggregate geometries
 (multipoint, multilinestring, polygon and multipolygon)

                              -------------------
        begin                : 2016-04-06
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
from qgis.core import QgsWkbTypes, QgsCoordinateTransform, QgsGeometry, QgsFeature, QgsProject


from .qad_generic_cmd import QadCommandClass
from ..qad_entity import QadEntity
from ..qad_getpoint import QadGetPointDrawModeEnum
from .qad_ssget_cmd import QadSSGetClass
from ..qad_msg import QadMsg
from .. import qad_utils
from .. import qad_layer
from .qad_entsel_cmd import QadEntSelClass



# Class that manages the JOIN command
class QadJOINCommandClass(QadCommandClass):

   def instantiateNewCmd(self):
      """instantiates a new command of the same type"""
      return QadJOINCommandClass(self.plugIn)

   def getName(self):
      return QadMsg.translate("Command_list", "JOIN")

   def getEnglishName(self):
      return "JOIN"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runJOINCommand)

   def getIcon(self):
      return QIcon(":/plugins/qad/icons/join.svg")

   def getNote(self):
      # set the explanatory notes of the command
      return QadMsg.translate("Command_JOIN", "Join existing geometries.")

   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)

      self.entity = QadEntity()

      self.SSGetClass = None
      self.entSelClass = None

   def __del__(self):
      QadCommandClass.__del__(self)
      if self.SSGetClass is not None:  del self.SSGetClass


   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      if self.step == 1: # when you are in the entity selection phase
         return self.entSelClass.getPointMapTool(drawMode)
      elif self.step == 2: # when you are in the entity group selection phase
         return self.SSGetClass.getPointMapTool()
      else:
         return QadCommandClass.getPointMapTool(self, drawMode)


   def getCurrentContextualMenu(self):
      if self.step == 1: # when you are in the entity selection phase
         return self.entSelClass.getCurrentContextualMenu()
      elif self.step == 2: # when you are in the entity group selection phase
         return None # return self.SSGetClass.getCurrentContextualMenu()()
      else:
         return self.contextualMenu


   def reinitSSGetClass(self):
      if self.SSGetClass is not None: del self.SSGetClass

      self.SSGetClass = QadSSGetClass(self.plugIn)
      self.SSGetClass.onlyEditableLayers = True
      self.SSGetClass.checkDimLayers = False # I discard the dimensions
      geometryType = self.entity.layer.geometryType()
      if geometryType == QgsWkbTypes.PointGeometry:
         self.SSGetClass.checkPointLayer = True
         self.SSGetClass.checkLineLayer = False
         self.SSGetClass.checkPolygonLayer = False
      elif geometryType == QgsWkbTypes.LineGeometry:
         self.SSGetClass.checkPointLayer = False
         self.SSGetClass.checkLineLayer = True
         self.SSGetClass.checkPolygonLayer = True
      elif geometryType == QgsWkbTypes.PolygonGeometry:
         self.SSGetClass.checkPointLayer = False
         self.SSGetClass.checkLineLayer = True
         self.SSGetClass.checkPolygonLayer = True


   # ============================================================================
   # addEntitySetToPoint
   # ============================================================================
   def addEntitySetToPoint(self, entitySet, removeOriginals = True):
      """Adds the entity set to the point to be modified"""
      geom = self.entity.getGeometry()
      layerList = []
      layerList.append(self.entity.layer)

      for layerEntitySet in entitySet.layerEntitySetList:
         layer = layerEntitySet.layer
         if layer.geometryType() != QgsWkbTypes.PointGeometry:
            self.showMsg(QadMsg.translate("QAD", "Invalid object."))
            return False

         if removeOriginals: layerList.append(layer)
         coordTransform = QgsCoordinateTransform(layer.crs(), self.entity.layer.crs(), QgsProject.instance())

         for featureId in layerEntitySet.featureIds:
            # if the feature is that of entity it is an error
            if layer.id() == self.entity.layerId() and featureId == self.entity.featureId:
               self.showMsg(QadMsg.translate("QAD", "Invalid object."))
               return False

            f = layerEntitySet.getFeature(featureId)
            # I transform the geometry into the crs of the layer of the entity to be modified
            geomToAdd = f.geometry()
            geomToAdd.transform(coordTransform)

            simplifiedGeoms = qad_utils.asPointOrPolyline(geomToAdd)
            for simplifiedGeom in simplifiedGeoms:
               # add a part
               if geom.addPartGeometry(simplifiedGeom) != QgsGeometry.Success:
                  self.showMsg(QadMsg.translate("QAD", "Invalid object."))
                  return False

      f = self.entity.getFeature()
      f.setGeometry(geom)

      layerList = entitySet.getLayerList()
      layerList.append(self.entity.layer)

      self.plugIn.beginEditCommand("Feature edited", layerList)

      # plugin, layer, feature, refresh, check_validity
      if qad_layer.updateFeatureToLayer(self.plugIn, self.entity.layer, f, False, False) == False:
         self.plugIn.destroyEditCommand()
         return False

      if removeOriginals:
         for layerEntitySet in entitySet.layerEntitySetList:
            if qad_layer.deleteFeaturesToLayer(self.plugIn, layerEntitySet.layer, layerEntitySet.featureIds, False) == False:
               self.plugIn.destroyEditCommand()
               return

      self.plugIn.endEditCommand()

      return True


   # ============================================================================
   # addEntitySetToPolyline
   # ============================================================================
   def addEntitySetToPolyline(self, entitySet, removeOriginals = True):
      """Adds the entity set to the polyline to be modified"""
      geom = self.entity.getGeometry()
      layerList = []
      layerList.append(self.entity.layer)

      for layerEntitySet in entitySet.layerEntitySetList:
         layer = layerEntitySet.layer
         if layer.geometryType() != QgsWkbTypes.PolygonGeometry and layer.geometryType() != QgsWkbTypes.LineGeometry:
            self.showMsg(QadMsg.translate("QAD", "Invalid object."))
            return False

         if removeOriginals: layerList.append(layer)
         coordTransform = QgsCoordinateTransform(layer.crs(), self.entity.layer.crs(), QgsProject.instance())

         for featureId in layerEntitySet.featureIds:
            # if the feature is that of entity it is an error
            if layer.id() == self.entity.layerId() and featureId == self.entity.featureId:
               self.showMsg(QadMsg.translate("QAD", "Invalid object."))
               return False

            f = layerEntitySet.getFeature(featureId)
            # I transform the geometry into the crs of the layer of the entity to be modified
            geomToAdd = f.geometry()
            geomToAdd.transform(coordTransform)

            # I reduce the geometry to points or polylines
            simplifiedGeoms = qad_utils.asPointOrPolyline(geomToAdd)
            for simplifiedGeom in simplifiedGeoms:
               if geom.addPartGeometry(simplifiedGeom) != QgsGeometry.Success:
                  self.showMsg(QadMsg.translate("QAD", "Invalid object."))
                  return False

      f = self.entity.getFeature()
      f.setGeometry(geom)

      layerList = entitySet.getLayerList()
      layerList.append(self.entity.layer)

      self.plugIn.beginEditCommand("Feature edited", layerList)

      # plugin, layer, feature, refresh, check_validity
      if qad_layer.updateFeatureToLayer(self.plugIn, self.entity.layer, f, False, False) == False:
         self.plugIn.destroyEditCommand()
         return False

      if removeOriginals:
         for layerEntitySet in entitySet.layerEntitySetList:
            if qad_layer.deleteFeaturesToLayer(self.plugIn, layerEntitySet.layer, layerEntitySet.featureIds, False) == False:
               self.plugIn.destroyEditCommand()
               return

      self.plugIn.endEditCommand()

      return True


   # ============================================================================
   # addEntitySetToPolygon
   # ============================================================================
   def addEntitySetToPolygon(self, entitySet, removeOriginals = True):
      """Adds the entity set to the polygon to be modified"""
      geom = self.entity.getGeometry()
      layerList = []
      layerList.append(self.entity.layer)

      for layerEntitySet in entitySet.layerEntitySetList:
         layer = layerEntitySet.layer
         if layer.geometryType() != QgsWkbTypes.PolygonGeometry and layer.geometryType() != QgsWkbTypes.LineGeometry:
            self.showMsg(QadMsg.translate("QAD", "Invalid object."))
            return False

         if removeOriginals: layerList.append(layer)
         coordTransform = QgsCoordinateTransform(layer.crs(), self.entity.layer.crs(), QgsProject.instance())

         for featureId in layerEntitySet.featureIds:
            # if the feature is that of entity it is an error
            if layer.id() == self.entity.layerId() and featureId == self.entity.featureId:
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

      f = self.entity.getFeature()
      f.setGeometry(geom)

      layerList = entitySet.getLayerList()
      layerList.append(self.entity.layer)

      self.plugIn.beginEditCommand("Feature edited", layerList)

      # plugin, layer, feature, refresh, check_validity
      if qad_layer.updateFeatureToLayer(self.plugIn, self.entity.layer, f, False, False) == False:
         self.plugIn.destroyEditCommand()
         return False

      if removeOriginals:
         for layerEntitySet in entitySet.layerEntitySetList:
            if qad_layer.deleteFeaturesToLayer(self.plugIn, layerEntitySet.layer, layerEntitySet.featureIds, False) == False:
               self.plugIn.destroyEditCommand()
               return

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
      self.entSelClass.msg = QadMsg.translate("Command_JOIN", "Select object to join to: ")
      # I discard the selection of dimensions
      self.entSelClass.checkDimLayers = False
      self.entSelClass.onlyEditableLayers = True
      self.entSelClass.deselectOnFinish = True

      self.entSelClass.run(msgMapTool, msg)


   # ============================================================================
   # waitForSSsel
   # ============================================================================
   def waitForSSsel(self, msgMapTool, msg):
      self.reinitSSGetClass()
      self.step = 2
      self.showMsg(QadMsg.translate("Command_JOIN", "\nSelect objects to join: "))
      self.SSGetClass.run(msgMapTool, msg)


   def run(self, msgMapTool = False, msg = None):
      if self.plugIn.canvas.mapSettings().destinationCrs().isGeographic():
         self.showMsg(QadMsg.translate("QAD", "\nThe coordinate reference system of the project must be a projected coordinate system.\n"))
         return True # end command

      if self.step == 0:
         self.waitForEntsel(msgMapTool, msg) # select the object to attach to
         return False # continua

      # =========================================================================
      # RESPONSE TO SELECTION OF ENTITY TO MODIFY
      elif self.step == 1:
         if self.entSelClass.run(msgMapTool, msg) == True:
            if self.entSelClass.entity.isInitialized():
               self.entity.set(self.entSelClass.entity)

               self.waitForSSsel(msgMapTool, msg)
            else:
               if self.entSelClass.canceledByUsr == True: # end command
                  return True
               self.showMsg(QadMsg.translate("QAD", "No geometries in this position."))
               self.waitForEntsel(msgMapTool, msg)

         return False # continua

      # =========================================================================
      # RESPONSE TO THE SELECTION GROUP'S REQUEST (from step = 1)
      elif self.step == 2:
         if self.SSGetClass.run(msgMapTool, msg) == True:
            if self.SSGetClass.entitySet.count() > 0:
               geometryType = self.entity.layer.geometryType()
               if geometryType == QgsWkbTypes.PointGeometry:
                  self.addEntitySetToPoint(self.SSGetClass.entitySet)
               elif geometryType == QgsWkbTypes.LineGeometry:
                  self.addEntitySetToPolyline(self.SSGetClass.entitySet)
               elif geometryType == QgsWkbTypes.PolygonGeometry:
                  self.addEntitySetToPolygon(self.SSGetClass.entitySet)

               return True

            self.waitForSSsel(msgMapTool, msg)
         return False


# Class that handles the DISJOIN command
class QadDISJOINCommandClass(QadCommandClass):

   def instantiateNewCmd(self):
      """instantiates a new command of the same type"""
      return QadDISJOINCommandClass(self.plugIn)

   def getName(self):
      return QadMsg.translate("Command_list", "DISJOIN")

   def getEnglishName(self):
      return "DISJOIN"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runDISJOINCommand)

   def getIcon(self):
      return QIcon(":/plugins/qad/icons/disjoin.svg")

   def getNote(self):
      # set the explanatory notes of the command
      return QadMsg.translate("Command_DISJOIN", "Disjoin existing geometries.")

   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)

      self.entity = QadEntity()

      self.SSGetClass = QadSSGetClass(plugIn)
      self.SSGetClass.onlyEditableLayers = False
      self.SSGetClass.checkDimLayers = False # I discard the dimensions

      self.entSelClass = None

      self.currSubGeom = None
      self.currAtSubGeom = None


   def __del__(self):
      QadCommandClass.__del__(self)
      del self.SSGetClass


   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      if self.step == 1: # when you are in the entity selection phase
         return self.entSelClass.getPointMapTool(drawMode)
      else:
         return QadCommandClass.getPointMapTool(self, drawMode)


   def getCurrentContextualMenu(self):
      if self.step == 1: # when you are in the entity selection phase
         return self.entSelClass.getCurrentContextualMenu()
      else:
         return self.contextualMenu


   # ============================================================================
   # setCurrentSubGeom
   # ============================================================================
   def setCurrentSubGeom(self, entSelClass):
      """Sets the current subgeometry"""
      self.currSubGeom = None
      self.currAtSubGeom = None

      # I verify that an entity has been selected
      if entSelClass.entity.isInitialized() == False:
         self.showMsg(QadMsg.translate("QAD", "No geometries in this position."))
         return False
      # I verify that it has been selected through a point
      # (to understand which subgeometry has been selected)
      if entSelClass.point is None: return False

      self.entity.set(entSelClass.entity)

      geom = self.layerToMapCoordinates(entSelClass.entity.layer, entSelClass.entity.getGeometry())

      # returns a tuple (<The squared cartesian distance>,
      #                    <minDistPoint>
      #                    <afterVertex>
      #                    <leftOf>)
      dummy = qad_utils.closestSegmentWithContext(entSelClass.point, geom)
      if dummy[2] is None:
         return False
      # returns the sub-geometry at the vertex <atVertex> and its position in the geometry (0-based)
      self.currSubGeom, self.currAtSubGeom = qad_utils.getSubGeomAtVertex(geom, dummy[2])
      if self.currSubGeom is None or self.currAtSubGeom is None:
         self.currSubGeom = None
         self.currAtSubGeom = None
         return False

      return True


   # ============================================================================
   # disjoinCurrentSubGeomToPolygon
   # ============================================================================
   def disjoinCurrentSubGeomToPolygon(self):
      """Disconnects the current sub-geometry of the polygon to be modified by creating a new entity"""
      layer = self.entity.layer
      # the position is expressed with a list (<main object index> [<secondary object index>])
      part = self.currAtSubGeom[0]
      ring = self.currAtSubGeom[1] if len(self.currAtSubGeom) == 2 else None

      geom = self.entity.getGeometry()
      gType = geom.type()

      if geom.isMultipart() == True and (gType == QgsWkbTypes.PointGeometry or gType == QgsWkbTypes.LineGeometry):
         if geom.deletePart(part) == False: # I disintegrate a part
            self.showMsg(QadMsg.translate("QAD", "Invalid object."))
            return False
         newGeom = self.mapToLayerCoordinates(layer, self.currSubGeom)
      elif gType == QgsWkbTypes.PolygonGeometry:
         if ring is not None: # I break up an island
            if geom.deleteRing(ring + 1, part) == False: # delete an island (Ring 0 is outer ring and can't be deleted)
               self.showMsg(QadMsg.translate("QAD", "Invalid object."))
               return False
            newGeom = QgsGeometry.fromPolygonXY([self.mapToLayerCoordinates(layer, self.currSubGeom).asPolyline()])
         else: # I disintegrate a part
            if geom.isMultipart() == False:
               self.showMsg(QadMsg.translate("QAD", "Invalid object."))
               return False

            newGeom = QgsGeometry.fromPolygonXY([self.mapToLayerCoordinates(layer, self.currSubGeom).asPolyline()])
            ring = 0
            ringGeom = qad_utils.getSubGeomAt(geom, [part, ring])
            # if the part has islands
            while ringGeom is not None:
               # add an island
               points = ringGeom.asPolyline() # vector of points
               if newGeom.addRing(points) != 0: # 0 in case of success
                  self.showMsg(QadMsg.translate("QAD", "Invalid object."))
                  return False
               ring = ring + 1
               ringGeom = qad_utils.getSubGeomAt(geom, [part, ring])

            if geom.deletePart(part) == False: # delete a part
               self.showMsg(QadMsg.translate("QAD", "Invalid object."))
               return False
      else:
         self.showMsg(QadMsg.translate("QAD", "Invalid object."))
         return False

      f = self.entity.getFeature()
      f.setGeometry(geom)

      self.plugIn.beginEditCommand("Feature edited", self.entity.layer)

      # plugin, layer, feature, refresh, check_validity
      if qad_layer.updateFeatureToLayer(self.plugIn, self.entity.layer, f, False, False) == False:
         self.plugIn.destroyEditCommand()
         return False

      # Add new feature
      newF = QgsFeature(f)
      newF.setGeometry(newGeom)
      if qad_layer.addFeatureToLayer(self.plugIn, self.entity.layer, newF, None, False, False) == False:
         self.plugIn.destroyEditCommand()
         return False

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
      self.entSelClass.msg = QadMsg.translate("Command_DISJOIN", "Select object to disjoin: ")
      # I discard the selection of dimensions
      self.entSelClass.checkDimLayers = False
      self.entSelClass.onlyEditableLayers = True
      self.entSelClass.deselectOnFinish = True

      self.entSelClass.run(msgMapTool, msg)


   def run(self, msgMapTool = False, msg = None):
      if self.plugIn.canvas.mapSettings().destinationCrs().isGeographic():
         self.showMsg(QadMsg.translate("QAD", "\nThe coordinate reference system of the project must be a projected coordinate system.\n"))
         return True # end command

      if self.step == 0:
         self.waitForEntsel(msgMapTool, msg) # select the object to disintegrate
         return False # continua

      # =========================================================================
      # RESPONSE TO SELECTION OF ENTITY TO MODIFY
      elif self.step == 1:
         if self.entSelClass.run(msgMapTool, msg) == True:
            if self.setCurrentSubGeom(self.entSelClass) == True:
               if self.disjoinCurrentSubGeomToPolygon() == True:
                  return True
            else:
               if self.entSelClass.canceledByUsr == True: # end command
                  return True
               self.showMsg(QadMsg.translate("QAD", "No geometries in this position."))

            self.waitForEntsel(msgMapTool, msg)

         return False # continua