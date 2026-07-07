# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 various utility functions

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

from qgis.PyQt.QtCore import QVariant, QDir, QMetaType, QRect
from qgis.PyQt.QtGui  import QCursor, QPixmap, QColor, QFont, QPalette, QGuiApplication
from qgis.PyQt.QtWidgets import QToolTip, QMessageBox, QApplication
from qgis.core import *
import qgis.utils


import os
import math
import sys
from gettext import find
import configparser
import time
import uuid, re

from .qad_variables import QadVariables
from .qad_msg import QadMsg


# Module that manages various QAD features


def getScreenGeometry(widget=None, globalPos=None, available=True):
   screen = None

   if globalPos is not None:
      app = QApplication.instance()
      if app is not None and hasattr(app, "screenAt"):
         screen = app.screenAt(globalPos)

   if screen is None and widget is not None:
      try:
         screen = widget.screen()
      except AttributeError:
         screen = None

   if screen is None:
      screen = QGuiApplication.primaryScreen()

   if screen is None:
      return QRect()

   return screen.availableGeometry() if available else screen.geometry()


def getMacAddress():
   return ':'.join(re.findall('..', '%012x' % uuid.getnode())).upper()


def criptPlainText(strValue):
   mytable = str.maketrans('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz -./0123456789:;<=>?@"', \
                           'NOPQRSTUVWXYZABCDEFGHIJKLMnopqrstuvwxyzabcdefghijklm9:;<=>?@" -./012345678')
   return strValue.translate(mytable)


def decriptPlainText(strValue):
   mytable = str.maketrans('NOPQRSTUVWXYZABCDEFGHIJKLMnopqrstuvwxyzabcdefghijklm9:;<=>?@" -./012345678', \
                           'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz -./0123456789:;<=>?@"')
   return strValue.translate(mytable)


# ===============================================================================
# GENERIC FUNCTIONS FOR COMMAND OPTIONS - START
# ===============================================================================


def extractUpperCaseSubstr(str):
   # I extract the uppercase part of the string
   upperPart = ""
   for letter in str:
      if letter.isupper():
         upperPart = upperPart + letter
      elif len(upperPart) > 0:
         break
   return upperPart


def evaluateCmdKeyWords(cmd, keyWordList):
   # Receives a command and the list of command option keywords
   # The function returns the keyword of the command followed by a possible error message if the keyword = None

   # The required portion of the keyword is specified in uppercase characters,
   # and the remainder of the keyword is specified in lowercase characters.
   # The uppercase abbreviation can be anywhere in the keyword
   if cmd == "": # if cmd = "" the find function returns 0 (no comment)
      return None, None
   upperCmd = cmd.upper()
   selectedKeyWords = []
   for keyWord in keyWordList:
      # I extract the capital part of the keyword
      upperPart = extractUpperCaseSubstr(keyWord)

      if upperPart.find(upperCmd) == 0: # if the uppercase part of the keyword begins with upperCmd
         if upperPart == upperCmd: # If equal
            return keyWord, None
         else:
            selectedKeyWords.append(keyWord)
      elif keyWord.upper().find(upperCmd) == 0: # if the keyword begins with cmd (insensitive)
         if keyWord.upper() == upperCmd: # If equal
            return keyWord, None
         else:
            selectedKeyWords.append(keyWord)

   selectedKeyWordsLen = len(selectedKeyWords)
   if selectedKeyWordsLen == 0:
      return None, None
   elif selectedKeyWordsLen == 1:
      return selectedKeyWords[0], None
   else:
      Msg = QadMsg.translate("QAD", "\nAmbiguous answer: specify with more clarity...")
      ambiguousMsg = ""
      for keyWord in selectedKeyWords:
         if ambiguousMsg == "":
            ambiguousMsg = keyWord
         else:
            ambiguousMsg = ambiguousMsg + QadMsg.translate("QAD", " or ") + keyWord

      Msg = Msg + "\n" + ambiguousMsg + QadMsg.translate("QAD", " ?\n")

   return None, Msg


# ===============================================================================
# GENERIC FUNCTIONS FOR COMMAND OPTIONS - END
# GENERIC FUNCTIONS FOR WIDGETS - TOP
# ===============================================================================


# ===============================================================================
# setMapCanvasToolTip
# ===============================================================================
# displays the mapCanvas tooltip text with the appearance determined by DYNTOOLTIPS
def setMapCanvasToolTip(msg):
   canvas = qgis.utils.iface.mapCanvas()
   pt = canvas.mapToGlobal(canvas.mouseLastXY())

   if QadVariables.get(QadMsg.translate("Environment variables", "DYNTOOLTIPS")) == 1:
      font_size = 8 + QadVariables.get(QadMsg.translate("Environment variables", "TOOLTIPSIZE"))

      #opacity = 100 - QadVariables.get(QadMsg.translate("Environment variables", "TOOLTIPTRANSPARENCY"))
      #fc.setAlphaF(opacity/100.0) # non va

      fColor = QColor(QadVariables.get(QadMsg.translate("Environment variables", "DYNEDITFORECOLOR")))
      bColor = QColor(QadVariables.get(QadMsg.translate("Environment variables", "DYNEDITBACKCOLOR")))
   else:
      font_size = QFont().pointSize()
      p = QPalette()
      fColor = p.color(QPalette.Inactive, QPalette.ToolTipText)
      bColor = p.color(QPalette.Inactive, QPalette.ToolTipBase)

   toolTipFont = QToolTip.font()
   if toolTipFont.pointSize() != font_size:
      toolTipFont.setPointSize(font_size)
      QToolTip.setFont(toolTipFont)

   toolTipPalette = QToolTip.palette()
   if toolTipPalette.color(QPalette.Inactive, QPalette.ToolTipText) != fColor or \
      toolTipPalette.color(QPalette.Inactive, QPalette.ToolTipBase) != bColor:
      toolTipPalette.setColor(QPalette.Inactive, QPalette.ToolTipText, fColor)
      toolTipPalette.setColor(QPalette.Inactive, QPalette.ToolTipBase, bColor)
      QToolTip.setPalette(toolTipPalette)

   QToolTip.showText(pt, msg)

   return


# ===============================================================================
# floatLineEditWidgetValidation
# ===============================================================================
# checks that the value of a line edit widget satisfies the allowed range for the environment variable
def intLineEditWidgetValidation(widget, var, msg):
   err = False
   string = widget.text()
   if str2int(string) is None:
      err = True
   else:
      if var.minNum is not None:
         if str2int(string) < var.minNum:
            err = True
      if var.maxNum is not None:
         if str2int(string) > var.maxNum:
            err = True

   if err:
      msg = msg + QadMsg.translate("QAD", ": enter a number")
      if var.minNum is not None:
         msg = msg + QadMsg.translate("QAD", " >= {0}").format(str(var.minNum))
      if var.maxNum is not None:
         if var.minNum is not None:
            msg = msg + QadMsg.translate("QAD", " and")
         msg = msg + QadMsg.translate("QAD", " <= {0}").format(str(var.maxNum))
      msg = msg + "."
      QMessageBox.critical(None, QadMsg.getQADTitle(), msg)
      widget.setFocus()
      widget.selectAll()
      return False
   return True


# ===============================================================================
# floatLineEditWidgetValidation
# ===============================================================================
# checks that the value of a line edit widget satisfies the allowed range for the environment variable
def floatLineEditWidgetValidation(widget, var, msg):
   err = False
   string = widget.text()
   if str2float(string) is None:
      err = True
   else:
      if var.minNum is not None:
         if str2float(string) < var.minNum:
            err = True
      if var.maxNum is not None:
         if str2float(string) > var.maxNum:
            err = True

   if err:
      msg = msg + QadMsg.translate("QAD", ": enter a number")
      if var.minNum is not None:
         minValMsg = msg + QadMsg.translate("QAD", " > {0}").format(str(var.minNum))
      else:
         minValMsg = ""
      if var.maxNum is not None:
         if len(minValMsg) > 0:
            msg = msg + QadMsg.translate("QAD", " and")
         msg = msg + QadMsg.translate("QAD", " < {0}").format(str(var.maxNum))
      msg = msg + "."
      QMessageBox.critical(None, QadMsg.getQADTitle(), msg)
      widget.setFocus()
      widget.selectAll()
      return False
   return True


# ===============================================================================
# GENERIC FUNCTIONS FOR WIDGETS - END
# ===============================================================================


# ===============================================================================
# isNumericField
# ===============================================================================
def isNumericField(field):
   """The function verifies that the QgsField type field is numeric"""
   fldType = field.type()
   if fldType == QMetaType.Double or fldType == QMetaType.LongLong or fldType == QMetaType.Int or \
      fldType == QMetaType.ULongLong or fldType == QMetaType.UInt:
      return True
   else:
      return False


# ===============================================================================
# checkUniqueNewName
# ===============================================================================
def checkUniqueNewName(newName, nameList, prefix = None, suffix = None, caseSensitive = True):
   """The function checks that the new name does not already exist in the <nameList> list.
      If it already exists in the list then add a prefix (if <> None) or a suffix (if <> None)
      until the name is no longer in the list
   """
   ok = False
   result = newName
   while ok == False:
      ok = True
      for name in nameList:
         if caseSensitive == True:
            if name == result:
               ok = False
               break
         else:
            if name.upper() == result.upper():
               ok = False
               break

      if ok == True:
         return result
      if prefix is not None:
         result = prefix + result
      else:
         if suffix is not None:
            result = result + suffix

   return None

# ===============================================================================
# wildCard2regularExpr
# ===============================================================================
def wildCard2regularExpr(wildCard, ignoreCase = True):
   """Returns the conversion of a string with wildcards (e.g. "gas*")
      in the form of a regular expression (e.g. "[g][a][s].*")
   """
   # ? -> .
   # * -> .*
   # other characters -> [character]
   regularExpr = ""
   for ch in wildCard:
      if ch == "?":
         regularExpr = regularExpr + "."
      elif ch == "*":
         regularExpr = regularExpr + ".*"
      else:
         if ignoreCase:
            regularExpr = regularExpr + "[" + ch.upper() + ch.lower() + "]"
         else:
            regularExpr = regularExpr + "[" + ch + "]"

   return regularExpr


# ===============================================================================
# str2float
# ===============================================================================
def str2float(s):
   """Returns the conversion of a string to a real number"""
   try:
      n = float(s)
      return n
   except ValueError:
      return None


# ===============================================================================
# str2long
# ===============================================================================
def str2long(s):
   """Returns the conversion of a string to a long number"""
   try:
      n = long(s)
      return n
   except ValueError:
      return None


# ===============================================================================
# str2int
# ===============================================================================
def str2int(s):
   """Returns the conversion of a string to an integer"""
   try:
      n = int(s)
      return n
   except ValueError:
      return None


# ===============================================================================
# str2bool
# ===============================================================================
def str2bool(s):
   """Returns the conversion of a string to bool"""
   try:
      upperS = s.upper()
      # 16 = "N", 17 = "NO"
      # "F" "FALSO"
      if upperS == "0" or \
         upperS == QadMsg.translate("QAD", "N") or \
         upperS == QadMsg.translate("QAD", "NO") or \
         upperS == QadMsg.translate("QAD", "F") or \
         upperS == QadMsg.translate("QAD", "FALSE") or \
         upperS == "FALSE":
         return False
      else:
         return True
   except ValueError:
      return None


# ===============================================================================
# str2QgsPoint
# ===============================================================================
def str2QgsPoint(s, lastPoint = None, currenPoint = None, oneNumberAllowed = True):
   """Returns the conversion of a string to QgsPointXY point
      if <oneNumberAllowed> = False it means that s cannot be a single number
      which would represent the distance from the last angled point based on the current point
      (this is prohibited when you want to accept a number or a point)
      lastPoint is used only for expressions like @10<45 (from last point, length 10, angle 45 degrees)
      or @ (from the last period)
      or @10.20 (from the last point, +10 for the X and +20 for the Y)
      or 100 (from last point, distance 100, angle based on current point)
   """
   expression = s.strip() # without leading or trailing spaces
   if len(expression) == 0:
      return None

   if expression[0] == "@": # coordinate relative a lastpoint
      if lastPoint is None:
         return None

      if len(expression) == 1:
         return lastPoint

      expression = expression[1:] # I discard the first "@" character
      coords = expression.split(",")
      if len(coords) == 2:
         OffSetX = str2float(coords[0].strip())
         OffSetY = str2float(coords[1].strip())
         if (OffSetX is None) or (OffSetY is None):
            return None
         return QgsPointXY(lastPoint.x() + OffSetX, lastPoint.y() + OffSetY)
      else:
         if len(coords) != 1:
            return None
         # check if the polar coordinate is being used
         expression = coords[0].strip()
         values = expression.split("<")
         if len(values) != 2:
            return None
         dist = str2float(values[0].strip())
         angle = str2float(values[1].strip())
         if (dist is None) or (angle is None):
            return None
         coords = getPolarPointByPtAngle(lastPoint, math.radians(angle), dist)
         return QgsPointXY(coords[0], coords[1])
   else:
      # check if a CRS is specified
      CRS, newExpr = strFindCRS(expression)
      if CRS is not None:
         if CRS.isGeographic():
            pt = strLatLon2QgsPoint(newExpr)
         else:
            coords = newExpr.split(",")
            if len(coords) != 2:
               return None
            x = str2float(coords[0].strip())
            y = str2float(coords[1].strip())
            if (x is None) or (y is None):
               return None
            pt = QgsPointXY(x, y)

         if pt is not None:
            destCRS = qgis.utils.iface.mapCanvas().mapSettings().destinationCrs() # Current CRS
            return QgsCoordinateTransform(CRS, destCRS, QgsProject.instance()).transform(pt) # I transform the coordinates


      coords = expression.split(",")
      if len(coords) == 2:  # coordinate assolute
         x = str2float(coords[0].strip())
         y = str2float(coords[1].strip())
         if (x is None) or (y is None):
            return None
         return QgsPointXY(x, y)
      else:
         if oneNumberAllowed == False: # forbidden for the string to be a single number
            return None

         dist = str2float(expression)

         if (dist is None) or (lastPoint is None) or (currenPoint is None):
            return None

         angle = getAngleBy2Pts(lastPoint, currenPoint)
         coords = getPolarPointByPtAngle(lastPoint, angle, dist)
         return QgsPointXY(coords[0], coords[1])


# ===============================================================================
# pointToStringFmt
# ===============================================================================
def pointToStringFmt(pt):
   """Returns the conversion of a QgsPointXY point to a formatted string"""
   return numToStringFmt(pt.x()) + "," + numToStringFmt(pt.y())


# ===============================================================================
# numToStringFmt
# ===============================================================================
def numToStringFmt(n, textDecimals = 4, textDecimalSep = '.', \
                      textSuppressLeadingZeros = False, textDecimalZerosSuppression = True,
                      textPrefix = "", textSuffix = ""):
   """Returns the conversion of a number (int or float) to a formatted string"""
   strIntPart, strDecPart = getStrIntDecParts(round(n, textDecimals)) # number of decimals

   if strIntPart == "0" and textSuppressLeadingZeros == True: # to suppress zeros at the beginning of the text or not
      strIntPart = ""

   for i in range(0, textDecimals - len(strDecPart), 1):  # adds "0" to arrive at the number of decimals
      strDecPart = strDecPart + "0"

   if textDecimalZerosSuppression == True: # to suppress trailing zeros in decimals
      strDecPart = strDecPart.rstrip("0")

   formattedText = "-" if n < 0 else "" # segno
   formattedText = formattedText + strIntPart # entire part
   if len(strDecPart) > 0: # decimal part
      formattedText = formattedText + textDecimalSep + strDecPart # decimal separator
   # add prefix and suffix for the dimension text
   return textPrefix + formattedText + textSuffix


# ===============================================================================
# strLatLon2QgsPoint
# ===============================================================================
def strFindCRS(s):
   """Looks up the coordinate system in a string indicating a point (use authid).
      The coordinate system must be expressed anywhere in the string and must be
      enclosed in round brackets (e.g. "111,222 (EPSG:3003)")
      Returns the SR and the purified SR string (e.g. "111,222")
   """
   initial = s.find("(")
   if initial == -1:
      return None, s
   final = s.find(")")
   if initial > final:
      return None, s
   authId = s[initial+1:final]
   authId = authId.strip() # without leading or trailing spaces
   return QgsCoordinateReferenceSystem(authId), s.replace(s[initial:final+1], "")


# ===============================================================================
# strLatLon2QgsPoint
# ===============================================================================
def strLatLon2QgsPoint(s):
   """Returns the conversion of a string containing a coordinate into latitude longitude
      o'clock QgsPointXY.

      The following formats are supported:
      DDD decimal degrees (49.11675S or S49.11675 or 49.11675 S or S 49.11675 or -49.1167)
      DMS degrees minutes seconds (49 7 20.06)
      DMM degrees minutes with decimal seconds (49 7.0055)

      Syntax latitude longitude:
      The separator can be a space, you can also use ' for minutes and " for seconds (47 7'20.06")
      The direction notation is uppercase or lowercase N, S, E, W before or after the coordinate
      ("N 37 24 23.3" or "N37 24 23.3" or "37 24 23.3 N" or "37 24 23.3N")
      You can also use negative coordinates for west and south.

      The first coordinate is interpreted as latitude unless you specify a direction letter (E or W)
      ("122 05 08.40 W 37 25 19.07 N")
      You can use a space, comma, or slash to delimit value pairs
      ("37.7 N 122.2 W" or "37.7 N,122.2 W" or "37.7 N/122.2 W")
   """
   expression = s.strip() # without leading or trailing spaces
   if len(expression) == 0:
      return None

   numbers = []
   directions = []
   word = ""
   for ch in s:
      if ch.isnumeric() or ch == "." or ch == "-":
         word += ch
      else:
         if len(word) > 0:
            n = str2float(word)
            if n is None:
               return None
            numbers.append(n)
            word = ""
         if ch == "N" or ch == "n" or ch == "S" or ch == "s" or ch == "E" or ch == "e" or ch == "W" or ch == "w":
            directions.append(ch.upper())
            word = ""

   directions_len = len(directions)
   if directions_len != 0 and directions_len != 2:
      return None

   numbers_len = len(numbers)
   if numbers_len == 2: # DDD
      lat = numbers[0]
      lon = numbers[1]
   elif numbers_len == 4: # DMM
      degrees = numbers[0]
      minutes = numbers[1]
      lat = degrees + minutes / 60
      degrees = numbers[2]
      minutes = numbers[3]
      lon = degrees + minutes / 60
   elif numbers_len == 6: # DMS
      degrees = numbers[0]
      minutes = numbers[1]
      seconds = numbers[2]
      lat = degrees + minutes / 60 + seconds / 3600
      degrees = numbers[3]
      minutes = numbers[4]
      seconds = numbers[5]
      lon = degrees + minutes / 60 + seconds / 3600
   else:
      return None

   if directions_len == 2:
      if lat < 0 or lon < 0:
         return None
      if directions[0] == "N" or directions[0] == "S": # latitude first
         if directions[0] == "S":
            lat = -lat
      elif directions[0] == "E" or directions[0] == "W": # longitude first
         dummy = lat
         lat = lon if directions[0] == "E" else -lon
         lon = dummy if directions[1] == "S" else -value2
      else:
         return None

      return QgsPointXY(lon, lat)
   else: # latitude first
      return QgsPointXY(lon, lat)


# ===============================================================================
# strip
# ===============================================================================
def strip(s, stripList):
   """Removes from the string <s> all the strings in the list <stripList> that are
      at the beginning and also at the end of the <s> string
   """
   for item in stripList:
      s = s.strip(item) # remove before and after
   return s


# ===============================================================================
# findFile
# ===============================================================================
def findFile(fileName):
   """Searc for the indicated file using the paths indicated by the "SUPPORTPATH" variable
      plus the local path of QAD. Returns the file path if successful
      or "" in case of file not found
   """
   path = QadVariables.get(QadMsg.translate("Environment variables", "SUPPORTPATH"))
   if len(path) > 0:
      path += ";"
   path += QgsApplication.qgisSettingsDirPath() + "python/plugins/qad/"
   # list of directories separated by ";"
   dirList = path.strip().split(";")
   for _dir in dirList:
      _dir = QDir.cleanPath(_dir)
      if _dir != "":
         if _dir.endswith("/") == False:
            _dir = _dir + "/"
         _dir = _dir + fileName

         if os.path.exists(_dir):
            return _dir

   return ""

   return s


# ===============================================================================
# getQADPath
# ===============================================================================
def getQADPath():
   """Returns the QAD installation path"""
   return os.path.dirname(os.path.realpath(__file__))


# ===============================================================================
# toRadians
# ===============================================================================
def toRadians(angle):
   """
   Converte da gradi a radianti
   """
   return math.radians(angle)


# ===============================================================================
# toDegrees
# ===============================================================================
def toDegrees(angle):
   """
   Converte da radianti a gradi
   """
   return math.degrees(angle)


# ===============================================================================
# normalizeAngle
# ===============================================================================
def normalizeAngle(angle, norm = math.pi * 2):
   """Normalize an angle to from [0 - 2pi] or from [0 - pi].
      So, for example, if an angle is larger than 2pi it is reduced to the right angle
      (the comparison in degrees would be from 380 to 20 degrees) or if it is negative it becomes positive
      (the comparison in degrees would be -90 to 270 degrees)
   """
   if angle == 0:
      return 0
   if angle > 0:
      return angle % norm
   else:
      return norm - ((-angle) % norm)


# ===============================================================================
# getStrIntDecParts
# ===============================================================================
def getStrIntDecParts(n):
   """Returns two strings representing the unsigned integer part and the decimal part of a number"""
   if type(n) == int or type(n) == long or type(n) == float:
      nStr = str(n)
      if "." in nStr:
         parts = nStr.split(".")
         return str(abs(int(parts[0]))), parts[1]
      else:
         return nStr, ""
   else:
      return None


# ===============================================================================
# distMapToLayerCoordinates
# ===============================================================================
def distMapToLayerCoordinates(dist, canvas, layer):
   # I find the central point of the screen
   boundBox = canvas.extent()
   x = (boundBox.xMinimum() + boundBox.xMaximum()) / 2
   y = (boundBox.yMinimum() + boundBox.yMaximum()) / 2
   pt1 = QgsPointXY(x, y)
   pt2 = QgsPointXY(x + dist, y)
   transformedPt1 = canvas.mapSettings().mapToLayerCoordinates(layer, pt1)
   transformedPt2 = canvas.mapSettings().mapToLayerCoordinates(layer, pt2)
   return getDistance(transformedPt1, transformedPt2)


# ===============================================================================
# filterFeaturesByType
# ===============================================================================
def filterFeaturesByType(features, filterByGeomType):
   """Receives a list of features and the type of geometry that needs to be filtered.
      The function modifies the <features> list, purifying it of geometries of different types
      from <filterByGeomType>.
      Returns 3 lists of points, lines and polygons respectively.
      The list of the type indicated by the <filterByGeomType> parameter will be empty, the others
      two lists will contain geometries.
   """
   resultPoint = []
   resultLine = []
   resultPolygon = []

   for i in range(len(features) - 1, -1, -1):
      f = features[i]
      g = f.geometry()
      geomType = g.type()
      if geomType != filterByGeomType:
         if geomType == QgsWkbTypes.PointGeometry:
            resultPoint.append(QgsGeometry(g))

         elif geomType == QgsWkbTypes.LineGeometry:
            resultLine.append(QgsGeometry(g))

         elif geomType == QgsWkbTypes.PolygonGeometry:
            resultPolygon.append(QgsGeometry(g))

         del features[i]

   return resultPoint, resultLine, resultPolygon


# ===============================================================================
# filterGeomsByType
# ===============================================================================
def filterGeomsByType(geoms, filterByGeomType):
   """Receives a list of geometries and the type of geometry that needs to be filtered.
      The function modifies the <geoms> list, purging it of geometries of different types
      from <filterByGeomType>.
      Returns 3 lists of points, lines and polygons respectively.
      The list of the type indicated by the <filterByGeomType> parameter will be empty, the others
      two lists will contain geometries.
   """
   resultPoint = []
   resultLine = []
   resultPolygon = []

   for i in range(len(geoms) - 1, -1, -1):
      g = geoms[i]
      geomType = g.type()
      if geomType != filterByGeomType:
         if geomType == QgsWkbTypes.PointGeometry:
            resultPoint.append(QgsGeometry(g))

         elif geomType == QgsWkbTypes.LineGeometry:
            resultLine.append(QgsGeometry(g))

         elif geomType == QgsWkbTypes.PolygonGeometry:
            resultPolygon.append(QgsGeometry(g))

         del geoms[i]

   return resultPoint, resultLine, resultPolygon


# ===============================================================================
# getEntSelCursor
# ===============================================================================
def getEntSelCursor():
   """Returns the image of the cursor for selecting an entity"""

   size = 1 + QadVariables.get(QadMsg.translate("Environment variables", "PICKBOX")) * 2
   # <width/cols> <height/rows> <colors> <char on pixel>
   row = str(size) + " " + str(size) + " 2 1"
   xpm = [row]
   # <Colors>
   xpm.append("  c None")
   xpm.append("+ c " + QadVariables.get(QadMsg.translate("Environment variables", "PICKBOXCOLOR")))
   # <Pixels>
   # es . "+++++",
   # es . "+   +",
   # es . "+   +",
   # es . "+   +",
   # es . "+++++",
   xpm.append("+" * size)
   if size > 1:
      row = "+" + " " * (size - 2) + "+"
      for i in range(size - 2): # da 0
         xpm.append(row)
      xpm.append("+" * size)

   return QCursor(QPixmap(xpm))


def getGetPointCursor():
   """Returns the image of the cursor for selecting a point"""
   pickBox = QadVariables.get(QadMsg.translate("Environment variables", "CURSORSIZE"))
   size = 1 + pickBox * 2
   # <width/cols> <height/rows> <colors> <char on pixel>
   row = str(size) + " " + str(size) + " 2 1"
   xpm = [row]
   # <Colors>
   xpm.append("  c None")
   xpm.append("+ c " + QadVariables.get(QadMsg.translate("Environment variables", "PICKBOXCOLOR")))
   # <Pixels>
   # es . "  +  ",
   # es . "  +  ",
   # es . "+++++",
   # es . "  +  ",
   # es . "  +  ",
   row = (" " * pickBox) + "+" + (" " * pickBox)
   xpm.append(row)
   if size > 1:
      for i in range(pickBox - 1): # da 0
         xpm.append(row)
      xpm.append("+" * (size))
      for i in range(pickBox - 1): # da 0
         xpm.append(row)

   return QCursor(QPixmap(xpm))


# ===============================================================================
# getFeatureRequest
# ===============================================================================
def getFeatureRequest(fetchAttributes = [], fetchGeometry = True, \
                      rect = None, useIntersect = False):
   # FOR NOW <fetchGeometry> IS NOT USED BECAUSE I DON'T KNOW HOW TO CAST in QgsFeatureRequest.Flags
   # returns a QgsFeatureRequest object to query a layer
   # It can get 4 arguments, all of them are optional:
   # fetchAttributes: List of attributes which should be fetched.
   #                  None = disable fetching attributes, Empty list means that all attributes are used.
   #                  default: empty list
   # fetchGeometry: Whether geometry of the feature should be fetched. Default: True
   # rect: Spatial filter by rectangle.
   #       None = no spatial search, empty rect means (QgsRectangle()), all features are fetched.
   #       Default: none
   # useIntersect: When using spatial filter, this argument says whether accurate test for intersection
   # should be done or whether test on bounding box suffices.
   # This is needed e.g. for feature identification or selection. Default: False

   request = QgsFeatureRequest()

   #flag = QgsFeatureRequest.NoFlags

#    if fetchGeometry == False:
#       flag = flag | QgsFeatureRequest.NoGeometry

   if rect is not None:
      r = QgsRectangle(rect)

        # no longer needed
#       # If the rectangle is squashed vertically or horizontally
#       # it turns out to be a line and the function makes a mess, so in this case I widen it a little
#       if doubleNear(r.xMinimum(), r.xMaximum(), 1.e-6):
#          r.setXMaximum(r.xMaximum() + 1.e-6)
#          r.setXMinimum(r.xMinimum() - 1.e-6)
#       if doubleNear(r.yMinimum(), r.yMaximum(), 1.e-6):
#          r.setYMaximum(r.yMaximum() + 1.e-6)
#          r.setYMinimum(r.yMinimum() - 1.e-6)

      request.setFilterRect(r)

      if useIntersect == True:
         request.setFlags(QgsFeatureRequest.ExactIntersect)

   if fetchAttributes is None:
      request.setSubsetOfAttributes([])
   else:
      if len(fetchAttributes) > 0:
         request.setSubsetOfAttributes(fetchAttributes)

   return request


# ===============================================================================
# getVisibleVectorLayers
# ===============================================================================
def getVisibleVectorLayers(canvas):
   # All vector layers visible
   layers = canvas.layers()
   for i in range(len(layers) - 1, -1, -1):
      # if the layer is not vector or not visible at this scale
      if layers[i].type() != QgsMapLayer.VectorLayer or \
         layers[i].hasScaleBasedVisibility() and \
         (canvas.mapSettings().scale() > layers[i].minimumScale() or canvas.mapSettings().scale() < layers[i].maximumScale()):
         del layers[i]
   return layers


# ===============================================================================
# getSnappableVectorLayers
# ===============================================================================
def getSnappableVectorLayers(canvas):
   # make QAD honor QGIS's snap settings (ALL LAYERS, ACTIVE LAYER, ADVANCED).
   # proposed by Oliver Dalang
   enabled = canvas.snappingUtils().config().enabled()
   mode = canvas.snappingUtils().config().mode()

   if enabled and mode == QgsSnappingConfig.ActiveLayer:
      if qgis.utils.iface.activeLayer() is None:
         layers = []
      else:
         layers = [qgis.utils.iface.activeLayer()]
   elif enabled and mode == QgsSnappingConfig.AdvancedConfiguration:
      layers = list(cfg.layer for cfg in canvas.snappingUtils().layers())
   else: # mode == QgsSnappingConfig.AllLayers:
      layers = canvas.layers()

   # Only vector layers visible
   for i in range(len(layers) - 1, -1, -1):
      # if the layer is not vector or not visible at this scale
      if layers[i].type() != QgsMapLayer.VectorLayer or \
         layers[i].hasScaleBasedVisibility() and \
         (canvas.mapSettings().scale() > layers[i].minimumScale() or canvas.mapSettings().scale() < layers[i].maximumScale()):
         del layers[i]
   return layers


# ===============================================================================
# getEntSel
# ===============================================================================
def getEntSel(point, mQgsMapTool, boxSize, \
              layersToCheck = None, checkPointLayer = True, checkLineLayer = True, checkPolygonLayer = True,
              onlyBoundary = True, onlyEditableLayers = False, \
              firstLayerToCheck = None, layerCacheGeomsDict = None, returnFeatureCached = False):
   """given a point (in screen coordinates) and a QgsMapTool,
      the function searces for the first entity inside the square
      of size <boxSize> (in pixels) centered on the point <point>
      layersToCheck = optional, list of layers to searc
      checkPointLayer = optional, consider point layers
      checkLineLayer = optional, consider line layers
      checkPolygonLayer = optional, consider polygon-type layers
      onlyBoundary = is used to consider only the edge of the polygons or even their interior
      onlyEditableLayers = to searc only editable layers
      firstLayerToCheck = to optimize the searc, first layer to check
      layerCacheGeomsDict = to optimize the searc, it is a cache of the layer geometries
      returnFeatureCached = to optimize, returns the feature read from the cache (when only the geometry is interested)

      Returns a list consisting of a QgsFeature and its layer and selection point
      if successful otherwise None
   """

   if checkPointLayer == False and checkLineLayer == False and checkPolygonLayer == False:
      return None

   #QApplication.setOverrideCursor(Qt.WaitCursor)

   if layersToCheck is None:
      # All vector layers visible
      _layers = getVisibleVectorLayers(mQgsMapTool.canvas) # All vector layers visible
   else:
      # only the list passed as a parameter
      _layers = layersToCheck

   # if the process can be optimized with the first layer to searc
   if firstLayerToCheck is not None:
      # I only consider if visible vector layer that is filtered by type
      if firstLayerToCheck.type() == QgsMapLayer.VectorLayer and \
         (onlyEditableLayers == False or firstLayerToCheck.isEditable()) and \
         (firstLayerToCheck.hasScaleBasedVisibility() == False or \
          (mQgsMapTool.canvas.mapSettings().scale() <= firstLayerToCheck.minimumScale() and mQgsMapTool.canvas.mapSettings().scale() >= firstLayerToCheck.maximumScale())) and \
         ((firstLayerToCheck.geometryType() == QgsWkbTypes.PointGeometry and checkPointLayer == True) or \
          (firstLayerToCheck.geometryType() == QgsWkbTypes.LineGeometry and checkLineLayer == True) or \
          (firstLayerToCheck.geometryType() == QgsWkbTypes.PolygonGeometry and checkPolygonLayer == True)):
         # returns feature, point
         res = getEntSelOnLayer(point, mQgsMapTool, boxSize, firstLayerToCheck, onlyBoundary, layerCacheGeomsDict, returnFeatureCached)
         if res is not None:
            return res[0], firstLayerToCheck, res[1]

   for layer in _layers: # cycle on layers
      # if the process can be optimized with the first layer to look for the jump in this loop
      if (firstLayerToCheck is not None) and firstLayerToCheck.id() == layer.id():
         continue;

      # I only consider vector layers that are filtered by type
      if layer.type() == QgsMapLayer.VectorLayer and \
          (onlyEditableLayers == False or layer.isEditable()) and \
          ((layer.geometryType() == QgsWkbTypes.PointGeometry and checkPointLayer == True) or \
           (layer.geometryType() == QgsWkbTypes.LineGeometry and checkLineLayer == True) or \
           (layer.geometryType() == QgsWkbTypes.PolygonGeometry and checkPolygonLayer == True)):
         # returns feature, point
         res = getEntSelOnLayer(point, mQgsMapTool, boxSize, layer, onlyBoundary, layerCacheGeomsDict, returnFeatureCached)
         if res is not None:
            return res[0], layer, res[1]

   #QApplication.restoreOverrideCursor()
   return None


# ===============================================================================
# getEntSelOnLayer
# ===============================================================================
def getEntSelOnLayer(point, mQgsMapTool, boxSize, layer, onlyBoundary = True, \
                     layerCacheGeomsDict = None, returnFeatureCached = False):
   """given a point (in screen coordinates) and a QgsMapTool,
      the function searces for the first entity of the layer inside the square
      of size <boxSize> (in pixels) centered on the point <point>
      onlyBoundary = is used to consider only the edge of the polygons or even their interior
      layerCacheGeomsDict = to optimize the searc, it is a cache of the layer geometries

      Returns a list consisting of a QgsFeature and the selection point
      if successful otherwise None
   """
   layerCoords = mQgsMapTool.toLayerCoordinates(layer, point)
   ToleranceInMapUnits = QgsTolerance.toleranceInMapUnits(boxSize, layer, \
                                                          mQgsMapTool.canvas.mapSettings(), \
                                                          QgsTolerance.Pixels) / 2

   selectRect = QgsRectangle(layerCoords.x() - ToleranceInMapUnits, layerCoords.y() - ToleranceInMapUnits, \
                             layerCoords.x() + ToleranceInMapUnits, layerCoords.y() + ToleranceInMapUnits)

   # whether the process can be optimized with cache
   if layerCacheGeomsDict is not None:
      cachedFeatures = layerCacheGeomsDict.getFeatures(layer, selectRect)

      featureRequest = QgsFeatureRequest()
      featureRequest.setSubsetOfAttributes([])

      for cachedFeature in cachedFeatures:
         # if it is a layer containing polygons then check whether to consider only the edges
         if onlyBoundary == False or layer.geometryType() != QgsWkbTypes.PolygonGeometry:
            if cachedFeature.geometry().intersects(selectRect):
               if returnFeatureCached: # returns the cache feature
                  return cachedFeature, point
               # I get the layer feature
               featureRequest.setFilterFid(cachedFeature.attribute("index"))
               featureIterator = layer.getFeatures(featureRequest)
               for feature in featureIterator:
                  return feature, point
         else:
            # I only consider the edges of the geometries and not the internal space of the polygons
            # I reduce geometries to points or polylines
            geoms = asPointOrPolyline(cachedFeature.geometry())
            for g in geoms:
               #start = time.time() # test
               #for i in range(1, 10):
               if g.intersects(selectRect):
                  if returnFeatureCached: # returns the cache feature
                     return cachedFeature, point

                  # I get the layer feature
                  featureRequest.setFilterFid(cachedFeature.attribute("index"))
                  featureIterator = layer.getFeatures(featureRequest)
                  for feature in featureIterator:
                     return feature, point
               #tempo = ((time.time() - start) * 1000) # test
               #tempo += 0 # test
   else:
      featureIterator = layer.getFeatures(getFeatureRequest([], True, selectRect, True))
      feature = QgsFeature()

      # if it is a layer containing polygons then check whether to consider only the edges
      if onlyBoundary == False or layer.geometryType() != QgsWkbTypes.PolygonGeometry:
         for feature in featureIterator:
            return feature, point
      else:
         # I only consider the edges of the geometries and not the internal space of the polygons
         for feature in featureIterator:
            # I reduce geometries to points or polylines
            geoms = asPointOrPolyline(feature.geometry())
            for g in geoms:
               if g.intersects(selectRect):
                  return feature, point

   return None


# ===============================================================================
# getFeatureById
# ===============================================================================
def getFeatureById(layer, id):
   """Get a feature from its id."""
   feature = QgsFeature()
   if layer.getFeatures(QgsFeatureRequest().setFilterFid(id)).nextFeature(feature):
      return feature
   else:
      return None


# ===============================================================================
# isGeomInBox
# ===============================================================================
def isGeomInBox(point, mQgsMapTool, geom, boxSize, crs = None, \
                checkPointLayer = True, checkLineLayer = True, checkPolygonLayer = True,
                onlyBoundary = True):
   """given a point (in screen coordinates) and a QgsMapTool,
      the function checks whether the geometry is inside the square
      of boxSize dimensions (in pixels) centered on the point
      geom = geometry to verify
      crs = geometry coordinate system (if = NOT means in map coordinates)
      checkPointLayer = optional, consider point geometry
      checkLineLayer = optional, consider line-type geometry
      checkPolygonLayer = optional, considers polygon-type geometry
      onlyBoundary = is used to consider only the edge of the polygons or even their interior
      Returns True if the geometry is in the square of size boxSize in (pixel) otherwise False
   """
   if geom is None:
      return False
   if checkPointLayer == False and checkLineLayer == False and checkPolygonLayer == False:
      return False

   # I only consider geometry filtered by type
   if ((geom.type() == QgsWkbTypes.PointGeometry and checkPointLayer == True) or \
       (geom.type() == QgsWkbTypes.LineGeometry and checkLineLayer == True) or \
       (geom.type() == QgsWkbTypes.PolygonGeometry and checkPolygonLayer == True)):
      mapPoint = mQgsMapTool.toMapCoordinates(point)
      mapGeom = QgsGeometry(geom)
      if crs is not None and mQgsMapTool.canvas.mapSettings().destinationCrs() != crs:
         # transform the geometry coordinates into map coordinates
         coordTransform = QgsCoordinateTransform(crs, mQgsMapTool.canvas.mapSettings().destinationCrs(), QgsProject.instance())
         mapGeom.transform(coordTransform)

      ToleranceInMapUnits = boxSize * mQgsMapTool.canvas.mapSettings().mapUnitsPerPixel()
      selectRect = QgsRectangle(mapPoint.x() - ToleranceInMapUnits, mapPoint.y() - ToleranceInMapUnits, \
                                mapPoint.x() + ToleranceInMapUnits, mapPoint.y() + ToleranceInMapUnits)

      # if it is a polygon geometry then check whether to consider only the edges
      if onlyBoundary == False or geom.type() != QgsWkbTypes.PolygonGeometry:
         if mapGeom.intersects(selectRect):
            return True
      else:
         # I only consider the edges of the geometry and not the internal space of the polygon
         # I reduce the geometry to points or polylines
         geoms = asPointOrPolyline(mapGeom)
         for g in geoms:
            if g.intersects(selectRect):
               return True

   return False


# ===============================================================================
# getGeomInBox
# ===============================================================================
def getGeomInBox(point, mQgsMapTool, geoms, boxSize, crs = None, \
                 checkPointLayer = True, checkLineLayer = True, checkPolygonLayer = True,
                 onlyBoundary = True):
   """given a point (in screen coordinates) and a QgsMapTool,
      the function searces for the first geometry inside the square
      of boxSize dimensions (in pixels) centered on the point
      geoms = list of geometries to verify
      crs = geometry coordinate system (if = NOT means in map coordinates)
      checkPointLayer = optional, consider point geometry
      checkLineLayer = optional, consider line-type geometry
      checkPolygonLayer = optional, considers polygon-type geometry
      onlyBoundary = is used to consider only the edge of the polygons or even their interior
      Returns the geometry that is in the square of size boxSize otherwise None
   """
   if geoms is None:
      return False
   for geom in geoms:
      if isGeomInBox(point, mQgsMapTool, geom, boxSize, crs, checkPointLayer, checkLineLayer, checkPolygonLayer, onlyBoundary):
         return geom
   return None


# ===============================================================================
# getActualSingleSelection
# ===============================================================================
def getActualSingleSelection(layers):
   """the function searces if there is only one selected entity between the layers
      Returns a QgsFeature and its layer on success otherwise None
   """
   selFeature = []

   for layer in layers: # cycle on layers
      if (layer.type() == QgsMapLayer.VectorLayer):
         selectedFeatureCount = layer.selectedFeaturCount()
         if selectedFeatureCount == 1:
            selFeature = layer.selectedFeatures()
            selLayer = Layer
         elif selectedFeatureCount > 1:
            del selFeature[:] # I empty the list
            break

   if len(selFeature) == 1: # if there was only one entity selected
      return selFeature[0], selLayer

   return None


def deselectAll(layers):
   """the function deselects all selected entities in the layers"""
   for layer in layers: # cycle on layers
      if (layer.type() == QgsMapLayer.VectorLayer):
         layer.removeSelection()


# ===============================================================================
# appendUniquePointToList
# ===============================================================================
def appendUniquePointToList(pointList, point):
   """Adds a point to the list checking that it is not already present.
      Returns True if the insertion occurred, False if the point was already there.
   """
   for iPoint in pointList:
      if ptNear(iPoint, point):
         return False

   pointList.append(point)
   return True


# ===============================================================================
# getPerpendicularPointOnInfinityLine
# ===============================================================================
def getPerpendicularPointOnInfinityLine(p1, p2, pt):
   """the function returns the perpendicular projection point of pt
      to the line passing through p1-p2.
   """

   diffX = p2.x() - p1.x()
   diffY = p2.y() - p1.y()

   if doubleNear(diffX, 0): # if the straight line passing through p1 and p2 is vertical
      return QgsPointXY(p1.x(), pt.y())
   elif doubleNear(diffY, 0): # if the straight line passing through p1 and p2 is horizontal
      return QgsPointXY(pt.x(), p1.y())
   else:
      coeff = diffY / diffX
      x = (coeff * p1.x() - p1.y() + pt.x() / coeff + pt.y()) / (coeff + 1 / coeff)
      y = coeff * (x - p1.x()) + p1.y()

      return QgsPointXY(x, y)


# ===============================================================================
# getInfinityLinePerpOnMiddle
# ===============================================================================
def getInfinityLinePerpOnMiddle(pt1, pt2):
   """given a segment pt1-pt2, the function finds a line perpendicular to the segment
      which passes through its midpoint. The function returns 2 points of the line.
   """
   ptMiddle = getMiddlePoint(pt1, pt2)
   dist = getDistance(pt1, ptMiddle)
   if dist == 0:
      return None
   angle = getAngleBy2Pts(pt1, pt2) + math.pi / 2
   pt2Middle = getPolarPointByPtAngle(ptMiddle, angle, dist)
   return ptMiddle, pt2Middle


# ===============================================================================
# getMiddleAngle
# ===============================================================================
def getMiddleAngle(angle1, angle2):
   """given 2 angles, the function returns the average angle."""
   a1 = normalizeAngle(angle1)
   a2 = normalizeAngle(angle2)
   if a2 < a1: a2 = (math.pi * 2) + a2
   return normalizeAngle((a2 + a1) / 2)


# ===============================================================================
# getBisectorInfinityLine
# ===============================================================================
def getBisectorInfinityLine(pt1, pt2, pt3, acuteMode = True):
   """given an angle defined by 3 points whose second point is the vertex of the angle,
      the function returns the line bisector of the angle through 2 points
      of the line (the vertex of the angle and another calculated point how far away
      the distance of pt1 from pt2).
      acuteMode = True considers the acute angle, acuteMode = False the obtuse angle
   """
   angle1 = getAngleBy2Pts(pt2, pt1)
   angle2 = getAngleBy2Pts(pt2, pt3)
   angle = (angle1 + angle2) / 2 # average angle
#   return pt2, getPolarPointByPtAngle(pt2, angle, 10)

   dist = getDistance(pt1, pt2)
   ptProj = getPolarPointByPtAngle(pt2, angle, dist)
   ptInverseProj = getPolarPointByPtAngle(pt2, angle - math.pi, dist)
   if getDistance(pt1, ptProj) < getDistance(pt1, ptInverseProj):
      if acuteMode == True:
         return pt2, ptProj
      else:
         return pt2, ptInverseProj
   else:
      if acuteMode == True:
         return pt2, ptInverseProj
      else:
         return pt2, ptProj


# ===============================================================================
# getXOnInfinityLine
# ===============================================================================
def getXOnInfinityLine(p1, p2, y):
   """given the Y coordinate of a point the function returns the X coordinate of the same
      on the line passing through p1-p2
   """

   diffX = p2.x() - p1.x()
   diffY = p2.y() - p1.y()

   if doubleNear(diffX, 0): # if the straight line passing through p1 and p2 is vertical
      return p1.x()
   elif doubleNear(diffY, 0): # if the straight line passing through p1 and p2 is horizontal
      return None # infinite points
   else:
      coeff = diffY / diffX
      return p1.x() + (y - p1.y()) / coeff


# ===============================================================================
# getYOnInfinityLine
# ===============================================================================
def getYOnInfinityLine(p1, p2, x):
   """given the Y coordinate of a point the function returns the X coordinate of the same
      on the line passing through p1-p2
   """

   diffX = p2.x() - p1.x()
   diffY = p2.y() - p1.y()

   if doubleNear(diffX, 0): # if the straight line passing through p1 and p2 is vertical
      return None # infinite points
   elif doubleNear(diffY, 0): # if the straight line passing through p1 and p2 is horizontal
      return p1.y()
   else:
      coeff = diffY / diffX
      return p1.y() + (x - p1.x()) * coeff


# ===============================================================================
# getSqrDistance
# ===============================================================================
def getSqrDistance(p1, p2):
   """the function returns the squared distance between 2 points (QgsPointXY)"""
   dx = p2.x() - p1.x()
   dy = p2.y() - p1.y()

   return dx * dx + dy * dy


# ===============================================================================
# getDistance
# ===============================================================================
def getDistance(p1, p2):
   """the function returns the distance between 2 points (QgsPointXY)"""
   return math.sqrt(getSqrDistance(p1, p2))


# ===============================================================================
# getMinDistancePtBetweenSegmentAndPt
# ===============================================================================
def getMinDistancePtBetweenSegmentAndPt(p1, p2, pt):
   """the function returns the minimum distance point and the minimum distance between a segment and a point
      (<minimum distance point><minimum distance>)
   """
   if isPtOnSegment(p1, p2, pt) == True:
      return [pt, 0]
   perpPt = getPerpendicularPointOnInfinityLine(p1, p2, pt)
   if perpPt is not None:
      if isPtOnSegment(p1, p2, perpPt) == True:
         return [perpPt, getDistance(perpPt, pt)]

   distFromP1 = getDistance(p1, pt)
   distFromP2 = getDistance(p2, pt)
   if distFromP1 < distFromP2:
      return [p1, distFromP1]
   else:
      return [p2, distFromP2]


# ===============================================================================
# getMiddlePoint
# ===============================================================================
def getMiddlePoint(p1, p2):
   """the function returns the midpoint between 2 points (QgsPointXY)"""
   x = (p1.x() + p2.x()) / 2
   y = (p1.y() + p2.y()) / 2

   return QgsPointXY(x, y)


# ===============================================================================
# getAngleBy2Pts
# ===============================================================================
def getAngleBy2Pts(p1, p2, tolerance = None):
   """the function returns the angle in radians of the straight line passing through p1 and p2"""
   diffX = p2.x() - p1.x()
   diffY = p2.y() - p1.y()
   if doubleNear(diffX, 0, tolerance): # if the straight line passing through p1 and p2 is vertical
      if p1.y() < p2.y():
         angle = math.pi / 2
      else :
         angle = math.pi * 3 / 2
   elif doubleNear(diffY, 0, tolerance): # if the straight line passing through p1 and p2 is horizontal
      if p1.x() <= p2.x():
         angle = 0.0
      else:
         angle = math.pi
   else:
      angle = math.atan(diffY / diffX)
      if diffX < 0:
         angle = math.pi + angle
      else:
         if diffY < 0:
            angle = 2 * math.pi + angle

   return angle


# ===============================================================================
# getAngleBy3Pts
# ===============================================================================
def getAngleBy3Pts(p1, vertex, p2, clockWise):
   """the function returns the angle in radians of the angle starting from <p1>
      to get to <p2> with vertex <vertex> in the <clockWise> direction (clockwise or counterclockwise)
   """
   angle1 = getAngleBy2Pts(p1, vertex)
   angle2 = getAngleBy2Pts(p2, vertex)
   if clockWise: # senso orario
      if angle2 > angle1:
         return (2 * math.pi) - (angle2 - angle1)
      else:
         return angle1 - angle2
   else: # senso anti-orario
      if angle2 < angle1:
         return (2 * math.pi) - (angle1 - angle2)
      else:
         return angle2 - angle1


# ===============================================================================
# isAngleBetweenAngles
# ===============================================================================
def isAngleBetweenAngles(startAngle, endAngle, angle):
   """the function returns True if the angle is within the starting and ending angles
      extremes included
   """
   _angle = angle % (math.pi * 2) # modulo

   if startAngle < endAngle:
      if (_angle > startAngle or doubleNear(_angle, startAngle)) and \
         (_angle < endAngle or doubleNear(_angle, endAngle)):
         return True
   else:
      if (_angle > 0 or doubleNear(_angle, 0)) and \
         (_angle < endAngle or doubleNear(_angle, endAngle)):
         return True

      if (_angle < (math.pi * 2) or doubleNear(_angle, (math.pi * 2))) and \
         (_angle > startAngle or doubleNear(_angle, startAngle)):
         return True

   return False


def getPolarPointBy2Pts(p1, p2, dist):
   """the function returns the point on the line passing through p1 and p2 which
      distance from p1 to p2 <dist>.
   """
   angle = getAngleBy2Pts(p1, p2)

   return getPolarPointByPtAngle(p1, angle, dist)


# ===============================================================================
# isPtOnSegment
# ===============================================================================
def isPtOnSegment(p1, p2, point):
   """the function returns true if the point is on the segment (extremes included).
      p1, p2 and point are QgsPointXY.
   """
   if p1.x() < p2.x():
      xMin = p1.x()
      xMax = p2.x()
   else:
      xMax = p1.x()
      xMin = p2.x()

   # check if the point can be on the 07/22/2017 segment
   if doubleSmaller(point.x(), xMin) or doubleGreater(point.x(), xMax): return False

   if p1.y() < p2.y():
      yMin = p1.y()
      yMax = p2.y()
   else:
      yMax = p1.y()
      yMin = p2.y()

   # check if the point can be on the 07/22/2017 segment
   if doubleSmaller(point.y(), yMin) or doubleGreater(point.y(), yMax): return False

   y = getYOnInfinityLine(p1, p2, point.x())
   if y is None: # the p1-p2 segment is vertical
      return True
   else:
      # if the point is on the infinite line that passes from p1-p2
      if doubleNear(point.y(), y):
         return True

   return False


# ===============================================================================
# getIntersectionPointOn2InfinityLines
# ===============================================================================
def getIntersectionPointOn2InfinityLines(line1P1, line1P2, line2P1, line2P2):
   """the function returns the point of intersection between the line passing through line1P1-line1P2 and
      the line passing through line2P1-line2P2.
   """
   line1DiffX = line1P2.x() - line1P1.x()
   line1DiffY = line1P2.y() - line1P1.y()

   line2DiffX = line2P2.x() - line2P1.x()
   line2DiffY = line2P2.y() - line2P1.y()

   if doubleNear(line1DiffX, 0) and doubleNear(line2DiffX, 0): # if line1 and line2 are vertical
      return None # sono parallele
   elif doubleNear(line1DiffY, 0) and doubleNear(line2DiffY, 0): # if line1 and line2 are horizontal
      return None # sono parallele

   if doubleNear(line1DiffX, 0): # if line 1 is vertical
      return QgsPointXY(line1P2.x(), getYOnInfinityLine(line2P1, line2P2, line1P2.x()))
   if doubleNear(line1DiffY, 0): # if line 1 is horizontal
      return QgsPointXY(getXOnInfinityLine(line2P1, line2P2, line1P2.y()), line1P2.y())
   if doubleNear(line2DiffX, 0): # if line2 is vertical
      return QgsPointXY(line2P2.x(), getYOnInfinityLine(line1P1, line1P2, line2P2.x()))
   if doubleNear(line2DiffY, 0): # if line2 is horizontal
      return QgsPointXY(getXOnInfinityLine(line1P1, line1P2, line2P2.y()), line2P2.y())

   line1Coeff = line1DiffY / line1DiffX
   line2Coeff = line2DiffY / line2DiffX

   if line1Coeff == line2Coeff: # sono parallele
      return None

   D = line1Coeff - line2Coeff
   # if D is so close to zero
   if doubleNear(D, 0.0):
      return None
   x = line1P1.x() * line1Coeff - line1P1.y() - line2P1.x() * line2Coeff + line2P1.y()
   x = x / D
   y = (x - line1P1.x()) * line1Coeff + line1P1.y()

   return QgsPointXY(x, y)


# ===============================================================================
# getNearestPoints
# ===============================================================================
def getNearestPoints(point, points, tolerance = 0):
   """Returns a list of points closest to point."""
   result = []
   minDist = sys.float_info.max

   if tolerance == 0: # only the closest point
      for pt in points:
         dist = getDistance(point, pt)
         if dist < minDist:
            minDist = dist
            nearestPoint = pt

      if minDist != sys.float_info.max: # trovato
         result.append(nearestPoint)
   else:
      nearest = getNearestPoints(point, points) # closest point
      nearestPoint = nearest[0]

      for pt in points:
         dist = getDistance(nearestPoint, pt)
         if dist <= tolerance:
            result.append(pt)

   return result


# ===============================================================================
# getPolarPointByPtAngle
# ===============================================================================
def getPolarPointByPtAngle(p1, angle, dist):
   """the function returns the point on the line passing through p1 with angle <angle> that
      is distant from p1 <dist>.
   """
   y = dist * math.sin(angle)
   x = dist * math.cos(angle)
   return QgsPointXY(p1.x() + x, p1.y() + y)


# ===============================================================================
# asPointOrPolyline
# ===============================================================================
def asPointOrPolyline(geom):
   """the function returns a list of point and/or polyline geometries into which the geometry is transformed."""
   # I transform the geometries into points or polylines
   result = []
   for g in geom.asGeometryCollection():
      gType = g.type()
      if g.isMultipart() == False:
         if gType == QgsWkbTypes.PointGeometry or gType == QgsWkbTypes.LineGeometry:
            result.append(g)

         elif gType == QgsWkbTypes.PolygonGeometry:
            lineList = g.asPolygon() # vettore di linee
            for line in lineList:
               _g = QgsGeometry.fromPolylineXY(line)
               result.append(_g)

      else: # multi
         if gType == QgsWkbTypes.PointGeometry:
            pointList = g.asMultiPoint() # vector of points
            for point in pointList:
               _g = QgsGeometry.fromPointXY(point)
               result.append(_g)

         elif gType == QgsWkbTypes.LineGeometry:
            lineList = g.asMultiPolyline() # vettore di linee
            for line in lineList:
               _g = QgsGeometry.fromPolylineXY(line)
               result.append(_g)

         elif gType == QgsWkbTypes.PolygonGeometry:
            polygonList = g.asMultiPolygon() # vettore di poligoni
            for polygon in polygonList:
               for line in polygon:
                  _g = QgsGeometry.fromPolylineXY(line)
                  result.append(_g)

   return result


# ===============================================================================
# leftOfLineCoords
# ===============================================================================
# usare qad_line
def leftOfLineCoords(x, y, x1, y1, x2, y2):
   """the function returns a number < 0 if the point x,y is to the left of the line x1,y1 -> x2,y2"""
   f1 = x - x1
   f2 = y2 - y1
   f3 = y - y1
   f4 = x2 - x1
   return f1*f2 - f3*f4

# usare qad_line
def leftOfLine(pt, pt1, pt2):
   return leftOfLineCoords(pt.x(), pt.y(), pt1.x(), pt1.y(), pt2.x(), pt2.y())


# ===============================================================================
# get a and b for line equation (y = ax + b)
# ===============================================================================
# usare qad_line
def get_A_B_LineEquation(x1, y1, x2, y2):
   # given 2 points, a and b of the equation of the straight line passing through the two points are calculated (y = ax + b)
   a = (y2 - y1) / (x2 - x1)
   # y = ax + b -> b = y - ax
   b = y1 - (a * x1)

   return a, b


# ===============================================================================
# radice cubica
# ===============================================================================
def cbrt(x):
   # https://stackoverflow.com/questions/28014241/how-to-find-cube-root-using-python
   if x>0:
      return x**(1.0 / 3.0)
   else:
      return -((-x)**(1.0 / 3.0))


# ===============================================================================
# ptNear
# ===============================================================================
def ptNear(pt1, pt2, tolerance = None):
   """the function compares 2 points (but allows a tolerance)"""
   if tolerance is None:
      myTolerance = QadVariables.get(QadMsg.translate("Environment variables", "TOLERANCE2COINCIDENT"))
   else:
      myTolerance = tolerance

   return getDistance(pt1, pt2) <= myTolerance


# ===============================================================================
# doubleNear
# ===============================================================================
def doubleNear(a, b, tolerance = None):
   """the function compares 2 floats (but allows a tolerance)"""
   if tolerance is None:
      myTolerance = QadVariables.get(QadMsg.translate("Environment variables", "TOLERANCE2COINCIDENT"))
   else:
      myTolerance = tolerance

   diff = a - b
   return diff >= -myTolerance and diff <= myTolerance


# ===============================================================================
# doubleGreater
# ===============================================================================
def doubleGreater(a, b, tolerance = None):
   """the function compares 2 floats (but allows a tolerance)"""
   if tolerance is None:
      myTolerance = QadVariables.get(QadMsg.translate("Environment variables", "TOLERANCE2COINCIDENT"))
   else:
      myTolerance = tolerance

   return a > b and not doubleNear(a, b, myTolerance)


# ===============================================================================
# doubleGreaterOrEquals
# ===============================================================================
def doubleGreaterOrEquals(a, b, tolerance = None):
   """the function compares 2 floats (but allows a tolerance)"""
   if tolerance is None:
      myTolerance = QadVariables.get(QadMsg.translate("Environment variables", "TOLERANCE2COINCIDENT"))
   else:
      myTolerance = tolerance

   return a > b or doubleNear(a, b, myTolerance)


# ===============================================================================
# doubleSmaller
# ===============================================================================
def doubleSmaller(a, b, tolerance = None):
   """the function compares 2 floats (but allows a tolerance)"""
   if tolerance is None:
      myTolerance = QadVariables.get(QadMsg.translate("Environment variables", "TOLERANCE2COINCIDENT"))
   else:
      myTolerance = tolerance

   return a < b and not doubleNear(a, b, myTolerance)


# ===============================================================================
# doubleSmallerOrEquals
# ===============================================================================
def doubleSmallerOrEquals(a, b, tolerance = None):
   """the function compares 2 floats (but allows a tolerance)"""
   if tolerance is None:
      myTolerance = QadVariables.get(QadMsg.translate("Environment variables", "TOLERANCE2COINCIDENT"))
   else:
      myTolerance = tolerance

   return a < b or doubleNear(a, b, myTolerance)


# ===============================================================================
# TanDirectionNear
# ===============================================================================
def TanDirectionNear(a, b, tolerance = None):
   """the function compares 2 tangent directions (but allows a tolerance)"""
   if tolerance is None:
      myTolerance = QadVariables.get(QadMsg.translate("Environment variables", "TOLERANCE2COINCIDENT"))
   else:
      myTolerance = tolerance

   a1 = normalizeAngle(a)
   b1 = normalizeAngle(b)
   if a1 > b1:
      diff1 = a1 - b1
      diff2 = (2 * math.pi + b1) - a1
   else:
      diff1 = b1 - a1
      diff2 = (2 * math.pi + a1) - b1

   return diff1 <= myTolerance or diff2 <= myTolerance


# ===============================================================================
# numericListAvg
# ===============================================================================
def numericListAvg(dblList):
   """the function calculates the average of a list of numbers"""
   if (dblList is None) or len(dblList) == 0:
      return None
   sum = 0
   for num in dblList:
      sum = sum + num

   return sum / len(dblList)


# ===============================================================================
# sqrDistToSegment
# ===============================================================================
# usare qad_line fino qui
def sqrDistToSegment(point, x1, y1, x2, y2, epsilon):
   """the function returns a list with
      (<minimum distance squared>
       <nearest point>)
   """
   minDistPoint = QgsPointXY()

   if x1 == x2 and y1 == y2:
      minDistPoint.setX(x1)
      minDistPoint.setY(y1)
   else:
      nx = y2 - y1
      ny = -( x2 - x1 )

      t = (point.x() * ny - point.y() * nx - x1 * ny + y1 * nx ) / (( x2 - x1 ) * ny - ( y2 - y1 ) * nx )

      if t < 0.0:
         minDistPoint.setX(x1)
         minDistPoint.setY(y1)
      elif t > 1.0:
         minDistPoint.setX(x2)
         minDistPoint.setY(y2)
      else:
         minDistPoint.setX( x1 + t *( x2 - x1 ) )
         minDistPoint.setY( y1 + t *( y2 - y1 ) )

   dist = point.sqrDist(minDistPoint)
   # prevent rounding errors if the point is directly on the segment
   if doubleNear( dist, 0.0, epsilon ):
      minDistPoint.setX( point.x() )
      minDistPoint.setY( point.y() )
      return (0.0, minDistPoint)

   return (dist, minDistPoint)


# ===============================================================================
# closestSegmentWithContext
# ===============================================================================
def closestSegmentWithContext(point, geom, epsilon = 1.e-15):
   """the function returns a list with
      (<minimum distance squared>
       <nearest point>
       <next vertex index of the closest segment (if the geometry is a line or polygon)>
       <"to the left of" if the point is to the left of the segment (< 0 -> left, > 0 -> right)
   """
   minDistPoint = QgsPointXY()
   closestSegmentIndex = 0
   sqrDist = sys.float_info.max

   gType = geom.type()
   if geom.isMultipart() == False:
      if gType == QgsWkbTypes.PointGeometry:
         minDistPoint = geom.asPoint()
         point.sqrDist(minDistPoint)
         return (point.sqrDist(minDistPoint), minDistPoint, None, None)

      elif gType == QgsWkbTypes.LineGeometry:
         points = geom.asPolyline() # vector of points
         index = 0
         for pt in points:
            if index > 0:
               prevX = thisX
               prevY = thisY

            thisX = pt.x()
            thisY = pt.y()

            if index > 0:
               result = sqrDistToSegment(point, prevX, prevY, thisX, thisY, epsilon)
               testdist = result[0]
               distPoint = result[1]

               if testdist < sqrDist:
                  closestSegmentIndex = index
                  sqrDist = testdist
                  minDistPoint = distPoint

            index = index + 1

         leftOf = leftOfLine(point, geom.vertexAt(closestSegmentIndex - 1), geom.vertexAt(closestSegmentIndex))
         return (sqrDist, minDistPoint, closestSegmentIndex, leftOf)

      elif gType == QgsWkbTypes.PolygonGeometry:
         lines = geom.asPolygon() # list of lines
         index = 0
         for line in lines:
            prevX = 0
            prevY = 0

            for pt in line: # list of points
               thisX = pt.x()
               thisY = pt.y()

               if prevX and prevY:
                  result = sqrDistToSegment(point, prevX, prevY, thisX, thisY, epsilon)
                  testdist = result[0]
                  distPoint = result[1]

                  if testdist < sqrDist:
                     closestSegmentIndex = index
                     sqrDist = testdist
                     minDistPoint = distPoint

               prevX = thisX
               prevY = thisY
               index = index + 1

         leftOf = leftOfLine(point, geom.vertexAt(closestSegmentIndex - 1), geom.vertexAt(closestSegmentIndex))
         return (sqrDist, minDistPoint, closestSegmentIndex, leftOf)

   else: # multi
      if gType == QgsWkbTypes.PointGeometry:
         minDistPoint = getNearestPoints(point, geom.asMultiPoint())[0] # vector of points
         return (point.sqrDist(minDistPoint), minDistPoint, None, None)

      elif gType == QgsWkbTypes.LineGeometry:
         lines = geom.asMultiPolyline() # list of lines
         pointindex = 0
         for line in lines:
            prevX = 0
            prevY = 0

            for pt in line: # list of points
               thisX = pt.x()
               thisY = pt.y()

               if prevX and prevY:
                  result = sqrDistToSegment(point, prevX, prevY, thisX, thisY, epsilon)
                  testdist = result[0]
                  distPoint = result[1]

                  if testdist < sqrDist:
                     closestSegmentIndex = pointindex
                     sqrDist = testdist
                     minDistPoint = distPoint

               prevX = thisX
               prevY = thisY
               pointindex = pointindex + 1

         leftOf = leftOfLine(point, geom.vertexAt(closestSegmentIndex - 1), geom.vertexAt(closestSegmentIndex))
         return (sqrDist, minDistPoint, closestSegmentIndex, leftOf)

      elif gType == QgsWkbTypes.PolygonGeometry:
         polygons = geom.asMultiPolygon() # vettore di poligoni
         pointindex = 0
         for polygon in polygons:
            for line in polygon: # list of lines
               prevX = 0
               prevY = 0

               for pt in line: # list of points
                  thisX = pt.x()
                  thisY = pt.y()

                  if prevX and prevY:
                     result = sqrDistToSegment(point, prevX, prevY, thisX, thisY, epsilon)
                     testdist = result[0]
                     distPoint = result[1]

                     if testdist < sqrDist:
                        closestSegmentIndex = pointindex
                        sqrDist = testdist
                        minDistPoint = distPoint

                  prevX = thisX
                  prevY = thisY
                  pointindex = pointindex + 1

         leftOf = leftOfLine(point, geom.vertexAt(closestSegmentIndex - 1), geom.vertexAt(closestSegmentIndex))
         return (sqrDist, minDistPoint, closestSegmentIndex, leftOf)

   return (-1, None, None, None)


# ===============================================================================
# rotatePoint
# ===============================================================================
def rotatePoint(point, basePt, angle):
   """the function rotates a point QgsPointXY according to a base point <basePt> and an angle <angle> in radians"""
   return getPolarPointByPtAngle(basePt, getAngleBy2Pts(basePt, point) + angle, getDistance(basePt, point))


# ===============================================================================
# scalePoint
# ===============================================================================
def scalePoint(point, basePt, scale):
   """the function scales a QgsPointXY point according to a base point <basePt> and a scale factor"""
   return getPolarPointByPtAngle(basePt, getAngleBy2Pts(basePt, point), getDistance(basePt, point) * scale)


# ===============================================================================
# movePoint
# ===============================================================================
def movePoint(point, offsetX, offsetY):
   """the function moves a QgsPointXY point according to an X and a Y offset"""
   return QgsPointXY(point.x() + offsetX, point.y() + offsetY)


# ===============================================================================
# mirrorPoint
# ===============================================================================
def mirrorPoint(point, mirrorPt, mirrorAngle):
   """the function moves a QgsPointXY point along a mirrored line passing through a
      a point <mirrorPt> and having angle <mirrorAngle>
   """
   pointAngle = getAngleBy2Pts(mirrorPt, point)
   dist = getDistance(mirrorPt, point)

   return getPolarPointByPtAngle(mirrorPt, mirrorAngle + (mirrorAngle - pointAngle), dist)


# ===============================================================================
# getSubGeomAtVertex
# ===============================================================================
def getSubGeomAtVertex(geom, atVertex):
   # returns the sub-geometry at the vertex <atVertex> and its position in the geometry (0-based)
   # the position is expressed with a list (<main object index> [<secondary object index>])
   gType = geom.type()
   if geom.isMultipart() == False:
      if gType == QgsWkbTypes.PointGeometry:
         if atVertex == 0:
            return QgsGeometry(geom), [0]

      elif gType == QgsWkbTypes.LineGeometry:
         pts = geom.asPolyline() # list of points
         if atVertex > len(pts) - 1:
            return None, None
         else:
            return QgsGeometry(geom), [0]

      elif gType == QgsWkbTypes.PolygonGeometry:
         lines = geom.asPolygon() # list of lines
         if len(lines) > 0:
            i = 0
            iRing = -1
            for line in lines:
               lineLen = len(line)
               if atVertex >= i and atVertex < i + lineLen: # the vertex number falls on this line
                  if iRing == -1: # this is the most external part
                     return QgsGeometry.fromPolylineXY(line), [0] # part <0>, ring <0>
                  else:
                     return QgsGeometry.fromPolylineXY(line), [0, iRing] # part <0>, ring <iRing>
               i = i + lineLen
               iRing = iRing + 1
         return None, None

   else: # multi
      if gType == QgsWkbTypes.PointGeometry:
         pts = geom.asMultiPoint() # list of points
         if atVertex > len(pts) - 1:
            return None, None
         else:
            return QgsGeometry.fromPointXY(pts[atVertex]), [atVertex]

      elif gType == QgsWkbTypes.LineGeometry:
         # I searc in which line the vertex <atVertex> is
         i = 0
         iLine = 0
         lines = geom.asMultiPolyline() # list of lines
         for line in lines:
            lineLen = len(line)
            if atVertex >= i and atVertex < i + lineLen:
               return QgsGeometry.fromPolylineXY(line), [iLine]
            i = i + lineLen
            iLine = iLine + 1
         return None, None

      elif gType == QgsWkbTypes.PolygonGeometry:
         i = 0
         iPolygon = 0
         polygons = geom.asMultiPolygon() # list of polygons
         for polygon in polygons:
            iRing = -1
            for line in polygon:
               lineLen = len(line)
               if atVertex >= i and atVertex < i + lineLen: # the vertex number falls on this line
                  if iRing == -1: # this is the most external part
                     return QgsGeometry.fromPolylineXY(line), [iPolygon] # part <iPolygon>
                  else:
                     return QgsGeometry.fromPolylineXY(line), [iPolygon, iRing] # part <iPolygon>, ring <iRing>

               i = i + lineLen
               iRing = iRing + 1
            iPolygon = iPolygon + 1

   return None, None


# ===============================================================================
# getSubGeomAt
# ===============================================================================
def getSubGeomAt(geom, atSubGeom):
   # returns the sub-geometry whose position
   # is expressed with a list (<index main object> [<index subobject>])
   gType = geom.type()
   if geom.isMultipart() == False:
      if gType == QgsWkbTypes.PointGeometry or gType == QgsWkbTypes.LineGeometry:
         if atSubGeom[0] == 0:
            return QgsGeometry(geom)

      elif gType == QgsWkbTypes.PolygonGeometry:
         if atSubGeom[0] == 0:
            lines = geom.asPolygon() # list of lines
            if len(atSubGeom) == 1: # this is the most external part
               return QgsGeometry.fromPolylineXY(lines[0])
            else:
               iRing = atSubGeom[1]
               if iRing + 1 < len(lines):
                  return QgsGeometry.fromPolylineXY(lines[iRing + 1])

   else: # multi
      if gType == QgsWkbTypes.PointGeometry:
         nPoint = atSubGeom[0]
         return QgsGeometry(geom.vertexAt(nPoint))

      elif gType == QgsWkbTypes.LineGeometry:
         nLine = atSubGeom[0]
         lines = geom.asMultiPolyline() # list of lines
         if nLine < len(lines):
            return QgsGeometry.fromPolylineXY(lines[nLine])

      elif gType == QgsWkbTypes.PolygonGeometry:
         nPolygon = atSubGeom[0]
         polygons = geom.asMultiPolygon() # list of polygons
         if nPolygon < len(polygons):
            lines = polygons[nPolygon]
            if len(atSubGeom) == 1: # this is the most external part
               return QgsGeometry.fromPolylineXY(lines[0])
            else:
               iRing = atSubGeom[1]
               if iRing + 1 < len(lines):
                  return QgsGeometry.fromPolylineXY(lines[iRing + 1])

   return None


# ===============================================================================
# setSubGeom
# ===============================================================================
def setSubGeom(geom, subGeom, atSubGeom):
   # returns a geometry with sub-geometry at position <atSubGeom>
   # sostituita da <subGeom>
   gType = geom.type()
   subGType = subGeom.type()
   ndx = 0

   if geom.isMultipart() == False:
      if gType == QgsWkbTypes.PointGeometry or gType == QgsWkbTypes.LineGeometry:
         if atSubGeom[0] == 0:
            if subGeom.isMultipart() == False and (subGType == QgsWkbTypes.PointGeometry or subGType == QgsWkbTypes.LineGeometry):
               return QgsGeometry(SubGeom)

      elif gType == QgsWkbTypes.PolygonGeometry:
         if subGeom.isMultipart() == False and subGType == QgsWkbTypes.LineGeometry:
            if atSubGeom[0] == 0:
               lines = geom.asPolygon() # list of lines
               if len(atSubGeom) == 1: # this is the most external part
                  del lines[0]
                  lines.insert(0, SubGeom.asPolyline())
                  # for approximation problems with LL the first point and the last point are not equal so I force it
                  lines[0][-1].set(lines[0][0].x(), lines[0][0].y())
                  return QgsGeometry.fromPolygonXY(lines)
               else:
                  iRing = atSubGeom[1]
                  if iRing + 1 < len(lines):
                     del lines[iRing + 1]
                     lines.insert(iRing + 1, SubGeom.asPolyline())
                     # for approximation problems with LL the first point and the last point are not equal so I force it
                     lines[iRing + 1][-1].set(lines[iRing + 1][0].x(), lines[iRing + 1][0].y())
                     return QgsGeometry.fromPolygonXY(lines)

   else: # multi
      if gType == QgsWkbTypes.PointGeometry:
         nPoint = atSubGeom[0]
         if subGeom.isMultipart() == False and subGType == QgsWkbTypes.PointGeometry:
            result = QgsGeometry(geom)
            pt = SubGeom.asPoint()
            if result.moveVertex(pt.x, pt.y(), nPoint) == True:
               return result

      elif gType == QgsWkbTypes.LineGeometry:
         if subGeom.isMultipart() == False and subGType == QgsWkbTypes.LineGeometry:
            nLine = atSubGeom[0]
            lines = geom.asMultiPolyline() # list of lines
            if nLine < len(lines) and nLine >= -len(lines):
               del lines[nLine]
               lines.insert(nLine, SubGeom.asPolyline())
               return QgsGeometry.fromMultiPolylineXY(lines)

      elif gType == QgsWkbTypes.PolygonGeometry:
         if subGeom.isMultipart() == False and subGType == QgsWkbTypes.LineGeometry:
            nPolygon = atSubGeom[0]
            polygons = geom.asMultiPolygon() # list of polygons
            if nPolygon < len(polygons):
               lines = polygons[nPolygon]
               if len(atSubGeom) == 1: # this is the most external part
                  del lines[0]
                  lines.insert(0, SubGeom.asPolyline())
                  # for approximation problems with LL the first point and the last point are not equal so I force it
                  lines[0][-1].set(lines[0][0].x(), lines[0][0].y())
                  return QgsGeometry.fromMultiPolygonXY(polygons)
               else:
                  iRing = atSubGeom[1]
                  if iRing + 1 < len(lines):
                     del lines[iRing + 1]
                     lines.insert(iRing + 1, SubGeom.asPolyline())
                     # for approximation problems with LL the first point and the last point are not equal so I force it
                     lines[iRing + 1][-1].set(lines[iRing + 1][0].x(), lines[iRing + 1][0].y())
                     return QgsGeometry.fromMultiPolygonXY(polygons)
         elif subGeom.isMultipart() == False and subGType == QgsWkbTypes.PolygonGeometry:
            nPolygon = atSubGeom[0]
            polygons = geom.asMultiPolygon() # list of polygons
            if nPolygon < len(polygons):
               del polygons[nPolygon]
               polygons.insert(nPolygon, SubGeom.asPolygon())
               return QgsGeometry.fromMultiPolygonXY(polygons)

   return None


# ===============================================================================
# delSubGeom
# ===============================================================================
def delSubGeom(geom, atSubGeom):
   # Delete the subgeometry at position <atSubGeom> from the geometry
   gType = geom.type()
   if geom.isMultipart() == False:
      if gType == QgsWkbTypes.PointGeometry or gType == QgsWkbTypes.LineGeometry:
         return None

      elif gType == QgsWkbTypes.PolygonGeometry:
         if atSubGeom[0] == 0:
            lines = geom.asPolygon() # list of lines
            if len(atSubGeom) == 1: # this is the most external part
               del lines[0]
               return QgsGeometry() # empty geometry because the polygon has been deleted
            else:
               iRing = atSubGeom[1]
               if iRing + 1 < len(lines):
                  del lines[iRing + 1]
                  return QgsGeometry.fromPolygonXY(lines)

   else: # multi
      if gType == QgsWkbTypes.PointGeometry:
         nPoint = atSubGeom[0]
         result = QgsGeometry(geom)
         pt = SubGeom.asPoint()
         if result.deleteVertex(nPoint) == True:
            return result

      elif gType == QgsWkbTypes.LineGeometry:
         nLine = atSubGeom[0]
         lines = geom.asMultiPolyline() # list of lines
         if nLine < len(lines) and nLine >= -len(lines):
            del lines[nLine]
            return QgsGeometry.fromMultiPolylineXY(lines)

      elif gType == QgsWkbTypes.PolygonGeometry:
         nPolygon = atSubGeom[0]
         polygons = geom.asMultiPolygon() # list of polygons
         if nPolygon < len(polygons):
            lines = polygons[nPolygon]
            if len(atSubGeom) == 1: # this is the most external part
               del polygons[nPolygon]
               return QgsGeometry.fromMultiPolygonXY(polygons)
            else:
               iRing = atSubGeom[1]
               if iRing + 1 < len(lines):
                  del lines[iRing + 1]
                  return QgsGeometry.fromMultiPolygonXY(polygons)

   return None


# ===============================================================================
# getAdjustedRubberBandVertex
# ===============================================================================
def getAdjustedRubberBandVertex(vertexBefore, vertex):
   adjustedVertex = QgsPointXY(vertex)

   # for a bug not yet understood in QGIS: if the line has only 2 vertices and
   # have the same x or y (horizontal or vertical line)
   # the line is not drawn so I move the x or y a little
   # of the second summit
   # 1.e-7 is derived from the fact that QgsPointXY's == operator has a tolerance of 1E-8
   if vertexBefore.x() == vertex.x():
      adjustedVertex.setX(vertex.x() + 1.e-7)
   if vertexBefore.y() == vertex.y():
      adjustedVertex.setY(vertex.y() + 1.e-7)

   return adjustedVertex


# ============================================================================
# QadRawConfigParser class suppporting unicode
# ============================================================================
class QadRawConfigParser(configparser.RawConfigParser):

   def __init__(self, defaults=None, dict_type=configparser._default_dict,
                 allow_no_value=False):
      configparser.RawConfigParser.__init__(self, defaults, dict_type, allow_no_value)

   def write(self, fp):
      """Fixed for Unicode output"""
      if self._defaults:
         fp.write("[%s]\n" % DEFAULTSECT)
         for (key, value) in self._defaults.items():
            fp.write("%s = %s\n" % (key, unicode(value).replace('\n', '\n\t')))
         fp.write("\n")
      for section in self._sections:
         fp.write("[%s]\n" % section)
         for (key, value) in self._sections[section].items():
            if key != "__name__":
               fp.write("%s = %s\n" % (key, unicode(value).replace('\n','\n\t')))
         fp.write("\n")


# ===============================================================================
# Timer class for profiling
# ===============================================================================
class Timer(object):
   # da usare:
   # with Timer() as t:
   #    ...
   # elasped = t.secs
   def __init__(self, verbose=False):
      self.verbose = verbose

   def __enter__(self):
      self.start = time.time()
      return self

   def __exit__(self, *args):
      self.end = time.time()
      self.secs = self.end - self.start
      self.msecs = self.secs * 1000  # millisecs
      if self.verbose:
         print ('elapsed time: %f ms' % self.msecs)
