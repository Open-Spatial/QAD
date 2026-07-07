# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 functions for joining linear elements

                              -------------------
        begin                : 2019-09-04
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


# Import the PyQt and QGIS libraries
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui  import *
from qgis.core import *
from qgis.gui import *
import qgis.utils


from .qad_msg import QadMsg
from .qad_variables import QadVariables
from .qad_geom_relations import *
from .qad_layer import createMemoryLayer
from .qad_polyline import *


# ============================================================================
# join2polyline
# ============================================================================
def join2polyline(polyline, polylineToJoinTo, toleranceDist = None, mode = 1):
   """the function joins the polyline <polyline> with another polyline <polylineToJoinTo> according to the <mode> mode.
      If successful it returns True otherwise False.
      <polyline> = polyline to join (will be modified)
      <polylineToJoinTo> = polyline to join with
      <toleranceDist> = tolerance distance for 2 points to be considered coincident
      <mode> = Set the merge method (used if toleranceDist > 0):
               1 -> Extend;  Allows you to join selected polylines by extending or cutting
                              the segments at the closest endpoints.
               2 -> Add; Allows you to join selected polylines by adding a segment
                              straight line between the closest endpoints.
               3 -> Both; Allows you to join selected polylines by extending or cutting, if possible.
                    Otherwise, it allows you to join selected polylines by adding
                    a straight segment between the closest endpoints.
   """
   if toleranceDist is None:
      myToleranceDist = QadVariables.get(QadMsg.translate("Environment variables", "TOLERANCE2COINCIDENT"))
   else:
      myToleranceDist = toleranceDist

   # I look for the point closest to the starting point of the polyline
   ptToJoin = polyline.getStartPt()
   isStartPt = True
   minDist = sys.float_info.max
   # I consider the starting point of the polyline to join
   dist = qad_utils.getDistance(ptToJoin, polylineToJoinTo.getStartPt())
   if dist < minDist:
      isStartPtToJoinTo = True
      minDist = dist
   # I consider the final point of the polyline to join
   dist = qad_utils.getDistance(ptToJoin, polylineToJoinTo.getEndPt())
   if dist < minDist:
      isStartPtToJoinTo = False
      minDist = dist

   # I look for the point closest to the final point of the polyline
   ptToJoin = polyline.getEndPt()
   # I consider the starting point of the polyline to join
   dist = qad_utils.getDistance(ptToJoin, polylineToJoinTo.getStartPt())
   if dist < minDist:
      isStartPt = False
      isStartPtToJoinTo = True
      minDist = dist
   # I consider the final point of the polyline to join
   dist = qad_utils.getDistance(ptToJoin, polylineToJoinTo.getEndPt())
   if dist < minDist:
      isStartPt = False
      isStartPtToJoinTo = False
      minDist = dist

   if minDist <= myToleranceDist: # found a point
      # if the starting point of the polyline to be joined is the same as the starting point of the polyline to be joined
      if isStartPt == True and isStartPtToJoinTo == True:
         part1 = polyline.getLinearObjectAt(0).copy()
         part1.reverse()
         part2 = polylineToJoinTo.getLinearObjectAt(0).copy()
         part2.reverse()

         res = joinEndPtsLinearParts(part1, part2, mode)
         if res is not None:
            # delete the first part
            polyline.remove(0)
            res.reverse()
            polyline.insertPolyline(0, res)

            # add the parts of <polylineToJoinTo> except the first one
            i = 1
            tot = polylineToJoinTo.qty()
            while i < tot:
               polyline.insert(0, polylineToJoinTo.getLinearObjectAt(i).copy().reverse())
               i = i + 1
            return True

      # if the starting point of the polyline to be joined is equal to the final point of the polyline to be joined
      elif isStartPt == True and isStartPtToJoinTo == False:
         part1 = polyline.getLinearObjectAt(0).copy()
         part1.reverse()
         part2 = polylineToJoinTo.getLinearObjectAt(-1)

         res = joinEndPtsLinearParts(part1, part2, mode)
         if res is not None:
            # delete the first part
            polyline.remove(0)
            res.reverse()
            polyline.insertPolyline(0, res)

            # add the parts of <polylineToJoinTo> except the last one
            i = polylineToJoinTo.qty() - 2
            while i >= 0:
               polyline.insert(0, polylineToJoinTo.getLinearObjectAt(i))
               i = i - 1
            return True

      # if the final point of the polyline to be joined is equal to the initial point of the polyline to be joined
      elif isStartPt == False and isStartPtToJoinTo == True:
         part1 = polyline.getLinearObjectAt(-1)
         part2 = polylineToJoinTo.getLinearObjectAt(0).copy()
         part2.reverse()

         res = joinEndPtsLinearParts(part1, part2, mode)
         if res is not None:
            # delete the last part
            polyline.remove(-1)
            polyline.appendPolyline(res)

            # add the parts of <polylineToJoinTo> except the first one
            i = 1
            tot = polylineToJoinTo.qty()
            while i < tot:
               polyline.append(polylineToJoinTo.getLinearObjectAt(i))
               i = i + 1
            return True

      # if the final point of the polyline to be joined is the same as the final point of the polyline to be joined
      elif isStartPt == False and isStartPtToJoinTo == False:
         part1 = polyline.getLinearObjectAt(-1)
         part2 = polylineToJoinTo.getLinearObjectAt(-1)

         res = joinEndPtsLinearParts(part1, part2, mode)
         if res is not None:
            # delete the last part
            polyline.remove(-1)
            polyline.appendPolyline(res)

            # add the parts of <polylineToJoinTo> except the last one
            i = polylineToJoinTo.qty() - 2
            while i >= 0:
               polyline.append(polylineToJoinTo.getLinearObjectAt(i).reverse())
               i = i - 1
            return True

   return False


# ===============================================================================
# joinEndPtsLinearParts
# ===============================================================================
def joinEndPtsLinearParts(part1, part2, mode):
   """the function performs the join (union) between 2 basic linear parts considering the final point of part1
      and the starting point of part2.
      The function receives:
      <part1> = first linear part
      <part2> = second part linear part
      <mode> = Set the merge method:
               1 -> Extend;  Allows you to join selected polylines by extending or cutting
                              the segments at the closest endpoints.
               2 -> Add; Allows you to join selected polylines by adding a segment
                              straight line between the closest endpoints.
               3 -> Both; Allows you to join selected polylines by extending or cutting, if possible.
                              Otherwise, it allows you to join selected polylines by adding
                              a straight segment between the closest endpoints.
      The function returns a QadPolyline that includes:
      part1 (possibly modified at the final point) +
      possible segment +
      part2 (possibly modified in the final point)
      or returns None if the union of the parts is not possible
   """
   polyline = QadPolyline()
   endPt1 = part1.getEndPt()
   endPt2 = part2.getEndPt()

   if qad_utils.ptNear(endPt1, endPt2): # the 2 parts are already joined
      polyline.append(part1.copy())
      p = part2.copy()
      p.reverse()
      polyline.append(p)
      return polyline

   if mode == 1: # Extend/Trim
      IntPtList = QadIntersections.twoBasicGeomObjects(part1, part2)
      if len(IntPtList) > 0: # Trim
         polyline.append(part1.copy())
         polyline.getLinearObjectAt(-1).setEndPt(IntPtList[0])
         p = part2.copy()
         p.reverse()
         polyline.append(p)
         polyline.getLinearObjectAt(-1).setStartPt(IntPtList[0])
         return polyline
      else: # extend
         IntPtList = QadIntersections.twoBasicGeomObjectExtensions(part1, part2)
         # I only consider the points beyond the beginning of the parts
         for i in range(len(IntPtList) - 1, -1, -1):
            if part1.getDistanceFromStart(IntPtList[i]) < 0 or \
               part2.getDistanceFromStart(IntPtList[i]) < 0:
               del IntPtList[i]

         if len(IntPtList) > 0:
            IntPt = IntPtList[0]
            polyline.append(part1.copy())
            polyline.getLinearObjectAt(-1).setEndPt(IntPtList[0])
            p = part2.copy()
            p.reverse()
            polyline.append(p)
            polyline.getLinearObjectAt(-1).setStartPt(IntPtList[0])
            return polyline

   if mode == 2 or mode == 3: # Add
      polyline.append(part1.copy())
      polyline.append([endPt1, endPt2])
      p = part2.copy()
      p.reverse()
      polyline.append(p)
      return polyline

   return None


# ============================================================================
# joinFeatureInVectorLayer
# ============================================================================
def joinFeatureInVectorLayer(featureIdToJoin, vectorLayer, tolerance2ApproxCurve, toleranceDist = None, \
                             mode = 2):
   """the function performs the join (union) of a polyline with a group of other polylines.
      MultiLineString geometries are not allowed.
      The layer must be editing (startEditing) and in a transaction (beginEditCommand)
      The function receives:
      <featureIdToJoin> = an ID of the feature to join
      <vectorLayer> = a QgsVectorLayer that must contain the features to merge
                      (the spatial indices of the vector x are used to be faster).
      <toleranceDist> = tolerance distance for 2 points to be considered coincident
      <tolerance2ApproxCurve> = approximation tolerance for curves (used if toleranceDist > 0)
      <mode> = Set the merge method (used if toleranceDist > 0):
               1 -> Extend;  Allows you to join selected polylines by extending or cutting
                              the segments at the closest endpoints.
               2 -> Add; Allows you to join selected polylines by adding a segment
                              straight line between the closest endpoints.
               3 -> Both; Allows you to join selected polylines by extending or cutting, if possible.
                    Otherwise, it allows you to join selected polylines by adding
                    a straight segment between the closest endpoints.
      The function modifies the <vectorLayer> by modifying the feature to be merged and deleting
      those joined with featureIdToJoin . The list of deleted features returns.
   """
   if toleranceDist is None:
      myToleranceDist = QadVariables.get(QadMsg.translate("Environment variables", "TOLERANCE2COINCIDENT"))
   else:
      myToleranceDist = toleranceDist

   featureToJoin = qad_utils.getFeatureById(vectorLayer, featureIdToJoin)
   if featureToJoin is None:
      return []

   g = QgsGeometry(featureToJoin.geometry())
   polyline = QadPolyline()
   polyline.fromPolyline(g.asPolyline())

   polylineToJoinTo = QadPolyline()

   deleteFeatures = []
   feature = QgsFeature()

   # I join using the starting point until I find features to join
   ptToJoin = polyline.getStartPt()
   found = True
   while found == True:
      found = False
      if ptToJoin is None: # test
         fermati = True
      # I searc for features at the starting point using a micro rectangle according to <myToleranceDist>
      selectRect = QgsRectangle(ptToJoin.x() - myToleranceDist, ptToJoin.y() - myToleranceDist, \
                                ptToJoin.x() + myToleranceDist, ptToJoin.y() + myToleranceDist)
      # I look for the point closest to the starting point of the polyline
      minDist = sys.float_info.max
      # fetchAttributes, fetchGeometry, rectangle, useIntersect
      for feature in vectorLayer.getFeatures(qad_utils.getFeatureRequest([], True, selectRect, True)):
         if feature.id() != featureIdToJoin: # I skip the feature to merge
            polylineToJoinTo.fromPolyline(feature.geometry().asPolyline())

            if join2polyline(polyline, polylineToJoinTo, myToleranceDist, mode) == True:
               found = True

               deleteFeatures.append(QgsFeature(feature))
               if vectorLayer.deleteFeature(feature.id()) == False:
                  return []

               ptToJoin = polyline.getStartPt()
               pts = polyline.asPolyline(tolerance2ApproxCurve)
               featureToJoin.setGeometry(QgsGeometry.fromPolylineXY(pts))
               if vectorLayer.updateFeature(featureToJoin) == False:
                  return []
               break

   # I join using the end point until I find features to join
   ptToJoin = polyline.getEndPt()
   found = True
   while found == True:
      found = False
      # I searc for features at the end point using a micro rectangle according to <myToleranceDist>
      selectRect = QgsRectangle(ptToJoin.x() - myToleranceDist, ptToJoin.y() - myToleranceDist, \
                                ptToJoin.x() + myToleranceDist, ptToJoin.y() + myToleranceDist)
      # fetchAttributes, fetchGeometry, rectangle, useIntersect
      for feature in vectorLayer.getFeatures(qad_utils.getFeatureRequest([], True, selectRect, True)):
         if feature.id() != featureIdToJoin: # I skip the feature to merge
            polylineToJoinTo.fromPolyline(feature.geometry().asPolyline())

            if join2polyline(polyline, polylineToJoinTo, myToleranceDist, mode) == True:
               found = True

               deleteFeatures.append(QgsFeature(feature))
               if vectorLayer.deleteFeature(feature.id()) == False:
                  return []

               ptToJoin = polyline.getEndPt()
               pts = polyline.asPolyline(tolerance2ApproxCurve)
               featureToJoin.setGeometry(QgsGeometry.fromPolylineXY(pts))
               if vectorLayer.updateFeature(featureToJoin) == False:
                  return []
               break

   return deleteFeatures


# ============================================================================
# polylineAsQgsFeatureList
# ============================================================================
def polylineAsQgsFeatureList(polyline, polylineMode):
   """the function returns a list of features.
      If polylineMode = True then the list of linear objects will be considered a single polyline
   """
   fList = []
   if polylineMode == False:
      for linearObject in polyline.defList:
        f = QgsFeature()
        f.setGeometry(QgsGeometry.fromPolylineXY(linearObject.asPolyline()))
        fList.append(f)
   else:
      f = QgsFeature()
      f.setGeometry(QgsGeometry.fromPolylineXY(polyline.asPolyline()))
      fList.append(f)

   return fList


# ============================================================================
# appendPolylineToTempQgsVectorLayer
# ============================================================================
def appendPolylineToTempQgsVectorLayer(polyline, vectorLayer, polylineMode, updateExtents = True):
   """the function inserts the linear objects of a polyline into an already created temporary QgsVectorLayer.
      If polylineMode = True then the list of linear objects will be considered a single polyline
      Returns the list of corresponding feature ids or None in case of error
   """
   fList = polylineAsQgsFeatureList(polyline, polylineMode)

   idList = []
   result = True
   if vectorLayer.startEditing() == False:
      return None

   vectorLayer.beginEditCommand("Feature added")

   for f in fList:
      if vectorLayer.addFeature(f):
         idList.append(f.id())
      else:
         result = False
         break

   if result == True:
      vectorLayer.endEditCommand();
      if updateExtents:
         vectorLayer.updateExtents()
      return idList
   else:
      vectorLayer.destroyEditCommand()
      return None


# ============================================================================
# selfJoinPolyline
# ============================================================================
def selfJoinPolyline(polyline):
   """the function is used when the polyline contains linear parts that are not connected to each other like a real polyline.
      Returns a QadPolyline list containing the polylines
      generated by the union of linear objects.
   """
   crs = qgis.utils.iface.mapCanvas().mapSettings().destinationCrs()
   # create a temporary layer in memory
   vectorLayer = createMemoryLayer("QAD_SelfJoinLines", "LineString", crs)
   provider = vectorLayer.dataProvider()

   # I join the parts of the polyline
   # insert the various linear objects into the layer
   idList = appendPolylineToTempQgsVectorLayer(polyline, vectorLayer, False)
   if idList is None:
      return []
   if provider.capabilities() & QgsVectorDataProvider.CreateSpatialIndex:
      provider.createSpatialIndex()

   vectorLayer.beginEditCommand("selfJoin")

   for featureIdToJoin in idList:
      #                         featureIdToJoin, vectorLayer, tolerance2ApproxCurve, tomyToleranceDist
      joinFeatureInVectorLayer(featureIdToJoin, vectorLayer, QadVariables.get(QadMsg.translate("Environment variables", "TOLERANCE2APPROXCURVE")))

   vectorLayer.endEditCommand()
   vectorLayer.commitChanges()

   result = []
   feature = QgsFeature()

   # fetchAttributes, fetchGeometry, rectangle, useIntersect
   for feature in vectorLayer.getFeatures(qad_utils.getFeatureRequest([], True, None, False)):
      polyline = QadPolyline()
      polyline.fromPolyline(feature.geometry().asPolyline())
      result.append(polyline)

   return result
