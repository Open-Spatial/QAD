# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 MEASURE command to create point objects at defined intervals along the perimeter or length of an object

                              -------------------
        begin                : 2016-09-12
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
from qgis.core import QgsGeometry, QgsFeature, QgsWkbTypes, QgsVectorLayerUtils
from qgis.PyQt.QtGui import QIcon


from .qad_generic_cmd import QadCommandClass
from ..qad_msg import QadMsg
from ..qad_getpoint import QadGetPointDrawModeEnum
from .qad_entsel_cmd import QadEntSelClass
from .qad_getdist_cmd import QadGetDistClass
from ..qad_textwindow import QadInputTypeEnum, QadInputModeEnum
from .. import qad_utils
from .. import qad_layer
from ..qad_dim import QadDimStyles
from ..qad_multi_geom import getQadGeomAt
from ..qad_geom_relations import getQadGeomClosestPart


# ===============================================================================
# QadMEASURECommandClassStepEnum class.
# ===============================================================================
class QadMEASURECommandClassStepEnum():
   ASK_FOR_ENT        = 1 # requires selection of an object (0 is the start of the command)
   ASK_FOR_ALIGNMENT  = 2 # richiede l'allineamento
   ASK_SEGMENT_LENGTH = 3 # requires the length of the segments



# Class that manages the MEASURE command
class QadMEASURECommandClass(QadCommandClass):

   def instantiateNewCmd(self):
      """instantiates a new command of the same type"""
      return QadMEASURECommandClass(self.plugIn)

   def getName(self):
      return QadMsg.translate("Command_list", "MEASURE")

   def getEnglishName(self):
      return "MEASURE"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runMEASURECommand)

   def getIcon(self):
      return QIcon(":/plugins/qad/icons/measure.svg")

   def getNote(self):
      # set the explanatory notes of the command
      return QadMsg.translate("Command_MEASURE", "Creates punctual objects at measured intervals along the length or perimeter of an object.")

   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      self.entSelClass = None
      self.GetDistClass = None
      self.objectAlignment = True
      self.segmentLength = 1

   def __del__(self):
      QadCommandClass.__del__(self)
      if self.entSelClass is not None:
         self.entSelClass.entity.deselectOnLayer()
         del self.entSelClass


   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      if self.step == QadMEASURECommandClassStepEnum.ASK_SEGMENT_LENGTH: # when you are in the distance request phase
         return self.GetDistClass.getPointMapTool()
      else:
         return QadCommandClass.getPointMapTool(self, drawMode)


   def getCurrentContextualMenu(self):
      if self.step == QadMEASURECommandClassStepEnum.ASK_SEGMENT_LENGTH: # when you are in the distance request phase
         return self.GetDistClass.getCurrentContextualMenu()
      else:
         return self.contextualMenu


   # ============================================================================
   # waitForEntsel
   # ============================================================================
   def waitForEntsel(self, msgMapTool, msg):
      if self.entSelClass is not None:
         del self.entSelClass
      self.step = QadMEASURECommandClassStepEnum.ASK_FOR_ENT
      self.entSelClass = QadEntSelClass(self.plugIn)
      self.entSelClass.msg = QadMsg.translate("Command_MEASURE", "Select object to measure: ")
      # I discard the selection of points
      self.entSelClass.checkPointLayer = False
      self.entSelClass.checkLineLayer = True
      self.entSelClass.checkPolygonLayer = True
      self.entSelClass.checkDimLayers = False
      self.entSelClass.onlyEditableLayers = False

      self.entSelClass.run(msgMapTool, msg)


   # ============================================================================
   # waitForAlignmentObjs
   # ============================================================================
   def waitForAlignmentObjs(self):
      self.step = QadMEASURECommandClassStepEnum.ASK_FOR_ALIGNMENT

      keyWords = QadMsg.translate("QAD", "Yes") + "/" + QadMsg.translate("QAD", "No")
      self.defaultValue = QadMsg.translate("QAD", "Yes")
      prompt = QadMsg.translate("Command_MEASURE", "Align with object ? [{0}] <{1}>: ").format(keyWords, self.defaultValue)

      englishKeyWords = "Yes" + "/" + "No"
      keyWords += "_" + englishKeyWords

      # msg, inputType, default, keyWords, no check
      self.waitFor(prompt, \
                   QadInputTypeEnum.KEYWORDS, \
                   self.defaultValue, \
                   keyWords, QadInputModeEnum.NONE)


   # ============================================================================
   # waitForSegmentLength
   # ============================================================================
   def waitForSegmentLength(self):
      self.step = QadMEASURECommandClassStepEnum.ASK_SEGMENT_LENGTH

      if self.GetDistClass is not None:
         del self.GetDistClass
      self.GetDistClass = QadGetDistClass(self.plugIn)

      self.GetDistClass.msg = QadMsg.translate("Command_MEASURE", "Enter the length of segment: ")
      self.GetDistClass.run()


   # ============================================================================
   # addFeature
   # ============================================================================
   def addFeature(self, layer, insPt, rot, openForm = True):
      transformedPoint = self.mapToLayerCoordinates(layer, insPt)
      g = QgsGeometry.fromPointXY(transformedPoint)
      f = QgsVectorLayerUtils.createFeature(layer, g, {}, layer.createExpressionContext())

      # if the scale depends on a field
      scaleFldName = qad_layer.get_symbolScaleFieldName(layer)
      if len(scaleFldName) > 0:
         f.setAttribute(scaleFldName, 1.0)

      # if the rotation depends on a field
      rotFldName = qad_layer.get_symbolRotationFieldName(layer)
      if len(rotFldName) > 0:
         f.setAttribute(rotFldName, qad_utils.toDegrees(rot))

      return qad_layer.addFeatureToLayer(self.plugIn, layer, f, None, True, False, openForm)


   # ============================================================================
   # doMeasure
   # ============================================================================
   def doMeasure(self, dstLayer):
      qadGeom = self.entSelClass.entity.getQadGeom()
      # the function returns a list with
      # (<minimum distance>
      # <nearest point>
      # <nearest geometry index>
      # <index of the nearest sub-geometry>
      # if closed geometry is polyline type the list also contains
      # <index of the closest sub-geometry part>
      # <"to the left of" if the point is to the left of the part (< 0 -> left, > 0 -> right)
      dummy = getQadGeomClosestPart(qadGeom, self.entSelClass.point)
      # returns the sub-geometry
      pathPolyline = getQadGeomAt(qadGeom, dummy[2], dummy[3])

      self.plugIn.beginEditCommand("Feature measured", dstLayer)

      i = 1
      distanceFromStart = self.segmentLength
      length = pathPolyline.length()
      openForm = True if length / distanceFromStart < 2 else False

      while distanceFromStart <= length:
         pt, rot = pathPolyline.getPointFromStart(distanceFromStart)
         if self.addFeature(dstLayer, pt, rot if self.objectAlignment else 0, openForm) == False:
            self.plugIn.destroyEditCommand()
            return False
         i = i + 1
         distanceFromStart = distanceFromStart + self.segmentLength

      self.plugIn.endEditCommand()
      return True

   def run(self, msgMapTool = False, msg = None):
      if self.plugIn.canvas.mapSettings().destinationCrs().isGeographic():
         self.showMsg(QadMsg.translate("QAD", "\nThe coordinate reference system of the project must be a projected coordinate system.\n"))
         return True # end command

      currLayer, errMsg = qad_layer.getCurrLayerEditable(self.plugIn.canvas, QgsWkbTypes.PointGeometry)
      if currLayer is None:
         self.showErr(errMsg)
         return True # end command

      if qad_layer.isSymbolLayer(currLayer) == False :
         errMsg = QadMsg.translate("QAD", "\nCurrent layer is not a symbol layer.")
         errMsg = errMsg + QadMsg.translate("QAD", "\nA symbol layer is a vector punctual layer without label.\n")
         self.showErr(errMsg)
         return True # end command

      if  len(QadDimStyles.getDimListByLayer(currLayer)) > 0:
         errMsg = QadMsg.translate("QAD", "\nThe current layer belongs to a dimension style.\n")
         self.showErr(errMsg)
         return True # end command

      if self.step == 0:
         self.waitForEntsel(msgMapTool, msg)
         return False # continua


      # =========================================================================
      # RESPONSE TO THE SELECTION OF AN ENTITY (from step = 0)
      elif self.step == QadMEASURECommandClassStepEnum.ASK_FOR_ENT:
         if self.entSelClass.run(msgMapTool, msg) == True:
            if self.entSelClass.entity.isInitialized():
               # if the destination layer is of symbol type
               if qad_layer.isSymbolLayer(currLayer) == True:
                  # whether the symbol can be rotated
                  if len(qad_layer.get_symbolRotationFieldName(currLayer)) >0:
                     self.waitForAlignmentObjs()
                  else:
                     self.waitForSegmentLength()
               return False
            else:
               if self.entSelClass.canceledByUsr == True: # end command
                  return True
               self.showMsg(QadMsg.translate("QAD", "No geometries in this position."))
               self.waitForEntsel(msgMapTool, msg)
         return False # continua


      # =========================================================================
      # RESPONSE TO THE REQUEST TO ALIGN OBJECTS (from step = ASK_FOR_ENT)
      elif self.step == QadMEASURECommandClassStepEnum.ASK_FOR_ALIGNMENT: # after waiting for a keyword the command is restarted
         if msgMapTool == True: # the point comes from a graphic selection
            if self.getPointMapTool().rightButton == True: # if used with the right mouse button
               value = self.defaultValue
            else:
               self.setMapTool(self.getPointMapTool()) # I reactivate the map tool
               return False
         else:
            # the keyword comes as a function parameter
            value = msg

         if type(value) == unicode:
            if value == QadMsg.translate("QAD", "Yes") or value == "Yes":
               self.objectAlignment = True
            else:
               self.objectAlignment = False

            self.waitForSegmentLength()

         return False


      # =========================================================================
      # RESPONSE TO THE SEGMENT LENGTH REQUEST (from step = ASK_FOR_ALIGNMENT)
      # =========================================================================
      elif self.step == QadMEASURECommandClassStepEnum.ASK_SEGMENT_LENGTH: # after waiting for a real number the command is restarted
         if self.GetDistClass.run(msgMapTool, msg) == True:
            self.getPointMapTool().refreshSnapType() # update the snapType which can be varied by other map tools
            if self.GetDistClass.dist is not None:
               self.segmentLength = self.GetDistClass.dist
               self.doMeasure(currLayer)

            del self.GetDistClass
            return True # end command
         else:
            return False