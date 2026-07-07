# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 functions for stretching graphical objects

                              -------------------
        begin                : 2013-11-11
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


from . import qad_utils
from .qad_variables import QadVariables
from .qad_msg import QadMsg
from .qad_snapper import *
from .qad_point import QadPoint
from .qad_ellipse import QadEllipse
from .qad_ellipse_arc import QadEllipseArc


# ===============================================================================
# isPtContainedForStretch
# ===============================================================================
def isPtContainedForStretch(point, containerGeom, tolerance=None):
   """Helper function for stretch functions (stretchPoint and stretchQgsLineStringGeometry).
      If containerGeom is a QgsGeometry object then it returns True if the point is spatially contained
      from containerGeom geometry.
      If containerGeom is a list of points then it returns True if the point is among those in the list.
   """
   if type(containerGeom) == QgsGeometry: # geometry
      return containerGeom.contains(point)
   elif type(containerGeom) == list: # list of points
      if tolerance is None:
         myTolerance = QadVariables.get(QadMsg.translate("Environment variables", "TOLERANCE2COINCIDENT"))
      else:
         myTolerance = tolerance

      for containerPt in containerGeom:
         if qad_utils.ptNear(containerPt, point, myTolerance): # if the points are sufficiently close
            return True
   return False


# ===============================================================================
# stretchQadGeometry
# ===============================================================================
def stretchQadGeometry(geom, ptListToStretch, offsetX, offsetY):
   """Stretch a qad entity in planar coordinates using grip points
      geom = qad entity to stretch
      ptListToStretch = list of geom points to stretch
      offsetX = offsetX
      offsetY = Y offset
   """
   if type(geom) == list: # entity composed of multiple geometries
      res = []
      iSub = 0
      for subGeom in geom:
         res.append(stretchQadGeometry(subGeom, ptListToStretch, offsetX, offsetY))
         iSub = iSub + 1
      return res
   else:
      gType = geom.whatIs()
      if gType == "POINT":
         return stretchPoint(geom, ptListToStretch, offsetX, offsetY)
      if gType == "MULTI_POINT":
         return stretchMultiPoint(geom, ptListToStretch, offsetX, offsetY)
      elif gType == "LINE":
         return stretchLine(geom, ptListToStretch, offsetX, offsetY)
      elif gType == "ARC":
         return stretchArc(geom, ptListToStretch, offsetX, offsetY)
      elif gType == "CIRCLE":
         return stretchCircle(geom, ptListToStretch, offsetX, offsetY)
      elif gType == "ELLIPSE":
         return stretchEllipse(geom, ptListToStretch, offsetX, offsetY)
      elif gType == "ELLIPSE_ARC":
         return stretchEllipseArc(geom, ptListToStretch, offsetX, offsetY)
      elif gType == "POLYLINE":
         return stretchPolyline(geom, ptListToStretch, offsetX, offsetY)
      elif gType == "MULTI_LINEAR_OBJ":
         return stretchMultiLinearObj(geom, ptListToStretch, offsetX, offsetY)
      elif gType == "POLYGON":
         return stretchPolygon(geom, ptListToStretch, offsetX, offsetY)
      elif gType == "MULTI_POLYGON":
         return stretchMultiPolygon(geom, ptListToStretch, offsetX, offsetY)

   return None


# ===============================================================================
# stretchPoint
# ===============================================================================
def stretchPoint(point, containerGeom, offsetX, offsetY):
   """Returns a new stretched point if it is contained in containerGeom
      point = point to stretch
      containerGeom = can be a QgsGeometry representing a polygon containing the geom points to stretch
                      or a list of points to iron
      offsetX = offsetX
      offsetY = Y offset
   """
   stretchedGeom = QadPoint(point)
   if isPtContainedForStretch(point, containerGeom): # if the point is contained in containerGeom
      stretchedGeom.move(offsetX, offsetY)

   return stretchedGeom


# ===============================================================================
# stretchMultiPoint
# ===============================================================================
def stretchMultiPoint(multiPoint, containerGeom, offsetX, offsetY):
   """Returns a new stretched multi point if it is contained in containerGeom
      point = point to stretch
      containerGeom = can be a QgsGeometry representing a polygon containing the geom points to stretch
                      or a list of points to iron
      offsetX = offsetX
      offsetY = Y offset
   """
   multiPointToStretch = multiPoint.copy()
   i = 0
   while i < multiPointToStretch.qty():
      point = multiPointToStretch.getPointAt(i)
      newPoint = stretchPoint(point, containerGeom, offsetX, offsetY)
      point.set(newPoint)
      i = i + 1

   return multiPointToStretch


# ===============================================================================
# stretchCircle
# ===============================================================================
def stretchCircle(circle, containerGeom, offsetX, offsetY):
   """Stretch a circle using the points that are contained in containerGeom
      circle = circle to stretch
      containerGeom = can be a QgsGeometry representing a polygon containing the geom points to stretch
                      or a list of points to iron
      offsetX = offsetX
      offsetY = Y offset
   """

   newCircle = circle.copy()
   newCenter = QgsPointXY(circle.center)
   newRadius = circle.radius

   if isPtContainedForStretch(circle.center, containerGeom): # if the center is contained in containerGeom
      newCenter.set(circle.center.x() + offsetX, circle.center.y() + offsetY) # I move the circle
   else:
      if type(containerGeom) == list: # list of points
         for containerPt in containerGeom:
            # whereIsPt returns -1 if the point is internal, 0 if it is on the circumference, 1 if it is external
            if circle.whereIsPt(containerPt) == 0:
               newPt = QgsPointXY(containerPt.x() + offsetX, containerPt.y() + offsetY)
               newRadius = qad_utils.getDistance(circle.center, newPt)
               break
      else: # geometry
         # returns the quadrant points
         quadrants = circle.getQuadrantPoints()
         for quadrant in quadrants:
            if isPtContainedForStretch(quadrant, containerGeom): # if the quadrant is contained in containerGeom
               newPt = QgsPointXY(quadrant.x() + offsetX, quadrant.y() + offsetY)
               newRadius = qad_utils.getDistance(circle.center, newPt)
               break

   return newCircle.set(newCenter, newRadius)


# ===============================================================================
# stretchArc
# ===============================================================================
def stretchArc(arc, containerGeom, offsetX, offsetY):
   """Stretch the grip points of an arc that are contained in containerGeom
      arc = arc to stretch
      containerGeom = can be a QgsGeometry representing a polygon containing the geom points to stretch
                      or a list of points to iron
      offsetX = offsetX
      offsetY = Y offset
   """
   newArc = arc.copy()

   if isPtContainedForStretch(arc.center, containerGeom): # if the center is contained in containerGeom
      newArc.center.set(arc.center.x() + offsetX, arc.center.y() + offsetY)
   else:
      startPt = arc.getStartPt()
      endPt = arc.getEndPt()
      middlePt = arc.getMiddlePt()
      newStartPt = QgsPointXY(startPt)
      newEndPt = QgsPointXY(endPt)
      newMiddlePt = QgsPointXY(middlePt)

      if isPtContainedForStretch(startPt, containerGeom): # if the starting point is contained in containerGeom
         newStartPt.set(startPt.x() + offsetX, startPt.y() + offsetY)

      if isPtContainedForStretch(endPt, containerGeom): # if the end point is contained in containerGeom
         newEndPt.set(endPt.x() + offsetX, endPt.y() + offsetY)

      if isPtContainedForStretch(middlePt, containerGeom): # if the midpoint is contained in containerGeom
         newMiddlePt.set(middlePt.x() + offsetX, middlePt.y() + offsetY)

      if newArc.reversed:
         if newArc.fromStartSecondEndPts(newEndPt, newMiddlePt, newStartPt) == False:
            return None
      else:
         if newArc.fromStartSecondEndPts(newStartPt, newMiddlePt, newEndPt) == False:
            return None

   return newArc


# ===============================================================================
# stretchEllipse
# ===============================================================================
def stretchEllipse(ellipse, containerGeom, offsetX, offsetY):
   """Stretch the grip points of an ellipse that are contained in containerGeom
      ellipse = ellipse to stretch
      containerGeom = can be a QgsGeometry representing a polygon containing the geom points to stretch
                      or a list of points to iron
      offsetX = offsetX
      offsetY = Y offset
   """
   newCenter = QgsPointXY(ellipse.center)
   newMajorAxisFinalPt = QgsPointXY(ellipse.majorAxisFinalPt)
   a = qad_utils.getDistance(ellipse.center, ellipse.majorAxisFinalPt) # semi-major axis
   b = a * ellipse.axisRatio # semi-minor axis
   angle = ellipse.getRotation()
   newAxisRatio = ellipse.axisRatio

   if isPtContainedForStretch(ellipse.center, containerGeom): # if the center is contained in containerGeom
      newCenter.set(ellipse.center.x() + offsetX, ellipse.center.y() + offsetY)
      newMajorAxisFinalPt.set(ellipse.majorAxisFinalPt.x() + offsetX, ellipse.majorAxisFinalPt.y() + offsetY)
   else:
      # returns the quadrant points: starting from majorAxisFinalPt in counterclockwise order
      quadrants = ellipse.getQuadrantPoints()
      majorAxisFinalPt1 = quadrants[0]
      majorAxisFinalPt2 = quadrants[2]
      minorAxisFinalPt1 = quadrants[1]
      minorAxisFinalPt2 = quadrants[3]

      if isPtContainedForStretch(majorAxisFinalPt1, containerGeom): # if the quadrant is contained in containerGeom
         pt = QgsPointXY(majorAxisFinalPt1.x() + offsetX, majorAxisFinalPt1.y() + offsetY)
         newA = qad_utils.getDistance(ellipse.center, pt) # nuovo semi-major axis
         newMajorAxisFinalPt = qad_utils.getPolarPointByPtAngle(ellipse.center, angle, newA)
         newAxisRatio = b / newA
      elif isPtContainedForStretch(majorAxisFinalPt2, containerGeom): # if the quadrant is contained in containerGeom
         pt = QgsPointXY(majorAxisFinalPt2.x() + offsetX, majorAxisFinalPt2.y() + offsetY)
         newA = qad_utils.getDistance(ellipse.center, pt) # nuovo semi-major axis
         newMajorAxisFinalPt = qad_utils.getPolarPointByPtAngle(ellipse.center, angle, newA)
         newAxisRatio = b / newA
      elif isPtContainedForStretch(minorAxisFinalPt1, containerGeom): # if the quadrant is contained in containerGeom
         pt = QgsPointXY(minorAxisFinalPt1.x() + offsetX, minorAxisFinalPt1.y() + offsetY)
         newB = qad_utils.getDistance(ellipse.center, pt) # nuovo semi-minor axis
         newAxisRatio = newB / a
      elif isPtContainedForStretch(minorAxisFinalPt2, containerGeom): # if the quadrant is contained in containerGeom
         pt = QgsPointXY(minorAxisFinalPt2.x() + offsetX, minorAxisFinalPt2.y() + offsetY)
         newB = qad_utils.getDistance(ellipse.center, pt) # nuovo semi-minor axis
         newAxisRatio = newB / a

   newEllipse = QadEllipse()
   return newEllipse.set(newCenter, newMajorAxisFinalPt, newAxisRatio)


# ===============================================================================
# stretchEllipseArc
# ===============================================================================
def stretchEllipseArc(ellipseArc, containerGeom, offsetX, offsetY):
   """Stretch the grip points of an ellipse arc that are contained in containerGeom
      ellipseArc = ellipse arc to stretch
      containerGeom = can be a QgsGeometry representing a polygon containing the geom points to stretch
                      or a list of points to iron
      offsetX = offsetX
      offsetY = Y offset
   """
   newCenter = QgsPointXY(ellipseArc.center)
   newMajorAxisFinalPt = QgsPointXY(ellipseArc.majorAxisFinalPt)
   a = qad_utils.getDistance(ellipseArc.center, ellipseArc.majorAxisFinalPt) # semi-major axis
   b = a * ellipseArc.axisRatio # semi-minor axis
   angle = ellipseArc.getRotation()
   startPt = ellipseArc.getStartPt()
   endPt = ellipseArc.getEndPt()
   newAxisRatio = ellipseArc.axisRatio
   newStartAngle = ellipseArc.startAngle
   newEndAngle = ellipseArc.endAngle

   if isPtContainedForStretch(ellipseArc.center, containerGeom): # if the center is contained in containerGeom
      newCenter.set(ellipseArc.center.x() + offsetX, ellipseArc.center.y() + offsetY)
      newMajorAxisFinalPt.set(ellipseArc.majorAxisFinalPt.x() + offsetX, ellipseArc.majorAxisFinalPt.y() + offsetY)
   else:
      # returns the quadrant points: starting from majorAxisFinalPt in counterclockwise order
      quadrants = ellipseArc.getQuadrantPoints()
      majorAxisFinalPt1 = quadrants[0]
      majorAxisFinalPt2 = quadrants[2]
      minorAxisFinalPt1 = quadrants[1]
      minorAxisFinalPt2 = quadrants[3]

      if majorAxisFinalPt1 is not None and isPtContainedForStretch(majorAxisFinalPt1, containerGeom): # if the quadrant is contained in containerGeom
         pt = QgsPointXY(majorAxisFinalPt1.x() + offsetX, majorAxisFinalPt1.y() + offsetY)
         newA = qad_utils.getDistance(ellipseArc.center, pt) # nuovo semi-major axis
         newMajorAxisFinalPt = qad_utils.getPolarPointByPtAngle(ellipseArc.center, angle, newA)
         newAxisRatio = b / newA
      elif majorAxisFinalPt2 is not None and isPtContainedForStretch(majorAxisFinalPt2, containerGeom): # if the quadrant is contained in containerGeom
         pt = QgsPointXY(majorAxisFinalPt2.x() + offsetX, majorAxisFinalPt2.y() + offsetY)
         newA = qad_utils.getDistance(ellipseArc.center, pt) # nuovo semi-major axis
         newMajorAxisFinalPt = qad_utils.getPolarPointByPtAngle(ellipseArc.center, angle, newA)
         newAxisRatio = b / newA
      elif minorAxisFinalPt1 is not None and isPtContainedForStretch(minorAxisFinalPt1, containerGeom): # if the quadrant is contained in containerGeom
         pt = QgsPointXY(minorAxisFinalPt1.x() + offsetX, minorAxisFinalPt1.y() + offsetY)
         newB = qad_utils.getDistance(ellipseArc.center, pt) # nuovo semi-minor axis
         newAxisRatio = newB / a
      elif minorAxisFinalPt2 is not None and isPtContainedForStretch(minorAxisFinalPt2, containerGeom): # if the quadrant is contained in containerGeom
         pt = QgsPointXY(minorAxisFinalPt2.x() + offsetX, minorAxisFinalPt2.y() + offsetY)
         newB = qad_utils.getDistance(ellipseArc.center, pt) # nuovo semi-minor axis
         newAxisRatio = newB / a
      elif isPtContainedForStretch(startPt, containerGeom): # if the starting point is contained in containerGeom
         newStartPt = QgsPointXY()
         newStartPt.set(startPt.x() + offsetX, startPt.y() + offsetY)
         newStartAngle = qad_utils.getAngleBy2Pts(ellipseArc.center, newStartPt) - angle
      elif isPtContainedForStretch(endPt, containerGeom): # if the end point is contained in containerGeom
         newEndPt = QgsPointXY()
         newEndPt.set(endPt.x() + offsetX, endPt.y() + offsetY)
         newEndAngle = qad_utils.getAngleBy2Pts(ellipseArc.center, newEndPt) - angle

   newEllipseArc = QadEllipseArc()
   return newEllipseArc.set(newCenter, newMajorAxisFinalPt, newAxisRatio, newStartAngle, newEndAngle)


# ===============================================================================
# stretchLine
# ===============================================================================
def stretchLine(line, containerGeom, offsetX, offsetY):
   """Stretch the grip points of a qadLine that are contained in containerGeom
      line = geometry to stretch
      containerGeom = can be a QgsGeometry representing a polygon containing the geom points to stretch
                      or a list of points to iron
      offsetX = offsetX
      offsetY = Y offset
   """
   lineToStretch = line.copy()

   pt = lineToStretch.getStartPt()
   if isPtContainedForStretch(pt, containerGeom): # if the point is contained in containerGeom
      # starting point change
      pt.setX(pt.x() + offsetX)
      pt.setY(pt.y() + offsetY)
      lineToStretch.setStartPt(pt)

   pt = lineToStretch.getEndPt()
   if isPtContainedForStretch(pt, containerGeom): # if the point is contained in containerGeom
      # end point change
      pt.setX(pt.x() + offsetX)
      pt.setY(pt.y() + offsetY)
      lineToStretch.setEndPt(pt)

   return lineToStretch


# ===============================================================================
# stretchPolyline
# ===============================================================================
def stretchPolyline(polyline, containerGeom, offsetX, offsetY):
   """Create a new polyline by stretching the grip points that are contained in containerGeom
      polyline = polyline to stretch
      containerGeom = can be a QgsGeometry representing a polygon containing the geom points to stretch
                      or a list of points to iron
      offsetX = offsetX
      offsetY = Y offset
   """
   polylineToStretch = polyline.copy()

   pt = polylineToStretch.getCentroid() # check if polyline has a centroid
   if pt is not None and isPtContainedForStretch(pt, containerGeom): # if the point is contained in containerGeom
      polylineToStretch.move(offsetX, offsetY)
   else:
      i = 0
      while i < polylineToStretch.qty():
         linearObject = polylineToStretch.getLinearObjectAt(i)
         newLinearObject = stretchQadGeometry(linearObject, containerGeom, offsetX, offsetY)
         if (newLinearObject is not None):
            polylineToStretch.insert(i, newLinearObject)
            polylineToStretch.remove(i + 1)

         i = i + 1

      # verifico e correggo i versi delle parti della polilinea
      polylineToStretch.reverseCorrection()

   return polylineToStretch


# ===============================================================================
# stretchMultiLinearObj
# ===============================================================================
def stretchMultiLinearObj(multiLinear, containerGeom, offsetX, offsetY):
   """Create a new linear multi by stretching the grip points that are contained in containerGeom
      polygon = multi linear to stretch
      containerGeom = can be a QgsGeometry representing a polygon containing the geom points to stretch
                      or a list of points to iron
      offsetX = offsetX
      offsetY = Y offset
   """
   multiLinearToStretch = multiLinear.copy()

   i = 0
   while i < multiLinearToStretch.qty():
      linearObject = multiLinearToStretch.getLinearObjectAt(i)
      newLinearObject = stretchQadGeometry(linearObject, containerGeom, offsetX, offsetY)
      multiLinearToStretch.insert(i, newLinearObject)
      multiLinearToStretch.remove(i + 1)

      i = i + 1

   return multiLinearToStretch


# ===============================================================================
# stretchPolygon
# ===============================================================================
def stretchPolygon(polygon, containerGeom, offsetX, offsetY):
   """Create a new polygon by stretching the grip points that are contained in containerGeom
      polygon = polygon to stretch
      containerGeom = can be a QgsGeometry representing a polygon containing the geom points to stretch
                      or a list of points to iron
      offsetX = offsetX
      offsetY = Y offset
   """
   polygonToStretch = polygon.copy()

   pt = polygonToStretch.getCentroid() # check if polyline has a centroid
   if pt is not None and isPtContainedForStretch(pt, containerGeom): # if the point is contained in containerGeom
         polygonToStretch.move(offsetX, offsetY)
   else:
      i = 0
      while i < polygonToStretch.qty():
         closedObject = polygonToStretch.getClosedObjectAt(i)
         newClosedObject = stretchQadGeometry(closedObject, containerGeom, offsetX, offsetY)
         polygonToStretch.insert(i, newClosedObject)
         polygonToStretch.remove(i + 1)

         i = i + 1

   return polygonToStretch


# ===============================================================================
# stretchMultiPolygon
# ===============================================================================
def stretchMultiPolygon(multiPolygon, containerGeom, offsetX, offsetY):
   """Create a new multi-polygon by stretching the grip points that are contained in containerGeom
      multiPolygon = multi polygon to stretch
      containerGeom = can be a QgsGeometry representing a polygon containing the geom points to stretch
                      or a list of points to iron
      offsetX = offsetX
      offsetY = Y offset
   """
   multiPolygonToStretch = multiPolygon.copy()

   pt = multiPolygonToStretch.getCentroid() # check if polyline has a centroid
   if pt is not None and isPtContainedForStretch(pt, containerGeom): # if the point is contained in containerGeom
         multiPolygonToStretch.move(offsetX, offsetY)
   else:
      i = 0
      while i < multiPolygonToStretch.qty():
         polygon = multiPolygonToStretch.getPolygonAt(i)
         newPolygon = stretchQadGeometry(polygon, containerGeom, offsetX, offsetY)
         multiPolygonToStretch.insert(i, newPolygon)
         multiPolygonToStretch.remove(i + 1)

         i = i + 1

   return multiPolygonToStretch