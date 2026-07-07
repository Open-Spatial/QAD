# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 command to insert into other commands for feature selection

                              -------------------
        begin                : 2013-09-18
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
from qgis.core import QgsWkbTypes, QgsPointXY


from .qad_generic_cmd import QadCommandClass
from ..qad_msg import QadMsg
from ..qad_textwindow import QadInputTypeEnum, QadInputModeEnum
from ..qad_entity import QadEntity
from ..qad_getpoint import QadGetPointSelectionModeEnum
from .. import qad_utils
from ..qad_dim import QadDimStyles
from ..qad_variables import QadVariables


# ===============================================================================
# QadEntSelClass
# ===============================================================================
class QadEntSelClass(QadCommandClass):
   """This class selects an entity. It is not able to select a dimension but only a component of a dimension."""

   def instantiateNewCmd(self):
      """instantiates a new command of the same type"""
      return QadEntSelClass(self.plugIn)

   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      self.entity = QadEntity()
      self.point = None
      # options to limit the objects to select
      self.onlyEditableLayers = False
      self.checkPointLayer = True
      self.checkLineLayer = True
      self.checkPolygonLayer = True
      self.checkDimLayers = True
      self.selDimEntity = False # to return a QadDimEntity object or not
      self.msg = QadMsg.translate("QAD", "Select object: ")
      self.deselectOnFinish = False
      self.canceledByUsr = False # becomes true if the user does not want to choose anything (e.g. if the right mouse button is used)

   def __del__(self):
      QadCommandClass.__del__(self)
      if self.deselectOnFinish:
         self.entity.deselectOnLayer()


   # ============================================================================
   # setEntity
   # ============================================================================
   def setEntity(self, layer, fid):
      del self.entity
      if self.selDimEntity: # whether a QadDimEntity object can be returned
         # check if the entity belongs to a dimensioning style
         self.entity = QadDimStyles.getDimEntity(layer, fid)
         if self.entity is None: # if it is not a dimension
            self.entity = QadEntity()
            self.entity.set(layer, fid)
      else:
         self.entity = QadEntity()
         self.entity.set(layer, fid)

      self.entity.selectOnLayer()


   # ============================================================================
   # getLayersToCheck
   # ============================================================================
   def getLayersToCheck(self):
      layerList = []
      for layer in qad_utils.getVisibleVectorLayers(self.plugIn.canvas): # All vector layers visible
         # I only consider vector layers that are filtered by type
         if ((layer.geometryType() == QgsWkbTypes.PointGeometry and self.checkPointLayer == True) or \
             (layer.geometryType() == QgsWkbTypes.LineGeometry and self.checkLineLayer == True) or \
             (layer.geometryType() == QgsWkbTypes.PolygonGeometry and self.checkPolygonLayer == True)) and \
             (self.onlyEditableLayers == False or layer.isEditable()):
            # if I need to include dimension layers
            if self.checkDimLayers == True or \
               len(QadDimStyles.getDimListByLayer(layer)) == 0:
               layerList.append(layer)

      return layerList


   def run(self, msgMapTool = False, msg = None):
      if self.plugIn.canvas.mapSettings().destinationCrs().isGeographic():
         self.showMsg(QadMsg.translate("QAD", "\nThe coordinate reference system of the project must be a projected coordinate system.\n"))
         return True # end command

      # =========================================================================
      # POINT or ENTITY REQUEST
      if self.step == 0: # start of command
         # set the map tool
         self.getPointMapTool().setSelectionMode(QadGetPointSelectionModeEnum.ENTITY_SELECTION)
         # set the layers to check on the map tool
         self.getPointMapTool().layersToCheck = self.getLayersToCheck()

         keyWords = QadMsg.translate("Command_ENTSEL", "Last")

         englishKeyWords = "Last"
         keyWords += "_" + englishKeyWords
         # is preparing to wait for a point or Enter or a keyword
         # msg, inputType, default, keyWords, no check
         self.waitFor(self.msg, \
                      QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                      None, \
                      keyWords, QadInputModeEnum.NONE)

         self.step = 1
         return False

      # =========================================================================
      # RESPONSE TO THE POINT or ENTITY REQUEST
      elif self.step == 1: # after waiting for a point the command restarts
         entity = None
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if while selecting a point
            # Another plugin was activated which deactivated Qad
            # so the command that returns here has been reactivated without the map tool
            # has selected a point
            if self.getPointMapTool().point is None: # the map tool was activated without a dot
               if self.getPointMapTool().rightButton == True: # if used with the right mouse button
                  self.canceledByUsr = True
                  return True # end command
               else:
                  self.setMapTool(self.getPointMapTool()) # I reactivate the map tool
                  return False

            value = self.getPointMapTool().point
            if self.getPointMapTool().entity.isInitialized():
               entity = self.getPointMapTool().entity
         else: # the dot comes as a parameter of the function
            value = msg

         if value is None:
            self.canceledByUsr = True
            return True # end command

         if type(value) == unicode:
            if value == QadMsg.translate("Command_ENTSEL", "Last") or value == "Last":
               # Select the last inserted entity
               lastEnt = self.plugIn.getLastEntity()
               if lastEnt is not None:
                  # layer control
                  if self.onlyEditableLayers == False or lastEnt.layer.isEditable() == True:
                     # type check
                     if (self.checkPointLayer == True and lastEnt.layer.geometryType() == QgsWkbTypes.PointGeometry) or \
                        (self.checkLineLayer == True and lastEnt.layer.geometryType() == QgsWkbTypes.LineGeometry) or \
                        (self.checkPolygonLayer == True and lastEnt.layer.geometryType() == QgsWkbTypes.PolygonGeometry):
                        # layer control of dimensions
                        if self.checkDimLayers == True or QadDimStyles.isDimEntity(lastEnt) == False:
                           self.setEntity(lastEnt.layer, lastEnt.featureId)
         elif type(value) == QgsPointXY:
            if entity is None:
               # I searc if there are entities in the indicated point
               result = qad_utils.getEntSel(self.getPointMapTool().toCanvasCoordinates(value),
                                            self.getPointMapTool(), \
                                            QadVariables.get(QadMsg.translate("Environment variables", "PICKBOX")), \
                                            self.getLayersToCheck())
               if result is not None:
                  feature = result[0]
                  layer = result[1]
                  self.setEntity(layer, feature.id())
            else:
               self.setEntity(entity.layer, entity.featureId)

            self.point = value

         if self.deselectOnFinish:
            self.entity.deselectOnLayer()

         return True # end command
