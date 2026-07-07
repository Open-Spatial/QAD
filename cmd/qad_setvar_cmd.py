# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 SETVAR command to set QAD environment variables

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
from ..qad_variables import QadVariables, QadVariableTypeEnum


# Class that manages the SETVAR command
class QadSETVARCommandClass(QadCommandClass):

   def instantiateNewCmd(self):
      """instantiates a new command of the same type"""
      return QadSETVARCommandClass(self.plugIn)

   def getName(self):
      return QadMsg.translate("Command_list", "SETVAR")

   def getEnglishName(self):
      return "SETVAR"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runSETVARCommand)

   def getIcon(self):
      return QIcon(":/plugins/qad/icons/variable.svg")

   def getNote(self):
      # set the explanatory notes of the command
      return QadMsg.translate("Command_SETVAR", "Sets the QAD environment variables.")

   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      self.varName = ""


   def run(self, msgMapTool = False, msg = None):
      if self.step == 0: # start of command
         # is preparing to wait for a string
         self.waitForString(QadMsg.translate("Command_SETVAR", "Enter the variable name or [?]: "), \
                            QadMsg.translate("Command_SETVAR", "?"))
         self.step = 1
         return False
      elif self.step == 1: # after waiting for the name of the variable the command is restarted
         if msgMapTool == True: # nothing can come from graphics
            return False
         #  the variable name comes as a function parameter
         self.varName = msg
         if self.varName == QadMsg.translate("Command_SETVAR", "?"): # list of variables
            # is preparing to wait for a string
            self.waitForString(QadMsg.translate("Command_SETVAR", "Enter variable(s) to list <*>: "), \
                               QadMsg.translate("Command_SETVAR", "*"))
            self.step = 3
            return False
         else:
            variable = QadVariables.getVariable(self.varName)
            if variable is None:
               msg = QadMsg.translate("Command_SETVAR", "\nUnknown variable. Enter {0} ? to list variable names.")
               self.showErr(msg.format(QadMsg.translate("Command_list", "SETVAR")))
               return False
            else:
               varValue = variable.value
               varDescr = variable.descr
               varType  = variable.typeValue

               if len(varDescr) > 0:
                  self.showMsg("\n" + varDescr)

               msg = QadMsg.translate("Command_SETVAR", "Enter new value for variable {0} <{1}>: ")
               if varType == QadVariableTypeEnum.STRING:
                  # is preparing to wait for a string
                  self.waitForString(msg.format(self.varName, varValue), varValue)
               elif varType == QadVariableTypeEnum.INT:
                  # is preparing to wait for an integer
                  self.waitForInt(msg.format(self.varName, varValue), varValue)
               elif varType == QadVariableTypeEnum.FLOAT:
                  # is preparing to wait for a real number
                  self.waitForFloat(msg.format(self.varName, varValue), varValue)
               elif varType == QadVariableTypeEnum.BOOL:
                  # is preparing to wait for a real number
                  self.waitForBool(msg.format(self.varName, varValue), varValue)
               elif varType == QadVariableTypeEnum.COLOR:
                  # is preparing to wait for a #RRGGBB COLOR
                  self.waitForString(msg.format(self.varName, varValue), varValue)
               self.step = 2
               return False
      elif self.step == 2: # after waiting for the value of the variable, the command is restarted
         if msgMapTool == True: # nothing can come from graphics
            return False
         # the value of the variable comes as a parameter of the function
         if QadVariables.set(self.varName, msg) == False: # invalid value
            msg = QadMsg.translate("Command_SETVAR", "\nValue not valid.")
            self.showErr(msg)
            return False
         else: # valid value
            QadVariables.save()
            self.plugIn.UpdatedVariablesEvent()
            return True
      elif self.step == 3: # after waiting for the name of the variable the command is restarted
         if msgMapTool == True: # nothing can come from graphics
            return False

         if msg == "*":
            varNames = QadVariables.getVarNames()
         else:
            #  the variable name comes as a function parameter
            varNames = msg.strip().split(",")

         varNames.sort()
         for self.varName in varNames:
            self.varName = self.varName.strip()
            varValue = QadVariables.get(self.varName)
            if varValue is not None:
               msg = "\n" + self.varName + "=" + str(varValue)
               self.showMsg(msg)

         self.plugIn.UpdatedVariablesEvent()

         return True