# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 class for managing polylines (list of lines, arcs, elliptical arcs)

                              -------------------
        begin                : 2019-02-26
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
import qgis.utils

import math


from . import qad_utils
from .qad_line import QadLine
from .qad_arc import QadArc
from .qad_ellipse_arc import QadEllipseArc
from .qad_layer import createMemoryLayer
from .qad_msg import QadMsg
from .qad_variables import QadVariables


# ===============================================================================
# QadPolyline class
# represents a list of linear objects such as: lines, arcs, ellipse arcs
# ===============================================================================
class QadPolyline():

   def __init__(self, polyline=None):
      self.defList = []
      # deflist = (<linearObj1><linearObj2>...)
      if polyline is not None:
         self.set(polyline)


   # ============================================================================
   # whatIs
   # ============================================================================
   def whatIs(self):
      return "POLYLINE"


   # ============================================================================
   # set
   # ============================================================================
   def set(self, polyline):
      self.removeAll()
      if isinstance(polyline, QadPolyline) == True: # is a polyline
         for linearObject in polyline.defList:
            self.append(linearObject)
      elif isinstance(polyline, list) == True: # is a list of polyline parts
         for linearObject in polyline:
            self.append(linearObject)
      return self


   def __eq__(self, polyline):
      # required
      """self == other"""
      if polyline.whatIs() != "POLYLINE": return False
      if self.qty() != polyline.qty(): return False
      for i in range(0, self.qty()):
         if self.getLinearObjectAt(i) != polyline.getLinearObjectAt(i): return False
      return True


   def __ne__(self, polyline):
      """self != other"""
      return not self.__eq__(polyline)


   def equals(self, polyline):
      # geometrically equal (the direction does NOT count)
      if polyline.whatIs() != "POLYLINE": return False
      if self.__eq__(polyline): return True
      dummy = polyline.copy()
      dummy.reverse()
      return self.__eq__(dummy)

   # ============================================================================
   # append
   # ============================================================================
   def append(self, linearObject):
      """the function adds a linear object to the bottom of the list.
            No geometric continuity check is carried out.
      """
      if linearObject is None: return
      return self.defList.append(linearObject.copy())


   # ============================================================================
   # appendPolyline
   # ============================================================================
   def appendPolyline(self, polyline, start = None, qty = None):
      """the function adds a polyline to the bottom of the list.
            If <start> is different from None it means number of the part of <polyline> to start from.
            If <qty> different from None it means number of parts of <polyline> to add, otherwise it means up to the end of <polyline>.
            No geometric continuity check is carried out.
      """
      if start is None:
         for linearObject in polyline.defList:
            self.append(linearObject)
      else:
         i = start
         if qty is None:
            tot = polyline.qty()
         else:
            tot = polyline.qty() if qty > polyline.qty() else qty

         while i < tot:
            self.append(polyline.defList[i])
            i = i + 1


   # ============================================================================
   # insert
   # ============================================================================
   def insert(self, partAt, linearObject):
      """the function adds a linear object in the i-th position of the list of linear objects.
            No geometric continuity check is carried out.
      """
      if partAt >= self.qty():
         return self.append(linearObject)
      else:
         return self.defList.insert(partAt, linearObject.copy())


   # ============================================================================
   # insertPolyline
   # ============================================================================
   def insertPolyline(self, i, polyline):
      """the function adds a polyline at the i-th position of the list."""
      ndx = i
      for linearObject in polyline.defList:
         self.insert(ndx, linearObject)
         ndx = ndx + 1


   # ============================================================================
   # insertPoint
   # ============================================================================
   def insertPoint(self, partAt, pt):
      """the function adds a point between the starting and ending point of the i-th part of the list.
            if i < 0 adds the point to the beginning of the polyline
            if i >= qty() adds the point to the end of the polyline
      """
      if partAt < 0: # insert a line at the beginning
         line = QadLine()
         line.set(pt, self.getStartPt())
         self.insert(0, line)
      elif partAt >= self.qty(): # insert a line at the bottom
         line = QadLine()
         line.set(self.getEndPt(), pt)
         self.append(line)
      else:
         linearObject = self.getLinearObjectAt(partAt)

         if linearObject.whatIs() == "LINE":
            line = QadLine()
            line.set(linearObject.getStartPt(), pt)
            self.insert(partAt, line)
            linearObject = self.getLinearObjectAt(partAt + 1)
            linearObject.set(pt, linearObject.getEndPt())

         elif linearObject.whatIs() == "ARC":
            arc1 = QadArc()
            arc2 = QadArc()
            totalAngle = linearObject.totalAngle()
            if linearObject.reversed:
               if arc1.fromStartEndPtsAngle(pt, linearObject.getStartPt(), totalAngle) == False:
                  return
               arc1.reversed = True
               if linearObject.fromStartEndPtsAngle(linearObject.getEndPt(), pt, totalAngle) == False:
                  return
               linearObject.reversed = True
            else:
               if arc1.fromStartEndPtsAngle(linearObject.getStartPt(), pt, totalAngle) == False:
                  return
               if linearObject.fromStartEndPtsAngle(pt, linearObject.getEndPt(), totalAngle) == False:
                  return

            self.insert(partAt, arc1)

         elif linearObject.whatIs() == "ELLIPSE_ARC":
            # TODO
            pass


   # ============================================================================
   # movePoint
   # ============================================================================
   def movePoint(self, vertexAt, pt):
      """the function moves a point between the starting and ending point of the i-th part of the list."""
      prevLinearObject, nextLinearObject = self.getPrevNextLinearObjectsAtVertex(vertexAt)

      if prevLinearObject is not None:
         if prevLinearObject.whatIs() == "LINE":
            prevLinearObject.setEndPt(pt)

         elif prevLinearObject.whatIs() == "ARC":
            if prevLinearObject.reversed:
               # I move the starting point of the arc
               if prevLinearObject.fromStartEndPtsAngle(pt, \
                                                        prevLinearObject.getStartPt(), \
                                                        prevLinearObject.totalAngle()) == False:
                  return False
               prevLinearObject.reversed = True
            else:
               # I move the end point of the arc
               if prevLinearObject.fromStartEndPtsAngle(prevLinearObject.getStartPt(), \
                                                        pt, \
                                                        prevLinearObject.totalAngle()) == False:
                  return False

         elif prevLinearObject.whatIs() == "ELLIPSE_ARC":
            # TODO
            pass

      if nextLinearObject is not None:
         if nextLinearObject.whatIs() == "LINE":
            nextLinearObject.setStartPt(pt)

         elif nextLinearObject.whatIs() == "ARC":
            if nextLinearObject.reversed:
               # I move the end point of the arc
               if nextLinearObject.fromStartEndPtsAngle(nextLinearObject.getEndPt(), \
                                                        pt, \
                                                        nextLinearObject.totalAngle()) == False:
                  return False
               nextLinearObject.reversed = True
            else:
               # I move the starting point of the arc
               if nextLinearObject.fromStartEndPtsAngle(pt, \
                                                        nextLinearObject.getEndPt(), \
                                                        nextLinearObject.totalAngle()) == False:
                  return False

         elif prevLinearObject.whatIs() == "ELLIPSE_ARC":
            # TODO
            pass

      return True


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
   # getVertexPosAtPt
   # ============================================================================
   def getVertexPosAtPt(self, pt):
      """the function returns the position of the vertex with coordinates <pt> (0-based),
            None if not found.
      """
      vertexAt = 0
      for linearObject in self.defList:
         if qad_utils.ptNear(linearObject.getStartPt(), pt):
            return vertexAt
         vertexAt = vertexAt + 1
      if self.isClosed() == False: # if it is not closed check the last vertex of the last part
         if qad_utils.ptNear(self.defList[-1].getEndPt(), pt):
            return vertexAt

      return None


   # ============================================================================
   # getPrevNextLinearObjectsAtVertex
   # ============================================================================
   def getPrevNextLinearObjectsAtVertex(self, vertexAt):
      """the function returns the linear object before and after the vertexAt-th vertex"""
      prevLinearObject = None
      nextLinearObject = None

      if vertexAt == 0: # first summit
         nextLinearObject = self.getLinearObjectAt(0)
         if self.isClosed():
            prevLinearObject = self.getLinearObjectAt(-1)
      elif vertexAt == self.qty(): # last summit
         prevLinearObject = self.getLinearObjectAt(-1)
         if self.isClosed():
            nextLinearObject = self.getLinearObjectAt(0)
      else:
         nextLinearObject = self.getLinearObjectAt(vertexAt)
         prevLinearObject = self.getLinearObjectAt(vertexAt - 1)

      return prevLinearObject, nextLinearObject


   # ============================================================================
   # getPointAtVertex
   # ============================================================================
   def getPointAtVertex(self, vertexAt):
      """the function returns the point of the vertexAt-th vertex that makes up the polyline (0-based)."""
      if vertexAt == self.qty(): # last summit
         return self.getLinearObjectAt(-1).getEndPt()
      else:
         return self.getLinearObjectAt(vertexAt).getStartPt()


   # ============================================================================
   # getNextPos
   # ============================================================================
   def getNextPos(self, i):
      """the function returns the position of the linear object following the i-th (0-based)
            taking into account that if the polyline is closed after the last object it returns to the beginning
            N.B: I'm not sure if it has to be cyclical...
      """
      if i == self.qty() - 1 or i == -1: # I'm at the end
         if self.isClosed(): # if it's closed I go back to the beginning
            return 0
         else:
            return None
      else:
         return i + 1


   # ============================================================================
   # getPrevPos
   # ============================================================================
   def getPrevPos(self, i):
      """the function returns the position of the part preceding the i-th (0-based)
            taking into account that if the polyline is closed before the first object it goes to the end
            N.B: I'm not sure if it has to be cyclical...
      """
      if i == 0: # I'm at the beginning
         if self.isClosed(): # if it's closed I'll go back to the end
            return self.qty() - 1
         else:
            return None
      else:
         return i - 1


   # ============================================================================
   # fromPolyline
   # ============================================================================
   def fromPolyline(self, points):
      """the function initializes a list of lines, arcs and ellipse arcs that make up the polyline.
            If a linear object has a coinciding start and end point (e.g. 2 consecutive vertices
            that overlap or arc with total angle = 0 or = 360)
            the object is removed from the list.
      """
      pointsLen = len(points)

      self.removeAll()
      arc = QadArc()
      ellipseArc = QadEllipseArc()
      line = QadLine()

      i = 0
      while i < pointsLen - 1: # up to the penultimate point
         # check if it is an arc
         endVertex = arc.fromPolyline(points, i)
         if endVertex is not None and qad_utils.ptNear(arc.getStartPt(), points[i]) == True:
            self.append(arc)
            i = endVertex
         else:
            # check if it is an arc of an ellipse
            endVertex = ellipseArc.fromPolyline(points, i)
            if endVertex is not None and qad_utils.ptNear(ellipseArc.getStartPt(), points[i]) == True:
               self.append(ellipseArc)
               i = endVertex
            else: # then it is a line
               line.set(points[i], points[i + 1])
               self.append(line)
               i = i + 1

      if self.qty() == 0: return False

      return True


   # ============================================================================
   # fromGeom
   # ============================================================================
   def fromGeom(self, geom):
      """the function initializes the polyline from a QgsGeometry object."""
      return self.fromPolyline(geom.asPolyline())


   # ===============================================================================
   # asPolyline
   # ===============================================================================
   def asPolyline(self, tolerance2ApproxCurve = None, atLeastNSegment = None):
      """the function returns a list of points that make up the polyline formed by a list of
            consecutive linear objects.
      """
      result = []
      firstPt = True
      for linearObject in self.defList:
         pts = linearObject.asPolyline(tolerance2ApproxCurve, atLeastNSegment)
         ptsLen = len(pts)
         if firstPt:
            i = 0
            firstPt = False
         else:
             i = 1
         while i < ptsLen:
            result.append(pts[i])
            i = i + 1

      return result


   # ===============================================================================
   # asLineString
   # ===============================================================================
   def asLineString(self, tolerance2ApproxCurve = None, atLeastNSegment = None):
      """the function returns the polyline in the form of a lineString."""
      pts = self.asPolyline(tolerance2ApproxCurve, atLeastNSegment)
      if pts is None or len(pts) == 0:
          return None
      return QgsLineString(pts)


   # ===============================================================================
   # asCompoundString
   # ===============================================================================
   def asCompoundString(self, tolerance2ApproxCurve = None, atLeastNSegment = None):
      """the function returns the polyline in the form of compoundString."""
      compoundCurve = QgsCompoundCurve()
      lastPt = None
      for linearObject in self.defList:
         if linearObject.whatIs() == "ARC":
            compoundCurve.addCurve(linearObject.asCircularString(lastPt))
         else:
            compoundCurve.addCurve(linearObject.asLineString(tolerance2ApproxCurve, atLeastNSegment, lastPt))
         lastPt = linearObject.getEndPt()

      return compoundCurve


   # ===============================================================================
   # asAbstractGeom
   # ===============================================================================
   def asAbstractGeom(self, wkbType = QgsWkbTypes.LineString, tolerance2ApproxCurve = None, atLeastNSegment = None):
      """the function returns the polyline in the form of QgsAbstractGeometry."""
      flatType = QgsWkbTypes.flatType(wkbType)

      if flatType == QgsWkbTypes.CompoundCurve:
         compoundCurve = self.asCompoundString(tolerance2ApproxCurve, atLeastNSegment)
         return compoundCurve

      elif flatType == QgsWkbTypes.MultiCurve:
         compoundCurve = self.asCompoundString(tolerance2ApproxCurve, atLeastNSegment)
         multiCurve = QgsMultiCurve()
         multiCurve.addGeometry(compoundCurve)
         return multiCurve

      elif flatType == QgsWkbTypes.CurvePolygon:
         compoundCurve = self.asCompoundString(tolerance2ApproxCurve, atLeastNSegment)
         curvePolygon = QgsCurvePolygon()
         curvePolygon.setExteriorRing(compoundCurve)
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
      """the function returns the polyline in the form of QgsGeometry."""
      return QgsGeometry(self.asAbstractGeom(wkbType, tolerance2ApproxCurve, atLeastNSegment))


   # ===============================================================================
   # copy
   # ===============================================================================
   def copy(self):
      # required
      return QadPolyline(self)


   # ===============================================================================
   # reverse
   # ===============================================================================
   def reverse(self):
      """the function reverses the direction of a list of consecutive linear objects."""
      self.defList.reverse()
      for linearObject in self.defList:
         linearObject.reverse()
      return self


   # ===============================================================================
   # reverseCorrection
   # ===============================================================================
   def reverseCorrection(self):
      """the function checks and corrects the directions of the parts of the polyline."""
      totPart = self.qty()
      if totPart <= 1: return
      atPart = 0
      while atPart < totPart:
         linearObject = self.getLinearObjectAt(atPart)
         gType = linearObject.whatIs()
         if gType == "ARC" or gType == "ELLIPSE_ARC":
            startPt = linearObject.getStartPt(usingReversedFlag = False)
            if atPart == 0: # first part
               linearObject2 = self.getLinearObjectAt(atPart + 1) # next part
               if qad_utils.ptNear(startPt, linearObject2.getStartPt()) or \
                  qad_utils.ptNear(startPt, linearObject2.getEndPt()):
                  linearObject.reversed = True
               else:
                  linearObject.reversed = False
            else: # parts after the first
               linearObject2 = self.getLinearObjectAt(atPart - 1) # previous part
               if qad_utils.ptNear(startPt, linearObject2.getEndPt()):
                  linearObject.reversed = False
               else:
                  linearObject.reversed = True
         elif gType == "LINE":
            startPt = linearObject.getStartPt()
            if atPart == 0: # first part
               linearObject2 = self.getLinearObjectAt(atPart + 1) # next part
               if qad_utils.ptNear(linearObject.getStartPt(), linearObject2.getStartPt()) or \
                  qad_utils.ptNear(startPt, linearObject2.getEndPt()):
                  linearObject.reverse()
            else:
               linearObject2 = self.getLinearObjectAt(atPart - 1) # previous part
               if qad_utils.ptNear(linearObject.getStartPt(), linearObject2.getEndPt()) == False:
                  linearObject.reverse()
         atPart = atPart + 1


   # ============================================================================
   # length
   # ============================================================================
   def length(self):
      """the function returns the sum of the lengths of the parts."""
      tot = 0
      for linearObject in self.defList:
         tot = tot + linearObject.length()
      return tot


   # ============================================================================
   # move
   # ============================================================================
   def move(self, offsetX, offsetY):
      """the function moves the parts according to an X and a Y offset"""
      for linearObject in self.defList:
         linearObject.move(offsetX, offsetY)


   # ============================================================================
   # qty
   # ============================================================================
   def qty(self):
      """the function returns the quantity of linear objects that make up the polyline."""
      return len(self.defList)


   # ============================================================================
   # getStartPt
   # ============================================================================
   def getStartPt(self):
      """the function returns the starting point of the polyline."""
      linearObject = self.getLinearObjectAt(0) # first linear object
      return None if linearObject is None else linearObject.getStartPt()


   # ============================================================================
   # setStartPt
   # ============================================================================
   def setStartPt(self, pt):
      """the function sets the starting point of the polyline."""
      linearObject = self.getLinearObjectAt(0) # first linear object
      return None if linearObject is None else linearObject.setStartPt(pt)


   # ============================================================================
   # getEndPt
   # ============================================================================
   def getEndPt(self):
      """the function returns the final point of the polyline."""
      linearObject = self.getLinearObjectAt(-1) # last linear object
      return None if linearObject is None else linearObject.getEndPt()


   # ============================================================================
   # setEndPt
   # ============================================================================
   def setEndPt(self, pt):
      """the function sets the final point of the polyline."""
      linearObject = self.getLinearObjectAt(-1) # last linear object
      return None if linearObject is None else linearObject.setEndPt(pt)


   # ============================================================================
   # getMiddlePt
   # ============================================================================
   def getMiddlePt(self):
      """the function returns the midpoint of the polyline."""
      return self.getPointFromStart(self.length() / 2)


   # ============================================================================
   # getCentroid
   # ============================================================================
   def getCentroid(self, tolerance2ApproxCurve = None):
      """the function returns the centroid point of a closed polyline."""
      if self.isClosed(): # check if polyline is closed
         ptList = self.asPolyline(tolerance2ApproxCurve)
         g =  QgsGeometry.fromPolygonXY([ptList])
         if g is not None:
            centroid = g.centroid()
            if centroid is not None:
               return g.centroid().asPoint()

      return None


   # ============================================================================
   # isClosed
   # ============================================================================
   def isClosed(self):
      """the function returns True if the polyline (list of parts segments-arcs) is closed."""
      if len(self.defList) == 0:
         return False
      else:
         return True if qad_utils.ptNear(self.getStartPt(), self.getEndPt()) else False


   # ============================================================================
   # setClose
   # ============================================================================
   def setClose(self, toClose = True):
      """the function closes or opens the polyline."""
      if toClose: # da chiudere
         if self.isClosed() == False:
            if self.qty() > 0:
               linearObject = self.getLinearObjectAt(-1)
               # check the last item
               if linearObject.whatIs() == "LINE":
                  if self.qty() > 1:
                     self.append(QadLine().set(self.getEndPt(), self.getStartPt()))
               elif linearObject.whatIs() == "ARC":
                  arc = QadArc()
                  if arc.fromStartEndPtsTan(linearObject.getEndPt(), \
                                            self.getStartPt(), \
                                            linearObject.getTanDirectionOnEndPt()) == False:
                     return
                  self.append(arc)
               elif linearObject.whatIs() == "ELLIPSE_ARC":
                  # TODO
                  pass

      else: # da aprire
         if self.isClosed() == True:
            if self.qty() > 1:
               self.remove(-1)


   # ===============================================================================
   # getBoundingBox
   # ===============================================================================
   def getBoundingBox(self):
      """the function returns the rectangle that encloses the polyline."""
      boundingBox = self.getLinearObjectAt(0).getBoundingBox()
      i = 1
      while i < self.qty():
         boundingBox.combineExtentWith(self.getLinearObjectAt(i).getBoundingBox())
         i = i + 1

      return boundingBox


   # ===============================================================================
   # isContainingEllipseArcs
   # ===============================================================================
   def segmentizeEllipseArcs(self, tolerance2ApproxCurve = None):
      """the function transforms ellipse arcs into segments"""
      if tolerance2ApproxCurve is None:
         tolerance = QadVariables.get(QadMsg.translate("Environment variables", "TOLERANCE2APPROXCURVE"))
      else:
         tolerance = tolerance2ApproxCurve

      if self.isClosed() == True:
         prevPartEndPt = self.defList[-1].getEndPt()
      else:
         prevPartEndPt = None

      partAt = 0
      while partAt < len(self.defList):
         linearObject = self.defList[partAt]
         if linearObject.whatIs() == "ELLIPSE_ARC":
            points = linearObject.asPolyline(tolerance)
            if prevPartEndPt is not None:
               points[0] = prevPartEndPt
            prevPartEndPt = points[-1]

            self.remove(partAt)
            pointsLen = len(points)
            i = 0
            while i < pointsLen - 1: # up to the penultimate point
               line = QadLine()
               line.set(points[i], points[i + 1])
               self.insert(partAt, line)
               partAt = partAt + 1
               i = i + 1
         else:
            prevPartEndPt = self.defList[partAt].getEndPt()
            partAt = partAt + 1

      return True


   # ============================================================================
   # getTanDirectionOnStartPt
   # ============================================================================
   def getTanDirectionOnStartPt(self):
      """the function returns the direction of the tangent to the starting point of the object."""
      linearObject = self.getLinearObjectAt(0) # first linear object
      return None if linearObject is None else linearObject.getTanDirectionOnStartPt()


   # ============================================================================
   # getTanDirectionOnEndPt
   # ============================================================================
   def getTanDirectionOnEndPt(self):
      """the function returns the direction of the tangent to the starting point of the object."""
      linearObject = self.getLinearObjectAt(-1) # last linear object
      return None if linearObject is None else linearObject.getTanDirectionOnEndPt()


   # ============================================================================
   # curve
   # ============================================================================
   def curve(self, toCurve = True):
      """if toCurve = True:
            the function curves each segment to fit the polyline
            passing the new polyline through the vertices.
            if toCurve = False:
            the function transforms each arc of the polyline into a straight segment (list of segment-arc parts).
      """
      if toCurve == False:
         i = 0
         while i < self.qty():
            linearObject = self.defList[i]
            if linearObject.whatIs() != "LINE":
               self.insert(i, QadLine().set(linearObject.getStartPt(), linearObject.getEndPt()))
               self.remove(i + 1)
            i = i + 1
         return

      tot = self.qty()
      if tot < 2: return
      isClosed = self.isClosed()

      newPolyline = QadPolyline()

      # first linear object
      current = self.getLinearObjectAt(0)
      prev = None
      tanDirectionOnStartPt = None
      if isClosed:
         prev = self.getLinearObjectAt(-1)
         arc = QadArc()
         if arc.fromStartSecondEndPts(prev.getStartPt(), current.getStartPt(), current.getEndPt()):
            if not arc.reversed: # arc is not reversed
               arc.setStartAngleByPt(current.getStartPt())
            else: # arc is reversed
               arc.setEndAngleByPt(current.getStartPt())
            tanDirectionOnStartPt = arc.getTanDirectionOnEndPt()

      next = self.getLinearObjectAt(1)
      newPolyline.defList.extend(getCurveLinearObjects(tanDirectionOnStartPt, prev, current, next))

      i = 1
      while i < tot - 1:
         tanDirectionOnStartPt = newPolyline.getLinearObjectAt(-1).getTanDirectionOnEndPt()
         prev = current
         current = next
         next = self.getLinearObjectAt(i + 1)
         newPolyline.defList.extend(getCurveLinearObjects(tanDirectionOnStartPt, prev, current, next))
         i = i + 1

      # last linear object
      tanDirectionOnStartPt = newPolyline.getLinearObjectAt(-1).getTanDirectionOnEndPt()
      prev = current
      current = next
      next = self.getLinearObjectAt(0) if isClosed else None
      newPolyline.defList.extend(getCurveLinearObjects(tanDirectionOnStartPt, prev, current, next))

      self.set(newPolyline)


   # ============================================================================
   # simplify
   # ============================================================================
   def simplify(self, tolerance):
      g = QgsGeometry.fromPolylineXY(self.asPolyline()).simplify(tolerance)
      return self.fromPolyline(g.asPolyline())


   # ============================================================================
   # getDistanceFromStart
   # ============================================================================
   def getDistanceFromStart(self, pt):
      """the function returns the distance of <pt> (which must be on the object) from the starting point."""
      tot = 0
      for linearObject in self.defList:
         if linearObject.containsPt(pt) == True:
            return tot + linearObject.getDistanceFromStart(pt)
         else:
            tot = tot + linearObject.length()

      return -1


   # ============================================================================
   # getPointFromStart
   # ============================================================================
   def getPointFromStart(self, distance):
      """the function returns a point (and the direction of the tangent) of the polyline at the distance <distance>
            (which must be on the object) from the starting point.
      """
      if distance < 0:
         return None, None
      d = distance
      for linearObject in self.defList:
         l = linearObject.length()
         if d > l:
            d = d - l
         else:
            return linearObject.getPointFromStart(d)

      return None, None


   # ============================================================================
   # lengthen_delta
   # ============================================================================
   def lengthen_delta(self, move_startPt, delta):
      """the function moves the starting point (if move_startPt = True) or ending point (if move_startPt = False)
            by a distance delta by lengthening (if delta > 0) or shortening (if delta < 0) the polyline
      """
      length = self.length()
      # polyline length + delta cannot be <= 0
      if length + delta <= 0:
         return False

      if move_startPt == False:
         # from the final point
         if delta >= 0: # I lengthen the polyline
            # last part
            return self.getLinearObjectAt(-1).lengthen_delta(False, delta)
         else: # I shorten the polyline
            # I look for the part where the shortened polyline would end
            nPart = 0
            d = length + delta
            for linearObject in self.defList:
               l = linearObject.length()
               if d > l:
                  d = d - l
                  nPart = nPart + 1
               else:
                  if linearObject.lengthen_delta(False, -(l - d)) == False:
                     return False
                  # if it is not the last part
                  if nPart+1 < len(self.defList):
                     # delete the parts following nPart
                     del self.defList[nPart+1 :]
                  return True
      else: # from the starting point
         # first part
         dummy = self.copy()
         dummy.reverse()
         if dummy.lengthen_delta(False, delta) == False:
            return False
         dummy.reverse()
         self.set(dummy)
         return True


   # ============================================================================
   # lengthen_deltaAngle
   # ============================================================================
   def lengthen_deltaAngle(self, move_startPt, delta):
      """the function moves the starting point (if move_startPt = True) or ending point (if move_startPt = False)
            of a certain number of delta degrees.
      """
      if move_startPt == False:
         # from the final point
         return self.getLinearObjectAt(-1).lengthen_deltaAngle(False, delta)
      else:
         # from the starting point
         return self.getLinearObjectAt(0).lengthen_deltaAngle(True, delta)


   # ===============================================================================
   # transform
   # ===============================================================================
   def transform(self, coordTransform):
      """the function returns a new polyline with the transformed coordinates."""
      result = QadPolyline()
      for linearObject in self.defList:
         result.append(linearObject.transform(coordTransform))
      return result


   # ===============================================================================
   # transformFromCRSToCRS
   # ===============================================================================
   def transformFromCRSToCRS(self, sourceCRS, destCRS):
      """the function transforms the coordinates of the points that make up the linear object."""
      return self.transform(QgsCoordinateTransform(sourceCRS, destCRS, QgsProject.instance()))


   # ============================================================================
   # containsPt
   # ============================================================================
   def containsPt(self, pt, startAt = 0):
      """the function returns True if the point is on the polyline otherwise False.
            Control starts from the <startAt> part (0-based)
      """
      tot = len(self.defList)
      if startAt < 0 or startAt >= tot:
         return False
      i = startAt
      while i < tot:
         linearObject = self.defList[i]
         if linearObject.containsPt(pt):
            return True
         i = i + 1
      return False


   # ============================================================================
   # move
   # ============================================================================
   def move(self, offsetX, offsetY):
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


   # ===============================================================================
   # rectangle creation functions
   # getRectByCorners
   # ===============================================================================
   def getRectByCorners(self, firstCorner, secondCorner, rot, gapType, \
                        gapValue1 = None, gapValue2 = None):
      """returns a polyline that defines the rectangle constructed using
            the two opposite edges firstCorner and secondCorner, the rotation with base point firstCorner and gapType
            0 = the edges of the rectangle have right angles
            1 = fillets the edges of the rectangle with a curvature radius gapValue1
            2 = chamfers the edges of the rectangle with 2 chamfering distances gapValue1, gapValue2
      """
      self.removeAll()
      # create a rotated rectangle with right angles
      secondCornerProj = qad_utils.getPolarPointByPtAngle(firstCorner, rot, 10)
      pt2 = qad_utils.getPerpendicularPointOnInfinityLine(firstCorner, secondCornerProj, secondCorner)
      angle = qad_utils.getAngleBy2Pts(firstCorner, pt2)
      pt4 = qad_utils.getPolarPointByPtAngle(secondCorner, angle + math.pi, \
                                             qad_utils.getDistance(firstCorner, pt2))

      line = QadLine()
      if gapType == 0: # the edges of the rectangle have right angles
         self.append(line.set(firstCorner, pt2))
         self.append(line.set(pt2, secondCorner))
         self.append(line.set(secondCorner, pt4))
         self.append(line.set(pt4, firstCorner))
         return True
      else:
         length = qad_utils.getDistance(firstCorner, pt2)
         width = qad_utils.getDistance(pt2, secondCorner)

         if gapType == 1: # fillets the edges of the rectangle with a curvature radius gapValue1
            if (gapValue1 * 2) > length or (gapValue1 * 2) > width: # the rectangle is too small
               self.append(line.set(firstCorner, pt2))
               self.append(line.set(pt2, secondCorner))
               self.append(line.set(secondCorner, pt4))
               self.append(line.set(pt4, firstCorner))
               return True

            arc = QadArc()

            diagonal = math.sqrt((gapValue1 * gapValue1) * 2)
            diagonal = gapValue1 - (diagonal / 2)

            # lato
            p1 = qad_utils.getPolarPointByPtAngle(firstCorner, angle, gapValue1)
            p2 = qad_utils.getPolarPointByPtAngle(pt2, angle + math.pi, gapValue1)
            self.append(line.set(p1, p2))
            # arc
            angle = qad_utils.getAngleBy2Pts(pt2, secondCorner)
            p3 = qad_utils.getPolarPointByPtAngle(pt2, angle, gapValue1)
            pMiddle = qad_utils.getMiddlePoint(p2, p3)
            pMiddle = qad_utils.getPolarPointByPtAngle(pMiddle, qad_utils.getAngleBy2Pts(pMiddle, pt2), diagonal)
            arc.fromStartSecondEndPts(p2, pMiddle, p3)
            self.append(arc)
            # lato
            p4 = qad_utils.getPolarPointByPtAngle(secondCorner, angle + math.pi, gapValue1)
            self.append(line.set(p3, p4))
            # arc
            angle = qad_utils.getAngleBy2Pts(secondCorner, pt4)
            p5 = qad_utils.getPolarPointByPtAngle(secondCorner, angle, gapValue1)
            pMiddle = qad_utils.getMiddlePoint(p4, p5)
            pMiddle = qad_utils.getPolarPointByPtAngle(pMiddle, qad_utils.getAngleBy2Pts(pMiddle, secondCorner), diagonal)
            arc.fromStartSecondEndPts(p4, pMiddle, p5)
            self.append(arc)
            # lato
            p6 = qad_utils.getPolarPointByPtAngle(pt4, angle + math.pi, gapValue1)
            self.append(line.set(p5, p6))
            # arc
            angle = qad_utils.getAngleBy2Pts(pt4, firstCorner)
            p7 = qad_utils.getPolarPointByPtAngle(pt4, angle, gapValue1)
            pMiddle = qad_utils.getMiddlePoint(p6, p7)
            pMiddle = qad_utils.getPolarPointByPtAngle(pMiddle, qad_utils.getAngleBy2Pts(pMiddle, pt4), diagonal)
            arc = QadArc()
            arc.fromStartSecondEndPts(p6, pMiddle, p7)
            self.append(arc)
            # lato
            p8 = qad_utils.getPolarPointByPtAngle(firstCorner, angle + math.pi, gapValue1)
            self.append(line.set(p7, p8))
            # arc
            pMiddle = qad_utils.getMiddlePoint(p8, p1)
            pMiddle = qad_utils.getPolarPointByPtAngle(pMiddle, qad_utils.getAngleBy2Pts(pMiddle, firstCorner), diagonal)
            arc = QadArc()
            arc.fromStartSecondEndPts(p8, pMiddle, p1)
            self.append(arc)
            return True
         elif gapType == 2: # smooths the edges of the rectangle with 2 chamfering distances gapValue1, gapValue2
            if (gapValue1 + gapValue2) > length or (gapValue1 + gapValue2) > width: # the rectangle is too small
               self.append(line.set(firstCorner, pt2))
               self.append(line.set(pt2, secondCorner))
               self.append(line.set(secondCorner, pt4))
               self.append(line.set(pt4, firstCorner))
               return True

            p1 = qad_utils.getPolarPointByPtAngle(firstCorner, angle, gapValue2)
            p2 = qad_utils.getPolarPointByPtAngle(pt2, angle + math.pi, gapValue1)
            angle = qad_utils.getAngleBy2Pts(pt2, secondCorner)
            p3 = qad_utils.getPolarPointByPtAngle(pt2, angle, gapValue2)
            p4 = qad_utils.getPolarPointByPtAngle(secondCorner, angle + math.pi, gapValue1)
            angle = qad_utils.getAngleBy2Pts(secondCorner, pt4)
            p5 = qad_utils.getPolarPointByPtAngle(secondCorner, angle, gapValue2)
            p6 = qad_utils.getPolarPointByPtAngle(pt4, angle+ math.pi, gapValue1)
            angle = qad_utils.getAngleBy2Pts(pt4, firstCorner)
            p7 = qad_utils.getPolarPointByPtAngle(pt4, angle, gapValue2)
            p8 = qad_utils.getPolarPointByPtAngle(firstCorner, angle + math.pi, gapValue1)

            self.append(line.set(p1, p2))
            self.append(line.set(p2, p3))
            self.append(line.set(p3, p4))
            self.append(line.set(p4, p5))
            self.append(line.set(p5, p6))
            self.append(line.set(p6, p7))
            self.append(line.set(p7, p8))
            self.append(line.set(p8, p1))
            return True

      return False


   # ===============================================================================
   # getRectByCornerAndDims
   # ===============================================================================
   def getRectByCornerAndDims(self, firstCorner, lengthDim, widthDim, rot, gapType, \
                              gapValue1 = None, gapValue2 = None):
      """returns a polyline that defines the rectangle constructed using
            an edge, length, width, rotation with firstCorner base point and gapType
            0 = the edges of the rectangle have right angles
            1 = fillets the edges of the rectangle with a curvature radius gapValue1
            2 = chamfers the edges of the rectangle with 2 chamfering distances gapValue1, gapValue2
      """
      pt2 = qad_utils.getPolarPointByPtAngle(firstCorner, rot, lengthDim)
      secondCorner = qad_utils.getPolarPointByPtAngle(pt2, rot + (math.pi / 2), widthDim)
      return self.getRectByCorners(firstCorner, secondCorner, rot, gapType, gapValue1, gapValue2)


   # ===============================================================================
   # getRectByAreaAndLength
   # ===============================================================================
   def getRectByAreaAndLength(self, firstCorner, area, lengthDim, rot, gapType, \
                              gapValue1 = None, gapValue2 = None):
      """returns a polyline that defines the rectangle constructed using
            an edge, the area, the width, the rotation with firstCorner base point and gapType
            0 = the edges of the rectangle have right angles
            1 = fillets the edges of the rectangle with a curvature radius gapValue1
            2 = chamfers the edges of the rectangle with 2 chamfering distances gapValue1, gapValue2
      """
      if gapType == 0: # the edges of the rectangle have right angles
         widthDim = area / lengthDim
         return self.getRectByCornerAndDims(firstCorner, lengthDim, widthDim, rot, gapType, \
                                            gapValue1, gapValue2)
      else:
         if gapType == 1: # fillets the edges of the rectangle with a curvature radius gapValue1
            angleArea = ((2 * gapValue1) * (2 * gapValue1)) - (math.pi * gapValue1 * gapValue1)
            widthDim = (area + angleArea) / lengthDim
            if (gapValue1 * 2) > lengthDim or (gapValue1 * 2) > widthDim: # the rectangle is too small
               widthDim = area / lengthDim
            return self.getRectByCornerAndDims(firstCorner, lengthDim, widthDim, rot, gapType, \
                                               gapValue1, gapValue2)
         elif gapType == 2: # smooths the edges of the rectangle with 2 chamfering distances gapValue1, gapValue2
            angleArea = 2 * (gapValue1 * gapValue2)
            widthDim = (area + angleArea) / lengthDim
            if (gapValue1 + gapValue2) > lengthDim or (gapValue1 + gapValue2) > widthDim: # the rectangle is too small
               widthDim = area / lengthDim
            return self.getRectByCornerAndDims(firstCorner, lengthDim, widthDim, rot, gapType, \
                                               gapValue1, gapValue2)


   # ===============================================================================
   # getRectByAreaAndWidth
   # ===============================================================================
   def getRectByAreaAndWidth(self, firstCorner, area, widthDim, rot, gapType, \
                              gapValue1 = None, gapValue2 = None):
      """returns a polyline that defines the rectangle constructed using
            an edge, the area, the width, the rotation with firstCorner base point and gapType
            0 = the edges of the rectangle have right angles
            1 = fillets the edges of the rectangle with a curvature radius gapValue1
            2 = chamfers the edges of the rectangle with 2 chamfering distances gapValue1, gapValue2
      """
      if gapType == 0: # the edges of the rectangle have right angles
         lengthDim = area / widthDim
         return self.getRectByCornerAndDims(firstCorner, lengthDim, widthDim, rot, gapType, \
                                            gapValue1, gapValue2)
      else:
         if gapType == 1: # fillets the edges of the rectangle with a curvature radius gapValue1
            angleArea = math.pi * gapValue1 * gapValue1
            lengthDim = (area + angleArea) / widthDim
            if (gapValue1 * 2) > lengthDim or (gapValue1 * 2) > widthDim: # the rectangle is too small
               lengthDim = area / widthDim
            return self.getRectByCornerAndDims(firstCorner, lengthDim, widthDim, rot, gapType, \
                                               gapValue1, gapValue2)
         elif gapType == 2: # smooths the edges of the rectangle with 2 chamfering distances gapValue1, gapValue2
            angleArea = 2 * (gapValue1 * gapValue2)
            lengthDim = (area + angleArea) / widthDim
            if (gapValue1 + gapValue2) > lengthDim or (gapValue1 + gapValue2) > widthDim: # the rectangle is too small
               lengthDim = area / widthDim
            return self.getRectByCornerAndDims(firstCorner, lengthDim, widthDim, rot, gapType, \
                                               gapValue1, gapValue2)


   # ===============================================================================
   # polygon creation functions
   # getPolygonByNsidesCenterRadius
   # ===============================================================================
   def getPolygonByNsidesCenterRadius(self, sideNumber, centerPt, radius, Inscribed, ptStart = None):
      """returns a polyline that defines the polygon constructed using
            sideNumber = number of sides
            centerPt = center of the polygon
            radius = radius of the circle
            Inscribed = if True it means inscribed polygon otherwise circumscribed
            ptStart = starting point
      """
      self.removeAll()
      line = QadLine()

      angleIncrement = 2 * math.pi / sideNumber
      # circumscribed polygon
      if Inscribed == False:
         # calculate the new radius
         myRadius = radius / math.cos(angleIncrement / 2)

         if ptStart is None:
            myPtStart = qad_utils.getPolarPointByPtAngle(centerPt, math.pi / 2 * 3 + (angleIncrement / 2), myRadius)
            angle = qad_utils.getAngleBy2Pts(centerPt, myPtStart)
         else:
            angle = qad_utils.getAngleBy2Pts(centerPt, ptStart)
            myPtStart = qad_utils.getPolarPointByPtAngle(centerPt, angle + (angleIncrement / 2), myRadius)
            angle = qad_utils.getAngleBy2Pts(centerPt, myPtStart)
      else: # inscribed polygon
         myRadius = radius

         if ptStart is None:
            myPtStart = qad_utils.getPolarPointByPtAngle(centerPt, math.pi / 2 * 3 + (angleIncrement / 2), myRadius)
            angle = qad_utils.getAngleBy2Pts(centerPt, myPtStart)
         else:
            myPtStart = ptStart
            angle = qad_utils.getAngleBy2Pts(centerPt, ptStart)

      previusPt = myPtStart
      for i in range(1, sideNumber, 1):
         angle = angle + angleIncrement
         pt = qad_utils.getPolarPointByPtAngle(centerPt, angle, myRadius)
         self.append(line.set(previusPt, pt))
         previusPt = pt
      self.append(line.set(previusPt, myPtStart))

      return True


   # ===============================================================================
   # getPolygonByNsidesEdgePts
   # ===============================================================================
   def getPolygonByNsidesEdgePts(self, sideNumber, firstEdgePt, secondEdgePt):
      """returns a polyline that defines the polygon constructed using
            sideNumber = number of sides
            firstEdgePt = first point of an edge
            secondEdgePt = second point of an edge
      """
      self.removeAll()
      line = QadLine()

      angleIncrement = 2 * math.pi / sideNumber
      angle = qad_utils.getAngleBy2Pts(firstEdgePt, secondEdgePt)
      sideLength = qad_utils.getDistance(firstEdgePt, secondEdgePt)

      self.append(line.set(firstEdgePt, secondEdgePt))
      previusPt = secondEdgePt
      for i in range(1, sideNumber - 1, 1):
         angle = angle + angleIncrement
         pt = qad_utils.getPolarPointByPtAngle(previusPt, angle, sideLength)
         self.append(line.set(previusPt, pt))
         previusPt = pt
      self.append(line.set(previusPt, firstEdgePt))

      return True


   # ===============================================================================
   # getPolygonByNsidesArea
   # ===============================================================================
   def getPolygonByNsidesArea(self, sideNumber, centerPt, area):
      """returns a polyline that defines the polygon constructed using
            sideNumber = number of sides
            centerPt = center of the polygon
            area = area of the polygon
      """
      angle = 2 * math.pi / sideNumber
      triangleArea = area / sideNumber / 2
      # I divide the polygon into sideNumber triangles
      # each triangle is divided in 2, generating 2 right triangles where
      # "(base * height) / 2 = Area" which is equivalent to "base = 2 * Area / height"
      # "tan(alpha) = base / height" which is equivalent to "tan(alpha) * height = base
      # by substitution we have
      # "tan(alfa) * altezza = 2 * Area / altezza" quindi
      # "altezza = sqrt(2 * Area / tan(alfa))"
      h = math.sqrt(2 * triangleArea / math.tan(angle / 2))

      return self.getPolygonByNsidesCenterRadius(sideNumber, centerPt, h, False)


   # ============================================================================
   # getPartPosAtPt
   # ============================================================================
   def getPartPosAtPt(self, pt, startAt = 0):
      """the function returns the position of the part containing the point <pt> (0-based),
            -1 if not found.
            Control starts from the <startAt> part (0-based)
      """
      tot = len(self.defList)
      if startAt < 0 or startAt >= tot:
         return -1
      i = startAt
      while i < tot:
         linearObject = self.defList[i]
         if linearObject.containsPt(pt):
            return i
         i = i + 1
      return -1


   # ===============================================================================
   # getGeomBetween2Pts
   # considerPolylineAsOpened is used to prevent the shortest path from startPt to endPt from returning in the case of a closed polyline.
   # see break on rectangle (on linestring layer)
   # ===============================================================================
   def getGeomBetween2Pts(self, startPt, endPt, considerPolylineAsOpened = False):
      """Returns a sub-geometry that starts from the startPt point and ends at the endPt point following the geometry path.
            If the polyline is closed it returns the shortest path to go from startPt to endPt.
      """
      tot = self.qty()

      iStart = self.getPartPosAtPt(startPt) # number of the part containing startPt
      if iStart == -1: return None

      result1 = QadPolyline()
      i = iStart
      lastPt = startPt
      ok1 = False
      while i < tot:
         linearObj = self.getLinearObjectAt(i)
         if linearObj.containsPt(endPt):
            result1.append(linearObj.getGeomBetween2Pts(lastPt, endPt))
            ok1 = True
            break
         elif i == iStart:
            result1.append(linearObj.getGeomBetween2Pts(lastPt, linearObj.getEndPt()))
         else:
            result1.append(linearObj)

         if result1.qty() > 0: lastPt = result1.getEndPt() # getGeomBetween2Pts potrebbe restituire None
         i = i + 1

      if ok1:
         if self.isClosed() == False or considerPolylineAsOpened == True: return result1
      else:
         # if the end is not found and it is a closed polyline, I start again from the beginning
         if self.isClosed():
            i = 0
            while i < iStart:
               linearObj = self.getLinearObjectAt(i)
               if linearObj.containsPt(endPt):
                  result1.append(linearObj.getGeomBetween2Pts(lastPt, endPt))
                  ok1 = True
                  break
               else:
                  if linearObj.length() > 0: result1.append(linearObj)

               if result1.qty() > 0: lastPt = result1.getEndPt() # getGeomBetween2Pts potrebbe restituire None

               i = i + 1

      # search in the opposite direction
      inversedPolyline = QadPolyline(self).reverse()

      result2 = QadPolyline()
      iStart = tot - 1 - iStart
      i = iStart
      lastPt = startPt
      ok2 = False
      while i < tot:
         linearObj = inversedPolyline.getLinearObjectAt(i)
         if linearObj.containsPt(endPt):
            result2.append(linearObj.getGeomBetween2Pts(lastPt, endPt))
            ok2 = True
            break
         elif i == iStart:
            result2.append(linearObj.getGeomBetween2Pts(lastPt, linearObj.getEndPt()))
         else:
            result2.append(linearObj)

         if result2.qty() > 0: lastPt = result2.getEndPt() # getGeomBetween2Pts potrebbe restituire None
         i = i + 1

      if ok2:
         if self.isClosed() == False: return result2
      else:
         # if the end is not found and it is a closed polyline, I start again from the beginning
         if self.isClosed():
            i = 0
            while i < iStart:
               linearObj = inversedPolyline.getLinearObjectAt(i)
               if linearObj.containsPt(endPt):
                  result2.append(linearObj.getGeomBetween2Pts(lastPt, endPt))
                  ok2 = True
                  break
               else:
                  if linearObj.length() > 0: result2.append(linearObj)

               if result2.qty() > 0: lastPt = result2.getEndPt() # getGeomBetween2Pts potrebbe restituire None
               i = i + 1

      if ok1:
         if ok2:
            return result1 if result1.length() < result2.length() else result2
         else:
            return result1
      else:
         if ok2:
            return result2
         else:
            return None


   # ===============================================================================
   # breakOnPts
   # ===============================================================================
   def breakOnPts(self, firstPt, secondPt):
      """the function breaks the geometry at one point (if <secondPt> = None) or at two points
            how does the trim. Returns one or two geometries resulting from the operation.
            <firstPt> = first dividing point
            <secondPt> = second dividing point
      """
      if secondPt is None or firstPt == secondPt: # break on one point
         if self.isClosed(): return None, None # if it is closed
         return [self.getGeomBetween2Pts(self.getStartPt(), firstPt), self.getGeomBetween2Pts(firstPt, self.getEndPt())]
      else: # break on 2 points
         dist1 = self.getDistanceFromStart(firstPt)
         dist2 = self.getDistanceFromStart(secondPt)
         if dist1 < dist2:
            g1 = self.getGeomBetween2Pts(self.getStartPt(), firstPt, True)
            g2 = self.getGeomBetween2Pts(secondPt, self.getEndPt(), True)
         else:
            g1 = self.getGeomBetween2Pts(self.getStartPt(), secondPt, True)
            g2 = self.getGeomBetween2Pts(firstPt, self.getEndPt(), True)

         if self.isClosed(): # if it is closed
            g2.appendPolyline(g1)
            return [g2, None]
         else:
            return [g1, g2]


# ===============================================================================
# getCurveLinearObjects
# ===============================================================================
def getCurveLinearObjects(tanDirectionOnStartPt, prev, current, next):
   """Given the direction of the tangent at the starting point of the current part e
      a succession of 3 linear parts,
      the function returns a list of linear parts
      to replace the <current> part to curve the polyline
   """
   # if there is neither the previous nor the subsequent part
   if prev is None and next is None:
      return current

   arc = QadArc()
   if prev is None: # there is no previous part
      if arc.fromStartSecondEndPts(current.getStartPt(), current.getEndPt(), next.getEndPt()) == False:
         return [current]
      if not arc.reversed: # arc is not reversed
         arc.setEndAngleByPt(current.getEndPt())
         return [arc]
      else: # arc is reversed
         arc.setStartAngleByPt(current.getEndPt())
         return [arc]
   else: # there is a previous part
      t = prev.getTanDirectionOnEndPt() if tanDirectionOnStartPt is None else tanDirectionOnStartPt

      if next is None: # there is no subsequent part
         if arc.fromStartEndPtsTan(current.getStartPt(), current.getEndPt(), t) == False:
            return [current]
         return [arc]
      else: # there is a previous and subsequent part
         if arc.fromStartSecondEndPts(prev.getStartPt(), current.getStartPt(), current.getEndPt()) == False:
            return [current]
         if not arc.reversed: # arc is not reversed
            arc.setStartAngleByPt(current.getStartPt())
         else: # arc is reversed
            arc.setEndAngleByPt(current.getStartPt())
         arc2 = QadArc()
         if arc2.fromStartSecondEndPts(current.getStartPt(), current.getEndPt(), next.getEndPt()) == False:
            return [current]
         if not arc2.reversed: # arc is not reversed
            arc2.setEndAngleByPt(current.getEndPt())
         else: # arc is reversed
            arc2.setStartAngleByPt(current.getEndPt())

         midPt = qad_utils.getMiddlePoint(arc.getMiddlePt(), arc2.getMiddlePt())

         if arc.fromStartEndPtsTan(current.getStartPt(), midPt, t) == False:
            return [current]

         if arc2.fromStartEndPtsTan(arc.getEndPt(), current.getEndPt(), \
                                    arc.getTanDirectionOnEndPt()) == False:
            return [current]

         return [arc, arc2]
