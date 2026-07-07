# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 class to manage the point request map tool

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


from qgis.PyQt.QtCore import Qt, QTimer, QEvent
from qgis.PyQt.QtGui import QColor, QCursor, QIcon, QKeyEvent
from qgis.PyQt.QtWidgets import QAction, QMenu
from qgis.core import QgsWkbTypes, QgsGeometry, QgsCoordinateTransform, QgsPointXY, QgsProject
from qgis.gui import QgsMapTool

import math
import time # profiling
import datetime


from . import qad_utils
from .qad_snapper import QadSnapper, QadSnapModeEnum, QadSnapTypeEnum, snapTypeEnum2Str
from .qad_snappointsdisplaymanager import QadSnapPointsDisplayManager
from .qad_entity import QadEntity
from .qad_variables import QadVariables, QadAUTOSNAPEnum, QadPOLARMODEnum, POLARADDANG_to_list
from .qad_rubberband import createRubberBand, getColorForCrossingSelectionArea, \
                            getColorForWindowSelectionArea, QadCursorTypeEnum, QadCursorRubberBand
from .qad_cacheareas import QadLayerCacheGeomsDict
from .qad_textwindow import QadInputTypeEnum
from .qad_dynamicinput import QadDynamicEditInput, QadDynamicInputContextEnum
from .qad_msg import QadMsg


# ===============================================================================
# QadGetPointSelectionModeEnum class.
# ===============================================================================
class QadGetPointSelectionModeEnum():
   NONE                     = 0  # no selection (used when a command only asks for the choice of options)
   POINT_SELECTION          = 1  # selecting a point
   ENTITY_SELECTION         = 2  # statically selecting an entity (searces for the entity only with the click event)
   ENTITYSET_SELECTION      = 3  # selection of a group of entities
   ENTITY_SELECTION_DYNAMIC = 4  # selection of an entity dynamically (searces for the entity with the click event e
                                 # with the mouse move event)


# ===============================================================================
# QadGetPointDrawModeEnum class.
# ===============================================================================
class QadGetPointDrawModeEnum():
   NONE              = 0     # none
   ELASTIC_LINE      = 1     # elastic line from __startPoint
   ELASTIC_RECTANGLE = 2     # elastic rectangle from __startPoint


from .qad_dsettings_dlg import QadDSETTINGSDialog, QadDSETTINGSTabIndexEnum


# ===============================================================================
# QadGetPoint get point class
# ===============================================================================
class QadGetPoint(QgsMapTool):

   def __init__(self, plugIn, drawMode = QadGetPointDrawModeEnum.NONE):
      QgsMapTool.__init__(self, plugIn.iface.mapCanvas())
      self.iface = plugIn.iface
      self.canvas = plugIn.iface.mapCanvas()
      self.plugIn = plugIn

      # cursore
      self.__csrRubberBand = None

      self.__QadSnapper = None
      self.__QadSnapPointsDisplayManager = None
      self.__oldSnapType = None
      self.__oldSnapProgrDist = None
      self.__geometryTypesAccordingToSnapType = (False, False, False)
      self.__startPoint = None
      self.tmpGeometries = [] # list of geometry not yet existing but to be counted for osnap points (in map coordinates)
      # options to limit the object to select
      self.onlyEditableLayers = False
      self.checkPointLayer = True
      self.checkLineLayer = True
      self.checkPolygonLayer = True
      self.layersToCheck = None

      self.__RubberBand = None
      self.__prevGeom = None

      self.__stopTimer = True

      # optimization for object searc
      # cache for object selection
      self.layerCacheGeomsDict = QadLayerCacheGeomsDict(self.canvas)
      self.lastLayerFound = None # last object found layer

      # set the selection mode
      self.setSelectionMode(QadGetPointSelectionModeEnum.POINT_SELECTION)

      self.setDrawMode(drawMode)

      self.__QadSnapper = QadSnapper()
      self.__QadSnapper.setSnapMode(QadSnapModeEnum.ONE_RESULT) # Only the closest point is returned
      # All vector layers visible according to QGIS settings
      # (current layer only, a set of layers, all layers)
      self.setSnapLayersFromQgis()
      self.canvas.snappingUtils().configChanged.connect(self.setSnapLayersFromQgis) # update snap layers whenever QGIS snap settings change


      self.__QadSnapper.setProgressDistance(QadVariables.get(QadMsg.translate("Environment variables", "OSPROGRDISTANCE")))
      self.setSnapType(QadVariables.get(QadMsg.translate("Environment variables", "OSMODE")))

      self.setOrthoMode() # set according to environment variables
      self.setAutoSnap() # set according to environment variables

      # I read the tolerance in map units
      ToleranceInMapUnits = QadVariables.get(QadMsg.translate("Environment variables", "PICKBOX")) * self.canvas.mapSettings().mapUnitsPerPixel()
      self.__QadSnapper.setDistToExcludeNea(ToleranceInMapUnits)
      self.__QadSnapper.setToleranceExtParLines(ToleranceInMapUnits)

      self.__QadSnapPointsDisplayManager = QadSnapPointsDisplayManager(self.canvas)
      self.__QadSnapPointsDisplayManager.setIconSize(QadVariables.get(QadMsg.translate("Environment variables", "AUTOSNAPSIZE")))
      self.__QadSnapPointsDisplayManager.setColor(QColor(QadVariables.get(QadMsg.translate("Environment variables", "AUTOSNAPCOLOR"))))

      # output
      self.rightButton = False
      # shift key
      self.shiftKey = False
      self.tmpShiftKey = False
      # ctrl key
      self.ctrlKey = False
      self.tmpCtrlKey = False

      self.point = None # point selected by click
      self.tmpPoint = None # point selected by mouse movement

      self.entity = QadEntity() # entity selected by the click
      self.tmpEntity = QadEntity() # entity selected by mouse movement

      self.snapTypeOnSelection = None # snap attivo al momento del click

      # profiling
      self.tempo_tot = 0
      self.tempo1 = 0
      self.tempo2 = 0

      self.startDateTimeForRightClick = 0

      # input dinamico
      self.dynamicEditInput = QadDynamicEditInput(plugIn, QadDynamicInputContextEnum.NONE)

      # midpoint management between 2 points (M2P)
      self.M2P_Mode = False # whether M2P mode is activated or not
      self.M2p_pt1 = None # first point


   def __del__(self):
      self.removeItems()
      self.canvas.snappingUtils().configChanged.disconnect(self.setSnapLayersFromQgis) # update snap layers whenever QGIS snap settings change


   def removeItems(self):
      if self.__csrRubberBand is not None:
         self.__csrRubberBand.removeItems() # first detach it from the canvas otherwise it will not be removed because it is used by canvas
         del self.__csrRubberBand
         self.__csrRubberBand = None

      if self.__RubberBand is not None:
         self.canvas.scene().removeItem(self.__RubberBand) # first detach it from the canvas otherwise it will not be removed because it is used by canvas
         del self.__RubberBand
         self.__RubberBand = None

      if self.__QadSnapper is not None:
         del self.__QadSnapper
         self.__QadSnapper = None

      if self.__QadSnapPointsDisplayManager is not None:
         self.__QadSnapPointsDisplayManager.removeItems() # first detach it from the canvas otherwise it will not be removed because it is used by canvas
         del self.__QadSnapPointsDisplayManager
         self.__QadSnapPointsDisplayManager = None

      if self.layerCacheGeomsDict is not None: # first detach it from the canvas otherwise it will not be removed because it is used by canvas (events)
         del self.layerCacheGeomsDict
         self.layerCacheGeomsDict = None

      if self.dynamicEditInput is not None:
         self.dynamicEditInput.removeItems()
         del self.dynamicEditInput
         self.dynamicEditInput = None


   # ============================================================================
   # getDynamicInput
   # ============================================================================
   def getDynamicInput(self):
      return self.dynamicEditInput


   # ============================================================================
   # setDrawMode
   # ============================================================================
   def setDrawMode(self, drawMode):
      self.__drawMode = drawMode
      if self.__RubberBand is not None:
         self.__RubberBand.hide()
         self.canvas.scene().removeItem(self.__RubberBand) # first detach it from the canvas otherwise it will not be removed because it is used by canvas
         del self.__RubberBand
         self.__RubberBand = None

      if self.__drawMode == QadGetPointDrawModeEnum.ELASTIC_LINE:
         self.refreshOrthoMode() # set the default
         self.__RubberBand = createRubberBand(self.canvas, QgsWkbTypes.LineGeometry)
         self.__RubberBand.setLineStyle(Qt.DotLine)
      elif self.__drawMode == QadGetPointDrawModeEnum.ELASTIC_RECTANGLE:
         self.rectangleCrossingSelectionColor = getColorForCrossingSelectionArea()
         self.rectangleWindowSelectionColor = getColorForWindowSelectionArea()

         self.__RubberBand = createRubberBand(self.canvas, QgsWkbTypes.PolygonGeometry, False, None, self.rectangleCrossingSelectionColor)
         self.__RubberBand.setLineStyle(Qt.DotLine)


   # ============================================================================
   # getDrawMode
   # ============================================================================
   def getDrawMode(self):
      return self.__drawMode


   # ============================================================================
   # setSelectionMode
   # ============================================================================
   def setSelectionMode(self, selectionMode):
      self.__selectionMode = selectionMode
      # set the cursor type
      if selectionMode == QadGetPointSelectionModeEnum.POINT_SELECTION:
         if QadVariables.get(QadMsg.translate("Environment variables", "APBOX")) == 0:
            self.setCursorType(QadCursorTypeEnum.CROSS) # a cross used to select a point
         else:
            self.setCursorType(QadCursorTypeEnum.CROSS | QadCursorTypeEnum.APERTURE) # a cross + a small square used to select a point
      elif selectionMode == QadGetPointSelectionModeEnum.ENTITY_SELECTION or \
           selectionMode == QadGetPointSelectionModeEnum.ENTITY_SELECTION_DYNAMIC:
         self.entity.clear() # selected entity
         self.setCursorType(QadCursorTypeEnum.BOX) # a small square used to select entities
      elif selectionMode == QadGetPointSelectionModeEnum.ENTITYSET_SELECTION:
         if QadVariables.get(QadMsg.translate("Environment variables", "APBOX")) == 0:
            self.setCursorType(QadCursorTypeEnum.CROSS) # a cross used to select a point
         else:
            self.setCursorType(QadCursorTypeEnum.CROSS | QadCursorTypeEnum.APERTURE) # a cross + a small square used to select a point
      elif selectionMode == QadGetPointSelectionModeEnum.NONE:
         self.setCursorType(QadCursorTypeEnum.NONE) # no cursor


   # ============================================================================
   # getSelectionMode
   # ============================================================================
   def getSelectionMode(self):
      return self.__selectionMode


   # ============================================================================
   # hidePointMapToolMarkers
   # ============================================================================
   def hidePointMapToolMarkers(self):
      if self.__QadSnapPointsDisplayManager is not None:
         self.__QadSnapPointsDisplayManager.hide()
      if self.__RubberBand is not None:
         self.__RubberBand.hide()


   # ============================================================================
   # showPointMapToolMarkers
   # ============================================================================
   def showPointMapToolMarkers(self):
      if self.__RubberBand is not None:
         self.__RubberBand.show()


   # ============================================================================
   # getPointMapToolMarkersCount
   # ============================================================================
   def getPointMapToolMarkersCount(self):
      if self.__RubberBand is None:
         return 0
      else:
         return self.__RubberBand.numberOfVertices()


   # ============================================================================
   # clear
   # ============================================================================
   def clear(self):
      self.hidePointMapToolMarkers()
      if self.__RubberBand is not None:
         self.canvas.scene().removeItem(self.__RubberBand) # first detach it from the canvas otherwise it will not be removed because it is used by canvas
         del self.__RubberBand
         self.__RubberBand = None

      self.__QadSnapper.removeReferenceLines()
      self.__QadSnapper.setStartPoint(None)

      self.point = None # point selected by click
      self.tmpPoint = None # point selected by mouse movement

      self.entity.clear() # entity selected by the click
      self.tmpEntity.clear() # entity selected by mouse movement

      self.snapTypeOnSelection = None # snap attivo al momento del click

      self.shiftKey = False
      self.tmpShiftKey = False # shift key pressed during mouse movement

      self.ctrlKey = False
      self.tmpCtrlKey = False # ctrl key pressed during mouse movement

      self.rightButton = False
      # options to limit the object to select
      self.onlyEditableLayers = False
      self.checkPointLayer = True # used only for ENTITY_SELECTION
      self.checkLineLayer = True # used only for ENTITY_SELECTION
      self.checkPolygonLayer = True # used only for ENTITY_SELECTION
      self.layersToCheck = None

      self.__oldSnapType = None
      self.__oldSnapProgrDist = None
      self.__startPoint = None
      self.clearTmpGeometries()


   # ============================================================================
   # cache
   # ============================================================================
   def updateLayerCacheOnMapCanvasExtent(self):
      if self.layerCacheGeomsDict is not None:
         del self.layerCacheGeomsDict
      # optimization for object searc
      self.layerCacheGeomsDict = QadLayerCacheGeomsDict(self.canvas)

      # if the goal is to select an entity dynamically
      if self.getSelectionMode() == QadGetPointSelectionModeEnum.ENTITY_SELECTION_DYNAMIC:
         if self.layerCacheGeomsDict.refreshOnMapCanvasExtent(self.layersToCheck, \
                                                              self.checkPointLayer, \
                                                              self.checkLineLayer, \
                                                              self.checkPolygonLayer, \
                                                              self.onlyEditableLayers) == False:
            del self.layerCacheGeomsDict
            self.layerCacheGeomsDict = None

      # if the objective is to select a point
      elif self.getSelectionMode() == QadGetPointSelectionModeEnum.POINT_SELECTION:
         if self.layerCacheGeomsDict.refreshOnMapCanvasExtent(None, \
                                                              self.__geometryTypesAccordingToSnapType[0], \
                                                              self.__geometryTypesAccordingToSnapType[1], \
                                                              self.__geometryTypesAccordingToSnapType[2], \
                                                              False) == False:
            del self.layerCacheGeomsDict
            self.layerCacheGeomsDict = None


   # ============================================================================
   # tmpGeometries
   # ============================================================================
   def clearTmpGeometries(self):
      del self.tmpGeometries[:] # I empty the list
      self.__QadSnapper.clearTmpGeometries()


   # ============================================================================
   # setTmpGeometry
   # ============================================================================
   def setTmpGeometry(self, geom, CRS = None):
      self.clearTmpGeometries()
      self.appendTmpGeometry(geom, CRS)


   # ============================================================================
   # appendTmpGeometry
   # ============================================================================
   def appendTmpGeometry(self, geom, CRS = None):
      if geom is None:
         return
      if CRS is not None and CRS != self.canvas.mapSettings().destinationCrs():
         g = QgsGeometry(geom)
         coordTransform = QgsCoordinateTransform(CRS, \
                                                 self.canvas.mapSettings().destinationCrs(), \
                                                 QgsProject.instance()) # I transform the geometry
         g.transform(coordTransform)
         self.tmpGeometries.append(g)
      else:
         self.tmpGeometries.append(geom)

      self.__QadSnapper.appendTmpGeometry(geom)


   # ============================================================================
   # setTmpGeometries
   # ============================================================================
   def setTmpGeometries(self, geoms, CRS = None):
      self.clearTmpGeometries()
      for g in geoms:
         self.appendTmpGeometry(g, CRS)


   # ============================================================================
   # SnapType
   # ============================================================================
   def setSnapLayersFromQgis(self):
      """
      Sets the layers to be snapped to from QGIS's settings
      """
      # All vector layers visible according to QGIS settings
      # (current layer only, a set of layers, all layers)
      if self.__QadSnapper is not None:
         self.__QadSnapper.setSnapLayers(qad_utils.getSnappableVectorLayers(self.canvas))


   # ============================================================================
   # SnapType
   # ============================================================================
   def setSnapType(self, snapType = None):
      if snapType is None:
         self.__QadSnapper.setSnapType(QadVariables.get(QadMsg.translate("Environment variables", "OSMODE")))
      else:
         self.__QadSnapper.setSnapType(snapType)

      self.__geometryTypesAccordingToSnapType = self.__QadSnapper.getGeometryTypesAccordingToSnapType()
      self.updateLayerCacheOnMapCanvasExtent()


   # ============================================================================
   # getSnapType
   # ============================================================================
   def getSnapType(self):
      return self.__QadSnapper.getSnapType()


   # ============================================================================
   # forceSnapTypeOnce
   # ============================================================================
   def forceSnapTypeOnce(self, snapType = None, snapParams = None):
      self.__oldSnapType = self.__QadSnapper.getSnapType()
      self.__oldSnapProgrDist = self.__QadSnapper.getProgressDistance()

      # if you want to set the perpendicular snap e
      # no starting point has been set
      if snapType == QadSnapTypeEnum.PER and self.__startPoint is None:
         # set the deferred perpendicular snap
         self.setSnapType(QadSnapTypeEnum.PER_DEF)
         return
      # if you want to set the tangent snap e
      # no starting point has been set
      if snapType == QadSnapTypeEnum.TAN and self.__startPoint is None:
         # set the deferred tangent snap
         self.setSnapType(QadSnapTypeEnum.TAN_DEF)
         return

      if snapParams is not None:
         for param in snapParams:
            if param[0] == QadSnapTypeEnum.PR:
               # if you want to set a progressive snap distance
               self.__QadSnapper.setProgressDistance(param[1])

      self.setSnapType(snapType)


   # ============================================================================
   # forceM2P
   # ============================================================================
   def forceM2P(self):
      self.M2P_Mode = True
      self.plugIn.showMsg("\n" + QadMsg.translate("Snap", "First point of mid: "))


   # ============================================================================
   # refreshSnapType
   # ============================================================================
   def refreshSnapType(self):
      self.__oldSnapType = None
      self.__oldSnapProgrDist = None
      self.__QadSnapper.setProgressDistance(QadVariables.get(QadMsg.translate("Environment variables", "OSPROGRDISTANCE")))
      self.setSnapType(QadVariables.get(QadMsg.translate("Environment variables", "OSMODE")))


   # ============================================================================
   # OrthoMode
   # ============================================================================
   def setOrthoMode(self, orthoMode = None):
      if orthoMode is None:
         self.__OrthoMode = QadVariables.get(QadMsg.translate("Environment variables", "ORTHOMODE"))
      else:
         self.__OrthoMode = orthoMode


   # ============================================================================
   # getOrthoCoord
   # ============================================================================
   def getOrthoCoord(self, point):
      if math.fabs(point.x() - self.__startPoint.x()) < \
         math.fabs(point.y() - self.__startPoint.y()):
         return QgsPointXY(self.__startPoint.x(), point.y())
      else:
         return QgsPointXY(point.x(), self.__startPoint.y())


   # ============================================================================
   # refreshOrthoMode
   # ============================================================================
   def refreshOrthoMode(self):
      self.setOrthoMode()


   # ============================================================================
   # AutoSnap
   # ============================================================================
   def setAutoSnap(self, autoSnap = None):
      # sets the variables:
      # self.__AutoSnap, self.__PolarAng, self.__PolarMode, self.__PolarAngOffset, self.__snapMarkerSizeInMapUnits, self.__PolarAddAngles
      # self.__QadSnapper is emptied of polar points if "Object Snap Tracking off"

      if autoSnap is None:
         self.__AutoSnap = QadVariables.get(QadMsg.translate("Environment variables", "AUTOSNAP"))
      else:
         self.__AutoSnap = autoSnap

      if (self.__AutoSnap & QadAUTOSNAPEnum.POLAR_TRACKING) == False: # polar tracking not enabled
         self.__PolarAng = None
         self.__PolarMode = None
         self.__PolarAngOffset = None
         self.__PolarAddAngles = None
      else:
         self.__PolarAng = math.radians(QadVariables.get(QadMsg.translate("Environment variables", "POLARANG")))
         self.__PolarMode = QadVariables.get(QadMsg.translate("Environment variables", "POLARMODE"))
         self.__PolarAngOffset = self.plugIn.lastSegmentAng
         if self.__PolarMode & QadPOLARMODEnum.ADDITIONAL_ANGLES:
            dummy = QadVariables.get(QadMsg.translate("Environment variables", "POLARADDANG"))
            self.__PolarAddAngles = POLARADDANG_to_list(dummy, True) # e.g. "1;2.3" generates the list in ascending order by converting to radians
         else:
            self.__PolarAddAngles = None


      if (self.__AutoSnap & QadAUTOSNAPEnum.OBJ_SNAP_TRACKING) == False: # Object Snap Tracking off
         if self.__QadSnapper is not None:
            self.__QadSnapper.removeOSnapPointsForPolar()

      # calculate the size of snap symbols in map units
      self.__snapMarkerSizeInMapUnits = QadVariables.get(QadMsg.translate("Environment variables", "AUTOSNAPSIZE")) * \
                                        self.canvas.mapSettings().mapUnitsPerPixel()


   def refreshAutoSnap(self):
      self.setAutoSnap()


   # ============================================================================
   # Dynamic Input
   # ============================================================================
   def refreshDynamicInput(self):
      self.dynamicEditInput.refreshOnEnvVariables()


   # ============================================================================
   # AutoSnap
   # ============================================================================
   def setPolarAngOffset(self, polarAngOffset):
      self.__PolarAngOffset = polarAngOffset # to manage the angle relative to the last segment


   # ============================================================================
   # getRealPolarAng
   # ============================================================================
   def getRealPolarAng(self):
      # returns the polar angle that really must be used taking into account the system variables
      if self.__AutoSnap is None: return None
      if (self.__AutoSnap & QadAUTOSNAPEnum.POLAR_TRACKING) == False: return None # polar tracking not enabled

      # the behavior of QAD is the same both for the points of the line being drawn and for the points of osanp
      if (self.__PolarMode & QadPOLARMODEnum.POLAR_TRACKING): # usa POLARANG
         return self.__PolarAng
      else:
         return math.pi / 2 # 90 gradi (ortogonale)


   # ============================================================================
   # getRealPolarAddAngles
   # ============================================================================
   def getRealPolarAddAngles(self):
      # returns the list of additional polar angles that really must be used taking into account the system variables
      if self.__AutoSnap is None: return None
      if (self.__AutoSnap & QadAUTOSNAPEnum.POLAR_TRACKING) == False: return None # polar tracking not enabled

      # the behavior of QAD is the same both for the points of the line being drawn and for the points of osanp
      if (self.__PolarMode & QadPOLARMODEnum.POLAR_TRACKING): # usa POLARANG
         return self.__PolarAng
      else:
         return math.pi / 2 # 90 gradi (ortogonale)


   # ============================================================================
   # getRealPolarAngOffset
   # ============================================================================
   def getRealPolarAngOffset(self):
      # returns the polar offset angle that really must be used taking into account the system variables
      if self.__AutoSnap is None: return None
      if (self.__AutoSnap & QadAUTOSNAPEnum.POLAR_TRACKING) == False: return None # polar tracking not enabled

      if (self.__PolarMode is not None and self.__PolarMode & QadPOLARMODEnum.MEASURE_RELATIVE_ANGLE): # (relative to the angular coefficient of the last segment)
         return self.__PolarAngOffset
      else:
         return 0 # 0 gradi (assoluto)


   # ============================================================================
   # setCursorType
   # ============================================================================
   def setCursorType(self, cursorType):
      if self.__csrRubberBand is not None:
         self.__csrRubberBand.removeItems() # first detach it from the canvas otherwise it will not be removed because it is used by canvas
         del self.__csrRubberBand
      self.__csrRubberBand = QadCursorRubberBand(self.canvas, cursorType)

      if cursorType == QadCursorTypeEnum.NONE:
         self.__cursor = QCursor(Qt.ArrowCursor)
      else:
         self.__cursor = QCursor(Qt.BlankCursor)
      self.__cursorType = cursorType


   # ============================================================================
   # getCursorType
   # ============================================================================
   def getCursorType(self):
      return self.__cursorType


   # ============================================================================
   # moveElastic
   # ============================================================================
   def moveElastic(self, point):
      numberOfVertices = self.__RubberBand.numberOfVertices()
      if numberOfVertices > 0:
         if numberOfVertices == 2:
            # for a bug not yet understood: if the line has only 2 vertices and
            # have the same x or y (horizontal or vertical line)
            # the line is not drawn so I move the x or y a little
            adjustedPoint = qad_utils.getAdjustedRubberBandVertex(self.__RubberBand.getPoint(0, 0), point)
            self.__RubberBand.movePoint(numberOfVertices - 1, adjustedPoint)
         else:
            p1 = self.__RubberBand.getPoint(0, 0)

            # if the objective is to select a selection group
            if self.getSelectionMode() == QadGetPointSelectionModeEnum.ENTITYSET_SELECTION:
               if point.x() > p1.x(): # if the point is to the right of p1 (initial point)
                  self.__RubberBand.setFillColor(self.rectangleWindowSelectionColor)
               else:
                  self.__RubberBand.setFillColor(self.rectangleCrossingSelectionColor)

            adjustedPoint = qad_utils.getAdjustedRubberBandVertex(p1, point)
            self.__RubberBand.movePoint(numberOfVertices - 3, QgsPointXY(p1.x(), adjustedPoint.y()))
            self.__RubberBand.movePoint(numberOfVertices - 2, adjustedPoint)
            self.__RubberBand.movePoint(numberOfVertices - 1, QgsPointXY(adjustedPoint.x(), p1.y()))


   # ============================================================================
   # getStartPoint
   # ============================================================================
   def getStartPoint(self):
      return None if self.__startPoint is None else QgsPointXY(self.__startPoint) # alloca


   # ============================================================================
   # setStartPoint
   # ============================================================================
   def setStartPoint(self, startPoint):
      self.__startPoint = startPoint
      self.__QadSnapper.setStartPoint(startPoint)

      if self.getDrawMode() == QadGetPointDrawModeEnum.ELASTIC_LINE:
         # foreseen use of the elastic line
         self.__RubberBand.reset(QgsWkbTypes.LineGeometry)
         #numberOfVertices = self.__RubberBand.numberOfVertices()
         #if numberOfVertices == 2:
         #   self.__RubberBand.removeLastPoint()
         #   self.__RubberBand.removeLastPoint()
         self.__RubberBand.addPoint(startPoint, False)

         point = self.toMapCoordinates(self.canvas.mouseLastXY()) # posizione
         # for a bug not yet understood: if the line has only 2 vertices and
         # have the same x or y (horizontal or vertical line)
         # the line is not drawn so I move the x or y a little
         point = qad_utils.getAdjustedRubberBandVertex(startPoint, point)

         self.__RubberBand.addPoint(point, True)

         # input dinamico
         self.dynamicEditInput.setPrevPoint(startPoint)
         if self.dynamicEditInput.isActive() and self.dynamicEditInput.isVisible:
            self.dynamicEditInput.show(True, self.canvas.mouseLastXY()) # visualizzo e resetto input dinamico
      elif self.getDrawMode() == QadGetPointDrawModeEnum.ELASTIC_RECTANGLE:
         # expected use of the elastic rectangle
         point = self.toMapCoordinates(self.canvas.mouseLastXY())

         self.__RubberBand.reset(QgsWkbTypes.PolygonGeometry)
         self.__RubberBand.addPoint(startPoint, False)

         # for a bug not yet understood: if the line has only 2 vertices and
         # have the same x or y (horizontal or vertical line)
         # the line is not drawn so I move the x or y a little
         point = qad_utils.getAdjustedRubberBandVertex(startPoint, point)

         self.__RubberBand.addPoint(QgsPointXY(startPoint.x(), point.y()), False)
         self.__RubberBand.addPoint(point, False)
         self.__RubberBand.addPoint(QgsPointXY(point.x(), startPoint.y()), True)

         # input dinamico
         self.dynamicEditInput.setPrevPoint(None)
      else:
         #input dinamico
         self.dynamicEditInput.setPrevPoint(None)


      self.__QadSnapPointsDisplayManager.setStartPoint(startPoint)


   # ============================================================================
   # toggleReferenceLines
   # ============================================================================
   def toggleReferenceLines(self, geom, oSnapPointsForPolar = None, shiftKey = None):
      if self.__stopTimer == False and (geom is not None):
         if self.__QadSnapper is not None:
            if self.__AutoSnap & QadAUTOSNAPEnum.OBJ_SNAP_TRACKING: # if the use of the snap points mode for polar use is enabled
               if self.__PolarMode is not None and self.__PolarMode & QadPOLARMODEnum.SHIFT_TO_ACQUIRE: # acquires snap points for polar use only when shift is pressed
                  useOSnapPointsForPolar = True if shiftKey else False
               else: # acquires snap points for polar use automatically
                  useOSnapPointsForPolar = True
            else: # if NOT enabled the use of the snap points mode for polar use
               useOSnapPointsForPolar = False

            # I take the current position of the mouse because to activate or deactivate the snap points for polar use
            # I have to be inside the snap symbol but this function is activated as soon as I am close to the geometry
            # (see APERTURE system variable) and therefore when the mouse can still be far from the snap point
            point = self.toMapCoordinates(self.canvas.mouseLastXY())
            if useOSnapPointsForPolar:
               self.__QadSnapper.toggleReferenceLines(geom, point, oSnapPointsForPolar, self.__snapMarkerSizeInMapUnits)
            else:
               self.__QadSnapper.toggleReferenceLines(geom, point)

            self.__QadSnapper.toggleIntExtLinearObj(geom, point)


   # ============================================================================
   # magneticCursor
   # ============================================================================
   def magneticCursor(self, oSnapPoints):
      if len(oSnapPoints) > 0:
         for item in oSnapPoints.items():
            for pt in item[1]:
               # the point <point> must be inside the snap point that has dimensions snapMarkerSizeInMapUnits
               if self.tmpPoint.x() >= pt.x() - self.__snapMarkerSizeInMapUnits and \
                  self.tmpPoint.x() <= pt.x() + self.__snapMarkerSizeInMapUnits and \
                  self.tmpPoint.y() >= pt.y() - self.__snapMarkerSizeInMapUnits and \
                  self.tmpPoint.y() <= pt.y() + self.__snapMarkerSizeInMapUnits:
                  self.tmpPoint.set(pt.x(), pt.y())
                  if self.__csrRubberBand is not None:
                     self.__csrRubberBand.moveEvent(self.tmpPoint)


   # ============================================================================
   # canvasMoveEvent
   # ============================================================================
   def canvasMoveEvent(self, event):
      self.tmpPoint = self.toMapCoordinates(event.pos())
      if self.__csrRubberBand is not None:
         self.__csrRubberBand.moveEvent(self.tmpPoint)

      # shift key pressed during mouse movement
      self.tmpShiftKey = True if event.modifiers() & Qt.ShiftModifier else False
      # ctrl key pressed during mouse movement
      self.tmpCtrlKey = True if event.modifiers() & Qt.ControlModifier else False

      # if the objective is to select a point
      if self.getSelectionMode() == QadGetPointSelectionModeEnum.POINT_SELECTION or \
         self.getSelectionMode() == QadGetPointSelectionModeEnum.ENTITYSET_SELECTION:
         return self.canvasMoveEventOnPointSel(event)
      elif self.getSelectionMode() == QadGetPointSelectionModeEnum.NONE:
         self.dynamicEditInput.mouseMoveEvent(event.pos())
      # if the objective is to select one or more entities
      else:
         return self.canvasMoveEventOnEntitySel(event)


   # ============================================================================
   # canvasMoveEventOnEntitySel
   # ============================================================================
   def canvasMoveEventOnEntitySel(self, event):
      self.dynamicEditInput.mouseMoveEvent(event.pos())
      # start = time.time() # test
      self.tmpEntity.clear()

      # start1 = time.time() # test

      # if the goal is to select an entity dynamically
      if self.getSelectionMode() == QadGetPointSelectionModeEnum.ENTITY_SELECTION_DYNAMIC:
         result = qad_utils.getEntSel(event.pos(), self, \
                                      QadVariables.get(QadMsg.translate("Environment variables", "PICKBOX")), \
                                      self.layersToCheck, \
                                      self.checkPointLayer, \
                                      self.checkLineLayer, \
                                      self.checkPolygonLayer, \
                                      True, self.onlyEditableLayers, \
                                      self.lastLayerFound, self.layerCacheGeomsDict)
      else:
         result = None

      #self.tempo1 += ((time.time() - start1) * 1000) # test

      # if a geometry was found
      if result is not None:
         feature = result[0]
         layer = result[1]
         self.lastLayerFound = layer
         self.tmpEntity.set(layer, feature.id())

      if self.getDrawMode() != QadGetPointDrawModeEnum.NONE:
         # foreseen use of the elastic line or elastic rectangle
         self.moveElastic(self.tmpPoint)

      # self.tempo_tot += ((time.time() - start) * 1000) # test


   # ============================================================================
   # canvasMoveEventOnPointSel
   # ============================================================================
   def canvasMoveEventOnPointSel(self, event):
      self.dynamicEditInput.mouseMoveEvent(event.pos())

      # start = time.time() # test
      result = qad_utils.getEntSel(event.pos(), self, \
                                   QadVariables.get(QadMsg.translate("Environment variables", "APERTURE")), \
                                   None, \
                                   self.__geometryTypesAccordingToSnapType[0], \
                                   self.__geometryTypesAccordingToSnapType[1], \
                                   self.__geometryTypesAccordingToSnapType[2], \
                                   True, False, \
                                   self.lastLayerFound, self.layerCacheGeomsDict, True)

      #self.tempo1 += ((time.time() - start1) * 1000) # test

      # if a geometry was found
      if result is not None:
         feature = result[0]
         layer = result[1]
         self.lastLayerFound = layer
         if self.layerCacheGeomsDict is not None:
            self.tmpEntity.set(layer, feature.attribute("index")) # reading the feature from the cache in index I find the code of the real feature
         else:
            self.tmpEntity.set(layer, feature.id()) # reading the feature directly from the class

         geometry = self.tmpEntity.getGeometry(self.canvas.mapSettings().destinationCrs()) # I transform the geometry into map coordinates
         point = self.toMapCoordinates(event.pos()) # I transform the point from screen coordinates to map coordinates

         oSnapPoints = self.__QadSnapper.getSnapPoint(self.tmpEntity, point, \
                                                      None, \
                                                      self.getRealPolarAng(), \
                                                      self.getRealPolarAngOffset(), \
                                                      self.__PolarAddAngles)

         if self.__AutoSnap & QadAUTOSNAPEnum.MAGNET: # Turns on the AutoSnap magnet
            self.magneticCursor(oSnapPoints)

         # if a geometry different from the one previously selected has been selected
         if geometry is not None and ((self.__prevGeom is None) or not self.__prevGeom.equals(geometry)):
            self.__prevGeom = QgsGeometry(geometry)
            runToggleReferenceLines = lambda: self.toggleReferenceLines(self.__prevGeom, oSnapPoints, self.tmpShiftKey)
            self.__stopTimer = False
            QTimer.singleShot(500, runToggleReferenceLines)
         elif geometry is None:
            self.__prevGeom = None
            self.__stopTimer = True
      else: # if a geometry was NOT found
         # start1 = time.time() # test

         # if no object was found then check if a tmpGeometries geometry falls into the openings box
         boxSize = QadVariables.get(QadMsg.translate("Environment variables", "APERTURE")) # I read the size of the square (in pixels)
         tmpGeometry = qad_utils.getGeomInBox(event.pos(),
                                              self, \
                                              self.tmpGeometries, \
                                              boxSize, \
                                              None, \
                                              self.__geometryTypesAccordingToSnapType[0], \
                                              self.__geometryTypesAccordingToSnapType[1], \
                                              self.__geometryTypesAccordingToSnapType[2], \
                                              True)

         #self.tempo2 += ((time.time() - start1) * 1000) # test

         if tmpGeometry is not None:
            oSnapPoints = self.__QadSnapper.getSnapPoint(tmpGeometry, self.tmpPoint, \
                                                         None, \
                                                         self.getRealPolarAng(), \
                                                         self.getRealPolarAngOffset(), \
                                                         self.__PolarAddAngles, \
                                                         True)

            if self.__AutoSnap & QadAUTOSNAPEnum.MAGNET: # Turns on the AutoSnap magnet
               self.magneticCursor(oSnapPoints)

            # if a geometry different from the one previously selected has been selected
            if tmpGeometry is not None and ((self.__prevGeom is None) or not self.__prevGeom.equals(tmpGeometry)):
               self.__prevGeom = QgsGeometry(tmpGeometry)
               runToggleReferenceLines = lambda: self.toggleReferenceLines(self.__prevGeom, \
                                                                           oSnapPoints, self.tmpShiftKey)
               self.__stopTimer = False
               QTimer.singleShot(500, runToggleReferenceLines)
         else: # if a temporary geometry has NOT been found (the same one you are drawing)
            oSnapPoints = self.__QadSnapper.getSnapPoint(None, self.tmpPoint, \
                                                         None, \
                                                         self.getRealPolarAng(), \
                                                         self.getRealPolarAngOffset(), \
                                                        self.__PolarAddAngles)

            if self.__AutoSnap & QadAUTOSNAPEnum.MAGNET: # Turns on the AutoSnap magnet
               self.magneticCursor(oSnapPoints)

            self.__prevGeom = None
            self.__stopTimer = True

      oSnapPoint = None

      # I display the snap point
      self.__QadSnapPointsDisplayManager.show(oSnapPoints, \
                                              self.__QadSnapper.getExtLinearObjs(), \
                                              self.__QadSnapper.getParLines(), \
                                              self.__QadSnapper.getIntExtLinearObjs(), \
                                              self.__QadSnapper.getOSnapPointsForPolar(), \
                                              self.__QadSnapper.getOSnapLinesForPolar())

      self.point = None
      self.tmpPoint = None
      # I store the snap point in point (I take the first valid one)
      for item in oSnapPoints.items():
         points = item[1]
         if points is not None:
            self.tmpPoint = points[0]
            oSnapPoint = points[0]
            break

      # if no osnap point was found
      if self.tmpPoint is None:
         # if you are using dynamic input that returns a timely result
         if self.dynamicEditInput.isActive() and self.dynamicEditInput.isVisible and \
            (self.dynamicEditInput.inputType & QadInputTypeEnum.POINT2D or self.dynamicEditInput.inputType & QadInputTypeEnum.POINT3D) and \
            self.dynamicEditInput.refreshResult(event.pos()) == True:
            self.tmpPoint = QgsPointXY(self.dynamicEditInput.resPt)
         else: # I take the point directly from the mouse
            self.tmpPoint = self.toMapCoordinates(event.pos())

      if oSnapPoint is None: # if there is no osnap point
         if self.__startPoint is not None: # if there is a starting point
            if self.tmpShiftKey == False: # if shift is not pressed
               if self.__OrthoMode == 1: # orto attivato
                  self.tmpPoint = self.getOrthoCoord(self.tmpPoint)
            else: # if shift is not pressed I have to toggle ortho
               if self.__OrthoMode == 0: # if ortho disabled activates it temporarily
                  self.tmpPoint = self.getOrthoCoord(self.tmpPoint)

      if self.getDrawMode() != QadGetPointDrawModeEnum.NONE:
         # foreseen use of the elastic line or elastic rectangle
         self.moveElastic(self.tmpPoint)

      # self.tempo_tot += ((time.time() - start) * 1000) # test


   # ============================================================================
   # canvasPressEvent
   # ============================================================================
   def canvasPressEvent(self, event):
      # shift key pressed during mouse click
      self.shiftKey = True if event.modifiers() & Qt.ShiftModifier else False

      # ctrl key pressed during mouse click
      self.ctrlKey = True if event.modifiers() & Qt.ControlModifier else False

      # volevo mettere questo evento nel canvasReleaseEvent
      # but the right click does not generate that type of event
      if event.button() == Qt.RightButton:
         self.startDateTimeForRightClick = datetime.datetime.now()
         self.rightButton = True
         return # I leave here to not continue the command from map tool

      if event.button() == Qt.LeftButton:
         self.rightButton = False

         if self.getSelectionMode() == QadGetPointSelectionModeEnum.ENTITY_SELECTION_DYNAMIC or \
            self.getSelectionMode() == QadGetPointSelectionModeEnum.ENTITY_SELECTION:
            self.tmpPoint = self.toMapCoordinates(event.pos())
            result = qad_utils.getEntSel(event.pos(), self, \
                                         QadVariables.get(QadMsg.translate("Environment variables", "PICKBOX")), \
                                         self.layersToCheck, \
                                         self.checkPointLayer, \
                                         self.checkLineLayer, \
                                         self.checkPolygonLayer, \
                                         True, self.onlyEditableLayers, \
                                         self.lastLayerFound) # I don't use self.layerCacheGeomsDict because if I have snaps disabled self.layerCacheGeomsDict is empty
            if result is not None:
               feature = result[0]
               layer = result[1]
               self.tmpEntity.set(layer, feature.id())

         self.__QadSnapper.removeReferenceLines()
         self.__QadSnapPointsDisplayManager.hide()

         self.__setPoint(event)

         if self.__oldSnapType is not None:
            self.setSnapType(self.__oldSnapType) # I report the previous value
            self.__QadSnapper.setProgressDistance(self.__oldSnapProgrDist)

      if self.M2P_Mode == True: # "midpoint between 2 points" mode
         if self.M2p_pt1 is None:
            self.M2p_pt1 = self.point
            self.plugIn.showMsg(QadMsg.translate("Snap", "Second point of mid: "))
         else:
            self.M2P_Mode = False
            self.point = qad_utils.getMiddlePoint(self.M2p_pt1, self.point)
            self.M2p_pt1 = None
            self.plugIn.setLastPoint(self.point)
            self.plugIn.QadCommands.continueCommandFromMapTool()
      else:
         self.plugIn.QadCommands.continueCommandFromMapTool()
         #self.plugIn.setStandardMapTool()


   # ============================================================================
   # canvasReleaseEvent
   # ============================================================================
   def canvasReleaseEvent(self, event):
      if event.button() == Qt.RightButton:
         self.rightButton = True
         # If the CTRL (or META) key was pressed
         if ((event.modifiers() & Qt.ControlModifier) or (event.modifiers() & Qt.MetaModifier)):
            self.displayOsnapPopupMenu(event.pos())
            return # I leave here to not continue the command from map tool

         actualCommand = self.plugIn.QadCommands.actualCommand
         if actualCommand is not None:
            contextualMenu = actualCommand.getCurrentContextualMenu()
         else:
            contextualMenu = None

         shortCutMenu = QadVariables.get(QadMsg.translate("Environment variables", "SHORTCUTMENU"))
         if shortCutMenu == 0 or contextualMenu is None:
            # equivale a premere INVIO
            return self.plugIn.showEvaluateMsg(None)

         # 16 = Enables the display of a shortcut menu when the right button on the pointing device is held down long enough
         if shortCutMenu & 16:
            now = datetime.datetime.now()
            value = QadVariables.get(QadMsg.translate("Environment variables", "SHORTCUTMENUDURATION"))
            shortCutMenuDuration = datetime.timedelta(0, 0, 0, value)
            # if it exceeds the number of milliseconds set by SHORTCUTMENUDURATION
            if now - self.startDateTimeForRightClick > shortCutMenuDuration:
               contextualMenu.popup(self.canvas.mapToGlobal(event.pos()))
               return # I leave here to not continue the command from map tool
            else:
               return self.plugIn.showEvaluateMsg(None)
         else:
            # 4 = Enables Command mode shortcut menus whenever a command is active.
            if shortCutMenu & 4:
               contextualMenu.popup(self.canvas.mapToGlobal(event.pos()))
               return # I leave here to not continue the command from map tool
            else:
               # 8 = Enables Command mode shortcut menus only when command options are currently available at the Command prompt.
               if shortCutMenu & 8 and contextualMenu is not None and len(contextualMenu.localKeyWords)>0:
                  contextualMenu.popup(self.canvas.mapToGlobal(event.pos()))
               else:
                  # equivale a premere INVIO
                  return self.plugIn.showEvaluateMsg(None)

      # if the objective is to select a rectangle
      if self.getDrawMode() == QadGetPointDrawModeEnum.ELASTIC_RECTANGLE:
         if event.button() == Qt.LeftButton:
            p1 = self.__RubberBand.getPoint(0, 0)
            # if the mouse is in a position other than the starting point of the rectangle
            if p1 != self.toMapCoordinates(event.pos()):
               self.__QadSnapper.removeReferenceLines()
               self.__QadSnapPointsDisplayManager.hide()

               self.__setPoint(event)

               self.rightButton = False

               if self.__oldSnapType is not None:
                  self.setSnapType(self.__oldSnapType) # I report the previous value
                  self.__QadSnapper.setProgressDistance(self.__oldSnapProgrDist)

               # shift key pressed during mouse click
               self.shiftKey = True if event.modifiers() & Qt.ShiftModifier else False

               # ctrl key pressed during mouse click
               self.ctrlKey = True if event.modifiers() & Qt.ControlModifier else False

               self.plugIn.QadCommands.continueCommandFromMapTool()
               #self.plugIn.setStandardMapTool()


   # ============================================================================
   # __setPoint
   # ============================================================================
   def __setPoint(self, event):
      # if the mouse had never been moved
      if self.tmpPoint is None:
         self.canvasMoveEvent(event)

      self.point = self.tmpPoint
      self.plugIn.setLastPoint(self.point)
      self.snapTypeOnSelection = self.getSnapType() # snap attivo al momento del click
      if self.tmpEntity.isInitialized():
         self.entity.set(self.tmpEntity.layer, self.tmpEntity.featureId)
      else:
         self.entity.clear()


   # ============================================================================
   # keyPressEvent
   # ============================================================================
   def keyPressEvent(self, e):
      myEvent = e
      # ALTGR cannot be used because it is used to indicate coordinates
#       # if Key_AltGr is pressed, then perform the as return
#       if e.key() == Qt.Key_AltGr:
#          myEvent = QKeyEvent(QEvent.KeyPress, Qt.Key_Return, Qt.NoModifier)
#       else:
#          myEvent = e

      self.plugIn.keyPressEvent(myEvent)


   # ============================================================================
   # activate
   # ============================================================================
   def activate(self):
      self.canvas.setToolTip("")

      if self.__csrRubberBand is not None:
         # current mouse position
         self.__csrRubberBand.moveEvent(self.toMapCoordinates(self.canvas.mouseLastXY()))
         self.__csrRubberBand.show()

      self.point = None
      self.tmpPoint = None

      self.entity = QadEntity() # entity selected by the click
      self.tmpEntity = QadEntity() # entity selected by mouse movement

      self.snapTypeOnSelection = None # snap attivo al momento del click

      self.shiftKey = False
      self.tmpShiftKey = False # shift key pressed during mouse movement

      self.ctrlKey = False
      self.tmpCtrlKey = False # ctrl key pressed during mouse movement

      self.rightButton = False
      self.canvas.setCursor(self.__cursor)
      self.showPointMapToolMarkers()
      self.plugIn.disableShortcut()

      self.dynamicEditInput.show(True)


   # ============================================================================
   # deactivate
   # ============================================================================
   def deactivate(self):
      try: # necessary because if you close QGIS this event starts even though the map tool object is no longer there!
         if self.__csrRubberBand is not None:
            self.__csrRubberBand.hide()
         self.hidePointMapToolMarkers()
         self.plugIn.enableShortcut()

         self.dynamicEditInput.show(False)
      except:
         pass


   # ============================================================================
   # isTransient
   # ============================================================================
   def isTransient(self): # Check whether this MapTool performs a zoom or pan operation
      return False


   # ============================================================================
   # isEditTool
   # ============================================================================
   def isEditTool(self):
      # although this tool makes editing return False because every time I select a feature
      # with the function QgsVectorLayer::select(QgsFeatureId featureId)
      # the call to isEditTool of the current tool starts in sequence and if it returns true it is deactivated
      # and then reactivated QadMapTool which resumes the interrupted command, creating a mess
      #return True # 2016
      return False


   # ============================================================================
   # displayOsnapPopupMenu
   # ============================================================================
   def displayOsnapPopupMenu(self, pos):
      popupMenu = QMenu(self.canvas)

      msg = QadMsg.translate("Snap", "Midpoint between 2 points")
      icon = QIcon(":/plugins/qad/icons/osnap_mid2p.svg")
      if icon is None:
         addEndLineSnapTypeAction = QAction(msg, popupMenu)
      else:
         addEndLineSnapTypeAction = QAction(icon, msg, popupMenu)
      addEndLineSnapTypeAction.triggered.connect(self.addM2PActionByPopupMenu)
      popupMenu.addAction(addEndLineSnapTypeAction)

      msg = QadMsg.translate("DSettings_Dialog", "Start / End")
      icon = QIcon(":/plugins/qad/icons/osnap_endLine.svg")
      if icon is None:
         addEndLineSnapTypeAction = QAction(msg, popupMenu)
      else:
         addEndLineSnapTypeAction = QAction(icon, msg, popupMenu)
      addEndLineSnapTypeAction.triggered.connect(self.addEndLineSnapTypeByPopupMenu)
      popupMenu.addAction(addEndLineSnapTypeAction)

      msg = QadMsg.translate("DSettings_Dialog", "Segment Start / End")
      icon = QIcon(":/plugins/qad/icons/osnap_end.svg")
      if icon is None:
         addEndSnapTypeAction = QAction(msg, popupMenu)
      else:
         addEndSnapTypeAction = QAction(icon, msg, popupMenu)
      addEndSnapTypeAction.triggered.connect(self.addEndSnapTypeByPopupMenu)
      popupMenu.addAction(addEndSnapTypeAction)

      msg = QadMsg.translate("DSettings_Dialog", "Middle point")
      icon = QIcon(":/plugins/qad/icons/osnap_mid.svg")
      if icon is None:
         addMidSnapTypeAction = QAction(msg, popupMenu)
      else:
         addMidSnapTypeAction = QAction(icon, msg, popupMenu)
      addMidSnapTypeAction.triggered.connect(self.addMidSnapTypeByPopupMenu)
      popupMenu.addAction(addMidSnapTypeAction)

      msg = QadMsg.translate("DSettings_Dialog", "Intersection")
      icon = QIcon(":/plugins/qad/icons/osnap_int.svg")
      if icon is None:
         addIntSnapTypeAction = QAction(msg, popupMenu)
      else:
         addIntSnapTypeAction = QAction(icon, msg, popupMenu)
      addIntSnapTypeAction.triggered.connect(self.addIntSnapTypeByPopupMenu)
      popupMenu.addAction(addIntSnapTypeAction)

      msg = QadMsg.translate("DSettings_Dialog", "Intersection on extension")
      icon = QIcon(":/plugins/qad/icons/osnap_extInt.svg")
      if icon is None:
         addExtIntSnapTypeAction = QAction(msg, popupMenu)
      else:
         addExtIntSnapTypeAction = QAction(icon, msg, popupMenu)
      addExtIntSnapTypeAction.triggered.connect(self.addExtIntSnapTypeByPopupMenu)
      popupMenu.addAction(addExtIntSnapTypeAction)

      msg = QadMsg.translate("DSettings_Dialog", "Extend")
      icon = QIcon(":/plugins/qad/icons/osnap_ext.svg")
      if icon is None:
         addExtSnapTypeAction = QAction(msg, popupMenu)
      else:
         addExtSnapTypeAction = QAction(icon, msg, popupMenu)
      addExtSnapTypeAction.triggered.connect(self.addExtSnapTypeByPopupMenu)
      popupMenu.addAction(addExtSnapTypeAction)

      popupMenu.addSeparator()

      msg = QadMsg.translate("DSettings_Dialog", "Center")
      icon = QIcon(":/plugins/qad/icons/osnap_cen.svg")
      if icon is None:
         addCenSnapTypeAction = QAction(msg, popupMenu)
      else:
         addCenSnapTypeAction = QAction(icon, msg, popupMenu)
      addCenSnapTypeAction.triggered.connect(self.addCenSnapTypeByPopupMenu)
      popupMenu.addAction(addCenSnapTypeAction)

      msg = QadMsg.translate("DSettings_Dialog", "Quadrant")
      icon = QIcon(":/plugins/qad/icons/osnap_qua.svg")
      if icon is None:
         addQuaSnapTypeAction = QAction(msg, popupMenu)
      else:
         addQuaSnapTypeAction = QAction(icon, msg, popupMenu)
      addQuaSnapTypeAction.triggered.connect(self.addQuaSnapTypeByPopupMenu)
      popupMenu.addAction(addQuaSnapTypeAction)

      msg = QadMsg.translate("DSettings_Dialog", "Tangent")
      icon = QIcon(":/plugins/qad/icons/osnap_tan.svg")
      if icon is None:
         addTanSnapTypeAction = QAction(msg, popupMenu)
      else:
         addTanSnapTypeAction = QAction(icon, msg, popupMenu)
      addTanSnapTypeAction.triggered.connect(self.addTanSnapTypeByPopupMenu)
      popupMenu.addAction(addTanSnapTypeAction)

      popupMenu.addSeparator()

      msg = QadMsg.translate("DSettings_Dialog", "Perpendicular")
      icon = QIcon(":/plugins/qad/icons/osnap_per.svg")
      if icon is None:
         addPerSnapTypeAction = QAction(msg, popupMenu)
      else:
         addPerSnapTypeAction = QAction(icon, msg, popupMenu)
      addPerSnapTypeAction.triggered.connect(self.addPerSnapTypeByPopupMenu)
      popupMenu.addAction(addPerSnapTypeAction)

      msg = QadMsg.translate("DSettings_Dialog", "Parallel")
      icon = QIcon(":/plugins/qad/icons/osnap_par.svg")
      if icon is None:
         addParSnapTypeAction = QAction(msg, popupMenu)
      else:
         addParSnapTypeAction = QAction(icon, msg, popupMenu)
      addParSnapTypeAction.triggered.connect(self.addParSnapTypeByPopupMenu)
      popupMenu.addAction(addParSnapTypeAction)

      msg = QadMsg.translate("DSettings_Dialog", "Node")
      icon = QIcon(":/plugins/qad/icons/osnap_nod.svg")
      if icon is None:
         addNodSnapTypeAction = QAction(msg, popupMenu)
      else:
         addNodSnapTypeAction = QAction(icon, msg, popupMenu)
      addNodSnapTypeAction.triggered.connect(self.addNodSnapTypeByPopupMenu)
      popupMenu.addAction(addNodSnapTypeAction)

      msg = QadMsg.translate("DSettings_Dialog", "Near")
      icon = QIcon(":/plugins/qad/icons/osnap_nea.svg")
      if icon is None:
         addNeaSnapTypeAction = QAction(msg, popupMenu)
      else:
         addNeaSnapTypeAction = QAction(icon, msg, popupMenu)
      addNeaSnapTypeAction.triggered.connect(self.addNeaSnapTypeByPopupMenu)
      popupMenu.addAction(addNeaSnapTypeAction)

      msg = QadMsg.translate("DSettings_Dialog", "Progressive")
      icon = QIcon(":/plugins/qad/icons/osnap_pr.svg")
      if icon is None:
         addPrSnapTypeAction = QAction(msg, popupMenu)
      else:
         addPrSnapTypeAction = QAction(icon, msg, popupMenu)
      addPrSnapTypeAction.triggered.connect(self.addPrSnapTypeByPopupMenu)
      popupMenu.addAction(addPrSnapTypeAction)

      msg = QadMsg.translate("DSettings_Dialog", "None")
      icon = QIcon(":/plugins/qad/icons/osnap_disable.svg")
      if icon is None:
         setSnapTypeToDisableAction = QAction(msg, popupMenu)
      else:
         setSnapTypeToDisableAction = QAction(icon, msg, popupMenu)
      setSnapTypeToDisableAction.triggered.connect(self.setSnapTypeToDisableByPopupMenu)
      popupMenu.addAction(setSnapTypeToDisableAction)

      popupMenu.addSeparator()

      msg = QadMsg.translate("DSettings_Dialog", "Object snap settings...")
      icon = QIcon(":/plugins/qad/icons/dsettings.svg")
      if icon is None:
         DSettingsAction = QAction(msg, popupMenu)
      else:
         DSettingsAction = QAction(icon, msg, popupMenu)
      DSettingsAction.triggered.connect(self.showDSettingsByPopUpMenu)
      popupMenu.addAction(DSettingsAction)

      popupMenu.popup(self.canvas.mapToGlobal(pos))


   # ============================================================================
   # addSnapTypeByPopupMenu
   # ============================================================================
   def addSnapTypeByPopupMenu(self, _snapType):
      # the function should only set object snap temporarily
      str = snapTypeEnum2Str(_snapType)
      self.plugIn.showEvaluateMsg(str)
      return
#       value = QadVariables.get(QadMsg.translate("Environment variables", "OSMODE"))
#       if value & QadSnapTypeEnum.DISABLE:
#          value =  value - QadSnapTypeEnum.DISABLE
#       QadVariables.set(QadMsg.translate("Environment variables", "OSMODE"), value | _snapType)
#       QadVariables.save()
#       self.refreshSnapType()


   def addM2PActionByPopupMenu(self):
      self.plugIn.showEvaluateMsg("_M2P")
   def addEndLineSnapTypeByPopupMenu(self):
      self.addSnapTypeByPopupMenu(QadSnapTypeEnum.END_PLINE)
   def addEndSnapTypeByPopupMenu(self):
      self.addSnapTypeByPopupMenu(QadSnapTypeEnum.END)
   def addMidSnapTypeByPopupMenu(self):
      self.addSnapTypeByPopupMenu(QadSnapTypeEnum.MID)
   def addIntSnapTypeByPopupMenu(self):
      self.addSnapTypeByPopupMenu(QadSnapTypeEnum.INT)
   def addExtIntSnapTypeByPopupMenu(self):
      self.addSnapTypeByPopupMenu(QadSnapTypeEnum.EXT_INT)
   def addExtSnapTypeByPopupMenu(self):
      self.addSnapTypeByPopupMenu(QadSnapTypeEnum.EXT)
   def addCenSnapTypeByPopupMenu(self):
      self.addSnapTypeByPopupMenu(QadSnapTypeEnum.CEN)
   def addQuaSnapTypeByPopupMenu(self):
      self.addSnapTypeByPopupMenu(QadSnapTypeEnum.QUA)
   def addTanSnapTypeByPopupMenu(self):
      self.addSnapTypeByPopupMenu(QadSnapTypeEnum.TAN)
   def addPerSnapTypeByPopupMenu(self):
      self.addSnapTypeByPopupMenu(QadSnapTypeEnum.PER)
   def addParSnapTypeByPopupMenu(self):
      self.addSnapTypeByPopupMenu(QadSnapTypeEnum.PAR)
   def addNodSnapTypeByPopupMenu(self):
      self.addSnapTypeByPopupMenu(QadSnapTypeEnum.NOD)
   def addNeaSnapTypeByPopupMenu(self):
      self.addSnapTypeByPopupMenu(QadSnapTypeEnum.NEA)
   def addPrSnapTypeByPopupMenu(self):
      self.addSnapTypeByPopupMenu(QadSnapTypeEnum.PR)


   # ============================================================================
   # setSnapTypeToDisableByPopupMenu
   # ============================================================================
   def setSnapTypeToDisableByPopupMenu(self):
      value = QadVariables.get(QadMsg.translate("Environment variables", "OSMODE"))
      QadVariables.set(QadMsg.translate("Environment variables", "OSMODE"), value | QadSnapTypeEnum.DISABLE)
      QadVariables.save()
      self.refreshSnapType()


   # ============================================================================
   # showDSettingsByPopUpMenu
   # ============================================================================
   def showDSettingsByPopUpMenu(self):
      d = QadDSETTINGSDialog(self.plugIn, QadDSETTINGSTabIndexEnum.OBJECT_SNAP)
      d.exec()
      self.refreshSnapType()
      self.refreshAutoSnap()
      self.setPolarAngOffset(self.plugIn.lastSegmentAng)
      self.refreshDynamicInput()


   # ============================================================================
   # mapToLayerCoordinates
   # ============================================================================
   def mapToLayerCoordinates(self, layer, point_geom):
      # transform point or geometry coordinates from output CRS to layer's CRS
      if self.canvas is None:
         return None
      if type(point_geom) == QgsPointXY:
         return self.canvas.mapSettings().mapToLayerCoordinates(layer, point_geom)
      elif type(point_geom) == QgsGeometry:
         fromCrs = self.canvas.mapSettings().destinationCrs()
         toCrs = layer.crs()

         if fromCrs == toCrs:
            return QgsGeometry(point_geom)

         # I transform the geometry in the canvas crs to work with xy plane coordinates
         coordTransform = QgsCoordinateTransform(self.canvas.mapSettings().destinationCrs(), \
                                                 layer.crs(), \
                                                 QgsProject.instance())
         g = QgsGeometry(point_geom)
         g.transform(coordTransform)
         return g
      else:
         return None


   # ============================================================================
   # layerToMapCoordinates
   # ============================================================================
   def layerToMapCoordinates(self, layer, point_geom):
      # transform point or geometry coordinates from layer's CRS to output CRS
      if self.canvas is None:
         return None
      if type(point_geom) == QgsPointXY:
         return self.canvas.mapSettings().layerToMapCoordinates(layer, point_geom)
      elif type(point_geom) == QgsGeometry:
         # I transform the geometry in the canvas crs to work with xy plane coordinates
         coordTransform = QgsCoordinateTransform(layer.crs(), \
                                                 self.canvas.mapSettings().destinationCrs(), \
                                                 QgsProject.instance())
         g = QgsGeometry(point_geom)
         g.transform(coordTransform)
         return g
      else:
         return None
