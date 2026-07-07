# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 ID command that returns the coordinate of a selected point

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

from qgis.core import QgsPointXY
from qgis.PyQt.QtGui import QIcon

from .qad_generic_cmd import QadCommandClass
from ..qad_msg import QadMsg


# Class that manages the ID command
class QadIDCommandClass(QadCommandClass):

   def instantiateNewCmd(self):
      """instantiates a new command of the same type"""
      return QadIDCommandClass(self.plugIn)

   def getName(self):
      return QadMsg.translate("Command_list", "ID")

   def getEnglishName(self):
      return "ID"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runIDCommand)

   def getIcon(self):
      return QIcon(":/plugins/qad/icons/id.svg")

   def getNote(self):
      # set the explanatory notes of the command
      return QadMsg.translate("Command_ID", "Displays the coordinate values of a specified location.")

   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)

   def run(self, msgMapTool = False, msg = None):
      if self.step == 0: # start of command
         self.waitForPoint() # is preparing to wait for a point
         self.step = self.step + 1
         return False
      elif self.step == 1: # after waiting for a point the command restarts
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

            pt = self.getPointMapTool().point
         else: # the dot comes as a parameter of the function
            pt = msg

         if type(pt) == QgsPointXY:
            self.plugIn.setLastPoint(pt)
            self.showMsg("\n" + pt.toString())
         return True