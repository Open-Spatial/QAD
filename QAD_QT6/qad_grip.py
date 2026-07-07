# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 class to manage grips

                              -------------------
        begin                : 2015-09-29
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

from qgis.PyQt.QtCore import QPointF, QRectF
from qgis.PyQt.QtGui import QPen, QColor, QBrush
from qgis.core import QgsPointXY, QgsWkbTypes, QgsGeometry
from qgis.gui import QgsMapCanvasItem

from .qad_multi_geom import *
from .qad_variables import QadVariables
from .qad_entity import QadEntity, QadEntityTypeEnum
from .qad_dim import QadDimStyles, QadDimComponentEnum
from .qad_msg import QadMsg


# ===============================================================================
# QadGripStatusEnum class.
# ===============================================================================
class QadGripStatusEnum():
   NONE             = 0  # none
   UNSELECTED       = 1  # grip not selected
   SELECTED         = 2  # grip selected
   HOVER            = 3  # grips not selected when the cursor lands on them


# ===============================================================================
# QadGripIconTypeEnum class.
# ===============================================================================
class QadGripIconTypeEnum():
   NONE             = 0  # none
   BOX              = 1  # a square
   CIRCLE           = 2  # circle
   RECTANGLE        = 3  # rettangolo


# ===============================================================================
# QadGripMarker class.
# ===============================================================================
class QadGripMarker(QgsMapCanvasItem):
   """Class that manages grip markers"""


   # ============================================================================
   # __init__
   # ============================================================================
   def __init__(self, mapCanvas):
      QgsMapCanvasItem.__init__(self, mapCanvas)
      self.canvas = mapCanvas
      self.iconType = QadGripIconTypeEnum.BOX # icon to be shown
      self.iconSize = QadVariables.get(QadMsg.translate("Environment variables", "GRIPSIZE"))
      self.borderColor = QadVariables.get(QadMsg.translate("Environment variables", "GRIPCONTOUR")) # color of the border
      self.center = QgsPointXY(0, 0) #  coordinates of the point in the center
      self.setGrip(QadGripStatusEnum.UNSELECTED, QadGripIconTypeEnum.BOX)


   def __del__(self):
      self.removeItem()


   def removeItem(self):
      self.canvas.scene().removeItem(self)


   def setCenter(self, point):
      # point is in map coordinates
      self.center = point
      pt = self.toCanvasCoordinates(self.center)
      self.setPos(pt)


   def setGrip(self, status, iconType, rot = None):
      # rot in radians counterclockwise (0 = horizontal)
      if status == QadGripStatusEnum.UNSELECTED:
         self.fillColor = QadVariables.get(QadMsg.translate("Environment variables", "GRIPCOLOR"))
      elif status == QadGripStatusEnum.SELECTED:
         self.fillColor = QadVariables.get(QadMsg.translate("Environment variables", "GRIPHOT"))
      elif status == QadGripStatusEnum.HOVER:
         self.fillColor = QadVariables.get(QadMsg.translate("Environment variables", "GRIPHOVER"))

      self.status = status
      self.__iconType = iconType
      if rot is not None:
         self.__rot = -qad_utils.toDegrees(rot) # trasformo in gradi in senso orario


   def paint(self, painter, option, widget):
      """painter is a QPainter"""
      pen = QPen(QColor(self.borderColor))
      pen.setWidth(1)
      painter.setPen(pen)
      painter.rotate(self.__rot)

      if self.__iconType == QadGripIconTypeEnum.NONE:
         pass
      elif self.__iconType == QadGripIconTypeEnum.BOX:
         # a square
         painter.fillRect(-self.iconSize, -self.iconSize, self.iconSize * 2, self.iconSize * 2, QBrush(QColor(self.fillColor)));
         painter.drawRect(-self.iconSize, -self.iconSize, self.iconSize * 2, self.iconSize * 2)
      elif self.__iconType == QadGripIconTypeEnum.CIRCLE:
         # circle
         painter.setBrush(QBrush(QColor(self.fillColor)))
         painter.drawEllipse(QPointF(0, 0), self.iconSize, self.iconSize)
      elif self.__iconType == QadGripIconTypeEnum.RECTANGLE:
         # a rectangle
         painter.fillRect(-self.iconSize, -int(self.iconSize / 2), self.iconSize * 2, self.iconSize, QBrush(QColor(self.fillColor)));
         painter.drawRect(-self.iconSize, -int(self.iconSize / 2), self.iconSize * 2, self.iconSize)


   def boundingRect(self):
      if self.__rot != 0:
         width = qad_utils.getDistance(QgsPointXY(0,0), QgsPointXY(self.iconSize, self.iconSize))
         height = width
      else:
         width = self.iconSize
         height = self.iconSize

      return QRectF(-width/2, -height/2, width, height)


   def updatePosition(self):
      self.setCenter(self.center)


# ===============================================================================
# QadGripPointTypeEnum class.
# ===============================================================================
class QadGripPointTypeEnum():
   NONE           = 0  # none
   VERTEX         = 1  # vertex of a geometry
   LINE_MID_POINT = 2  # midpoint of a segment
   CENTER         = 3  # center of a circle, an arc, an ellipse or an arc of an ellipse
   QUA_POINT      = 4  # quadrant point
   ARC_MID_POINT  = 5  # midpoint of an arc or an arc of an ellipse
   END_VERTEX     = 6  # initial and final vertex of a geometry


# ===============================================================================
# QadEntityGripPoint class.
# ===============================================================================
class QadEntityGripPoint():
   """Class that manages a grip point for an entity"""


   # ============================================================================
   # __init__
   # ============================================================================
   def __init__(self, mapCanvas, point, type, atGeom = 0, atSubGeom = 0, nVertex = 0, rot = 0.0):
      self.atGeom = atGeom # geometry number (0-index)
      self.atSubGeom = atSubGeom # sub-geometry number (0-index)
      self.nVertex = nVertex # vertex number of the geometry polyline and sub-geometry (0-index)

      self.gripType = type

      self.gripMarker = QadGripMarker(mapCanvas)
      self.gripMarker.setGrip(QadGripStatusEnum.UNSELECTED, self.gripType2IconType(self.gripType), rot)
      self.gripMarker.setCenter(point)

   def __del__(self):
      self.removeItem()
      del self.gripMarker

   def removeItem(self):
      self.gripMarker.removeItem()

   def getPoint(self):
      return self.gripMarker.center

   def isIntersecting(self, point):
      # point is in map coordinates
      ToleranceInMapUnits = self.gripMarker.iconSize * self.gripMarker.canvas.mapSettings().mapUnitsPerPixel()
      if point.x() >= self.getPoint().x() - ToleranceInMapUnits and \
         point.x() <= self.getPoint().x() + ToleranceInMapUnits and \
         point.y() >= self.getPoint().y() - ToleranceInMapUnits and \
         point.y() <= self.getPoint().y() + ToleranceInMapUnits:
         return True
      else:
         return False

   def select(self): # select a grip
      self.gripMarker.setGrip(QadGripStatusEnum.SELECTED, self.gripType2IconType(self.gripType))
      self.gripMarker.show()

   def unselect(self): # deselects a grip
      self.gripMarker.setGrip(QadGripStatusEnum.UNSELECTED, self.gripType2IconType(self.gripType))
      self.gripMarker.show()

   def hover(self): # grip not selected when cursor lands on it
      if self.getStatus() == QadGripStatusEnum.UNSELECTED:
         self.gripMarker.setGrip(QadGripStatusEnum.HOVER, self.gripType2IconType(self.gripType))
         self.gripMarker.show()

   def getStatus(self):
      return self.gripMarker.status

   def gripType2IconType(self, gripType):
      if gripType == QadGripPointTypeEnum.VERTEX or gripType == QadGripPointTypeEnum.END_VERTEX:
         return QadGripIconTypeEnum.BOX
      elif gripType == QadGripPointTypeEnum.LINE_MID_POINT or gripType == QadGripPointTypeEnum.ARC_MID_POINT:
         return QadGripIconTypeEnum.RECTANGLE
      elif gripType == QadGripPointTypeEnum.CENTER:
         return QadGripIconTypeEnum.CIRCLE
      elif gripType == QadGripPointTypeEnum.QUA_POINT:
         return QadGripIconTypeEnum.BOX
      else:
         return None


# ===============================================================================
# QadEntityGripPoints class.
# ===============================================================================
class QadEntityGripPoints(QgsMapCanvasItem):
   """Class that manages grip points for an entity"""


   # ============================================================================
   # __init__
   # ============================================================================
   def __init__(self, plugIn, entity = None, grips = 2):
      self.plugIn = plugIn
      self.mapCanvas = plugIn.canvas
      self.gripPoints = [] # list of grip points in map coordinates
      self.iHoverGripPoints = [] # list of hover point positions in gripPoints
      # Build the spatial index for faster lookup.
      self.index = QgsSpatialIndex()
      if entity is not None:
         self.entity = QadEntity(entity)
         self.gripPoints = self.initGripPoints(grips)
         self.index = self.initIndexGripPoints()


   def __del__(self):
      self.removeItems()
      if self.index is not None:
         del self.index


   def set(self, layer, featureId, grips = 2):
      self.entity = QadEntity()
      self.entity.set(layer, featureId)
      self.gripPoints = self.initGripPoints(grips)
      self.index = self.initIndexGripPoints()


   def removeItems(self):
      for gripPoint in self.gripPoints:
         gripPoint.removeItem()
      del self.gripPoints[:]
      del self.iHoverGripPoints[:]
      del self.index
      self.index = QgsSpatialIndex()


   def selectIntersectingGripPoints(self, point):
      # selects grips that intersect a point in map coordinates
      res = 0

      # Get the i-pos of all the features in the index that are within
      # the bounding box of the current feature because these are the ones
      # that will be touching.
      ToleranceInMapUnits = QadVariables.get(QadMsg.translate("Environment variables", "GRIPSIZE")) * self.mapCanvas.mapSettings().mapUnitsPerPixel()
      rect = QgsRectangle(point.x() - ToleranceInMapUnits, point.y() - ToleranceInMapUnits, \
                          point.x() + ToleranceInMapUnits, point.y() + ToleranceInMapUnits)

      iList = self.index.intersects(rect)
      for i in iList:
         self.gripPoints[i].select()
         res = res + 1

#       for gripPoint in self.gripPoints:
#          if gripPoint.isIntersecting(point):
#             gripPoint.select()
#             res = res + 1

      return res


   def unselectIntersectingGripPoints(self, point):
      # deselects grips that intersect a point in map coordinates
      res = 0

      # Get the i-pos of all the features in the index that are within
      # the bounding box of the current feature because these are the ones
      # that will be touching.
      ToleranceInMapUnits = QadVariables.get(QadMsg.translate("Environment variables", "GRIPSIZE")) * self.mapCanvas.mapSettings().mapUnitsPerPixel()
      rect = QgsRectangle(point.x() - ToleranceInMapUnits, point.y() - ToleranceInMapUnits, \
                          point.x() + ToleranceInMapUnits, point.y() + ToleranceInMapUnits)

      iList = self.index.intersects(rect)
      for i in iList:
         self.gripPoints[i].unselect()
         res = res + 1

#       for gripPoint in self.gripPoints:
#          if gripPoint.isIntersecting(point):
#             gripPoint.unselect()
#             res = res + 1
      return res


   def toggleSelectIntersectingGripPoints(self, point):
      # select deselected grips and deselect selected grips
      # that intersect a point in map coordinates

      # Get the i-pos of all the features in the index that are within
      # the bounding box of the current feature because these are the ones
      # that will be touching.
      ToleranceInMapUnits = QadVariables.get(QadMsg.translate("Environment variables", "GRIPSIZE")) * self.mapCanvas.mapSettings().mapUnitsPerPixel()
      rect = QgsRectangle(point.x() - ToleranceInMapUnits, point.y() - ToleranceInMapUnits, \
                          point.x() + ToleranceInMapUnits, point.y() + ToleranceInMapUnits)

      iList = self.index.intersects(rect)
      for i in iList:
         if self.gripPoints[i].getStatus() == QadGripStatusEnum.SELECTED:
            self.gripPoints[i].unselect()
         else:
            self.gripPoints[i].select()

#       for gripPoint in self.gripPoints:
#          if gripPoint.isIntersecting(point):
#             if gripPoint.getStatus() == QadGripStatusEnum.SELECTED:
#                gripPoint.unselect()
#             else:
#                gripPoint.select()


   def hoverIntersectingGripPoints(self, point):
      # I select in hover mode the grips that intersect a point (in map coordinates)
      # not selected when the cursor lands on it

      for i in self.iHoverGripPoints:
         status = self.gripPoints[i].getStatus()
         if status == QadGripStatusEnum.SELECTED:
            self.gripPoints[i].select()
         else:
            self.gripPoints[i].unselect()

#       for gripPoint in self.gripPoints:
#          status = gripPoint.getStatus()
#          if status == QadGripStatusEnum.SELECTED:
#             gripPoint.select()
#          else:
#             gripPoint.unselect()

      res = 0
      del self.iHoverGripPoints[:]

      # Get the i-pos of all the features in the index that are within
      # the bounding box of the current feature because these are the ones
      # that will be touching.
      ToleranceInMapUnits = QadVariables.get(QadMsg.translate("Environment variables", "GRIPSIZE")) * self.mapCanvas.mapSettings().mapUnitsPerPixel()
      rect = QgsRectangle(point.x() - ToleranceInMapUnits, point.y() - ToleranceInMapUnits, \
                          point.x() + ToleranceInMapUnits, point.y() + ToleranceInMapUnits)

      iList = self.index.intersects(rect)
      for i in iList:
         self.gripPoints[i].hover()
         self.iHoverGripPoints.append(i)
         res = res + 1

#       for gripPoint in self.gripPoints:
#          if gripPoint.isIntersecting(point):
#             gripPoint.hover()
#             res = res + 1
#          else:
#             status = gripPoint.getStatus()
#             if status == QadGripStatusEnum.SELECTED:
#                gripPoint.select()
#             else:
#                gripPoint.unselect()
      return res


   def isIntersecting(self, point):
      # returns the first grip point (QadEntityGripPoint) that intersects point (in map coordinates)

      # Get the i-pos of all the features in the index that are within
      # the bounding box of the current feature because these are the ones
      # that will be touching.
      ToleranceInMapUnits = QadVariables.get(QadMsg.translate("Environment variables", "GRIPSIZE")) * self.mapCanvas.mapSettings().mapUnitsPerPixel()
      rect = QgsRectangle(point.x() - ToleranceInMapUnits, point.y() - ToleranceInMapUnits, \
                          point.x() + ToleranceInMapUnits, point.y() + ToleranceInMapUnits)

      iList = self.index.intersects(rect)
      for i in iList:
         return self.gripPoints[i]


#       for gripPoint in self.gripPoints:
#          if gripPoint.isIntersecting(point):
#             return gripPoint
      return None


   def getSelectedGripPoints(self):
      # returns a list of points where grips are selected
      result = []

      for gripPoint in self.gripPoints:
         if gripPoint.getStatus() == QadGripStatusEnum.SELECTED:
            result.append(gripPoint)

      return result


   def initGripPoints(self, grips = 2):
      # returns a list of QadEntityGripPoints
      atGeom = 0
      atSubGeom = 0
      result = []

      g = self.entity.getQadGeom()
      if g is None:
         return result

      # check if the entity belongs to a dimensioning style
      dimEntity = QadDimStyles.getDimEntity(self.entity)
      if dimEntity is not None:
         return self.getGripPointsFromDimComponent(dimEntity, self.entity)

      gType = g.whatIs()
      if gType == "POINT":
         # I convert the point from the coordinate layer into map coordinates
         gp = QadEntityGripPoint(self.mapCanvas, g, QadGripPointTypeEnum.VERTEX)
         result.append(gp)

      elif gType == "MULTI_POINT":
         for atGeom in range(0, g.qty()):
            gp = QadEntityGripPoint(self.mapCanvas, g.getPointAt(atGeom), QadGripPointTypeEnum.VERTEX, atGeom)
            result.append(gp)

      elif gType == "ARC":
         result = self.getGripPointsFromQadArc(g, 0, 0, grips)

      elif gType == "CIRCLE":
         result = self.getGripPointsFromQadCircle(g, 0, 0)

      elif gType == "ELLIPSE":
         result = self.getGripPointsFromQadEllipse(g, 0, 0)

      elif gType == "ELLIPSE_ARC":
         result = self.getGripPointsFromQadEllipseArc(g, 0, 0, grips)

      elif gType == "LINE":
         result = self.getGripPointsFromQadLine(g, 0, 0, grips)

      elif gType == "POLYLINE":
         result = self.getGripPointsFromPolyline(g, 0, 0, grips)

      elif gType == "MULTI_LINEAR_OBJ":
         for atGeom in range(0, g.qty()):
            subGeom = g.getLinearObjectAt(atGeom)
            subGeomType = subGeom.whatIs()
            if subGeomType == "ARC":
               result.extend(self.getGripPointsFromQadArc(subGeom, atGeom, 0, grips))
            elif subGeomType == "CIRCLE":
               result.extend(self.getGripPointsFromQadCircle(subGeom, atGeom, 0))
            elif subGeomType == "ELLIPSE":
               result.extend(self.getGripPointsFromQadEllipse(subGeom, atGeom, 0))
            elif subGeomType == "ELLIPSE_ARC":
               result.extend(self.getGripPointsFromQadEllipseArc(subGeom, atGeom, 0, grips))
            elif subGeomType == "LINE":
               result.extend(self.getGripPointsFromQadLine(subGeom, atGeom, 0, grips))
            elif subGeomType == "POLYLINE":
               result.extend(self.getGripPointsFromPolyline(subGeom, atGeom, 0, grips))

      elif gType == "POLYGON":
         for atSubGeom in range(0, g.qty()):
            closedObj = g.getClosedObjectAt(atSubGeom)
            subGeomType = closedObj.whatIs()
            if subGeomType == "ARC":
               result.extend(self.getGripPointsFromQadArc(closedObj, 0, atSubGeom, grips))
            elif subGeomType == "CIRCLE":
               result.extend(self.getGripPointsFromQadCircle(closedObj, 0, atSubGeom))
            elif subGeomType == "ELLIPSE":
               result.extend(self.getGripPointsFromQadEllipse(closedObj, 0, atSubGeom))
            elif subGeomType == "ELLIPSE_ARC":
               result.extend(self.getGripPointsFromQadEllipseArc(closedObj, 0, atSubGeom, grips))
            elif subGeomType == "LINE":
               result.extend(self.getGripPointsFromQadLine(closedObj, 0, atSubGeom, grips))
            elif subGeomType == "POLYLINE":
               result.extend(self.getGripPointsFromPolyline(closedObj, 0, atSubGeom, grips))
               # add the centroid
               gp = QadEntityGripPoint(self.mapCanvas, closedObj.getCentroid(), QadGripPointTypeEnum.CENTER, 0, atSubGeom)
               result.append(gp)

      elif gType == "MULTI_POLYGON":
         for atGeom in range(0, g.qty()):
            polygon = g.getPolygonAt(atGeom)
            for atSubGeom in range(0, polygon.qty()):
               closedObj = polygon.getClosedObjectAt(atSubGeom)
               subGeomType = closedObj.whatIs()
               if subGeomType == "ARC":
                  result.extend(self.getGripPointsFromQadArc(closedObj, atGeom, atSubGeom, grips))
               elif subGeomType == "CIRCLE":
                  result.extend(self.getGripPointsFromQadCircle(closedObj, atGeom, atSubGeom))
               elif subGeomType == "ELLIPSE":
                  result.extend(self.getGripPointsFromQadEllipse(closedObj, atGeom, atSubGeom))
               elif subGeomType == "ELLIPSE_ARC":
                  result.extend(self.getGripPointsFromQadEllipseArc(closedObj, atGeom, atSubGeom, grips))
               elif subGeomType == "LINE":
                  result.extend(self.getGripPointsFromQadLine(closedObj, atGeom, atSubGeom, grips))
               elif subGeomType == "POLYLINE":
                  result.extend(self.getGripPointsFromPolyline(closedObj, atGeom, atSubGeom, grips))
                  # add the centroid
                  gp = QadEntityGripPoint(self.mapCanvas, closedObj.getCentroid(), QadGripPointTypeEnum.CENTER, atGeom, atSubGeom)
                  result.append(gp)

               atSubGeom = atSubGeom + 1
            atGeom = atGeom + 1

      return result


   def initIndexGripPoints(self):
      # initializes the spatial index of the grip point list
      index = QgsSpatialIndex()
      f = QgsFeature(QgsFields(), 0)
      i = 0
      for gp in self.gripPoints:
         f.setId(i)
         f.setGeometry(QgsGeometry.fromPointXY(gp.getPoint()))
         index.addFeature(f)
         i = i + 1

      return index


   def getGripPointsFromPolyline(self, polyline, atGeom = 0, atSubGeom = 0, grips = 2):
      """Gets a list of grip points from a QadPolyline in map coordinates (vertices and midpoints with rotation)
            grips = 1 Displays grips
            grips = 2 Displays additional midpoint grips on polyline segments
      """
      result = []

      isClosed = polyline.isClosed()
      nVertex = 0
      while nVertex < polyline.qty():
         linearObject = polyline.getLinearObjectAt(nVertex)
         startPt = linearObject.getStartPt()
         if isClosed == False and nVertex == 0:
            gp = QadEntityGripPoint(self.mapCanvas, startPt, QadGripPointTypeEnum.END_VERTEX, atGeom, atSubGeom, nVertex)
         else:
            gp = QadEntityGripPoint(self.mapCanvas, startPt, QadGripPointTypeEnum.VERTEX, atGeom, atSubGeom, nVertex)
         result.append(gp)

         if grips == 2: # Displays additional midpoint grips on polyline segments
            middlePt = linearObject.getMiddlePt()
            rot = linearObject.getTanDirectionOnPt(middlePt)
            linearObjectType = linearObject.whatIs()
            if linearObjectType == "LINE":
               gp = QadEntityGripPoint(self.mapCanvas, middlePt, QadGripPointTypeEnum.LINE_MID_POINT, atGeom, atSubGeom, nVertex, rot)
            elif linearObjectType == "ARC" or linearObjectType == "ELLIPSE_ARC":
               gp = QadEntityGripPoint(self.mapCanvas, middlePt, QadGripPointTypeEnum.ARC_MID_POINT, atGeom, atSubGeom, nVertex, rot)

            result.append(gp)
         nVertex = nVertex + 1

      # only if the polyline is open
      if isClosed == False:
         linearObject = polyline.getLinearObjectAt(-1) # last part
         endPt = linearObject.getEndPt()
         gp = QadEntityGripPoint(self.mapCanvas, endPt, QadGripPointTypeEnum.END_VERTEX, atGeom, atSubGeom, nVertex)
         result.append(gp)

      return result


   def getGripPointsFromQadLine(self, line, atGeom = 0, atSubGeom = 0, grips = 2):
      """Gets a list of grip points from a QadLine in map coordinates (start, end, middle)"""
      result = []
      startPt = line.getStartPt()
      gp = QadEntityGripPoint(self.mapCanvas, startPt, QadGripPointTypeEnum.END_VERTEX, atGeom, atSubGeom, 0)
      result.append(gp)

      if grips == 2: # Displays additional midpoint grips on polyline segments
         middlePt = line.getMiddlePt()
         rot = line.getTanDirectionOnMiddlePt()
         gp = QadEntityGripPoint(self.mapCanvas, middlePt, QadGripPointTypeEnum.LINE_MID_POINT, atGeom, atSubGeom, 0, rot)
         result.append(gp)


      endPt = line.getEndPt()
      gp = QadEntityGripPoint(self.mapCanvas, endPt, QadGripPointTypeEnum.END_VERTEX, atGeom, atSubGeom, 1)
      result.append(gp)

      return result


   def getGripPointsFromQadCircle(self, circle, atGeom = 0, atSubGeom = 0):
      """Gets a list of grip points from a QadCircle in map coordinates (center and quadrant points)"""
      result = []
      gp = QadEntityGripPoint(self.mapCanvas, circle.center, QadGripPointTypeEnum.CENTER, atGeom, atSubGeom, -1)
      result.append(gp)
      qua_points = circle.getQuadrantPoints()
      for pt in qua_points:
         gp = QadEntityGripPoint(self.mapCanvas, pt, QadGripPointTypeEnum.QUA_POINT, atGeom, atSubGeom, -1)
         result.append(gp)

      return result


   def getGripPointsFromQadEllipse(self, ellipse, atGeom = 0, atSubGeom = 0):
      """Gets a list of grip points from a QadEllipse in map coordinates (center and quadrant points)"""
      result = []
      gp = QadEntityGripPoint(self.mapCanvas, ellipse.center, QadGripPointTypeEnum.CENTER, atGeom, atSubGeom, -1)
      result.append(gp)
      qua_points = ellipse.getQuadrantPoints()
      for pt in qua_points:
         gp = QadEntityGripPoint(self.mapCanvas, pt, QadGripPointTypeEnum.QUA_POINT, atGeom, atSubGeom, -1)
         result.append(gp)

      return result


   def getGripPointsFromQadArc(self, arc, atGeom = 0, atSubGeom = 0, grips = 2):
      """Gets a list of grip points from a QadArc in map coordinates (center, start, end, middle point)"""
      result = []
      gp = QadEntityGripPoint(self.mapCanvas, arc.center, QadGripPointTypeEnum.CENTER, atGeom, atSubGeom, -1)
      result.append(gp)

      startPt = arc.getStartPt()
      gp = QadEntityGripPoint(self.mapCanvas, startPt, QadGripPointTypeEnum.END_VERTEX, atGeom, atSubGeom, 0)
      result.append(gp)

      endPt = arc.getEndPt()
      gp = QadEntityGripPoint(self.mapCanvas, endPt, QadGripPointTypeEnum.END_VERTEX, atGeom, atSubGeom, 1)
      result.append(gp)

      if grips == 2: # Displays additional midpoint grips on polyline segments
         middlePt = arc.getMiddlePt()
         rot = arc.getTanDirectionOnMiddlePt()
         gp = QadEntityGripPoint(self.mapCanvas, middlePt, QadGripPointTypeEnum.ARC_MID_POINT, atGeom, atSubGeom, 0, rot)
         result.append(gp)

      return result


   def getGripPointsFromQadEllipseArc(self, ellipseArc, atGeom = 0, atSubGeom = 0, grips = 2):
      """Gets a list of grip points from a QadEllipseArc in map coordinates (center point, start point, end point, and quadrant points)"""
      result = []
      gp = QadEntityGripPoint(self.mapCanvas, ellipseArc.center, QadGripPointTypeEnum.CENTER, atGeom, atSubGeom, -1)
      result.append(gp)

      startPt = ellipseArc.getStartPt()
      gp = QadEntityGripPoint(self.mapCanvas, startPt, QadGripPointTypeEnum.END_VERTEX, atGeom, atSubGeom, 0)
      result.append(gp)

      endPt = ellipseArc.getEndPt()
      gp = QadEntityGripPoint(self.mapCanvas, endPt, QadGripPointTypeEnum.END_VERTEX, atGeom, atSubGeom, 1)
      result.append(gp)

      qua_points = ellipseArc.getQuadrantPoints()
      for pt in qua_points:
         if pt is not None:
            gp = QadEntityGripPoint(self.mapCanvas, pt, QadGripPointTypeEnum.QUA_POINT, atGeom, atSubGeom, -1)
            result.append(gp)

      return result


   def getGripPointsFromDimComponent(self, dimEntity, component):
      """Gets a list of dimension component grip points
            component = QadEntity
      """
      result = []
      dimComponent = dimEntity.getDimComponentByEntity(component)
      if dimComponent is None: return result

      if dimComponent == QadDimComponentEnum.TEXT_PT or \
         dimComponent == QadDimComponentEnum.DIM_PT1 or \
         dimComponent == QadDimComponentEnum.DIM_PT2:
         g = component.getQadGeom()
         gType = g.whatIs()
         if gType == "POINT":
            gp = QadEntityGripPoint(self.mapCanvas, g, QadGripPointTypeEnum.VERTEX)
            result.append(gp)

      return result


# ===============================================================================
# QadEntitySetGripPoints class.
# ===============================================================================
class QadEntitySetGripPoints(QgsMapCanvasItem):
   """Class that manages grip points for a selection set of entities"""


   # ============================================================================
   # __init__
   # ============================================================================
   def __init__(self, plugIn):
      self.plugIn = plugIn
      self.mapCanvas = plugIn.canvas
      self.entityGripPoints = []


   def __del__(self):
      self.removeItems()


   def removeItems(self):
      for entityGripPoint in self.entityGripPoints:
         entityGripPoint.removeItems()
      del self.entityGripPoints[:]


   def set(self, entitySet, grips = 2):
      """
         grips = 0 Hides grips
         grips = 1 Displays grips
         grips = 2 Displays additional midpoint grips on polyline segments
      """
      self.removeItems()

      if grips == 0: # nasconde i grip
         return

      # for each layer
      for layerEntitySet in entitySet.layerEntitySetList:
         for featureId in layerEntitySet.featureIds:
            entityGripPoints = QadEntityGripPoints(self.plugIn)
            entityGripPoints.set(layerEntitySet.layer, featureId, grips)
            self.entityGripPoints.append(entityGripPoints)


   def addEntity(self, entity, grips = 2):
      """
         grips = 0 Hides grips
         grips = 1 Displays grips
         grips = 2 Displays additional midpoint grips on polyline segments
      """
      if grips == 0: # nasconde i grip
         return
      if self.containsEntity(entity) == False:
         entityGripPoints = QadEntityGripPoints(self.plugIn)
         entityGripPoints.set(entity.layer, entity.featureId, grips)
         self.entityGripPoints.append(entityGripPoints)


   def hoverIntersectingGripPoints(self, point):
      res = 0
      for entityGripPoint in self.entityGripPoints:
         res = res + entityGripPoint.hoverIntersectingGripPoints(point)
      return res


   def selectIntersectingGripPoints(self, point):
      res = 0
      for entityGripPoint in self.entityGripPoints:
         res = res + entityGripPoint.selectIntersectingGripPoints(point)
      return res


   def unselectIntersectingGripPoints(self, point):
      res = 0
      for entityGripPoint in self.entityGripPoints:
         res = res + entityGripPoint.unselectIntersectingGripPoints(point)
      return res


   def toggleSelectIntersectingGripPoints(self, point):
      for entityGripPoint in self.entityGripPoints:
         entityGripPoint.toggleSelectIntersectingGripPoints(point)


   def isIntersecting(self, point):
      # returns 2 values: QadEntityGripPoints, QadEntityGripPoint
      for entityGripPoints in self.entityGripPoints:
         res = entityGripPoints.isIntersecting(point)
         if res is not None:
            return entityGripPoints, res
      return None, None


   def getSelectedEntityGripPoints(self):
      # returns a list of entityGripPoints with selected grip points
      # the function does not make copies of entityGripPoints
      result = []
      for entityGripPoint in self.entityGripPoints:
         for gripPoint in entityGripPoint.gripPoints:
            if gripPoint.getStatus() == QadGripStatusEnum.SELECTED:
               result.append(entityGripPoint)

      return result


   def containsEntity(self, entity):
      for entityGripPoint in self.entityGripPoints:
         if entityGripPoint.entity == entity:
            return True
      return False


   def count(self):
      return len(self.entityGripPoints)

