# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 class for managing polygons (list of polylines)

                              -------------------
        begin                : 2019-03-14
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


from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui  import *
from qgis.core import *
from qgis.gui import *


from . import qad_utils
from .qad_circle import QadCircle
from .qad_ellipse import QadEllipse
from .qad_polyline import QadPolyline


# ===============================================================================
# QadPolygon class
# represents a list of closed geometries: QadPolyline, QadCircle, QadEllipse
# ===============================================================================
class QadPolygon():

   def __init__(self, polygon=None):
      self.defList = []
      # deflist = (<closed geometry 1> <closed geometry 2>...)
      if polygon is not None:
         self.set(polygon)


   # ============================================================================
   # whatIs
   # ============================================================================
   def whatIs(self):
      return "POLYGON"


   # ============================================================================
   # isClosed
   # ============================================================================
   def isClosed(self):
      return True


   # ============================================================================
   # set
   # ============================================================================
   def set(self, polygon):
      self.removeAll()
      for closedObject in polygon.defList:
         self.append(closedObject)
      return self


   def __eq__(self, polygon):
      # required
      """self == other"""
      if polygon.whatIs() != "POLYLINE": return False
      if self.qty() != polygon.qty(): return False
      for i in range(0, self.qty()):
         if self.getClosedObjectAt(i) != polygon.getClosedObjectAt(i): return False
      return True


   def __ne__(self, polygon):
      """self != other"""
      return not self.__eq__(polygon)


   # ============================================================================
   # append
   # ============================================================================
   def append(self, closedObject):
      """the function adds a closed geometry to the bottom of the list."""
      if closedObject is None: return
      objectType = closedObject.whatIs()
      if objectType == "POLYLINE":
         if closedObject.isClosed() == False: return False
      elif objectType != "CIRCLE" and objectType != "ELLIPSE":
         return False
      self.defList.append(closedObject.copy())
      return True


   # ============================================================================
   # insert
   # ============================================================================
   def insert(self, i, closedObject):
      """the function adds a closed geometry in the i-th position of the list of closed geometries."""
      if i >= self.qty():
         return self.append(closedObject)
      else:
         return self.defList.insert(i, closedObject.copy())


   # ============================================================================
   # remove
   # ============================================================================
   def remove(self, i):
      """the function deletes a closed geometry in the i-th position of the list."""
      del self.defList[i]


   # ============================================================================
   # removeAll
   # ============================================================================
   def removeAll(self):
      """the function deletes the closed geometries of the list."""
      del self.defList[:]


   # ============================================================================
   # getClosedObjectAt
   # ============================================================================
   def getClosedObjectAt(self, i):
      """the function returns the geometry closed at the i-th position
            with negative numbers it starts from the bottom (e.g. -1 = last position)
      """
      if self.qty() == 0 or i > self.qty() - 1:
         return None
      return self.defList[i]


   # ============================================================================
   # fromPolygon
   # ============================================================================
   def fromPolygon(self, lineList):
      """the function initializes a list of closed geometries that composes the polygon passed into lists of points."""
      self.removeAll()
      ellipse = QadEllipse()
      circle = QadCircle()
      polyline = QadPolyline()

      for points in lineList:
         # check if it is a circle
         if circle.fromPolyline(points):
            self.append(circle)
         else:
            # check if it is an ellipse
            if ellipse.fromPolyline(points):
               self.append(ellipse)
            else:
               # check if it is a polyline
               if polyline.fromPolyline(points):
                  if polyline.isClosed():
                     self.append(polyline)

      if self.qty() == 0: return None
      return True


   # ============================================================================
   # fromGeom
   # ============================================================================
   def fromGeom(self, geom):
      """the function initializes the polygon from a QgsGeometry object."""
      return self.fromPolygon(geom.asPolygon())


   # ===============================================================================
   # asPolygon
   # ===============================================================================
   def asPolygon(self, tolerance2ApproxCurve = None, atLeastNSegment = None):
      """the function returns a list of lists of points that make up a polygon."""
      result = []
      for closedObject in self.defList:
         result.append(closedObject.asPolyline(tolerance2ApproxCurve, atLeastNSegment))

      return result


   # ===============================================================================
   # asAbstractGeom
   # ===============================================================================
   def asAbstractGeom(self, wkbType = QgsWkbTypes.LineString, tolerance2ApproxCurve = None, atLeastNSegment = None):
      """the function returns the polygon in the form of QgsAbstractGeometry."""
      flatType = QgsWkbTypes.flatType(wkbType)

      if flatType == QgsWkbTypes.CurvePolygon:
         curvePolygon = QgsCurvePolygon()
         exteriorRing = True
         for closedObject in self.defList:
            if exteriorRing == True:
               curvePolygon.setExteriorRing(closedObject.asAbstractGeom(QgsWkbTypes.CompoundCurve , tolerance2ApproxCurve, atLeastNSegment))
               exteriorRing = False
            else:
               curvePolygon.addInteriorRing(closedObject.asAbstractGeom(QgsWkbTypes.CompoundCurve , tolerance2ApproxCurve, atLeastNSegment))
         return curvePolygon

      elif flatType == QgsWkbTypes.MultiSurface: # Geometry that is combined from several Curvepolygons is called MultiSurface
         curvedPolygon = self.asAbstractGeom(QgsWkbTypes.CurvePolygon, tolerance2ApproxCurve, atLeastNSegment)
         multiSurface = QgsMultiSurface()
         multiSurface.addGeometry(curvedPolygon)
         return multiSurface

      elif flatType == QgsWkbTypes.MultiPolygon:
         polygon = self.asAbstractGeom(QgsWkbTypes.Polygon, tolerance2ApproxCurve, atLeastNSegment)
         multiPolygon = QgsMultiPolygon()
         multiPolygon.addGeometry(polygon)
         return multiPolygon

      polygon = QgsPolygon()
      exteriorRing = True
      for closedObject in self.defList:
         if exteriorRing == True:
            polygon.setExteriorRing(closedObject.asAbstractGeom(QgsWkbTypes.LineString , tolerance2ApproxCurve, atLeastNSegment))
            exteriorRing = False
         else:
            polygon.addInteriorRing(closedObject.asAbstractGeom(QgsWkbTypes.LineString , tolerance2ApproxCurve, atLeastNSegment))
      return polygon


   # ===============================================================================
   # asGeom
   # ===============================================================================
   def asGeom(self, wkbType = QgsWkbTypes.LineString, tolerance2ApproxCurve = None, atLeastNSegment = None):
      """the function returns the polygon in the form of QgsGeometry."""
      return QgsGeometry(self.asAbstractGeom(wkbType, tolerance2ApproxCurve, atLeastNSegment))


   # ===============================================================================
   # copy
   # ===============================================================================
   def copy(self):
      # required
      return QadPolygon(self)


   # ============================================================================
   # move
   # ============================================================================
   def move(self, offsetX, offsetY):
      """the function moves the closed geometries according to an X and a Y offset"""
      for closedObject in self.defList:
         closedObject.move(offsetX, offsetY)


   # ============================================================================
   # rotate
   # ============================================================================
   def rotate(self, basePt, angle):
      for closedObject in self.defList:
         closedObject.rotate(basePt, angle)


   # ============================================================================
   # scale
   # ============================================================================
   def scale(self, basePt, scale):
      for closedObject in self.defList:
         closedObject.scale(basePt, scale)


   # ============================================================================
   # mirror
   # ============================================================================
   def mirror(self, mirrorPt, mirrorAngle):
      for closedObject in self.defList:
         closedObject.mirror(mirrorPt, mirrorAngle)


   # ============================================================================
   # qty
   # ============================================================================
   def qty(self):
      """the function returns the quantity of closed geometries that make up the polygon."""
      return len(self.defList)


   # ============================================================================
   # getCentroid
   # ============================================================================
   def getCentroid(self, tolerance2ApproxCurve = None):
      """the function returns the centroid point."""
      g = self.asGeom(QgsWkbTypes.LineString, tolerance2ApproxCurve)
      if g is not None:
         centroid = g.centroid()
         if centroid is not None:
            return g.centroid().asPoint()

      return None


   # ===============================================================================
   # transform
   # ===============================================================================
   def transform(self, coordTransform):
      """the function returns a new polygon with the transformed coordinates."""
      result = QadPolygon()
      for closedObject in self.defList:
         result.append(closedObject.transform(coordTransform))
      return result


   # ===============================================================================
   # transformFromCRSToCRS
   # ===============================================================================
   def transformFromCRSToCRS(self, sourceCRS, destCRS):
      """the function transforms the coordinates of the points that make up the polygon."""
      return self.transform(QgsCoordinateTransform(sourceCRS, destCRS, QgsProject.instance()))


   # ===============================================================================
   # getBoundingBox
   # ===============================================================================
   def getBoundingBox(self):
      """the function returns the rectangle that encloses the polygon."""
      boundingBox = self.getClosedObjectAt(0).getBoundingBox()
      i = 1
      while i < self.qty():
         boundingBox.combineExtentWith(self.getClosedObjectAt(i).getBoundingBox())
         i = i + 1

      return boundingBox


   # ===============================================================================
   # containsPt
   # ===============================================================================
   def containsPt(self, pt):
      """the function returns True if the point is on the polygon otherwise False."""
      for closedObject in self.defList:
         if closedObject.containsPt(pt): return True

      return False
