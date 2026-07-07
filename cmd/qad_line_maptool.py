# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 class to manage the point request map tool for the line command

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


from .. import qad_utils
from ..qad_snapper import QadSnapper, QadSnapTypeEnum
from ..qad_getpoint import QadGetPoint, QadGetPointDrawModeEnum
from ..qad_rubberband import QadRubberBand


# ===============================================================================
# Qad_line_maptool_ModeEnum class.
# ===============================================================================
class Qad_line_maptool_ModeEnum():
   # if nothing is known, the first point is required
   NONE_KNOWN_ASK_FOR_FIRST_PT = 1
   # Once the first point is known, the second point is required
   FIRST_PT_KNOWN_ASK_FOR_SECOND_PT = 2
   # once the size of the first point of tangency is known, the second point is required
   FIRST_TAN_KNOWN_ASK_FOR_SECOND_PT = 3
   # once the size of the first point of perpendicularity is known, the second point is required
   FIRST_PER_KNOWN_ASK_FOR_SECOND_PT = 4


# ===============================================================================
# Qad_line_maptool class
# ===============================================================================
class Qad_line_maptool(QadGetPoint):

   def __init__(self, plugIn):
      QadGetPoint.__init__(self, plugIn)

      self.mode = None
      self.firstPt = None
      self.tan1 = None
      self.per1 = None
      self.entity1 = None
      self.__rubberBand = QadRubberBand(self.canvas)

   def __del__(self):
      QadGetPoint.__del__(self)

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

      line = None

      # Once the first point is known, the second point is required
      if self.mode == Qad_line_maptool_ModeEnum.FIRST_PT_KNOWN_ASK_FOR_SECOND_PT:
         if (self.firstPt is not None):
            line = [self.firstPt, self.tmpPoint]
      # once the size of the first point of tangency is known, the second point is required
      elif self.mode == Qad_line_maptool_ModeEnum.FIRST_TAN_KNOWN_ASK_FOR_SECOND_PT:
         snapper = QadSnapper()
         snapper.setSnapLayers(qad_utils.getSnappableVectorLayers(self.canvas))
         snapper.setSnapType(QadSnapTypeEnum.TAN)
         snapper.setStartPoint(self.tmpPoint)
         oSnapPoints = snapper.getSnapPoint(self.entity1, self.tan1)
         # I store the snap point in point (I take the first valid one)
         for item in oSnapPoints.items():
            points = item[1]
            if points is not None:
               line = [points[0], self.tmpPoint]
               break
      # once the size of the first point of perpendicularity is known, the second point is required
      elif self.mode == Qad_line_maptool_ModeEnum.FIRST_PER_KNOWN_ASK_FOR_SECOND_PT:
         snapper = QadSnapper()
         snapper.setSnapLayers(qad_utils.getSnappableVectorLayers(self.canvas))
         snapper.setSnapType(QadSnapTypeEnum.PER)
         snapper.setStartPoint(self.tmpPoint)
         oSnapPoints = snapper.getSnapPoint(self.entity1, self.per1)
         # I store the snap point in point (I take the first valid one)
         for item in oSnapPoints.items():
            points = item[1]
            if points is not None:
               line = [points[0], self.tmpPoint]
               break

      if line is not None:
         self.__rubberBand.setLine(line)


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
      # if nothing is known, the first point is required
      if self.mode == Qad_line_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_FIRST_PT:
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
         self.setStartPoint(None)
      # Once the first point is known, the second point is required
      elif self.mode == Qad_line_maptool_ModeEnum.FIRST_PT_KNOWN_ASK_FOR_SECOND_PT:
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.firstPt)
      # once the size of the first point of tangency is known, the second point is required
      elif self.mode == Qad_line_maptool_ModeEnum.FIRST_TAN_KNOWN_ASK_FOR_SECOND_PT:
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
      # once the size of the first point of perpendicularity is known, the second point is required
      elif self.mode == Qad_line_maptool_ModeEnum.FIRST_PER_KNOWN_ASK_FOR_SECOND_PT:
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
