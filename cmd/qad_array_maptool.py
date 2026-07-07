# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin ok

 class to manage the map tool for the array command

                              -------------------
        begin                : 2016-05-31
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
from ..qad_getpoint import QadGetPoint, QadGetPointSelectionModeEnum, QadGetPointDrawModeEnum
from ..qad_highlight import QadHighlight
from ..qad_dim import QadDimStyles, appendDimEntityIfNotExisting
from ..qad_entity import QadCacheEntitySetIterator, QadEntityTypeEnum
from .. import qad_array_fun


# ===============================================================================
# Qad_array_maptool_ModeEnum class.
# ===============================================================================
class Qad_array_maptool_ModeEnum():
   # nothing is required
   NONE = 0
   # the base point is required
   ASK_FOR_BASE_PT = 1
   # requires the first point for the distance between columns
   ASK_FOR_COLUMN_SPACE_FIRST_PT = 2
   # requires the first point for the cell size
   ASK_FOR_1PT_CELL = 3
   # requires the second point for the cell size
   ASK_FOR_2PT_CELL = 4
   # requires the first point for the distance between rows
   ASK_FOR_ROW_SPACE_FIRST_PT = 5


# ===============================================================================
# Qad_array_maptool class
# ===============================================================================
class Qad_array_maptool(QadGetPoint):

   def __init__(self, plugIn):
      QadGetPoint.__init__(self, plugIn)

      self.cacheEntitySet = None
      self.basePt = None
      self.arrayType = None
      self.distanceBetweenRows = None
      self.distanceBetweenCols = None
      self.itemsRotation = None

      # rectangular array
      self.rectangleAngle = None
      self.rectangleCols = None
      self.rectangleRows = None
      self.firstPt = None

      # path array
      self.pathTangentDirection = None
      self.pathRows = None
      self.pathItemsNumber = None
      self.pathPolyline = None

      # polar array
      self.centerPt = None
      self.polarItemsNumber = None
      self.polarAngleBetween = None
      self.polarRows = None

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
   # doRectangleArray
   # ============================================================================
   def doRectangleArray(self):
      self.__highlight.reset()

      dimElaboratedList = [] # list of dimensions already processed
      entityIterator = QadCacheEntitySetIterator(self.cacheEntitySet)
      for entity in entityIterator:
         qadGeom = entity.getQadGeom().copy() # this is how I initialize the qad info
         # check if the entity belongs to a dimensioning style
         dimEntity = QadDimStyles.getDimEntity(entity)
         if dimEntity is not None:
            if appendDimEntityIfNotExisting(dimElaboratedList, dimEntity) == False: # dimension already processed
               continue
            entity = dimEntity

         if qad_array_fun.arrayRectangleEntity(self.plugIn, entity, self.basePt, self.rectangleRows, self.rectangleCols, \
                                               self.distanceBetweenRows, self.distanceBetweenCols, self.rectangleAngle, self.itemsRotation,
                                               False, self.__highlight) == False:
            return


   # ============================================================================
   # doPathArray
   # ============================================================================
   def doPathArray(self):
      self.__highlight.reset()

      dimElaboratedList = [] # list of dimensions already processed
      entityIterator = QadCacheEntitySetIterator(self.cacheEntitySet)
      for entity in entityIterator:
         qadGeom = entity.getQadGeom().copy() # this is how I initialize the qad info
         # check if the entity belongs to a dimensioning style
         dimEntity = QadDimStyles.getDimEntity(entity)
         if dimEntity is not None:
            if appendDimEntityIfNotExisting(dimElaboratedList, dimEntity) == False: # dimension already processed
               continue
            entity = dimEntity

         if qad_array_fun.arrayPathEntity(self.plugIn, entity, self.basePt, self.pathRows, self.pathItemsNumber, \
                                          self.distanceBetweenRows, self.distanceBetweenCols, self.pathTangentDirection, self.itemsRotation, \
                                          self.pathPolyline, self.distanceFromStartPt, \
                                          False, self.__highlight) == False:
            return


   # ============================================================================
   # doPolarArray
   # ============================================================================
   def doPolarArray(self):
      self.__highlight.reset()

      dimElaboratedList = [] # list of dimensions already processed
      entityIterator = QadCacheEntitySetIterator(self.cacheEntitySet)
      for entity in entityIterator:
         qadGeom = entity.getQadGeom().copy() # this is how I initialize the qad info
         # check if the entity belongs to a dimensioning style
         dimEntity = QadDimStyles.getDimEntity(entity)
         if dimEntity is not None:
            if appendDimEntityIfNotExisting(dimElaboratedList, dimEntity) == False: # dimension already processed
               continue
            entity = dimEntity

         if qad_array_fun.arrayPolarEntity(self.plugIn, entity, self.basePt, self.centerPt, self.polarItemsNumber, \
                                           self.polarAngleBetween, self.polarRows, self.distanceBetweenRows, self.itemsRotation, \
                                           False, self.__highlight) == False:
            return


   def canvasMoveEvent(self, event):
      QadGetPoint.canvasMoveEvent(self, event)

#       # once the base point is known, the second point is requested
#       if self.mode == Qad_array_maptool_ModeEnum.BASE_PT_KNOWN_ASK_FOR_COPY_PT:
#          self.setCopiedGeometries(self.tmpPoint)


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
      # nothing is required
      if self.mode == Qad_array_maptool_ModeEnum.NONE:
         self.setSelectionMode(QadGetPointSelectionModeEnum.NONE)
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
      # the base point is required
      elif self.mode == Qad_array_maptool_ModeEnum.ASK_FOR_BASE_PT:
         self.setSelectionMode(QadGetPointSelectionModeEnum.POINT_SELECTION)
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
      # requires the first point for the distance between columns
      elif self.mode == Qad_array_maptool_ModeEnum.ASK_FOR_COLUMN_SPACE_FIRST_PT:
         self.setSelectionMode(QadGetPointSelectionModeEnum.POINT_SELECTION)
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
      # requires the first point for the cell size
      elif self.mode == Qad_array_maptool_ModeEnum.ASK_FOR_1PT_CELL:
         self.setSelectionMode(QadGetPointSelectionModeEnum.POINT_SELECTION)
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
      # requires the second point for the cell size
      elif self.mode == Qad_array_maptool_ModeEnum.ASK_FOR_2PT_CELL:
         self.setSelectionMode(QadGetPointSelectionModeEnum.POINT_SELECTION)
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_RECTANGLE)
         self.setStartPoint(self.firstPt)
      # requires the first point for the distance between rows
      elif self.mode == Qad_array_maptool_ModeEnum.ASK_FOR_ROW_SPACE_FIRST_PT:
         self.setSelectionMode(QadGetPointSelectionModeEnum.POINT_SELECTION)
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)


      # the second point is required for the distance between columns
#       elif self.mode == Qad_array_maptool_ModeEnum.ASK_FOR_COLUMN_SPACE_SECOND_PT:
#          self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
#          self.setStartPoint(self.firstPt)
