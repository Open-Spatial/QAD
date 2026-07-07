# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 functions for extend and trim

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

from .qad_multi_geom import *
from .qad_geom_relations import *
from .qad_entity import *
from .qad_arc import *
from .qad_ellipse_arc import *


# ===============================================================================
# extendQadGeometry
# ===============================================================================
def extendQadGeometry(qadGeom, pt, limitEntitySet, edgeMode):
   """the function extends a QAD (linear) geometry in the initial or final part up to
      meet the closest object in the <limitEntitySet> group according to the <edgeMode> mode.
      <qadGeom> = QAD linear geometry to extend
      <pt> = dot indicating the part of that object that needs to be extended
      <QadEntitySet> = group of entities that serves as an extension limit
      <edgeMode> if = 0 the geometry must extend until it meets the closest object
                 if = 1 the geometry must be extended until it meets the closest object o
                 also its extension
   """
   if qadGeom is None:
      return None

   # the function returns a list with
   # (<minimum distance>
   # <nearest vertex point>
   # <nearest geometry index>
   # <index of the nearest sub-geometry>
   # <index of the closest sub-geometry part>
   # <nearest vertex index>
   result = getQadGeomClosestVertex(qadGeom, pt)
   nearPt = result[1]
   atGeom = result[2]
   atSubGeom = result[3]
   subGeom = getQadGeomAt(qadGeom, atGeom, atSubGeom)

   if not isLinearQadGeom(subGeom): return None
   middleLength = subGeom.length() / 2
   distFromStart = subGeom.getDistanceFromStart(nearPt)

   if subGeom.whatIs() == "POLYLINE":
      if subGeom.isClosed(): # cannot be done with a closed polyline
         return None
      if distFromStart > middleLength:
         # final part
         linearObjectToExtend = subGeom.getLinearObjectAt(-1).copy()
      else:
         # initial part
         linearObjectToExtend = subGeom.getLinearObjectAt(0).copy()
         linearObjectToExtend.reverse()
   else:
      linearObjectToExtend = subGeom.copy()
      if distFromStart < middleLength:
         # initial part
         linearObjectToExtend.reverse()

   # for each entity of limitEntitySet I look for the intersection points
   intPts = []
   entityIterator = QadEntitySetIterator(limitEntitySet)
   for limitEntity in entityIterator:
      limitGeom = limitEntity.getQadGeom()
      if limitGeom is None:
         continue
      intPts.extend(getIntersectionPtsExtendQadGeometry(linearObjectToExtend, limitGeom, edgeMode))

   # I look for the intersection point closest to the end point of linearObject
   testGeom = linearObjectToExtend.copy()
   newEndPt = None
   minDist = sys.float_info.max

   for intPt in intPts:
      testGeom.setEndPt(intPt)
      length = testGeom.length()
      if length < minDist:
         minDist = length
         newEndPt = intPt

   if newEndPt is None:
      return None

   result = subGeom.copy()
   if distFromStart > middleLength:
      # final point
      result.setEndPt(newEndPt)
   else:
      # starting point
      result.setStartPt(newEndPt)

   return setQadGeomAt(qadGeom, result, atGeom, atSubGeom)


# ===============================================================================
# getIntersectionPtsExtendQadGeometry
# ===============================================================================
def getIntersectionPtsExtendQadGeometry(linearObject, limitGeom, edgeMode):
   """the function calculates the intersection points between the extension of the linear part
      beyond the end point until meeting the <limitGeom> geometry according to the <edgeMode> mode.
      Points beyond the endpoint of <linearObject> are returned.
      <linearObject> = QAD base geometry to extend (line, arc, ellipse arc, circle, ellipse)
      <limitGeom> = QAD geometry to use as extension limit
      <edgeMode> if = 0 the geometry must extend until it meets the closest object
                 if = 1 the geometry must be extended until it meets the closest object o
                 also its extension
   """
   if linearObject is None or limitGeom is None:
      return []

   intPts = []

   intPts = QadIntersections.twoGeomObjectsExtensions(linearObject, limitGeom)
   if edgeMode == 0: # without extending limitGeom
      # delete the intersection points that are not on limitGeom
      for i in range(len(intPts) - 1, -1, -1):
         if limitGeom.containsPt(intPts[i]) == False: del intPts[i]

   # delete the intersection points that are on linearObject
   for i in range(len(intPts) - 1, -1, -1):
      if linearObject.containsPt(intPts[i]) == True: del intPts[i]

   # delete intersection points that are not beyond the end of linearObject
   if linearObject.whatIs() == "LINE":
      angle = linearObject.getTanDirectionOnPt()
      for i in range(len(intPts) - 1, -1, -1):
         if qad_utils.doubleNear(angle, qad_utils.getAngleBy2Pts(linearObject.getStartPt(), intPts[i])) == False:
            del intPts[i]

   return intPts



# ===============================================================================
# trimQadGeometry
# ===============================================================================
def trimQadGeometry(qadGeom, pt, limitEntitySet, edgeMode):
   """the function cuts the QAD (linear) geometry into a part whose limits are the plus intersections
      close to pt with the objects of the <limitEntitySet> group according to the <edgeMode> mode.
      <qadGeom> = QAD geometry to cut
      <pt> = point indicating the part of that object that must be cut
      <limitEntitySet> = group of entities that serves as the cutting limit
      <edgeMode> if = 0 the geometry must extend until it meets the closest object
                 if = 1 the geometry must be extended until it meets the closest object o
                 also its extension

      Returns a list:
      (<geometry 1 resulting from operation> <geometry 2 resulting from operation> <atGeom> <atSubGeom>)
   """
   if qadGeom is None:
      return None

   gType = qadGeom.whatIs()
   if gType == "POINT" or gType == "MULTI_POINT": return None

   # the function returns a list with
   # (<minimum distance>
   # <nearest point>
   # <nearest geometry index>
   # <index of the nearest sub-geometry>
   # <index of the closest sub-geometry part>
   # <"to the left of" if the point is to the left of the part with the following values:
   # - < 0 = left (for line, arc or ellipse arc) or inside (for circles, ellipses)
   # - > 0 = right (for line, arc or ellipse arc) or outside (for circles, ellipses)
   # )
   result = getQadGeomClosestPart(qadGeom, pt)
   nearPt = result[1]
   atGeom = result[2]
   atSubGeom = result[3]
   subGeom = getQadGeomAt(qadGeom, atGeom, atSubGeom)

   # for each entity of limitEntitySet I look for the intersection points
   intPts = []
   entityIterator = QadEntitySetIterator(limitEntitySet)
   for limitEntity in entityIterator:
      limitGeom = limitEntity.getQadGeom()
      if limitGeom is None:
         continue
      intPts.extend(getIntersectionPtsTrimQadGeometry(subGeom, limitGeom, edgeMode))

   # I order the intersection points by distance from the starting point
   distFromStartList = []
   subGeomType = subGeom.whatIs()
   if subGeomType == "CIRCLE" or subGeomType == "ELLIPSE":
      # I use angles
      for intPt in intPts:
         distFromStartList.append(qad_utils.getAngleBy2Pts(subGeom.center, intPt))
   else:
      # I use distances
      for intPt in intPts:
         distFromStartList.append(subGeom.getDistanceFromStart(intPt))

   intPtSortedList = []
   distFromStartSortedList = []
   minDist = sys.float_info.max
   i = 0
   while i < len(distFromStartList):
      insertAt = 0
      while insertAt < len(distFromStartSortedList):
         if distFromStartList[i] > distFromStartSortedList[insertAt]:
            insertAt = insertAt + 1
         else:
            break

      intPtSortedList.insert(insertAt, intPts[i])
      distFromStartSortedList.insert(insertAt, distFromStartList[i])
      i = i + 1

   if subGeomType == "CIRCLE" or subGeomType == "ELLIPSE":
      if len(intPtSortedList) < 2: return None
      distFromStart = qad_utils.getAngleBy2Pts(subGeom.center, nearPt)
      if subGeomType == "ELLIPSE":
         ellipseAngle = qad_utils.getAngleBy2Pts(subGeom.center, subGeom.majorAxisFinalPt)

      # I search for the angles that contain the selected point
      i = 0
      while i < len(distFromStartSortedList) - 1:
         if qad_utils.isAngleBetweenAngles(distFromStartSortedList[i], distFromStartSortedList[i + 1], distFromStart):
            if subGeomType == "CIRCLE":
               return [QadArc().set(subGeom.center, subGeom.radius, distFromStartSortedList[i + 1], distFromStartSortedList[i]), None, atGeom, atSubGeom]
            else:
               return [QadEllipseArc().set(subGeom.center, subGeom.majorAxisFinalPt, subGeom.axisRatio, distFromStartSortedList[i + 1] - ellipseAngle, distFromStartSortedList[i] - ellipseAngle), None, atGeom, atSubGeom]
         i = i + 1

      if qad_utils.isAngleBetweenAngles(distFromStartSortedList[-1], distFromStartSortedList[0], distFromStart):
         if subGeomType == "CIRCLE":
            return [QadArc().set(subGeom.center, subGeom.radius, distFromStartSortedList[0], distFromStartSortedList[-1]), None, atGeom, atSubGeom]
         else:
            return [QadEllipseArc().set(subGeom.center, subGeom.majorAxisFinalPt, subGeom.axisRatio, distFromStartSortedList[0] - ellipseAngle, distFromStartSortedList[-1] - ellipseAngle), None, atGeom, atSubGeom]

#       if qad_utils.isAngleBetweenAngles(distFromStartList[0], distFromStartList[1], distFromStart):
#          firstAngle = distFromStartList[0]
#          secondAngle = distFromStartList[1]
#       else:
#          firstAngle = distFromStartList[1]
#          secondAngle = distFromStartList[0]

#       if subGeomType == "CIRCLE":
#          return [QadArc().set(subGeom.center, subGeom.radius, secondAngle, firstAngle), None, atGeom, atSubGeom]
#       else:
#          return [QadEllipseArc().set(subGeom.center, subGeom.majorAxisFinalPt, subGeom.axisRatio, secondAngle, firstAngle), None, atGeom, atSubGeom]

   distFromStart = subGeom.getDistanceFromStart(nearPt)

   i = 0
   firstPt = subGeom.getStartPt()
   while i < len(distFromStartSortedList):
      if distFromStart <= distFromStartSortedList[i]:
         break
      firstPt = intPtSortedList[i]
      i = i + 1

   if i < len(distFromStartSortedList):
      secondPt = intPtSortedList[i]
   else:
      secondPt = subGeom.getEndPt()

   if firstPt == subGeom.getStartPt() and secondPt == subGeom.getEndPt(): return None

   if firstPt == subGeom.getStartPt():
      return [subGeom.getGeomBetween2Pts(secondPt, subGeom.getEndPt()), None, atGeom, atSubGeom]
   elif secondPt == subGeom.getEndPt():
      return [subGeom.getGeomBetween2Pts(subGeom.getStartPt(), firstPt), None, atGeom, atSubGeom]
   else:
      g1 = subGeom.getGeomBetween2Pts(subGeom.getStartPt(), firstPt)
      g2 = subGeom.getGeomBetween2Pts(secondPt, subGeom.getEndPt())
      return [g1, g2, atGeom, atSubGeom]


# ===============================================================================
# getIntersectionPtsTrimQadGeometry
# ===============================================================================
def getIntersectionPtsTrimQadGeometry(qadGeom, limitGeom, edgeMode):
   """the function calculates the intersection points between <qadGeom> and the <limitGeom> geometry according to the <edgeMode> mode.
      <linearObject> = QAD base geometry to extend (line, arc, ellipse arc, circle, ellipse)
      <limitGeom> = QAD geometry to use as extension limit
      <edgeMode> if = 0 the geometry must extend until it meets the closest object
                 if = 1 the geometry must be extended until it meets the closest object o
                 also its extension
   """
   if qadGeom is None or limitGeom is None:
      return []

   if edgeMode == 0: # without extending limitGeom
      return QadIntersections.twoGeomObjects(qadGeom, limitGeom)
   else: # extending limitGeom
      return QadIntersections.geomObjectWithGeomObjectExtensions(qadGeom, limitGeom)
