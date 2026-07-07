# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 class to manage the map tool for dimension commands

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


import math


from .. import qad_utils
from ..qad_getpoint import QadGetPoint, QadGetPointDrawModeEnum
from ..qad_dim import QadDimStyleAlignmentEnum
from ..qad_rubberband import QadRubberBand


# ===============================================================================
# Qad_dim_maptool_ModeEnum class.
# ===============================================================================
class Qad_dim_maptool_ModeEnum():
   # if nothing is known, the first dimensioning point is requested
   NONE_KNOWN_ASK_FOR_FIRST_PT = 1
   # once the first point is known, the second dimensioning point is requested
   FIRST_PT_KNOWN_ASK_FOR_SECOND_PT = 2
   # once the dimensioning points are known, the position of the linear dimension line is required
   FIRST_SECOND_PT_KNOWN_ASK_FOR_LINEAR_DIM_LINE_POS = 3
   # dimension text is required
   ASK_FOR_TEXT = 4
   # Once the dimensioning points are known, the position of the aligned dimension line is required
   FIRST_SECOND_PT_KNOWN_ASK_FOR_ALIGNED_DIM_LINE_POS = 5
   # a point on the arc is required for the arc dimension
   ASK_FOR_PARTIAL_ARC_PT_FOR_DIM_ARC = 6
   # once the dimensioning points are known, the position of the arc dimension line is required
   FIRST_SECOND_PT_KNOWN_ASK_FOR_ARC_DIM_LINE_POS = 7
   # Once the object to be dimensioned is known (arc or circle), the position of the radius dimension line is required
   OBJ_KNOWN_ASK_FOR_RADIUS_DIM_LINE_POS = 8


# ===============================================================================
# Qad_dim_maptool class
# ===============================================================================
class Qad_dim_maptool(QadGetPoint):

   def __init__(self, plugIn):
      QadGetPoint.__init__(self, plugIn)

      dimStyle = None
      self.dimPt1 = None
      self.dimPt2 = None
      self.dimCircle = None

      self.dimArc = None # for arc dimensioning

      self.forcedTextRot = None # dimension text rotation
      self.measure = None # dimension measure (if None is calculated)
      self.preferredAlignment = QadDimStyleAlignmentEnum.HORIZONTAL # alignment of the dimension line
      self.forcedDimLineAlignment = None # forced dimension line alignment
      self.forcedDimLineRot = 0.0 # Forced dimension line rotation
      self.leader = False # to draw the leader line in arc dimensioning

      self.__rubberBand = QadRubberBand(self.canvas)


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


   def setDimLineAlignment(self, LinePosPt, horizLine1, horizLine2, verticalLine1, verticalLine2):
      # < 0 if to the left of the line
      sxOfHorizLine1 = True if qad_utils.leftOfLine(LinePosPt, horizLine1[0], horizLine1[1]) < 0 else False
      sxOfHorizLine2 = True if qad_utils.leftOfLine(LinePosPt, horizLine2[0], horizLine2[1]) < 0 else False

      sxOfVerticalLine1 = True if qad_utils.leftOfLine(LinePosPt, verticalLine1[0], verticalLine1[1]) < 0 else False
      sxOfVerticalLine2 = True if qad_utils.leftOfLine(LinePosPt, verticalLine2[0], verticalLine2[1]) < 0 else False

      # if LinePosPt is between the horizontal limit lines and is not between the vertical limit lines
      if sxOfHorizLine1 != sxOfHorizLine2 and sxOfVerticalLine1 == sxOfVerticalLine2:
         self.preferredAlignment = QadDimStyleAlignmentEnum.HORIZONTAL
      # if LinePosPt is not between the horizontal limit lines and is between the vertical limit lines
      elif sxOfHorizLine1 == sxOfHorizLine2 and sxOfVerticalLine1 != sxOfVerticalLine2:
         self.preferredAlignment = QadDimStyleAlignmentEnum.VERTICAL

      return


   # ============================================================================
   # setLinearDimPtsAndDimLineAlignmentOnCircle
   # ============================================================================
   def setLinearDimPtsAndDimLineAlignmentOnCircle(self, LinePosPt, circle):
      pt1 = qad_utils.getPolarPointByPtAngle(circle.center, self.forcedDimLineRot, circle.radius)
      pt2 = qad_utils.getPolarPointByPtAngle(pt1, self.forcedDimLineRot + math.pi / 2, circle.radius)
      horizLine1 = [pt1, pt2]

      pt1 = qad_utils.getPolarPointByPtAngle(circle.center, self.forcedDimLineRot, -1 * circle.radius)
      pt2 = qad_utils.getPolarPointByPtAngle(pt1, self.forcedDimLineRot + math.pi / 2, circle.radius)
      horizLine2 = [pt1, pt2]

      pt1 = qad_utils.getPolarPointByPtAngle(circle.center, self.forcedDimLineRot + math.pi / 2, circle.radius)
      pt2 = qad_utils.getPolarPointByPtAngle(pt1, self.forcedDimLineRot, circle.radius)
      verticalLine1 = [pt1, pt2]

      pt1 = qad_utils.getPolarPointByPtAngle(circle.center, self.forcedDimLineRot + math.pi / 2, -1 * circle.radius)
      pt2 = qad_utils.getPolarPointByPtAngle(pt1, self.forcedDimLineRot, circle.radius)
      verticalLine2 = [pt1, pt2]

      # if a forced alignment has not been set, calculate it automatically
      if self.forcedDimLineAlignment is None:
         self.setDimLineAlignment(LinePosPt, horizLine1, horizLine2, verticalLine1, verticalLine2)
      else:
         self.preferredAlignment = self.forcedDimLineAlignment

      if self.preferredAlignment == QadDimStyleAlignmentEnum.HORIZONTAL:
         self.dimPt1 = horizLine1[0]
         self.dimPt2 = horizLine2[0]
      else:
         self.dimPt1 = verticalLine1[0]
         self.dimPt2 = verticalLine2[0]


   # ============================================================================
   # setLinearDimLineAlignmentOnDimPts
   # ============================================================================
   def setLinearDimLineAlignmentOnDimPts(self, LinePosPt):
      # if a forced alignment has not been set, calculate it automatically
      if self.forcedDimLineAlignment is None:
         pt2 = qad_utils.getPolarPointByPtAngle(self.dimPt1, self.forcedDimLineRot + math.pi / 2, 1)
         horizLine1 = [self.dimPt1, pt2]

         pt2 = qad_utils.getPolarPointByPtAngle(self.dimPt2, self.forcedDimLineRot + math.pi / 2, 1)
         horizLine2 = [self.dimPt2, pt2]

         pt2 = qad_utils.getPolarPointByPtAngle(self.dimPt1, self.forcedDimLineRot, 1)
         verticalLine1 = [self.dimPt1, pt2]

         pt2 = qad_utils.getPolarPointByPtAngle(self.dimPt2, self.forcedDimLineRot, 1)
         verticalLine2 = [self.dimPt2, pt2]

         self.setDimLineAlignment(LinePosPt, horizLine1, horizLine2, verticalLine1, verticalLine2)
      else:
         self.preferredAlignment = self.forcedDimLineAlignment


   # ============================================================================
   # canvasMoveEvent
   # ============================================================================
   def canvasMoveEvent(self, event):
      QadGetPoint.canvasMoveEvent(self, event)

      self.__rubberBand.reset()

      dimEntity = None

      # once the dimensioning points are known, the position of the linear dimension line is required
      if self.mode == Qad_dim_maptool_ModeEnum.FIRST_SECOND_PT_KNOWN_ASK_FOR_LINEAR_DIM_LINE_POS:
         if self.dimCircle is not None:
            self.setLinearDimPtsAndDimLineAlignmentOnCircle(self.tmpPoint, self.dimCircle)
         else:
            self.setLinearDimLineAlignmentOnDimPts(self.tmpPoint)

         dimEntity, textOffsetRect = self.dimStyle.getLinearDimFeatures(self.canvas, \
                                                                        self.dimPt1, \
                                                                        self.dimPt2, \
                                                                        self.tmpPoint, \
                                                                        self.measure, \
                                                                        self.preferredAlignment, \
                                                                        self.forcedDimLineRot)
      # once the dimensioning points are known, the position of the aligned dimension line is required
      elif self.mode == Qad_dim_maptool_ModeEnum.FIRST_SECOND_PT_KNOWN_ASK_FOR_ALIGNED_DIM_LINE_POS:
         dimEntity, textOffsetRect = self.dimStyle.getAlignedDimFeatures(self.canvas, \
                                                                         self.dimPt1, \
                                                                         self.dimPt2, \
                                                                         self.tmpPoint, \
                                                                         self.measure)
      # once the dimensioning points are known, the position of the arc dimension line is required
      elif self.mode == Qad_dim_maptool_ModeEnum.FIRST_SECOND_PT_KNOWN_ASK_FOR_ARC_DIM_LINE_POS:
         dimEntity, textOffsetRect = self.dimStyle.getArcDimFeatures(self.canvas, \
                                                                     self.dimArc, \
                                                                     self.tmpPoint, \
                                                                     self.measure,
                                                                     self.leader)
      # Once the object to be dimensioned is known (arc or circle), the position of the radius dimension line is required
      elif self.mode == Qad_dim_maptool_ModeEnum.OBJ_KNOWN_ASK_FOR_RADIUS_DIM_LINE_POS:
         dimObj = self.dimCircle if (self.dimCircle is not None) else self.dimArc
         dimEntity, textOffsetRect = self.dimStyle.getRadiusDimFeatures(self.canvas, \
                                                                        dimObj, \
                                                                        self.tmpPoint, \
                                                                        self.measure)

      if dimEntity is not None:
         # dimension text
         self.__rubberBand.addGeometry(dimEntity.textualFeature.geometry(), self.dimStyle.getTextualLayer()) # geom and layer
         self.__rubberBand.addGeometry(textOffsetRect, self.dimStyle.getTextualLayer()) # geom and layer
         for g in dimEntity.getLinearGeometryCollection():
            self.__rubberBand.addGeometry(g, self.dimStyle.getLinearLayer()) # geom and layer
         for g in dimEntity.getSymbolGeometryCollection():
            self.__rubberBand.addGeometry(g, self.dimStyle.getSymbolLayer()) # geom and layer


   def activate(self):
      QadGetPoint.activate(self)
      if self.__rubberBand is not None:
         self.__rubberBand.show()

   def deactivate(self):
      try: # necessary because if you close QGIS this event starts even though the map tool object is no longer there!
         QadGetPoint.deactivate(self)
         if self.__rubberBand is not None:
            self.__rubberBand.hide()
      except:
         pass

   def setMode(self, mode):
      self.mode = mode
      # if nothing is known, the first dimensioning point is requested
      if self.mode == Qad_dim_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_FIRST_PT:
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
      # once the first point is known, the second dimensioning point is requested
      elif self.mode == Qad_dim_maptool_ModeEnum.FIRST_PT_KNOWN_ASK_FOR_SECOND_PT:
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.dimPt1)
      # once the dimensioning points are known, the position of the dimension line is required
      elif self.mode == Qad_dim_maptool_ModeEnum.FIRST_SECOND_PT_KNOWN_ASK_FOR_LINEAR_DIM_LINE_POS:
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
         self.setStartPoint(None)
      # dimension text is required
      elif self.mode == Qad_dim_maptool_ModeEnum.ASK_FOR_TEXT:
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
      # once the dimensioning points are known, the position of the aligned dimension line is required
      elif self.mode == Qad_dim_maptool_ModeEnum.FIRST_SECOND_PT_KNOWN_ASK_FOR_ALIGNED_DIM_LINE_POS:
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
         self.setStartPoint(None)
      # a point on the arc is required for the arc dimension
      elif self.mode == Qad_dim_maptool_ModeEnum.ASK_FOR_PARTIAL_ARC_PT_FOR_DIM_ARC:
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
      # once the dimensioning points are known, the position of the dimension line is required
      elif self.mode == Qad_dim_maptool_ModeEnum.FIRST_SECOND_PT_KNOWN_ASK_FOR_ARC_DIM_LINE_POS:
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
      # Once the object to be dimensioned is known (arc or circle), the position of the radius dimension line is required
      elif self.mode == Qad_dim_maptool_ModeEnum.OBJ_KNOWN_ASK_FOR_RADIUS_DIM_LINE_POS:
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
