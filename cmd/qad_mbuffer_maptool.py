# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 class to manage the map tool for the mbuffer command

                              -------------------
        begin                : 2013-09-19
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


from ..qad_msg import QadMsg
from .. import qad_utils
from ..qad_snapper import *
from ..qad_snappointsdisplaymanager import *
from ..qad_variables import QadVariables
from ..qad_getpoint import QadGetPoint, QadGetPointDrawModeEnum
from ..qad_rubberband import QadRubberBand
from ..qad_mbuffer_fun import buffer
from ..qad_multi_geom import fromQadGeomToQgsGeom


# ===============================================================================
# Qad_mbuffer_maptool_ModeEnum class.
# ===============================================================================
class Qad_mbuffer_maptool_ModeEnum():
   # if nothing is known, the first point is required
   NONE_KNOWN_ASK_FOR_FIRST_PT = 1
   # known the first point requires the width of the buffer
   FIRST_PT_ASK_FOR_BUFFER_WIDTH = 2

# ===============================================================================
# Qad_mbuffer_maptool class
# ===============================================================================
class Qad_mbuffer_maptool(QadGetPoint):

   def __init__(self, plugIn):
      QadGetPoint.__init__(self, plugIn)

      self.startPtForBufferWidth = None
      # see the minimum number of points for an arc or circle to be recognized
      # nei files qad_arc.py e qad_circle.py e qad_ellipse.py
      self.segments = 12
      self.entitySet = QadEntitySet()
      self.geomType = QgsWkbTypes.PolygonGeometry
      self.__rubberBand = QadRubberBand(self.canvas, True)

   def setRubberBandColor(self, rubberBandBorderColor, rubberBandFillColor):
      if rubberBandBorderColor is not None:
         self.__rubberBand.setBorderColor(rubberBandBorderColor)
      if rubberBandFillColor is not None:
         self.__rubberBand.setFillColor(rubberBandFillColor)

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

      # known the first point requires the width of the buffer
      if self.mode == Qad_mbuffer_maptool_ModeEnum.FIRST_PT_ASK_FOR_BUFFER_WIDTH:
         width = qad_utils.getDistance(self.startPtForBufferWidth, self.tmpPoint)
         tolerance = QadVariables.get(QadMsg.translate("Environment variables", "TOLERANCE2APPROXCURVE"))

         for layerEntitySet in self.entitySet.layerEntitySetList:
            entityIterator = QadLayerEntitySetIterator(layerEntitySet)
            for entity in entityIterator:
               bufferedQadGeom = buffer(entity.getQadGeom(), width)
               if bufferedQadGeom is not None:
                  # I transform the geometry into the layer crs
                  self.__rubberBand.addGeometry(fromQadGeomToQgsGeom(bufferedQadGeom, entity.layer), entity.layer)


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
      if self.mode == Qad_mbuffer_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_FIRST_PT:
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
      # known the first point requires the width of the buffer
      elif self.mode == Qad_mbuffer_maptool_ModeEnum.FIRST_PT_ASK_FOR_BUFFER_WIDTH:
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.startPtForBufferWidth)
