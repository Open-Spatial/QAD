# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 PLINE command to draw a line

                              -------------------
        begin                : 2013-07-15
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
from qgis.PyQt.QtGui import QIcon
from qgis.core import QgsWkbTypes, QgsGeometry


from ..qad_getpoint import QadGetPointDrawModeEnum, QadGetPointSelectionModeEnum
from ..qad_line import QadLine
from .qad_line_maptool import Qad_line_maptool, Qad_line_maptool_ModeEnum
from .qad_generic_cmd import QadCommandClass
from ..qad_msg import QadMsg
from ..qad_textwindow import QadInputTypeEnum, QadInputModeEnum
from ..qad_snapper import QadSnapTypeEnum, QadSnapper
from ..qad_geom_relations import *
from .. import qad_layer
from .. import qad_utils
from ..qad_rubberband import createRubberBand
from ..qad_entity import QadEntity
from ..qad_geom_relations import getQadGeomClosestPart


# Class that manages the LINE command
class QadLINECommandClass(QadCommandClass):

   def instantiateNewCmd(self):
      """instantiates a new command of the same type"""
      return QadLINECommandClass(self.plugIn)

   def getName(self):
      return QadMsg.translate("Command_list", "LINE")

   def getEnglishName(self):
      return "LINE"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runLINECommand)

   def getIcon(self):
      return QIcon(":/plugins/qad/icons/line.svg")

   def getNote(self):
      # set the explanatory notes of the command
      return QadMsg.translate("Command_LINE", "Creates straight line segments.")

   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      self.vertices = []
      self.rubberBand = createRubberBand(self.plugIn.canvas, QgsWkbTypes.LineGeometry)
      self.firstPtTan = None
      self.firstPtPer = None
      self.firstEntity = None
      self.firstQadGeomPart = None
      # if this flag = True the command is used within another command to draw a line
      # which will not be saved on a layer
      self.virtualCmd = False

   def __del__(self):
      QadCommandClass.__del__(self)
      self.rubberBand.hide()
      self.plugIn.canvas.scene().removeItem(self.rubberBand)


   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      if (self.plugIn is not None):
         if self.PointMapTool is None:
            self.PointMapTool = Qad_line_maptool(self.plugIn)
         return self.PointMapTool
      else:
         return None


   def addVertex(self, point):
      self.vertices.append(point)
      self.addPointToRubberBand(point)
      self.plugIn.setLastPointAndSegmentAng(self.vertices[-1])
      self.setTmpGeometriesToMapTool()

   def delLastVertex(self):
      if len(self.vertices) > 0:
         del self.vertices[-1] # last vertex gate
         self.removeLastPointToRubberBand()
         if len(self.vertices) > 0:
            self.plugIn.setLastPointAndSegmentAng(self.vertices[-1])
         self.setTmpGeometriesToMapTool()


   # ============================================================================
   # addPointToRubberBand
   # ============================================================================
   def addPointToRubberBand(self, point, doUpdate = True):
      numberOfVertices = self.rubberBand.numberOfVertices()

      if numberOfVertices == 2:
         # for a bug not yet understood: if the line has only 2 vertices and
         # have the same x or y (horizontal or vertical line)
         # the line is not drawn so I move the x or y a little
         adjustedPoint = qad_utils.getAdjustedRubberBandVertex(self.rubberBand.getPoint(0, 0), point)
         self.rubberBand.addPoint(adjustedPoint, doUpdate)
      else:
         self.rubberBand.addPoint(point, doUpdate)


   # ============================================================================
   # removeLastPointToRubberBand
   # ============================================================================
   def removeLastPointToRubberBand(self):
      self.rubberBand.removeLastPoint()

   def addLinesToLayer(self, layer):
      i = 1
      line = QadLine()
      while i < len(self.vertices):
         line.set(self.vertices[i - 1], self.vertices[i])
         geom = line.asGeom(layer.wkbType())
         if geom is not None:
            qad_layer.addGeomToLayer(self.plugIn, layer, self.mapToLayerCoordinates(layer, geom), None, True, False, \
                                     True if len(self.vertices) == 2 else False)
         i = i + 1

   def capturedGeometries(self, target_wkb_type = None):
      """Return captured LINE segment geometries in map coordinates."""
      geoms = []
      wkb_type = target_wkb_type if target_wkb_type is not None else QgsWkbTypes.LineString
      i = 1
      line = QadLine()
      while i < len(self.vertices):
         line.set(self.vertices[i - 1], self.vertices[i])
         geom = line.asGeom(wkb_type)
         if geom is not None:
            geoms.append(QgsGeometry(geom))
         i = i + 1
      return geoms


   # ============================================================================
   # setTmpGeometriesToMapTool
   # ============================================================================
   def setTmpGeometriesToMapTool(self):
      self.getPointMapTool().clearTmpGeometries()
      i = 1
      while i < len(self.vertices):
         # for snapping add this temporary geometry
         self.getPointMapTool().appendTmpGeometry(QgsGeometry.fromPolylineXY([self.vertices[i - 1], self.vertices[i]]))
         i = i + 1


   def run(self, msgMapTool = False, msg = None):
      if self.plugIn.canvas.mapSettings().destinationCrs().isGeographic():
         self.showMsg(QadMsg.translate("QAD", "\nThe coordinate reference system of the project must be a projected coordinate system.\n"))
         return True # end command

      if self.virtualCmd == False: # if you really want to save the polyline in a layer
         currLayer, errMsg = qad_layer.getCurrLayerEditable(self.plugIn.canvas, QgsWkbTypes.LineGeometry)
         if currLayer is None:
            self.showErr(errMsg)
            return True # end command

      if self.step == 0 and self.hasPendingCaptureSelectionStep():
         self.waitForCaptureSelectionStep()
         self.step = 900
         return False

      if self.step == 900:
         value = self.consumeCaptureSelectionStep(msgMapTool, msg)
         if value is None:
            return True
         if value is False:
            return False
         self.addVertex(value)
         if self.shouldFinishVirtualCapture(len(self.vertices)):
            return True # end command
         if self.hasPendingCaptureSelectionStep():
            self.waitForCaptureSelectionStep()
            return False
         self.getPointMapTool().setSelectionMode(QadGetPointSelectionModeEnum.POINT_SELECTION)
         self.getPointMapTool().firstPt = value
         self.getPointMapTool().setMode(Qad_line_maptool_ModeEnum.FIRST_PT_KNOWN_ASK_FOR_SECOND_PT)
         keyWords = QadMsg.translate("Command_LINE", "Undo")
         englishKeyWords = "Undo"
         prompt = QadMsg.translate("Command_LINE", "Specify next point or [{0}]: ").format(keyWords)
         prompt = self.capturePointPrompt("line_menu", "next_point", prompt)
         keyWords += "_" + englishKeyWords
         self.waitFor(prompt, QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, None, keyWords, QadInputModeEnum.NONE)
         self.step = 1
         return False

      # FIRST POINT REQUEST
      if self.step == 0: # start of command
         # set the map tool
         self.getPointMapTool().setMode(Qad_line_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_FIRST_PT)
         # is preparing to wait for a point or Enter
         self.waitForPoint(self.capturePrompt("first_point", QadMsg.translate("Command_LINE", "Specify first point: ")))
         self.step = 1
         return False

      # =========================================================================
      # RESPONSE TO THE REQUEST POINT OR MAIN MENU
      elif self.step == 1: # after waiting for a point the command restarts
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if while selecting a point
            # Another plugin was activated which deactivated Qad
            # so the command that returns here has been reactivated without the map tool
            # has selected a point
            if self.getPointMapTool().point is None: # the map tool was activated without a dot
               if self.getPointMapTool().rightButton == True: # if used with the right mouse button
                  if self.virtualCmd == False: # if you really want to save in a layer
                     self.addLinesToLayer(currLayer)
                  return True # end command
               else:
                  self.setMapTool(self.getPointMapTool()) # I reactivate the map tool
                  return False

            snapTypeOnSel = self.getPointMapTool().snapTypeOnSelection
            value = self.getPointMapTool().point
            entity = self.getPointMapTool().entity
         else: # the dot comes as a parameter of the function
            value = msg
            snapTypeOnSel = QadSnapTypeEnum.NONE

         if type(value) == unicode:
            if value == QadMsg.translate("Command_LINE", "Undo") or value == "Undo":
               self.delLastVertex() # last vertex gate
               # set the map tool
               if len(self.vertices) == 0:
                  self.getPointMapTool().setMode(Qad_line_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_FIRST_PT)
                  # is preparing to wait for a point or Enter
                  #                        msg, inputType,              default, keyWords, no check
                  self.waitFor(self.capturePrompt("first_point", QadMsg.translate("Command_LINE", "Specify first point: ")), \
                               QadInputTypeEnum.POINT2D, None, "", QadInputModeEnum.NONE)
                  return False
               else:
                  self.getPointMapTool().firstPt = self.vertices[-1]
                  self.getPointMapTool().setMode(Qad_line_maptool_ModeEnum.FIRST_PT_KNOWN_ASK_FOR_SECOND_PT)
            elif value == QadMsg.translate("Command_LINE", "Close") or value == "Close":
               newPt = self.vertices[0]
               self.addVertex(newPt) # add a new vertex
               if self.virtualCmd == False: # if you really want to save in a layer
                  self.addLinesToLayer(currLayer)
               return True # end command
         else:
            if len(self.vertices) == 0: # first point
               if value is None:
                  if self.plugIn.lastPoint is not None:
                     value = self.plugIn.lastPoint
                  else:
                     return True # end command

               # if a point has been selected with the TAN_DEF mode it is a deferred point
               if snapTypeOnSel == QadSnapTypeEnum.TAN_DEF and entity.isInitialized():
                  # if an explicit point was selected
                  if (self.firstPtTan is None) and (self.firstPtPer is None):
                     self.firstPtPer = None
                     self.firstPtTan = value
                     self.firstEntity = QadEntity(entity) # duplicate the entity

                     # the function returns a list with
                     # (<minimum distance>
                     #  <nearest point>
                     #  <nearest geometry index>
                     #  <index of the nearest sub-geometry>
                     #   if closed geometry is polyline type the list also contains
                     #  <index of the closest sub-geometry part>
                     #  <"to the left of" if the point is to the left of the part (< 0 -> left, > 0 -> right)
                     # )
                     result = getQadGeomClosestPart(self.firstEntity.getQadGeom(), self.firstPtTan)
                     self.firstQadGeomPart = getQadGeomPartAt(self.firstEntity.getQadGeom(), result[2], result[3], result[4])

                     # set the map tool
                     self.getPointMapTool().tan1 = self.firstPtTan
                     self.getPointMapTool().entity1 = self.firstEntity
                     self.getPointMapTool().setMode(Qad_line_maptool_ModeEnum.FIRST_TAN_KNOWN_ASK_FOR_SECOND_PT)

                  # if a point had been selected with the TAN_DEF mode
                  elif self.firstPtTan is not None:
                     result = getQadGeomClosestPart(entity.getQadGeom(), value)
                     secondQadGeomPart = getQadGeomPartAt(entity.getQadGeom(), result[2], result[3], result[4])

                     tangent = QadTangency.bestTwoBasicGeomObjects(self.firstQadGeomPart, self.firstPtTan, secondQadGeomPart, value)
                     if tangent is not None:
                        # I take the point closest to valueself.firstEntity
                        if qad_utils.getDistance(tangent.getStartPt(), value) < qad_utils.getDistance(tangent.getEndPt(), value):
                           self.addVertex(tangent.getEndPt()) # add a new vertex
                           self.addVertex(tangent.getStartPt()) # add a new vertex
                           self.getPointMapTool().firstPt = tangent.getStartPt()
                        else:
                           self.addVertex(tangent.getStartPt()) # add a new vertex
                           self.addVertex(tangent.getEndPt()) # add a new vertex
                           self.getPointMapTool().firstPt = tangent.getEndPt()
                        # set the map tool
                        self.getPointMapTool().setMode(Qad_line_maptool_ModeEnum.FIRST_PT_KNOWN_ASK_FOR_SECOND_PT)
                     else:
                        self.showMsg(QadMsg.translate("Command_LINE", "\nNo tangent possible"))

                  # if a point had been selected with the PER_DEF mode
                  elif self.firstPtPer is not None:
                     result = getQadGeomClosestPart(entity.getQadGeom(), value)
                     secondQadGeomPart = getQadGeomPartAt(entity.getQadGeom(), result[2], result[3], result[4])

                     tangent = QadTangPerp.bestTwoBasicGeomObjects(secondQadGeomPart, value, self.firstQadGeomPart, self.firstPtPer)
                     if tangent is not None:
                        # I take the point closest to value
                        if qad_utils.getDistance(tangent.getStartPt(), value) < qad_utils.getDistance(tangent.getEndPt(), value):
                           self.addVertex(tangent.getEndPt()) # add a new vertex
                           self.addVertex(tangent.getStartPt()) # add a new vertex
                           self.getPointMapTool().firstPt = tangent.getStartPt()
                        else:
                           self.addVertex(tangent.getStartPt()) # add a new vertex
                           self.addVertex(tangent.getEndPt()) # add a new vertex
                           self.getPointMapTool().firstPt = tangent.getEndPt()
                        # set the map tool
                        self.getPointMapTool().setMode(Qad_line_maptool_ModeEnum.FIRST_PT_KNOWN_ASK_FOR_SECOND_PT)
                     else:
                        self.showMsg(QadMsg.translate("Command_LINE", "\nNo tangent possible"))

               # if a point has been selected with the PER_DEF mode it is a deferred point
               elif snapTypeOnSel == QadSnapTypeEnum.PER_DEF and entity.isInitialized():
                  # if an explicit point was selected
                  if (self.firstPtTan is None) and (self.firstPtPer is None):
                     self.firstPtTan = None
                     self.firstPtPer = value
                     self.firstEntity = QadEntity(entity) # duplicate the entity

                     # the function returns a list with
                     # (<minimum distance>
                     #  <nearest point>
                     #  <nearest geometry index>
                     #  <index of the nearest sub-geometry>
                     #   if closed geometry is polyline type the list also contains
                     #  <index of the closest sub-geometry part>
                     #  <"to the left of" if the point is to the left of the part (< 0 -> left, > 0 -> right)
                     # )
                     result = getQadGeomClosestPart(self.firstEntity.getQadGeom(), self.firstPtPer)
                     self.firstQadGeomPart = getQadGeomPartAt(self.firstEntity.getQadGeom(), result[2], result[3], result[4])

                     # set the map tool
                     self.getPointMapTool().per1 = self.firstPtPer
                     self.getPointMapTool().entity1 = self.firstEntity
                     self.getPointMapTool().setMode(Qad_line_maptool_ModeEnum.FIRST_PER_KNOWN_ASK_FOR_SECOND_PT)

                  # if a point had been selected with the TAN_DEF mode
                  elif self.firstPtTan is not None:
                     result = getQadGeomClosestPart(entity.getQadGeom(), value)
                     secondQadGeomPart = getQadGeomPartAt(entity.getQadGeom(), result[2], result[3], result[4])

                     tangent = QadTangPerp.bestTwoBasicGeomObjects(self.firstQadGeomPart, self.firstPtTan, secondQadGeomPart, value)
                     if tangent is not None:
                        # I take the point closest to value
                        if qad_utils.getDistance(tangent.getStartPt(), value) < qad_utils.getDistance(tangent.getEndPt(), value):
                           self.addVertex(tangent.getEndPt()) # add a new vertex
                           self.addVertex(tangent.getStartPt()) # add a new vertex
                           self.getPointMapTool().firstPt = tangent.getStartPt()
                        else:
                           self.addVertex(tangent.getStartPt()) # add a new vertex
                           self.addVertex(tangent.getEndPt()) # add a new vertex
                           self.getPointMapTool().firstPt = tangent.getEndPt()
                        # set the map tool
                        self.getPointMapTool().setMode(Qad_line_maptool_ModeEnum.FIRST_PT_KNOWN_ASK_FOR_SECOND_PT)
                     else:
                        self.showMsg(QadMsg.translate("Command_LINE", "\nNo perpendicular possible"))

                  # if a point had been selected with the PER_DEF mode
                  elif self.firstPtPer is not None:
                     result = getQadGeomClosestPart(entity.getQadGeom(), value)
                     secondQadGeomPart = getQadGeomPartAt(entity.getQadGeom(), result[2], result[3], result[4])

                     line = QadPerpPerp.bestTwoBasicGeomObjects(self.firstQadGeomPart, self.firstPtPer, secondQadGeomPart, value)
                     if line is not None:
                        # I take the point closest to value
                        if qad_utils.getDistance(line.getStartPt(), value) < qad_utils.getDistance(line.getEndPt(), value):
                           self.addVertex(line.getEndPt()) # add a new vertex
                           self.addVertex(line.getStartPt()) # add a new vertex
                           self.getPointMapTool().firstPt = line.getStartPt()
                        else:
                           self.addVertex(line.getStartPt()) # add a new vertex
                           self.addVertex(line.getEndPt()) # add a new vertex
                           self.getPointMapTool().firstPt = line.getEndPt()
                        # set the map tool
                        self.getPointMapTool().setMode(Qad_line_maptool_ModeEnum.FIRST_PT_KNOWN_ASK_FOR_SECOND_PT)
                     else:
                        self.showMsg(QadMsg.translate("Command_LINE", "\nNo perpendicular possible"))
               else: # otherwise it is an explicit point
                  # if a point had been selected with the TAN_DEF mode
                  if self.firstPtTan is not None:
                     snapper = QadSnapper()
                     snapper.setSnapLayers(qad_utils.getSnappableVectorLayers(self.plugIn.canvas))
                     snapper.setSnapType(QadSnapTypeEnum.TAN)
                     snapper.setStartPoint(value)
                     oSnapPoints = snapper.getSnapPoint(self.firstEntity, self.firstPtTan)
                     # I store the snap point in point (I take the first valid one)
                     for item in oSnapPoints.items():
                        points = item[1]
                        if points is not None:
                           self.addVertex(points[0]) # add a new vertex
                           self.addVertex(value) # add a new vertex
                           break

                     if len(self.vertices) == 0:
                        self.showMsg(QadMsg.translate("Command_LINE", "\nNo tangent possible"))
                  # if a point had been selected with the PER_DEF mode
                  elif self.firstPtPer is not None:
                     snapper = QadSnapper()
                     snapper.setSnapLayers(qad_utils.getSnappableVectorLayers(self.plugIn.canvas))
                     snapper.setSnapType(QadSnapTypeEnum.PER)
                     snapper.setStartPoint(value)
                     oSnapPoints = snapper.getSnapPoint(self.firstEntity, self.firstPtPer)
                     # I store the snap point in point (I take the first valid one)
                     for item in oSnapPoints.items():
                        points = item[1]
                        if points is not None:
                           self.addVertex(points[0]) # add a new vertex
                           self.addVertex(value) # add a new vertex
                           break

                     if len(self.vertices) == 0:
                        self.showMsg(QadMsg.translate("Command_LINE", "\nNo perpendicular possible"))
                  else:
                     self.addVertex(value) # add a new vertex

                  if len(self.vertices) > 0:
                     if self.shouldFinishVirtualCapture(len(self.vertices)):
                        return True # end command
                     # set the map tool
                     self.getPointMapTool().firstPt = value
                     self.getPointMapTool().setMode(Qad_line_maptool_ModeEnum.FIRST_PT_KNOWN_ASK_FOR_SECOND_PT)
            else: # second point
               if value is None:
                  if self.virtualCmd == False: # if you really want to save in a layer
                     self.addLinesToLayer(currLayer)
                  return True # end command
               # if the first point is explicit
               if len(self.vertices) > 0:
                  self.addVertex(value) # add a new vertex
                  if self.shouldFinishVirtualCapture(len(self.vertices)):
                     return True # end command
                  # set the map tool
                  self.getPointMapTool().firstPt = value
                  self.getPointMapTool().setMode(Qad_line_maptool_ModeEnum.FIRST_PT_KNOWN_ASK_FOR_SECOND_PT)

         if len(self.vertices) > 2:
            keyWords = QadMsg.translate("Command_LINE", "Close") + "/" + \
                       QadMsg.translate("Command_LINE", "Undo")
            englishKeyWords = "Close" + "/" + "Undo"
         else:
            keyWords = QadMsg.translate("Command_LINE", "Undo")
            englishKeyWords = "Undo"
         prompt = QadMsg.translate("Command_LINE", "Specify next point or [{0}]: ").format(keyWords)
         prompt = self.capturePointPrompt("line_menu", "next_point", prompt)

         keyWords += "_" + englishKeyWords
         # is preparing to wait for a point or Enter or a keyword
         # msg, inputType, default, keyWords, no check
         self.waitFor(prompt, \
                      QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                      None, \
                      keyWords, QadInputModeEnum.NONE)

         return False

