# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 class for managing lines

                              -------------------
        begin                : 2018-12-27
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


from . import qad_utils


# ===============================================================================
# QadLine line class
# ===============================================================================
class QadLine():

   def __init__(self, line = None):
      if line is not None:
         self.set(line.pt1, line.pt2)
      else:
         self.pt1 = None
         self.pt2 = None


   def whatIs(self):
      # required
      return "LINE"


   def set(self, pt1, pt2 = None):
      if isinstance(pt1, QadLine):
         line = pt1
         return self.set(line.pt1, line.pt2)

      self.pt1 = QgsPointXY(pt1)
      self.pt2 = QgsPointXY(pt2)
      return self

   def transform(self, coordTransform):
      # required
      """Transform this geometry as described by CoordinateTransform ct."""
      self.pt1 = coordTransform.transform(self.pt1)
      self.pt2 = coordTransform.transform(self.pt2)


   def transformFromCRSToCRS(self, sourceCRS, destCRS):
      # required
      """Transform this geometry as described by CRS."""
      if (sourceCRS is not None) and (destCRS is not None) and sourceCRS != destCRS:
         coordTransform = QgsCoordinateTransform(sourceCRS, destCRS, QgsProject.instance()) # I transform the coordinates
         self.transform(coordTransform)


   def __eq__(self, line):
      # required
      """self == other"""
      if line.whatIs() != "LINE": return False
      # strictly equal (the direction counts)
      if self.pt1 != line.pt1 or self.pt2 != line.pt2:
         return False
      else:
         return True


   def __ne__(self, line):
      """self != other"""
      return not self.__eq__(line)


   def equals(self, line):
      # geometrically equal (the direction does NOT count)
      if line.whatIs() != "LINE": return False
      if self.__eq__(line): return True
      dummy = line.copy()
      dummy.reverse()
      return self.__eq__(dummy)


   def copy(self):
      # required
      return QadLine(self)


   # ============================================================================
   # reverse
   # ============================================================================
   def reverse(self):
      # required
      # I reverse the direction of the line
      dummy = self.pt1
      self.pt1 = self.pt2
      self.pt2 = dummy
      return self

   # ============================================================================
   # getStartPt, setStartPt
   # ============================================================================
   def getStartPt(self):
      # required
      return self.pt1

   def setStartPt(self, pt):
      # required
      self.pt1 = QgsPointXY(pt)


   # ============================================================================
   # getEndPt, setEndPt
   # ============================================================================
   def getEndPt(self):
      # required
      return self.pt2

   def setEndPt(self, pt):
      # required
      self.pt2 = QgsPointXY(pt)


   # ===============================================================================
   # getMiddlePt
   # ===============================================================================
   def getMiddlePt(self):
      """the function returns the midpoint of the line (QgsPointXY)"""
      x = (self.pt1.x() + self.pt2.x()) / 2
      y = (self.pt1.y() + self.pt2.y()) / 2

      return QgsPointXY(x, y)


   # ===============================================================================
   # getBoundingBox
   # ===============================================================================
   def getBoundingBox(self):
      """the function returns the rectangle that encloses the segment."""
      if self.pt1.x() > self.pt2.x():
         xMaxLine = self.pt1.x()
         xMinLine = self.pt2.x()
      else:
         xMaxLine = self.pt2.x()
         xMinLine = self.pt1.x()

      if self.pt1.y() > self.pt2.y():
         yMaxLine = self.pt1.y()
         yMinLine = self.pt2.y()
      else:
         yMaxLine = self.pt2.y()
         yMinLine = self.pt1.y()

      return QgsRectangle(xMinLine, yMinLine, xMaxLine, yMaxLine)


   # ============================================================================
   # getTanDirectionOnPt
   # ============================================================================
   def getTanDirectionOnPt(self, pt = None):
      # required
      """the function returns the direction of the tangent to the object point.
            pt is used only for compatibility with other linear classes (e.g. arc)
      """
      return qad_utils.getAngleBy2Pts(self.getStartPt(), self.getEndPt())


   # ============================================================================
   # getTanDirectionOnStartPt, getTanDirectionOnEndPt, getTanDirectionOnMiddlePt
   # ============================================================================
   def getTanDirectionOnStartPt(self):
      # required
      """the function returns the direction of the tangent to the starting point of the object."""
      return self.getTanDirectionOnPt()

   def getTanDirectionOnEndPt(self):
      # required
      """the function returns the direction of the tangent to the final point of the object."""
      return self.getTanDirectionOnPt()

   def getTanDirectionOnMiddlePt(self):
      # required
      """the function returns the direction of the tangent to the midpoint of the object."""
      return self.getTanDirectionOnPt()


   # ============================================================================
   # fromPt1PolarPt2
   # ============================================================================
   def fromPt1PolarPt2(self, pt1, angle, dist):
      """set the characteristics of the line through:
            starting point
            corner
            distance from the starting point
      """
      self.pt1 = QgsPointXY(pt1)
      self.pt2 = qad_utils.getPolarPointByPtAngle(pt1, angle, dist)
      return True


   # ===============================================================================
   # getXOnInfinityLine
   # ===============================================================================
   def getXOnInfinityLine(self, y):
      """given the Y coordinate of a point the function returns the X coordinate of the same
            on the line
      """

      diffX = self.pt2.x() - self.pt1.x()
      diffY = self.pt2.y() - self.pt1.y()

      if qad_utils.doubleNear(diffX, 0): # if the straight line passing through p1 and p2 is vertical
         return self.pt1.x()
      elif qad_utils.doubleNear(diffY, 0): # if the straight line passing through p1 and p2 is horizontal
         return None # infinite points
      else:
         coeff = diffY / diffX
         return self.pt1.x() + (y - self.pt1.y()) / coeff


   # ===============================================================================
   # getYOnInfinityLine
   # ===============================================================================
   def getYOnInfinityLine(self, x):
      """given the X coordinate of a point the function returns the Y coordinate of the same
            on the line
      """

      diffX = self.pt2.x() - self.pt1.x()
      diffY = self.pt2.y() - self.pt1.y()

      if qad_utils.doubleNear(diffX, 0): # if the straight line passing through p1 and p2 is vertical
         return None # infinite points
      elif qad_utils.doubleNear(diffY, 0): # if the straight line passing through p1 and p2 is horizontal
         return self.pt1.y()
      else:
         coeff = diffY / diffX
         return self.pt1.y() + (x - self.pt1.x()) * coeff


   # ===============================================================================
   # getSqrLength
   # ===============================================================================
   def getSqrLength(self):
      """the function returns the squared length of the line"""
      dx = self.pt2.x() - self.pt1.x()
      dy = self.pt2.y() - self.pt1.y()

      return dx * dx + dy * dy


   # ===============================================================================
   # length
   # ===============================================================================
   def length(self):
      # required
      return math.sqrt(self.getSqrLength())


   # ===============================================================================
   # getMinDistancePtBetweenSegmentAndPt
   # ===============================================================================
   def getMinDistancePtBetweenSegmentAndPt(self, pt):
      """the function returns the minimum distance point and the minimum distance between a segment and a point
            (<minimum distance point><minimum distance>)
      """
      if self.containsPt(pt) == True:
         return [pt, 0]
      perpPt = self.getPerpendicularPointOnInfinityLine(pt)
      if perpPt is not None:
         if self.containsPt(perpPt) == True:
            return [perpPt, perpPt.distance(pt)]

      distFromP1 = self.pt1.distance(pt)
      distFromP2 = self.pt2.distance(pt)
      if distFromP1 < distFromP2:
         return [self.pt1, distFromP1]
      else:
         return [self.pt2, distFromP2]


   # ===============================================================================
   # getPerpendicularPointOnInfinityLine
   # ===============================================================================
   def getPerpendicularPointOnInfinityLine(self, pt):
      """the function returns the perpendicular projection point of pt to the line."""

      diffX = self.pt2.x() - self.pt1.x()
      diffY = self.pt2.y() - self.pt1.y()

      if qad_utils.doubleNear(diffX, 0): # if the straight line passing through p1 and p2 is vertical
         return QgsPointXY(self.pt1.x(), pt.y())
      elif qad_utils.doubleNear(diffY, 0): # if the straight line passing through p1 and p2 is horizontal
         return QgsPointXY(self.pt.x(), pt1.y())
      else:
         coeff = diffY / diffX
         x = (coeff * self.pt1.x() - self.pt1.y() + pt.x() / coeff + pt.y()) / (coeff + 1 / coeff)
         y = coeff * (x - self.pt1.x()) + self.pt1.y()

         return QgsPointXY(x, y)


   # ===============================================================================
   # getInfinityLinePerpOnMiddle
   # ===============================================================================
   def getInfinityLinePerpOnMiddle(self):
      """the function finds a line perpendicular to and passing through the midpoint of the line."""
      ptMiddle = self.getMiddlePt()
      dist = self.pt1.distance(ptMiddle)
      if dist == 0:
         return None
      angle = qad_utils.getAngleBy2Pts(self.pt1, self.pt2) + math.pi / 2
      pt2Middle = qad_utils.getPolarPointByPtAngle(ptMiddle, angle, dist)
      line = QadLine()
      line.set(ptMiddle, pt2Middle)
      return line


   # ===============================================================================
   # isPtOnInfinityLine
   # ===============================================================================
   def isPtOnInfinityLine(self, point):
      """the function returns true if the point is on the segment (extremes included).
            point is of type QgsPointXY.
      """
      y = self.getYOnInfinityLine(point.x())
      if y is None: # the infinite line lineP1-lineP2 is vertical
         if qad_utils.doubleNear(point.x(), self.pt1.x()):
            return True
      else:
         # if the point is on the infinite line that passes from p1-p2
         if qad_utils.doubleNear(point.y(), y):
            return True

      return False


   # ===============================================================================
   # containsPt
   # ===============================================================================
   def containsPt(self, point):
      # required
      """the function returns true if the point is on the segment (extremes included).
            point is of type QgsPointXY.
      """
      if self.pt1.x() < self.pt2.x():
         xMin = self.pt1.x()
         xMax = self.pt2.x()
      else:
         xMax = self.pt1.x()
         xMin = self.pt2.x()

      # check if the point can be on the segment
      if qad_utils.doubleSmaller(point.x(), xMin) or qad_utils.doubleGreater(point.x(), xMax): return False

      if self.pt1.y() < self.pt2.y():
         yMin = self.pt1.y()
         yMax = self.pt2.y()
      else:
         yMax = self.pt1.y()
         yMin = self.pt2.y()

      # check if the point can be on the segment
      if qad_utils.doubleSmaller(point.y(), yMin) or qad_utils.doubleGreater(point.y(), yMax): return False

      return self.isPtOnInfinityLine(point)


   # ===============================================================================
   # leftOf
   # ===============================================================================
   def leftOf(self, pt):
      # required
      """the function returns a number < 0 if the point pt is to the left of the line pt1 -> pt2"""
      f1 = pt.x() - self.pt1.x()
      f2 = self.pt2.y() - self.pt1.y()
      f3 = pt.y() - self.pt1.y()
      f4 = self.pt2.x() - self.pt1.x()
      return f1*f2 - f3*f4


   # ===============================================================================
   # get a and b for line equation (y = ax + b)
   # ===============================================================================
   def get_A_B_LineEquation(self):
      # given 2 points, a and b of the equation of the straight line passing through the two points are calculated (y = ax + b)
      a = (self.pt2.y() - self.pt1.y()) / (self.pt2.x() - self.pt1.x())
      # y = ax + b -> b = y - ax
      b = self.pt1.y() - (a * self.pt1.x())

      return a, b


   # ===============================================================================
   # sqrDist
   # ===============================================================================
   def sqrDist(self, point):
      # required
      """the function returns a list with
            (<minimum distance squared>
             <nearest point>)
      """
      minDistPoint = QgsPointXY()

      if self.pt1.x() == self.pt2.x() and self.pt1.y() == self.pt2.y():
         minDistPoint.setX(self.pt1.x())
         minDistPoint.setY(self.pt1.y())
      else:
         nx = self.pt2.y() - self.pt1.y()
         ny = -( self.pt2.x() - self.pt1.x() )

         t = (point.x() * ny - point.y() * nx - self.pt1.x() * ny + self.pt1.y() * nx ) / \
             (( self.pt2.x() - self.pt1.x() ) * ny - ( self.pt2.y() - self.pt1.y() ) * nx )

         if t < 0.0:
            minDistPoint.setX(self.pt1.x())
            minDistPoint.setY(self.pt1.y())
         elif t > 1.0:
            minDistPoint.setX(self.pt2.x())
            minDistPoint.setY(self.pt2.y())
         else:
            minDistPoint.setX( self.pt1.x() + t *( self.pt2.x() - self.pt1.x() ) )
            minDistPoint.setY( self.pt1.y() + t *( self.pt2.y() - self.pt1.y() ) )

      dist = point.sqrDist(minDistPoint)
      # prevent rounding errors if the point is directly on the segment
      if qad_utils.doubleNear(dist, 0.0):
         minDistPoint.setX( point.x() )
         minDistPoint.setY( point.y() )
         return (0.0, minDistPoint)

      return (dist, minDistPoint)


   # ============================================================================
   # getDistanceFromStart
   # ============================================================================
   def getDistanceFromStart(self, pt):
      # required
      """the function returns the distance of <pt> (which must be on the object or its extension)
            from the starting point.
      """
      dummy = QadLine(self)
      dummy.setEndPt(pt)

      # if the point is on the extension from the starting point
      if self.containsPt(pt) == False and \
         self.getStartPt().distance(pt) < self.getEndPt().distance(pt):
         return -dummy.length()
      else:
         return dummy.length()


   # ============================================================================
   # getPointFromStart
   # ============================================================================
   def getPointFromStart(self, distance):
      # required
      """the function returns a point (and the direction of the tangent) at the distance <distance>
            (which must be on the object) from the starting point.
      """
      if distance < 0:
         return None, None
      l = self.length()
      if distance > l:
         return None, None

      angle = self.getTanDirectionOnStartPt()
      return qad_utils.getPolarPointByPtAngle(self.getStartPt(), angle, distance), angle


   # ============================================================================
   # getDistanceFromEnd
   # ============================================================================
   def getDistanceFromEnd(self, pt):
      # required
      """the function returns the distance of <pt> (which must be on the object or its extension)
            from the final point.
      """
      return self.length() - self.getDistanceFromStart()


   # ===============================================================================
   # getPointFromEnd
   # ===============================================================================
   def getPointFromEnd(self, distance):
      """the function returns a point (and the direction of the tangent) at the distance <distance>
            (which must be on the object) from the end point.
      """
      d = self.length() - distance
      return self.getPointFromStart(d)


   # ============================================================================
   # asPolyline
   # ============================================================================
   def asPolyline(self, tolerance2ApproxCurve = None, atLeastNSegment = None):
      # required
      """returns a list of points that defines the line"""
      return [self.getStartPt(), self.getEndPt()]


   # ===============================================================================
   # asLineString
   # ===============================================================================
   def asLineString(self, tolerance2ApproxCurve = None, atLeastNSegment = None, forcedStartPt = None):
      """the function returns the line in the form of lineString.
            tolerance2ApproxCurve and atLeastNSegment are used for compatibility only
            When the line is part of a polyline, its starting point must coincide with the final point of the previous part
            therefore the starting point is forced.
      """
      if forcedStartPt is None:
         return QgsLineString(QgsPoint(self.getStartPt()), QgsPoint(self.getEndPt()))
      else:
         return QgsLineString(QgsPoint(forcedStartPt), QgsPoint(self.getEndPt()))


   # ===============================================================================
   # asAbstractGeom
   # ===============================================================================
   def asAbstractGeom(self, wkbType = QgsWkbTypes.LineString, tolerance2ApproxCurve = None, atLeastNSegment = None):
      """the function returns the line in the form of QgsAbstractGeometry."""
      flatType = QgsWkbTypes.flatType(wkbType)

      if flatType == QgsWkbTypes.CompoundCurve:
         lineString = self.asLineString()
         compoundCurve = QgsCompoundCurve()
         compoundCurve.addCurve(lineString)
         return compoundCurve

      elif flatType == QgsWkbTypes.MultiCurve:
         lineString = self.asLineString()
         multiCurve = QgsMultiCurve()
         multiCurve.addGeometry(lineString)
         return multiCurve

      elif flatType == QgsWkbTypes.MultiLineString:
         lineString = self.asLineString()
         multiLineString = QgsMultiLineString()
         multiLineString.addGeometry(lineString)
         return multiLineString

      return self.asLineString()


   # ===============================================================================
   # asGeom
   # ===============================================================================
   def asGeom(self, wkbType = QgsWkbTypes.LineString, tolerance2ApproxCurve = None, atLeastNSegment = None):
      """the function returns the line in the form of QgsGeometry.
            tolerance2ApproxCurve and atLeastNSegment are declared for compatibility only
      """
      return QgsGeometry(self.asAbstractGeom(wkbType, tolerance2ApproxCurve, atLeastNSegment))


   # ============================================================================
   # lengthen_delta
   # ============================================================================
   def lengthen_delta(self, move_startPt, delta):
      # required
      """the function moves the starting point (if move_startPt = True) or ending point (if move_startPt = False)
            of a delta distance
      """
      length = self.length()
      # part length + delta cannot be <= 0
      if length + delta <= 0:
         return False

      angle = self.getTanDirectionOnPt()
      if move_startPt == True:
         self.setStartPt(qad_utils.getPolarPointByPtAngle(self.getStartPt(), angle + math.pi, delta))
      else:
         self.setEndPt(qad_utils.getPolarPointByPtAngle(self.getEndPt(), angle, delta))
      return True


   # ============================================================================
   # lengthen_deltaAngle
   # ============================================================================
   def lengthen_deltaAngle(self, move_startPt, delta):
      # required
      """the function moves the starting point (if move_startPt = True) or ending point (if move_startPt = False)
            of the line by a certain number of degrees delta compared to the previous slope
      """
      angle = self.getTanDirectionOnPt()
      if move_startPt == True:
         self.setStartPt(qad_utils.getPolarPointByPtAngle(self.getEndPt(), angle + math.pi + delta, self.length()))
      else:
         self.setEndPt(qad_utils.getPolarPointByPtAngle(self.getStartPt(), angle + delta, self.length()))
      return True


   # ============================================================================
   # move
   # ============================================================================
   def move(self, offsetX, offsetY):
      # required
      self.pt1 = qad_utils.movePoint(self.pt1, offsetX, offsetY)
      self.pt2 = qad_utils.movePoint(self.pt2, offsetX, offsetY)


   # ============================================================================
   # rotate
   # ============================================================================
   def rotate(self, basePt, angle):
      self.pt1 = qad_utils.rotatePoint(self.pt1, basePt, angle)
      self.pt2 = qad_utils.rotatePoint(self.pt2, basePt, angle)


   # ============================================================================
   # scale
   # ============================================================================
   def scale(self, basePt, scale):
      self.pt1 = qad_utils.scalePoint(self.pt1, basePt, scale)
      self.pt2 = qad_utils.scalePoint(self.pt2, basePt, scale)


   # ============================================================================
   # mirror
   # ============================================================================
   def mirror(self, mirrorPt, mirrorAngle):
      self.pt1 = qad_utils.mirrorPoint(self.pt1, mirrorPt, mirrorAngle)
      self.pt2 = qad_utils.mirrorPoint(self.pt2, mirrorPt, mirrorAngle)


   # ===============================================================================
   # offset
   # ===============================================================================
   def offset(self, offsetDist, offsetSide):
      """the function returns the offset of a line
            according to a distance and an offset side ("right" or "left")
      """
      if offsetSide == "right":
         AngleProjected = qad_utils.getAngleBy2Pts(self.pt1, self.pt2) - (math.pi / 2)
      else:
         AngleProjected = qad_utils.getAngleBy2Pts(self.pt1, self.pt2) + (math.pi / 2)
      # calculate the projected point
      self.pt1 = qad_utils.getPolarPointByPtAngle(self.pt1, AngleProjected, offsetDist)
      self.pt2 = qad_utils.getPolarPointByPtAngle(self.pt2, AngleProjected, offsetDist)
      return True


   # ============================================================================
   # extend
   # ============================================================================
   def extend(self, limitPt):
      """the function extends the line (start or end point of the line) until it meets the <limitPt> point."""
      if self.pt1.distance(limitPt) < self.pt2.distance(limitPt):
         self.pt1.setX(limitPt.x())
         self.pt1.setY(limitPt.y())
      else:
         self.pt2.setX(limitPt.x())
         self.pt2.setY(limitPt.y())


   # ===============================================================================
   # breakOnPts
   # ===============================================================================
   def breakOnPts(self, firstPt, secondPt):
      # required
      """the function breaks the geometry at one point (if <secondPt> = None) or at two points
            how does the trim. Returns one or two geometries resulting from the operation.
            <firstPt> = first dividing point
            <secondPt> = second dividing point
      """
      # the function returns a list with (<minimum squared distance> <nearest point>)
      dummy = self.sqrDist(firstPt)
      myFirstPt = dummy[1]

      mySecondPt = None
      if secondPt is not None:
         dummy = self.sqrDist(secondPt)
         mySecondPt = dummy[1]

      # check whether it is appropriate to reverse the points
      if self.getDistanceFromStart(myFirstPt) > self.getDistanceFromStart(mySecondPt):
         dummy = myFirstPt
         myFirstPt = mySecondPt
         mySecondPt = dummy

      part1 = self.getGeomBetween2Pts(self.getStartPt(), myFirstPt)
      if mySecondPt is None:
         part2 = self.getGeomBetween2Pts(myFirstPt, self.getEndPt())
      else:
         part2 = self.getGeomBetween2Pts(mySecondPt, self.getEndPt())

      return [part1, part2]


   # ===============================================================================
   # getGeomBetween2Pts
   # ===============================================================================
   def getGeomBetween2Pts(self, startPt, endPt):
      """Returns a sub-geometry that starts from the startPt point and ends at the endPt point following the geometry path."""
      if qad_utils.ptNear(startPt, endPt): return None
      if self.containsPt(startPt) == False: return None
      if self.containsPt(endPt) == False: return None

      return QadLine().set(startPt, endPt)


# ===============================================================================
# getBoundingPtsOnOnInfinityLine
# ===============================================================================
def getBoundingPtsOnOnInfinityLine(pts):
   """Given a list of unordered points <pts> on an infinite line,
      the function returns the two extreme points to the point bundle (the two points furthest from each other).
   """
   tot = len(pts)
   if tot < 3:
      return pts[:] # I copy the list

   result = []
   # elaboro i tratti intermedi
   # calculate the direction from the first point to the second point
   angle = qad_utils.getAngleBy2Pts(pts[0], pts[1])
   # loop over all points considering only those that have the same direction with the previous point (boundingPt1)
   i = 2
   boundingPt1 = pts[1]
   while i < tot:
      pt2 = pts[i]
      if qad_utils.TanDirectionNear(angle, qad_utils.getAngleBy2Pts(boundingPt1, pt2)):
         boundingPt1 = pt2
      i = i + 1

   # calculate the direction from the second point to the first point
   angle = qad_utils.getAngleBy2Pts(pts[1], pts[0])
   # loop over all points considering only those that have the same direction with the previous point (boundingPt2)
   i = 2
   boundingPt2 = pts[0]
   while i < tot:
      pt2 = pts[i]
      if qad_utils.TanDirectionNear(angle, qad_utils.getAngleBy2Pts(boundingPt2, pt2)):
         boundingPt2 = pt2
      i = i + 1

   return [QgsPointXY(boundingPt1), QgsPointXY(boundingPt2)]
