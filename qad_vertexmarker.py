# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 class to manage marker symbols

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


from .qad_msg import QadMsg
from .qad_variables import QadVariables


# ===============================================================================
# QadVertexmarkerIconTypeEnum class.
# ===============================================================================
class QadVertexmarkerIconTypeEnum():
   NONE             = 0  # none
   CROSS            = 1  # cross
   X                = 2  # an X
   BOX              = 3  # a square
   TRIANGLE         = 4  # equilateral triangle pointing up
   CIRCLE           = 5  # circle
   CIRCLE_X         = 6  # circle with an x in the center
   RHOMBUS          = 7  # rhombus
   INFINITY_LINE    = 8  # infinite line (------ . .)
   DOUBLE_BOX       = 9  # two offset squares
   PERP             = 10 # "perpendicular" symbol
   TANGENT          = 11 # a circle with a tangent line on it
   DOUBLE_TRIANGLE  = 12 # two triangles one on top of the other with vertex in the center (hourglass)
   BOX_X            = 13 # square with an x in the center
   PARALLEL         = 14 # two parallel lines at 45 degrees
   PROGRESS         = 15 # line with X and dots (----X-- . .)
   X_INFINITY_LINE  = 16 # X and dots (X-- . .)
   PERP_DEFERRED    = 17 # like perpendicular with dots
   TANGENT_DEFERRED = 18 # like tangent with dots


class QadVertexMarker(QgsMapCanvasItem):
   """Class that manages vertex markers"""


   # ============================================================================
   # __init__
   # ============================================================================
   def __init__(self, mapCanvas):
      QgsMapCanvasItem.__init__(self, mapCanvas)
      self.__canvas = mapCanvas
      self.__iconType = QadVertexmarkerIconTypeEnum.X # icon to be shown
      self.__iconSize = QadVariables.get(QadMsg.translate("Environment variables", "AUTOSNAPSIZE"))
      self.__center = QgsPointXY(0, 0) #  coordinates of the point in the center
      self.__color = QColor(255, 0, 0) # color of the marker
      self.__penWidth = 2 # pen width


   def __del__(self):
      self.removeItem()


   def removeItem(self):
      self.__canvas.scene().removeItem(self)


   def setCenter(self, point):
      self.__center = point
      pt = self.toCanvasCoordinates(self.__center)
      self.setPos(pt)


   def setIconType(self, iconType):
      self.__iconType = iconType


   def setIconSize(self, iconSize):
      self.__iconSize = iconSize


   def setColor(self, color):
      self.__color = color


   def setPenWidth(self, width):
      self.__penWidth = width


   def paint(self, painter, option, widget):
      """p is a QPainter"""

      s = self.__iconSize

      pen = QPen(self.__color)
      pen.setWidth(self.__penWidth)
      painter.setPen(pen)

      if self.__iconType == QadVertexmarkerIconTypeEnum.NONE:
         pass
      elif self.__iconType == QadVertexmarkerIconTypeEnum.CROSS:
      # cross
         painter.drawLine(QLineF(-s,  0,  s,  0))
         painter.drawLine(QLineF( 0, -s,  0,  s))
      elif self.__iconType == QadVertexmarkerIconTypeEnum.X:
         # an X
         painter.drawLine(QLineF(-s, -s,  s,  s))
         painter.drawLine(QLineF(-s,  s,  s, -s))
      elif self.__iconType == QadVertexmarkerIconTypeEnum.BOX:
         # a square
         painter.drawLine(QLineF(-s, -s,  s, -s))
         painter.drawLine(QLineF( s, -s,  s,  s))
         painter.drawLine(QLineF( s,  s, -s,  s))
         painter.drawLine(QLineF(-s,  s, -s, -s))
      elif self.__iconType == QadVertexmarkerIconTypeEnum.TRIANGLE:
      # equilateral triangle pointing up
         painter.drawLine(QLineF(-s,  s,  s,  s))
         painter.drawLine(QLineF( s,  s,  0, -s))
         painter.drawLine(QLineF( 0, -s, -s,  s))
      elif self.__iconType == QadVertexmarkerIconTypeEnum.CIRCLE:
         # circle
         # the line is thinner
         pen.setWidth(int(self.__penWidth / 2))
         painter.setPen(pen)
         painter.drawEllipse(QPointF(0, 0), s, s)
         pen.setWidth(self.__penWidth)
         painter.setPen(pen)
      elif self.__iconType == QadVertexmarkerIconTypeEnum.CIRCLE_X:
         # circle with an x in the center
         # the line is thinner
         pen.setWidth(int(self.__penWidth / 2))
         painter.setPen(pen)
         painter.drawEllipse(QPointF(0, 0), s, s)
         painter.drawLine(QLineF(-s, -s,  s,  s))
         painter.drawLine(QLineF(-s,  s,  s, -s))
         pen.setWidth(self.__penWidth)
         painter.setPen(pen)
      elif self.__iconType == QadVertexmarkerIconTypeEnum.RHOMBUS:
      # rhombus
         painter.drawLine(QLineF( 0, -s, -s,  0))
         painter.drawLine(QLineF(-s,  0,  0,  s))
         painter.drawLine(QLineF( 0,  s,  s,  0))
         painter.drawLine(QLineF( s,  0,  0, -s))
      elif self.__iconType == QadVertexmarkerIconTypeEnum.INFINITY_LINE:
         # infinite line (------ . .)
         l = self.__penWidth
         painter.drawLine(QLineF(-s,  0,  0,  0))
         painter.drawLine(QLineF(2 * l,  0,  2 * l,  0))
         painter.drawLine(QLineF(4 * l,  0,  4 * l,  0))
      elif self.__iconType == QadVertexmarkerIconTypeEnum.DOUBLE_BOX:
      # two offset squares
         l = (s / 4)
         painter.drawLine(QLineF(-s, -s, -s,  l))
         painter.drawLine(QLineF(-s,  l, -l,  l))
         painter.drawLine(QLineF(-l,  l, -l,  s))
         painter.drawLine(QLineF(-l,  s,  s,  s))
         painter.drawLine(QLineF( s,  s,  s, -l))
         painter.drawLine(QLineF( s, -l,  l, -l))
         painter.drawLine(QLineF( l, -l,  l, -s))
         painter.drawLine(QLineF( l, -s, -s, -s))
      elif self.__iconType == QadVertexmarkerIconTypeEnum.PERP:
         # "perpendicular" symbol
         painter.drawLine(QLineF(-s, -s, -s,  s))
         painter.drawLine(QLineF(-s,  s,  s,  s))
         painter.drawLine(QLineF(-s,  0,  0,  0))
         painter.drawLine(QLineF( 0,  0,  0,  s))
      elif self.__iconType == QadVertexmarkerIconTypeEnum.TANGENT:
         # a circle with a tangent line on it
         # the line is thinner
         l = s - self.__penWidth
         pen.setWidth(int(self.__penWidth / 2))
         painter.setPen(pen)
         painter.drawEllipse(QPointF(0, 0), l + 1, l + 1)
         pen.setWidth(self.__penWidth)
         painter.setPen(pen)
         painter.drawLine(QLineF(-s, -s,  s, -s))
      elif self.__iconType == QadVertexmarkerIconTypeEnum.DOUBLE_TRIANGLE:
         # two triangles one on top of the other with vertex in the center (hourglass)
         # the oblique lines are thinner
         pen.setWidth(int(self.__penWidth / 2))
         painter.setPen(pen)
         painter.drawLine(QLineF(-s, -s,  s,  s))
         painter.drawLine(QLineF( s, -s, -s,  s))
         pen.setWidth(self.__penWidth)
         painter.setPen(pen)
         painter.drawLine(QLineF(-s, -s,  s, -s))
         painter.drawLine(QLineF(-s,  s,  s,  s))
      elif self.__iconType == QadVertexmarkerIconTypeEnum.BOX_X:
         # square with an x in the center
         painter.drawLine(QLineF(-s, -s,  s, -s))
         painter.drawLine(QLineF( s, -s,  s,  s))
         painter.drawLine(QLineF( s,  s, -s,  s))
         painter.drawLine(QLineF(-s,  s, -s, -s))
         # the oblique lines of the x are thinner
         pen.setWidth(int(self.__penWidth / 2))
         painter.setPen(pen)
         painter.drawLine(QLineF(-s, -s,  s,  s))
         painter.drawLine(QLineF(-s,  s,  s, -s))
         pen.setWidth(self.__penWidth)
         painter.setPen(pen)
      elif self.__iconType == QadVertexmarkerIconTypeEnum.PARALLEL:
         # two parallel lines at 45 degrees
         painter.drawLine(QLineF(-s,  0,  0, -s))
         painter.drawLine(QLineF( 0,  s,  s,  0))
      elif self.__iconType == QadVertexmarkerIconTypeEnum.PROGRESS:
         # line with X and dots (----X-- . .)
         l = self.__penWidth
         painter.drawLine(QLineF(-s,  0,  0,  0))
         painter.drawLine(QLineF(2 * l,  0,  2 * l,  0))
         painter.drawLine(QLineF(4 * l,  0,  4 * l,  0))
         # the oblique lines of the x are thinner
         pen.setWidth(int(self.__penWidth / 2))
         l = s / 2
         painter.setPen(pen)
         painter.drawLine(QLineF(-l, -l,  l,  l))
         painter.drawLine(QLineF(-l,  l,  l, -l))
         pen.setWidth(self.__penWidth)
         painter.setPen(pen)
      elif self.__iconType == QadVertexmarkerIconTypeEnum.X_INFINITY_LINE:
         # line with X and dots (X-- . .)
         l = self.__penWidth
         painter.drawLine(QLineF(2 * l,  0,  2 * l,  0))
         painter.drawLine(QLineF(4 * l,  0,  4 * l,  0))
         # the oblique lines of the x are thinner
         pen.setWidth(int(self.__penWidth / 2))
         l = s / 2
         painter.setPen(pen)
         painter.drawLine(QLineF(-l, -l,  l,  l))
         painter.drawLine(QLineF(-l,  l,  l, -l))
         pen.setWidth(self.__penWidth)
         painter.setPen(pen)
      elif self.__iconType == QadVertexmarkerIconTypeEnum.PERP_DEFERRED:
         painter.drawLine(QLineF(-s, -s, -s,  s))
         painter.drawLine(QLineF(-s,  s,  s,  s))
         painter.drawLine(QLineF(-s,  0,  0,  0))
         painter.drawLine(QLineF( 0,  0,  0,  s))
         # "perpendicular" symbol with dots
         l = s - self.__penWidth
         l = l + (self.__penWidth * 2)
         painter.drawLine(QLineF(l,  0,  l,  0))
         l = l + (self.__penWidth * 2)
         painter.drawLine(QLineF(l,  0,  l,  0))
      elif self.__iconType == QadVertexmarkerIconTypeEnum.TANGENT_DEFERRED:
         # a circle with a tangent line on it
         # the line is thinner
         l = s - self.__penWidth
         pen.setWidth(int(self.__penWidth / 2))
         painter.setPen(pen)
         painter.drawEllipse(QPointF(0, 0), l + 1, l + 1)
         pen.setWidth(self.__penWidth)
         painter.setPen(pen)
         painter.drawLine(QLineF(-s, -s,  s, -s))
      # like tangent with dots
         l = l + (self.__penWidth * 2)
         painter.drawLine(QLineF(l,  0,  l,  0))
         l = l + (self.__penWidth * 2)
         painter.drawLine(QLineF(l,  0,  l,  0))


   def boundingRect(self):
      a = self.__iconSize / 2.0 + 1
      width = 2 * a + self.__penWidth * 2
      height = 2 * a
      return QRectF(-a, -a, width, height)


   def updatePosition(self):
      self.setCenter(self.__center)
