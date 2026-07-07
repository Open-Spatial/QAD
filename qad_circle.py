# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 class for managing circles

                              -------------------
        begin                : 2013-05-22
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

import math
import sys

from . import qad_utils
from .qad_variables import QadVariables
from .qad_msg import QadMsg


# ===============================================================================
# QadCircle circle class
# ===============================================================================
class QadCircle():

   def __init__(self, circle = None):
      if circle is not None:
         self.set(circle.center, circle.radius)
      else:
         self.center = None
         self.radius = None

   def whatIs(self):
      # required
      return "CIRCLE"


   # ============================================================================
   # isClosed
   # ============================================================================
   def isClosed(self):
      return True


   def set(self, center, radius = None):
      if isinstance(center, QadCircle):
         circle = center
         return self.set(circle.center, circle.radius)

      if radius <= 0: return None
      self.center = QgsPointXY(center)
      self.radius = radius
      return self

   def transform(self, coordTransform):
      """Transform this geometry as described by CoordinateTranasform ct."""
      self.center = coordTransform.transform(self.center)

   def transformFromCRSToCRS(self, sourceCRS, destCRS):
      """Transform this geometry as described by CRS."""
      if (sourceCRS is not None) and (destCRS is not None) and sourceCRS != destCRS:
         coordTransform = QgsCoordinateTransform(sourceCRS, destCR, QgsProject.instance()) # I transform the coordinates
         self.center =  coordTransform.transform(self.center)

   def __eq__(self, circle):
      # required
      """self == other"""
      if circle.whatIs() != "CIRCLE": return False
      if self.center != circle.center or self.radius != circle.radius:
         return False
      else:
         return True

   def __ne__(self, circle):
      """self != other"""
      return not self.__eq__(circle)


   def equals(self, circle):
      # geometrically equal (the direction does NOT count)
      return self.__eq__(circle)


   def copy(self):
      # required
      return QadCircle(self)


   def length(self):
      return 2 * math.pi * self.radius


   # ===============================================================================
   # getBoundingBox
   # ===============================================================================
   def getBoundingBox(self):
      """the function returns the rectangle that encloses the circle."""
      return QgsRectangle(self.center.x() - self.radius,
                          self.center.y() - self.radius,
                          self.center.x() + self.radius,
                          self.center.y() + self.radius)


   # ===============================================================================
   # containsPt
   # ===============================================================================
   def containsPt(self, point):
      # required
      """the function returns true if the point is on the circumference of the circle."""
      # whereIsPt returns -1 if the point is internal, 0 if it is on the circumference, 1 if it is external
      return True if self.whereIsPt(point) == 0 else 0


   # ===============================================================================
   # lengthBetween2Points
   # ===============================================================================
   def lengthBetween2Points(self, pt1, pt2, leftOfPt1):
      """Calculate the distance between 2 points on the circle. The arc considered can be
            the one to the left or right of <pt1> (see <leftOfPt1>)
            if <leftOfPt1> is boolean then if = True the arc to the left of pt1 is considered
            if <leftOfPt1> is float then it means that it is the direction of the tangent on pt1
                           and if the direction is to the left, the arc to the left of pt1 is considered
      """
      if qad_utils.ptNear(pt1, pt2): # if the points are so close that they are considered equal
         return 0

      if type(leftOfPt1) == float: # tangent direction on pt1
         startAngle = qad_utils.getAngleBy2Pts(self.center, pt1)
         if qad_utils.doubleNear(qad_utils.normalizeAngle(startAngle + math.pi / 2),
                                 qad_utils.normalizeAngle(leftOfPt1)):
            _leftOfPt1 = True
         else:
            _leftOfPt1 = False
      else: # booolean
         _leftOfPt1 = leftOfPt1

      if _leftOfPt1: # arc to the left of pt1
         startAngle = qad_utils.getAngleBy2Pts(self.center, pt1)
         endAngle = qad_utils.getAngleBy2Pts(self.center, pt2)
      else: # arc to the right of pt1
         startAngle = qad_utils.getAngleBy2Pts(self.center, pt2)
         endAngle = qad_utils.getAngleBy2Pts(self.center, pt1)

      if startAngle < endAngle:
         totalAngle = endAngle - startAngle
      else:
         totalAngle =  (2 * math.pi - startAngle) + endAngle

      return self.radius * totalAngle


   def area(self):
      return math.pi * self.radius * self.radius


   def isPtOnCircle(self, point):
      return True if self.whereIsPt(point) == 0 else False # -1 inside, 0 sulla circonferenza, 1 outside


   # ============================================================================
   # whereIsPt
   # ============================================================================
   def whereIsPt(self, point):
      # returns -1 if the point is internal, 0 if it is on the circumference, 1 if it is external
      dist = self.center.distance(point)
      if qad_utils.doubleNear(dist, self.radius): return 0
      elif dist < self.radius: return -1 # inside
      else: return 1 # outside


   def getQuadrantPoints(self):
      # returns the quadrant points: pt top, pt bottom, right, left of center
      pt1 = QgsPointXY(self.center.x(), self.center.y() + self.radius)
      pt2 = QgsPointXY(self.center.x(), self.center.y()- self.radius)
      pt3 = QgsPointXY(self.center.x() + self.radius, self.center.y())
      pt4 = QgsPointXY(self.center.x() - self.radius, self.center.y())
      return [pt1, pt2, pt3, pt4]




   # ============================================================================
   # asPolyline
   # ============================================================================
   def asPolyline(self, tolerance2ApproxCurve = None, atLeastNSegment = None):
      """returns a list of points that define the circle"""

      if tolerance2ApproxCurve is None:
         tolerance = QadVariables.get(QadMsg.translate("Environment variables", "TOLERANCE2APPROXCURVE"))
      else:
         tolerance = tolerance2ApproxCurve

      if atLeastNSegment is None:
         _atLeastNSegment = QadVariables.get(QadMsg.translate("Environment variables", "CIRCLEMINSEGMENTQTY"), 12)
      else:
         _atLeastNSegment = atLeastNSegment

      # Calculate the length of the segment with Pythagoras
      dummy      = self.radius - tolerance
      if dummy <= 0: # if the tolerance is too low compared to the radius
         SegmentLen = self.radius
      else:
         dummy      = (self.radius * self.radius) - (dummy * dummy)
         SegmentLen = math.sqrt(dummy) # radice quadrata
         SegmentLen = SegmentLen * 2

      if SegmentLen == 0: # if the tolerance is too low the length of the segment becomes zero
         return None

      # calculate how many segments are needed (not less than _atLeastNSegment)
      SegmentTot = math.ceil(self.length() / SegmentLen)
      if SegmentTot < _atLeastNSegment:
         SegmentTot = _atLeastNSegment

      points = []
      # first point
      firsPt = qad_utils.getPolarPointByPtAngle(self.center, 0, self.radius)
      points.append(firsPt)

      i = 1
      angle = 0
      offsetAngle = 2 * math.pi / SegmentTot
      while i < SegmentTot:
         angle = angle + offsetAngle
         pt = qad_utils.getPolarPointByPtAngle(self.center, angle, self.radius)
         points.append(pt)
         i = i + 1

      # last point (same as the first)
      points.append(firsPt)
      return points


   # ===============================================================================
   # asCircularString
   # ===============================================================================
   def asCircularString(self):
      """the function returns the circle in the form of circularString."""
      circle = QgsCircle(QgsPoint(self.center), self.radius)
      return circle.toCircularString()


   # ===============================================================================
   # asLineString
   # ===============================================================================
   def asLineString(self, tolerance2ApproxCurve = None, atLeastNSegment = None):
      """the function returns the circle in the form of a lineString."""
      pts = self.asPolyline(tolerance2ApproxCurve, atLeastNSegment)
      if pts is None or len(pts) == 0:
          return None
      return QgsLineString(pts)


   # ===============================================================================
   # asAbstractGeom
   # ===============================================================================
   def asAbstractGeom(self, wkbType = QgsWkbTypes.LineString, tolerance2ApproxCurve = None, atLeastNSegment = None):
      """the function returns the circle in the form of QgsAbstractGeometry."""
      flatType = QgsWkbTypes.flatType(wkbType)

      if flatType == QgsWkbTypes.CompoundCurve:
         circularString = self.asCircularString()
         compoundCurve = QgsCompoundCurve()
         compoundCurve.addCurve(circularString)
         return compoundCurve

      elif flatType == QgsWkbTypes.MultiCurve:
         circularString = self.asCircularString()
         multiCurve = QgsMultiCurve()
         multiCurve.addGeometry(circularString)
         return multiCurve

      elif flatType == QgsWkbTypes.CurvePolygon:
         circularString = self.asCircularString()
         curvePolygon = QgsCurvePolygon()
         curvePolygon.setExteriorRing(circularString)
         return curvePolygon

      elif flatType == QgsWkbTypes.MultiSurface: # Geometry that is combined from several CurvePolygon is called MultiSurface
         curvePolygon = self.asAbstractGeom(QgsWkbTypes.CurvePolygon, tolerance2ApproxCurve, atLeastNSegment)
         multiSurface = QgsMultiSurface()
         multiSurface.addGeometry(curvePolygon)
         return multiSurface

      elif flatType == QgsWkbTypes.Polygon:
         linestring = self.asLineString(tolerance2ApproxCurve, atLeastNSegment)
         polygon = QgsPolygon()
         polygon.setExteriorRing(linestring)
         return polygon

      elif flatType == QgsWkbTypes.MultiPolygon:
         polygon = self.asAbstractGeom(QgsWkbTypes.Polygon, tolerance2ApproxCurve, atLeastNSegment)
         multiPolygon = QgsMultiPolygon()
         multiPolygon.addGeometry(polygon)
         return multiPolygon

      elif flatType == QgsWkbTypes.MultiLineString:
         lineString = self.asLineString(tolerance2ApproxCurve, atLeastNSegment)
         multiLineString = QgsMultiLineString()
         multiLineString.addGeometry(lineString)
         return multiLineString

      return self.asLineString(tolerance2ApproxCurve, atLeastNSegment)


   # ===============================================================================
   # asGeom
   # ===============================================================================
   def asGeom(self, wkbType = QgsWkbTypes.LineString, tolerance2ApproxCurve = None, atLeastNSegment = None):
      """the function returns the circle in the form of QgsGeometry."""
      return QgsGeometry(self.asAbstractGeom(wkbType, tolerance2ApproxCurve, atLeastNSegment))


   # ============================================================================
   # fromPolyline
   # ============================================================================
   def fromPolyline(self, points, atLeastNSegment = None):
      """sets the characteristics of the circle encountered in the list of points
            returns True if a circle was found otherwise False.
            N.B. in points must NOT be in geographic coordinates
      """
      # if the initial and final points do not coincide it is not a circle
      if points[0] != points[-1]:
         return False

      totPoints = len(points)

      if atLeastNSegment is None:
         _atLeastNSegment = QadVariables.get(QadMsg.translate("Environment variables", "CIRCLEMINSEGMENTQTY"), 12)
      else:
         _atLeastNSegment = atLeastNSegment

      # for it to be a circle you need at least _atLeastNSegment segments
      if (totPoints - 1) < _atLeastNSegment or _atLeastNSegment < 2:
         return False

      # I move the first 3 points close to 0.0 to improve the accuracy of the calculations
      dx = points[0].x()
      dy = points[0].y()
      myPoints = []
      myPoints.append(qad_utils.movePoint(points[0], -dx, -dy))
      myPoints.append(qad_utils.movePoint(points[1], -dx, -dy))
      myPoints.append(qad_utils.movePoint(points[2], -dx, -dy))

#       InfinityLinePerpOnMiddle1 = qad_utils.getInfinityLinePerpOnMiddle(myPoints[0], myPoints[1])
#       if InfinityLinePerpOnMiddle1 is None: return False
#       InfinityLinePerpOnMiddle2 = qad_utils.getInfinityLinePerpOnMiddle(myPoints[1], myPoints[2])
#       if InfinityLinePerpOnMiddle2 is None: return False
#
#       # calculate the presumed center with 2 segments
#       center = qad_utils.getIntersectionPointOn2InfinityLines(InfinityLinePerpOnMiddle1[0], \
#                                                               InfinityLinePerpOnMiddle1[1], \
#                                                               InfinityLinePerpOnMiddle2[0], \
#                                                               InfinityLinePerpOnMiddle2[1])
#       if center is None: return False # linee parallele

      # if I use QgsCircle I get better precision
      circle = QgsCircle.from3Points(QgsPoint(myPoints[0]), QgsPoint(myPoints[1]), QgsPoint(myPoints[2]))
      if circle.isEmpty() == True:
         return False

      center = circle.center()
      center = QgsPointXY(center.x(), center.y())
      radius = center.distance(myPoints[0]) # calculate the presumed radius

      # if the end point of the arc is to the left of the
      # segment that joins the initial and intermediate points then the direction is anti-clockwise
      startClockWise = False if qad_utils.leftOfLine(myPoints[2], myPoints[0], myPoints[1]) < 0 else True
      angle = qad_utils.getAngleBy3Pts(myPoints[0], center, myPoints[2], startClockWise)

      i = 3
      while i < totPoints:
         # I move the points closer to 0.0 to improve the accuracy of the calculations
         myPoints.append(qad_utils.movePoint(points[i], -dx, -dy))

         # if TOLERANCE2COINCIDENT = 0.001 a circle of 1000 m is recognized
         # if the calculated point is not close enough to the real point
         # otherwise I find problems with intersections with objects
         if qad_utils.ptNear(qad_utils.getPolarPointByPtAngle(center, qad_utils.getAngleBy2Pts(center, myPoints[i]), radius), \
                             myPoints[i]) == False:
            return False

         # calculate the direction of the arc and the angle
         clockWise = True if qad_utils.leftOfLine(myPoints[i], myPoints[i - 1], myPoints[i - 2]) < 0 else False
         # the direction must be the same as the original one
         if startClockWise != clockWise: return False
         angle = angle + qad_utils.getAngleBy3Pts(myPoints[i-1], center, myPoints[i], startClockWise)
         # the inscribed angle cannot be > 360
         if qad_utils.doubleSmallerOrEquals(angle, 2 * math.pi):
            i = i + 1
         else:
            return False

      self.center = center
      self.radius = radius
      # I translate the geometry to return it to its original position
      self.move(dx, dy)

      return True


   # ============================================================================
   # move
   # ============================================================================
   def move(self, offsetX, offsetY):
      self.center = qad_utils.movePoint(self.center, offsetX, offsetY)


   # ============================================================================
   # rotate
   # ============================================================================
   def rotate(self, basePt, angle):
      self.center = qad_utils.rotatePoint(self.center, basePt, angle)


   # ============================================================================
   # scale
   # ============================================================================
   def scale(self, basePt, scale):
      self.center = qad_utils.scalePoint(self.center, basePt, scale)
      self.radius = self.radius * scale


   # ============================================================================
   # mirror
   # ============================================================================
   def mirror(self, mirrorPt, mirrorAngle):
      self.center = qad_utils.mirrorPoint(self.center, mirrorPt, mirrorAngle)


   # ===============================================================================
   # offset
   # ===============================================================================
   def offset(self, offsetDist, offsetSide):
      """the function modifies the circle by offsetting it
            according to a distance and an offset side ("internal" or "external")
      """
      if offsetSide == "internal":
         # offset towards the inside of the circle
         radius = self.radius - offsetDist
         if radius <= 0:
            return False
      else:
         # offset towards the outside of the circle
         radius = self.radius + offsetDist

      self.radius = radius

      return True


   # ============================================================================
   # fromCenterPtArea
   # ============================================================================
   def fromCenterArea(self, centerPt, area):
      """set the characteristics of the circle through:
            the central point
            area
      """
      if centerPt is None or area <= 0:
         return None
      self.center = centerPt
      self.radius = math.sqrt(area / math.pi)
      return self


   # ============================================================================
   # fromDiamEnds
   # ============================================================================
   def fromDiamEnds(self, startPt, endPt):
      """sets the characteristics of the circle through the end points of the diameter:
            starting point
            final point
      """
      self.radius = qad_utils.getDistance(startPt, endPt) / 2
      if self.radius == 0:
         return None
      self.center = qad_utils.getMiddlePoint(startPt, endPt)
      return self
