# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 class to manage the map tool for the pedit command

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


from qgis.core import QgsPointXY, QgsWkbTypes, QgsGeometry


from .. import qad_utils
from ..qad_snapper import *
from ..qad_variables import QadVariables
from ..qad_getpoint import QadGetPoint, QadGetPointSelectionModeEnum, QadGetPointDrawModeEnum
from ..qad_polyline import QadPolyline
from ..qad_rubberband import QadRubberBand
from ..qad_highlight import QadHighlight
from ..qad_dim import QadDimStyles
from ..qad_msg import QadMsg


# ===============================================================================
# Qad_pedit_maptool_ModeEnum class.
# ===============================================================================
class Qad_pedit_maptool_ModeEnum():
   # requires the selection of an entity
   ASK_FOR_ENTITY_SEL = 1
   # nothing is required
   NONE = 2
   # the first point is required for approximation distance calculation
   ASK_FOR_FIRST_TOLERANCE_PT = 3
   # once the first point is known, the second point is required to calculate the approximation distance
   FIRST_TOLERANCE_PT_KNOWN_ASK_FOR_SECOND_PT = 4
   # requires a new vertex to be inserted
   ASK_FOR_NEW_VERTEX = 5
   # requires the new position of a vertex to be moved
   ASK_FOR_MOVE_VERTEX = 6
   # requires the position closest to a vertex
   ASK_FOR_VERTEX = 7
   # base point is required (grip mode)
   ASK_FOR_BASE_PT = 8


# ===============================================================================
# Qad_pedit_maptool class
# ===============================================================================
class Qad_pedit_maptool(QadGetPoint):

   def __init__(self, plugIn):
      QadGetPoint.__init__(self, plugIn)

      self.firstPt = None
      self.mode = None

      self.layer = None
      self.polyline = QadPolyline()
      self.tolerance2ApproxCurve = None
      self.vertexAt = 0
      self.vertexPt = None
      self.after = True
      self.basePt = None
      self.__highlight = QadHighlight(self.canvas)


   def hidePointMapToolMarkers(self):
      QadGetPoint.hidePointMapToolMarkers(self)
      self.__highlight.hide()

   def showPointMapToolMarkers(self):
      QadGetPoint.showPointMapToolMarkers(self)
      self.__highlight.show()

   def clear(self):
      QadGetPoint.clear(self)
      self.__highlight.reset()
      self.mode = None
      if self.basePt is not None:
         del(self.basePt)
         self.basePt = None

   def setPolyline(self, polyline, layer):
      self.polyline.set(polyline)
      self.layer = layer
      self.tolerance2ApproxCurve = QadVariables.get(QadMsg.translate("Environment variables", "TOLERANCE2APPROXCURVE"))


   def setVertexAt(self, vertexAt, after = None):
      if vertexAt == self.polyline.qty():
         self.firstPt = self.polyline.getLinearObjectAt(-1).getEndPt()
      else:
         self.firstPt = self.polyline.getLinearObjectAt(vertexAt).getStartPt()

      self.vertexPt = QgsPointXY(self.firstPt)
      self.vertexAt = vertexAt
      self.after = after


   def canvasMoveEvent(self, event):
      QadGetPoint.canvasMoveEvent(self, event)

      self.__highlight.reset()
      tmpPolyline = None

      # requires a new vertex to be inserted
      if self.mode == Qad_pedit_maptool_ModeEnum.ASK_FOR_NEW_VERTEX:
         if self.basePt is not None:
            offsetX = self.tmpPoint.x() - self.basePt.x()
            offsetY = self.tmpPoint.y() - self.basePt.y()
            newPt = QgsPointXY(self.vertexPt.x() + offsetX, self.vertexPt.y() + offsetY)
         else:
            newPt = QgsPointXY(self.tmpPoint)

         tmpPolyline = self.polyline.copy()

         if self.after: # after
            if self.vertexAt == tmpPolyline.qty() and tmpPolyline.isClosed():
               tmpPolyline.insertPoint(0, newPt)
            else:
               tmpPolyline.insertPoint(self.vertexAt, newPt)
         else: # before
            if self.vertexAt == 0 and tmpPolyline.isClosed():
               tmpPolyline.insertPoint(tmpPolyline.qty() - 1, newPt)
            else:
               tmpPolyline.insertPoint(self.vertexAt - 1, newPt)

      elif self.mode == Qad_pedit_maptool_ModeEnum.ASK_FOR_MOVE_VERTEX:
         newPt = QgsPointXY(self.tmpPoint)
         tmpPolyline = self.polyline.copy()
         tmpPolyline.movePoint(self.vertexAt, newPt)

      if tmpPolyline is not None:
         if self.layer is not None:
            geom = tmpPolyline.asGeom(self.layer.wkbType())
         else:
            geom = tmpPolyline.asGeom(QgsWkbTypes.CurvePolygon)

         # I transform the geometry into the layer crs
         self.__highlight.addGeometry(self.mapToLayerCoordinates(self.layer, geom), self.layer)

#          pts = tmpPolyline.asPolyline(self.tolerance2ApproxCurve)
#          if self.layer.geometryType() == QgsWkbTypes.PolygonGeometry:
#             geom = QgsGeometry.fromPolygonXY([pts])
#          else:
#             geom = QgsGeometry.fromPolylineXY(pts)
#
#          # I transform the geometry into the layer crs
#          self.__highlight.addGeometry(self.mapToLayerCoordinates(self.layer, geom), self.layer)


   def activate(self):
      QadGetPoint.activate(self)
      self.__highlight.show()

   def deactivate(self):
      try: # necessary because if you close QGIS this event starts even though the map tool object is no longer there!
         QadGetPoint.deactivate(self)
         self.__highlight.hide()
      except:
         pass

   def setMode(self, mode):
      self.mode = mode

      # requires the selection of an entity
      if self.mode == Qad_pedit_maptool_ModeEnum.ASK_FOR_ENTITY_SEL:
         self.setSelectionMode(QadGetPointSelectionModeEnum.ENTITY_SELECTION)

         # only editable linear or polygon layers that do not belong to dimensions
         layerList = []
         for layer in qad_utils.getVisibleVectorLayers(self.plugIn.canvas): # All vector layers visible
            if (layer.geometryType() == QgsWkbTypes.LineGeometry or layer.geometryType() == QgsWkbTypes.PolygonGeometry) and \
               layer.isEditable():
               if len(QadDimStyles.getDimListByLayer(layer)) == 0:
                  layerList.append(layer)

         self.layersToCheck = layerList
         self.setSnapType(QadSnapTypeEnum.DISABLE)
      # nothing is required
      elif self.mode == Qad_pedit_maptool_ModeEnum.NONE:
         self.setSelectionMode(QadGetPointSelectionModeEnum.POINT_SELECTION)
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
      # the first point is required for approximation distance calculation
      # requires the position closest to a vertex
      elif self.mode == Qad_pedit_maptool_ModeEnum.ASK_FOR_FIRST_TOLERANCE_PT:
         self.onlyEditableLayers = False
         self.checkPointLayer = True
         self.checkLineLayer = True
         self.checkPolygonLayer = True
         self.setSnapType()
         self.setSelectionMode(QadGetPointSelectionModeEnum.POINT_SELECTION)
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
      # once the first point is known, the second point is required to calculate the approximation distance
      elif self.mode == Qad_pedit_maptool_ModeEnum.FIRST_TOLERANCE_PT_KNOWN_ASK_FOR_SECOND_PT or \
           self.mode == Qad_pedit_maptool_ModeEnum.ASK_FOR_NEW_VERTEX or \
           self.mode == Qad_pedit_maptool_ModeEnum.ASK_FOR_MOVE_VERTEX:
         self.onlyEditableLayers = False
         self.checkPointLayer = True
         self.checkLineLayer = True
         self.checkPolygonLayer = True
         self.setSnapType()
         self.setSelectionMode(QadGetPointSelectionModeEnum.POINT_SELECTION)
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.firstPt)
      # requires the position closest to a vertex
      elif self.mode == Qad_pedit_maptool_ModeEnum.ASK_FOR_VERTEX:
         self.setSnapType(QadSnapTypeEnum.DISABLE)
         self.setSelectionMode(QadGetPointSelectionModeEnum.POINT_SELECTION)
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
         self.setStartPoint(None)
      # base point is required (grip mode)
      elif self.mode == Qad_pedit_maptool_ModeEnum.ASK_FOR_BASE_PT:
         self.setSnapType()
         self.setSelectionMode(QadGetPointSelectionModeEnum.POINT_SELECTION)
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)


# ===============================================================================
# Qad_gripLineToArcConvert_maptool_ModeEnum class.
# ===============================================================================
class Qad_gripLineToArcConvert_maptool_ModeEnum():
   # once the starting and ending points of the arc are known, the intermediate point is required
   START_END_PT_KNOWN_ASK_FOR_SECOND_PT = 1
   # nothing is required
   NONE = 2


# ===============================================================================
# Qad_gripLineToArcConvert_maptool class
# ===============================================================================
class Qad_gripLineToArcConvert_maptool(QadGetPoint):

   def __init__(self, plugIn):
      QadGetPoint.__init__(self, plugIn)

      self.firstPt = None
      self.mode = None

      self.layer = None
      self.polyline = QadPolyline()
      self.linearObject = None
      self.startPt = None
      self.endPt = None
      self.tolerance2ApproxCurve = None
      self.__highlight = QadHighlight(self.canvas)


   def hidePointMapToolMarkers(self):
      QadGetPoint.hidePointMapToolMarkers(self)
      self.__highlight.hide()

   def showPointMapToolMarkers(self):
      QadGetPoint.showPointMapToolMarkers(self)
      self.__highlight.show()

   def clear(self):
      QadGetPoint.clear(self)
      self.__highlight.reset()
      self.mode = None

   def setPolyline(self, polyline, layer, partAt):
      self.polyline.set(polyline)
      self.layer = layer
      self.tolerance2ApproxCurve = QadVariables.get(QadMsg.translate("Environment variables", "TOLERANCE2APPROXCURVE"))
      self.linearObject = self.polyline.getLinearObjectAt(partAt)
      self.firstPt = self.polyline.getMiddlePt()
      self.startPt = self.polyline.getStartPt()
      self.endPt = self.polyline.getEndPt()


   def canvasMoveEvent(self, event):
      QadGetPoint.canvasMoveEvent(self, event)

      self.__highlight.reset()
      ok = False

      # once the starting and ending points of the arc are known, the intermediate point is required
      if self.mode == Qad_gripLineToArcConvert_maptool_ModeEnum.START_END_PT_KNOWN_ASK_FOR_SECOND_PT:
         if self.linearObject is None:
            return
         arc = QadArc()
         if arc.fromStartSecondEndPts(self.startPt, self.tmpPoint, self.endPt) == False:
            return
         if qad_utils.ptNear(self.startPt, arc.getStartPt()):
            self.linearObject.setArc(arc, False) # non-reverse arc
         else:
            self.linearObject.setArc(arc, True) # reverse arc
         ok = True

      if ok:
         pts = self.polyline.asPolyline(self.tolerance2ApproxCurve)
         if self.layer.geometryType() == QgsWkbTypes.PolygonGeometry:
            geom = QgsGeometry.fromPolygonXY([pts])
         else:
            geom = QgsGeometry.fromPolylineXY(pts)
         # I transform the geometry into the layer crs
         self.__highlight.addGeometry(self.mapToLayerCoordinates(self.layer, geom), self.layer)


   def activate(self):
      QadGetPoint.activate(self)
      self.__highlight.show()

   def deactivate(self):
      try: # necessary because if you close QGIS this event starts even though the map tool object is no longer there!
         QadGetPoint.deactivate(self)
         self.__highlight.hide()
      except:
         pass

   def setMode(self, mode):
      self.mode = mode

      # once the starting and ending points of the arc are known, the intermediate point is required
      if self.mode == Qad_gripLineToArcConvert_maptool_ModeEnum.START_END_PT_KNOWN_ASK_FOR_SECOND_PT:
         self.setSelectionMode(QadGetPointSelectionModeEnum.POINT_SELECTION)
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.firstPt)
      # nothing is required
      elif self.mode == Qad_pedit_maptool_ModeEnum.NONE:
         self.setSelectionMode(QadGetPointSelectionModeEnum.POINT_SELECTION)
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
