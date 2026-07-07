# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 class to manage the map tool for the stretch command

                              -------------------
        begin                : 2014-01-08
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
from ..qad_variables import QadVariables
from ..qad_getpoint import QadGetPoint, QadGetPointSelectionModeEnum, QadGetPointDrawModeEnum
from ..qad_multi_geom import *
from ..qad_dim import QadDimEntity, QadDimStyles
from ..qad_stretch_fun import stretchQadGeometry
from ..qad_highlight import QadHighlight
from ..qad_msg import QadMsg
from ..qad_entity import QadEntitySet, QadEntity, QadEntityTypeEnum
from ..qad_multi_geom import fromQadGeomToQgsGeom


# ===============================================================================
# Qad_stretch_maptool_ModeEnum class.
# ===============================================================================
class Qad_stretch_maptool_ModeEnum():
   # requires the selection of the first point of the rectangle to select the objects
   ASK_FOR_FIRST_PT_RECTANGLE = 1
   # knowing nothing the first point of the rectangle requires the second point
   FIRST_PT_KNOWN_ASK_FOR_SECOND_PT_RECTANGLE = 2
   # known nothing, the base point is required
   NONE_KNOWN_ASK_FOR_BASE_PT = 3
   # once the base point is known, the second point is required for the movement
   BASE_PT_KNOWN_ASK_FOR_MOVE_PT = 4


# ===============================================================================
# Qad_stretch_maptool class
# ===============================================================================
class Qad_stretch_maptool(QadGetPoint):

   def __init__(self, plugIn):
      QadGetPoint.__init__(self, plugIn)

      self.basePt = None
      self.SSGeomList = [] # list of entities to stretch with selection geom
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
   # stretch
   # ============================================================================
   def stretch(self, entity, containerGeom, offsetX, offsetY, tolerance2ApproxCurve):
      # entity = entity to stretch
      # ptList = list of points to stretch
      # offsetX, offsetY = spostamento da applicare
      # tolerance2ApproxCurve = tolerance to recreate curves
      # check if the entity belongs to a dimensioning style
      if entity.whatIs() == "ENTITY":
         stretchedGeom = entity.getQadGeom()
         # check inserted because with dimensions, this is deleted and recreated so some objects may no longer exist
         if stretchedGeom is None: # if there is no jump without error
            return True
         # stretch the feature
         stretchedGeom = stretchQadGeometry(stretchedGeom, containerGeom, \
                                            offsetX, offsetY)

         if stretchedGeom is not None:
            # I transform the geometry into the layer crs
            self.__highlight.addGeometry(fromQadGeomToQgsGeom(stretchedGeom, entity.layer), entity.layer)

      elif entity.whatIs() == "DIMENTITY":
         newDimEntity = QadDimEntity(entity) # I copy it
         # stretch the dimension
         newDimEntity.stretch(containerGeom, offsetX, offsetY)
         self.__highlight.addGeometry(newDimEntity.textualFeature.geometry(), newDimEntity.getTextualLayer())
         self.__highlight.addGeometries(newDimEntity.getLinearGeometryCollection(), newDimEntity.getLinearLayer())
         self.__highlight.addGeometries(newDimEntity.getSymbolGeometryCollection(), newDimEntity.getSymbolLayer())

      return True


   # ============================================================================
   # addStretchedGeometries
   # ============================================================================
   def addStretchedGeometries(self, newPt):
      self.__highlight.reset()

      dimElaboratedList = [] # list of dimensions already processed

      tolerance2ApproxCurve = QadVariables.get(QadMsg.translate("Environment variables", "TOLERANCE2APPROXCURVE"))
      offsetX = newPt.x() - self.basePt.x()
      offsetY = newPt.y() - self.basePt.y()

      entity = QadEntity()
      for SSGeom in self.SSGeomList:
         # copy entitySet
         entitySet = QadEntitySet(SSGeom[0])
         geomSel = SSGeom[1]

         for layerEntitySet in entitySet.layerEntitySetList:
            layer = layerEntitySet.layer

            for featureId in layerEntitySet.featureIds:
               entity.set(layer, featureId)

               # check if the entity belongs to a dimensioning style
               dimEntity = QadDimStyles.getDimEntity(entity)
               if dimEntity is None:
                  self.stretch(entity, geomSel, offsetX, offsetY, tolerance2ApproxCurve)
               else:
                  found = False
                  for dimElaborated in dimElaboratedList:
                     if dimElaborated == dimEntity:
                        found = True

                  if found == False: # share not yet processed
                     dimElaboratedList.append(dimEntity)
                     self.stretch(dimEntity, geomSel, offsetX, offsetY, tolerance2ApproxCurve)


   def canvasMoveEvent(self, event):
      QadGetPoint.canvasMoveEvent(self, event)

      # once the base point is known, the second point for the rotation angle is required
      if self.mode == Qad_stretch_maptool_ModeEnum.BASE_PT_KNOWN_ASK_FOR_MOVE_PT:
         self.addStretchedGeometries(self.tmpPoint)


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

      # requires the selection of the first point of the rectangle to select the objects
      if self.mode == Qad_stretch_maptool_ModeEnum.ASK_FOR_FIRST_PT_RECTANGLE:
         self.setSelectionMode(QadGetPointSelectionModeEnum.POINT_SELECTION)
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
      # knowing nothing the first point of the rectangle requires the second point
      elif self.mode == Qad_stretch_maptool_ModeEnum.FIRST_PT_KNOWN_ASK_FOR_SECOND_PT_RECTANGLE:
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_RECTANGLE)
      # known nothing, the base point is required
      elif self.mode == Qad_stretch_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_BASE_PT:
         self.setSelectionMode(QadGetPointSelectionModeEnum.POINT_SELECTION)
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
      # Once the base point is known, the second point is required
      elif self.mode == Qad_stretch_maptool_ModeEnum.BASE_PT_KNOWN_ASK_FOR_MOVE_PT:
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.basePt)


# ===============================================================================
# Qad_gripStretch_maptool class
# ===============================================================================
class Qad_gripStretch_maptool(QadGetPoint):

   def __init__(self, plugIn):
      QadGetPoint.__init__(self, plugIn)

      self.basePt = None
      self.selectedEntityGripPoints = [] # list in which each element is an entity + a list of points to stretch
      self.__highlight = QadHighlight(self.canvas)
      self.prevPart = None # for dynamic input
      self.nextPart = None # for dynamic input

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
   # setSelectedEntityGripPoints
   # ============================================================================
   def setSelectedEntityGripPoints(self, selectedEntityGripPoints):
      self.selectedEntityGripPoints = selectedEntityGripPoints


   # ============================================================================
   # getSelectedEntityGripPointNdx
   # ============================================================================
   def getSelectedEntityGripPointNdx(self, entity):
      # list of entityGripPoints with selected grip points
      # searces for the position of an entity in the list where each element is an entity + a list of points to stretch
      i = 0
      tot = len(self.selectedEntityGripPoints)
      while i < tot:
         selectedEntityGripPoint = self.selectedEntityGripPoints[i]
         if selectedEntityGripPoint[0] == entity:
            return i
         i = i + 1
      return -1


   # ============================================================================
   # stretch
   # ============================================================================
   def stretch(self, entity, ptList, offsetX, offsetY, tolerance2ApproxCurve):
      # entity = entity to stretch
      # ptList = list of points to stretch
      # offsetX, offsetY = spostamento da applicare
      # tolerance2ApproxCurve = tolerance to recreate curves
      # entitySet = selection group of entities to stretch
      # check if the entity belongs to a dimensioning style
      if entity.whatIs() == "ENTITY":
         stretchedGeom = stretchQadGeometry(entity.getQadGeom(), ptList, offsetX, offsetY)

         if stretchedGeom is not None:
            # I transform the geometry into the layer crs
            self.__highlight.addGeometry(fromQadGeomToQgsGeom(stretchedGeom, entity.layer), entity.layer)
         return stretchedGeom
      elif entity.whatIs() == "DIMENTITY":
         # stretch the dimension
         entity.stretch(ptList, offsetX, offsetY)
         self.__highlight.addGeometry(entity.textualFeature.geometry(), entity.getTextualLayer())
         self.__highlight.addGeometries(entity.getLinearGeometryCollection(), entity.getLinearLayer())
         self.__highlight.addGeometries(entity.getSymbolGeometryCollection(), entity.getSymbolLayer())


   # ============================================================================
   # addStretchedGeometries
   # ============================================================================
   def addStretchedGeometries(self, newPt):
      self.__highlight.reset()

      dimElaboratedList = [] # list of dimensions already processed
      iEnt = 0
      for selectedEntity in self.selectedEntityGripPoints:
         entity = selectedEntity[0]
         ptList = selectedEntity[1]
         layer = entity.layer

         tolerance2ApproxCurve = QadVariables.get(QadMsg.translate("Environment variables", "TOLERANCE2APPROXCURVE"))
         offsetX = newPt.x() - self.basePt.x()
         offsetY = newPt.y() - self.basePt.y()

         # check if the entity belongs to a dimensioning style
         dimEntity = QadDimStyles.getDimEntity(entity)
         if dimEntity is None:
            stretchedGeom = self.stretch(entity, ptList, offsetX, offsetY, tolerance2ApproxCurve)
         else:
            found = False
            for dimElaborated in dimElaboratedList:
               if dimElaborated == dimEntity:
                  found = True
            if found == False: # share not yet processed
               dimEntitySet = dimEntity.getEntitySet()
               # create a single list containing the grip points of all the components of the dimension
               dimPtlist = []
               for layerEntitySet in dimEntitySet.layerEntitySetList:
                  for featureId in layerEntitySet.featureIds:
                     componentDim = QadEntity()
                     componentDim.set(layerEntitySet.layer, featureId)
                     i = self.getSelectedEntityGripPointNdx(componentDim)
                     if i >= 0:
                        dimPtlist.extend(self.selectedEntityGripPoints[i][1])

               dimElaboratedList.append(dimEntity)
               self.stretch(dimEntity, dimPtlist, offsetX, offsetY, tolerance2ApproxCurve)
         iEnt = iEnt + 1


   def canvasMoveEvent(self, event):
      QadGetPoint.canvasMoveEvent(self, event)

      # once the base point is known, the second point for the rotation angle is required
      if self.mode == Qad_stretch_maptool_ModeEnum.BASE_PT_KNOWN_ASK_FOR_MOVE_PT:
         self.addStretchedGeometries(self.tmpPoint)


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
      if self.mode == Qad_stretch_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_BASE_PT:
         self.setSelectionMode(QadGetPointSelectionModeEnum.POINT_SELECTION)
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
         self.__highlight.reset()
         self.prevPart = None
         self.nextPart = None
         self.getDynamicInput().setPrevPoint(None)
         self.getDynamicInput().setPrevPart(self.prevPart)
         self.getDynamicInput().setNextPart(self.nextPart)

      # Once the base point is known, the second point is required
      elif self.mode == Qad_stretch_maptool_ModeEnum.BASE_PT_KNOWN_ASK_FOR_MOVE_PT:
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.basePt)
         self.getDynamicInput().setPrevPart(self.prevPart)
         self.getDynamicInput().setNextPart(self.nextPart)
         if self.prevPart is not None or self.nextPart is not None:
            self.getDynamicInput().setPrevPoint(None)
