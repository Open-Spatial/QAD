# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin ok

 functions for creating arrays of graphical objects

                              -------------------
        begin                : 2016-05-26
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
import qgis.utils

import math

from . import qad_utils
from . import qad_arc
from . import qad_circle
from .qad_snapper import *
from . import qad_layer
from .qad_highlight import QadHighlight
from .qad_entity import *
from .qad_dim import *
from . import qad_label
from .qad_multi_geom import fromQadGeomToQgsGeom

# ===============================================================================
# doMoveAndRotateGeom
# ===============================================================================
def doMoveAndRotateGeom(plugIn, entity, offsetX, offsetY, angle, basePt, addToLayer, highlightObj):
   # assistive function
   if entity.whatIs() == "ENTITY":
      qadGeom = entity.getQadGeom().copy()
      qadGeom.move(offsetX, offsetY)
      if angle is not None:
         qadGeom.rotate(basePt, angle)

      g = fromQadGeomToQgsGeom(qadGeom, entity.layer)
      if addToLayer:
         newF = QgsFeature(entity.getFeature()) # I'm copying it because otherwise it'll end up in paper
         newF.setGeometry(g)

         if len(entity.rotFldName) > 0:
            rotValue = newF.attribute(entity.rotFldName)
            # a volte vale None e a volte null (vai a capire...)
            rotValue = 0 if rotValue is None or rotValue == NULL else qad_utils.toRadians(rotValue) # the rotation is in degrees in the feature field
            rotValue = rotValue + angle
            newF.setAttribute(entity.rotFldName, qad_utils.toDegrees(qad_utils.normalizeAngle(rotValue)))

         # plugin, layer, feature, coordTransform, refresh, check_validity
         if qad_layer.addFeatureToLayer(plugIn, entity.layer, newF, None, False, False, False) == False:
            return False

      if highlightObj is not None:
         highlightObj.addGeometry(g, entity.layer)

      del qadGeom
      del g

   elif ent.whatIs() == "DIMENTITY": # if the entity is a dimension
      newDimEntity = QadDimEntity(dimEntity)
      newDimEntity.move(offsetX, offsetY)
      if angle is not None:
         newDimEntity.rotate(basePt, angle)

      if addToLayer:
         if newDimEntity.addToLayers(plugIn) == False:
            return False

      if highlightObj is not None:
         highlightObj.addGeometry(newDimEntity.textualFeature.geometry(), newDimEntity.getTextualLayer())
         highlightObj.addGeometries(newDimEntity.getLinearGeometryCollection(), newDimEntity.getLinearLayer())
         highlightObj.addGeometries(newDimEntity.getSymbolGeometryCollection(), newDimEntity.getSymbolLayer())

      del newDimEntity

   return True


# ===============================================================================
# arrayRectangleEntity
# ===============================================================================
def arrayRectangleEntity(plugIn, ent, basePt, rows, cols, distanceBetweenRows, distanceBetweenCols, angle, itemsRotation,
                         addToLayer, highlightObj):
   """rectangular series
      ent = QAD entity to create the series (QadEntity or QadDimEntity)
      basePt = base point in map coordinates (QgsPointXY)
      rows = number of rows
      cols = number of columns
      distanceBetweenRows = distance between rows in map coordinates
      distanceBetweenCols = distance between columns in map coordinates
      angle = series angle (radians)
      itemsRotation = True if you want to rotate the items as the corner of the array
      addToLayer = if True adds the new entities to the layer
      highlightObj = if it is different from None, the geometries are added to the QadHighlight object

      the function returns True on success and False on error
   """
   for row in range(0, rows):
      firstBasePt = qad_utils.getPolarPointByPtAngle(basePt, angle + math.pi / 2, distanceBetweenRows * row)
      distX = 0
      for col in range(0, cols):
         newBasePt = qad_utils.getPolarPointByPtAngle(firstBasePt, angle, distanceBetweenCols * col)
         offsetX = newBasePt.x() - basePt.x()
         offsetY = newBasePt.y() - basePt.y()

         if doMoveAndRotateGeom(plugIn, ent, offsetX, offsetY, \
                                angle if itemsRotation else None, \
                                newBasePt, addToLayer, highlightObj) == False:
            return False

         distX = distX + distanceBetweenCols

   return True


# ===============================================================================
# arrayPathEntity
# ===============================================================================
def arrayPathEntity(plugIn, ent, basePt, rows, cols, distanceBetweenRows, distanceBetweenCols, tangentDirection, itemsRotation, \
                    pathPolyline, distanceFromStartPt, addToLayer, highlightObj):
   """trajectory series
      ent = QAD entity to create the series (QadEntity or QadDimEntity)
      basePt = base point in map coordinates (QgsPointXY)
      rows = number of rows
      cols = number of columns
      distanceBetweenRows = distance between rows in map coordinates
      distanceBetweenCols = distance between columns in map coordinates
      tangentDirection = specifies how the elements arranged in series are aligned with respect to the initial direction of the trajectory
      itemsRotation = True if you want to rotate the items as the corner of the array
      pathPolyline = path to follow (QadPolyline) in map coordinates
      distanceFromStartPt = distance from the start point of the track
      addToLayer = if True adds the new entities to the layer
      highlightObj = if it is different from None, the geometries are added to the QadHighlight object

      the function returns True on success and False on error
   """
   firstBasePt = basePt
   firstTanDirection = pathPolyline.getTanDirectionOnStartPt()
   for col in range(0, cols):
      distX = (distanceBetweenCols * col) + distanceFromStartPt
      firstBasePt, angle = pathPolyline.getPointFromStart(distX) # returns the point and the direction of the tang at that point
      if firstBasePt is not None:
         for row in range(0, rows):
            newBasePt = qad_utils.getPolarPointByPtAngle(firstBasePt, angle + math.pi/2, distanceBetweenRows * row)
            offsetX = newBasePt.x() - basePt.x()
            offsetY = newBasePt.y() - basePt.y()

            if doMoveAndRotateGeom(plugIn, ent, offsetX, offsetY, \
                                   angle - tangentDirection if itemsRotation else -tangentDirection, \
                                   newBasePt, addToLayer, highlightObj) == False:
               return False

      distX = distX + distanceBetweenCols

   return True


# ===============================================================================
# arrayPolarEntity
# ===============================================================================
def arrayPolarEntity(plugIn, ent, basePt, centerPt, itemsNumber, angleBetween, rows, distanceBetweenRows, itemsRotation, \
                     addToLayer, highlightObj):
   """polar series
      ent = QAD entity to create the series (QadEntity or QadDimEntity)
      basePt = base point in map coordinates (QgsPointXY)
      centerPt = center point in map coordinates (QgsPointXY)
      itemsNumber = number of copies to create
      angleBetween = angle between one element and another (radians)
      rows = number of rows
      distanceBetweenRows = distance between rows in map coordinates
      itemsRotation = True if you want to rotate the items around the circle
      addToLayer = if True adds the new entities to the layer
      highlightObj = if it is different from None, the geometries are added to the QadHighlight object
   """
   firstAngle = qad_utils.getAngleBy2Pts(centerPt, basePt)
   dist = qad_utils.getDistance(centerPt, basePt)
   for row in range(0, rows):
      angle = firstAngle
      for i in range(0, itemsNumber):
         newBasePt = qad_utils.getPolarPointByPtAngle(centerPt, angle, dist)
         offsetX = newBasePt.x() - basePt.x()
         offsetY = newBasePt.y() - basePt.y()

         if doMoveAndRotateGeom(plugIn, ent, offsetX, offsetY, \
                                i * angleBetween if itemsRotation else None, \
                                newBasePt, addToLayer, highlightObj) == False:
            return False
         angle = angle + angleBetween

      dist = dist + distanceBetweenRows

   return True

