# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 class to display snap points

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
import time # profiling

from . import qad_utils
from .qad_variables import QadVariables, QadAUTOSNAPEnum
from .qad_snapper import QadSnapTypeEnum, snapTypeEnum2Descr
from .qad_vertexmarker import QadVertexmarkerIconTypeEnum, QadVertexMarker
from .qad_rubberband import createRubberBand
from .qad_msg import QadMsg
from .qad_geom_relations import QadPerpendicularity


class QadSnapPointsDisplayManager():
   """Class that manages the display of snap points"""


   # ============================================================================
   # __init__
   # ============================================================================
   def __init__(self, mapCanvas):
      self.__mapCanvas = mapCanvas
      self.__vertexMarkers = [] # list of displayed point markers
      self.__startPoint = QgsPointXY()
      self.__iconSize = QadVariables.get(QadMsg.translate("Environment variables", "AUTOSNAPSIZE"))
      self.__color = QColor(255, 0, 0) # color of the marker
      self.__penWidth = 2 # pen width
      self.__lineMarkers = [] # list of RubberBands displayed

   # ============================================================================
   # __del__
   # ============================================================================
   def __del__(self):
      self.removeItems()


   def removeItems(self):
      self.hide()

      # I empty the list of markers by removing them from the canvas
      for vertexMarker in self.__vertexMarkers:
         vertexMarker.removeItem()
      del self.__vertexMarkers[:]

      # I empty the extension line by removing them from the canvas
      for lineMarker in self.__lineMarkers:
         self.__mapCanvas.scene().removeItem(lineMarker)
      del self.__lineMarkers[:]


   def setIconSize(self, iconSize):
      self.__iconSize = iconSize


   def setColor(self, color):
      self.__color = color


   def setPenWidth(self, width):
      self.__penWidth = width


   def setStartPoint(self, point):
      """Sets the starting point for PAR snap mode"""
      self.__startPoint = point


   def __getIconType(self, snapType):
      if snapType == QadSnapTypeEnum.END or snapType == QadSnapTypeEnum.END_PLINE:
         return QadVertexmarkerIconTypeEnum.BOX
      elif snapType == QadSnapTypeEnum.MID:
         return QadVertexmarkerIconTypeEnum.TRIANGLE
      elif snapType == QadSnapTypeEnum.CEN:
         return QadVertexmarkerIconTypeEnum.CIRCLE
      elif snapType == QadSnapTypeEnum.NOD:
         return QadVertexmarkerIconTypeEnum.CIRCLE_X
      elif snapType == QadSnapTypeEnum.QUA:
         return QadVertexmarkerIconTypeEnum.RHOMBUS
      elif snapType == QadSnapTypeEnum.INT:
         return QadVertexmarkerIconTypeEnum.X
      elif snapType == QadSnapTypeEnum.INS:
         return QadVertexmarkerIconTypeEnum.DOUBLE_BOX
      elif snapType == QadSnapTypeEnum.PER:
         return QadVertexmarkerIconTypeEnum.PERP
      elif snapType == QadSnapTypeEnum.TAN:
         return QadVertexmarkerIconTypeEnum.TANGENT
      elif snapType == QadSnapTypeEnum.NEA:
         return QadVertexmarkerIconTypeEnum.DOUBLE_TRIANGLE
      elif snapType == QadSnapTypeEnum.APP:
         return QadVertexmarkerIconTypeEnum.BOX_X
      elif snapType == QadSnapTypeEnum.EXT:
         return QadVertexmarkerIconTypeEnum.INFINITY_LINE
      elif snapType == QadSnapTypeEnum.PAR:
         return QadVertexmarkerIconTypeEnum.PARALLEL
      elif snapType == QadSnapTypeEnum.PR:
         return QadVertexmarkerIconTypeEnum.PROGRESS
      elif snapType == QadSnapTypeEnum.EXT_INT:
         return QadVertexmarkerIconTypeEnum.X_INFINITY_LINE
      elif snapType == QadSnapTypeEnum.PER_DEF:
         return QadVertexmarkerIconTypeEnum.PERP_DEFERRED
      elif snapType == QadSnapTypeEnum.TAN_DEF:
         return QadVertexmarkerIconTypeEnum.TANGENT_DEFERRED
      else:
         return QadVertexmarkerIconTypeEnum.NONE


   def hide(self):
      """
      Hides previously displayed markers
      """
      for vertexMarker in self.__vertexMarkers:
         vertexMarker.hide()

      for lineMarker in self.__lineMarkers:
         lineMarker.hide()


   def show(self, SnapPoints, \
            extLinearObjs = None, \
            parLines = None, \
            intExtLinearObjs = None, \
            oSnapPointsForPolar = None, \
            oSnapLinesForPolar = None):
      """Displays snap points, receives a dictionary of snap point lists
            divided by snap types (e.g. {END : [pt1 .. ptn] MID : [pt1 .. ptn]})
            e
            list of linear objects to extend (list of QadLine or QadArc or QadEllipseArc) for EXT snap mode
            list of lines for parallel mode (QadLine list) for PAR snap mode
            line of linear objects for intersection on extension (list of QadLine or QadArc or QadEllipseArc) for EXT_INT snap mode
      """
      self.hide()

      # I empty the marker list
      for vertexMarker in self.__vertexMarkers:
         vertexMarker.removeItem()
      del self.__vertexMarkers[:]

      # I empty the extension line
      for lineMarker in self.__lineMarkers:
         self.__mapCanvas.scene().removeItem(lineMarker)
      del self.__lineMarkers[:]

      autoSnap = QadVariables.get(QadMsg.translate("Environment variables", "AUTOSNAP"))

      self.__mapCanvas.setToolTip("")

      # snap points
      for snapPoint in SnapPoints.items():
         snapType = snapPoint[0]
         i = -1
         for point in snapPoint[1]:
            i = i + 1

            if autoSnap & QadAUTOSNAPEnum.DISPLAY_MARK: # Turns on the AutoSnap mark
               self.__vertexMarkers.append(self.getVertexMarker(snapType, point))
               # I draw the snap marker
               #self.__vertexMarkers.append(self.getVertexMarker(snapType, point))

            if autoSnap & QadAUTOSNAPEnum.DISPLAY_TOOLTIPS: # Turns on the AutoSnap tooltips
               qad_utils.setMapCanvasToolTip(snapTypeEnum2Descr(snapType))

            # extension lines
            if snapType == QadSnapTypeEnum.EXT and (extLinearObjs is not None):
               for extLinearObj in extLinearObjs:
                  geomType = extLinearObj.whatIs()
                  if geomType == "LINE":
                     dummyPt = QadPerpendicularity.fromPointToInfinityLine(point, extLinearObj)
                     # if dummyPt and point are so close that they are considered equal
                     if qad_utils.ptNear(point, dummyPt):
                        # I take the vertex closest to point
                        if qad_utils.getDistance(point, extLinearObj.getStartPt()) < qad_utils.getDistance(point, extLinearObj.getEndPt()):
                           dummyPt = extLinearObj.getStartPt()
                        else:
                           dummyPt = extLinearObj.getEndPt()

                        # for a bug not yet understood: if the line has only 2 vertices and
                        # have the same x or y (horizontal or vertical line)
                        # the line is not drawn so I move the x or y a little
                        dummyPt = qad_utils.getAdjustedRubberBandVertex(point, dummyPt)
                        # I draw the extension line
                        self.__lineMarkers.append(self.getLineMarker(point, dummyPt))
                  else: # ARC o ELLIPSE_ARC
                     clonedLinearObj = extLinearObj.copy()

                     if qad_utils.getDistance(point, clonedLinearObj.getStartPt()) > \
                        qad_utils.getDistance(point, clonedLinearObj.getEndPt()):
                        clonedLinearObj.setEndAngleByPt(point)
                     else:
                        clonedLinearObj.setStartAngleByPt(point)

                     # I draw the extension arc
                     arcMarker = self.getLinearObjMarker(clonedLinearObj)
                     if arcMarker is not None:
                        self.__lineMarkers.append(arcMarker)

            # linee di parallelismo
            if snapType == QadSnapTypeEnum.PAR and (self.__startPoint is not None):
               boundBox = self.__mapCanvas.extent()
               xMin = boundBox.xMinimum()
               yMin = boundBox.yMinimum()
               xMax = boundBox.xMaximum()
               yMax = boundBox.yMaximum()

               upperIntersX = qad_utils.getXOnInfinityLine(self.__startPoint, point, yMax)
               if upperIntersX > xMax or upperIntersX < xMin:
                  upperIntersX = None

               lowerIntersX = qad_utils.getXOnInfinityLine(self.__startPoint, point, yMin)
               if lowerIntersX > xMax or lowerIntersX < xMin:
                  lowerIntersX = None

               leftIntersY  = qad_utils.getYOnInfinityLine(self.__startPoint, point, xMin)
               if leftIntersY > yMax or leftIntersY < yMin:
                  leftIntersY = None

               rightIntersY = qad_utils.getYOnInfinityLine(self.__startPoint, point, xMax)
               if rightIntersY > yMax or rightIntersY < yMin:
                  rightIntersY = None

               p1 = None
               p2 = None

               if upperIntersX is not None:
                  p1 = QgsPointXY(upperIntersX, yMax)

               if leftIntersY is not None:
                  if leftIntersY != yMax:
                     if p1 is None:
                        p1 = QgsPointXY(xMin, leftIntersY)
                     else:
                        p2 = QgsPointXY(xMin, leftIntersY)

               if lowerIntersX is not None:
                  if lowerIntersX != xMin:
                     if p1 is None:
                        p1 = QgsPointXY(lowerIntersX, yMin)
                     elif p2 is None:
                        p2 = QgsPointXY(lowerIntersX, yMin)

               if rightIntersY is not None:
                  if rightIntersY != yMin:
                     if p2 is None:
                        p2 = QgsPointXY(xMax, rightIntersY)

               if (p1 is not None) and (p2 is not None):
                  # for a bug not yet understood: if the line has only 2 vertices and
                  # have the same x or y (horizontal or vertical line)
                  # the line is not drawn so I move the x or y a little
                  p2 = qad_utils.getAdjustedRubberBandVertex(p1, p2)
                  # I draw the parallel line
                  self.__lineMarkers.append(self.getLineMarker(p1, p2))

      # lines for polar pointing
      if oSnapLinesForPolar is not None:
         for line in oSnapLinesForPolar:
            lineMarker = self.getLineMarkerForPolar(line.getStartPt(), line.getEndPt())
            if lineMarker is not None:
               # I draw the line
               self.__lineMarkers.append(lineMarker)

      # midpoints of linear objects marked as to be extended
      if extLinearObjs is not None:
         for extLinearObj in extLinearObjs:
            point = extLinearObj.getMiddlePt()
            # I draw the extension marker
            self.__vertexMarkers.append(self.getVertexMarker(QadSnapTypeEnum.EXT, point))

      # midpoints of lines marked as parallel
      if parLines is not None:
         for parLine in parLines:
            point = parLine.getMiddlePt()
            # I draw the parallel marker
            self.__vertexMarkers.append(self.getVertexMarker(QadSnapTypeEnum.PAR, point))

      # midpoint of the line marked as extended intersection
      if intExtLinearObjs is not None:
         for intExtLinearObj in intExtLinearObjs:
            point = intExtLinearObj.getMiddlePt()
            # I draw the marker
            self.__vertexMarkers.append(self.getVertexMarker(QadSnapTypeEnum.EXT_INT, point))

      # osnap points used for the polar option
      if oSnapPointsForPolar is not None:
         for snapPoint in oSnapPointsForPolar.items():
            snapType = snapPoint[0]
            for item in snapPoint[1]:
               # I draw the snap marker
               self.__vertexMarkers.append(self.getVertexMarker(snapType, item))


   def getVertexMarker(self, snapType, point):
      """Create a point marker"""
      vertexMarker = QadVertexMarker(self.__mapCanvas)
      vertexMarker.setIconSize(self.__iconSize)
      vertexMarker.setColor(self.__color)
      vertexMarker.setPenWidth(self.__penWidth)
      vertexMarker.setIconType(self.__getIconType(snapType))
      vertexMarker.setCenter(point)
      return vertexMarker


   def getLineMarker(self, pt1, pt2):
      """Create a linear marker"""
      lineMarker = createRubberBand(self.__mapCanvas, QgsWkbTypes.LineGeometry, True)
      lineMarker.setColor(self.__color)
      lineMarker.setLineStyle(Qt.DashLine)
      lineMarker.addPoint(pt1, False)
      lineMarker.addPoint(pt2, True)
      return lineMarker


   def getLineMarkerForPolar(self, startPoint, point):
      """Creates a linear marker for polar tracking"""
      boundBox = self.__mapCanvas.extent()
      xMin = boundBox.xMinimum()
      yMin = boundBox.yMinimum()
      xMax = boundBox.xMaximum()
      yMax = boundBox.yMaximum()

      p1 = startPoint
      p2 = point

      x2 = None
      if p2.y() > p1.y(): # half-line that goes upwards
         x2 = qad_utils.getXOnInfinityLine(p1, p2, yMax)
      elif p2.y() < p1.y(): # half-line going downwards
         x2 = qad_utils.getXOnInfinityLine(p1, p2, yMin)
      else: # horizontal ray line
         if p2.x() > p1.x(): # half-line going to the right
            x2 = xMax
         elif p2.x() < p1.x(): # half-line going to the left
            x2 = xMin

      y2 = None
      if p2.x() > p1.x(): # half-line going to the right
         y2 = qad_utils.getYOnInfinityLine(p1, p2, xMax)
      elif p2.x() < p1.x(): # half-line going to the left
         y2 = qad_utils.getYOnInfinityLine(p1, p2, xMin)
      else: # vertical ray line
         if p2.y() > p1.y(): # half-line that goes upwards
            y2 = yMax
         elif p2.y() < p1.y(): # half-line going downwards
            y2 = yMin

      if x2 is not None:
         if x2 > xMax:
            x2 = xMax
         elif x2 < xMin:
            x2 = xMin

      if y2 is not None:
         if y2 > yMax:
            y2 = yMax
         elif y2 < yMin:
            y2 = yMin

      if (x2 is not None) and (y2 is not None):
         p2 = QgsPointXY(x2, y2)
         # for a bug not yet understood: if the line has only 2 vertices and
         # have the same x or y (horizontal or vertical line)
         # the line is not drawn so I move the x or y a little
         p2 = qad_utils.getAdjustedRubberBandVertex(p1, p2)
         # I draw the line
         return self.getLineMarker(p1, p2)
      else:
         return None


   def getLinearObjMarker(self, linearObj):
      """Creates a linear marker x a linear object"""
      lineMarker = createRubberBand(self.__mapCanvas, QgsWkbTypes.LineGeometry, True)
      lineMarker.setColor(self.__color)
      lineMarker.setLineStyle(Qt.DotLine)
      points = linearObj.asPolyline()
      if points is None:
         return None
      tot = len(points)
      i = 0
      while i < (tot - 1):
         lineMarker.addPoint(points[i], False)
         i = i + 1
      lineMarker.addPoint(points[i], True)
      return lineMarker

