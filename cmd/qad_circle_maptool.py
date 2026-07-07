# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 class to manage the point request map tool for the circle command

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


from qgis.core import QgsWkbTypes


from .. import qad_utils
from ..qad_getpoint import QadGetPoint, QadGetPointDrawModeEnum, QadGetPointSelectionModeEnum
from ..qad_circle import QadCircle
from ..qad_circle_fun import *
from ..qad_rubberband import QadRubberBand
from ..qad_snapper import QadSnapTypeEnum


# ===============================================================================
# Qad_circle_maptool_ModeEnum class.
# ===============================================================================
class Qad_circle_maptool_ModeEnum():
   # I know nothing, the center is required
   NONE_KNOWN_ASK_FOR_CENTER_PT = 1
   # Once the center of the circle is known, the radius is required
   CENTER_PT_KNOWN_ASK_FOR_RADIUS = 2
   # Once the center of the circle is known, the diameter is required
   CENTER_PT_KNOWN_ASK_FOR_DIAM = 3
   # if nothing is known, the first point is required
   NONE_KNOWN_ASK_FOR_FIRST_PT = 4
   # Once the first point is known, the second point is required
   FIRST_PT_KNOWN_ASK_FOR_SECOND_PT = 5
   # Once the first and second points are known, the third point is required
   FIRST_SECOND_PT_KNOWN_ASK_FOR_THIRD_PT = 6
   # if nothing is known, the first end point diam. is required
   NONE_KNOWN_ASK_FOR_FIRST_DIAM_PT = 7
   # once the first diam end point is known, the second diam end point is required
   FIRST_DIAM_PT_KNOWN_ASK_FOR_SECOND_DIAM_PT = 8
   # if nothing is known, the magnitude of the first point of tangency is required
   NONE_KNOWN_ASK_FOR_FIRST_TAN = 9
   # once the magnitude of the first tangency point is known, that of the second tangency point is required
   FIRST_TAN_KNOWN_ASK_FOR_SECOND_TAN = 10
   # once the first and second entities of the tangency points are known, the radius is required
   FIRST_SECOND_TAN_KNOWN_ASK_FOR_RADIUS = 11
   # I note the first, second magnitude of the tangent points and the first point to measure the radius
   # the second point is required to measure the radius
   FIRST_SECOND_TAN_FIRSTPTRADIUS_KNOWN_ASK_FOR_SECONDPTRADIUS = 12

# ===============================================================================
# Qad_circle_maptool class
# ===============================================================================
class Qad_circle_maptool(QadGetPoint):

   def __init__(self, plugIn):
      QadGetPoint.__init__(self, plugIn)

      self.centerPt = None
      self.radius = None
      self.firstPt = None
      self.secondPt = None
      self.firstDiamPt = None
      self.tan1 = None
      self.tan2 = None
      self.startPtForRadius = None

      self.__rubberBand = QadRubberBand(self.canvas, False)
      self.layer = None
      self.mode = None


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

      circle = None

      # Once the center of the circle is known, the radius is required
      if self.mode == Qad_circle_maptool_ModeEnum.CENTER_PT_KNOWN_ASK_FOR_RADIUS:
         radius = qad_utils.getDistance(self.centerPt, self.tmpPoint)
         circle = QadCircle().set(self.centerPt, radius)
      # Once the center of the circle is known, the diameter is required
      elif self.mode == Qad_circle_maptool_ModeEnum.CENTER_PT_KNOWN_ASK_FOR_DIAM:
         diam = qad_utils.getDistance(self.centerPt, self.tmpPoint)
         circle = QadCircle().set(self.centerPt, diam / 2)
      # Once the first and second points are known, the third point is required
      elif self.mode == Qad_circle_maptool_ModeEnum.FIRST_SECOND_PT_KNOWN_ASK_FOR_THIRD_PT:
         if (self.firstPt is not None) and (self.secondPt is not None):
            circle = circleFrom3Pts(self.firstPt, self.secondPt, self.tmpPoint)
      # once the first diam end point is known, the second diam end point is required
      elif self.mode == Qad_circle_maptool_ModeEnum.FIRST_DIAM_PT_KNOWN_ASK_FOR_SECOND_DIAM_PT:
         if self.firstDiamPt is not None:
            circle = QadCircle().fromDiamEnds(self.firstDiamPt, self.tmpPoint)
      # I note the first, second magnitude of the tangent points and the first point to measure the radius
      # the second point is required to measure the radius
      elif self.mode == Qad_circle_maptool_ModeEnum.FIRST_SECOND_TAN_FIRSTPTRADIUS_KNOWN_ASK_FOR_SECONDPTRADIUS:
         radius = qad_utils.getDistance(self.startPtForRadius, self.tmpPoint)
         circle = circleFrom2TanPtsRadius(self.tanGeom1, self.tanPt1, \
                                          self.tanGeom2, self.tanPt2, radius)

      if circle is not None:
         if self.layer is not None:
            g = circle.asGeom(self.layer.wkbType())
         else:
            g = circle.asGeom(QgsWkbTypes.CompoundCurve) # is a virtual circle that will not be saved by this command

         if g is not None:
            self.__rubberBand.setGeometry(g)


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
      # I know nothing, the center is required
      if self.mode == Qad_circle_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_CENTER_PT:
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
      # Once the center of the circle is known, the radius is required
      elif self.mode == Qad_circle_maptool_ModeEnum.CENTER_PT_KNOWN_ASK_FOR_RADIUS:
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.centerPt)
      # Once the center of the circle is known, the diameter is required
      elif self.mode == Qad_circle_maptool_ModeEnum.CENTER_PT_KNOWN_ASK_FOR_DIAM:
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.centerPt)
      # if nothing is known, the first point is required
      elif self.mode == Qad_circle_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_FIRST_PT:
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
      # Once the first point is known, the second point is required
      elif self.mode == Qad_circle_maptool_ModeEnum.FIRST_PT_KNOWN_ASK_FOR_SECOND_PT:
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
      # Once the first and second points are known, the third point is required
      elif self.mode == Qad_circle_maptool_ModeEnum.FIRST_SECOND_PT_KNOWN_ASK_FOR_THIRD_PT:
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
      # if nothing is known, the first end point diam. is required
      elif self.mode == Qad_circle_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_FIRST_DIAM_PT:
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
      # once the first diam end point is known, the second diam end point is required
      elif self.mode == Qad_circle_maptool_ModeEnum.FIRST_DIAM_PT_KNOWN_ASK_FOR_SECOND_DIAM_PT:
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
      # if nothing is known, the magnitude of the first point of tangency is required
      elif self.mode == Qad_circle_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_FIRST_TAN:
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
         self.setSelectionMode(QadGetPointSelectionModeEnum.ENTITY_SELECTION)
         self.forceSnapTypeOnce(QadSnapTypeEnum.TAN_DEF)
      # once the magnitude of the first tangency point is known, that of the second tangency point is required
      elif self.mode == Qad_circle_maptool_ModeEnum.FIRST_TAN_KNOWN_ASK_FOR_SECOND_TAN:
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
         self.setSelectionMode(QadGetPointSelectionModeEnum.ENTITY_SELECTION)
         self.forceSnapTypeOnce(QadSnapTypeEnum.TAN_DEF)
      # once the first and second entities of the tangency points are known, the radius is required
      elif self.mode == Qad_circle_maptool_ModeEnum.FIRST_SECOND_TAN_KNOWN_ASK_FOR_RADIUS:
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
         # as the pointer had been changed in ENTITY_SELECTION from the previous selection
         self.setSelectionMode(QadGetPointSelectionModeEnum.POINT_SELECTION)
      # I note the first, second magnitude of the tangent points and the first point to measure the radius
      # the second point is required to measure the radius
      elif self.mode == Qad_circle_maptool_ModeEnum.FIRST_SECOND_TAN_FIRSTPTRADIUS_KNOWN_ASK_FOR_SECONDPTRADIUS:
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.startPtForRadius)
