# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 class to manage snaps

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


from qgis.core import *

import math
import sys

from . import qad_utils
from .qad_multi_geom import *
from .qad_geom_relations import *
from .qad_entity import *
from .qad_msg import QadMsg
from .qad_variables import QadVariables


# ===============================================================================
# QadSnapTypeEnum class.
# ===============================================================================
class QadSnapTypeEnum():
   NONE      = 0       # none
   END       = 1       # end points of each segment
   MID       = 2       # midpoint
   CEN       = 4       # center (centroid)
   NOD       = 8       # point object
   QUA       = 16      # quadrant point
   INT       = 32      # intersection
   INS       = 64      # insertion point
   PER       = 128     # perpendicular point
   TAN       = 256     # tangent
   NEA       = 512     # closest point
   C         = 1024    # clear all object snaps
   APP       = 2048    # apparent intersection
   EXT       = 4096    # extension
   PAR       = 8192    # parallel
   DISABLE   = 16384   # osnap off
   PR        = 65536   # progressive distance
   EXT_INT   = 131072  # intersection on extension
   PER_DEF   = 262144  # deferred perpendicular (come NEA)
   TAN_DEF   = 524288  # deferred tangent (come NEA)
   POLAR     = 1048576 # polar tracking
   END_PLINE = 2097152 # end points of the entire polyline

# ===============================================================================
# QadSnapModeEnum class.
# ===============================================================================
class QadSnapModeEnum():
   ONE_RESULT           = 0 # Only the closest point is returned
   ALL_RESULTS          = 2 # All points

# ===============================================================================
# QadVertexSearcModeEnum class.
# ===============================================================================
class QadVertexSearchModeEnum():
   ALL               = 0 # all vertices
   EXCLUDE_START_END = 1 # exclude the start and end point
   ONLY_START_END    = 2 # only the starting and ending points


# ===============================================================================
# Qad snapper class.
# ===============================================================================
class QadSnapper():
   """Class that manages snap points, snap points are always stored in the canvas coordinate system
      which uses a flat system (no geographic coordinates)
   """


   # ============================================================================
   # __init__
   # ============================================================================
   def __init__(self):
      self.__snapType = QadSnapTypeEnum.NONE
      self.__snapLayers = None
      self.__snapMode = QadSnapModeEnum.ONE_RESULT

      # canvas coordinate system in which to store the snap points (to work with xy plane coordinates)
      self.__snapPointCRS = qgis.utils.iface.mapCanvas().mapSettings().destinationCrs()
      self.__startPoint = None
      self.__toleranceExtParLines = 0

      self.__extLinearObjs = [] # list of linear objects to extend (QadLine or QadArc or QadEllipseArc)
      self.__parLines = [] # list of lines for parallel mode (each element is a QadLine)
      self.__intExtLinearObjs = [] # list of linear objects for intersection on extension (QadLine or QadArc or QadEllipseArc)

      self.__cacheEntitySet = QadCacheEntitySet() # cache of QAD entities
      self.__oSnapPointsForPolar = dict() # dictionary of osnap points selected for the polar option
      self.__oSnapLinesForPolar = [] # list of lines (QadLine) for the polar option
      self.__progressDistance = 0.0 # progressive distance from the start of the line
      self.__distToExcludeNea = 0.0 # distance within which there are snap points
                                    # different from nearest; these have priority over nearest
                                    # otherwise nearest would always win
      self.tmpGeometries = [] # list of qad geometries not yet existing but to be counted for osnap points (in map coordinates)


   # ============================================================================
   # SnapType
   # ============================================================================
   def setSnapType(self, snapType):
      """Sets the snapping type"""
      if self.__snapType != snapType:
         self.__snapType = snapType
         self.removeReferenceLines()
   def getSnapType(self):
      """Returns the snapping type"""
      return self.__snapType


   # ============================================================================
   # SnapType
   # ============================================================================
   def getGeometryTypesAccordingToSnapType(self):
      """Check which geometries are affected by the type of snap set
            Returns a list of 3 elements: (point, line, polygon)
            - if the first element is true the dot type is involved otherwise false
            - if the second element is true the line type is involved otherwise false
            - if the third element is true the polygon type is involved otherwise false
      """
      if self.getSnapType() == QadSnapTypeEnum.NONE or \
         self.getSnapType() & QadSnapTypeEnum.DISABLE:
         return False, False, False

      point = False
      line = False
      polygon = False

      # <point object> or <insertion point> or <nearest point>
      if self.getSnapType() & QadSnapTypeEnum.NOD or \
         self.getSnapType() & QadSnapTypeEnum.INS or \
         self.getSnapType() & QadSnapTypeEnum.NEA:
         point = True

      # <end point> or <midpoint> or <center (centroid or arc center)> or
      # <intersection> or <perpendicular point> or <tangent> or
      # <nearest point> or <apparent intersection> or <extension>
      # <parallel> or <progressive distance> or <extension intersection>
      if self.getSnapType() & QadSnapTypeEnum.END or \
         self.getSnapType() & QadSnapTypeEnum.END_PLINE or \
         self.getSnapType() & QadSnapTypeEnum.MID or \
         self.getSnapType() & QadSnapTypeEnum.CEN or \
         self.getSnapType() & QadSnapTypeEnum.QUA or \
         self.getSnapType() & QadSnapTypeEnum.INT or \
         self.getSnapType() & QadSnapTypeEnum.PER or \
         self.getSnapType() & QadSnapTypeEnum.TAN or \
         self.getSnapType() & QadSnapTypeEnum.NEA or \
         self.getSnapType() & QadSnapTypeEnum.APP or \
         self.getSnapType() & QadSnapTypeEnum.EXT or \
         self.getSnapType() & QadSnapTypeEnum.PAR or \
         self.getSnapType() & QadSnapTypeEnum.PR or \
         self.getSnapType() & QadSnapTypeEnum.EXT_INT or \
         self.getSnapType() & QadSnapTypeEnum.PER_DEF or \
         self.getSnapType() & QadSnapTypeEnum.TAN_DEF:
         line = True

      # <end point> or <midpoint> or <center (centroid or arc center)> or
      # <quadrant point> or <intersection> or <perpendicular point> or <tangent> or
      # <nearest point> or <apparent intersection> or <extension>
      # <parallel> or <progressive distance> or <extension intersection>
      if self.getSnapType() & QadSnapTypeEnum.END or \
         self.getSnapType() & QadSnapTypeEnum.MID or \
         self.getSnapType() & QadSnapTypeEnum.CEN or \
         self.getSnapType() & QadSnapTypeEnum.QUA or \
         self.getSnapType() & QadSnapTypeEnum.INT or \
         self.getSnapType() & QadSnapTypeEnum.PER or \
         self.getSnapType() & QadSnapTypeEnum.TAN or \
         self.getSnapType() & QadSnapTypeEnum.NEA or \
         self.getSnapType() & QadSnapTypeEnum.APP or \
         self.getSnapType() & QadSnapTypeEnum.EXT or \
         self.getSnapType() & QadSnapTypeEnum.PAR or \
         self.getSnapType() & QadSnapTypeEnum.PR or \
         self.getSnapType() & QadSnapTypeEnum.EXT_INT or \
         self.getSnapType() & QadSnapTypeEnum.PER_DEF or \
         self.getSnapType() & QadSnapTypeEnum.TAN_DEF:
         polygon = True

      return point, line, polygon


   # ============================================================================
   # Snapmode
   # ============================================================================
   def setSnapMode(self, snapMode):
      """Set the snapping mode"""
      self.__snapMode = snapMode
   def getSnapMode(self):
      """Returns the snapping mode"""
      return self.__snapMode


   # ============================================================================
   # SnapLayers
   # ============================================================================
   def setSnapLayers(self, snapLayers):
      """
      Imposta i layer da considerare nello snapping
      """
      self.__snapLayers = snapLayers
   def getSnapLayers(self):
      """Returns the list of layers to consider for snapping"""
      return self.__snapLayers


   # ============================================================================
   # setStartPoint
   # ============================================================================
   def setStartPoint(self, startPoint):
      """sets the starting point used to calculate snap points"""
      self.__startPoint = startPoint


   # ============================================================================
   # setDistToExcludeNea
   # ============================================================================
   def setDistToExcludeNea(self, distToExcludeNea):
      """sets the distance within which if there are snap points other than nearest
            these have priority over nearest otherwise nearest would always win
      """
      self.__distToExcludeNea = distToExcludeNea


   # ===========================================================================
   # getOsnapPtAndLinesForPolar
   # ===========================================================================
   def getOsnapPtAndLinesForPolar(self, point, polarAng, polarAngOffset, polarAddAngles):
      # calculate polar points for all osnap points selected for the polar option and for the current point
      # points go to result, lines go to self.__oSnapLinesForPolar

      result = []
      del self.__oSnapLinesForPolar[:]
      # for all osnap points selected for the polar option
      for item in self.__oSnapPointsForPolar.items():
         # I skip the POLAR type
         if item[0] != QadSnapTypeEnum.POLAR:
            for startPoint in item[1]:
               pts = self.getPolarCoord(startPoint, point, polarAng, polarAngOffset, polarAddAngles) # returns a list with a single point
               if len(pts) > 0:
                  self.__appendUniquePoint(result, pts[0]) # without duplication
                  l = QadLine().set(startPoint, pts[0])
                  self.__oSnapLinesForPolar.append(l)

      # for the starting point
      if self.__startPoint is not None:
         pts = self.getPolarCoord(self.__startPoint, point, polarAng, polarAngOffset, polarAddAngles) # returns a list with a single point
         if len(pts) > 0:
            self.__appendUniquePoint(result, pts[0]) # without duplication
            l = QadLine().set(self.__startPoint, pts[0])
            self.__oSnapLinesForPolar.append(l)

      return result


   # ============================================================================
   # getIntPtsBetweenOSnapLinesForPolar
   # ============================================================================
   def getIntPtsBetweenOSnapLinesForPolar(self):
      # calculate the intersections of the polar lines
      result = []
      i = 0
      totLines = len(self.__oSnapLinesForPolar)
      while i < totLines:
         line1 = self.__oSnapLinesForPolar[i]
         j = i + 1
         while j < totLines:
            line2 = self.__oSnapLinesForPolar[j]
            point = QadIntersections.twoInfinityLines(line1, line2)
            if point is not None:
               self.__appendUniquePoint(result, point) # without duplication
            j = j + 1
         i = i + 1

      return result


   # ============================================================================
   # OSnapPointsForPolar
   # ============================================================================
   def __toggleOSnapPointsForPolar(self, mousePoint, oSnapPointsForPolar, snapMarkerSizeInMapUnits = None):
      """Adds an osnap point used for the polar option
            if not yet added to the list otherwise remove it from the list
            __oSnapPointsForPolar is a dictionary of snap point lists
            divided by snap types (e.g. {END : [pt1 .. ptn] MID : [pt1 .. ptn]})
      """
      del self.__oSnapLinesForPolar[:]

      markerSize = QadVariables.get(QadMsg.translate("Environment variables", "AUTOSNAPSIZE")) if snapMarkerSizeInMapUnits is None else snapMarkerSizeInMapUnits

      for itemToToggle in oSnapPointsForPolar.items():
         for ptToToggle in itemToToggle[1]: # for each point
            # if the point <point> is inside the snap point marker which has dimensions markerSize
            if mousePoint.x() >= ptToToggle.x() - markerSize and mousePoint.x() <= ptToToggle.x() + markerSize and \
               mousePoint.y() >= ptToToggle.y() - markerSize and mousePoint.y() <= ptToToggle.y() + markerSize:
               add = True
               for item in self.__oSnapPointsForPolar.items():
                  polarPts = item[1]
                  for i in range(len(polarPts) - 1, -1, -1):
                     polarPt = polarPts[i]
                     # if the point <point> is inside the polar snap point marker which has dimensions markerSize
                     if mousePoint.x() >= polarPt.x() - markerSize and mousePoint.x() <= polarPt.x() + markerSize and \
                        mousePoint.y() >= polarPt.y() - markerSize and mousePoint.y() <= polarPt.y() + markerSize:
                        del polarPts[i]
                        add = False

               if add:
                  key = itemToToggle[0]
                  if key in self.__oSnapPointsForPolar: # if already present
                     self.__oSnapPointsForPolar[key].append(ptToToggle)
                  else:
                     self.__oSnapPointsForPolar[key] = [ptToToggle]

#       autoSnapSize = QadVariables.get(QadMsg.translate("Environment variables", "AUTOSNAPSIZE"))
#
#       for itemToToggle in oSnapPointsForPolar.items():
#          key = itemToToggle[0]
#          # non considero alcuni tipi di snap
#          if key == QadSnapTypeEnum.INT or key == QadSnapTypeEnum.PER or key == QadSnapTypeEnum.TAN or \
#             key == QadSnapTypeEnum.NEA or key == QadSnapTypeEnum.APP or key == QadSnapTypeEnum.EXT or \
#             key == QadSnapTypeEnum.PAR or key == QadSnapTypeEnum.PR or key == QadSnapTypeEnum.EXT_INT or \
#             key == QadSnapTypeEnum.PER_DEF or key == QadSnapTypeEnum.TAN_DEF or key == QadSnapTypeEnum.POLAR:
#             continue
#
#          for ptToToggle in itemToToggle[1]: # for each point
#             # the point <point> must be inside the snap point that has dimensions snapMarkerSizeInMapUnits
#             if point.x() >= ptToToggle.x() - snapMarkerSizeInMapUnits and point.x() <= ptToToggle.x() + snapMarkerSizeInMapUnits and \
#                point.y() >= ptToToggle.y() - snapMarkerSizeInMapUnits and point.y() <= ptToToggle.y() + snapMarkerSizeInMapUnits:
#                add = True
#                for item in self.__oSnapPointsForPolar.items():
#                   i = 0
#                   for pt in item[1]:
#                      if pt == ptToToggle:
#                         del item[1][i]
#                         add = False
#                         i = i + 1
#
#                if add:
#                   if key in self.__oSnapPointsForPolar: # if already present
#                      self.__oSnapPointsForPolar[key].append(ptToToggle)
#                   else:
#                      self.__oSnapPointsForPolar[key] = [ptToToggle]


   def removeOSnapPointsForPolar(self):
      """Delete all osnap points used for the polar option"""
      self.__oSnapPointsForPolar.clear() # I empty the dictionary
      del self.__oSnapLinesForPolar[:] # I empty the list

   def getOSnapPointsForPolar(self):
      return self.__oSnapPointsForPolar

   def getOSnapLinesForPolar(self):
      return self.__oSnapLinesForPolar


   # ===========================================================================
   # ReferenceLines
   # ===========================================================================
   def toggleReferenceLines(self, geomEntity, point, oSnapPointsForPolar = None, snapMarkerSizeInMapUnits = None):
      """geomEntity can be a QgsGeometry with canvas coordinates or a QadEntity
            if you pass a QadEntity the snapper uses its cache
            point is in canvas coordinates
      """
      if oSnapPointsForPolar is not None:
         self.__toggleOSnapPointsForPolar(point, oSnapPointsForPolar, snapMarkerSizeInMapUnits)

      # used only for EXT or PAR snaps
      if not(self.__snapType & QadSnapTypeEnum.EXT) and \
         not(self.__snapType & QadSnapTypeEnum.PAR):
         return

      if type(geomEntity) == QgsGeometry: # if it is a QGIS geometry
         qadGeom = fromQgsGeomToQadGeom(geomEntity)
      else: # is an entity of QAD
         # I use QAD's entity cache
         cacheEntity = self.__cacheEntitySet.getEntity(geomEntity.layerId(), geomEntity.featureId)
         if cacheEntity is None:
            cacheEntity = self.__cacheEntitySet.appendEntity(geomEntity) # add it to the cache
         qadGeom = cacheEntity.getQadGeom()

      # the function returns a list with
      # (<minimum distance>
      #  <nearest point>
      #  <nearest geometry index>
      #  <index of the nearest sub-geometry>
      #   if closed geometry is polyline type the list also contains
      #  <index of the closest sub-geometry part>
      #  <"to the left of" if the point is to the left of the part (< 0 -> left, > 0 -> right)
      # )
      result = getQadGeomClosestPart(qadGeom, point)
      g = getQadGeomPartAt(qadGeom, result[2], result[3], result[4])

      geomType = g.whatIs()
      if self.__snapType & QadSnapTypeEnum.EXT:
         self.toggleExtLinearObj(g)
      if self.__snapType & QadSnapTypeEnum.PAR:
         self.toggleParLine(g)


   def removeReferenceLines(self):
      self.removeExtLinearObjs()
      self.removeParLines()
      self.removeIntExtLinearObj()
      self.removeOSnapPointsForPolar()


   # ============================================================================
   # setToleranceExtParLines
   # ============================================================================
   def setToleranceExtParLines(self, tolerance):
      self.__toleranceExtParlines = tolerance


   # ============================================================================
   # tmpGeometries (temporary geometries are in the canvas crs
   # ============================================================================
   def clearTmpGeometries(self):
      del self.tmpGeometries[:] # I empty the list

   def setTmpGeometry(self, geom):
      self.clearTmpGeometries()
      self.appendTmpGeometry(geom)

   def appendTmpGeometry(self, geom):
      if geom is None:
         return
      if type(geom) == QgsGeometry: # if it is a QGIS geometry
         qadGeom = fromQgsGeomToQadGeom(geom)
         self.tmpGeometries.append(qadGeom)
      else: # is a geometry of QAD
         self.tmpGeometries.append(geom)


   def setTmpGeometries(self, geoms, CRS = None):
      self.clearTmpGeometries()
      for g in geoms:
         self.appendTmpGeometry(g, CRS)


   # ===========================================================================
   # getSnapPoint
   # ===========================================================================
   def getSnapPoint(self, geomEntity, point, excludePoints = None, \
                    polarAng = None, polarAngOffset = None, polarAddAngles = None, isTemporaryGeom = False):
      """Given a geometry (QgsGeometry) or a qad entity (QadEntity) and a point (cursor position) in the map canvas coordinate system
            gets snap points (excluding points in excludePoints).
            Returns a dictionary of snap point lists
            divided by snap types (e.g. {END : [pt1 .. ptn] MID : [pt1 .. ptn]})
            - excludePoints = list of points to exclude expressed in __snapPointCRS
            - polarAng angle in radians for polar pointing
            - polarAngOffset angle in radians relative to the last segment
            - polarAddAngles list of angles (in radians) in addition to polarAng
            - isTemporaryGeom flag indicating whether geom is a temporary object that does not yet exist
      """
      g = None
      gPart = None

      if geomEntity is not None:
         cacheEntity = None
         qadGeom = None
         if type(geomEntity) == QgsGeometry: # if it is a QGIS geometry
            qadGeom = fromQgsGeomToQadGeom(geomEntity)
         else: # is an entity of QAD
            # the geometry must be in a snapping-enabled layer
            if geomEntity.layer in self.__snapLayers:
               # I use QAD's entity cache
               cacheEntity = self.__cacheEntitySet.getEntity(geomEntity.layerId(), geomEntity.featureId)
               if cacheEntity is None:
                  cacheEntity = self.__cacheEntitySet.appendEntity(geomEntity) # add it to the cache
               qadGeom = cacheEntity.getQadGeom()

         if qadGeom is not None:
            # the function returns a list with
            # (<minimum distance>
            #  <nearest point>
            #  <nearest geometry index>
            #  <index of the nearest sub-geometry>
            #   if closed geometry is polyline type the list also contains
            #  <index of the closest sub-geometry part>
            #  <"to the left of" if the point is to the left of the part (< 0 -> left, > 0 -> right)
            # )
            result = getQadGeomClosestPart(qadGeom, point)
            atGeom = result[2]
            atSubGeom = result[3]
            g = getQadGeomAt(qadGeom, atGeom, atSubGeom)
            if self.__snapMode == QadSnapModeEnum.ONE_RESULT:
               gPart = getQadGeomPartAt(qadGeom, atGeom, atSubGeom, result[4])

            # snap statici
            staticSnapPoints = self.getStaticSnapPoints(g, gPart, isTemporaryGeom)
         else:
            staticSnapPoints = dict()
      else:
         staticSnapPoints = dict()

      # snap dinamici
      dynamicSnapPoints = self.getDynamicSnapPoints(g, gPart, point)

      allSnapPoints = staticSnapPoints
      for item in dynamicSnapPoints.items():
         allSnapPoints[item[0]] = item[1]

      # polar tracking or angles added to polarAng
      if polarAng is not None or polarAddAngles is not None:
         # for all osnap points selected for the polar option and for the current point
         allSnapPoints[QadSnapTypeEnum.POLAR] = self.getOsnapPtAndLinesForPolar(point, polarAng, polarAngOffset, polarAddAngles)
         # calculate the intersections of the polar lines and add them to allSnapPoints[QadSnapTypeEnum.INT]
         intPts = self.getIntPtsBetweenOSnapLinesForPolar()
         if len(intPts) > 0:
            if QadSnapTypeEnum.INT in allSnapPoints:
               for intPt in intPts:
                  self.__appendUniquePoint(allSnapPoints[QadSnapTypeEnum.INT], point) # without duplication
            else:
               allSnapPoints[QadSnapTypeEnum.INT] = intPts

      if self.__snapMode == QadSnapModeEnum.ONE_RESULT:
         # Only the closest point is returned
         result = self.getNearestPoints(point, allSnapPoints)
      elif self.__snapMode == QadSnapModeEnum.ALL_RESULTS:
         result = allSnapPoints # All points are returned

      if excludePoints is not None:
         for p in excludePoints:
            self.__delPoint(p, result)

      return result


   # ============================================================================
   # getStaticSnapPoints
   # ============================================================================
   def getStaticSnapPoints(self, geom, gPart, isTemporaryGeom = False):
      """Given a qad geometry, the geometry of a part of the qad geometry, obtains the static snap points that do not depend on the
            cursor position.
            The part, if existing, is used for points of type: END, MID, INT, APP
            Returns a dictionary of snap point lists
            divided by snap types (e.g. {END : [pt1 .. ptn] MID : [pt1 .. ptn]})
            - isTemporaryGeom flag indicating whether geom is a temporary object that does not yet exist
      """

      result = dict()

      if (self.__snapType & QadSnapTypeEnum.DISABLE) or geom is None:
         return result

      if self.__snapType & QadSnapTypeEnum.END:
         if gPart is None:
            result[QadSnapTypeEnum.END] = self.getEndPoints(geom, QadVertexSearchModeEnum.ALL)
         else:
            result[QadSnapTypeEnum.END] = self.getEndPoints(gPart, QadVertexSearchModeEnum.ALL)

      if self.__snapType & QadSnapTypeEnum.END_PLINE:
         result[QadSnapTypeEnum.END_PLINE] = self.getEndPoints(geom, QadVertexSearchModeEnum.ONLY_START_END)

      if self.__snapType & QadSnapTypeEnum.MID:
         if gPart is None:
            result[QadSnapTypeEnum.MID] = self.getMidPoints(geom)
         else:
            result[QadSnapTypeEnum.MID] = self.getMidPoints(gPart)

      if self.__snapType & QadSnapTypeEnum.NOD:
         result[QadSnapTypeEnum.NOD] = self.getNodPoint(geom)

      if self.__snapType & QadSnapTypeEnum.QUA:
         if gPart is None:
            result[QadSnapTypeEnum.QUA] = self.getQuaPoints(geom)
         else:
            result[QadSnapTypeEnum.QUA] = self.getQuaPoints(gPart)

      if self.__snapType & QadSnapTypeEnum.INT:
         if gPart is None or isTemporaryGeom:
            result[QadSnapTypeEnum.INT] = self.getIntPoints(geom, isTemporaryGeom)
         else:
            result[QadSnapTypeEnum.INT] = self.getIntPoints(gPart, isTemporaryGeom)

      if self.__snapType & QadSnapTypeEnum.INS:
         result[QadSnapTypeEnum.INS] = self.getNodPoint(geom)

      if self.__snapType & QadSnapTypeEnum.APP:
         if gPart is None or isTemporaryGeom:
            result[QadSnapTypeEnum.APP] = self.getIntPoints(geom, isTemporaryGeom)
         else:
            result[QadSnapTypeEnum.APP] = self.getIntPoints(gPart, isTemporaryGeom)

      if self.__snapType & QadSnapTypeEnum.CEN:
         if gPart is None:
            result[QadSnapTypeEnum.CEN] = self.getCenPoint(geom)
         else:
            result[QadSnapTypeEnum.CEN] = self.getCenPoint(gPart)

      return result


   # ============================================================================
   # getDynamicSnapPoints
   # ============================================================================
   def getDynamicSnapPoints(self, geom, gPart, point):
      """Given a qad geometry, the geometry of a part of the qad geometry, obtains the dynamic snap points that depend on the
            cursor position (in the canvas coordinate system) o
            from __startPoint (in the canvas coordinate system).
            The part, if existing, is used for points of type: NEA, MID, INT, APP
            Returns a dictionary of snap point lists
            divided by snap types (e.g. {END : [pt1 .. ptn] MID : [pt1 .. ptn]})
      """

      result = dict()

      if (self.__snapType & QadSnapTypeEnum.DISABLE):
         return result

      if self.__snapType & QadSnapTypeEnum.PER:
         if gPart is None:
            result[QadSnapTypeEnum.PER] = self.getPerPoints(geom)
         else:
            result[QadSnapTypeEnum.PER] = self.getPerPoints(gPart)

      if self.__snapType & QadSnapTypeEnum.TAN:
         if gPart is None:
            result[QadSnapTypeEnum.TAN] = self.getTanPoints(geom)
         else:
            result[QadSnapTypeEnum.TAN] = self.getTanPoints(gPart)

      if self.__snapType & QadSnapTypeEnum.NEA:
         if gPart is None:
            result[QadSnapTypeEnum.NEA] = self.getNeaPoints(geom, point)
         else:
            result[QadSnapTypeEnum.NEA] = self.getNeaPoints(gPart, point)

      if self.__snapType & QadSnapTypeEnum.EXT:
         result[QadSnapTypeEnum.EXT] = self.getExtPoints(point)

      if self.__snapType & QadSnapTypeEnum.PAR:
         result[QadSnapTypeEnum.PAR] = self.getParPoints(point)

      if self.__snapType & QadSnapTypeEnum.PR:
         if geom is not None:
            geomType = geom.whatIs()
         else:
            geomType = "";
         # if the main geometry is multi... I have to consider the selected part
         if geomType == "MULTI_LINEAR_OBJ" or geomType == "MULTI_POLYGON":
            result[QadSnapTypeEnum.PR] = self.getProgressPoint(gPart, point)[0]
         else:
            result[QadSnapTypeEnum.PR] = self.getProgressPoint(geom, point)[0]

      if self.__snapType & QadSnapTypeEnum.EXT_INT:
         result[QadSnapTypeEnum.EXT_INT] = self.getIntExtPoint(geom, point)

      if self.__snapType & QadSnapTypeEnum.PER_DEF:
         if gPart is None:
            result[QadSnapTypeEnum.PER_DEF] = self.getNeaPoints(geom, point)
         else:
            result[QadSnapTypeEnum.PER_DEF] = self.getNeaPoints(gPart, point)

      if self.__snapType & QadSnapTypeEnum.TAN_DEF:
         if gPart is None:
            g = geom
         else:
            g = gPart

         if g is not None:
            # only for curved geometry
            geomType = g.whatIs()
            if geomType == "ARC" or geomType == "CIRCLE" or geomType == "ELLIPSE_ARC" or geomType == "ELLIPSE":
               result[QadSnapTypeEnum.TAN_DEF] = self.getNeaPoints(g, point)

      return result


   # ============================================================================
   # getEndPoints
   # ============================================================================
   def getEndPoints(self, geom, VertexSearchMode = QadVertexSearchModeEnum.ALL):
      """Searces for the start and end points of a qad geometry.
            - VertexSearcMode = end point searc mode
            Returns a list of QgsPointXY points
      """
      result = []

      if geom is None:
         return result

      geomType = geom.whatIs()
      if geomType == "LINE" or geomType == "ARC" or geomType == "ELLIPSE_ARC":
         if VertexSearchMode == QadVertexSearchModeEnum.ONLY_START_END or \
            VertexSearchMode == QadVertexSearchModeEnum.ALL:
            self.__appendUniquePoint(result, geom.getStartPt()) # add without duplication
            self.__appendUniquePoint(result, geom.getEndPt()) # add without duplication
      elif geomType == "POLYLINE":
         if VertexSearchMode == QadVertexSearchModeEnum.ONLY_START_END or \
            VertexSearchMode == QadVertexSearchModeEnum.ALL:
            self.__appendUniquePoint(result, geom.getStartPt()) # add without duplication

         if VertexSearchMode == QadVertexSearchModeEnum.EXCLUDE_START_END or \
            VertexSearchMode == QadVertexSearchModeEnum.ALL:
            i = 1 # second linear object of polyline geometry
            while i < geom.qty():
               linearObject = geom.getLinearObjectAt(i)
               self.__appendUniquePoint(result, linearObject.getStartPt()) # add without duplication
               i = i + 1

         if VertexSearchMode == QadVertexSearchModeEnum.ONLY_START_END or \
            VertexSearchMode == QadVertexSearchModeEnum.ALL:
            self.__appendUniquePoint(result, geom.getEndPt()) # add without duplication

      return result


   # ============================================================================
   # getMidPoints
   # ============================================================================
   def getMidPoints(self, geom):
      """Searces for the midpoints of the segments of a qad geometry.
            Returns a list of QgsPointXY points
      """
      result = []

      if geom is None:
         return result

      geomType = geom.whatIs()
      if geomType == "LINE" or geomType == "ARC" or geomType == "ELLIPSE_ARC":
         self.__appendUniquePoint(result, QgsPointXY(geom.getMiddlePt())) # add without duplication
      elif geomType == "POLYLINE":
         i = 0
         while i < geom.qty():
            linearObject = self.getLinearObjectAt(i)
            self.__appendUniquePoint(result, QgsPointXY(linearObject.getMiddlePt())) # add without duplication
            i = i + 1

      return result


   # ============================================================================
   # getCenPoint
   # ============================================================================
   def getCenPoint(self, geom):
      """Searc for the center points of arcs, circles, ellipse arcs, ellipses present in qad geometry.
            Returns a list of QgsPointXY points
      """
      result = []

      if geom is None:
         return result

      geomType = geom.whatIs()
      if geomType == "ARC" or geomType == "CIRCLE" or geomType == "ELLIPSE" or geomType == "ELLIPSE_ARC":
         self.__appendUniquePoint(result, geom.center) # add without duplication

      elif geomType == "POLYLINE":
         i = 0
         while i < geom.qty():
            linearObject = geom.getLinearObjectAt(i)
            result.extend(self.getCenPoint(linearObject))
            i = i + 1

      return result


   # ============================================================================
   # getNodPoint
   # ============================================================================
   def getNodPoint(self, geom):
      """Find the insertion point of a qad point.
            Returns a list of QgsPointXY points
      """
      result = []

      if geom is None:
         return result

      geomType = geom.whatIs()
      if geomType == "POINT":
         self.__appendUniquePoint(result, QgsPointXY(geom)) # add without duplication
      elif geomType == "MULTI_POINT":
         i = 0
         while i < geom.qty():
            self.__appendUniquePoint(result, self.getPointAt(i)) # add without duplication
            i = i + 1

      return result


   # ============================================================================
   # getQuaPoints
   # ============================================================================
   def getQuaPoints(self, geom):
      """Searc for quadrant points of qad geometry.
            Returns a list of QgsPointXY points
      """
      result = []

      if geom is None:
         return result

      geomType = geom.whatIs()
      if geomType == "ARC" or geomType == "CIRCLE" or geomType == "ELLIPSE" or geomType == "ELLIPSE_ARC":
         points = geom.getQuadrantPoints()
         for point in points:
            if points is not None: # because the arc of the ellipse returns the quadrant points to zero if they are not in the arc
               self.__appendUniquePoint(result, point) # without duplication

      return result


   # ============================================================================
   # getIntPoints
   # ============================================================================
   def getIntPoints(self, geom, isTemporaryGeom = False):
      """Searces for intersection points of a qad geometry with other geometries on __snapLayers layers.
            - isTemporaryGeom flag indicating whether geom is a temporary object that does not yet exist
            Returns a list of QgsPointXY points
      """
      result = []

      if geom is None:
         return result

      geomBoundingBoxCache = QadGeomBoundingBoxCache(geom)
      boundingBox = geomBoundingBoxCache.getTotalBoundingBox()

      for iLayer in self.__snapLayers: # loop over the layers to control
         if (iLayer.type() == QgsMapLayer.VectorLayer):
            iLayerCRS = iLayer.crs()
            coordTransform = QgsCoordinateTransform(self.__snapPointCRS, iLayerCRS, QgsProject.instance()) # trasformo in coord ilayer
            iLayerBoundingBox = coordTransform.transformBoundingBox(boundingBox)

            feature = QgsFeature()
            # I searc for entities that intersect the rectangle
            # fetchAttributes, fetchGeometry, rectangle, useIntersect
            for feature in iLayer.getFeatures(qad_utils.getFeatureRequest([], True, iLayerBoundingBox, True)):
               g2 = fromQgsGeomToQadGeom(feature.geometry(), iLayerCRS) # get a geometry of qad
               if geom.whatIs() == g2.whatIs() and geom.equals(g2): continue # jumps itself

               intersectionPoints = QadIntersections.twoGeomObjects(g2, geom, geomBoundingBoxCache)
               for point in intersectionPoints:
                  self.__appendUniquePoint(result, point) # without duplication

      if isTemporaryGeom:
         intersectionPoints = QadIntersections.twoGeomObjects(geom, geom, geomBoundingBoxCache)
         for point in intersectionPoints:
            self.__appendUniquePoint(result, point) # without duplication

      # list of geometry not yet existing but to be counted for osnap points (in map coordinates)
      for tmpGeometry in self.tmpGeometries:
         intersectionPoints = QadIntersections.twoGeomObjects(tmpGeometry, geom, geomBoundingBoxCache)
         for point in intersectionPoints:
            self.__appendUniquePoint(result, point) # without duplication

      return result


   # ============================================================================
   # Start of dynamic points
   # ============================================================================


   # ============================================================================
   # getPerPoints
   # ============================================================================
   def getPerPoints(self, geom):
      """Searc for the perpendicular projection point of self.__startPoint
            (expressed in __snapPointCRS) on the side of geom closest to point.
            Returns a list of QgsPointXY points
      """
      result = []

      if geom is None:
         return result

      if self.__startPoint is None:
         return result

      PerpendicularPoints = QadPerpendicularity.fromPointToBasicGeomObjectExtensions(self.__startPoint, geom)
      for PerpendicularPoint in PerpendicularPoints:
         self.__appendUniquePoint(result, PerpendicularPoint) # without duplication

      return result


   # ============================================================================
   # getTanPoints
   # ============================================================================
   def getTanPoints(self, geom):
      """Searces for points on an object that are tangent to the line through self.__startPoint
            (expressed in __snapPointCRS).
            Returns a list of QgsPointXY points
      """
      result = []

      if geom is None:
         return result

      if self.__startPoint is None:
         return result

      result = []
      tangencyPoints = QadTangency.fromPointToBasicGeomObject(self.__startPoint, geom)
      for tangencyPoint in tangencyPoints:
         self.__appendUniquePoint(result, tangencyPoint) # without duplication

      return result


   # ============================================================================
   # getNeaPoints
   # ============================================================================
   def getNeaPoints(self, geom, point):
      """Searces for the point of an object that is closest to point.
            Returns a list of QgsPointXY points
      """
      if geom is None: return []

      # the function returns a list with
      # (<minimum distance>
      #  <nearest point>
      #  <nearest geometry index>
      #  <index of the nearest sub-geometry>
      #   if closed geometry is polyline type the list also contains
      #  <index of the closest sub-geometry part>
      #  <"to the left of" if the point is to the left of the part (< 0 -> left, > 0 -> right)
      # )
      result = getQadGeomClosestPart(geom, point)
      closestPoint = result[1]
      result = []
      self.__appendUniquePoint(result, closestPoint) # without duplication

      return result


   # ============================================================================
   # toggleExtLinearObj
   # ============================================================================
   def toggleExtLinearObj(self, linearObj):
      """Adds a linear object (QadLine or QadArc or QadEllipseArc) for finding points with EXT (extension) mode
            if not yet added to the list otherwise remove it from the list
      """
      geomType = linearObj.whatIs()
      if geomType == "ARC" or geomType == "ELLIPSE_ARC" or geomType == "LINE":
         # check that it is not already there
         i = 0
         for iObj in self.__extLinearObjs:
            if geomType == iObj.whatIs():
               if geomType == "LINE":
                  if linearObj.equals(iObj): # geometrically equal (the direction does NOT count)
                     # if it already exists I remove it
                     del self.__extLinearObjs[i]
                     return
               elif linearObj == iObj:
                  # if it already exists I remove it
                  del self.__extLinearObjs[i]
                  return
            i = i + 1

         # if it doesn't exist yet I'll add it
         self.__extLinearObjs.append(linearObj)


   def removeExtLinearObjs(self):
      """Delete all linear objects for point searc with EXT (extension) mode"""
      del self.__extLinearObjs[:] # I empty the list

   def getExtLinearObjs(self):
      return self.__extLinearObjs


   def getExtPoints(self, point):
      """Searces for points on line extensions stored in the __extLinearObjs list.
            - point is a QgsPointXY
            Returns a list of QgsPointXY points
      """
      result = []

      for g in self.__extLinearObjs:
         ExtPoints = QadPerpendicularity.fromPointToBasicGeomObjectExtensions(point, g)
         for ExtPoint in ExtPoints:
            if qad_utils.getDistance(point, ExtPoint) <= self.__toleranceExtParlines:
               self.__appendUniquePoint(result, ExtPoint) # without duplication

      return result


   # ============================================================================
   # getParPoints
   # ============================================================================
   def toggleParLine(self, line):
      """Adds a line for finding points with PAR (parallel) mode
            if not yet added to the list otherwise remove it from the list
      """
      """
      Adds a line to search for points with EXT or PAR mode
      if it is not already in the list; otherwise removes it from the list
      """
      if line.whatIs() != "LINE": return

      # check that it is not already there
      i = 0
      for iObj in self.__parLines:
         if line.equals(iObj): # geometrically equal (the direction does NOT count)
            # if it already exists I remove it
            del self.__parLines[i]
            return
         i = i + 1

      # if it doesn't exist yet I'll add it
      self.__parLines.append(line)


   def removeParLines(self):
      """Delete all lines for point searc with PAR (parallel) mode"""
      del self.__parLines[:] # I empty the list

   def getParLines(self):
      return self.__parLines


   def getParPoints(self, point):
      """Searces for points on lines parallel to the lines stored in the __partLines list
            which pass through __startPoint and which are closest to point.
            N.B. __parLines, __startPoint and point must be expressed in the same coordinate system
            - line is a list of 2 points
            - point is a QgsPointXY
            Returns a list of QgsPointXY points
      """
      result = []

      if (self.__startPoint is None) or len(self.__parLines) == 0:
         return result

      p2 = QgsPointXY()

      for line in self.__parLines:
         pt1 = line.getStartPt()
         pt2 = line.getEndPt()
         diffX = pt2.x() - pt1.x()
         diffY = pt2.y() - pt1.y()

         if diffX == 0: # if the straight line passing through pt1 and pt2 is vertical
            parPoint = QgsPointXY(self.__startPoint.x(), point.y())
         elif diffY == 0: # if the straight line passing through pt1 and pt2 is horizontal
            parPoint = QgsPointXY(point.x(), self.__startPoint.y())
         else:
            # Calculate the equation of the straight line passing through __startPoint with known angular coefficient
            p2.setX(self.__startPoint.x() + diffX)
            p2.setY(self.__startPoint.y() + diffY)
            parPoint = qad_utils.getPerpendicularPointOnInfinityLine(self.__startPoint, p2, point)

         if qad_utils.getDistance(point, parPoint) <= self.__toleranceExtParlines:
            self.__appendUniquePoint(result, parPoint) # without duplication

      return result


   # ============================================================================
   # getProgressPoint
   # ============================================================================
   def setProgressDistance(self, progressDistance):
      """Sets the progressive distance from the start in the __snapPointCRS system
            for searcing with PR (progressive) mode
      """
      self.__progressDistance = progressDistance


   def getProgressDistance(self,):
      return self.__progressDistance


   def getProgressPoint(self, geom, point):
      """Searces for the point on the geometry a certain distance from the vertex closest to the point
            (if the distance >=0 means towards from the beginning to the end of the line,
            if the distance < 0 it means towards from the end to the beginning of the line.
            Returns a list of QgsPointXY points + a list of segment angular coefficients
            on which the points fall
      """
      result = [[],[]]
      if geom is None:
         return result

      geomType = geom.whatIs()
      if geomType != "LINE" and geomType != "ARC" and geomType != "ELLIPSE_ARC" and geomType != "POLYLINE":
         return result

      g = geom.copy()
      ProgressPoints = []
      segmentAngles = []

      if self.__progressDistance < 0:
         g.reverse()
         progressDistance = -self.__progressDistance
      else:
         progressDistance = self.__progressDistance

      # the function returns a list with
      # (<minimum distance>
      # <nearest vertex point>
      # <nearest geometry index>
      # <index of the nearest sub-geometry>
      # <index of the closest sub-geometry part>
      # <nearest vertex index>
      result = getQadGeomClosestVertex(g, point)
      iVertex = result[5]

      lengthFromStart = 0
      if geomType == "POLYLINE":
         # calculate the distance of the vertex from the beginning of the geometry
         for i in range(0, iVertex, 1):
            lengthFromStart = lengthFromStart + g.getLinearObjectAt(i).length()

         delta = (lengthFromStart + progressDistance) - g.length()
         # the function moves the end point by a distance delta by lengthening (if delta > 0) or shortening (if delta < 0) the polyline
         if g.lengthen_delta(False, delta) == True:
            linearObject = g.getLinearObjectAt(-1) # last linear object
            ProgressPoints.append(QgsPointXY(linearObject.getEndPt()))
            if self.__progressDistance < 0:
               linearObject.reverse()
               segmentAngles.append(linearObject.getTanDirectionOnStartPt())
            else:
               segmentAngles.append(linearObject.getTanDirectionOnEndPt())
      else:
         # calculate the distance of the vertex from the beginning of the geometry
         if iVertex == 1: # final point
            lengthFromStart = g.length()
         delta = (lengthFromStart + progressDistance) - g.length()

         # the function moves the end point by a distance delta by lengthening (if delta > 0) or shortening (if delta < 0) the polyline
         if g.lengthen_delta(False, delta) == True:
            ProgressPoints.append(QgsPointXY(g.getEndPt()))
            if self.__progressDistance < 0:
               g.reverse()
               segmentAngles.append(g.getTanDirectionOnStartPt())
            else:
               segmentAngles.append(g.getTanDirectionOnEndPt())

      return (ProgressPoints, segmentAngles)


   # ============================================================================
   # toggleIntExtLinearObj
   # ============================================================================
   def toggleIntExtLinearObj(self, geomEntity, point):
      """Adds a linear object (QadLine or QadArc or QadEllipseArc) for finding points with EXT_INT mode (intersection over extension)
            if not yet inserted otherwise remove it from the list
      """
      # used only for EXT_INT snaps
      if not (self.__snapType & QadSnapTypeEnum.EXT_INT):
         return

      if type(geomEntity) == QgsGeometry: # if it is a QGIS geometry
         qadGeom = fromQgsGeomToQadGeom(geomEntity)
      else: # is an entity of QAD
         # I use QAD's entity cache
         cacheEntity = self.__cacheEntitySet.getEntity(geomEntity.layerId(), geomEntity.featureId)
         if cacheEntity is None:
            cacheEntity = self.__cacheEntitySet.appendEntity(geomEntity) # add it to the cache
         qadGeom = cacheEntity.getQadGeom()

      # the function returns a list with
      # (<minimum distance>
      #  <nearest point>
      #  <nearest geometry index>
      #  <index of the nearest sub-geometry>
      #   if the sub-geometry is polyline type the list also contains
      #  <index of the closest sub-geometry part>
      #  <"to the left of" if the point is to the left of the part (< 0 -> left, > 0 -> right)
      # )
      geomType = qadGeom.whatIs()
      result = getQadGeomClosestPart(qadGeom, point)
      if len(result) > 4: # if the function returns the part number
         linearObj = getQadGeomPartAt(qadGeom, result[2], result[3], result[4])
         geomType = linearObj.whatIs()
      else:
         linearObj = geom

      if geomType != "LINE" and geomType != "ARC" and geomType != "ELLIPSE_ARC": return

      # if no linear object has been selected add it
      if len(self.__intExtLinearObjs) == 0:
         self.__intExtLinearObjs.append(linearObj.copy())
      else:
         if geomType == self.__intExtLinearObjs[0].whatIs():
            if geomType == "LINE":
               if linearObj.equals(self.__intExtLinearObjs[0]): # geometrically equal (the direction does NOT count)
                  # if it already exists I remove it
                  self.removeIntExtLinearObj()
                  return
            elif linearObj == self.__intExtLinearObjs[0]:
               # if it already exists I remove it
               self.removeIntExtLinearObj()
               return


   def removeIntExtLinearObj(self):
      """Delete the linear object for finding points with EXT_INT mode (intersection over extension)"""
      del self.__intExtLinearObjs[:] # I empty the list


   def getIntExtLinearObjs(self):
      return self.__intExtLinearObjs


   def getIntExtPoint(self, geom, point):
      """Searces for the intersection point between the geometry and a linear object stored in __intExtLinearObjs
            Returns a list of QgsPointXY points
      """
      if geom is None: return []

      # if no linear object has been selected
      if len(self.__intExtLinearObjs) == 0: return []

      # the function returns a list with
      # (<minimum distance>
      #  <nearest point>
      #  <nearest geometry index>
      #  <index of the nearest sub-geometry>
      #   if closed geometry is polyline type the list also contains
      #  <index of the closest sub-geometry part>
      #  <"to the left of" if the point is to the left of the part (< 0 -> left, > 0 -> right)
      # )
      result = getQadGeomClosestPart(geom, point)
      g = getQadGeomPartAt(geom, result[2], result[3], result[4])

      intExtPoints = QadIntersections.twoBasicGeomObjectExtensions(g, self.__intExtLinearObjs[0])

      result = []
      for intExtPoint in intExtPoints:
         self.__appendUniquePoint(result, intExtPoint) # without duplication

      return result


   # ============================================================================
   # utiliy functions
   # ============================================================================
   def __appendUniquePoint(self, pointList, point):
      """Adds a point to the list checking that it is not already present.
            Returns True if the insertion occurred, False if the point was already there.
      """
      # It is assumed that the list is sorted, the insertion will take place maintaining the ordering
      lo = 0
      hi = len(pointList)
      while lo < hi:
         mid = (lo + hi) // 2 # digits after the decimal point are removed

         if self.__comparePts(pointList[mid], point) == -1: lo = mid+1
         else: hi = mid

      if lo != len(pointList) and self.__comparePts(pointList[lo], point) == 0: # the point was already there
         return False
      pointList.insert(lo, point)
      return True

      #return qad_utils.appendUniquePointToList(pointList, _point)


   # ============================================================================
   # __comparePts
   # ============================================================================
   def __comparePts(self, p1, p2):
      # compares 2 points, returns 0 if they are equal, -1 if the first < than the second, 1 if the first > than the second
      if p1.x() > p2.x(): return 1
      if p1.x() < p2.x(): return -1
      # the x's are equal so check the y's
      if p1.y() > p2.y(): return 1
      if p1.y() < p2.y(): return -1
      return 0 # numeri uguali


   # ============================================================================
   # getNearestPoints
   # ============================================================================
   def getNearestPoints(self, point, SnapPoints, tolerance = 0):
      """It returns a list with the first element being the snap type e
            the second element is the point closest to point.
            SnapPoints is a dictionary of snap point lists
            divided by snap types (e.g. {END : [pt1 .. ptn] MID : [pt1 .. ptn]})
      """
      result = dict()
      minDist = sys.float_info.max

      if tolerance == 0: # only the closest point
         for item in SnapPoints.items():
            # I exclude NEA and POLAR which I will discuss later
            if (item[0] != QadSnapTypeEnum.NEA and item[0] != QadSnapTypeEnum.POLAR) and (item[1] is not None):
               for pt in item[1]:
                  dist = qad_utils.getDistance(point, pt)
                  if dist < minDist:
                     minDist = dist
                     snapType = item[0]
                     NearestPoint = pt

         # if the found point is further away than <__distToExcludeNea> then I also consider
         # any NEA points
         if minDist > self.__distToExcludeNea:
            # if the NEA type snap has been selected
            if QadSnapTypeEnum.NEA in SnapPoints.keys():
               items = SnapPoints[QadSnapTypeEnum.NEA]
               if (items is not None):
                  for pt in items:
                     dist = qad_utils.getDistance(point, pt)
                     if dist < minDist:
                        minDist = dist
                        snapType = QadSnapTypeEnum.NEA
                        NearestPoint = pt

         # if the found point is further away than <__distToExcludeNea> then I also consider
         # any POLAR points
         if minDist > self.__distToExcludeNea:
            # if the POLAR type snap has been selected
            if QadSnapTypeEnum.POLAR in SnapPoints.keys():
               items = SnapPoints[QadSnapTypeEnum.POLAR]
               if (items is not None):
                  for pt in items:
                     dist = qad_utils.getDistance(point, pt)
                     if dist < minDist:
                        minDist = dist
                        snapType = QadSnapTypeEnum.POLAR
                        NearestPoint = pt

         if minDist != sys.float_info.max: # trovato
            result[snapType] = [NearestPoint]

      else:
         nearest = self.getNearestPoints(point, SnapPoints) # closest point
         dummy = nearest.items()
         dummy = dummy[0]
         NearestPoint = dummy[1]

         for item in SnapPoints.items():
            NearestPoints = []
            for pt in item[1]:
               dist = qad_utils.getDistance(NearestPoint, pt)
               if dist <= tolerance:
                  NearestPoints.append(pt)

            if len(NearestPoints) > 0:
               snapType = item[0]
               result[snapType] = NearestPoint

      return result


   def __delPoint(self, point, SnapPoints):
      """Delete the point from the SnapPoints list (if it exists)
            SnapPoints is a dictionary of snap point lists
            divided by snap types (e.g. {END : [pt1 .. ptn] MID : [pt1 .. ptn]})
      """
      for item in SnapPoints.items():
         i = 0
         for pt in item[1]:
            if pt == point:
               del item[1][i]
            i = i + 1


   # ============================================================================
   # getPolarCoord
   # ============================================================================
   def getPolarCoord(self, startPoint, point, polarAng, polarAngOffset, polarAddAngles):
      result = []

      angle = qad_utils.getAngleBy2Pts(startPoint, point)
      offsetAngle = angle - polarAngOffset
      value = math.modf(offsetAngle / polarAng) # returns a list -> (<decimal part> <integer part>)
      if value[0] >= 0.5: # prendo intervallo successivo
         offsetAngle = (value[1] + 1) * polarAng
      else:
         offsetAngle = value[1] * polarAng
      offsetAngle  = offsetAngle + polarAngOffset

      dist = qad_utils.getDistance(startPoint, point)
      pt2 = qad_utils.getPolarPointByPtAngle(startPoint, offsetAngle, dist)

      polarPt = qad_utils.getPerpendicularPointOnInfinityLine(startPoint, pt2, point)
      if qad_utils.getDistance(polarPt, point) <= self.__toleranceExtParlines:
         self.__appendUniquePoint(result, polarPt) # without duplication

      if polarAddAngles is not None and len(polarAddAngles) > 0:
         for polarAddAngle in polarAddAngles:
            polarPt = qad_utils.getPolarPointByPtAngle(startPoint, polarAddAngle + polarAngOffset, dist)
            if qad_utils.getDistance(polarPt, point) <= self.__toleranceExtParlines:
               self.__appendUniquePoint(result, polarPt) # without duplication

      return result


# ============================================================================
# generic functions
# ============================================================================


# ===============================================================================
# str2snapTypeEnum
# ===============================================================================
def str2snapTypeEnum(s):
   """Returns the conversion of a string to a combination of snap types
      or -1 if there are no snaps indicated.
   """
   snapType = QadSnapTypeEnum.NONE
   snapTypeStrList = s.strip().split(",")
   for snapTypeStr in snapTypeStrList:
      snapTypeStr = snapTypeStr.strip().upper()

      # "NES" no snap
      if snapTypeStr == QadMsg.translate("Snap", "NONE") or snapTypeStr == "_NONE":
         return QadSnapTypeEnum.NONE
      # "FIN" end points of each segment
      elif snapTypeStr == QadMsg.translate("Snap", "END") or snapTypeStr == "_END":
         snapType = snapType | QadSnapTypeEnum.END
      # "FIN_PL" end points of the entire polyline
      elif snapTypeStr == QadMsg.translate("Snap", "END_PL") or snapTypeStr == "_END_PL":
         snapType = snapType | QadSnapTypeEnum.END_PLINE
      # "MED" midpoint
      elif snapTypeStr == QadMsg.translate("Snap", "MID") or snapTypeStr == "_MID":
         snapType = snapType | QadSnapTypeEnum.MID
      # "CEN" center (centroid)
      elif snapTypeStr == QadMsg.translate("Snap", "CEN") or snapTypeStr == "_CEN":
         snapType = snapType | QadSnapTypeEnum.CEN
      # "NOD" point object
      elif snapTypeStr == QadMsg.translate("Snap", "NOD") or snapTypeStr == "_NOD":
         snapType = snapType | QadSnapTypeEnum.NOD
      # "HERE" quadrant point
      elif snapTypeStr == QadMsg.translate("Snap", "QUA") or snapTypeStr == "_QUA":
         snapType = snapType | QadSnapTypeEnum.QUA
      # "INT" intersection
      elif snapTypeStr == QadMsg.translate("Snap", "INT") or snapTypeStr == "_INT":
         snapType = snapType | QadSnapTypeEnum.INT
      # "INS" insertion point
      elif snapTypeStr == QadMsg.translate("Snap", "INS") or snapTypeStr == "_INS":
         snapType = snapType | QadSnapTypeEnum.INS
      # "PER" perpendicular point
      elif snapTypeStr == QadMsg.translate("Snap", "PER") or snapTypeStr == "_PER":
         snapType = snapType | QadSnapTypeEnum.PER
      # "TAN" tangent
      elif snapTypeStr == QadMsg.translate("Snap", "TAN") or snapTypeStr == "_TAN":
         snapType = snapType | QadSnapTypeEnum.TAN
      # "VIC" closest point
      elif snapTypeStr == QadMsg.translate("Snap", "NEA") or snapTypeStr == "_NEA":
         snapType = snapType | QadSnapTypeEnum.NEA
      # "APP" apparent intersection
      elif snapTypeStr == QadMsg.translate("Snap", "APP") or snapTypeStr == "_APP":
         snapType = snapType | QadSnapTypeEnum.APP
      # "EST" Estensione
      elif snapTypeStr == QadMsg.translate("Snap", "EXT") or snapTypeStr == "_EXT":
         snapType = snapType | QadSnapTypeEnum.EXT
      # "PAR" Parallelo
      elif snapTypeStr == QadMsg.translate("Snap", "PAR") or snapTypeStr == "_PAR":
         snapType = snapType | QadSnapTypeEnum.PAR
      # if it starts for "PR" progressive distance
      elif snapTypeStr.find(QadMsg.translate("Snap", "PR")) == 0 or \
           snapTypeStr.find("_PR") == 0:
         # the next PR part can be blank or numeric
         if snapTypeStr.find(QadMsg.translate("Snap", "PR")) == 0:
            param = snapTypeStr[len(QadMsg.translate("Snap", "PR")):]
         else:
            param = snapTypeStr[len("_PR"):]
         if len(param) == 0 or qad_utils.str2float(param) is not None:
            snapType = snapType | QadSnapTypeEnum.PR
      # "EST_INT" intersection on extension
      elif snapTypeStr == QadMsg.translate("Snap", "EXT_INT") or snapTypeStr == "_EXT_INT":
         snapType = snapType | QadSnapTypeEnum.EXT_INT

   return snapType if snapType != QadSnapTypeEnum.NONE else -1


# ===============================================================================
# snapTypeEnum2Str
# ===============================================================================
def snapTypeEnum2Str(snapType):
   """Returns the conversion of a snap type to a string."""
   # "FIN" end points of each segment
   if snapType == QadSnapTypeEnum.END:
      return QadMsg.translate("Snap", "END")
   # "FIN_PL" end points of the entire polyline
   elif snapType == QadSnapTypeEnum.END_PLINE:
      return QadMsg.translate("Snap", "END_PL")
   # "MED" midpoint
   elif snapType == QadSnapTypeEnum.MID:
      return QadMsg.translate("Snap", "MID")
   # "CEN" center (centroid)
   elif snapType == QadSnapTypeEnum.CEN:
      return QadMsg.translate("Snap", "CEN")
   # "NOD" point object
   elif snapType == QadSnapTypeEnum.NOD:
      return QadMsg.translate("Snap", "NOD")
   # "HERE" quadrant point
   elif snapType == QadSnapTypeEnum.QUA:
      return QadMsg.translate("Snap", "QUA")
   # "INT" intersection
   elif snapType == QadSnapTypeEnum.INT:
      return QadMsg.translate("Snap", "INT")
   # "INS" insertion point
   elif snapType == QadSnapTypeEnum.INS:
      return QadMsg.translate("Snap", "INS")
   # "PER" perpendicular point
   elif snapType == QadSnapTypeEnum.PER:
      return QadMsg.translate("Snap", "PER")
   # "TAN" tangent
   elif snapType == QadSnapTypeEnum.TAN:
      return QadMsg.translate("Snap", "TAN")
   # "VIC" closest point
   elif snapType == QadSnapTypeEnum.NEA:
      return QadMsg.translate("Snap", "NEA")
   # "APP" apparent intersection
   elif snapType == QadSnapTypeEnum.APP:
      return QadMsg.translate("Snap", "APP")
   # "EST" Estensione
   elif snapType == QadSnapTypeEnum.EXT:
      return QadMsg.translate("Snap", "EXT")
   # "PAR" Parallelo
   elif snapType == QadSnapTypeEnum.PAR:
      return QadMsg.translate("Snap", "PAR")
   # "PR" progressive distance
   elif snapType == QadSnapTypeEnum.PR:
      return QadMsg.translate("Snap", "PR")
   # "EST_INT" intersection on extension
   elif snapType == QadSnapTypeEnum.EXT_INT:
      return QadMsg.translate("Snap", "EXT_INT")

   return ""


# ===============================================================================
# snapTypeEnum2Descr
# ===============================================================================
def snapTypeEnum2Descr(snapType):
   """Returns the conversion of a snap type to a descriptive string."""
   # "FIN" end points of each segment
   if snapType == QadSnapTypeEnum.END:
      return QadMsg.translate("Snap", "Segment end point")
   # "FIN_PL" end points of the entire polyline
   elif snapType == QadSnapTypeEnum.END_PLINE:
      return QadMsg.translate("Snap", "Polyline end point")
   # "MED" midpoint
   elif snapType == QadSnapTypeEnum.MID:
      return QadMsg.translate("Snap", "Middle point")
   # "CEN" center (centroid)
   elif snapType == QadSnapTypeEnum.CEN:
      return QadMsg.translate("Snap", "Center point")
   # "NOD" point object
   elif snapType == QadSnapTypeEnum.NOD:
      return QadMsg.translate("Snap", "Node")
   # "HERE" quadrant point
   elif snapType == QadSnapTypeEnum.QUA:
      return QadMsg.translate("Snap", "Quadrant")
   # "INT" intersection
   elif snapType == QadSnapTypeEnum.INT:
      return QadMsg.translate("Snap", "Intersection")
   # "INS" insertion point
   elif snapType == QadSnapTypeEnum.INS:
      return QadMsg.translate("Snap", "Insertion point")
   # "PER" perpendicular point
   elif snapType == QadSnapTypeEnum.PER:
      return QadMsg.translate("Snap", "Perpendicular")
   # "TAN" tangent
   elif snapType == QadSnapTypeEnum.TAN:
      return QadMsg.translate("Snap", "Tangent")
   # "VIC" closest point
   elif snapType == QadSnapTypeEnum.NEA:
      return QadMsg.translate("Snap", "Near")
   # "APP" apparent intersection
   elif snapType == QadSnapTypeEnum.APP:
      return QadMsg.translate("Snap", "Apparent intersection")
   # "EST" Estensione
   elif snapType == QadSnapTypeEnum.EXT:
      return QadMsg.translate("Snap", "Extension")
   # "PAR" Parallelo
   elif snapType == QadSnapTypeEnum.PAR:
      return QadMsg.translate("Snap", "Parallel")
   # "PR" progressive distance
   elif snapType == QadSnapTypeEnum.PR:
      return QadMsg.translate("Snap", "Progressive distance")
   # "EST_INT" intersection on extension
   elif snapType == QadSnapTypeEnum.EXT_INT:
      return QadMsg.translate("Snap", "Intersection on extension")

   return ""


# ===============================================================================
# str2snapParam
# ===============================================================================
def str2snapParams(s):
   """Returns the conversion of a string into a list of parameters for snap types"""
   params = []
   snapTypeStrList = s.strip().split(",")
   for snapTypeStr in snapTypeStrList:
      snapTypeStr = snapTypeStr.strip().upper()
      # if it starts for "PR" progressive distance
      if snapTypeStr.find(QadMsg.translate("Snap", "PR")) == 0 or \
         snapTypeStr.find("_PR") == 0:
         # the next PR part can be blank or numeric
         if snapTypeStr.find(QadMsg.translate("Snap", "PR")) == 0:
            param = qad_utils.str2float(snapTypeStr[len(QadMsg.translate("Snap", "PR")):]) # to the end of the string
         else:
            param = qad_utils.str2float(snapTypeStr[len("_PR"):]) # to the end of the string
         if param is not None:
            params.append([QadSnapTypeEnum.PR, param])

   return params
