# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 class to manage the map tool for the rectangle command

                              -------------------
        begin                : 2013-12-3
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


from qgis.core import QgsWkbTypes


from ..qad_polyline import QadPolyline
from ..qad_getpoint import QadGetPoint, QadGetPointDrawModeEnum
from ..qad_rubberband import QadRubberBand


# ===============================================================================
# Qad_rectangle_maptool_ModeEnum class.
# ===============================================================================
class Qad_rectangle_maptool_ModeEnum():
   # I know nothing, the first corner is requested
   NONE_KNOWN_ASK_FOR_FIRST_CORNER = 1
   # Once the first angle is known, the opposite angle is required
   FIRST_CORNER_KNOWN_ASK_FOR_SECOND_CORNER = 2
   # once the first angle is known, rotation is required
   FIRST_CORNER_KNOWN_ASK_FOR_ROTATION = 3

# ===============================================================================
# Qad_rotate_maptool class
# ===============================================================================
class Qad_rectangle_maptool(QadGetPoint):

   def __init__(self, plugIn):
      QadGetPoint.__init__(self, plugIn)

      self.firstCorner = None
      self.secondCorner = None
      self.basePt = None
      self.gapType = 0 # 0 = Angoli retti; 1 = Raccorda i segmenti; 2 = Cima i segmenti
      self.gapValue1 = 0 # if gapType = 1 -> radius of curvature; if gapType = 2 -> first trimming distance
      self.gapValue2 = 0 # if gapType = 2 -> second trimming distance
      self.rot = 0
      self.polyline = QadPolyline()

      self.__rubberBand = QadRubberBand(self.canvas, True)
      self.geomType = QgsWkbTypes.PolygonGeometry

   def hidePointMapToolMarkers(self):
      QadGetPoint.hidePointMapToolMarkers(self)
      self.__rubberBand.hide()

   def showPointMapToolMarkers(self):
      QadGetPoint.showPointMapToolMarkers(self)
      self.__rubberBand.show()

   def clear(self):
      QadGetPoint.clear(self)
      self.__rubberBand.reset()
      self.mode = None

   def canvasMoveEvent(self, event):
      QadGetPoint.canvasMoveEvent(self, event)

      self.__rubberBand.reset()

      result = False

      # Once the first angle is known, the opposite angle is required
      if self.mode == Qad_rectangle_maptool_ModeEnum.FIRST_CORNER_KNOWN_ASK_FOR_SECOND_CORNER:
         result = self.polyline.getRectByCorners(self.firstCorner, self.tmpPoint, self.rot, \
                                                 self.gapType, self.gapValue1, self.gapValue2)

      if result == True:
         vertices = self.polyline.asPolyline()
         if self.geomType == QgsWkbTypes.PolygonGeometry:
            self.__rubberBand.setPolygon(vertices)
         else:
            self.__rubberBand.setLine(vertices)

   def activate(self):
      QadGetPoint.activate(self)
      self.__rubberBand.show()

   def deactivate(self):
      try: # necessary because if you close QGIS this event starts even though the map tool object is no longer there!
         QadGetPoint.deactivate(self)
         self.__rubberBand.hide()
      except:
         pass

   def setMode(self, mode):
      self.mode = mode
      # I know nothing, the first corner is requested
      if self.mode == Qad_rectangle_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_FIRST_CORNER:
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
      # Once the first angle is known, the opposite angle is required
      elif self.mode == Qad_rectangle_maptool_ModeEnum.FIRST_CORNER_KNOWN_ASK_FOR_SECOND_CORNER:
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
      # once the first angle is known, rotation is required
      elif self.mode == Qad_rectangle_maptool_ModeEnum.FIRST_CORNER_KNOWN_ASK_FOR_ROTATION:
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.firstCorner)

