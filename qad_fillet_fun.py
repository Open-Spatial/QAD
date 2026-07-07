# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin ok

 functions for fillet operations

                              -------------------
        begin                : 2019-08-20
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

import math

from .qad_arc import QadArc
from .qad_multi_geom import *
from .qad_geom_relations import *
from .qad_entity import *
from .qad_offset_fun import offsetBridgeTheGapBetweenLines


# ============================================================================
# isStartedPtChanged
# ============================================================================
def isStartedPtChanged(oldQadGeom, newQadGeom, filletQadGeom, nearNewQadGeom):
   """Help function for the filletQadGeometry and fillet2QadGeometries functions.

      Given a qad geometry and the new geometries obtained from the fillet operation,
      the function returns True if the starting point of the qad geometry has been changed and False
      if the end point has been changed.
   """
   # if the new geometry compared to oldQadGeom has not changed
   if qad_utils.ptNear(oldQadGeom.getStartPt(), newQadGeom.getStartPt()) and \
      qad_utils.ptNear(oldQadGeom.getEndPt(), newQadGeom.getEndPt()):
      if filletQadGeom is not None: # if a connecting element exists
         # check if the starting point of oldQadGeom is connected with this connection element
         if qad_utils.ptNear(oldQadGeom.getStartPt(), filletQadGeom.getStartPt()) or \
            qad_utils.ptNear(oldQadGeom.getStartPt(), filletQadGeom.getEndPt()):
            changedStartPt = True
         else:
            changedStartPt = False
      else: # if there is no connection element
         # check if the starting point of oldQadGeom is connected to the new neighboring geometry nearNewQadGeom
         if qad_utils.ptNear(oldQadGeom.getStartPt(), nearNewQadGeom.getStartPt()) or \
            qad_utils.ptNear(oldQadGeom.getStartPt(), nearNewQadGeom.getEndPt()):
            changedStartPt = True
         else:
            changedStartPt = False
   else: # if the new geometry has changed check at which point
      if qad_utils.ptNear(oldQadGeom.getStartPt(), newQadGeom.getStartPt()) == False:
         changedStartPt = True
      else:
         changedStartPt = False

   return changedStartPt


# ============================================================================
# filletQadGeometry
# ============================================================================
def filletQadPolyline(qadPolyline, partAt1, pointAt1, partAt2, pointAt2, \
                      filletMode, radius):
   """Give a qad geometry, 2 parts and two 2 points where the connection between the two must be made
      parts, the function returns a polyline as a result of the fillet.
      <filletMode> fillet mode; 1=Cut-extend, 2=Do not cut-extend
      <radius> fillet radius
   """
   if partAt1 == partAt2: return None

   basicQadGeom1 = qadPolyline.getLinearObjectAt(partAt1)
   basicQadGeom2 = qadPolyline.getLinearObjectAt(partAt2)

   res = filletBridgeTheGapBetween2BasicQadGeometries(basicQadGeom1, pointAt1, basicQadGeom2, pointAt2, filletMode, radius)

   if res is None: # raccordo non possibile
      return None

   filletPolyline = qadPolyline.copy()

   if res[0] is not None:
      filletPolyline.remove(partAt1)
      filletPolyline.insert(partAt1, res[0])

      # if the starting point of basicQadGeom1 has been changed
      if isStartedPtChanged(basicQadGeom1, res[0], res[1], res[2]):
         # only the end point of partAt1 can be varied (if it is less than partAt2)
         if partAt1 < partAt2: return None
      else: # if the end point of basicQadGeom1 has been varied
         # only the starting point of partAt1 can be varied (if it is greater than partAt2)
         if partAt1 > partAt2: return None

   if res[2] is not None:
      filletPolyline.remove(partAt2)
      filletPolyline.insert(partAt2, res[2])

      # if the starting point of basicQadGeom2 has been changed
      if isStartedPtChanged(basicQadGeom2, res[2], res[1], res[0]):
         # only the end point of partAt2 can be varied (if it is less than partAt1)
         if partAt2 < partAt1: return None
      else: # if the end point of basicQadGeom1 has been varied
         # only the starting point of partAt2 can be varied (if it is greater than partAt1)
         if partAt2 > partAt1: return None

   # I remove all the parts that are between partAt1 and partAt2
   if partAt1 < partAt2:
      for i in range(partAt1 + 1, partAt2):
         filletPolyline.remove(i)
      if res[1] is not None: # insert a fillet arc
         filletPolyline.insert(partAt1 + 1, res[1])
   else:
      for i in range(partAt2 + 1, partAt1):
         filletPolyline.remove(i)
      if res[1] is not None: # insert a fillet arc
         filletPolyline.insert(partAt2 + 1, res[1])

   # verifico e correggo i versi delle parti della polilinea
   filletPolyline.reverseCorrection()

   return filletPolyline


# ============================================================================
# fillet2QadGeometries
# ============================================================================
def fillet2QadGeometries(qadGeom1, atGeom1, atSubGeom1, partAt1, pointAt1, \
                         qadGeom2, atGeom2, atSubGeom2, partAt2, pointAt2, \
                         filletMode, radius):
   """Given two qad geometries, the part and the point where the connection must be made between the two
      polylines, the function returns a polyline as a result of the fitting and two flags that
      they give indications on what needs to be done to the original polylines:
      (0=nothing, 1=modify, 2=delete)
      <filletMode> fillet mode; 1=Cut-extend, 2=Do not cut-extend
      <radius> fillet radius
   """
   gType1 = qadGeom1.whatIs()
   gType2 = qadGeom2.whatIs()

   if gType1 == "POLYLINE" or gType1 == "MULTI_LINEAR_OBJ" or gType1 == "POLYGON" or gType1 == "MULTI_POLYGON":
      subQadGeom1 = getQadGeomAt(qadGeom1, atGeom1, atSubGeom1)
      if subQadGeom1.whatIs() == "POLYLINE":
         basicQadGeom1 = subQadGeom1.getLinearObjectAt(partAt1)
      else:
         basicQadGeom1 = subQadGeom1

   else:
      subQadGeom1 = basicQadGeom1 = qadGeom1
   subQadGeomType1 = subQadGeom1.whatIs()

   if gType2 == "POLYLINE" or gType2 == "MULTI_LINEAR_OBJ" or gType2 == "POLYGON" or gType2 == "MULTI_POLYGON":
      subQadGeom2 = getQadGeomAt(qadGeom2, atGeom2, atSubGeom2)
      if subQadGeom2.whatIs() == "POLYLINE":
         basicQadGeom2 = subQadGeom2.getLinearObjectAt(partAt2)
      else:
         basicQadGeom2 = subQadGeom2
   else:
      subQadGeom2 = basicQadGeom2 = qadGeom2
   subQadGeomType2 = subQadGeom2.whatIs()

   res = filletBridgeTheGapBetween2BasicQadGeometries(basicQadGeom1, pointAt1, basicQadGeom2, pointAt2, filletMode, radius)

   if res is None: # raccordo non possibile
      return None

   filletPolyline = QadPolyline()

   if res[0] is None or \
      subQadGeomType1 == "CIRCLE" or subQadGeomType1 == "ELLIPSE" or subQadGeomType1 == "POLYGON":
      whatToDoGeom1 = 0 # 0=nothing
   else:
      whatToDoGeom1 = 1 # 0=nothing, 1=modify, 2=delete
      if subQadGeomType1 == "POLYLINE":
         # if the starting point of basicQadGeom1 has been changed
         if isStartedPtChanged(basicQadGeom1, res[0], res[1], res[2]):
            # I take all the parts after partAt1
            for i in range(subQadGeom1.qty() - 1, partAt1, -1):
               filletPolyline.append(subQadGeom1.getLinearObjectAt(i))
         else:
            # I take all the parts before partAt1
            for i in range(0, partAt1):
               filletPolyline.append(subQadGeom1.getLinearObjectAt(i))
      filletPolyline.append(res[0])

   if res[1] is not None: # fillet arc
      filletPolyline.append(res[1])

   if res[2] is None or \
      subQadGeomType2 == "CIRCLE" or subQadGeomType2 == "ELLIPSE" or subQadGeomType2 == "POLYGON":
      whatToDoGeom2 = 0 # 0=nothing
   elif res[2] is not None:
      # 0=nothing, 1=modify, 2=delete
      if whatToDoGeom1 == 1: # if geometry1 has been changed
         whatToDoGeom2 = 2 # geometry 2 joins 1 and must be deleted
      else:
         whatToDoGeom2 = 1

      filletPolyline.append(res[2])
      if subQadGeomType2 == "POLYLINE":
         # if the starting point of basicQadGeom2 has been changed
         if isStartedPtChanged(basicQadGeom2, res[2], res[1], res[0]):
            # I take all the parts after partAt2
            for i in range(partAt2 + 1, subQadGeom2.qty()):
               filletPolyline.append(subQadGeom2.getLinearObjectAt(i))
         else:
            # I take all the parts before partAt2
            for i in range(partAt2 - 1, -1, -1):
               filletPolyline.append(subQadGeom2.getLinearObjectAt(i))

   # verifico e correggo i versi delle parti della polilinea
   filletPolyline.reverseCorrection()

   # 1=modify
   if whatToDoGeom1 == 1 and (gType1 == "MULTI_LINEAR_OBJ" or gType1 == "POLYGON" or gType1 == "MULTI_POLYGON"):
      updGeom = setQadGeomAt(qadGeom1, filletPolyline, atGeom1, atSubGeom1)
      return updGeom, whatToDoGeom1, whatToDoGeom2
   elif whatToDoGeom2 == 1 and (gType2 == "MULTI_LINEAR_OBJ" or gType2 == "POLYGON" or gType2 == "MULTI_POLYGON"):
      updGeom = setQadGeomAt(qadGeom2, filletPolyline, atGeom2, atSubGeom2)
      return updGeom, whatToDoGeom1, whatToDoGeom2
   else:
      return filletPolyline, whatToDoGeom1, whatToDoGeom2


# ============================================================================
# filletBridgeTheGapBetween2BasicQadGeometries
# ============================================================================
def filletBridgeTheGapBetween2BasicQadGeometries(qadGeom1, pointAt1, qadGeom2, pointAt2, filletMode, radius):
   """Given two basic geometries of qad, the part and the point where the connection between the two must be made
      polylines, the function returns a polyline as a result of the fitting and two flags that
      they give indications on what needs to be done to the original polylines:
      (0=nothing, 1=modify, 2=delete)
      <filletMode> fillet mode; 1=Cut-extend, 2=Do not cut-extend
      <radius> fillet radius

      It returns a list of 3 elements (None in case of error):
      a geometry 1 that replaces <qadGeom1>, if = None <qadGeom1> must be removed
      an arc, if = None there is no connecting arc between the two lines
      a geometry 2 that replaces <qadGeom2>, if = None <qadGeom2> must be removed
   """
   gType1 = qadGeom1.whatIs()
   gType2 = qadGeom2.whatIs()

   if gType1 == "CIRCLE":
      if gType2 == "CIRCLE":
         res = filletBridgeTheGapBetweenCircles(qadGeom1, pointAt1, qadGeom2, pointAt2, radius)
      elif gType2 == "ELLIPSE":
         res = filletBridgeTheGapBetweenCircleEllipse(qadGeom1, pointAt1, qadGeom2, pointAt2, radius, filletMode)
      elif gType2 == "ARC":
         res = filletBridgeTheGapBetweenArcCircle(qadGeom2, pointAt2, qadGeom1, pointAt1, radius, filletMode)
         if res is not None:
            dummy = res[0] # I invert the first and third elements
            res[0] = res[2]
            res[2] = dummy
      elif gType2 == "ELLIPSE_ARC":
         res = filletBridgeTheGapBetweenCircleEllipsearc(qadGeom1, pointAt1, qadGeom2, pointAt2, radius, filletMode)
      elif gType2 == "LINE":
         res = filletBridgeTheGapBetweenCircleLine(qadGeom1, pointAt1, qadGeom2, pointAt2, radius, filletMode)

   elif gType1 == "ELLIPSE":
      if gType2 == "CIRCLE":
         res = filletBridgeTheGapBetweenCircleEllipse(qadGeom2, pointAt2, qadGeom1, pointAt1, radius, filletMode)
         if res is not None:
            dummy = res[0] # I invert the first and third elements
            res[0] = res[2]
            res[2] = dummy
      elif gType2 == "ELLIPSE":
         res = filletBridgeTheGapBetweenEllipses(qadGeom1, pointAt1, qadGeom2, pointAt2, radius)
      elif gType2 == "ARC":
         res = filletBridgeTheGapBetweenArcEllipse(qadGeom2, pointAt2, qadGeom1, pointAt1, radius, filletMode)
         if res is not None:
            dummy = res[0] # I invert the first and third elements
            res[0] = res[2]
            res[2] = dummy
      elif gType2 == "ELLIPSE_ARC":
         res = filletBridgeTheGapBetweenEllipseEllipsearc(qadGeom1, pointAt1, qadGeom2, pointAt2, radius, filletMode)
      elif gType2 == "LINE":
         res = filletBridgeTheGapBetweenEllipseLine(qadGeom1, pointAt1, qadGeom2, pointAt2, radius, filletMode)

   elif gType1 == "ARC":
      if gType2 == "CIRCLE":
         res = filletBridgeTheGapBetweenArcCircle(qadGeom1, pointAt1, qadGeom2, pointAt2, radius, filletMode)
      elif gType2 == "ELLIPSE":
         res = filletBridgeTheGapBetweenArcEllipse(qadGeom2, pointAt2, qadGeom1, pointAt1, radius, filletMode)
      elif gType2 == "ARC":
         res = filletBridgeTheGapBetweenArcs(qadGeom1, pointAt1, qadGeom2, pointAt2, radius, filletMode)
      elif gType2 == "ELLIPSE_ARC":
         res = filletBridgeTheGapBetweenArcEllipsearc(qadGeom1, pointAt1, qadGeom2, pointAt2, radius, filletMode)
      elif gType2 == "LINE":
         res = filletBridgeTheGapBetweenArcLine(qadGeom1, pointAt1, qadGeom2, pointAt2, radius, filletMode)

   elif gType1 == "ELLIPSE_ARC":
      if gType2 == "CIRCLE":
         res = filletBridgeTheGapBetweenCircleEllipsearc(qadGeom2, pointAt2, qadGeom1, pointAt1, radius, filletMode)
         if res is not None:
            dummy = res[0] # I invert the first and third elements
            res[0] = res[2]
            res[2] = dummy
      elif gType2 == "ELLIPSE":
         res = filletBridgeTheGapBetweenEllipseEllipsearc(qadGeom2, pointAt2, qadGeom1, pointAt1, radius, filletMode)
         if res is not None:
            dummy = res[0] # I invert the first and third elements
            res[0] = res[2]
            res[2] = dummy
      elif gType2 == "ARC":
         res = filletBridgeTheGapBetweenArcEllipsearc(qadGeom1, pointAt1, qadGeom2, pointAt2, radius, filletMode)
         if res is not None:
            dummy = res[0] # I invert the first and third elements
            res[0] = res[2]
            res[2] = dummy
      elif gType2 == "ELLIPSE_ARC":
         res = filletBridgeTheGapBetweenEllipsearcs(qadGeom1, pointAt1, qadGeom2, pointAt2, radius, filletMode)
      elif gType2 == "LINE":
         res = filletBridgeTheGapBetweenLineEllipsearc(qadGeom2, pointAt2, qadGeom1, pointAt1, radius, filletMode)
         if res is not None:
            dummy = res[0] # I invert the first and third elements
            res[0] = res[2]
            res[2] = dummy

   elif gType1 == "LINE":
      if gType2 == "CIRCLE":
         res = filletBridgeTheGapBetweenCircleLine(qadGeom1, pointAt1, qadGeom2, pointAt2, radius, filletMode)
         if res is not None:
            dummy = res[0] # I invert the first and third elements
            res[0] = res[2]
            res[2] = dummy
      elif gType2 == "ELLIPSE":
         res = filletBridgeTheGapBetweenEllipseLine(qadGeom1, pointAt1, qadGeom2, pointAt2, radius, filletMode)
         if res is not None:
            dummy = res[0] # I invert the first and third elements
            res[0] = res[2]
            res[2] = dummy
      elif gType2 == "ARC":
         res = filletBridgeTheGapBetweenArcLine(qadGeom2, pointAt2, qadGeom1, pointAt1, radius, filletMode)
         if res is not None:
            dummy = res[0] # I invert the first and third elements
            res[0] = res[2]
            res[2] = dummy
      elif gType2 == "ELLIPSE_ARC":
         res = filletBridgeTheGapBetweenLineEllipsearc(qadGeom1, pointAt1, qadGeom2, pointAt2, radius, filletMode)
      elif gType2 == "LINE":
         if radius == 0:
            res = filletBridgeTheGapBetweenLines(qadGeom1, pointAt1, qadGeom2, pointAt2, radius, 0)
         else:
            res = filletBridgeTheGapBetweenLines(qadGeom1, pointAt1, qadGeom2, pointAt2, radius, 1)

   return res


# ===============================================================================
# START - 2 CIRCLES
# ===============================================================================


# ===============================================================================
# filletBridgeTheGapBetweenCircles
# ===============================================================================
def filletBridgeTheGapBetweenCircles(circle1, ptOnCircle1, circle2, ptOnCircle2, radius):
   """the function connects two circles through
      a connecting arc of radius <radius> that comes closest to the selection points
      on the circles.

      It returns a list of 3 elements (None in case of error):
      None
      an arc, if = None there is no connecting arc between the two lines
      None
   """
   # ricavo i possibili arci di raccordo
   filletArcs = getFilletArcsBetweenCircles(circle1, circle2, radius)

   # I look for the valid arc closest to ptOnCircle1 and ptOnCircle2
   AvgList = []
   Avg = sys.float_info.max

   resFilletArc = QadArc()
   for filletArc in filletArcs:
      if circle1.isPtOnCircle(filletArc.getStartPt()):
         distFromPtOnCircle1 = circle1.lengthBetween2Points(filletArc.getStartPt(), \
                                                            ptOnCircle1, \
                                                            filletArc.getTanDirectionOnStartPt() + math.pi)
         distFromPtOnCircle2 = circle2.lengthBetween2Points(filletArc.getEndPt(), \
                                                            ptOnCircle2, \
                                                            filletArc.getTanDirectionOnEndPt())
      else:
         distFromPtOnCircle1 = circle1.lengthBetween2Points(filletArc.getEndPt(), \
                                                            ptOnCircle1, \
                                                            filletArc.getTanDirectionOnEndPt())
         distFromPtOnCircle2 = circle2.lengthBetween2Points(filletArc.getStartPt(), \
                                                            ptOnCircle2, \
                                                            filletArc.getTanDirectionOnStartPt()+ math.pi)

      del AvgList[:]
      AvgList.append(distFromPtOnCircle1)
      AvgList.append(distFromPtOnCircle2)

      currAvg = qad_utils.numericListAvg(AvgList)
      if currAvg < Avg: # closer on average
         Avg = currAvg
         resFilletArc.set(filletArc)

   if Avg == sys.float_info.max:
      return None

   return [None, resFilletArc, None]


# ===============================================================================
# getFilletArcsBetweenCircles
# ===============================================================================
def getFilletArcsBetweenCircles(circle1, circle2, radius):
   """the function connects two circles through a connecting arc of radius <radius>.

      Returns a list of possible arcs
   """
   res = []

   # case 1: connection between <circle1> and <circle2> forming an inflection with each of the circles
   # create a new circle concentric to circle1 with radius increased by <radius>
   newCircle1 = QadCircle(circle1)
   newCircle1.radius = newCircle1.radius + radius
   # create a new circle concentric to circle2 with radius increased by <radius>
   newCircle2 = QadCircle(circle2)
   newCircle2.radius = newCircle2.radius + radius

   res.extend(auxFilletArcsBetweenCircles(newCircle1, newCircle2, radius))

   # case 2: connection between <circle1> and <circle2> without forming an inflection with each of the circles
   if radius - circle1.radius > 0 and radius - circle2.radius > 0:
      # create a new circle concentric to circle1 with radius = <radius> - radius of circle1
      newCircle1 = QadCircle(circle1)
      newCircle1.radius = radius - newCircle1.radius
      # create a new circle concentric to circle2 with radius = <radius> - radius of circle2
      newCircle2 = QadCircle(circle2)
      newCircle2.radius = radius - newCircle2.radius

      res.extend(auxFilletArcsBetweenCircles(newCircle1, newCircle2, radius))

   # case 3: connection between <circle1> and <circle2> forming an inflection only with circle1
   if radius - circle2.radius > 0:
      # create a new circle concentric to circle1 with radius increased by <radius>
      newCircle1 = QadCircle(circle1)
      newCircle1.radius = newCircle1.radius + radius
      # create a new circle concentric to circle2 with radius = <radius> - radius of circle2
      newCircle2 = QadCircle(circle2)
      newCircle2.radius = radius - newCircle2.radius

      res.extend(auxFilletArcsBetweenCircles(newCircle1, newCircle2, radius))

   # case 4: connection between <circle1> and <circle2> forming an inflection only with circle2
   if radius - circle1.radius > 0:
      # create a new circle concentric to circle1 with radius increased by <radius>
      newCircle1 = QadCircle(circle1)
      newCircle1.radius = radius - newCircle1.radius
      # create a new circle concentric to circle2 with radius = <radius> - radius of circle2
      newCircle2 = QadCircle(circle2)
      newCircle2.radius = newCircle2.radius + radius

      res.extend(auxFilletArcsBetweenCircles(newCircle1, newCircle2, radius))

   # case 5: connection between <circle1> and <circle2> inside <circle1> forming an inflection only with circle2
   if qad_utils.getDistance(circle1.center, circle2.center) + circle2.radius <= circle1.radius and \
      circle1.radius - radius > 0:
      # create a new circle concentric to circle1 with radius decreased by <radius>
      newCircle1 = QadCircle(circle1)
      newCircle1.radius = newCircle1.radius - radius
      # create a new circle concentric to circle2 with radius increased by <radius>
      newCircle2 = QadCircle(circle2)
      newCircle2.radius = newCircle2.radius + radius

      res.extend(auxFilletArcsBetweenCircles(newCircle1, newCircle2, radius))

   # case 6: connection between <circle1> inside <circle2> and <circle2> forming an inflection only with circle1
   if qad_utils.getDistance(circle1.center, circle2.center) + circle1.radius <= circle2.radius and \
      circle2.radius - radius > 0:
      # create a new circle concentric to circle1 with radius increased by <radius>
      newCircle1 = QadCircle(circle1)
      newCircle1.radius = newCircle1.radius + radius
      # create a new circle concentric to circle2 with radius decreased by <radius>
      newCircle2 = QadCircle(circle2)
      newCircle2.radius = newCircle2.radius - radius

      res.extend(auxFilletArcsBetweenCircles(newCircle1, newCircle2, radius))

   # caso 7: raccordo tra <circle1> e <circle2> inside a <circle1> without forming any inflection
   if qad_utils.getDistance(circle1.center, circle2.center) + circle2.radius <= circle1.radius and \
      circle1.radius - radius > 0 and radius - circle2.radius:
      # create a new circle concentric to circle1 with radius decreased by <radius>
      newCircle1 = QadCircle(circle1)
      newCircle1.radius = newCircle1.radius - radius
      # create a new circle concentric to circle2 with radius = <radius> - radius of circle2
      newCircle2 = QadCircle(circle2)
      newCircle2.radius = radius - newCircle2.radius

      res.extend(auxFilletArcsBetweenCircles(newCircle1, newCircle2, radius))

   return res


# ===============================================================================
# auxFilletArcsBetweenCircles
# ===============================================================================
def auxFilletArcsBetweenCircles(circle1, circle2, radius, both = True):
   """the helper function to getFilletArcsBetweenCircles
      Returns a list of possible connecting arcs between the circles <circle1> and <circle2>
   """
   res = []
   # calculate the intersections between the two circles
   # which will give rise to the centers of the fillet arces
   intPts = QadIntersections.twoCircles(circle1, circle2)

   if len(intPts) > 0:
      # a point of tangency is given by the point at a radius distance from the center of the fillet arc
      # in the direction of the center of the arc <circle1>
      angle = qad_utils.getAngleBy2Pts(intPts[0], circle1.center)
      tanC1Pt = qad_utils.getPolarPointByPtAngle(intPts[0], angle, radius)
      # a point of tangency is given by the point at a radius distance from the center of the fillet arc
      # in the direction of the center of the arc <circle2>
      angle = qad_utils.getAngleBy2Pts(intPts[0], circle2.center)
      tanC2Pt = qad_utils.getPolarPointByPtAngle(intPts[0], angle, radius)
      filletArc = QadArc()
      if filletArc.fromStartCenterEndPts(tanC1Pt, intPts[0], tanC2Pt) == True:
         res.append(filletArc)
      if both:
         # I invert the initial-final angle
         filletArc = QadArc(filletArc)
         filletArc.inverseAngles()
         res.append(filletArc)

      if len(intPts) > 1:
         # a point of tangency is given by the point at a radius distance from the center of the fillet arc
         # in the direction of the center of the arc <circle1>
         angle = qad_utils.getAngleBy2Pts(intPts[1], circle1.center)
         tanC1Pt = qad_utils.getPolarPointByPtAngle(intPts[1], angle, radius)
         # a point of tangency is given by the point at a radius distance from the center of the fillet arc
         # in the direction of the center of the arc <circle2>
         angle = qad_utils.getAngleBy2Pts(intPts[1], circle2.center)
         tanC2Pt = qad_utils.getPolarPointByPtAngle(intPts[1], angle, radius)
         filletArc = QadArc()
         if filletArc.fromStartCenterEndPts(tanC1Pt, intPts[1], tanC2Pt) == True:
            res.append(filletArc)
         if both:
            # I invert the initial-final angle
            filletArc = QadArc(filletArc)
            filletArc.inverseAngles()
            res.append(filletArc)

   return res


# ===============================================================================
# END - 2 CIRCLES
# BEGINNING - CIRCLE AND ELLIPSE
# ===============================================================================


# ===============================================================================
# filletBridgeTheGapBetweenCircleEllipse
# ===============================================================================
def filletBridgeTheGapBetweenCircleEllipse(circle, ptOnCircle, ellipse, ptOnEllipse, radius):
   """the function fillets a circle with an ellipse through
      a connecting arc of radius <radius> that comes closest to the selection points
      on the two geometries.

      It returns a list of 3 elements (None in case of error):
      None
      an arc, if = None there is no connecting arc between the two lines
      None
   """
   # TODO
   return [None, None, None]


# ===============================================================================
# END - CIRCLE AND ELLIPSE
# START - 2 LINES
# ===============================================================================


# ===============================================================================
# filletBridgeTheGapBetweenLines
# ===============================================================================
def filletBridgeTheGapBetweenLines(line1, ptOnLine1, line2, ptOnLine2, radius, filletMode):
   """the function connects 2 straight segments (QadLine) across
      a connecting arc of radius <radius> that comes closest to the selection points
      on segment 1 <ptOnLine1> and on segment 2 <ptOnLine2>.
      <filletMode> fillet mode; 1=Cut-extend, 2=Do not cut-extend

      It returns a list of 3 elements (None in case of error):
      a line that replaces <line1>, if = None <line1> should be removed
      an arc, if = None there is no connecting arc between the two lines
      a line that replaces <line2>, if = None <line2> should be removed
   """
   if radius == 0: # Estende i segmenti
      # I look for the intersection point between the two lines
      ptInt = QadIntersections.twoInfinityLines(line1, line2)
      if ptInt is None: # linee parallele
         return None

      distBetweenLine1Pt1AndPtInt = qad_utils.getDistance(line1.getStartPt(), ptInt)
      distBetweenLine1Pt2AndPtInt = qad_utils.getDistance(line1.getEndPt(), ptInt)
      distBetweenLine2Pt1AndPtInt = qad_utils.getDistance(line2.getStartPt(), ptInt)
      distBetweenLine2Pt2AndPtInt = qad_utils.getDistance(line2.getEndPt(), ptInt)

      if distBetweenLine1Pt1AndPtInt > distBetweenLine1Pt2AndPtInt:
         # second point of line1 closest to the intersection point
         resLine1 = QadLine().set(line1.getStartPt(), ptInt)
      else:
         # first point of line1 closest to the intersection point
         resLine1 = QadLine().set(ptInt, line1.getEndPt())

      if distBetweenLine2Pt1AndPtInt > distBetweenLine2Pt2AndPtInt:
         # second point of line2 closest to the intersection point
         resLine2 = QadLine().set(line2.getStartPt(), ptInt)
      else:
         # first point of line2 closest to the intersection point
         resLine2 = QadLine().set(ptInt, line2.getEndPt())

      return [resLine1, None, resLine2]
   else: # Raccorda i segmenti
      filletArcs = getFilletArcsBetweenLines(line1, line2, radius)

      # I look for the valid edge closest to ptOnLine1 and ptOnLine2
      AvgList = []
      Avg = sys.float_info.max

      resLine1 = QadLine()
      resFilletArc = QadArc()
      resLine2 = QadLine()
      for filletArc in filletArcs:
         # get the new segment so that it is tangent with the fillet arc
         newLine1, distFromPtOnLine1 = getNewLineAccordingFilletArc(line1, filletArc, ptOnLine1)
         if newLine1 is None:
            continue
         # get the new segment so that it is tangent with the fillet arc
         newLine2, distFromPtOnLine2 = getNewLineAccordingFilletArc(line2, filletArc, ptOnLine2)
         if newLine2 is None:
            continue

         del AvgList[:]
         AvgList.append(distFromPtOnLine1)
         AvgList.append(distFromPtOnLine2)

         currAvg = qad_utils.numericListAvg(AvgList)
         if currAvg < Avg: # closer on average
            Avg = currAvg
            resLine1.set(newLine1)
            resFilletArc.set(filletArc)
            resLine2.set(newLine2)

      if Avg == sys.float_info.max:
         return None

      if filletMode == 1: # 1=Trim-extend
         return [resLine1, resFilletArc, resLine2]
      else:
         return [None, resFilletArc, None]


# ===============================================================================
# getFilletArcsBetweenLines
# ===============================================================================
def getFilletArcsBetweenLines(line1, line2, radius):
   """the function connects two straight lines (QadLine) through
      a connecting arc of radius <radius>.

      Returns a list of possible arcs
   """
   res = []

   # I look for the intersection point between the two lines
   intPt = QadIntersections.twoInfinityLines(line1, line2)
   if intPt is None: # linee parallele
      # calculate the perpendicular projection of the starting point of <line1> onto <line2>
      ptPerp = QadPerpendicularity.fromPointToInfinityLine(line1.getStartPt(), line2)
      d = qad_utils.getDistance(line1.getStartPt(), ptPerp)
      # d must be 2 times <radius>
      if qad_utils.doubleNear(radius * 2, d):
         angle = qad_utils.getAngleBy2Pts(line1.getStartPt(), ptPerp)
         ptCenter = gad_utils.getPolarPointByPtAngle(line1.getStartPt(), angle, radius)
         filletArc = QadArc()
         if filletArc.fromStartCenterEndPts(line1.getStartPt(), ptCenter, ptPerp) == True:
            res.append(filletArc)
         # same arc with the starting and ending points reversed
         filletArc = QadArc()
         if filletArc.fromStartCenterEndPts(ptPerp, ptCenter, line1.getStartPt()) == True:
            res.append(filletArc)

         ptPerp = qad_utils.getPolarPointByPtAngle(line1.getEndPt(), angle, d)
         ptCenter = qad_utils.getPolarPointByPtAngle(line1.getEndPt(), angle, radius)
         filletArc = QadArc()
         if filletArc.fromStartCenterEndPts(line1.getEndPt(), ptCenter, ptPerp) == True:
            res.append(filletArc)
         # same arc with the starting and ending points reversed
         filletArc = QadArc()
         if filletArc.fromStartCenterEndPts(ptPerp, ptCenter, line1.getEndPt()) == True:
            res.append(filletArc)
   else: # linee non parallele
      angleLine1 = line1.getTanDirectionOnPt()
      angleLine2 = line2.getTanDirectionOnPt()

      ptLine1 = qad_utils.getPolarPointByPtAngle(intPt, angleLine1, 1)
      ptLine2 = qad_utils.getPolarPointByPtAngle(intPt, angleLine2, 1)
      res.extend(auxFilletArcsBetweenLines(ptLine1, ptLine2, intPt, radius))

      ptLine2 = qad_utils.getPolarPointByPtAngle(intPt, angleLine2, -1)
      res.extend(auxFilletArcsBetweenLines(ptLine1, ptLine2, intPt, radius))

      ptLine1 = qad_utils.getPolarPointByPtAngle(intPt, angleLine1, -1)
      res.extend(auxFilletArcsBetweenLines(ptLine1, ptLine2, intPt, radius))

      ptLine2 = qad_utils.getPolarPointByPtAngle(intPt, angleLine2, 1)
      res.extend(auxFilletArcsBetweenLines(ptLine1, ptLine2, intPt, radius))

   return res


# ===============================================================================
# getNewLineAccordingFilletArc
# ===============================================================================
def getNewLineAccordingFilletArc(line, filletArc, ptOnLine):
   """given a straight segment (<line>) and an arc that si
      fille it to it (<filleArc>), the function returns a new straight segment
      modifying <line> so that it is tangent to the fitting arc.
      Also, using a point indicated on the <ptOnLine> segment returns
      the distance of that point from the point of tangency with the connecting arc.
   """
   newLine = QadLine()

   # I determine which point (initial or final) of the fillet arc
   # intersects on the extension of the straight segment
   if line.isPtOnInfinityLine(filletArc.getStartPt()):
      filletPtOnLine = filletArc.getStartPt()
      isStartFilletPtOnLine = True
   else:
      filletPtOnLine = filletArc.getEndPt()
      isStartFilletPtOnLine = False

   if line.containsPt(filletPtOnLine) == True: # if the point is inside the segment
      newLine.set(filletPtOnLine, line.getEndPt())

      if isStartFilletPtOnLine: # if the starting point of the fillet arc is on the line
         # if the new segment is not a valid segment
         if qad_utils.ptNear(newLine.getStartPt(), newLine.getEndPt()):
            # if the fillet arc is tangent to the final point of the new segment
            if qad_utils.TanDirectionNear(line.getTanDirectionOnEndPt(), \
                                          qad_utils.normalizeAngle(filletArc.getTanDirectionOnStartPt())) == True:
               newLine.set(line) # restore the original segment
         else:
            # if the fillet arc is not tangent to the starting point of the new segment
            if qad_utils.TanDirectionNear(newLine.getTanDirectionOnStartPt(), \
                                          qad_utils.normalizeAngle(filletArc.getTanDirectionOnStartPt() + math.pi)) == False:
               newLine.set(line.getStartPt(), filletPtOnLine)

         # if the new segment is not a valid segment
         if qad_utils.ptNear(newLine.getStartPt(), newLine.getEndPt()) or \
            newLine.containsPt(ptOnLine) == False:
            return None, None

         # calculate the distance from the ptOnLine point
         distFromPtOnLine = qad_utils.getDistance(ptOnLine, filletPtOnLine)
      else: # if the final point of the fillet arc is on the line
         # if the new segment is not a valid segment
         if qad_utils.ptNear(newLine.getStartPt(), newLine.getEndPt()):
            # if the fillet arc is tangent to the final point of the new segment
            if qad_utils.TanDirectionNear(line.getTanDirectionOnEndPt(), \
                                          qad_utils.normalizeAngle(filletArc.getTanDirectionOnEndPt() + math.pi)) == True:
               newLine.set(line) # restore the original segment
         else:
            # if the fillet arc is not tangent to the starting point of the new segment
            if qad_utils.TanDirectionNear(newLine.getTanDirectionOnStartPt(), \
                                          filletArc.getTanDirectionOnEndPt()) == False:
               newLine.set(line.getStartPt(), filletPtOnLine)

         # if the new segment is not a valid segment
         if qad_utils.ptNear(newLine.getStartPt(), newLine.getEndPt()) or \
            newLine.containsPt(ptOnLine) == False:
            return None, None

         # calculate the distance from the ptOnLine point
         distFromPtOnLine = qad_utils.getDistance(ptOnLine, filletPtOnLine)

      return newLine, distFromPtOnLine
   else: # if the point is outside the segment
      if qad_utils.getDistance(line.getStartPt(), filletPtOnLine) < qad_utils.getDistance(line.getEndPt(), filletPtOnLine):
         newLine.set(filletPtOnLine, line.getEndPt())
      else:
         newLine.set(line.getStartPt(), filletPtOnLine)

      return getNewLineAccordingFilletArc(newLine, filletArc, ptOnLine)


# ===============================================================================
# auxFilletArcsBetweenLines
# ===============================================================================
def auxFilletArcsBetweenLines(ptLine1, ptLine2, intPt, radius, both = True):
   """the helper function to getFilletArcsBetweenLines
      Returns a list of possible connecting arcs between the
      line 1 going from <ptLine1> to the point of intersection with line 2 <intPt>
      e
      line2 that goes from <ptLine2> to the point of intersection with line 1 <intPt>
   """
   res = []

   angleLine1 = qad_utils.getAngleBy2Pts(intPt, ptLine1)
   angleLine2 = qad_utils.getAngleBy2Pts(intPt, ptLine2)

   line = QadLine().set(ptLine1, ptLine2)
   bisectorInfinityLinePts = qad_utils.getBisectorInfinityLine(ptLine1, intPt, ptLine2, True)
   bisectorLine = QadLine().set(bisectorInfinityLinePts[0], bisectorInfinityLinePts[1])
   # I look for the point of intersection between the bisector and
   # the straight line that joins the most distant points of the two lines
   pt = QadIntersections.twoInfinityLines(bisectorLine, line)
   angleBisectorLine = qad_utils.getAngleBy2Pts(intPt, pt)

   # calculate the angle (absolute value) between a side and the bisector
   alfa = angleLine1 - angleBisectorLine
   if alfa < 0:
      alfa = angleBisectorLine - angleLine1
   if alfa > math.pi:
      alfa = (2 * math.pi) - alfa

   # calculate the angle of the right triangle knowing that the sum of the internal angles = 180
   # - alpha - 90 degrees (right angle)
   distFromIntPt = math.tan(math.pi - alfa - (math.pi / 2)) * radius
   pt1Proj = qad_utils.getPolarPointByPtAngle(intPt, angleLine1, distFromIntPt)
   pt2Proj = qad_utils.getPolarPointByPtAngle(intPt, angleLine2, distFromIntPt)
   # Pitagora
   distFromIntPt = math.sqrt((distFromIntPt * distFromIntPt) + (radius * radius))
   secondPt = qad_utils.getPolarPointByPtAngle(intPt, angleBisectorLine, distFromIntPt - radius)
   filletArc = QadArc()
   if filletArc.fromStartSecondEndPts(pt1Proj, secondPt, pt2Proj) == True:
      res.append(filletArc)
   if both:
      # I invert the initial-final angle
      filletArc = QadArc(filletArc)
      filletArc.inverseAngles()
      res.append(filletArc)

   return res


# ===============================================================================
# END - 2 LINES
# BEGINNING - ARC AND CIRCLE
# ===============================================================================


# ===============================================================================
# filletBridgeTheGapBetweenArcCircle
# ===============================================================================
def filletBridgeTheGapBetweenArcCircle(arc, ptOnArc, circle, ptOnCircle, radius, filletMode):
   """the function fillets an arc and a circle through
      a connecting arc of radius <radius> that comes closest to the selection points
      on the arc <ptOnArc> and on the circle <ptCircle>.
      <filletMode> fillet mode; 1=Cut-extend, 2=Do not cut-extend

      It returns a list of 3 elements (None in case of error):
      an arc that replaces <arc>
      an arc, if = None there is no connecting arc between the two lines
      None
   """
   # ricavo i possibili arci di raccordo
   filletArcs = getFilletArcsBetweenArcCircle(arc, circle, radius)

   # I searc for the closest valid arc to ptOnArc and ptOnCircle
   AvgList = []
   Avg = sys.float_info.max

   resFilletArc = QadArc()
   resArc = QadArc()
   for filletArc in filletArcs:
      # get the new arc so that it is tangent with the fillet arc
      newArc, distFromPtOnArc = getNewArcAccordingFilletArc(arc, filletArc, ptOnArc)
      if newArc is None:
         continue

      # calculate the distance from the ptOnCircle point
      if circle.isPtOnCircle(filletArc.getStartPt()): # if the starting point of the fillet arc is on the circle
         distFromPtOnCircle = circle.lengthBetween2Points(filletArc.getStartPt(), \
                                                          ptOnCircle, \
                                                          filletArc.getTanDirectionOnStartPt() + math.pi)
      else: # if the final point of the fillet arc is on the circle
         distFromPtOnCircle = circle.lengthBetween2Points(filletArc.getEndPt(), \
                                                          ptOnCircle, \
                                                          filletArc.getTanDirectionOnEndPt())

      del AvgList[:]
      AvgList.append(distFromPtOnArc)
      AvgList.append(distFromPtOnCircle)

      currAvg = qad_utils.qad_utils.numericListAvg(AvgList)
      if currAvg < Avg: # closer on average
         Avg = currAvg
         resArc.set(newArc)
         resFilletArc.set(filletArc)

   if Avg == sys.float_info.max:
      return None

   if filletMode == 1: # 1=Trim-extend
      return [resArc, resFilletArc, None]
   else:
      return [None, resFilletArc, None]


# ===============================================================================
# getFilletArcsBetweenArcCircle
# ===============================================================================
def getFilletArcsBetweenArcCircle(arc, circle, radius):
   """the function fillets an arc and a circle through
      a connecting arc of radius <radius>.

      Returns a list of possible arcs
   """
   circle1 = QadCircle()
   circle1.set(arc.center, arc.radius)

   return getFilletArcsBetweenCircles(circle1, circle, radius)


# ===============================================================================
# getNewArcAccordingFilletArc
# ===============================================================================
def getNewArcAccordingFilletArc(arc, filletArc, ptOnArc):
   """given an arc (<arc>) and another arc that connects to it (<filleArc>),
      the function returns a new arc by modifying <arc> to be
      tangent to the connecting arc. Also, using a point indicated on the bow
      <ptOnArc> returns the distance of that point from the point of tangency with the arc
      fillet using the tangent direction of the fillet arc.
   """
   circle = QadCircle()
   circle.set(arc.center, arc.radius)

   newArc = QadArc(arc)

   # I determine which point (initial or final) of the fillet arc
   # intersects on the extension of the arc
   if circle.isPtOnCircle(filletArc.getStartPt()):
      filletPtOnArc = filletArc.getStartPt()
      isStartFilletPtOnArc = True
   else:
      filletPtOnArc = filletArc.getEndPt()
      isStartFilletPtOnArc = False

   # I verify that the fillet arc is tangent to the arc
   newArc.setStartAngleByPt(filletPtOnArc)

   if isStartFilletPtOnArc: # if the starting point of the fillet arc is on the arc
      # if the new arc is not a valid arc
      if qad_utils.doubleNear(newArc.startAngle, newArc.endAngle):
         # if the fillet arc is tangent to the final point of the arc
         if qad_utils.TanDirectionNear(arc.getTanDirectionOnEndPt(), \
                                       qad_utils.normalizeAngle(filletArc.getTanDirectionOnStartPt())) == True:
            newArc.startAngle = arc.startAngle # restore the original bow
      else:
         # if the fillet arc is not tangent to the starting point of the new arc
         if qad_utils.TanDirectionNear(newArc.getTanDirectionOnStartPt(), \
                                       qad_utils.normalizeAngle(filletArc.getTanDirectionOnStartPt() + math.pi)) == False:
            newArc.startAngle = arc.startAngle # restore the original bow
            newArc.setEndAngleByPt(filletPtOnArc)

      # if the new arc is not a valid arc
      if qad_utils.doubleNear(newArc.startAngle, newArc.endAngle):
         return None, None

      # calculate the distance from the ptOnArc point
      distFromPtOnArc = circle.lengthBetween2Points(filletArc.getStartPt(), \
                                                    ptOnArc, \
                                                    filletArc.getTanDirectionOnStartPt() + math.pi)
   else: # if the final point of the fillet arc is on the arc
      # if the new arc is not a valid arc
      if qad_utils.doubleNear(newArc.startAngle, newArc.endAngle):
         # if the fillet arc is tangent to the final point of the arc
         if qad_utils.TanDirectionNear(arc.getTanDirectionOnEndPt(), \
                                       qad_utils.normalizeAngle(filletArc.getTanDirectionOnEndPt() + math.pi)) == True:
            newArc.startAngle = arc.startAngle # restore the original bow
      else:
         # if the fillet arc is not tangent to the starting point of the new arc
         if qad_utils.TanDirectionNear(newArc.getTanDirectionOnStartPt(), \
                                       filletArc.getTanDirectionOnEndPt()) == False:
            newArc.startAngle = arc.startAngle # restore the original bow
            newArc.setEndAngleByPt(filletPtOnArc)

      # if the new arc is not a valid arc
      if qad_utils.doubleNear(newArc.startAngle, newArc.endAngle):
         return None, None

      # calculate the distance from the ptOnArc point
      distFromPtOnArc = circle.lengthBetween2Points(filletArc.getEndPt(), \
                                                    ptOnArc, \
                                                    filletArc.getTanDirectionOnEndPt())

   return newArc, distFromPtOnArc


# ===============================================================================
# END - ARC AND CIRCLE
# BEGINNING - CIRCLE AND ARC OF ELLIPSE
# ===============================================================================


# ===============================================================================
# filletBridgeTheGapBetweenCircleEllipsearc
# ===============================================================================
def filletBridgeTheGapBetweenCircleEllipsearc(circle, ptOnCircle, ellipseArc, ptOnEllipseArc, radius):
   """the function fillets a circle and an arc through ellipse
      a connecting arc of radius <radius> that comes closest to the selection points
      on the 2 geometries.

      It returns a list of 3 elements (None in case of error):
      None
      an arc, if = None there is no connecting arc between the two lines
      None
   """
   # TODO
   return [None, None, None]


# ===============================================================================
# END - CIRCLE AND ARC OF ELLIPSE
# BEGINNING - CIRCLE AND LINE
# ===============================================================================


# ===============================================================================
# filletBridgeTheGapBetweenCircleLine
# ===============================================================================
def filletBridgeTheGapBetweenCircleLine(circle, ptOnCircle, line, ptOnLine, radius, filletMode):
   """the function fillets a circle and a straight segment (QadLine) through
      a connecting arc of radius <radius> that comes closest to the selection points
      on the circle <ptOnCircle> and on the straight segment <ptOnLine>.
      <filletMode> fillet mode; 1=Cut-extend, 2=Do not cut-extend

      It returns a list of 3 elements (None in case of error):
      None
      an arc, if = None there is no connecting arc between the two lines
      a line that replaces <line> if filleMode = 1 (Cut-Extend) otherwise None
   """
   # ricavo i possibili arci di raccordo
   filletArcs = getFilletArcsBetweenCircleLine(circle, line, radius)

   # I searc for the closest valid arc to ptOnArc and ptOnLine
   AvgList = []
   Avg = sys.float_info.max

   resFilletArc = QadArc()
   resLine = QadLine()
   for filletArc in filletArcs:
      # get the new segment so that it is tangent with the fillet arc
      newLine, distFromPtOnLine = getNewLineAccordingFilletArc(line, filletArc, ptOnLine)
      if newLine is None:
         continue

      if circle.isPtOnCircle(filletArc.getStartPt()):
         distFromPtOnCircle = circle.lengthBetween2Points(filletArc.getStartPt(), \
                                                          ptOnCircle, \
                                                          filletArc.getTanDirectionOnStartPt() + math.pi)
      else:
         distFromPtOnCircle = circle.lengthBetween2Points(filletArc.getEndPt(), \
                                                          ptOnCircle, \
                                                          filletArc.getTanDirectionOnEndPt())

      del AvgList[:]
      AvgList.append(distFromPtOnLine)
      AvgList.append(distFromPtOnCircle)

      currAvg = qad_utils.numericListAvg(AvgList)
      if currAvg < Avg: # closer on average
         Avg = currAvg
         resLine.set(newLine)
         resFilletArc.set(filletArc)

   if Avg == sys.float_info.max:
      return None

   if filletMode == 1: # 1=Trim-extend
      return [None, resFilletArc, resLine]
   else:
      return [None, resFilletArc, None]


# ===============================================================================
# auxFilletArcsBetweenCircleLine
# ===============================================================================
def auxFilletArcsBetweenCircleLine(circle, line, origCircle, origLine, both = True):
   """the helper function to getFilletArcsBetweenArcLine
      Returns a list of possible connecting arcs between <circle> and <line>
   """
   res = []
   # calculate the intersections between the circumference of the circle and the straight line parallel to <line>
   # which will give rise to the centers of the fillet arces
   intPts = QadIntersections.infinityLineWithCircle(line, circle)
   if len(intPts) > 0:
      # a point of tangency is given by the point at a radius distance from the center of <origCircle>
      # towards the center of the fillet arc
      angle = qad_utils.getAngleBy2Pts(origCircle.center, intPts[0])
      tanCirclePt = qad_utils.getPolarPointByPtAngle(origCircle.center, angle, origCircle.radius)
      # a point of tangency is the perpendicular projection of the center of the fillet arc
      # con <origLine>
      ptPerp = QadPerpendicularity.fromPointToInfinityLine(intPts[0], origLine)
      filletArc = QadArc()
      if filletArc.fromStartCenterEndPts(tanCirclePt, \
                                         intPts[0], \
                                         ptPerp) == True:
         res.append(filletArc)
         if both:
            # I invert the initial-final angle
            filletArc = QadArc(filletArc)
            filletArc.inverseAngles()
            res.append(filletArc)

      if len(intPts) > 1: # # two centers for the two fillet arcs
         # a point of tangency is given by the point at a distance arc.radius from the center of <arc>
         # towards the center of the fillet arc
         angle = qad_utils.getAngleBy2Pts(origCircle.center, intPts[1])
         tanCirclePt = qad_utils.getPolarPointByPtAngle(origCircle.center, angle, origCircle.radius)
         # a point of tangency is the perpendicular projection of the center of the fillet arc
         # con <line>
         ptPerp = QadPerpendicularity.fromPointToInfinityLine(intPts[1], origLine)
         filletArc = QadArc()
         if filletArc.fromStartCenterEndPts(tanCirclePt, \
                                            intPts[1], \
                                            ptPerp) == True:
            res.append(filletArc)
            if both:
               # I invert the initial-final angle
               filletArc = QadArc(filletArc)
               filletArc.inverseAngles()
               res.append(filletArc)

   return res


# ===============================================================================
# getFilletArcsBetweenCircleLine
# ===============================================================================
def getFilletArcsBetweenCircleLine(circle, line, radius):
   """the function fillets a circle and a straight line (QadLine) through
      a connecting arc of radius <radius>.

      Returns a list of possible arcs
   """
   res = []

   offsetCircle = circle.copy()

   intPts = QadIntersections.infinityLineWithCircle(line, circle)
   if len(intPts) == 0:
      # if the circle is the straight line generated by the extension of line
      # have no points in common
      leftOfLine = line.leftOf(circle.center)
      # create a straight line parallel to <line> at a distance <radius> towards the center of <circle>
      linePar = QadLine()
      angle = line.getTanDirectionOnStartPt()
      if leftOfLine < 0: # on the left
         linePar.set(qad_utils.getPolarPointByPtAngle(line.getStartPt(), angle + math.pi / 2, radius), \
                     qad_utils.getPolarPointByPtAngle(line.getEndPt(), angle + math.pi / 2, radius))
      else :# on the right
         linePar.set(qad_utils.getPolarPointByPtAngle(line.getStartPt(), angle - math.pi / 2, radius), \
                     qad_utils.getPolarPointByPtAngle(line.getEndPt(), angle - math.pi / 2, radius))

      # Calculate the distance from the center of <circle> to <line>
      ptPerp = QadPerpendicularity.fromPointToInfinityLine(circle.center, line)
      d = qad_utils.getDistance(circle.center, ptPerp)
      # <radius> must be >= (d - circle radius) / 2
      if radius >= (d - circle.radius) / 2:

         # case 1: connection between <circle> and <line> forming an inflection with <circle>

         # create a circle with a radius increased by <radius>
         offsetCircle.radius = circle.radius + radius
         res.extend(auxFilletArcsBetweenCircleLine(offsetCircle, linePar, circle, line))

         # case 2: connection between <circle> and <line> without forming an inflection with <circle>

         # <radius> must be > circle radius
         if radius > circle.radius:
            # create a circle with radius = <radius> - circle.radius
            offsetCircle.radius = radius - circle.radius
            res.extend(auxFilletArcsBetweenCircleLine(offsetCircle, linePar, circle, line))
   else:
      # if the circle is the straight line generated by the extension of line
      # have points in common
      # create a straight line parallel to <line> at a distance <radius> to the left
      linePar = QadLine()
      angle = line.getTanDirectionOnStartPt()
      linePar.set(qad_utils.getPolarPointByPtAngle(line.getStartPt(), angle + math.pi / 2, radius), \
                  qad_utils.getPolarPointByPtAngle(line.getEndPt(), angle + math.pi / 2, radius))

      # create a circle with a radius increased by <radius>
      offsetCircle.radius = circle.radius + radius
      res.extend(auxFilletArcsBetweenCircleLine(offsetCircle, linePar, circle, line))

      if circle.radius > radius:
         # create a circle with a radius decreased by <radius>
         offsetCircle.radius = circle.radius - radius
         res.extend(auxFilletArcsBetweenCircleLine(offsetCircle, linePar, circle, line))

      # create a straight line parallel to <line> at a distance <radius> to the right
      linePar.set(qad_utils.getPolarPointByPtAngle(line.getStartPt(), angle - math.pi / 2, radius), \
                  qad_utils.getPolarPointByPtAngle(line.getEndPt(), angle - math.pi / 2, radius))

      # create a circle with a radius increased by <radius>
      offsetCircle.radius = circle.radius + radius
      res.extend(auxFilletArcsBetweenCircleLine(offsetCircle, linePar, circle, line))
      # calculate the intersections between the circumference of the circle and the straight line parallel to <line>

      if circle.radius > radius:
         # create a circle with a radius decreased by <radius>
         offsetCircle.radius = circle.radius - radius
         res.extend(auxFilletArcsBetweenCircleLine(offsetCircle, linePar, circle, line))

   return res


# ===============================================================================
# END - CIRCLE AND LINE
# START - 2 ELLIPSES
# ===============================================================================


# ===============================================================================
# filletBridgeTheGapBetweenEllipses
# ===============================================================================
def filletBridgeTheGapBetweenEllipses(ellipse1, ptOnEllipse1, ellipse2, ptOnEllipse2, radius):
   """the function connects two ellipses across
      a connecting arc of radius <radius> that comes closest to the selection points
      on the ellipses.

      It returns a list of 3 elements (None in case of error):
      None
      an arc, if = None there is no connecting arc between the two lines
      None
   """
   # TODO
   return [None, None, None]


# ===============================================================================
# END - 2 ELLIPSES
# BEGINNING - ARC AND ELLIPSE
# ===============================================================================


# ===============================================================================
# filletBridgeTheGapBetweenArcEllipse
# ===============================================================================
def filletBridgeTheGapBetweenArcEllipse(arc, ptOnArc, ellipse, ptOnEllipse, radius):
   """the function fillets an arc with an ellipse through
      a connecting arc of radius <radius> that comes closest to the selection points
      on geometries.

      It returns a list of 3 elements (None in case of error):
      None
      an arc, if = None there is no connecting arc between the two lines
      None
   """
   # TODO
   return [None, None, None]


# ===============================================================================
# END - ARC AND ELLIPSE
# BEGINNING - ELLIPSE AND ARC OF ELLIPSE
# ===============================================================================


# ===============================================================================
# filletBridgeTheGapBetweenEllipseEllipsearc
# ===============================================================================
def filletBridgeTheGapBetweenEllipseEllipsearc(ellipse, ptOnEllipse, ellipseArc, ptOnEllipseArc, radius):
   """the function fillets an ellipse with an arc of ellipse through
      a connecting arc of radius <radius> that comes closest to the selection points
      on geometries.

      It returns a list of 3 elements (None in case of error):
      None
      an arc, if = None there is no connecting arc between the two lines
      None
   """
   # TODO
   return [None, None, None]


# ===============================================================================
# END - ELLIPSE AND ARC OF ELLIPSE
# BEGINNING - ELLIPSE AND LINE
# ===============================================================================


# ===============================================================================
# filletBridgeTheGapBetweenEllipseLine
# ===============================================================================
def filletBridgeTheGapBetweenEllipseLine(ellipse, ptOnEllipse, line, ptOnLine, radius):
   """the function fillets an ellipse with a line through
      a connecting arc of radius <radius> that comes closest to the selection points
      on geometries.

      It returns a list of 3 elements (None in case of error):
      None
      an arc, if = None there is no connecting arc between the two lines
      None
   """
   # TODO
   return [None, None, None]


# ===============================================================================
# END - ELLIPSE AND LINE
# BEGINNING - 2 ARCHES
# ===============================================================================


# ===============================================================================
# filletBridgeTheGapBetweenArcs
# ===============================================================================
def filletBridgeTheGapBetweenArcs(arc1, ptOnArc1, arc2, ptOnArc2, radius, filletMode):
   """the function connects two arcs through
      a connecting arc of radius <radius> that comes closest to the selection points
      on arc1 <ptOnArc1> and on arc2 <ptOnArc2>.
      <filletMode> fillet mode; 1=Cut-extend, 2=Do not cut-extend

      It returns a list of 3 elements (None in case of error):
      an arc that replaces <arc1>
      an arc, if = None there is no connecting arc between the two lines
      an arc that replaces <arc2>
   """
   # ricavo i possibili arci di raccordo
   filletArcs = getFilletArcsBetweenArcs(arc1, arc2, radius)

   # I look for the valid arc closest to ptOnArc1 and ptOnArc2
   AvgList = []
   Avg = sys.float_info.max

   resFilletArc = QadArc()
   resArc1 = QadArc()
   resArc2 = QadArc()
   for filletArc in filletArcs:
      # get the new arc1 so that it is tangent with the fillet arc
      newArc1, distFromPtOnArc1 = getNewArcAccordingFilletArc(arc1.getArc(), filletArc, ptOnArc1)
      if newArc1 is None:
         continue
      # get the new arc so that it is tangent with the fillet arc
      newArc2, distFromPtOnArc2 = getNewArcAccordingFilletArc(arc2.getArc(), filletArc, ptOnArc2)
      if newArc2 is None:
         continue

      del AvgList[:]
      AvgList.append(distFromPtOnArc1)
      AvgList.append(distFromPtOnArc2)

      currAvg = qad_utils.numericListAvg(AvgList)
      if currAvg < Avg: # closer on average
         Avg = currAvg
         resArc1.set(newArc1)
         resFilletArc.set(filletArc)
         resArc2.set(newArc2)

   if Avg == sys.float_info.max:
      return None

   if filletMode == 1: # 1=Trim-extend
      return [resArc1, resFilletArc, resArc2]
   else:
      return [None, resFilletArc, None]


# ===============================================================================
# getFilletArcsBetweenArcs
# ===============================================================================
def getFilletArcsBetweenArcs(arc1, arc2, radius):
   """the function connects two arcs through a connecting arc of radius <radius>.

      Returns a list of possible arcs
   """
   circle1 = QadCircle()
   circle1.set(arc1.center, arc1.radius)
   circle2 = QadCircle()
   circle2.set(arc2.center, arc2.radius)

   return getFilletArcsBetweenCircles(circle1, circle2, radius)


# ===============================================================================
# END - 2 ARCHES
# BEGINNING - ARC AND ARC OF ELLIPSE
# ===============================================================================


# ===============================================================================
# filletBridgeTheGapBetweenArcEllipsearc
# ===============================================================================
def filletBridgeTheGapBetweenArcEllipsearc(arc, ptOnArc, ellipseArc, ptOnEllipseArc, radius):
   """the function connects an acro with an ellipse arc
      a connecting arc of radius <radius> that comes closest to the selection points
      on geometries.

      It returns a list of 3 elements (None in case of error):
      None
      an arc, if = None there is no connecting arc between the two lines
      None
   """
   # TODO
   return [None, None, None]


# ===============================================================================
# END - ARC AND ARC OF ELLIPSE
# BEGINNING - ARC AND LINE
# ===============================================================================


# ===============================================================================
# filletBridgeTheGapBetweenArcLine
# ===============================================================================
def filletBridgeTheGapBetweenArcLine(arc, ptOnArc, line, ptOnLine, radius, filletMode):
   """the function fillets an arc and a straight segment through
      a connecting arc of radius <radius> that comes closest to the selection points
      on the arc <ptOnArc> and on the straight segment <ptOnLine>.
      <filletMode> fillet mode; 1=Cut-extend, 2=Do not cut-extend

      It returns a list of 3 elements (None in case of error):
      an arc that replaces <arc>
      an arc, if = None there is no connecting arc between the two lines
      a line that replaces <line>
   """
   # ricavo i possibili arci di raccordo
   filletArcs = getFilletArcsBetweenArcLine(arc, line, radius)

   # I searc for the closest valid arc to ptOnArc and ptOnLine
   AvgList = []
   Avg = sys.float_info.max

   resArc = QadArc()
   resFilletArc = QadArc()
   resLine = QadLine()
   for filletArc in filletArcs:
      # get the new segment so that it is tangent with the fillet arc
      newLine, distFromPtOnLine = getNewLineAccordingFilletArc(line, filletArc, ptOnLine)
      if newLine is None:
         continue

      # get the new arc so that it is tangent with the fillet arc
      newArc, distFromPtOnArc = getNewArcAccordingFilletArc(arc, filletArc, ptOnArc)
      if newArc is None:
         continue

      del AvgList[:]
      AvgList.append(distFromPtOnLine)
      AvgList.append(distFromPtOnArc)

      currAvg = qad_utils.numericListAvg(AvgList)
      if currAvg < Avg: # closer on average
         Avg = currAvg
         resLine.set(newLine)
         resFilletArc.set(filletArc)
         resArc.set(newArc)

   if Avg == sys.float_info.max:
      return None

   if filletMode == 1: # 1=Trim-extend
      return [resArc, resFilletArc, resLine]
   else:
      return [None, resFilletArc, None]


# ===============================================================================
# getFilletArcsBetweenArcLine
# ===============================================================================
def getFilletArcsBetweenArcLine(arc, line, radius):
   """the function fillets an arc and a straight line through
      a connecting arc of radius <radius>.

      Returns a list of possible arcs
   """
   circle = QadCircle()
   circle.set(arc.center, arc.radius)

   return getFilletArcsBetweenCircleLine(circle, line, radius)


# ===============================================================================
# END - ARC AND LINE
# BEGINNING - 2 ARCS OF ELLIPSE
# ===============================================================================


# ===============================================================================
# filletBridgeTheGapBetweenEllipsearcs
# ===============================================================================
def filletBridgeTheGapBetweenEllipsearcs(ellipseArc1, ptOnEllipseArc1, ellipseArc2, ptOnEllipseArc2, radius):
   """the function connects two ellipse arcs through
      a connecting arc of radius <radius> that comes closest to the selection points
      on the arcs of ellipses.

      It returns a list of 3 elements (None in case of error):
      an ellipse arc that replaces <ellipseArc1>
      an arc, if = None there is no connecting arc between the two lines
      an ellipse arc that replaces <ellipseArc2>
   """
   # TODO
   return [None, None, None]


# ===============================================================================
# END - 2 ARCS OF ELLIPSE
# BEGINNING - LINE AND ARC OF ELLIPSE
# ===============================================================================


# ===============================================================================
# filletBridgeTheGapBetweenLineEllipsearc
# ===============================================================================
def filletBridgeTheGapBetweenLineEllipsearc(line, ptOnLine, ellipseArc, ptOnEllipseArc, radius):
   """the function fillets a line and an ellipse arc through
      a connecting arc of radius <radius> that comes closest to the selection points
      on geometries.

      It returns a list of 3 elements (None in case of error):
      a line that replaces <line>
      an arc, if = None there is no connecting arc between the two geometries
      an ellipse arc that replaces <ellipseArc>
   """
   # TODO
   return [None, None, None]


# ===============================================================================
# END - LINE AND ARC OF ELLIPSE
# START - POLYLINE
# ===============================================================================


# ============================================================================
# filletAllPartsQadPolyline
# ============================================================================
def filletAllPartsQadPolyline(polyline, radius):
   """the function connects each segment to the next with a known radius of curvature,
      the new polyline will have the vertices changed.
   """
   if radius <= 0: return
   newPolyline = QadPolyline()

   part = polyline.getLinearObjectAt(0)
   i = 1
   tot = polyline.qty()
   while i <= tot - 1:
      nextPart = polyline.getLinearObjectAt(i)
      if part.whatIs() == "LINE" and nextPart.whatIs() == "LINE":
         # Returns a list of 3 elements (None in case of error):
         # - a line replacing <part>, if = None <part> should be removed
         # - an arc, if = None there is no fillet arc between the two lines
         # - a line that replaces <nextPart>, if = None <nextPart> should be removed
         res = offsetBridgeTheGapBetweenLines(part, nextPart, radius, 1)
         if res is None:
            return
         if res[0] is not None:
            part = res[0]
            newPolyline.append(part)
         if res[1] is not None:
            part = res[1]
            newPolyline.append(part)
         if res[2] is not None:
            part = res[2]
      i = i + 1

   if polyline.isClosed():
      nextPart = newPolyline.getLinearObjectAt(0)
      if part.whatIs() == "LINE" and nextPart.whatIs() == "LINE":

         # Returns a list of 3 elements (None in case of error):
         # - a line replacing <part>, if = None <part> should be removed
         # - an arc, if = None there is no fillet arc between the two lines
         # - a line that replaces <nextPart>, if = None <nextPart> should be removed
         res = offsetBridgeTheGapBetweenLines(part, nextPart, radius, 1)
         if res is None:
            return
         if res[0] is not None:
            newPolyline.append(res[0])
         if res[1] is not None:
            newPolyline.append(res[1])
         if res[2] is not None:
            nextPart.set(res[2])
   else:
      newPolyline.append(part)

   polyline.set(newPolyline)

   return True
