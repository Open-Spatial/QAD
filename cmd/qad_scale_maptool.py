# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin ok

 class to manage the map tool for the scale command

                              -------------------
        begin                : 2013-09-27
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
from ..qad_getpoint import QadGetPoint, QadGetPointDrawModeEnum
from ..qad_dim import QadDimStyles, QadDimEntity, appendDimEntityIfNotExisting
from ..qad_highlight import QadHighlight
from ..qad_entity import QadCacheEntitySetIterator, QadEntityTypeEnum
from ..qad_multi_geom import fromQadGeomToQgsGeom


# ===============================================================================
# Qad_scale_maptool_ModeEnum class.
# ===============================================================================
class Qad_scale_maptool_ModeEnum():
   # known nothing, the base point is required
   NONE_KNOWN_ASK_FOR_BASE_PT = 1
   # once the base point is known, the second point for the scale is required
   BASE_PT_KNOWN_ASK_FOR_SCALE_PT = 2
   # requires the first point for the reference length
   ASK_FOR_FIRST_PT_REFERENCE_LEN = 3
   # once the first point is known, the second point is required for the reference length
   FIRST_PT_KNOWN_ASK_FOR_SECOND_PT_REFERENCE_LEN = 4
   # Once the base point is known, the second point is required for the new length
   BASE_PT_KNOWN_ASK_FOR_NEW_LEN_PT = 5
   # the first point for the new length is required
   ASK_FOR_FIRST_NEW_LEN_PT = 6
   # Once the first point is known, the second point is required for the new length
   FIRST_PT_KNOWN_ASK_FOR_SECOND_NEW_LEN_PT = 7

# ===============================================================================
# Qad_scale_maptool class
# ===============================================================================
class Qad_scale_maptool(QadGetPoint):

   def __init__(self, plugIn):
      QadGetPoint.__init__(self, plugIn)

      self.basePt = None
      self.Pt1ReferenceLen = None
      self.ReferenceLen = 0
      self.Pt1NewLen = None
      self.cacheEntitySet = None
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


   # ============================================================================
   # scale
   # ============================================================================
   def scale(self, entity, basePt, scale):
      # check if the entity belongs to a dimensioning style
      if entity.whatIs() == "ENTITY":
         # scale the geometry of the entity
         qadGeom = entity.getQadGeom().copy() # I copy it
         qadGeom.scale(basePt, scale)
         self.__highlight.addGeometry(fromQadGeomToQgsGeom(qadGeom, entity.layer), entity.layer)
      elif entity.whatIs() == "DIMENTITY":
         newDimEntity = QadDimEntity(entity) # I copy it
         # scale the dimension
         newDimEntity.scale(basePt, scale)
         self.__highlight.addGeometry(newDimEntity.textualFeature.geometry(), newDimEntity.getTextualLayer())
         self.__highlight.addGeometries(newDimEntity.getLinearGeometryCollection(), newDimEntity.getLinearLayer())
         self.__highlight.addGeometries(newDimEntity.getSymbolGeometryCollection(), newDimEntity.getSymbolLayer())


   # ============================================================================
   # addScaledGeometries
   # ============================================================================
   def addScaledGeometries(self, scale):
      self.__highlight.reset()

      if scale <= 0: return

      dimElaboratedList = [] # list of dimensions already processed
      entityIterator = QadCacheEntitySetIterator(self.cacheEntitySet)
      for entity in entityIterator:
         qadGeom = entity.getQadGeom() # this is how I initialize the qad info
         # check if the entity belongs to a dimensioning style
         dimEntity = QadDimStyles.getDimEntity(entity)
         if dimEntity is not None:
            if appendDimEntityIfNotExisting(dimElaboratedList, dimEntity) == False: # dimension already processed
               continue
            entity = dimEntity

         self.scale(entity, self.basePt, scale)


   def canvasMoveEvent(self, event):
      QadGetPoint.canvasMoveEvent(self, event)

      # once the base point is known, the second point for the scale is required
      if self.mode == Qad_scale_maptool_ModeEnum.BASE_PT_KNOWN_ASK_FOR_SCALE_PT:
         scale = qad_utils.getDistance(self.basePt, self.tmpPoint)
         self.addScaledGeometries(scale)
      # once the first point is known, the second point is required for the reference length
      elif self.mode == Qad_scale_maptool_ModeEnum.BASE_PT_KNOWN_ASK_FOR_NEW_LEN_PT:
         len = qad_utils.getDistance(self.basePt, self.tmpPoint)
         scale = len / self.ReferenceLen
         self.addScaledGeometries(scale)
      # Once the first point is known, the second point is required for the new length
      elif self.mode == Qad_scale_maptool_ModeEnum.FIRST_PT_KNOWN_ASK_FOR_SECOND_NEW_LEN_PT:
         len = qad_utils.getDistance(self.Pt1NewLen, self.tmpPoint)
         scale = len / self.ReferenceLen
         self.addScaledGeometries(scale)


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
      # known nothing, the base point is required
      if self.mode == Qad_scale_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_BASE_PT:
         self.clear()
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
         self.__highlight.reset()
      # once the base point is known, the second point for the scale is required
      elif self.mode == Qad_scale_maptool_ModeEnum.BASE_PT_KNOWN_ASK_FOR_SCALE_PT:
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.basePt)
      # requires the first point for the reference length
      elif self.mode == Qad_scale_maptool_ModeEnum.ASK_FOR_FIRST_PT_REFERENCE_LEN:
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
         self.__highlight.reset()
      # once the first point is known, the second point is required for the reference length
      elif self.mode == Qad_scale_maptool_ModeEnum.FIRST_PT_KNOWN_ASK_FOR_SECOND_PT_REFERENCE_LEN:
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.Pt1ReferenceLen)
      # Once the base point is known, the second point is required for the new length
      elif self.mode == Qad_scale_maptool_ModeEnum.BASE_PT_KNOWN_ASK_FOR_NEW_LEN_PT:
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.basePt)
      # the first point for the new length is required
      elif self.mode == Qad_scale_maptool_ModeEnum.ASK_FOR_FIRST_NEW_LEN_PT:
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
         self.__highlight.reset()
      # Once the first point is known, the second point is required for the new length
      elif self.mode == Qad_scale_maptool_ModeEnum.FIRST_PT_KNOWN_ASK_FOR_SECOND_NEW_LEN_PT:
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.Pt1NewLen)
