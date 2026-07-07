# -*- coding: utf-8 -*-

"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 class to manage command aliases

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
from qgis.PyQt.QtCore import *
import os.path
import codecs
from qgis.core import *


from . import qad_utils


# Class that handles Qad command aliases
class QadCommandAliasesClass():

   def __init__(self):
      self.__commandAliases = dict()  # dictionary of command aliases

   def getCommandAliasDict(self,):
      """Returns the alias dictionary"""
      return self.__commandAliases

   # ============================================================================
   # getCommandName
   # ============================================================================
   def getCommandName(self, alias):
      """Given the alias it returns the name of the command"""
      if type(alias) == str or type(alias) == unicode:
         return self.__commandAliases.get(alias.upper())
      else:
         return self.__commandAliases.get(alias.toUpper())


   # ============================================================================
   # load
   # ============================================================================
   def load(self, Path = "", exceptionList = None):
      """Load the list of command aliases from file
            Returns True on success, false on error
      """
      # I empty the dictionary and reset it with the default values
      self.__commandAliases.clear()

      if Path == "":
         # If the path is not indicated I use the "qad.pgp" file in the local language
         userLocaleList = QSettings().value("locale/userLocale").split("_")
         language = userLocaleList[0]
         region = userLocaleList[1] if len(userLocaleList) > 1 else ""

         fileName = "qad" + "_" + language + "_" + region + ".pgp "# I try to load the selected language and region
         Path = qad_utils.findFile(fileName)
         if Path == "": # if file not found
            fileName = "qad" + "_" + language + ".pgp " # I try to load the language
            Path = qad_utils.findFile(fileName)
            if Path == "": # if file not found
               return True
      else:
         if not os.path.exists(Path):
            return True

      file = codecs.open(unicode(Path), "r", encoding='utf-8') # opens the file for reading in unicode utf-8 mode

      for line in file:
         line = qad_utils.strip(line, [" ", "\t", "\r\n"]) # I remove spaces and tabs before and after
         if len(line) == 0:
            continue
         # if the line begins with ; then it is a commented line
         if line[0] == ";":
            continue

         # I read the name of the alias + the name of the command (e.g. "alias, *command")
         sep = line.find(",")
         if sep <= 0:
            continue
         alias = line[0:sep]
         alias = qad_utils.strip(alias, [" ", "\t", "\r\n"]) # I remove spaces and tabs before and after
         if len(alias) == 0:
            continue

         command = line[sep+1:]
         command = qad_utils.strip(command, [" ", "\t", "\r\n"]) # I remove spaces and tabs before and after
         if len(command) <= 1:
            continue
         # if the command does not begin with * then it is not an alias
         if command[0] != "*":
            continue
         command = command[1:]
         # the command cannot contain spaces
         sep = command.find(" ")
         if sep > 0:
            continue

         if exceptionList is None:
            self.__commandAliases[alias.upper()] = command.upper()
         else:
            if alias.upper() not in exceptionList:
               self.__commandAliases[alias.upper()] = command.upper()

      file.close()

      return True
