# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 DSETTINGS command for drawing settings

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


from ..qad_dsettings_dlg import QadDSETTINGSDialog


from .qad_generic_cmd import QadCommandClass
from ..qad_msg import QadMsg


# Class that manages the DSETTINGS command
class QadDSETTINGSCommandClass(QadCommandClass):

   def instantiateNewCmd(self):
      """instantiates a new command of the same type"""
      return QadDSETTINGSCommandClass(self.plugIn)

   def getName(self):
      return QadMsg.translate("Command_list", "DSETTINGS")

   def getEnglishName(self):
      return "DSETTINGS"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runDSETTINGSCommand)

   def getIcon(self):
      return QIcon(":/plugins/qad/icons/dsettings.svg")

   def getNote(self):
      # set the explanatory notes of the command
      return QadMsg.translate("Command_DSETTINGS", "Drafting Settings (snaps, etc.).")

   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)

   def run(self, msgMapTool = False, msg = None):
      Form = QadDSETTINGSDialog(self.plugIn)
      Form.exec()
      return True
