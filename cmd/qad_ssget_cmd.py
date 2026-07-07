# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 command to insert into other commands for selecting a group of features

                              -------------------
        begin                : 2013-05-22
        copyright            : iiiii
        email                : hhhhh
        developers           : bbbbb aaaaa ggggg
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
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


from ..qad_variables import QadVariables
from .qad_generic_cmd import QadCommandClass
from ..qad_msg import QadMsg
from ..qad_textwindow import QadInputTypeEnum, QadInputModeEnum
from ..qad_entity import QadEntitySet, getSelSet
from ..qad_dim import QadDimStyles
from ..qad_getpoint import QadGetPointDrawModeEnum, QadGetPointSelectionModeEnum
from .qad_pline_cmd import QadPLINECommandClass
from .qad_circle_cmd import QadCIRCLECommandClass, QadCircle
from .qad_mpolygon_cmd import QadMPOLYGONCommandClass
from ..qad_dynamicinput import QadDynamicInputContextEnum
# this import had to be moved to the end because qad_mbuffer_cmd imports qad_ssget_cmd
#from qad_mbuffer_cmd import QadMBUFFERCommandClass
from ..qad_utils import getVisibleVectorLayers, distMapToLayerCoordinates
from ..qad_rubberband import getColorForCrossingSelectionArea, \
                             getColorForWindowSelectionArea

# ===============================================================================
# QadSSGetClass
# ===============================================================================
class QadSSGetClass(QadCommandClass):
# Class that manages the selection of geometric objects

   def instantiateNewCmd(self):
      """instantiates a new command of the same type"""
      return QadSSGetClass(self.plugIn)

   def __init__(self, plugIn):
      self.init(plugIn)

   def __del__(self):
      QadCommandClass.__del__(self)
      #self.entitySet.deselectOnLayer()
      if self.PLINECommand is not None: del self.PLINECommand
      if self.CIRCLECommand is not None: del self.CIRCLECommand
      if self.MPOLYGONCommand is not None: del self.MPOLYGONCommand
      if self.MBUFFERCommand is not None: del self.MBUFFERCommand
      if self.SSGetClass is not None: del self.SSGetClass


   def init(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      self.AddOnSelection = True # if = False means remove
      self.entitySet = QadEntitySet()
      self.points = []
      self.currSelectionMode = ""
      # options to limit the objects to select
      self.onlyEditableLayers = False
      self.checkPointLayer = True
      self.checkLineLayer = True
      self.checkPolygonLayer = True
      self.checkDimLayers = True # includes all the features that make up the selected dimensions

      self.help = False
      # if SingleSelection = True the first indicated object or group of objects is selected,
      # without requiring any other selections.
      self.SingleSelection = False
      self.pickAdd = QadVariables.get(QadMsg.translate("Environment variables", "PICKADD"))

      # if exitAfterSelection = True the command is terminated after any selection
      # regardless of whether or not an object or group of objects has been selected.
      # used by QadVirtualSelCommandClass
      self.exitAfterSelection = False

      # selection of objects most recently added to the selection set (x cancel option)
      self.lastEntitySet = QadEntitySet()
      self.PLINECommand = None
      self.CIRCLECommand = None
      self.MPOLYGONCommand = None
      self.MBUFFERCommand = None
      self.SSGetClass = None

   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      if self.step == 4: # when you are in the line drawing phase
         return self.PLINECommand.getPointMapTool(drawMode)
      elif self.step == 5: # when you are drawing a circle
         return self.CIRCLECommand.getPointMapTool(drawMode)
      elif self.step == 6: # when you are in the entity selection phase
         return self.SSGetClass.getPointMapTool(drawMode)
      elif self.step == 7: # when you are drawing a polygon
         return self.MPOLYGONCommand.getPointMapTool(drawMode)
      elif self.step == 8: # when you are in the buffer drawing phase
         return self.MBUFFERCommand.getPointMapTool(drawMode)
      else:
         ptMapTool = QadCommandClass.getPointMapTool(self, drawMode)
         #ptMapTool.setSnapType(QadSnapTypeEnum.DISABLE) I do not understand why
         ptMapTool.setOrthoMode(0)
         return ptMapTool


   def getCurrentContextualMenu(self):
      if self.step == 4: # when you are in the line drawing phase
         return self.PLINECommand.getCurrentContextualMenu()
      elif self.step == 5: # when you are drawing a circle
         return self.CIRCLECommand.getCurrentContextualMenu()
      elif self.step == 6: # when you are in the entity selection phase
         return None # return self.SSGetClass.getCurrentContextualMenu()
      elif self.step == 7: # when you are drawing a polygon
         return self.MPOLYGONCommand.getCurrentContextualMenu()
      elif self.step == 8: # when you are in the buffer drawing phase
         return self.MBUFFERCommand.getCurrentContextualMenu()
      else:
         return self.contextualMenu


   # ============================================================================
   # getLayersToCheck
   # ============================================================================
   def getLayersToCheck(self):
      layerList = []
      for layer in getVisibleVectorLayers(self.plugIn.canvas): # All vector layers visible
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


   # ============================================================================
   # showMsgOnAddRemove
   # ============================================================================
   def showMsgOnAddRemove(self, found):
      msg = QadMsg.translate("Command_SSGET", " found {0}, total {1}")
      self.showMsg(msg.format(found, self.entitySet.count()), False) # does not repeat the 2016 prompt


   # ============================================================================
   # elaborateEntity
   # ============================================================================
   def elaborateEntity(self, entity, shiftKey):
      if self.AddOnSelection == True: # add to selection set
         if shiftKey: # if the selection was made with shift pressed
            if self.pickAdd == 0: # The objects most recently selected become the selection set
               if self.entitySet.containsEntity(entity): # if the entity had already been selected
                  self.AddRemoveEntity(entity, False) # remove the entity
               else:
                  self.AddRemoveEntity(entity, True) # add the entity
            else:
               self.AddRemoveEntity(entity, False) # remove the entity
         else: # without shift key
            if self.pickAdd == 0: # The objects most recently selected become the selection set
               self.SetEntity(entity)
            else:
               self.AddRemoveEntity(entity, True) # add the entity
      else: # if you need to remove it from the selection group
         self.AddRemoveEntity(entity, False) # remove the entity


   # ============================================================================
   # SetEntity
   # ============================================================================
   def SetEntity(self, entity):
      # layer control
      if self.onlyEditableLayers == True and entity.layer.isEditable() == False:
         self.showMsgOnAddRemove(0)
         return
      # type check
      if (self.checkPointLayer == False and entity.layer.geometryType() == QgsWkbTypes.PointGeometry) or \
         (self.checkLineLayer == False and entity.layer.geometryType() == QgsWkbTypes.LineGeometry) or \
         (self.checkPolygonLayer == False and entity.layer.geometryType() == QgsWkbTypes.PolygonGeometry):
         self.showMsgOnAddRemove(0)
         return

      # layer control of dimensions
      # check if the entity belongs to a dimensioning style
      dimEntity = QadDimStyles.getDimEntity(entity)
      if self.checkDimLayers == False and dimEntity is not None:
         self.showMsgOnAddRemove(0)
         return

      self.entitySet.deselectOnLayer()
      self.entitySet.clear()
      self.entitySet.addEntity(entity)

      if self.checkDimLayers == True and dimEntity is not None:
         # add the dimensioning components to set <entitySet>
         self.entitySet.unite(dimEntity.getEntitySet())

      self.showMsgOnAddRemove(self.entitySet.count())
      self.entitySet.selectOnLayer(False) # incremental = False aaaaaaaaaaaaaaaaaaaaaaaa here the activate event of qad_map tool starts (if the layer is not being edited)
      self.lastEntitySet.clear()
      self.lastEntitySet.addEntity(entity)


   # ============================================================================
   # AddRemoveEntity
   # ============================================================================
   def AddRemoveEntity(self, entity, Add):
      # layer control
      if self.onlyEditableLayers == True and entity.layer.isEditable() == False:
         self.showMsgOnAddRemove(0)
         return
      # type check
      if (self.checkPointLayer == False and entity.layer.geometryType() == QgsWkbTypes.PointGeometry) or \
         (self.checkLineLayer == False and entity.layer.geometryType() == QgsWkbTypes.LineGeometry) or \
         (self.checkPolygonLayer == False and entity.layer.geometryType() == QgsWkbTypes.PolygonGeometry):
         self.showMsgOnAddRemove(0)
         return
      # layer control of dimensions
      if self.checkDimLayers == False and len(QadDimStyles.getDimListByLayer(entity.layer)) > 0:
         self.showMsgOnAddRemove(0)
         return

      self.entitySet.deselectOnLayer()
      if Add == True: # add to selection set
         self.entitySet.addEntity(entity)
      else: # remove from selection set
         self.entitySet.removeEntity(entity)

      if self.checkDimLayers == True:
         dimEntitySet = QadEntitySet()
         dimEntitySet.addEntity(entity)
         # The function checks whether the entities that are part of an entitySet are also part of dimensioning and,
         # if true, adds/removes all dimension components to/from the entitySet.
         QadDimStyles.addAllDimComponentsToEntitySet(dimEntitySet, self.onlyEditableLayers)
         if Add == True: # add to selection set
            self.entitySet.unite(dimEntitySet)
         else: # remove from selection set
            self.entitySet.subtract(dimEntitySet)
         self.showMsgOnAddRemove(dimEntitySet.count())
      else:
         self.showMsgOnAddRemove(1)

      self.entitySet.selectOnLayer(False) # incremental = False
      self.lastEntitySet.clear()
      self.lastEntitySet.addEntity(entity)


   # ============================================================================
   # elaborateSelSet
   # ============================================================================
   def elaborateSelSet(self, selSet, shiftKey):
      if self.checkDimLayers == True:
         dimEntitySet = QadEntitySet(selSet)
         # The function checks whether the entities that are part of an entitySet are also part of dimensioning and,
         # if true, adds all dimension components to the entitySet.
         QadDimStyles.addAllDimComponentsToEntitySet(dimEntitySet, self.onlyEditableLayers)
         selSet.unite(dimEntitySet)

      if self.AddOnSelection == True: # add to selection set
         if shiftKey: # if the selection was made with shift pressed
            if self.pickAdd == 0: # The objects most recently selected become the selection set
               # check if there are any objects not yet selected
               intersectSS = QadEntitySet(selSet)
               intersectSS.subtract(self.entitySet)
               if intersectSS.isEmpty(): # all objects were already selected
                  self.AddRemoveSelSet(selSet, False) # I remove the selection group
               else:
                  self.AddRemoveSelSet(selSet, True) # add the selection group
            else:
               self.AddRemoveSelSet(selSet, False) # I remove the selection group
         else: # without shift key
            if self.pickAdd == 0: # The objects most recently selected become the selection set
               self.SetSelSet(selSet)
            else:
               self.AddRemoveSelSet(selSet, True) # add the selection group
      else: # if you need to remove it from the selection group
         self.AddRemoveSelSet(selSet, False) # I remove the selection group


   # ============================================================================
   # SetSelSet
   # ============================================================================
   def SetSelSet(self, selSet):
      for layerEntitySet in self.entitySet.layerEntitySetList:
         # if the layer is not present in selSet
         if selSet.findLayerEntitySet(layerEntitySet) is None:
            layerEntitySet.deselectOnLayer()
         else:
            layerEntitySet.deselectOnLayer()

      self.entitySet.set(selSet)

      self.showMsgOnAddRemove(self.entitySet.count())
      self.entitySet.selectOnLayer(False) # incremental = False
      self.lastEntitySet.set(selSet)


   # ============================================================================
   # AddCurrentQgsSelectedFeatures
   # ============================================================================
   def AddCurrentQgsSelectedFeatures(self):
      # check if there are entities currently selected
      self.entitySet.initByCurrentQgsSelectedFeatures(self.getLayersToCheck())
      found = self.entitySet.count()
      if found > 0:
         msg = QadMsg.translate("Command_SSGET", "\nfound {0}")
         self.showMsg(msg.format(found), False) # does not repeat the prompt
         return True
      else:
         return False


   # ============================================================================
   # AddRemoveSelSet
   # ============================================================================
   def AddRemoveSelSet(self, selSet, Add):
      self.entitySet.deselectOnLayer()
      if Add == True: # add to selection set
         self.entitySet.unite(selSet)
      else: # remove from selection set
         self.entitySet.subtract(selSet)

      self.showMsgOnAddRemove(selSet.count())

      self.entitySet.selectOnLayer(False) # incremental = False
      self.lastEntitySet.set(selSet)

   # ============================================================================
   # AddRemoveSelSetByFence
   # ============================================================================
   def AddRemoveSelSetByFence(self, points):
      if len(points) > 1:
         selSet = getSelSet("F", self.getPointMapTool(), points, \
                                      self.getLayersToCheck())
         self.elaborateSelSet(selSet, False)

   # ============================================================================
   # AddRemoveSelSetByPolygon
   # ============================================================================
   def AddRemoveSelSetByPolygon(self, mode, points):
      if len(points) > 2:
         selSet = getSelSet(mode, self.getPointMapTool(), points, \
                                      self.getLayersToCheck())
         self.elaborateSelSet(selSet, False)

   # ============================================================================
   # AddRemoveSelSetByGeometry
   # ============================================================================
   def AddRemoveSelSetByGeometry(self, mode, geom):
      if type(geom) == QgsGeometry: # single geometry
         selSet = getSelSet(mode, self.getPointMapTool(), geom, \
                                      self.getLayersToCheck())
      else: # list of geometries
         selSet = QadEntitySet()
         for g in geom:
            partial = getSelSet(mode, self.getPointMapTool(), g, \
                                          self.getLayersToCheck())
            selSet.unite(partial)
      self.elaborateSelSet(selSet, False)


   # ============================================================================
   # WaitForFirstPoint
   # ============================================================================
   def WaitForFirstPoint(self):
      self.step = 1

      # "Finestra" "Ultimo" "Interseca"
      # "Riquadro" "Tutto" "iNTercetta"
      # "FPoligono" "IPoligono"
      # "FCerchio" "ICerchio"
      # "FOggetti" "IOggetti"
      # "FBuffer" "IBuffer"
      # "AGgiungi" "Elimina"
      # "Precedente" "Annulla"
      # "AUto" "SIngolo" "Help"
      keyWords = QadMsg.translate("Command_SSGET", "Window") + "/" + \
                 QadMsg.translate("Command_SSGET", "Last") + "/" + \
                 QadMsg.translate("Command_SSGET", "Crossing") + "/" + \
                 QadMsg.translate("Command_SSGET", "Box") + "/" + \
                 QadMsg.translate("Command_SSGET", "All") + "/" + \
                 QadMsg.translate("Command_SSGET", "Fence") + "/" + \
                 QadMsg.translate("Command_SSGET", "WPolygon") + "/" + \
                 QadMsg.translate("Command_SSGET", "CPolygon") + "/" + \
                 QadMsg.translate("Command_SSGET", "WCircle") + "/" + \
                 QadMsg.translate("Command_SSGET", "CCircle") + "/" + \
                 QadMsg.translate("Command_SSGET", "WObjects") + "/" + \
                 QadMsg.translate("Command_SSGET", "CObjects") + "/" + \
                 QadMsg.translate("Command_SSGET", "WBuffer") + "/" + \
                 QadMsg.translate("Command_SSGET", "CBuffer") + "/" + \
                 QadMsg.translate("Command_SSGET", "Add") + "/" + \
                 QadMsg.translate("Command_SSGET", "Remove") + "/" + \
                 QadMsg.translate("Command_SSGET", "Previous") + "/" + \
                 QadMsg.translate("Command_SSGET", "Undo") + "/" + \
                 QadMsg.translate("Command_SSGET", "AUto") + "/" + \
                 QadMsg.translate("Command_SSGET", "SIngle") + "/" + \
                 QadMsg.translate("Command_SSGET", "Help")
      englishKeyWords = "Window" + "/" + "Last" + "/" + "Crossing" + "/" + "Box" + "/" \
                         + "All" + "/" + "Fence" + "/" + "WPolygon" + "/" + "CPolygon" + "/" \
                         + "WCircle" + "/" + "CCircle" + "/" + "WObjects" + "/" + "CObjects" + "/" \
                         + "WBuffer" + "/" + "CBuffer" + "/" + "Add" + "/" + "Remove" + "/" \
                         + "Previous" + "/" + "Undo" + "/" + "AUto" + "/" + "SIngle" + "/" + "Help"

      if self.AddOnSelection == True:
         prompt = QadMsg.translate("Command_SSGET", "Select Objects")
      else:
         prompt = QadMsg.translate("Command_SSGET", "Remove objects")

      if self.help == True:
         prompt = prompt + QadMsg.translate("Command_SSGET", " or [{0}]").format(keyWords)

      prompt = prompt + QadMsg.translate("Command_SSGET", ": ")

      # set the map tool
      self.getPointMapTool().setSelectionMode(QadGetPointSelectionModeEnum.ENTITY_SELECTION)
      self.getPointMapTool().setDrawMode(QadGetPointDrawModeEnum.NONE)
      # set the layers to check on the map tool
      self.getPointMapTool().layersToCheck = self.getLayersToCheck()
      self.points = []

      keyWords += "_" + englishKeyWords
      # is preparing to wait for a point or Enter or a keyword
      # msg, inputType, default, keyWords, no check
      self.waitFor(prompt, \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                   None, \
                   keyWords, QadInputModeEnum.NONE)
      # input dinamico
      di = self.getPointMapTool().getDynamicInput()
      di.context = QadDynamicInputContextEnum.NONE
      di.showInputMsg(prompt, QadInputTypeEnum.NONE)
      return

   def run(self, msgMapTool = False, msg = None):
      # returns:
      # True for unfinished selection
      # False for selection terminated
      if self.plugIn.canvas.mapSettings().destinationCrs().isGeographic():
         self.showMsg(QadMsg.translate("QAD", "\nThe coordinate reference system of the project must be a projected coordinate system.\n"))
         return True # errore

      # =========================================================================
      # FIRST POINT REQUEST FOR OBJECT SELECTION
      if self.step == 0:
         # if you can also select objects before you start a command
         if QadVariables.get(QadMsg.translate("Environment variables", "PICKFIRST")) == 1:
            if self.AddCurrentQgsSelectedFeatures() == True:
               self.plugIn.setLastEntitySet(self.entitySet)
               return True;
         self.WaitForFirstPoint()
         return False # continua

      # =========================================================================
      # RESPONSE TO THE FIRST POINT REQUEST FOR OBJECT SELECTION
      elif self.step == 1: # after waiting for a point or Enter or a keyword the command is restarted
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if while selecting a point
            # Another plugin was activated which deactivated Qad
            # so the command that returns here has been reactivated without the map tool
            # has selected a point
            if self.getPointMapTool().point is None: # the map tool was activated without a dot
               if self.getPointMapTool().rightButton == True: # if used with the right mouse button
                  if self.entitySet.count() > 0:
                     self.plugIn.setLastEntitySet(self.entitySet)
                  return True # end
               else:
                  self.setMapTool(self.getPointMapTool()) # I reactivate the map tool
                  return False # continua

            shiftKey = self.getPointMapTool().shiftKey

            # if an entity has been selected
            if self.getPointMapTool().entity.isInitialized():
               value = self.getPointMapTool().entity
            else:
               value = self.getPointMapTool().point
         else: # the dot comes as a parameter of the function
            shiftKey = False
            value = msg

         if value is None:
            if self.entitySet.count() > 0:
               self.plugIn.setLastEntitySet(self.entitySet)
            return True # end

         if type(value) == unicode:
            self.currSelectionMode = value

            if value == QadMsg.translate("Command_SSGET", "Window") or value == "Window" or \
               value == QadMsg.translate("Command_SSGET", "Crossing") or value == "Crossing":
               # "Window" = Selects all objects that are completely inside a rectangle defined by two points
               # "Intersect" = Select objects that intersect or are within an area defined by two points
               # set the map tool
               self.getPointMapTool().setSelectionMode(QadGetPointSelectionModeEnum.POINT_SELECTION)
               self.getPointMapTool().setDrawMode(QadGetPointDrawModeEnum.NONE)
               # is preparing to wait for a point
               self.waitForPoint(QadMsg.translate("Command_SSGET", "First corner: "))
               self.step = 2
            if value == QadMsg.translate("Command_SSGET", "Last") or value == "Last":
               # Select the last inserted entity
               if self.plugIn.getLastEntity() is None:
                  self.showMsgOnAddRemove(0)
               else:
                  self.AddRemoveEntity(self.plugIn.getLastEntity(), self.AddOnSelection)
                  if self.SingleSelection == True and self.entitySet.count() > 0:
                     self.plugIn.setLastEntitySet(self.entitySet)
                     return True # end

               if self.exitAfterSelection == True:
                  return True # end

               self.WaitForFirstPoint()
            elif value == QadMsg.translate("Command_SSGET", "Box") or value == "Box":
               # Selects all objects that intersect or are within a rectangle specified by two points.
               # If the points of the rectangle are specified from right to left, Box is equivalent to Intersect,
               # otherwise it is equivalent to Window
               # set the map tool
               self.getPointMapTool().setSelectionMode(QadGetPointSelectionModeEnum.POINT_SELECTION)
               self.getPointMapTool().setDrawMode(QadGetPointDrawModeEnum.NONE)
               # is preparing to wait for a point
               self.waitForPoint(QadMsg.translate("Command_SSGET", "First corner: "))
               self.step = 2
            elif value == QadMsg.translate("Command_SSGET", "All") or value == "All":
               # Select all objects
               selSet = getSelSet("X", self.getPointMapTool(), None, \
                                            self.getLayersToCheck())
               self.elaborateSelSet(selSet, False)
               if self.SingleSelection == True and self.entitySet.count() > 0:
                  self.plugIn.setLastEntitySet(self.entitySet)
                  return True # end

               if self.exitAfterSelection == True:
                  return True # end

               self.WaitForFirstPoint()
            elif value == QadMsg.translate("Command_SSGET", "Fence") or value == "Fence":
               # Select all objects that intersect a polyline
               self.PLINECommand = QadPLINECommandClass(self.plugIn)
               # if this flag = True the command is used within another command to draw a line
               # which will not be saved on a layer
               self.PLINECommand.virtualCmd = True
               self.PLINECommand.run(msgMapTool, msg)
               self.step = 4
            elif value == QadMsg.translate("Command_SSGET", "WPolygon") or value == "WPolygon" or \
                 value == QadMsg.translate("Command_SSGET", "CPolygon") or value == "CPolygon":
               # "FPolygon" = Selects objects that are completely inside a polygon defined by points
               # "IPolygon" = Select objects that intersect or lie within a polygon defined by specifying points
               self.MPOLYGONCommand = QadMPOLYGONCommandClass(self.plugIn)
               # if this flag = True the command is used within another command to draw a line
               # which will not be saved on a layer
               self.MPOLYGONCommand.virtualCmd = True

               if value == QadMsg.translate("Command_SSGET", "WPolygon") or value == "WPolygon":
                  self.MPOLYGONCommand.setRubberBandColor(None, getColorForWindowSelectionArea())
               else:
                  self.MPOLYGONCommand.setRubberBandColor(None, getColorForCrossingSelectionArea())

               self.MPOLYGONCommand.run(msgMapTool, msg)
               self.step = 7
            elif value == QadMsg.translate("Command_SSGET", "WCircle") or value == "WCircle" or \
                 value == QadMsg.translate("Command_SSGET", "CCircle") or value == "CCircle":
               # "FCircle" = Select objects that are completely inside a circle
               # "ICircle" = Select objects that intersect or are within a circle
               self.CIRCLECommand = QadCIRCLECommandClass(self.plugIn)
               # if this flag = True the command is used within another command to draw a circle
               # which will not be saved on a layer
               self.CIRCLECommand.virtualCmd = True

               if value == QadMsg.translate("Command_SSGET", "WCircle") or value == "WCircle":
                  self.CIRCLECommand.setRubberBandColor(None, getColorForWindowSelectionArea())
               else:
                  self.CIRCLECommand.setRubberBandColor(None, getColorForCrossingSelectionArea())

               self.CIRCLECommand.run(msgMapTool, msg)
               self.step = 5
            elif value == QadMsg.translate("Command_SSGET", "WObjects") or value == "WObjects" or \
                 value == QadMsg.translate("Command_SSGET", "CObjects") or value == "CObjects":
               # "Objects" = Select objects that are completely inside objects to select
               # "IObjects" = Select objects that intersect or are within objects to select
               self.SSGetClass = QadSSGetClass(self.plugIn)
               self.SSGetClass.run(msgMapTool, msg)
               self.step = 6
            elif value == QadMsg.translate("Command_SSGET", "WBuffer") or value == "WBuffer" or \
                 value == QadMsg.translate("Command_SSGET", "CBuffer") or value == "CBuffer":
               # this import had to be moved because qad_mbuffer_cmd imports qad_ssget_cmd
               from .qad_mbuffer_cmd import QadMBUFFERCommandClass

               # "FBuffer" = Select objects that are completely within buffers around objects to select
               # "IBuffer" = Select objects that intersect or are within buffers around objects to select
               self.MBUFFERCommand = QadMBUFFERCommandClass(self.plugIn)
               # if this flag = True the command is used within another command to draw a circle
               # which will not be saved on a layer
               self.MBUFFERCommand.virtualCmd = True

               if value == QadMsg.translate("Command_SSGET", "WBuffer") or value == "WBuffer":
                  self.MBUFFERCommand.setRubberBandColor(None, getColorForWindowSelectionArea())
               else:
                  self.MBUFFERCommand.setRubberBandColor(None, getColorForCrossingSelectionArea())

               self.MBUFFERCommand.run(msgMapTool, msg)
               self.step = 8
            elif value == QadMsg.translate("Command_SSGET", "Add") or value == "Add":
               # Switch to Add method: The selected objects can be added to the selection set
               self.AddOnSelection = True
               self.WaitForFirstPoint()
            elif value == QadMsg.translate("Command_SSGET", "Remove") or value == "Remove":
               # Switch to Remove method: Objects can be removed from the selection set
               self.AddOnSelection = False
               self.WaitForFirstPoint()
            elif value == QadMsg.translate("Command_SSGET", "Previous") or value == "Previous":
               # Select the latest selection group
               if self.plugIn.lastEntitySet is None:
                  self.showMsgOnAddRemove(0)
               else:
                  entitySet = QadEntitySet()
                  entitySet.set(self.plugIn.lastEntitySet)
                  # layer control
                  if self.onlyEditableLayers == True:
                     entitySet.removeNotEditable()
                  # type check
                  if self.checkPointLayer == False:
                     entitySet.removeGeomType(QgsWkbTypes.PointGeometry)
                  if self.checkLineLayer == False:
                     entitySet.removeGeomType(QgsWkbTypes.LineGeometry)
                  if self.checkPolygonLayer == False:
                     entitySet.removeGeomType(QgsWkbTypes.PolygonGeometry)
                  # controllo sulle dimensionture
                  if self.checkDimLayers == False:
                     QadDimStyles.removeAllDimLayersFromEntitySet(entitySet)

                  entitySet.removeNotExisting()
                  self.elaborateSelSet(entitySet, False)
                  if self.SingleSelection == True and self.entitySet.count() > 0:
                     self.plugIn.setLastEntitySet(self.entitySet)
                     return True # end

               if self.exitAfterSelection == True:
                  return True # end

               self.WaitForFirstPoint()
            elif value == QadMsg.translate("Command_SSGET", "Undo") or value == "Undo":
               # Clears the selection of the object most recently added to the selection set.
               # I reverse the selection type
               prevAddOnSelection = self.AddOnSelection
               self.AddOnSelection = not self.AddOnSelection
               self.elaborateSelSet(self.lastEntitySet, False)
               # Reset selection type
               self.AddOnSelection = prevAddOnSelection
               if self.SingleSelection == True and self.entitySet.count() > 0:
                  self.plugIn.setLastEntitySet(self.entitySet)
                  return True # end

               if self.exitAfterSelection == True:
                  return True # end

               self.WaitForFirstPoint()
            elif value == QadMsg.translate("Command_SSGET", "AUto") or value == "AUto":
               # Switch to automatic selection: the objects over which the pointer is positioned are selected.
               # By clicking on an empty area inside or outside an object,
               # creates the first corner of a selection rectangle, as with the Box method
               self.SingleSelection = False
               self.WaitForFirstPoint()
            elif value == QadMsg.translate("Command_SSGET", "SIngle") or value == "SIngle":
               # Switch to Single method: the first indicated object or group of objects is selected,
               # without requiring any other selections.
               self.SingleSelection = True
               if self.entitySet.count() > 0:
                  self.plugIn.setLastEntitySet(self.entitySet)
                  return True # end
               self.WaitForFirstPoint()
            elif value == QadMsg.translate("Command_SSGET", "Help") or value == "Help":
               self.help = True
               self.WaitForFirstPoint()
         elif type(value) == QgsPointXY: # if the starting point of the rectangle has been inserted
            self.currSelectionMode = QadMsg.translate("Command_SSGET", "Box")
            self.points.append(value)

            self.getPointMapTool().setSelectionMode(QadGetPointSelectionModeEnum.ENTITYSET_SELECTION)
            self.getPointMapTool().setDrawMode(QadGetPointDrawModeEnum.ELASTIC_RECTANGLE)
            self.getPointMapTool().setStartPoint(value)

            # is preparing to wait for a point
            self.waitForPoint(QadMsg.translate("Command_SSGET", "Specify opposite corner: "))
            self.step = 3
         else: # if an entity has been selected
            self.elaborateEntity(value, shiftKey)

            if self.SingleSelection == True and self.entitySet.count() > 0:
               self.plugIn.setLastEntitySet(self.entitySet)
               return True # end

            if self.exitAfterSelection == True:
               return True # end

            self.WaitForFirstPoint()

         return False # continua

      # =========================================================================
      # RESPONSE TO THE REQUEST FOR THE FIRST POINT OF THE OPTION RECTANGLE
      # FINESTRA, INTERSECA, RIQUADRO (da step = 1)
      elif self.step == 2: # after waiting for a point the command restarts
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if while selecting a point
            # Another plugin was activated which deactivated Qad
            # so the command that returns here has been reactivated without the map tool
            # has selected a point
            if self.getPointMapTool().point is None: # the map tool was activated without a dot
               if self.getPointMapTool().rightButton == True: # if used with the right mouse button
                  self.showMsg(QadMsg.translate("Command_SSGET", "Window not correct."))
                  self.WaitForFirstPoint()
                  return False
               else:
                  self.setMapTool(self.getPointMapTool()) # I reactivate the map tool
                  return False

            value = self.getPointMapTool().point
         else: # the dot comes as a parameter of the function
            value = msg

         if type(value) == QgsPointXY:
            self.points.append(value)
            self.getPointMapTool().setSelectionMode(QadGetPointSelectionModeEnum.ENTITYSET_SELECTION)
            self.getPointMapTool().setDrawMode(QadGetPointDrawModeEnum.ELASTIC_RECTANGLE)

            # change the color set by setDrawMode
            if self.currSelectionMode == QadMsg.translate("Command_SSGET", "Window") or value == "Window":
               self.getPointMapTool().rectangleCrossingSelectionColor = self.getPointMapTool().rectangleWindowSelectionColor
            elif self.currSelectionMode == QadMsg.translate("Command_SSGET", "Crossing") or value == "Crossing":
                self.getPointMapTool().rectangleWindowSelectionColor = self.getPointMapTool().rectangleCrossingSelectionColor

            self.rectangleCrossingSelectionColor = getColorForCrossingSelectionArea()
            self.rectangleWindowSelectionColor = getColorForWindowSelectionArea()

            self.getPointMapTool().setStartPoint(value)
            # is preparing to wait for a point
            self.waitForPoint(QadMsg.translate("Command_SSGET", "Specify opposite corner: "))
            self.step = 3
         else:
            self.showMsg(QadMsg.translate("Command_SSGET", "Window not correct."))
            self.WaitForFirstPoint()

         return False # continua


      # =========================================================================
      # RESPONSE TO THE REQUEST OF THE SECOND POINT OF THE RECTANGLE (from step = 1)
      elif self.step == 3: # after waiting for a point the command restarts
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if while selecting a point
            # Another plugin was activated which deactivated Qad
            # so the command that returns here has been reactivated without the map tool
            # has selected a point
            if self.getPointMapTool().point is None: # the map tool was activated without a dot
               if self.getPointMapTool().rightButton == True: # if used with the right mouse button
                  self.showMsg(QadMsg.translate("Command_SSGET", "Window not correct."))
                  # is preparing to wait for a point
                  self.waitForPoint(QadMsg.translate("Command_SSGET", "Specify opposite corner: "))
                  return False
               else:
                  self.setMapTool(self.getPointMapTool()) # I reactivate the map tool
                  return False

            shiftKey = self.getPointMapTool().shiftKey
            value = self.getPointMapTool().point
         else: # the dot comes as a parameter of the function
            shiftKey = False
            value = msg

         if type(value) == QgsPointXY:
            self.getPointMapTool().clear()
            self.points.append(value)

            if self.currSelectionMode == QadMsg.translate("Command_SSGET", "Box") or \
               self.currSelectionMode == "Box":
               if self.points[0].x() < value.x():
                  mode = "W"
               else:
                  mode = "C"
            elif self.currSelectionMode == QadMsg.translate("Command_SSGET", "Window") or \
               self.currSelectionMode == "Window":
               mode = "W"
            else: # "Interseca"
               mode = "C"

            selSet = getSelSet(mode, self.getPointMapTool(), self.points, \
                                         self.getLayersToCheck())
            self.elaborateSelSet(selSet, shiftKey)

            if self.SingleSelection == True and self.entitySet.count() > 0:
               self.plugIn.setLastEntitySet(self.entitySet)
               return True # end

            if self.exitAfterSelection == True:
               return True # end

            self.WaitForFirstPoint()
         else:
            self.showMsg(QadMsg.translate("Command_SSGET", "Window not correct."))
            # is preparing to wait for a point
            self.waitForPoint(QadMsg.translate("Command_SSGET", "Specify opposite corner: "))

         return False # continua


      # =========================================================================
      # RESPONSE TO THE POINT REQUEST FOR INTERCEPTION MODE (from step = 1 or 4)
      elif self.step == 4: # after waiting for a point the command restarts
         if self.PLINECommand.run(msgMapTool, msg) == True:
            self.showMsg("\n")
            self.AddRemoveSelSetByFence(self.PLINECommand.polyline.asPolyline())
            del self.PLINECommand
            self.PLINECommand = None

            if self.SingleSelection == True and self.entitySet.count() > 0:
               self.plugIn.setLastEntitySet(self.entitySet)
               return True # end

            if self.exitAfterSelection == True:
               return True # end

            self.WaitForFirstPoint()
         return False


      # =========================================================================
      # RESPONSE TO THE REQUEST FOR FC CIRCLE and IC CIRCLE MODES (from step = 1 or 5)
      elif self.step == 5: # after waiting for a point the command restarts
         if self.CIRCLECommand.run(msgMapTool, msg) == True:
            self.showMsg("\n")
            if (self.CIRCLECommand.centerPt is not None) and \
               (self.CIRCLECommand.radius is not None):
               circle = QadCircle()
               circle.set(self.CIRCLECommand.centerPt, self.CIRCLECommand.radius)
               points = circle.asPolyline()
               if self.currSelectionMode == QadMsg.translate("Command_SSGET", "WCircle") or \
                  self.currSelectionMode == "WCircle":
                  self.AddRemoveSelSetByPolygon("WP", points)
               elif self.currSelectionMode == QadMsg.translate("Command_SSGET", "CCircle") or \
                  self.currSelectionMode == "CCircle":
                  self.AddRemoveSelSetByPolygon("CP", points)

            del self.CIRCLECommand
            self.CIRCLECommand = None

            if self.SingleSelection == True and self.entitySet.count() > 0:
               self.plugIn.setLastEntitySet(self.entitySet)
               return True # end

            if self.exitAfterSelection == True:
               return True # end

            self.WaitForFirstPoint()
         return False


      # =========================================================================
      # RESPONSE TO THE REQUEST FOR SELECTION OF OBJECTS FOR SHEETS and IOBJECTS MODE (from step = 1 or 6)
      elif self.step == 6: # after waiting for a point the command restarts
         if self.SSGetClass.run(msgMapTool, msg) == True:
            self.showMsg("\n")
            destCRS = self.SSGetClass.getPointMapTool().canvas.mapSettings().destinationCrs()
            geoms = self.SSGetClass.entitySet.getGeometryCollection(destCRS) # I transform the geometry

            if self.currSelectionMode == QadMsg.translate("Command_SSGET", "WObjects") or \
               self.currSelectionMode == "WObjects":
               self.AddRemoveSelSetByGeometry("WO", geoms)
            elif self.currSelectionMode == QadMsg.translate("Command_SSGET", "CObjects") or \
               self.currSelectionMode == "CObjects":
               self.AddRemoveSelSetByGeometry("CO", geoms)

            del self.SSGetClass
            self.SSGetClass = None

            if self.SingleSelection == True and self.entitySet.count() > 0:
               self.plugIn.setLastEntitySet(self.entitySet)
               return True # end

            if self.exitAfterSelection == True:
               return True # end

            self.WaitForFirstPoint()
         return False


      # =========================================================================
      # RESPONSE TO THE REQUEST FOR FPOLIGON and IPOLIGON MODES (from step = 1 or 7)
      elif self.step == 7: # after waiting for a point the command restarts
         if self.MPOLYGONCommand.run(msgMapTool, msg) == True:
            self.showMsg("\n")
            if self.currSelectionMode == QadMsg.translate("Command_SSGET", "WPolygon") or \
               self.currSelectionMode == "WPolygon":
               self.AddRemoveSelSetByPolygon("WP", self.MPOLYGONCommand.PLINECommand.polyline.asPolyline())
            elif self.currSelectionMode == QadMsg.translate("Command_SSGET", "CPolygon") or \
               self.currSelectionMode == "CPolygon":
               self.AddRemoveSelSetByPolygon("CP", self.MPOLYGONCommand.PLINECommand.polyline.asPolyline())

            del self.MPOLYGONCommand
            self.MPOLYGONCommand = None

            if self.SingleSelection == True and self.entitySet.count() > 0:
               self.plugIn.setLastEntitySet(self.entitySet)
               return True # end

            if self.exitAfterSelection == True:
               return True # end

            self.WaitForFirstPoint()
         return False


      # =========================================================================
      # RESPONSE TO THE OBJECT SELECTION REQUEST FOR FBUFFER and IBUFFER MODES (from step = 1 or 8)
      elif self.step == 8: # after waiting for a point the command restarts
         if self.MBUFFERCommand.run(msgMapTool, msg) == True:
            self.showMsg("\n")

            bufferGeoms = []
            for layerEntitySet in self.MBUFFERCommand.entitySet.layerEntitySetList:
               geoms = layerEntitySet.getGeometryCollection()
               width = distMapToLayerCoordinates(self.MBUFFERCommand.width, \
                                                           self.MBUFFERCommand.getPointMapTool().canvas,\
                                                           layerEntitySet.layer)
               for geom in geoms:
                  bufferGeoms.append(geom.buffer(width, self.MBUFFERCommand.segments))

            if self.currSelectionMode == QadMsg.translate("Command_SSGET", "WBuffer") or \
               self.currSelectionMode == "WBuffer":
               self.AddRemoveSelSetByGeometry("WO", bufferGeoms)
            elif self.currSelectionMode == QadMsg.translate("Command_SSGET", "CBuffer") or \
               self.currSelectionMode == "CBuffer":
               self.AddRemoveSelSetByGeometry("CO", bufferGeoms)

            del self.MBUFFERCommand
            self.MBUFFERCommand = None

            if self.SingleSelection == True and self.entitySet.count() > 0:
               self.plugIn.setLastEntitySet(self.entitySet)
               return True # end

            if self.exitAfterSelection == True:
               return True # end

            self.WaitForFirstPoint()
         return False