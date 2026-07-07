# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 class for managing multi-geometries (multipolygons)

                             -------------------
        begin                : 2019-03-15
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
from qgis.core import *
from qgis.gui import *
import qgis.utils


from .qad_point import *
from .qad_line import QadLine
from .qad_circle import QadCircle
from .qad_ellipse import QadEllipse
from .qad_polyline import QadPolyline
from .qad_polygon import QadPolygon
from .qad_layer import createMemoryLayer


# ===============================================================================
# QadLinearObject class
# returns a linear object line, arc, ellipse arc, polyline but also
# circle and ellipse (incorrectly) because they can exist in LINESTRING layers
# ===============================================================================
class QadLinearObject():

   def __init__(self):
      pass


   # ============================================================================
   # fromPolyline
   # ============================================================================
   @staticmethod
   def fromPolyline(points):
      """the function returns a linear object which can be:
            line, arc, ellipse arc, polyline but also
            circle and ellipse (incorrectly) because they can exist in LINESTRING layers
      """
      tot_points = len(points)
      if tot_points == 0:
         return None

      if tot_points == 2:
         line = QadLine()
         line.set(points[0], points[1])
         return line

      # check if it is a circle
      circle = QadCircle()
      if circle.fromPolyline(points): return circle
      del circle
      # check if it is an ellipse
      ellipse = QadEllipse()
      if ellipse.fromPolyline(points): return ellipse
      del ellipse
      # check if it is a polyline
      polyline = QadPolyline()
      if polyline.fromPolyline(points):
         if polyline.qty() == 1: # if it is composed of only 1 object
            return polyline.getLinearObjectAt(0)
         else:
            return polyline
      del polyline

      return None


   # ============================================================================
   # fromGeom
   # ============================================================================
   @staticmethod
   def fromGeom(geom):
      """the function returns a linear object which can be:
            line, arc, ellipse arc, polyline but also
            circle and ellipse (incorrectly) because they can exist in LINESTRING layers
      """
      return QadLinearObject.fromPolyline(geom.asPolyline())


# ===============================================================================
# QadMultiPoint class
# represents a list of point objects
# ===============================================================================
class QadMultiPoint():

   def __init__(self, multiPoint=None):
      self.defList = []
      # deflist = (<point 1> <point 2>...)
      if multiPoint is not None:
         self.set(multiPoint)


   # ============================================================================
   # whatIs
   # ============================================================================
   def whatIs(self):
      return "MULTI_POINT"


   # ============================================================================
   # isClosed
   # ============================================================================
   def isClosed(self):
      return False


   # ============================================================================
   # set
   # ============================================================================
   def set(self, multiPoint):
      self.removeAll()
      for point in multiPoint.defList:
         self.append(point)
      return self


   def __eq__(self, multiPoint):
      # required
      """self == other"""
      if multiPoint.whatIs() != "MULTI_POINT": return False
      if self.qty() != multiPoint.qty(): return False
      for i in range(0, self.qty()):
         if self.getPointAt(i) != multiPoint.getPointAt(i): return False
      return True


   def __ne__(self, multiPoint):
      """self != other"""
      return not self.__eq__(multiPoint)


   # ============================================================================
   # append
   # ============================================================================
   def append(self, point):
      """the function adds a linear point to the bottom of the list."""
      if point is None: return
      if type(point) == QgsPointXY:
         self.defList.append(QadPoint(point))
      else:
         objectType = point.whatIs()
         if objectType != "POINT": return False
         self.defList.append(point.copy())

      return True


   # ============================================================================
   # insert
   # ============================================================================
   def insert(self, i, point):
      """the function adds a point in the i-th position of the point list."""
      if i >= self.qty():
         return self.append(point)
      else:
         if type(point) == QgsPointXY:
            self.defList.append(QadPoint(point))
         else:
            objectType = point.whatIs()
            if objectType != "POINT": return False
            return self.defList.insert(i, point.copy())



   # ============================================================================
   # remove
   # ============================================================================
   def remove(self, i):
      """the function deletes a point in the i-th position of the list."""
      del self.defList[i]


   # ============================================================================
   # removeAll
   # ============================================================================
   def removeAll(self):
      """the function deletes the points in the list."""
      del self.defList[:]


   # ============================================================================
   # getPointAt
   # ============================================================================
   def getPointAt(self, i):
      """the function returns the point at the i-th position
            with negative numbers it starts from the bottom (e.g. -1 = last position)
      """
      if self.qty() == 0 or i > self.qty() - 1:
         return None
      return self.defList[i]


   # ============================================================================
   # setPointAt
   # ============================================================================
   def setPointAt(self, pt, i):
      """the function sets the i-th point"""
      return self.getPointAt(i).set(pt)


   # ============================================================================
   # fromMultiPoint
   # ============================================================================
   def fromMultiPoint(self, pointList):
      """the function initializes a list of points that makes up the multiPoint passed in the form of a list of points."""
      self.removeAll()
      for point in pointList:
         self.append(point)

      if self.qty() == 0: return False

      return True


   # ============================================================================
   # fromGeom
   # ============================================================================
   def fromGeom(self, geom):
      """the function initializes a list of QgsPointXY points that composes the multiPoint from a QgsGeometry object."""
      return self.fromMultiPoint(geom.asMultiPoint())


   # ===============================================================================
   # asMultiPoint
   # ===============================================================================
   def asMultiPoint(self):
      """the function returns a list of QgsPointXY points that make up a multiPoint."""
      result = []
      for point in self.defList:
         result.append(QgsPointXY(point))

      return result


   # ===============================================================================
   # asGeom
   # ===============================================================================
   def asGeom(self, wkbType = QgsWkbTypes.MultiPoint , tolerance2ApproxCurve = None, atLeastNSegment = None):
      """the function returns the multiPoint in the form of QgsGeometry.
            wkbType, tolerance2ApproxCurve and atLeastNSegment are declared for compatibility only
      """
      return QgsGeometry.fromMultiPointXY(self.asMultiPoint())


   # ===============================================================================
   # copy
   # ===============================================================================
   def copy(self):
      # required
      return QadMultiPoint(self)


   # ============================================================================
   # move
   # ============================================================================
   def move(self, offsetX, offsetY):
      """the function moves the points according to an X and a Y offset"""
      for point in self.defList:
         point.move(offsetX, offsetY)


   # ============================================================================
   # rotate
   # ============================================================================
   def rotate(self, basePt, angle):
      for point in self.defList:
         point.rotate(basePt, angle)


   # ============================================================================
   # scale
   # ============================================================================
   def scale(self, basePt, scale):
      for point in self.defList:
         point.scale(basePt, scale)


   # ============================================================================
   # mirror
   # ============================================================================
   def mirror(self, mirrorPt, mirrorAngle):
      for point in self.defList:
         point.mirror(mirrorPt, mirrorAngle)


   # ============================================================================
   # qty
   # ============================================================================
   def qty(self):
      """the function returns the quantity of points that make up the multipoint."""
      return len(self.defList)


   # ===============================================================================
   # transform
   # ===============================================================================
   def transform(self, coordTransform):
      """the function returns a new multipoint with the transformed coordinates."""
      result = QadMultiPoint()
      for point in self.defList:
         result.append(point.transform(coordTransform))
      return result


   # ===============================================================================
   # transformFromCRSToCRS
   # ===============================================================================
   def transformFromCRSToCRS(self, sourceCRS, destCRS):
      """the function transforms the coordinates of the points that make up the multipoint."""
      return self.transform(QgsCoordinateTransform(sourceCRS, destCRS, QgsProject.instance()))


   # ===============================================================================
   # closestPoint
   # ===============================================================================
   def closestPoint(pt):
      """the function returns a list with
            (<minimum distance>
             <nearest point>
             <nearest point index>
      """
      dist = sys.float_info.max
      index = 0
      for point in self.defList:
         d = point.distance(pt)
         if d < dist:
            dist = d
            minDistPoint = point
            pointIndex = index

         index = index + 1

      return (dist, minDistPoint, pointIndex)


   # ===============================================================================
   # getBoundingBox
   # ===============================================================================
   def getBoundingBox(self):
      """the function returns the rectangle that encloses the points."""
      boundingBox = self.getPointAt(0).getBoundingBox()
      i = 1
      while i < self.qty():
         boundingBox.combineExtentWith(self.getPointAt(i).getBoundingBox())
         i = i + 1

      return boundingBox


# ===============================================================================
# QadMultiLinearObject class
# represents a list of linear objects including circle and ellipse (incorrectly) because they can exist in LINESTRING layers
# ===============================================================================
class QadMultiLinearObject():

   def __init__(self, multiLinearObject=None):
      self.defList = []
      # deflist = (<obj 1> <obj 2>...)
      if multiLinearObject is not None:
         self.set(multiLinearObject)


   # ============================================================================
   # whatIs
   # ============================================================================
   def whatIs(self):
      return "MULTI_LINEAR_OBJ"


   # ============================================================================
   # set
   # ============================================================================
   def set(self, multiLinearObject):
      self.removeAll()
      for linearObject in multiLinearObject.defList:
         self.append(linearObject)
      return self


   def __eq__(self, multiLinearObject):
      # required
      """self == other"""
      if multiLinearObject.whatIs() != "MULTI_LINEAR_OBJ": return False
      if self.qty() != multiLinearObject.qty(): return False
      for i in range(0, self.qty()):
         if self.getLinearObjectAt(i) != multiLinearObject.getLinearObjectAt(i): return False
      return True


   def __ne__(self, multiLinearObject):
      """self != other"""
      return not self.__eq__(multiLinearObject)


   # ============================================================================
   # append
   # ============================================================================
   def append(self, linearObject):
      """the function adds a linear object to the bottom of the list."""
      if linearObject is None: return
      objectType = linearObject.whatIs()
      if objectType != "LINE" and objectType != "ARC" and objectType != "ELLIPSE_ARC" and \
         objectType != "POLYLINE" and objectType != "CIRCLE" and objectType != "ELLIPSE":
         return False
      self.defList.append(linearObject.copy())
      return True


   # ============================================================================
   # insert
   # ============================================================================
   def insert(self, i, linearObject):
      """the function adds a linear object in the i-th position of the list of linear objects."""
      if i >= self.qty():
         return self.append(linearObject)
      else:
         return self.defList.insert(i, linearObject.copy())


   # ============================================================================
   # remove
   # ============================================================================
   def remove(self, i):
      """the function deletes a linear object in the i-th position of the list."""
      del self.defList[i]


   # ============================================================================
   # removeAll
   # ============================================================================
   def removeAll(self):
      """the function deletes the linear objects in the list."""
      del self.defList[:]


   # ============================================================================
   # getLinearObjectAt
   # ============================================================================
   def getLinearObjectAt(self, i):
      """the function returns the linear object at the i-th position
            with negative numbers it starts from the bottom (e.g. -1 = last position)
      """
      if self.qty() == 0 or i > self.qty() - 1:
         return None
      return self.defList[i]


   # ============================================================================
   # setLinearObjectAt
   # ============================================================================
   def setLinearObjectAt(self, linearObject, i):
      """the function sets the i-th linear object"""
      return self.getLinearObjectAt(i).set(linearObject)


   # ============================================================================
   # fromMultiLinearObject
   # ============================================================================
   def fromMultiLinearObject(self, linearObjectList):
      """the function initializes a list of linear objects that makes up the multiLinearObject passed in the form of a list of points."""
      self.removeAll()

      for points in linearObjectList:
         linearObject = QadLinearObject.fromPolyline(points)
         if linearObject is not None:
            self.append(linearObject)

      if self.qty() == 0: return False
      return True


   # ============================================================================
   # fromGeom
   # ============================================================================
   def fromGeom(self, geom):
      """the function initializes a list of linear objects that makes up the multiLinearObject from a QgsGeometry object."""
      return self.fromMultiLinearObject(geom.asMultiPolyline())


   # ===============================================================================
   # asMultiPolyline
   # ===============================================================================
   def asMultiPolyline(self, tolerance2ApproxCurve = None, atLeastNSegment = None):
      """the function returns a list of lists of lists of points that make up a multiLinearObject."""
      result = []
      for linearObject in self.defList:
         result.append(linearObject.asPolyline(tolerance2ApproxCurve, atLeastNSegment))

      return result


   # ===============================================================================
   # asGeom
   # ===============================================================================
   def asGeom(self, wkbType = QgsWkbTypes.MultiLineString, tolerance2ApproxCurve = None, atLeastNSegment = None):
      """the function returns the multiLinearObject in the form of QgsGeometry."""
      flatType = QgsWkbTypes.flatType(wkbType)

      if flatType == QgsWkbTypes.MultiCurve:
         multiCurve = QgsMultiCurve()
         for linearObject in self.defList:
            multiCurve.addGeometry(linearObject.asAbstractGeom(QgsWkbTypes.CompoundCurve, tolerance2ApproxCurve, atLeastNSegment))
         return QgsGeometry(multiCurve)

      return QgsGeometry.fromMultiPolylineXY(self.asMultiPolyline(tolerance2ApproxCurve, atLeastNSegment))


   # ===============================================================================
   # copy
   # ===============================================================================
   def copy(self):
      # required
      return QadMultiLinearObject(self)


   # ============================================================================
   # move
   # ============================================================================
   def move(self, offsetX, offsetY):
      """the function moves the linear objects according to an X and a Y offset"""
      for linearObject in self.defList:
         linearObject.move(offsetX, offsetY)


   # ============================================================================
   # rotate
   # ============================================================================
   def rotate(self, basePt, angle):
      for linearObject in self.defList:
         linearObject.rotate(basePt, angle)


   # ============================================================================
   # scale
   # ============================================================================
   def scale(self, basePt, scale):
      for linearObject in self.defList:
         linearObject.scale(basePt, scale)


   # ============================================================================
   # mirror
   # ============================================================================
   def mirror(self, mirrorPt, mirrorAngle):
      for linearObject in self.defList:
         linearObject.mirror(mirrorPt, mirrorAngle)


   # ============================================================================
   # qty
   # ============================================================================
   def qty(self):
      """the function returns the quantity of linear objects that make up the multiline."""
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
      """the function returns a new multiline with the transformed coordinates."""
      result = QadMultiLinearObject()
      for linearObject in self.defList:
         result.append(linearObject.transform(coordTransform))
      return result


   # ===============================================================================
   # transformFromCRSToCRS
   # ===============================================================================
   def transformFromCRSToCRS(self, sourceCRS, destCRS):
      """the function transforms the coordinates of the points that make up the multiline."""
      return self.transform(QgsCoordinateTransform(sourceCRS, destCRS, QgsProject.instance()))


   # ===============================================================================
   # getBoundingBox
   # ===============================================================================
   def getBoundingBox(self):
      """the function returns the rectangle that encloses the linear elements."""
      boundingBox = self.getLinearObjectAt(0).getBoundingBox()
      i = 1
      while i < self.qty():
         boundingBox.combineExtentWith(self.getLinearObjectAt(i).getBoundingBox())
         i = i + 1

      return boundingBox


   # ===============================================================================
   # containsPt
   # ===============================================================================
   def containsPt(self, pt):
      """the function returns True if the point is on the multiline otherwise False."""
      for linearObject in self.defList:
         if linearObject.containsPt(pt): return True

      return False


# ===============================================================================
# QadMultiPolygon class
# represents a list of polygons
# ===============================================================================
class QadMultiPolygon():

   def __init__(self, multiPolygon=None):
      self.defList = []
      # deflist = (<polygon 1> <polygon 2>...)
      if multiPolygon is not None:
         self.set(multiPolygon)


   # ============================================================================
   # whatIs
   # ============================================================================
   def whatIs(self):
      return "MULTI_POLYGON"


   # ============================================================================
   # isClosed
   # ============================================================================
   def isClosed(self):
      return True


   # ============================================================================
   # set
   # ============================================================================
   def set(self, multiPolygon):
      self.removeAll()
      for polygon in multiPolygon.defList:
         self.append(polygon)
      return self


   def __eq__(self, multiPolygon):
      # required
      """self == other"""
      if multiPolygon.whatIs() != "MULTI_POLYGON": return False
      if self.qty() != multiPolygon.qty(): return False
      for i in range(0, self.qty()):
         if self.getPointAt(i) != multiPolygon.getPolygonAt(i): return False
      return True


   def __ne__(self, multiPolygon):
      """self != other"""
      return not self.__eq__(multiPolygon)


   # ============================================================================
   # append
   # ============================================================================
   def append(self, polygon):
      """the function adds a polygon to the bottom of the list."""
      if polygon is None: return
      if polygon.whatIs() != "POLYGON": return False
      self.defList.append(polygon.copy())
      return True


   # ============================================================================
   # insert
   # ============================================================================
   def insert(self, i, polygon):
      """the function adds a polygon in the i-th position of the polygon list."""
      if i >= self.qty():
         return self.append(polygon)
      else:
         return self.defList.insert(i, polygon.copy())


   # ============================================================================
   # remove
   # ============================================================================
   def remove(self, i):
      """the function deletes a polygon in the i-th position of the list."""
      del self.defList[i]


   # ============================================================================
   # removeAll
   # ============================================================================
   def removeAll(self):
      """the function deletes the polygons in the list."""
      del self.defList[:]


   # ============================================================================
   # getPolygonAt
   # ============================================================================
   def getPolygonAt(self, i):
      """the function returns the polygon at the i-th position
            with negative numbers it starts from the bottom (e.g. -1 = last position)
      """
      if self.qty() == 0 or i > self.qty() - 1:
         return None
      return self.defList[i]


   # ============================================================================
   # setPolygonAt
   # ============================================================================
   def setPolygonAt(self, polygon, i):
      """the function sets the i-th polygon"""
      return self.getPolygonAt(i).set(polygon)


   # ============================================================================
   # fromMultiPolygon
   # ============================================================================
   def fromMultiPolygon(self, polygonList):
      """the function initializes a list of polygons that makes up the multipolygon passed in the form of a list of points."""
      self.removeAll()
      polygon = QadPolygon()

      for points in polygonList:
         # check if it is a polygon
         if polygon.fromPolygon(points):
            self.append(polygon)

      if self.qty() == 0: return False
      return True


   # ============================================================================
   # fromGeom
   # ============================================================================
   def fromGeom(self, geom):
      """the function initializes the multipolygon from a QgsGeometry object."""
      return self.fromMultiPolygon(geom.asMultiPolygon())


   # ===============================================================================
   # asMultiPolygon
   # ===============================================================================
   def asMultiPolygon(self, tolerance2ApproxCurve = None, atLeastNSegment = None):
      """the function returns a list of lists of lists of points that make up a multipolygon."""
      result = []
      for polygon in self.defList:
         result.append(polygon.asPolygon(tolerance2ApproxCurve, atLeastNSegment))

      return result


   # ===============================================================================
   # asGeom
   # ===============================================================================
   def asGeom(self, wkbType = QgsWkbTypes.LineString, tolerance2ApproxCurve = None, atLeastNSegment = None):
      """the function returns the multipolygon in the form of QgsGeometry."""
      flatType = QgsWkbTypes.flatType(wkbType)

      if flatType == QgsWkbTypes.MultiSurface: # Geometry that is combined from several Curvepolygons is called MultiSurface
         multiSurface = QgsMultiSurface()
         for polygon in self.defList:
            multiSurface.addGeometry(polygon.asAbstractGeom(QgsWkbTypes.CurvePolygon, tolerance2ApproxCurve, atLeastNSegment))
         return QgsGeometry(multiSurface)

      return QgsGeometry.fromMultiPolygonXY(self.asMultiPolygon(tolerance2ApproxCurve, atLeastNSegment))


   # ===============================================================================
   # copy
   # ===============================================================================
   def copy(self):
      # required
      return QadMultiPolygon(self)


   # ============================================================================
   # move
   # ============================================================================
   def move(self, offsetX, offsetY):
      """the function moves the polygons according to an X and a Y offset"""
      for polygon in self.defList:
         polygon.move(offsetX, offsetY)


   # ============================================================================
   # rotate
   # ============================================================================
   def rotate(self, basePt, angle):
      for polygon in self.defList:
         polygon.rotate(basePt, angle)


   # ============================================================================
   # scale
   # ============================================================================
   def scale(self, basePt, scale):
      for polygon in self.defList:
         polygon.scale(basePt, scale)


   # ============================================================================
   # mirror
   # ============================================================================
   def mirror(self, mirrorPt, mirrorAngle):
      for polygon in self.defList:
         polygon.mirror(mirrorPt, mirrorAngle)


   # ============================================================================
   # qty
   # ============================================================================
   def qty(self):
      """the function returns the quantity of polygons that make up the multipolygon."""
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
      """the function returns a new multipolygon with the transformed coordinates."""
      result = QadMultiPolygon()
      for polygon in self.defList:
         result.append(polygon.transform(coordTransform))
      return result


   # ===============================================================================
   # transformFromCRSToCRS
   # ===============================================================================
   def transformFromCRSToCRS(self, sourceCRS, destCRS):
      """the function transforms the coordinates of the points that make up the multipolygon."""
      return self.transform(QgsCoordinateTransform(sourceCRS, destCRS, QgsProject.instance()))


   # ===============================================================================
   # getBoundingBox
   # ===============================================================================
   def getBoundingBox(self):
      """the function returns the rectangle that encloses the multipolygon."""
      boundingBox = self.getPolygonAt(0).getBoundingBox()
      i = 1
      while i < self.qty():
         boundingBox.combineExtentWith(self.getPolygonAt(i).getBoundingBox())
         i = i + 1

      return boundingBox


   # ===============================================================================
   # containsPt
   # ===============================================================================
   def containsPt(self, pt):
      """the function returns True if the point is on the multi-polygon, otherwise False."""
      for polygon in self.defList:
         if polygon.containsPt(pt): return True

      return False


# ===============================================================================
# fromQgsGeomtoQadGeom
# ===============================================================================
def fromQgsGeomToQadGeom(QgsGeom, crs = None):
   """the function returns a QAD geometry from a QGIS geometry and its coordinate system.
      The coordinates of the QAD geometry are those of the canvas for working with xy plane coordinates
   """
   g = QgsGeometry(QgsGeom)

   if crs is None:
      g = QgsGeom
   else:
      # I transform the geometry in the canvas crs to work with xy plane coordinates
      canvasCrs = qgis.utils.iface.mapCanvas().mapSettings().destinationCrs()
      if crs != canvasCrs:
         coordTransform = QgsCoordinateTransform(crs, canvasCrs, QgsProject.instance())
         g.transform(coordTransform)

   # commented because if I have a polygon and divide it into 2 parts it becomes invalid but you want to manage it anyway
   # sometimes coordinate transformation generates invalid objects
   #if g.isGeosValid() == False: return None
   gType = g.type()
   if g.isMultipart() == False:
      if gType == QgsWkbTypes.PointGeometry:
         qadGeom = QadPoint()
         if qadGeom.fromGeom(g): return qadGeom
      elif gType == QgsWkbTypes.LineGeometry:
         return QadLinearObject.fromGeom(g)
      elif gType == QgsWkbTypes.PolygonGeometry:
         qadGeom = QadPolygon()
         if qadGeom.fromGeom(g): return qadGeom
   else:
      if gType == QgsWkbTypes.PointGeometry:
         qadGeom = QadMultiPoint()
         if qadGeom.fromGeom(g): return qadGeom
      elif gType == QgsWkbTypes.LineGeometry:
         qadGeom = QadMultiLinearObject()
         if qadGeom.fromGeom(g): return qadGeom
      elif gType == QgsWkbTypes.PolygonGeometry:
         qadGeom = QadMultiPolygon()
         if qadGeom.fromGeom(g): return qadGeom

   return None


# ===============================================================================
# fromQadGeomToQgsGeom
# ===============================================================================
def fromQadGeomToQgsGeom(qadGeom, layer):
   """the function returns a QGIS geometry from a QAD geometry.
      The coordinates of the QAD geometry are those of the canvas for working with xy plane coordinates
   """
   g = qadGeom.asGeom(layer.wkbType())
   if g is None: return None

   # I transform the geometry in the layer crs (the QAD geometry is in the canvas system to work with xy plane coordinates)
   canvasCrs = qgis.utils.iface.mapCanvas().mapSettings().destinationCrs()
   if layer.crs() != canvasCrs:
      coordTransform = QgsCoordinateTransform(canvasCrs, layer.crs(), QgsProject.instance())
      g.transform(coordTransform)

   return g


# ===============================================================================
# getQadGeomAt
# ===============================================================================
def getQadGeomAt(qadGeom, atGeom = 0, atSubGeom = 0):
   """the function returns the geometry to the specified position"""
   qadGeomType = qadGeom.whatIs()
   if qadGeomType == "MULTI_POINT":
      return None if atSubGeom != 0 else qadGeom.getPointAt(atGeom)
   elif qadGeomType == "MULTI_LINEAR_OBJ":
      return None if atSubGeom != 0 else qadGeom.getLinearObjectAt(atGeom)
   elif qadGeomType == "MULTI_POLYGON":
      g = qadGeom.getPolygonAt(atGeom)
      if g is None: return None
      return g.getClosedObjectAt(atSubGeom)
   elif qadGeomType == "POLYGON":
      return None if atGeom != 0 else qadGeom.getClosedObjectAt(atSubGeom)
   else:
      return None if atGeom != 0 or atSubGeom != 0 else qadGeom


# ===============================================================================
# getQadGeomPartAt
# ===============================================================================
def getQadGeomPartAt(qadGeom, atGeom = 0, atSubGeom = 0, atPart = 0):
   """the function returns the part of the geometry to the specified position"""
   subQadGeom = getQadGeomAt(qadGeom, atGeom, atSubGeom)
   if subQadGeom is None: return None
   qadSubGeomType = subQadGeom.whatIs()
   if qadSubGeomType == "POLYLINE":
      return subQadGeom.getLinearObjectAt(atPart)
   else:
      return subQadGeom


# ===============================================================================
# setQadGeomAt
# ===============================================================================
def setQadGeomAt(qadGeom, newGeom, atGeom = 0, atSubGeom = 0):
   """the function returns the new modified geometry at the specified position"""
   qadGeomType = qadGeom.whatIs()
   if qadGeomType == "MULTI_POINT" or qadGeomType == "MULTI_LINEAR_OBJ":
      if atSubGeom != 0: return None
      newQadGeom = qadGeom.copy()
      newQadGeom.remove(atGeom)
      newQadGeom.insert(atGeom, newGeom)
   elif qadGeomType == "MULTI_POLYGON":
      newQadGeom = qadGeom.copy()
      if atSubGeom == 0:
         newQadGeom.remove(atGeom)
         newQadGeom.insert(atGeom, newGeom)
      else:
         g = newQadGeom.getPolygonAt(atGeom)
         g.remove(atSubGeom)
         g.insert(atSubGeom, newGeom)
   elif qadGeomType == "POLYGON":
      if atGeom != 0: return None
      newQadGeom = qadGeom.copy()
      newQadGeom.remove(atSubGeom)
      newQadGeom.insert(atSubGeom, newGeom)
   else:
      if atGeom != 0 or atSubGeom != 0: return None
      newQadGeom = newGeom

   return newQadGeom


# ===============================================================================
# delQadGeomAt
# ===============================================================================
def delQadGeomAt(qadGeom, atGeom = 0, atSubGeom = 0):
   """the function deletes the sub-geometry at the specified position"""
   qadGeomType = qadGeom.whatIs()
   if qadGeomType == "MULTI_POINT":
      if atSubGeom != 0:
         return False
      else:
         del qadGeom.defList[atGeom]
         return True
   elif qadGeomType == "MULTI_LINEAR_OBJ":
      if atSubGeom != 0:
         return False
      else:
         del qadGeom.defList[atGeom]
         return True
   elif qadGeomType == "MULTI_POLYGON":
      g = qadGeom.getPolygonAt(atGeom)
      if g is None:
         return False
      del g.defList[atSubGeom]
      return True
   elif qadGeomType == "POLYGON":
      if atGeom != 0:
         return False
      else:
         del qadGeom.defList[atSubGeom]
      return True
   else:
      return False


# ===============================================================================
# isLinearQadGeom
# ===============================================================================
def isLinearQadGeom(qadGeom):
   """the function returns True if it is a linear geometry"""
   gType = qadGeom.whatIs()
   if gType == "POLYLINE" or gType == "LINE" or gType == "ARC" or gType == "ELLIPSE_ARC":
      return True
   else:
      return False


# ===============================================================================
# convertToPolyline
# ===============================================================================
def convertToPolyline(qadGeom):
   """the function transforms a geometry into QadPolyline, if possible"""
   gType = qadGeom.whatIs()
   if gType != "POLYLINE" and gType != "LINE" and gType != "ARC" and gType != "ELLIPSE_ARC":
      return None
   if gType == "POLYLINE":
      polyline = qadGeom.copy()
   else:
      polyline = QadPolyline()
      polyline.append(qadGeom)

   return polyline


# ===============================================================================
# QadGeomBoundingBoxCache class
# class to quickly searc which parts of a polyline or polygon or multi object intersect with
# a boundingBox.
# ===============================================================================
class QadGeomBoundingBoxCache():

   def __init__(self, geom):
      # create a temporary layer in memory
      self.cacheLayer = createMemoryLayer("QadLayerCacheArea", "Polygon", qgis.utils.iface.mapCanvas().mapSettings().destinationCrs())

      provider = self.cacheLayer.dataProvider()
      provider.addAttributes([QgsField("geom_at", QMetaType.Int, "Int")]) # geometry code
      provider.addAttributes([QgsField("sub_geom_at", QMetaType.Int, "Int")]) # sub geometry code
      provider.addAttributes([QgsField("part_at", QMetaType.Int, "Int")]) # part code
      self.cacheLayer.updateFields()

      if provider.capabilities() & QgsVectorDataProvider.CreateSpatialIndex:
         provider.createSpatialIndex()

      if self.cacheLayer.startEditing() == False: return

      geomAt = 0
      subGeomAt = 0
      partAt = 0
      error = False
      geomType = geom.whatIs()

      if geomType == "MULTI_POINT":
         for geomAt in range(0, geom.qty()):
            if self.insertBoundingBox(self.getPointAt(geomAt).getBoundingBox(), geomAt, subGeomAt, partAt) == False:
               error = True
               break

      elif geomType == "MULTI_LINEAR_OBJ":
         for geomAt in range(0, geom.qty()):
            linearObj =  geom.getLinearObjectAt(geomAt)
            if linearObj.whatIs() == "POLYLINE":
               for partAt in range(0, linearObj.qty()):
                  part = linearObj.getLinearObjectAt(partAt)
                  if self.insertBoundingBox(part.getBoundingBox(), geomAt, subGeomAt, partAt) == False:
                     error = True
                     break
            else:
               if self.insertBoundingBox(linearObj.getBoundingBox(), geomAt, subGeomAt, partAt) == False:
                  error = True
            if error: break

      elif geomType == "POLYLINE":
         for partAt in range(0, geom.qty()):
            part = geom.getLinearObjectAt(partAt)
            if self.insertBoundingBox(part.getBoundingBox(), geomAt, subGeomAt, partAt) == False:
               error = True
               break

      elif geomType == "POLYGON":
         for subGeomAt in range(0, geom.qty()):
            closedObj = geom.getClosedObjectAt(geomAt)
            for partAt in range(0, closedObj.qty()):
               part = closedObj.getLinearObjectAt(partAt)
               if self.insertBoundingBox(part.getBoundingBox(), geomAt, subGeomAt, partAt) == False:
                  error = True
                  break
            if error: break

      elif geomType == "MULTI_POLYGON":
         for geomAt in range(0, geom.qty()):
            polygon = geom.getPolygonAt(geomAt)
            for subGeomAt in range(0, polygon.qty()):
               closedObj =  subGeomAt.getClosedObjectAt(subGeomAt)
               for partAt in range(0, closedObj.qty()):
                  part = closedObj.getLinearObjectAt(partAt)
                  if self.insertBoundingBox(part.getBoundingBox(), geomAt, subGeomAt, partAt) == False:
                     error = True
                     break
               if error: break
            if error: break

      else:
         error = True if self.insertBoundingBox(geom.getBoundingBox(), geomAt, subGeomAt, partAt) == False else False

      if error:
         self.cacheLayer.rollBack()
         del self.cacheLayer
         self.cacheLayer = None
      else:
         self.cacheLayer.commitChanges()


   # ============================================================================
   # __del__
   # ============================================================================
   def __del__(self):
      del self.cacheLayer
      self.cacheLayer = None


   # ============================================================================
   # insertBoundingBox
   # ============================================================================
   def insertBoundingBox(self, boundingBox, geomAt, subGeomAt, partAt):
      newFeature = QgsFeature()
      newFeature.initAttributes(3)
      newFeature.setAttribute(0, geomAt)
      newFeature.setAttribute(1, subGeomAt)
      newFeature.setAttribute(2, partAt)
      newFeature.setGeometry(QgsGeometry().fromRect(boundingBox))
      return self.cacheLayer.addFeature(newFeature)


   # ============================================================================
   # getIntersectionWithBoundingBox
   # ============================================================================
   def getIntersectionWithBoundingBox(self, boundingBox):
      request = QgsFeatureRequest()
      request.setFilterRect(boundingBox)
      request.setSubsetOfAttributes([])

      feature = QgsFeature()
      result = []
      featureIterator = self.cacheLayer.getFeatures(request)
      for feature in featureIterator:
         geom_at = feature.attribute("geom_at")
         sub_geom_at = feature.attribute("sub_geom_at")
         part_at = feature.attribute("part_at")
         result.append((geom_at, sub_geom_at, part_at))

      return result


   # ============================================================================
   # getTotalBoundingBox
   # ============================================================================
   def getTotalBoundingBox(self):
      feature = QgsFeature()
      featureIterator = self.cacheLayer.getFeatures(qad_utils.getFeatureRequest())
      result = None
      for feature in featureIterator:
         if result is None:
            result = feature.geometry().boundingBox()
         else:
            result.combineExtentWith(feature.geometry().boundingBox())
      return result