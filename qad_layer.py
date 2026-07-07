# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 functions for layers

                              -------------------
        begin                : 2013-11-15
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
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui  import *
from qgis.core import *
from qgis.gui import *
import re # regular expression


from .qad_msg import QadMsg
from .qad_label import get_labelFieldNames


# ===============================================================================
# layerGeometryTypeToStr
# ===============================================================================
def layerGeometryTypeToStr(geomType):
   """returns the string corresponding to the geometry type of the layer"""
   msg = ""
   if (type(geomType) == list or type(geomType) == tuple): # if type list
      for gType in geomType:
         if len(msg) > 0:
            msg = msg + ", "
         msg = msg + layerGeometryTypeToStr(gType)
   else:
      if geomType == QgsWkbTypes.PointGeometry:
         msg = QadMsg.translate("QAD", "point")
      elif geomType == QgsWkbTypes.LineGeometry:
         msg = QadMsg.translate("QAD", "line")
      elif geomType == QgsWkbTypes.PolygonGeometry:
         msg = QadMsg.translate("QAD", "polygon")

   return msg


# ===============================================================================
# getCurrLayerEditable
# ===============================================================================
def getCurrLayerEditable(canvas, geomType = None):
   """Returns the current layer if it is updateable and compatible with the geomType + type
      any error message.
      If <geomType> is a list then check that it is compatible with at least one type in the <geomType> list
      otherwise if <> None checks whether it is compatible with the <geomType> type
   """
   vLayer = canvas.currentLayer()
   if vLayer is None:
      return None, QadMsg.translate("QAD", "\nNo current layer.\n")

   if (vLayer.type() != QgsMapLayer.VectorLayer):
      return None, QadMsg.translate("QAD", "\nThe current layer is not a vector layer.\n")

   if geomType is not None:
      if (type(geomType) == list or type(geomType) == tuple): # if type list
         if vLayer.geometryType() not in geomType:
            errMsg = QadMsg.translate("QAD", "\nThe geometry type of the current layer is {0} and it is not valid.\n")
            errMsg = errMsg + QadMsg.translate("QAD", "Admitted {1} layer type only.\n")
            errMsg.format(layerGeometryTypeToStr(vLayer.geometryType()), layerGeometryTypeToStr(geomType))
            return None, errMsg.format(layerGeometryTypeToStr(vLayer.geometryType()), layerGeometryTypeToStr(geomType))
      else:
         if vLayer.geometryType() != geomType:
            errMsg = QadMsg.translate("QAD", "\nThe geometry type of the current layer is {0} and it is not valid.\n")
            errMsg = errMsg + QadMsg.translate("QAD", "Admitted {1} layer type only.\n")
            errMsg.format(layerGeometryTypeToStr(vLayer.geometryType()), layerGeometryTypeToStr(geomType))
            return None, errMsg.format(layerGeometryTypeToStr(vLayer.geometryType()), layerGeometryTypeToStr(geomType))

   provider = vLayer.dataProvider()
   if not (provider.capabilities() & QgsVectorDataProvider.EditingCapabilities):
      return None, QadMsg.translate("QAD", "\nThe current layer is not editable.\n")

   if not vLayer.isEditable():
      return None, QadMsg.translate("QAD", "\nThe current layer is not editable.\n")

   return vLayer, None


# ===============================================================================
# addPointToLayer
# ===============================================================================
def addPointToLayer(plugIn, layer, point, transform = True, refresh = True, check_validity = False, openForm = True):
   """Adds a point to a layer. If the point is already
      in the coordinate system of the layer then it should not be transformed if instead it is in the
      map-coordinate system then transform must be = True
   """
   if transform:
      transformedPoint = plugIn.canvas.mapSettings().mapToLayerCoordinates(layer, point)
      g = QgsGeometry.fromPointXY(transformedPoint)
   else:
      g = QgsGeometry.fromPointXY(point)

   return addGeomToLayer(plugIn, layer, g, None, refresh, check_validity, openForm)

#    f = QgsFeature()
#
#    if transform:
#       transformedPoint = plugIn.canvas.mapSettings().mapToLayerCoordinates(layer, point)
#       g = QgsGeometry.fromPointXY(transformedPoint)
#    else:
#       g = QgsGeometry.fromPointXY(point)
#
#    if check_validity:
#       if not g.isGeosValid():
#          return False
#
#    f.setGeometry(g)
#
#    # Add attributefields to feature.
#    fields = layer.fields()
#    f.setFields(fields)
#
#    # assign default values
#    provider = layer.dataProvider()
#    for field in fields.toList():
#       i = fields.indexFromName(field.name())
#       f[field.name()] = provider.defaultValue(i)
#
#    if openForm == True:
#       if get_Disable_enter_attribute_values_dialog() == False:
#          if plugIn.iface.openFeatureForm(layer, f, True) == False:
#             return False
#
#    if refresh == True:
#       plugIn.beginEditCommand("Feature added", layer)
#
#    if layer.addFeature(f):
#       if refresh == True:
#          plugIn.endEditCommand()
#       plugIn.setLastEntity(layer, f.id())
#       result = True
#    else:
#       if refresh == True:
#          plugIn.destroyEditCommand()
#       result = False
#
#    return result


# ===============================================================================
# addLineToLayer
# ===============================================================================
def addLineToLayer(plugIn, layer, points, transform = True, refresh = True, check_validity = False, openForm = True):
   """Adds a line (list of points) to a layer. If the list of points is already
      in the coordinate system of the layer then it should not be transformed if instead it is in the
      map-coordinate system then transform must be = True
   """
   if len(points) < 2: # at least 2 points
      return False

   if transform:
      layerPoints = []
      for point in points:
         transformedPoint = plugIn.canvas.mapSettings().mapToLayerCoordinates(layer, point)
         layerPoints.append(transformedPoint)
      g = QgsGeometry.fromPolylineXY(layerPoints)
   else:
      g = QgsGeometry.fromPolylineXY(points)

   return addGeomToLayer(plugIn, layer, g, None, refresh, check_validity, openForm)

#    if len(points) < 2: # at least 2 points
#       return False
#
#    f = QgsFeature()
#
#    if transform:
#       layerPoints = []
#       for point in points:
#          transformedPoint = plugIn.canvas.mapSettings().mapToLayerCoordinates(layer, point)
#          layerPoints.append(transformedPoint)
#       g = QgsGeometry.fromPolylineXY(layerPoints)
#    else:
#       g = QgsGeometry.fromPolylineXY(points)
#
#    if check_validity:
#       if not g.isGeosValid():
#          return False
#
#    f.setGeometry(g)
#
#    # Add attributefields to feature.
#    fields = layer.fields()
#    f.setFields(fields)
#
#    # assign default values
#    provider = layer.dataProvider()
#    for field in fields.toList():
#       i = fields.indexFromName(field.name())
#       f[field.name()] = provider.defaultValue(i)
#
#    if openForm == True:
#       if get_Disable_enter_attribute_values_dialog() == False:
#          if plugIn.iface.openFeatureForm(layer, f, True) == False:
#             return False
#
#    if refresh == True:
#       plugIn.beginEditCommand("Feature added", layer)
#
#    if layer.addFeature(f):
#       if refresh == True:
#          plugIn.endEditCommand()
#       plugIn.setLastEntity(layer, f.id())
#       result = True
#    else:
#       if refresh == True:
#          plugIn.destroyEditCommand()
#       result = False
#
#    return result


# ===============================================================================
# addPolygonToLayer
# ===============================================================================
def addPolygonToLayer(plugIn, layer, points, transform = True, refresh = True, check_validity = False, openForm = True):
   """Adds a polygon (list of points) to a layer. If the list of points is already
      in the coordinate system of the layer then it should not be transformed if instead it is in the
      map-coordinate system then transform must be = True
   """
   if len(points) < 3: # at least 4 points (the first and last are the same)
      return False

   if transform:
      layerPoints = []
      for point in points:
         transformedPoint = plugIn.canvas.mapSettings().mapToLayerCoordinates(layer, point)
         layerPoints.append(transformedPoint)
      g = QgsGeometry.fromPolygonXY([layerPoints])
   else:
      g = QgsGeometry.fromPolygonXY([points])

   return addGeomToLayer(plugIn, layer, g, None, refresh, check_validity, openForm)

#    if len(points) < 3: # at least 4 points (the first and last are equal)
#       return False
#
#    f = QgsFeature()
#
#    if transform:
#       layerPoints = []
#       for point in points:
#          transformedPoint = plugIn.canvas.mapSettings().mapToLayerCoordinates(layer, point)
#          layerPoints.append(transformedPoint)
#       g = QgsGeometry.fromPolygonXY([layerPoints])
#    else:
#       g = QgsGeometry.fromPolygonXY([points])
#
#    if check_validity:
#       if not g.isGeosValid():
#          return False
#
#    f.setGeometry(g)
#
#    # Add attributefields to feature.
#    fields = layer.fields()
#    f.setFields(fields)
#
#    # assign default values
#    provider = layer.dataProvider()
#    for field in fields.toList():
#       i = fields.indexFromName(field.name())
#       f[field.name()] = provider.defaultValue(i)
#
#    if openForm == True:
#       if get_Disable_enter_attribute_values_dialog() == False:
#          if plugIn.iface.openFeatureForm(layer, f, True) == False:
#             return False
#
#    if refresh == True:
#       plugIn.beginEditCommand("Feature added", layer)
#
#    if layer.addFeature(f):
#       if refresh == True:
#          plugIn.endEditCommand()
#       plugIn.setLastEntity(layer, f.id())
#       result = True
#    else:
#       if refresh == True:
#          plugIn.destroyEditCommand()
#       result = False
#
#    return result


# ===============================================================================
# addGeomToLayer
# ===============================================================================
def addGeomToLayer(plugIn, layer, geom, coordTransform = None, refresh = True, check_validity = False, openForm = True):
   """Adds geometry to a layer. If the geometry needs to be converted then
      the <coordTransform> parameter of type QgsCoordinateTransform must be passed.
      refresh controls the command transaction and canvas refresh
   """
   g = QgsGeometry(geom)
   if coordTransform is not None:
      g.transform(coordTransform)

   if check_validity:
      if not g.isGeosValid():
         return False

   f = QgsVectorLayerUtils.createFeature(layer, g, {}, layer.createExpressionContext())
   if refresh == True: plugIn.beginEditCommand("Feature added", layer)
   if layer.addFeature(f) == False:
      if refresh == True: plugIn.destroyEditCommand()
      return False

   if openForm == True:
      if get_Disable_enter_attribute_values_dialog() == False:
         if plugIn.iface.openFeatureForm(layer, f) == False:
            if refresh == True: plugIn.destroyEditCommand()
            re = layer.deleteFeature(f.id())
            return False

   if refresh == True: plugIn.endEditCommand()
   plugIn.setLastEntity(layer, f.id())

   return True

#    f = QgsFeature()
#
#    g = QgsGeometry(geom)
#    if coordTransform is not None:
#       g.transform(coordTransform)
#
#    if check_validity:
#       if not g.isGeosValid():
#          return False
#
#    f.setGeometry(g)
#
#    # Add attribute fields to feature.
#    fields = layer.fields()
#    f.setFields(fields)
#
#    # assign default values
#    provider = layer.dataProvider()
#    for field in fields.toList():
#       i = fields.indexFromName(field.name())
#       f[field.name()] = provider.defaultValue(i)
#
#    f = QgsVectorLayerUtils.createFeature(layer, g, {}, layer.createExpressionContext())
#
#    if openForm == True:
#       if get_Disable_enter_attribute_values_dialog() == False:
#          if plugIn.iface.openFeatureForm(layer, f) == False:
#             return False
#
#    if refresh == True:
#       plugIn.beginEditCommand("Feature added", layer)
#
#    if layer.addFeature(f):
#       if refresh == True:
#          plugIn.endEditCommand()
#       plugIn.setLastEntity(layer, f.id())
#       result = True
#    else:
#       if refresh == True:
#          plugIn.destroyEditCommand()
#       result = False
#
#    return result

# ===============================================================================
# addGeomsToLayer
# ===============================================================================
def addGeomsToLayer(plugIn, layer, geoms, coordTransform = None, refresh = True, check_validity = False):
   """Adds geometry to a layer. If the geometry needs to be converted then
      the <coordTransform> parameter of type QgsCoordinateTransform must be passed.
      refresh controls the command transaction and canvas refresh
   """
   if refresh == True:
      plugIn.beginEditCommand("Feature added", layer)

   for geom in geoms:
      if addGeomToLayer(plugIn, layer, geom, coordTransform, False, check_validity) == False:
         if refresh == True:
            plugIn.destroyEditCommand()
            return False

   if refresh == True:
      plugIn.endEditCommand()

   return True


# ===============================================================================
# addFeatureToLayer
# ===============================================================================
def addFeatureToLayer(plugIn, layer, f, coordTransform = None, refresh = True, check_validity = False, openForm = True):
   """Adds a feature to a layer. If the geometry needs to be converted then
      the <coordTransform> parameter of type QgsCoordinateTransform must be passed.
      <refresh> controls the command transaction and canvas refresh
   """

   if coordTransform is not None:
      g = QgsGeometry(f.geometry())
      g.transform(coordTransform)
      f.setGeometry(g)

   if check_validity:
      if not f.geometry().isGeosValid():
         return False

   if openForm == True:
      if get_Disable_enter_attribute_values_dialog() == False:
         if plugIn.iface.openFeatureForm(layer, f, True) == False:
            return False

   if refresh == True:
      plugIn.beginEditCommand("Feature added", layer)

   # use default value for primary key fields if it's NOT NULL
   provider = layer.dataProvider()
   pkAttrList = layer.primaryKeyAttributes()
   count = layer.fields().count()
   i = 0
   while i < count:
      if i in pkAttrList:
         defVal = provider.defaultValue(i)
         f[i] = defVal
         # if defVal is not None or layer.providerType() == "spatialite":
         #    f[i] = provider.defaultValue(i)
      i = i + 1

   if layer.addFeature(f):
      if refresh == True:
         plugIn.endEditCommand()
         layer.triggerRepaint()

      plugIn.setLastEntity(layer, f.id())
      result = True
   else:
      if refresh == True:
         plugIn.destroyEditCommand()
      result = False

   return result


# ===============================================================================
# addFeaturesToLayer
# ===============================================================================
def addFeaturesToLayer(plugIn, layer, features, coordTransform = None, refresh = True, check_validity = False):
   """Adds features to a layer. If the geometry needs to be converted then
      the <coordTransform> parameter of type QgsCoordinateTransform must be passed.
      <refresh> controls the command transaction and canvas refresh
   """
   if refresh == True:
      plugIn.beginEditCommand("Feature added", layer)

   for f in features:
      if addFeatureToLayer(plugIn, layer, f, coordTransform, False, check_validity, False) == False:
         if refresh == True:
            plugIn.destroyEditCommand()
            return False

   if refresh == True:
      plugIn.endEditCommand()

   return True


# ===============================================================================
# updateFeatureToLayer
# ===============================================================================
def updateFeatureToLayer(plugIn, layer, f, refresh = True, check_validity = False):
   """Update the feature to a layer.
      refresh controls the command transaction and canvas refresh
   """
   if check_validity:
      if not f.geometry().isGeosValid():
         return False

   if refresh == True:
      plugIn.beginEditCommand("Feature modified", layer)

   if layer.updateFeature(f):
      if refresh == True:
         plugIn.endEditCommand()

      result = True
   else:
      if refresh == True:
         plugIn.destroyEditCommand()
      result = False

   return result


# ===============================================================================
# updateFeaturesToLayer
# ===============================================================================
def updateFeaturesToLayer(plugIn, layer, features, refresh = True, check_validity = False):
   """Update features on a layer.
      refresh controls the command transaction and canvas refresh
   """
   if refresh == True:
      plugIn.beginEditCommand("Feature modified", layer)

   for f in features:
      if updateFeatureToLayer(plugIn, layer, f, False, check_validity) == False:
         if refresh == True:
            plugIn.destroyEditCommand()
            return False

   if refresh == True:
      plugIn.endEditCommand()

   return True


# ===============================================================================
# deleteFeatureToLayer
# ===============================================================================
def deleteFeatureToLayer(plugIn, layer, featureId, refresh = True):
   """Delete the feature from a layer.
      refresh controls the command transaction and canvas refresh
   """
   if refresh == True:
      plugIn.beginEditCommand("Feature deleted", layer)

   if layer.deleteFeature(featureId):
      if refresh == True:
         plugIn.endEditCommand()

      result = True
   else:
      if refresh == True:
         plugIn.destroyEditCommand()
      result = False

   return result


# ===============================================================================
# deleteFeaturesToLayer
# ===============================================================================
def deleteFeaturesToLayer(plugIn, layer, featureIds, refresh = True):
   """Update features on a layer.
      refresh controls the command transaction and canvas refresh
   """
   if refresh == True:
      plugIn.beginEditCommand("Feature deleted", layer)

   for featureId in featureIds:
      if deleteFeatureToLayer(plugIn, layer, featureId, False) == False:
         if refresh == True:
            plugIn.destroyEditCommand()
            return False

   if refresh == True:
      plugIn.endEditCommand()

   return True


# ===============================================================================
# getLayersByName
# ===============================================================================
def getLayersByName(regularExprName):
   """Returns the list of layers whose name matches the searc regular expression
      (for conversion from wildcards see the wildCard2regularExpr function)
      the regular expression to only match if the text is an exact match is
      (for example, to match for abc, then 1abc1, 1abc, and abc1 would not match):
      use the start and end delimiters: ^abc$
   """
   result = []
   regExprCompiled = re.compile(regularExprName)
   for layer in QgsProject.instance().mapLayers().values():
      if re.match(regExprCompiled, layer.name()):
         if layer.isValid():
            result.append(layer)

   return result


# ===============================================================================
# getLayerById
# ===============================================================================
def getLayerById(id):
   """Returns the layer with known id"""
   for layer in QgsProject.instance().mapLayers().values():
      if layer.id() == id:
         return layer
   return None


# ===============================================================================
# get_symbolRotationFieldName
# ===============================================================================
def get_symbolRotationFieldName(layer):
   """
   return rotation field name (or empty string if not set or not supported by renderer)
   """
   if (layer.type() != QgsMapLayer.VectorLayer) or (layer.geometryType() != QgsWkbTypes.PointGeometry):
      return ""

   try:
      renderer = layer.renderer()
      expr = renderer.symbol().dataDefinedAngle().asExpression()
      expr = QgsSymbolLayerUtils.fieldOrExpressionToExpression(expr)
      columns = expr.referencedColumns()
      if len(columns) == 1:
         for column in columns:
            return column
      else:
         return ""
   except:
      return ""


# ===============================================================================
# get_symbolScaleFieldName
# ===============================================================================
def get_symbolScaleFieldName(layer):
   """
   return symbol scale field name (or empty string if not set or not supported by renderer)
   """
   if (layer.type() != QgsMapLayer.VectorLayer) or (layer.geometryType() != QgsWkbTypes.PointGeometry):
      return ""

   try:
      renderer = layer.renderer()
      expr = renderer.symbol().dataDefinedSize().asExpression()
      expr = QgsSymbolLayerUtils.fieldOrExpressionToExpression(expr)
      columns = expr.referencedColumns()
      if len(columns) == 1:
         for column in columns:
            return column
      else:
         return ""

   except:
      return ""



# ===============================================================================
# isTextLayer
# ===============================================================================
def isTextLayer(layer):
   """return True if the layer is text"""
   # must be a point-type VectorLayer
   if (layer.type() != QgsMapLayer.VectorLayer) or (layer.geometryType() != QgsWkbTypes.PointGeometry):
      return False
   renderer = layer.renderer()
   if renderer is None: return False

   context = QgsRenderContext()
   # must have the symbol-i transparent at least within 10%
   for symbol in renderer.symbols(context):
      if symbol.opacity() > 0.1: # 1 for opaque, 0 for invisible
         return False
   # must have labels
   if layer.labeling() is None:
      return False
   if layer.labelsEnabled() == False:
      return False

   # check that there is at least one field as a label
   labelFieldNames = get_labelFieldNames(layer)
   if len(labelFieldNames) == 0:
      return False

   return True


# ===============================================================================
# isSymbolLayer
# ===============================================================================
def isSymbolLayer(layer):
   """return True if the layer is of symbol type"""
   # must be a point-type VectorLayer
   if (layer.type() != QgsMapLayer.VectorLayer) or (layer.geometryType() != QgsWkbTypes.PointGeometry):
      return False
   # if the rotation is read from a field, remember that for the symbols the rotation is clockwise
   # therefore use the expression 360 - <rotation field>
   # if it is not a text layer it is a symbol layer
   return False if isTextLayer(layer) else True



# ===============================================================================
# get_Disable_enter_attribute_values_dialog
# ===============================================================================
def get_Disable_enter_attribute_values_dialog():
   value = QSettings().value('/qgis/digitizing/disable_enter_attribute_values_dialog', True)
   if type(value) == str:
      return False if value.lower() == 'false' else True
   elif type(value) == bool:
      return value

   return True

# ============================================================================
# TOP - QAD temporary layer management
# ============================================================================


# ===============================================================================
# createQADTempLayer
# ===============================================================================
def createQADTempLayer(plugIn, GeomType):
   """Adds three lists of geometries respectively to three temporary layers of QAD (one for each type of
      geometry). If the geometries are to be converted then
      the <coordTransform> parameter of type QgsCoordinateTransform must be passed.
      <epsg> = the authority identifier for this srs
   """
   layer = None
   crs = plugIn.iface.mapCanvas().mapSettings().destinationCrs()

   if GeomType == QgsWkbTypes.PointGeometry:
      layerName = QadMsg.translate("QAD", "QAD - Temporary points")
      layerList = QgsProject.instance().mapLayersByName(layerName)
      if len(layerList) == 0:
         layer = createMemoryLayer(layerName, "Point", crs)
         QgsProject.instance().addMapLayers([layer], True)
      else:
         layer = layerList[0]
   elif GeomType == QgsWkbTypes.LineGeometry:
      layerName = QadMsg.translate("QAD", "QAD - Temporary lines")
      layerList = QgsProject.instance().mapLayersByName(layerName)
      if len(layerList) == 0:
         layer = createMemoryLayer(layerName, "LineString", crs)
         QgsProject.instance().addMapLayers([layer], True)
      else:
         layer = layerList[0]
   elif GeomType == QgsWkbTypes.PolygonGeometry:
      layerName = QadMsg.translate("QAD", "QAD - Temporary polygons")
      layerList = QgsProject.instance().mapLayersByName(layerName)
      if len(layerList) == 0:
         layer = createMemoryLayer(layerName, "Polygon", crs)
         QgsProject.instance().addMapLayers([layer], True)
      else:
         layer = layerList[0]

   layer.startEditing()
   return layer


# ===============================================================================
# createMemoryLayer
# ===============================================================================
def createMemoryLayer(layerName, geomType, crs):
   """Create an in-memory layer with spatial index.
      <layerName> = name of the layer
      <geomType> = string representing the type of geometry:
      "LineString", "Polygon", "MultiPoint", "MultiLineString", or "MultiPolygon"
      <crs> = QgsCoordinateReferenceSystem object representing the coordinate system
   """
   # first create a layer with a definitely valid crs
   # I then set the correct coordinate system
   # I do this because if the name of the coordinate system contains strange characters
   # then the constructor of QgsVectorLayer messes up (sometimes it messes up e.g. with "USER:100004")
   layer = QgsVectorLayer(geomType + "?crs=epsg:3003&index=yes", layerName, "memory")
   layer.setCrs(crs, False)
   return layer


# ===============================================================================
# addGeometriesToQADTempLayers
# ===============================================================================
def addGeometriesToQADTempLayers(plugIn, pointGeoms = None, lineGeoms = None, polygonGeoms = None, \
                               crs = None, refresh = True):
   """Adds three lists of geometries respectively to three temporary layers of QAD (one for each type of
      geometry). If the geometries are to be converted then
      the <csr> parameter must be passed which defines the coordinate system of the geometries.
   """
   if pointGeoms is not None and len(pointGeoms) > 0:
      layer = createQADTempLayer(plugIn, QgsWkbTypes.PointGeometry)
      if layer is None:
         return False
      if crs is None:
         # plugin, layer, geoms, coordTransform, refresh, check_validity
         if addGeomsToLayer(plugIn, layer, pointGeoms, None, refresh, False) == False:
            return False
      else:
         # plugin, layer, geoms, coordTransform, refresh, check_validity
         if addGeomsToLayer(plugIn, layer, pointGeoms, QgsCoordinateTransform(crs, layer.crs(), QgsProject.instance()), \
                            refresh, False) == False:
            return False

   if lineGeoms is not None and len(lineGeoms) > 0:
      layer = createQADTempLayer(plugIn, QgsWkbTypes.LineGeometry)
      if layer is None:
         return False
      if crs is None:
         # plugin, layer, geoms, coordTransform, refresh, check_validity
         if addGeomsToLayer(plugIn, layer, lineGeoms, None, refresh, False) == False:
            return False
      else:
         # plugin, layer, geoms, coordTransform, refresh, check_validity
         if addGeomsToLayer(plugIn, layer, lineGeoms, QgsCoordinateTransform(crs, layer.crs(), QgsProject.instance()), \
                            refresh, False) == False:
            return False

   if polygonGeoms is not None and len(polygonGeoms) > 0:
      layer = createQADTempLayer(plugIn, QgsWkbTypes.PolygonGeometry)
      if layer is None:
         return False
      if crs is None:
         # plugin, layer, geoms, coordTransform, refresh, check_validity
         if addGeomsToLayer(plugIn, layer, polygonGeoms, None, refresh, False) == False:
            return False
      else:
         # plugin, layer, geoms, coordTransform, refresh, check_validity
         if addGeomsToLayer(plugIn, layer, polygonGeoms, QgsCoordinateTransform(crs, layer.crs(), QgsProject.instance()), \
                            refresh, False) == False:
            return False

   return True


# ===============================================================================
# QadLayerStatusEnum class.
# ===============================================================================
class QadLayerStatusEnum():
   UNKNOWN = 0
   COMMIT_BY_EXTERNAL = 1 # save when called by events external to QAD
   COMMIT_BY_INTERNAL = 2 # save when called by events internal to QAD

# ===============================================================================
# QadLayerStatusListClass class.
# ===============================================================================
class QadLayerStatusListClass():
   def __init__(self):
      self.layerStatusList = [] # list of pairs (<layer id>-<layer status>)

   def __del__(self):
      del self.layerStatusList

   def getStatus(self, layerId):
      for layerStatus in self.layerStatusList:
         if layerStatus[0] == layerId:
            return layerStatus[1]
      return QadLayerStatusEnum.UNKNOWN

   def setStatus(self, layerId, status):
      # check if it was already on the list
      for layerStatus in self.layerStatusList:
         if layerStatus[0] == layerId:
            layerStatus[1] = status
            return
      # if it wasn't there I'll add it
      self.layerStatusList.append([layerId, status])
      return

   def remove(self, layerId):
      i = 0
      for layerStatus in self.layerStatusList:
         if layerStatus[0] == layerId:
            del self.layerStatusList[i]
            return
         else:
            i = i + 1
      return