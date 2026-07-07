# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 class for managing arcs

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


from . import qad_utils
from .qad_circle import QadCircle
from .qad_variables import QadVariables
from .qad_msg import QadMsg


# ===============================================================================
# QadArc arc class
# ===============================================================================
class QadArc(QadCircle):

   def __init__(self, arc=None):
      if arc is not None:
         if arc.radius <= 0: return None
         self.set(arc.center, arc.radius, arc.startAngle, arc.endAngle, arc.reversed)
      else:
         self.center = None
         self.radius = None
         self.startAngle = None # like the arc for the circle
         self.endAngle = None
         # if reversed is True the direction of the arc is from endAngle to startAngle
         self.reversed = False


   def whatIs(self):
      # required
      return "ARC"


   # ============================================================================
   # isClosed
   # ============================================================================
   def isClosed(self):
      return False


   def set(self, center, radius=None, startAngle=None, endAngle=None, reversed=False):
      if isinstance(center, QadArc):
         arc = center
         return self.set(arc.center, arc.radius, arc.startAngle, arc.endAngle, arc.reversed)

      if radius <= 0: return None
      self.center = QgsPointXY(center)
      self.radius = radius
      self.reversed = reversed
      if self.setArc(startAngle, endAngle) == False: return None
      return self


   def setArc(self, startAngle, endAngle):
      # controlled angle set to initialize the arc
      _startAngle = qad_utils.normalizeAngle(startAngle)
      _endAngle = qad_utils.normalizeAngle(endAngle)
      if _startAngle == _endAngle: return False # full circle
      self.startAngle = _startAngle
      self.endAngle = _endAngle


   def __eq__(self, arc):
      # required
      """self == other"""
      if arc.whatIs() != "ARC": return False
      if self.center != arc.center or self.radius != arc.radius or \
         self.startAngle != arc.startAngle or self.endAngle != arc.endAngle or self.reversed != arc.reversed:
         return False
      else:
         return True


   def __ne__(self, arc):
      """self != other"""
      return not self.__eq__(arc)


   def equals(self, arc):
      # geometrically equal (the direction does NOT count)
      return self.__eq__(arc)


   def copy(self):
      # required
      return QadArc(self)


   def totalAngle(self):
      if self.startAngle < self.endAngle:
         return self.endAngle - self.startAngle
      else:
         return (2 * math.pi - self.startAngle) + self.endAngle


   # ===============================================================================
   # length
   # ===============================================================================
   def length(self):
      # required
      return self.radius * self.totalAngle()


   # ============================================================================
   # reverse
   # ============================================================================
   def reverse(self):
      # I reverse the direction of the arc (start-end point)
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
      if usingReversedFlag:
         return qad_utils.getPolarPointByPtAngle(self.center,
                                                 self.endAngle if self.reversed else self.startAngle,
                                                 self.radius)
      else:
         return qad_utils.getPolarPointByPtAngle(self.center,
                                                 self.startAngle,
                                                 self.radius)

   def setStartPt(self, pt):
      # required
      if self.reversed:
         return self.setEndAngleByPt(pt)
      else:
         return self.setStartAngleByPt(pt)


   def setStartAngleByPt(self, pt):
      # to be used to modify an already defined arc
      angle = qad_utils.getAngleBy2Pts(self.center, pt)
      if angle == self.endAngle: return False
      self.startAngle = angle
      return True


   # ============================================================================
   # getEndPt, setEndPt
   # ============================================================================
   def getEndPt(self, usingReversedFlag = True):
      # required
      # usingReversedFlag is used to know the starting point in case the arc has a direction (in the polyline)
      if usingReversedFlag:
         return qad_utils.getPolarPointByPtAngle(self.center,
                                                 self.startAngle if self.reversed else self.endAngle,
                                                 self.radius)
      else:
         return qad_utils.getPolarPointByPtAngle(self.center,
                                                 self.endAngle,
                                                 self.radius)

   def setEndPt(self, pt):
      # required
      if self.reversed:
         return self.setStartAngleByPt(pt)
      else:
         return self.setEndAngleByPt(pt)


   def setEndAngleByPt(self, pt):
      # to be used to modify an already defined arc
      angle = qad_utils.getAngleBy2Pts(self.center, pt)
      if angle == self.startAngle:
         return False
      self.endAngle = angle
      return True


   # ============================================================================
   # isPtOnArcOnlyByAngle
   # ============================================================================
   def isPtOnArcOnlyByAngle(self, point):
      # the function evaluates whether a point is on the arc by considering only the start/end angles
      return self.isAngleBetweenAngles(qad_utils.getAngleBy2Pts(self.center, point))


   # ============================================================================
   # isAngleBetweenAngles
   # ============================================================================
   def isAngleBetweenAngles(self, angle):
      # the function evaluates whether an angle is between the start/end angles
      return qad_utils.isAngleBetweenAngles(self.startAngle, self.endAngle, angle)


   # ===============================================================================
   # getBoundingBox
   # ===============================================================================
   def getBoundingBox(self):
      """the function returns the rectangle that encloses the arc."""
      circleBoundingBox = QadCircle.getBoundingBox(self)

      p1 = qad_utils.getPolarPointByPtAngle(self.center, self.startAngle, self.radius)
      p2 = qad_utils.getPolarPointByPtAngle(self.center, self.endAngle, self.radius)

      if p1.x() > p2.x():
         xMax = p1.x()
         xMin = p2.x()
      else:
         xMax = p2.x()
         xMin = p1.x()

      if p1.y() > p2.y():
         yMax = p1.y()
         yMin = p2.y()
      else:
         yMax = p2.y()
         yMin = p1.y()

      end = self.endAngle
      if end < self.startAngle: end = end + 2 * math.pi

      if end > math.pi / 2:
         if self.startAngle < math.pi / 2: yMax = circleBoundingBox.yMaximum()
         if end > math.pi:
            if self.startAngle < math.pi: xMin = circleBoundingBox.xMinimum()
            if end > math.pi * 3 / 4:
               if self.startAngle < math.pi * 3 / 4: yMin = circleBoundingBox.yMinimum()
               if end > math.pi * 2:
                  xMax = circleBoundingBox.xMaximum()
                  if end > math.pi * 2 + math.pi / 2:
                     yMax = circleBoundingBox.yMaximum()
                     if end > math.pi * 2 + math.pi:
                        xMin = circleBoundingBox.xMinimum()
                        if end > math.pi * 2 + math.pi * 3 / 4:
                           yMin = circleBoundingBox.yMinimum()

      return QgsRectangle(xMin, yMin, xMax, yMax)


   # ===============================================================================
   # containsPt
   # ===============================================================================
   def containsPt(self, point):
      # required
      """the function returns true if the point is on the arc (extremes included).
            point is of type QgsPointXY.
      """
      dist = qad_utils.getDistance(self.center, point)
      if qad_utils.doubleNear(self.radius, dist):
         return self.isPtOnArcOnlyByAngle(point)
      else:
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
      dummy = QadArc(self)
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
      if distance < 0:
         return None, None
      l = self.length()
      if distance > l:
         return None, None

      # (2*pi) : (2*pi*r) = angle : delta
      angle = distance / self.radius

      if self.reversed:
         angle = self.endAngle - angle
      else:
         angle = self.startAngle + angle

      pt = qad_utils.getPolarPointByPtAngle(self.center, angle, self.radius)
      return pt, self.getTanDirectionOnPt(pt)


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
      circle = QadCircle().set(self.center, self.radius)
      # arc length + delta cannot be >= the circumference of the circle
      if length + delta >= circle.length():
         return False
      # (2*pi) : (2*pi*r) = angle : delta
      angle = delta / self.radius

      if move_startPt == True:
         if self.reversed:
            self.endAngle = self.endAngle + angle
         else:
            self.startAngle = self.startAngle - angle
      else:
         if self.reversed:
            self.startAngle = self.startAngle - angle
         else:
            self.endAngle = self.endAngle + angle
      return True


   # ============================================================================
   # lengthen_deltaAngle
   # ============================================================================
   def lengthen_deltaAngle(self, move_startPt, delta):
      # required
      """the function moves the starting point (if move_startPt = True) or ending point (if move_startPt = False)
            of the arc of a certain number of delta degrees
      """
      totalAngle = self.totalAngle()
      # arc angle + delta cannot be >= 2 * pi
      if totalAngle + delta >= 2 * math.pi:
         return False
      # arc angle + delta cannot be <= 0
      if totalAngle + delta <= 0:
         return False

      if move_startPt == True:
         if self.reversed:
            self.endAngle = self.endAngle + delta
         else:
            self.startAngle = self.startAngle - delta
      else:
         if self.reversed:
            self.startAngle = self.startAngle - delta
         else:
            self.endAngle = self.endAngle + delta
      return True


   # ============================================================================
   # getQuadrantPoints
   # ============================================================================
   def getQuadrantPoints(self):
      result = []

      angle = 0
      if self.isAngleBetweenAngles(angle) == True:
         result.append(QgsPointXY(self.center.x() + self.radius, self.center.y()))

      angle = math.pi / 2
      if self.isAngleBetweenAngles(angle) == True:
         result.append(QgsPointXY(self.center.x(), self.center.y() + self.radius))

      angle = math.pi
      if self.isAngleBetweenAngles(angle) == True:
         result.append(QgsPointXY(self.center.x() - self.radius, self.center.y()))

      angle = math.pi * 3 / 2
      if self.isAngleBetweenAngles(angle) == True:
         result.append(QgsPointXY(self.center.x(), self.center.y() - self.radius))

      return result


   # ===============================================================================
   # getMiddlePoint
   # ===============================================================================
   def getMiddlePt(self):
      halfAngle = self.totalAngle() / 2
      return qad_utils.getPolarPointByPtAngle(self.center,
                                              self.startAngle + halfAngle,
                                              self.radius)


   # ============================================================================
   # getTanDirectionOnPt
   # ============================================================================
   def getTanDirectionOnPt(self, pt):
      # required
      """the function returns the direction of the tangent to the object point."""
      angle = qad_utils.getAngleBy2Pts(self.center, pt)
      if self.reversed:  # the direction of the arc is reversed
         return qad_utils.normalizeAngle(angle - math.pi / 2)
      else:
         return qad_utils.normalizeAngle(angle + math.pi / 2)


   # ============================================================================
   # getTanDirectionOnStartPt, getTanDirectionOnEndPt, getTanDirectionOnMiddlePt
   # ============================================================================
   def getTanDirectionOnStartPt(self):
      # required
      """the function returns the direction of the tangent to the starting point of the object."""
      return self.getTanDirectionOnPt(self.getStartPt())

   def getTanDirectionOnEndPt(self):
      # required
      """the function returns the direction of the tangent to the final point of the object."""
      return self.getTanDirectionOnPt(self.getEndPt())


   def getTanDirectionOnMiddlePt(self):
      # required
      """the function returns the direction of the tangent to the midpoint of the object."""
      return self.getTanDirectionOnPt(self.getMiddlePt())


   # ===============================================================================
   # leftOf
   # ===============================================================================
   def leftOf(self, pt):
      # required
      """the function returns a number < 0 if the point pt is to the left of the arc ptStart -> ptEnd"""
      if qad_utils.getDistance(self.center, pt) - self.radius > 0:
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
   def asPolyline(self, tolerance2ApproxCurve=None, atLeastNSegment=None):
      # required
      """returns a list of points that defines the arc"""
      if tolerance2ApproxCurve is None:
         tolerance = QadVariables.get(QadMsg.translate("Environment variables", "TOLERANCE2APPROXCURVE"))
      else:
         tolerance = tolerance2ApproxCurve

      if atLeastNSegment is None:
         _atLeastNSegment = QadVariables.get(QadMsg.translate("Environment variables", "ARCMINSEGMENTQTY"), 12)
      else:
         _atLeastNSegment = atLeastNSegment

      # Calculate the length of the segment with Pythagoras
      dummy = self.radius - tolerance
      if dummy <= 0:  # if the tolerance is too low compared to the radius
         SegmentLen = self.radius
      else:
         dummy = (self.radius * self.radius) - (dummy * dummy)
         SegmentLen = math.sqrt(dummy)  # radice quadrata
         SegmentLen = SegmentLen * 2

      if SegmentLen == 0:  # if the tolerance is too low the length of the segment becomes zero
         return None

      # calculate how many segments are needed (not less than _atLeastNSegment)
      SegmentTot = math.ceil(self.length() / SegmentLen)
      if SegmentTot < _atLeastNSegment:
         SegmentTot = _atLeastNSegment

      if SegmentTot > 99999: # I put a limit on the number of segments
         SegmentTot = _atLeastNSegment

      points = []
      if self.reversed:  # the direction of the arc is reversed
         pt = qad_utils.getPolarPointByPtAngle(self.center, self.endAngle, self.radius)
         points.append(pt)

         i = 1
         angle = self.endAngle
         offsetAngle = self.totalAngle() / SegmentTot
         while i < SegmentTot:
            angle = angle - offsetAngle
            pt = qad_utils.getPolarPointByPtAngle(self.center, angle, self.radius)
            points.append(pt)
            i = i + 1

         # last point
         pt = qad_utils.getPolarPointByPtAngle(self.center, self.startAngle, self.radius)
      else:
         pt = qad_utils.getPolarPointByPtAngle(self.center, self.startAngle, self.radius)
         points.append(pt)

         i = 1
         angle = self.startAngle
         offsetAngle = self.totalAngle() / SegmentTot
         while i < SegmentTot:
            angle = angle + offsetAngle
            pt = qad_utils.getPolarPointByPtAngle(self.center, angle, self.radius)
            points.append(pt)
            i = i + 1

         # last point
         pt = qad_utils.getPolarPointByPtAngle(self.center, self.endAngle, self.radius)
      points.append(pt)

      return points


   # ===============================================================================
   # asCircularString
   # ===============================================================================
   def asCircularString(self, forcedStartPt = None):
      """the function returns the arc in the form of circularString.
            When the arc is part of a polyline, its starting point must coincide with the final point of the previous part
            therefore the starting point is forced.
      """
      if forcedStartPt is None:
         return QgsCircularString(QgsPoint(self.getStartPt()), QgsPoint(self.getMiddlePt()), QgsPoint(self.getEndPt()))
      else:
         return QgsCircularString(QgsPoint(forcedStartPt), QgsPoint(self.getMiddlePt()), QgsPoint(self.getEndPt()))


   # ===============================================================================
   # asLineString
   # ===============================================================================
   def asLineString(self, tolerance2ApproxCurve = None, atLeastNSegment = None):
      """the function returns the arc in the form of a lineString."""
      pts = self.asPolyline(tolerance2ApproxCurve, atLeastNSegment)
      if pts is None or len(pts) == 0:
          return None
      return QgsLineString(pts)


   # ===============================================================================
   # asAbstractGeom
   # ===============================================================================
   def asAbstractGeom(self, wkbType = QgsWkbTypes.LineString, tolerance2ApproxCurve = None, atLeastNSegment = None):
      """the function returns the arc in the form of QgsAbstractGeometry."""
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
      """the function returns the arc in the form of QgsGeometry."""
      return QgsGeometry(self.asAbstractGeom(wkbType, tolerance2ApproxCurve, atLeastNSegment));


   # ============================================================================
   # fromStartSecondEndPts
   # ============================================================================
   def fromStartSecondEndPts(self, startPt, secondPt, endPt):
      """set the characteristics of the arc through:
            starting point
            second point (intermediate)
            final point
      """
      points = [startPt, secondPt, endPt]
      # list of points, starts from point 0, at least 2 segments
      if self.fromPolyline(points, 0, 2) == None: return False
      return True


   # ============================================================================
   # fromStartCenterEndPts
   # ============================================================================
   def fromStartCenterEndPts(self, startPt, centerPt, endPt):
      """set the characteristics of the arc through:
            starting point
            center
            final point
      """
      if startPt == centerPt or startPt == endPt or endPt == centerPt:
         return False

      self.center = centerPt
      self.radius = qad_utils.getDistance(centerPt, startPt)
      self.startAngle = qad_utils.getAngleBy2Pts(centerPt, startPt)
      self.endAngle = qad_utils.getAngleBy2Pts(centerPt, endPt)
      self.reversed = False
      return True


   # ============================================================================
   # fromStartCenterPtsAngle
   # ============================================================================
   def fromStartCenterPtsAngle(self, startPt, centerPt, angle):
      """set the characteristics of the arc through:
            starting point
            center
            inscribed angle
      """
      if startPt == centerPt or angle == 0:
         return False

      self.center = centerPt
      self.radius = qad_utils.getDistance(centerPt, startPt)
      self.startAngle = qad_utils.getAngleBy2Pts(centerPt, startPt)
      self.endAngle = self.startAngle + angle
      if self.endAngle > math.pi * 2:
         self.endAngle = self.endAngle % (math.pi * 2)  # modulo
      self.reversed = False
      return True


   # ============================================================================
   # fromStartCenterPtsChord
   # ============================================================================
   def fromStartCenterPtsChord(self, startPt, centerPt, chord):
      """set the characteristics of the arc through:
            starting point
            center
            length of the chord between starting and ending point
      """
      if startPt == centerPt or chord == 0:
         return False

      self.center = centerPt
      self.radius = qad_utils.getDistance(centerPt, startPt)
      if chord > 2 * self.radius:
         return False
      self.startAngle = qad_utils.getAngleBy2Pts(centerPt, startPt)
      # Teorema della corda
      angle = 2 * math.asin(chord / (2 * self.radius))
      self.endAngle = self.startAngle + angle
      self.reversed = False
      return True


   # ============================================================================
   # fromStartCenterPtsLength
   # ============================================================================
   def fromStartCenterPtsLength(self, startPt, centerPt, length):
      """set the characteristics of the arc through:
            starting point
            center
            length of the chord between starting and ending point
      """
      if startPt == centerPt or chord == 0:
         return False

      self.center = centerPt
      self.radius = qad_utils.getDistance(centerPt, startPt)
      circumference = 2 * math.pi * self.radius
      if length >= circumference:
         return False
      self.startAngle = qad_utils.getAngleBy2Pts(centerPt, startPt)

      # circumference : math.pi * 2 = length : angle
      angle = (math.pi * 2) * length / circumference
      self.endAngle = self.startAngle + angle
      self.reversed = False
      return True


   # ============================================================================
   # fromStartEndPtsAngle
   # ============================================================================
   def fromStartEndPtsAngle(self, startPt, endPt, angle):
      """set the characteristics of the arc through:
            starting point
            final point
            inscribed angle
      """
      if startPt == endPt or angle == 0:
         return False

      chord = qad_utils.getDistance(startPt, endPt)
      half_chord = chord / 2
      # Teorema della corda
      self.radius = half_chord / math.sin(angle / 2)

      angleSegment = qad_utils.getAngleBy2Pts(startPt, endPt)
      ptMiddle = qad_utils.getMiddlePoint(startPt, endPt)

      # Pitagora
      distFromCenter = math.sqrt((self.radius * self.radius) - (half_chord * half_chord))
      if angle < math.pi:  # if angle < 180 degrees
         # add 90 degrees to searc for the left center of the segment
         self.center = qad_utils.getPolarPointByPtAngle(ptMiddle,
                                                        angleSegment + (math.pi / 2),
                                                        distFromCenter)
      else:
         # I subtract 90 degrees to find the center right of the segment
         self.center = qad_utils.getPolarPointByPtAngle(ptMiddle,
                                                        angleSegment - (math.pi / 2),
                                                        distFromCenter)
      self.startAngle = qad_utils.getAngleBy2Pts(self.center, startPt)
      self.endAngle = qad_utils.getAngleBy2Pts(self.center, endPt)
      self.reversed = False
      return True


   # ============================================================================
   # fromStartEndPtsTan
   # ============================================================================
   def fromStartEndPtsTan(self, startPt, endPt, tan):
      """set the characteristics of the arc through:
            starting point
            final point
            direction of the tangent on the starting point
      """
      if startPt == endPt:
         return False

      angleSegment = qad_utils.getAngleBy2Pts(startPt, endPt)
      if tan == angleSegment or tan == angleSegment - math.pi:
         return False

      chord = qad_utils.getDistance(startPt, endPt)
      half_chord = chord / 2
      ptMiddle = qad_utils.getMiddlePoint(startPt, endPt)

      angle = tan + (math.pi / 2)
      angle = angleSegment - angle
      distFromCenter = math.tan(angle) * half_chord
      self.center = qad_utils.getPolarPointByPtAngle(ptMiddle,
                                                     angleSegment - (math.pi / 2),
                                                     distFromCenter)
      pt = qad_utils.getPolarPointByPtAngle(startPt, tan, chord)

      if qad_utils.leftOfLine(endPt, startPt, pt) < 0:
         # arc develops to the left of the tangent
         self.startAngle = qad_utils.getAngleBy2Pts(self.center, startPt)
         self.endAngle = qad_utils.getAngleBy2Pts(self.center, endPt)
         self.reversed = False
      else:
         # arc develops to the right of the tangent
         self.startAngle = qad_utils.getAngleBy2Pts(self.center, endPt)
         self.endAngle = qad_utils.getAngleBy2Pts(self.center, startPt)
         self.reversed = True

      self.radius = qad_utils.getDistance(startPt, self.center)
      return True


   # ============================================================================
   # fromStartEndPtsRadius
   # ============================================================================
   def fromStartEndPtsRadius(self, startPt, endPt, radius):
      """set the characteristics of the arc through:
            starting point
            final point
            radius
      """
      if startPt == endPt or radius <= 0:
         return False

      chord = qad_utils.getDistance(startPt, endPt)
      half_chord = chord / 2
      if radius < half_chord:
         return False

      self.radius = radius
      angleSegment = qad_utils.getAngleBy2Pts(startPt, endPt)
      ptMiddle = qad_utils.getMiddlePoint(startPt, endPt)

      # Pitagora
      distFromCenter = math.sqrt((self.radius * self.radius) - (half_chord * half_chord))
      # add 90 degrees
      self.center = qad_utils.getPolarPointByPtAngle(ptMiddle,
                                                     angleSegment + (math.pi / 2),
                                                     distFromCenter)
      self.startAngle = qad_utils.getAngleBy2Pts(self.center, startPt)
      self.endAngle = qad_utils.getAngleBy2Pts(self.center, endPt)
      self.reversed = False
      return True


   # ============================================================================
   # fromStartPtAngleRadiusChordDirection
   # ============================================================================
   def fromStartPtAngleRadiusChordDirection(self, startPt, angle, radius, chordDirection):
      """set the characteristics of the arc through:
            starting point
            inscribed angle
            radius
            direction of the string
      """
      if angle == 0 or angle == 2 * math.pi or radius <= 0:
         return False

      a = chordDirection + (math.pi / 2) - (angle / 2)
      self.radius = radius
      self.center = qad_utils.getPolarPointByPtAngle(startPt, a, radius)
      endPt = qad_utils.getPolarPointByPtAngle(self.center, a + math.pi + angle, radius)

      self.startAngle = qad_utils.getAngleBy2Pts(self.center, startPt)
      self.endAngle = qad_utils.getAngleBy2Pts(self.center, endPt)
      self.reversed = False
      return True


   # ============================================================================
   # fromPolyline
   # ============================================================================
   def fromPolyline(self, points, startVertex, atLeastNSegment=None):
      """sets the characteristics of the first arc encountered in the list of points
            starting from the startVertex position (0-indexed).
            Returns the position in the list of the end point if an arc was found
            otherwise None
            N.B. the points must NOT be in geographic coordinates
      """
      # if the initial and final points coincide it is not an arc
      if points[startVertex] == points[-1]:
         return None

      i = startVertex

      if atLeastNSegment is None:
         _atLeastNSegment = QadVariables.get(QadMsg.translate("Environment variables", "ARCMINSEGMENTQTY"), 12)
      else:
         _atLeastNSegment = atLeastNSegment

      totPoints = len(points) - startVertex
      nSegment = totPoints - 1
      # for it to be an arc you need at least _atLeastNSegment segments and at least 3 points
      if nSegment < _atLeastNSegment or totPoints < 3:
         return None

      myPoints = []
      # I move the first 3 points close to 0.0 to improve the accuracy of the calculations
      dx = points[startVertex].x()
      dy = points[startVertex].y()
      myPoints.append(qad_utils.movePoint(points[startVertex], -dx, -dy))
      myPoints.append(qad_utils.movePoint(points[startVertex + 1], -dx, -dy))
      myPoints.append(qad_utils.movePoint(points[startVertex + 2], -dx, -dy))

#       InfinityLinePerpOnMiddle1 = qd_utils.getInfinityLinePerpOnMiddle(myPoints[0], myPoints[1])
#       if InfinityLinePerpOnMiddle1 is None: return None
#       InfinityLinePerpOnMiddle2 = qad_utils.getInfinityLinePerpOnMiddle(myPoints[1], myPoints[2])
#       if InfinityLinePerpOnMiddle2 is None: return None
#
#       # calculate the presumed center with 2 segments
#       center = qad_utils.getIntersectionPointOn2InfinityLines(InfinityLinePerpOnMiddle1[0], \
#                                                               InfinityLinePerpOnMiddle1[1], \
#                                                               InfinityLinePerpOnMiddle2[0], \
#                                                               InfinityLinePerpOnMiddle2[1])
#       if center is None: return None # linee parallele

      # if I use QgsCircle I get better precision
      circle = QgsCircle.from3Points(QgsPoint(myPoints[0]), QgsPoint(myPoints[1]), QgsPoint(myPoints[2]))
      if circle.isEmpty() == True:
         return None

      center = circle.center()
      center = QgsPointXY(center.x(), center.y())
      radius = qad_utils.getDistance(center, myPoints[0])  # calculate the presumed radius

      # calculate the direction of the arc and the angle of the arc
      # if an intermediate point of the arc is to the left of the
      # segment that joins the two points then the direction is anti-clockwise
      startClockWise = True if qad_utils.leftOfLine(myPoints[1], myPoints[0], myPoints[2]) < 0 else False
      angle = qad_utils.getAngleBy3Pts(myPoints[0], center, myPoints[2], startClockWise)

      # I use the distance TOLERANCE2COINCIDENT / 2 because in a polyline if there are 2 consecutive arcs
      # you want to be sure that the end point of the first arc is far from the start point of the
      # second arc no more than TOLERANCE2COINCIDENT for them to be considered 2 coincident points
      myTolerance = QadVariables.get(QadMsg.translate("Environment variables", "TOLERANCE2COINCIDENT")) / 2
      # myTolerance = 0 # test

      i = 3
      while i < totPoints:
         # I move the points closer to 0.0 to improve the accuracy of the calculations
         myPoints.append(qad_utils.movePoint(points[i + startVertex], -dx, -dy))

         # if TOLERANCE2COINCIDENT = 0.001 an arc of 1000 m is recognized
         # if the calculated point is not close enough to the real point
         # otherwise I find problems with intersections with objects
         if qad_utils.ptNear(qad_utils.getPolarPointByPtAngle(center, qad_utils.getAngleBy2Pts(center, myPoints[i]), radius), \
                              myPoints[i], myTolerance) == False:
             break

         # calculate the direction of the arc and the angle
         clockWise = True if qad_utils.leftOfLine(myPoints[i - 1], myPoints[i - 2], myPoints[i]) < 0 else False
         if startClockWise != clockWise: break # changed direction
         angle = angle + qad_utils.getAngleBy3Pts(myPoints[i - 1], center, myPoints[i], startClockWise)
         if angle >= 2 * math.pi: break # the arc cannot have an internal angle greater than or equal to 2 pi

         i = i + 1

      # if not enough subsequent segments were found
      i = i - 1 # last valid point of the arc
      if i < _atLeastNSegment: return None

      self.center = center
      self.radius = radius

      # if the direction is clockwise
      if startClockWise:
         # I invert the initial angle with the final one
         self.endAngle = qad_utils.getAngleBy2Pts(center, myPoints[0])
         self.startAngle = qad_utils.getAngleBy2Pts(center, myPoints[i])
         self.reversed = True
      else:
         self.startAngle = qad_utils.getAngleBy2Pts(center, myPoints[0])
         self.endAngle = qad_utils.getAngleBy2Pts(center, myPoints[i])
         self.reversed = False

      # I translate the geometry to return it to its original position
      self.move(dx, dy)

      return i + startVertex


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
      angle = qad_utils.getAngleBy2Pts(self.center, point)
      if self.isAngleBetweenAngles(angle):
         distFromArc = qad_utils.getDistance(self.center, point) - self.radius
         return (distFromArc * distFromArc, qad_utils.getPolarPointByPtAngle(self.center, angle, self.radius))
      else:
         startPt = self.getStartPt()
         endPt = self.getEndPt()
         distFromStartPt = qad_utils.getSqrDistance(startPt, point)
         distFromEndPt = qad_utils.getSqrDistance(endPt, point)
         if distFromStartPt < distFromEndPt:
            return (distFromStartPt, startPt)
         else:
            return (distFromEndPt, endPt)



   # ============================================================================
   # move
   # ============================================================================
   def move(self, offsetX, offsetY):
      # required
      self.center = qad_utils.movePoint(self.center, offsetX, offsetY)


   # ============================================================================
   # rotate
   # ============================================================================
   def rotate(self, basePt, angle):
      self.center = qad_utils.rotatePoint(self.center, basePt, angle)
      self.startAngle = qad_utils.normalizeAngle(self.startAngle + angle)
      self.endAngle = qad_utils.normalizeAngle(self.endAngle + angle)


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
      startPt = qad_utils.mirrorPoint(self.getStartPt(), mirrorPt, mirrorAngle)
      secondPt = qad_utils.mirrorPoint(self.getMiddlePt(), mirrorPt, mirrorAngle)
      endPt = qad_utils.mirrorPoint(self.getEndPt(), mirrorPt, mirrorAngle)
      self.fromStartSecondEndPts(startPt, secondPt, endPt)
      #self.reversed = not self.reversed # change the direction of the arc


   # ===============================================================================
   # offset
   # ===============================================================================
   def offset(self, offsetDist, offsetSide):
      """the function modifies the arc by offsetting it
            according to a distance and an offset side ("right" or "left" or "internal" or "external")
      """
      side = ""
      if offsetSide == "right":
         if self.reversed: # direzione oraria
            side = "internal" # offset towards the inside of the circle
         else:
            side = "external" # offset towards the outside of the circle
      elif offsetSide == "left":
         if self.reversed: # direzione oraria
            side = "external" # offset towards the outside of the circle
         else:
            side = "internal" # offset towards the inside of the circle
      else:
         side = offsetSide

      if side == "internal": # offset towards the inside of the circle
         radius = self.radius - offsetDist
      elif side == "external": # offset towards the outside of the circle
         radius = self.radius + offsetDist

      if radius <= 0: return False
      self.radius = radius

      return True


   # ============================================================================
   # extend
   # ============================================================================
   def extend(self, extend_startPt, limitPt, tolerance2ApproxCurve):
      """the function extends the arc from the starting point if extend_startPt = True (otherwise final) up to
            meet the point <limitPt>.
      """
      if extend_startPt:
         if self.reversed:
            return self.setEndAngleByPt(limitPt)
         else:
            return self.setStartAngleByPt(limitPt)
      else:
         if self.reversed:
            return self.setStartAngleByPt(limitPt)
         else:
            return self.setEndAngleByPt(limitPt)


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
