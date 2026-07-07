# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin ok

 class for managing dimensions

                              -------------------
        begin                : 2014-02-20
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
from qgis.PyQt.QtGui  import *
from qgis.core import *
from qgis.gui import *
import qgis.utils

import os
import codecs
import math
import sys


from .qad_msg import QadMsg
from . import qad_utils
from .qad_line import getBoundingPtsOnOnInfinityLine, QadLine
from .qad_arc import QadArc
from .qad_geom_relations import *
from . import qad_stretch_fun
from . import qad_layer
from . import qad_label
from .qad_entity import *
from .qad_variables import QadVariables
from .qad_multi_geom import fromQgsGeomToQadGeom, fromQadGeomToQgsGeom


"""
The dimension class is composed of three layers: text, line, and symbol, all using the same coordinate system.

The text layer must have all the characteristics of the QAD text layer, plus:
- label placement using "Around point" mode with distance = 0
  (meaning the insertion point is at the lower left)
- text size in map units (the size varies depending on zoom).
- dimStyleFieldName = "dim_style"; field name containing the dimension style name (optional)
- dimTypeFieldName = "dim_type"; field name containing the dimension style type (optional)
- the "Show upside-down labels" option must be set to "always" in the "Labels"->"Rendering" tab
- rotation must be read from the field indicated by rotFieldName
- idFieldName = "id"; field name containing the dimension code (optional)
- rotation must be derived from rotFieldName
- character font can be derived from a field
- character size can be derived from a field
- text color can be derived from a field (optional)

The symbol layer must have all the characteristics of the QAD symbol layer, plus:
- the arrow symbol with rotation 0 must be horizontal with the arrow pointing right
  and its insertion point must be on the arrow tip
- symbol size in map units (the size varies depending on zoom),
  set the symbol size so the arrow width is 1 map unit.
- componentFieldName = "type"; field name containing the dimension component type (see QadDimComponentEnum) (optional)
- idParentFieldName = "id_parent"; field name containing the dimension text code (optional)
- scale must be set through Style->Advanced->scale size field-><scale field name>
- scale mode must be set through Style->Advanced->scale size field->scale diameter
- rotation must be read from the field indicated by rotFieldName (360-rotFieldName)

The line layer must have all the characteristics of the line layer, plus:
- componentFieldName = "type"; field name containing the dimension component type (see QadDimComponentEnum) (optional)
- colorFieldName = "color"; field name containing the color 'r,g,b,alpha'; alpha is optional (0=transparent, 255=opaque) (optional)
- idParentFieldName = "id_parent"; field name containing the dimension text code (optional)
- scaleFieldName = "scale"; field name containing the symbol scale factor (optional)
  if used, use the "single symbol" style (the only one that allows the scale to be set as scale diameter)
  scale must be set through Style->Advanced->scale size field-><scale field name>
  scale mode must be set through Style->Advanced->scale size field->scale diameter
- rotFieldName = "rot"; field name containing the symbol rotation
  rotation must be read from the field indicated by rotFieldName (360-rotFieldName)

The line layer must have all the characteristics of the line layer, plus:
- componentFieldName = "type"; field name containing the dimension component type (see QadDimComponentEnum) (optional)
- lineTypeFieldName = "line_type"; field name containing the line type (optional)
- colorFieldName = "color"; field name containing the color 'r,g,b,alpha'; alpha is optional (0=transparent, 255=opaque) (optional)
- idParentFieldName = "id_parent"; field name containing the dimension text code (optional)

"""


# ===============================================================================
# QadDimTypeEnum class.
# ===============================================================================
class QadDimTypeEnum():
   ALIGNED    = "AL" # linear dimension aligned to the origin points of the extension lines
   ANGULAR    = "AN" # angular dimension, measures the angle between the 3 points or between the selected objects
   BASE_LINE  = "BL" # linear, angular or coordinate dimension starting from the baseline of the previous dimension or a selected dimension
   DIAMETER   = "DI" # dimension for the diameter of a circle or arc
   LEADER     = "LD" # creates a line that allows you to connect an annotation to a feature
   LINEAR     = "LI" # linear dimension with a horizontal or vertical dimension line
   RADIUS     = "RA" # radial dimension, measures the radius of a selected circle or arc and displays dimension text with a radius symbol in front
   ARC_LENTGH = "AR" # dimension for the length of an arc


# ===============================================================================
# QadDimComponentEnum class.
# ===============================================================================
class QadDimComponentEnum():
   DIM_LINE1 = "D1" # dimension line ("Dimension line 1")
   DIM_LINE2 = "D2" # dimension line ("Dimension line 2")
   DIM_LINE_EXT1 = "X1" # dimension line extension ("Dimension line eXtension 1")
   DIM_LINE_EXT2 = "X2" # dimension line extension ("Dimension line eXtension 2")
   EXT_LINE1 = "E1" # first extension line ("Extension line 1")
   EXT_LINE2 = "E2" # second extension line ("Extension line 2")
   LEADER_LINE = "L" # dimension line used when the text is outside the dimension ("Leader")
   ARC_LEADER_LINE = "AL" # dimension carrying line used to connect the dimension text with the arc to be dimensioned (see "dimarc" "leader" option)
   BLOCK1 = "B1" # first arrow block ("Block 1")
   BLOCK2 = "B2" # second arrow block ("Block 2")
   LEADER_BLOCK = "LB" # arrow block for leader ("Leader Block")
   ARC_BLOCK = "AB" # arc symbol ("Arc Block")
   DIM_PT1 = "D1" # first point to dimension ("Dimension point 1")
   DIM_PT2 = "D2" # second point to dimension ("Dimension point 2")
   TEXT_PT = "T" # dimension text point ("Text")
   CENTER_MARKER_LINE = "CL" # line that defines the center marker of an arc or circle


# ===============================================================================
# QadDimStyleAlignmentEnum class.
# ===============================================================================
class QadDimStyleAlignmentEnum():
   HORIZONTAL      = 0 # orizzontale
   VERTICAL        = 1 # verticale
   ALIGNED         = 2 # allineata
   FORCED_ROTATION = 3 # forced rotation


# ===============================================================================
# QadDimStyleTxtVerticalPosEnum class.
# ===============================================================================
class QadDimStyleTxtVerticalPosEnum():
   CENTERED_LINE = 0 # text centered on the dimension line
   ABOVE_LINE    = 1 # text above the dimension line but in case the dimension line is not horizontal
                     # and the text is inside the extension lines and forced horizontal then the text becomes centered
   EXTERN_LINE   = 2 # text positioned opposite the dimension points
   BELOW_LINE    = 4 # text below the dimension line but in case the dimension line is not horizontal
                     # and the text is inside the extension lines and forced horizontal then the text becomes centered


# ===============================================================================
# QadDimStyleTxtHorizontalPosEnum class.
# ===============================================================================
class QadDimStyleTxtHorizontalPosEnum():
   CENTERED_LINE      = 0 # text centered on the dimension line
   FIRST_EXT_LINE     = 1 # text near the first extension line
   SECOND_EXT_LINE    = 2 # text near the second extension line
   FIRST_EXT_LINE_UP  = 3 # text above and aligned to the first extension line
   SECOND_EXT_LINE_UP = 4 # text above and aligned to the second extension line


# ===============================================================================
# QadDimStyleTxtRotEnum class.
# ===============================================================================
class QadDimStyleTxtRotModeEnum():
   HORIZONTAL      = 0 # horizontal text
   ALIGNED_LINE    = 1 # text aligned with the dimension line
   ISO             = 2 # text aligned with dimension line if between extension lines,
                       # otherwise horizontal text
   FORCED_ROTATION = 3 # text with forced rotation


# ===============================================================================
# QadDimStyleArcSymbolPosEnum class.
# ===============================================================================
class QadDimStyleArcSymbolPosEnum():
   BEFORE_TEXT = 0 # symbol before text
   ABOVE_TEXT  = 1 # symbol above the text
   NONE        = 2 # no symbol


# ===============================================================================
# QadDimStyleArcSymbolPosEnum class.
# ===============================================================================
class QadDimStyleTxtDirectionEnum():
   SX_TO_DX = 0 # from left to right
   DX_TO_SX = 1 # from right to left


# ===============================================================================
# QadDimStyleTextBlocksAdjustEnum class.
# ===============================================================================
class QadDimStyleTextBlocksAdjustEnum():
   BOTH_OUTSIDE_EXT_LINES = 0 # moves text and arrows outside extension lines
   FIRST_BLOCKS_THEN_TEXT = 1 # first move the arrows then, if that's not enough, also the text
   FIRST_TEXT_THEN_BLOCKS = 2 # first move the text and then, if that's not enough, also the arrows
   WHICHEVER_FITS_BEST    = 3 # Move text or arrows indiscriminately (the object that fits best)


# ===============================================================================
# QadDim dimension style class
# ===============================================================================
class QadDimStyle():

   def __init__(self, dimStyle = None):
      self.name = "standard" # style name
      self.description = ""
      self.path = "" # path and file name where it was saved/loaded
      self.dimType = QadDimTypeEnum.ALIGNED # dimension type

      # dimension text
      self.textPrefix = "" # prefix for the dimension text
      self.textSuffix = "" # suffix for the dimension text
      self.textSuppressLeadingZeros = False # to suppress zeros at the beginning of the text or not
      self.textDecimalZerosSuppression = True # to suppress trailing zeros in decimals
      self.textHeight = 1.0 # text height (DIMTXT) in map units
      self.textVerticalPos = QadDimStyleTxtVerticalPosEnum.ABOVE_LINE # vertical position of the text with respect to the dimension line (DIMTAD)
      self.textHorizontalPos = QadDimStyleTxtHorizontalPosEnum.CENTERED_LINE # horizontal position of the text with respect to the dimension line (DIMTAD)
      self.textOffsetDist = 0.5 # distance added around the text when the dimension line is broken to insert it (DIMGAP)
      self.textRotMode = QadDimStyleTxtRotModeEnum.ALIGNED_LINE # text rotation mode (DIMTIH and DIMTOH)
      self.textForcedRot = 0.0 # forced text rotation
      self.textDecimals = 2 # number of decimals (DIMDEC)
      self.textDecimalSep = "." # decimal separator (DIMDSEP)
      self.textFont = "Arial" # text font name (DIMTXSTY)
      self.textColor = "255,255,255,255" # Color for dimension texts (DIMCLRT); white with total opacity
      self.textDirection = QadDimStyleTxtDirectionEnum.SX_TO_DX # specifies the direction of the dimension text (DIMTXTDIRECTION) 0 = from left to right, 1 = from right to left
      self.arcSymbPos = QadDimStyleArcSymbolPosEnum.BEFORE_TEXT # draw the arc symbol with DIMARC (DIMARCSYM) or not.

      # dimension lines
      self.dimLine1Show = True # Show or hide the first dimension line (DIMSD1)
      self.dimLine2Show = True # Show or hide the second dimension line (DIMSD2)
      self.dimLineLineType = "continuous" # Linetype for dimension lines (DIMLTYPE)
      self.dimLineColor = "255,255,255,255" # Color for dimension lines (DIMCLRD); white with total opacity
      self.dimLineSpaceOffset = 3.75 # Controls dimension line spacing in baseline dimensions (DIMDLI)
      self.dimLineOffsetExtLine = 0.0 # dimension line distance beyond extension line (DIMDLE)


      # symbols for dimension lines
      # the arrow block is a right-pointing arrow with the insertion point at the arrowhead
      self.block1Name = "triangle2" # name of the symbol to use as the arrowhead on the first dimension line (DIMBLK1)
      self.block2Name = "triangle2"  # name of the symbol to use as the arrowhead on the second dimension line (DIMBLK2)
      self.blockLeaderName = "triangle2" # name of the symbol to use as the arrowhead on the leader line (DIMLDRBLK)
      self.blockWidth = 0.5 # symbol width (horizontally) when size in map units = 1 (see "triangle2")
      self.blockScale = 1.0 # scala della dimensione del simbolo (DIMASZ)
      self.centerMarkSize = 0.0 # draws whether or not the center marker or centerlines for dimensions created with
                                # DIMCENTER, DIMDIAMETER, e DIMRADIUS (DIMCEN).
                                # 0 = nothing, > 0 center marker size, < 0 axis line size

      # adaptation of text and arrows
      self.textBlockAdjust = QadDimStyleTextBlocksAdjustEnum.WHICHEVER_FITS_BEST # (DIMATFIT)
      self.blockSuppressionForNoSpace = False # Suppress arrowheads if there is not enough space inside the extension lines (DIMSOXD)

      # extension lines
      self.extLine1Show = True # Show or hide the first extension line (DIMSE1)
      self.extLine2Show = True # Show or hide the second extension line (DIMSE2)
      self.extLine1LineType = "continuous" # Linetype for first extension line (DIMLTEX1)
      self.extLine2LineType = "continuous" # Linetype for second extension line (DIMLTEX2)
      self.extLineColor = "255,255,255,255" # Color for extension lines (DIMCLRE); white with total opacity
      self.extLineOffsetDimLine = 0.0 # distance of the extension line beyond the dimension line (DIMEXE)
      self.extLineOffsetOrigPoints = 0.0 # distance of the extension line from the points to be dimensioned (DIMEXO)
      self.extLineIsFixedLen = False # Enables fixed length for extension lines (DIMFXLON)
      self.extLineFixedLen = 1.0 # fixed length of extension lines (DIMFXL) from the dimension line
                                 # to the dimension point shifted by extLineOffsetOrigPoints
                                 # (the extension line does not go beyond the point to be dimensioned)

      # layers and their characteristics
      # I have to allocate fields at QadDimStyle class level because QgsFeature.setFields only uses the pointer to the fields list
      # which, if privately allocated in any function, would be destroyed upon exiting the function
      self.textualLayerName = None    # layer name to store the dimension text
      self.__textualLayer = None        # layer to store the dimension text
      self.__textFields = None
      self.__textualFeaturePrototype = None

      self.linearLayerName = None    # layer name to store the dimension lines
      self.__linearLayer = None        # layer to store dimension lines
      self.__lineFields = None
      self.__linearFeaturePrototype = None

      self.symbolLayerName = None  # layer name to store the dimension arrow blocks
      self.__symbolLayer = None      # layer to store dimension arrow blocks
      self.__symbolFields = None
      self.__symbolFeaturePrototype = None

      self.componentFieldName = "type"      # name of the field that contains the type of dimension component (see QadDimComponentEnum)
      self.lineTypeFieldName = "line_type"  # name of the field containing the linetype
      self.colorFieldName = "color"         # name of the field that contains the color 'r,g,b,alpha'; alpha is optional (0=transparent, 255=opaque)
      self.idFieldName = "id"               # name of the field that contains the dimension code in the text layer
      self.idParentFieldName = "id_parent"  # name of the field that contains the dimension code in the symbol and line layers
      self.dimStyleFieldName = "dim_style"  # name of the field that contains the name of the dimension style
      self.dimTypeFieldName = "dim_type"    # name of the field that contains the type of the dimension style
      self.symbolFieldName = "block"        # name of the field that contains the name of the symbol
      self.scaleFieldName = "scale"         # name of the field containing the dimension
      self.rotFieldName = "rot"             # name of the field that contains rotation in degrees

      if dimStyle is None:
         return
      self.set(dimStyle)


   # ============================================================================
   # GENERIC FUNCTIONS - START
   # ============================================================================

   def set(self, dimStyle):
      self.name = dimStyle.name
      self.description = dimStyle.description
      self.path = dimStyle.path
      self.dimType = dimStyle.dimType

      # dimension text
      self.textPrefix = dimStyle.textPrefix
      self.textSuffix = dimStyle.textSuffix
      self.textSuppressLeadingZeros = dimStyle.textSuppressLeadingZeros
      self.textDecimalZerosSuppression = dimStyle.textDecimalZerosSuppression
      self.textHeight = dimStyle.textHeight
      self.textVerticalPos = dimStyle.textVerticalPos
      self.textHorizontalPos = dimStyle.textHorizontalPos
      self.textOffsetDist = dimStyle.textOffsetDist
      self.textRotMode = dimStyle.textRotMode
      self.textForcedRot = dimStyle.textForcedRot
      self.textDecimals = dimStyle.textDecimals
      self.textDecimalSep = dimStyle.textDecimalSep
      self.textFont = dimStyle.textFont
      self.textColor = dimStyle.textColor
      self.textDirection = dimStyle.textDirection
      self.arcSymbPos = dimStyle.arcSymbPos

      # dimension lines
      self.dimLine1Show = dimStyle.dimLine1Show
      self.dimLine2Show = dimStyle.dimLine2Show
      self.dimLineLineType = dimStyle.dimLineLineType
      self.dimLineColor = dimStyle.dimLineColor
      self.dimLineSpaceOffset = dimStyle.dimLineSpaceOffset
      self.dimLineOffsetExtLine = dimStyle.dimLineOffsetExtLine

      # symbols for dimension lines
      self.block1Name = dimStyle.block1Name
      self.block2Name = dimStyle.block2Name
      self.blockLeaderName = dimStyle.blockLeaderName
      self.blockWidth = dimStyle.blockWidth
      self.blockScale = dimStyle.blockScale
      self.blockSuppressionForNoSpace = dimStyle.blockSuppressionForNoSpace
      self.centerMarkSize = dimStyle.centerMarkSize

      # adaptation of text and arrows
      self.textBlockAdjust = dimStyle.textBlockAdjust

      # extension lines
      self.extLine1Show = dimStyle.extLine1Show
      self.extLine2Show = dimStyle.extLine2Show
      self.extLine1LineType = dimStyle.extLine1LineType
      self.extLine2LineType = dimStyle.extLine2LineType
      self.extLineColor = dimStyle.extLineColor
      self.extLineOffsetDimLine = dimStyle.extLineOffsetDimLine
      self.extLineOffsetOrigPoints = dimStyle.extLineOffsetOrigPoints
      self.extLineIsFixedLen = dimStyle.extLineIsFixedLen
      self.extLineFixedLen = dimStyle.extLineFixedLen

      # layers and their characteristics
      self.textualLayerName = dimStyle.textualLayerName
      self.__textualLayer = dimStyle.__textualLayer
      self.__textFields = dimStyle.__textFields
      self.__textualFeaturePrototype = dimStyle.__textualFeaturePrototype
      self.linearLayerName = dimStyle.linearLayerName
      self.__linearLayer = dimStyle.__linearLayer
      self.__lineFields = dimStyle.__lineFields
      self.__linearFeaturePrototype = dimStyle.__linearFeaturePrototype
      self.symbolLayerName = dimStyle.symbolLayerName
      self.__symbolLayer = dimStyle.__symbolLayer
      self.__symbolFields = dimStyle.__symbolFields
      self.__symbolFeaturePrototype = dimStyle.__symbolFeaturePrototype

      self.componentFieldName = dimStyle.componentFieldName
      self.symbolFieldName = dimStyle.symbolFieldName
      self.lineTypeFieldName = dimStyle.lineTypeFieldName
      self.colorFieldName = dimStyle.colorFieldName
      self.idFieldName = dimStyle.idFieldName
      self.idParentFieldName = dimStyle.idParentFieldName
      self.dimStyleFieldName = dimStyle.dimStyleFieldName
      self.dimTypeFieldName = dimStyle.dimTypeFieldName
      self.scaleFieldName = dimStyle.scaleFieldName
      self.rotFieldName = dimStyle.rotFieldName


   # ============================================================================
   # getPropList
   # ============================================================================
   def getPropList(self):
      proplist = dict() # name dictionary with list [description, value]
      propDescr = QadMsg.translate("Dimension", "Name")
      proplist["name"] = [propDescr, self.name]
      propDescr = QadMsg.translate("Dimension", "Description")
      proplist["description"] = [propDescr, self.description]
      propDescr = QadMsg.translate("Dimension", "File path")
      proplist["path"] = [propDescr, self.path]

      # dimension text
      value = self.textPrefix
      if len(self.textPrefix) > 0:
         value += "<>"
      value += self.textSuffix
      propDescr = QadMsg.translate("Dimension", "Text prefix and suffix")
      proplist["textPrefix"] = [propDescr, value]
      propDescr = QadMsg.translate("Dimension", "Leading zero suppression")
      proplist["textSuppressLeadingZeros"] = [propDescr, self.textSuppressLeadingZeros]
      propDescr = QadMsg.translate("Dimension", "Trailing zero suppression")
      proplist["textDecimalZerosSuppression"] = [propDescr, self.textDecimalZerosSuppression]
      propDescr = QadMsg.translate("Dimension", "Text height")
      proplist["textHeight"] = [propDescr, self.textHeight]
      propDescr = QadMsg.translate("Dimension", "Vertical text position")
      proplist["textVerticalPos"] = [propDescr, self.textVerticalPos]
      propDescr = QadMsg.translate("Dimension", "Horizontal text position")
      proplist["textHorizontalPos"] = [propDescr, self.textHorizontalPos]
      propDescr = QadMsg.translate("Dimension", "Text offset")
      proplist["textOffsetDist"] = [propDescr, self.textOffsetDist]
      propDescr = QadMsg.translate("Dimension", "Text alignment")
      proplist["textRotMode"] = [propDescr, self.textRotMode]
      propDescr = QadMsg.translate("Dimension", "Fixed text rotation")
      proplist["textForcedRot"] = [propDescr, self.textForcedRot]
      propDescr = QadMsg.translate("Dimension", "Precision")
      proplist["textDecimals"] = [propDescr, self.textDecimals]
      propDescr = QadMsg.translate("Dimension", "Decimal separator")
      proplist["textDecimalSep"] = [propDescr, self.textDecimalSep]
      propDescr = QadMsg.translate("Dimension", "Text font")
      proplist["textFont"] = [propDescr, self.textFont]
      propDescr = QadMsg.translate("Dimension", "Text color")
      proplist["textColor"] = [propDescr, self.textColor]
      if self.textDirection == QadDimStyleTxtDirectionEnum.SX_TO_DX:
         value = QadMsg.translate("Dimension", "From left to right")
      else:
         value = QadMsg.translate("Dimension", "From right to left")
      propDescr = QadMsg.translate("Dimension", "Text direction")
      proplist["textDirection"] = [propDescr, value]
      propDescr = QadMsg.translate("Dimension", "Arc len. symbol")
      proplist["arcSymbPos"] = [propDescr, self.arcSymbPos]

      # dimension lines
      propDescr = QadMsg.translate("Dimension", "Dim line 1 visible")
      proplist["dimLine1Show"] = [propDescr, self.dimLine1Show]
      propDescr = QadMsg.translate("Dimension", "Dim line 2 visible")
      proplist["dimLine2Show"] = [propDescr, self.dimLine2Show]
      propDescr = QadMsg.translate("Dimension", "Dim line linetype")
      proplist["dimLineLineType"] = [propDescr, self.dimLineLineType]
      propDescr = QadMsg.translate("Dimension", "Dim line color")
      proplist["dimLineColor"] = [propDescr, self.dimLineColor]
      propDescr = QadMsg.translate("Dimension", "Offset from origin")
      proplist["dimLineSpaceOffset"] = [propDescr, self.dimLineSpaceOffset]
      propDescr = QadMsg.translate("Dimension", "Dim line extension")
      proplist["dimLineOffsetExtLine"] = [propDescr, self.dimLineOffsetExtLine]

      # symbols for dimension lines
      propDescr = QadMsg.translate("Dimension", "Arrow 1")
      proplist["block1Name"] = [propDescr, self.block1Name]
      propDescr = QadMsg.translate("Dimension", "Arrow 2")
      proplist["block2Name"] = [propDescr, self.block2Name]
      propDescr = QadMsg.translate("Dimension", "Leader arrow")
      proplist["blockLeaderName"] = [propDescr, self.blockLeaderName]
      propDescr = QadMsg.translate("Dimension", "Arrowhead width")
      proplist["blockWidth"] = [propDescr, self.blockWidth]
      propDescr = QadMsg.translate("Dimension", "Arrowhead scale")
      proplist["blockScale"] = [propDescr, self.blockScale]
      propDescr = QadMsg.translate("Dimension", "Center mark size")
      proplist["centerMarkSize"] = [propDescr, self.centerMarkSize]

      # adaptation of text and arrows
      propDescr = QadMsg.translate("Dimension", "Fit: arrows and text")
      proplist["textBlockAdjust"] = [propDescr, self.textBlockAdjust]
      propDescr = QadMsg.translate("Dimension", "Suppress arrows for lack of space")
      proplist["blockSuppressionForNoSpace"] = [propDescr, self.blockSuppressionForNoSpace]

      # extension lines
      propDescr = QadMsg.translate("Dimension", "Ext. line 1 visible")
      proplist["extLine1Show"] = [propDescr, self.extLine1Show]
      propDescr = QadMsg.translate("Dimension", "Ext. line 2 visible")
      proplist["extLine2Show"] = [propDescr, self.extLine2Show]
      propDescr = QadMsg.translate("Dimension", "Ext. line 1 linetype")
      proplist["extLine1LineType"] = [propDescr, self.extLine1LineType]
      propDescr = QadMsg.translate("Dimension", "Ext. line 2 linetype")
      proplist["extLine2LineType"] = [propDescr, self.extLine2LineType]
      propDescr = QadMsg.translate("Dimension", "Ext. line color")
      proplist["extLineColor"] = [propDescr, self.extLineColor]
      propDescr = QadMsg.translate("Dimension", "Ext. line extension")
      proplist["extLineOffsetDimLine"] = [propDescr, self.extLineOffsetDimLine]
      propDescr = QadMsg.translate("Dimension", "Ext. line offset")
      proplist["extLineOffsetOrigPoints"] = [propDescr, self.extLineOffsetOrigPoints]
      propDescr = QadMsg.translate("Dimension", "Fixed length ext. line activated")
      proplist["extLineIsFixedLen"] = [propDescr, self.extLineIsFixedLen]
      propDescr = QadMsg.translate("Dimension", "Fixed length ext. line")
      proplist["extLineFixedLen"] = [propDescr, self.extLineFixedLen]

      # layers and their characteristics
      propDescr = QadMsg.translate("Dimension", "Layer for dim texts")
      proplist["textualLayerName"] = [propDescr, self.textualLayerName]
      propDescr = QadMsg.translate("Dimension", "Layer for dim lines")
      proplist["linearLayerName"] = [propDescr, self.linearLayerName]
      propDescr = QadMsg.translate("Dimension", "Layer for dim arrows")
      proplist["symbolLayerName"] = [propDescr, self.symbolLayerName]

      propDescr = QadMsg.translate("Dimension", "Field for component type")
      proplist["componentFieldName"] = [propDescr, self.componentFieldName]
      propDescr = QadMsg.translate("Dimension", "Field for linetype")
      proplist["lineTypeFieldName"] = [propDescr, self.lineTypeFieldName]
      propDescr = QadMsg.translate("Dimension", "Field for color")
      proplist["colorFieldName"] = [propDescr, self.colorFieldName]
      propDescr = QadMsg.translate("Dimension", "Field for dim ID in texts")
      proplist["idFieldName"] = [propDescr, self.idFieldName]
      propDescr = QadMsg.translate("Dimension", "Field for dim ID in lines and arrows")
      proplist["idParentFieldName"] = [propDescr, self.idParentFieldName]
      propDescr = QadMsg.translate("Dimension", "Field for dim style name")
      proplist["dimStyleFieldName"] = [propDescr, self.dimStyleFieldName]
      propDescr = QadMsg.translate("Dimension", "Field for dim type")
      proplist["dimTypeFieldName"] = [propDescr, self.dimTypeFieldName]
      propDescr = QadMsg.translate("Dimension", "Field for symbol name")
      proplist["symbolFieldName"] = [propDescr, self.symbolFieldName]
      propDescr = QadMsg.translate("Dimension", "Field for arrows scale")
      proplist["scaleFieldName"] = [propDescr, self.scaleFieldName]
      propDescr = QadMsg.translate("Dimension", "Field for arrows rotation")
      proplist["rotFieldName"] = [propDescr, self.rotFieldName]

      return proplist


   # ============================================================================
   # getLayer
   # ============================================================================
   def getLayer(self, layerName):
      if layerName is not None:
         layerList = QgsProject.instance().mapLayersByName(layerName)
         if len(layerList) == 1:
            return layerList[0]
      return None


   # ============================================================================
   # text layer
   def getTextualLayer(self):
      if self.__textualLayer is None:
         self.__textualLayer = self.getLayer(self.textualLayerName)
      return self.__textualLayer

   def getTextualLayerFields(self):
      if self.__textFields is None:
         self.__textFields = None if self.getTextualLayer() is None else self.getTextualLayer().fields()
      return self.__textFields

   def getTextualFeaturePrototype(self):
      if self.__textualFeaturePrototype is None:
         if self.getTextualLayerFields() is not None:
            self.__textualFeaturePrototype = QgsFeature(self.getTextualLayerFields())
            self.initFeatureToDefautlValues(self.getTextualLayer(), self.__textualFeaturePrototype)
      return self.__textualFeaturePrototype


   # ============================================================================
   # linear layer
   def getLinearLayer(self):
      if self.__linearLayer is None:
         self.__linearLayer = self.getLayer(self.linearLayerName)
      return self.__linearLayer

   def getLinearLayerFields(self):
      if self.__lineFields is None:
         self.__lineFields = None if self.getLinearLayer() is None else self.getLinearLayer().fields()
      return self.__lineFields

   def getLinearFeaturePrototype(self):
      if self.__linearFeaturePrototype is None:
         if self.getLinearLayerFields() is not None:
            self.__linearFeaturePrototype = QgsFeature(self.getLinearLayerFields())
            self.initFeatureToDefautlValues(self.getLinearLayer(), self.__linearFeaturePrototype)
      return self.__linearFeaturePrototype


   # ============================================================================
   # symbol layer
   def getSymbolLayer(self):
      if self.__symbolLayer is None:
         self.__symbolLayer = self.getLayer(self.symbolLayerName)
      return self.__symbolLayer

   def getSymbolLayerFields(self):
      if self.__symbolFields is None:
         self.__symbolFields = None if self.getSymbolLayer() is None else self.getSymbolLayer().fields()
      return self.__symbolFields

   def getSymbolFeaturePrototype(self):
      if self.__symbolFeaturePrototype is None:
         if self.getSymbolLayerFields() is not None:
            self.__symbolFeaturePrototype = QgsFeature(self.getSymbolLayerFields())
            self.initFeatureToDefautlValues(self.getSymbolLayer(), self.__symbolFeaturePrototype)
      return self.__symbolFeaturePrototype


   # ============================================================================
   # initFeatureToDefautlValues
   # ============================================================================
   def initFeatureToDefautlValues(self, layer, f):
      # assign default values
      provider = layer.dataProvider()
      fields = f.fields()
      for field in fields.toList():
         i = fields.indexFromName(field.name())
         f[field.name()] = provider.defaultValue(i)


   # ============================================================================
   # getDefaultDimFilePath
   # ============================================================================
   def getDefaultDimFilePath(self):
      # obtains the automatic path where to save/load the dimensioning file
      # if there is a loaded project the path is that of the project
      projectFilePath = QgsProject.instance().absoluteFilePath()
      path = "" if len(projectFilePath) == 0 else QFileInfo(projectFilePath).absolutePath()
      if len(path) == 0:
         # if there is no project loaded I use the qad installation path
         path = QDir.cleanPath(QgsApplication.qgisSettingsDirPath() + "python/plugins/qad")
      return path + "/"


   # ============================================================================
   # save
   # ============================================================================
   def save(self, path = "", overwrite = True):
      """Saves the dimensioning style settings to a file."""
      if path == "" and self.path != "":
         _path = self.path
      else:
         dir, base = os.path.split(path) # returns path and file name with extension
         if dir == "":
            dir = self.getDefaultDimFilePath()
         else:
            dir = QDir.cleanPath(dir) + "/"

         name, ext = os.path.splitext(base)
         if name == "":
            name = self.name

         if ext == "": # if there is no extension add it
            ext = ".dim"

         _path = dir + name + ext

      if overwrite == False: # if you don't want to overwrite
         if os.path.exists(_path):
            return False

      dir = QFileInfo(_path).absoluteDir()
      if not dir.exists():
         os.makedirs(dir.absolutePath())

      config = qad_utils.QadRawConfigParser(allow_no_value=True)
      config.add_section("dimension_options")
      config.set("dimension_options", "name", str(self.name))
      config.set("dimension_options", "description", self.description)
      config.set("dimension_options", "dimType", str(self.dimType))

      # dimension text
      config.set("dimension_options", "textPrefix", str(self.textPrefix))
      config.set("dimension_options", "textSuffix", str(self.textSuffix))
      config.set("dimension_options", "textSuppressLeadingZeros", str(self.textSuppressLeadingZeros))
      config.set("dimension_options", "textDecimalZerosSuppression", str(self.textDecimalZerosSuppression))
      config.set("dimension_options", "textHeight", str(self.textHeight))
      config.set("dimension_options", "textVerticalPos", str(self.textVerticalPos))
      config.set("dimension_options", "textHorizontalPos", str(self.textHorizontalPos))
      config.set("dimension_options", "textOffsetDist", str(self.textOffsetDist))
      config.set("dimension_options", "textRotMode", str(self.textRotMode))
      config.set("dimension_options", "textForcedRot", str(self.textForcedRot))
      config.set("dimension_options", "textDecimals", str(self.textDecimals))
      config.set("dimension_options", "textDecimalSep", str(self.textDecimalSep))
      config.set("dimension_options", "textFont", str(self.textFont))
      config.set("dimension_options", "textColor", str(self.textColor))
      config.set("dimension_options", "textDirection", str(self.textDirection))
      config.set("dimension_options", "arcSymbPos", str(self.arcSymbPos))

      # dimension lines
      config.set("dimension_options", "dimLine1Show", str(self.dimLine1Show))
      config.set("dimension_options", "dimLine2Show", str(self.dimLine2Show))
      config.set("dimension_options", "dimLineLineType", str(self.dimLineLineType))
      config.set("dimension_options", "dimLineColor", str(self.dimLineColor))
      config.set("dimension_options", "dimLineSpaceOffset", str(self.dimLineSpaceOffset))
      config.set("dimension_options", "dimLineOffsetExtLine", str(self.dimLineOffsetExtLine))

      # symbols for dimension lines
      config.set("dimension_options", "block1Name", str(self.block1Name))
      config.set("dimension_options", "block2Name", str(self.block2Name))
      config.set("dimension_options", "blockLeaderName", str(self.blockLeaderName))
      config.set("dimension_options", "blockWidth", str(self.blockWidth))
      config.set("dimension_options", "blockScale", str(self.blockScale))
      config.set("dimension_options", "blockSuppressionForNoSpace", str(self.blockSuppressionForNoSpace))
      config.set("dimension_options", "centerMarkSize", str(self.centerMarkSize))

      # adaptation of text and arrows
      config.set("dimension_options", "textBlockAdjust", str(self.textBlockAdjust))

      # extension lines
      config.set("dimension_options", "extLine1Show", str(self.extLine1Show))
      config.set("dimension_options", "extLine2Show", str(self.extLine2Show))
      config.set("dimension_options", "extLine1LineType", str(self.extLine1LineType))
      config.set("dimension_options", "extLine2LineType", str(self.extLine2LineType))
      config.set("dimension_options", "extLineColor", str(self.extLineColor))
      config.set("dimension_options", "extLineOffsetDimLine", str(self.extLineOffsetDimLine))
      config.set("dimension_options", "extLineOffsetOrigPoints", str(self.extLineOffsetOrigPoints))
      config.set("dimension_options", "extLineIsFixedLen", str(self.extLineIsFixedLen))
      config.set("dimension_options", "extLineFixedLen", str(self.extLineFixedLen))

      # layers and their characteristics
      config.set("dimension_options", "textualLayerName", "" if self.textualLayerName is None else self.textualLayerName)
      config.set("dimension_options", "linearLayerName", "" if self.linearLayerName is None else self.linearLayerName)
      config.set("dimension_options", "symbolLayerName", "" if self.symbolLayerName is None else self.symbolLayerName)
      config.set("dimension_options", "componentFieldName", str(self.componentFieldName))
      config.set("dimension_options", "symbolFieldName", str(self.symbolFieldName))
      config.set("dimension_options", "lineTypeFieldName", str(self.lineTypeFieldName))
      config.set("dimension_options", "colorFieldName", str(self.colorFieldName))
      config.set("dimension_options", "idFieldName", str(self.idFieldName))
      config.set("dimension_options", "idParentFieldName", str(self.idParentFieldName))
      config.set("dimension_options", "dimStyleFieldName", str(self.dimStyleFieldName))
      config.set("dimension_options", "dimTypeFieldName", str(self.dimTypeFieldName))
      config.set("dimension_options", "scaleFieldName", str(self.scaleFieldName))
      config.set("dimension_options", "rotFieldName", str(self.rotFieldName))

      with codecs.open(_path, 'w', 'utf-8') as configFile:
          config.write(configFile)

      self.path = _path

      return True


   # ============================================================================
   # load
   # ============================================================================
   def load(self, path):
      """Load dimension style settings from a file."""
      if path is None or path == "":
         return False

      if os.path.dirname(path) == "": # path contains only the file name (without dir)
         _path = self.getDefaultDimFilePath()
         _path = _path + path
      else:
         _path = path

      if not os.path.exists(_path):
         return False

      config = qad_utils.QadRawConfigParser(allow_no_value=True)
      # file = codecs.open(_path, "r", "utf-8")
      # config.read_file(file)
      # file.close()
      config.read(_path)

      value = config.get("dimension_options", "name", fallback = None)
      if value is not None:
         self.name = value
      value = config.get("dimension_options", "description", fallback = None)
      if value is not None:
         self.description = value
      value = config.get("dimension_options", "dimType", fallback = None)
      if value is not None:
         self.dimType = value

      # dimension text
      value = config.get("dimension_options", "textPrefix", fallback = None)
      if value is not None:
         self.textPrefix = value
      value = config.get("dimension_options", "textSuffix", fallback = None)
      if value is not None:
         self.textSuffix = value
      value = config.getboolean("dimension_options", "textSuppressLeadingZeros", fallback = None)
      if value is not None:
         self.textSuppressLeadingZeros = value
      value = config.getboolean("dimension_options", "textDecimalZerosSuppression", fallback = None)
      if value is not None:
         self.textDecimalZerosSuppression = value
      value = config.getfloat("dimension_options", "textHeight", fallback = None)
      if value is not None:
         self.textHeight = value
      value = config.getint("dimension_options", "textVerticalPos", fallback = None)
      if value is not None:
         self.textVerticalPos = value
      value = config.getint("dimension_options", "textHorizontalPos", fallback = None)
      if value is not None:
         self.textHorizontalPos = value
      value = config.getfloat("dimension_options", "textOffsetDist", fallback = None)
      if value is not None:
         self.textOffsetDist = value
      value = config.getint("dimension_options", "textRotMode", fallback = None)
      if value is not None:
         self.textRotMode = value
      value = config.getfloat("dimension_options", "textForcedRot", fallback = None)
      if value is not None:
         self.textForcedRot = value
      value = config.getint("dimension_options", "textDecimals", fallback = None)
      if value is not None:
         self.textDecimals = value
      value = config.get("dimension_options", "textDecimalSep", fallback = None)
      if value is not None:
         self.textDecimalSep = value
      value = config.get("dimension_options", "textFont", fallback = None)
      if value is not None:
         self.textFont = value
      value = config.get("dimension_options", "textColor", fallback = None)
      if value is not None:
         self.textColor = value
      value = config.getint("dimension_options", "textDirection", fallback = None)
      if value is not None:
         self.textDirection = value
      value = config.getint("dimension_options", "arcSymbPos", fallback = None)
      if value is not None:
         self.arcSymbPos = value

      # dimension lines
      value = config.getboolean("dimension_options", "dimLine1Show", fallback = None)
      if value is not None:
         self.dimLine1Show = value
      value = config.getboolean("dimension_options", "dimLine2Show", fallback = None)
      if value is not None:
         self.dimLine2Show = value
      value = config.get("dimension_options", "dimLineLineType", fallback = None)
      if value is not None:
         self.dimLineLineType = value
      value = config.get("dimension_options", "dimLineColor", fallback = None)
      if value is not None:
         self.dimLineColor = value
      value = config.getfloat("dimension_options", "dimLineSpaceOffset", fallback = None)
      if value is not None:
         self.dimLineSpaceOffset = value
      value = config.getfloat("dimension_options", "dimLineOffsetExtLine", fallback = None)
      if value is not None:
         self.dimLineOffsetExtLine = value

      # symbols for dimension lines
      value = config.get("dimension_options", "block1Name", fallback = None)
      if value is not None:
         self.block1Name = value
      value = config.get("dimension_options", "block2Name", fallback = None)
      if value is not None:
         self.block2Name = value
      value = config.get("dimension_options", "blockLeaderName", fallback = None)
      if value is not None:
         self.blockLeaderName = value
      value = config.getfloat("dimension_options", "blockWidth", fallback = None)
      if value is not None:
         self.blockWidth = value
      value = config.getfloat("dimension_options", "blockScale", fallback = None)
      if value is not None:
         self.blockScale = value
      value = config.getboolean("dimension_options", "blockSuppressionForNoSpace", fallback = None)
      if value is not None:
         self.blockSuppressionForNoSpace = value
      value = config.getfloat("dimension_options", "centerMarkSize", fallback = None)
      if value is not None:
         self.centerMarkSize = value

      # adaptation of text and arrows
      value = config.getint("dimension_options", "textBlockAdjust", fallback = None)
      if value is not None:
         self.textBlockAdjust = value

      # extension lines
      value = config.getboolean("dimension_options", "extLine1Show", fallback = None)
      if value is not None:
         self.extLine1Show = value
      value = config.getboolean("dimension_options", "extLine2Show", fallback = None)
      if value is not None:
         self.extLine2Show = value
      value = config.get("dimension_options", "extLine1LineType", fallback = None)
      if value is not None:
         self.extLine1LineType = value
      value = config.get("dimension_options", "extLine2LineType", fallback = None)
      if value is not None:
         self.extLine2LineType = value
      value = config.get("dimension_options", "extLineColor", fallback = None)
      if value is not None:
         self.extLineColor = value
      value = config.getfloat("dimension_options", "extLineOffsetDimLine", fallback = None)
      if value is not None:
         self.extLineOffsetDimLine = value
      value = config.getfloat("dimension_options", "extLineOffsetOrigPoints", fallback = None)
      if value is not None:
         self.extLineOffsetOrigPoints = value
      value = config.getboolean("dimension_options", "extLineIsFixedLen", fallback = None)
      if value is not None:
         self.extLineIsFixedLen = value
      value = config.getfloat("dimension_options", "extLineFixedLen", fallback = None)
      if value is not None:
         self.extLineFixedLen = value

      # layers and their characteristics
      value = config.get("dimension_options", "textualLayerName", fallback = None)
      if value is not None:
         self.textualLayerName = value
      value = config.get("dimension_options", "linearLayerName", fallback = None)
      if value is not None:
         self.linearLayerName = value
      value = config.get("dimension_options", "symbolLayerName", fallback = None)
      if value is not None:
         self.symbolLayerName = value

      value = config.get("dimension_options", "componentFieldName", fallback = None)
      if value is not None:
         self.componentFieldName = value
      value = config.get("dimension_options", "symbolFieldName", fallback = None)
      if value is not None:
         self.symbolFieldName = value
      value = config.get("dimension_options", "lineTypeFieldName", fallback = None)
      if value is not None:
         self.lineTypeFieldName = value
      value = config.get("dimension_options", "colorFieldName", fallback = None)
      if value is not None:
         self.colorFieldName = value
      value = config.get("dimension_options", "idFieldName", fallback = None)
      if value is not None:
         self.idFieldName = value
      value = config.get("dimension_options", "idParentFieldName", fallback = None)
      if value is not None:
         self.idParentFieldName = value
      value = config.get("dimension_options", "dimStyleFieldName", fallback = None)
      if value is not None:
         self.dimStyleFieldName = value
      value = config.get("dimension_options", "dimTypeFieldName", fallback = None)
      if value is not None:
         self.dimTypeFieldName = value
      value = config.get("dimension_options", "scaleFieldName", fallback = None)
      if value is not None:
         self.scaleFieldName = value
      value = config.get("dimension_options", "rotFieldName", fallback = None)
      if value is not None:
         self.rotFieldName = value

      self.path = _path

      return True


   # ============================================================================
   # remove
   # ============================================================================
   def remove(self):
      """Clears the dimensioning style settings file."""
      currDimStyleName = QadVariables.get(QadMsg.translate("Environment variables", "DIMSTYLE"))
      if self.name == currDimStyleName: # the style to be deleted is the current one
         return False

      if self.path is not None and self.path != "":
         if os.path.exists(self.path):
            try:
               os.remove(self.path)
            except:
               return False

      return True

   # ============================================================================
   # rename
   # ============================================================================
   def rename(self, newName):
      """Renames the name of the style and dimensioning style settings file."""
      if newName == self.name: # same name
         return True
      oldName = self.name

      if self.path is not None or self.path != "":
         if os.path.exists(self.path):
            try:
               dir, base = os.path.split(self.path)
               dir = QDir.cleanPath(dir) + "/"

               name, ext = os.path.splitext(base)
               newPath = dir + "/" + newName + ext

               os.rename(self.path, newPath)
               self.path = newPath
               self.name = newName
               self.save()
            except:
               return False
      else:
         self.name = newName

      currDimStyleName = QadVariables.get(QadMsg.translate("Environment variables", "DIMSTYLE"))
      if oldName == currDimStyleName: # the style to be renamed is the current one
         QadVariables.set(QadMsg.translate("Environment variables", "DIMSTYLE"), newName)

      self.name = newName
      return True


   # ============================================================================
   # getInValidErrMsg
   # ============================================================================
   def getInValidErrMsg(self):
      """Checks whether the dimensioning style is invalid and returns the error message if so.
            If the dimensioning is valid, it returns None.
      """
      prefix = QadMsg.translate("Dimension", "\nThe dimension style \"{0}\" ").format(self.name)

      if self.getTextualLayer() is None:
         return prefix + QadMsg.translate("Dimension", "has not the textual layer for dimension.\n")
      if qad_layer.isTextLayer(self.getTextualLayer()) == False:
         errPartial = QadMsg.translate("Dimension", "has the textual layer for dimension ({0}) which is not a textual layer.")
         errMsg = prefix + errPartial.format(self.getTextualLayer().name())
         errMsg = errMsg + QadMsg.translate("QAD", "\nA textual layer is a vector punctual layer having a label and the symbol transparency no more than 10%.\n")
         return errMsg

      if self.getSymbolLayer() is None:
         return prefix + QadMsg.translate("Dimension", "has not the symbol layer for dimension.\n")
      if qad_layer.isSymbolLayer(self.getSymbolLayer()) == False:
         errPartial = QadMsg.translate("Dimension", "has the symbol layer for dimension ({0}) which is not a symbol layer.")
         errMsg = prefix + errPartial.format(self.getSymbolLayer().name())
         errMsg = errMsg + QadMsg.translate("QAD", "\nA symbol layer is a vector punctual layer without label.\n")
         return errMsg

      if self.getLinearLayer() is None:
         return prefix + QadMsg.translate("Dimension", "has not the linear layer for dimension.\n")
      # must be a line-type VectorLayer
      if (self.getLinearLayer().type() != QgsMapLayer.VectorLayer) or (self.getLinearLayer().geometryType() != QgsWkbTypes.LineGeometry):
         errPartial = QadMsg.translate("Dimension", "has the linear layer for dimension ({0}) which is not a linear layer.")
         errMsg = prefix + errPartial.format(self.getSymbolLayer().name())
         return errMsg
      # the layers must have the same coordinate system
      if not (self.getTextualLayer().crs() == self.getLinearLayer().crs() and self.getLinearLayer().crs() == self.getSymbolLayer().crs()):
         errMsg = prefix + QadMsg.translate("Dimension", "has not the layers with the same coordinate reference system.")
         return errMsg

      return None


   # ============================================================================
   # isValid
   # ============================================================================
   def isValid(self):
      """Checks whether the dimensioning style is valid and returns True if so.
            If the dimensioning is invalid, it returns False.
      """
      return True if self.getInValidErrMsg() is None else False


   # ===============================================================================
   # getNotGraphEditableErrMsg
   # ===============================================================================
   def getNotGraphEditableErrMsg(self):
      """Checks whether the dimensioning style layers are read-only and returns the error message if so.
            If the dimensioning style layers are editable, it returns None.
      """
      prefix = QadMsg.translate("Dimension", "\nThe dimension style \"{0}\" ").format(self.name)

      # text layer
      textualLayer = self.getTextualLayer()
      if textualLayer is None:
         errPartial = QadMsg.translate("Dimension", "hasn't the textual layer ({0}).")
         return prefix + errPartial.format(self.textualLayerName)

      provider = textualLayer.dataProvider()
      if not (provider.capabilities() & QgsVectorDataProvider.EditingCapabilities):
         errPartial = QadMsg.translate("Dimension", "has the textual layer ({0}) not editable.")
         return prefix + errPartial.format(self.textualLayerName)
      if not textualLayer.isEditable():
         errPartial = QadMsg.translate("Dimension", "has the textual layer ({0}) not editable.")
         return prefix + errPartial.format(self.textualLayerName)

      # symbol layer
      symbolLayer = self.getSymbolLayer()
      if symbolLayer is None:
         errPartial = QadMsg.translate("Dimension", "hasn't the symbol layer ({0}).")
         return prefix + errPartial.format(self.symbolLayerName)

      provider = symbolLayer.dataProvider()
      if not (provider.capabilities() & QgsVectorDataProvider.EditingCapabilities):
         errPartial = QadMsg.translate("Dimension", "has the symbol layer ({0}) not editable.")
         return prefix + errPartial.format(self.symbolLayerName)
      if not symbolLayer.isEditable():
         errPartial = QadMsg.translate("Dimension", "has the symbol layer ({0}) not editable.")
         return prefix + errPartial.format(self.symbolLayerName)

      # line layer
      linearLayer = self.getLinearLayer()
      if linearLayer is None:
         errPartial = QadMsg.translate("Dimension", "hasn't the symbol layer ({0}).")
         return prefix + errPartial.format(self.linearLayerName)

      provider = linearLayer.dataProvider()
      if not (provider.capabilities() & QgsVectorDataProvider.EditingCapabilities):
         errPartial = QadMsg.translate("Dimension", "has the linear layer ({0}) not editable.")
         return prefix + errPartial.format(self.linearLayerName)
      if not linearLayer.isEditable():
         errPartial = QadMsg.translate("Dimension", "has the linear layer ({0}) not editable.")
         return prefix + errPartial.format(self.linearLayerName)

      return None


   # ============================================================================
   # adjustLineAccordingTextRect
   # ============================================================================
   def adjustLineAccordingTextRect(self, textRect, line, textLinearDimComponentOn):
      """Given a line, what type of dimension component does it represent (textLinearDimComponentOn)
            and a rectangle representing the dimension text occupation (in the form of a QadPolyline),
            the function returns 2 lines (can be None) so that the text does not overlap the line and that the
            dimension settings are respected (dimLine1Show, dimLine2Show, extLine1Show, extLine2Show)
      """
      line1 = None
      line2 = None
      # Returns the points of intersection between the rectangle <textRect> (QadPolyline) representing the text
      # and a <line> segment. The list is sorted by distance from the starting point of the line.
      intPts = QadIntersections.getOrderedPolylineIntersectionPtsWithBasicGeom(textRect, line, True)[0] # orderByStartPtOfLinearObject = True
      if textLinearDimComponentOn == QadDimComponentEnum.DIM_LINE1: # dimension line ("Dimension line")
         if len(intPts) == 2: # the rectangle is on the line
            if self.dimLine1Show:
               line1 = QadLine().set(line.getStartPt(), intPts[0])
            if self.dimLine2Show:
               line2 = QadLine().set(intPts[1], line.getEndPt())
         else: # the rectangle is not on the line
            if self.dimLine1Show and self.dimLine2Show:
               line1 = line.copy()
            else:
               space1, space2 = self.getSpaceForBlock1AndBlock2OnLine(textRect, line)
               rot = qad_utils.getAngleBy2Pts(line.getStartPt(), line.getEndPt()) # angle of the dimension line
               intPt1 = qad_utils.getPolarPointByPtAngle(line.getStartPt(), rot, space1)
               intPt2 = qad_utils.getPolarPointByPtAngle(line.getEndPt(), rot - math.pi, space2)

               if self.dimLine1Show:
                  line1 = QadLine().set(line.getStartPt(), intPt2)
               elif self.dimLine2Show:
                  line2 = QadLine().set(line.getEndPt(), intPt1)
      elif textLinearDimComponentOn == QadDimComponentEnum.EXT_LINE1: # first extension line ("Extension line 1")
         if self.extLine1Show:
            if len(intPts) > 0:
               line1 = QadLine().set(line.getStartPt(), intPts[0])
            else:
               line1 = line.copy()
      elif textLinearDimComponentOn == QadDimComponentEnum.EXT_LINE2: # second extension line ("Extension line 2")
         if self.extLine2Show:
            if len(intPts) > 0:
               line1 = QadLine().set(line.getStartPt(), intPts[0])
            else:
               line1 = line.copy()
      elif textLinearDimComponentOn == QadDimComponentEnum.LEADER_LINE: # dimension line used when the text is outside the dimension ("Leader")
         if len(intPts) > 0:
            line1 = QadLine().set(line.getEndPt(), intPts[0])
         else:
            line1 = line.copy()

      return line1, line2


   # ============================================================================
   # adjustArcAccordingTextRect
   # ============================================================================
   def adjustArcAccordingTextRect(self, textRect, arc, textLinearDimComponentOn):
      """Given an arc (<arc>), what type of dimension component does it represent (textLinearDimComponentOn)
            and a rectangle representing the dimension text occupancy, the function returns
            two arcs (can be None) so that the text does not overlap the arc and that the
            dimension settings are respected (dimLine1Show, dimLine2Show, extLine1Show, extLine2Show)
      """
      intPts =  QadIntersections.getOrderedPolylineIntersectionPtsWithBasicGeom(textRect, arc, True)[0] # orderByStartPtOfPart = True
      arc1 = None
      arc2 = None

      if textLinearDimComponentOn == QadDimComponentEnum.DIM_LINE1: # dimension line ("Dimension line")
         if len(intPts) >= 2: # the rectangle is on the line
            if self.dimLine1Show:
               arc1 = QadArc(arc)
               arc1.setEndAngleByPt(intPts[0])
            if self.dimLine2Show:
               arc2 = QadArc(arc)
               arc2.setStartAngleByPt(intPts[-1])# last point
         else: # the rectangle is not on the line
            if self.dimLine1Show and self.dimLine2Show:
               arc1 = QadArc(arc)
            else:
               space1, space2 = self.getSpaceForBlock1AndBlock2OnArc(textRect, arc)

               if self.dimLine1Show:
                  arc1 = QadArc(arc)
                  pt, dummyTg = arc1.getPointFromStart(space1)
                  arc1.setEndAngleByPt(pt)
               elif self.dimLine2Show:
                  arc2 = QadArc(arc)
                  pt, dummyTg = arc2.getPointFromStart(arc2.length() - space2)
                  arc2.setStartAngleByPt(pt)
      elif textLinearDimComponentOn == QadDimComponentEnum.EXT_LINE1: # first extension line ("Extension line 1")
         if self.extLine1Show:
            if len(intPts) > 0:
               arc1 = QadArc(arc)
               arc1.setEndAngleByPt(intPts[0])
      elif textLinearDimComponentOn == QadDimComponentEnum.EXT_LINE2: # second extension line ("Extension line 2")
         if self.extLine2Show:
            if len(intPts) > 0:
               arc1 = QadArc(arc)
               arc1.setEndAngleByPt(intPts[0])
      elif textLinearDimComponentOn == QadDimComponentEnum.LEADER_LINE: # dimension line used when the text is outside the dimension ("Leader")
         if len(intPts) > 0:
            arc1 = QadArc(arc)
            arc1.setEndAngleByPt(intPts[0])

      return arc1, arc2


   # ============================================================================
   # setDimId
   # ============================================================================
   def setDimId(self, dimId, features, parentId = False):
      """Sets all features passed into the <features> list with the dimension code."""
      fieldName = self.idParentFieldName if parentId else self.idFieldName

      if len(fieldName) == 0:
         return True

      i = 0
      tot = len(features)
      while i < tot:
         try:
            f = features[i]
            if f is not None:
               # set the dimension code
               f.setAttribute(fieldName, dimId)
         except:
            return False
         i = i + 1
      return True


   # ============================================================================
   # recodeDimIdOnFeatures
   # ============================================================================
   def recodeDimIdOnFeatures(self, oldDimId, newDimId, features, parentId = False):
      """Searc for all features passed in the <features> list with the feature code
            quotes oldDimId and recodes them with newDimId.
      """
      fieldName = self.idParentFieldName if parentId else self.idFieldName

      if len(fieldName) == 0:
         return True

      i = 0
      tot = len(features)
      while i < tot:
         try:
            f = features[i]
            if f is not None:
               if f.attribute(fieldName) == oldDimId:
                  # set the dimension code
                  f.setAttribute(fieldName, newDimId)
         except:
            return False
         i = i + 1
      return True


   def textCommitChangesOnSave(self, plugIn):
      """Save dimension texts to get new IDs
            and call updateTextReferencesOnSave via the committedFeaturesAdded signal.
      """
      # save the texts to have the definitive encoding
      if self.getTextualLayer() is not None:
         # sign that this layer is saved by QAD
         plugIn.layerStatusList.setStatus(self.getTextualLayer().id(), qad_layer.QadLayerStatusEnum.COMMIT_BY_INTERNAL)
         res = self.getTextualLayer().commitChanges()
         if res == False:
            errors = self.getTextualLayer().commitErrors()
         plugIn.layerStatusList.remove(self.getTextualLayer().id())
         return res
      else:
         return False


   # ============================================================================
   # updateTextReferencesOnSave
   # ============================================================================
   def updateTextReferencesOnSave(self, plugIn, textAddedEntitySet):
      """Updates and saves the dimensioning style entity references contained in textAddedEntitySet."""
      if textAddedEntitySet.isEmpty() == True:
         return True
      if self.startEditing() == False:
         return False

      plugIn.beginEditCommand("Dimension recoded", [self.getSymbolLayer(), self.getLinearLayer(), self.getTextualLayer()])

      entity = QadEntity()
      entityIterator = textAddedEntitySet.getEntities()

      for entity in entityIterator:
         oldDimId = entity.getAttribute(self.idFieldName)
         newDimId = entity.getFeature().id()
         if oldDimId is None or self.recodeDimId(plugIn, oldDimId, newDimId) == False:
            return False

      plugIn.endEditCommand()

      return True


   # ============================================================================
   # startEditing
   # ============================================================================
   def startEditing(self):
      if self.getTextualLayer() is not None and self.getTextualLayer().isEditable() == False:
         if self.getTextualLayer().startEditing() == False:
            return False
      if self.getLinearLayer() is not None and self.getLinearLayer().isEditable() == False:
         if self.getLinearLayer().startEditing() == False:
            return False
      if self.getSymbolLayer() is not None and self.getSymbolLayer().isEditable() == False:
         if self.getSymbolLayer().startEditing() == False:
            return False


   # ============================================================================
   # commitChanges
   # ============================================================================
   def commitChanges(self, plugIn):
      if self.startEditing() == False:
         return False

      excludedLayer = plugIn.beforeCommitChangesDimLayer

      if (excludedLayer is None) or excludedLayer.id() != self.getTextualLayer().id():
         # sign that this layer is saved by QAD
         plugIn.layerStatusList.setStatus(self.getTextualLayer().id(), qad_layer.QadLayerStatusEnum.COMMIT_BY_INTERNAL)
         # except textual entities
         if self.getTextualLayer().commitChanges(False) == False: # By setting stopEditing to false, the layer will stay in editing mode.
            errors = self.getTextualLayer().commitErrors()
         plugIn.layerStatusList.remove(self.getTextualLayer().id())

      if (excludedLayer is None) or excludedLayer.id() != self.getLinearLayer().id():
         # sign that this layer is saved by QAD
         plugIn.layerStatusList.setStatus(self.getLinearLayer().id(), qad_layer.QadLayerStatusEnum.COMMIT_BY_INTERNAL)
         # except linear entities
         if self.getLinearLayer().commitChanges(False) == False: # By setting stopEditing to false, the layer will stay in editing mode.
            errors = self.getTextualLayer().commitErrors()
         plugIn.layerStatusList.remove(self.getLinearLayer().id())

      if (excludedLayer is None) or excludedLayer.id() != self.getSymbolLayer().id():
         # sign that this layer is saved by QAD
         plugIn.layerStatusList.setStatus(self.getSymbolLayer().id(), qad_layer.QadLayerStatusEnum.COMMIT_BY_INTERNAL)
         # except for punctual entities
         if self.getSymbolLayer().commitChanges(False) == False: # By setting stopEditing to false, the layer will stay in editing mode.
            errors = self.getTextualLayer().commitErrors()
         plugIn.layerStatusList.remove(self.getSymbolLayer().id())


   # ============================================================================
   # recodeDimId
   # ============================================================================
   def getEntitySet(self, dimId):
      """Obtain a QadEntitySet with all the features of the dimId dimension."""
      result = QadEntitySet()
      if len(self.idFieldName) == 0 or len(self.idParentFieldName) == 0:
         return result

      if self.isValid() == False: return result;

      layerEntitySet = QadLayerEntitySet()

      # I searc for the text entity
      expression = "\"" + self.idFieldName + "\"=" + str(dimId)
      featureIter = self.getTextualLayer().getFeatures(QgsFeatureRequest().setFilterExpression(expression))
      layerEntitySet.set(self.getTextualLayer())
      layerEntitySet.addFeatures(featureIter)
      result.addLayerEntitySet(layerEntitySet)

      expression = "\"" + self.idParentFieldName + "\"=" + str(dimId)

      # I searc for line entities
      layerEntitySet.clear()
      featureIter = self.getLinearLayer().getFeatures(QgsFeatureRequest().setFilterExpression(expression))
      layerEntitySet.set(self.getLinearLayer())
      layerEntitySet.addFeatures(featureIter)
      result.addLayerEntitySet(layerEntitySet)

      # I searc and set id_parent for point entities
      layerEntitySet.clear()
      featureIter = self.getSymbolLayer().getFeatures(QgsFeatureRequest().setFilterExpression(expression))
      layerEntitySet.set(self.getSymbolLayer())
      layerEntitySet.addFeatures(featureIter)
      result.addLayerEntitySet(layerEntitySet)

      return result


   # ============================================================================
   # recodeDimId
   # ============================================================================
   def recodeDimId(self, plugIn, oldDimId, newDimId):
      """Recode all the features of the oldDimId dimension with the new newDimId code."""
      if len(self.idFieldName) == 0 or len(self.idParentFieldName) == 0:
         return True

      entitySet = self.getEntitySet(oldDimId)

      # set the text entity
      layerEntitySet = entitySet.findLayerEntitySet(self.getTextualLayer())
      if layerEntitySet is not None:
         features = layerEntitySet.getFeatureCollection()
         if self.setDimId(newDimId, features, False) == False:
            return False
         # plugin, layer, features, refresh, check_validity
         if qad_layer.updateFeaturesToLayer(plugIn, self.getTextualLayer(), features, False, False) == False:
            return False

      # set id_parent for line entities
      layerEntitySet = entitySet.findLayerEntitySet(self.getLinearLayer())
      if layerEntitySet is not None:
         features = layerEntitySet.getFeatureCollection()
         if self.setDimId(newDimId, features, True) == False:
            return False
         # plugin, layer, features, refresh, check_validity
         if qad_layer.updateFeaturesToLayer(plugIn, self.getLinearLayer(), features, False, False) == False:
            return False

      # set id_parent for point entities
      layerEntitySet = entitySet.findLayerEntitySet(self.getSymbolLayer())
      if layerEntitySet is not None:
         features = layerEntitySet.getFeatureCollection()
         if self.setDimId(newDimId, features, True) == False:
            return False
         # plugin, layer, features, refresh, check_validity
         if qad_layer.updateFeaturesToLayer(plugIn, self.getSymbolLayer(), features, False, False) == False:
            return False

      return True


   # ============================================================================
   # addDimEntityToLayers
   # ============================================================================
   def addDimEntityToLayers(self, plugIn, dimEntity):
      """Adds a dimension entity to the relevant layers by recoding the components."""
      if dimEntity is None:
         return False

      plugIn.beginEditCommand("Dimension added", [self.getSymbolLayer(), self.getLinearLayer(), self.getTextualLayer()])

      # first of all insert the dimension text
      # plugin, layer, feature, coordTransform, refresh, check_validity
      if qad_layer.addFeatureToLayer(plugIn, self.getTextualLayer(), dimEntity.textualFeature, None, False, False, False) == False:
         plugIn.destroyEditCommand()
         return False

      dimId = dimEntity.textualFeature.id()

      if self.setDimId(dimId, [dimEntity.textualFeature], False) == True: # setto id
         # plugin, layer, feature, refresh, check_validity
         if qad_layer.updateFeatureToLayer(plugIn, self.getTextualLayer(), dimEntity.textualFeature, False, False) == False:
            plugIn.destroyEditCommand()
            return False

      # features puntuali
      self.setDimId(dimId, dimEntity.symbolFeatures, True) # setto id_parent
      # plugin, layer, features, coordTransform, refresh, check_validity
      if qad_layer.addFeaturesToLayer(plugIn, self.getSymbolLayer(), dimEntity.symbolFeatures, None, False, False) == False:
         plugIn.destroyEditCommand()
         return False

      # features lineari
      self.setDimId(dimId, dimEntity.linearFeatures, True) # setto id_parent
      # plugin, layer, features, coordTransform, refresh, check_validity
      if qad_layer.addFeaturesToLayer(plugIn, self.getLinearLayer(), dimEntity.linearFeatures, None, False, False) == False:
         plugIn.destroyEditCommand()
         return False

      plugIn.endEditCommand()

      return True


   # ============================================================================
   # getDimIdByEntity
   # ============================================================================
   def getDimIdByEntity(self, entity):
      """The function, given an entity, checks whether it is part of the dimensioning style and,
            if successful, returns the dimensioning code otherwise None.
            Additionally, the function sets the dimensioning type if possible.
      """
      if entity.layer.name() == self.textualLayerName:
         dimId = entity.getAttribute(self.idFieldName)
         if dimId is None:
            return None
         f = entity.getFeature()
      elif entity.layer.name() == self.linearLayerName or \
           entity.layer.name() == self.symbolLayerName:
         textualLayer = self.getTextualLayer()
         if textualLayer is None: return None

         dimId = entity.getAttribute(self.idParentFieldName)
         if dimId is None:
            return None
         # I searc for the text entity
         expression = "\"" + self.idFieldName + "\"=" + str(dimId)
         f = QgsFeature()
         if textualLayer.getFeatures(QgsFeatureRequest().setFilterExpression(expression)).nextFeature(f) == False:
            return None
      else:
         return None

      try:
         # I read the dimensioning style name
         dimName = f.attribute(self.dimStyleFieldName)
         if dimName != self.name:
            return None
      except:
         return None

      try:
         # I read the type of the dimensioning style
         self.dimType = f.attribute(self.dimTypeFieldName)
      except:
         pass

      return dimId


   # ============================================================================
   # isDimLayer
   # ============================================================================
   def isDimLayer(self, layer):
      """The function, given a layer, checks whether it is part of the dimensioning style."""
      if layer.name() == self.textualLayerName or \
         layer.name() == self.linearLayerName or \
         layer.name() == self.symbolLayerName:
         return True
      else:
         return False


   # ============================================================================
   # getFilteredLayerEntitySet
   # ============================================================================
   def getFilteredLayerEntitySet(self, layerEntitySet):
      """The function, given a QadLayerEntitySet, filters and returns only those belonging to the dimensioning style."""
      result = QadLayerEntitySet()
      entity = QadEntity()
      entityIterator = layerEntitySet.getEntities()

      for entity in entityIterator:
         if self.getDimIdByEntity(entity) is not None:
            result.addEntity(entity)

      return result




   # ============================================================================
   # BLOCK FUNCTIONS - START
   # ============================================================================


   # ============================================================================
   # getBlock1Size
   # ============================================================================
   def getBlock1Size(self):
      """Returns the size of block 1 of arrows in map units."""
      return 0 if self.block1Name == "" else self.blockWidth * self.blockScale


   # ============================================================================
   # getBlock2Size
   # ============================================================================
   def getBlock2Size(self):
      """Returns the block size 2 of arrows in map units."""
      # blockWidth = symbol width (horizontally) when size in map units = 1 (see "triangle2")
      # blockScale = scala della dimensione del simbolo (DIMASZ)
      return 0 if self.block2Name == "" else self.blockWidth * self.blockScale


   # ============================================================================
   # getBlocksRotOnLine
   # ============================================================================
   def getBlocksRotOnLine(self, dimLine, inside):
      """Returns a list of 2 elements describing the rotations of the two blocks:
            - the first element is the rotation of block 1
            - the second element is the rotation of block 2

            dimLine = dimension line
            inside = mode flag, if = true the arrows are internal otherwise they are external
      """
      rot = dimLine.getTanDirectionOnPt() # angle of the dimension line
      if inside:
         rot1 = rot + math.pi
         rot2 = rot
      else:
         rot1 = rot
         rot2 = rot + math.pi

      return qad_utils.normalizeAngle(rot1), qad_utils.normalizeAngle(rot2)


   # ============================================================================
   # getBlocksRotOnArc
   # ============================================================================
   def getBlocksRotOnArc(self, dimLineArc, inside):
      """Returns a list of 2 elements describing the rotations of the two blocks:
            - the first element is the rotation of block 1
            - the second element is the rotation of block 2

            dimLineArc = arc representing the dimension line (QadArc)
            inside = mode flag, if = true the arrows are internal otherwise they are external
      """
      rot1 = dimLineArc.getTanDirectionOnPt(dimLineArc.getStartPt()) # angle of the dimension line at the beginning of the arc
      rot2 = dimLineArc.getTanDirectionOnPt(dimLineArc.getEndPt()) # angle of the dimension line at the end of the arc
      if inside:
         rot1 = rot1 + math.pi
      else:
         rot2 = rot2 + math.pi

      return qad_utils.normalizeAngle(rot1), qad_utils.normalizeAngle(rot2)


   # ============================================================================
   # getSpaceForBlock1AndBlock2OnLine
   # ============================================================================
   def getSpaceForBlock1AndBlock2OnLineAuxiliary(self, dimLine, rectCorner):
      # calculate the projection of a vertex of the rectangle onto the dimLine
      perpPt = QadPerpendicularity.fromPointToInfinityLine(rectCorner, dimLine)
      # if the projection is not in the segment
      if dimLine.containsPt(perpPt) == False:
         # if the projection falls beyond the starting point of dimLine
         if qad_utils.getDistance(dimLine.getStartPt(), perpPt) < qad_utils.getDistance(dimLine.getEndPt(), perpPt):
            return 0, dimLine.length()
         else: # if the projection falls beyond the end point of dimLine
            return dimLine.length(), 0
      else:
         return qad_utils.getDistance(dimLine.getStartPt(), perpPt), qad_utils.getDistance(dimLine.getEndPt(), perpPt)

   def getSpaceForBlock1AndBlock2OnLine(self, txtRect, dimLine):
      """txtRect = text occupation rectangle (QadPolyline) or None if there is no text
            dimLine = dimension line
            Returns the space available for blocks 1 and 2 considering the rectangle (QadPolyline) representing the text
            and the dimension line dimLine.
      """
      if txtRect is None: # if there is no text (it has been moved outside the dimension line)
         spaceForBlock1 = dimLine.length() / 2
         spaceForBlock2 = spaceForBlock1
      else:
         # calculate the projection of the four vertices of the rectangle onto the dimLine
         linearObject = txtRect.getLinearObjectAt(0)
         partial1SpaceForBlock1, partial1SpaceForBlock2 = self.getSpaceForBlock1AndBlock2OnLineAuxiliary(dimLine, \
                                                                                                         linearObject.getStartPt())
         linearObject = txtRect.getLinearObjectAt(1)
         partial2SpaceForBlock1, partial2SpaceForBlock2 = self.getSpaceForBlock1AndBlock2OnLineAuxiliary(dimLine, \
                                                                                                         linearObject.getStartPt())
         spaceForBlock1 = partial1SpaceForBlock1 if partial1SpaceForBlock1 < partial2SpaceForBlock1 else partial2SpaceForBlock1
         spaceForBlock2 = partial1SpaceForBlock2 if partial1SpaceForBlock2 < partial2SpaceForBlock2 else partial2SpaceForBlock2

         linearObject = txtRect.getLinearObjectAt(2)
         partial3SpaceForBlock1, partial3SpaceForBlock2 = self.getSpaceForBlock1AndBlock2OnLineAuxiliary(dimLine, \
                                                                                                         linearObject.getStartPt())
         if partial3SpaceForBlock1 < spaceForBlock1:
            spaceForBlock1 = partial3SpaceForBlock1
         if partial3SpaceForBlock2 < spaceForBlock2:
            spaceForBlock2 = partial3SpaceForBlock2

         linearObject = txtRect.getLinearObjectAt(3)
         partial4SpaceForBlock1, partial4SpaceForBlock2 = self.getSpaceForBlock1AndBlock2OnLineAuxiliary(dimLine, \
                                                                                                         linearObject.getStartPt())
         if partial4SpaceForBlock1 < spaceForBlock1:
            spaceForBlock1 = partial4SpaceForBlock1
         if partial4SpaceForBlock2 < spaceForBlock2:
            spaceForBlock2 = partial4SpaceForBlock2

      return spaceForBlock1, spaceForBlock2


   # ============================================================================
   # getSpaceForBlock1AndBlock2OnArc
   # ============================================================================
   def getSpaceForBlock1AndBlock2OnArcAuxiliary(self, dimLineArc, rectCorner):
      # calculate the projection of a vertex of the rectangle onto the arc dimLineArc
      angle = qad_utils.getAngleBy2Pts(dimLineArc.center, rectCorner)
      perpPt = qad_utils.getPolarPointByPtAngle(dimLineArc.center, angle, dimLineArc.radius)
      startPt = dimLineArc.getStartPt()
      endPt = dimLineArc.getEndPt()
      # if the projection is not on the arc
      if dimLineArc.containsPt(perpPt) == False:
         # if the projection falls beyond the startPt point (I use strings)
         if qad_utils.getDistance(startPt, perpPt) < qad_utils.getDistance(endPt, perpPt):
            return 0, dimLineArc.length()
         else: # if the projection falls beyond the endPt point
            return dimLineArc.length(), 0
      else:
         arc1 = QadArc(dimLineArc)
         arc1.setEndAngleByPt(perpPt)
         arc2 = QadArc(dimLineArc)
         arc2.setStartAngleByPt(perpPt)
         return arc1.length(), arc2.length()

   def getSpaceForBlock1AndBlock2OnArc(self, txtRect, dimLineArc):
      """txtRect = text occupation rectangle or None if there is no text
            dimLineArc = arc representing the dimension line
            Returns the space available for blocks 1 and 2 considering the rectangle (QadPolyline) representing the text
            and the dimension line dimLineArc.
      """
      if txtRect is None: # if there is no text (it has been moved outside the dimension line)
         spaceForBlock1 = dimLineArc.length() / 2
         spaceForBlock2 = spaceForBlock1
      else:
         # text rectangle
         p1 = txtRect.getLinearObjectAt(0).getStartPt()
         p2 = txtRect.getLinearObjectAt(1).getStartPt()
         p3 = txtRect.getLinearObjectAt(2).getStartPt()
         p4 = txtRect.getLinearObjectAt(3).getStartPt()
         rect1 = QgsGeometry.fromPolygonXY([[p1, p2, p3, p4, p1]])
         # first block square
         pt = dimLineArc.getStartPt()
         lineRot = dimLineArc.getTanDirectionOnPt(pt)
         p1 = qad_utils.getPolarPointByPtAngle(pt, lineRot + math.pi / 2, self.getBlock1Size() / 2)
         p2 = qad_utils.getPolarPointByPtAngle(p1, lineRot, self.getBlock1Size())
         p3 = qad_utils.getPolarPointByPtAngle(p2, lineRot - math.pi / 2, self.getBlock1Size())
         p4 = qad_utils.getPolarPointByPtAngle(p3, lineRot, - self.getBlock1Size())
         rect2 = QgsGeometry.fromPolygonXY([[p1, p2, p3, p4, p1]])

         if rect1.intersects(rect2):
            spaceForBlock1 = 0
         else:
            spaceForBlock1 = dimLineArc.length() / 2

         # first block square
         pt = dimLineArc.getEndPt()
         lineRot = dimLineArc.getTanDirectionOnPt(pt) - 2 * math.pi
         p1 = qad_utils.getPolarPointByPtAngle(pt, lineRot + math.pi / 2, self.getBlock2Size() / 2)
         p2 = qad_utils.getPolarPointByPtAngle(p1, lineRot, self.getBlock2Size())
         p3 = qad_utils.getPolarPointByPtAngle(p2, lineRot - math.pi / 2, self.getBlock2Size())
         p4 = qad_utils.getPolarPointByPtAngle(p3, lineRot - 2 * math.pi, self.getBlock2Size())
         rect2 = QgsGeometry.fromPolygonXY([[p1, p2, p3, p4, p1]])

         if rect1.intersects(rect2):
            spaceForBlock2 = 0
         else:
            spaceForBlock2 = dimLineArc.length() / 2


#          # calculate the projection of the four vertices of the rectangle onto the line dimLinePt1, dimLinePt2
#          linearObject = txtRect.getLinearObjectAt(0)
#          partial1SpaceForBlock1, partial1SpaceForBlock2 = self.getSpaceForBlock1AndBlock2OnArcAuxiliary(dimLineArc, \
#                                                                                                         linearObject.getStartPt())
#          linearObject = txtRect.getLinearObjectAt(1)
#          partial2SpaceForBlock1, partial2SpaceForBlock2 = self.getSpaceForBlock1AndBlock2OnArcAuxiliary(dimLineArc, \
#                                                                                                         linearObject.getStartPt())
#          spaceForBlock1 = partial1SpaceForBlock1 if partial1SpaceForBlock1 < partial2SpaceForBlock1 else partial2SpaceForBlock1
#          spaceForBlock2 = partial1SpaceForBlock2 if partial1SpaceForBlock2 < partial2SpaceForBlock2 else partial2SpaceForBlock2
#
#          linearObject = txtRect.getLinearObjectAt(2)
#          partial3SpaceForBlock1, partial3SpaceForBlock2 = self.getSpaceForBlock1AndBlock2OnArcAuxiliary(dimLineArc, \
#                                                                                                         linearObject.getStartPt())
#          if partial3SpaceForBlock1 < spaceForBlock1:
#             spaceForBlock1 = partial3SpaceForBlock1
#          if partial3SpaceForBlock2 < spaceForBlock2:
#             spaceForBlock2 = partial3SpaceForBlock2
#
#          linearObject = txtRect.getLinearObjectAt(3)
#          partial4SpaceForBlock1, partial4SpaceForBlock2 = self.getSpaceForBlock1AndBlock2OnArcAuxiliary(dimLineArc, \
#                                                                                                         linearObject.getStartPt())
#          if partial4SpaceForBlock1 < spaceForBlock1:
#             spaceForBlock1 = partial4SpaceForBlock1
#          if partial4SpaceForBlock2 < spaceForBlock2:
#             spaceForBlock2 = partial4SpaceForBlock2

      return spaceForBlock1, spaceForBlock2


   # ============================================================================
   # getSymbolFeature
   # ============================================================================
   def getSymbolFeature(self, insPt, rot, isBlock1, textLinearDimComponentOn):
      """Returns the feature for the arrow symbol.
            insPt = insertion point
            rot = rotation expressed in radians
            isBlock1 = if True it is block1 otherwise block2
            textLinearDimComponentOn = indicates the component of the dimension where the dimension text is located (QadDimComponentEnum)
      """
      # if there is no dimension symbol
      if insPt is None or rot is None:
         return None
      # if it is symbol 1
      if isBlock1 == True:
         # if dimension line 1 should not be shown (valid only if the text is on the dimension line)
         if self.dimLine1Show == False and \
           (textLinearDimComponentOn == QadDimComponentEnum.DIM_LINE1 or textLinearDimComponentOn == QadDimComponentEnum.DIM_LINE2):
            return None
      else: # if it is symbol 2
         # if dimension line 2 is not to be shown (valid only if the text is on the dimension line)
         if self.dimLine2Show == False and \
           (textLinearDimComponentOn == QadDimComponentEnum.DIM_LINE1 or textLinearDimComponentOn == QadDimComponentEnum.DIM_LINE2):
            return None

      f = QgsFeature(self.getSymbolFeaturePrototype())
      g = fromQadGeomToQgsGeom(QadPoint().set(insPt), self.getSymbolLayer())
      f.setGeometry(g)

      # set the scale of the block
      try:
         if len(self.scaleFieldName) > 0:
            f.setAttribute(self.scaleFieldName, self.blockScale)
      except:
         pass

      # set the rotation
      try:
         if len(self.rotFieldName) > 0:
            f.setAttribute(self.rotFieldName, qad_utils.toDegrees(rot)) # Converte da radianti a gradi
      except:
         pass

      # set the color
      try:
         if len(self.colorFieldName) > 0:
            f.setAttribute(self.colorFieldName, self.dimLineColor)
      except:
         pass

      # set the dimensioning component type
      if self.dimType == QadDimTypeEnum.RADIUS: # if radius type dimensioning
         try:
            if len(self.componentFieldName) > 0:
               f.setAttribute(self.componentFieldName, QadDimComponentEnum.LEADER_BLOCK)
         except:
            pass

         try:
            if len(self.symbolFieldName) > 0:
               f.setAttribute(self.symbolFieldName, self.blockLeaderName)
         except:
            pass
      else:
         try:
            if len(self.componentFieldName) > 0:
               f.setAttribute(self.componentFieldName, QadDimComponentEnum.BLOCK1 if isBlock1 else QadDimComponentEnum.BLOCK2)
         except:
            pass

         try:
            if len(self.symbolFieldName) > 0:
               f.setAttribute(self.symbolFieldName, self.block1Name if isBlock1 else self.block2Name)
         except:
            pass

      return f


   # ============================================================================
   # getDimPointFeature
   # ============================================================================
   def getDimPointFeature(self, insPt, isDimPt1):
      """Returns the feature for the dimension point.
            insPt = insertion point
            isDimPt1 = if True it is dimension point 1 otherwise it is dimension point 2
      """
      symbolFeaturePrototype = self.getSymbolFeaturePrototype()
      if symbolFeaturePrototype is None:
         return None
      f = QgsFeature(symbolFeaturePrototype)
      g = fromQadGeomToQgsGeom(QadPoint().set(insPt), self.getSymbolLayer()) # I transform the geometry
      f.setGeometry(g)

      # set the dimensioning component type
      try:
         f.setAttribute(self.componentFieldName, QadDimComponentEnum.DIM_PT1 if isDimPt1 else QadDimComponentEnum.DIM_PT2)
      except:
         pass

      try:
         # set the color
         if len(self.colorFieldName) > 0:
            f.setAttribute(self.colorFieldName, self.dimLineColor)
      except:
         pass

      return f


   # ============================================================================
   # getLeaderSymbolFeature
   # ============================================================================
   def getLeaderSymbolFeature(self, insPt, rot):
      """Returns the arrow symbol feature for the leader line.
            insPt = insertion point
            rot = rotation expressed in radians
      """
      # if there is no dimension symbol
      if insPt is None or rot is None:
         return None

      f = QgsFeature(self.getSymbolFeaturePrototype())
      g = fromQadGeomToQgsGeom(QadPoint().set(insPt), self.getSymbolLayer()) # I transform the geometry
      f.setGeometry(g)

      # set the scale of the block
      try:
         if len(self.scaleFieldName) > 0:
            f.setAttribute(self.scaleFieldName, self.blockScale)
      except:
         pass

      # set the rotation
      try:
         if len(self.rotFieldName) > 0:
            f.setAttribute(self.rotFieldName, qad_utils.toDegrees(rot)) # Converte da radianti a gradi
      except:
         pass

      # set the color
      try:
         if len(self.colorFieldName) > 0:
            f.setAttribute(self.colorFieldName, self.dimLineColor)
      except:
         pass

      # set the dimensioning component type
      try:
         if len(self.componentFieldName) > 0:
            f.setAttribute(self.componentFieldName, QadDimComponentEnum.LEADER_BLOCK)
      except:
         pass

      try:
         if len(self.symbolFieldName) > 0:
            f.setAttribute(self.symbolFieldName, self.blockLeaderName)
      except:
         pass

      return f


   # ============================================================================
   # getArcSymbolLineFeature
   # ============================================================================
   def getArcSymbolLineFeature(self, arc):
      """Returns the feature for the arc symbol.
            arc = arc
      """
      # if there is no bow
      if arc is None:
         return None

      f = QgsFeature(self.getLinearFeaturePrototype())
      g = fromQadGeomToQgsGeom(arc, self.getLinearLayer()) # I transform the geometry
      f.setGeometry(g)

      try:
         # set the dimensioning component type
         if len(self.componentFieldName) > 0:
            f.setAttribute(self.componentFieldName, QadDimComponentEnum.ARC_BLOCK)
      except:
         pass

      try:
         # set the linetype
         if len(self.lineTypeFieldName) > 0:
            f.setAttribute(self.lineTypeFieldName, self.dimLineLineType)
      except:
         pass

      try:
         # set the color
         if len(self.colorFieldName) > 0:
            f.setAttribute(self.colorFieldName, self.dimLineColor)
      except:
         pass

      return f


   # ============================================================================
   # BLOCK FUNCTIONS - END
   # TEXT FUNCTIONS - START
   # ============================================================================


   # ============================================================================
   # getFormattedText
   # ============================================================================
   def getFormattedText(self, measure):
      """Returns the formatted dimension measurement text"""
      if type(measure) == int or type(measure) == float:
         return qad_utils.numToStringFmt(measure, self.textDecimals, self.textDecimalSep, \
                                         self.textSuppressLeadingZeros, self.textDecimalZerosSuppression, \
                                         self.textPrefix, self.textSuffix)
      elif type(measure) == unicode or type(measure) == str:
         return measure
      else:
         return ""


   # ============================================================================
   # getNumericText
   # ============================================================================
   def getNumericText(self, text):
      """Returns the numeric value of the formatted dimension measurement text"""
      textToConvert = text.lstrip(self.textPrefix)
      textToConvert = textToConvert.rstrip(self.textSuffix)
      textToConvert = textToConvert.replace(self.textDecimalSep, ".")

      return qad_utils.str2float(textToConvert)


   # ============================================================================
   # textRectToQadPolyline
   # ============================================================================
   def textRectToQadPolyline(self, ptBottomLeft, textWidth, textHeight, rot):
      """Returns the rectangle representing the text as a QadPolyline.
            <2>----width----<3>
             |               |
           height height
             |               |
            <1>----width----<4>
      """
      pt2 = qad_utils.getPolarPointByPtAngle(ptBottomLeft, rot + (math.pi / 2), textHeight)
      pt3 = qad_utils.getPolarPointByPtAngle(pt2, rot, textWidth)
      pt4 = qad_utils.getPolarPointByPtAngle(ptBottomLeft, rot , textWidth)
      res = QadPolyline()
      res.fromPolyline([ptBottomLeft, pt2, pt3, pt4, ptBottomLeft])
      return res


   # ============================================================================
   # getBoundingPointsTextRectProjectedToLine
   # ============================================================================
   def getBoundingPointsTextRectProjectedToLine(self, line, textRect):
      """Returns a list of 2 points which are the extreme points of the projection of the 4 corners of the rectangle
            on the <line> line.
      """
      rectCorners = textRect.asPolyline()
      # calculate the projection of the corners of the rectangle onto the line pt1-pt2
      perpPts = []

      p = QadPerpendicularity.fromPointToInfinityLine(rectCorners[0], line)
      qad_utils.appendUniquePointToList(perpPts, p)
      p = QadPerpendicularity.fromPointToInfinityLine(rectCorners[1], line)
      qad_utils.appendUniquePointToList(perpPts, p)
      p = QadPerpendicularity.fromPointToInfinityLine(rectCorners[2], line)
      qad_utils.appendUniquePointToList(perpPts, p)
      p = QadPerpendicularity.fromPointToInfinityLine(rectCorners[3], line)
      qad_utils.appendUniquePointToList(perpPts, p)

      return getBoundingPtsOnOnInfinityLine(perpPts)


   # ============================================================================
   # getTextPositionOnLine
   # ============================================================================
   def getTextPositionOnLine(self, pt1, pt2, textWidth, textHeight, horizontalPos, verticalPos, rotMode):
      """pt1 = first point of the line
            pt2 = second point of the line
            textWidth = text width
            textHeight = text height

            Returns the insertion point and rotation of the text along the pt1-pt2 line with the modes:
            horizontalPos = QadDimStyleTxtHorizontalPosEnum.CENTERED_LINE (centered at the line)
                            QadDimStyleTxtHorizontalPosEnum.FIRST_EXT_LINE (near point pt1)
                            QadDimStyleTxtHorizontalPosEnum.SECOND_EXT_LINE (near point pt2)
            verticalPos = QadDimStyleTxtVerticalPosEnum.CENTERED_LINE (centered at the line)
                          QadDimStyleTxtVerticalPosEnum.ABOVE_LINE (above the line)
                          QadDimStyleTxtVerticalPosEnum.BELOW_LINE (below the line)
            rotMode = QadDimStyleTxtRotModeEnum.HORIZONTAL (horizontal text)
                      QadDimStyleTxtRotModeEnum.ALIGNED_LINE (text aligned with the line)
                      QadDimStyleTxtRotModeEnum.FORCED_ROTATION (text with forced rotation)
      """
      lineRot = qad_utils.getAngleBy2Pts(pt1, pt2) # angle of the line

      if (lineRot > math.pi * 3 / 2 and lineRot <= math.pi * 2) or \
          (lineRot >= 0 and lineRot <= math.pi / 2): # da sx a dx
         textInsPtCloseToPt1 = True
      else: # da dx a sx
         textInsPtCloseToPt1 = False

      if rotMode == QadDimStyleTxtRotModeEnum.ALIGNED_LINE: # text aligned to the line
         if lineRot > (math.pi / 2) and lineRot <= math.pi * 3 / 2: # if the text is upside down I will rotate it
            textRot = lineRot - math.pi
         else:
            textRot = lineRot

         # allineamento orizzontale
         # =========================
         if horizontalPos == QadDimStyleTxtHorizontalPosEnum.CENTERED_LINE: # text centered on the line
            middlePt = qad_utils.getMiddlePoint(pt1, pt2)
            if textInsPtCloseToPt1: # the text insertion point is near pt1
               insPt = qad_utils.getPolarPointByPtAngle(middlePt, lineRot - math.pi, textWidth / 2)
            else: # the text insertion point is near pt2
               insPt = qad_utils.getPolarPointByPtAngle(middlePt, lineRot, textWidth / 2)

         elif horizontalPos == QadDimStyleTxtHorizontalPosEnum.FIRST_EXT_LINE: # text near pt1
            # I use textOffsetDist 2 times because once is the distance from the point pt1 + an offset around the text
            if textInsPtCloseToPt1: # the text insertion point is near pt1
               insPt = qad_utils.getPolarPointByPtAngle(pt1, lineRot, self.textOffsetDist + self.textOffsetDist)
            else: # the text insertion point is near pt2
               insPt = qad_utils.getPolarPointByPtAngle(pt1, lineRot, textWidth + self.textOffsetDist + self.textOffsetDist)

         elif horizontalPos == QadDimStyleTxtHorizontalPosEnum.SECOND_EXT_LINE: # text near pt2
            # I use textOffsetDist 2 times because once is the distance from the point pt1 + an offset around the text
            lineLen = qad_utils.getDistance(pt1, pt2)
            if textInsPtCloseToPt1: # the text insertion point is near pt1
               insPt = qad_utils.getPolarPointByPtAngle(pt1, lineRot, lineLen - textWidth - (self.textOffsetDist + self.textOffsetDist))
            else: # the text insertion point is near pt2
               insPt = qad_utils.getPolarPointByPtAngle(pt1, lineRot, lineLen - (self.textOffsetDist + self.textOffsetDist))

         # allineamento verticale
         # =========================
         if verticalPos == QadDimStyleTxtVerticalPosEnum.CENTERED_LINE: # text centered on the line
            if textInsPtCloseToPt1: # the text insertion point is near pt1
               insPt = qad_utils.getPolarPointByPtAngle(insPt, lineRot - math.pi / 2, textHeight / 2)
            else: # the text insertion point is near pt2
               insPt = qad_utils.getPolarPointByPtAngle(insPt, lineRot + math.pi / 2, textHeight / 2)
         elif verticalPos == QadDimStyleTxtVerticalPosEnum.ABOVE_LINE: # above the line
            # I use textOffsetDist 2 times because once is the distance from the line + an offset around the text
            if textInsPtCloseToPt1: # the text insertion point is near pt1
               insPt = qad_utils.getPolarPointByPtAngle(insPt, lineRot + math.pi / 2, self.textOffsetDist + self.textOffsetDist)
            else: # the text insertion point is near pt2
               insPt = qad_utils.getPolarPointByPtAngle(insPt, lineRot - math.pi / 2, self.textOffsetDist + self.textOffsetDist)
         elif verticalPos == QadDimStyleTxtVerticalPosEnum.BELOW_LINE: # below the line
            # I use textOffsetDist 2 times because once is the distance from the line + an offset around the text
            if textInsPtCloseToPt1: # the text insertion point is near pt1
               insPt = qad_utils.getPolarPointByPtAngle(insPt, lineRot - math.pi / 2, textHeight + (self.textOffsetDist + self.textOffsetDist))
            else: # the text insertion point is near pt2
               insPt = qad_utils.getPolarPointByPtAngle(insPt, lineRot + math.pi / 2, textHeight + (self.textOffsetDist + self.textOffsetDist))

      # horizontal text or text with forced rotation
      elif rotMode == QadDimStyleTxtRotModeEnum.HORIZONTAL or rotMode == QadDimStyleTxtRotModeEnum.FORCED_ROTATION:

         lineLen = qad_utils.getDistance(pt1, pt2) # line length
         textRot = 0.0 if rotMode == QadDimStyleTxtRotModeEnum.HORIZONTAL else self.textForcedRot

         # I look for the corner of the rectangle closest to the line
         #  <2>----width----<3>
         #   |               |
         # height          height
         #   |               |
         #  <1>----width----<4>
         # get the rectangle that encloses the text and position it with its lower left corner on the point pt1
         textRect = self.textRectToQadPolyline(pt1, textWidth, textHeight, textRot)
         # get the extreme points of the projection of the rectangle on the line
         pts = self.getBoundingPointsTextRectProjectedToLine(QadLine().set(pt1, pt2), textRect)
         projectedTextWidth = qad_utils.getDistance(pts[0], pts[1])

         # allineamento orizzontale
         # =========================
         if horizontalPos == QadDimStyleTxtHorizontalPosEnum.CENTERED_LINE: # text centered on the line
            closestPtToPt1 = qad_utils.getPolarPointByPtAngle(pt1, lineRot, (lineLen - projectedTextWidth) / 2)

         elif horizontalPos == QadDimStyleTxtHorizontalPosEnum.FIRST_EXT_LINE: # text near pt1
            closestPtToPt1 = qad_utils.getPolarPointByPtAngle(pt1, lineRot, self.textOffsetDist)

         elif horizontalPos == QadDimStyleTxtHorizontalPosEnum.SECOND_EXT_LINE: # text near pt2
            closestPtToPt1 = qad_utils.getPolarPointByPtAngle(pt1, lineRot, lineLen - self.textOffsetDist - projectedTextWidth)

         # if the line has an angle between (0-90] degrees (first quadrant)
         if lineRot > 0 and lineRot <= math.pi / 2:
            # the point closest to pt1 corresponds to the lower left corner of the rectangle that encloses the text
            # I get the insertion point of the text (bottom left corner)
            insPt = QgsPointXY(closestPtToPt1)
            textRect = self.textRectToQadPolyline(insPt, textWidth, textHeight, textRot)
            rectCorners = textRect.asPolyline()

            # allineamento verticale
            # =========================
            if verticalPos == QadDimStyleTxtVerticalPosEnum.ABOVE_LINE: # above the line
               # angle 4 must be above the line away from self.textOffsetDist
               rectPt = rectCorners[3]
            elif verticalPos == QadDimStyleTxtVerticalPosEnum.BELOW_LINE: # below the line
               # angle 2 must be under the line away from self.textOffsetDist
               rectPt = rectCorners[1]

         # if the line has an angle between (90-180] degrees (second quadrant)
         elif lineRot > math.pi / 2 and lineRot <= math.pi:
            # the point closest to pt1 corresponds to the lower right corner of the rectangle that encloses the text
            # I get the insertion point of the text (bottom left corner)
            insPt = QgsPointXY(closestPtToPt1.x() - textWidth, closestPtToPt1.y())
            textRect = self.textRectToQadPolyline(insPt, textWidth, textHeight, textRot)
            rectCorners = textRect.asPolyline()

            # allineamento verticale
            # =========================
            if verticalPos == QadDimStyleTxtVerticalPosEnum.ABOVE_LINE: # above the line
               # angle 1 must be above the line away from self.textOffsetDist
               rectPt = rectCorners[0]
            elif verticalPos == QadDimStyleTxtVerticalPosEnum.BELOW_LINE: # below the line
               # angle 3 must be under the line away from self.textOffsetDist
               rectPt = rectCorners[2]

         # if the line has an angle between (180-270] degrees (third quadrant)
         elif lineRot > math.pi and lineRot <= math.pi * 3 / 2:
            # the point closest to pt1 corresponds to the top right corner of the rectangle that encloses the text
            # I get the insertion point of the text (bottom left corner)
            insPt = QgsPointXY(closestPtToPt1.x() - textWidth, closestPtToPt1.y() - textHeight)
            textRect = self.textRectToQadPolyline(insPt, textWidth, textHeight, textRot)
            rectCorners = textRect.asPolyline()

            # allineamento verticale
            # =========================
            if verticalPos == QadDimStyleTxtVerticalPosEnum.ABOVE_LINE: # above the line
               # angle 4 must be above the line away from self.textOffsetDist
               rectPt = rectCorners[3]
            elif verticalPos == QadDimStyleTxtVerticalPosEnum.BELOW_LINE: # below the line
               # angle 2 must be under the line away from self.textOffsetDist
               rectPt = rectCorners[1]

         # if the line has an angle between (270-360] degrees (fourth quadrant)
         elif (lineRot > math.pi * 3 / 2 and lineRot <= 360) or lineRot == 0:
            # the point closest to pt1 corresponds to the top right corner of the rectangle that encloses the text
            # I get the insertion point of the text (top left corner)
            insPt = QgsPointXY(closestPtToPt1.x(), closestPtToPt1.y() - textHeight)
            textRect = self.textRectToQadPolyline(insPt, textWidth, textHeight, textRot)
            rectCorners = textRect.asPolyline()

            # allineamento verticale
            # =========================
            if verticalPos == QadDimStyleTxtVerticalPosEnum.ABOVE_LINE: # above the line
               # angle 1 must be above the line away from self.textOffsetDist
               rectPt = rectCorners[0]
            elif verticalPos == QadDimStyleTxtVerticalPosEnum.BELOW_LINE: # below the line
               # angle 3 must be under the line away from self.textOffsetDist
               rectPt = rectCorners[2]

         # allineamento verticale
         # =========================
         if verticalPos == QadDimStyleTxtVerticalPosEnum.CENTERED_LINE: # text centered on the line
            # the center of the rectangle must be on the line
            centerPt = qad_utils.getPolarPointByPtAngle(rectCorners[0], \
                                                        qad_utils.getAngleBy2Pts(rectCorners[0], rectCorners[2]), \
                                                        qad_utils.getDistance(rectCorners[0], rectCorners[2]) / 2)
            perpPt = qad_utils.getPerpendicularPointOnInfinityLine(pt1, pt2, centerPt)
            offsetAngle = qad_utils.getAngleBy2Pts(centerPt, perpPt)
            offsetDist = qad_utils.getDistance(centerPt, perpPt)
         elif verticalPos == QadDimStyleTxtVerticalPosEnum.ABOVE_LINE: # above the line
            # the angle must be above the line away from self.textOffsetDist
            perpPt = qad_utils.getPerpendicularPointOnInfinityLine(pt1, pt2, rectPt)
            # if the line has an angle between (90-270] degrees
            if lineRot > math.pi / 2 and lineRot <= math.pi * 3 / 2:
               offsetAngle = lineRot - math.pi / 2
            else: # if the line has an angle between (270-90] degrees
               offsetAngle = lineRot + math.pi / 2
            offsetDist = qad_utils.getDistance(rectPt, perpPt) + self.textOffsetDist
         elif verticalPos == QadDimStyleTxtVerticalPosEnum.BELOW_LINE: # below the line
            # the angle must be below the line away from self.textOffsetDist
            perpPt = qad_utils.getPerpendicularPointOnInfinityLine(pt1, pt2, rectPt)
            # if the line has an angle between (90-270] degrees
            if lineRot > math.pi / 2 and lineRot <= math.pi * 3 / 2:
               offsetAngle = lineRot + math.pi / 2
            else: # if the line has an angle between (270-90] degrees
               offsetAngle = lineRot - math.pi / 2
            offsetDist = qad_utils.getDistance(rectPt, perpPt) + self.textOffsetDist

         # I translate the rectangle
         insPt = qad_utils.getPolarPointByPtAngle(insPt, offsetAngle, offsetDist)
         textRect = self.textRectToQadPolyline(insPt, textWidth, textHeight, textRot)

      return insPt, textRot


   # ============================================================================
   # getTextPositionOnArc
   # ============================================================================
   def getTextPositionOnArc(self, arc, textWidth, textHeight, horizontalPos, verticalPos, rotMode):
      """arc = QadArc object
            textWidth = text width including offset (2 times offset, in front and behind the text)
            textHeight = text height including offset (2 times offset, above and below the text)

            Returns the insertion point and rotation of the text along the arc <arc> as follows:
            horizontalPos = QadDimStyleTxtHorizontalPosEnum.CENTERED_LINE (centered at the line)
                            QadDimStyleTxtHorizontalPosEnum.FIRST_EXT_LINE (near point pt1)
                            QadDimStyleTxtHorizontalPosEnum.SECOND_EXT_LINE (near point pt2)
            verticalPos = QadDimStyleTxtVerticalPosEnum.CENTERED_LINE (centered at the line)
                          QadDimStyleTxtVerticalPosEnum.ABOVE_LINE (above the line)
                          QadDimStyleTxtVerticalPosEnum.BELOW_LINE (below the line)
            rotMode = QadDimStyleTxtRotModeEnum.HORIZONTAL (horizontal text)
                      QadDimStyleTxtRotModeEnum.ALIGNED_LINE (text aligned with the line)
                      QadDimStyleTxtRotModeEnum.FORCED_ROTATION (text with forced rotation)
      """
      arcLength = arc.length()

      # calculate the development of the length of the text (with offsets) on the arc (the text is a straight line)
      myArc = QadArc()
      if myArc.fromStartCenterPtsChord(arc.getStartPt(), arc.center, textWidth):
         TextWidthOnArc = myArc.length()
      else:
         TextWidthOnArc = textWidth
      # calculate the development of the length of the offset on the arc (the text is a straight line)
      if myArc.fromStartCenterPtsChord(arc.getStartPt(), arc.center, self.textOffsetDist):
         textOffsetDistOnArc = myArc.length()
      else:
         textOffsetDistOnArc = self.textOffsetDist

      if rotMode == QadDimStyleTxtRotModeEnum.HORIZONTAL: # horizontal text
         textRot = 0.0
      elif rotMode == QadDimStyleTxtRotModeEnum.FORCED_ROTATION: # text with forced rotation
         textRot = self.textForcedRot


      # allineamento orizzontale
      # =========================
      if horizontalPos == QadDimStyleTxtHorizontalPosEnum.CENTERED_LINE: # text centered on the line
         insPtCenterTxt = arc.getMiddlePt()
         lineRot = arc.getTanDirectionOnPt(insPtCenterTxt)

         if rotMode == QadDimStyleTxtRotModeEnum.ALIGNED_LINE: # text aligned to the line
            textRot = lineRot
            if textRot > (math.pi / 2) and textRot <= math.pi * 3 / 2: # if the text is upside down I will rotate it
               textRot = textRot - math.pi


      elif horizontalPos == QadDimStyleTxtHorizontalPosEnum.FIRST_EXT_LINE: # text near pt1
         # I use textOffsetDist 2 times because once is the distance from the point pt1 + an offset around the text
         insPtCenterTxt, dummyTg = arc.getPointFromStart(textOffsetDistOnArc + textOffsetDistOnArc + TextWidthOnArc / 2)

         lineRot = arc.getTanDirectionOnPt(insPtCenterTxt)

         if rotMode == QadDimStyleTxtRotModeEnum.ALIGNED_LINE: # text aligned to the line
            textRot = lineRot
            if textRot > (math.pi / 2) and textRot <= math.pi * 3 / 2: # if the text is upside down I will rotate it
               textRot = textRot - math.pi


      elif horizontalPos == QadDimStyleTxtHorizontalPosEnum.SECOND_EXT_LINE: # text near pt2
         # I use textOffsetDist 2 times because once is the distance from the point pt1 + an offset around the text
         insPtCenterTxt, dummyTg = arc.getPointFromStart(arcLength - TextWidthOnArc / 2 - textOffsetDistOnArc - textOffsetDistOnArc)
         lineRot = arc.getTanDirectionOnPt(insPtCenterTxt)

         if rotMode == QadDimStyleTxtRotModeEnum.ALIGNED_LINE: # text aligned to the line
            textRot = lineRot
            if textRot > (math.pi / 2) and textRot <= math.pi * 3 / 2: # if the text is upside down I will rotate it
               textRot = textRot - math.pi

      # angle of the line that joins the center of the arc with the center of the text
      angleOnCenterTxt = qad_utils.getAngleBy2Pts(arc.center, insPtCenterTxt)
      # I normalize the angle
      textRot = qad_utils.normalizeAngle(textRot)
      if (textRot > math.pi * 3 / 2 and textRot <= math.pi * 2) or \
         (textRot >= 0 and textRot < math.pi / 2): # da sx a dx
         insPt = qad_utils.getPolarPointByPtAngle(insPtCenterTxt, textRot, -textWidth / 2)
      else:
         insPt = qad_utils.getPolarPointByPtAngle(insPtCenterTxt, textRot, textWidth / 2)


      # allineamento verticale
      # =========================
      angleOnCenterTxt = qad_utils.getAngleBy2Pts(arc.center, insPtCenterTxt)

      if verticalPos == QadDimStyleTxtVerticalPosEnum.CENTERED_LINE: # text centered on the line
         if textRot > (math.pi / 2) and textRot <= math.pi * 3 / 2: # if the text is upside down
            if (angleOnCenterTxt > 0 and angleOnCenterTxt <= math.pi): # the text moves towards the final point of the arc
               insPt = qad_utils.getPolarPointByPtAngle(insPt, angleOnCenterTxt, textHeight / 2)
            else: # the text goes towards the starting point of the arc
               insPt = qad_utils.getPolarPointByPtAngle(insPt, angleOnCenterTxt, -textHeight / 2)
         else: # the text is straight
            if (angleOnCenterTxt > 0 and angleOnCenterTxt <= math.pi): # the text goes towards the starting point of the arc
               insPt = qad_utils.getPolarPointByPtAngle(insPt, angleOnCenterTxt, -textHeight / 2)
            else: # the text moves towards the final point of the arc
               insPt = qad_utils.getPolarPointByPtAngle(insPt, angleOnCenterTxt, textHeight / 2)


      elif verticalPos == QadDimStyleTxtVerticalPosEnum.ABOVE_LINE: # above the line
         if textRot > (math.pi / 2) and textRot <= math.pi * 3 / 2: # if the text is upside down
            if (angleOnCenterTxt > 0 and angleOnCenterTxt <= math.pi): # the text moves towards the final point of the arc
               insPt = qad_utils.getPolarPointByPtAngle(insPt, angleOnCenterTxt, -self.textOffsetDist)
            else: # the text goes towards the starting point of the arc
               insPt = qad_utils.getPolarPointByPtAngle(insPt, angleOnCenterTxt, self.textOffsetDist)
         else: # the text is straight
            if (angleOnCenterTxt > 0 and angleOnCenterTxt <= math.pi): # the text goes towards the starting point of the arc
               insPt = qad_utils.getPolarPointByPtAngle(insPt, angleOnCenterTxt, self.textOffsetDist)
            else: # the text moves towards the final point of the arc
               insPt = qad_utils.getPolarPointByPtAngle(insPt, angleOnCenterTxt, -self.textOffsetDist)


      elif verticalPos == QadDimStyleTxtVerticalPosEnum.BELOW_LINE: # below the line
         if textRot > (math.pi / 2) and textRot <= math.pi * 3 / 2: # if the text is upside down
            if (angleOnCenterTxt > 0 and angleOnCenterTxt <= math.pi): # the text moves towards the final point of the arc
               insPt = qad_utils.getPolarPointByPtAngle(insPt, angleOnCenterTxt, (textHeight + self.textOffsetDist))
            else: # the text goes towards the starting point of the arc
               insPt = qad_utils.getPolarPointByPtAngle(insPt, angleOnCenterTxt, -(textHeight + self.textOffsetDist))
         else: # the text is straight
            if (angleOnCenterTxt > 0 and angleOnCenterTxt <= math.pi): # the text goes towards the starting point of the arc
               insPt = qad_utils.getPolarPointByPtAngle(insPt, angleOnCenterTxt, -(textHeight + self.textOffsetDist))
            else: # the text moves towards the final point of the arc
               insPt = qad_utils.getPolarPointByPtAngle(insPt, angleOnCenterTxt, (textHeight + self.textOffsetDist))


      return insPt, textRot


   # ============================================================================
   # getTextPosAndLinesOutOfDimLines
   # ============================================================================
   def getTextPosAndLinesOutOfDimLines(self, dimLinePt1, dimLinePt2, textWidth, textHeight):
      """Returns a list of 3 items if text is moved outside the lines
            of extension because it was too big:
            - the first element is the insertion point
            - the second element is the rotation of the text
            - the third element is a list of lines to use as dimension holders

            The function positions it next to the extension line 2.
            dimLinePt1 = first point of the dimension line (QgsPointXY)
            dimLinePt2 = second point of the dimension line (QgsPointXY)
            textWidth = text width
            textHeight = text height
      """
      # I get the dimension carrying lines for the external text
      lines = self.getLeaderLinesOnLine(dimLinePt1, dimLinePt2, textWidth, textHeight)
      # I consider the last one to be the one that refers to the text
      line = lines.getLinearObjectAt(-1)

      if self.textRotMode == QadDimStyleTxtRotModeEnum.FORCED_ROTATION:
         textRotMode = QadDimStyleTxtRotModeEnum.FORCED_ROTATION
      else:
         textRotMode = QadDimStyleTxtRotModeEnum.ALIGNED_LINE

      textInsPt, textRot = self.getTextPositionOnLine(line.getStartPt(), line.getEndPt(), textWidth, textHeight, \
                                                      QadDimStyleTxtHorizontalPosEnum.FIRST_EXT_LINE, \
                                                      self.textVerticalPos, textRotMode)
      return textInsPt, textRot, lines


   # ============================================================================
   # getTextPosAndLinesOutOfDimArc
   # ============================================================================
   def getTextPosAndLinesOutOfDimArc(self, dimLineArc, textWidth, textHeight):
      """Returns a list of 3 items if text is moved outside the lines
            of extension because it was too big:
            - the first element is the insertion point of the text
            - the second element is the rotation of the text
            - the third element is a list of lines to use as dimension holders

            The function positions it next to the extension line 2.
            getTextPosAndLinesOutOfDimArc = arc representing the dimension line (QadArc)
            textWidth = text width
            textHeight = text height
      """
      # I get the dimension carrying lines for the external text
      lines = self.getLeaderLinesOnArc(dimLineArc, textWidth, textHeight)
      # I consider the last one to be the one that refers to the text
      line = lines.getLinearObjectAt(-1)

      if self.textRotMode == QadDimStyleTxtRotModeEnum.FORCED_ROTATION:
         textRotMode = QadDimStyleTxtRotModeEnum.FORCED_ROTATION
      else:
         textRotMode = QadDimStyleTxtRotModeEnum.ALIGNED_LINE

      textInsPt, textRot = self.getTextPositionOnLine(line.getStartPt(), line.getEndPt(), textWidth, textHeight, \
                                                      QadDimStyleTxtHorizontalPosEnum.FIRST_EXT_LINE, \
                                                      self.textVerticalPos, textRotMode)
      return textInsPt, textRot, lines


   # ============================================================================
   # getLinearTextAndBlocksPosition
   # ============================================================================
   def getLinearTextAndBlocksPosition(self, dimPt1, dimPt2, dimLine, textWidth, textHeight):
      """dimPt1 = first point to dimension
            dimPt2 = second point to dimension
            dimLine = dimension line (QadLine)
            textWidth = text width
            textHeight = text height

            Returns a list of 4 items:
            - the first element is a list with the insertion point of the dimension text and its rotation
            - the second element is a list with flag indicating the type of the line on which the text was placed; see QadDimComponentEnum
                                  and a list of "leader" lines in case the text is outside the dimension
            - the third element is the rotation of the first block of arrows; can be None if not visible
            - the fourth element is the rotation of the second block of arrows; can be None if not visible
      """
      textInsPt                = None # text insertion point
      textRot                  = None # text rotation
      textLinearDimComponentOn = None # code of the linear component on which the text is positioned
      txtLeaderLines           = None # list of "leader" lines in case the text is outside the dimension
      block1Rot                = None # rotation of the first arrow block
      block2Rot                = None # rotation of the second arrow block

      # if the text is between the dimension extension lines
      if self.textHorizontalPos == QadDimStyleTxtHorizontalPosEnum.CENTERED_LINE or \
         self.textHorizontalPos == QadDimStyleTxtHorizontalPosEnum.FIRST_EXT_LINE or \
         self.textHorizontalPos == QadDimStyleTxtHorizontalPosEnum.SECOND_EXT_LINE:

         dimLineRot = qad_utils.getAngleBy2Pts(dimLine.getStartPt(), dimLine.getEndPt()) # angle of the dimension line

         # change the ends of the dimension line to consider the space occupied by the blocks
         dimLinePt1Offset = qad_utils.getPolarPointByPtAngle(dimLine.getStartPt(), dimLineRot, self.getBlock1Size())
         dimLinePt2Offset = qad_utils.getPolarPointByPtAngle(dimLine.getEndPt(), dimLineRot + math.pi, self.getBlock2Size())

         # text above or below the dimension line if the dimension line is not horizontal
         # and the text is inside the extension lines and forced horizontal then the text becomes centered
         if (self.textVerticalPos == QadDimStyleTxtVerticalPosEnum.ABOVE_LINE or self.textVerticalPos == QadDimStyleTxtVerticalPosEnum.BELOW_LINE) and \
            (dimLineRot != 0 and dimLineRot != math.pi) and self.textRotMode == QadDimStyleTxtRotModeEnum.HORIZONTAL:
            textVerticalPos = QadDimStyleTxtVerticalPosEnum.CENTERED_LINE
         # text positioned opposite the dimension points
         elif self.textVerticalPos == QadDimStyleTxtVerticalPosEnum.EXTERN_LINE:
            # angle from the first dimension point to the first point of the dimension line
            dimPtToDimLinePt_rot = qad_utils.getAngleBy2Pts(dimPt1, dimLine.getStartPt())
            if dimPtToDimLinePt_rot > 0 and \
               (dimPtToDimLinePt_rot < math.pi or qad_utils.doubleNear(dimPtToDimLinePt_rot,  math.pi)):
               textVerticalPos = QadDimStyleTxtVerticalPosEnum.ABOVE_LINE
            else:
               textVerticalPos = QadDimStyleTxtVerticalPosEnum.BELOW_LINE
         else:
            textVerticalPos = self.textVerticalPos

         if self.textRotMode == QadDimStyleTxtRotModeEnum.ISO:
            textInsPt, textRot = self.getTextPositionOnLine(dimLinePt1Offset, dimLinePt2Offset, textWidth, textHeight, \
                                                            self.textHorizontalPos, textVerticalPos, QadDimStyleTxtRotModeEnum.ALIGNED_LINE)
         else:
            textInsPt, textRot = self.getTextPositionOnLine(dimLinePt1Offset, dimLinePt2Offset, textWidth, textHeight, \
                                                            self.textHorizontalPos, textVerticalPos, self.textRotMode)

         rect = self.textRectToQadPolyline(textInsPt, textWidth, textHeight, textRot)
         spaceForBlock1, spaceForBlock2 = self.getSpaceForBlock1AndBlock2OnLine(rect, dimLine)

         # if there is not enough space to insert text and symbols inside the extension lines,
         # use qad_utils.doubleSmaller because sometimes the two numbers are almost equal
         if spaceForBlock1 == 0 or spaceForBlock2 == 0 or \
            qad_utils.doubleSmaller(spaceForBlock1, self.getBlock1Size() + self.textOffsetDist) or \
            qad_utils.doubleSmaller(spaceForBlock2, self.getBlock2Size() + self.textOffsetDist):
            if self.blockSuppressionForNoSpace: # suppresses symbols if there is not enough space inside the extension lines
               block1Rot = None
               block2Rot = None

               # I consider the text without arrows
               if self.textRotMode == QadDimStyleTxtRotModeEnum.ISO:
                  textInsPt, textRot = self.getTextPositionOnLine(dimLine.getStartPt(), dimLine.getEndPt(), textWidth, textHeight, \
                                                                  self.textHorizontalPos, textVerticalPos, QadDimStyleTxtRotModeEnum.ALIGNED_LINE)
               else:
                  textInsPt, textRot = self.getTextPositionOnLine(dimLine.getStartPt(), dimLine.getEndPt(), textWidth, textHeight, \
                                                                  self.textHorizontalPos, textVerticalPos, self.textRotMode)

               rect = self.textRectToQadPolyline(textInsPt, textWidth, textHeight, textRot)
               spaceForBlock1, spaceForBlock2 = self.getSpaceForBlock1AndBlock2OnLine(rect, dimLine)
               # if there is no room even for the text without the arrows
               if spaceForBlock1 == 0 or spaceForBlock2 == 0 or \
                  spaceForBlock1 < self.textOffsetDist or spaceForBlock2 < self.textOffsetDist:
                  # moves text outside extension lines
                  textInsPt, textRot, txtLeaderLines = self.getTextPosAndLinesOutOfDimLines(dimLine.getStartPt(), dimLine.getEndPt(), \
                                                                                            textWidth, textHeight)
                  textLinearDimComponentOn = QadDimComponentEnum.LEADER_LINE
               else:
                  textLinearDimComponentOn = QadDimComponentEnum.DIM_LINE1
            else: # non devo sopprimere i simboli
               # the first thing to move outside is:
               if self.textBlockAdjust == QadDimStyleTextBlocksAdjustEnum.BOTH_OUTSIDE_EXT_LINES:
                  # moves text and arrows outside extension lines
                  textInsPt, textRot, txtLeaderLines = self.getTextPosAndLinesOutOfDimLines(dimLine.getStartPt(), dimLine.getEndPt(), \
                                                                                            textWidth, textHeight)
                  textLinearDimComponentOn = QadDimComponentEnum.LEADER_LINE
                  block1Rot, block2Rot = self.getBlocksRotOnLine(dimLine, False) # frecce esterne
               # first move the arrows then, if that's not enough, also the text
               elif self.textBlockAdjust == QadDimStyleTextBlocksAdjustEnum.FIRST_BLOCKS_THEN_TEXT:
                  block1Rot, block2Rot = self.getBlocksRotOnLine(dimLine, False) # frecce esterne
                  # I consider the text without arrows
                  if self.textRotMode == QadDimStyleTxtRotModeEnum.ISO:
                     textInsPt, textRot = self.getTextPositionOnLine(dimLine.getStartPt(), dimLine.getEndPt(), \
                                                                     textWidth, textHeight, \
                                                                     self.textHorizontalPos, textVerticalPos, QadDimStyleTxtRotModeEnum.ALIGNED_LINE)
                  else:
                     textInsPt, textRot = self.getTextPositionOnLine(dimLine.getStartPt(), dimLine.getEndPt(), \
                                                                     textWidth, textHeight, \
                                                                     self.textHorizontalPos, textVerticalPos, self.textRotMode)

                  rect = self.textRectToQadPolyline(textInsPt, textWidth, textHeight, textRot)
                  spaceForBlock1, spaceForBlock2 = self.getSpaceForBlock1AndBlock2OnLine(rect, dimLine)
                  # if there is no room even for the text without the arrows
                  if spaceForBlock1 == 0 or spaceForBlock2 == 0 or \
                     spaceForBlock1 < self.textOffsetDist or spaceForBlock2 < self.textOffsetDist:
                     # moves text outside extension lines
                     textInsPt, textRot, txtLeaderLines = self.getTextPosAndLinesOutOfDimLines(dimLine.getStartPt(), dimLine.getEndPt(), \
                                                                                               textWidth, textHeight)
                     textLinearDimComponentOn = QadDimComponentEnum.LEADER_LINE
                  else:
                     textLinearDimComponentOn = QadDimComponentEnum.DIM_LINE1
               # first move the text and then, if that's not enough, also the arrows
               elif self.textBlockAdjust == QadDimStyleTextBlocksAdjustEnum.FIRST_TEXT_THEN_BLOCKS:
                  # I move the text outside the extension lines
                  textInsPt, textRot, txtLeaderLines = self.getTextPosAndLinesOutOfDimLines(dimLine.getStartPt(), dimLine.getEndPt(), \
                                                                                            textWidth, textHeight)
                  textLinearDimComponentOn = QadDimComponentEnum.LEADER_LINE
                  # if the arrows don't even fit
                  if dimLine.length() <= self.getBlock1Size() + self.getBlock2Size():
                     block1Rot, block2Rot = self.getBlocksRotOnLine(dimLine, False) # frecce esterne
                  else:
                     block1Rot, block2Rot = self.getBlocksRotOnLine(dimLine, True) # frecce interne
               # Move text or arrows indiscriminately (the object that fits best)
               elif self.textBlockAdjust == QadDimStyleTextBlocksAdjustEnum.WHICHEVER_FITS_BEST:
                  # I move the bulkiest one
                  if self.getBlock1Size() + self.getBlock2Size() > textWidth: # arrows are bulkier than text
                     textLinearDimComponentOn = QadDimComponentEnum.DIM_LINE1
                     block1Rot, block2Rot = self.getBlocksRotOnLine(dimLine, False) # frecce esterne

                     # I consider the text without arrows
                     if self.textRotMode == QadDimStyleTxtRotModeEnum.ISO:
                        textInsPt, textRot = self.getTextPositionOnLine(dimLine.getStartPt(), dimLine.getEndPt(), \
                                                                        textWidth, textHeight, \
                                                                        self.textHorizontalPos, textVerticalPos, QadDimStyleTxtRotModeEnum.ALIGNED_LINE)
                     else:
                        textInsPt, textRot = self.getTextPositionOnLine(dimLine.getStartPt(), dimLine.getEndPt(), \
                                                                        textWidth, textHeight, \
                                                                        self.textHorizontalPos, textVerticalPos, self.textRotMode)

                     rect = self.textRectToQadPolyline(textInsPt, textWidth, textHeight, textRot)
                     spaceForBlock1, spaceForBlock2 = self.getSpaceForBlock1AndBlock2OnLine(rect, dimLine)
                     # if there is no room even for the text without the arrows
                     if spaceForBlock1 == 0 or spaceForBlock2 == 0 or \
                        spaceForBlock1 < self.textOffsetDist or spaceForBlock2 < self.textOffsetDist:
                        # moves text outside extension lines
                        textInsPt, textRot, txtLeaderLines = self.getTextPosAndLinesOutOfDimLines(dimLine.getStartPt(), dimLine.getEndPt(), \
                                                                                                  textWidth, textHeight)
                        textLinearDimComponentOn = QadDimComponentEnum.LEADER_LINE
                     else:
                        textLinearDimComponentOn = QadDimComponentEnum.DIM_LINE1
                  else: # the text is more cumbersome than the symbols
                     # I move the text outside the extension lines
                     textInsPt, textRot, txtLeaderLines = self.getTextPosAndLinesOutOfDimLines(dimLine.getStartPt(), dimLine.getEndPt(), \
                                                                                               textWidth, textHeight)
                     textLinearDimComponentOn = QadDimComponentEnum.LEADER_LINE
                     # if the arrows don't even fit
                     if dimLine.length() <= self.getBlock1Size() + self.getBlock2Size():
                        block1Rot, block2Rot = self.getBlocksRotOnLine(dimLine, False) # frecce esterne
                     else:
                        block1Rot, block2Rot = self.getBlocksRotOnLine(dimLine, True) # frecce interne
         else: # if there is enough space to insert text and symbols inside the extension lines,
            textLinearDimComponentOn = QadDimComponentEnum.DIM_LINE1
            block1Rot, block2Rot = self.getBlocksRotOnLine(dimLine, True) # frecce interne

      # the text is above and aligned with the first extension line
      elif self.textHorizontalPos == QadDimStyleTxtHorizontalPosEnum.FIRST_EXT_LINE_UP:
         # angle of the line from the dimension point to the start of the dimension line
         rotLine = qad_utils.getAngleBy2Pts(dimPt1, dimLine.getStartPt())
         pt = qad_utils.getPolarPointByPtAngle(dimLine.getStartPt(), rotLine, self.textOffsetDist + textWidth)
         if self.textVerticalPos == QadDimStyleTxtVerticalPosEnum.EXTERN_LINE:
            textVerticalPos = QadDimStyleTxtVerticalPosEnum.ABOVE_LINE
         else:
            textVerticalPos = self.textVerticalPos

         if self.textRotMode == QadDimStyleTxtRotModeEnum.FORCED_ROTATION:
            textRotMode = QadDimStyleTxtRotModeEnum.FORCED_ROTATION
         else:
            textRotMode = QadDimStyleTxtRotModeEnum.ALIGNED_LINE

         textInsPt, textRot = self.getTextPositionOnLine(dimLine.getStartPt(), pt, textWidth, textHeight, \
                                                         QadDimStyleTxtHorizontalPosEnum.FIRST_EXT_LINE, \
                                                         textVerticalPos, textRotMode)
         textLinearDimComponentOn = QadDimComponentEnum.EXT_LINE1

         # calculate block space in the absence of text
         spaceForBlock1, spaceForBlock2 = self.getSpaceForBlock1AndBlock2OnLine(None, dimLine)
         # if there is no space for blocks
         if spaceForBlock1 < self.getBlock1Size() or spaceForBlock2 < self.getBlock2Size():
            if self.blockSuppressionForNoSpace: # i blocchi sono soppressi
               block1Rot = None
               block2Rot = None
            else: # I move the arrows outwards
               block1Rot, block2Rot = self.getBlocksRotOnLine(dimLine, False)
         else: # there is space for blocks
            block1Rot, block2Rot = self.getBlocksRotOnLine(dimLine, True) # frecce interne

      # the text is above and aligned with the second extension line
      elif self.textHorizontalPos == QadDimStyleTxtHorizontalPosEnum.SECOND_EXT_LINE_UP:
         # angle of the line from the dimension point to the start of the dimension line
         rotLine = qad_utils.getAngleBy2Pts(dimPt2, dimLine.getEndPt())
         pt = qad_utils.getPolarPointByPtAngle(dimLine.getEndPt(), rotLine, self.textOffsetDist + textWidth)
         if self.textVerticalPos == QadDimStyleTxtVerticalPosEnum.EXTERN_LINE:
            textVerticalPos = QadDimStyleTxtVerticalPosEnum.ABOVE_LINE
         else:
            textVerticalPos = self.textVerticalPos

         if self.textRotMode == QadDimStyleTxtRotModeEnum.FORCED_ROTATION:
            textRotMode = QadDimStyleTxtRotModeEnum.FORCED_ROTATION
         else:
            textRotMode = QadDimStyleTxtRotModeEnum.ALIGNED_LINE

         textInsPt, textRot = self.getTextPositionOnLine(dimLine.getEndPt(), pt, textWidth, textHeight, \
                                                         QadDimStyleTxtHorizontalPosEnum.FIRST_EXT_LINE, \
                                                         textVerticalPos, textRotMode)
         textLinearDimComponentOn = QadDimComponentEnum.EXT_LINE2

         # calculate block space in the absence of text
         spaceForBlock1, spaceForBlock2 = self.getSpaceForBlock1AndBlock2OnLine(None, dimLine)
         # if there is no space for blocks
         if spaceForBlock1 < self.getBlock1Size() or spaceForBlock2 < self.getBlock2Size():
            if self.blockSuppressionForNoSpace: # i blocchi sono soppressi
               block1Rot = None
               block2Rot = None
            else: # I move the arrows outwards
               block1Rot, block2Rot = self.getBlocksRotOnLine(dimLine, False)
         else: # there is space for blocks
            block1Rot, block2Rot = self.getBlocksRotOnLine(dimLine, True) # frecce interne

      if self.textDirection == QadDimStyleTxtDirectionEnum.DX_TO_SX:
         # the insertion point becomes the top right corner of the rectangle
         textInsPt = qad_utils.getPolarPointByPtAngle(textInsPt, textRot, textWidth)
         textInsPt = qad_utils.getPolarPointByPtAngle(textInsPt, textRot + math.pi / 2, textHeight)
         # the rotation is reversed
         textRot = qad_utils.normalizeAngle(textRot + math.pi)

      return [[textInsPt, textRot], [textLinearDimComponentOn, txtLeaderLines], block1Rot, block2Rot]


   # ============================================================================
   # getArcTextAndBlocksPosition
   # ============================================================================
   def getArcTextAndBlocksPosition(self, dimArc, dimLineArc, textWidth, textHeight):
      """dimArc = arc to dimension
            dimLineArc = dimension line in the form of an arc
            textWidth = text width
            textHeight = text height

            Returns a list of 4 items:
            - the first element is a list with the insertion point of the dimension text and its rotation
            - the second element is a list with flag indicating the type of the line on which the text was placed; see QadDimComponentEnum
                                  and a list of "leader" lines in case the text is outside the dimension
            - the third element is the rotation of the first block of arrows; can be None if not visible
            - the fourth element is the rotation of the second block of arrows; can be None if not visible
      """
      textInsPt                = None # text insertion point
      textRot                  = None # text rotation
      textLinearDimComponentOn = None # code of the linear component on which the text is positioned
      txtLeaderLines           = None # list of "leader" lines in case the text is outside the dimension
      block1Rot                = None # rotation of the first arrow block
      block2Rot                = None # rotation of the second arrow block

      dimLineArcPt1 = dimLineArc.getStartPt()
      dimLineArcPt2 = dimLineArc.getEndPt()
      dimLineArcLen = dimLineArc.length()
      # if the text is between the dimension extension lines
      if self.textHorizontalPos == QadDimStyleTxtHorizontalPosEnum.CENTERED_LINE or \
         self.textHorizontalPos == QadDimStyleTxtHorizontalPosEnum.FIRST_EXT_LINE or \
         self.textHorizontalPos == QadDimStyleTxtHorizontalPosEnum.SECOND_EXT_LINE:

         dimLineArcMiddlePt = dimLineArc.getMiddlePt()
         dimLineRot = dimLineArc.getTanDirectionOnPt(dimLineArcMiddlePt) # angle at the midpoint of the arc

         dimLineArcPt1Offset, dummyTg = dimLineArc.getPointFromStart(self.getBlock1Size())
         dimLineArcPt2Offset, dummyTg = dimLineArc.getPointFromStart(dimLineArcLen - self.getBlock2Size())

         # text above or below the dimension line if the dimension line is not horizontal
         # and the text is inside the extension lines and forced horizontal then the text becomes centered
         if (self.textVerticalPos == QadDimStyleTxtVerticalPosEnum.ABOVE_LINE or self.textVerticalPos == QadDimStyleTxtVerticalPosEnum.BELOW_LINE) and \
            (dimLineRot != 0 and dimLineRot != math.pi) and self.textRotMode == QadDimStyleTxtRotModeEnum.HORIZONTAL:
            textVerticalPos = QadDimStyleTxtVerticalPosEnum.CENTERED_LINE
         # text positioned opposite the dimension points
         elif self.textVerticalPos == QadDimStyleTxtVerticalPosEnum.EXTERN_LINE:
            # temporarily set it centered just to have the position of the text
            textVerticalPos = QadDimStyleTxtVerticalPosEnum.CENTERED_LINE
         else:
            textVerticalPos = self.textVerticalPos

         if self.textRotMode == QadDimStyleTxtRotModeEnum.ISO:
            textInsPt, textRot = self.getTextPositionOnArc(dimLineArc, textWidth, textHeight, \
                                                           self.textHorizontalPos, textVerticalPos, QadDimStyleTxtRotModeEnum.ALIGNED_LINE)
         else:
            textInsPt, textRot = self.getTextPositionOnArc(dimLineArc, textWidth, textHeight, \
                                                           self.textHorizontalPos, textVerticalPos, self.textRotMode)

         # text positioned opposite the dimension points
         if self.textVerticalPos == QadDimStyleTxtVerticalPosEnum.EXTERN_LINE:
            # central point of the dimension text
            insPtCenterTxt = qad_utils.getPolarPointByPtAngle(textInsPt, textRot, textWidth / 2)
            # angle from the center of the arc to the center point of the dimension text
            dimCenterToTextInsPt_rot = qad_utils.getAngleBy2Pts(dimArc.center, insPtCenterTxt)
            if dimCenterToTextInsPt_rot > 0 and \
               (dimCenterToTextInsPt_rot <= math.pi or qad_utils.doubleNear(dimCenterToTextInsPt_rot, math.pi)):
               if dimLineArc.radius >= dimArc.radius:
                  textVerticalPos = QadDimStyleTxtVerticalPosEnum.ABOVE_LINE
               else:
                  textVerticalPos = QadDimStyleTxtVerticalPosEnum.BELOW_LINE
            else:
               if dimLineArc.radius >= dimArc.radius:
                  textVerticalPos = QadDimStyleTxtVerticalPosEnum.BELOW_LINE
               else:
                  textVerticalPos = QadDimStyleTxtVerticalPosEnum.ABOVE_LINE

            if self.textRotMode == QadDimStyleTxtRotModeEnum.ISO:
               textInsPt, textRot = self.getTextPositionOnArc(dimLineArc, textWidth, textHeight, \
                                                              self.textHorizontalPos, textVerticalPos, QadDimStyleTxtRotModeEnum.ALIGNED_LINE)
            else:
               textInsPt, textRot = self.getTextPositionOnArc(dimLineArc, textWidth, textHeight, \
                                                              self.textHorizontalPos, textVerticalPos, self.textRotMode)

         rect = self.textRectToQadPolyline(textInsPt, textWidth, textHeight, textRot)
         spaceForBlock1, spaceForBlock2 = self.getSpaceForBlock1AndBlock2OnArc(rect, dimLineArc)

         # if there is not enough space to insert text and symbols inside the extension lines,
         # use qad_utils.doubleSmaller because sometimes the two numbers are almost equal
         if spaceForBlock1 == 0 or spaceForBlock2 == 0 or \
            qad_utils.doubleSmaller(spaceForBlock1, self.getBlock1Size() + self.textOffsetDist) or \
            qad_utils.doubleSmaller(spaceForBlock2, self.getBlock2Size() + self.textOffsetDist):
            if self.blockSuppressionForNoSpace: # suppresses symbols if there is not enough space inside the extension lines
               block1Rot = None
               block2Rot = None

               # I consider the text without arrows
               if self.textRotMode == QadDimStyleTxtRotModeEnum.ISO:
                  textInsPt, textRot = self.getTextPositionOnArc(dimLineArc, textWidth, textHeight, \
                                                                 self.textHorizontalPos, textVerticalPos, QadDimStyleTxtRotModeEnum.ALIGNED_LINE)
               else:
                  textInsPt, textRot = self.getTextPositionOnArc(dimLineArc, textWidth, textHeight, \
                                                                 self.textHorizontalPos, textVerticalPos, self.textRotMode)

               rect = self.textRectToQadPolyline(textInsPt, textWidth, textHeight, textRot)
               spaceForBlock1, spaceForBlock2 = self.getSpaceForBlock1AndBlock2OnArc(rect, dimLineArc)
               # if there is no room even for the text without the arrows
               if spaceForBlock1 == 0 or spaceForBlock2 == 0 or \
                  spaceForBlock1 < self.textOffsetDist or spaceForBlock2 < self.textOffsetDist:
                  # moves text outside extension lines
                  textInsPt, textRot, txtLeaderLines = self.getTextPosAndLinesOutOfDimArc(dimLineArc, textWidth, textHeight)
                  textLinearDimComponentOn = QadDimComponentEnum.LEADER_LINE
               else:
                  textLinearDimComponentOn = QadDimComponentEnum.DIM_LINE1
            else: # non devo sopprimere i simboli
               # the first thing to move outside is:
               if self.textBlockAdjust == QadDimStyleTextBlocksAdjustEnum.BOTH_OUTSIDE_EXT_LINES:
                  # moves text and arrows outside extension lines
                  textInsPt, textRot, txtLeaderLines = self.getTextPosAndLinesOutOfDimArc(dimLineArc, textWidth, textHeight)
                  textLinearDimComponentOn = QadDimComponentEnum.LEADER_LINE
                  block1Rot, block2Rot = self.getBlocksRotOnArc(dimLineArc, False) # frecce esterne
               # first move the arrows then, if that's not enough, also the text
               elif self.textBlockAdjust == QadDimStyleTextBlocksAdjustEnum.FIRST_BLOCKS_THEN_TEXT:
                  block1Rot, block2Rot = self.getBlocksRotOnArc(dimLineArc, False) # frecce esterne
                  # I consider the text without arrows
                  if self.textRotMode == QadDimStyleTxtRotModeEnum.ISO:
                     textInsPt, textRot = self.getTextPositionOnArc(dimLineArc, textWidth, textHeight, \
                                                                    self.textHorizontalPos, textVerticalPos, QadDimStyleTxtRotModeEnum.ALIGNED_LINE)
                  else:
                     textInsPt, textRot = self.getTextPositionOnArc(dimLineArc, textWidth, textHeight, \
                                                                    self.textHorizontalPos, textVerticalPos, self.textRotMode)

                  rect = self.textRectToQadPolyline(textInsPt, textWidth, textHeight, textRot)
                  spaceForBlock1, spaceForBlock2 = self.getSpaceForBlock1AndBlock2OnArc(rect, dimLineArc)
                  # if there is no room even for the text without the arrows
                  if spaceForBlock1 == 0 or spaceForBlock2 == 0 or \
                     spaceForBlock1 < self.textOffsetDist or spaceForBlock2 < self.textOffsetDist:
                     # moves text outside extension lines
                     textInsPt, textRot, txtLeaderLines = self.getTextPosAndLinesOutOfDimArc(dimLineArc, textWidth, textHeight)
                     textLinearDimComponentOn = QadDimComponentEnum.LEADER_LINE
                  else:
                     textLinearDimComponentOn = QadDimComponentEnum.DIM_LINE1
               # first move the text and then, if that's not enough, also the arrows
               elif self.textBlockAdjust == QadDimStyleTextBlocksAdjustEnum.FIRST_TEXT_THEN_BLOCKS:
                  # I move the text outside the extension lines
                  textInsPt, textRot, txtLeaderLines = self.getTextPosAndLinesOutOfDimArc(dimLineArc, textWidth, textHeight)
                  textLinearDimComponentOn = QadDimComponentEnum.LEADER_LINE
                  # if the arrows don't even fit
                  if dimLineArcLen <= self.getBlock1Size() + self.getBlock2Size():
                     block1Rot, block2Rot = self.getBlocksRotOnArc(dimLineArc, False) # frecce esterne
                  else:
                     block1Rot, block2Rot = self.getBlocksRotOnArc(dimLineArc, True) # frecce interne
               # Move text or arrows indiscriminately (the object that fits best)
               elif self.textBlockAdjust == QadDimStyleTextBlocksAdjustEnum.WHICHEVER_FITS_BEST:
                  # I move the bulkiest one
                  if self.getBlock1Size() + self.getBlock2Size() > textWidth: # arrows are bulkier than text
                     textLinearDimComponentOn = QadDimComponentEnum.DIM_LINE1
                     block1Rot, block2Rot = self.getBlocksRotOnArc(dimLineArc, False) # frecce esterne

                     # I consider the text without arrows
                     if self.textRotMode == QadDimStyleTxtRotModeEnum.ISO:
                        textInsPt, textRot = self.getTextPositionOnArc(dimLineArc, textWidth, textHeight, \
                                                                       self.textHorizontalPos, textVerticalPos, QadDimStyleTxtRotModeEnum.ALIGNED_LINE)
                     else:
                        textInsPt, textRot = self.getTextPositionOnArc(dimLineArc, textWidth, textHeight, \
                                                                       self.textHorizontalPos, textVerticalPos, self.textRotMode)

                     rect = self.textRectToQadPolyline(textInsPt, textWidth, textHeight, textRot)
                     spaceForBlock1, spaceForBlock2 = self.getSpaceForBlock1AndBlock2OnArc(rect, dimLineArc)
                     # if there is no room even for the text without the arrows
                     if spaceForBlock1 == 0 or spaceForBlock2 == 0 or \
                        spaceForBlock1 < self.textOffsetDist or spaceForBlock2 < self.textOffsetDist:
                        # moves text outside extension lines
                        textInsPt, textRot, txtLeaderLines = self.getTextPosAndLinesOutOfDimArc(dimLineArc, textWidth, textHeight)
                        textLinearDimComponentOn = QadDimComponentEnum.LEADER_LINE
                     else:
                        textLinearDimComponentOn = QadDimComponentEnum.DIM_LINE1
                  else: # the text is more cumbersome than the symbols
                     # I move the text outside the extension lines
                     textInsPt, textRot, txtLeaderLines = self.getTextPosAndLinesOutOfDimArc(dimLineArc, textWidth, textHeight)
                     textLinearDimComponentOn = QadDimComponentEnum.LEADER_LINE
                     # if the arrows don't even fit
                     if dimLineArcLen <= self.getBlock1Size() + self.getBlock2Size():
                        block1Rot, block2Rot = self.getBlocksRotOnArc(dimLineArc, False) # frecce esterne
                     else:
                        block1Rot, block2Rot = self.getBlocksRotOnArc(dimLineArc, True) # frecce interne
         else: # if there is enough space to insert text and symbols inside the extension lines,
            textLinearDimComponentOn = QadDimComponentEnum.DIM_LINE1
            block1Rot, block2Rot = self.getBlocksRotOnArc(dimLineArc, True) # frecce interne

      # the text is above and aligned with the first extension line
      elif self.textHorizontalPos == QadDimStyleTxtHorizontalPosEnum.FIRST_EXT_LINE_UP:
         # angle of the line from the dimension point to the start of the dimension line
         if dimArc.startAngle == dimLineArc.startAngle:
            rotLine = qad_utils.getAngleBy2Pts(dimArc.getStartPt(), dimLineArcPt1)
         else:
            rotLine = qad_utils.getAngleBy2Pts(dimArc.getEndPt(), dimLineArcPt1)

         pt = qad_utils.getPolarPointByPtAngle(dimLineArcPt1, rotLine, self.textOffsetDist + textWidth)
         if self.textVerticalPos == QadDimStyleTxtVerticalPosEnum.EXTERN_LINE:
            textVerticalPos = QadDimStyleTxtVerticalPosEnum.ABOVE_LINE
         else:
            textVerticalPos = self.textVerticalPos

         if self.textRotMode == QadDimStyleTxtRotModeEnum.FORCED_ROTATION:
            textRotMode = QadDimStyleTxtRotModeEnum.FORCED_ROTATION
         else:
            textRotMode = QadDimStyleTxtRotModeEnum.ALIGNED_LINE

         textInsPt, textRot = self.getTextPositionOnLine(dimLineArcPt1, pt, textWidth, textHeight, \
                                                         QadDimStyleTxtHorizontalPosEnum.FIRST_EXT_LINE, \
                                                         textVerticalPos, textRotMode)
         textLinearDimComponentOn = QadDimComponentEnum.EXT_LINE1

         # calculate block space in the absence of text
         spaceForBlock1, spaceForBlock2 = self.getSpaceForBlock1AndBlock2OnArc(None, dimLineArc)
         # if there is no space for blocks
         if spaceForBlock1 < self.getBlock1Size() or spaceForBlock2 < self.getBlock2Size():
            if self.blockSuppressionForNoSpace: # i blocchi sono soppressi
               block1Rot = None
               block2Rot = None
            else: # I move the arrows outwards
               block1Rot, block2Rot = self.getBlocksRotOnArc(dimLineArc, False)
         else: # there is space for blocks
            block1Rot, block2Rot = self.getBlocksRotOnArc(dimLineArc, True) # frecce interne

      # the text is above and aligned with the second extension line
      elif self.textHorizontalPos == QadDimStyleTxtHorizontalPosEnum.SECOND_EXT_LINE_UP:
         # angle of the line from the dimension point to the start of the dimension line
         # angle of the line from the dimension point to the start of the dimension line
         if dimArc.startAngle == dimLineArc.startAngle:
            rotLine = qad_utils.getAngleBy2Pts(dimArc.getEndPt(), dimLineArcPt2)
         else:
            rotLine = qad_utils.getAngleBy2Pts(dimArc.getStartPt(), dimLineArcPt2)

         pt = qad_utils.getPolarPointByPtAngle(dimLineArcPt2, rotLine, self.textOffsetDist + textWidth)
         if self.textVerticalPos == QadDimStyleTxtVerticalPosEnum.EXTERN_LINE:
            textVerticalPos = QadDimStyleTxtVerticalPosEnum.ABOVE_LINE
         else:
            textVerticalPos = self.textVerticalPos

         if self.textRotMode == QadDimStyleTxtRotModeEnum.FORCED_ROTATION:
            textRotMode = QadDimStyleTxtRotModeEnum.FORCED_ROTATION
         else:
            textRotMode = QadDimStyleTxtRotModeEnum.ALIGNED_LINE

         textInsPt, textRot = self.getTextPositionOnLine(dimLineArcPt2, pt, textWidth, textHeight, \
                                                         QadDimStyleTxtHorizontalPosEnum.FIRST_EXT_LINE, \
                                                         textVerticalPos, textRotMode)
         textLinearDimComponentOn = QadDimComponentEnum.EXT_LINE2

         # calculate block space in the absence of text
         spaceForBlock1, spaceForBlock2 = self.getSpaceForBlock1AndBlock2OnArc(None, dimLineArc)
         # if there is no space for blocks
         if spaceForBlock1 < self.getBlock1Size() or spaceForBlock2 < self.getBlock2Size():
            if self.blockSuppressionForNoSpace: # i blocchi sono soppressi
               block1Rot = None
               block2Rot = None
            else: # I move the arrows outwards
               block1Rot, block2Rot = self.getBlocksRotOnArc(dimLineArc, False)
         else: # there is space for blocks
            block1Rot, block2Rot = self.getBlocksRotOnArc(dimLineArc, True) # frecce interne

      if self.textDirection == QadDimStyleTxtDirectionEnum.DX_TO_SX:
         # the insertion point becomes the top right corner of the rectangle
         textInsPt = qad_utils.getPolarPointByPtAngle(textInsPt, textRot, textWidth)
         textInsPt = qad_utils.getPolarPointByPtAngle(textInsPt, textRot + math.pi / 2, textHeight)
         # the rotation is reversed
         textRot = qad_utils.normalizeAngle(textRot + math.pi)

      return [[textInsPt, textRot], [textLinearDimComponentOn, txtLeaderLines], block1Rot, block2Rot]


   # ============================================================================
   # getRadiusTextAndBlocksPosition
   # ============================================================================
   def getRadiusTextAndBlocksPosition(self, dimLine, textWidth, textHeight):
      """dimLine = dimension line (QadLine)
            textWidth = text width
            textHeight = text height

            Returns a list of 4 items:
            - the first element is a list with the insertion point of the dimension text and its rotation
            - the second element is a list with flag indicating the type of the line on which the text was placed; see QadDimComponentEnum
                                  and a list of "leader" lines in case the text is outside the dimension
            - the third element is the rotation of the first block of arrows; can be None if not visible
            - the fourth element is the rotation of the second block of arrows; can be None if not visible
      """
      textInsPt                = None # text insertion point
      textRot                  = None # text rotation
      textLinearDimComponentOn = None # code of the linear component on which the text is positioned
      txtLeaderLines           = None # list of "leader" lines in case the text is outside the dimension

      # change some dimension parameters
      block1Name = self.block1Name
      self.block1Name = "" # no arrow at dimension point 1
      block2Name = self.block2Name
      self.block2Name = "" # no arrow at dimension point 2
      textBlockAdjust = self.textBlockAdjust
      self.textBlockAdjust = QadDimStyleTextBlocksAdjustEnum.FIRST_TEXT_THEN_BLOCKS # if the text doesn't fit it goes outside the dimension line
      textHorizontalPos = self.textHorizontalPos
      self.textHorizontalPos = QadDimStyleTxtHorizontalPosEnum.FIRST_EXT_LINE

      res = self.getLinearTextAndBlocksPosition(dimLine.getStartPt(), dimLine.getEndPt(), dimLine, textWidth, textHeight)

      # restore original values
      self.block1Name = block1Name
      self.block2Name = block2Name
      self.textBlockAdjust = textBlockAdjust
      self.textHorizontalPos = textHorizontalPos

      return res


   # ============================================================================
   # getTextFeature
   # ============================================================================
   def getTextFeature(self, measure, pt = None, rot = None):
      """Returns the dimension text feature.
            Rotation is expressed in radians.
      """
      _pt = QgsPointXY(0,0) if pt is None else pt
      _rot = 0 if rot is None else rot

      textualFeaturePrototype = self.getTextualFeaturePrototype()
      if textualFeaturePrototype is None:
         return None
      f = QgsFeature(textualFeaturePrototype)
      g = fromQadGeomToQgsGeom(QadPoint().set(_pt), self.getTextualLayer()) # I transform the geometry
      f.setGeometry(g)

      # if the text depends on only one field
      labelFieldNames = qad_label.get_labelFieldNames(self.getTextualLayer())
      if len(labelFieldNames) == 1 and len(labelFieldNames[0]) > 0:
         f.setAttribute(labelFieldNames[0], self.getFormattedText(measure))

      # if the text height depends on only one field
      sizeFldNames = qad_label.get_labelSizeFieldNames(self.getTextualLayer())
      if len(sizeFldNames) == 1 and len(sizeFldNames[0]) > 0:
         f.setAttribute(sizeFldNames[0], self.textHeight) # text height

      # if the rotation depends on only one field
      rotFldNames = qad_label.get_labelRotationFieldNames(self.getTextualLayer())
      if len(rotFldNames) == 1 and len(rotFldNames[0]) > 0:
         f.setAttribute(rotFldNames[0], qad_utils.toDegrees(_rot)) # Converte da radianti a gradi

      # if the font depends on only one field
      fontFamilyFldNames = qad_label.get_labelFontFamilyFieldNames(self.getTextualLayer())
      if len(fontFamilyFldNames) == 1 and len(fontFamilyFldNames[0]) > 0:
         f.setAttribute(fontFamilyFldNames[0], self.textFont) # text font name

      # set the color
      try:
         if len(self.colorFieldName) > 0:
            f.setAttribute(self.colorFieldName, self.textColor)
      except:
         pass

      # set the dimensioning style
      try:
         if len(self.dimStyleFieldName) > 0:
            f.setAttribute(self.dimStyleFieldName, self.name)
         if len(self.dimTypeFieldName) > 0:
            f.setAttribute(self.dimTypeFieldName, self.dimType)
      except:
         pass

      return f


   # ============================================================================
   # TEXT FUNCTIONS - END
   # FUNCTIONS FOR THE LEADER LINE - START
   # ============================================================================


   # ============================================================================
   # getAuxiliarySecondLeaderLine
   # ============================================================================
   def getAuxiliarySecondLeaderLine(self, pt1, rotLine, textWidth, textHeight):
      """Internal support function for subsequent leaders who deal with the leader line.
            Returns the second dimension line (the one closest to the text).
            pt1 = point from which to start the line (QgsPointXY)
            rotLine = angle of the first dimension line (QgsPointXY)
            textWidth = text width
            textHeight = text height
      """
      # horizontal text rotation mode or
      # text aligned with the dimension line if between the extension lines, otherwise horizontal text
      if self.textRotMode == QadDimStyleTxtRotModeEnum.HORIZONTAL or \
         self.textRotMode == QadDimStyleTxtRotModeEnum.ISO:
         if qad_utils.doubleNear(rotLine, math.pi / 2): # verticale dal basso verso l'alto
            pt2 = qad_utils.getPolarPointByPtAngle(pt1, 0, self.textOffsetDist + textWidth)
         elif qad_utils.doubleNear(rotLine, math.pi * 3 / 2): # vertical from top to bottom
            pt2 = qad_utils.getPolarPointByPtAngle(pt1, math.pi, self.textOffsetDist + textWidth)
         elif (rotLine > math.pi * 3 / 2 and rotLine <= math.pi * 2) or \
              (rotLine >= 0 and rotLine < math.pi / 2): # da sx a dx
            pt2 = qad_utils.getPolarPointByPtAngle(pt1, 0, self.textOffsetDist + textWidth)
         else: # da dx a sx
            pt2 = qad_utils.getPolarPointByPtAngle(pt1, math.pi, self.textOffsetDist + textWidth)
      elif self.textRotMode == QadDimStyleTxtRotModeEnum.ALIGNED_LINE: # text aligned with the dimension line
         pt2 = qad_utils.getPolarPointByPtAngle(pt1, rotLine, self.textOffsetDist + textWidth)
      elif self.textRotMode == QadDimStyleTxtRotModeEnum.FORCED_ROTATION: # text with forced rotation
         pt2 = qad_utils.getPolarPointByPtAngle(pt1, self.textForcedRot, self.textOffsetDist + textWidth)

      return QadLine().set(pt1, pt2)


   # ============================================================================
   # getLeaderLinesOnLine
   # ============================================================================
   def getLeaderLinesOnLine(self, dimLinePt1, dimLinePt2, textWidth, textHeight):
      """Returns a polyline (QadPolyline) that forms the dimension holder if the text is moved
            outside the extension lines because it was too big.
            dimLinePt1 = first point of the dimension line (QgsPointXY)
            dimLinePt2 = second point of the dimension line (QgsPointXY)
            textWidth = text width
            textHeight = text height
      """
      res = QadPolyline()
      # the lines are next to extension line 1
      if self.textHorizontalPos == QadDimStyleTxtHorizontalPosEnum.FIRST_EXT_LINE:
         rotLine = qad_utils.getAngleBy2Pts(dimLinePt2, dimLinePt1) # angle of the dimension line
         pt1 = qad_utils.getPolarPointByPtAngle(dimLinePt1, rotLine, self.getBlock1Size())
         res.append(QadLine().set(dimLinePt1, pt1))
      # the lines are next to extension line 2
      else:
         rotLine = qad_utils.getAngleBy2Pts(dimLinePt1, dimLinePt2) # angle of the dimension line
         pt1 = qad_utils.getPolarPointByPtAngle(dimLinePt2, rotLine, self.getBlock2Size())
         res.append(QadLine().set(dimLinePt2, pt1))

      # get the second dimension extension line
      line2 = self.getAuxiliarySecondLeaderLine(pt1, rotLine, textWidth, textHeight)
      res.append(line2)

      return res


   # ============================================================================
   # getLeaderLinesOnArc
   # ============================================================================
   def getLeaderLinesOnArc(self, dimLineArc, textWidth, textHeight):
      """Returns a polyline (QadPolyline) that forms the dimension holder if the text is moved
            outside the extension lines because it was too big.
            dimLineArc = arc representing the dimension arc (QadArc)
            textWidth = text width
            textHeight = text height
      """
      res = QadPolyline()
      # the lines are next to extension line 1
      if self.textHorizontalPos == QadDimStyleTxtHorizontalPosEnum.FIRST_EXT_LINE:
         startPt = dimLineArc.getStartPt()
         rotLine = dimLineArc.getTanDirectionOnPt(startPt) + math.pi # angle of the line leading to the starting point
         pt1 = qad_utils.getPolarPointByPtAngle(startPt, rotLine, self.getBlock1Size())
         res.append(QadLine().set(startPt, pt1))
      # the lines are next to extension line 2
      else:
         endPt = dimLineArc.getEndPt()
         rotLine = dimLineArc.getTanDirectionOnPt(endPt) # angle of the line leading to the final point
         pt1 = qad_utils.getPolarPointByPtAngle(endPt, rotLine, self.getBlock2Size())
         res.append(QadLine().set(endPt, pt1))

      # get the second dimension extension line
      line2 = self.getAuxiliarySecondLeaderLine(pt1, rotLine, textWidth, textHeight)
      res.append(line2)

      return res


   # ============================================================================
   # getLeaderFeature
   # ============================================================================
   def getLeaderFeature(self, leaderLines, leaderLineType = QadDimComponentEnum.LEADER_LINE):
      """Returns the feature for the extension line.
            leaderLines = leader polyline (QadPolyline)
            leaderLineType = type of leader line (LEADER_LINE, ARC_LEADER_LINE, ...)
      """
      if leaderLines is None:
         return None

      linearFeaturePrototype = self.getLinearFeaturePrototype()
      if linearFeaturePrototype is None:
         return None
      f = QgsFeature(linearFeaturePrototype)
      g = fromQadGeomToQgsGeom(leaderLines, self.getLinearLayer())
      f.setGeometry(g)

      try:
         # set the dimensioning component type
         if len(self.componentFieldName) > 0:
            f.setAttribute(self.componentFieldName, leaderLineType)
      except:
         pass

      try:
         # set the linetype
         if len(self.lineTypeFieldName) > 0:
            f.setAttribute(self.lineTypeFieldName, self.dimLineLineType)
      except:
         pass

      try:
         # set the color
         if len(self.colorFieldName) > 0:
            f.setAttribute(self.colorFieldName, self.dimLineColor)
      except:
         pass

      return f


   # ============================================================================
   # getArcLeaderLine
   # ============================================================================
   def getArcLeaderLine(self, pt, arc):
      """Returns the line that joins the text to the arc to be dimensioned."""
      intPts = QadIntersections.infinityLineWithArc(QadLine().set(pt, arc.center), arc)
      if len(intPts) == 1:
         return QadLine().set(pt, intPts[0])
      elif len(intPts) == 2:
         # I choose the closest
         if qad_utils.getDistance(pt, intPts[0]) < qad_utils.getDistance(pt, intPts[1]):
            return QadLine().set(pt, intPts[0])
         else:
            return QadLine().set(pt, intPts[1])
      else:
         return None


   # ============================================================================
   # FUNCTIONS FOR THE LEADER LINE - END
   # FUNCTIONS FOR EXTENSION LINES - START
   # ============================================================================


   # ============================================================================
   # getExtLine
   # ============================================================================
   def getExtLine(self, dimPt, dimLinePt):
      """dimPt = point to dimension
            dimLinePt = corresponding point of the dimension line

            returns an extension line modified according to the dimensioning style
            the first point is close to the dimension line, the second to the point to be dimensioned
      """

      angle = qad_utils.getAngleBy2Pts(dimPt, dimLinePt)
      # distance of the extension line beyond the dimension line
      pt1 = qad_utils.getPolarPointByPtAngle(dimLinePt, angle, self.extLineOffsetDimLine)
      # distance of the extension line from the points to be dimensioned
      pt2 = qad_utils.getPolarPointByPtAngle(dimPt, angle, self.extLineOffsetOrigPoints)

      if self.extLineIsFixedLen == True: # fixed extension line length enabled
         if qad_utils.getDistance(pt1, pt2) > self.extLineFixedLen:
            # fixed length of extension lines (DIMFXL) from the dimension line
            # to the dimension point shifted by extLineOffsetOrigPoints
            # (the extension line does not go beyond the point to be dimensioned)
            d = qad_utils.getDistance(dimLinePt, dimPt)
            if d > self.extLineFixedLen:
               d = self.extLineFixedLen
            pt2 = qad_utils.getPolarPointByPtAngle(dimLinePt, angle + math.pi, d)

      return QadLine().set(pt1, pt2)


   # ============================================================================
   # getExtArc
   # ============================================================================
   def getExtArc(self, arc, linePosPt):
      """arc = arc to dimension
            linePosPt = point corresponding to where to place the dimension

            Returns an extension arc for DIMRADIUS dimensioning
      """
      # if the point is inside the arc
      angle = qad_utils.getAngleBy2Pts(arc.center, linePosPt)
      if qad_utils.isAngleBetweenAngles(arc.startAngle, arc.endAngle, angle) == True:
         return None

      myArc = QadArc()
      pt = qad_utils.getPolarPointByPtAngle(arc.center, angle, arc.radius) # point on the curve
      # on the side of the starting point of the arc
      if qad_utils.getDistance(pt, arc.getStartPt()) < qad_utils.getDistance(pt, arc.getEndPt()):
         myArc.set(arc.center, arc.radius, angle, arc.startAngle)
         if myArc.length() <= self.extLineOffsetOrigPoints:
            return None

         myArc.setStartAngleByPt(pt)
         dummyPt, dummyTg = myArc.getPointFromStart(-self.extLineOffsetDimLine)
         myArc.setStartAngleByPt(dummyPt)
         dummyPt, dummyTg = arc.getPointFromStart(-self.extLineOffsetOrigPoints)
         myArc.setEndAngleByPt(dummyPt) # end point change
      else: # on the side of the final point of the arc
         myArc.set(arc.center, arc.radius, arc.endAngle, angle)
         if myArc.length() <= self.extLineOffsetOrigPoints:
            return None
         dummyPt, dummyTg = arc.getPointFromEnd(self.extLineOffsetOrigPoints)
         myArc.setStartAngleByPt(dummyPt) # starting point change
         myArc.setEndAngleByPt(pt)
         dummyPt, dummyTg = myArc.getPointFromEnd(self.extLineOffsetDimLine)
         myArc.setEndAngleByPt(dummyPt)

      return myArc


   # ============================================================================
   # getExtLineFeature
   # ============================================================================
   def getExtLineFeature(self, extLine, isExtLine1):
      """Returns the feature for the extension line.
            extLine = QadLine or QadArc extension line
            isExtLine1 = if True it is extension line 1 otherwise it is extension line 2
      """
      if (isExtLine1 == True and self.extLine1Show == False) or \
         (isExtLine1 == False and self.extLine2Show == False):
         return None

      f = QgsFeature(self.getLinearFeaturePrototype())
      g = fromQadGeomToQgsGeom(extLine, self.getLinearLayer()) # I transform the geometry
      f.setGeometry(g)

      try:
         # set the dimensioning component type
         if len(self.componentFieldName) > 0:
            f.setAttribute(self.componentFieldName, QadDimComponentEnum.EXT_LINE1 if isExtLine1 else QadDimComponentEnum.EXT_LINE2)
      except:
         pass

      try:
         # set the linetype
         if len(self.lineTypeFieldName) > 0:
            f.setAttribute(self.lineTypeFieldName, self.extLine1LineType if isExtLine1 else self.extLine2LineType)
      except:
         pass

      try:
         # set the color
         if len(self.colorFieldName) > 0:
            f.setAttribute(self.colorFieldName, self.extLineColor)
      except:
         pass

      return f


   # ============================================================================
   # FUNCTIONS FOR EXTENSION LINES - END
   # FUNCTIONS FOR THE DIMENSION LINE - START
   # ============================================================================


   # ============================================================================
   # getDimLine
   # ============================================================================
   def getDimLine(self, dimPt1, dimPt2, linePosPt, preferredAlignment = QadDimStyleAlignmentEnum.HORIZONTAL,
                  dimLineRotation = 0.0):
      """Returns the dimension line within the extension lines (any extensions will be calculated
            from function: getDimLineExtensions)

            dimPt1 = first point to dimension
            dimPt2 = second point to dimension
            linePosPt = point to indicate where the dimension line should be positioned
            preferredAlignment = indicates whether you should align to the dimension points horizontally or vertically
                                 (if the elevation points form a slanted line). Used only for linear dimensions
            dimLineRotation = dimension line angle (default = 0). Used only for linear dimensions
      """
      if self.dimType == QadDimTypeEnum.ALIGNED:
         # calculate the perpendicular projection of the point <linePosPt> on the line joining <dimPt1> to <dimPt2>
         ptPerp = qad_utils.getPerpendicularPointOnInfinityLine(dimPt1, dimPt2, linePosPt)
         d = qad_utils.getDistance(linePosPt, ptPerp)

         angle = qad_utils.getAngleBy2Pts(dimPt1, dimPt2)
         if qad_utils.leftOfLine(linePosPt, dimPt1, dimPt2) < 0: # to the left of the line that joins <dimPt1> to <dimPt2>
            angle = angle + (math.pi / 2)
         else:
            angle = angle - (math.pi / 2)

         return QadLine().set(qad_utils.getPolarPointByPtAngle(dimPt1, angle, d), \
                              qad_utils.getPolarPointByPtAngle(dimPt2, angle, d))
      elif self.dimType == QadDimTypeEnum.LINEAR:
         if preferredAlignment == QadDimStyleAlignmentEnum.HORIZONTAL:
            ptDummy = qad_utils.getPolarPointByPtAngle(dimPt1, dimLineRotation + math.pi / 2, 1)
            pt1 = qad_utils.getPerpendicularPointOnInfinityLine(dimPt1, ptDummy, linePosPt)
            ptDummy = qad_utils.getPolarPointByPtAngle(dimPt2, dimLineRotation + math.pi / 2, 1)
            pt2 = qad_utils.getPerpendicularPointOnInfinityLine(dimPt2, ptDummy, linePosPt)

            return QadLine().set(pt1, pt2)
         elif preferredAlignment == QadDimStyleAlignmentEnum.VERTICAL:
            ptDummy = qad_utils.getPolarPointByPtAngle(dimPt1, dimLineRotation, 1)
            pt1 = qad_utils.getPerpendicularPointOnInfinityLine(dimPt1, ptDummy, linePosPt)
            ptDummy = qad_utils.getPolarPointByPtAngle(dimPt2, dimLineRotation, 1)
            pt2 = qad_utils.getPerpendicularPointOnInfinityLine(dimPt2, ptDummy, linePosPt)

            return QadLine().set(pt1, pt2)


   # ============================================================================
   # getDimLineForArc
   # ============================================================================
   def getDimLineForArc(self, arc, linePosPt):
      """Returns the dimension line (as an arc) for the width of an arc +
            a flag to warn if the arc has been reversed
            Returns the dimension line within the extension lines (any extensions will be calculated
            from function: getDimArcExtensions)

            arc = QadArc arc object (in map units)
            linePosPt = point to indicate where the dimension line should be positioned
      """
      if self.dimType == QadDimTypeEnum.ARC_LENTGH:
         myArc = QadArc(arc)
         # calculate the distance between <linePosPt> and the center of the arc
         d = qad_utils.getDistance(linePosPt, myArc.center)
         myArc.radius = d # change the radius

         # if the point is not inside the arc I consider the inverse of the arc
         angle = qad_utils.getAngleBy2Pts(myArc.center, linePosPt)
         if qad_utils.isAngleBetweenAngles(myArc.startAngle, myArc.endAngle, angle) == False:
            myArc.inverseAngles()
         return myArc

      return None


   # ============================================================================
   # getDimLineFeature
   # ============================================================================
   def getDimLineFeature(self, dimLine, isDimLine1, textLinearDimComponentOn):
      """Returns the feature for the dimension line.
            dimLine = dimension line (QadLine or QadArc)
            isDimLine1 = if True it is dimension line 1 otherwise it is dimension line 2
            textLinearDimComponentOn = indicates the component of the dimension where the dimension text is located (QadDimComponentEnum)
      """

      # if there is no dimension line
      if dimLine is None:
         return None
      if isDimLine1 == True: # if it is dimension line 1
         # if the dimension line 1 must be invisible (valid only if the text is on the dimension line)
         if self.dimLine1Show == False and \
           (textLinearDimComponentOn == QadDimComponentEnum.DIM_LINE1 or textLinearDimComponentOn == QadDimComponentEnum.DIM_LINE2):
            return None
      else: # if it is level line 2
         # if the dimension line 2 must be invisible (valid only if the text is on the dimension line)
         if self.dimLine2Show == False and \
           (textLinearDimComponentOn == QadDimComponentEnum.DIM_LINE1 or textLinearDimComponentOn == QadDimComponentEnum.DIM_LINE2):
            return None

      f = QgsFeature(self.getLinearFeaturePrototype())
      g = fromQadGeomToQgsGeom(dimLine, self.getLinearLayer()) # I transform the geometry
      f.setGeometry(g)

      try:
         # set the dimensioning component type
         if len(self.componentFieldName) > 0:
            f.setAttribute(self.componentFieldName, QadDimComponentEnum.DIM_LINE1 if isDimLine1 else QadDimComponentEnum.DIM_LINE2)
      except:
         pass

      try:
         # set the linetype
         if len(self.lineTypeFieldName) > 0:
            f.setAttribute(self.lineTypeFieldName, self.dimLineLineType)
      except:
         pass

      try:
         # set the color
         if len(self.colorFieldName) > 0:
            f.setAttribute(self.colorFieldName, self.dimLineColor)
      except:
         pass

      return f


   # ============================================================================
   # FUNCTIONS FOR THE DIMENSION LINE - END
   # FUNCTIONS FOR DIMENSION LINE EXTENSIONS - TOP
   # ============================================================================


   # ============================================================================
   # getDimLineExtensions
   # ============================================================================
   def getDimLineExtensions(self, dimLine1, dimLine2):
      """Returns the extensions of the dimension lines at the beginning and end (see variable dimLineOffsetExtLine)"""
      # if it is not greater than 0 or if there are no dimension lines
      if self.dimLineOffsetExtLine <= 0 or (dimLine1 is None and dimLine2 is None):
         return None, None

      extDimLine1 = None
      extDimLine2 = None
      # set the lines in the same direction as the dimension line
      rot = qad_utils.getAngleBy2Pts(dimLine1.getStartPt(), dimLine1.getEndPt())
      if dimLine1 is not None:
         # starting point change
         extDimLine1 = QadLine().set(qad_utils.getPolarPointByPtAngle(dimLine1.getStartPt(), rot + math.pi, self.dimLineOffsetExtLine), \
                                     dimLine1.getStartPt())
         if dimLine2 is None: # if the dimension line consists of only one line
            # end point change
            extDimLine2 = QadLine().set(dimLine1.getEndPt(), \
                                        qad_utils.getPolarPointByPtAngle(dimLine1.getEndPt(), rot, self.dimLineOffsetExtLine))

      if dimLine2 is not None:
         rot = qad_utils.getAngleBy2Pts(dimLine2.getStartPt(), dimLine2.getEndPt())
         # end point change
         extDimLine2 = QadLine().set(dimLine2.getEndPt(), \
                                     qad_utils.getPolarPointByPtAngle(dimLine2.getEndPt(), rot, self.dimLineOffsetExtLine))

      return extDimLine1, extDimLine2


   # ============================================================================
   # getDimArcExtension
   # ============================================================================
   def getDimArcExtensions(self, dimLineArc1, dimLineArc2):
      """Returns the extensions of the dimensioning arcs by applying to the start and end (see variable dimLineOffsetExtLine)"""
      # if it is not greater than 0 or if there are no dimension lines
      if self.dimLineOffsetExtLine <= 0 or (dimLineArc1 is None and dimLineArc2 is None):
         return None, None

      extDimArc1 = None
      extDimArc2 = None
      if dimLineArc1 is not None:
         extDimArc1 = QadArc(dimLineArc1)
         extDimArc1.endAngle = dimLineArc1.startAngle
         dummyPt, dummyTg = dimLineArc1.getPointFromStart(-self.dimLineOffsetExtLine)
         extDimArc1.setStartAngleByPt(dummyPt) # starting point change
         if dimLineArc2 is None: # if the dimension line consists of only one arc
            extDimArc2 = QadArc(dimLineArc1)
            extDimArc2.startAngle = dimLineArc1.endAngle
            dummyPt, dummtTg = dimLineArc1.getPointFromEnd(self.dimLineOffsetExtLine)
            extDimArc2.setEndAngleByPt(dummyPt) # end point change

      if dimLineArc2 is not None:
         extDimArc2 = QadArc(dimLineArc2)
         extDimArc2.startAngle = dimLineArc1.endAngle
         dummyPt, dummtTg = dimLineArc2.getPointFromEnd(self.dimLineOffsetExtLine)
         dimLineArc2.setEndAngleByPt(dummyPt) # end point change

      return extDimArc1, extDimArc2


   # ============================================================================
   # getDimLineExtFeature
   # ============================================================================
   def getDimLineExtFeature(self, extLine, isExtLine1):
      """Returns the feature for extending the dimension line.
            extLine = extension line (QadLine or QadArc)
            isExtLine1 = if True it is the extension of dimension line 1 otherwise of dimension line 2
      """
      if extLine is None:
         return None

      f = QgsFeature(self.getLinearFeaturePrototype())
      g = fromQadGeomToQgsGeom(extLine, self.getLinearLayer()) # I transform the geometry
      f.setGeometry(g)

      try:
         # set the dimensioning component type
         if len(self.componentFieldName) > 0:
            f.setAttribute(self.componentFieldName, QadDimComponentEnum.DIM_LINE_EXT1 if isExtLine1 else QadDimComponentEnum.DIM_LINE_EXT2)
      except:
         pass

      try:
         # set the linetype
         if len(self.lineTypeFieldName) > 0:
            f.setAttribute(self.lineTypeFieldName, self.extLine1LineType if isExtLine1 else self.extLine2LineType)
      except:
         pass

      try:
         # set the color
         if len(self.colorFieldName) > 0:
            f.setAttribute(self.colorFieldName, self.extLineColor)
      except:
         pass

      return f


   # ============================================================================
   # FUNCTIONS FOR DIMENSION LINE EXTENSIONS - END
   # LINEAR DIMENSIONING FUNCTIONS - START
   # ============================================================================


   # ============================================================================
   # getLinearDimFeatures
   # ============================================================================
   def getLinearDimFeatures(self, canvas, dimPt1, dimPt2, linePosPt, measure = None, \
                            preferredAlignment = QadDimStyleAlignmentEnum.HORIZONTAL, \
                            dimLineRotation = 0.0):
      """dimPt1 = first point to dimension (in map units)
            dimPt2 = second point to dimension (in map units)
            linePosPt = point to indicate where the dimension line should be positioned (in map units)
            measure = indicates whether the measure is predetermined or (if = None) must be calculated
            preferredAlignment = if the dimension style is linear, indicates whether to align to the dimension points
                                 horizontally or vertically (if the dimension points form an oblique line)
            dimLineRotation = dimension line angle (default = 0)

            # linear dimension with a horizontal or vertical dimension line
            # returns a list of elements that describe the geometry of the dimension:
            # 1 list = feature of the first and second dimension points; QgsFeature 1, QgsFeature 2
            # 2 list = feature of the first and second dimension lines (the latter can be None); QgsFeature 1, QgsFeature 2
            #3 list = dimension text point feature and occupancy rectangle geometry; QgsFeature, QgsGeometry
            #4 list = feature of the first and second symbols for the dimension line (can be None); QgsFeature 1, QgsFeature 2
            # 5 list = features of the first and second extension lines (can be None); QgsFeature 1, QgsFeature 2
            #6 element = leader line feature (can be None); QgsFeature
      """
      self.dimType = QadDimTypeEnum.LINEAR

      # dimension points
      dimPt1Feature = self.getDimPointFeature(dimPt1, True) # True = first dimension point
      dimPt2Feature = self.getDimPointFeature(dimPt2, False) # False = second dimension point

      # dimension line within the extension lines
      dimLine1 = self.getDimLine(dimPt1, dimPt2, linePosPt, preferredAlignment, dimLineRotation)
      dimLine2 = None

      # text and blocks
      if measure is None:
         textValue = dimLine1.length()
      else:
         textValue = unicode(measure)

      textFeature = self.getTextFeature(textValue)
      textWidth, textHeight = qad_label.calculateLabelSize(self.getTextualLayer(), textFeature, canvas)

      # create a rectangle around the text with a buffer = self.textOffsetDist
      textWidthOffset  = textWidth + self.textOffsetDist * 2
      textHeightOffset = textHeight + self.textOffsetDist * 2

      # Returns a list of 4 elements:
      # - the first element is a list with the insertion point of the dimension text and its rotation
      # - the second element is a list with flag indicating the type of the line on which the text was placed; vedi QadDimComponentEnum
      #                       and a list of "leader" lines in case the text is outside the dimension
      # - the third element is the rotation of the first block of arrows; can be None if not visible
      # - the fourth element is the rotation of the second block of arrows; can be None if not visible
      dummy1, dummy2, block1Rot, block2Rot = self.getLinearTextAndBlocksPosition(dimPt1, dimPt2, \
                                                                                 dimLine1, \
                                                                                 textWidthOffset, textHeightOffset)

      textOffsetRectInsPt = dummy1[0]
      textRot             = dummy1[1]
      textLinearDimComponentOn = dummy2[0]
      txtLeaderLines           = dummy2[1]

      # I find the true insertion point of the text taking into account the surrounding buffer
      textInsPt = qad_utils.getPolarPointByPtAngle(textOffsetRectInsPt, textRot, self.textOffsetDist)
      textInsPt = qad_utils.getPolarPointByPtAngle(textInsPt, textRot + math.pi / 2, self.textOffsetDist)

      # text
      textGeom = QgsGeometry.fromPointXY(textInsPt)
      textFeature = self.getTextFeature(textValue, textInsPt, textRot)

      # blocchi frecce
      block1Feature = self.getSymbolFeature(dimLine1.getStartPt(), block1Rot, True, textLinearDimComponentOn) # True = first dimension point
      block2Feature = self.getSymbolFeature(dimLine1.getEndPt(), block2Rot, False, textLinearDimComponentOn) # False = second dimension point

      extLine1 = self.getExtLine(dimPt1, dimLine1.getStartPt())
      extLine2 = self.getExtLine(dimPt2, dimLine1.getEndPt())

      # create a rectangle around the text with an offset
      textOffsetRect = self.textRectToQadPolyline(textOffsetRectInsPt, textWidthOffset, textHeightOffset, textRot)

      if textLinearDimComponentOn == QadDimComponentEnum.DIM_LINE1: # dimension line ("Dimension line")
         dimLine1, dimLine2 = self.adjustLineAccordingTextRect(textOffsetRect, dimLine1, QadDimComponentEnum.DIM_LINE1)
      elif textLinearDimComponentOn == QadDimComponentEnum.EXT_LINE1: # first extension line ("Extension line 1")
         if extLine1 is not None:
            extLineRot = qad_utils.getAngleBy2Pts(dimPt1, dimLine1.getStartPt())
            extLine1 = self.getExtLine(dimPt1, qad_utils.getPolarPointByPtAngle(dimLine1.getStartPt(), extLineRot, textWidth + self.textOffsetDist))
            # change the direction of the line because getExtLine returns a line from the dimension line towards the dimension point
            reverseExtLine1 = extLine1.copy().reverse()
            extLine1, dummy = self.adjustLineAccordingTextRect(textOffsetRect, reverseExtLine1, QadDimComponentEnum.EXT_LINE1)
      elif textLinearDimComponentOn == QadDimComponentEnum.EXT_LINE2: # second extension line ("Extension line 2")
         if extLine2 is not None:
            extLineRot = qad_utils.getAngleBy2Pts(dimPt2, dimLine1.getEndPt())
            extLine2 = self.getExtLine(dimPt2, qad_utils.getPolarPointByPtAngle(dimLine1.getEndPt(), extLineRot, textWidth + self.textOffsetDist))
            # change the direction of the line because getExtLine returns a line from the dimension line towards the dimension point
            reverseExtLine2 = extLine2.copy().reverse()
            extLine2, dummy = self.adjustLineAccordingTextRect(textOffsetRect, reverseExtLine2, QadDimComponentEnum.EXT_LINE2)
      elif textLinearDimComponentOn == QadDimComponentEnum.LEADER_LINE: # dimension line used when the text is outside the dimension ("Leader")
         lastLine = txtLeaderLines.getLinearObjectAt(-1)
         lastLine, dummy = self.adjustLineAccordingTextRect(textOffsetRect, lastLine, QadDimComponentEnum.LEADER_LINE)
         txtLeaderLines.remove(-1) # replace the last element
         txtLeaderLines.append(lastLine)

      # dimension lines
      dimLine1Feature = self.getDimLineFeature(dimLine1, True, textLinearDimComponentOn) # True = first dimension line
      dimLine2Feature = self.getDimLineFeature(dimLine2, False, textLinearDimComponentOn) # False = second dimension line

      # dimension line extensions
      dimLineExt1, dimLineExt2 = self.getDimLineExtensions(dimLine1, dimLine2)
      dimLineExt1Feature = self.getDimLineExtFeature(dimLineExt1, True)
      dimLineExt2Feature = self.getDimLineExtFeature(dimLineExt2, False)

      # extension lines
      extLine1Feature = self.getExtLineFeature(extLine1, True)  # True = first extension line
      extLine2Feature = self.getExtLineFeature(extLine2, False) # False = second extension line

      # leader line
      txtLeaderLineFeature = self.getLeaderFeature(txtLeaderLines)

      dimEntity = QadDimEntity()
      dimEntity.dimStyle = self
      # features testuali
      dimEntity.textualFeature = textFeature
      # features lineari
      if dimLine1Feature is not None:
         dimEntity.linearFeatures.append(dimLine1Feature)
      if dimLine2Feature is not None:
         dimEntity.linearFeatures.append(dimLine2Feature)

      if dimLineExt1Feature is not None:
         dimEntity.linearFeatures.append(dimLineExt1Feature)
      if dimLineExt2Feature is not None:
         dimEntity.linearFeatures.append(dimLineExt2Feature)

      if extLine1Feature is not None:
         dimEntity.linearFeatures.append(extLine1Feature)
      if extLine2Feature is not None:
         dimEntity.linearFeatures.append(extLine2Feature)

      if txtLeaderLineFeature is not None:
         dimEntity.linearFeatures.append(txtLeaderLineFeature)
      # features puntuali
      dimEntity.symbolFeatures.extend([dimPt1Feature, dimPt2Feature])
      if block1Feature is not None:
         dimEntity.symbolFeatures.append(block1Feature)
      if block2Feature is not None:
         dimEntity.symbolFeatures.append(block2Feature)

      return dimEntity, QgsGeometry.fromPolygonXY([textOffsetRect.asPolyline()])


   # ============================================================================
   # addLinearDimToLayers
   # ============================================================================
   def addLinearDimToLayers(self, plugIn, dimPt1, dimPt2, linePosPt, measure = None, \
                            preferredAlignment = QadDimStyleAlignmentEnum.HORIZONTAL, \
                            dimLineRotation = 0.0):
      """Adds the features that make up a linear dimension to the layers."""
      dimEntity, textOffsetRect = self.getLinearDimFeatures(plugIn.canvas, \
                                                            dimPt1, \
                                                            dimPt2, \
                                                            linePosPt, \
                                                            measure, \
                                                            preferredAlignment, \
                                                            dimLineRotation)

      return self.addDimEntityToLayers(plugIn, dimEntity)


   # ============================================================================
   # FUNCTIONS FOR LINEAR DIMENSIONS - END
   # FUNCTIONS FOR ALIGNED DIMENSIONING - START
   # ============================================================================


   # ============================================================================
   # getAlignedDimFeatures
   # ============================================================================
   def getAlignedDimFeatures(self, canvas, dimPt1, dimPt2, linePosPt, measure = None):
      """dimPt1 = first point to dimension (in map units)
            dimPt2 = second point to dimension (in map units)
            linePosPt = point to indicate where the dimension line should be positioned (in map units)
            measure = indicates whether the measure is predetermined or (if = None) must be calculated

            # linear dimension with a horizontal or vertical dimension line
            # returns a list of elements that describe the geometry of the dimension:
            # 1 list = feature of the first and second dimension points; QgsFeature 1, QgsFeature 2
            # 2 list = feature of the first and second dimension lines (the latter can be None); QgsFeature 1, QgsFeature 2
            #3 list = dimension text point feature and occupancy rectangle geometry; QgsFeature, QgsGeometry
            #4 list = feature of the first and second symbols for the dimension line (can be None); QgsFeature 1, QgsFeature 2
            # 5 list = features of the first and second extension lines (can be None); QgsFeature 1, QgsFeature 2
            #6 element = leader line feature (can be None); QgsFeature
      """
      self.dimType = QadDimTypeEnum.ALIGNED

      # dimension points
      dimPt1Feature = self.getDimPointFeature(dimPt1, True) # True = first dimension point
      dimPt2Feature = self.getDimPointFeature(dimPt2, False) # False = second dimension point

      # dimension line within the extension lines
      dimLine1 = self.getDimLine(dimPt1, dimPt2, linePosPt)
      dimLine2 = None

      # text and blocks
      if measure is None:
         textValue = dimLine1.length()
      else:
         textValue = unicode(measure)

      textFeature = self.getTextFeature(textValue)
      textWidth, textHeight = qad_label.calculateLabelSize(self.getTextualLayer(), textFeature, canvas)

      # create a rectangle around the text with a buffer = self.textOffsetDist
      textWidthOffset  = textWidth + self.textOffsetDist * 2
      textHeightOffset = textHeight + self.textOffsetDist * 2

      # Returns a list of 4 elements:
      # - the first element is a list with the insertion point of the dimension text and its rotation
      # - the second element is a list with flag indicating the type of the line on which the text was placed; vedi QadDimComponentEnum
      #                       and a list of "leader" lines in case the text is outside the dimension
      # - the third element is the rotation of the first block of arrows; can be None if not visible
      # - the fourth element is the rotation of the second block of arrows; can be None if not visible
      dummy1, dummy2, block1Rot, block2Rot = self.getLinearTextAndBlocksPosition(dimPt1, dimPt2, \
                                                                                 dimLine1, \
                                                                                 textWidthOffset, textHeightOffset)
      textOffsetRectInsPt = dummy1[0]
      textRot             = dummy1[1]
      textLinearDimComponentOn = dummy2[0]
      txtLeaderLines           = dummy2[1]

      # I find the true insertion point of the text taking into account the surrounding buffer
      textInsPt = qad_utils.getPolarPointByPtAngle(textOffsetRectInsPt, textRot, self.textOffsetDist)
      textInsPt = qad_utils.getPolarPointByPtAngle(textInsPt, textRot + math.pi / 2, self.textOffsetDist)

      # text
      textGeom = QgsGeometry.fromPointXY(textInsPt)
      textFeature = self.getTextFeature(textValue, textInsPt, textRot)

      # blocchi frecce
      block1Feature = self.getSymbolFeature(dimLine1.getStartPt(), block1Rot, True, textLinearDimComponentOn) # True = first dimension point
      block2Feature = self.getSymbolFeature(dimLine1.getEndPt(), block2Rot, False, textLinearDimComponentOn) # False = second dimension point

      extLine1 = self.getExtLine(dimPt1, dimLine1.getStartPt())
      extLine2 = self.getExtLine(dimPt2, dimLine1.getEndPt())

      # create a rectangle around the text with an offset
      textOffsetRect = self.textRectToQadPolyline(textOffsetRectInsPt, textWidthOffset, textHeightOffset, textRot)

      if textLinearDimComponentOn == QadDimComponentEnum.DIM_LINE1: # dimension line ("Dimension line")
         dimLine1, dimLine2 = self.adjustLineAccordingTextRect(textOffsetRect, dimLine1, QadDimComponentEnum.DIM_LINE1)
      elif textLinearDimComponentOn == QadDimComponentEnum.EXT_LINE1: # first extension line ("Extension line 1")
         if extLine1 is not None:
            extLineRot = qad_utils.getAngleBy2Pts(dimPt1, dimLine1.getStartPt())
            extLine1 = self.getExtLine(dimPt1, qad_utils.getPolarPointByPtAngle(dimLine1.getStartPt(), extLineRot, textWidth + self.textOffsetDist))
            # change the direction of the line because getExtLine returns a line from the dimension line towards the dimension point
            reverseExtLine1 = extLine1.copy().reverse()
            extLine1, dummy = self.adjustLineAccordingTextRect(textOffsetRect, reverseExtLine1, QadDimComponentEnum.EXT_LINE1)
      elif textLinearDimComponentOn == QadDimComponentEnum.EXT_LINE2: # second extension line ("Extension line 2")
         if extLine2 is not None:
            extLineRot = qad_utils.getAngleBy2Pts(dimPt2, dimLine1.getEndPt())
            extLine2 = self.getExtLine(dimPt2, qad_utils.getPolarPointByPtAngle(dimLine1.getEndPt(), extLineRot, textWidth + self.textOffsetDist))
            # change the direction of the line because getExtLine returns a line from the dimension line towards the dimension point
            reverseExtLine2 = extLine2.copy().reverse()
            extLine2, dummy = self.adjustLineAccordingTextRect(textOffsetRect, reverseExtLine2, QadDimComponentEnum.EXT_LINE2)
      elif textLinearDimComponentOn == QadDimComponentEnum.LEADER_LINE: # dimension line used when the text is outside the dimension ("Leader")
         lastLine = txtLeaderLines.getLinearObjectAt(-1)
         lastLine, dummy = self.adjustLineAccordingTextRect(textOffsetRect, lastLine, QadDimComponentEnum.LEADER_LINE)
         txtLeaderLines.remove(-1) # replace the last element
         txtLeaderLines.append(lastLine)

      # dimension lines
      dimLine1Feature = self.getDimLineFeature(dimLine1, True, textLinearDimComponentOn) # True = first dimension line
      dimLine2Feature = self.getDimLineFeature(dimLine2, False, textLinearDimComponentOn) # False = second dimension line

      # dimension line extensions
      dimLineExt1, dimLineExt2 = self.getDimLineExtensions(dimLine1, dimLine2)
      dimLineExt1Feature = self.getDimLineExtFeature(dimLineExt1, True)
      dimLineExt2Feature = self.getDimLineExtFeature(dimLineExt2, False)

      # extension lines
      extLine1Feature = self.getExtLineFeature(extLine1, True)  # True = first extension line
      extLine2Feature = self.getExtLineFeature(extLine2, False) # False = second extension line

      # leader line
      txtLeaderLineFeature = self.getLeaderFeature(txtLeaderLines)

      dimEntity = QadDimEntity()
      dimEntity.dimStyle = self
      # features testuali
      dimEntity.textualFeature = textFeature
      # features lineari
      if dimLine1Feature is not None:
         dimEntity.linearFeatures.append(dimLine1Feature)
      if dimLine2Feature is not None:
         dimEntity.linearFeatures.append(dimLine2Feature)

      if dimLineExt1Feature is not None:
         dimEntity.linearFeatures.append(dimLineExt1Feature)
      if dimLineExt2Feature is not None:
         dimEntity.linearFeatures.append(dimLineExt2Feature)

      if extLine1Feature is not None:
         dimEntity.linearFeatures.append(extLine1Feature)
      if extLine2Feature is not None:
         dimEntity.linearFeatures.append(extLine2Feature)

      if txtLeaderLineFeature is not None:
         dimEntity.linearFeatures.append(txtLeaderLineFeature)
      # features puntuali
      dimEntity.symbolFeatures.extend([dimPt1Feature, dimPt2Feature])
      if block1Feature is not None:
         dimEntity.symbolFeatures.append(block1Feature)
      if block2Feature is not None:
         dimEntity.symbolFeatures.append(block2Feature)

      return dimEntity, QgsGeometry.fromPolygonXY([textOffsetRect.asPolyline()])


   # ============================================================================
   # addAlignedDimToLayers
   # ============================================================================
   def addAlignedDimToLayers(self, plugIn, dimPt1, dimPt2, linePosPt, measure = None, \
                            preferredAlignment = QadDimStyleAlignmentEnum.HORIZONTAL, \
                            dimLineRotation = 0.0):
      """dimPt1 = first point to dimension (in map units)
            dimPt2 = second point to dimension (in map units)
            linePosPt = point to indicate where the dimension line should be positioned (in map units)
            measure = indicates whether the measure is predetermined or (if = None) must be calculated
            preferredAlignment = if the dimension style is linear, indicates whether to align to the dimension points
                                 horizontally or vertically (if the dimension points form an oblique line)
            dimLineRotation = dimension line angle (default = 0)

            Adds the features that make up an aligned dimension to the layers.
      """
      dimEntity, textOffsetRect = self.getAlignedDimFeatures(plugIn.canvas, \
                                                             dimPt1, \
                                                             dimPt2, \
                                                             linePosPt, \
                                                             measure)

      return self.addDimEntityToLayers(plugIn, dimEntity)


   # ============================================================================
   # FUNCTIONS FOR ALIGNED DIMENSIONING - END
   # FUNCTIONS FOR ARC DIMENSIONS - START
   # ============================================================================


   # ============================================================================
   # getArcDimFeatures
   # ============================================================================
   def getArcDimFeatures(self, canvas, dimArc, linePosPt, measure = None, arcLeader = None):
      """dimArc = QadArc arc object to dimension (in map units)
            linePosPt = point to indicate where the dimension line should be positioned (in map units)
            measure = indicates whether the measure is predetermined or (if = None) must be calculated
            arcLeader = indicates whether the leader line should be drawn from the dimension to the arc

            # arc dimension to measure the length of an arc or part of it
            # returns a list of elements that describe the geometry of the dimension:
            # 1 list = feature of the first and second dimension points; QgsFeature 1, QgsFeature 2
            # 2 list = feature of the first and second dimension lines (the latter can be None); QgsFeature 1, QgsFeature 2
            #3 list = dimension text point feature and occupancy rectangle geometry; QgsFeature, QgsGeometry
            #4 list = feature of the first and second symbols for the dimension line (can be None); QgsFeature 1, QgsFeature 2
            # 5 list = features of the first and second extension lines (can be None); QgsFeature 1, QgsFeature 2
            #6 element = leader line feature (can be None); QgsFeature
      """
      self.dimType = QadDimTypeEnum.ARC_LENTGH

      # dimension line in the form of an arc
      dimLineArc1 = self.getDimLineForArc(dimArc, linePosPt)
      dimLineArc1StartPt = dimLineArc1.getStartPt()
      dimLineArc1EndPt = dimLineArc1.getEndPt()
      dimLineArc2 = None

      dimPt1 = dimArc.getStartPt()
      dimPt2 = dimArc.getEndPt()

      # dimension points
      dimPt1Feature = self.getDimPointFeature(dimPt1, True) # True = first dimension point
      dimPt2Feature = self.getDimPointFeature(dimPt2, False) # False = second dimension point

      # text and blocks
      if measure is None:
         textValue = dimArc.length()
      else:
         textValue = unicode(measure)

      textFeature = self.getTextFeature(textValue)
      textWidth, textHeight = qad_label.calculateLabelSize(self.getTextualLayer(), textFeature, canvas)

      # create a rectangle around the text with a buffer = self.textOffsetDist
      textWidthOffset  = textWidth + self.textOffsetDist * 2
      textHeightOffset = textHeight + self.textOffsetDist * 2

      arcSymbRadius = textHeight * 2 / 4
      if self.arcSymbPos == QadDimStyleArcSymbolPosEnum.BEFORE_TEXT:
         textWidthOffset = textWidthOffset + self.textOffsetDist + 2 * arcSymbRadius
      elif self.arcSymbPos == QadDimStyleArcSymbolPosEnum.ABOVE_TEXT:
         textHeightOffset = textHeightOffset + self.textOffsetDist + arcSymbRadius

      # Returns a list of 4 elements:
      # - the first element is a list with the insertion point of the dimension text and its rotation
      # - the second element is a list with flag indicating the type of the line on which the text was placed; vedi QadDimComponentEnum
      #                       and a list of "leader" lines in case the text is outside the dimension
      # - the third element is the rotation of the first block of arrows; can be None if not visible
      # - the fourth element is the rotation of the second block of arrows; can be None if not visible
      dummy1, dummy2, block1Rot, block2Rot = self.getArcTextAndBlocksPosition(dimArc, dimLineArc1, \
                                                                              textWidthOffset, textHeightOffset)
      textOffsetRectInsPt = dummy1[0]
      textRot             = dummy1[1]
      textLinearDimComponentOn = dummy2[0]
      txtLeaderLines           = dummy2[1]

      # I find the true insertion point of the text taking into account the surrounding buffer
      if self.arcSymbPos == QadDimStyleArcSymbolPosEnum.BEFORE_TEXT:
         textInsPt = qad_utils.getPolarPointByPtAngle(textOffsetRectInsPt, textRot, self.textOffsetDist + self.textOffsetDist + 2 * arcSymbRadius)
         textInsPt = qad_utils.getPolarPointByPtAngle(textInsPt, textRot + math.pi / 2, self.textOffsetDist)
      else:
         textInsPt = qad_utils.getPolarPointByPtAngle(textOffsetRectInsPt, textRot, self.textOffsetDist)
         textInsPt = qad_utils.getPolarPointByPtAngle(textInsPt, textRot + math.pi / 2, self.textOffsetDist)

      # text
      textGeom = QgsGeometry.fromPointXY(textInsPt)
      textFeature = self.getTextFeature(textValue, textInsPt, textRot)

      # blocchi frecce
      block1Feature = self.getSymbolFeature(dimLineArc1StartPt, block1Rot, True, textLinearDimComponentOn) # True = first dimension point
      block2Feature = self.getSymbolFeature(dimLineArc1EndPt, block2Rot, False, textLinearDimComponentOn) # False = second dimension point

      extLine1 = self.getExtLine(dimPt1, dimLineArc1StartPt)
      extLine2 = self.getExtLine(dimPt2, dimLineArc1EndPt)

      # create a rectangle around the text with an offset
      textOffsetRect = self.textRectToQadPolyline(textOffsetRectInsPt, textWidthOffset, textHeightOffset, textRot)

      if textLinearDimComponentOn == QadDimComponentEnum.DIM_LINE1: # dimension line ("Dimension line")
         dimLineArc1, dimLineArc2 = self.adjustArcAccordingTextRect(textOffsetRect, dimLineArc1, QadDimComponentEnum.DIM_LINE1)
      elif textLinearDimComponentOn == QadDimComponentEnum.EXT_LINE1: # first extension line ("Extension line 1")
         if extLine1 is not None:
            extLineRot = qad_utils.getAngleBy2Pts(dimPt1, dimLineArc1StartPt)
            extLine1 = self.getExtLine(dimPt1, qad_utils.getPolarPointByPtAngle(dimLineArc1StartPt, extLineRot, textWidth + self.textOffsetDist))
            # change the direction of the line because getExtLine returns a line from the dimension line towards the dimension point
            reverseExtLine1 = extLine1.copy().reverse()
            extLine1, dummy = self.adjustLineAccordingTextRect(textOffsetRect, reverseExtLine1, QadDimComponentEnum.EXT_LINE1)
      elif textLinearDimComponentOn == QadDimComponentEnum.EXT_LINE2: # second extension line ("Extension line 2")
         if extLine2 is not None:
            extLineRot = qad_utils.getAngleBy2Pts(dimPt2, dimLineArc1EndPt)
            extLine2 = self.getExtLine(dimPt2, qad_utils.getPolarPointByPtAngle(dimLineArc1EndPt, extLineRot, textWidth + self.textOffsetDist))
            # change the direction of the line because getExtLine returns a line from the dimension line towards the dimension point
            reverseExtLine2 = extLine2.copy().reverse()
            extLine2, dummy = self.adjustLineAccordingTextRect(textOffsetRect, reverseExtLine2, QadDimComponentEnum.EXT_LINE2)
      elif textLinearDimComponentOn == QadDimComponentEnum.LEADER_LINE: # dimension line used when the text is outside the dimension ("Leader")
         lastLine = txtLeaderLines.getLinearObjectAt(-1)
         lastLine, dummy = self.adjustLineAccordingTextRect(textOffsetRect, lastLine, QadDimComponentEnum.LEADER_LINE)
         txtLeaderLines.remove(-1) # replace the last element
         txtLeaderLines.append(lastLine)

      # dimension lines
      if dimLineArc1 is None:
         dimLine1Feature = None
      else:
         dimLine1Feature = self.getDimLineFeature(dimLineArc1, True, textLinearDimComponentOn) # True = first dimension line

      if dimLineArc2 is None:
         dimLine2Feature = None
      else:
         dimLine2Feature = self.getDimLineFeature(dimLineArc2, False, textLinearDimComponentOn) # False = second dimension line

      # dimension line extensions
      dimArcExt1, dimArcExt2 = self.getDimArcExtensions(dimLineArc1, dimLineArc2)
      if dimArcExt1 is None:
         dimLineExt1Feature = None
      else:
         dimLineExt1Feature = self.getDimLineExtFeature(dimArcExt1, True)

      if dimArcExt2 is None:
         dimLineExt2Feature = None
      else:
         dimLineExt2Feature = self.getDimLineExtFeature(dimArcExt2, False)

      # extension lines
      extLine1Feature = self.getExtLineFeature(extLine1, True)  # True = first extension line
      extLine2Feature = self.getExtLineFeature(extLine2, False) # False = second extension line

      # leader line
      txtLeaderLineFeature = self.getLeaderFeature(txtLeaderLines, QadDimComponentEnum.ARC_LEADER_LINE)


      # arc leader line
      arcLeaderLineFeature  = None
      arcLeaderBlockFeature = None
      if arcLeader: # if you want the line that joins the text to the arc to be dimensioned
         arcLeaderLine = self.getArcLeaderLine(textOffsetRectInsPt, dimArc)
         if arcLeaderLine is not None:
            arcLeaderLines = QadPolyline()
            arcLeaderLines.append(arcLeaderLine)
            arcLeaderLineFeature = self.getLeaderFeature(arcLeaderLines)
            arcLeaderBlockFeature = self.getLeaderSymbolFeature(arcLeaderLine.getEndPt(), \
                                                                arcLeaderLine.getTanDirectionOnPt())
      # bow symbol
      arcSymbolLineFeature = None
      if self.arcSymbPos == QadDimStyleArcSymbolPosEnum.BEFORE_TEXT:
         arc = QadArc()
         arcPt1 = qad_utils.getPolarPointByPtAngle(textInsPt, textRot, - self.textOffsetDist)
         arcCenter = qad_utils.getPolarPointByPtAngle(arcPt1, textRot, - arcSymbRadius)
         arcPt2 = qad_utils.getPolarPointByPtAngle(arcCenter, textRot, - arcSymbRadius)
         arc.fromStartCenterEndPts(arcPt1, arcCenter, arcPt2)
         arcSymbolLineFeature = self.getArcSymbolLineFeature(arc)
      elif self.arcSymbPos == QadDimStyleArcSymbolPosEnum.ABOVE_TEXT:
         arc = QadArc()
         arcCenter = qad_utils.getPolarPointByPtAngle(textInsPt, textRot, textWidth / 2)
         arcCenter = qad_utils.getPolarPointByPtAngle(arcCenter, textRot + math.pi / 2, arcSymbRadius + self.textOffsetDist)
         arcPt1 = qad_utils.getPolarPointByPtAngle(arcCenter, textRot, arcSymbRadius)
         arcPt2 = qad_utils.getPolarPointByPtAngle(arcCenter, textRot, - arcSymbRadius)
         arc.fromStartCenterEndPts(arcPt1, arcCenter, arcPt2)
         arcSymbolLineFeature = self.getArcSymbolLineFeature(arc)

      dimEntity = QadDimEntity()
      dimEntity.dimStyle = self
      # features testuali
      dimEntity.textualFeature = textFeature
      # features lineari
      if dimLine1Feature is not None:
         dimEntity.linearFeatures.append(dimLine1Feature)
      if dimLine2Feature is not None:
         dimEntity.linearFeatures.append(dimLine2Feature)

      if dimLineExt1Feature is not None:
         dimEntity.linearFeatures.append(dimLineExt1Feature)
      if dimLineExt2Feature is not None:
         dimEntity.linearFeatures.append(dimLineExt2Feature)

      if extLine1Feature is not None:
         dimEntity.linearFeatures.append(extLine1Feature)
      if extLine2Feature is not None:
         dimEntity.linearFeatures.append(extLine2Feature)

      if txtLeaderLineFeature is not None:
         dimEntity.linearFeatures.append(txtLeaderLineFeature)
      if arcLeaderLineFeature is not None:
         dimEntity.linearFeatures.append(arcLeaderLineFeature)
      if arcSymbolLineFeature is not None:
         dimEntity.linearFeatures.append(arcSymbolLineFeature)
      # features puntuali
      dimEntity.symbolFeatures.extend([dimPt1Feature, dimPt2Feature])
      if block1Feature is not None:
         dimEntity.symbolFeatures.append(block1Feature)
      if block2Feature is not None:
         dimEntity.symbolFeatures.append(block2Feature)
      if arcLeaderBlockFeature is not None:
         dimEntity.symbolFeatures.append(arcLeaderBlockFeature)

      return dimEntity, QgsGeometry.fromPolygonXY([textOffsetRect.asPolyline()])


   # ============================================================================
   # addArcDimToLayers
   # ============================================================================
   def addArcDimToLayers(self, plugIn, dimArc, linePosPt, measure = None, arcLeader = False):
      """dimArc = arc to dimension (in map units)
            linePosPt = point to indicate where the dimension line should be positioned (in map units)
            measure = indicates whether the measure is predetermined or (if = None) must be calculated
            arcLeader = indicates whether the leader line should be drawn from the dimension to the arc

            Adds the features that make up an aligned dimension to the layers.
      """
      dimEntity, textOffsetRect = self.getArcDimFeatures(plugIn.canvas, \
                                                         dimArc, \
                                                         linePosPt, \
                                                         measure, \
                                                         arcLeader)

      return self.addDimEntityToLayers(plugIn, dimEntity)


   # ============================================================================
   # FUNCTIONS FOR ARC - END DIMENSIONING
   # FUNCTIONS FOR RADIUS DIMENSIONS - START
   # ============================================================================


   # ============================================================================
   # getCenterMarkerLinesFeature
   # ============================================================================
   def getCenterMarkerLinesFeature(self, canvas, dimObj, linePosPt):
      """center = point of the center of the arc or circle to dimension (in map units)
            linePosPt = point to indicate where the dimension line should be positioned (in map units)
            Returns a list of features representing center marker lines
      """
      if self.centerMarkSize == 0.0: # 0 = nothing
         return []
      # if linePosPos is < the radius, the center marker must not be inserted
      if qad_utils.getDistance(dimObj.center , linePosPt) < dimObj.radius:
         return []

      geoms = []
      if self.centerMarkSize > 0.0: # center marker size
         horizLine = QadLine().set(QgsPointXY(dimObj.center.x() - self.centerMarkSize, dimObj.center.y()), \
                                   QgsPointXY(dimObj.center.x() + self.centerMarkSize, dimObj.center.y()))
         geoms.append(horizLine)

         vertLine = QadLine().set(QgsPointXY(dimObj.center.x(), dimObj.center.y() - self.centerMarkSize), \
                                  QgsPointXY(dimObj.center.x(), dimObj.center.y() + self.centerMarkSize))
         geoms.append(vertLine)
      else: # axis line size
         centerMarkSize = -self.centerMarkSize

         horizLine = QadLine().set(QgsPointXY(dimObj.center.x() - centerMarkSize, dimObj.center.y()), \
                                   QgsPointXY(dimObj.center.x() + centerMarkSize, dimObj.center.y()))
         geoms.append(horizLine)

         vertLine = QadLine().set(QgsPointXY(dimObj.center.x(), dimObj.center.y() - centerMarkSize), \
                                  QgsPointXY(dimObj.center.x(), dimObj.center.y() + centerMarkSize))
         geoms.append(vertLine)

         if (2 * centerMarkSize) < dimObj.radius:
            horizLine = QadLine().set(QgsPointXY(dimObj.center.x() - (2 * centerMarkSize), dimObj.center.y()), \
                                      QgsPointXY(dimObj.center.x() - dimObj.radius - centerMarkSize, dimObj.center.y()))
            geoms.append(horizLine)

            horizLine = QadLine().set(QgsPointXY(dimObj.center.x() + (2 * centerMarkSize), dimObj.center.y()), \
                                      QgsPointXY(dimObj.center.x() + dimObj.radius + centerMarkSize, dimObj.center.y()))
            geoms.append(horizLine)

            vertLine = QadLine().set(QgsPointXY(dimObj.center.x(), dimObj.center.y() - (2 * centerMarkSize)), \
                                     QgsPointXY(dimObj.center.x(), dimObj.center.y() - dimObj.radius - centerMarkSize))
            geoms.append(vertLine)

            vertLine = QadLine().set(QgsPointXY(dimObj.center.x(), dimObj.center.y() + (2 * centerMarkSize)), \
                                     QgsPointXY(dimObj.center.x(), dimObj.center.y() + dimObj.radius + centerMarkSize))
            geoms.append(vertLine)

      features = []
      for g in geoms:
         f = QgsFeature(self.getLinearFeaturePrototype())
         f.setGeometry(fromQadGeomToQgsGeom(g, self.getLinearLayer())) # I transform the geometry

         try:
            # set the dimensioning component type
            if len(self.componentFieldName) > 0:
               f.setAttribute(self.componentFieldName, QadDimComponentEnum.CENTER_MARKER_LINE)
         except:
            pass

         try:
            # set the linetype
            if len(self.lineTypeFieldName) > 0:
               f.setAttribute(self.lineTypeFieldName, self.dimLineLineType)
         except:
            pass

         try:
            # set the color
            if len(self.colorFieldName) > 0:
               f.setAttribute(self.colorFieldName, self.dimLineColor)
         except:
            pass

         features.append(f)

      return features


   # ============================================================================
   # getRadiusDimFeatures
   # ============================================================================
   def getRadiusDimFeatures(self, canvas, dimObj, linePosPt, measure = None):
      """dimObj = arc circle object to dimension (in map units)
            linePosPt = point to indicate where the dimension line should be positioned (in map units)
            measure = indicates whether the measure is predetermined or (if = None) must be calculated

            # radius dimension to measure the length of an arc or circle radius
            # returns a list of elements that describe the geometry of the dimension:
            # 1 list = feature of the first and second dimension points; QgsFeature 1, QgsFeature 2
            # 2 list = feature of the first and second dimension lines (the latter can be None); QgsFeature 1, QgsFeature 2
            #3 list = dimension text point feature and occupancy rectangle geometry; QgsFeature, QgsGeometry
            #4 list = feature of the first and second symbols for the dimension line (can be None); QgsFeature 1, QgsFeature 2
            # 5 list = features of the first and second extension lines (can be None); QgsFeature 1, QgsFeature 2
            #6 element = leader line feature (can be None); QgsFeature
      """
      self.dimType = QadDimTypeEnum.RADIUS

      # center marker
      dimCenterMarkers = self.getCenterMarkerLinesFeature(canvas, dimObj, linePosPt)

      # dimension points
      dimPt1 = dimObj.center
      angle = qad_utils.getAngleBy2Pts(dimPt1, linePosPt)
      dimPt2 = qad_utils.getPolarPointByPtAngle(dimPt1, angle, dimObj.radius) # point on the curve

      dimPt1Feature = self.getDimPointFeature(dimPt1, True) # True = first dimension point
      dimPt2Feature = self.getDimPointFeature(dimPt2, False) # False = second dimension point

      # if dimension block 1 and dimension block 2 are visible
      if self.block1Name != "" and self.block1Name != "":
         blockRot = qad_utils.getAngleBy2Pts(linePosPt, dimPt2)
         if qad_utils.getDistance(linePosPt, dimPt2) <= 2 * self.getBlock2Size():
            linePosPt = qad_utils.getPolarPointByPtAngle(dimPt2, blockRot + math.pi, 2 * self.getBlock2Size())
         # arrow block
         blockFeature = self.getSymbolFeature(dimPt2, blockRot, \
                                              True if self.block1Name != "" else False, \
                                              QadDimComponentEnum.LEADER_LINE)
      else:
         blockFeature = None

      # dimension line
      dimLine = QadLine().set(linePosPt, dimPt2)
      # dimension line 1 or dimension line 2 must be visible
      if self.dimLine1Show == True or self.dimLine2Show == True:
         dimLineFeature = self.getDimLineFeature(dimLine, self.dimLine1Show, QadDimComponentEnum.LEADER_LINE)
      else: # the dimension line is invisible
         dimLineFeature = None

      # extension line
      extLineFeature = None
      if dimObj.whatIs() == "ARC":
         extArc = self.getExtArc(dimObj, linePosPt)
         # extension lines
         if extArc is not None:
            extLineFeature = self.getExtLineFeature(extArc, True)  # True = first extension line

      # text and blocks
      if measure is None:
         textValue = QadMsg.translate("Command_DIM", "R") + self.getFormattedText(dimObj.radius) # I put the R of Radius before it
      else:
         textValue = unicode(measure)

      textFeature = self.getTextFeature(textValue)
      textWidth, textHeight = qad_label.calculateLabelSize(self.getTextualLayer(), textFeature, canvas)

      # create a rectangle around the text with a buffer = self.textOffsetDist
      textWidthOffset  = textWidth + self.textOffsetDist * 2
      textHeightOffset = textHeight + self.textOffsetDist * 2

      # create a dummy line for text positioning
      # I make it half the length of the text to force the text outside the dummy line
      pt = qad_utils.getPolarPointByPtAngle(linePosPt, angle + math.pi, textWidthOffset / 2)

      # Returns a list of 4 elements:
      # - the first element is a list with the insertion point of the dimension text and its rotation
      # - the second element is a list with flag indicating the type of the line on which the text was placed; vedi QadDimComponentEnum
      #                       and a list of "leader" lines in case the text is outside the dimension
      dummy1, dummy2, block1Rot, block2Rot = self.getRadiusTextAndBlocksPosition(QadLine().set(linePosPt, pt), \
                                                                                 textWidthOffset, textHeightOffset)
      textOffsetRectInsPt = dummy1[0]
      textRot             = dummy1[1]
      textLinearDimComponentOn = dummy2[0]
      txtLeaderLines           = dummy2[1]

      # I find the true insertion point of the text taking into account the surrounding buffer
      textInsPt = qad_utils.getPolarPointByPtAngle(textOffsetRectInsPt, textRot, self.textOffsetDist)
      textInsPt = qad_utils.getPolarPointByPtAngle(textInsPt, textRot + math.pi / 2, self.textOffsetDist)

      # text
      textGeom = QgsGeometry.fromPointXY(textInsPt)
      textFeature = self.getTextFeature(textValue, textInsPt, textRot)

      # create a rectangle around the text with an offset
      textOffsetRect = self.textRectToQadPolyline(textOffsetRectInsPt, textWidthOffset, textHeightOffset, textRot)

      lastLine = txtLeaderLines.getLinearObjectAt(-1)
      lastLine, dummy = self.adjustLineAccordingTextRect(textOffsetRect, lastLine, QadDimComponentEnum.LEADER_LINE)
      txtLeaderLines.remove(-1) # replace the last element
      txtLeaderLines.append(lastLine)

      # leader line
      txtLeaderLineFeature = self.getLeaderFeature(txtLeaderLines)

      dimEntity = QadDimEntity()
      dimEntity.dimStyle = self
      # features testuali
      dimEntity.textualFeature = textFeature
      # features lineari
      if dimLineFeature is not None:
         dimEntity.linearFeatures.append(dimLineFeature)
      if extLineFeature is not None:
         dimEntity.linearFeatures.append(extLineFeature)
      if txtLeaderLineFeature is not None:
         dimEntity.linearFeatures.append(txtLeaderLineFeature)
      for dimCenterMarker in dimCenterMarkers:
         dimEntity.linearFeatures.append(dimCenterMarker)
      # features puntuali
      dimEntity.symbolFeatures.extend([dimPt1Feature, dimPt2Feature])
      if blockFeature is not None:
         dimEntity.symbolFeatures.append(blockFeature)

      return dimEntity, QgsGeometry.fromPolygonXY([textOffsetRect.asPolyline()])


   # ============================================================================
   # addRadiusDimToLayers
   # ============================================================================
   def addRadiusDimToLayers(self, plugIn, dimObj, linePosPt, measure = None):
      """dimObj = arc circle object to dimension (in map units)
            linePosPt = point to indicate where the dimension line should be positioned (in map units)
            measure = indicates whether the measure is predetermined or (if = None) must be calculated

            Adds the features that make up an aligned dimension to the layers.
      """
      dimEntity, textOffsetRect = self.getRadiusDimFeatures(plugIn.canvas, \
                                                            dimObj, \
                                                            linePosPt, \
                                                            measure)

      return self.addDimEntityToLayers(plugIn, dimEntity)


   # ============================================================================
   # FUNCTIONS FOR DIMENSIONING RADIUS - END
   # ============================================================================


# ===============================================================================
# QadDimStylesClass list of dimension styles
# ===============================================================================
class QadDimStylesClass():

   def __init__(self, dimStyleList = None):
      if dimStyleList is None:
         self.dimStyleList = []
      else:
         self.set(dimStyleList)


   def __del__(self):
      if dimStyleList is None:
         del self.dimStyleList[:]


   def isEmpty(self):
      return True if self.count() == 0 else False


   def count(self):
      return len(self.dimStyleList)


   def clear(self):
      del self.dimStyleList[:]


   def findDimStyle(self, dimStyleName):
      """The function, given a dimensioning style name, searces for it in the list and,
            if successful, returns the dimensioning style.
      """
      for dimStyle in self.dimStyleList:
         if dimStyle.name == dimStyleName:
            return dimStyle
      return None


   def addDimStyle(self, dimStyle, toFile = False, filePath = ""):
      d = self.findDimStyle(dimStyle)
      if d is None:
         self.dimStyleList.append(QadDimStyle(dimStyle))
         if toFile:
            if dimStyle.save(filePath, False) == False: # without overwriting the file
               return False
         return True

      return False


   # ============================================================================
   # removeDimStyle
   # ============================================================================
   def removeDimStyle(self, dimStyleName, toFile = False):
      i = 0
      for dimStyle in self.dimStyleList:
         if dimStyle.name == dimStyleName:
            del self.dimStyleList[i]
            if toFile:
               dimStyle.remove()
            return True
         else:
            i = i + 1

      return False


   # ============================================================================
   # renameDimStyle
   # ============================================================================
   def renameDimStyle(self, dimStyleName, newDimStyleName):
      if dimStyleName == newDimStyleName: # same name
         return True

      if self.findDimStyle(newDimStyleName) is not None:
         return False
      dimStyle = self.findDimStyle(dimStyleName)
      if dimStyle is None:
         return False
      return dimStyle.rename(newDimStyleName)


   # ============================================================================
   # load
   # ============================================================================
   def load(self, dir = None, append = False):
      """Loads the settings of all dimensioning styles present in the indicated directory.
            if dir = None if there is a loaded project the path is that of the project otherwise + the local path of qad
      """
      if dir is None:
         if append == False:
            self.clear()

         # if there is a loaded project with a filesystem path, use that path
         projectFilePath = QgsProject.instance().absoluteFilePath()
         path = "" if len(projectFilePath) == 0 else QFileInfo(projectFilePath).absolutePath()
         if len(path) > 0:
            path += "/;"
         path += QgsApplication.qgisSettingsDirPath() + "python/plugins/qad/"

         # list of directories separated by ";"
         dirList = path.strip().split(";")
         for _dir in dirList:
            self.load(_dir, True) # in append
      else:
         _dir = QDir.cleanPath(dir)
         if _dir == "":
            return False

         if _dir.endswith("/") == False:
            _dir = _dir + "/"

         if not os.path.exists(_dir):
            return False

         if append == False:
            self.clear()
         dimStyle = QadDimStyle()

         fileNames = os.listdir(_dir)
         for fileName in fileNames:
            if fileName.endswith(".dim"):
               path = _dir + fileName
               if dimStyle.load(path) == True:
                  if self.findDimStyle(dimStyle.name) is None:
                     self.addDimStyle(dimStyle)

      return True


   # ============================================================================
   # getDimIdByEntity
   # ============================================================================
   def getDimIdByEntity(self, entity):
      """The function, given an entity, checks whether it is part of a dimensioning style of the list and,
            if successful, returns the dimensioning style and dimensioning code otherwise None, None.
      """
      for dimStyle in self.dimStyleList:
         dimId = dimStyle.getDimIdByEntity(entity)
         if dimId is not None:
            return dimStyle, dimId
      return None, None


   # ============================================================================
   # isDimEntity
   # ============================================================================
   def isDimEntity(self, entity):
      """The function, given an entity, checks whether it is part of a dimensioning style of the list and,
            if successful, it returns true otherwise False.
      """
      dimStyle, dimId = self.getDimIdByEntity(entity)
      if dimStyle is None or dimId is None:
         return False
      else:
         return True


   # ============================================================================
   # getDimEntity
   # ============================================================================
   def getDimEntity(self, layer, fid = None):
      """the function can be called in 2 ways:
               with a single parameter of type QadEntity
               with two parameters, the first QgsVectorLayer and the second the feature id
      """
      # check if the entity belongs to a dimensioning style
      if isinstance(layer, QgsVectorLayer):
         entity = QadEntity()
         entity.set(layer, fid)
         dimStyle, dimId = self.getDimIdByEntity(entity)
      else: # the layer parameter can be a QadEntity object
         dimStyle, dimId = self.getDimIdByEntity(layer)

      if (dimStyle is None) or (dimId is None):
         return None

      dimEntity = QadDimEntity()
      if dimEntity.initByDimId(dimStyle, dimId) == False:
         return None

      return dimEntity


   # ============================================================================
   # getDimListByLayer
   # ============================================================================
   def getDimListByLayer(self, layer):
      """The function, given a layer, checks whether it is part of one or more dimensioning styles in the list and,
            if successful, it returns the list of dimensioning styles it belongs to.
      """
      result = []
      for dimStyle in self.dimStyleList:
         if dimStyle.isDimLayer(layer):
            if dimStyle not in result:
               result.append(dimStyle)

      return result


   # ============================================================================
   # addAllDimComponentsToEntitySet
   # ============================================================================
   def addAllDimComponentsToEntitySet(self, entitySet, onlyEditableLayers):
      """The function checks whether the entities that are part of an entitySet are also part of dimensioning and,
            if so, adds all dimension components to the entitySet.
      """
      elaboratedDimEntitySet = QadEntitySet() # list of processed dimension entities
      entity = QadEntity()
      for layerEntitySet in entitySet.layerEntitySetList:
         # check if the layer belongs to one or more dimensioning styles
         dimStyleList = self.getDimListByLayer(layerEntitySet.layer)
         for dimStyle in dimStyleList: # for all dimension styles
            if dimStyle is not None:
               remove = False
               if onlyEditableLayers == True:
                  # if even just one layer is not editable
                  if dimStyle.getTextualLayer().isEditable() == False or \
                     dimStyle.getSymbolLayer().isEditable() == False or \
                     dimStyle.getLinearLayer().isEditable() == False:
                     remove = True
               features = layerEntitySet.getFeatureCollection()
               for feature in features:
                  entity.set(layerEntitySet.layer, feature.id())
                  if not elaboratedDimEntitySet.containsEntity(entity):
                     dimId = dimStyle.getDimIdByEntity(entity)
                     if dimId is not None:
                        dimEntitySet = dimStyle.getEntitySet(dimId)
                        if remove == False:
                           entitySet.unite(dimEntitySet)
                        else:
                           entitySet.subtract(dimEntitySet)

                        elaboratedDimEntitySet.unite(dimEntitySet)


   # ============================================================================
   # removeAllDimLayersFromEntitySet
   # ============================================================================
   def removeAllDimLayersFromEntitySet(self, entitySet):
      """The function removes all entities that are part of dimensions from the entitySet."""
      for dimStyle in self.dimStyleList:
         entitySet.removeLayerEntitySet(dimStyle.getTextualLayer())
         entitySet.removeLayerEntitySet(dimStyle.getSymbolLayer())
         entitySet.removeLayerEntitySet(dimStyle.getLinearLayer())


# ===============================================================================
# QadDimEntity dimension entity class
# ===============================================================================
class QadDimEntity():

   # ============================================================================
   # __init__
   # ============================================================================
   def __init__(self, dimEntity = None):
      self.dimStyle = None
      self.textualFeature = None
      self.linearFeatures = []
      self.symbolFeatures = []

      if dimEntity is not None:
         self.set(dimEntity)


   def whatIs(self):
      return "DIMENTITY"


   def isInitialized(self):
      if (self.dimStyle is None) or (self.textualFeature is None):
         return False
      else:
         return True


   def __eq__(self, dimEntity):
      """self == other"""
      if self.isInitialized() == False or dimEntity.isInitialized() == False :
         return False

      if self.getTextualLayer() == dimEntity.getTextualLayer() and self.getDimId() == dimEntity.getDimId():
         return True
      else:
         return False


   # ============================================================================
   # isValid
   # ============================================================================
   def isValid(self):
      """Checks whether the dimensioning style is valid and returns True if so.
            If the dimensioning is invalid, it returns False.
      """
      if self.dimStyle is None:
         return False
      return self.dimStyle.isValid()


   # ============================================================================
   # getTextualLayer
   # ============================================================================
   def getTextualLayer(self):
      if self.dimStyle is None:
         return None
      return self.dimStyle.getTextualLayer()


   # ============================================================================
   # getLinearLayer
   # ============================================================================
   def getLinearLayer(self):
      if self.dimStyle is None:
         return None
      return self.dimStyle.getLinearLayer()


   # ============================================================================
   # getSymbolLayer
   # ============================================================================
   def getSymbolLayer(self):
      if self.dimStyle is None:
         return None
      return self.dimStyle.getSymbolLayer()


   # ============================================================================
   # set
   # ============================================================================
   def set(self, dimEntity):
      self.dimStyle = QadDimStyle(dimEntity.dimStyle)

      self.textualFeature = QgsFeature(dimEntity.textualFeature)

      del self.linearFeatures[:]
      for f in dimEntity.linearFeatures:
         self.linearFeatures.append(QgsFeature(f))

      del self.symbolFeatures[:]
      for f in dimEntity.symbolFeatures:
         self.symbolFeatures.append(QgsFeature(f))


   # ============================================================================
   # getLinearGeometryCollection
   # ============================================================================
   def getLinearGeometryCollection(self):
      result = []
      for f in self.linearFeatures:
         result.append(f.geometry())
      return result


   # ============================================================================
   # getSymbolGeometryCollection
   # ============================================================================
   def getSymbolGeometryCollection(self):
      result = []
      for f in self.symbolFeatures:
         result.append(f.geometry())
      return result


   # ============================================================================
   # getDimId
   # ============================================================================
   def getDimId(self):
      """The function returns the dimensioning code otherwise None."""
      try:
         return self.textualFeature.attribute(self.idFieldName)
      except:
         return None


   def recodeDimIdToFeature(self, newDimId):
      try:
         # set the dimension code
         self.textualFeature.setAttribute(self.dimStyle.idFieldName, newDimId)
         for f in self.linearFeatures:
            f.setAttribute(self.dimStyle.idParentFieldName, newDimId)
         for f in self.symbolFeatures:
            f.setAttribute(self.dimStyle.idParentFieldName, newDimId)
      except:
         return False

      return True


   # ============================================================================
   # addToLayers
   # ============================================================================
   def addToLayers(self, plugIn):
      # first of all insert the dimension text to recode the dimensioning
      # plugin, layer, feature, coordTransform, refresh, check_validity
      if qad_layer.addFeatureToLayer(plugIn, self.getTextualLayer(), self.textualFeature, None, False, False, False) == False:
         return False
      newDimId = self.textualFeature.id()

      if self.recodeDimIdToFeature(newDimId) == False:
         return False

      # plugin, layer, feature, refresh, check_validity
      if qad_layer.updateFeatureToLayer(plugIn, self.getTextualLayer(), self.textualFeature, False, False) == False:
         return False
      # plugin, layer, features, coordTransform, refresh, check_validity
      if qad_layer.addFeaturesToLayer(plugIn, self.getLinearLayer(), self.linearFeatures, None, False, False) == False:
         return False
      # plugin, layer, features, coordTransform, refresh, check_validity
      if qad_layer.addFeaturesToLayer(plugIn, self.getSymbolLayer(), self.symbolFeatures, None, False, False) == False:
         return False

      return True


   # ============================================================================
   # deleteToLayers
   # ============================================================================
   def deleteToLayers(self, plugIn):
      ids =[]

      # plugin, layer, featureId, refresh
      if qad_layer.deleteFeatureToLayer(plugIn, self.getTextualLayer(), self.textualFeature.id(), False) == False:
         return False

      for f in self.linearFeatures:
         ids.append(f.id())
      # plugin, layer, featureIds, refresh
      if qad_layer.deleteFeaturesToLayer(plugIn, self.getLinearLayer(), ids, False) == False:
         return False

      del ids[:]
      for f in self.symbolFeatures:
         ids.append(f.id())
      # plugin, layer, featureIds, refresh
      if qad_layer.deleteFeaturesToLayer(plugIn, self.getSymbolLayer(), ids, False) == False:
         return False

      return True


   # ============================================================================
   # initByEntity
   # ============================================================================
   def initByEntity(self, dimStyle, entity):
      dimId = dimStyle.getDimIdByEntity(entity)
      if dimId is None:
         return False
      return self.initByDimId(dimStyle, dimId)


   # ============================================================================
   # initByDimId
   # ============================================================================
   def initByDimId(self, dimStyle, dimId):
      self.dimStyle = QadDimStyle(dimStyle)
      entitySet = self.dimStyle.getEntitySet(dimId)
      if entitySet.count() == 0: return False

      self.textualFeature = None
      layerEntitySet = entitySet.findLayerEntitySet(self.getTextualLayer())
      if layerEntitySet is not None:
         features = layerEntitySet.getFeatureCollection()
         self.textualFeature = features[0]

      # linear entities
      layerEntitySet = entitySet.findLayerEntitySet(self.getLinearLayer())
      del self.linearFeatures[:] # I empty the list
      if layerEntitySet is not None:
         self.linearFeatures = layerEntitySet.getFeatureCollection()

      # point entities
      layerEntitySet = entitySet.findLayerEntitySet(self.getSymbolLayer())
      del self.symbolFeatures[:] # I empty the list
      if layerEntitySet is not None:
         self.symbolFeatures = layerEntitySet.getFeatureCollection()

      return True


   # ============================================================================
   # getEntitySet
   # ============================================================================
   def getEntitySet(self):
      result = QadEntitySet()

      if self.isValid() == False: return result;

      layerEntitySet = QadLayerEntitySet()
      layerEntitySet.set(self.getTextualLayer(), [self.textualFeature])
      result.addLayerEntitySet(layerEntitySet)

      layerEntitySet = QadLayerEntitySet()
      layerEntitySet.set(self.getLinearLayer(), self.linearFeatures)
      result.addLayerEntitySet(layerEntitySet)

      layerEntitySet = QadLayerEntitySet()
      layerEntitySet.set(self.getSymbolLayer(), self.symbolFeatures)
      result.addLayerEntitySet(layerEntitySet)

      return result


   # ============================================================================
   # selectOnLayer
   # ============================================================================
   def selectOnLayer(self, incremental = True):
      self.getEntitySet().selectOnLayer(incremental)


   # ============================================================================
   # deselectOnLayer
   # ============================================================================
   def deselectOnLayer(self):
      self.getEntitySet().deselectOnLayer()


   # ============================================================================
   # getDimPts
   # ============================================================================
   def getDimPts(self, destinationCrs = None):
      """destinationCrs = coordinate system in which the result will be returned"""

      dimPt1 = None
      dimPt2 = None

      if len(self.dimStyle.componentFieldName) > 0:
         # I searc among the specific elements
         for f in self.symbolFeatures:
            try:
               value = f.attribute(self.dimStyle.componentFieldName)
               if value == QadDimComponentEnum.DIM_PT1: # first point to dimension ("Dimension point 1")
                  g = f.geometry()
                  if (destinationCrs is not None) and destinationCrs != self.getSymbolLayer().crs():
                     g.transform(QgsCoordinateTransform(self.getSymbolLayer().crs(), \
                                                        destinationCrs,
                                                        QgsProject.instance())) # I transform the geometry into map coordinates

                  dimPt1 = g.asPoint()
               elif value == QadDimComponentEnum.DIM_PT2: # second point to dimension ("Dimension point 2")
                  g = f.geometry()
                  if (destinationCrs is not None) and destinationCrs != self.getSymbolLayer().crs():
                     g.transform(QgsCoordinateTransform(self.getSymbolLayer().crs(), \
                                                         destinationCrs,
                                                         QgsProject.instance())) # I transform the geometry into map coordinates

                  dimPt2 = g.asPoint()
            except:
               return None, None

      return QadPoint(dimPt1), QadPoint(dimPt2)


   # ============================================================================
   # getDimLinePts
   # ============================================================================
   def getDimLinePts(self, destinationCrs = None):
      """destinationCrs = coordinate system in which the result will be returned"""
      dimLinePt1 = None
      dimLinePt2 = None
      # I look for the start-end points of the dimension line
      if len(self.dimStyle.componentFieldName) > 0:
         # I first searc among the linear elements
         for f in self.linearFeatures:
            try:
               value = f.attribute(self.dimStyle.componentFieldName)
               # first point to dimension ("Dimension point 1") or second point to dimension ("Dimension point 2")
               if value == QadDimComponentEnum.DIM_LINE1 or value == QadDimComponentEnum.DIM_LINE2:
                  g = f.geometry()

                  if (destinationCrs is not None) and destinationCrs != self.getSymbolLayer().crs():
                     g.transform(QgsCoordinateTransform(self.getLinearLayer().crs(), \
                                                        destinationCrs, \
                                                        QgsProject.instance())) # I transform the geometry into map coordinates

                  pts = qad_utils.asPointOrPolyline(g)[0].asPolyline()
                  if value == QadDimComponentEnum.DIM_LINE1:
                     dimLinePt1 = pts[0]
                  else:
                     dimLinePt2 = pts[-1]

            except:
               return None, None

         if dimLinePt1 is None or dimLinePt2 is None:
            # then I searc among the specific elements
            for f in self.symbolFeatures:
               try:
                  value = f.attribute(self.dimStyle.componentFieldName)
                  # first arrow block ("Block 1")
                  if dimLinePt1 is None and value == QadDimComponentEnum.BLOCK1:
                     g = f.geometry()

                     if (destinationCrs is not None) and destinationCrs != self.getSymbolLayer().crs():
                        g.transform(QgsCoordinateTransform(self.getSymbolLayer().crs(), \
                                                           destinationCrs, \
                                                           QgsProject.instance())) # I transform the geometry into map coordinates

                     dimLinePt1 = g.asPoint()

                  # second arrow block ("Block 2")
                  if dimLinePt2 is None and value == QadDimComponentEnum.BLOCK2:
                     g = f.geometry()

                     if (destinationCrs is not None) and destinationCrs != self.getSymbolLayer().crs():
                        g.transform(QgsCoordinateTransform(self.getSymbolLayer().crs(), \
                                                           destinationCrs, \
                                                           QgsProject.instance())) # I transform the geometry into map coordinates

                     dimLinePt2 = g.asPoint()

               except:
                  return None, None

      return dimLinePt1, dimLinePt2


   # ============================================================================
   # getDimArc
   # ============================================================================
   def getDimArc(self, destinationCrs = None):
      """destinationCrs = coordinate system in which the result will be returned"""
      # I look for dimension points
      dimPt1, dimPt2 = self.getDimPts(destinationCrs)
      if dimPt1 is None or dimPt2 is None: return None

      # I look for the starting and ending points of the dimension line
      dimLinePt1, dimLinePt2 = self.getDimLinePts(destinationCrs)
      if dimLinePt1 is None or dimLinePt2 is None: return None

      ang1 = qad_utils.normalizeAngle(qad_utils.getAngleBy2Pts(dimPt1, dimLinePt1))
      ang2 = qad_utils.normalizeAngle(qad_utils.getAngleBy2Pts(dimLinePt2, dimPt2))
      if qad_utils.TanDirectionNear(ang1, ang2) == True: # 180 degree arc
         ptCenter = qad_utils.getMiddlePoint(dimPt1, dimPt2)
      else:
         ptCenter = qad_utils.getIntersectionPointOn2InfinityLines(dimPt1, dimLinePt1, dimPt2, dimLinePt2)

      arc = QadArc()
      if arc.fromStartCenterEndPts(dimPt1, ptCenter, dimPt2) == False:
         return None

      return arc


   # ============================================================================
   # getDimLeaderLine
   # ============================================================================
   def getDimLeaderLine(self, leaderLineType = None, destinationCrs = None):
      """Find the dimension line of the indicated type (in destinationCrs typically = map coordinates)
            destinationCrs = coordinate system in which containerGeom is expressed and in which the result will be returned
      """
      if len(self.dimStyle.componentFieldName) > 0:
         # I first searc among the linear elements
         for f in self.linearFeatures:
            try:
               value = f.attribute(self.dimStyle.componentFieldName)
               if value == leaderLineType:
                  g = f.geometry()

                  if (destinationCrs is not None) and destinationCrs != self.getSymbolLayer().crs():
                     g.transform(QgsCoordinateTransform(self.getLinearLayer().crs(), \
                                                        destinationCrs, \
                                                        QgsProject.instance())) # I transform the geometry into map coordinates

                  return qad_utils.asPointOrPolyline(g)[0].asPolyline()
            except:
               return None

      return None


   # ============================================================================
   # getDimLinePosPt
   # ============================================================================
   def getDimLinePosPt(self, containerGeom = None, destinationCrs = None):
      """Find a point among the various possible points that indicates where the dimension line is located (in destinationCrs typically = map coordinates)
            if containerGeom <> None the point must be contained in containerGeom
            containerGeom = can be a QgsGeometry representing a polygon (in destinationCrs typically = map coordinates) containing the geom points to stretch
                            or a list of points to stretch (in destinationCrs typically = map coordinates)
            destinationCrs = coordinate system in which containerGeom is expressed and in which the result will be returned
      """

      if len(self.dimStyle.componentFieldName) > 0:
         # I first searc among the linear elements
         for f in self.linearFeatures:
            try:
               value = f.attribute(self.dimStyle.componentFieldName)
               # first point to dimension ("Dimension point 1") or second point to dimension ("Dimension point 2")
               if value == QadDimComponentEnum.DIM_LINE1 or value == QadDimComponentEnum.DIM_LINE2:
                  g = f.geometry()

                  if (destinationCrs is not None) and destinationCrs != self.getSymbolLayer().crs():
                     g.transform(QgsCoordinateTransform(self.getLinearLayer().crs(), \
                                                        destinationCrs, \
                                                        QgsProject.instance())) # I transform the geometry into map coordinates

                  pts = qad_utils.asPointOrPolyline(g)[0].asPolyline()
                  if containerGeom is not None: # I verify that the starting point is inside containerGeom
                     if type(containerGeom) == QgsGeometry: # geometry
                        if containerGeom.contains(pts[0]) == True:
                           return QadPoint(pts[0])
                        else:
                           # check that the final point is inside containerGeom
                           if containerGeom.contains(pts[-1]) == True:
                              return QadPoint(pts[-1])
                     elif type(containerGeom) == list: # list of points
                        for containerPt in containerGeom:
                           if qad_utils.ptNear(containerPt, pts[0]): # if the points are sufficiently close
                              return QadPoint(pts[0])
                           else:
                              # I verify the final point
                              if qad_utils.ptNear(containerPt,pts[-1]):
                                 return QadPoint(pts[-1])
                  else:
                     return QadPoint(pts[0]) # starting point
            except:
               return None

         # then I searc among the specific elements
         for f in self.symbolFeatures:
            try:
               value = f.attribute(self.dimStyle.componentFieldName)
               # first arrow block ("Block 1") o second arrow block ("Block 2")
               if value == QadDimComponentEnum.BLOCK1 or value == QadDimComponentEnum.BLOCK2:
                  g = f.geometry()

                  if (destinationCrs is not None) and destinationCrs != self.getSymbolLayer().crs():
                     g.transform(QgsCoordinateTransform(self.getSymbolLayer().crs(), \
                                                        destinationCrs, \
                                                        QgsProject.instance())) # I transform the geometry into map coordinates

                  dimLinePosPt = g.asPoint()
                  if containerGeom is not None: # I verify that the point is inside containerGeom
                     if type(containerGeom) == QgsGeometry: # geometry
                        if containerGeom.contains(dimLinePosPt) == True:
                           return QadPoint(dimLinePosPt)
                     elif type(containerGeom) == list: # list of points
                        for containerPt in containerGeom:
                           if ptNear(containerPt, dimLinePosPt): # if the points are sufficiently close
                              return QadPoint(dimLinePosPt)
                  else:
                     return QadPoint(dimLinePosPt)
            except:
               return None

      return None


   # ============================================================================
   # getDimLinearAlignment
   # ============================================================================
   def getDimLinearAlignment(self):
      dimLinearAlignment = None
      dimLineRotation = None
      Pts = []

      if len(self.dimStyle.componentFieldName) > 0:
         # I first searc among the linear elements
         for f in self.linearFeatures:
            try:
               value = f.attribute(self.dimStyle.componentFieldName)
               if value == QadDimComponentEnum.DIM_LINE1: # first point to dimension ("Dimension point 1")
                  Pts = qad_utils.asPointOrPolyline(f.geometry())[0].asPolyline()
                  break
               elif value == QadDimComponentEnum.DIM_LINE2: # second point to dimension ("Dimension point 2")
                  Pts = qad_utils.asPointOrPolyline(f.geometry())[0].asPolyline()
                  break
            except:
               return None, None

         if Pts is None:
            # then I searc among the specific elements
            for f in self.symbolFeatures:
               try:
                  value = f.attribute(self.dimStyle.componentFieldName)
                  if value == QadDimComponentEnum.BLOCK1: # first arrow block ("Block 1")
                     Pts.append(f.geometry().asPoint())
                  elif value == QadDimComponentEnum.BLOCK2: # second arrow block ("Block 1")
                     Pts.append(f.geometry().asPoint())
               except:
                  return None, None

      if len(Pts) > 1: # at least 2 points
         if qad_utils.doubleNear(Pts[0].x(), Pts[-1].x()): # vertical line (same x)
            dimLinearAlignment = QadDimStyleAlignmentEnum.VERTICAL
            dimLineRotation = 0
         elif qad_utils.doubleNear(Pts[0].y(), Pts[-1].y()): # horizontal line (same y)
            dimLinearAlignment = QadDimStyleAlignmentEnum.HORIZONTAL
            dimLineRotation = 0
         else:
            dimLinearAlignment = QadDimStyleAlignmentEnum.HORIZONTAL
            dimLineRotation = qad_utils.getAngleBy2Pts(Pts[0], Pts[-1])


      return dimLinearAlignment, dimLineRotation


   # ============================================================================
   # getDimCircle
   # ============================================================================
   def getDimCircle(self, destinationCrs = None):
      """destinationCrs = coordinate system in which the result will be returned
            Returns a circle to which the DIMRADIUS dimension refers
      """
      # I look for dimension points
      dimPt1, dimPt2 = self.getDimPts(destinationCrs)
      if dimPt1 is None or dimPt2 is None: return None

      circle = QadCircle()
      circle.center = dimPt1
      circle.radius = qad_utils.getDistance(dimPt1, dimPt2)

      return circle


   # ============================================================================
   # getTextRot
   # ============================================================================
   def getTextRot(self):
      textRot = None

      if len(self.dimStyle.rotFieldName) > 0:
         try:
            textRot = self.textualFeature.attribute(self.dimStyle.rotFieldName)
         except:
            return None

      return qad_utils.toRadians(textRot)


   # ============================================================================
   # getTextValue
   # ============================================================================
   def getTextValue(self):
      textValue = None

      if self.dimStyle.getTextualLayer() is None:
         return None;

      # if the text depends on only one field
      labelFieldNames = qad_label.get_labelFieldNames(self.dimStyle.getTextualLayer())
      if len(labelFieldNames) == 1 and len(labelFieldNames[0]) > 0:
         try:
            textValue = self.textualFeature.attribute(labelFieldNames[0])
         except:
            return None

      return textValue


   # ============================================================================
   # getTextPt
   # ============================================================================
   def getTextPt(self, destinationCrs = None):
      # destinationCrs = coordinate system in which the result will be returned
      g = self.textualFeature.geometry()
      if (destinationCrs is not None) and destinationCrs != self.getTextualLayer().crs():
         g.transform(QgsCoordinateTransform(self.getTextualLayer().crs(), \
                                            destinationCrs,
                                            QgsProject.instance())) # I transform the geometry into map coordinates

      return g.asPoint()


   # ============================================================================
   # isCalculatedText
   # ============================================================================
   def isCalculatedText(self):
      # the function checks whether the dimension text is calculated from the graphics or whether a different text has been forced
      measure = self.getTextValue()

      if self.dimStyle.dimType == QadDimTypeEnum.ALIGNED: # linear dimension aligned to the origin points of the extension lines
         dimPt1, dimPt2 = self.getDimPts()
         return measure == self.dimStyle.getFormattedText(qad_utils.getDistance(dimPt1, dimPt2))
      elif self.dimStyle.dimType == QadDimTypeEnum.LINEAR: # linear dimension with a horizontal or vertical dimension line
         dimPt1, dimPt2 = self.getDimPts()
         linePosPt = self.getDimLinePosPt()
         preferredAlignment, dimLineRotation = self.getDimLinearAlignment()

         # dimension line within the extension lines
         dimLine = self.dimStyle.getDimLine(dimPt1, dimPt2, linePosPt, preferredAlignment, dimLineRotation)
         if dimLine is None: return False
         return measure == self.dimStyle.getFormattedText(dimLine.length())
      elif self.dimStyle.dimType == QadDimTypeEnum.ARC_LENTGH: # dimension for the length of an arc
         dimArc = self.getDimArc()
         if dimArc is None: return False
         return measure == self.dimStyle.getFormattedText(dimArc.length())
      elif self.dimStyle.dimType == QadDimTypeEnum.RADIUS: # radial dimension, measures the radius of a circle or arc
         dimPt1, dimPt2 = self.getDimPts()
         return measure == self.dimStyle.getFormattedText(qad_utils.getDistance(dimPt1, dimPt2))

      return True


   # ============================================================================
   # isCalculatedTextRot
   # ============================================================================
   def isCalculatedTextRot(self):
      # the function checks whether the rotation of the dimension text is calculated by the graphics or whether a different rotation has been forced
      measure = self.getTextValue()
      txtRot = self.getTextRot()
      canvas = qgis.utils.iface.mapCanvas()
      destinationCrs = canvas.mapSettings().destinationCrs()

      if self.dimStyle.dimType == QadDimTypeEnum.ALIGNED: # linear dimension aligned to the origin points of the extension lines
         dimPt1, dimPt2 = self.getDimPts(destinationCrs)
         linePosPt = self.getDimLinePosPt(None, destinationCrs)
         if (dimPt1 is not None) and (dimPt2 is not None) and \
            (linePosPt is not None):
            dimEntity, textOffsetRect = self.dimStyle.getAlignedDimFeatures(canvas, \
                                                                            dimPt1, \
                                                                            dimPt2, \
                                                                            linePosPt, \
                                                                            measure)
            return txtRot == dimEntity.getTextRot()

      elif self.dimStyle.dimType == QadDimTypeEnum.LINEAR: # linear dimension with a horizontal or vertical dimension line
         dimPt1, dimPt2 = self.getDimPts(destinationCrs)
         linePosPt = self.getDimLinePosPt(None, destinationCrs)
         dimLinearAlignment, dimLineRotation = self.getDimLinearAlignment()

         if (dimPt1 is not None) and (dimPt2 is not None) and \
            (linePosPt is not None) and \
            (dimLinearAlignment is not None) and (dimLineRotation is not None):

            if dimLinearAlignment == QadDimStyleAlignmentEnum.VERTICAL:
               dimLineRotation = math.pi / 2
            dimLinearAlignment = QadDimStyleAlignmentEnum.HORIZONTAL

            dimEntity, textOffsetRect = self.dimStyle.getLinearDimFeatures(canvas, \
                                                                           dimPt1, \
                                                                           dimPt2, \
                                                                           linePosPt, \
                                                                           measure, \
                                                                           dimLinearAlignment, \
                                                                           dimLineRotation)
            return txtRot == dimEntity.getTextRot()

      elif self.dimStyle.dimType == QadDimTypeEnum.ARC_LENTGH: # dimension for the length of an arc
         dimArc = self.getDimArc()
         linePosPt = self.getDimLinePosPt(None, destinationCrs)

         if (dimArc is not None) and (linePosPt is not None):
            dimEntity, textOffsetRect = self.dimStyle.getArcDimFeatures(canvas, dimArc, linePosPt, measure)
            return txtRot == dimEntity.getTextRot()

      elif self.dimStyle.dimType == QadDimTypeEnum.RADIUS: # radial dimension, measures the radius of a circle or arc
         dimCircle = self.getDimCircle()
         linePosPt = self.getDimLinePosPt(None, destinationCrs)

         if (dimCircle is not None) and (linePosPt is not None):
            dimEntity, textOffsetRect = self.dimStyle.getRadiusDimFeatures(canvas, dimCircle, linePosPt, measure)
            return txtRot == dimEntity.getTextRot()

      return True


   # ============================================================================
   # move
   # ============================================================================
   def move(self, offsetX, offsetY):
      # offsetX = spostamento X in map coordinate
      # offsetY = spostamento Y in map coordinate
      if self.isValid() == False: return False;

      canvas = qgis.utils.iface.mapCanvas()
      destinationCrs = canvas.mapSettings().destinationCrs()

      g = self.textualFeature.geometry()
      qadGeom = fromQgsGeomToQadGeom(g, self.getTextualLayer().crs())
      qadGeom.move(offsetX, offsetY)
      g = fromQadGeomToQgsGeom(qadGeom, self.getTextualLayer())
      self.textualFeature.setGeometry(g)

      for f in self.linearFeatures:
         g = f.geometry()
         qadGeom = fromQgsGeomToQadGeom(g, self.getLinearLayer().crs())
         qadGeom.move(offsetX, offsetY)
         g = fromQadGeomToQgsGeom(qadGeom, self.getLinearLayer())
         f.setGeometry(g)

      for f in self.symbolFeatures:
         g = f.geometry()
         qadGeom = fromQgsGeomToQadGeom(g, self.getSymbolLayer().crs())
         qadGeom.move(offsetX, offsetY)
         g = fromQadGeomToQgsGeom(qadGeom, self.getSymbolLayer())
         f.setGeometry(g)

      return False


   # ============================================================================
   # rotate
   # ============================================================================
   def rotate(self, basePt, angle):
      # basePt = base point expressed in map coordinates
      if self.isValid() == False: return False;

      canvas = qgis.utils.iface.mapCanvas()
      destinationCrs = canvas.mapSettings().destinationCrs()

      measure = None if self.isCalculatedText() else self.getTextValue()
      textRot = None if self.isCalculatedTextRot() else self.getTextRot()

      if textRot is not None: # if the rotation was forced then set it
         prevTextRotMode = self.dimStyle.textRotMode
         self.dimStyle.textRotMode = QadDimStyleTxtRotModeEnum.FORCED_ROTATION
         self.dimStyle.textForcedRot = textRot

      if self.dimStyle.dimType == QadDimTypeEnum.ALIGNED: # linear dimension aligned to the origin points of the extension lines
         dimPt1, dimPt2 = self.getDimPts(destinationCrs)
         linePosPt = self.getDimLinePosPt(None, destinationCrs)
         if (dimPt1 is not None) and (dimPt2 is not None) and \
            (linePosPt is not None):
            dimPt1 = qad_utils.rotatePoint(dimPt1, basePt, angle)
            dimPt2 = qad_utils.rotatePoint(dimPt2, basePt, angle)
            linePosPt = qad_utils.rotatePoint(linePosPt, basePt, angle)

            dimEntity, textOffsetRect = self.dimStyle.getAlignedDimFeatures(canvas, \
                                                                            dimPt1, \
                                                                            dimPt2, \
                                                                            linePosPt, \
                                                                            measure)
            self.set(dimEntity)

      elif self.dimStyle.dimType == QadDimTypeEnum.LINEAR: # linear dimension with a horizontal or vertical dimension line
         dimPt1, dimPt2 = self.getDimPts(destinationCrs)
         linePosPt = self.getDimLinePosPt(None, destinationCrs)
         preferredAlignment, dimLineRotation = self.getDimLinearAlignment()
         if (dimPt1 is not None) and (dimPt2 is not None) and \
            (linePosPt is not None) and \
            (preferredAlignment is not None) and (dimLineRotation is not None):
            dimPt1 = qad_utils.rotatePoint(dimPt1, basePt, angle)
            dimPt2 = qad_utils.rotatePoint(dimPt2, basePt, angle)
            linePosPt = qad_utils.rotatePoint(linePosPt, basePt, angle)
            dimLinearAlignment, dimLineRotation = self.getDimLinearAlignment()

            if dimLinearAlignment == QadDimStyleAlignmentEnum.VERTICAL:
               dimLineRotation = math.pi / 2
            dimLinearAlignment = QadDimStyleAlignmentEnum.HORIZONTAL
            dimLineRotation = dimLineRotation + angle

            dimEntity, textOffsetRect = self.dimStyle.getLinearDimFeatures(canvas, \
                                                                           dimPt1, \
                                                                           dimPt2, \
                                                                           linePosPt, \
                                                                           measure, \
                                                                           dimLinearAlignment, \
                                                                           dimLineRotation)
            self.set(dimEntity)

      elif self.dimStyle.dimType == QadDimTypeEnum.ARC_LENTGH: # dimension for the length of an arc
         dimArc = self.getDimArc(destinationCrs)
         linePosPt = self.getDimLinePosPt(None, destinationCrs)
         if (dimArc is not None) and (linePosPt is not None):
            dimArc.rotate(basePt, angle)
            linePosPt = qad_utils.rotatePoint(linePosPt, basePt, angle)
            arcLeader = True if self.getDimLeaderLine(QadDimComponentEnum.ARC_LEADER_LINE) is not None else False

            dimEntity, textOffsetRect = self.dimStyle.getArcDimFeatures(canvas, \
                                                                        dimArc, \
                                                                        linePosPt, \
                                                                        measure, \
                                                                        arcLeader)
            self.set(dimEntity)

      elif self.dimStyle.dimType == QadDimTypeEnum.RADIUS: # radial dimension, measures the radius of a circle or arc
         # cannot be done because it is not possible to know whether the dimension referred to a circle or an arc
         # at the moment I assume it always refers to a circle
         dimCircle = self.getDimCircle()
         linePosPt = self.getDimLinePosPt(None, destinationCrs)

         if (dimCircle is not None) and (linePosPt is not None):
            dimCircle.rotate(basePt, angle)
            linePosPt = qad_utils.rotatePoint(linePosPt, basePt, angle)
            dimEntity, textOffsetRect = self.dimStyle.getRadiusDimFeatures(canvas, dimCircle, linePosPt, measure)
            self.set(dimEntity)

      if textRot is not None:
         self.dimStyle.textRotMode = prevTextRotMode # restore the previous situation

      return True


   # ============================================================================
   # scale
   # ============================================================================
   def scale(self, basePt, scale):
      # basePt = base point expressed in map coordinates
      if self.isValid() == False: return False;

      canvas = qgis.utils.iface.mapCanvas()
      destinationCrs = canvas.mapSettings().destinationCrs()

      measure = None if self.isCalculatedText() else self.getTextValue()
      textRot = None if self.isCalculatedTextRot() else self.getTextRot()

      if textRot is not None: # if the rotation was forced then set it
         prevTextRotMode = self.dimStyle.textRotMode
         self.dimStyle.textRotMode = QadDimStyleTxtRotModeEnum.FORCED_ROTATION
         self.dimStyle.textForcedRot = textRot

      if self.dimStyle.dimType == QadDimTypeEnum.ALIGNED: # linear dimension aligned to the origin points of the extension lines
         dimPt1, dimPt2 = self.getDimPts(destinationCrs)
         linePosPt = self.getDimLinePosPt(None, destinationCrs)
         if (dimPt1 is not None) and (dimPt2 is not None) and \
            (linePosPt is not None):
            dimPt1 = qad_utils.scalePoint(dimPt1, basePt, scale)
            dimPt2 = qad_utils.scalePoint(dimPt2, basePt, scale)
            linePosPt = qad_utils.scalePoint(linePosPt, basePt, scale)

            dimEntity, textOffsetRect = self.dimStyle.getAlignedDimFeatures(canvas, \
                                                                            dimPt1, \
                                                                            dimPt2, \
                                                                            linePosPt, \
                                                                            measure)
            self.set(dimEntity)

      elif self.dimStyle.dimType == QadDimTypeEnum.LINEAR: # linear dimension with a horizontal or vertical dimension line
         dimPt1, dimPt2 = self.getDimPts(destinationCrs)
         linePosPt = self.getDimLinePosPt(None, destinationCrs)
         preferredAlignment, dimLineRotation = self.getDimLinearAlignment()
         if (dimPt1 is not None) and (dimPt2 is not None) and \
            (linePosPt is not None) and \
            (preferredAlignment is not None) and (dimLineRotation is not None):
            textForcedRot = self.getTextRot()
            if textForcedRot is not None:
               self.dimStyle.textForcedRot = textForcedRot

            dimPt1 = qad_utils.scalePoint(dimPt1, basePt, scale)
            dimPt2 = qad_utils.scalePoint(dimPt2, basePt, scale)
            linePosPt = qad_utils.scalePoint(linePosPt, basePt, scale)
            dimLinearAlignment, dimLineRotation = self.getDimLinearAlignment()

            if dimLinearAlignment == QadDimStyleAlignmentEnum.VERTICAL:
               dimLineRotation = math.pi / 2
            dimLinearAlignment = QadDimStyleAlignmentEnum.HORIZONTAL

            dimEntity, textOffsetRect = self.dimStyle.getLinearDimFeatures(canvas, \
                                                                           dimPt1, \
                                                                           dimPt2, \
                                                                           linePosPt, \
                                                                           measure, \
                                                                           dimLinearAlignment, \
                                                                           dimLineRotation)
            self.set(dimEntity)

      elif self.dimStyle.dimType == QadDimTypeEnum.ARC_LENTGH: # dimension for the length of an arc
         dimArc = self.getDimArc(destinationCrs)
         linePosPt = self.getDimLinePosPt(None, destinationCrs)
         if (dimArc is not None) and \
            (linePosPt is not None):
            dimArc.scale(basePt, scale)
            linePosPt = qad_utils.scalePoint(linePosPt, basePt, scale)
            arcLeader = True if self.getDimLeaderLine(QadDimComponentEnum.ARC_LEADER_LINE) is not None else False

            dimEntity, textOffsetRect = self.dimStyle.getArcDimFeatures(canvas, \
                                                                        dimArc, \
                                                                        linePosPt, \
                                                                        measure, \
                                                                        arcLeader)
            self.set(dimEntity)

      elif self.dimStyle.dimType == QadDimTypeEnum.RADIUS: # radial dimension, measures the radius of a circle or arc
         # cannot be done because it is not possible to know whether the dimension referred to a circle or an arc
         # at the moment I assume it always refers to a circle
         dimCircle = self.getDimCircle()
         linePosPt = self.getDimLinePosPt(None, destinationCrs)

         if (dimCircle is not None) and (linePosPt is not None):
            dimCircle.scale(basePt, scale)
            linePosPt = qad_utils.scalePoint(linePosPt, basePt, scale)
            dimEntity, textOffsetRect = self.dimStyle.getRadiusDimFeatures(canvas, dimCircle, linePosPt, measure)
            self.set(dimEntity)

      if textRot is not None:
         self.dimStyle.textRotMode = prevTextRotMode # restore the previous situation

      return True


   # ============================================================================
   # mirror
   # ============================================================================
   def mirror(self, mirrorPt, mirrorAngle):
      # mirrorPt = base point expressed in map coordinates
      if self.isValid() == False: return False;

      canvas = qgis.utils.iface.mapCanvas()
      destinationCrs = canvas.mapSettings().destinationCrs()

      measure = None if self.isCalculatedText() else self.getTextValue()
      textRot = None if self.isCalculatedTextRot() else self.getTextRot()

      if textRot is not None: # if the rotation was forced then set it
         prevTextRotMode = self.dimStyle.textRotMode
         self.dimStyle.textRotMode = QadDimStyleTxtRotModeEnum.FORCED_ROTATION
         self.dimStyle.textForcedRot = textRot

      if self.dimStyle.dimType == QadDimTypeEnum.ALIGNED: # linear dimension aligned to the origin points of the extension lines
         dimPt1, dimPt2 = self.getDimPts(destinationCrs)
         linePosPt = self.getDimLinePosPt(None, destinationCrs)
         if (dimPt1 is not None) and (dimPt2 is not None) and \
            (linePosPt is not None):
            dimPt1 = qad_utils.mirrorPoint(dimPt1, mirrorPt, mirrorAngle)
            dimPt2 = qad_utils.mirrorPoint(dimPt2, mirrorPt, mirrorAngle)
            linePosPt = qad_utils.mirrorPoint(linePosPt, mirrorPt, mirrorAngle)

            dimEntity, textOffsetRect = self.dimStyle.getAlignedDimFeatures(canvas, \
                                                                            dimPt1, \
                                                                            dimPt2, \
                                                                            linePosPt, \
                                                                            measure)
            self.set(dimEntity)

      elif self.dimStyle.dimType == QadDimTypeEnum.LINEAR: # linear dimension with a horizontal or vertical dimension line
         dimPt1, dimPt2 = self.getDimPts(destinationCrs)
         linePosPt = self.getDimLinePosPt(None, destinationCrs)
         preferredAlignment, dimLineRotation = self.getDimLinearAlignment()
         if (dimPt1 is not None) and (dimPt2 is not None) and \
            (linePosPt is not None) and \
            (preferredAlignment is not None) and (dimLineRotation is not None):
            textForcedRot = self.getTextRot()
            if textForcedRot is not None:
               self.dimStyle.textForcedRot = textForcedRot

            dimPt1 = qad_utils.mirrorPoint(dimPt1, mirrorPt, mirrorAngle)
            dimPt2 = qad_utils.mirrorPoint(dimPt2, mirrorPt, mirrorAngle)
            linePosPt = qad_utils.mirrorPoint(linePosPt, mirrorPt, mirrorAngle)
            dimLinearAlignment, dimLineRotation = self.getDimLinearAlignment()

            if dimLinearAlignment == QadDimStyleAlignmentEnum.VERTICAL:
               dimLineRotation = math.pi / 2
            dimLinearAlignment = QadDimStyleAlignmentEnum.HORIZONTAL

            ptDummy = qad_utils.getPolarPointByPtAngle(mirrorPt, dimLineRotation, 1)
            ptDummy = qad_utils.mirrorPoint(ptDummy, mirrorPt, mirrorAngle)
            dimLineRotation = qad_utils.getAngleBy2Pts(mirrorPt, ptDummy)

            dimEntity, textOffsetRect = self.dimStyle.getLinearDimFeatures(canvas, \
                                                                           dimPt1, \
                                                                           dimPt2, \
                                                                           linePosPt, \
                                                                           measure, \
                                                                           dimLinearAlignment, \
                                                                           dimLineRotation)
            self.set(dimEntity)

      elif self.dimStyle.dimType == QadDimTypeEnum.ARC_LENTGH: # dimension for the length of an arc
         dimArc = self.getDimArc(destinationCrs)
         linePosPt = self.getDimLinePosPt(None, destinationCrs)
         if (dimArc is not None) and \
            (linePosPt is not None):
            dimArc.mirror(mirrorPt, mirrorAngle)
            linePosPt = qad_utils.mirrorPoint(linePosPt, mirrorPt, mirrorAngle)
            arcLeader = True if self.getDimLeaderLine(QadDimComponentEnum.ARC_LEADER_LINE) is not None else False

            dimEntity, textOffsetRect = self.dimStyle.getArcDimFeatures(canvas, \
                                                                        dimArc, \
                                                                        linePosPt, \
                                                                        measure, \
                                                                        arcLeader)
            self.set(dimEntity)

      elif self.dimStyle.dimType == QadDimTypeEnum.RADIUS: # radial dimension, measures the radius of a circle or arc
         # cannot be done because it is not possible to know whether the dimension referred to a circle or an arc
         # at the moment I assume it always refers to a circle
         dimCircle = self.getDimCircle()
         linePosPt = self.getDimLinePosPt(None, destinationCrs)

         if (dimCircle is not None) and (linePosPt is not None):
            dimCircle.mirror(mirrorPt, mirrorAngle)
            linePosPt = qad_utils.mirrorPoint(linePosPt, mirrorPt, mirrorAngle)
            dimEntity, textOffsetRect = self.dimStyle.getRadiusDimFeatures(canvas, dimCircle, linePosPt, measure)
            self.set(dimEntity)

      if textRot is not None:
         self.dimStyle.textRotMode = prevTextRotMode # restore the previous situation

      return True


   # ============================================================================
   # stretch
   # ============================================================================
   def stretch(self, containerGeom, offsetX, offsetY):
      """containerGeom = can be a QgsGeometry representing a polygon containing the geom points to stretch
                            or a list of points to stretch expressed in map coordinates
            offsetX = offsetX in map coordinates
            offsetY = Y offset in map coordinates
      """
      if self.isValid() == False: return False;

      canvas = qgis.utils.iface.mapCanvas()
      destinationCrs = canvas.mapSettings().destinationCrs()

      measure = None if self.isCalculatedText() else self.getTextValue()
      textRot = None if self.isCalculatedTextRot() else self.getTextRot()

      if textRot is not None: # if the rotation was forced then set it
         prevTextRotMode = self.dimStyle.textRotMode
         self.dimStyle.textRotMode = QadDimStyleTxtRotModeEnum.FORCED_ROTATION
         self.dimStyle.textForcedRot = textRot

      if self.dimStyle.dimType == QadDimTypeEnum.ALIGNED: # linear dimension aligned to the origin points of the extension lines
         dimPt1, dimPt2 = self.getDimPts(destinationCrs)
         linePosPt = self.getDimLinePosPt(containerGeom, destinationCrs)

         if dimPt1 is not None:
            newPt = qad_stretch_fun.stretchPoint(dimPt1, containerGeom, offsetX, offsetY)
            if newPt is not None:
               dimPt1 = newPt

         if dimPt2 is not None:
            newPt = qad_stretch_fun.stretchPoint(dimPt2, containerGeom, offsetX, offsetY)
            if newPt is not None:
               dimPt2 = newPt

         if linePosPt is not None:
            newPt = qad_stretch_fun.stretchPoint(linePosPt, containerGeom, offsetX, offsetY)
            if newPt is not None:
               linePosPt = newPt
         else:
            linePosPt = self.getDimLinePosPt(None, destinationCrs)
            # check if the dimension text was involved
            if qad_stretch_fun.isPtContainedForStretch(self.getTextPt(destinationCrs), containerGeom):
               if linePosPt is not None:
                  linePosPt = qad_utils.movePoint(linePosPt, offsetX, offsetY)

         if (dimPt1 is not None) and (dimPt2 is not None) and \
            (linePosPt is not None):
            dimEntity, textOffsetRect = self.dimStyle.getAlignedDimFeatures(canvas, \
                                                                            dimPt1, \
                                                                            dimPt2, \
                                                                            linePosPt, \
                                                                            measure)
            self.set(dimEntity)

      elif self.dimStyle.dimType == QadDimTypeEnum.LINEAR: # linear dimension with a horizontal or vertical dimension line
         dimPt1, dimPt2 = self.getDimPts(destinationCrs)
         linePosPt = self.getDimLinePosPt(containerGeom, destinationCrs)

         dimLinearAlignment, dimLineRotation = self.getDimLinearAlignment()

         if dimPt1 is not None:
            newPt = qad_stretch_fun.stretchPoint(dimPt1, containerGeom, offsetX, offsetY)
            if newPt is not None:
               dimPt1 = newPt

         if dimPt2 is not None:
            newPt = qad_stretch_fun.stretchPoint(dimPt2, containerGeom, offsetX, offsetY)
            if newPt is not None:
               dimPt2 = newPt

         if linePosPt is not None:
            newPt = qad_stretch_fun.stretchPoint(linePosPt, containerGeom, offsetX, offsetY)
            if newPt is not None:
               linePosPt = newPt
         else:
            linePosPt = self.getDimLinePosPt(None, destinationCrs)
            # check if the dimension text was involved
            if qad_stretch_fun.isPtContainedForStretch(self.getTextPt(destinationCrs), containerGeom):
               if linePosPt is not None:
                  linePosPt = qad_utils.movePoint(linePosPt, offsetX, offsetY)

         if (dimPt1 is not None) and (dimPt2 is not None) and \
            (linePosPt is not None) and \
            (dimLinearAlignment is not None) and (dimLineRotation is not None):
            if dimLinearAlignment == QadDimStyleAlignmentEnum.VERTICAL:
               dimLineRotation = math.pi / 2
            dimLinearAlignment = QadDimStyleAlignmentEnum.HORIZONTAL

            dimEntity, textOffsetRect = self.dimStyle.getLinearDimFeatures(canvas, \
                                                                           dimPt1, \
                                                                           dimPt2, \
                                                                           linePosPt, \
                                                                           measure, \
                                                                           dimLinearAlignment, \
                                                                           dimLineRotation)
            self.set(dimEntity)

      elif self.dimStyle.dimType == QadDimTypeEnum.ARC_LENTGH: # dimension for the length of an arc
         dimArc = self.getDimArc(destinationCrs)
         linePosPt = self.getDimLinePosPt(containerGeom, destinationCrs)

         if dimArc is not None:
            dimArc = qad_stretch_fun.stretchQadGeometry(dimArc, containerGeom, \
                                                        offsetX, offsetY)

         if linePosPt is not None:
            newPt = qad_utils.movePoint(linePosPt, offsetX, offsetY)
            linePosPt = qad_utils.getPolarPointBy2Pts(dimArc.center, linePosPt, qad_utils.getDistance(dimArc.center, newPt))
         else:
            linePosPt = self.getDimLinePosPt(None, destinationCrs)
            # check if the dimension text was involved
            textPt = self.getTextPt(destinationCrs)
            if qad_stretch_fun.isPtContainedForStretch(textPt, containerGeom):
               if linePosPt is not None:
                  newPt = qad_utils.movePoint(textPt, offsetX, offsetY)
                  linePosPt = qad_utils.getPolarPointBy2Pts(dimArc.center, linePosPt, qad_utils.getDistance(dimArc.center, newPt))

         if (dimArc is not None) and \
            (linePosPt is not None):
            arcLeader = True if self.getDimLeaderLine(QadDimComponentEnum.ARC_LEADER_LINE) is not None else False

            dimEntity, textOffsetRect = self.dimStyle.getArcDimFeatures(canvas, \
                                                                        dimArc, \
                                                                        linePosPt, \
                                                                        measure, \
                                                                        arcLeader)
            self.set(dimEntity)

      elif self.dimStyle.dimType == QadDimTypeEnum.RADIUS: # radial dimension, measures the radius of a circle or arc
         # cannot be done because it is not possible to know whether the dimension referred to a circle or an arc
         # at the moment I assume it always refers to a circle
         dimCircle = self.getDimCircle()
         linePosPt = self.getDimLinePosPt(containerGeom, destinationCrs)

         if type(containerGeom) == list: # list of points
            for containerPt in containerGeom:
               # whereIsPt returns -1 if the point is internal, 0 if it is on the circumference, 1 if it is external
               if dimCircle.whereIsPt(containerPt) == 0:
                  linePosPt = None # I move the point that was on the circumference

         if dimCircle is not None:
            dimCircle = qad_stretch_fun.stretchQadGeometry(dimCircle, containerGeom, \
                                                           offsetX, offsetY)

         if linePosPt is not None:
            newPt = qad_utils.movePoint(linePosPt, offsetX, offsetY)
            linePosPt = qad_utils.getPolarPointBy2Pts(dimCircle.center, linePosPt, qad_utils.getDistance(dimCircle.center, newPt))
         else:
            linePosPt = self.getDimLinePosPt(None, destinationCrs)
            # check if the dimension text was involved
            textPt = self.getTextPt(destinationCrs)
            if qad_stretch_fun.isPtContainedForStretch(textPt, containerGeom):
               if linePosPt is not None:
                  newPt = qad_utils.movePoint(textPt, offsetX, offsetY)
                  linePosPt = qad_utils.getPolarPointBy2Pts(dimCircle.center, linePosPt, qad_utils.getDistance(dimCircle.center, newPt))

         if (dimCircle is not None) and (linePosPt is not None):
            dimEntity, textOffsetRect = self.dimStyle.getRadiusDimFeatures(canvas, dimCircle, linePosPt, measure)
            self.set(dimEntity)

      if textRot is not None:
         self.dimStyle.textRotMode = prevTextRotMode # restore the previous situation

      return True;


   # ============================================================================
   # getDimComponentByEntity
   # ============================================================================
   def getDimComponentByEntity(self, entity):
      """The function, given an entity, returns the dimensioning component."""
      if entity.layer == self.getTextualLayer():
         return QadDimComponentEnum.TEXT_PT
      elif entity.layer == self.getLinearLayer() or \
           entity.layer == self.getSymbolLayer():
         try:
            return entity.getFeature().attribute(self.dimStyle.componentFieldName)
         except:
            return None

      return None


# ============================================================================
# appendDimEntityIfNotExisting
# ============================================================================
def appendDimEntityIfNotExisting(dimEntityList, dimEntity):
   """The function is useful in commands to avoid processing objects belonging to dimensioning several times
      dimEntityList is to be declared as a simple list (e.g. dimElaboratedList = [])
      The function searces in dimEntityList if dimEntity exists, if so it returns False
      otherwise it adds dimEntity to the list and returns True
   """
   for item in dimEntityList:
      if item == dimEntity: return False
   dimEntityList.append(dimEntity)
   return True


# ===============================================================================
#  = global variable
# ===============================================================================

QadDimStyles = QadDimStylesClass()                 # list of loaded dimensioning styles
