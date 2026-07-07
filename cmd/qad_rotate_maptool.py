# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin ok

 class to manage the map tool for the rotate command

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
from ..qad_getpoint import QadGetPoint, QadGetPointDrawModeEnum, QadGetPointSelectionModeEnum
from ..qad_dim import QadDimStyles, appendDimEntityIfNotExisting, QadDimEntity
from ..qad_highlight import QadHighlight
from ..qad_entity import QadCacheEntitySetIterator, QadEntityTypeEnum
from ..qad_multi_geom import fromQadGeomToQgsGeom


# ===============================================================================
# Qad_rotate_maptool_ModeEnum class.
# ===============================================================================
class Qad_rotate_maptool_ModeEnum():
   # known nothing, the base point is required
   NONE_KNOWN_ASK_FOR_BASE_PT = 1
   # once the base point is known, the second point for the rotation angle is required
   BASE_PT_KNOWN_ASK_FOR_ROTATION_PT = 2
   # requires the first point for the reference angle
   ASK_FOR_FIRST_PT_REFERENCE_ANG = 3
   # once the first point is known, the second point is required for the reference angle
   FIRST_PT_KNOWN_ASK_FOR_SECOND_PT_REFERENCE_ANG = 4
   # once the base point is known, the second point for the new angle is required
   BASE_PT_KNOWN_ASK_FOR_NEW_ROTATION_PT = 5
   # requires the first point for the new angle
   ASK_FOR_FIRST_NEW_ROTATION_PT = 6
   # once the first point is known, the second point is required for the new angle
   FIRST_PT_KNOWN_ASK_FOR_SECOND_NEW_ROTATION_PT = 7

# ===============================================================================
# Qad_rotate_maptool class
# ===============================================================================
class Qad_rotate_maptool(QadGetPoint):

   def __init__(self, plugIn):
      QadGetPoint.__init__(self, plugIn)

      self.basePt = None
      self.Pt1ReferenceAng = None
      self.ReferenceAng = 0
      self.Pt1NewAng = None
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
   # rotate
   # ============================================================================
   def rotate(self, entity, basePt, angle):
      # check if the entity belongs to a dimensioning style
      if entity.whatIs() == "ENTITY":
         # rotate the geometry of the entity
         qadGeom = entity.getQadGeom().copy() # I copy it
         qadGeom.rotate(basePt, angle)
         self.__highlight.addGeometry(fromQadGeomToQgsGeom(qadGeom, entity.layer), entity.layer)
      elif entity.whatIs() == "DIMENTITY":
         newDimEntity = QadDimEntity(entity) # I copy it
         # rotate the dimension
         newDimEntity.rotate(basePt, angle)
         self.__highlight.addGeometry(newDimEntity.textualFeature.geometry(), newDimEntity.getTextualLayer())
         self.__highlight.addGeometries(newDimEntity.getLinearGeometryCollection(), newDimEntity.getLinearLayer())
         self.__highlight.addGeometries(newDimEntity.getSymbolGeometryCollection(), newDimEntity.getSymbolLayer())


   # ============================================================================
   # addRotatedGeometries
   # ============================================================================
   def addRotatedGeometries(self, angle):
      self.__highlight.reset()

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

         self.rotate(entity, self.basePt, angle)


   def canvasMoveEvent(self, event):
      QadGetPoint.canvasMoveEvent(self, event)

      # once the base point is known, the second point for the rotation angle is required
      if self.mode == Qad_rotate_maptool_ModeEnum.BASE_PT_KNOWN_ASK_FOR_ROTATION_PT:
         angle = qad_utils.getAngleBy2Pts(self.basePt, self.tmpPoint)
         self.addRotatedGeometries(angle)
      # once the base point is known, the second point for the new angle is required
      elif self.mode == Qad_rotate_maptool_ModeEnum.BASE_PT_KNOWN_ASK_FOR_NEW_ROTATION_PT:
         angle = qad_utils.getAngleBy2Pts(self.basePt, self.tmpPoint)
         diffAngle = angle - self.ReferenceAng
         self.addRotatedGeometries(diffAngle)
      # once the first point is known, the second point is required for the new angle
      elif self.mode == Qad_rotate_maptool_ModeEnum.FIRST_PT_KNOWN_ASK_FOR_SECOND_NEW_ROTATION_PT:
         angle = qad_utils.getAngleBy2Pts(self.Pt1NewAng, self.tmpPoint)
         diffAngle = angle - self.ReferenceAng
         self.addRotatedGeometries(diffAngle)


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
      if self.mode == Qad_rotate_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_BASE_PT:
         self.setSelectionMode(QadGetPointSelectionModeEnum.POINT_SELECTION)
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
         self.__highlight.reset()
      # once the base point is known, the second point for the rotation angle is required
      elif self.mode == Qad_rotate_maptool_ModeEnum.BASE_PT_KNOWN_ASK_FOR_ROTATION_PT:
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.basePt)
      # requires the first point for the reference angle
      elif self.mode == Qad_rotate_maptool_ModeEnum.ASK_FOR_FIRST_PT_REFERENCE_ANG:
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
         self.__highlight.reset()
      # once the first point is known, the second point is required for the reference angle
      elif self.mode == Qad_rotate_maptool_ModeEnum.FIRST_PT_KNOWN_ASK_FOR_SECOND_PT_REFERENCE_ANG:
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.Pt1ReferenceAng)
      # once the base point is known, the second point for the new angle is required
      elif self.mode == Qad_rotate_maptool_ModeEnum.BASE_PT_KNOWN_ASK_FOR_NEW_ROTATION_PT:
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.basePt)
      # requires the first point for the new angle
      elif self.mode == Qad_rotate_maptool_ModeEnum.ASK_FOR_FIRST_NEW_ROTATION_PT:
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
      # once the first point is known, the second point is required for the new angle
      elif self.mode == Qad_rotate_maptool_ModeEnum.FIRST_PT_KNOWN_ASK_FOR_SECOND_NEW_ROTATION_PT:
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.Pt1NewAng)
