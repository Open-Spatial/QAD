# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin OK

 PLINE command to draw a polyline

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


# Import the PyQt and QGIS libraries
from qgis.PyQt.QtGui import QIcon
from qgis.core import QgsWkbTypes, QgsGeometry, QgsPointXY


from ..qad_line import QadLine
from ..qad_polyline import QadPolyline
from ..qad_getpoint import QadGetPointDrawModeEnum, QadGetPointSelectionModeEnum
from .qad_pline_maptool import Qad_pline_maptool, Qad_pline_maptool_ModeEnum
from .qad_arc_maptool import Qad_arc_maptool, Qad_arc_maptool_ModeEnum
from ..qad_arc import QadArc
from .qad_generic_cmd import QadCommandClass
from ..qad_msg import QadMsg
from ..qad_textwindow import QadInputTypeEnum, QadInputModeEnum
from .. import qad_utils
from .. import qad_layer
from ..qad_rubberband import createRubberBand
from ..qad_dim import QadDimStyles
from ..qad_multi_geom import getQadGeomAt, fromQgsGeomToQadGeom
from ..qad_geom_relations import getQadGeomClosestPart, getQadGeomBetween2Pts
from ..qad_variables import QadVariables

# Class that manages the PLINE command
class QadPLINECommandClass(QadCommandClass):

   def instantiateNewCmd(self):
      """instantiates a new command of the same type"""
      return QadPLINECommandClass(self.plugIn)

   def getName(self):
      return QadMsg.translate("Command_list", "PLINE")

   def getEnglishName(self):
      return "PLINE"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runPLINECommand)

   def getIcon(self):
      return QIcon(":/plugins/qad/icons/pline.svg")

   def getNote(self):
      # set the explanatory notes of the command
      return QadMsg.translate("Command_PLINE", "Creates a polyline by many methods.\n\nA polyline is a single object that is composed of line,\nand arc segments.")

   def __init__(self, plugIn, asToolForMPolygon = False):
      QadCommandClass.__init__(self, plugIn)
      self.polyline = QadPolyline()
      self.firstVertex = None

      self.asToolForMPolygon = asToolForMPolygon
      if self.asToolForMPolygon:
         self.rubberBand = createRubberBand(self.plugIn.canvas, QgsWkbTypes.PolygonGeometry, False)
      else:
         self.rubberBand = createRubberBand(self.plugIn.canvas, QgsWkbTypes.LineGeometry)

      self.ArcPointMapTool = None
      self.mode = "LINE"
      # if this flag = True the command is used within another command to draw a line
      # which will not be saved on a layer
      self.virtualCmd = False


   def __del__(self):
      QadCommandClass.__del__(self)
      if self.ArcPointMapTool is not None:
         self.ArcPointMapTool.removeItems()
         del self.ArcPointMapTool

      self.rubberBand.hide()
      self.plugIn.canvas.scene().removeItem(self.rubberBand)


   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      if (self.plugIn is not None):
         if self.mode == "ARC":
            if self.ArcPointMapTool is None:
               self.ArcPointMapTool = Qad_arc_maptool(self.plugIn, self.asToolForMPolygon) # if True means it is used to draw a polygon
               if self.virtualCmd == False: # if you really want to save the polyline in a layer
                  currLayer, errMsg = qad_layer.getCurrLayerEditable(self.plugIn.canvas, QgsWkbTypes.LineGeometry)
                  if currLayer is not None:
                     self.ArcPointMapTool.layer = currLayer

            return self.ArcPointMapTool
         else:
            if self.PointMapTool is None:
               self.PointMapTool = Qad_pline_maptool(self.plugIn, self.asToolForMPolygon) # if True means it is used to draw a polygon
            return self.PointMapTool
      else:
         return None


   def setRubberBandColor(self, rubberBandBorderColor, rubberBandFillColor):
      if rubberBandBorderColor is not None:
         self.rubberBand.setBorderColor(rubberBandBorderColor)
      if rubberBandFillColor is not None:
         self.rubberBand.setFillColor(rubberBandFillColor)


   def getLastSegmentAng(self):
      if self.polyline.qty() == 0:
         result = self.plugIn.lastSegmentAng
      else:
         result = self.polyline.getTanDirectionOnEndPt()

      return result


   def getFirstPt(self):
      if self.polyline.qty() == 0:
         return self.firstVertex
      else:
         return self.polyline.getStartPt()


   def getLastPt(self):
      if self.polyline.qty() == 0:
         return self.firstVertex
      else:
         return self.polyline.getEndPt()


   # ============================================================================
   # WaitForArcMenu
   # ============================================================================
   def WaitForArcMenu(self):
      # the CEnter option is translated into Italian as "CEntro" in the "WaitForArcMenu" context
      # the Undo option is translated into Italian as "ANNulla" in the "WaitForArcMenu" context
      keyWords = QadMsg.translate("Command_PLINE", "Angle") + "/" + \
                 QadMsg.translate("Command_PLINE", "CEnter", "WaitForArcMenu") + "/" + \
                 QadMsg.translate("Command_PLINE", "Close") +  "/" + \
                 QadMsg.translate("Command_PLINE", "Direction") + "/" + \
                 QadMsg.translate("Command_PLINE", "Line") + "/" + \
                 QadMsg.translate("Command_PLINE", "Radius") +  "/" + \
                 QadMsg.translate("Command_PLINE", "Second point") + "/" + \
                 QadMsg.translate("Command_PLINE", "Undo", "WaitForArcMenu")
      englishKeyWords = "Angle" + "/" + "CEnter" + "/" + "Close" + "/" + \
                        "Direction" + "/" + "Line" + "/" + "Radius" + "/" + \
                        "Second point"  + "/" + "Undo"

      prompt = QadMsg.translate("Command_PLINE", "Specify the final point of the arc (hold Ctrl to switch direction) or [{0}]: ").format(keyWords)

      self.arcStartPt = self.getLastPt() # last summit
      self.arcTanOnStartPt = self.getLastSegmentAng()

      # The arc segment is tangent to the previous polyline segment
      # I use the map tool for the arc
      self.mode = "ARC"
      self.getPointMapTool().arcStartPt = self.arcStartPt
      self.getPointMapTool().arcTanOnStartPt = self.arcTanOnStartPt
      self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.START_PT_TAN_KNOWN_ASK_FOR_END_PT)
      if self.asToolForMPolygon:
         self.getPointMapTool().endVertex = self.polyline.getStartPt()

      keyWords += "_" + englishKeyWords
      # is preparing to wait for a point or Enter or a keyword
      # msg, inputType, default, keyWords, no check
      self.waitFor(prompt, \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                   None, \
                   keyWords, QadInputModeEnum.NONE)
      self.step = 101
      return

   # ============================================================================
   # WaitForLineMenu
   # ============================================================================
   def WaitForLineMenu(self):
      # the Undo option is translated into Italian as "ANnulla" in the "WaitForLineMenu" context
      if self.polyline.qty() >= 2:
         keyWords = QadMsg.translate("Command_PLINE", "Arc") + "/" + \
                    QadMsg.translate("Command_PLINE", "Close") + "/" + \
                    QadMsg.translate("Command_PLINE", "Length") + "/" + \
                    QadMsg.translate("Command_PLINE", "Undo", "WaitForLineMenu") + "/" + \
                    QadMsg.translate("Command_PLINE", "Trace")
         englishKeyWords = "Arc" + "/" + "Close" + "/" + "Length" + "/" + "Undo"+ "/" + "Trace"
      else:
         keyWords = QadMsg.translate("Command_PLINE", "Arc") + "/" + \
                    QadMsg.translate("Command_PLINE", "Length") + "/" + \
                    QadMsg.translate("Command_PLINE", "Undo", "WaitForLineMenu") + "/" + \
                    QadMsg.translate("Command_PLINE", "Trace")
         englishKeyWords = "Arc" + "/" + "Length"+ "/" + "Undo" + "/" + "Trace"

      prompt = QadMsg.translate("Command_PLINE", "Specify next point or [{0}]: ").format(keyWords)
      prompt = self.capturePointPrompt("pline_menu", "next_point", prompt)

      self.step = 1 # MENU PRINCIPLE

      keyWords += "_" + englishKeyWords
      # is preparing to wait for a point or Enter or a keyword
      # msg, inputType, default, keyWords, no check
      self.waitFor(prompt, \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                   None, \
                   keyWords, QadInputModeEnum.NONE)


   # ============================================================================
   # waitForTracePt
   # ============================================================================
   def waitForTracePt(self, msgMapTool, msg):
      self.step = 3
      # set the map tool
      self.getPointMapTool().setMode(Qad_pline_maptool_ModeEnum.ASK_FOR_TRACE_PT)
      self.getPointMapTool().firstPt = self.getLastPt() # last summit
      # is preparing to wait for a point
      self.waitForPoint(QadMsg.translate("Command_PLINE", "Select the object in the trace end point: "))


   # ============================================================================
   # addPointToPolyline
   # ============================================================================
   def addPointToPolyline(self, pt):
      if self.firstVertex is None:
         self.firstVertex = QgsPointXY(pt)
         self.plugIn.setLastPoint(pt)
         self.getPointMapTool().setStartPoint(self.firstVertex)
         if self.asToolForMPolygon:
            self.getPointMapTool().endVertex = self.firstVertex
         return
      else:
         self.addLinearObjToPolyline(QadLine().set(self.getLastPt(), pt))


   # ============================================================================
   # addLinearObjToPolyline
   # ============================================================================
   def addLinearObjToPolyline(self, linearObj):
      pts = linearObj.asPolyline()
      tot = len(pts)
      if tot > 0:
         if self.rubberBand.numberOfVertices() > 0:
            i = 1
         else:
            i = 0
         tot = tot - 1
         while i < tot:
            self.addPointToRubberBand(pts[i], False)
            i = i + 1
         self.addPointToRubberBand(pts[-1], True)

         self.polyline.append(linearObj)
         self.plugIn.setLastPoint(pts[-1])
         self.plugIn.setLastSegmentAng(self.getLastSegmentAng())
         self.getPointMapTool().setPolarAngOffset(self.plugIn.lastSegmentAng)
         self.getPointMapTool().setStartPoint(pts[-1])
         self.getPointMapTool().setTmpGeometry(self.polyline.asGeom()) # for snapping add this temporary geometry


   # ============================================================================
   # removeLastLinearObjToPolyline
   # ============================================================================
   def removeLastLinearObjToPolyline(self):
      totLinearObjs = self.polyline.qty()
      if totLinearObjs == 0: return
      linearObj = self.polyline.getLinearObjectAt(-1)
      lastPt = linearObj.getStartPt()
      pts = linearObj.asPolyline()
      tot = len(pts)
      if totLinearObjs == 1:
         i = 0
      else:
         i = 1
      while i < tot:
         self.rubberBand.removeLastPoint()
         i = i + 1

      self.polyline.remove(-1) # last part gate
      self.plugIn.setLastPoint(lastPt)
      self.plugIn.setLastSegmentAng(self.getLastSegmentAng())
      self.getPointMapTool().setTmpGeometry(self.polyline.asGeom()) # for snapping add this temporary geometry
      self.getPointMapTool().setPolarAngOffset(self.plugIn.lastSegmentAng)
      self.getPointMapTool().setStartPoint(lastPt)


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

   def capturedGeometries(self, target_wkb_type = None):
      """Return captured PLINE geometry in map coordinates."""
      wkb_type = target_wkb_type if target_wkb_type is not None else QgsWkbTypes.LineString
      geom = self.polyline.asGeom(wkb_type)
      if geom is None:
         return []
      return [QgsGeometry(geom)]


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
         self.addPointToPolyline(value)
         captured_point_count = (1 if self.firstVertex is not None else 0) + self.polyline.qty()
         if self.shouldFinishVirtualCapture(captured_point_count):
            return True # end command
         if self.hasPendingCaptureSelectionStep():
            self.waitForCaptureSelectionStep()
            return False
         self.getPointMapTool().setSelectionMode(QadGetPointSelectionModeEnum.POINT_SELECTION)
         self.getPointMapTool().setMode(Qad_pline_maptool_ModeEnum.DRAW_LINE)
         self.WaitForLineMenu()
         return False

      # FIRST POINT REQUEST
      if self.step == 0: # start of command
         self.getPointMapTool().setMode(Qad_pline_maptool_ModeEnum.DRAW_LINE) # set the elastic line
         # is preparing to wait for a point or Enter
         #                        msg, inputType,              default, keyWords, no check
         self.waitForPoint(self.capturePrompt("first_point", QadMsg.translate("Command_PLINE", "Specify start point: ")))
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
               self.setMapTool(self.getPointMapTool()) # I reactivate the map tool
               return False

               if self.getPointMapTool().rightButton == True: # if used with the right mouse button
                  if self.virtualCmd == False: # if you really want to save the polyline in a layer
                     geom = self.polyline.asGeom(currLayer.wkbType())
                     if geom is not None:
                        qad_layer.addGeomToLayer(self.plugIn, currLayer, self.mapToLayerCoordinates(currLayer, geom))
                  return True # end command
               else:
                  self.setMapTool(self.getPointMapTool()) # I reactivate the map tool
                  return False

            value = self.getPointMapTool().point
         else: # the dot comes as a parameter of the function
            value = msg

         if value is None:
            if self.firstVertex is None:
               if self.plugIn.lastPoint is not None:
                  value = self.plugIn.lastPoint
               else:
                  return True # end command
            else:
               if self.virtualCmd == False: # if you really want to save the polyline in a layer
                  geom = self.polyline.asGeom(currLayer.wkbType())
                  if geom is not None:
                     qad_layer.addGeomToLayer(self.plugIn, currLayer, self.mapToLayerCoordinates(currLayer, geom))
               return True # end command

         if type(value) == unicode:
            if value == QadMsg.translate("Command_PLINE", "Arc") or value == "Arc":
               self.WaitForArcMenu()
               return False
            elif value == QadMsg.translate("Command_PLINE", "Length") or value == "Length":
               # is preparing to wait for a point or a real number
               # msg, inputType, default, keyWords, positive values
               # "Specify line length: "
               self.waitFor(QadMsg.translate("Command_PLINE", "Specify line length: "), \
                            QadInputTypeEnum.POINT2D | QadInputTypeEnum.FLOAT, \
                            None, "", \
                            QadInputModeEnum.NOT_NULL | QadInputModeEnum.NOT_ZERO | QadInputModeEnum.NOT_NEGATIVE)
               self.step = 2
               return False
            # the Undo option is translated into Italian as "ANnulla" in the "WaitForLineMenu" context
            elif value == QadMsg.translate("Command_PLINE", "Undo", "WaitForLineMenu") or value == "Undo":
               if self.polyline.qty() > 0:
                  self.getPointMapTool().clear()
                  self.getPointMapTool().setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
                  self.removeLastLinearObjToPolyline()
               else:
                  self.showMsg(QadMsg.translate("QAD", "\nThe command has been canceled."))
            elif value == QadMsg.translate("Command_PLINE", "Close") or value == "Close":
               self.polyline.setClose()
               if self.virtualCmd == False: # if you really want to save the polyline in a layer
                  geom = self.polyline.asGeom(currLayer.wkbType())
                  if geom is not None:
                     qad_layer.addGeomToLayer(self.plugIn, currLayer, self.mapToLayerCoordinates(currLayer, geom))
               return True # end command
            elif value == QadMsg.translate("Command_PLINE", "Trace") or value == "Trace":
               self.waitForTracePt(msgMapTool, msg)
               return False # continua

         elif type(value) == QgsPointXY:
            self.addPointToPolyline(value)
            captured_point_count = (1 if self.firstVertex is not None else 0) + self.polyline.qty()
            if self.shouldFinishVirtualCapture(captured_point_count):
               return True # end command

         self.WaitForLineMenu()

         return False

      # =========================================================================
      # RESPONSE TO THE "Length" REQUEST (from step = 1)
      elif self.step == 2: # after waiting for a point or a real number the command is restarted
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if while selecting a point
            # Another plugin was activated which deactivated Qad
            # so the command that returns here has been reactivated without the map tool
            # has selected a point
            if self.getPointMapTool().point is None: # the map tool was activated without a dot
               if self.getPointMapTool().rightButton == True: # if used with the right mouse button
                  return True # end command
               else:
                  self.setMapTool(self.getPointMapTool()) # I reactivate the map tool
                  return False

            value = self.getPointMapTool().point
         else: # the dot comes as a parameter of the function
            value = msg

         if type(value) == QgsPointXY:
            dist = qad_utils.getDistance(self.getLastPt(), value)
         else:
            dist = value

         newPt = qad_utils.getPolarPointByPtAngle(self.getLastPt(), self.getLastSegmentAng(), dist)
         self.addPointToPolyline(newPt)

         self.WaitForLineMenu()

         self.step = 1 # torno al MENU PRINCIPLE

         return False


      # =========================================================================
      # ANSWER TO THE REQUEST "Select the object at the final tracing point: " (from step = 1)
      elif self.step == 3:
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if while selecting a point
            # Another plugin was activated which deactivated Qad
            # so the command that returns here has been reactivated without the map tool
            # has selected a point
            if self.getPointMapTool().point is None: # the map tool was activated without a dot
               if self.getPointMapTool().rightButton == True: # if used with the right mouse button
                  return True # end command
               else:
                  self.setMapTool(self.getPointMapTool()) # I reactivate the map tool
                  return False

            value = self.getPointMapTool().point
         else: # the dot comes as a parameter of the function
            value = msg

         if type(value) == QgsPointXY:
            geom = None
            layer = None
            if self.getPointMapTool().entity.isInitialized(): # the point comes from the mouse
               entSelected = True
               layer = self.getPointMapTool().entity.layer
               geom = self.getPointMapTool().entity.getGeometry()
            else: # the point comes from the keyboard
               # I searc if there are entities at the point indicated considering
               # only linear or polygon layers that do not belong to dimensions
               layerList = []
               for layer in qad_utils.getVisibleVectorLayers(self.plugIn.canvas): # All vector layers visible
                  if layer.geometryType() == QgsWkbTypes.LineGeometry or layer.geometryType() == QgsWkbTypes.PolygonGeometry:
                     if len(QadDimStyles.getDimListByLayer(layer)) == 0:
                        layerList.append(layer)

               result = qad_utils.getEntSel(self.getPointMapTool().toCanvasCoordinates(value),
                                            self.getPointMapTool(), \
                                            QadVariables.get(QadMsg.translate("Environment variables", "PICKBOX")), \
                                            layerList)
               if result is not None:
                  feature = result[0]
                  layer = result[1]
                  geom = feature.getGeometry()

            if geom is not None and layer is not None:
               qadGeom = fromQgsGeomToQadGeom(geom, layer.crs())
               # the function returns a list with
               # (<minimum distance>
               # <nearest point>
               # <nearest geometry index>
               # <index of the nearest sub-geometry>
               # <index of the closest sub-geometry part>
               # <"to the left of" if the point is to the left of the part (< 0 -> left, > 0 -> right)
               dummy = getQadGeomClosestPart(qadGeom, value)
               qadGeom = getQadGeomAt(qadGeom, dummy[2], dummy[3])
               subGeom = getQadGeomBetween2Pts(qadGeom, self.getLastPt(), dummy[1])
               if subGeom is not None:
                  pl = QadPolyline()
                  pl.fromPolyline(subGeom.asPolyline())
                  tot = pl.qty()
                  i = 0
                  while i < tot:
                     self.addLinearObjToPolyline(pl.getLinearObjectAt(i))
                     i = i + 1

         self.WaitForLineMenu()
         self.getPointMapTool().setMode(Qad_pline_maptool_ModeEnum.DRAW_LINE)
         self.getPointMapTool().setTmpGeometry(self.polyline.asGeom()) # for snapping add this temporary geometry
         self.getPointMapTool().setStartPoint(self.getLastPt())

         return False


      # =========================================================================
      # ANSWER TO THE REQUEST "Specify end point of the arc or [Angle/Center/Close/Direction/Line/Radius/Second point/Undo]: " (from step = 1)
      elif self.step == 101: # after waiting for a point or a keyword the command is restarted
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if while selecting a point
            # Another plugin was activated which deactivated Qad
            # so the command that returns here has been reactivated without the map tool
            # has selected a point
            if self.getPointMapTool().point is None: # the map tool was activated without a dot
               if self.getPointMapTool().rightButton == True: # if used with the right mouse button
                  if self.virtualCmd == False: # if you really want to save the polyline in a layer
                     geom = self.polyline.asGeom(currLayer.wkbType())
                     if geom is not None:
                        qad_layer.addGeomToLayer(self.plugIn, currLayer, self.mapToLayerCoordinates(currLayer, geom))
                  return True # end command
               else:
                  self.setMapTool(self.getPointMapTool()) # I reactivate the map tool
                  return False

            value = self.getPointMapTool().point
            ctrlPressed = self.getPointMapTool().ctrlKey
         else: # the dot comes as a parameter of the function
            value = msg
            ctrlPressed = False

         if value is None:
            if self.virtualCmd == False: # if you really want to save the polyline in a layer
               geom = self.polyline.asGeom(currLayer.wkbType())
               if geom is not None:
                  qad_layer.addGeomToLayer(self.plugIn, currLayer, self.mapToLayerCoordinates(currLayer, geom))
            return True # end command

         if type(value) == unicode:
            if value == QadMsg.translate("Command_PLINE", "Angle") or value == "Angle":
               self.arcStartPt = self.getLastPt()

               # set the map tool
               self.getPointMapTool().arcStartPt = self.arcStartPt
               self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.START_PT_KNOWN_ASK_FOR_ANGLE)
               # is preparing to wait for a point or a real number
               # msg, inputType, default, keyWords, isNullable
               self.waitFor(QadMsg.translate("Command_PLINE", "Specify the included angle: "), \
                            QadInputTypeEnum.POINT2D | QadInputTypeEnum.ANGLE, \
                            None, "", \
                            QadInputModeEnum.NOT_NULL | QadInputModeEnum.NOT_ZERO)
               self.step = 102
            # the CEnter option is translated into Italian as "CEntro" in the "WaitForArcMenu" context
            elif value == QadMsg.translate("Command_PLINE", "CEnter", "WaitForArcMenu") or value == "CEnter":
               self.arcStartPt = self.getLastPt()

               # set the map tool
               self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_CENTER_PT)
               # is preparing to wait for a point
               self.waitForPoint(QadMsg.translate("Command_PLINE", "Specify the center of the arc: "))
               self.step = 108
            elif value == QadMsg.translate("Command_PLINE", "Close") or value == "Close":
               arc = QadArc()

               if arc.fromStartEndPtsTan(self.arcStartPt, self.getFirstPt(), self.arcTanOnStartPt) == True:
                  self.addLinearObjToPolyline(arc)

                  if self.virtualCmd == False: # if you really want to save the polyline in a layer
                     geom = self.polyline.asGeom(currLayer.wkbType())
                     if geom is not None:
                        qad_layer.addGeomToLayer(self.plugIn, currLayer, self.mapToLayerCoordinates(currLayer, geom))

                  return True # end command
            elif value == QadMsg.translate("Command_PLINE", "Direction") or value == "Direction":
               self.arcStartPt = self.getLastPt()

               # set the map tool
               self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.START_PT_KNOWN_ASK_FOR_SECOND_PT)
               # is preparing to wait for a point or a real number
               # msg, inputType, default, keyWords, isNullable
               self.waitFor(QadMsg.translate("Command_PLINE", "Specify the tangent direction for the start point of the arc: "), \
                            QadInputTypeEnum.POINT2D | QadInputTypeEnum.ANGLE, \
                            None, "", QadInputModeEnum.NOT_NULL)
               self.step = 112
            elif value == QadMsg.translate("Command_PLINE", "Line") or value == "Line":
               self.mode = "LINE"
               self.getPointMapTool().refreshSnapType() # update the snapType which can be changed from the arc map tool
               self.getPointMapTool().setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
               self.getPointMapTool().setStartPoint(self.getLastPt())
               self.WaitForLineMenu()
            elif value == QadMsg.translate("Command_PLINE", "Radius") or value == "Radius":
               self.arcStartPt = self.getLastPt()

               # set the map tool
               self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.START_PT_ANGLE_KNOWN_ASK_FOR_RADIUS)
               # is preparing to wait for a point or a real number
               # msg, inputType, default, keyWords, positive values
               self.waitFor(QadMsg.translate("Command_PLINE", "Specify the radius of the arc: "), \
                            QadInputTypeEnum.POINT2D | QadInputTypeEnum.FLOAT, \
                            None, "", \
                            QadInputModeEnum.NOT_NULL | QadInputModeEnum.NOT_ZERO | QadInputModeEnum.NOT_NEGATIVE)
               self.step = 114
            elif value == QadMsg.translate("Command_PLINE", "Second point") or value == "Second point":
               self.arcStartPt = self.getLastPt()

               # set the map tool
               self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.START_PT_KNOWN_ASK_FOR_SECOND_PT)
               # is preparing to wait for a point
               self.waitForPoint(QadMsg.translate("Command_PLINE", "Specify second point of the arc: "))
               self.step = 119
            # the Undo option is translated into Italian as "ANNulla" in the "WaitForArcMenu" context
            elif value == QadMsg.translate("Command_PLINE", "Undo", "WaitForArcMenu") or value == "Undo":
               if self.polyline.qty() > 0:
                  self.getPointMapTool().clear()
                  self.getPointMapTool().setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
                  self.removeLastLinearObjToPolyline()
               else:
                  self.showMsg(QadMsg.translate("QAD", "\nThe command has been canceled."))
               self.WaitForArcMenu()
         elif type(value) == QgsPointXY: # the final point of the arc has been inserted
            arc = QadArc()
            if arc.fromStartEndPtsTan(self.arcStartPt, value, self.arcTanOnStartPt) == True:
               if ctrlPressed: # I invert the initial-final angle
                  arc.inverseAngles()
               self.addLinearObjToPolyline(arc)

            self.WaitForArcMenu()

         return False


      # =========================================================================
      # ANSWER TO THE REQUEST "Specify inscribed angle: " (from step = 101)
      elif self.step == 102: # after waiting for a point or a real number the command is restarted
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if while selecting a point
            # Another plugin was activated which deactivated Qad
            # so the command that returns here has been reactivated without the map tool
            # has selected a point
            if self.getPointMapTool().point is None: # the map tool was activated without a dot
               if self.getPointMapTool().rightButton == True: # if used with the right mouse button
                  return True # end command
               else:
                  self.setMapTool(self.getPointMapTool()) # I reactivate the map tool
                  return False

            value = self.getPointMapTool().point
         else: # the dot comes as a parameter of the function
            value = msg

         if type(value) == QgsPointXY:
            self.arcAngle = qad_utils.getAngleBy2Pts(self.arcStartPt, value)
         else:
            self.arcAngle = value

         # set the map tool
         self.getPointMapTool().arcAngle = self.arcAngle
         self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.START_PT_ANGLE_KNOWN_ASK_FOR_END_PT)

         # the CEnter option is translated into Italian as "Centro" in the "START_PT_ANGLE_KNOWN_ASK_FOR_END_PT" context
         keyWords = QadMsg.translate("Command_PLINE", "CEnter", "START_PT_ANGLE_KNOWN_ASK_FOR_END_PT") + "/" + \
                    QadMsg.translate("Command_PLINE", "Radius")
         englishKeyWords = "CEnter" + "/" + "Radius"
         prompt = QadMsg.translate("Command_PLINE", "Specify the final point of the arc (hold Ctrl to switch direction) or [{0}]: ").format(keyWords)

         keyWords += "_" + englishKeyWords
         # is preparing to wait for a point or a keyword
         # msg, inputType, default, keyWords, isNullable
         self.waitFor(prompt, \
                      QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                      None, \
                      keyWords, QadInputModeEnum.NOT_NULL)
         self.step = 103

         return False


      # =========================================================================
      # ANSWER TO THE REQUEST "Specify end point of the arc or [Center/Radius]: : " (from step = 102)
      elif self.step == 103: # after waiting for a point or a keyword the command is restarted
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if while selecting a point
            # Another plugin was activated which deactivated Qad
            # so the command that returns here has been reactivated without the map tool
            # has selected a point
            if self.getPointMapTool().point is None: # the map tool was activated without a dot
               if self.getPointMapTool().rightButton == True: # if used with the right mouse button
                  return True # end command
               else:
                  self.setMapTool(self.getPointMapTool()) # I reactivate the map tool
                  return False

            value = self.getPointMapTool().point
            ctrlPressed = self.getPointMapTool().ctrlKey
         else: # the dot comes as a parameter of the function
            value = msg
            ctrlPressed = False

         if type(value) == unicode:
            # the CEnter option is translated into Italian as "Centro" in the "START_PT_ANGLE_KNOWN_ASK_FOR_END_PT" context
            if value == QadMsg.translate("Command_PLINE", "CEnter", "START_PT_ANGLE_KNOWN_ASK_FOR_END_PT") or value == "CEnter":
               # set the map tool
               self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.START_PT_ANGLE_KNOWN_ASK_FOR_CENTER_PT)
               # is preparing to wait for a point
               self.waitForPoint(QadMsg.translate("Command_PLINE", "Specify the center of the arc (hold Ctrl to switch direction): "))
               self.step = 104
            elif value == QadMsg.translate("Command_PLINE", "Radius") or value == "Radius":
               # set the map tool
               self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.START_PT_ANGLE_KNOWN_ASK_FOR_RADIUS)
               # is preparing to wait for a point or a real number
               # msg, inputType, default, keyWords, positive values
               self.waitFor(QadMsg.translate("Command_PLINE", "Specify the radius of the arc: "), \
                            QadInputTypeEnum.POINT2D | QadInputTypeEnum.FLOAT, \
                            None, "", \
                            QadInputModeEnum.NOT_NULL | QadInputModeEnum.NOT_ZERO | QadInputModeEnum.NOT_NEGATIVE)
               self.step = 105
         elif type(value) == QgsPointXY: # the final point of the arc has been inserted
            arc = QadArc()
            if arc.fromStartEndPtsAngle(self.arcStartPt, value, self.arcAngle) == True:
               if ctrlPressed: # I invert the initial-final angle
                  arc.inverseAngles()
               self.addLinearObjToPolyline(arc)

               self.WaitForArcMenu()
               return False

            # the CEnter option is translated into Italian as "Centro" in the "START_PT_ANGLE_KNOWN_ASK_FOR_END_PT" context
            keyWords = QadMsg.translate("Command_PLINE", "CEnter", "START_PT_ANGLE_KNOWN_ASK_FOR_END_PT") + "/" + \
                       QadMsg.translate("Command_PLINE", "Radius")
            prompt = QadMsg.translate("Command_PLINE", "Specify the final point of the arc (hold Ctrl to switch direction) or [{0}]: ").format(keyWords)

            englishKeyWords = "CEnter" + "/" + "Radius"
            keyWords += "_" + englishKeyWords
            # is preparing to wait for a point or a keyword
            # msg, inputType, default, keyWords, isNullable
            self.waitFor(prompt, \
                         QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                         None, \
                         keyWords, QadInputModeEnum.NOT_NULL)

         return False


      # =========================================================================
      # RESPONSE TO THE ARC CENTER REQUEST (from step = 103)
      elif self.step == 104: # after waiting for a point the command restarts
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if while selecting a point
            # Another plugin was activated which deactivated Qad
            # so the command that returns here has been reactivated without the map tool
            # has selected a point
            if self.getPointMapTool().point is None: # the map tool was activated without a dot
               if self.getPointMapTool().rightButton == True: # if used with the right mouse button
                  return True # end command
               else:
                  self.setMapTool(self.getPointMapTool()) # I reactivate the map tool
                  return False

            value = self.getPointMapTool().point
            ctrlPressed = self.getPointMapTool().ctrlKey
         else: # the dot comes as a parameter of the function
            value = msg
            ctrlPressed = False

         arc = QadArc()
         if arc.fromStartCenterPtsAngle(self.arcStartPt, value, self.arcAngle) == True:
            if ctrlPressed: # I invert the initial-final angle
               arc.inverseAngles()
            self.addLinearObjToPolyline(arc)

            self.WaitForArcMenu()
            return False

         # is preparing to wait for a point
         self.waitForPoint(QadMsg.translate("Command_PLINE", "Specify the center of the arc: "))

         return False


      # =========================================================================
      # RESPONSE TO RADIUS REQUEST (from step = 103)
      elif self.step == 105: # after waiting for a point or a real number the command is restarted
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if while selecting a point
            # Another plugin was activated which deactivated Qad
            # so the command that returns here has been reactivated without the map tool
            # has selected a point
            if self.getPointMapTool().point is None: # the map tool was activated without a dot
               if self.getPointMapTool().rightButton == True: # if used with the right mouse button
                  return True # end command
               else:
                  self.setMapTool(self.getPointMapTool()) # I reactivate the map tool
                  return False

            value = self.getPointMapTool().point
         else: # the dot comes as a parameter of the function
            value = msg

         if type(value) == QgsPointXY:
            self.arcStartPtForRadius = value

            # set the map tool
            self.getPointMapTool().arcStartPtForRadius = self.arcStartPtForRadius
            self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.START_PT_ANGLE_KNOWN_ASK_FOR_SECONDPTRADIUS)

            # is preparing to wait for a point
            self.waitForPoint(QadMsg.translate("Command_PLINE", "Specify second point: "))
            self.step = 106
         else:
            self.arcRadius = value
            self.plugIn.setLastRadius(self.arcRadius)

            # set the map tool
            self.getPointMapTool().arcRadius = self.arcRadius
            self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.START_PT_ANGLE_RADIUS_KNOWN_ASK_FOR_CHORDDIRECTION)
            # is preparing to wait for a point or a real number
            # msg, inputType, default, keyWords, isNullable
            msg = QadMsg.translate("Command_PLINE", "Specify the direction for the chord of the arc (hold Ctrl to switch direction) <{0}>: ")
            self.waitFor(msg.format(str(self.getLastSegmentAng())), \
                         QadInputTypeEnum.POINT2D | QadInputTypeEnum.ANGLE, \
                         None, "", QadInputModeEnum.NOT_NULL)
            self.step = 107

         return False


      # =========================================================================
      # RESPONSE TO THE REQUEST SECOND POINT OF THE RAY (from step = 105)
      elif self.step == 106: # after waiting for a point the command restarts
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if while selecting a point
            # Another plugin was activated which deactivated Qad
            # so the command that returns here has been reactivated without the map tool
            # has selected a point
            if self.getPointMapTool().point is None: # the map tool was activated without a dot
               if self.getPointMapTool().rightButton == True: # if used with the right mouse button
                  return True # end command
               else:
                  self.setMapTool(self.getPointMapTool()) # I reactivate the map tool
                  return False

            value = self.getPointMapTool().point
         else: # the dot comes as a parameter of the function
            value = msg

         self.arcRadius = qad_utils.getDistance(self.arcStartPtForRadius, value)
         self.plugIn.setLastRadius(self.arcRadius)

         # set the map tool
         self.getPointMapTool().arcRadius = self.arcRadius
         self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.START_PT_ANGLE_RADIUS_KNOWN_ASK_FOR_CHORDDIRECTION)
         # is preparing to wait for a point or a real number
         # msg, inputType, default, keyWords, isNullable
         msg = QadMsg.translate("Command_PLINE", "Specify the direction for the chord of the arc (hold Ctrl to switch direction) <{0}>: ")
         self.waitFor(msg.format(str(self.getLastSegmentAng())), \
                      QadInputTypeEnum.POINT2D | QadInputTypeEnum.ANGLE, \
                      None, "", QadInputModeEnum.NOT_NULL)
         self.step = 107


      # =========================================================================
      # RESPONSE TO THE BOW STRING DIRECTION REQUEST (from step = 106 and 107)
      elif self.step == 107: # after waiting for a point the command restarts
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if while selecting a point
            # Another plugin was activated which deactivated Qad
            # so the command that returns here has been reactivated without the map tool
            # has selected a point
            if self.getPointMapTool().point is None: # the map tool was activated without a dot
               if self.getPointMapTool().rightButton == True: # if used with the right mouse button
                  return True # end command
               else:
                  self.setMapTool(self.getPointMapTool()) # I reactivate the map tool
                  return False

            value = self.getPointMapTool().point
            ctrlPressed = self.getPointMapTool().ctrlKey
         else: # the dot comes as a parameter of the function
            value = msg
            ctrlPressed = False

         if type(value) == QgsPointXY:
            self.arcChordDirection = qad_utils.getAngleBy2Pts(self.arcStartPt, value)
         else:
            self.arcChordDirection = value

         arc = QadArc()
         if arc.fromStartPtAngleRadiusChordDirection(self.arcStartPt, self.arcAngle, \
                                                     self.arcRadius, self.arcChordDirection) == True:
            if ctrlPressed: # I invert the initial-final angle
               arc.inverseAngles()
            self.addLinearObjToPolyline(arc)

            self.WaitForArcMenu()
            return False

         # set the map tool
         self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.START_PT_ANGLE_RADIUS_KNOWN_ASK_FOR_CHORDDIRECTION)
         # is preparing to wait for a point or a real number
         # msg, inputType, default, keyWords, isNullable
         msg = QadMsg.translate("Command_PLINE", "Specify the direction for the chord of the arc (hold Ctrl to switch direction) <{0}>: ")
         self.waitFor(msg.format(str(self.getLastSegmentAng())), \
                      QadInputTypeEnum.POINT2D | QadInputTypeEnum.ANGLE, \
                      None, "", QadInputModeEnum.NOT_NULL)

         return False


      # =========================================================================
      # RESPONSE TO THE ARC CENTER REQUEST (from step = 101)
      elif self.step == 108: # after waiting for a point the command restarts
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if while selecting a point
            # Another plugin was activated which deactivated Qad
            # so the command that returns here has been reactivated without the map tool
            # has selected a point
            if self.getPointMapTool().point is None: # the map tool was activated without a dot
               if self.getPointMapTool().rightButton == True: # if used with the right mouse button
                  return True # end command
               else:
                  self.setMapTool(self.getPointMapTool()) # I reactivate the map tool
                  return False

            value = self.getPointMapTool().point
         else: # the dot comes as a parameter of the function
            value = msg

         self.arcCenterPt = value

         # set the map tool
         self.getPointMapTool().arcCenterPt = self.arcCenterPt
         self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.START_CENTER_PT_KNOWN_ASK_FOR_END_PT)

         keyWords = QadMsg.translate("Command_PLINE", "Angle") + "/" + \
                    QadMsg.translate("Command_PLINE", "chord Length")
         prompt = QadMsg.translate("Command_PLINE", "Specify the final point of the arc (hold Ctrl to switch direction) or [{0}]: ").format(keyWords)

         englishKeyWords = "Angle" + "/" + "chord Length"
         keyWords += "_" + englishKeyWords
         # is preparing to wait for a point or a keyword
         # msg, inputType, default, keyWords, isNullable
         self.waitFor(prompt, \
                      QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                      None, \
                      keyWords, QadInputModeEnum.NOT_NULL)
         self.step = 109

         return False


      # =========================================================================
      # ANSWER TO THE REQUEST "Specify end point of the arc or [Angle/Chord Length]: " (from step = 108)
      elif self.step == 109: # after waiting for a point or a keyword the command is restarted
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if while selecting a point
            # Another plugin was activated which deactivated Qad
            # so the command that returns here has been reactivated without the map tool
            # has selected a point
            if self.getPointMapTool().point is None: # the map tool was activated without a dot
               if self.getPointMapTool().rightButton == True: # if used with the right mouse button
                  return True # end command
               else:
                  self.setMapTool(self.getPointMapTool()) # I reactivate the map tool
                  return False

            value = self.getPointMapTool().point
            ctrlPressed = self.getPointMapTool().ctrlKey
         else: # the dot comes as a parameter of the function
            value = msg
            ctrlPressed = False

         if type(value) == unicode:
            if value == QadMsg.translate("Command_PLINE", "Angle") or value == "Angle":
               # set the map tool
               self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.START_CENTER_PT_KNOWN_ASK_FOR_ANGLE)
               # is preparing to wait for a point or a real number
               # msg, inputType, default, keyWords, values != 0
               self.waitFor(QadMsg.translate("Command_PLINE", "Specify the included angle (hold Ctrl to switch direction): "), \
                            QadInputTypeEnum.POINT2D | QadInputTypeEnum.ANGLE, \
                            None, "", \
                            QadInputModeEnum.NOT_NULL | QadInputModeEnum.NOT_ZERO)
               self.step = 110
               return False
            elif value == QadMsg.translate("Command_PLINE", "chord Length") or value == "chord Length":
               # set the map tool
               self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.START_CENTER_PT_KNOWN_ASK_FOR_CHORD)
               # is preparing to wait for a point or a real number
               # msg, inputType, default, keyWords, positive values
               self.waitFor(QadMsg.translate("Command_PLINE", "Specify the chord length (hold Ctrl to switch direction): "), \
                            QadInputTypeEnum.POINT2D | QadInputTypeEnum.FLOAT, \
                            None, "", \
                            QadInputModeEnum.NOT_NULL | QadInputModeEnum.NOT_ZERO | QadInputModeEnum.NOT_NEGATIVE)
               self.step = 111
               return False
         elif type(value) == QgsPointXY: # if the final point of the arc has been entered
            self.arcEndPt = value

            arc = QadArc()
            if arc.fromStartCenterEndPts(self.arcStartPt, self.arcCenterPt, self.arcEndPt) == True:
               if ctrlPressed: # I invert the initial-final angle
                  arc.inverseAngles()
               self.addLinearObjToPolyline(arc)

               self.WaitForArcMenu()
               return False

         keyWords = QadMsg.translate("Command_PLINE", "Angle") + "/" + \
                    QadMsg.translate("Command_PLINE", "chord Length")
         prompt = QadMsg.translate("Command_PLINE", "Specify the final point of the arc (hold Ctrl to switch direction) or [{0}]: ").format(keyWords)

         englishKeyWords = "Angle" + "/" + "chord Length"
         keyWords += "_" + englishKeyWords
         # is preparing to wait for a point or a keyword
         # msg, inputType, default, keyWords, isNullable
         self.waitFor(prompt, \
                      QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                      None, \
                      keyWords, QadInputModeEnum.NOT_NULL)
         return False


      # =========================================================================
      # ANSWER TO THE REQUEST "Specify inscribed angle: " (from step = 109)
      elif self.step == 110: # after waiting for a point or a real number the command is restarted
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if while selecting a point
            # Another plugin was activated which deactivated Qad
            # so the command that returns here has been reactivated without the map tool
            # has selected a point
            if self.getPointMapTool().point is None: # the map tool was activated without a dot
               if self.getPointMapTool().rightButton == True: # if used with the right mouse button
                  return True # end command
               else:
                  self.setMapTool(self.getPointMapTool()) # I reactivate the map tool
                  return False

            value = self.getPointMapTool().point
            ctrlPressed = self.getPointMapTool().ctrlKey
         else: # the dot comes as a parameter of the function
            value = msg
            ctrlPressed = False

         if type(value) == QgsPointXY:
            self.arcAngle = qad_utils.getAngleBy2Pts(self.arcCenterPt, value)
         else:
            self.arcAngle = value

         arc = QadArc()
         if arc.fromStartCenterPtsAngle(self.arcStartPt, self.arcCenterPt, self.arcAngle) == True:
            if ctrlPressed: # I invert the initial-final angle
               arc.inverseAngles()
            self.addLinearObjToPolyline(arc)

            self.WaitForArcMenu()
            return False

         # is preparing to wait for a point or a real number
         # msg, inputType, default, keyWords, isNullable
         self.waitFor(QadMsg.translate("Command_PLINE", "Specify the included angle (hold Ctrl to switch direction): "), \
                      QadInputTypeEnum.POINT2D | QadInputTypeEnum.ANGLE, \
                      None, "", \
                      QadInputModeEnum.NOT_NULL | QadInputModeEnum.NOT_ZERO)

         return False


      # =========================================================================
      # ANSWER TO THE REQUEST "Specify rope length: " (from step = 109)
      elif self.step == 111: # after waiting for a point or a real number the command is restarted
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if while selecting a point
            # Another plugin was activated which deactivated Qad
            # so the command that returns here has been reactivated without the map tool
            # has selected a point
            if self.getPointMapTool().point is None: # the map tool was activated without a dot
               if self.getPointMapTool().rightButton == True: # if used with the right mouse button
                  return True # end command
               else:
                  self.setMapTool(self.getPointMapTool()) # I reactivate the map tool
                  return False

            value = self.getPointMapTool().point
            ctrlPressed = self.getPointMapTool().ctrlKey
         else: # the dot comes as a parameter of the function
            value = msg
            ctrlPressed = False

         if type(value) == QgsPointXY:
            self.arcChord = qad_utils.getDistance(self.arcStartPt, value)
         else:
            self.arcChord = value

         arc = QadArc()
         if arc.fromStartCenterPtsChord(self.arcStartPt, self.arcCenterPt, self.arcChord) == True:
            if ctrlPressed: # I invert the initial-final angle
               arc.inverseAngles()
            self.addLinearObjToPolyline(arc)

            self.WaitForArcMenu()
            return False

         # is preparing to wait for a point or a real number
         # msg, inputType, default, keyWords, positive values
         self.waitFor(QadMsg.translate("Command_PLINE", "Specify the chord length (hold Ctrl to switch direction): "), \
                      QadInputTypeEnum.POINT2D | QadInputTypeEnum.FLOAT, \
                      None, "", \
                      QadInputModeEnum.NOT_NULL | QadInputModeEnum.NOT_ZERO | QadInputModeEnum.NOT_NEGATIVE)

         return False


      # =========================================================================
      # ANSWER TO THE REQUEST "Specify tangent direction for the starting point of the arc: " (from step = 101)
      elif self.step == 112: # after waiting for a point or a real number the command is restarted
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if while selecting a point
            # Another plugin was activated which deactivated Qad
            # so the command that returns here has been reactivated without the map tool
            # has selected a point
            if self.getPointMapTool().point is None: # the map tool was activated without a dot
               if self.getPointMapTool().rightButton == True: # if used with the right mouse button
                  return True # end command
               else:
                  self.setMapTool(self.getPointMapTool()) # I reactivate the map tool
                  return False

            value = self.getPointMapTool().point
         else: # the dot comes as a parameter of the function
            value = msg

         if type(value) == QgsPointXY:
            self.arcTanOnStartPt = qad_utils.getAngleBy2Pts(self.arcStartPt, value)
         else:
            self.arcTanOnStartPt = value

         # set the map tool
         self.getPointMapTool().arcTanOnStartPt = self.arcTanOnStartPt
         self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.START_PT_TAN_KNOWN_ASK_FOR_END_PT)

         # is preparing to wait for a point
         self.waitForPoint(QadMsg.translate("Command_PLINE", "Specify the final point of the arc (hold Ctrl to switch direction): "))
         self.step = 113
         return False


      # =========================================================================
      # RESPONSE TO THE ARC END POINT REQUEST (from step = 112)
      elif self.step == 113: # after waiting for a point the command restarts
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if while selecting a point
            # Another plugin was activated which deactivated Qad
            # so the command that returns here has been reactivated without the map tool
            # has selected a point
            if self.getPointMapTool().point is None: # the map tool was activated without a dot
               if self.getPointMapTool().rightButton == True: # if used with the right mouse button
                  return True # end command
               else:
                  self.setMapTool(self.getPointMapTool()) # I reactivate the map tool
                  return False

            value = self.getPointMapTool().point
            ctrlPressed = self.getPointMapTool().ctrlKey
         else: # the dot comes as a parameter of the function
            value = msg
            ctrlPressed = False

         arc = QadArc()
         if arc.fromStartEndPtsTan(self.arcStartPt, value, self.arcTanOnStartPt) == True:
            if ctrlPressed: # I invert the initial-final angle
               arc.inverseAngles()
            self.addLinearObjToPolyline(arc)

            self.WaitForArcMenu()
            return False

         # is preparing to wait for a point
         self.waitForPoint(QadMsg.translate("Command_PLINE", "Specify the final point of the arc (hold Ctrl to switch direction): "))

         return False


      # =========================================================================
      # RESPONSE TO RADIUS REQUEST (from step = 101)
      elif self.step == 114: # after waiting for a point or a real number the command is restarted
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if while selecting a point
            # Another plugin was activated which deactivated Qad
            # so the command that returns here has been reactivated without the map tool
            # has selected a point
            if self.getPointMapTool().point is None: # the map tool was activated without a dot
               if self.getPointMapTool().rightButton == True: # if used with the right mouse button
                  return True # end command
               else:
                  self.setMapTool(self.getPointMapTool()) # I reactivate the map tool
                  return False

            value = self.getPointMapTool().point
         else: # the dot comes as a parameter of the function
            value = msg

         if type(value) == QgsPointXY:
            self.arcStartPtForRadius = value

            # set the map tool
            self.getPointMapTool().arcStartPtForRadius = self.arcStartPtForRadius
            self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.START_PT_ANGLE_KNOWN_ASK_FOR_SECONDPTRADIUS)

            # is preparing to wait for a point
            self.waitForPoint(QadMsg.translate("Command_PLINE", "Specify second point: "))
            self.step = 115
         else:
            self.arcRadius = value
            self.plugIn.setLastRadius(self.arcRadius)

            # set the map tool
            self.getPointMapTool().arcRadius = self.arcRadius
            self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.START_PT_RADIUS_KNOWN_ASK_FOR_END_PT)

            keyWords = QadMsg.translate("Command_PLINE", "Angle")
            prompt = QadMsg.translate("Command_PLINE", "Specify the final point of the arc (hold Ctrl to switch direction) or [{0}]: ").format(keyWords)
            englishKeyWords = "Angle"
            keyWords += "_" + englishKeyWords
            # is preparing to wait for a point or a real number
            # msg, inputType, default, keyWords, isNullable
            self.waitFor(prompt, \
                         QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                         None, keyWords, QadInputModeEnum.NOT_NULL)
            self.step = 116

         return False


      # =========================================================================
      # RESPONSE TO THE REQUEST SECOND POINT OF THE RAY (from step = 114)
      elif self.step == 115: # after waiting for a point the command restarts
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if while selecting a point
            # Another plugin was activated which deactivated Qad
            # so the command that returns here has been reactivated without the map tool
            # has selected a point
            if self.getPointMapTool().point is None: # the map tool was activated without a dot
               if self.getPointMapTool().rightButton == True: # if used with the right mouse button
                  return True # end command
               else:
                  self.setMapTool(self.getPointMapTool()) # I reactivate the map tool
                  return False

            value = self.getPointMapTool().point
         else: # the dot comes as a parameter of the function
            value = msg

         self.arcRadius = qad_utils.getDistance(self.arcStartPtForRadius, value)
         self.plugIn.setLastRadius(self.arcRadius)

         # set the map tool
         self.getPointMapTool().arcRadius = self.arcRadius
         self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.START_PT_RADIUS_KNOWN_ASK_FOR_END_PT)

         keyWords = QadMsg.translate("Command_PLINE", "Angle")
         prompt = QadMsg.translate("Command_PLINE", "Specify the final point of the arc (hold Ctrl to switch direction) or [{0}]: ").format(keyWords)
         englishKeyWords = "Angle"
         keyWords += "_" + englishKeyWords
         # is preparing to wait for a point or a real number
         # msg, inputType, default, keyWords, isNullable
         self.waitFor(prompt, \
                      QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                      None, keyWords, QadInputModeEnum.NOT_NULL)
         self.step = 116

         return False


      # =========================================================================
      # ANSWER TO THE REQUEST "Specify end point of the arc or [Angle]: " (from step = 114 or 115)
      elif self.step == 116: # after waiting for a point or a keyword the command is restarted
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if while selecting a point
            # Another plugin was activated which deactivated Qad
            # so the command that returns here has been reactivated without the map tool
            # has selected a point
            if self.getPointMapTool().point is None: # the map tool was activated without a dot
               if self.getPointMapTool().rightButton == True: # if used with the right mouse button
                  return True # end command
               else:
                  self.setMapTool(self.getPointMapTool()) # I reactivate the map tool
                  return False

            value = self.getPointMapTool().point
            ctrlPressed = self.getPointMapTool().ctrlKey
         else: # the dot comes as a parameter of the function
            value = msg
            ctrlPressed = False

         if type(value) == unicode:
            if value == QadMsg.translate("Command_PLINE", "Angle") or value == "Angle":
               # set the map tool
               self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.START_PT_KNOWN_ASK_FOR_ANGLE)
               # is preparing to wait for a point or a real number
               # msg, inputType, default, keyWords, isNullable
               self.waitFor(QadMsg.translate("Command_PLINE", "Specify the included angle: "), \
                            QadInputTypeEnum.POINT2D | QadInputTypeEnum.ANGLE, \
                            None, "", \
                            QadInputModeEnum.NOT_NULL | QadInputModeEnum.NOT_ZERO)
               self.step = 117
         elif type(value) == QgsPointXY: # the final point of the arc has been inserted
            arc = QadArc()
            if arc.fromStartEndPtsRadius(self.arcStartPt, value, self.arcRadius) == True:
               if ctrlPressed: # I invert the initial-final angle
                  arc.inverseAngles()
               self.addLinearObjToPolyline(arc)

            self.WaitForArcMenu()

         return False


      # =========================================================================
      # ANSWER TO THE REQUEST "Specify inscribed angle: " (from step = 116)
      elif self.step == 117: # after waiting for a point or a real number the command is restarted
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if while selecting a point
            # Another plugin was activated which deactivated Qad
            # so the command that returns here has been reactivated without the map tool
            # has selected a point
            if self.getPointMapTool().point is None: # the map tool was activated without a dot
               if self.getPointMapTool().rightButton == True: # if used with the right mouse button
                  return True # end command
               else:
                  self.setMapTool(self.getPointMapTool()) # I reactivate the map tool
                  return False

            value = self.getPointMapTool().point
         else: # the dot comes as a parameter of the function
            value = msg

         if type(value) == QgsPointXY:
            self.arcAngle = qad_utils.getAngleBy2Pts(self.arcStartPt, value)
         else:
            self.arcAngle = value

         # set the map tool
         self.getPointMapTool().arcAngle = self.arcAngle
         self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.START_PT_ANGLE_RADIUS_KNOWN_ASK_FOR_CHORDDIRECTION)
         # is preparing to wait for a point or a real number
         # msg, inputType, default, keyWords, isNullable
         msg = QadMsg.translate("Command_PLINE", "Specify the direction for the chord of the arc (hold Ctrl to switch direction) <{0}>: ")
         self.waitFor(msg.format(str(self.getLastSegmentAng())), \
                      QadInputTypeEnum.POINT2D | QadInputTypeEnum.ANGLE, \
                      None, "", QadInputModeEnum.NOT_NULL)
         self.step = 118

         return False


      # =========================================================================
      # RESPONSE TO THE REQUEST FOR BOW STRING DIRECTION (from step = 117)
      elif self.step == 118: # after waiting for a point the command restarts
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if while selecting a point
            # Another plugin was activated which deactivated Qad
            # so the command that returns here has been reactivated without the map tool
            # has selected a point
            if self.getPointMapTool().point is None: # the map tool was activated without a dot
               if self.getPointMapTool().rightButton == True: # if used with the right mouse button
                  return True # end command
               else:
                  self.setMapTool(self.getPointMapTool()) # I reactivate the map tool
                  return False

            value = self.getPointMapTool().point
            ctrlPressed = self.getPointMapTool().ctrlKey
         else: # the dot comes as a parameter of the function
            value = msg
            ctrlPressed = False

         if type(value) == QgsPointXY:
            self.arcChordDirection = qad_utils.getAngleBy2Pts(self.arcStartPt, value)
         else:
            self.arcChordDirection = value

         arc = QadArc()
         if arc.fromStartPtAngleRadiusChordDirection(self.arcStartPt, self.arcAngle, \
                                                     self.arcRadius, self.arcChordDirection) == True:
            if ctrlPressed: # I invert the initial-final angle
               arc.inverseAngles()
            self.addLinearObjToPolyline(arc)

            self.WaitForArcMenu()
            return False

         # set the map tool
         self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.START_PT_ANGLE_RADIUS_KNOWN_ASK_FOR_CHORDDIRECTION)
         # is preparing to wait for a point or a real number
         # msg, inputType, default, keyWords, isNullable
         msg = QadMsg.translate("Command_PLINE", "Specify the direction for the chord of the arc (hold Ctrl to switch direction) <{0}>: ")
         self.waitFor(msg.format(str(self.getLastSegmentAng())), \
                      QadInputTypeEnum.POINT2D | QadInputTypeEnum.ANGLE, \
                      None, "", QadInputModeEnum.NOT_NULL)

         return False


      # =========================================================================
      # RESPONSE TO THE SECOND POINT REQUEST (from step = 101)
      elif self.step == 119: # after waiting for a point or a keyword the command is restarted
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if while selecting a point
            # Another plugin was activated which deactivated Qad
            # so the command that returns here has been reactivated without the map tool
            # has selected a point
            if self.getPointMapTool().point is None: # the map tool was activated without a dot
               if self.getPointMapTool().rightButton == True: # if used with the right mouse button
                  return True # end command
               else:
                  self.setMapTool(self.getPointMapTool()) # I reactivate the map tool
                  return False

            value = self.getPointMapTool().point
         else: # the dot comes as a parameter of the function
            value = msg

         self.arcSecondPt = value
         # set the map tool
         self.getPointMapTool().arcSecondPt = self.arcSecondPt
         self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.START_SECOND_PT_KNOWN_ASK_FOR_END_PT)

         # is preparing to wait for a point
         self.waitForPoint(QadMsg.translate("Command_PLINE", "Specify the final point of the arc: "))
         self.step = 120

         return False


      # =========================================================================
      # RESPONSE TO THE ARC END POINT REQUEST (from step = 119)
      elif self.step == 120: # after waiting for a point the command restarts
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if while selecting a point
            # Another plugin was activated which deactivated Qad
            # so the command that returns here has been reactivated without the map tool
            # has selected a point
            if self.getPointMapTool().point is None: # the map tool was activated without a dot
               if self.getPointMapTool().rightButton == True: # if used with the right mouse button
                  return True # end command
               else:
                  self.setMapTool(self.getPointMapTool()) # I reactivate the map tool
                  return False

            value = self.getPointMapTool().point
         else: # the dot comes as a parameter of the function
            value = msg

         self.arcEndPt = value

         arc = QadArc()
         if arc.fromStartSecondEndPts(self.arcStartPt, self.arcSecondPt, self.arcEndPt) == True:
            self.addLinearObjToPolyline(arc)

            self.WaitForArcMenu()
            return False

         # is preparing to wait for a point
         self.waitForPoint(QadMsg.translate("Command_PLINE", "Specify the final point of the arc: "))
         return False
