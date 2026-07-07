# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 STRETCH command to stretch graphical objects

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
from qgis.core import QgsPointXY, QgsGeometry, QgsRectangle


from ..qad_line import QadLine
from .qad_stretch_maptool import Qad_stretch_maptool, Qad_stretch_maptool_ModeEnum, Qad_gripStretch_maptool
from ..qad_getpoint import QadGetPointDrawModeEnum
from ..qad_textwindow import QadInputTypeEnum, QadInputModeEnum
from .qad_mpolygon_cmd import QadMPOLYGONCommandClass
from .qad_rectangle_cmd import QadRECTANGLECommandClass
from .qad_generic_cmd import QadCommandClass
from ..qad_variables import QadVariables
from ..qad_msg import QadMsg
from .. import qad_utils
from .. import qad_layer
from .. import qad_stretch_fun
from .. import qad_grip
from ..qad_entity import QadEntitySet, getSelSet, QadEntityTypeEnum, QadEntity
from ..qad_dim import QadDimStyles, QadDimEntity
from ..qad_multi_geom import fromQadGeomToQgsGeom



# Class that manages the STRETCH command
class QadSTRETCHCommandClass(QadCommandClass):

   def instantiateNewCmd(self):
      """instantiates a new command of the same type"""
      return QadSTRETCHCommandClass(self.plugIn)

   def getName(self):
      return QadMsg.translate("Command_list", "STRETCH")

   def getEnglishName(self):
      return "STRETCH"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runSTRETCHCommand)

   def getIcon(self):
      return QIcon(":/plugins/qad/icons/stretch.svg")

   def getNote(self):
      # set the explanatory notes of the command
      return QadMsg.translate("Command_STRETCH", "Stretches objects.")

   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      self.AddOnSelection = True # if = False means remove
      self.points = []
      self.MPOLYGONCommand = None
      self.SSGeomList = [] # list of entities to stretch with selection geom
      self.basePt = QgsPointXY()

   def __del__(self):
      QadCommandClass.__del__(self)
      if self.MPOLYGONCommand is not None:
         del self.MPOLYGONCommand
      for SSGeom in self.SSGeomList:
         SSGeom[0].deselectOnLayer()


   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      if self.step == 2: # when you are in the line drawing phase
         return self.MPOLYGONCommand.getPointMapTool(drawMode)
      else:
         if (self.plugIn is not None):
            if self.PointMapTool is None:
               self.PointMapTool = Qad_stretch_maptool(self.plugIn)
            return self.PointMapTool
         else:
            return None


   def getCurrentContextualMenu(self):
      if self.step == 2: # when you are in the line drawing phase
         return self.MPOLYGONCommand.getCurrentContextualMenu()
      else:
         return self.contextualMenu


   def stretch(self, entity, containerGeom, offsetX, offsetY, tolerance2ApproxCurve, openForm = True):
      # entity = entity to stretch
      # ptList = list of points to stretch
      # offsetX, offsetY = spostamento da applicare
      # tolerance2ApproxCurve = tolerance to recreate curves

      if entity.whatIs() == "DIMENTITY":
         dimEntity = entity
      else:
         # check if the entity belongs to a dimensioning style
         dimEntity = QadDimStyles.getDimEntity(entity)

      if dimEntity is None:
         stretchedGeom = entity.getQadGeom()
         # check inserted because with dimensions, this is deleted and recreated so some objects may no longer exist
         if stretchedGeom is None: # if there is no jump without error
            return True
         # stretch the feature
         stretchedGeom = qad_stretch_fun.stretchQadGeometry(stretchedGeom, containerGeom, \
                                                            offsetX, offsetY)

         if stretchedGeom is not None:
            # I transform the geometry into the layer crs
            f = entity.getFeature()
            f.setGeometry(fromQadGeomToQgsGeom(stretchedGeom, entity.layer))
            # plugin, layer, feature, refresh, check_validity
            if qad_layer.updateFeatureToLayer(self.plugIn, entity.layer, f, False, False) == False:
               return False

      else:
         # stretch the dimension
         if dimEntity.deleteToLayers(self.plugIn) == False:
            return False
         newDimEntity = QadDimEntity(dimEntity) # I copy it
         newDimEntity.stretch(containerGeom, offsetX, offsetY)
         if newDimEntity.addToLayers(self.plugIn) == False:
            return False

      return True


   # ============================================================================
   # stretchFeatures
   # ============================================================================
   def stretchFeatures(self, newPt):
      # I get a single QadEntitySet with the selected entities
      entitySet = QadEntitySet()
      for SSGeom in self.SSGeomList:
         entitySet.unite(SSGeom[0])
      self.plugIn.beginEditCommand("Feature stretched", entitySet.getLayerList())
      openForm = True if entitySet.count() == 1 else False

      dimElaboratedList = [] # list of dimensions already processed

      tolerance2ApproxCurve = QadVariables.get(QadMsg.translate("Environment variables", "TOLERANCE2APPROXCURVE"))
      offsetX = newPt.x() - self.basePt.x()
      offsetY = newPt.y() - self.basePt.y()

      entity = QadEntity()
      for SSGeom in self.SSGeomList:
         # copy entitySet
         entitySet = QadEntitySet(SSGeom[0])
         geomSel = SSGeom[1]

         for layerEntitySet in entitySet.layerEntitySetList:
            layer = layerEntitySet.layer

            for featureId in layerEntitySet.featureIds:
               entity.set(layer, featureId)

               # check if the entity belongs to a dimensioning style
               dimEntity = QadDimStyles.getDimEntity(entity)
               if dimEntity is None:
                  if self.stretch(entity, geomSel, offsetX, offsetY, tolerance2ApproxCurve, openForm) == False:
                     self.plugIn.destroyEditCommand()
                     return
               else:
                  found = False
                  for dimElaborated in dimElaboratedList:
                     if dimElaborated == dimEntity:
                        found = True

                  if found == False: # share not yet processed
                     # add the layers of the dimension components
                     self.plugIn.addLayerListToLastEditCommand("Feature stretched",
                                                               [dimEntity.getSymbolLayer(), dimEntity.getLinearLayer(), dimEntity.getTextualLayer()])

                     dimElaboratedList.append(dimEntity)
                     if self.stretch(dimEntity, geomSel, offsetX, offsetY, tolerance2ApproxCurve) == False:
                        self.plugIn.destroyEditCommand()
                        return

      self.plugIn.endEditCommand()


   # ============================================================================
   # setEntitySetGeom
   # ============================================================================
   def setEntitySetGeom(self, entitySet, selGeom):
      for SSGeom in self.SSGeomList:
         SSGeom[0].deselectOnLayer()
      del self.SSGeomList[:] # I empty the list
      # adds the selection set with the geometry used for selection
      self.SSGeomList.append([entitySet, selGeom])
      entitySet.selectOnLayer(False) # incremental = False

   # ============================================================================
   # addEntitySetGeom
   # ============================================================================
   def addEntitySetGeom(self, entitySet, selGeom):
      # delete the objects present in entitySet from the previous groups
      self.removeEntitySet(entitySet)
      # adds the selection set with the geometry used for selection
      self.SSGeomList.append([entitySet, selGeom])
      entitySet.selectOnLayer(True) # incremental = True


   # ============================================================================
   # removeEntitySet
   # ============================================================================
   def removeEntitySet(self, entitySet):
      # delete the objects present in entitySet from the previous groups
      for SSGeom in self.SSGeomList:
         SSGeom[0].subtract(entitySet)
      for SSGeom in self.SSGeomList:
         SSGeom[0].selectOnLayer(False) # incremental = False


   # ============================================================================
   # SSGeomListIsEmpty
   # ============================================================================
   def SSGeomListIsEmpty(self):
      if len(self.SSGeomList) == 0:
         return True
      for SSGeom in self.SSGeomList:
         if SSGeom[0].isEmpty() == False:
            return False
      return True


   # ============================================================================
   # waitForObjectSel
   # ============================================================================
   def waitForObjectSel(self):
      self.step = 1
      # set the map tool
      self.getPointMapTool().setMode(Qad_stretch_maptool_ModeEnum.ASK_FOR_FIRST_PT_RECTANGLE)

      keyWords = QadMsg.translate("Command_STRETCH", "Polygon") + "/" + \
                 QadMsg.translate("Command_STRETCH", "Add") + "/" + \
                 QadMsg.translate("Command_STRETCH", "Remove")

      if self.AddOnSelection == True:
         prompt = QadMsg.translate("Command_STRETCH", "Select vertices")
      else:
         prompt = QadMsg.translate("Command_STRETCH", "Remove vertices")
      prompt = prompt + QadMsg.translate("Command_STRETCH", " to stretch crossed by a selection window or [{0}]: ").format(keyWords)

      englishKeyWords = "Polygon" + "/" + "Add" + "/" + "Remove"
      keyWords += "_" + englishKeyWords
      # is preparing to wait for a point or Enter or a keyword
      # msg, inputType, default, keyWords, no check
      self.waitFor(prompt, QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                   None, \
                   keyWords, QadInputModeEnum.NONE)


   # ============================================================================
   # waitForBasePt
   # ============================================================================
   def waitForBasePt(self):
      self.step = 4
      # set the map tool
      self.getPointMapTool().setMode(Qad_stretch_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_BASE_PT)

      keyWords = QadMsg.translate("Command_STRETCH", "Displacement")
      prompt = QadMsg.translate("Command_STRETCH", "Specify base point or [{0}] <{0}>: ").format(keyWords)

      englishKeyWords = "Displacement"
      keyWords += "_" + englishKeyWords
      # is preparing to wait for a point or Enter or a keyword
      # msg, inputType, default, keyWords, no check
      self.waitFor(prompt, \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                   None, \
                   keyWords, QadInputModeEnum.NONE)


   # ============================================================================
   # run
   # ============================================================================
   def run(self, msgMapTool = False, msg = None):
      if self.plugIn.canvas.mapSettings().destinationCrs().isGeographic():
         self.showMsg(QadMsg.translate("QAD", "\nThe coordinate reference system of the project must be a projected coordinate system.\n"))
         return True # end command

      # =========================================================================
      # OBJECT SELECTION REQUEST
      if self.step == 0: # start of command
         # is preparing to wait for the selection of the objects to be ironed
         self.waitForObjectSel()
         return False

      # =========================================================================
      # RESPONSE TO THE SELECTION OF OBJECTS TO IRON
      elif self.step == 1:
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if while selecting a point
            # Another plugin was activated which deactivated Qad
            # so the command that returns here has been reactivated without the map tool
            # has selected a point
            if self.getPointMapTool().point is None: # the map tool was activated without a dot
               if self.getPointMapTool().rightButton == True: # if used with the right mouse button
                  value = None
               else:
                  self.setMapTool(self.getPointMapTool()) # I reactivate the map tool
                  return False
            else:
               value = self.getPointMapTool().point
         else: # the dot comes as a parameter of the function
            value = msg

         if type(value) == unicode:
            if value == QadMsg.translate("Command_STRETCH", "Polygon") or value == "Polygon":
               # Select all objects that are inside the polygon
               self.MPOLYGONCommand = QadMPOLYGONCommandClass(self.plugIn)
               # if this flag = True the command is used within another command to draw a line
               # which will not be saved on a layer
               self.MPOLYGONCommand.virtualCmd = True
               self.MPOLYGONCommand.run(msgMapTool, msg)
               self.step = 2
               return False
            elif value == QadMsg.translate("Command_SSGET", "Add") or value == "Add":
               # Switch to Add method: The selected objects can be added to the selection set
               self.AddOnSelection = True
            elif value == QadMsg.translate("Command_SSGET", "Remove") or value == "Remove":
               # Switch to Remove method: Objects can be removed from the selection set
               self.AddOnSelection = False
         elif type(value) == QgsPointXY: # if a point has been selected
            del self.points[:] # I empty the list
            self.points.append(value)
            # set the map tool
            self.getPointMapTool().setMode(Qad_stretch_maptool_ModeEnum.FIRST_PT_KNOWN_ASK_FOR_SECOND_PT_RECTANGLE)
            self.getPointMapTool().setStartPoint(value)

            # is preparing to wait for a point
            self.waitForPoint(QadMsg.translate("Command_STRETCH", "Specify opposite corner: "))
            self.step = 3
            return False
         else:
            if self.SSGeomListIsEmpty():
               return True
            # prepares to wait for the base point or the shift
            self.waitForBasePt()
            return False

         # is preparing to wait for the selection of the objects to be ironed
         self.waitForObjectSel()

         return False

      # =========================================================================
      # RESPONSE TO THE POINT REQUEST FOR POLYGON MODE (from step = 1)
      elif self.step == 2: # after waiting for a point the command restarts
         if self.MPOLYGONCommand.run(msgMapTool, msg) == True:
            if self.MPOLYGONCommand.PLINECommand.polyline.qty() > 0:
               # I searc for all geometries intersecting the polygon
               # and considering only editable layers
               selSet = getSelSet("CP", self.getPointMapTool(), self.MPOLYGONCommand.PLINECommand.polyline.asPolyline(), \
                                  None, True, True, True, \
                                  True)
               # if the selection occurred with shift pressed or if the selSet group must be removed from the group
               if self.AddOnSelection == False:
                  self.removeEntitySet(selSet)
               else:
                  self.setEntitySetGeom(selSet, QgsGeometry.fromPolygonXY([self.MPOLYGONCommand.PLINECommand.polyline.asPolyline()]))

            del self.MPOLYGONCommand
            self.MPOLYGONCommand = None

            # is preparing to wait for the selection of the objects to be ironed
            self.waitForObjectSel()
            self.getPointMapTool().refreshSnapType() # update the snapType which can be varied from the mpolygon map tool
         return False

      # =========================================================================
      # RESPONSE TO THE POINT REQUEST FOR WINDOW MODE (from step = 1)
      elif self.step == 3: # after waiting for a point the command restarts
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if while selecting a point
            # Another plugin was activated which deactivated Qad
            # so the command that returns here has been reactivated without the map tool
            # has selected a point
            if self.getPointMapTool().point is None: # the map tool was activated without a dot
               if self.getPointMapTool().rightButton == True: # if used with the right mouse button
                  self.showMsg(QadMsg.translate("Command_STRETCH", "Window not correct."))
                  # is preparing to wait for a point
                  self.waitForPoint(QadMsg.translate("Command_STRETCH", "Specify opposite corner: "))
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
            self.points.append(value)
            # I searc for all geometries intersecting the rectangle
            # and considering only editable layers
            selSet = getSelSet("C", self.getPointMapTool(), self.points, \
                               None, True, True, True, \
                               True)
            # if you should remove the entitySet group from the group
            if self.AddOnSelection == False:
               self.removeEntitySet(selSet)
            else:
               if shiftKey: # if the selection was made with shift pressed
                  self.addEntitySetGeom(selSet, QgsGeometry.fromRect(QgsRectangle(self.points[0], self.points[1])))
               else:
                  self.setEntitySetGeom(selSet, QgsGeometry.fromRect(QgsRectangle(self.points[0], self.points[1])))
            # is preparing to wait for the selection of the objects to be ironed
            self.waitForObjectSel()
         return False

      # =========================================================================
      # RESPONSE TO THE BASE POINT REQUEST (from step = 1)
      elif self.step == 4: # after waiting for a point or a real number the command is restarted
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if while selecting a point
            # Another plugin was activated which deactivated Qad
            # so the command that returns here has been reactivated without the map tool
            # has selected a point
            if self.getPointMapTool().point is None: # the map tool was activated without a dot
               if self.getPointMapTool().rightButton == True: # if used with the right mouse button
                  pass # opzione di default "spostamento"
               else:
                  self.setMapTool(self.getPointMapTool()) # I reactivate the map tool
                  return False

            value = self.getPointMapTool().point
         else: # the dot comes as a parameter of the function
            value = msg

         # set the map tool
         self.getPointMapTool().SSGeomList = self.SSGeomList

         if value is None or type(value) == unicode:
            self.basePt.set(0, 0)
            self.getPointMapTool().basePt = self.basePt
            self.getPointMapTool().setMode(Qad_stretch_maptool_ModeEnum.BASE_PT_KNOWN_ASK_FOR_MOVE_PT)
            # is preparing to wait for a point
            msg = QadMsg.translate("Command_STRETCH", "Specify the displacement from the origin point 0,0 <{0}, {1}>: ")
            # msg, inputType, default, keyWords, no check
            self.waitFor(msg.format(str(self.plugIn.lastOffsetPt.x()), str(self.plugIn.lastOffsetPt.y())), \
                         QadInputTypeEnum.POINT2D, \
                         self.plugIn.lastOffsetPt, \
                         "", QadInputModeEnum.NONE)
            self.step = 5
         elif type(value) == QgsPointXY: # if the base point has been entered
            self.basePt.set(value.x(), value.y())

            # set the map tool
            self.getPointMapTool().basePt = self.basePt
            self.getPointMapTool().setMode(Qad_stretch_maptool_ModeEnum.BASE_PT_KNOWN_ASK_FOR_MOVE_PT)

            # is preparing to wait for a point or Enter or a keyword
            # msg, inputType, default, keyWords, no check
            self.waitFor(QadMsg.translate("Command_STRETCH", "Specify second point or <use first point as displacement from origin point 0,0>: "), \
                         QadInputTypeEnum.POINT2D, \
                         None, \
                         "", QadInputModeEnum.NONE)
            self.step = 6

         return False

      # =========================================================================
      # RESPONSE TO THE MOVEMENT POINT REQUEST (from step = 2)
      elif self.step == 5: # after waiting for a point or a real number the command is restarted
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

         self.plugIn.setLastOffsetPt(value)
         self.stretchFeatures(value)
         return True # end command

      # =========================================================================
      # RESPONSE TO THE SECOND POINT REQUEST FOR MOVEMENT (from step = 2)
      elif self.step == 6: # after waiting for a point or a real number the command is restarted
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

         if value is None:
            newPt = QgsPointXY(self.basePt.x() * 2, self.basePt.y() * 2)
            self.stretchFeatures(newPt)
         elif type(value) == QgsPointXY: # if the movement with a point has been inserted
            self.stretchFeatures(value)

         return True # end command



# ============================================================================
# Class that manages the STRETCH command for grips
# ============================================================================
class QadGRIPSTRETCHCommandClass(QadCommandClass):


   def instantiateNewCmd(self):
      """instantiates a new command of the same type"""
      return QadGRIPSTRETCHCommandClass(self.plugIn)


   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      self.selectedEntityGripPoints = [] # list in which each element is an entity + a list of points to stretch
      self.basePt = QgsPointXY()
      self.skipToNextGripCommand = False
      self.copyEntities = False
      self.nOperationsToUndo = 0


   def __del__(self):
      QadCommandClass.__del__(self)


   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      if (self.plugIn is not None):
         if self.PointMapTool is None:
            self.PointMapTool = Qad_gripStretch_maptool(self.plugIn)
         return self.PointMapTool
      else:
         return None


   # ============================================================================
   # addToSelectedEntityGripPoints
   # ============================================================================
   def addToSelectedEntityGripPoints(self, entityGripPoints):
      # entity with grip point list
      i = 0
      gripPoints = entityGripPoints.gripPoints
      gripPointsLen = len(gripPoints)
      ptList = []
      while i < gripPointsLen:
         gripPoint = gripPoints[i]
         # grip point selected
         if gripPoint.getStatus() == qad_grip.QadGripStatusEnum.SELECTED:
            if gripPoint.gripType == qad_grip.QadGripPointTypeEnum.CENTER:
               ptList.append(gripPoint.getPoint())
            elif gripPoint.gripType == qad_grip.QadGripPointTypeEnum.LINE_MID_POINT:
               # add the previous and next vertex of the intermediate one
               if i > 0:
                  ptList.append(gripPoints[i - 1].getPoint())
               if i < gripPointsLen - 1:
                  # if the next grip is center it is the last stretch of a polygon
                  if gripPoints[i + 1].gripType == qad_grip.QadGripPointTypeEnum.CENTER:
                     ptList.append(gripPoints[0].getPoint()) # I take the first point
                  else:
                     ptList.append(gripPoints[i + 1].getPoint())
            elif gripPoint.gripType == qad_grip.QadGripPointTypeEnum.QUA_POINT:
               ptList.append(gripPoint.getPoint())
            elif gripPoint.gripType == qad_grip.QadGripPointTypeEnum.VERTEX or \
                 gripPoint.gripType == qad_grip.QadGripPointTypeEnum.END_VERTEX:
               ptList.append(gripPoint.getPoint())
            elif gripPoint.gripType == qad_grip.QadGripPointTypeEnum.ARC_MID_POINT:
               ptList.append(gripPoint.getPoint())
         i = i + 1

      if len(ptList) > 0:
         self.selectedEntityGripPoints.append([entityGripPoints.entity, ptList])


   # ============================================================================
   # setSelectedEntityGripPoints
   # ============================================================================
   def setSelectedEntityGripPoints(self, entitySetGripPoints):
      # list of entityGripPoints with selected grip points
      # returns a list in which each element is an entity + a list of points to stretch
      del self.selectedEntityGripPoints[:] # I empty the list

      for entityGripPoints in entitySetGripPoints.entityGripPoints:
         self.addToSelectedEntityGripPoints(entityGripPoints)
      self.getPointMapTool().setSelectedEntityGripPoints(self.selectedEntityGripPoints)

      # input : self.basePt e entitySetGripPoints
      # I searc in entitySetGripPoints for the entity that has only one selected grip corresponding to basePt
      entityGripPoints, entityGripPoint = entitySetGripPoints.isIntersecting(self.basePt)
      if entityGripPoint.getStatus() == qad_grip.QadGripStatusEnum.SELECTED and \
         len(entityGripPoints.getSelectedGripPoints()) == 1:

         entity = entityGripPoints.entity
         # check if the entity belongs to a dimensioning style
         if QadDimStyles.isDimEntity(entity):
            pass
         else:
            qadGeom = entity.getQadGeom(entityGripPoint.atGeom, entityGripPoint.atSubGeom)
            qadGeomType = qadGeom.whatIs()
            if qadGeomType == "POLYLINE":
               self.getPointMapTool().prevPart, self.getPointMapTool().nextPart = qadGeom.getPrevNextLinearObjectsAtVertex(entityGripPoint.nVertex)
            elif qadGeomType == "CIRCLE":
               if qadGeom.isPtOnCircle(entityGripPoint.getPoint()):
                  line = QadLine()
                  line.set(qadGeom.center, entityGripPoint.getPoint())
                  self.getPointMapTool().prevPart = line
            elif qadGeomType == "ELLIPSE":
               if qadGeom.containsPt(entityGripPoint.getPoint()):
                  line = QadLine()
                  line.set(qadGeom.center, entityGripPoint.getPoint())
                  self.getPointMapTool().prevPart = line


   # ============================================================================
   # getSelectedEntityGripPointNdx
   # ============================================================================
   def getSelectedEntityGripPointNdx(self, entity):
      # list of entityGripPoints with selected grip points
      # searces for the position of an entity in the list where each element is an entity + a list of points to stretch
      i = 0
      tot = len(self.selectedEntityGripPoints)
      while i < tot:
         selectedEntityGripPoint = self.selectedEntityGripPoints[i]
         if selectedEntityGripPoint[0] == entity:
            return i
         i = i + 1
      return -1


   # ============================================================================
   # stretch
   # ============================================================================
   def stretch(self, entity, ptList, offsetX, offsetY, tolerance2ApproxCurve, openForm):
      # entity = entity to stretch
      # ptList = list of points to stretch
      # offsetX, offsetY = spostamento da applicare
      # tolerance2ApproxCurve = tolerance to recreate curves

      if entity.whatIs() == "DIMENTITY":
         dimEntity = entity
      else:
         # check if the entity belongs to a dimensioning style
         dimEntity = QadDimStyles.getDimEntity(entity)

      if dimEntity is None:
         stretchedGeom = entity.getQadGeom()
         # check inserted because with dimensions, this is deleted and recreated so some objects may no longer exist
         if stretchedGeom is None: # if there is no jump without error
            return True

         # stretch the feature
         stretchedGeom = qad_stretch_fun.stretchQadGeometry(stretchedGeom, ptList, \
                                                            offsetX, offsetY)

         if stretchedGeom is not None:
            # I transform the QAD geometry into GSIS geometry in the layer crs
            f = entity.getFeature()
            f.setGeometry(fromQadGeomToQgsGeom(stretchedGeom, entity.layer))
            if self.copyEntities == False:
               # plugin, layer, feature, refresh, check_validity
               if qad_layer.updateFeatureToLayer(self.plugIn, entity.layer, f, False, False) == False:
                  return False
            else:
               # plugin, layer, features, coordTransform, refresh, check_validity
               if qad_layer.addFeatureToLayer(self.plugIn, entity.layer, f, None, False, False, openForm) == False:
                  return False

      else:
         # stretch the dimension
         if self.copyEntities == False:
            if dimEntity.deleteToLayers(self.plugIn) == False:
               return False
         newDimEntity = QadDimEntity(dimEntity) # I copy it
         newDimEntity.stretch(ptList, offsetX, offsetY)
         if newDimEntity.addToLayers(self.plugIn) == False:
            return False
         # I don't know why sometimes the map doesn't update so I force the update
         self.plugIn.canvas.refresh()

      return True


   # ============================================================================
   # stretchFeatures
   # ============================================================================
   def stretchFeatures(self, newPt):
      # I get a single QadEntitySet with the selected entities
      entitySet = QadEntitySet()
      for selectedEntity in self.selectedEntityGripPoints:
         entitySet.addEntity(selectedEntity[0])
      self.plugIn.beginEditCommand("Feature stretched", entitySet.getLayerList())
      openForm = True if len(self.selectedEntityGripPoints) == 1 else False

      dimElaboratedList = [] # list of dimensions already processed

      for selectedEntity in self.selectedEntityGripPoints:
         entity = selectedEntity[0]
         ptList = selectedEntity[1]
         layer = entity.layer

         tolerance2ApproxCurve = QadVariables.get(QadMsg.translate("Environment variables", "TOLERANCE2APPROXCURVE"))
         offsetX = newPt.x() - self.basePt.x()
         offsetY = newPt.y() - self.basePt.y()

         # check if the entity belongs to a dimensioning style
         dimEntity = QadDimStyles.getDimEntity(entity)
         if dimEntity is None:
            if self.stretch(entity, ptList, offsetX, offsetY, tolerance2ApproxCurve, openForm) == False:
               self.plugIn.destroyEditCommand()
               return
         else:
            found = False
            for dimElaborated in dimElaboratedList:
               if dimElaborated == dimEntity:
                  found = True

            if found == False: # share not yet processed
               # add the layers of the dimension components
               self.plugIn.addLayerListToLastEditCommand("Feature stretched",
                                                         [dimEntity.getSymbolLayer(), dimEntity.getLinearLayer(), dimEntity.getTextualLayer()])

               dimEntitySet = dimEntity.getEntitySet()
               # create a single list containing the grip points of all the components of the dimension
               dimPtlist = []
               for layerEntitySet in dimEntitySet.layerEntitySetList:
                  for featureId in layerEntitySet.featureIds:
                     componentDim = QadEntity()
                     componentDim.set(layerEntitySet.layer, featureId)
                     i = self.getSelectedEntityGripPointNdx(componentDim)
                     if i >= 0:
                        dimPtlist.extend(self.selectedEntityGripPoints[i][1])

               dimElaboratedList.append(dimEntity)
               if self.stretch(dimEntity, dimPtlist, offsetX, offsetY, tolerance2ApproxCurve, False) == False:
                  self.plugIn.destroyEditCommand()
                  return

      self.plugIn.endEditCommand()
      self.nOperationsToUndo = self.nOperationsToUndo + 1


   # ============================================================================
   # waitForStretchPoint
   # ============================================================================
   def waitForStretchPoint(self):
      self.step = 1
      self.plugIn.setLastPoint(self.basePt)
      # set the map tool
      self.getPointMapTool().basePt = self.basePt
      self.getPointMapTool().setMode(Qad_stretch_maptool_ModeEnum.BASE_PT_KNOWN_ASK_FOR_MOVE_PT)

      keyWords = QadMsg.translate("Command_GRIP", "Base point") + "/" + \
                 QadMsg.translate("Command_GRIP", "Copy") + "/" + \
                 QadMsg.translate("Command_GRIP", "Undo") + "/" + \
                 QadMsg.translate("Command_GRIP", "eXit")

      prompt = QadMsg.translate("Command_GRIPSTRETCH", "Specify stretch point or [{0}]: ").format(keyWords)

      englishKeyWords = "Base point" + "/" + "Copy" + "/" + "Undo" + "/" + "eXit"
      keyWords += "_" + englishKeyWords
      # is preparing to wait for a point or Enter or a keyword
      # msg, inputType, default, keyWords, no check
      self.waitFor(prompt, QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                   None, \
                   keyWords, QadInputModeEnum.NONE)


   # ============================================================================
   # waitForBasePt
   # ============================================================================
   def waitForBasePt(self):
      self.step = 2
      # set the map tool
      self.getPointMapTool().setMode(Qad_stretch_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_BASE_PT)

      # is preparing to wait for a point
      self.waitForPoint(QadMsg.translate("Command_GRIPSTRETCH", "Specify base point: "))


   # ============================================================================
   # run
   # ============================================================================
   def run(self, msgMapTool = False, msg = None):
      if self.plugIn.canvas.mapSettings().destinationCrs().isGeographic():
         self.showMsg(QadMsg.translate("QAD", "\nThe coordinate reference system of the project must be a projected coordinate system.\n"))
         return True # end command

      # =========================================================================
      # OBJECT SELECTION REQUEST
      if self.step == 0: # start of command
         if len(self.selectedEntityGripPoints) == 0: # there are no objects to stretch
            return True
         self.showMsg(QadMsg.translate("Command_GRIPSTRETCH", "\n** STRETCH **\n"))
         # is preparing to wait for a stretching point
         self.waitForStretchPoint()
         return False

      # =========================================================================
      # RESPONSE TO THE REQUEST FOR A STRETCH POINT
      elif self.step == 1:
         ctrlKey = False
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if while selecting a point
            # Another plugin was activated which deactivated Qad
            # so the command that returns here has been reactivated without the map tool
            # has selected a point
            if self.getPointMapTool().point is None: # the map tool was activated without a dot
               if self.getPointMapTool().rightButton == True: # if used with the right mouse button
                  value = None
               else:
                  self.setMapTool(self.getPointMapTool()) # I reactivate the map tool
                  return False
            else:
               value = self.getPointMapTool().point

            ctrlKey = self.getPointMapTool().ctrlKey
         else: # the dot comes as a parameter of the function
            value = msg

         if type(value) == unicode:
            if value == QadMsg.translate("Command_GRIP", "Base point") or value == "Base point":
               # is preparing to wait for the base point
               self.waitForBasePt()
            elif value == QadMsg.translate("Command_GRIP", "Copy") or value == "Copy":
               # Copy entities leaving the originals unchanged
               self.copyEntities = True
               # is preparing to wait for a stretching point
               self.waitForStretchPoint()
            elif value == QadMsg.translate("Command_GRIP", "Undo") or value == "Undo":
               if self.nOperationsToUndo > 0:
                  self.nOperationsToUndo = self.nOperationsToUndo - 1
                  self.plugIn.undoEditCommand()
               else:
                  self.showMsg(QadMsg.translate("QAD", "\nThe command has been canceled."))
               # is preparing to wait for a stretching point
               self.waitForStretchPoint()
            elif value == QadMsg.translate("Command_GRIP", "eXit") or value == "eXit":
               return True # end command
         elif type(value) == QgsPointXY: # if a point has been selected
            if ctrlKey:
               self.copyEntities = True

            self.stretchFeatures(value)

            if self.copyEntities == False:
               return True
            # is preparing to wait for a stretching point
            self.waitForStretchPoint()

         else:
            if self.copyEntities == False:
               self.skipToNextGripCommand = True
            return True # end command

         return False


      # =========================================================================
      # RESPONSE TO THE BASE POINT REQUEST (from step = 1)
      elif self.step == 2: # after waiting for a point
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if while selecting a point
            # Another plugin was activated which deactivated Qad
            # so the command that returns here has been reactivated without the map tool
            # has selected a point
            if self.getPointMapTool().point is None: # the map tool was activated without a dot
               if self.getPointMapTool().rightButton == True: # if used with the right mouse button
                  pass # opzione di default "spostamento"
               else:
                  self.setMapTool(self.getPointMapTool()) # I reactivate the map tool
                  return False

            value = self.getPointMapTool().point
         else: # the dot comes as a parameter of the function
            value = msg

         if type(value) == QgsPointXY: # if the base point has been entered
            self.basePt.set(value.x(), value.y())
            # set the map tool
            self.getPointMapTool().basePt = self.basePt

         # is preparing to wait for a stretching point
         self.waitForStretchPoint()

         return False
