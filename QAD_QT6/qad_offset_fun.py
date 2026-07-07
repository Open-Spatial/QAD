# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 functions for offset operations

                              -------------------
        begin                : 2019-05-20
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
from .qad_join_fun import selfJoinPolyline
from .qad_arc import QadArc
from .qad_polyline import *
from .qad_variables import QadVariables


# ===============================================================================
# offsetQGSGeom
# ===============================================================================
def offsetQGSGeom(qgsGeom, offsetDistOrPoint, gapType, forcedOffsetDist = None):
   """the function offsets a QGIS geometry

      according to a distance or a point (from which to calculate the distance)
      - for polygons a positive value is towards the outside, negative is towards the inside
      - for lines a positive value is towards the left, negative is towards the right with respect to the direction of the line

       one way <gapType>:
      0 = Extends line segments to their projected intersections
      1 = Connect the line segments at their projected intersections.
          The radius of each arc segment is equal to the offset distance
      2 = Trims line segments at projected intersections.
          The perpendicular distance from each peak to its respective vertex
          on the original object is equal to the offset distance.

      if <offsetDistOrPoint> is a point and forcedDist <> None
      the distance is forced with this parameter (which must always be positive) while the offset side is taken from the point

      The function returns a list of qgis geometries as a result of the offset
   """
   if type(offsetDistOrPoint) == QgsPointXY:
      # returns a tuple (<The squared cartesian distance>,
      #                    <minDistPoint>
      #                    <afterVertex>
      #                    <leftOf>)
      dummy = qgsGeom.closestSegmentWithContext(offsetDistOrPoint)
      if dummy is None or dummy[0] <= 0:
         return []
      if forcedOffsetDist is None:
         offsetDist = math.sqrt(dummy[0])  # radice quadrata
      else:
         offsetDist = forcedOffsetDist

      if offsetDist == 0:
         return []

      leftOf = dummy[3]
      if qgsGeom.type() == QgsWkbTypes.LineGeometry:
         # if leftOf > 0 the point is to the right of the line then offsetDist must be negative
         if leftOf > 0:
            offsetDist = -offsetDist
      else:
         # if the point is inside the geometry offsetDist must be negative
         if QgsGeometry.fromPointXY(offsetDistOrPoint).within(qgsGeom) == True:
            offsetDist = -offsetDist
   else:
      offsetDist = offsetDistOrPoint

   atLeastNSegment = QadVariables.get(QadMsg.translate("Environment variables", "ARCMINSEGMENTQTY"), 12)
   if gapType == 0:
      joinStyle = Qgis.JoinStyle.Miter
   elif gapType == 1:
      joinStyle = Qgis.JoinStyle.Round
   elif gapType == 1:
      joinStyle = Qgis.JoinStyle.Bevel

   miterLimit= 20
   if qgsGeom.type() == QgsWkbTypes.LineGeometry:
      resultGeom = qgsGeom.offsetCurve(offsetDist, atLeastNSegment, joinStyle, miterLimit)
   else:
      capStyle = Qgis.EndCapStyle.Round
      resultGeom = qgsGeom.buffer(offsetDist, atLeastNSegment, capStyle, joinStyle, miterLimit)

   result = []
   if resultGeom is not None:
      for part in resultGeom.parts():
         result.append(QgsGeometry.fromWkt(part.asWkt())) # if add part directly then qgis stops

   return result


# ===============================================================================
# offsetPolyline
# ===============================================================================
def offsetPolyline(qadGeom, offsetDist, offsetSide, gapType):
   """the function offsets a QAD geometry
      according to a distance and an offset side ("right" or "left")
      and a <gapType> mode:
      0 = Extends line segments to their projected intersections
      1 = Connect the line segments at their projected intersections.
          The radius of each arc segment is equal to the offset distance
      2 = Trims line segments at projected intersections.
          The perpendicular distance from each peak to its respective vertex
          on the original object is equal to the offset distance.

      The function returns a list of geometries as a result of the offset
   """
   result = []

   linearObj = qadGeom.copy() # I'll make a copy
   gType = linearObj.whatIs()
   if gType == "CIRCLE":
      # if offsetSide = "right" means towards the outside of the circle
      # if offsetSide = "left" means towards the inside of the circle
      if offsetSide == "left":
         # offset towards the inside of the circle
         if linearObj.offset(offsetDist, "internal") == True: result.append(linearObj)
      else:
         # offset towards the outside of the circle
         if linearObj.offset(offsetDist, "external") == True: result.append(linearObj)
   elif gType == "ELLIPSE":
      # the offset of an ellipse is not an ellipse
      # if offsetSide = "right" means towards the outside of the ellipse
      # if offsetSide = "left" means towards the inside of the ellipse
      if offsetSide == "left":
         # offset towards the inside of the ellipse
         pts = linearObj.offset(offsetDist, "internal")
      else:
         # offset outward of the ellipse
         pts = linearObj.offset(offsetDist, "external")

      if pts is not None:
         polyline = QadPolyline()
         polyline.fromPolyline(pts)
         result.append(polyline)
   elif gType == "LINE" or gType == "ARC":
      if linearObj.offset(offsetDist, offsetSide) == True: result.append(linearObj)
   elif gType == "ELLIPSE_ARC":
      # the offset of an ellipse is not an ellipse
      pts = linearObj.offset(offsetDist, offsetSide)
      if pts is not None:
         polyline = QadPolyline()
         polyline.fromPolyline(pts)
         result.append(polyline)
   elif gType == "POLYLINE":
      # currently ellipse arcs in a polyline are not supported so I transform them into segments
      if linearObj.segmentizeEllipseArcs() == False:
         return []
      # I get the uncut offset polyline
      untrimmedOffsetPolyline = getUntrimmedOffSetPolyline(linearObj, offsetDist, offsetSide, gapType)
      # test
      #return [untrimmedOffsetPolyline]

      # I reverse the direction of the points to obtain the reversed uncut offset polyline
      reversedPolyline = linearObj.copy() # I duplicate the polyline
      reversedPolyline.reverse()
      untrimmedReversedOffsetPolyline = getUntrimmedOffSetPolyline(reversedPolyline, offsetDist, offsetSide, gapType)

      # test
      #return [untrimmedReversedOffsetPolyline]

      # I cut the polyline where necessary
      result = getTrimmedOffSetPolyline(linearObj, \
                                        untrimmedOffsetPolyline, \
                                        untrimmedReversedOffsetPolyline, \
                                        offsetDist)

   return result



# ===============================================================================
# dualClipping
# ===============================================================================
def dualClipping(polyline, untrimmedOffsetPolyline, untrimmedReversedOffsetPolyline, offsetDist):
   """the function performs dual clipping on untrimmedOffsetPolyline.
      <polyline>: list of the original parts of the polyline
      <untrimmedOffsetPolyline>: list of untrimmed parts derived from the offset
      <untrimmedReversedOffsetPolyline>: list of untrimmed parts derived from reverse offset

      The function returns a list of parts resulting from dual clipping
   """

   # start Dual Clipping

   # Calculate the intersection points between <untrimmedOffsetPolyline> and <untrimmedReversedOffsetPolyline>
   intPtList = getIntersectionPointsWithPolyline(untrimmedOffsetPolyline, untrimmedReversedOffsetPolyline)
   # Calculate the self intersection points of <untrimmedOffsetPolyline>
   intSelfPtList = getSelfIntersectionPoints(untrimmedOffsetPolyline)
   """
      The previous 2 functions return a list where each element is a sublist composed of:
      1) intersection point of the polyline with itself
      2) distance of the intersection point from the start of the polyline
      3) number of the part containing the intersection point
   """
   # add self intersection points to the list of intersection points without duplicating the points
   # using the coordinates of the point and the part number on which the point is located as a unique key
   lenOriginalIntPtList = len(intPtList)
   for intSelfPt in intSelfPtList:
      found = False
      for i in range(lenOriginalIntPtList):
         intPt = intPtList[i]
         # if the points are so close that they are considered equal and it is the same part
         if qad_utils.ptNear(intPt[0], intSelfPt[0]) == True and \
            intPt[2] == intSelfPt[2]:
            found = True

      if found == False:
         intPtList.append(intSelfPt)

   # if there are no intersection points or self intersection points
   if len(intPtList) == 0:
      return untrimmedOffsetPolyline.defList

   # I sort the intersection points by distance from the start of untrimmedOffsetPolyline
   intPtListOrderedByDistFromStart = []
   for intPt in intPtList:
      insertAt = 0
      for intPtOrderedByDistFromStart in intPtListOrderedByDistFromStart:
         if intPtOrderedByDistFromStart[1] < intPt[1]:
            insertAt = insertAt + 1
         else:
            break
      intPtListOrderedByDistFromStart.insert(insertAt, intPt)

   # I generate a new list with the parts with intersections divided into many subparts
   splittedPolyline = []
   for iPart in range(len(untrimmedOffsetPolyline.defList)):
      part = untrimmedOffsetPolyline.getLinearObjectAt(iPart)
      # check if the part has intersections
      subPartList = []
      for intPt in intPtListOrderedByDistFromStart:
         if (intPt[2] == iPart): # if the intersection refers to the affected part
            if len(subPartList) == 0: # first intersection for this part
               subPartList.append(part.getGeomBetween2Pts(part.getStartPt(), intPt[0]))
            else: # from the second intersection onward
               subPartList.append(part.getGeomBetween2Pts(lastIntPt[0], intPt[0]))
            lastIntPt = intPt
         else:
            if intPt[2] > iPart: # not continuous with the intersections of the subsequent parts
               break
      if len(subPartList) > 0: # if the part has been divided into sub-parts
         subPartList.append(part.getGeomBetween2Pts(lastIntPt[0], part.getEndPt()))
         splittedPolyline.extend(subPartList)
      else:
         splittedPolyline.append(part)

   # test
   #return splittedPolyline

   dualClippedPartList = []
   partListForClipByCircle = [] # list of parts that must be cut with a circle
   #nPenultimaParte = polyline.qty() - 2 # 0-indexed
   circle = QadCircle()

   # for all parts of splittedPolyline
   for part in splittedPolyline:
      # calculate the intersections of the part with all the parts of <polyline> (original polyline)
      dummyPolyline = QadPolyline()
      dummyPolyline.append(part)
      intPtList = getIntersectionPointsWithPolyline(polyline, dummyPolyline)
      # if there are no intersection points add this part to dualClippedPartList
      if len(intPtList) == 0:
         dualClippedPartList.append(part)
      else: # if intersection points exist
         # check if all the intersection points are not on the first segment or on the penultimate segment of <polyline>
         reject = True
         for intPt in intPtList:
            if intPt[2] == 0 or intPt[2] == polyline.qty() - 1: # if at least one intersection point is on the first or last segment
               reject = False
               break

         if reject == False:
            # I attach the parts of <part> that are external to all circles
            # with center = the intersection points and radius = the offset distance
            partListForClipByCircle = [part]
            for intPt in intPtList:
               # I construct a circle whose center is the intersection point and the radius is the offset distance
               circle.set(intPt[0], offsetDist)

               i = 0
               while i < len(partListForClipByCircle):
                  externalPartsOfIntPt = getPartsExternalToCircle(partListForClipByCircle[i], circle)
                  del partListForClipByCircle[i]
                  for externalPartOfIntPt in externalPartsOfIntPt.defList:
                     partListForClipByCircle.insert(i, externalPartOfIntPt)
                     i = i + 1

            for partForClipByCircle in partListForClipByCircle:
               dualClippedPartList.append(partForClipByCircle)

   return dualClippedPartList


# ===============================================================================
# generalClosedPointPairClipping
# ===============================================================================
def generalClosedPointPairClipping(polyline, dualClippedPolyline, offsetDist):
   """the function performs general closed point pair clipping on dualClippedPolyline.
      <polyline>: list of the original parts of the polyline
      <dualClippedPolyline>: list of parts resulting from dual clipping
      <offsetDist> offset distance

      For each part of the original polyline I look for the closest point for each
      part of dualClippedPolyline. If this point is closer than offsetDist then I do
      a circle with center point of the original polyline and delete the
      segment piece of dualClippedPolyline inside the circle. This is to eliminate the pieces of
      dualClippedPolyline closer than offsetDist to polyline.

      The function returns a list of parts resulting from general closed point pair clipping
   """
   # start of General Closed Point Pair clipping
   GCPPCList = QadPolyline(dualClippedPolyline) # I duplicate the parts list
   circle = QadCircle()

#    # for each part of polyline
#    for part in polyline.defList:
#       # for each part of GCPPCList
#       i = 0
#       while i < GCPPCList.qty():
#          GCPPCPart = GCPPCList.getLinearObjectAt(i)
#          # check which part point is closest to GCPPCPart
#          # the function returns <minimum distance><minimum distance point on object1><minimum distance point on object2>
#          MinDistancePts = QadMinDistance.fromTwoBasicGeomObjects(part, GCPPCPart)
#          # if the distance is less than offsetDist (and not so close as to be considered equal)
#          if qad_utils.doubleSmaller(MinDistancePts[0], offsetDist):
#             # create a circle at the part point closest to GCPPCPart
#             circle.set(MinDistancePts[1], offsetDist)
#             # I get the parts of GCPPCPart outside the circle
#             splittedParts = getPartsExternalToCircle(GCPPCPart, circle)
#             # if the splittedParts consists of only one part which is equal to GCPPCPart
#             # e.g. if GCPPCPart is tangent to the circle then I don't do anything
#             if splittedParts.qty() == 1 and splittedParts.getLinearObjectAt(0) == GCPPCPart:
#                i = i + 1
#             else:
#                # I replace them with GCPPCPart
#                GCPPCList.remove(i)
#                for splittedPart in splittedParts.defList:
#                   GCPPCList.insert(i, splittedPart)
#                   i = i + 1
#          else:
#             i = i + 1

#    GCPPCList = QadPolyline()
#    circle = QadCircle()
#
#    # for each part of GCPPCList I searc for the pair of closest points with <polyline>
#    for part in dualClippedPolyline:
#       """
#       the function returns
#       <minimum distance>
#       <minimum distance point on object1>
#       <geomIndex su object1>
#       <subGeomIndex su object1>
#       <partIndex su object1>
#       <minimum distance point on object2>
#       <geomIndex su object2>
#       <subGeomIndex su object2>
#       <partIndex su object2>
#       of the 2 geometric objects.
#       """
#       for origPart in polyline.defList:
#          MinDistancePts = QadMinDistance.fromTwoGeomObjects(part, origPart)
#          # if the distance is less than offsetDist (for precision of the calculations it could be very close so I accept a tolerance)
#          if qad_utils.doubleSmaller(MinDistancePts[0], offsetDist) == True:
#             # create a circle at the polyline point closest to part
#             circle.set(MinDistancePts[5], offsetDist)
#             # I get the parts of parts outside the circle
#             splittedParts = getPartsExternalToCircle(part, circle)
#             for splittedPart in splittedParts.defList:
#                GCPPCList.append(splittedPart)
#          else:
#             GCPPCList.append(part)

   GCPPCList = QadPolyline()
   circle = QadCircle()

   # for each part of dualClippedPolyline I searc for the pair of closest points with <polyline>
   for part in dualClippedPolyline:
      """the function returns
            <minimum distance>
            <minimum distance point on object1>
            <minimum distance point on object2>
      """
      splittedParts = [part]
      for origPart in polyline.defList:
         while True:
            i = 0
            splitted = False
            while i < len(splittedParts):
               splittedPart = splittedParts[i]
               MinDistancePts = QadMinDistance.fromTwoBasicGeomObjects(splittedPart, origPart)
               # if the distance is less than offsetDist (for precision of the calculations it could be very close so I accept a tolerance)
               if qad_utils.doubleSmaller(MinDistancePts[0], offsetDist) == True:
                  splitted = True
                  # create a circle at the polyline point closest to part
                  circle.set(MinDistancePts[2], offsetDist)
                  # I get the parts of parts outside the circle
                  outsideParts = getPartsExternalToCircle(splittedPart, circle)
                  # I replace them with splittedPart
                  del splittedParts[i]
                  for outsidePart in outsideParts.defList:
                     splittedParts.insert(i, outsidePart)
                     i = i + 1
               else:
                  i = i + 1

            if splitted == False:
               break

      for splittedPart in splittedParts:
         GCPPCList.append(splittedPart)

   return GCPPCList


# ===============================================================================
# getTrimmedOffSetPolyline
# ===============================================================================
def getTrimmedOffSetPolyline(polyline, untrimmedOffsetPolyline, untrimmedReversedOffsetPolyline, \
                             offsetDist):
   """the function cuts the polyline where necessary using <dual clipping> and <general Closed Point Pair Clipping>.
      <polyline>: list of the original parts of the polyline
      <untrimmedOffsetPolyline>: list of untrimmed parts derived from the offset
      <untrimmedReversedOffsetPolyline>: list of untrimmed parts derived from reverse offset
      <offsetDist> offset distance

      The function returns a list of parts of the polyline (list of segments or arcs or ellipse arcs)
   """

   # I do dual clipping
   dualClippedPolyline = dualClipping(polyline, untrimmedOffsetPolyline, untrimmedReversedOffsetPolyline, offsetDist)
   # test
   #return dualClippedPolyline
   #GCPPCList = untrimmedOffsetPolyline
   #GCPPCList = dualClipping(polyline, untrimmedOffsetPolyline, untrimmedReversedOffsetPolyline, offsetDist)

   # I do general closed point pair clipping
   GCPPCList = generalClosedPointPairClipping(polyline, dualClippedPolyline, offsetDist)
   # test
   #return GCPPCList.defList

   # I join the parts
   return selfJoinPolyline(GCPPCList)


# ===============================================================================
# getUntrimmedOffSetPolyline
# ===============================================================================
def getUntrimmedOffSetPolyline(polyline, offsetDist, offsetSide, gapType):
   """the function makes the offset not cleaned of any cuts to be made (see
      getTrimmedOffSetPolyline") of a polyline
      according to a distance and an offset side ("right" or "left")
      and a <gapType> mode:
      0 = Extends line segments to their projected intersections
      1 = Connect the line segments at their projected intersections.
          The radius of each arc segment is equal to the offset distance
      2 = Trims line segments at projected intersections.
          The perpendicular distance from each peak to its respective vertex
          on the original object is equal to the offset distance.

      The function returns a polyline whose parts are not connected
   """
   # check if polyline is closed
   isClosedPolyline = polyline.isClosed()

   # create a list of the segments and arcs that form the polyline
   polyline = preTreatmentOffset(polyline)

   # I offset each part of the polyline
   newPolyline = QadPolyline()
   i = 0
   while i < polyline.qty():
      part = polyline.getLinearObjectAt(i)
      gType = part.whatIs()
      if gType == "LINE": # segmento
         newPart = part.copy()
         newPart.offset(offsetDist, offsetSide)
         newPolyline.append(newPart)
      elif gType == "ARC": # arc
         newPart = part.copy()
         if newPart.offset(offsetDist, offsetSide) == True:
            newPolyline.append(newPart)
      elif gType == "ELLIPSE_ARC": # arc of ellipse
         pts = part.offset(offsetDist, offsetSide)
         if pts is not None:
            offsetEllipseArc = QadPolyline()
            if offsetEllipseArc.fromPolyline(pts) == True:
               newPolyline.appendPolyline(offsetEllipseArc)
            del pts

      i = i + 1

   # test fino qui OK
   # return newPolyline

   # calculate the intersection points between adjacent parts
   # to obtain an uncut offset line
   if isClosedPolyline == True:
      i = -1
   else:
      i = 0

   untrimmedOffsetPolyline = QadPolyline()
   virtualPartPositionList = []
   while i < newPolyline.qty() - 1:
      if i == -1: # closed polyline so I examine the last segment and the first
         part = newPolyline.getLinearObjectAt(-1) # last part
         nextPart = newPolyline.getLinearObjectAt(0) # first part
      else:
         part = newPolyline.getLinearObjectAt(i)
         nextPart = newPolyline.getLinearObjectAt(i + 1)

      if untrimmedOffsetPolyline.qty() == 0:
         lastUntrimmedOffsetPt = part.getStartPt()
      else:
         lastUntrimmedOffsetPt = untrimmedOffsetPolyline.getLinearObjectAt(-1).getEndPt() # last part

      IntPointInfo = getIntersectionPointInfoOffset(part, nextPart)
      if IntPointInfo is not None: # if there is an intersection
         IntPoint = IntPointInfo[0]
         IntPointTypeForPart = IntPointInfo[1]
         IntPointTypeForNextPart = IntPointInfo[2]

      if part.whatIs() == "LINE": # segmento
         if nextPart.whatIs() == "LINE": # segmento-segmento
            if IntPointInfo is not None: # if there is an intersection point
               if IntPointTypeForPart == 1: # TIP
                  if IntPointTypeForNextPart == 1: # TIP
                     untrimmedOffsetPolyline.append(QadLine().set(lastUntrimmedOffsetPt, IntPoint))
                  else: # FIP
                     untrimmedOffsetPolyline.append(QadLine().set(lastUntrimmedOffsetPt, part.getEndPt()))
                     untrimmedOffsetPolyline.append(QadLine().set(part.getEndPt(), nextPart.getStartPt()))
                     # add the position of this virtual part
                     virtualPartPositionList.append(untrimmedOffsetPolyline.qty() - 1)
               else: # FIP
                  if IntPointTypeForPart == 3: # PFIP
                     if gapType != 0:
                        newLines = offsetBridgeTheGapBetweenLines(part, nextPart, offsetDist, gapType)
                        untrimmedOffsetPolyline.append(newLines[0])
                        untrimmedOffsetPolyline.append(newLines[1]) # arc or connecting line
                     else:
                        untrimmedOffsetPolyline.append(QadLine().set(lastUntrimmedOffsetPt, IntPoint))
                  else: # NFIP
                     untrimmedOffsetPolyline.append(QadLine().set(lastUntrimmedOffsetPt, part.getEndPt()))
                     untrimmedOffsetPolyline.append(QadLine().set(part.getEndPt(), nextPart.getStartPt()))
                     # add the position of this virtual part
                     virtualPartPositionList.append(untrimmedOffsetPolyline.qty() - 1)

         elif nextPart.whatIs() == "ARC": # arc-segment
            if IntPointInfo is not None: # if there is an intersection point
               if IntPointTypeForPart == 1: # TIP
                  if IntPointTypeForNextPart == 1: # TIP
                     untrimmedOffsetPolyline.append(QadLine().set(lastUntrimmedOffsetPt, IntPoint))
                  else: # FIP
                     untrimmedOffsetPolyline.append(QadLine().set(lastUntrimmedOffsetPt, part.getEndPt()))
                     untrimmedOffsetPolyline.append(QadLine().set(part.getEndPt(), nextPart.getStartPt()))
                     # add the position of this virtual part
                     virtualPartPositionList.append(untrimmedOffsetPolyline.qty() - 1)
               else: # FIP
                  if IntPointTypeForPart == 3: # PFIP
                     if IntPointTypeForNextPart == 2: # FIP
                        untrimmedOffsetPolyline.append(QadLine().set(lastUntrimmedOffsetPt, part.getEndPt()))
                        newPart = fillet2PartsOffset(part, nextPart, offsetSide, offsetDist)
                        if newPart is not None:
                           untrimmedOffsetPolyline.append(newPart)
                     elif IntPointTypeForNextPart == 1: # TIP
                        untrimmedOffsetPolyline.append(QadLine().set(lastUntrimmedOffsetPt, IntPoint))
                  else: # NFIP
                     if IntPointTypeForNextPart == 1: # TIP
                        untrimmedOffsetPolyline.append(QadLine().set(lastUntrimmedOffsetPt, part.getEndPt()))
                        untrimmedOffsetPolyline.append(QadLine().set(part.getEndPt(), nextPart.getStartPt()))
                        # add the position of this virtual part
                        virtualPartPositionList.append(untrimmedOffsetPolyline.qty() - 1)
            else: # there is no intersection point
               untrimmedOffsetPolyline.append(QadLine().set(lastUntrimmedOffsetPt, part.getEndPt()))
               newPart = fillet2PartsOffset(part, nextPart, offsetSide, offsetDist)
               if newPart is not None:
                  untrimmedOffsetPolyline.append(newPart)
      elif part.whatIs() == "ARC": # arc
         if nextPart.whatIs() == "LINE": # arc-segment
            if IntPointInfo is not None: # if there is an intersection point
               if IntPointTypeForPart == 1: # TIP
                  newPart = part.copy()
                  newPart.setStartPt(lastUntrimmedOffsetPt) # modify the arc
                  newPart.setEndPt(IntPoint) # modify the arc
                  untrimmedOffsetPolyline.append(newPart)

                  if IntPointTypeForNextPart != 1: # TIP
                     untrimmedOffsetPolyline.append(QadLine().set(IntPoint, nextPart.getStartPt()))
                     # add the position of this virtual part
                     virtualPartPositionList.append(untrimmedOffsetPolyline.qty() - 1)

               else: # FIP
                  newPart = part.copy()
                  newPart.setStartPt(lastUntrimmedOffsetPt) # modify the arc
                  untrimmedOffsetPolyline.append(newPart)

                  if IntPointTypeForNextPart == 4: # NFIP
                     newPart = fillet2PartsOffset(part, nextPart, offsetSide, offsetDist)
                     if newPart is not None:
                        untrimmedOffsetPolyline.append(newPart)
                  elif IntPointTypeForNextPart == 1: # TIP
                     untrimmedOffsetPolyline.append(QadLine().set(part.getEndPt(), nextPart.getStartPt()))
                     # add the position of this virtual part
                     virtualPartPositionList.append(untrimmedOffsetPolyline.qty() - 1)
            else: # there is no intersection point
               newPart = part.copy()
               newPart.setStartPt(lastUntrimmedOffsetPt) # modify the arc
               untrimmedOffsetPolyline.append(newPart)
               newPart = fillet2PartsOffset(part, nextPart, offsetSide, offsetDist)
               if newPart is not None:
                  untrimmedOffsetPolyline.append(newPart)

         elif nextPart.whatIs() == "ARC": # bow-bow
            if IntPointInfo is not None: # if there is an intersection point
               if IntPointTypeForPart == 1: # TIP
                  if IntPointTypeForNextPart == 1: # TIP
                     newPart = part.copy()
                     newPart.setStartPt(lastUntrimmedOffsetPt) # modify the arc
                     newPart.setEndPt(IntPoint) # modify the arc
                     untrimmedOffsetPolyline.append(newPart)
                  else : # FIP
                     newPart = part.copy()
                     newPart.setStartPt(lastUntrimmedOffsetPt) # modify the arc
                     untrimmedOffsetPolyline.append(newPart)

                     if part.reversed == False:
                        center = qad_utils.getPolarPointByPtAngle(part.center, part.endAngle, part.radius - offsetDist)
                     else:
                        center = qad_utils.getPolarPointByPtAngle(part.center, part.startAngle, part.radius - offsetDist)

                     secondPtNewArc = qad_utils.getPolarPointByPtAngle(center, \
                                                                       qad_utils.getAngleBy2Pts(center, IntPoint), \
                                                                       offsetDist)
                     newArc = QadArc()
                     newArc.fromStartSecondEndPts(part.getEndPt(), \
                                                  secondPtNewArc, \
                                                  nextPart.getStartPt())

                     untrimmedOffsetPolyline.append(newArc)
                     # add the position of this virtual part
                     virtualPartPositionList.append(untrimmedOffsetPolyline.qty() - 1)
               else: # FIP
                  if IntPointTypeForNextPart == 1: # TIP
                     newPart = part.copy()
                     newPart.setStartPt(lastUntrimmedOffsetPt) # modify the arc
                     untrimmedOffsetPolyline.append(newPart)

                     if reversed == False:
                        center = qad_utils.getPolarPointByPtAngle(part.center, part.endAngle, part.radius - offsetDist)
                     else:
                        center = qad_utils.getPolarPointByPtAngle(part.center, part.startAngle, part.radius - offsetDist)

                     secondPtNewArc = qad_utils.getPolarPointByPtAngle(center, \
                                                                       qad_utils.getAngleBy2Pts(center, IntPoint), \
                                                                       offsetDist)
                     newArc = QadArc()
                     newArc.fromStartSecondEndPts(part.getEndPt(), \
                                                  secondPtNewArc, \
                                                  nextPart.getStartPt())
                     untrimmedOffsetPolyline.append(newArc)
                     # add the position of this virtual part
                     virtualPartPositionList.append(untrimmedOffsetPolyline.qty() - 1)
                  else: # FIP
                     newPart = part.copy()
                     newPart.setStartPt(lastUntrimmedOffsetPt) # modify the arc
                     newPart.setEndPt(IntPoint) # modify the arc
                     untrimmedOffsetPolyline.append(newPart)
            else: # there is no intersection point
               newPart = part.copy()
               newPart.setStartPt(lastUntrimmedOffsetPt) # modify the arc
               untrimmedOffsetPolyline.append(newPart)

               # before connecting, check whether the arc <part> is entirely inside the offset zone
               # of the <nextPart> arc and vice versa.
               # To replicate this exception make a polyline composed of 2 arcs:
               # the first with center at ..., radius..., initial angle ... final angle ...
               # the second with center at ..., radius..., initial angle ... final angle ...
               # right offset = 8
               dist = qad_utils.getDistance(part.center, nextPart.center)
               minDistArc, maxDistArc = getOffsetDistancesFromCenterOnOffsetedArc(part, offsetDist, offsetSide)
               minDistNextArc, maxDistNextArc = getOffsetDistancesFromCenterOnOffsetedArc(nextPart, offsetDist, offsetSide)

               if (dist + nextPart.radius <= maxDistArc and dist - nextPart.radius >= minDistArc) or \
                  (dist + part.radius <= maxDistNextArc and dist - part.radius >= minDistNextArc):
                  untrimmedOffsetPolyline.append(QadLine().set(newPart.getEndPt(), nextPart.getStartPt()))
               else:
                  newPart = fillet2PartsOffset(part, nextPart, offsetSide, offsetDist)
                  if newPart is not None:
                     untrimmedOffsetPolyline.append(newPart)

      i = i + 1

   if newPolyline.qty() > 0:
      if isClosedPolyline == False:
         if untrimmedOffsetPolyline.qty() == 0:
            # first point of the first part of newPolyline
            lastUntrimmedOffsetPt = newPolyline.getLinearObjectAt(0).getStartPt()
         else:
            # last point of the last part of untrimmedOffsetPolyline
            lastUntrimmedOffsetPt = untrimmedOffsetPolyline.getLinearObjectAt(-1).getEndPt()

         newPart = newPolyline.getLinearObjectAt(-1).copy()
         newPart.setStartPt(lastUntrimmedOffsetPt) # modify the beginning
         untrimmedOffsetPolyline.append(newPart)
      else:
         # first point = last point
         untrimmedOffsetPolyline.getLinearObjectAt(0).setStartPt(untrimmedOffsetPolyline.getLinearObjectAt(-1).getEndPt()) # modify the beginning

   # I do pre-clipping on the virtual parts
   #return virtualPartClipping(untrimmedOffsetPolyline, virtualPartPositionList)
   # test
   return untrimmedOffsetPolyline


# ===============================================================================
# preTreatmentOffset
# ===============================================================================
def preTreatmentOffset(polyline):
   """the function checks the "local self intersection">:
      if the i-th segment (or arc or ellipse arc) and the next have 2 intersections then a vertex is inserted
      in the i-th segment (or arc or arc of ellipse) between the 2 points of intersection.
      The function receives a list of segments, arcs and ellipse arcs and returns a new list of parts
   """
   # check if polyline is closed
   i = -1 if polyline.isClosed() else 0

   result = QadPolyline()
   while i < polyline.qty() - 1:
      if i == -1: # closed polyline so I examine the last segment and the first
         part = polyline.getLinearObjectAt(-1)
         nextPart = polyline.getLinearObjectAt(0)
      else:
         part = polyline.getLinearObjectAt(i)
         nextPart = polyline.getLinearObjectAt(i + 1)

      ptIntList = QadIntersections.twoBasicGeomObjects(part, nextPart)
      if len(ptIntList) == 2: # 2 intersection points
         # calculate the midpoint between the 2 intersection points in part
         gType = part.whatIs()
         if gType == "LINE": # segmento
            ptMiddle = qad_utils.getMiddlePoint(ptIntList[0], ptIntList[1])
            result.append(QadLine().set(part.getStartPt(), ptMiddle))
            result.append(QadLine().set(ptMiddle, part.getEndPt()))
         elif gType == "ARC": # arc
            arc1 = part.copy()
            arc2 = part.copy()
            # if the points are so close that they are considered equal
            if qad_utils.ptNear(part.getEndPt(), ptIntList[0]):
               ptInt = part.getEndPt()
            else:
               ptInt = part.getStartPt()

            arc1.setEndPt(ptInt)
            arc2.setStartPt(ptInt)
            result.append(arc1)
            result.append(arc2)
      else: # a single intersection point
         result.append(part)

      i = i + 1

   if polyline.isClosed() == False: # if it is not closed add the last part
      if polyline.qty() > 1:
         result.append(nextPart)
      else:
         result.append(polyline.getLinearObjectAt(0))

   return result


# ===============================================================================
# getIntersectionPointInfoOffset
# ===============================================================================
def getIntersectionPointInfoOffset(part, nextPart):
   """the function returns the point of intersection between the 2 parts e
      and the intersection type for <part> and for <nextPart>.
      The parts must have already been offset individually:

      1 = TIP (True Intersection Point) if the intersection point obtained by extending
      the 2 parts is found on <part>

      2 = FIP (False Intersection Point) if the intersection point obtained by extending
      the 2 parts is not found on <part>

      3 = PFIP (Positive FIP) if the intersection point is in the same direction as the starting point

      4 = NFIP (Negative FIP) if the intersection point is in the opposite direction of the start
   """

   ptIntList = QadIntersections.twoBasicGeomObjectExtensions(part, nextPart)

   if len(ptIntList) == 0:
      if qad_utils.ptNear(part.getEndPt(), nextPart.getStartPt()) == True:
      #if part.getEndPt() == nextPart.getStartPt(): # <nextPart> inizia dove finisce <part>
         return [part.getEndPt(), 1, 1] # TIP-TIP
      else:
         return None
   elif len(ptIntList) == 1:
      gType = part.whatIs()
      if gType == "LINE": # segmento
         if part.containsPt(ptIntList[0]):
            intTypePart = 1 # TIP
         else: # the intersection is not on the segment (FIP)
            # if the direction is the same as the segment
            if qad_utils.doubleNear(qad_utils.getAngleBy2Pts(part.getStartPt(), part.getEndPt()), \
                                    qad_utils.getAngleBy2Pts(part.getStartPt(), ptIntList[0])):
               intTypePart = 3 # PFIP
            else:
               intTypePart = 4 # NFIP
      else: # arc or arc of ellipse
         if part.containsPt(ptIntList[0]):
            intTypePart = 1 # TIP
         else:
            intTypePart = 2 # FIP

      gType = nextPart.whatIs()
      if gType == "LINE": # segmento
         if nextPart.containsPt(ptIntList[0]):
            intTypeNextPart = 1 # TIP
         else: # the intersection is not on the segment (FIP)
            # if the direction is the same as the segment
            if qad_utils.doubleNear(qad_utils.getAngleBy2Pts(nextPart.getStartPt(), nextPart.getEndPt()), \
                                    qad_utils.getAngleBy2Pts(nextPart.getStartPt(), ptIntList[0])):
               intTypeNextPart = 3 # PFIP
            else:
               intTypeNextPart = 4 # NFIP
      else: # arc or arc of ellipse
         if nextPart.containsPt(ptIntList[0]):
            intTypeNextPart = 1 # TIP
         else:
            intTypeNextPart = 2 # FIP

      return [ptIntList[0], intTypePart, intTypeNextPart]

   else: # 2 intersection points
      # I choose the point closest to the final point of part
      gType = part.whatIs()
      if gType == "LINE": # segmento
         if qad_utils.getDistance(ptIntList[0], part.getEndPt()) < qad_utils.getDistance(ptIntList[1], part.getEndPt()):
            ptInt = ptIntList[0]
         else:
            ptInt = ptIntList[1]

         if part.containsPt(ptInt):
            intTypePart = 1 # TIP
         else: # the intersection is not on the segment (FIP)
            # if the direction is the same as the segment
            if qad_utils.doubleNear(qad_utils.getAngleBy2Pts(part.getStartPt(), part.getEndPt()), \
                                    qad_utils.getAngleBy2Pts(part.getStartPt(), ptInt)):
               intTypePart = 3 # PFIP
            else:
               intTypePart = 4 # NFIP

         # the second part is definitely an arc
         if nextPart.containsPt(ptInt):
            intTypeNextPart = 1 # TIP
         else: # the intersection is not on the arc (FIP)
            intTypeNextPart = 2 # FIP

         return [ptInt, intTypePart, intTypeNextPart]
      else: # arc or arc of ellipse
         finalPt = part.getEndPt()

         if qad_utils.getDistance(ptIntList[0], finalPt) < qad_utils.getDistance(ptIntList[1], finalPt):
            ptInt = ptIntList[0]
         else:
            ptInt = ptIntList[1]

         if part.containsPt(ptInt):
            intTypePart = 1 # TIP
         else: # the intersection is not on the arc (FIP)
            intTypePart = 2 # FIP

         gType = nextPart.whatIs()
         if gType == "LINE": # segmento
            if nextPart.containsPt(ptInt):
               intTypeNextPart = 1 # TIP
            else: # the intersection is not on the segment (FIP)
               # if the direction is the same as the segment
               if qad_utils.doubleNear(qad_utils.getAngleBy2Pts(nextPart.getStartPt(), nextPart.getEndPt()), \
                                       qad_utils.getAngleBy2Pts(nextPart.getStartPt(), ptInt)):
                  intTypeNextPart = 3 # PFIP
               else:
                  intTypeNextPart = 4 # NFIP
         else: # arc or arc of ellipse
            if nextPart.containsPt(ptInt):
               intTypeNextPart = 1 # TIP
            else: # the intersection is not on the arc (FIP)
               intTypeNextPart = 2 # FIP

         return [ptInt, intTypePart, intTypeNextPart]


# ============================================================================
# getSelfIntersectionPoints
# ============================================================================
def getSelfIntersectionPoints(polyline):
   """the function returns a list in which each element is a sublist composed of:
      1) point of intersection of the polyline with itself
      2) distance of the intersection points from the start of the polyline
      3) number of the part containing the intersection point
   """
   result = []
   distFromStartPrevPart = 0
   for iPart in range(len(polyline.defList)):
      part = polyline.defList[iPart]
      startPtOfPart = part.getStartPt()
      endPtOfPart = part.getEndPt()

      # calculate intersections with all parts except itself
      for jPart in range(len(polyline.defList)):
         if (iPart == jPart):
            continue
         partialIntPtList = QadIntersections.twoBasicGeomObjects(part, polyline.defList[jPart])
         for partialIntPt in partialIntPtList:
            # I exclude the points that are at the beginning-end of part
            # if the points are so close that they are considered equal
            if qad_utils.ptNear(startPtOfPart, partialIntPt) == False and \
               qad_utils.ptNear(endPtOfPart, partialIntPt) == False:
               # insert the point with the distance from the start of the polyline and the part number
               distFromStartPart = part.getDistanceFromStart(partialIntPt)
               result.append([partialIntPt, distFromStartPart + distFromStartPrevPart, iPart])

      distFromStartPrevPart += part.length()

   return result


# ============================================================================
# getIntersectionPointsWithPolyline
# ============================================================================
def getIntersectionPointsWithPolyline(polyline1, polyline2):
   """the function returns a list in which each element is a sublist composed of:
      1) intersection point of the polyline with <polyline2>
      2) distance of the intersection points from the start of the polyline
      3) number of the part containing the intersection point
   """
   result = []
   distFromStartPrevPart = 0
   for iPart in range(len(polyline1.defList)):
      part = polyline1.defList[iPart]
      startPtOfPart = part.getStartPt()
      endPtOfPart = part.getEndPt()

      # calculate the intersections with all parts of <polyline2>
      for jPart in range(len(polyline2.defList)):
         partialIntPtList = QadIntersections.twoBasicGeomObjects(part, polyline2.defList[jPart])
         for partialIntPt in partialIntPtList:
            # I exclude the points that are at the beginning-end of part
            # if the points are so close that they are considered equal
            if qad_utils.ptNear(startPtOfPart, partialIntPt) == False and \
               qad_utils.ptNear(endPtOfPart, partialIntPt) == False:
               # insert the point with the distance from the start of the polyline and the part number
               distFromStartPart = part.getDistanceFromStart(partialIntPt)
               result.append([partialIntPt, distFromStartPart + distFromStartPrevPart, iPart])

      distFromStartPrevPart += part.length()

   return result



# ===============================================================================
# offsetBridgeTheGapBetweenLines
# ===============================================================================


def offsetBridgeTheGapBetweenLines(line1, line2, offset, gapType):
   """the function fills the gap between 2 straight segments (QadLine) in the offset command
      according to a distance <offset> (which corresponds to the offset distance s
      called by that command) and a <gapType> mode:
      0 = Extends segments to their projected intersections
      1 = Fillets the segments through a fillet arc of radius <offset>
      2 = Trims line segments at projected intersections.
          The perpendicular distance from each peak to its respective vertex
          on the original object is equal to the distance <offset>.

      If
      It returns a list of 3 elements (None in case of error):
      a line that replaces <line1>, if = None <line1> should be removed
      an arc, if = None there is no connecting arc between the two lines
      a line that replaces <line2>, if = None <line2> should be removed
   """
   # I look for the intersection point between the two lines
   ptInt = QadIntersections.twoInfinityLines(line1, line2)
   if ptInt is None: # linee parallele
      return None
   distBetweenLine1Pt1AndPtInt = qad_utils.getDistance(line1.getStartPt(), ptInt)
   distBetweenLine1Pt2AndPtInt = qad_utils.getDistance(line1.getEndPt(), ptInt)
   distBetweenLine2Pt1AndPtInt = qad_utils.getDistance(line2.getStartPt(), ptInt)
   distBetweenLine2Pt2AndPtInt = qad_utils.getDistance(line2.getEndPt(), ptInt)

   if gapType == 0: # Estende i segmenti
      if distBetweenLine1Pt1AndPtInt > distBetweenLine1Pt2AndPtInt:
         # second point of line1 closest to the intersection point
         newLine1 = QadLine().set(line1.getStartPt(), ptInt)
      else:
         # first point of line1 closest to the intersection point
         newLine1 = QadLine().set(ptInt, line1.getEndPt())

      if distBetweenLine2Pt1AndPtInt > distBetweenLine2Pt2AndPtInt:
         # second point of line2 closest to the intersection point
         newLine2 = QadLine().set(line2.getStartPt(), ptInt)
      else:
         # first point of line2 closest to the intersection point
         newLine2 = QadLine().set(ptInt, line2.getEndPt())

      return [newLine1, None, newLine2]
   elif gapType == 1: # Raccorda i segmenti
      pt1Distant = line1.getStartPt() if distBetweenLine1Pt1AndPtInt > distBetweenLine1Pt2AndPtInt else line1.getEndPt()
      angleLine1 = qad_utils.getAngleBy2Pts(ptInt, pt1Distant)

      pt2Distant = line2.getStartPt() if distBetweenLine2Pt1AndPtInt > distBetweenLine2Pt2AndPtInt else line2.getEndPt()
      angleLine2 = qad_utils.getAngleBy2Pts(ptInt, pt2Distant)

      bisectorInfinityLinePts = qad_utils.getBisectorInfinityLine(pt1Distant, ptInt, pt2Distant, True)
      bisectorLine = QadLine().set(bisectorInfinityLinePts[0], bisectorInfinityLinePts[1])

      # I look for the point of intersection between the bisector and
      # the straight line that joins the most distant points of the two lines
      pt = QadIntersections.twoInfinityLines(bisectorLine, \
                                             QadLine().set(pt1Distant, pt2Distant))
      angleBisectorLine = qad_utils.getAngleBy2Pts(ptInt, pt)

      # calculate the angle (absolute value) between a side and the bisector
      alfa = angleLine1 - angleBisectorLine
      if alfa < 0:
         alfa = angleBisectorLine - angleLine1
      if alfa > math.pi:
         alfa = (2 * math.pi) - alfa

      # calculate the angle of the right triangle knowing that the sum of the internal angles = 180
      # - alpha - 90 degrees (right angle)
      distFromPtInt = math.tan(math.pi - alfa - (math.pi / 2)) * offset
      pt1Proj = qad_utils.getPolarPointByPtAngle(ptInt, angleLine1, distFromPtInt)
      pt2Proj = qad_utils.getPolarPointByPtAngle(ptInt, angleLine2, distFromPtInt)
      # Pitagora
      distFromPtInt = math.sqrt((distFromPtInt * distFromPtInt) + (offset * offset))
      secondPt = qad_utils.getPolarPointByPtAngle(ptInt, angleBisectorLine, distFromPtInt - offset)
      arc = QadArc()
      arc.fromStartSecondEndPts(pt1Proj, secondPt, pt2Proj)

      if distBetweenLine1Pt1AndPtInt > distBetweenLine1Pt2AndPtInt:
         # second point of line1 closest to the intersection point
         newLine1 = QadLine().set(pt1Distant, pt1Proj)
      else:
         # first point of line1 closest to the intersection point
         newLine1 = QadLine().set(pt1Proj, pt1Distant)

      if distBetweenLine2Pt1AndPtInt > distBetweenLine2Pt2AndPtInt:
         # second point of line2 closest to the intersection point
         newLine2 = QadLine().set(pt2Distant, pt2Proj)
      else:
         # first point of line2 closest to the intersection point
         newLine2 = QadLine().set(pt2Proj, pt2Distant)

      # if the points are so close that they are considered equal
      if qad_utils.ptNear(newLine1.getEndPt(), arc.getStartPt()) == False:
         arc.reverse()
      return [newLine1, arc, newLine2]
   elif gapType == 2: # Cima i segmenti
      bisectorInfinityLinePts = qad_utils.getBisectorInfinityLine(line1.getEndPt(), ptInt, line2.getEndPt(), True)
      bisectorLine = QadLine().set(bisectorInfinityLinePts[0], bisectorInfinityLinePts[1])

      angleBisectorLine = qad_utils.getAngleBy2Pts(bisectorLine[0], bisectorLine[1])
      ptProj = qad_utils.getPolarPointByPtAngle(ptInt, angleBisectorLine, offset)

      pt1Proj = QadPerpendicularity.fromPointToInfinityLine(ptProj, line1)
      if distBetweenLine1Pt1AndPtInt > distBetweenLine1Pt2AndPtInt:
         # second point of line1 closest to the intersection point
         newLine1 = QadLine().set(line1.getStartPt(), pt1Proj)
      else:
         # first point of line1 closest to the intersection point
         newLine1 = QadLine().set(pt1Proj, line1.getEndPt())

      pt2Proj = QadPerpendicularity.fromPointToInfinityLine(ptProj, line2)
      if distBetweenLine2Pt1AndPtInt > distBetweenLine2Pt2AndPtInt:
         # second point of line2 closest to the intersection point
         newLine2 = QadLine().set(line2.getStartPt(), pt2Proj)
      else:
         # first point of line2 closest to the intersection point
         newLine2 = QadLine().set(pt2Proj, line2.getEndPt())

      return [newLine1, QadLine().set(pt1Proj, pt2Proj), newLine2]

   return None


# ===============================================================================
# fillet2PartsOffset
# ===============================================================================
def fillet2PartsOffset(part, nextPart, offsetSide, offsetDist):
   """the function connects 2 parts in the following cases:
      1) segment-arc (PFIP-FIP, no intersection)
      2) arc-segment (FIP-NFIP, no intersection)
      3) arc-arc (no intersection)
   """
   gType = part.whatIs()
   # if the first part is a segment
   if gType == "LINE":
      newNextPart = part.copy()
      newNextPart.reverse() # I reverse the direction
      newPart = nextPart.copy()
      newPart.reverse() # I reverse the direction
      newOffSetSide = "left" if offsetSide == "right" else "right"
      result = fillet2PartsOffset(newPart, newNextPart, newOffSetSide, offsetDist)
      if result is not None:
         result.reverse() # I reverse the direction
      return result

   elif gType == "ARC": # if the first part is an arc
      AngleProjected = qad_utils.getAngleBy2Pts(part.center, part.getEndPt())
      if part.reversed == False: # the arc turns to the left
         if offsetSide == "right": # l'offset era verso l'outside
            # calculate the projected point to re-obtain the original one
            center = qad_utils.getPolarPointByPtAngle(part.center, AngleProjected, part.radius - offsetDist)
         else: # l'offset era verso l'inside
            center = qad_utils.getPolarPointByPtAngle(part.center, AngleProjected, part.radius + offsetDist)
      else: # the arc turns to the right
         if offsetSide == "right": # l'offset era verso l'inside
            center = qad_utils.getPolarPointByPtAngle(part.center, AngleProjected, part.radius + offsetDist)
         else: # l'offset era verso l'outside
            center = qad_utils.getPolarPointByPtAngle(part.center, AngleProjected, part.radius - offsetDist)

      newArc = QadArc()
      # if the center of the connection arc is inside the offset arc
      if qad_utils.getDistance(part.center, center) < part.radius:
         if part.reversed == False:
            if newArc.fromStartCenterEndPts(part.getEndPt(), center, nextPart.getStartPt()) == False:
               return None
            newArc.reversed = False
         else:
            if newArc.fromStartCenterEndPts(nextPart.getStartPt(), center, part.getEndPt()) == False:
               return None
            newArc.reversed = True
      else: # if the center of the connection arc is outside the offset arc
         if part.reversed == False:
            if newArc.fromStartCenterEndPts(nextPart.getStartPt(), center, part.getEndPt()) == False:
               return None
            newArc.reversed = True
         else:
            if newArc.fromStartCenterEndPts(part.getEndPt(), center, nextPart.getStartPt()) == False:
               return None
            newArc.reversed = False

      return newArc


# ===============================================================================
# getOffsetDistancesFromCenterOnOffsetedArc
# ===============================================================================
def getOffsetDistancesFromCenterOnOffsetedArc(arc, offsetDist, offsetSide):
   """the function returns the minimum and maximum distance from the center of the arc on which an offset has already been made.
      These distances generate an offset area around the original arc.
      <arc> arc that has already been offset
      <offsetDist> offset distance
      <offsetSide> part where you want the "right" or "left" offset
   """
   if arc.reversed: # the arc turns to the right
      if offsetSide == "right": # offset on the inside of the arc
         minDist = arc.radius
         maxDist = arc.radius + 2 * offsetDist
      else: # offset on the outside of the arc
         maxDist = arc.radius
         minDist = arc.radius - 2 * offsetDist
   else: # the arc turns to the left
      if offsetSide == "right": # offset on the outside of the arc
         maxDist = arc.radius
         minDist = arc.radius - 2 * offsetDist
      else: # offset on the inside of the arc
         minDist = arc.radius
         maxDist = arc.radius + 2 * offsetDist

   if minDist < 0: minDist = 0

   return minDist, maxDist


# ===============================================================================
# virtualPartClipping
# ===============================================================================
def virtualPartClipping(untrimmedOffsetPolyline, virtualPartPositionList):
   """the function returns a list of parts into which the generated islands are cut
      from virtual parts (which reverse the direction of the line).
      For each virtual part, it is checked whether the preceding and following parts form an island.
      If so, if possible (see specific cases), the sole is removed.
      <untrimmedOffsetPolyline> parts list
      <virtualPartPositionList> list of virtual part positions (is modified)
   """
   result = untrimmedOffsetPolyline.copy()

   # I first delete all islands with virtual parts that the parts have
   # directly adjacent intersecting
   i = len(virtualPartPositionList) - 1
   while i >= 0:
      virtualPartPosition = virtualPartPositionList[i]
      # part following the virtual one
      nextPos = result.getNextPos(virtualPartPosition)
      # previous part
      prevPos = result.getPrevPos(virtualPartPosition)

      if (prevPos is not None) and (nextPos is not None):
         nextPart = result.getLinearObjectAt(nextPos)
         prevPart = result.getLinearObjectAt(prevPos)
         # check if they have only one intersection point
         ptIntList = QadIntersections.twoBasicGeomObjects(prevPart, nextPart)
         if len(ptIntList) == 1:
            nextPart.setStartPt(ptIntList[0]) # modify the beginning
            prevPart.setEndPt(ptIntList[0]) # change the end
            result.remove(virtualPartPosition)
            del virtualPartPositionList[i]
            for j in range(i, len(virtualPartPositionList)):
               virtualPartPositionList[j] = virtualPartPositionList[j] - 1 # I stop all by one
      i = i - 1

   # I eliminate all islands with virtual parts that have intersecting adjacent parts
   # but which do not form other islands with the rest of the line.
   # when I consider a side adjacent to the virtual part on one side I have to consider the intersections
   # starting from the next side, the one adjacent to the opposite side of the virtual one
   for i in range(len(virtualPartPositionList) - 1, -1, -1):
      virtualPartPosition = virtualPartPositionList[i]
      # until the intersection is found
      nPrevPartsToRemove = -1
      prevPos = virtualPartPosition
      ptIntList = []
      while len(ptIntList) == 0:
         virtualPart = result.getLinearObjectAt(virtualPartPosition)
         # part following the virtual one
         nextPos = result.getNextPos(virtualPartPosition)
         nNextPartsToRemove = 0
         # previous part
         prevPos = result.getPrevPos(prevPos)
         # if I find a virtual part I stop
         if virtualPartPositionList.count(prevPos) > 0:
            break

         # the last condition is if the polyline is closed
         if (prevPos is None) or (nextPos is None) or prevPos == nextPos:
            break

         nPrevPartsToRemove = nPrevPartsToRemove + 1
         prevPart = result.getLinearObjectAt(prevPos)

         # loop until there are no more following parts
         while (nextPos is not None) and (prevPos != nextPos):
            # if I find a virtual part I stop
            if virtualPartPositionList.count(nextPos) > 0:
               break
            nextPart = result.getLinearObjectAt(nextPos)
            ptIntList = QadIntersections.twoBasicGeomObjects(prevPart, nextPart)
            if len(ptIntList) > 0:
               break
            nextPos = result.getNextPos(nextPos) # next part
            nNextPartsToRemove = nNextPartsToRemove + 1

      if len(ptIntList) == 1 and \
         not qad_utils.ptNear(ptIntList[0], virtualPart.getStartPt()) and \
         not qad_utils.ptNear(ptIntList[0], virtualPart.getEndPt()):
         prevPart_1 = prevPart.copy()
         # if the starting point of the part does not coincide with that of the intersection point
         if not qad_utils.ptNear(ptIntList[0], prevPart.getStartPt()):
            prevPart_1.setEndPt(ptIntList[0]) # change the end
            prevPart_2 = prevPart.copy()
            prevPart_2.setStartPt(ptIntList[0]) # modify the beginning
         else:
            prevPart_2 = None

         nextPart_1 = nextPart.copy()
         # if the end point of the part does not coincide with that of the intersection point
         if not qad_utils.ptNear(ptIntList[0], nextPart.getEndPt()):
            nextPart_1.setEndPt(ptIntList[0]) # change the end
            nextPart_2 = nextPart.copy()
            nextPart_2.setStartPt(ptIntList[0]) # modify the beginning
         else:
            nextPart_2 = None

         ########################################################
         # create a parts list that defines the island - start
         islandPolyline = QadPolyline()

         if prevPart_2 is None:
            islandPolyline.append(prevPart_1)
         else:
            islandPolyline.append(prevPart_2)

         pos = virtualPartPosition
         for j in range(nPrevPartsToRemove, 0, - 1):
            pos = result.getPrevPos(pos) # previous part
            islandPolyline.append(result.getLinearObjectAt(pos))

         islandPolyline.append(virtualPart)

         pos = virtualPartPosition
         for j in range(1, nNextPartsToRemove + 1, 1):
            pos = result.getNextPos(pos) # next part
            islandPolyline.append(result.getLinearObjectAt(pos))

         islandPolyline.append(nextPart_1)

         # create a parts list that defines the island - end
         ########################################################

         # check if the following parts form areas with islandPolyline (more than 2 intersections)
         if nextPart_2 is not None:
            nIntersections = 1
         else:
            nIntersections = 0

         for j in range(nextPos + 1, result.qty(), 1):
            dummy = QadIntersections.getOrderedPolylineIntersectionPtsWithBasicGeom(islandPolyline, result.getLinearObjectAt(j))
            intPtList = dummy[0]
            nIntersections = nIntersections + len(intPtList)

         # if it is positive and less than or equal to 2 I also check on the other side
         if nIntersections > 0 and nIntersections <= 2:
            # check if the previous parts form areas with islandPolyline (at least 2 intersections)
            if prevPart_2 is not None:
               nIntersections = 1
            else:
               nIntersections = 0

            for j in range(prevPos - 1, -1, -1):
               dummy = QadIntersections.getOrderedPolylineIntersectionPtsWithBasicGeom(islandPolyline, result.getLinearObjectAt(j))
               intPtList = dummy[0]
               nIntersections = nIntersections + len(intPtList)

            # if it is positive and less than or equal to 2 I also check on the other side
            if nIntersections > 0 and nIntersections <= 2:
               # rimuovo island da result
               if nextPart_2 is not None:
                  nextPart.setStartPt(nextPart_2.getStartPt()) # modify the beginning
               else:
                  result.remove(nextPos)

               # delete the unnecessary parts
               for j in range(0, nNextPartsToRemove, 1):
                  result.remove(virtualPartPosition + 1)

               # delete the virtual part
               result.remove(virtualPartPosition)

               # delete the unnecessary parts
               for j in range(0, nPrevPartsToRemove, 1):
                  result.remove(virtualPartPosition - nPrevPartsToRemove)

               if prevPart_2 is not None:
                  prevPart.setEndPt(nextPart_2.getStartPt()) # change the end
               else:
                  result.remove(prevPos)

               del virtualPartPositionList[i]

   return result


# ===============================================================================
# getIntPtListBetweenPartAndPartListOffset
# ===============================================================================
def getIntPtListBetweenPartAndPartListOffset(part, polyline):
   """the function returns two lists:
      the first is a list of intersection points between the <part> part
      and the polyline <polyline> ordered by distance from the starting point
      of part (discards duplicates and start-end points of part)
      the second is a list that contains, respectively for each intersection point,
      the part number (0-based) of <polyline> where that point is located.
      <part>: a segment or arc
      <polyline>: list of parts of a polyline
   """
   startPtOfPart = part.getStartPt()
   endPtOfPart = part.getEndPt()
   intPtSortedList = [] # list of ((point, distance from start of part)...)
   partNumber = -1
   # for each part of polyline
   for part2 in polyline.defList:
      partNumber = partNumber + 1
      partialIntPtList = QadIntersections.twoBasicGeomObjects(part, part2)
      for partialIntPt in partialIntPtList:
         # I exclude the points that are at the beginning-end of part

         # if the points are so close that they are considered equal
         if qad_utils.ptNear(startPtOfPart, partialIntPt) == False and \
            qad_utils.ptNear(endPtOfPart, partialIntPt) == False:
            # I exclude points that are already in intPtSortedList
            found = False
            for intPt in intPtSortedList:
               if qad_utils.ptNear(intPt[0], partialIntPt):
                  found = True
                  break

            if found == False:
               # insert the point ordered by distance from the start of the part
               distFromStart = part.getDistanceFromStart(partialIntPt)
               insertAt = 0
               for intPt in intPtSortedList:
                  if intPt[1] < distFromStart:
                     insertAt = insertAt + 1
                  else:
                     break
               intPtSortedList.insert(insertAt, [partialIntPt, distFromStart, partNumber])
   resultIntPt = []
   resultPartNumber = []
   for intPt in intPtSortedList:
      resultIntPt.append(intPt[0])
      resultPartNumber.append(intPt[2])

   return resultIntPt, resultPartNumber


# ============================================================================
# getPartsExternalToCircle
# ============================================================================
def getPartsExternalToCircle(linearObj, circle):
   """the function uses a circle to divide the linear object.
      The parts outside the circle are returned
      in order from the start point to the end point of the linear object.
   """
   result = QadPolyline()

   startPt = linearObj.getStartPt()
   endPt = linearObj.getEndPt()
   intPtList = QadIntersections.twoBasicGeomObjects(circle, linearObj)

   intPtSortedList = []
   for pt in intPtList:
      # insert the point ordered by distance from the beginning of part
      distFromStart = linearObj.getDistanceFromStart(pt)
      insertAt = 0
      for intPt in intPtSortedList:
         if intPt[1] < distFromStart:
            insertAt = insertAt + 1
         else:
            break
      intPtSortedList.insert(insertAt, [pt, distFromStart])

   del intPtList[:] # I empty the list
   for intPt in intPtSortedList:
      intPtList.append(intPt[0])

   startPtFromCenter = qad_utils.getDistance(circle.center, startPt)
   endPtFromCenter = qad_utils.getDistance(circle.center, endPt)
   intPtListLen = len(intPtList)
   if intPtListLen == 0: # if there are no intersection points
      # if both end points of the part are outside the circle
      if startPtFromCenter >= circle.radius and endPtFromCenter >= circle.radius:
         result.append(linearObj)
   elif intPtListLen == 1: # if there is only one intersection point
      # if both end points of the part are outside the circle
      if startPtFromCenter >= circle.radius and endPtFromCenter >= circle.radius:
         result.append(linearObj)
      # if the first point of the part is internal and the second external to the circle
      elif startPtFromCenter < circle.radius and endPtFromCenter > circle.radius:
         newLinearobj = linearObj.copy()
         newLinearobj.setStartPt(intPtList[0])
         result.append(newLinearobj)
      # if the first point of the part is external and the second internal to the circle
      elif startPtFromCenter > circle.radius and endPtFromCenter < circle.radius:
         newLinearobj = linearObj.copy()
         newLinearobj.setEndPt(intPtList[0])
         result.append(newLinearobj)
   else : # if there are two intersection points
      # if the first point of the part is outside the circle
      if startPtFromCenter > circle.radius:
         newLinearobj = linearObj.copy()
         newLinearobj.setEndPt(intPtList[0])
         result.append(newLinearobj)
      # if the second point of the part is outside the circle
      if endPtFromCenter > circle.radius:
         newLinearobj = linearObj.copy()
         newLinearobj.setStartPt(intPtList[1])
         result.append(newLinearobj)

   return result
