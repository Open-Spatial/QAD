# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 class for managing entities

                              -------------------
        begin                : 2013-08-22
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
from qgis.core import *
from qgis.utils import iface
import sys


from . import qad_label
from . import qad_layer
from . import qad_stretch_fun
from . import qad_utils
from .qad_multi_geom import *
from .qad_variables import QadVariables


# ===============================================================================
# QadEntityTypeEnum class.
# ===============================================================================
class QadEntityTypeEnum():
   NONE                = 0
   SYMBOL              = 1
   TEXT                = 2
   LINEAROBJ           = 3 # line, arc, circle, ellipse arc, ellipse, polyline (and multi)
   POLYGON             = 4 # polygon (and multi)


# ===============================================================================
# QadEntity entity class
# ===============================================================================
class QadEntity():

   def __init__(self, entity = None):
      self.entityType = QadEntityTypeEnum.NONE

      if entity is not None:
         self.set(entity)
      else:
         self.layer = None
         self.featureId = None
         # single qad geometry (point, line, arc, circle, ellipse arc, ellipse, polyline, polygon)
         # or multiple (multipoint, multi linear object, multi polygon)
         self.qadGeom = None # in the canvas crs to work with xy plane coordinates
         self.isTextualLayer = False
         self.isSymbolLayer = False
         self.rotFldName = "" # field used for rotating texts or symbols


   def whatIs(self):
      return "ENTITY"


   # ===============================================================================
   # set
   # ===============================================================================
   def set(self, layer_or_entity, featureId = None):
      self.clear()
      if isinstance(layer_or_entity, QgsVectorLayer):
         self.layer = layer_or_entity # the layer cannot be copied
         self.featureId = featureId # copy the feature identifier
      else: # layer is an entity
         self.layer = layer_or_entity.layer
         self.featureId = layer_or_entity.featureId

         self.entityType = layer_or_entity.entityType
         self.qadGeom = None if layer_or_entity.qadGeom is None else layer_or_entity.qadGeom.copy() # I copy the geometry
         self.isTextualLayer = layer_or_entity.isTextualLayer
         self.isSymbolLayer = layer_or_entity.isSymbolLayer
         self.rotFldName = layer_or_entity.rotFldName

      return self


   def __initQadInfo(self):
      # inizializza entityType, qadGeom, dimStyle, dimId, isTextualLayer, isSymbolLayer
      if self.qadGeom is not None:
         return self.entityType

      if self.isInitialized() == False:
         return QadEntityTypeEnum.NONE

      self.entityType = QadEntityTypeEnum.NONE
      self.isTextualLayer = False
      self.isSymbolLayer = False
      self.rotFldName = "" # field used for rotating texts or symbols

      layerGeomType = self.layer.geometryType()

      if layerGeomType == QgsWkbTypes.PointGeometry:
         if qad_layer.isTextLayer(self.layer):
            self.isTextualLayer = True
            self.entityType = QadEntityTypeEnum.TEXT
            # if the rotation depends on only one field
            rotFldNames = qad_label.get_labelRotationFieldNames(self.layer)
            if len(rotFldNames) == 1 and len(rotFldNames[0]) > 0:
               self.rotFldName = rotFldNames[0]

         elif qad_layer.isSymbolLayer(self.layer):
            self.isSymbolLayer = True
            self.entityType = QadEntityTypeEnum.SYMBOL
            self.rotFldName = qad_layer.get_symbolRotationFieldName(self.layer)

      elif layerGeomType == QgsWkbTypes.LineGeometry:
            self.entityType = QadEntityTypeEnum.LINEAROBJ
      elif layerGeomType == QgsWkbTypes.PolygonGeometry:
            self.entityType = QadEntityTypeEnum.POLYGON

      g = self.getGeometry()
      if g is None:
         return QadEntityTypeEnum.NONE

      self.qadGeom = fromQgsGeomToQadGeom(g, self.layer.crs())
      if self.qadGeom is None: return QadEntityTypeEnum.NONE

      qadGeomType = self.qadGeom.whatIs()
      layerGeomType = self.layer.geometryType()

      return self.entityType


   def getEntityType(self):
      return self.entityType


   def getQadGeom(self, atGeom = None, atSubGeom = None):
      self.__initQadInfo()
      if atGeom is None and atSubGeom is None:
         return self.qadGeom
      else:
         return getQadGeomAt(self.qadGeom, atGeom, atSubGeom)


   def isInitialized(self):
      if (self.layer is None) or (self.featureId is None):
         return False
      else:
         return True


   def clear(self):
      self.layer = None
      self.featureId = None
      self.entityType = QadEntityTypeEnum.NONE
      self.qadGeom = None
      self.isTextualLayer = False
      self.isSymbolLayer = False
      self.rotFldName = ""


   def __eq__(self, entity):
      """self == other"""
      if self.isInitialized() == False or entity.isInitialized() == False :
         return False

      if self.layerId() == entity.layerId() and self.featureId == entity.featureId:
         return True
      else:
         return False


   def __ne__(self, entity):
      """self != other"""
      if self.isInitialized() == False or entity.isInitialized() == False:
         return True

      if self.layerId() != entity.layerId() or self.featureId != entity.featureId:
         return True
      else:
         return False


   def layerId(self):
      if self.isInitialized() == False:
         return None
      return self.layer.id()


   def crs(self):
      if self.isInitialized() == False:
         return None
      return self.layer.crs()


   def copy(self):
      return QadEntity(self)


   def getFeature(self):
      if self.isInitialized() == False:
         return None

      return qad_utils.getFeatureById(self.layer, self.featureId)


   def exists(self):
      if self.getFeature() is None:
         return False
      else:
         return True


   def getGeometry(self, destCRS = None):
      feature = self.getFeature()
      if feature is None:
         return None
      g = QgsGeometry(feature.geometry()) # makes a copy
      if destCRS is not None and destCRS != self.crs():
         coordTransform = QgsCoordinateTransform(self.crs(), destCRS, QgsProject.instance()) # transform the geometry into destCRS coordinates
         g.transform(coordTransform)

      return g



#    this function makes no sense because feature is a temporary local variable to which the geometry is set
#    but then, at the end of the function, it is destroyed.
#    def setGeometry(self, geom):
#       feature = self.getFeature()
#       if feature is None:
#          return None
#       return feature.setGeometry(geom)


   def getAttribute(self, attribName):
      feature = self.getFeature()
      if feature is None:
         return None
      try:
         return feature.attribute(attribName)
      except:
         return None


   def getAttributes(self):
      feature = self.getFeature()
      if feature is None:
         return None

      return feature.attributes()[:] # makes a copy


   def selectOnLayer(self, incremental = True):
      if self.isInitialized() == True:
         if incremental == False:
            self.layer.removeSelection()

         self.layer.select(self.featureId) # aaaaaaaaaaaaaaaaaaaaaaaaa here the activate event of qad_map tool starts


   def deselectOnLayer(self):
      if self.isInitialized() == False:
         return False

      self.layer.deselect(self.featureId)


# ===============================================================================
# QadCacheEntitySetIterator
# ===============================================================================
class QadCacheEntitySetIterator():
   # class to iterate the entities of a QadCacheEntitySet
   def __init__(self, cacheEntitySet):
      self.i = 0
      self.cacheEntitySet = cacheEntitySet

   def __iter__(self):
      return self

   def __next__(self):
      if self.i < len(self.cacheEntitySet.entityList):
         ent = self.cacheEntitySet.entityList[self.i]
         self.i += 1
         return ent
      else:
         raise StopIteration


# ===============================================================================
# QadCacheEntitySet
# ===============================================================================
class QadCacheEntitySet():
   """Class that manages a cache memory for entities"""

   # ============================================================================
   # __init__
   # ============================================================================
   def __init__(self):
      self.entityList = []


   # ============================================================================
   # __del__
   # ============================================================================
   def __del__(self):
      self.clear()


   # ============================================================================
   # clear
   # ============================================================================
   def clear(self):
      # clear cache
      for entity in self.entityList: del entity
      del self.entityList[:]


   # ============================================================================
   # isEmpty
   # ============================================================================
   def isEmpty(self):
      return True if len(self.entityList) == 0 else False


   # ============================================================================
   # count
   # ============================================================================
   def count(self):
      return len(self.entityList)


   # ============================================================================
   # getEntity
   # ============================================================================
   def getEntity(self, layerId, featureId):
      for entity in self.entityList:
         if entity.layerId() == layerId and entity.featureId == featureId:
            return entity
      return None


   # ============================================================================
   # appendEntity
   # ============================================================================
   def appendEntity(self, entity):
      clonedEntity = QadEntity(entity)
      self.entityList.append(clonedEntity) # I copy it
      return clonedEntity


   # ============================================================================
   # appendEntitySet
   # ============================================================================
   def appendEntitySet(self, entitySet):
      for layerEntitySet in entitySet.layerEntitySetList:
         entityIterator = QadLayerEntitySetIterator(layerEntitySet)
         for entity in entityIterator:
             self.appendEntity(entity)


   # ============================================================================
   # getLayerList
   # ============================================================================
   def getLayerList(self):
      layerList = []
      for entity in self.entityList:
         found = False
         for layer in layerList:
            if entity.layer.id() == layer.id():
               found = True
               break
         if found == False:
            layerList.append(entity.layer)

      return layerList


   # ============================================================================
   # getBoundingBox
   # ============================================================================
   def getBoundingBox(self):
      # returns the occupation rectangle of the entities
      result = None
      for entity in self.entityList:
         entBouningBox = entity.getQadGeom().getBoundingBox()
         if result is None:
            result = entBouningBox
         else:
            result.combineExtentWith(entBouningBox)
      return result


# ===============================================================================
# QadLayerEntitySetIterator
# ===============================================================================
class QadLayerEntitySetIterator():
   # class to iterate the entities of a QadLayerEntitySet
   def __init__(self, layerEntitySet):
      self.i = 0
      self.layerEntitySet = layerEntitySet
      self.ent = QadEntity()

   def __iter__(self):
      return self

   def __next__(self):
      if self.i < len(self.layerEntitySet.featureIds):
         self.ent.set(self.layerEntitySet.layer, self.layerEntitySet.featureIds[self.i])
         self.i += 1
         return self.ent
      else:
         raise StopIteration

   def next(self):
      return self.__next__()


# ===============================================================================
# QadLayerEntitySet entities of a layer class
# ===============================================================================
class QadLayerEntitySet():

   def __init__(self, layerEntitySet = None):

      if layerEntitySet is not None:
         self.set(layerEntitySet.layer, layerEntitySet.featureIds)
      else:
         self.layer = None
         self.featureIds = []


   def whatIs(self):
      return "LAYERENTITYSET"


   def isInitialized(self):
      if self.layer is None:
         return False
      else:
         return True


   def isEmpty(self):
      if self.isInitialized() == False:
         return True
      return not self.featureIds


   def count(self):
      if self.isInitialized() == False:
         return 0
      return len(self.featureIds)


   def clear(self):
      if self.isInitialized() == False:
         return 0
      self.layer = None
      del self.featureIds[:]


   def getEntities(self): # returns an iterator
      return QadLayerEntitySetIterator(self)


   def layerId(self):
      if self.isInitialized() == False:
         return None
      return self.layer.id()

   def crs(self):
      if self.isInitialized() == False:
         return None
      return self.layer.crs()

   def set(self, layer, features = None):
      if isinstance(layer, QgsVectorLayer):
         self.layer = layer # the layer cannot be copied
         self.featureIds = []
         if features is not None:
            self.addFeatures(features)
      else: # layer is an entity
         return self.set(layer.layer, layer.featureIds)


   def initByCurrentQgsSelectedFeatures(self, layer):
      self.clear()
      self.layer = layer
      self.featureIds = self.layer.selectedFeatureIds()


   def getFeature(self, featureId):
      if self.isInitialized() == False:
         return None
      return qad_utils.getFeatureById(self.layer, featureId)


   def getGeometry(self, featureId):
      feature = self.getFeature(featureId)
      if feature is None:
         return None
      return QgsGeometry(feature.geometry()) # makes a copy

   def setGeometry(self, featureId, geom):
      feature = self.getFeature(featureId)
      if feature is None:
         return None
      return feature.setGeometry(geom)


   def getGeometryCollection(self, destCRS = None):
      result = []
      if destCRS is not None:
         coordTransform = QgsCoordinateTransform(self.layer.crs(), destCRS, QgsProject.instance()) # I transform the geometry
      for featureId in self.featureIds:
         g = self.getGeometry(featureId)
         if g is not None:
            if destCRS is not None:
               g.transform(coordTransform)

               # Due to an unknown bug when I transform the geometry I then make a buffer of it
               # the calculation gives an incorrect result when the geometry is new or modified
               # (in the layer cache) and the coordinate system is different from that of the current map
               gType = g.type()
               if g.isMultipart() == False:
                  if gType == QgsWkbTypes.PointGeometry:
                     g = QgsGeometry().fromPointXY(g.asPoint())
                  elif gType == QgsWkbTypes.LineGeometry:
                     g = QgsGeometry().fromPolylineXY(g.asPolyline())
                  elif gType == QgsWkbTypes.PolygonGeometry:
                     g = QgsGeometry().fromPolygonXY(g.asPolygon())
               else:
                  if gType == QgsWkbTypes.PointGeometry:
                     g = QgsGeometry().fromMultiPointXY(g.asMultiPoint())
                  elif gType == QgsWkbTypes.LineGeometry:
                     g = QgsGeometry().fromMultiPolylineXY(g.asMultiPolyline())
                  elif gType == QgsWkbTypes.PolygonGeometry:
                     g = QgsGeometry().fromMultiPolygonXY(g.asMultiPolygon())

            result.append(g)
      return result


   def getFeatureCollection(self):
      result = []
      for featureId in self.featureIds:
         f = self.getFeature(featureId)
         if f is not None:
            result.append(f)
      return result


   def selectOnLayer(self, incremental = True):
      if self.isInitialized() == True:
         if len(self.featureIds) > 0:
            if incremental == False:
               self.layer.removeSelection()

            self.layer.select(self.featureIds)
         else:
            if incremental == False:
               self.layer.removeSelection()


   def deselectOnLayer(self):
      if self.isInitialized() == True:
         if len(self.featureIds) > 0:
            self.layer.deselect(self.featureIds)


   def containsFeature(self, feature):
      if self.isInitialized() == False:
         return False

      if type(feature) == QgsFeature:
         return feature.id() in self.featureIds
      else:
         return feature in self.featureIds


   def containsEntity(self, entity):
      if self.isInitialized() == False:
         return False

      if self.layerId() != entity.layerId():
         return False
      return containsFeature(entity.featureId)


   def addFeature(self, feature):
      if self.isInitialized() == False:
         return False

      if type(feature) == QgsFeature:
         if self.containsFeature(feature.id()) == False:
            self.featureIds.append(feature.id())
            return True
         else:
            return False
      else:
         if self.containsFeature(feature) == False:
            self.featureIds.append(feature)
            return True
         else:
            return False


   def removeFeature(self, feature):
      if self.isInitialized() == False:
         return False

      try:
         if type(feature) == QgsFeature:
            return self.featureIds.remove(feature.id())
         else:
            return self.featureIds.remove(feature)
      except:
         return None


   def addEntity(self, entity):
      if self.isInitialized() == False:
         self.set(entity.layer)
      else:
         if self.layerId() != entity.layerId():
            return

      self.addFeature(entity.featureId)


   def removeEntity(self, entity):
      if self.isInitialized() == False:
         return False

      if self.layerId() != entity.layerId():
         return False

      return self.removeFeature(entity.featureId)


   def addFeatures(self, features):
      if self.isInitialized() == False:
         return None
      for feature in features:
         if type(feature) == QgsFeature:
            self.addFeature(feature.id())
         else:
            self.addFeature(feature) # featureId


   def addLayerEntitySet(self, layerEntitySet):
      if self.isInitialized() == False:
         self.set(layerEntitySet.layer)
      else:
         if self.layerId() != layerEntitySet.layerId():
            return
      self.addFeatures(layerEntitySet.featureIds)


   def unite(self, layerEntitySet):
      if self.isInitialized() == False:
         return

      if self.layerId() == layerEntitySet.layerId():
         self.featureIds = list(set.union(set(self.featureIds), set(layerEntitySet.featureIds)))


   def intersect(self, layerEntitySet):
      if self.isInitialized() == False:
         return

      if self.layerId() == layerEntitySet.layerId():
         self.featureIds = list(set(self.featureIds) & set(layerEntitySet.featureIds))


   def subtract(self, layerEntitySet):
      if self.isInitialized() == False:
         return

      if self.layerId() == layerEntitySet.layerId():
         self.featureIds = list(set(self.featureIds) - set(layerEntitySet.featureIds))


   def getNotExistingFeaturedIds(self):
      featureIds = []
      if self.isInitialized() == True:
         feature = QadEntity()
         for featureId in self.featureIds:
            feature.set(self.layer, featureId)
            if not feature.exists():
               featureIds.append(featureId)
      return featureIds


   def removeNotExisting(self):
      featureIds = self.getNotExistingFeaturedIds()
      self.featureIds = list(set(self.featureIds) - set(featureIds))


   def boundingBox(self):
      # returns the occupation rectangle of the layer entities
      result = None
      geoms = self.getGeometryCollection()
      for g in geoms:
         if result is None:
            result = g.boundingBox()
         else:
            result.combineExtentWith(g.boundingBox())
      return result


# ===============================================================================
# QadEntitySetIterator
# ===============================================================================
class QadEntitySetIterator():
   # class to iterate the entities of a QadEntitySet
   def __init__(self, entitySet):
      self.i = 0
      self.entitySet = entitySet
      self.layerEntitySetIterator = None
      self.ent = QadEntity()

   def __iter__(self):
      return self

   def __next__(self):
      while self.i < len(self.entitySet.layerEntitySetList):
         if self.layerEntitySetIterator is None:
            self.layerEntitySetIterator = QadLayerEntitySetIterator(self.entitySet.layerEntitySetList[self.i])
         try:
            return self.layerEntitySetIterator.next()
         except StopIteration:
            self.i += 1
            del self.layerEntitySetIterator
            self.layerEntitySetIterator = None
      raise StopIteration


# ===============================================================================
# QadEntitySet entities of a layers class
# ===============================================================================
class QadEntitySet():

   def __init__(self, entitySet = None):
      self.layerEntitySetList = []
      if entitySet is not None:
         self.set(entitySet)


   def whatIs(self):
      return "ENTITYSET"


   def isEmpty(self):
      for layerEntitySet in self.layerEntitySetList:
         if layerEntitySet.isEmpty() == False:
            return False
      return True


   def count(self):
      tot = 0
      for layerEntitySet in self.layerEntitySetList:
         tot = tot + layerEntitySet.count()
      return tot


   def clear(self):
      del self.layerEntitySetList[:]


   def set(self, entitySet):
      self.clear()
      for layerEntitySet in entitySet.layerEntitySetList:
         self.addLayerEntitySet(layerEntitySet)


   def initByCurrentQgsSelectedFeatures(self, layers):
      self.clear()

      for layer in layers:
         if layer.selectedFeatureCount() > 0:
            layerEntitySet = QadLayerEntitySet()
            layerEntitySet.initByCurrentQgsSelectedFeatures(layer)
            self.layerEntitySetList.append(layerEntitySet)


   def findLayerEntitySet(self, layer):
      if layer is None:
         return None
      if isinstance(layer, QgsVectorLayer): # layers
         return self.findLayerEntitySet(layer.id())
      elif type(layer) == unicode: # layer id
         for layerEntitySet in self.layerEntitySetList:
            if layerEntitySet.layerId() == layer:
               return layerEntitySet
         return None
      else: # QadLayerEntitySet
         return self.findLayerEntitySet(layer.layer)


   def getLayerList(self):
      layerList = []
      for layerEntitySet in self.layerEntitySetList:
         layerList.append(layerEntitySet.layer)
      return layerList


   def getGeometryCollection(self, destCRS = None):
      result = []
      for layerEntitySet in self.layerEntitySetList:
         partial = layerEntitySet.getGeometryCollection(destCRS)
         if partial is not None:
            result.extend(partial)
      return result


   def getFeatureCollection(self):
      result = []
      for layerEntitySet in self.layerEntitySetList:
         partial = layerEntitySet.getFeatureCollection()
         if partial is not None:
            result.extend(partial)
      return result


   def selectOnLayer(self, incremental = True):
      for layerEntitySet in self.layerEntitySetList:
         layerEntitySet.selectOnLayer(incremental)


   def deselectOnLayer(self):
      for layerEntitySet in self.layerEntitySetList:
         layerEntitySet.deselectOnLayer()


   def containsEntity(self, entity):
      layerEntitySet = self.findLayerEntitySet(entity.layer)
      if layerEntitySet is None:
         return False
      return layerEntitySet.containsFeature(entity.featureId)


   def addEntity(self, entity):
      if entity is None or entity.isInitialized() == False:
         return False
      layerEntitySet = self.findLayerEntitySet(entity.layer)
      if layerEntitySet is None:
         layerEntitySet = QadLayerEntitySet()
         layerEntitySet.set(entity.layer)
         self.layerEntitySetList.append(layerEntitySet)
      return layerEntitySet.addFeature(entity.featureId)


   def removeEntity(self, entity):
      layerEntitySet = self.findLayerEntitySet(entity.layer)
      if layerEntitySet is None:
         return False
      return layerEntitySet.removeFeature(entity.featureId)


   def removeLayerEntitySet(self, layer):
      i = 0
      for layerEntitySet in self.layerEntitySetList:
         if layerEntitySet.id() == layer.id():
            del layerEntitySet[i]
            return True
         i = i + 1
      return False


   def addLayerEntitySet(self, layerEntitySet):
      _layerEntitySet = self.findLayerEntitySet(layerEntitySet)
      if _layerEntitySet is None:
         _layerEntitySet = QadLayerEntitySet()
         _layerEntitySet.set(layerEntitySet.layer)
         self.layerEntitySetList.append(_layerEntitySet)
      _layerEntitySet.addFeatures(layerEntitySet.featureIds)


   def unite(self, entitySet):
      if entitySet is None:
         return
      for layerEntitySet in entitySet.layerEntitySetList:
         _layerEntitySet = self.findLayerEntitySet(layerEntitySet)
         if _layerEntitySet is None:
            _layerEntitySet = QadLayerEntitySet()
            _layerEntitySet.set(layerEntitySet.layer)
            self.layerEntitySetList.append(_layerEntitySet)
         _layerEntitySet.unite(layerEntitySet)


   def intersect(self, entitySet):
      if entitySet is None:
         return
      for i in range(len(self.layerEntitySetList) - 1, -1, -1):
         _layerEntitySet = self.layerEntitySetList[i]
         layerEntitySet = entitySet.findLayerEntitySet(_layerEntitySet)
         if layerEntitySet is None:
            del self.layerEntitySetList[i]
         else:
            _layerEntitySet.intersect(layerEntitySet)


   def subtract(self, entitySet):
      if entitySet is None:
         return
      for _layerEntitySet in self.layerEntitySetList:
         layerEntitySet = entitySet.findLayerEntitySet(_layerEntitySet)
         if layerEntitySet is not None:
            _layerEntitySet.subtract(layerEntitySet)


   def removeNotExisting(self):
      for layerEntitySet in self.layerEntitySetList:
         layerEntitySet.removeNotExisting()


   def removeNotEditable(self):
      for i in range(len(self.layerEntitySetList) - 1, -1, -1):
         layerEntitySet = self.layerEntitySetList[i]
         if layerEntitySet.layer.isEditable() == False:
            del self.layerEntitySetList[i]


   def removeGeomType(self, type):
      for i in range(len(self.layerEntitySetList) - 1, -1, -1):
         layerEntitySet = self.layerEntitySetList[i]
         if layerEntitySet.layer.geometryType() == type:
            del self.layerEntitySetList[i]


   def purge(self):
      # removes layers with zero objects
      for i in range(len(self.layerEntitySetList) - 1, -1, -1):
         layerEntitySet = self.layerEntitySetList[i]
         if layerEntitySet.count() == 0:
            del self.layerEntitySetList[i]


   def boundingBox(self, destCRS):
      # returns the occupation rectangle of the selset
      result = None
      for layerEntitySet in self.layerEntitySetList:
         partial = layerEntitySet.boundingBox()
         if partial is not None:
            coordTransform = QgsCoordinateTransform(layerEntitySet.crs(), destCRS, QgsProject.instance()) # I transform the geometry
            if result is None:
               result = QgsRectangle(coordTransform.transform(partial.xMinimum(), partial.yMinimum()), \
                                     coordTransform.transform(partial.xMaximum(), partial.yMaximum()))
            else:
               result.combineExtentWith(QgsRectangle(coordTransform.transform(partial.xMinimum(), partial.yMinimum()), \
                                        coordTransform.transform(partial.xMaximum(), partial.yMaximum())))
      return result


# ===============================================================================
# getSelSet
# ===============================================================================
def getSelSet(mode, mQgsMapTool, points = None, \
              layersToCheck = None, checkPointLayer = True, checkLineLayer = True, checkPolygonLayer = True,
              onlyEditableLayers = False):
   """given a QgsMapTool, a selection mode and an optional list of points (in map coordinates),
      the function searces for entities.
      mode = "C" -> Crossing selection (inside and crossing)
             "CO" -> Crossing objects (inside and crossing)
             "CP" -> Crossing polygon (inside and crossing)
             "F" -> Fence selection (crossing)
             "W" -> Window selection (inside)
             "WO" -> Window objects (inside)
             "WP" -> Windows polygon (inside)
             "X" -> all
      layersToCheck = optional, list of layers to searc
      checkPointLayer = optional, consider point layers
      checkLineLayer = optional, consider line layers
      checkPolygonLayer = optional, consider polygon-type layers
      onlyEditableLayers = optional, consider layers editable
      Returns a QadEntitySet on success otherwise None
   """

   if checkPointLayer == False and checkLineLayer == False and checkPolygonLayer == False:
      return None

   entity = QadEntity()
   result = QadEntitySet()
   feature = QgsFeature()

   #QApplication.setOverrideCursor(Qt.WaitCursor)

   if layersToCheck is None:
      # All layers visible
      _layers = qad_utils.getVisibleVectorLayers(mQgsMapTool.canvas) # All vector layers visible
   else:
      # only the list passed as a parameter
      _layers = layersToCheck

   for layer in _layers: # cycle on layers
      # I only consider vector layers that are filtered by type
      if (layer.type() == QgsMapLayer.VectorLayer) and \
          ((layer.geometryType() == QgsWkbTypes.PointGeometry and checkPointLayer == True) or \
           (layer.geometryType() == QgsWkbTypes.LineGeometry and checkLineLayer == True) or \
           (layer.geometryType() == QgsWkbTypes.PolygonGeometry and checkPolygonLayer == True)) and \
           (onlyEditableLayers == False or layer.isEditable()):
         provider = layer.dataProvider()

         if mode.upper() == "X": # take all features
            # fetchAttributes, fetchGeometry, rectangle, useIntersect
            for feature in layer.getFeatures(qad_utils.getFeatureRequest([], True,  None, False)):
               entity.set(layer, feature.id())
               result.addEntity(entity)

         elif mode.upper() == "C": # crossing selection
            p1 = mQgsMapTool.toLayerCoordinates(layer, points[0])
            p2 = mQgsMapTool.toLayerCoordinates(layer, points[1])
            selectRect = QgsRectangle(p1, p2)
            # Select features in rectangle
            # fetchAttributes, fetchGeometry, rectangle, useIntersect
            for feature in layer.getFeatures(qad_utils.getFeatureRequest([], True, selectRect, True)):
               entity.set(layer, feature.id())
               result.addEntity(entity)

         elif mode.upper() == "W": # window selection
            p1 = mQgsMapTool.toLayerCoordinates(layer, points[0])
            p2 = mQgsMapTool.toLayerCoordinates(layer, points[1])
            selectRect = QgsRectangle(p1, p2)
            g = QgsGeometry.fromRect(selectRect)
            # Select features in rectangle
            # fetchAttributes, fetchGeometry, rectangle, useIntersect
            for feature in layer.getFeatures(qad_utils.getFeatureRequest([], True, selectRect, True)):
               # only the features completely inside the rectangle
               if g.contains(feature.geometry()):
                  entity.set(layer, feature.id())
                  result.addEntity(entity)

         elif mode.upper() == "CP": # crossing polygon
            polyline = []
            for point in points:
               polyline.append(mQgsMapTool.toLayerCoordinates(layer, point))

            g = QgsGeometry.fromPolygonXY([polyline])
            # Select features in the polygon bounding box
            # fetchAttributes, fetchGeometry, rectangle, useIntersect
            for feature in layer.getFeatures(qad_utils.getFeatureRequest([], True, g.boundingBox(), True)):
               # only the features intersecting the polygon
               if g.intersects(feature.geometry()):
                  entity.set(layer, feature.id())
                  result.addEntity(entity)

         elif mode.upper() == "WP": # windows polygon
            polyline = []
            for point in points:
               polyline.append(mQgsMapTool.toLayerCoordinates(layer, point))

            g = QgsGeometry.fromPolygonXY([polyline])
            # Select features in the polygon bounding box
            # fetchAttributes, fetchGeometry, rectangle, useIntersect
            for feature in layer.getFeatures(qad_utils.getFeatureRequest([], True, g.boundingBox(), True)):
               # only features completely inside the polygon
               if g.contains(feature.geometry()):
                  entity.set(layer, feature.id())
                  result.addEntity(entity)

         elif mode.upper() == "CO": # crossing object
            # points is in this case a QgsGeometry
            g = QgsGeometry(points)
            if mQgsMapTool.canvas.mapSettings().destinationCrs() != layer.crs():
               coordTransform = QgsCoordinateTransform(mQgsMapTool.canvas.mapSettings().destinationCrs(), \
                                                       layer.crs(), \
                                                       QgsProject.instance()) # I transform the geometry
               g.transform(coordTransform)

            # Select features in the object bounding box
            if g.isMultipart() == False and g.type() == QgsWkbTypes.PointGeometry:
               Tolerance = QadVariables.get(QadMsg.translate("Environment variables", "PICKBOX")) # I read tolerance
               ToleranceInMapUnits = QgsTolerance.toleranceInMapUnits(Tolerance, layer, \
                                                                      mQgsMapTool.canvas.mapSettings(), \
                                                                      QgsTolerance.Pixels)

               pt = g.asPoint()
               # QgsRectangle (double xmin=0, double ymin=0, double xmax=0, double ymax=0)
               selectRect = QgsRectangle(pt.x() - ToleranceInMapUnits, pt.y() - ToleranceInMapUnits, \
                                         pt.x() + ToleranceInMapUnits, pt.y() + ToleranceInMapUnits)
               # fetchAttributes, fetchGeometry, rectangle, useIntersect
               request = qad_utils.getFeatureRequest([], True, selectRect, True)
            else:
               # fetchAttributes, fetchGeometry, rectangle, useIntersect
               request = qad_utils.getFeatureRequest([], True, g.boundingBox(), True)

            # fetchAttributes, fetchGeometry, rectangle, useIntersect
            for feature in layer.getFeatures(request):
               # only the features intersecting the object
               if g.intersects(feature.geometry()):
                  entity.set(layer, feature.id())
                  result.addEntity(entity)

         elif mode.upper() == "WO": # windows object
            # points is in this case a QgsGeometry
            g = QgsGeometry(points)
            if mQgsMapTool.canvas.mapSettings().destinationCrs() != layer.crs():
               coordTransform = QgsCoordinateTransform(mQgsMapTool.canvas.mapSettings().destinationCrs(), \
                                                       layer.crs(), \
                                                       QgsProject.instance()) # I transform the geometry
               g.transform(coordTransform)

            # Select features in the object bounding box
            if g.isMultipart() == False and g.type() == QgsWkbTypes.PointGeometry:
               Tolerance = QadVariables.get(QadMsg.translate("Environment variables", "PICKBOX")) # I read tolerance
               ToleranceInMapUnits = QgsTolerance.toleranceInMapUnits(Tolerance, layer, \
                                                                      mQgsMapTool.canvas.mapSettings(), \
                                                                      QgsTolerance.Pixels)

               pt = g.asPoint()
               selectRect = QgsRectangle(pt.x() - ToleranceInMapUnits, pt.y() - ToleranceInMapUnits, \
                                         pt.x() + ToleranceInMapUnits, pt.y() + ToleranceInMapUnits)
               # fetchAttributes, fetchGeometry, rectangle, useIntersect
               request = qad_utils.getFeatureRequest([], True, selectRect, True)
            else:
               # fetchAttributes, fetchGeometry, rectangle, useIntersect
               request = qad_utils.getFeatureRequest([], True, g.boundingBox(), True)

            gList = []
            if g.type() == QgsWkbTypes.LineGeometry:
               polygon = QadPolygon()

               if g.isMultipart() == False:
                  # if g is a linestring then I try to convert it to a polygon
                  if polygon.fromPolygon([g.asPolyline()]) == True:
                     gList.append(QgsGeometry.fromPolygonXY(polygon.asPolygon()))
               else:
                  # if g is a multilinestring then I try to convert it to a list of polygons if the linestrings are closed
                  multipolyline = g.asMultiPolyline()
                  for polyline in multipolyline:
                     if polygon.fromPolygon([polyline]) == True:
                        gList.append(QgsGeometry.fromPolygonXY(polygon.asPolygon()))
            else: # if it is not a linestring
               if g.type() == QgsWkbTypes.PolygonGeometry:
                  gList.append(g)

            # only features completely internal to the object
            for feature in layer.getFeatures(request):
               for g in gList:
                  if g.contains(feature.geometry()):
                     entity.set(layer, feature.id())
                     result.addEntity(entity)

         elif mode.upper() == "F": # fence
            polyline = []
            for point in points:
               polyline.append(mQgsMapTool.toLayerCoordinates(layer, point))

            g = QgsGeometry.fromPolylineXY(polyline)
            # Select features in the polyline bounding box
            # fetchAttributes, fetchGeometry, rectangle, useIntersect
            for feature in layer.getFeatures(qad_utils.getFeatureRequest([], True, g.boundingBox(), True)):
               # only the features that intersect the polyline
               if g.intersects(feature.geometry()):
                  entity.set(layer, feature.id())
                  result.addEntity(entity)

   #QApplication.restoreOverrideCursor()
   return result
