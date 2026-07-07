# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 QAD UNDO and REDO command

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

from .qad_generic_cmd import QadCommandClass
from ..qad_msg import QadMsg
from ..qad_textwindow import QadInputTypeEnum, QadInputModeEnum


# Class that manages the UNDO command
class QadUNDOCommandClass(QadCommandClass):

   def instantiateNewCmd(self):
      """instantiates a new command of the same type"""
      return QadUNDOCommandClass(self.plugIn)

   def getName(self):
      return QadMsg.translate("Command_list", "UNDO")

   def getEnglishName(self):
      return "UNDO"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runUNDOCommand)

   def getIcon(self):
      return QIcon(":/plugins/qad/icons/undo.svg")

   def getNote(self):
      # set the explanatory notes of the command
      return QadMsg.translate("Command_UNDO", "Reverses the effect of commands.")

   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)

   def run(self, msgMapTool = False, msg = None):
      self.isValidPreviousInput = True # to manage the command also in macros

      if self.step == 0: # start of command
         keyWords = QadMsg.translate("Command_UNDO", "BEgin") + "/" + \
                    QadMsg.translate("Command_UNDO", "End") + "/" + \
                    QadMsg.translate("Command_UNDO", "Mark") + "/" + \
                    QadMsg.translate("Command_UNDO", "Back")
         default = 1
         prompt = QadMsg.translate("Command_UNDO", "Enter the number of operations to undo or [{0}] <{1}>: ").format(keyWords, str(default))

         englishKeyWords = "BEgin" + "/" + "End" + "/" + "Mark" + "/" + "Back"
         keyWords += "_" + englishKeyWords
         # is going to wait for a positive integer or enter or a keyword
         # msg, inputType, default, keyWords, positive values
         self.waitFor(prompt, \
                      QadInputTypeEnum.INT | QadInputTypeEnum.KEYWORDS, \
                      default, \
                      keyWords, QadInputModeEnum.NOT_ZERO | QadInputModeEnum.NOT_NEGATIVE)
         self.step = 1
         return False

      # =========================================================================
      # RESPONSE TO THE INTEGER NUMBER REQUEST (from step = 0)
      elif self.step == 1: # after waiting for a point or a real number the command is restarted
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if while selecting a point
            # Another plugin was activated which deactivated Qad
            # so the command that returns here has been reactivated without the map tool
            # has selected a point
            if self.getPointMapTool().point is None: # the map tool was activated without a dot
               if self.getPointMapTool().rightButton == True: # if used with the right mouse button
                  self.plugIn.undoEditCommand()
                  return True # end command
               else:
                  self.setMapTool(self.getPointMapTool()) # I reactivate the map tool
                  return False

            value = self.getPointMapTool().point
         else: # the dot comes as a parameter of the function
            value = msg

         if type(value) == unicode:
            if value == QadMsg.translate("Command_UNDO", "BEgin") or value == "BEgin":
               self.plugIn.insertBeginGroup()
            elif value == QadMsg.translate("Command_UNDO", "End") or value == "End":
               if self.plugIn.insertEndGroup() == False:
                  self.showMsg(QadMsg.translate("Command_UNDO", "\nNo open group."))
            elif value == QadMsg.translate("Command_UNDO", "Mark") or value == "Mark":
               if self.plugIn.insertBookmark() == False:
                  self.showMsg(QadMsg.translate("Command_UNDO", "\nA mark can't be inserted into a group."))
            elif value == QadMsg.translate("Command_UNDO", "Back") or value == "Back":
               if self.plugIn.getPrevBookmarkPos() == -1: # non ci sono bookmark precedenti
                  keyWords = QadMsg.translate("QAD", "Yes") + "/" + \
                             QadMsg.translate("QAD", "No")
                  default = QadMsg.translate("QAD", "Yes")
                  prompt = QadMsg.translate("Command_UNDO", "This will undo everything. OK ? <{0}>: ").format(default)

                  englishKeyWords = "Yes" + "/" + "No"
                  keyWords += "_" + englishKeyWords
                  # is preparing to wait for enter or a keyword
                  # msg, inputType, default, keyWords, no check
                  self.waitFor(prompt, \
                               QadInputTypeEnum.KEYWORDS, \
                               default, \
                               keyWords, QadInputModeEnum.NONE)
                  self.step = 2
                  return False
               else:
                  self.plugIn.undoUntilBookmark()
         elif type(value) == int:
            self.plugIn.undoEditCommand(value)

         return True

      # =========================================================================
      # RESPONSE TO THE REQUEST TO CANCEL EVERYTHING (from step = 1)
      elif self.step == 2: # after waiting for a keyword the command is restarted
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if while selecting a point
            # Another plugin was activated which deactivated Qad
            # so the command that returns here has been reactivated without the map tool
            # has selected a point
            if self.getPointMapTool().point is None: # the map tool was activated without a dot
               if self.getPointMapTool().rightButton == True: # if used with the right mouse button
                  self.plugIn.undoUntilBookmark()
                  self.showMsg(QadMsg.translate("Command_UNDO", "All has been undone."))
                  return True # end command
               else:
                  self.setMapTool(self.getPointMapTool()) # I reactivate the map tool
                  return False

            value = self.getPointMapTool().point
         else: # the dot comes as a parameter of the function
            value = msg

         if type(value) == unicode:
            if value == QadMsg.translate("QAD", "Yes") or value == "Yes":
               self.showMsg(QadMsg.translate("Command_UNDO", "All has been undone."))
               self.plugIn.undoUntilBookmark()

         return True # end command


# Class that manages the REDO command
class QadREDOCommandClass(QadCommandClass):

   def instantiateNewCmd(self):
      """instantiates a new command of the same type"""
      return QadREDOCommandClass(self.plugIn)

   def getName(self):
      return QadMsg.translate("Command_list", "REDO")

   def getEnglishName(self):
      return "REDO"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runREDOCommand)

   def getIcon(self):
      return QIcon(":/plugins/qad/icons/redo.svg")

   def getNote(self):
      # set the explanatory notes of the command
      return QadMsg.translate("Command_UNDO", "Reverses the effects of previous UNDO.")

   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)

   def run(self, msgMapTool = False, msg = None):
      self.plugIn.redoEditCommand()
      return True