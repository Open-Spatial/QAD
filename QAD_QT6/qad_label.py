# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 functions for labels

                              -------------------
        begin                : 2014-04-24
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
from qgis.PyQt.QtGui  import *
from qgis.core import *
from qgis.gui import *


# ===============================================================================
# get_tokenListFromLblFieldName ausilio di getTokenListFromLblFieldName
# ===============================================================================
def getToken(expr, start, endChar = None):
   """returns a word within the string expr that begins in the start position and ends with the character
      endChar. If endChar <> None then two consecutive endChars are worth one e.g. 'a''a' = a'a
   """
   token = ""
   tot = len(expr)
   i = start
   if endChar is None:
      separators = "()+-*/%^=><|, \"'"
      while i < tot:
         ch = expr[i]
         if separators.find(ch) >= 0:
            return token, i
         token = token + ch
         i = i + 1
   else:
      while i < tot:
         ch = expr[i]
         if ch != endChar:
            token = token + ch
         elif i + 1 < tot: # if there is a subsequent character
            if expr[i + 1] == endChar: # if next character = endChar
               token = token + ch
               i = i + 1
            else:
               return token, i
         i = i + 1

   return token, i


# ===============================================================================
# getTokenListFromLblFieldName ausilio di get_labelFieldNames
# ===============================================================================
def getTokenListFromLblFieldName(expr):
   """returns a list of tokens, excluding strings, from the expression passed as a parameter"""
   result = []
   i = 0
   tot = len(expr)
   while i < tot:
      ch = expr[i]
      if ch == "\"": # if a field name begins
         token, i = getToken(expr, i + 1, "\"")
         if len(token) > 0:
            result.append(token)
      elif ch == "'": # if a string begins
         token, i = getToken(expr, i + 1, "'")
      else:
         token, i = getToken(expr, i)
         if len(token) > 0:
            result.append(token)

      i = i + 1

   return result


# ===============================================================================
# get_activeDataDefinedPropertyFieldNames
# ===============================================================================
def get_activeDataDefinedPropertyFieldNames(layer, dataDefinedProperty):
   """returns the list of field names that determine the value of the active property"""
   result = []

   if (dataDefinedProperty is not None) and dataDefinedProperty.isActive():
      if len(dataDefinedProperty.expressionString()) > 0:
         # estraggo i token
         tokenList = getTokenListFromLblFieldName(dataDefinedProperty.expressionString())

         labeling = layer.labeling()
         if labeling is not None:
            if type(labeling) == QgsVectorLayerSimpleLabeling:
               palLayerSettings = labeling.settings()
               fields = layer.fields()

               for field in fields:
                  if field.name() in tokenList:
                     if field.name() not in result: # avoid duplicates
                        result.append(field.name())
      else:
         result.append(dataDefinedProperty.field())

   return result


# ===============================================================================
# get_scaleFieldName
# ===============================================================================
def get_labelFieldNames(layer):
   """returns the list of fields that contribute to forming the label text"""
   result = []

   if layer.type() == QgsMapLayer.VectorLayer and layer.labeling() is not None:
      palyr = layer.labeling().settings()
      lblFieldName = palyr.fieldName
      if palyr.isExpression: # Is this label made from a expression string eg FieldName || 'mm'.
         # estraggo i token
         tokenList = getTokenListFromLblFieldName(lblFieldName)

         labeling = layer.labeling()
         if labeling is not None:
            if type(labeling) == QgsVectorLayerSimpleLabeling:
               palLayerSettings = labeling.settings()
               fields = palLayerSettings.mCurFields
               for field in fields:
                  if field.name() in tokenList:
                     if field.name() not in result: # avoid duplicates
                        result.append(field.name())
      else:
         result.append(lblFieldName)

   return result


# ===============================================================================
# get_labelRotationFieldNames
# ===============================================================================
def get_labelRotationFieldNames(layer):
   """returns the list of fields that contribute to the rotation of the label"""
   if layer.type() == QgsMapLayer.VectorLayer and layer.labeling() is not None:
      palyr = layer.labeling().settings()
      dataDefined = palyr.dataDefinedProperties().property(QgsPalLayerSettings.LabelRotation)
      return get_activeDataDefinedPropertyFieldNames(layer, dataDefined)

   return []


# ===============================================================================
# get_labelSizeFieldNames
# ===============================================================================
def get_labelSizeFieldNames(layer):
   """returns the list of fields that contribute to forming the size of the label text"""
   if layer.type() == QgsMapLayer.VectorLayer and layer.labeling() is not None:
      palyr = layer.labeling().settings()
      dataDefined = palyr.dataDefinedProperties().property(QgsPalLayerSettings.Size)
      return get_activeDataDefinedPropertyFieldNames(layer, dataDefined)

   return []


# ===============================================================================
# get_labelFontFamilyFieldNames
# ===============================================================================
def get_labelFontFamilyFieldNames(layer):
   """returns the list of fields that contribute to forming the name of the label font"""
   if layer.type() == QgsMapLayer.VectorLayer and layer.labeling() is not None:
      palyr = layer.labeling().settings()
      dataDefined = palyr.dataDefinedProperties().property(QgsPalLayerSettings.Family)
      return get_activeDataDefinedPropertyFieldNames(layer, dataDefined)

   return []


# ===============================================================================
# get_labelText
# ===============================================================================
def get_labelText(palLayerSettings, feature):
   """returns the label text"""
   lblFieldName = palLayerSettings.fieldName
   if lblFieldName == "":
      return ""
   if palLayerSettings.isExpression: # Is this label made from a expression string eg FieldName || 'mm'.
      expr = QgsExpression(lblFieldName)
      val = expr.evaluate(feature)
   else:
      val = feature.attribute(lblFieldName)

   return val


# ===============================================================================
# get_labelFontSize
# ===============================================================================
def get_labelFontSize(palLayerSettings, feature):
   """returns the font size of the label as an integer"""
   val = None
   dataDefined = palLayerSettings.dataDefinedProperties().property(QgsPalLayerSettings.Size)
   if (dataDefined is not None) and dataDefined.isActive():
      if len(dataDefined.expressionString()) > 0:
         expr = QgsExpression(dataDefined.expressionString())
         val = expr.evaluate(feature)
      else:
         val = feature.attribute(dataDefined.field())
   else:
      # Returns the label text formatting settings, e.g., font settings, buffer settings, etc.
      fmt = palLayerSettings.format()
      val = fmt.font().pointSize() # Returns the point size of the font

   return None if val is None else int(val)


# ===============================================================================
# get_labelFontFamily
# ===============================================================================
def get_labelFontFamily(palLayerSettings, feature):
   """returns the font name of the label"""
   val = None
   dataDefined = palLayerSettings.dataDefinedProperties().property(QgsPalLayerSettings.Family)
   if (dataDefined is not None) and dataDefined.isActive():
      if len(dataDefined.expressionString()) > 0:
         expr = QgsExpression(dataDefined.expressionString())
         val = expr.evaluate(feature)
      else:
         val = feature.attribute(dataDefined.field())
   else:
      # Returns the label text formatting settings, e.g., font settings, buffer settings, etc.
      fmt = palLayerSettings.format()
      val = fmt.font().family()

   return val


# ===============================================================================
# get_labelFontTextNamedStyle
# ===============================================================================
def get_labelFontTextNamedStyle(palLayerSettings, feature):
   """returns the name of the label's font style"""
   val = None
   dataDefined = palLayerSettings.dataDefinedProperties().property(QgsPalLayerSettings.FontStyle)
   if (dataDefined is not None) and dataDefined.isActive():
      if len(dataDefined.expressionString()) > 0:
         expr = QgsExpression(dataDefined.expressionString())
         val = expr.evaluate(feature)
      else:
         val = feature.attribute(dataDefined.field())
   else:
      val = palLayerSettings.textNamedStyle

   return val


# ===============================================================================
# get_labelIsBold
# ===============================================================================
def get_labelIsBold(palLayerSettings, feature):
   """returns if the label font is bold"""
   val = None
   dataDefined = palLayerSettings.dataDefinedProperties().property(QgsPalLayerSettings.Bold)
   if (dataDefined is not None) and dataDefined.isActive():
      if len(dataDefined.expressionString()) > 0:
         expr = QgsExpression(dataDefined.expressionString())
         val = expr.evaluate(feature)
      else:
         val = feature.attribute(dataDefined.field())
   else:
      # Returns the label text formatting settings, e.g., font settings, buffer settings, etc.
      fmt = palLayerSettings.format()
      val = fmt.font().bold()

   return val


# ===============================================================================
# get_labelIsItalic
# ===============================================================================
def get_labelIsItalic(palLayerSettings, feature):
   """returns if the label font is italic"""
   val = None
   dataDefined = palLayerSettings.dataDefinedProperties().property(QgsPalLayerSettings.Italic)
   if (dataDefined is not None) and dataDefined.isActive():
      if len(dataDefined.expressionString()) > 0:
         expr = QgsExpression(dataDefined.expressionString())
         val = expr.evaluate(feature)
      else:
         val = feature.attribute(dataDefined.field())
   else:
      # Returns the label text formatting settings, e.g., font settings, buffer settings, etc.
      fmt = palLayerSettings.format()
      val = fmt.font().italic()

   return val


# ===============================================================================
# get_labelIsUnderline
# ===============================================================================
def get_labelIsUnderline(palLayerSettings, feature):
   """returns if the label font is underlined"""
   val = None
   dataDefined = palLayerSettings.dataDefinedProperties().property(QgsPalLayerSettings.Underline)
   if (dataDefined is not None) and dataDefined.isActive():
      if len(dataDefined.expressionString()) > 0:
         expr = QgsExpression(dataDefined.expressionString())
         val = expr.evaluate(feature)
      else:
         val = feature.attribute(dataDefined.field())
   else:
      # Returns the label text formatting settings, e.g., font settings, buffer settings, etc.
      fmt = palLayerSettings.format()
      val = fmt.font().underline()

   return val


# ===============================================================================
# get_labelIsStrikeOut
# ===============================================================================
def get_labelIsStrikeOut(palLayerSettings, feature):
   """returns if the label font is crossed out"""
   val = None
   dataDefined = palLayerSettings.dataDefinedProperties().property(QgsPalLayerSettings.Strikeout)
   if (dataDefined is not None) and dataDefined.isActive():
      if len(dataDefined.expressionString()) > 0:
         expr = QgsExpression(dataDefined.expressionString())
         val = expr.evaluate(feature)
      else:
         val = feature.attribute(dataDefined.field())
   else:
      # Returns the label text formatting settings, e.g., font settings, buffer settings, etc.
      fmt = palLayerSettings.format()
      val = fmt.font().strikeOut()

   return val


# ===============================================================================
# get_labelFontCase
# ===============================================================================
def get_labelFontCase(palLayerSettings, feature):
   """returns whether the label font is uppercase/lowercase and various options:
      QFont::MixedCase 0 This is the normal text rendering option where no capitalization change is applied.
      QFont::AllUppercase 1 This alters the text to be rendered in all uppercase type.
      QFont::AllLowercase 2 This alters the text to be rendered in all lowercase type.
      QFont::SmallCaps 3 This alters the text to be rendered in small-caps type.
      QFont::Capitalize 4 This alters the text to be rendered with the first character of each word as an uppercase character.
   """
   val = None
   dataDefined = palLayerSettings.dataDefinedProperties().property(QgsPalLayerSettings.FontCase)
   if (dataDefined is not None) and dataDefined.isActive():
      if len(dataDefined.expressionString()) > 0:
         expr = QgsExpression(dataDefined.expressionString())
         val = expr.evaluate(feature)
      else:
         val = feature.attribute(dataDefined.field())
   else:
      # Returns the label text formatting settings, e.g., font settings, buffer settings, etc.
      fmt = palLayerSettings.format()
      val = fmt.font().capitalization()

   return val


# ===============================================================================
# get_labelFontSizeInMapUnits
# ===============================================================================
def get_labelFontSizeInMapUnits(palLayerSettings, feature):
   """returns whether the label font unit is in map units"""
   val = None
   dataDefined = palLayerSettings.dataDefinedProperties().property(QgsPalLayerSettings.FontSizeUnit)
   if (dataDefined is not None) and dataDefined.isActive():
      if len(dataDefined.expressionString()) > 0:
         expr = QgsExpression(dataDefined.expressionString())
         val = True if expr.evaluate(feature) == QgsUnitTypes.RenderMapUnits else False
      else:
         val = True if feature.attribute(dataDefined.field()) == QgsUnitTypes.RenderMapUnits else False
   else:
      # Returns the label text formatting settings, e.g., font settings, buffer settings, etc.
      fmt = palLayerSettings.format()
      val = True if fmt.sizeUnit() == QgsUnitTypes.RenderMapUnits else False

   return val


# ===============================================================================
# get_labelRot
# ===============================================================================
def get_labelRot(palLayerSettings, feature):
   """returns the rotation of the label"""
   val = 0
   dataDefined = palLayerSettings.dataDefinedProperties().property(QgsPalLayerSettings.LabelRotation)
   if (dataDefined is not None) and dataDefined.isActive():
      if len(dataDefined.expressionString()) > 0:
         expr = QgsExpression(dataDefined.expressionString())
         val = expr.evaluate(feature)
      else:
         val = feature.attribute(dataDefined.field())

   return val


# ===============================================================================
# calculateLabelSize
# ===============================================================================
def calculateLabelSize(layer, feature, canvas):
   """
   return size for label in map units
   """
   if layer.type() != QgsMapLayer.VectorLayer and layer.labeling() is not None:
      return None, None
   palyr = layer.labeling().settings()
   # Returns the label text formatting settings, e.g., font settings, buffer settings, etc.
   fmt = palyr.format()
   font = fmt.font()

   text = get_labelText(palyr, feature)

   fontName = get_labelFontFamily(palyr, feature)
   if fontName is not None:
      font.setFamily(fontName)

   fontBold = get_labelIsBold(palyr, feature)
   if fontBold is not None and fontBold:
      font.setBold(fontBold)

   fontItalic = get_labelIsItalic(palyr, feature)
   if fontItalic is not None and fontItalic:
      font.setItalic(fontItalic)

   fontUnderline = get_labelIsUnderline(palyr, feature)
   if fontUnderline is not None and fontUnderline:
      font.setUnderline(fontUnderline)

   fontStrikeOut = get_labelIsStrikeOut(palyr, feature)
   if fontStrikeOut is not None and fontStrikeOut:
      font.setStrikeOut(fontStrikeOut)

   fontCase = get_labelFontCase(palyr, feature)
   if fontCase is not None:
      font.setCapitalization(fontCase)

   fontSize = get_labelFontSize(palyr, feature)
   if fontSize is not None:

      isFontSizeInMapUnits = get_labelFontSizeInMapUnits(palyr, feature)

      if isFontSizeInMapUnits:
         if fontSize < 100:
            font.setPixelSize(fontSize * 100)
         else:
            font.setPixelSize(fontSize)

      fontMetricsF = QFontMetricsF(font)
      rect = fontMetricsF.boundingRect(text)
      dimX = rect.width()
      dimY = rect.height()
      if isFontSizeInMapUnits:
         if fontSize < 100: # if dimX and dimY are already in map units * 10
            return dimX / 100, dimY / 100
         else:
            return dimX, dimY
      else:
         mapToPixel = canvas.getCoordinateTransform() # trasformo pixel in map units
         dimX = dimX * mapToPixel.mapUnitsPerPixel()
         dimY = dimY * mapToPixel.mapUnitsPerPixel()
         return dimX, dimY

   return None, None
