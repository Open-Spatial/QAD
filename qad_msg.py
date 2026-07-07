# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 class for message translations

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


from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui  import * # for QDesktopServices
import os.path
import sys

import urllib.parse
import platform
#from plotly.graph_objs.bar.marker.colorbar import title
import webbrowser


# traduction class.
class QadMsgClass():


   def __init__(self):
      pass


   # ============================================================================
   # translate
   # ============================================================================
   def translate(self, context, sourceText, disambiguation = None, n = -1):
      # to use in a line without coupling it to other calls for example (for lupdate.exe which otherwise doesn't find them):
      # NON VA BENE
      #     proplist["blockScale"] = [QadMsg.translate("Dimension", "Scala frecce"), \
      #                               self.blockScale]
      # VA BENE
      #     msg = QadMsg.translate("Dimension", "Scala frecce")
      #     proplist["blockScale"] = [msg, self.blockScale]

      # contesti:
      # "QAD" for general translations
      # "Popup_menu_graph_window" for the popup menu in the graphics window
      # "Text_window" for the text window
      # "Command_list" for command names
      # "Command_<English command name>" for translations of a specific command (e.g. "Command_PLINE")
      # "Snap" for snap types
      # finestre varie (es. "DSettings_Dialog", DimStyle_Dialog, ...)
      # "Dimension" for dimensions
      # "Environment variables" for environment variable names
      # "Help" for the titles of the chapters of the manual which serve as sections in the help html file
      return QCoreApplication.translate(context, sourceText, disambiguation, n)



   # ===============================================================================
   # getQADTitle
   # ===============================================================================
   def getQADTitle(self, sponsorWith = False):
      title = QadMsg.translate("QAD", "QAD")
      if sponsorWith == True:
         title += " (supported by "
         title +=  QadMsg.translate("SUPPORTER", "SUPPORTER WANTED")
         title += ")"

      return title


# ===============================================================================
# qadShowPluginHelp
# ===============================================================================
def qadShowPluginPDFHelp(section = "", filename = "QAD"):
   """Opens the help file in PDF format to the notes section.
      to know the section/page of the html file use internet explorer,
      select the item of interest in the right window and read its address from the box at the top.
      This is because Internet Explorer inserts all the whitespace and tab characters that other browsers don't.
   """
   basepath = os.path.dirname(os.path.realpath(__file__))

   # initialize locale
   userLocaleList = QSettings().value("locale/userLocale").split("_")
   language = userLocaleList[0]
   region = userLocaleList[1] if len(userLocaleList) > 1 else ""

   path = QDir.cleanPath(basepath + "/help")
   helpfile = os.path.join(path, filename + "_" + language + "_" + region + ".pdf") # I try to load the selected language and region

   if not os.path.exists(helpfile):
      helpfile = os.path.join(path, filename + "_" + language + ".pdf")  # I try to load the language
      if not os.path.exists(helpfile):
         helpfile = os.path.join(path, filename + "_en" + ".pdf") # I try to load the English language
         if not os.path.exists(helpfile):
            return

   if section != "":
      helpfile = helpfile + "#" + urllib.parse.quote(section.encode('utf-8').decode('utf-8'))

   webbrowser.open_new(helpfile)


# ===============================================================================
# qadShowPluginHelp
# ===============================================================================
def qadShowPluginHelp(section = "", filename = "index", packageName = None):
   """show a help in the user's html browser.
      to know the section/page of the html file use internet explorer,
      select the item of interest in the right window and read its address from the box at the top.
      This is because Internet Explorer inserts all the whitespace and tab characters that other browsers don't.
   """
   try:
      basepath = ""
      if packageName is None:
         basepath = os.path.dirname(os.path.realpath(__file__))
      else:
         basepath = os.path.dirname(os.path.realpath(sys.modules[packageName].__file__))
   except:
      return

   # initialize locale
   userLocaleList = QSettings().value("locale/userLocale").split("_")
   language = userLocaleList[0]
   region = userLocaleList[1] if len(userLocaleList) > 1 else ""

   path = QDir.cleanPath(basepath + "/help/help")
   helpPath = path + "_" + language + "_" + region # I try to load the selected language and region

   if not os.path.exists(helpPath):
      helpPath = path + "_" + language # I try to load the language
      if not os.path.exists(helpPath):
         helpPath = path + "_en" # I try to load the English language
         if not os.path.exists(helpPath):
            return

   helpfile = os.path.join(helpPath, filename + ".html")
   if os.path.exists(helpfile):
      url = "file:///"+helpfile

      if section != "":
         url = url + "#" + urllib.parse.quote(section.encode('utf-8').decode('utf-8'))

      # the QDesktopServices.openUrl function in windows does not open the section
      if platform.system() == "Windows":
         import subprocess
         from winreg import HKEY_CURRENT_USER, HKEY_LOCAL_MACHINE, OpenKey, QueryValue

         try: # provo a livello di utente
            with OpenKey(HKEY_CURRENT_USER, r"Software\Classes\http\shell\open\command") as key:
               cmd = QueryValue(key, None)
         except: # if it wasn't there at user level I try at machine level
            with OpenKey(HKEY_LOCAL_MACHINE, r"Software\Classes\http\shell\open\command") as key:
               cmd = QueryValue(key, None)

         if cmd.find("\"%1\"") >= 0:
            subprocess.Popen(cmd.replace("%1", url))
         else:
            if cmd.find("%1") >= 0:
               subprocess.Popen(cmd.replace("%1", "\"" + url + "\""))
            else:
               subprocess.Popen(cmd + " \"" + url + "\"")
      else:
         QDesktopServices.openUrl(QUrl(url))


# ===============================================================================
# qadShowSupportersPage
# ===============================================================================
def qadShowSupportersPage():
   """
   show the supporter members page in the user's html browser.
   """
   try:
      webbrowser.open_new("https://qadplugin.wordpress.com/donations")
   except:
      return


# ===============================================================================
# QadMsg = global variable
# ===============================================================================

QadMsg = QadMsgClass()
