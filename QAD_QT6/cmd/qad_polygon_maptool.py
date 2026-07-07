# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 class to manage the map tool for the polygon command

                              -------------------
        begin                : 2014-11-17
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


from .. import qad_utils
from ..qad_polyline import QadPolyline
from ..qad_getpoint import QadGetPoint, QadGetPointDrawModeEnum
from ..qad_rubberband import QadRubberBand
from ..qad_msg import QadMsg


# ===============================================================================
# Qad_polygon_maptool_ModeEnum class.
# ===============================================================================
class Qad_polygon_maptool_ModeEnum():
   # the center is required
   ASK_FOR_CENTER_PT = 1
   # once the center is known, the radius is required
   CENTER_PT_KNOWN_ASK_FOR_RADIUS = 2
   # the first point of the edge is required
   ASK_FOR_FIRST_EDGE_PT = 3
   # the second point of the edge is required
   FIRST_EDGE_PT_KNOWN_ASK_FOR_SECOND_EDGE_PT = 4

# ===============================================================================
# Qad_polygon_maptool class
# ===============================================================================
class Qad_polygon_maptool(QadGetPoint):

   def __init__(self, plugIn):
      QadGetPoint.__init__(self, plugIn)
      self.mode = None

      self.sideNumber = None
      self.centerPt = None
      self.constructionModeByCenter = None
      self.firstEdgePt = None
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

      if self.mode is not None:
         # once the center is known, the radius is required
         if self.mode == Qad_polygon_maptool_ModeEnum.CENTER_PT_KNOWN_ASK_FOR_RADIUS:
            radius = qad_utils.getDistance(self.centerPt, self.tmpPoint)

            InscribedOption = True if self.constructionModeByCenter == QadMsg.translate("Command_POLYGON", "Inscribed in circle") else False
            result = self.polyline.getPolygonByNsidesCenterRadius(self.sideNumber, self.centerPt, radius, InscribedOption, self.tmpPoint)
         # the second point of the edge is required
         elif self.mode == Qad_polygon_maptool_ModeEnum.FIRST_EDGE_PT_KNOWN_ASK_FOR_SECOND_EDGE_PT:
            result = self.polyline.getPolygonByNsidesEdgePts(self.sideNumber, self.firstEdgePt, self.tmpPoint)

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
      # the center is required
      if self.mode == Qad_polygon_maptool_ModeEnum.ASK_FOR_CENTER_PT:
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
      # once the center is known, the radius is required
      if self.mode == Qad_polygon_maptool_ModeEnum.CENTER_PT_KNOWN_ASK_FOR_RADIUS:
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.centerPt)
      # the first point of the edge is required
      if self.mode == Qad_polygon_maptool_ModeEnum.ASK_FOR_FIRST_EDGE_PT:
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
      # the second point of the edge is required
      if self.mode == Qad_polygon_maptool_ModeEnum.FIRST_EDGE_PT_KNOWN_ASK_FOR_SECOND_EDGE_PT:
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.firstEdgePt)
