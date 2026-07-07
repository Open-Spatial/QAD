# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 class to manage the map tool for the offset command

                              -------------------
        begin                : 2013-10-04
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


from qgis.core import QgsWkbTypes, QgsGeometry


from .. import qad_utils
from ..qad_getpoint import QadGetPoint, QadGetPointDrawModeEnum, QadGetPointSelectionModeEnum
from ..qad_highlight import QadHighlight
from ..qad_dim import QadDimStyles
from ..qad_msg import QadMsg
from ..qad_offset_fun import offsetPolyline, offsetQGSGeom
from ..qad_geom_relations import getQadGeomClosestPart
from ..qad_multi_geom import fromQgsGeomToQadGeom


# ===============================================================================
# Qad_offset_maptool_ModeEnum class.
# ===============================================================================
class Qad_offset_maptool_ModeEnum():
   # requires the first point for offset calculation
   ASK_FOR_FIRST_OFFSET_PT = 1
   # once the first point is known, the second point is required for offset calculation
   FIRST_OFFSET_PT_KNOWN_ASK_FOR_SECOND_PT = 2
   # note the offset distance, the point is required to establish which side
   OFFSET_KNOWN_ASK_FOR_SIDE_PT = 3
   # the passing point is required to establish which side and at which offset
   ASK_FOR_PASSAGE_PT = 4
   # requires the selection of an object
   ASK_FOR_ENTITY_SELECTION = 5

# ===============================================================================
# Qad_offset_maptool class
# ===============================================================================
class Qad_offset_maptool(QadGetPoint):

   def __init__(self, plugIn):
      QadGetPoint.__init__(self, plugIn)

      self.firstPt = None
      self.layer = None
      self.subGeom = None
      self.subGeomAsPolyline = None # geometry in the form of a list of points
      self.offset = 0
      self.lastOffSetOnLeftSide = 0
      self.lastOffSetOnRightSide = 0
      self.gapType = 0
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


   def addOffSetGeometries(self, newPt):
      self.__highlight.reset()

      # the function returns a list with
      # (<minimum distance>
      # <nearest point>
      # <nearest geometry index>
      # <index of the nearest sub-geometry>
      # <index of the closest sub-geometry part>
      # <"to the left of" if the point is to the left of the part with the following values:
      # - < 0 = left (for line, arc or ellipse arc) or inside (for circles, ellipses)
      # - > 0 = right (for line, arc or ellipse arc) or outside (for circles, ellipses)
#       result = getQadGeomClosestPart(self.subGeom, newPt)
#       leftOf = result[5]
#
#       if self.offset < 0:
#          offsetDistance = result[0] # minimum distance
#       else:
#          offsetDistance = self.offset
#
#          if leftOf < 0: # left (for line, arc or ellipse arc) or inside (for circles, ellipses)
#             offsetDistance = offsetDistance + self.lastOffSetOnLeftSide
#          else: # to the right
#             offsetDistance = offsetDistance + self.lastOffSetOnRightSide

      forcedOffsetDist = None
      if self.offset > 0: # if a distance has already been set I just need to check the direction of the offset
         # the function returns a list with
         # (<minimum distance>
         # <nearest point>
         # <nearest geometry index>
         # <index of the nearest sub-geometry>
         # <index of the closest sub-geometry part>
         # <"to the left of" if the point is to the left of the part with the following values:
         # - < 0 = left (for line, arc or ellipse arc) or inside (for circles, ellipses)
         # - > 0 = right (for line, arc or ellipse arc) or outside (for circles, ellipses)
         dummy = getQadGeomClosestPart(self.subGeom, newPt)
         leftOf = dummy[5]

         if leftOf < 0: # left (for line, arc or ellipse arc) or inside (for circles, ellipses)
            forcedOffsetDist = self.offset + self.lastOffSetOnLeftSide
         else: # to the right
            forcedOffsetDist = self.offset + self.lastOffSetOnRightSide


      # if self.subGeom implements the isClosed method
      closed = self.subGeom.isClosed() if hasattr(self.subGeom, "isClosed") and callable(getattr(self.subGeom, "isClosed")) else False

      if self.layer.geometryType() == QgsWkbTypes.PolygonGeometry or closed == True:
         qgsGeom = QgsGeometry.fromPolygonXY([self.subGeom.asPolyline()])
      else:
         qgsGeom = QgsGeometry.fromPolylineXY(self.subGeom.asPolyline())

      offsetQGSGeomList = offsetQGSGeom(qgsGeom, \
                                        newPt, \
                                        self.gapType, \
                                        forcedOffsetDist)

      for g in offsetQGSGeomList:
         # I convert to QAD geometry to recognize curves
         g = fromQgsGeomToQadGeom(g).asGeom(self.layer.wkbType())
         self.__highlight.addGeometry(self.mapToLayerCoordinates(self.layer, g), self.layer)

#       lines = offsetPolyline(self.subGeom, \
#                              offsetDistance, \
#                              "left" if leftOf < 0 else "right", \
#                              self.gapType)
#
#       for line in lines:
#          pts = line.asPolyline()
#          if self.layer.geometryType() == QgsWkbTypes.PolygonGeometry:
#             if line[0] == line[-1]: # if it is a closed line
#                offsetGeom = QgsGeometry.fromPolygonXY([pts])
#             else:
#                offsetGeom = QgsGeometry.fromPolylineXY(pts)
#          else:
#             offsetGeom = QgsGeometry.fromPolylineXY(pts)

#          self.__highlight.addGeometry(self.mapToLayerCoordinates(self.layer, offsetGeom), self.layer)


   def canvasMoveEvent(self, event):
      QadGetPoint.canvasMoveEvent(self, event)

      # note the offset distance, the point is required to establish which side
      if self.mode == Qad_offset_maptool_ModeEnum.OFFSET_KNOWN_ASK_FOR_SIDE_PT:
         self.addOffSetGeometries(self.tmpPoint)
      # the passing point is required to establish which side and at which offset
      elif self.mode == Qad_offset_maptool_ModeEnum.ASK_FOR_PASSAGE_PT:
         self.addOffSetGeometries(self.tmpPoint)


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
      self.clear()
      self.mode = mode
      # requires the first point for offset calculation
      if self.mode == Qad_offset_maptool_ModeEnum.ASK_FOR_FIRST_OFFSET_PT:
         self.setSelectionMode(QadGetPointSelectionModeEnum.POINT_SELECTION)
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
         self.onlyEditableLayers = False
      # once the first point is known, the second point is required for offset calculation
      if self.mode == Qad_offset_maptool_ModeEnum.FIRST_OFFSET_PT_KNOWN_ASK_FOR_SECOND_PT:
         self.setSelectionMode(QadGetPointSelectionModeEnum.POINT_SELECTION)
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.firstPt)
         self.onlyEditableLayers = False
      # note the offset distance, the point is required to establish which side
      elif self.mode == Qad_offset_maptool_ModeEnum.OFFSET_KNOWN_ASK_FOR_SIDE_PT:
         self.setSelectionMode(QadGetPointSelectionModeEnum.POINT_SELECTION)
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
         self.onlyEditableLayers = False
      # the passing point is required to establish which side and at which offset
      elif self.mode == Qad_offset_maptool_ModeEnum.ASK_FOR_PASSAGE_PT:
         self.setSelectionMode(QadGetPointSelectionModeEnum.POINT_SELECTION)
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
         self.onlyEditableLayers = False
      # requires the selection of an object
      elif self.mode == Qad_offset_maptool_ModeEnum.ASK_FOR_ENTITY_SELECTION:
         self.setSelectionMode(QadGetPointSelectionModeEnum.ENTITY_SELECTION)
         # only editable linear or polygon layers that do not belong to dimensions
         layerList = []
         for layer in qad_utils.getVisibleVectorLayers(self.plugIn.canvas): # All vector layers visible
            if (layer.geometryType() == QgsWkbTypes.LineGeometry or layer.geometryType() == QgsWkbTypes.PolygonGeometry) and \
               layer.isEditable():
               if len(QadDimStyles.getDimListByLayer(layer)) == 0:
                  layerList.append(layer)

         self.layersToCheck = layerList
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
         self.onlyEditableLayers = True
