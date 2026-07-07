# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 class to manage the point request map tool for the arc command

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


from qgis.core import QgsCoordinateTransform, QgsGeometry, QgsProject, QgsWkbTypes


from .. import qad_utils
from ..qad_getpoint import QadGetPoint, QadGetPointDrawModeEnum
from ..qad_line import QadLine
from ..qad_polyline import QadPolyline
from ..qad_arc import QadArc
from ..qad_rubberband import QadRubberBand
from ..qad_highlight import QadHighlight
from ..qad_entity import QadEntity


# ===============================================================================
# Qad_arc_maptool_ModeEnum class.
# ===============================================================================
class Qad_arc_maptool_ModeEnum():
   # if nothing is known, the first point is required
   NONE_KNOWN_ASK_FOR_START_PT = 1
   # Once the initial point of the arc is known, the second point is required
   START_PT_KNOWN_ASK_FOR_SECOND_PT = 2
   # once the starting point and the second point of the arc are known, the final point is required
   START_SECOND_PT_KNOWN_ASK_FOR_END_PT = 3
   # Once the initial point of the arc is known, the center is required
   START_PT_KNOWN_ASK_FOR_CENTER_PT = 4
   # once the starting point and the center of the arc are known, the final point is required
   START_CENTER_PT_KNOWN_ASK_FOR_END_PT = 5
   # once the starting point and the center of the arc are known, the inscribed angle is required
   START_CENTER_PT_KNOWN_ASK_FOR_ANGLE = 6
   # once the starting point and the center of the arc are known, the length of the string is required
   START_CENTER_PT_KNOWN_ASK_FOR_CHORD = 7
   # Once the initial point of the arc is known, the final point is required
   START_PT_KNOWN_ASK_FOR_END_PT = 8
   # note the starting and ending points of the arc, the center is required
   START_END_PT_KNOWN_ASK_FOR_CENTER = 9
   # once the initial and final points of the arc are known, the inscribed angle is required
   START_END_PT_KNOWN_ASK_FOR_ANGLE = 10
   # once the initial and final points of the arc are known, the direction of the tangent to the initial point is required
   START_END_PT_KNOWN_ASK_FOR_TAN = 11
   # once you know the starting and ending points of the arc, the radius is required
   START_END_PT_KNOWN_ASK_FOR_RADIUS = 12
   # I know nothing, the center is required
   NONE_KNOWN_ASK_FOR_CENTER_PT = 13
   # Once the center of the arc is known, the starting point is required
   CENTER_PT_KNOWN_ASK_FOR_START_PT = 14
   # once the starting point and the tangent to the starting point are known, the final point is required
   START_PT_TAN_KNOWN_ASK_FOR_END_PT = 15
   # Once the initial point of the arc is known, the inscribed angle is required
   START_PT_KNOWN_ASK_FOR_ANGLE = 16
   # once the starting point and the inscribed angle of the arc are known, the final point is required
   START_PT_ANGLE_KNOWN_ASK_FOR_END_PT = 17
   # once the starting point and the inscribed angle of the arc are known, the center is required
   START_PT_ANGLE_KNOWN_ASK_FOR_CENTER_PT = 18
   # once the starting point and the inscribed angle of the arc are known, the radius is required
   START_PT_ANGLE_KNOWN_ASK_FOR_RADIUS = 19
   # once the initial point and the inscribed angle of the arc are known, the second point is required to measure the radius
   START_PT_ANGLE_KNOWN_ASK_FOR_SECONDPTRADIUS = 20
   # once the starting point, the inscribed angle and the radius of the arc are known, the direction of the chord is required
   START_PT_ANGLE_RADIUS_KNOWN_ASK_FOR_CHORDDIRECTION = 21
   # once the starting point and the radius of the arc are known, the final point is required
   START_PT_RADIUS_KNOWN_ASK_FOR_END_PT = 22


# ===============================================================================
# Qad_arc_maptool class
# ===============================================================================
class Qad_arc_maptool(QadGetPoint):

   def __init__(self, plugIn, asToolForMPolygon = False):
      QadGetPoint.__init__(self, plugIn)
      self.arcStartPt = None
      self.arcSecondPt = None
      self.arcEndPt = None
      self.arcCenterPt = None
      self.arcTanOnStartPt = None
      self.arcAngle = None
      self.arcStartPtForRadius = None
      self.arcRadius = None
      self.__rubberBand = QadRubberBand(self.canvas)

      self.asToolForMPolygon = asToolForMPolygon # if True means it is used to draw a polygon
      if self.asToolForMPolygon:
         self.__polygonRubberBand = QadRubberBand(self.plugIn.canvas, True)
         self.endVertex = None # points to the starting and ending vertex of the QadPLINECommandClass polygon
      else:
         self.__polygonRubberBand = None

      self.layer = None


   def hidePointMapToolMarkers(self):
      QadGetPoint.hidePointMapToolMarkers(self)
      self.__rubberBand.hide()
      if self.__polygonRubberBand is not None: self.__polygonRubberBand.hide()

   def showPointMapToolMarkers(self):
      QadGetPoint.showPointMapToolMarkers(self)
      self.__rubberBand.show()
      if self.__polygonRubberBand is not None: self.__polygonRubberBand.show()

   def clear(self):
      QadGetPoint.clear(self)
      self.__rubberBand.reset()
      if self.__polygonRubberBand is not None: self.__polygonRubberBand.reset()
      self.mode = None


   # ============================================================================
   # removeItems
   # ============================================================================
   def removeItems(self):
      QadGetPoint.removeItems(self)
      # first detach it from the canvas otherwise it will not be removed because it is used by canvas
      if self.__rubberBand is not None:
         del self.__rubberBand
         self.__rubberBand = None

      if self.__polygonRubberBand is not None:
         del self.__polygonRubberBand
         self.__polygonRubberBand = None


   def canvasMoveEvent(self, event):
      QadGetPoint.canvasMoveEvent(self, event)

      self.__rubberBand.reset()
      if self.__polygonRubberBand is not None: self.__polygonRubberBand.reset()

      result = False
      arc = QadArc()

      # once the first and second points of the arc are known, the third point is required
      if self.mode == Qad_arc_maptool_ModeEnum.START_SECOND_PT_KNOWN_ASK_FOR_END_PT:
         result = arc.fromStartSecondEndPts(self.arcStartPt, self.arcSecondPt, self.tmpPoint)
      # note the first point and the center of the arc, the final point is required
      elif self.mode == Qad_arc_maptool_ModeEnum.START_CENTER_PT_KNOWN_ASK_FOR_END_PT:
         result = arc.fromStartCenterEndPts(self.arcStartPt, self.arcCenterPt, self.tmpPoint)
         if result == True and self.tmpCtrlKey: # I invert the initial-final angle
            arc.inverseAngles()
      # note the first point and the center of the arc, the inscribed angle is required
      elif self.mode == Qad_arc_maptool_ModeEnum.START_CENTER_PT_KNOWN_ASK_FOR_ANGLE:
         angle = qad_utils.getAngleBy2Pts(self.arcCenterPt, self.tmpPoint)
         result = arc.fromStartCenterPtsAngle(self.arcStartPt, self.arcCenterPt, angle)
         if result == True and self.tmpCtrlKey: # I invert the initial-final angle
            arc.inverseAngles()
      # note the first point and the center of the arc, the length of the string is required
      elif self.mode == Qad_arc_maptool_ModeEnum.START_CENTER_PT_KNOWN_ASK_FOR_CHORD:
         chord = qad_utils.getDistance(self.arcStartPt, self.tmpPoint)
         result = arc.fromStartCenterPtsChord(self.arcStartPt, self.arcCenterPt, chord)
         if result == True and self.tmpCtrlKey: # I invert the initial-final angle
            arc.inverseAngles()
      # note the starting and ending points of the arc, the center is required
      elif self.mode == Qad_arc_maptool_ModeEnum.START_END_PT_KNOWN_ASK_FOR_CENTER:
         result = arc.fromStartCenterEndPts(self.arcStartPt, self.tmpPoint, self.arcEndPt)
         if result == True and self.tmpCtrlKey: # I invert the initial-final angle
            arc.inverseAngles()
      # once the initial and final points of the arc are known, the inscribed angle is required
      elif self.mode == Qad_arc_maptool_ModeEnum.START_END_PT_KNOWN_ASK_FOR_ANGLE:
         angle = qad_utils.getAngleBy2Pts(self.arcStartPt, self.tmpPoint)
         result = arc.fromStartEndPtsAngle(self.arcStartPt, self.arcEndPt, angle)
         if result == True and self.tmpCtrlKey: # I invert the initial-final angle
            arc.inverseAngles()
      # once you know the starting and ending points of the arc, you need the direction of the tangent
      elif self.mode == Qad_arc_maptool_ModeEnum.START_END_PT_KNOWN_ASK_FOR_TAN:
         tan = qad_utils.getAngleBy2Pts(self.arcStartPt, self.tmpPoint)
         result = arc.fromStartEndPtsTan(self.arcStartPt, self.arcEndPt, tan)
         if result == True and self.tmpCtrlKey: # I invert the initial-final angle
            arc.inverseAngles()
      # once you know the starting and ending points of the arc, the radius is required
      elif self.mode == Qad_arc_maptool_ModeEnum.START_END_PT_KNOWN_ASK_FOR_RADIUS:
         radius = qad_utils.getDistance(self.arcEndPt, self.tmpPoint)
         result = arc.fromStartEndPtsRadius(self.arcStartPt, self.arcEndPt, radius)
         if result == True and self.tmpCtrlKey: # I invert the initial-final angle
            arc.inverseAngles()
      # once the starting point and the tangent to the starting point are known, the final point is required
      elif self.mode == Qad_arc_maptool_ModeEnum.START_PT_TAN_KNOWN_ASK_FOR_END_PT:
         result = arc.fromStartEndPtsTan(self.arcStartPt, self.tmpPoint, self.arcTanOnStartPt)
         if result == True and self.tmpCtrlKey: # I invert the initial-final angle
            arc.inverseAngles()
      # once the starting point and the inscribed angle of the arc are known, the final point is required
      elif self.mode == Qad_arc_maptool_ModeEnum.START_PT_ANGLE_KNOWN_ASK_FOR_END_PT:
         result = arc.fromStartEndPtsAngle(self.arcStartPt, self.tmpPoint, self.arcAngle)
         if result == True and self.tmpCtrlKey: # I invert the initial-final angle
            arc.inverseAngles()
      # once the starting point and the inscribed angle of the arc are known, the center is required
      elif self.mode == Qad_arc_maptool_ModeEnum.START_PT_ANGLE_KNOWN_ASK_FOR_CENTER_PT:
         result = arc.fromStartCenterPtsAngle(self.arcStartPt, self.tmpPoint, self.arcAngle)
         if result == True and self.tmpCtrlKey: # I invert the initial-final angle
            arc.inverseAngles()
      # once the starting point, the inscribed angle and the radius of the arc are known, the direction of the chord is required
      elif self.mode == Qad_arc_maptool_ModeEnum.START_PT_ANGLE_RADIUS_KNOWN_ASK_FOR_CHORDDIRECTION:
         chordDirection = qad_utils.getAngleBy2Pts(self.arcStartPt, self.tmpPoint)
         result = arc.fromStartPtAngleRadiusChordDirection(self.arcStartPt, self.arcAngle, \
                                                           self.arcRadius, chordDirection)
         if result == True and self.tmpCtrlKey: # I invert the initial-final angle
            arc.inverseAngles()
      # once the starting point and the radius of the arc are known, the final point is required
      elif self.mode == Qad_arc_maptool_ModeEnum.START_PT_RADIUS_KNOWN_ASK_FOR_END_PT:
         result = arc.fromStartEndPtsRadius(self.arcStartPt, self.tmpPoint, self.arcRadius)
         if result == True and self.tmpCtrlKey: # I invert the initial-final angle
            arc.inverseAngles()

      if result == True:
         if self.__polygonRubberBand is None: # means it is NOT used to draw a polygon
            if self.layer is not None:
               g = arc.asGeom(self.layer.wkbType())
            else:
               g = arc.asGeom(QgsWkbTypes.CompoundCurve) # is a virtual arc that will not be saved by this command

            if g is not None: self.__rubberBand.setGeometry(g)
         else: # means it is used to draw a polygon
            pline = QadPolyline()
            pline.append(arc)

            if self.endVertex is not None:
               line = QadLine()
               line.set(arc.getEndPt(), self.endVertex)
               pline.append(line)
               line = QadLine()
               line.set(self.endVertex, arc.getStartPt())
               pline.append(line)
            else:
               line = QadLine()
               line.set(arc.getEndPt(), arc.getStartPt())
               pline.append(line)

            if self.layer is not None:
               g = pline.asGeom(self.layer.wkbType())
            else:
               g = pline.asGeom(QgsWkbTypes.CurvePolygon) # is a virtual arc that will not be saved by this command

            self.__polygonRubberBand.setGeometry(g)

#          points = arc.asPolyline()
#
#          if points is not None:
#             self.__rubberBand.setLine(points)
#             if self.__polygonRubberBand is not None: # means it is used to draw a polygon
#                if self.endVertex is not None:
#                   points.insert(0, self.endVertex)
#                   self.__polygonRubberBand.setPolygon(points)


   def activate(self):
      QadGetPoint.activate(self)
      self.__rubberBand.show()
      if self.__polygonRubberBand is not None: self.__polygonRubberBand.show()

   def deactivate(self):
      try: # necessary because if you close QGIS this event starts even though the map tool object is no longer there!
         QadGetPoint.deactivate(self)
         self.__rubberBand.hide()
         if self.__polygonRubberBand is not None: self.__polygonRubberBand.hide()
      except:
         pass

   def setMode(self, mode):
      self.mode = mode
      # if nothing is known, the first point is required
      if self.mode == Qad_arc_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_START_PT:
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
      # once the first point of the arc is known, the second point is requested
      elif self.mode == Qad_arc_maptool_ModeEnum.START_PT_KNOWN_ASK_FOR_SECOND_PT:
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.arcStartPt)
      # once the first and second points of the arc are known, the third point is required
      elif self.mode == Qad_arc_maptool_ModeEnum.START_SECOND_PT_KNOWN_ASK_FOR_END_PT:
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.arcSecondPt)
      # Once the first point of the arc is known, the center is required
      elif self.mode == Qad_arc_maptool_ModeEnum.START_PT_KNOWN_ASK_FOR_CENTER_PT:
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.arcStartPt)
      # note the first point and the center of the arc, the final point is required
      elif self.mode == Qad_arc_maptool_ModeEnum.START_CENTER_PT_KNOWN_ASK_FOR_END_PT:
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.arcCenterPt)
      # note the first point and the center of the arc, the inscribed angle is required
      elif self.mode == Qad_arc_maptool_ModeEnum.START_CENTER_PT_KNOWN_ASK_FOR_ANGLE:
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.arcCenterPt)
      # note the first point and the center of the arc, the length of the string is required
      elif self.mode == Qad_arc_maptool_ModeEnum.START_CENTER_PT_KNOWN_ASK_FOR_CHORD:
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.arcStartPt)
      # Once the initial point of the arc is known, the final point is required
      elif self.mode == Qad_arc_maptool_ModeEnum.START_PT_KNOWN_ASK_FOR_END_PT:
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.arcStartPt)
      # note the starting and ending points of the arc, the center is required
      elif self.mode == Qad_arc_maptool_ModeEnum.START_END_PT_KNOWN_ASK_FOR_CENTER:
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
      # once the initial and final points of the arc are known, the inscribed angle is required
      elif self.mode == Qad_arc_maptool_ModeEnum.START_END_PT_KNOWN_ASK_FOR_ANGLE:
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.arcStartPt)
      # once you know the starting and ending points of the arc, you need the direction of the tangent
      elif self.mode == Qad_arc_maptool_ModeEnum.START_END_PT_KNOWN_ASK_FOR_TAN:
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.arcStartPt)
      # once you know the starting and ending points of the arc, the radius is required
      elif self.mode == Qad_arc_maptool_ModeEnum.START_END_PT_KNOWN_ASK_FOR_RADIUS:
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.arcEndPt)
      # I know nothing, the center is required
      elif self.mode == Qad_arc_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_CENTER_PT:
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
      # Once the center of the arc is known, the starting point is required
      elif self.mode == Qad_arc_maptool_ModeEnum.CENTER_PT_KNOWN_ASK_FOR_START_PT:
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.arcCenterPt)
      # once the starting point and the tangent to the starting point are known, the final point is required
      elif self.mode == Qad_arc_maptool_ModeEnum.START_PT_TAN_KNOWN_ASK_FOR_END_PT:
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.arcStartPt)
      # Once the initial point of the arc is known, the inscribed angle is required
      elif self.mode == Qad_arc_maptool_ModeEnum.START_PT_KNOWN_ASK_FOR_ANGLE:
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.arcStartPt)
      # once the starting point and the inscribed angle of the arc are known, the final point is required
      elif self.mode == Qad_arc_maptool_ModeEnum.START_PT_ANGLE_KNOWN_ASK_FOR_END_PT:
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.arcStartPt)
      # once the starting point and the inscribed angle of the arc are known, the center is required
      elif self.mode == Qad_arc_maptool_ModeEnum.START_PT_ANGLE_KNOWN_ASK_FOR_CENTER_PT:
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
      # once the starting point and the inscribed angle of the arc are known, the radius is required
      elif self.mode == Qad_arc_maptool_ModeEnum.START_PT_ANGLE_KNOWN_ASK_FOR_RADIUS:
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
      # once the initial point and the inscribed angle of the arc are known, the second point is required to measure the radius
      elif self.mode == Qad_arc_maptool_ModeEnum.START_PT_ANGLE_KNOWN_ASK_FOR_SECONDPTRADIUS:
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.arcStartPtForRadius)
      # once the starting point, the inscribed angle and the radius of the arc are known, the direction of the chord is required
      elif self.mode == Qad_arc_maptool_ModeEnum.START_PT_ANGLE_RADIUS_KNOWN_ASK_FOR_CHORDDIRECTION:
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.arcStartPt)
      # once the starting point and the radius of the arc are known, the final point is required
      elif self.mode == Qad_arc_maptool_ModeEnum.START_PT_RADIUS_KNOWN_ASK_FOR_END_PT:
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.arcStartPt)



# ===============================================================================
# Qad_scale_maptool_ModeEnum class.
# ===============================================================================
class Qad_gripChangeArcRadius_maptool_ModeEnum():
   # the base point is required
   ASK_FOR_BASE_PT = 1
   # once the base point is known, the second point for the radius is required
   BASE_PT_KNOWN_ASK_FOR_RADIUS_PT = 2


# ===============================================================================
# Qad_gripChangeArcRadius_maptool class
# ===============================================================================
class Qad_gripChangeArcRadius_maptool(QadGetPoint):

   def __init__(self, plugIn):
      QadGetPoint.__init__(self, plugIn)

      self.basePt = None
      self.entity = None
      self.arc = None
      self.coordTransform = None
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

   def setEntity(self, entity):
      self.entity = QadEntity(entity)
      self.arc = self.entity.getQadGeom() # arc in map coordinates
      self.basePt = self.arc.center
      self.coordTransform = QgsCoordinateTransform(self.canvas.mapSettings().destinationCrs(), \
                                                   entity.layer.crs(), \
                                                   QgsProject.instance())


   # ============================================================================
   # stretch
   # ============================================================================
   def changeRadius(self, radius):
      self.__highlight.reset()
      # radius = new radius of the arc
      # tolerance2ApproxCurve = tolerance to recreate curves
      self.arc.radius = radius
      points = self.arc.asPolyline()
      if points is None:
         return False

      g = QgsGeometry.fromPolylineXY(points)
      # I transform the geometry into the layer crs
      g.transform(self.coordTransform)
      self.__highlight.addGeometry(g, self.entity.layer)


   def canvasMoveEvent(self, event):
      QadGetPoint.canvasMoveEvent(self, event)

      # once the base point is known, the second point for the radius is required
      if self.mode == Qad_gripChangeArcRadius_maptool_ModeEnum.BASE_PT_KNOWN_ASK_FOR_RADIUS_PT:
         radius = qad_utils.getDistance(self.basePt, self.tmpPoint)
         self.changeRadius(radius)


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
      if self.mode == Qad_gripChangeArcRadius_maptool_ModeEnum.ASK_FOR_BASE_PT:
         self.clear()
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
         self.__highlight.reset()
      # once the base point is known, the second point for the radius is required
      elif self.mode == Qad_gripChangeArcRadius_maptool_ModeEnum.BASE_PT_KNOWN_ASK_FOR_RADIUS_PT:
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.basePt)
