# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin ok

 class to manage the point request map tool for the ellipse command

                              -------------------
        begin                : 2018-05-22
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


from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui  import *
from qgis.core import QgsWkbTypes
import math


from .. import qad_utils
from ..qad_getpoint import QadGetPoint, QadGetPointDrawModeEnum
from ..qad_ellipse import QadEllipse
from ..qad_ellipse_arc import QadEllipseArc
from ..qad_rubberband import QadRubberBand


# ===============================================================================
# Qad_ellipse_maptool_ModeEnum class.
# ===============================================================================
class Qad_ellipse_maptool_ModeEnum():
   # if nothing is known, the first end point of the axis is required
   NONE_KNOWN_ASK_FOR_FIRST_FINAL_AXIS_PT = 1
   # once the first end point of the axis is known, the second end point of the axis is required
   FIRST_FINAL_AXIS_PT_KNOWN_ASK_FOR_SECOND_FINAL_AXIS_PT = 2
   # requires specifying the distance from the second axis
   ASK_FOR_DIST_TO_OTHER_AXIS = 3
   # requires rotation around the major axis
   ASK_ROTATION_ROUND_MAJOR_AXIS = 4
   # requires the starting angle
   ASK_START_ANGLE = 5
   # requires the final angle
   ASK_END_ANGLE = 6
   # requires the included angle
   ASK_INCLUDED_ANGLE = 7
   # requires the initial parametric angle
   ASK_START_PARAMETER = 8
   # requires the final parametric angle
   ASK_END_PARAMETER = 9
   # requires the center
   ASK_FOR_CENTER = 10
   # requires the first firing point
   ASK_FOR_FIRST_FOCUS = 11
   # requires the second focus point
   ASK_FOR_SECOND_FOCUS = 12
   # requires a point on the ellipse
   ASK_FOR_PT_ON_ELLIPSE = 13
   # requires the area of the ellipse
   ASK_AREA = 14


# ===============================================================================
# Qad_ellipse_maptool class
# ===============================================================================
class Qad_ellipse_maptool(QadGetPoint):

   def __init__(self, plugIn):
      QadGetPoint.__init__(self, plugIn)

      self.axis1Pt1 = None # first endpoint of the axis
      self.axis1Pt2 = None # second endpoint of the axis
      self.distToOtherAxis = 0.0 # distance from the other axis
      self.rot = 0 # rotation around the axis
      self.centerPt = None # central point of the ellipse
      self.ellipse = None
      self.ellipseArc = QadEllipseArc()
      self.startAngle = 0.0 # the ellipse can be incomplete (like the arc for the circle)
      self.endAngle = math.pi * 2 # A startAngle of 0 and endAngle of 2pi will produce a closed Ellipse.
      self.includedAngle = 0.0
      self.focus1 = None # first firing point
      self.focus2 = None # second firing point

      self.__rubberBand = QadRubberBand(self.canvas, False)
      self.geomType = QgsWkbTypes.PolygonGeometry
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

      ellipse = None

      # once the center of the ellipse is known, it requires specifying the distance from the second axis
      if self.mode == Qad_ellipse_maptool_ModeEnum.ASK_FOR_DIST_TO_OTHER_AXIS:
         dist = qad_utils.getDistance(self.centerPt, self.tmpPoint)
         ellipse = QadEllipse().fromAxis1FinalPtsAxis2Len(self.axis1Pt2, self.axis1Pt1, dist)
      # once the center of the ellipse is known, it requires rotation around the major axis
      elif self.mode == Qad_ellipse_maptool_ModeEnum.ASK_ROTATION_ROUND_MAJOR_AXIS:
         angle = qad_utils.getAngleBy2Pts(self.centerPt, self.tmpPoint)
         dist = math.fabs(qad_utils.getDistance(self.axis1Pt1, self.axis1Pt2) / 2 * math.cos(angle))
         ellipse = QadEllipse().fromAxis1FinalPtsAxis2Len(self.axis1Pt2, self.axis1Pt1, dist)
      # note the ellipse, requires the initial angle
      elif self.mode == Qad_ellipse_maptool_ModeEnum.ASK_START_ANGLE:
         ellipse = self.ellipse
      # note the ellipse, requires the final angle
      elif self.mode == Qad_ellipse_maptool_ModeEnum.ASK_END_ANGLE:
         ellipseAngle = qad_utils.getAngleBy2Pts(self.ellipse.center, self.ellipse.majorAxisFinalPt)
         self.endAngle = qad_utils.getAngleBy2Pts(self.ellipse.center, self.tmpPoint) - ellipseAngle
         self.ellipseArc.set(self.ellipse.center, self.ellipse.majorAxisFinalPt, self.ellipse.axisRatio, self.startAngle, self.endAngle)
         ellipse = self.ellipseArc
      # note the ellipse, requires the included angle
      elif self.mode == Qad_ellipse_maptool_ModeEnum.ASK_INCLUDED_ANGLE:
         includedAngle = qad_utils.getAngleBy2Pts(self.ellipse.center, self.tmpPoint)
         self.endAngle = self.startAngle + includedAngle
         self.ellipseArc.set(self.ellipse.center, self.ellipse.majorAxisFinalPt, self.ellipse.axisRatio, self.startAngle, self.endAngle)
         ellipse = self.ellipseArc
      # note the ellipse, requires the initial parametric angle
      elif self.mode == Qad_ellipse_maptool_ModeEnum.ASK_START_PARAMETER:
         ellipse = self.ellipse
      # note the ellipse, requires the final parametric angle
      elif self.mode == Qad_ellipse_maptool_ModeEnum.ASK_END_PARAMETER:
         ellipseAngle = qad_utils.getAngleBy2Pts(self.ellipse.center, self.ellipse.majorAxisFinalPt)
         self.endAngle = self.ellipse.getAngleFromParam(qad_utils.getAngleBy2Pts(self.ellipse.center, self.tmpPoint) - ellipseAngle)
         self.ellipseArc.set(self.ellipse.center, self.ellipse.majorAxisFinalPt, self.ellipse.axisRatio, self.startAngle, self.endAngle)
         ellipse = self.ellipseArc
      # not the foci of the ellipse, requires specifying a point on the ellipse
      if self.mode == Qad_ellipse_maptool_ModeEnum.ASK_FOR_PT_ON_ELLIPSE:
         ellipse = QadEllipse().fromFoci(self.focus1, self.focus2, self.tmpPoint)

      if ellipse is not None:
         points = ellipse.asPolyline()

         if points is not None:
            if self.geomType == QgsWkbTypes.PolygonGeometry:
               self.__rubberBand.setPolygon(points)
            else:
               self.__rubberBand.setLine(points)


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
      # if nothing is known, the first end point of the axis is required
      if self.mode == Qad_ellipse_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_FIRST_FINAL_AXIS_PT:
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
      # requires specifying the distance from the second axis
      elif self.mode == Qad_ellipse_maptool_ModeEnum.FIRST_FINAL_AXIS_PT_KNOWN_ASK_FOR_SECOND_FINAL_AXIS_PT:
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         if self.axis1Pt1 is not None:
            self.setStartPoint(self.axis1Pt1)
         else:
            self.setStartPoint(self.centerPt)
      # requires specifying the distance from the second axis
      elif self.mode == Qad_ellipse_maptool_ModeEnum.ASK_FOR_DIST_TO_OTHER_AXIS:
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.centerPt)
      # requires rotation around the major axis
      elif self.mode == Qad_ellipse_maptool_ModeEnum.ASK_ROTATION_ROUND_MAJOR_AXIS:
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.centerPt)
      # requires the starting angle
      elif self.mode == Qad_ellipse_maptool_ModeEnum.ASK_START_ANGLE:
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.ellipse.center)
      # requires the final angle
      elif self.mode == Qad_ellipse_maptool_ModeEnum.ASK_END_ANGLE:
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.ellipse.center)
      # requires the included angle
      elif self.mode == Qad_ellipse_maptool_ModeEnum.ASK_INCLUDED_ANGLE:
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.ellipse.center)
      # requires the initial parametric angle
      elif self.mode == Qad_ellipse_maptool_ModeEnum.ASK_START_PARAMETER:
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.ellipse.center)
      # requires the final parametric angle
      elif self.mode == Qad_ellipse_maptool_ModeEnum.ASK_END_PARAMETER:
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.ellipse.center)
      # requires the center
      elif self.mode == Qad_ellipse_maptool_ModeEnum.ASK_FOR_CENTER:
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
      # requires the first firing point
      elif self.mode == Qad_ellipse_maptool_ModeEnum.ASK_FOR_FIRST_FOCUS:
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
      # requires the second focus point
      elif self.mode == Qad_ellipse_maptool_ModeEnum.ASK_FOR_SECOND_FOCUS:
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
      # requires a point on the ellipse
      elif self.mode == Qad_ellipse_maptool_ModeEnum.ASK_FOR_PT_ON_ELLIPSE:
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
      # requires the area of the ellipse
      elif self.mode == Qad_ellipse_maptool_ModeEnum.ASK_AREA:
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
