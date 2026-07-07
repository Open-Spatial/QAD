# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 class for managing elliptical arcs

                              -------------------
        begin                : 2019-02-18
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
from .qad_ellipse import QadEllipse, MathTools
from .qad_variables import QadVariables
from .qad_msg import QadMsg


# ===============================================================================
# QadEllipseArc arc of ellipse class
# ===============================================================================
class QadEllipseArc(QadEllipse):

   def __init__(self, ellipseArc = None):
      if ellipseArc is not None:
         self.set(ellipseArc.center, ellipseArc.majorAxisFinalPt, ellipseArc.axisRatio, ellipseArc.startAngle, ellipseArc.endAngle, ellipseArc.reversed)
      else:
         self.center = None
         self.majorAxisFinalPt = None # final point of the major axis (right)
         self.axisRatio = 0 # ratio between minor axis and major axis
         self.startAngle = None # initial angle with respect to the axis that goes from the center to majorAxisFinalPt
         self.endAngle = None # final angle with respect to the axis that goes from the center to majorAxisFinalPt
         # if reversed is True the direction of the arc of ellipse is from endAngle to startAngle
         self.reversed = None

   def whatIs(self):
      # required
      return "ELLIPSE_ARC"


   # ============================================================================
   # isClosed
   # ============================================================================
   def isClosed(self):
      return False


   def set(self, center, majorAxisFinalPt = None, axisRatio = None, startAngle = None, endAngle = None, reversed=False):
      if isinstance(center, QadEllipseArc):
         ellipseArc = center
         return self.set(ellipseArc.center, ellipseArc.majorAxisFinalPt, ellipseArc.axisRatio, ellipseArc.startAngle, ellipseArc.endAngle, ellipseArc.reversed)

      if center == majorAxisFinalPt: return None
      self.center = QgsPointXY(center)
      self.majorAxisFinalPt = QgsPointXY(majorAxisFinalPt)
      self.axisRatio = axisRatio
      self.reversed = reversed
      if self.setArc(startAngle, endAngle) == False: return None
      return self


   def setArc(self, startAngle, endAngle):
      # controlled set of angles to initialize the ellipse arc
      _startAngle = qad_utils.normalizeAngle(startAngle)
      _endAngle = qad_utils.normalizeAngle(endAngle)
      if _startAngle == _endAngle: return False # complete ellipse
      self.startAngle = _startAngle
      self.endAngle = _endAngle


   def __eq__(self, ellipseArc):
      # required
      """self == other"""
      if ellipseArc.whatIs() != "ELLIPSE_ARC": return False
      if self.center != ellipseArc.center or self.majorAxisFinalPt != ellipseArc.majorAxisFinalPt or self.axisRatio != ellipseArc.axisRatio or \
         self.startAngle != ellipseArc.startAngle or self.endAngle != ellipseArc.endAngle:
         return False
      return True


   def __ne__(self, ellipseArc):
      """self != other"""
      return not self.__eq__(ellipseArc)


   def equals(self, ellipseArc):
      # geometrically equal (the direction does NOT count)
      return self.__eq__(ellipseArc)


   def copy(self):
      # required
      return QadEllipseArc(self)


   # ===============================================================================
   # length
   # ===============================================================================
   def length(self):
      # required
      # temporarily approximate by segmenting the arc...
      pts = self.asPolyline()
      arcLen = 0
      i = 0
      while i < len(pts) - 1:
         arcLen = arcLen + qad_utils.getDistance(pts[i], pts[i + 1])
         i = i + 1
      return arcLen
      # TODO
      a = qad_utils.getDistance(self.center, self.majorAxisFinalPt) # semi-major axis
      b = a * self.axisRatio # semi-minor axis
      return 0


   # ============================================================================
   # reverse
   # ============================================================================
   def reverse(self):
      # I invert the direction of the ellipse arc (initial-final point)
      self.reversed = not self.reversed
      return self

   # ============================================================================
   # inverseAngles
   # ============================================================================
   def inverseAngles(self):
      # I invert the initial-final angle
      dummy = self.endAngle
      self.endAngle = self.startAngle
      self.startAngle = dummy
      # to keep the same starting point I reverse the direction of the starting-end points
      self.reverse()


   # ============================================================================
   # getStartPt, setStartPt
   # ============================================================================
   def getStartPt(self, usingReversedFlag = True):
      # required
      # usingReversedFlag is used to know the starting point in case the arc has a direction (in the polyline)
      # returns the starting point
      if usingReversedFlag:
         param = self.getParamFromAngle(self.endAngle if self.reversed else self.startAngle)
      else:
         param = self.getParamFromAngle(self.startAngle)
      return self.getPointAt(param)

   def setStartPt(self, pt):
      # required
      return self.setStartAngleByPt(pt)


   def setStartAngleByPt(self, pt):
      # to be used to modify an already defined ellipse arc
      angle = qad_utils.getAngleBy3Pts(self.majorAxisFinalPt, self.center, pt, False)
      if self.reversed:
         if angle == self.startAngle: return False
         self.endAngle = angle
      else:
         if angle == self.endAngle: return False
         self.startAngle = angle
      return True


   # ============================================================================
   # getEndPt, setEndPt
   # ============================================================================
   def getEndPt(self, usingReversedFlag = True):
      # required
      # usingReversedFlag is used to know the starting point in case the arc has a direction (in the polyline)
      # returns the final point
      if usingReversedFlag:
         param = self.getParamFromAngle(self.startAngle if self.reversed else self.endAngle)
      else:
         param = self.getParamFromAngle(self.endAngle)
      return self.getPointAt(param)

   def setEndPt(self, pt):
      # required
      return self.setEndAngleByPt(pt)


   def setEndAngleByPt(self, pt):
      # to be used to modify an already defined ellipse arc
      angle = qad_utils.getAngleBy3Pts(self.majorAxisFinalPt, self.center, pt, False)
      if self.reversed:
         if angle == self.endAngle: return False
         self.startAngle = angle
      else:
         if angle == self.startAngle: return False
         self.endAngle = angle

      return True


   # ============================================================================
   # isPtOnEllipseArcOnlyByAngle
   # ============================================================================
   def isPtOnEllipseArcOnlyByAngle(self, point):
      # the function evaluates whether a point is on the ellipse arc by considering only the initial/final angles
      angle = qad_utils.getAngleBy3Pts(self.majorAxisFinalPt, self.center, point, False)
      return qad_utils.isAngleBetweenAngles(self.startAngle, self.endAngle, angle)


   # ============================================================================
   # containsPt
   # ============================================================================
   def containsPt(self, point):
      # required
      """the function returns true if the point is on the arc of the ellipse (extremes included).
            point is of type QgsPointXY.
      """
      if self.whereIsPt(point) == 0: # -1 internal, 0 on the ellipse, 1 external:
         return self.isPtOnEllipseArcOnlyByAngle(point)
      return False


   # ============================================================================
   # getDistanceFromStart
   # ============================================================================
   def getDistanceFromStart(self, pt):
      # required
      """the function returns the distance of <pt> (which must be on the object or its extension)
            from the starting point.
      """
      if qad_utils.ptNear(pt, self.getStartPt()): return 0.0
      dummy = QadEllipseArc(self)
      dummy.setEndPt(pt)
      return dummy.length()


   # ============================================================================
   # getPointFromStart
   # ============================================================================
   def getPointFromStart(self, distance):
      # required
      """the function returns a point (and the direction of the tangent) at the distance <distance>
            (which must be on the object) from the starting point.
      """
      # temporarily segment the arc of the ellipse...
      from .qad_line import QadLine
      if distance < 0:
         return None, None
      pts = self.asPolyline()
      d = distance
      i = 0
      while i < len(pts) - 1:
         linearObject = QadLine().set(pts[i], pts[i + 1])
         l = linearObject.length()
         if d > l:
            d = d - l
            i = i + 1
         else:
            return linearObject.getPointFromStart(d)
      return None, None

      # TODO

      if distance < 0:
         return None, None
      l = self.length()
      if distance > l:
         return None, None


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
   # lengthen_delta
   # ============================================================================
   def lengthen_delta(self, move_startPt, delta):
      # required
      """the function moves the starting point (if move_startPt = True) or ending point (if move_startPt = False)
            of a delta distance
      """
      length = self.length()
      ellipse = QadEllipse().set(self.center, self.majorAxisFinalPt, self.axisRatio)
      # arc length of ellipse + delta cannot be >= the length of the ellipse
      if length + delta >= ellipse.length() or length + delta <= 0:
         return False

      dummy = self.copy()

      if move_startPt == True:
         dummy.reverse()
         if dummy.lengthen_delta(False, delta) == False: return False
         self.setStartPt(dummy.getEndPt())
      else:
         if self.reversed:
            dummy.setArc(qad_utils.normalizeAngle(self.endAngle+0.001), self.endAngle)
         else:
            dummy.setArc(self.startAngle, qad_utils.normalizeAngle(self.startAngle-0.001))

         distFromStart = length + delta
         pt, angle = dummy.getPointFromStart(distFromStart)
         if pt is not None:
            self.setEndPt(pt)
      return True

      # TODO
      return False


   # ===============================================================================
   # getBoundingBox
   # ===============================================================================
   def getBoundingBox(self):
      """the function returns the rectangle that encloses the ellipse arc."""
      ellipseBoundingBox = QadEllipse.getBoundingBox(self)
      # TODO
      return ellipseBoundingBox


   # ============================================================================
   # getQuadrantPoints
   # ============================================================================
   def getQuadrantPoints(self):
      Pts = QadEllipse.getQuadrantPoints(self)
      # I cancel the points outside the ellipse arc but return a 4 by list
      # know what each quadrant point corresponds to
      if self.isPtOnEllipseArcOnlyByAngle(Pts[3]) == False: Pts[3] = None
      if self.isPtOnEllipseArcOnlyByAngle(Pts[2]) == False: Pts[2] = None
      if self.isPtOnEllipseArcOnlyByAngle(Pts[1]) == False: Pts[1] = None
      if self.isPtOnEllipseArcOnlyByAngle(Pts[0]) == False: Pts[0] = None

      return Pts


   # ===============================================================================
   # getMiddleParam
   # ===============================================================================
   def getMiddleParam(self):
      return self.getParamFromAngle(qad_utils.getMiddleAngle(self.startAngle, self.endAngle))


   # ===============================================================================
   # getMiddlePoint
   # ===============================================================================
   def getMiddlePt(self):
      return self.getPointAt(self.getMiddleParam())


   # ============================================================================
   # getTanDirectionOnStartPt, getTanDirectionOnEndPt, getTanDirectionOnMiddlePt
   # ============================================================================
   # ============================================================================
   # getTanDirectionOnStartPt, getTanDirectionOnEndPt, getTanDirectionOnMiddlePt
   # ============================================================================
   def getTanDirectionOnStartPt(self):
      # required
      """the function returns the direction of the tangent to the starting point of the object."""
      result = self.getTanDirectionOnPt(self.getStartPt())
      if self.reversed:
         result = result + math.pi
      return result

   def getTanDirectionOnEndPt(self):
      # required
      """the function returns the direction of the tangent to the final point of the object."""
      result = self.getTanDirectionOnPt(self.getEndPt())
      if self.reversed:
         result = result + math.pi
      return result

   def getTanDirectionOnMiddlePt(self):
      # required
      """the function returns the direction of the tangent to the midpoint of the object."""
      result = self.getTanDirectionOnPt(self.getMiddlePt())
      if self.reversed:
         result = result + math.pi
      return result


   # ===============================================================================
   # leftOf
   # ===============================================================================
   def leftOf(self, pt):
      # required
      """the function returns a number < 0 if the point pt is to the left of the ellipse arc ptStart -> ptEnd"""
      whereIs = self.whereIsPt(pt) # returns -1 if the point is internal, 0 if it is on the ellipse, 1 if it is external

      if self.whereIsPt(pt) == 1: # returns -1 if the point is internal, 0 if it is on the ellipse, 1 if it is external
         # outside the arc
         if self.reversed:  # the arc is in the reverse direction
            return -1  # on the left
         else:
            return 1  # on the right
      else:
         # inside the arc
         if self.reversed:  # the arc is in the reverse direction
            return 1  # on the right
         else:
            return -1  # on the left


   # ============================================================================
   # asPolyline
   # ============================================================================
   def asPolyline(self, tolerance2ApproxCurve = None, atLeastNSegment = None):
      """returns a list of points that defines the tangent"""
      if tolerance2ApproxCurve is None:
         tolerance = QadVariables.get(QadMsg.translate("Environment variables", "TOLERANCE2APPROXCURVE"))
      else:
         tolerance = tolerance2ApproxCurve

      if atLeastNSegment is None:
         _atLeastNSegment = QadVariables.get(QadMsg.translate("Environment variables", "ELLIPSEARCMINSEGMENTQTY"), 12)
      else:
         _atLeastNSegment = atLeastNSegment

      param = self.getParamFromAngle(self.startAngle)
      endParam = self.getParamFromAngle(self.endAngle)
      if param > endParam:
         param = param - (2 * math.pi)
      pt = self.getPointAt(param)

      angle = qad_utils.getAngleBy3Pts(self.getStartPt(False), self.center, self.getEndPt(False), False)
      if angle == 0: return None
      angleStep = angle / _atLeastNSegment

      points = []
      points.append(pt)
      while True:
         param, pt = self.getNextParamPt(param, pt, angleStep, tolerance)
         if param > endParam: break
         points.append(pt)

      lastPt = self.getPointAt(endParam)

      if points[-1] != lastPt: # if the last point does not coincide with the terminal point of the ellipse arc
         if qad_utils.ptNear(points[-1], lastPt): # if the last point is close enough to the terminal point of the ellipse arc
            points[-1].set(lastPt.x(), lastPt.y()) # I move the last point and make it coincide with the terminal point of the ellipse arc
         else:
            points.append(QgsPointXY(lastPt)) # add the last point coinciding with the terminal point of the ellipse arc

      if self.reversed: points.reverse()
      return points


   # ===============================================================================
   # asLineString
   # ===============================================================================
   def asLineString(self, tolerance2ApproxCurve = None, atLeastNSegment = None, forcedStartPt = None):
      """the function returns the ellipse in the form of a lineString.
            When the ellipse arc is part of a polyline, its starting point must coincide with the final point of the previous part
            therefore the starting point is forced.
      """
      pts = self.asPolyline(tolerance2ApproxCurve, atLeastNSegment)
      if pts is None or len(pts) == 0:
          return None
      if forcedStartPt is not None:
         pts[0] = QgsPointXY(forcedStartPt)
      return QgsLineString(pts)


   # ===============================================================================
   # asAbstractGeom
   # ===============================================================================
   def asAbstractGeom(self, wkbType = QgsWkbTypes.LineString, tolerance2ApproxCurve = None, atLeastNSegment = None):
      """the function returns the ellipse in the form of QgsAbstractGeometry."""
      flatType = QgsWkbTypes.flatType(wkbType)

      if flatType == QgsWkbTypes.CompoundCurve:
         linestring = self.asLineString(tolerance2ApproxCurve, atLeastNSegment)
         compoundCurve = QgsCompoundCurve()
         compoundCurve.addCurve(linestring)
         return compoundCurve

      elif flatType == QgsWkbTypes.MultiCurve:
         linestring = self.asLineString(tolerance2ApproxCurve, atLeastNSegment)
         multiCurve = QgsMultiCurve()
         multiCurve.addGeometry(linestring)
         return multiCurve

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
      """the function returns the ellipse in the form of QgsGeometry."""
      return QgsGeometry(self.asAbstractGeom(wkbType, tolerance2ApproxCurve, atLeastNSegment));


   # ============================================================================
   # fromPolyline
   # ============================================================================
   def fromPolyline(self, points, startVertex, atLeastNSegment = None):
      """Sets the characteristics of the ellipse arc encountered in the point list
            starting from the startVertex position (0-indexed).
            Returns the position in the list of the end point if an ellipse arc was found
            otherwise None
            N.B. the points must NOT be in geographic coordinates
      """
      # if the initial and final points coincide it is not an arc of an ellipse
      if points[startVertex] == points[-1]: return None

      if atLeastNSegment is None:
         _atLeastNSegment = QadVariables.get(QadMsg.translate("Environment variables", "ELLIPSEARCMINSEGMENTQTY"), 12)
      else:
         _atLeastNSegment = atLeastNSegment

      totPoints = len(points) - startVertex
      nSegment = totPoints - 1
      # for it to be an arc you need at least _atLeastNSegment segments and at least 5 points
      if nSegment < _atLeastNSegment or totPoints < 5:
         return None

      everyNPts = int(max(_atLeastNSegment, 5) / 5)

      # I move the 5 rating points close to 0.0 to improve the accuracy of the calculations
      dx = points[startVertex].x()
      dy = points[startVertex].y()
      first5Points = []
      first5Points.append(qad_utils.movePoint(points[startVertex], -dx, -dy))
      first5Points.append(qad_utils.movePoint(points[startVertex + everyNPts], -dx, -dy))
      first5Points.append(qad_utils.movePoint(points[startVertex + everyNPts * 2], -dx, -dy))
      first5Points.append(qad_utils.movePoint(points[startVertex + everyNPts * 3], -dx, -dy))
      first5Points.append(qad_utils.movePoint(points[startVertex + everyNPts * 4], -dx, -dy))

      # this translation is for avoiding floating point precision issues
      baryC = MathTools.barycenter(first5Points)

      pointListBC = []
      for pt in first5Points :
         pointListBC.append((pt[0] - baryC[0], pt[1] - baryC[1]))
      # find the center and the axes of by solving the conic equation :
      # ax2 + bxy + cy2 + dx + ey + f = 0
      conic = MathTools.conicEquation(pointListBC)
      [a, b, c, d, e, f] = conic
      # conditions for the existence of an ellipse
      if MathTools.bareissDeterminant([[a, b/2, d/2], [b/2, c, e/2], [d/2, e/2, f]]) == 0 or a*c - b*b/4 <= 0:
         # Could not find the ellipse passing by these five points.
         return None
      cX = (b*e - 2*c*d) / (4*a*c - b*b)
      cY = (d*b - 2*a*e) / (4*a*c - b*b)
      center = (cX, cY)
      res = MathTools.ellipseAxes(conic)
      if res is None: return None
      axisDir1 = res[0]
      axisDir2 = res[1]
      axisLen1 = MathTools.ellipseAxisLen(conic, center, axisDir1)
      if axisLen1 is None: return None
      axisLen2 = MathTools.ellipseAxisLen(conic, center, axisDir2)
      if axisLen2 is None: return None

      if axisLen1 > axisLen2:
         majorDir = axisDir1
         majorLen = axisLen1
         minorLen = axisLen2
      else:
         majorDir = axisDir2
         majorLen = axisLen2
         minorLen = axisLen1
      rotAngle = math.atan2(majorDir[1], majorDir[0])

      center = QgsPointXY(center[0], center[1])
      majorAxisFinalPt = qad_utils.rotatePoint(QgsPointXY(majorLen + center[0], center[1]), center, rotAngle)
      majorAxisFinalPt.setX(majorAxisFinalPt.x() + baryC[0])
      majorAxisFinalPt.setY(majorAxisFinalPt.y() + baryC[1])

      axisRatio = minorLen / majorLen;

      center = QgsPointXY(center[0] + baryC[0], center[1] + baryC[1])

      testEllipse = QadEllipse()
      if testEllipse.set(center, majorAxisFinalPt, axisRatio) is None:
         return None
      foci = testEllipse.getFocus()
      if len(foci) == 0: return None

      myPoints = []
      # I move the points closer to 0.0 to improve the accuracy of the calculations
      i = startVertex
      while i < len(points):
         myPoints.append(qad_utils.movePoint(points[i], -dx, -dy))
         i = i + 1

      # if the midpoint of the line (points[1]) is to the left of
      # segment that joins the initial points (points[0]) and final points (points[2]) then the direction is clockwise
      startClockWise = False if qad_utils.leftOfLine(myPoints[2], myPoints[0], myPoints[1]) < 0 else True
      angle = 0

      # I use the distance TOLERANCE2COINCIDENT / 2 because in a polyline if there are 2 consecutive ellipse arcs
      # you want to be sure that the end point of the first arc of the ellipse is far from the starting point of the
      # second arc of ellipse no more than TOLERANCE2COINCIDENT for 2 points to be considered coincident
      myTolerance = QadVariables.get(QadMsg.translate("Environment variables", "TOLERANCE2COINCIDENT")) / 2

      # check that the points are on the ellipse and I stop at the first point outside it
      i = 0
      while i < totPoints:
         # if TOLERANCE2COINCIDENT = 0.001 an arc of 1000 m is recognized
         # if the calculated point is not close enough to the real point
         # otherwise I find problems with intersections with objects
         relativeAngle = qad_utils.getAngleBy2Pts(center, myPoints[i]) - testEllipse.getRotation()
         if qad_utils.ptNear(testEllipse.getPointAt(testEllipse.getParamFromAngle(relativeAngle)), \
                             myPoints[i], myTolerance) == False:
            break

         # calculate the direction of the arc and the angle
         if i < 2:
            clockWise = False if qad_utils.leftOfLine(myPoints[i], myPoints[i + 1], myPoints[i + 2]) < 0 else True
         else:
            clockWise = False if qad_utils.leftOfLine(myPoints[i], myPoints[i - 2], myPoints[i - 1]) < 0 else True
         # the direction must be the same as the original one
         if startClockWise != clockWise:
            break

         if i > 0: # I skip the first point
            angle = angle + qad_utils.getAngleBy3Pts(myPoints[i-1], center, myPoints[i], startClockWise)
            # the inscribed angle cannot be >= 360
            if angle >= 2 * math.pi:
               break
         i = i + 1

      # if not enough subsequent segments were found
      i = i - 1 # last valid point of the arc
      if i < _atLeastNSegment: return None

      self.center = center
      self.majorAxisFinalPt = majorAxisFinalPt
      self.axisRatio = axisRatio

      if startClockWise: # if it is clockwise
         self.endAngle = qad_utils.getAngleBy3Pts(self.majorAxisFinalPt, self.center, myPoints[0], False)
         self.startAngle = qad_utils.getAngleBy3Pts(self.majorAxisFinalPt, self.center, myPoints[i], False)
         self.reversed = True
      else:
         self.startAngle = qad_utils.getAngleBy3Pts(self.majorAxisFinalPt, self.center, myPoints[0], False)
         self.endAngle = qad_utils.getAngleBy3Pts(self.majorAxisFinalPt, self.center, myPoints[i], False)
         self.reversed = False

      # I translate the geometry to return it to its original position
      self.move(dx, dy)

      return i + startVertex


   # ===============================================================================
   # breakOnPts
   # ===============================================================================
   def breakOnPts(selfs, firstPt, secondPt):
      # required
      """the function breaks the geometry at one point (if <secondPt> = None) or at two points
            how does the trim. Returns one or two geometries resulting from the operation.
            <firstPt> = first dividing point
            <secondPt> = second dividing point
      """
      angle = qad_utils.getAngleBy3Pts(self.majorAxisFinalPt, self.center, firstPt, False)
      param = self.getParamFromAngle(angle)
      myFirstPt = self.getPointAt(param)

      mySecondPt = None
      if secondPt is not None:
         angle = qad_utils.getAngleBy3Pts(self.majorAxisFinalPt, self.center, secondPt, False)
         param = self.getParamFromAngle(angle)
         mySecondPt = self.getPointAt(param)

      part1 = self.getGeomBetween2Pts(self.getStartPt(), myFirstPt)
      if mySecondPt is None:
         part2 = self.getGeomBetween2Pts(myFirstPt, self.getEndPt())
      else:
         part2 = self.getGeomBetween2Pts(mySecondPt, self.getEndPt())

      return [part1, part2]


   # ============================================================================
   # mirror
   # ============================================================================
   def mirror(self, mirrorPt, mirrorAngle):
      QadEllipse.mirror(self, mirrorPt, mirrorAngle)
      self.startAngle = (2 * math.pi) - self.startAngle
      self.endAngle = (2 * math.pi) - self.endAngle


   # ===============================================================================
   # offset
   # ===============================================================================
   def offset(self, offsetDist, offsetSide, tolerance2ApproxCurve = None):
      """the function returns the arc of the ellipse by offsetting it.
            since the offset of an arc of an ellipse is not an arc of an ellipse, it returns a list of points or None
            according to a distance and an offset side ("right" or "left" or "internal" or "external")
      """
      side = ""
      if offsetSide == "right":
         if self.reversed: # direzione oraria
            side = "internal" # offset towards the inside of the ellipse
         else:
            side = "external" # offset outward of the ellipse
      elif offsetSide == "left":
         if self.reversed: # direzione oraria
            side = "external" # offset outward of the ellipse
         else:
            side = "internal" # offset towards the inside of the ellipse
      else:
         side = offsetSide

      if side == "internal": # offset towards the inside of the ellipse
         dist = -offsetDist
         a = qad_utils.getDistance(self.center, self.majorAxisFinalPt) # semi-major axis
         b = a * self.axisRatio # semi-minor axis
         if a > b:
            if b <= offsetDist: return None
         else:
            if a <= offsetDist: return None
      elif side == "external": # offset outward of the ellipse
         dist = offsetDist

      if tolerance2ApproxCurve is None:
         tolerance = QadVariables.get(QadMsg.translate("Environment variables", "TOLERANCE2APPROXCURVE"))
      else:
         tolerance = tolerance2ApproxCurve

      _atLeastNSegment = QadVariables.get(QadMsg.translate("Environment variables", "ELLIPSEARCMINSEGMENTQTY"), 12)

      param = self.getParamFromAngle(self.startAngle)
      endParam = self.getParamFromAngle(self.endAngle)
      if param > endParam:
         param = param - (2 * math.pi)
      pt = self.getPointAt(param)
      ptOffset = qad_utils.getPolarPointByPtAngle(pt, self.getNormalAngleToAPointOnEllipse(pt), dist)

      angle = qad_utils.getAngleBy3Pts(self.getStartPt(False), self.center, self.getEndPt(False), False)
      angleStep = angle / _atLeastNSegment

      points = []
      points.append(ptOffset)
      while True:
         param, ptOffset = self.getNextParamPtForOffset(param, ptOffset, angleStep, tolerance, dist)
         if param > endParam: break
         points.append(ptOffset)

      lastPt = self.getPointAt(endParam)
      lastPtOffset = qad_utils.getPolarPointByPtAngle(lastPt, self.getNormalAngleToAPointOnEllipse(lastPt), dist)
      if qad_utils.ptNear(points[-1], lastPtOffset) == False: points.append(lastPtOffset) # last item in the list

      if self.reversed: points.reverse()
      return points


   # ============================================================================
   # fromFoci
   # ============================================================================
   def fromFoci(self, f1, f2, ptOnEllipse, startAngle, endAngle):
      """set the characteristics of the ellipse through:
            the two fires
            a point on the ellipse
                   /-ptOnEllipse- / |   f1 f2 |
                  \ /
                   \-------------/
      """
      if QadEllipse.fromFoci(self, f1, f2, ptOnEllipse) == False: return False
      self.setArc(startAngle, endAngle)
      return True


   # ============================================================================
   # fromExtent
   # ============================================================================
   def fromExtent(self, pt1, pt2, rot, startAngle, endAngle):
      """set the characteristics of the ellipse through:
            the two extension points (opposite corners) of the rectangle that encloses the ellipse
            rotation of the extension rectangle
                   /-------------\ pt2
                  / |               |
                  \ /
              pt1 \-------------/
      """
      if QadEllipse.fromExtent(self, pt1, pt2, rot) == False: return False
      self.setArc(startAngle, endAngle)
      return True


   # ============================================================================
   # fromCenterAxis1FinalPtAxis2FinalPt
   # ============================================================================
   def fromCenterAxis1FinalPtAxis2FinalPt(self, ptCenter, axis1FinalPt, axis2FinalPt, startAngle, endAngle):
      """set the characteristics of the ellipse through:
            the central point
            the end point of the axis
            the end point of the other axis
                   /--axis2FinalPt-- / |     ptCenter axis1FinalPt
                  \ /
                   \----------------/
      """
      if QadEllipse.fromCenterAxis1FinalPtAxis2FinalPt(self, ptCenter, axis1FinalPt, axis2FinalPt) == False: return False
      self.setArc(startAngle, endAngle)
      return True


   # ============================================================================
   # fromCenterAxis1FinalPtDistAxis2
   # ============================================================================
   def fromCenterAxis1FinalPtDistAxis2(self, ptCenter, axis1FinalPt, distAxis2, startAngle, endAngle):
      """set the characteristics of the ellipse through:
            the central point
            the end point of the axis
            distance from the center to the end point of the other axis
                   /----------|-------- / distAxis2 |     ptCenter axis1FinalPt
                  \ /
                   \----------------/
      """
      if QadEllipse.fromCenterAxis1FinalPtDistAxis2(self, ptCenter, axis1FinalPt, distAxis2) == False: return False
      self.setArc(startAngle, endAngle)
      return True


   # ============================================================================
   # fromCenterAxis1FinalPtAxis2FinalPt
   # ============================================================================
   def fromCenterAxis1FinalPtAxis2FinalPt(self, axis1Finalpt1, axis1Finalpt2, axis2FinalPt, startAngle, endAngle):
      """set the characteristics of the ellipse through:
            the end points of the axis
            the end point of the other axis
                   /--axis2FinalPt-- / axis1Finalpt2 axis1Finalpt1
                  \ /
                   \----------------/
      """
      if QadEllipse.fromCenterAxis1FinalPtAxis2FinalPt(self, axis1Finalpt1, axis1Finalpt2, axis2FinalPt) == False: return False
      self.setArc(startAngle, endAngle)
      return True


   # ============================================================================
   # fromAxis1FinalPtsAxis2Len
   # ============================================================================
   def fromAxis1FinalPtsAxis2Len(self, axis1FinalPt1, axis1FinalPt2, distAxis2, startAngle, endAngle):
      """set the characteristics of the ellipse through:
            the end points of the axis
            distance from the center to the end point of the other axis
                   /------|------- / distAxis2 axis1pt2 |    axis1pt1
                  \ /
                   \--------------/
      """
      if QadEllipse.fromAxis1FinalPtsAxis2Len(self, axis1FinalPt1, axis1FinalPt2, distAxis2) == False: return False
      self.setArc(startAngle, endAngle)
      return True


   # ============================================================================
   # fromAxis1FinalPtsArea
   # ============================================================================
   def fromAxis1FinalPtsArea(self, axis1FinalPt1, axis1FinalPt2, area, startAngle, endAngle):
      """set the characteristics of the ellipse through:
            the end points of the axis
            area of the ellipse
                   /-------------- / axis1pt2 axis1pt1
                  \ /
                   \--------------/
      """
      if QadEllipse.fromAxis1FinalPtsArea(self, axis1FinalPt1, axis1FinalPt2, area) == False: return False
      self.setArc(startAngle, endAngle)
      return True


   # ===============================================================================
   # getGeomBetween2Pts
   # ===============================================================================
   def getGeomBetween2Pts(self, startPt, endPt):
      """Returns a sub-geometry that starts from the startPt point and ends at the endPt point following the geometry path."""
      if qad_utils.ptNear(startPt, endPt): return None
      if self.containsPt(startPt) == False: return None
      if self.containsPt(endPt) == False: return None

      result = self.copy()
      d1 = self.getDistanceFromStart(startPt)
      if d1 < self.getDistanceFromStart(endPt):
         result.setStartPt(startPt)
         result.setEndPt(endPt)
      else:
         result.setStartPt(endPt)
         result.setEndPt(startPt)
         result.reversed = True

      return result
