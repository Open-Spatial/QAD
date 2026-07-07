# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 functions for the BREAK command to cut an object

                              -------------------
        begin                : 2019-08-08
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
from qgis.core import *
from qgis.gui import *


from .qad_multi_geom import getQadGeomAt, isLinearQadGeom
from .qad_geom_relations import *


# ===============================================================================
# breakQadGeometry
# ===============================================================================
def breakQadGeometry(qadGeom, firstPt, secondPt):
   """the function breaks the geometry at one point (if <secondPt> = None) or at two points
      how does the trim.
      <qadGeom> = geometry to cut
      <firstPt> = first dividing point
      <secondPt> = second dividing point
   """
   if qadGeom is None: return None

   gType = qadGeom.whatIs()
   if gType == "POINT" or gType == "MULTI_POINT":
      return None

   # the function returns a list with
   # (<minimum distance>
   # <nearest point>
   # <nearest geometry index>
   # <index of the nearest sub-geometry>
   # <index of the closest sub-geometry part>
   # <"to the left of" if the point is to the left of the part with the following values:
   # - < 0 = left (for line, arc or ellipse arc) or inside (for circles, ellipses)
   # - > 0 = right (for line, arc or ellipse arc) or outside (for circles, ellipses)
   # )
   result = getQadGeomClosestPart(qadGeom, firstPt)
   myFirstPt = result[1]
   atGeom = result[2]
   atSubGeom = result[3]
   subQadGeom = getQadGeomAt(qadGeom, atGeom, atSubGeom).copy()

   mySecondPt = None
   if secondPt is not None:
      # the function returns a list with
      # (<minimum distance>
      # <nearest point>
      # <nearest geometry index>
      # <index of the nearest sub-geometry>
      # <index of the closest sub-geometry part>
      # <"to the left of" if the point is to the left of the part with the following values:
      # - < 0 = left (for line, arc or ellipse arc) or inside (for circles, ellipses)
      # - > 0 = right (for line, arc or ellipse arc) or outside (for circles, ellipses)
      # )
      result = getQadGeomClosestPart(qadGeom, secondPt)
      mySecondPt = result[1]
      atGeom = result[2]
      atSubGeom = result[3]
      # if the subgeometries are different
      if result[2] != atGeom or result[3] != atSubGeom:  return None

   if mySecondPt is None or qad_utils.ptNear(myFirstPt, mySecondPt):
      # I divide the polyline into 2
      if isLinearQadGeom(subQadGeom) == False: return None

      dummy = subQadGeom.breakOnPts(myFirstPt, None)
      if dummy is None: return None
      return [dummy[0], dummy[1], atGeom, atSubGeom]
   else: # there is also the second dividing point
      gType = subQadGeom.whatIs()
      if gType == "CIRCLE":
         endAngle = qad_utils.getAngleBy2Pts(subQadGeom.center, myFirstPt)
         startAngle = qad_utils.getAngleBy2Pts(subQadGeom.center, mySecondPt)
         arc = QadArc().set(subQadGeom.center, subQadGeom.radius, startAngle, endAngle)
         return [arc, None, atGeom, atSubGeom]

      elif gType == "ELLIPSE":
         endAngle = qad_utils.getAngleBy3Pts(subQadGeom.majorAxisFinalPt, subQadGeom.center, myFirstPt, False)
         startAngle = qad_utils.getAngleBy3Pts(subQadGeom.majorAxisFinalPt, subQadGeom.center, mySecondPt, False)
         ellipseArc = QadEllipseArc().set(subQadGeom.center, subQadGeom.majorAxisFinalPt, subQadGeom.axisRatio, startAngle, endAngle)
         return [ellipseArc, None, atGeom, atSubGeom]

      else:
         dummy = subQadGeom.breakOnPts(myFirstPt, mySecondPt)
         return [dummy[0], dummy[1], atGeom, atSubGeom]

