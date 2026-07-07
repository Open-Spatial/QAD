# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 class to manage the map tool for the pline command

                              -------------------
        begin                : 2016-04-07
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


from qgis.PyQt.QtCore import QSettings


from .. import qad_utils
from ..qad_snapper import QadSnapTypeEnum
from ..qad_getpoint import QadGetPoint, QadGetPointSelectionModeEnum, QadGetPointDrawModeEnum
from ..qad_rubberband import QadRubberBand
from ..qad_multi_geom import getQadGeomAt
from ..qad_geom_relations import getQadGeomClosestPart, getQadGeomBetween2Pts

# ===============================================================================
# Qad_pline_maptool_ModeEnum class.
# ===============================================================================
class Qad_pline_maptool_ModeEnum():
   # nothing is required
   NONE = 0
   # the end point is required to trace an existing object
   ASK_FOR_TRACE_PT = 1
   # a line must be drawn
   DRAW_LINE = 2


# ===============================================================================
# Qad_pline_maptool class
# ===============================================================================
class Qad_pline_maptool(QadGetPoint):

   def __init__(self, plugIn, asToolForMPolygon = False):
      QadGetPoint.__init__(self, plugIn)

      self.firstPt = None
      self.mode = None

      self.asToolForMPolygon = asToolForMPolygon # if True means it is used to draw a polygon
      if self.asToolForMPolygon:
         self.__polygonRubberBand = QadRubberBand(self.plugIn.canvas, True)
         self.endVertex = None # points to the starting and ending vertex of the QadPLINECommandClass polygon

      self.__polylineTraceRubberBand = QadRubberBand(self.plugIn.canvas, True) # to use in trace of an existing object
      settings = QSettings()
      width = int(settings.value("/qgis/digitizing/line_width", 1))
      self.__polylineTraceRubberBand.setWidth(width * 2)

   def hidePointMapToolMarkers(self):
      QadGetPoint.hidePointMapToolMarkers(self)
      if self.asToolForMPolygon:
         self.__polygonRubberBand.hide()
      self.__polylineTraceRubberBand.hide()

   def showPointMapToolMarkers(self):
      QadGetPoint.showPointMapToolMarkers(self)
      if self.asToolForMPolygon:
         self.__polygonRubberBand.show()
      self.__polylineTraceRubberBand.show()

   def clear(self):
      QadGetPoint.clear(self)
      if self.asToolForMPolygon:
         self.__polygonRubberBand.reset()
      self.__polylineTraceRubberBand.reset()
      self.mode = None

   def canvasMoveEvent(self, event):
      QadGetPoint.canvasMoveEvent(self, event)

      if self.asToolForMPolygon == True: # if True means it is used to draw a polygon
         self.__polygonRubberBand.reset()
      self.__polylineTraceRubberBand.reset()

      startPoint = self.getStartPoint()
      if startPoint is None: return

      points = None

      # the end point is required to trace an existing object
      if self.mode == Qad_pline_maptool_ModeEnum.ASK_FOR_TRACE_PT:
         if self.tmpEntity.isInitialized():
            qadGeom = self.tmpEntity.getQadGeom()
            dummy = getQadGeomClosestPart(qadGeom, self.tmpPoint)
            qadGeom = getQadGeomAt(qadGeom, dummy[2], dummy[3])
            subGeom = getQadGeomBetween2Pts(qadGeom, startPoint, dummy[1])
            if subGeom is not None:
               points = subGeom.asPolyline()
      else:
         points = [startPoint, self.tmpPoint]

      if self.mode == Qad_pline_maptool_ModeEnum.ASK_FOR_TRACE_PT:
         if (points is not None): self.__polylineTraceRubberBand.setLine(points)

      # polygon case
      if self.asToolForMPolygon:
         if (points is not None) and (self.endVertex is not None) and (startPoint != self.endVertex):
            points.insert(0, self.endVertex)
            self.__polygonRubberBand.setPolygon(points)

      del startPoint


   def activate(self):
      QadGetPoint.activate(self)
      if self.asToolForMPolygon:
         self.__polygonRubberBand.show()
      self.__polylineTraceRubberBand.show()

   def deactivate(self):
      try: # necessary because if you close QGIS this event starts even though the map tool object is no longer there!
         QadGetPoint.deactivate(self)
         if self.asToolForMPolygon:
            self.__polygonRubberBand.hide()
         self.__polylineTraceRubberBand.hide()
      except:
         pass

   def setMode(self, mode):
      self.mode = mode

      # the end point is required to trace an existing object
      if self.mode == Qad_pline_maptool_ModeEnum.ASK_FOR_TRACE_PT:
         self.checkPointLayer = False # I discard the selection of points
         self.checkLineLayer = True
         self.checkPolygonLayer = True
         self.onlyEditableLayers = False
         self.forceSnapTypeOnce(QadSnapTypeEnum.END)

         self.setSelectionMode(QadGetPointSelectionModeEnum.ENTITY_SELECTION_DYNAMIC)
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
      # nothing is required
      elif self.mode == Qad_pline_maptool_ModeEnum.NONE:
         self.setSelectionMode(QadGetPointSelectionModeEnum.NONE)
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
      # a line must be drawn
      elif self.mode == Qad_pline_maptool_ModeEnum.DRAW_LINE:
         self.setSelectionMode(QadGetPointSelectionModeEnum.POINT_SELECTION)
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE) # set the elastic line
