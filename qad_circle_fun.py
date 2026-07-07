# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 functions for creating circles

                              -------------------
        begin                : 2018-04-08
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
from .qad_geom_relations import *


# ============================================================================
# circleFrom3Pts
# ============================================================================
def circleFrom3Pts(firstPt, secondPt, thirdPt):
   """create a circle through:
      starting point
      second point (intermediate)
      final point
   """
   l = QadLine()
   l.set(firstPt, secondPt)
   InfinityLinePerpOnMiddle1 = QadPerpendicularity.getInfinityLinePerpOnMiddleLine(l)
   l.set(secondPt, thirdPt)
   InfinityLinePerpOnMiddle2 = QadPerpendicularity.getInfinityLinePerpOnMiddleLine(l)
   if InfinityLinePerpOnMiddle1 is None or InfinityLinePerpOnMiddle2 is None:
      return None
   center = QadIntersections.twoInfinityLines(InfinityLinePerpOnMiddle1, InfinityLinePerpOnMiddle2)
   if center is None: return None # linee parallele
   radius = center.distance(firstPt)

   return QadCircle().set(center, radius)


# ===========================================================================
# circleFrom2IntPtsCircleTanPts
# ===========================================================================
def circleFrom2IntPtsCircleTanPts(pt1, pt2, circle, pt):
   """create a circle through 2 intersection points and a tangent circle:
      intersection point1
      intersection point2
      circle of tangency (QadCircle object)
      circle selection point
   """
   # http://www.batmath.it/matematica/a_apollonio/ppc.htm
   circleList = []

   if pt1 == pt2: return None

   dist1 = pt1.distance(circle.center) # distance of point 1 from the center
   dist2 = pt2.distance(circle.center) # distance of point 2 from the center

   # both points must be external or internal to circle
   if (dist1 > circle.radius and dist2 < circle.radius) or \
      (dist1 < circle.radius and dist2 > circle.radius):
      return None

   l = QadLine()
   l.set(pt1, pt2)

   if dist1 == dist2: # the axis of pt1 and pt2 passes through the center of the circle
      if dist1 == circle.radius: # both points are on the circumference of circle
         return None

      axis = QadPerpendicularity.getInfinityLinePerpOnMiddleLine(l) # axis of pt1 and pt2
      intPts = QadIntersections.infinityLineWithCircle(axis, circle) # points of intersection between the axis and circle
      for intPt in intPts:
         circleTan = circleFrom3Pts(pt1, pt2, intPt)
         if circleTan is not None:
            circleList.append(circleTan)
   elif dist1 > circle.radius and dist2 > circle.radius : # both points are external to circle
      # get any circumference passing through p1 and p2 and intersecting circle
      circleInt = circleFrom3Pts(pt1, pt2, circle.center)
      if circleInt is None: return None

      intPts = QadIntersections.twoCircles(circle, circleInt)
      l1 = QadLine().set(pt1, pt2)
      l2 = QadLine().set(intPts[0], intPts[1])
      intPt = QadIntersections.twoInfinityLines(l1, l2)
      tanPts = QadTangency.fromPointToCircle(intPt, circle)
      for tanPt in tanPts:
         circleTan = circleFrom3Pts(pt1, pt2, tanPt)
         if circleTan is not None:
            circleList.append(circleTan)
   elif dist1 < circle.radius and dist2 < circle.radius : # both points are inside circle
      # get any circumference passing through p1 and p2 and intersecting circle
      ptMiddle = qad_utils.getMiddlePoint(pt1, pt2)
      angle = qad_utils.getAngleBy2Pts(pt1, pt2) + math.pi / 2
      pt3 = qad_utils.getPolarPointByPtAngle(ptMiddle, angle, 2 * circle.radius)
      circleInt = circleFrom3Pts(pt1, pt2, pt3)
      if circleInt is None:
         return None
      intPts = QadIntersections.twoCircles(circle, circleInt)
      l1 = QadLine().set(pt1, pt2)
      l2 = QadLine().set(intPts[0], intPts[1])
      intPt = QadIntersections.twoInfinityLines(l1, l2)
      tanPts = QadTangency.fromPointToCircle(intPt, circle)
      for tanPt in tanPts:
         circleTan = circleFrom3Pts(pt1, pt2, tanPt)
         if circleTan is not None:
            circleList.append(circleTan)
   elif dist1 == radius: # point 1 on the circumference of circle
      # a single circle having as its center the intersection between the pt1 and pt2 axes and the straight line
      # passing through the center of circle and pt1
      axis = QadPerpendicularity.getInfinityLinePerpOnMiddleLine(l) # axis of pt1 and pt2
      l1 = QadLine().set(circle.center, pt1)
      intPt = QadIntersections.twoInfinityLines(axis, l1)
      circleTan = QadCircle().set(intPt, qad_utils.getDistance(pt1, intPt))
      circleList.append(circleTan)
   elif dist2 == radius: # point3 is on the circumference of circle
      # a single circle having as its center the intersection between the pt1 and pt2 axes and the straight line
      # passing through the center of circle and pt2
      axis = QadPerpendicularity.getInfinityLinePerpOnMiddleLine(l) # axis of pt1 and pt2
      l2 = QadLine().set(circle.center, pt2)
      intPt = QadIntersections.twoInfinityLines(axis, l2)
      circleTan = QadCircle().set(intPt, qad_utils.getDistance(pt2, intPt))
      circleList.append(circleTan)

   if len(circleList) == 0:
      return None

   result = QadCircle()
   minDist = sys.float_info.max
   for circleTan in circleList:
      angle = qad_utils.getAngleBy2Pts(circleTan.center, circle.center)
      if qad_utils.getDistance(circleTan.center, circle.center) < circle.radius: # inner circle
         angle = angle + math.pi / 2
      ptInt = qad_utils.getPolarPointByPtAngle(circleTan.center, angle, circleTan.radius)
      dist = qad_utils.getDistance(ptInt, pt)

      if dist < minDist: # closer on average
         minDist = dist
         result.center = circleTan.center
         result.radius = circleTan.radius

   return result


# ===========================================================================
# circleFrom2IntPtsLineTanPts
# ===========================================================================
def circleFrom2IntPtsLineTanPts(pt1, pt2, line, pt, AllCircles = False):
   """create one or more circles (see allCircles) through 2 intersection points and a tangent line:
      intersection point1
      intersection point2
      tangency line (QadLine)
      line selection point
      the AllCircles parameter if = True returns all the circles otherwise only the one closest to pt1 and pt2
   """
   circleList = []

   pt1Line = line.getStartPt()
   pt2Line = line.getEndPt()

   A = (pt1.x() * pt1.x()) + (pt1.y() * pt1.y())
   B = (pt2.x() * pt2.x()) + (pt2.y() * pt2.y())

   E = - pt1.x() + pt2.x()
   F = pt1.y() - pt2.y()
   if F == 0:
      if AllCircles == True:
         return circleList
      else:
         return None

   G = (-A + B) / F
   H = E / F

   if pt1Line.x() - pt2Line.x() == 0:
      # the line is vertical
      e = pt1Line.x()
      I = H * H
      if I == 0:
         if AllCircles == True:
            return circleList
         else:
            return None
      J = (2 * G * H) - (4 * e) + (4 * pt2.x()) + (4 * H * pt2.y())
      K = (G * G) - (4 * e * e) + (4 * B) + (4 * G * pt2.y())
   else:
      # line equation -> y = dx + e
      d = (pt2Line.y() - pt1Line.y()) / (pt2Line.x() - pt1Line.x())
      e = - d * pt1Line.x() + pt1Line.y()
      C = 4 * (1 + d * d)
      D = 2 * d * e
      d2 = d * d
      I = 1 + (H * H * d2) + 2 * H * d
      if I == 0:
         if AllCircles == True:
            return circleList
         else:
            return None
      J = (2 * d2 * G * H) + (2 * D) + (2 * D * H * d) + (2 * G * d) - (e * C * H) + (pt2.x() * C) + H * pt2.y() * C
      K = (G * G * d2) + (2 * D * G * d) + (D * D) - (C * e * e) - (C * G * e) + (B * C) + (G * pt2.y() * C)

   L = (J * J) - (4 * I * K)
   if L < 0:
      if AllCircles == True:
         return circleList
      else:
         return None

   a1 = (-J + math.sqrt(L)) / (2 * I)
   b1 = (a1 * H) + G
   c1 = - B - (a1 * pt2.x()) - (b1 * pt2.y())
   center = QgsPointXY()
   center.setX(- (a1 / 2))
   center.setY(- (b1 / 2))
   radius = math.sqrt((a1 * a1 / 4) + (b1 * b1 / 4) - c1)
   circle = QadCircle()
   circle.set(center, radius)
   circleList.append(circle)

   a2 = (-J - math.sqrt(L)) / (2 * I)
   b2 = (a2 * H) + G
   c2 = - B - (a2 * pt2.x()) - (b2 * pt2.y())
   center.setX(- (a2 / 2))
   center.setY(- (b2 / 2))
   radius = math.sqrt((a2 * a2 / 4) + (b2 * b2 / 4) - c2)
   circle = QadCircle()
   circle.set(center, radius)
   circleList.append(circle)

   if AllCircles == True:
      return circleList

   if len(circleList) == 0:
      return None

   result = QadCircle()
   minDist = sys.float_info.max
   for circle in circleList:
      ptInt = QadPerpendicularity.fromPointToInfinityLine(circle.center, line)
      dist = ptInt.distance(pt)

      if dist < minDist: # closer on average
         minDist = dist
         result.center = circle.center
         result.radius = circle.radius

   return result


# ============================================================================
# circleFrom2IntPts1TanPt
# ============================================================================
def circleFrom2IntPts1TanPt(pt1, pt2, geom, pt):
   """creates a circle through 2 intersection points and a tangent object:
      intersection point1
      intersection point2
      tangency geometry (line, arc or circle)
      geometry selection point
   """
   objType = geom.whatIs()

   if objType != "LINE" and objType != "ARC" and objType != "CIRCLE":
      return None

   if objType == "ARC": # if it is an arc I transform it into a circle
      obj = QadCircle().set(geom.center, geom.radius)
      objType = "CIRCLE"
   else:
      obj = geom

   if objType == "LINE":
      return circleFrom2IntPtsLineTanPts(pt1, pt2, obj, pt)
   elif objType == "CIRCLE":
      return circleFrom2IntPtsCircleTanPts(pt1, pt2, obj, pt)

   return None


# ============================================================================
# circleFrom1IntPt2TanPts
# ============================================================================
def circleFrom1IntPt2TanPts(pt, geom1, pt1, geom2, pt2):
   """creates a circle through 1 intersection points and 2 tangent objects:
      intersection point
      tangency geometry1 (line, arc or circle)
      geometry selection point1
      tangency geometry2 (line, arc or circle)
      geometry selection point2
   """
   obj1Type = geom1.whatIs()
   obj2Type = geom2.whatIs()

   if (obj1Type != "LINE" and obj1Type != "ARC" and obj1Type != "CIRCLE") or \
      (obj2Type != "LINE" and obj2Type != "ARC" and obj2Type != "CIRCLE"):
      return None

   if obj1Type == "ARC": # if it is an arc I transform it into a circle
      obj1 = QadCircle().set(geom1.center, geom1.radius)
      obj1Type = "CIRCLE"
   else:
      obj1 = geom1

   if obj2Type == "ARC": # if it is an arc I transform it into a circle
      obj2 = QadCircle().set(geom2.center, geom2.radius)
      obj2Type = "CIRCLE"
   else:
      obj2 = geom2

   if obj1Type == "LINE":
      if obj2Type == "LINE":
         return circleFrom1IntPtLineLineTanPts(pt, obj1, pt1, obj2, pt2)
      elif obj2Type == "CIRCLE":
         return circleFrom1IntPtLineCircleTanPts(pt, obj1, pt1, obj2, pt2)
   elif obj1Type == "CIRCLE":
      if obj2Type == "LINE":
         return circleFrom1IntPtLineCircleTanPts(pt, obj2, pt2, obj1, pt1)
      elif obj2Type == "CIRCLE":
         return circleFrom1IntPtCircleCircleTanPts(pt, obj1, pt1, obj2, pt2)

   return None


# ===========================================================================
# circleFrom1IntPtLineLineTanPts
# ===========================================================================
def circleFrom1IntPtLineLineTanPts(pt, line1, pt1, line2, pt2, AllCircles = False):
   """create one or more circles (see allCircles) through 1 intersection points and two tangent lines:
      intersection point
      tangency line1 (QLine)
      line selection point1
      tangency line2 (QLine)
      line selection point2
      the AllCircles parameter if = True returns all the circles and they are not the one closest to pt1 and pt2
   """
   # http://www.batmath.it/matematica/a_apollonio/prr.htm
   circleList = []

   # check if the lines are parallel
   ptInt = QadIntersections.twoInfinityLines(line1, line2)
   if ptInt is None: # the lines are parallel
      # If the lines are parallel the problem has solutions only if the point
      # is not outside the strip identified by the two straight lines, and it is enough to consider
      # the symmetric of A with respect to the bisector of the strip.
      ptPerp = QadPerpendicularity.fromPointToInfinityLine(line2.getStartPt(), line1)
      angle = qad_utils.getAngleBy2Pts(line2.getStartPt(), ptPerp)
      dist = qad_utils.getDistance(line2.getStartPt(), ptPerp)
      pt1ParLine = qad_utils.getPolarPointByPtAngle(line2.getStartPt(), angle, dist / 2)
      angle = angle + math.pi / 2
      pt2ParLine = qad_utils.getPolarPointByPtAngle(pt1ParLine, angle, dist)
      l = QadLine().set(pt1ParLine, pt2ParLine)
      ptPerp = QadPerpendicularity.fromPointToInfinityLine(pt, l)
      dist = qad_utils.getDistance(pt, ptPerp)

      # I find the point symmetrical
      angle = qad_utils.getAngleBy2Pts(pt, ptPerp)
      ptSymmetric = qad_utils.getPolarPointByPtAngle(pt, angle, dist * 2)
      return circleFrom2IntPtsLineTanPts(pt, ptSymmetric, line1, pt1, AllCircles)
   else: # the lines are not parallel
      if ptInt == pt:
         return None
      # if the point is on line1 or line2
      ptPerp1 = QadPerpendicularity.fromPointToInfinityLine(pt, line1)
      ptPerp2 = QadPerpendicularity.fromPointToInfinityLine(pt, line2)
      if ptPerp1 == pt or ptPerp2 == pt:
         # If the lines are incident and the point belongs to one of the two the construction
         # is almost immediate: just trace the bisectors of the two angles identified by the lines
         # and the perpendicular through pt to the line to which pt itself belongs. You will have two circumferences.

         if ptPerp1 == pt: # if the point is on line1
            angle = qad_utils.getAngleBy2Pts(line2.getStartPt(), line2.getEndPt())
            ptLine = qad_utils.getPolarPointByPtAngle(ptInt, angle, 10)
            Bisector1 = qad_utils.getBisectorInfinityLine(pt, ptInt, ptLine)
            ptLine = qad_utils.getPolarPointByPtAngle(ptInt, angle + math.pi, 10)
            Bisector2 = qad_utils.getBisectorInfinityLine(pt, ptInt, ptLine)
            angle = qad_utils.getAngleBy2Pts(line1.getStartPt(), line1.getEndPt())
            ptPerp = qad_utils.getPolarPointByPtAngle(pt, angle + math.pi / 2, 10)
         else: # if the point is on line2
            angle = qad_utils.getAngleBy2Pts(line1.getStartPt(), line1.getEndPt())
            ptLine = qad_utils.getPolarPointByPtAngle(ptInt, angle, 10)
            Bisector1 = qad_utils.getBisectorInfinityLine(pt, ptInt, ptLine)
            ptLine = qad_utils.getPolarPointByPtAngle(ptInt, angle + math.pi, 10)
            Bisector2 = qad_utils.getBisectorInfinityLine(pt, ptInt, ptLine)
            angle = qad_utils.getAngleBy2Pts(line2.getStartPt(), line2.getEndPt())
            ptPerp = qad_utils.getPolarPointByPtAngle(pt, angle + math.pi / 2, 10)

         l1 = QadLine().set(Bisector1[0], Bisector1[1])
         l2 = QadLine().set(pt, ptPerp)
         center = QadIntersections.twoInfinityLines(l1, l2)

         radius = qad_utils.getDistance(pt, center)
         circleTan = QadCircle()
         circleTan.set(center, radius)
         circleList.append(circleTan)

         l1.set(Bisector2[0], Bisector2[1])
         center = QadIntersections.twoInfinityLines(l1, l2)
         radius = qad_utils.getDistance(pt, center)
         circleTan = QadCircle()
         circleTan.set(center, radius)
         circleList.append(circleTan)
      else:
         # Bisector of the internal angle of the triangle having as vertex the points of intersection of the lines
         Bisector = qad_utils.getBisectorInfinityLine(ptPerp1, ptInt, ptPerp2)
         l = QadLine().set(Bisector[0], Bisector[1])
         ptPerp = QadPerpendicularity.fromPointToInfinityLine(pt, l)
         dist = qad_utils.getDistance(pt, ptPerp)

         # I find the point symmetrical
         angle = qad_utils.getAngleBy2Pts(pt, ptPerp)
         ptSymmetric = qad_utils.getPolarPointByPtAngle(pt, angle, dist * 2)
         return circleFrom2IntPtsLineTanPts(pt, ptSymmetric, line1, pt1, AllCircles)

   if AllCircles == True:
      return circleList

   if len(circleList) == 0:
      return None

   result = QadCircle()
   AvgList = []
   Avg = sys.float_info.max
   for circleTan in circleList:
      del AvgList[:] # I empty the list

      ptInt = QadPerpendicularity.fromPointToInfinityLine(circleTan.center, line1)
      AvgList.append(qad_utils.getDistance(ptInt, pt1))

      ptInt = QadPerpendicularity.fromPointToInfinityLine(circleTan.center, line2)
      AvgList.append(qad_utils.getDistance(ptInt, pt2))

      currAvg = qad_utils.numericListAvg(AvgList)
      if currAvg < Avg: # closer on average
         Avg = currAvg
         result.center = circleTan.center
         result.radius = circleTan.radius

   return result


# ===============================================================================
# solveCircleTangentTo2LinesAndCircle
# ===============================================================================
def solveCircleTangentTo2LinesAndCircle(line1, line2, circle, s1, s2):
   """Find the two circles tangent to two lines and a circle (that would be 8 circles that lie with the
      4 combinations of s1, s2 that take on the value -1 or 1)
      and returns the one closest to pt
   """
   circleList = []
   # http://www.batmath.it/matematica/a_apollonio/rrc.htm

   # This construction uses a particular geometric transformation, which some call parallel dilation:
   # imagine that the radius r of the given circle c is reduced to zero (the circle is reduced to its center),
   # while the lines remain parallel with distances from the center of the circle which has been reduced to zero increased o
   # decreased by r. We are thus brought back to the case of a point and two lines and one of the techniques seen can be applied
   # in quel caso.

   line1Par = []
   angle = qad_utils.getAngleBy2Pts(line1.getStartPt(), line1.getEndPt())
   line1Par.append(qad_utils.getPolarPointByPtAngle(line1[0], angle + math.pi / 2, circle.radius * s1))
   line1Par.append(qad_utils.getPolarPointByPtAngle(line1.getEndPt(), angle + math.pi / 2, circle.radius * s1))

   line2Par = []
   angle = qad_utils.getAngleBy2Pts(line2.getStartPt(), line2.getEndPt())
   line2Par.append(qad_utils.getPolarPointByPtAngle(line2.getStartPt(), angle + math.pi / 2, circle.radius * s2))
   line2Par.append(qad_utils.getPolarPointByPtAngle(line2.getEndPt(), angle + math.pi / 2, circle.radius * s2))

   circleList = circleFrom1IntPtLineLineTanPts(circle.center, line1Par, None, line2Par, None, True)

   for circleTan in circleList:
      ptPerp = qad_utils.getPerpendicularPointOnInfinityLine(line1.getStartPt(), line1.getEndPt(), circleTan.center)
      circleTan.radius = qad_utils.getDistance(ptPerp, circleTan.center)

   return circleList


# ============================================================================
# circleFromLineLineCircleTanPts
# ============================================================================
def circleFromLineLineCircleTanPts(line1, pt1, line2, pt2, circle, pt3):
   """create a circle through three lines:
      tangency line1 (QadLine)
      line selection point1
      tangency line2 (QadLine)
      line selection point2
      circle of tangency (QadCircle object)
      circle selection point
   """
   circleList = []

   circleList.extend(solveCircleTangentTo2LinesAndCircle(line1, line2, circle, -1, -1))
   circleList.extend(solveCircleTangentTo2LinesAndCircle(line1, line2, circle, -1,  1))
   circleList.extend(solveCircleTangentTo2LinesAndCircle(line1, line2, circle,  1, -1))
   circleList.extend(solveCircleTangentTo2LinesAndCircle(line1, line2, circle,  1,  1))

   if len(circleList) == 0:
      return None

   result = QadCircle()
   AvgList = []
   Avg = sys.float_info.max
   for circleTan in circleList:
      del AvgList[:] # I empty the list

      ptInt = qad_utils.getPerpendicularPointOnInfinityLine(line1.getStartPt(), line1.getEndPt(), circleTan.center)
      AvgList.append(ptInt.distance(pt1))

      ptInt = qad_utils.getPerpendicularPointOnInfinityLine(line2.getStartPt(), line2.getEndPt(), circleTan.center)
      AvgList.append(ptInt.distance(pt2))

      angle = qad_utils.getAngleBy2Pts(circleTan.center, circle.center)
      if circleTan.center.distance(circle.center) < circle.radius: # inner circle
         angle = angle + math.pi / 2
      ptInt = qad_utils.getPolarPointByPtAngle(circleTan.center, angle, circleTan.radius)
      AvgList.append(ptInt.distance(pt3))

      currAvg = qad_utils.numericListAvg(AvgList)
      if currAvg < Avg: # closer on average
         Avg = currAvg
         result.center = circleTan.center
         result.radius = circleTan.radius

   return True


# ============================================================================
# circleFrom3TanPts
# ============================================================================
def circleFrom3TanPts(geom1, pt1, geom2, pt2, geom3, pt3):
   """creates a circle through three tangent objects for the ends of the diameter:
      tangent geometry 1 (line, arc or circle)
      geometry selection point 1
      tangent geometry 2 (line, arc or circle)
      geometry selection point 2
   """
   obj1Type = geom1.whatIs()
   obj2Type = geom2.whatIs()
   obj3Type = geom3.whatIs()

   if (obj1Type != "LINE" and obj1Type != "ARC" and obj1Type != "CIRCLE") or \
      (obj2Type != "LINE" and obj2Type != "ARC" and obj2Type != "CIRCLE") or \
      (obj3Type != "LINE" and obj3Type != "ARC" and obj3Type != "CIRCLE"):
      return None

   if obj1Type == "ARC": # if it is an arc I transform it into a circle
      obj1 = QadCircle().set(geom1.center, geom1.radius)
      obj1Type = "CIRCLE"
   else:
      obj1 = geom1

   if obj2Type == "ARC": # if it is an arc I transform it into a circle
      obj2 = QadCircle().set(geom2.center, geom2.radius)
      obj2Type = "CIRCLE"
   else:
      obj2 = geom2

   if obj3Type == "ARC": # if it is an arc I transform it into a circle
      obj3 = QadCircle().set(geom3.center, geom3.radius)
      obj3Type = "CIRCLE"
   else:
      obj3 = geom3

   if obj1Type == "LINE":
      if obj2Type == "LINE":
         if obj3Type == "LINE":
            return circleFromLineLineLineTanPts(obj1, pt1, obj2, pt2, obj3, pt3)
         elif obj3Type == "CIRCLE":
            return circleFromLineLineCircleTanPts(obj1, pt1, obj2, pt2, obj3, pt3)
      elif obj2Type == "CIRCLE":
         if obj3Type == "LINE":
            return circleFromLineLineCircleTanPts(obj1, pt1, obj3, pt3, obj2, pt2)
         elif obj3Type == "CIRCLE":
            return circleFromLineCircleCircleTanPts(obj1, pt1, obj2, pt2, obj3, pt3)
   elif obj1Type == "CIRCLE":
      if obj2Type == "LINE":
         if obj3Type == "LINE":
            return circleFromLineLineCircleTanPts(obj2, pt2, obj3, pt3, obj1, pt1)
         elif obj3Type == "CIRCLE":
            return circleFromLineCircleCircleTanPts(obj2, pt2, obj1, pt1, obj3, pt3)
      elif obj2Type == "CIRCLE":
         if obj3Type == "LINE":
            return circleFromLineCircleCircleTanPts(obj3, pt3, obj1, pt1, obj2, pt2)
         elif obj3Type == "CIRCLE":
            return circleFromCircleCircleCircleTanPts(obj1, pt1, obj2, pt2, obj3, pt3)

   return None


# ============================================================================
# circleFromLineLineLineTanPts
# ============================================================================
def circleFromLineLineLineTanPts(line1, pt1, line2, pt2, line3, pt3):
   """Create a circle through three lines:
      tangency line1 (QadLine)
      line selection point1
      tangency line2 (QadLine)
      line selection point2
      tangency line3 (QadLine)
      line selection point3
   """
   circleList = []

   # Intersection points of the lines (line1, line2, line3)
   ptInt1 = QadIntersections.twoInfinityLines(line1, line2)
   ptInt2 = QadIntersections.twoInfinityLines(line2, line3)
   ptInt3 = QadIntersections.twoInfinityLines(line3, line1)

   # three parallel lines
   if (ptInt1 is None) and (ptInt2 is None):
      return circleList

   if (ptInt1 is None): # line1 and line2 are parallel
      circleList.extend(circleFrom2ParLinesLineTanPts(line1, line2, line3))
   elif (ptInt2 is None): # line2 and line3 are parallel
      circleList.extend(circleFrom2ParLinesLineTanPts(line2, line3, line1))
   elif (ptInt3 is None): # line3 and line1 are parallel
      circleList.extend(circleFrom2ParLinesLineTanPts(line3, line1, line2))
   else:
      # Bisectors of the internal angles of the triangle having as vertices the points of intersection of the lines
      Bisector123 = qad_utils.getBisectorInfinityLine(ptInt1, ptInt2, ptInt3)
      Bisector231 = qad_utils.getBisectorInfinityLine(ptInt2, ptInt3, ptInt1)
      Bisector312 = qad_utils.getBisectorInfinityLine(ptInt3, ptInt1, ptInt2)
      # Point of intersection of the bisectors = center of the circumference inscribed in the triangle
      l1 = QadLine().set(Bisector123[0], Bisector123[1])
      l2 = QadLine().set(Bisector231[0], Bisector231[1])
      center = QadIntersections.twoInfinityLines(l1, l2)

      # Perpendicular to the straight lines line1 passing through the center of the inscribed circle
      ptPer = QadPerpendicularity.fromPointToInfinityLine(center, line1)
      radius = center.distance(ptPer)
      circle = QadCircle()
      circle.set(center, radius)
      circleList.append(circle)

      # Bisettrici degli angoli esterni del triangolo
      angle = qad_utils.getAngleBy2Pts(Bisector123[0], Bisector123[1]) + math.pi / 2
      Bisector123 = QadLine().set(ptInt2, qad_utils.getPolarPointByPtAngle(ptInt2, angle, 10))

      angle = qad_utils.getAngleBy2Pts(Bisector231[0], Bisector231[1]) + math.pi / 2
      Bisector231 = QadLine().set(ptInt3, qad_utils.getPolarPointByPtAngle(ptInt3, angle, 10))

      angle = qad_utils.getAngleBy2Pts(Bisector312[0], Bisector312[1]) + math.pi / 2
      Bisector312 = QadLine().set(ptInt1, qad_utils.getPolarPointByPtAngle(ptInt1, angle, 10))

      # Points of intersection of the bisectors = center of the ex-inscribed circles
      center = QadIntersections.twoInfinityLines(Bisector123, Bisector231)
      l = QadLine().set(ptInt2, ptInt3)
      ptPer = QadPerpendicularity.fromPointToInfinityLine(center, l)
      radius = center.distance(ptPer)
      circle = QadCircle()
      circle.set(center, radius)
      circleList.append(circle)

      center = QadIntersections.twoInfinityLines(Bisector231, Bisector312)
      l.set(ptInt3, ptInt1)
      ptPer = QadPerpendicularity.fromPointToInfinityLine(center, l)
      radius = center.distance(ptPer)
      circle = QadCircle()
      circle.set(center, radius)
      circleList.append(circle)

      center = QadIntersections.twoInfinityLines(Bisector312, Bisector123)
      l.set(ptInt1, ptInt2)
      ptPer = QadPerpendicularity.fromPointToInfinityLine(center, l)
      radius = center.distance(ptPer)
      circle = QadCircle()
      circle.set(center, radius)
      circleList.append(circle)

   if len(circleList) == 0:
      return None

   result = QadCircle()
   AvgList = []
   Avg = sys.float_info.max
   for circleTan in circleList:
      del AvgList[:] # I empty the list

      ptInt = QadPerpendicularity.fromPointToInfinityLine(circleTan.center, line1)
      AvgList.append(ptInt.distance(pt1))

      ptInt = QadPerpendicularity.fromPointToInfinityLine(circleTan.center, line2)
      AvgList.append(ptInt.distance(pt2))

      ptInt = QadPerpendicularity.fromPointToInfinityLine(circleTan.center, line3)
      AvgList.append(ptInt.distance(pt3))

      currAvg = qad_utils.numericListAvg(AvgList)
      if currAvg < Avg: # closer on average
         Avg = currAvg
         result.center = circleTan.center
         result.radius = circleTan.radius

   return result


# ===========================================================================
# circleFrom2ParLinesLineTanPts
# ===========================================================================
def circleFrom2ParLinesLineTanPts(parLine1, parLine2, line3):
   """Create two circles through 2 parallel lines and a third non-parallel line:
      tangent line1 (QadLine) parallel to line2
      tangent line2 (QadLine) parallel to line1
      tangency line3 (QadLine)
   """
   circleList = []

   ptInt2 = QadIntersections.twoInfinityLines(parLine2, line3)
   ptInt3 = QadIntersections.twoInfinityLines(line3, parLine1)

   if parLine1.getStartPt() == ptInt3:
      pt = parLine1.getEndPt()
   else:
      pt = parLine1.getStartPt()
   Bisector123 = qad_utils.getBisectorInfinityLine(pt, ptInt2, ptInt3)

   if parLine2.getStartPt() == ptInt2:
      pt = parLine2.getEndPt()
   else:
      pt = parLine2.getStartPt()
   Bisector312 = qad_utils.getBisectorInfinityLine(pt, ptInt3, ptInt2)

   # Point of intersection of the bisectors = center of the circle
   center = qad_utils.getIntersectionPointOn2InfinityLines(Bisector123[0], Bisector123[1], \
                                                           Bisector312[0], Bisector312[1])
   ptPer = QadPerpendicularity.fromPointToInfinityLine(center, parLine1)
   radius = center.distance(ptPer)
   circle = QadCircle()
   circle.set(center, radius)
   circleList.append(circle)

   # Bisettrici degli angoli esterni
   Bisector123 = Bisector123 + math.pi / 2
   Bisector312 = Bisector312 + math.pi / 2
   # Point of intersection of the bisectors = center of the circle
   center = qad_utils.getIntersectionPointOn2InfinityLines(Bisector123[0], Bisector123[1], \
                                                           Bisector312[0], Bisector312[1])
   ptPer = QadPerpendicularity.fromPointToInfinityLine(center, parLine1)
   radius = center.distance(ptPer)
   circle = QadCircle()
   circle.set(center, radius)
   circleList.append(circle)

   return circleList


# ============================================================================
# circleFromLineCircleCircleTanPts
# ============================================================================
def circleFromLineCircleCircleTanPts(line, pt, circle1, pt1, circle2, pt2):
   """sets the characteristics of the circle through three lines:
      tangency line (QadLine)
      line selection point
      circle1 of tangency (QadCircle object)
      circle selection point1
      circle2 of tangency (QadCircle object)
      circle selection point2
   """
   circleList = []

   circleList.extend(solveCircleTangentToLineAnd2Circles(line, circle1, circle2, -1, -1))
   circleList.extend(solveCircleTangentToLineAnd2Circles(line, circle1, circle2, -1,  1))
   circleList.extend(solveCircleTangentToLineAnd2Circles(line, circle1, circle2,  1, -1))
   circleList.extend(solveCircleTangentToLineAnd2Circles(line, circle1, circle2,  1,  1))

   if len(circleList) == 0:
      return None

   result = QadCircle()
   AvgList = []
   Avg = sys.float_info.max
   for circleTan in circleList:
      del AvgList[:] # I empty the list

      ptInt = QadPerpendicularity.fromPointToInfinityLine(circleTan.center, line)
      AvgList.append(ptInt.distance(t))

      angle = qad_utils.getAngleBy2Pts(circleTan.center, circle1.center)
      if circleTan.center.distance(circle1.center) < circle1.radius: # inner circle
         angle = angle + math.pi / 2
      ptInt = qad_utils.getPolarPointByPtAngle(circleTan.center, angle, circleTan.radius)
      AvgList.append(ptInt.distance(pt1))

      angle = qad_utils.getAngleBy2Pts(circleTan.center, circle2.center)
      if circleTan.center.distance(circle2.center) < circle2.radius: # inner circle
         angle = angle + math.pi / 2
      ptInt = qad_utils.getPolarPointByPtAngle(circleTan.center, angle, circleTan.radius)
      AvgList.append(ptInt.distance(pt2))

      currAvg = qad_utils.numericListAvg(AvgList)
      if currAvg < Avg: # closer on average
         Avg = currAvg
         result.center = circleTan.center
         result.radius = circleTan.radius

   return result


# ============================================================================
# circleFromCircleCircleCircleTanPts
# ============================================================================
def circleFromCircleCircleCircleTanPts(circle1, pt1, circle2, pt2, circle3, pt3):
   """Create a circle through three tangent circles:
      circle1 of tangency (QadCircle object)
      circle selection point1
      circle2 of tangency (QadCircle object)
      circle selection point2
      circle3 of tangency (QadCircle object)
      circle selection point3
   """
   circleList = []
   circle = solveApollonius(circle1, circle2, circle3, -1, -1, -1)
   if circle is not None:
      circleList.append(circle)
   circle = solveApollonius(circle1, circle2, circle3, -1, -1,  1)
   if circle is not None:
      circleList.append(circle)
   circle = solveApollonius(circle1, circle2, circle3, -1,  1, -1)
   if circle is not None:
      circleList.append(circle)
   circle = solveApollonius(circle1, circle2, circle3, -1,  1,  1)
   if circle is not None:
      circleList.append(circle)
   circle = solveApollonius(circle1, circle2, circle3,  1, -1, -1)
   if circle is not None:
      circleList.append(circle)
   circle = solveApollonius(circle1, circle2, circle3,  1, -1,  1)
   if circle is not None:
      circleList.append(circle)
   circle = solveApollonius(circle1, circle2, circle3,  1,  1, -1)
   if circle is not None:
      circleList.append(circle)
   circle = solveApollonius(circle1, circle2, circle3,  1,  1,  1)
   if circle is not None:
      circleList.append(circle)

   if len(circleList) == 0:
      return None

   result = QadCircle()
   AvgList = []
   Avg = sys.float_info.max
   for circleTan in circleList:
      del AvgList[:] # I empty the list

      angle = qad_utils.getAngleBy2Pts(circleTan.center, circle1.center)
      if circleTan.center.distance(circle1.center) < circle1.radius: # inner circle
         angle = angle + math.pi / 2
      ptInt = qad_utils.getPolarPointByPtAngle(circleTan.center, angle, circleTan.radius)
      AvgList.append(ptInt.distance(pt1))

      angle = qad_utils.getAngleBy2Pts(circleTan.center, circle2.center)
      if circleTan.center.distance(circle2.center) < circle2.radius: # inner circle
         angle = angle + math.pi / 2
      ptInt = qad_utils.getPolarPointByPtAngle(circleTan.center, angle, circleTan.radius)
      AvgList.append(ptInt.distance(pt2))

      angle = qad_utils.getAngleBy2Pts(circleTan.center, circle3.center)
      if circleTan.center.distance(circle3.center) < circle3.radius: # inner circle
         angle = angle + math.pi / 2
      ptInt = qad_utils.getPolarPointByPtAngle(circleTan.center, angle, circleTan.radius)
      AvgList.append(ptInt.distance(pt3))

      currAvg = qad_utils.numericListAvg(AvgList)
      if currAvg < Avg: # closer on average
         Avg = currAvg
         result.center = circleTan.center
         result.radius = circleTan.radius

   return result


# ===========================================================================
# circleFrom1IntPtLineCircleTanPts
# ===========================================================================
def circleFrom1IntPtLineCircleTanPts(pt, line1, pt1, circle2, pt2, AllCircles = False):
   """create one or more circles (see AllCircles) through 1 intersection point, 1 tangent line and 1 circle:
      intersection point
      tangency line (QadLine)
      line selection point
      circle of tangency (QadLine)
      circle selection point
      the AllCircles parameter if = True returns all the circles and they are not the one closest to pt1 and pt2
   """
   # http://www.batmath.it/matematica/a_apollonio/prc.htm
   circleList = []

   # A circle circle2, a point pt and a straight line1 are given on the assumption that pt
   # is not on line1 or on the circle.
   # We want to find the circles passing through the point and tangent to the straight line and the given circle.
   # The problem can be easily solved using an inversion of any center pt and radius.
   # Once the inverse circumferences of the given straight line and the given circle have been found, their common tangents are found.
   # The inverses of these common tangents are the circles sought.

   if line1.getYOnInfinityLine(pt.x()) == pt.y() or \
      qad_utils.getDistance(pt, circle2.center) == circle2.radius:
      if AllCircles == True:
         return circleList
      else:
         return None

   c = QadCircle()
   c.set(pt, 10)

   circularInvLine = getCircularInversionOfLine(c, line1)
   circularInvCircle = getCircularInversionOfCircle(c, circle2)
   tangents = QadTangency.twoCircles(circularInvCircle, circularInvLine)
   for tangent in tangents:
      circleList.append(getCircularInversionOfLine(c, tangent))

   if AllCircles == True:
      return circleList

   if len(circleList) == 0:
      return None

   result = QadCircle()
   AvgList = []
   Avg = sys.float_info.max
   for circleTan in circleList:
      del AvgList[:] # I empty the list

      ptInt = QadPerpendicularity.fromPointToInfinityLine(circleTan.center, line1)
      AvgList.append(qad_utils.getDistance(ptInt, pt1))

      angle = qad_utils.getAngleBy2Pts(circleTan.center, circle2.center)
      if qad_utils.getDistance(circleTan.center, circle2.center) < circle2.radius: # inner circle
         angle = angle + math.pi / 2
      ptInt = qad_utils.getPolarPointByPtAngle(circleTan.center, angle, circleTan.radius)
      AvgList.append(qad_utils.getDistance(ptInt, pt2))

      currAvg = qad_utils.numericListAvg(AvgList)
      if currAvg < Avg: # closer on average
         Avg = currAvg
         result.center = circleTan.center
         result.radius = circleTan.radius

   return result


# ===========================================================================
# circleFrom1IntPtCircleCircleTanPts
# ===========================================================================
def circleFrom1IntPtCircleCircleTanPts(pt, circle1, pt1, circle2, pt2):
   """Create circles through 1 intersection point, 2 tangent circles:
      intersection point
      circle1 of tangency (QadCircle object)
      circle selection point1
      circle2 of tangency (QadCircle object)
      circle selection point2
   """
   # http://www.batmath.it/matematica/a_apollonio/prc.htm
   circleList = []

   # A point pt and two circles circle1 and circle2 are given;
   # the circles passing through pt and tangent to the two circles must be determined.
   # We propose a construction that uses inversion, as it seems the most elegant to us.
   # In reality one could also make a construction using the homothety centers of the two given circles
   # but, in essence, it is just a way to disguise the use of inversion.
   # An inversion circle with center pt and any radius is considered.
   # The inverse circles of the two given circles and their common tangents are determined.
   # The inverse circles of these common tangents are those that satisfy the problem.

   c = QadCircle()
   c.set(pt, 10)

   circularInvCircle1 = getCircularInversionOfCircle(c, circle1)
   circularInvCircle2 = getCircularInversionOfCircle(c, circle2)
   tangents = QadTangency.twoCircles(circularInvCircle1, circularInvCircle2)
   for tangent in tangents:
      circleList.append(getCircularInversionOfLine(c, tangent))

   if len(circleList) == 0:
      return None

   result = QadCircle()
   AvgList = []
   Avg = sys.float_info.max
   for circleTan in circleList:
      del AvgList[:] # I empty the list

      angle = qad_utils.getAngleBy2Pts(circleTan.center, circle1.center)
      if qad_utils.getDistance(circleTan.center, circle1.center) < circle1.radius: # inner circle
         angle = angle + math.pi / 2
      ptInt = qad_utils.getPolarPointByPtAngle(circleTan.center, angle, circleTan.radius)
      AvgList.append(qad_utils.getDistance(ptInt, pt1))

      angle = qad_utils.getAngleBy2Pts(circleTan.center, circle2.center)
      if qad_utils.getDistance(circleTan.center, circle2.center) < circle2.radius: # inner circle
         angle = angle + math.pi / 2
      ptInt = qad_utils.getPolarPointByPtAngle(circleTan.center, angle, circleTan.radius)
      AvgList.append(qad_utils.getDistance(ptInt, pt2))

      currAvg = qad_utils.numericListAvg(AvgList)
      if currAvg < Avg: # closer on average
         Avg = currAvg
         result.center = circleTan.center
         result.radius = circleTan.radius

   return result


# ============================================================================
# circleFromDiamEndsPtTanPt
# ============================================================================
def circleFromDiamEndsPtTanPt(startPt, geom, pt):
   """Create a circle through an end point of diameter e
      a tangent object for the other end:
      starting point
      tangent geometry 1 (line, arc or circle)
      geometry selection point 1
   """
   objype = geom.whatIs()

   if (objType != "LINE" and objType != "ARC" and objType != "CIRCLE"): return None

   if objType == "ARC": # if it is an arc I transform it into a circle
      obj = QadCircle().set(geom.center, geom.radius)
      objType = "CIRCLE"
   else:
      obj = geom

   if objType == "LINE":
      ptPer = QadPerpendicularity.fromPointToInfinityLine(startPt, obj)
      return QadCircle().fromDiamEnds(startPt, ptPer)
   elif objType == "CIRCLE":
      l = QadLine().set(startPt, obj.center)
      intPts = QadIntersections.infinityLineWithCircle(l, obj)
      # I choose the point closest to the pt point
      ptTan = qad_utils.getNearestPoints(pt, ptIntList)[0]
      return QadCircle().fromDiamEnds(startPt, ptTan)


# ============================================================================
# circleFromDiamEnds2TanPts
# ============================================================================
def circleFromDiamEnds2TanPts(geom1, pt1, geom2, pt2):
   """I create a circle through two tangent objects for the ends of the diameter:
      tangency geometry1 (line, arc or circle)
      geometry selection point1
      tangency geometry2 (line, arc or circle)
      geometry selection point2
   """
   obj1Type = geom1.whatIs()
   obj2Type = geom2.whatIs()

   if (obj1Type != "LINE" and obj1Type != "ARC" and obj1Type != "CIRCLE") or \
      (obj2Type != "LINE" and obj2Type != "ARC" and obj2Type != "CIRCLE"):
      return None

   if obj1Type == "ARC": # if it is an arc I transform it into a circle
      obj1 = QadCircle().set(geom1.center, geom1.radius)
      obj1Type = "CIRCLE"
   else:
      obj1 = geom1

   if obj2Type == "ARC": # if it is an arc I transform it into a circle
      obj2 = QadCircle().set(geom2.center, geom2.radius)
      obj2Type = "CIRCLE"
   else:
      obj2 = geom2

   if obj1Type == "LINE":
      if obj2Type == "LINE":
         return None # The diameter cannot be tangent to two lines
      elif obj2Type == "CIRCLE":
         return circleFromLineCircleTanPts(obj1, obj2, pt2)
   elif obj1Type == "CIRCLE":
      if obj2Type == "LINE":
         return circleFromLineCircleTanPts(obj2, obj1, pt1)
      elif obj2Type == "CIRCLE":
         return circleFromCircleCircleTanPts(obj1, pt1, obj2, pt2)

   return None


# ============================================================================
# circleFromLineCircleTanPts
# ============================================================================
def circleFromLineCircleTanPts(line, circle, ptCircle):
   """I create a circle through a line, a circle of tangency:
      tangency line (QadLine)
      circle of tangency (QadCircle object)
      circle selection point
   """
   ptPer = QadPerpendicularity.fromPointToInfinityLine(circle.center, line)
   tanPoints = []
   tanPoints.append(qad_utils.getPolarPointBy2Pts(circle.center, ptPer, circle.radius))
   tanPoints.append(qad_utils.getPolarPointBy2Pts(circle.center, ptPer, -circle.radius))
   # I choose the point closest to the pt point
   ptTan = qad_utils.getNearestPoints(ptCircle, tanPoints)[0]
   return QadCircle().fromDiamEnds(ptPer, ptTan)


# ============================================================================
# circleFromCircleCircleTanPts
# ============================================================================
def circleFromCircleCircleTanPts(circle1, pt1, circle2, pt2):
   """Create a circle through two circles of tangency:
      circle1 of tangency (QadCircle object)
      circle selection point1
      circle2 of tangency (QadCircle object)
      circle selection point2
   """
   l = QadLine().set(circle1.center, circle2.center)
   ptIntList = QadIntersections.infinityLineWithCircle(l, circle1)
   # I choose the point closest to the point pt1
   ptTan1 = qad_utils.getNearestPoints(pt1, ptIntList)[0]

   ptIntList = QadIntersections.infinityLineWithCircle(l, circle2)
   # I choose the point closest to point pt2
   ptTan2 = qad_utils.getNearestPoints(pt2, ptIntList)[0]

   return QadCircle().fromDiamEnds(ptTan1, ptTan2)


# ============================================================================
# circleFrom2TanPtsRadius
# ============================================================================
def circleFrom2TanPtsRadius(geom1, pt1, geom2, pt2, radius):
   """Create a circle through 2 tangent objects and a radius:
      tangency geometry1 (line, arc or circle)
      geometry selection point1
      tangency object2 (line, arc or circle)
      geometry selection point2
      radius
   """
   obj1Type = geom1.whatIs()
   obj2Type = geom2.whatIs()

   if (obj1Type != "LINE" and obj1Type != "ARC" and obj1Type != "CIRCLE") or \
      (obj2Type != "LINE" and obj2Type != "ARC" and obj2Type != "CIRCLE"):
      return False

   if obj1Type == "ARC": # if it is an arc I transform it into a circle
      obj1 = QadCircle().set(geom1.center, geom1.radius)
      obj1Type = "CIRCLE"
   else:
      obj1 = geom1

   if obj2Type == "ARC": # if it is an arc I transform it into a circle
      obj2 = QadCircle().set(geom2.center, geom2.radius)
      obj2Type = "CIRCLE"
   else:
      obj2 = geom2

   if obj1Type == "LINE":
      if obj2Type == "LINE":
         return circleFromLineLineTanPtsRadius(obj1, pt1, obj2, pt2, radius)
      elif obj2Type == "CIRCLE":
         return circleFromLineCircleTanPtsRadius(obj1, pt1, obj2, pt2, radius)
   elif obj1Type == "CIRCLE":
      if obj2Type == "LINE":
         return circleFromLineCircleTanPtsRadius(obj2, pt2, obj1, pt1, radius)
      elif obj2Type == "CIRCLE":
         return circleFromCircleCircleTanPtsRadius(obj1, pt1, obj2, pt2, radius)

   return None


# ============================================================================
# circleFromLineLineTanPtsRadius
# ============================================================================
def circleFromLineLineTanPtsRadius(line1, pt1, line2, pt2, radius):
   """Create a circle through two tangent lines and a radius:
      tangency line1 (QadLine)
      line selection point1
      tangency line2 (QadLine)
      line selection point2
      radius
   """
   # calculate the midpoint between the two selection points
   ptMiddle = qad_utils.getMiddlePoint(pt1, pt2)

   # check if the lines are parallel
   ptInt = QadIntersections.twoInfinityLines(line1, line2)
   if ptInt is None: # the lines are parallel
      ptPer = QadPerpendicularity.fromPointToInfinityLine(ptMiddle, line1)
      if qad_utils.doubleNear(radius, qad_utils.getDistance(ptPer, ptMiddle)):
         return QadCircle().set(ptMiddle, radius)
      else:
         return None

   # line angle1
   angle = qad_utils.getAngleBy2Pts(line1.getStartPt(), line1.getEndPt())
   # straight line parallel to one side of the line1 distant radius
   angle = angle + math.pi / 2
   pt1Par1Line1 = qad_utils.getPolarPointByPtAngle(line1.getStartPt(), angle, radius)
   pt2Par1Line1 = qad_utils.getPolarPointByPtAngle(line1.getEndPt(), angle, radius)
   # parallel line on the other side of line1 at distance radius
   angle = angle - math.pi
   pt1Par2Line1 = qad_utils.getPolarPointByPtAngle(line1.getStartPt(), angle, radius)
   pt2Par2Line1 = qad_utils.getPolarPointByPtAngle(line1.getEndPt(), angle, radius)

   # line angle2
   angle = qad_utils.getAngleBy2Pts(line2.getStartPt(), line2.getEndPt())
   # straight line parallel to one side of the line2 distant radius
   angle = angle + math.pi / 2
   pt1Par1Line2 = qad_utils.getPolarPointByPtAngle(line2.getStartPt(), angle, radius)
   pt2Par1Line2 = qad_utils.getPolarPointByPtAngle(line2.getEndPt(), angle, radius)
   # parallel line on the other side of line2 at distance radius
   angle = angle - math.pi
   pt1Par2Line2 = qad_utils.getPolarPointByPtAngle(line2.getStartPt(), angle, radius)
   pt2Par2Line2 = qad_utils.getPolarPointByPtAngle(line2.getEndPt(), angle, radius)

   # calculate the intersections
   ptIntList = []
   ptInt = qad_utils.getIntersectionPointOn2InfinityLines(pt1Par1Line1, pt2Par1Line1, \
                                                          pt1Par1Line2, pt2Par1Line2)
   ptIntList.append(ptInt)

   ptInt = qad_utils.getIntersectionPointOn2InfinityLines(pt1Par1Line1, pt2Par1Line1, \
                                                          pt1Par2Line2, pt2Par2Line2)
   ptIntList.append(ptInt)

   ptInt = qad_utils.getIntersectionPointOn2InfinityLines(pt1Par2Line1, pt2Par2Line1, \
                                                          pt1Par1Line2, pt2Par1Line2)
   ptIntList.append(ptInt)

   ptInt = qad_utils.getIntersectionPointOn2InfinityLines(pt1Par2Line1, pt2Par2Line1, \
                                                          pt1Par2Line2, pt2Par2Line2)
   ptIntList.append(ptInt)

   # I choose the point closest to the midpoint
   center = qad_utils.getNearestPoints(ptMiddle, ptIntList)[0]
   return QadCircle().set(center, radius)


# ============================================================================
# circleFromLineCircleTanPtsRadius
# ============================================================================
def circleFromLineCircleTanPtsRadius(line, ptLine, circle, ptCircle, radius):
   """Create a circle through a line, a circle of tangency and a radius:
      tangency line (QadLine)
      line selection point
      circle of tangency (QadCircle object)
      circle selection point
      radius
   """
   # calculate the midpoint between the two selection points
   ptMiddle = qad_utils.getMiddlePoint(ptLine, ptCircle)

   # line angle1
   angle = qad_utils.getAngleBy2Pts(line.getStartPt(), line.getEndPt())
   # straight line parallel to one side of the line1 distant radius
   angle = angle + math.pi / 2
   pt1Par1Line = qad_utils.getPolarPointByPtAngle(line.getStartPt(), angle, radius)
   pt2Par1Line = qad_utils.getPolarPointByPtAngle(line.getEndPt(), angle, radius)
   # parallel line on the other side of line1 at distance radius
   angle = angle - math.pi
   pt1Par2Line = qad_utils.getPolarPointByPtAngle(line.getStartPt(), angle, radius)
   pt2Par2Line = qad_utils.getPolarPointByPtAngle(line.getEndPt(), angle, radius)

   # create a circle with a larger radius
   circleTan = QadCircle()
   circleTan.set(circle.center, circle.radius + radius)

   l = QadLine().set(pt1Par1Line, pt2Par1Line)
   ptIntList = QadIntersections.infinityLineWithCircle(l, circleTan)

   l.set(pt1Par2Line, pt2Par2Line)
   ptIntList2 = QadIntersections.infinityLineWithCircle(l, circleTan)

   ptIntList.extend(ptIntList2)

   if len(ptIntList) == 0: # no intersection
      return None

   # I choose the point closest to the midpoint
   center = qad_utils.getNearestPoints(ptMiddle, ptIntList)[0]
   return QadCircle().set(center, radius)


# ============================================================================
# circleFromCircleCircleTanPtsRadius
# ============================================================================
def circleFromCircleCircleTanPtsRadius(circle1, pt1, circle2, pt2, radius):
   """Create a circle through two circles of tangency and a radius:
      circle1 of tangency (QadCircle object)
      circle selection point1
      circle2 of tangency (QadCircle object)
      circle selection point2
      radius
   """
   # calculate the midpoint between the two selection points
   ptMiddle = qad_utils.getMiddlePoint(pt1, pt2)

   # create two circles with a larger radius
   circle1Tan = QadCircle()
   circle1Tan.set(circle1.center, circle1.radius + radius)
   circle2Tan = QadCircle()
   circle2Tan.set(circle2.center, circle2.radius + radius)
   ptIntList = QadIntersections.twoCircles(circle1Tan, circle2Tan)

   if len(ptIntList) == 0: # no intersection
      return None

   # I choose the point closest to the midpoint
   center = qad_utils.getNearestPoints(ptMiddle, ptIntList)[0]
   return QadCircle().set(center, radius)


# ===============================================================================
# solveCircleTangentToLineAnd2Circles
# ===============================================================================
def solveCircleTangentToLineAnd2Circles(line, circle1, circle2, s1, s2):
   """Find the two circles tangent to a straight line and two circles (that would be 8 circles that lie with the
      4 combinations of s1, s2 that take on the value -1 or 1)
      and returns the one closest to pt
   """
   # http://www.batmath.it/matematica/a_apollonio/rcc.htm

   # The simplest way to solve this problem is to use a particular
   # geometric transformation, which some call parallel dilation: it is imagined that the radius r
   # of the smallest of the circles in question is reduced to zero (the circle is reduced to its center),
   # while the lines (resp. the other circles) remain parallel (resp. concentric) with distances
   # from the center of the circle which has been reduced to zero (respectively with radiuses of the circles) increased or
   # diminuiti di r.
   # If we apply this transformation to our case, reducing the radius of the smallest circle to zero
   # (or one of the two if they have the same radius) we will end up with a point, a circle and a straight line:
   # find the circles passing through the point and tangent to the line and the circle (in the already known way)
   # we can apply the inverse transformation of the previous parallel dilation to determine
   # the required circumferences.
   if circle1.radius <= circle2.radius:
      smallerCircle = circle1
      greaterCircle = circle2
   else:
      smallerCircle = circle2
      greaterCircle = circle1

   linePar = []
   angle = qad_utils.getAngleBy2Pts(line[0], line[1])
   linePar.append(qad_utils.getPolarPointByPtAngle(line[0], angle + math.pi / 2, smallerCircle.radius * s1))
   linePar.append(qad_utils.getPolarPointByPtAngle(line[1], angle + math.pi / 2, smallerCircle.radius * s1))

   circlePar = QadCircle(greaterCircle)
   circlePar.radius = circlePar.radius + smallerCircle.radius * s1

   circleList = circleFrom1IntPtLineCircleTanPts(smallerCircle.center, linePar, None, circlePar, None, True)

   for circleTan in circleList:
      ptPerp = qad_utils.getPerpendicularPointOnInfinityLine(line[0], line[1], circleTan.center)
      circleTan.radius = qad_utils.getDistance(ptPerp, circleTan.center)

   return circleList


# ===============================================================================
# solveApollonius
# ===============================================================================
def solveApollonius(c1, c2, c3, s1, s2, s3):
   """>>> solveApollonius((0, 0, 1), (4, 0, 1), (2, 4, 2), 1,1,1)
      Circle(x=2.0, y=2.1, r=3.9)
      >>> solveApollonius((0, 0, 1), (4, 0, 1), (2, 4, 2), -1,-1,-1)
      Circle(x=2.0, y=0.8333333333333333, r=1.1666666666666667)
      Find the circle tangent to three circles (that would be 8 circles that are found with the
      8 combinations of s1, s2, s3 which take the value -1 or 1)
   """
   x1 = c1.center.x()
   y1 = c1.center.y()
   r1 = c1.radius
   x2 = c2.center.x()
   y2 = c2.center.y()
   r2 = c2.radius
   x3 = c3.center.x()
   y3 = c3.center.y()
   r3 = c3.radius

   v11 = 2*x2 - 2*x1
   v12 = 2*y2 - 2*y1
   v13 = x1*x1 - x2*x2 + y1*y1 - y2*y2 - r1*r1 + r2*r2
   v14 = 2*s2*r2 - 2*s1*r1

   v21 = 2*x3 - 2*x2
   v22 = 2*y3 - 2*y2
   v23 = x2*x2 - x3*x3 + y2*y2 - y3*y3 - r2*r2 + r3*r3
   v24 = 2*s3*r3 - 2*s2*r2

   if v11 == 0:
      return None

   w12 = v12/v11
   w13 = v13/v11
   w14 = v14/v11

   if v21 == 0:
      return None

   w22 = v22/v21-w12
   w23 = v23/v21-w13
   w24 = v24/v21-w14

   if w22 == 0:
      return None

   P = -w23/w22
   Q = w24/w22
   M = -w12*P-w13
   N = w14 - w12*Q

   a = N*N + Q*Q - 1
   b = 2*M*N - 2*N*x1 + 2*P*Q - 2*Q*y1 + 2*s1*r1
   c = x1*x1 + M*M - 2*M*x1 + P*P + y1*y1 - 2*P*y1 - r1*r1

   # Find a root of a quadratic equation. This requires the circle centers not to be e.g. colinear
   if a == 0:
      return None
   D = (b * b) - (4 * a * c)

   # if D is so close to zero
   if qad_utils.doubleNear(D, 0.0):
      D = 0
   elif D < 0: # you cannot take the square root of a negative number
      return None

   rs = (-b-math.sqrt(D))/(2*a)

   xs = M+N*rs
   ys = P+Q*rs

   center = QgsPointXY(xs, ys)
   circle = QadCircle().set(center, rs)
   return circle


# ===============================================================================
# getCircularInversionOfPoint
# ===============================================================================
def getCircularInversionOfPoint(circleRef, pt):
   """the function returns the circular inversion of a point"""
   dist = qad_utils.getDistance(circleRef.center, pt)
   angle = qad_utils.getAngleBy2Pts(circleRef.center, pt)
   circInvDist = circleRef.radius * circleRef.radius / dist
   return qad_utils.getPolarPointByPtAngle(circleRef.center, angle, circInvDist)


# ===============================================================================
# getCircularInversionOfLine
# ===============================================================================
def getCircularInversionOfLine(circleRef, line):
   """the function returns the circular inversion of a line (which is a circle)"""
   angleLine = qad_utils.getAngleBy2Pts(line.getStartPt(), line.getEndPt())
   ptNearestLine = QadPerpendicularity.fromPointToInfinityLine(circleRef.center, line)
   dist = qad_utils.getDistance(circleRef.center, ptNearestLine)

   pt1 = getCircularInversionOfPoint(circleRef, ptNearestLine)

   pt = qad_utils.getPolarPointByPtAngle(ptNearestLine, angleLine, dist)
   pt2 = getCircularInversionOfPoint(circleRef, pt)

   pt = qad_utils.getPolarPointByPtAngle(ptNearestLine, angleLine + math.pi, dist)
   pt3 = getCircularInversionOfPoint(circleRef, pt)

   return circleFrom3Pts(pt1, pt2, pt3)


# ===============================================================================
# getCircularInversionOfCircle
# ===============================================================================
def getCircularInversionOfCircle(circleRef, circle):
   """the function returns the circular inversion of a circle (which is a circle)"""

   angleLine = qad_utils.getAngleBy2Pts(circle.center, circleRef.center)
   ptNearestLine = qad_utils.getPolarPointByPtAngle(circle.center, angleLine, circle.radius)
   dist = qad_utils.getDistance(circleRef.center, circle.center)

   pt1 = getCircularInversionOfPoint(circleRef, ptNearestLine)

   pt = qad_utils.getPolarPointByPtAngle(circle.center, angleLine + math.pi / 2, circle.radius)
   pt2 = getCircularInversionOfPoint(circleRef, pt)

   pt = qad_utils.getPolarPointByPtAngle(circle.center, angleLine - math.pi / 2, circle.radius)
   pt3 = getCircularInversionOfPoint(circleRef, pt)

   return circleFrom3Pts(pt1, pt2, pt3)
