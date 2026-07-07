# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 class to manage environment variables

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
import os.path
from qgis.core import *
import math


from . import qad_utils
from .qad_msg import QadMsg


# ===============================================================================
# Qad variable type class.
# ===============================================================================
class QadVariableTypeEnum():
   UNKNOWN = 0 # unknown (not managed by QAD)
   STRING  = 1 # characters
   COLOR   = 2 # color expressed in characters (e.g. red = "#FF0000")
   INT     = 3 # integer number
   FLOAT   = 4 # number with decimals
   BOOL    = 5 # boolean (True or False)


# ===============================================================================
# Qad AUTOSNAP class.
# ===============================================================================
class QadAUTOSNAPEnum():
   DISPLAY_MARK      = 1  # Turns on the AutoSnap mark
   DISPLAY_TOOLTIPS  = 2  # Turns on the AutoSnap tooltips
   MAGNET            = 4  # Turns on the AutoSnap magnet
   POLAR_TRACKING    = 8  # Turns on polar tracking
   OBJ_SNAP_TRACKING = 16 # Turns on object snap tracking
   DISPLAY_TOOLTIPS_POLAR_OSNAP_TRACKING_ORTHO = 32 # Turns on tooltips for polar tracking, object snap tracking, and Ortho mode


# ===============================================================================
# Qad INPUTSEARCHOPTIONS class.
# ===============================================================================
class QadINPUTSEARCHOPTIONSEnum():
   ON              = 1  # Turns off all automated keyboard features when typing at the Command prompt
   AUTOCOMPLETE    = 2  # Automatically appends suggestions as each keystroke is entered after the second keystroke
   DISPLAY_LIST    = 4  # Displays a list of suggestions as keystrokes are entered
   DISPLAY_ICON    = 8  # Displays the icon of the command or system variable, if available
   EXCLUDE_SYS_VAR = 16 # Excludes the display of system variables


# ===============================================================================
# Qad POLARMODE class.
# ===============================================================================
class QadPOLARMODEnum():
   MEASURE_RELATIVE_ANGLE = 1 # if setted: Measure polar angles from selected objects (relative)
                              # if not setted: Measure polar angles based on current UCS (absolute)
   POLAR_TRACKING         = 2 # if setted: Use polar tracking settings in object snap tracking
                              # if not setted: Track orthogonally only
   ADDITIONAL_ANGLES      = 4 # if setted: Use additional polar tracking angles
   SHIFT_TO_ACQUIRE       = 8 # if setted: Press Shift to acquire object snap tracking points,
                              # if not setted: Acquire automatically object snap tracking points


# ===============================================================================
# Qad DELOBJ class.
# ===============================================================================
class QadDELOBJEnum():
   ALL_RETAINED       =  0 # All defining geometry is retained
   DELETE_ALL         =  1 # Delete all defining geometry
   ASK_FOR_DELETE_ALL = -1 # Ask the user for delete all defining geometry


# ===============================================================================
# Qad GRIPMULTIFUNCTIONAL class.
# ===============================================================================
class QadGRIPMULTIFUNCTIONALEnum():
   ON_CTRL_CYCLE_AND_HOT_GRIPT   = 1 # Access multi-functional grips with Ctrl-cycling and the Hot Grip shortcut menu
   ON_DYNAMIC_MENU_AND_HOT_GRIPT = 2 # Access multi-functional grips with the dynamic menu and the Hot Grip shortcut menu


# ===============================================================================
# Qad global or project class.
# ===============================================================================
class QadVariableLevelEnum():
   GLOBAL  = 0 # QAD global variable
   PROJECT = 2 # current project variable (which overrides the global one)


# ===============================================================================
# Qad variable class.
# ===============================================================================
class QadVariable():
   """Class that manages QAD environment variables"""

   def __init__(self, name, value, typeValue, minNum = None, maxNum = None, descr = "", level = QadVariableLevelEnum.GLOBAL):
      self.name = name
      self.value = value
      self.typeValue = typeValue
      self.default = value
      self.minNum = minNum
      self.maxNum = maxNum
      self.descr = descr
      self.level = level # of type QadVariableLevelEnum


# ===============================================================================
# Qad variables class.
# ===============================================================================
class QadVariablesClass():
   """Class that manages Qad environment variables"""

   def __init__(self):
      """Initializes a dictionary with variables and their default values"""
      self.__VariableValuesDict = dict() # private variable <variable name>-<variable value>

      # APBOX (int): displays the AutoSnap aperture box. Global variable.
      VariableName = QadMsg.translate("Environment variables", "APBOX") # x lupdate
      VariableDescr = QadMsg.translate("Environment variables", "Turns the display of the AutoSnap aperture box on or off." + \
                                       "\nThe aperture box is displayed in the center of the crosshairs when you snap to an object.") # x lupdate
      VariableDescr = VariableDescr + "\n" + QadMsg.translate("Environment variables", "Integer type")
      VariableDescr = VariableDescr + ", " + QadMsg.translate("Environment variables", "global variable") + "."
      self.__VariableValuesDict[VariableName] = QadVariable(VariableName, int(0), \
                                                            QadVariableTypeEnum.INT, \
                                                            0, 1, \
                                                            VariableDescr, \
                                                            QadVariableLevelEnum.GLOBAL)

      # APERTURE (int): Determines the size of the object selection box. Global variable.
      VariableName = QadMsg.translate("Environment variables", "APERTURE") # x lupdate
      VariableDescr = QadMsg.translate("Environment variables", "Controls the size of the object target box, in pixels.") # x lupdate
      VariableDescr = VariableDescr + "\n" + QadMsg.translate("Environment variables", "Integer type")
      VariableDescr = VariableDescr + ", " + QadMsg.translate("Environment variables", "global variable") + "."
      self.__VariableValuesDict[VariableName] = QadVariable(VariableName, int(10), \
                                                            QadVariableTypeEnum.INT, \
                                                            1, 50, \
                                                            VariableDescr, \
                                                            QadVariableLevelEnum.GLOBAL)

      # ARCMINSEGMENTQTY (int): minimum number of segments for an arc to be recognized. Project variable.
      VariableName = QadMsg.translate("Environment variables", "ARCMINSEGMENTQTY") # x lupdate
      VariableDescr = QadMsg.translate("Environment variables", "Minimum number of segments to approximate an arc.") # x lupdate
      VariableDescr = VariableDescr + "\n" + QadMsg.translate("Environment variables", "Integer type")
      VariableDescr = VariableDescr + ", " + QadMsg.translate("Environment variables", "project variable") + "."
      self.__VariableValuesDict[VariableName] = QadVariable(VariableName, int(12), \
                                                            QadVariableTypeEnum.INT, \
                                                            4, 999, \
                                                            VariableDescr, \
                                                            QadVariableLevelEnum.PROJECT)

      # AUTOSNAP (int): Controls the display of autosnap (sum of bits) markers. Global variable.
      VariableName = QadMsg.translate("Environment variables", "AUTOSNAP")
      VariableDescr = QadMsg.translate("Environment variables", "Controls the display of the AutoSnap marker, tooltip, and magnet." + \
                                       "\nAlso turns on polar and object snap tracking, and controls the display of polar tracking, object snap tracking, and Ortho mode tooltips." + \
                                       "\nThe setting is stored as a bitcode using the sum of the following values:" + \
                                       "\n0 = Turns off the AutoSnap marker, tooltips, and magnet. Also turns off polar tracking, object snap tracking, and tooltips for polar tracking, object snap tracking, and Ortho mode." + \
                                       "\n1 = Turns on the AutoSnap mark." + \
                                       "\n2 = Turns on the AutoSnap tooltips." + \
                                       "\n4 = Turns on the AutoSnap magnet." + \
                                       "\n8 = Turns on polar tracking." + \
                                       "\n16 = Turns on object snap tracking." + \
                                       "\n32 = Turns on tooltips for polar tracking, object snap tracking, and Ortho mode.") # x lupdate
      VariableDescr = VariableDescr + "\n" + QadMsg.translate("Environment variables", "Integer type")
      VariableDescr = VariableDescr + ", " + QadMsg.translate("Environment variables", "global variable") + "."
      self.__VariableValuesDict[VariableName] = QadVariable(VariableName, int(63), \
                                                            QadVariableTypeEnum.INT, \
                                                            0, 64, \
                                                            VariableDescr, \
                                                            QadVariableLevelEnum.GLOBAL)

      # AUTOSNAPCOLOR (str): Sets the color (RGB) of the autosnap markers. Global variable.
      VariableName = QadMsg.translate("Environment variables", "AUTOSNAPCOLOR") # x lupdate
      VariableDescr = QadMsg.translate("Environment variables", "Controls the color of the AutoSnap marker (RGB, #33A02C = green).") # x lupdate
      VariableDescr = VariableDescr + "\n" + QadMsg.translate("Environment variables", "Character type")
      VariableDescr = VariableDescr + ", " + QadMsg.translate("Environment variables", "global variable") + "."
      self.__VariableValuesDict[VariableName] = QadVariable(VariableName, unicode("#33A02C"), \
                                                            QadVariableTypeEnum.COLOR, \
                                                            None, None, \
                                                            VariableDescr, \
                                                            QadVariableLevelEnum.GLOBAL)

      # AUTOSNAPSIZE (int): AutoSnap symbol size in pixels. Global variable.
      VariableName = QadMsg.translate("Environment variables", "AUTOSNAPSIZE") # x lupdate
      VariableDescr = QadMsg.translate("Environment variables", "AutoSnap marker size in pixel.") # x lupdate
      VariableDescr = VariableDescr + "\n" + QadMsg.translate("Environment variables", "Integer type")
      VariableDescr = VariableDescr + ", " + QadMsg.translate("Environment variables", "global variable") + "."
      self.__VariableValuesDict[VariableName] = QadVariable(VariableName, int(5), \
                                                            QadVariableTypeEnum.INT, \
                                                            1, 20, \
                                                            VariableDescr, \
                                                            QadVariableLevelEnum.GLOBAL)

      # AUTOTRECKINGVECTORCOLOR (str): Sets the color (RGB) of the autotrack vector (polar lines, extension lines). Global variable.
      VariableName = QadMsg.translate("Environment variables", "AUTOTRECKINGVECTORCOLOR") # x lupdate
      VariableDescr = QadMsg.translate("Environment variables", "Autotreck vector color (RGB, #33A02C = green).") # x lupdate
      VariableDescr = VariableDescr + "\n" + QadMsg.translate("Environment variables", "Character type")
      VariableDescr = VariableDescr + ", " + QadMsg.translate("Environment variables", "global variable") + "."
      self.__VariableValuesDict[VariableName] = QadVariable(VariableName, unicode("#33A02C"), \
                                                            QadVariableTypeEnum.COLOR, \
                                                            None, None, \
                                                            VariableDescr, \
                                                            QadVariableLevelEnum.GLOBAL)

      # CIRCLEMINSEGMENTQTY (int): minimum number of segments for a circle to be recognized. Project variable.
      VariableName = QadMsg.translate("Environment variables", "CIRCLEMINSEGMENTQTY") # x lupdate
      VariableDescr = QadMsg.translate("Environment variables", "Minimum number of segments to approximate a circle.") # x lupdate
      VariableDescr = VariableDescr + "\n" + QadMsg.translate("Environment variables", "Integer type")
      VariableDescr = VariableDescr + ", " + QadMsg.translate("Environment variables", "project variable") + "."
      self.__VariableValuesDict[VariableName] = QadVariable(VariableName, int(12), \
                                                            QadVariableTypeEnum.INT, \
                                                            6, 999, \
                                                            VariableDescr, \
                                                            QadVariableLevelEnum.PROJECT)

      # CMDHISTORYBACKCOLOR (str): Sets the background color (RGB) of the command history window. Global variable.
      VariableName = QadMsg.translate("Environment variables", "CMDHISTORYBACKCOLOR") # x lupdate
      VariableDescr = QadMsg.translate("Environment variables", "Command history background color (RGB, #C8C8C8 = grey).") # x lupdate
      VariableDescr = VariableDescr + "\n" + QadMsg.translate("Environment variables", "Character type")
      VariableDescr = VariableDescr + ", " + QadMsg.translate("Environment variables", "global variable") + "."
      self.__VariableValuesDict[VariableName] = QadVariable(VariableName, unicode("#C8C8C8"), \
                                                            QadVariableTypeEnum.COLOR, \
                                                            None, None, \
                                                            VariableDescr, \
                                                            QadVariableLevelEnum.GLOBAL)

      # CMDHISTORYFORECOLOR (str): Sets the color (RGB) of the command history window text. Global variable.
      VariableName = QadMsg.translate("Environment variables", "CMDHISTORYFORECOLOR") # x lupdate
      VariableDescr = QadMsg.translate("Environment variables", "Command history text color (RGB, #000000 = black).") # x lupdate
      VariableDescr = VariableDescr + "\n" + QadMsg.translate("Environment variables", "Character type")
      VariableDescr = VariableDescr + ", " + QadMsg.translate("Environment variables", "global variable") + "."
      self.__VariableValuesDict[VariableName] = QadVariable(VariableName, unicode("#000000"), \
                                                            QadVariableTypeEnum.COLOR, \
                                                            None, None, \
                                                            VariableDescr, \
                                                            QadVariableLevelEnum.GLOBAL)

      # CMDINPUTHISTORYMAX (int): Sets the maximum number of commands in the historicization list. Global variable.
      VariableName = QadMsg.translate("Environment variables", "CMDINPUTHISTORYMAX") # x lupdate
      VariableDescr = QadMsg.translate("Environment variables", "Sets the maximum number of previous input values that are stored for a prompt in a command.") # x lupdate
      VariableDescr = VariableDescr + "\n" + QadMsg.translate("Environment variables", "Integer type")
      VariableDescr = VariableDescr + ", " + QadMsg.translate("Environment variables", "global variable") + "."
      self.__VariableValuesDict[VariableName] = QadVariable(VariableName, int(20), \
                                                            QadVariableTypeEnum.INT, \
                                                            1, 999, \
                                                            VariableDescr, \
                                                            QadVariableLevelEnum.GLOBAL)

      # CMDLINEBACKCOLOR (str): Sets the background color (RGB) of the command window. Global variable.
      VariableName = QadMsg.translate("Environment variables", "CMDLINEBACKCOLOR") # x lupdate
      VariableDescr = QadMsg.translate("Environment variables", "Active prompt background color (RGB, #FFFFFF = white).") # x lupdate
      VariableDescr = VariableDescr + "\n" + QadMsg.translate("Environment variables", "Character type")
      VariableDescr = VariableDescr + ", " + QadMsg.translate("Environment variables", "global variable") + "."
      self.__VariableValuesDict[VariableName] = QadVariable(VariableName, unicode("#FFFFFF"), \
                                                            QadVariableTypeEnum.COLOR, \
                                                            None, None, \
                                                            VariableDescr, \
                                                            QadVariableLevelEnum.GLOBAL)

      # CMDLINEFORECOLOR (str): Sets the color (RGB) of the command history window text. Global variable.
      VariableName = QadMsg.translate("Environment variables", "CMDLINEFORECOLOR") # x lupdate
      VariableDescr = QadMsg.translate("Environment variables", "Active prompt color (RGB, #000000 = black).") # x lupdate
      VariableDescr = VariableDescr + "\n" + QadMsg.translate("Environment variables", "Character type")
      VariableDescr = VariableDescr + ", " + QadMsg.translate("Environment variables", "global variable") + "."
      self.__VariableValuesDict[VariableName] = QadVariable(VariableName, unicode("#000000"), \
                                                            QadVariableTypeEnum.COLOR, \
                                                            None, None, \
                                                            VariableDescr, \
                                                            QadVariableLevelEnum.GLOBAL)

      # CMDLINEOPTBACKCOLOR (str): Sets the background color (RGB) of the command option keyword. Global variable.
      VariableName = QadMsg.translate("Environment variables", "CMDLINEOPTBACKCOLOR") # x lupdate
      VariableDescr = QadMsg.translate("Environment variables", "Command option keyword background color (RGB, #D2D2D2 = grey).") # x lupdate
      VariableDescr = VariableDescr + "\n" + QadMsg.translate("Environment variables", "Character type")
      VariableDescr = VariableDescr + ", " + QadMsg.translate("Environment variables", "global variable") + "."
      self.__VariableValuesDict[VariableName] = QadVariable(VariableName, unicode("#D2D2D2"), \
                                                            QadVariableTypeEnum.COLOR, \
                                                            None, None, \
                                                            VariableDescr, \
                                                            QadVariableLevelEnum.GLOBAL)

      # CMDLINEOPTCOLOR (str): Sets the color (RGB) of the command option keyword. Global variable.
      VariableName = QadMsg.translate("Environment variables", "CMDLINEOPTCOLOR") # x lupdate
      VariableDescr = QadMsg.translate("Environment variables", "Command option keyword color (RGB, #0000FF = blue).") # x lupdate
      VariableDescr = VariableDescr + "\n" + QadMsg.translate("Environment variables", "Character type")
      VariableDescr = VariableDescr + ", " + QadMsg.translate("Environment variables", "global variable") + "."
      self.__VariableValuesDict[VariableName] = QadVariable(VariableName, unicode("#0000FF"), \
                                                            QadVariableTypeEnum.COLOR, \
                                                            None, None, \
                                                            VariableDescr, \
                                                            QadVariableLevelEnum.GLOBAL)

      # CMDLINEOPTHIGHLIGHTEDCOLOR (str): Sets the color (RGB) of the highlighted command option. Global variable.
      VariableName = QadMsg.translate("Environment variables", "CMDLINEOPTHIGHLIGHTEDCOLOR") # x lupdate
      VariableDescr = QadMsg.translate("Environment variables", "Command option highlighted color (RGB, #B3B3B3 = grey).") # x lupdate
      VariableDescr = VariableDescr + "\n" + QadMsg.translate("Environment variables", "Character type")
      VariableDescr = VariableDescr + ", " + QadMsg.translate("Environment variables", "global variable") + "."
      self.__VariableValuesDict[VariableName] = QadVariable(VariableName, unicode("#B3B3B3"), \
                                                            QadVariableTypeEnum.COLOR, \
                                                            None, None, \
                                                            VariableDescr, \
                                                            QadVariableLevelEnum.GLOBAL)

      # COPYMODE (int). Global variable.
      # 0 = Set the COPY command to repeat automatically
      # 1 = Sets the COPY command to create a single copy
      VariableName = QadMsg.translate("Environment variables", "COPYMODE") # x lupdate
      VariableDescr = QadMsg.translate("Environment variables", "Controls whether the COPY command repeats automatically:" + \
                                       "\n0 = Sets the COPY command to repeat automatically." + \
                                       "\n1 = Sets the COPY command to create a single copy.") # x lupdate
      VariableDescr = VariableDescr + "\n" + QadMsg.translate("Environment variables", "Integer type")
      VariableDescr = VariableDescr + ", " + QadMsg.translate("Environment variables", "global variable") + "."
      self.__VariableValuesDict[VariableName] = QadVariable(VariableName, int(0), \
                                                            QadVariableTypeEnum.INT, \
                                                            0, 1, \
                                                            VariableDescr, \
                                                            QadVariableLevelEnum.GLOBAL)

      # CROSSINGAREACOLOR (str): Sets the color (RGB) of the object selection area in intersection mode. Global variable.
      VariableName = QadMsg.translate("Environment variables", "CROSSINGAREACOLOR") # x lupdate
      VariableDescr = QadMsg.translate("Environment variables", "Controls the color of the transparent selection area during crossing selection (RGB, #00FF3F = green)." + \
                                       "\nThe SELECTIONAREA system variable must be on.") # x lupdate
      VariableDescr = VariableDescr + "\n" + QadMsg.translate("Environment variables", "Character type")
      VariableDescr = VariableDescr + ", " + QadMsg.translate("Environment variables", "global variable") + "."
      self.__VariableValuesDict[VariableName] = QadVariable(VariableName, unicode("#00FF3F"), \
                                                            QadVariableTypeEnum.COLOR, \
                                                            None, None, \
                                                            VariableDescr, \
                                                            QadVariableLevelEnum.GLOBAL) # green

      # CURSORCOLOR (str): Sets the color (RGB) of the cursor (the cross). Global variable.
      VariableName = QadMsg.translate("Environment variables", "CURSORCOLOR") # x lupdate
      VariableDescr = QadMsg.translate("Environment variables", "Cross pointer color (RGB, #FF0000 = red).") # x lupdate
      VariableDescr = VariableDescr + "\n" + QadMsg.translate("Environment variables", "Character type")
      VariableDescr = VariableDescr + ", " + QadMsg.translate("Environment variables", "global variable") + "."
      self.__VariableValuesDict[VariableName] = QadVariable(VariableName, unicode("#FF0000"), \
                                                            QadVariableTypeEnum.COLOR, \
                                                            None, None, \
                                                            VariableDescr, \
                                                            QadVariableLevelEnum.GLOBAL)

      # CURSORSIZE (int): Sets the size of the cursor (the cross) in pixels. Global variable.
      VariableName = QadMsg.translate("Environment variables", "CURSORSIZE") # x lupdate
      VariableDescr = QadMsg.translate("Environment variables", "Determines the size of the crosshairs as a percentage of the screen size.") # x lupdate
      VariableDescr = VariableDescr + "\n" + QadMsg.translate("Environment variables", "Integer type")
      VariableDescr = VariableDescr + ", " + QadMsg.translate("Environment variables", "global variable") + "."
      self.__VariableValuesDict[VariableName] = QadVariable(VariableName, int(5), \
                                                            QadVariableTypeEnum.INT, \
                                                            1, 100, \
                                                            VariableDescr, \
                                                            QadVariableLevelEnum.GLOBAL)

      # DELOBJ (int): Controls whether geometry used to create other objects is retained or deleted. Global variable.
      VariableName = QadMsg.translate("Environment variables", "DELOBJ") # x lupdate
      VariableDescr = QadMsg.translate("Environment variables", "Controls whether geometry used to create other objects is retained or deleted:" + \
                                       "\n0  = All defining geometry is retained." + \
                                       "\n1  = Deletes all defining geometry." + \
                                       "\n-1 = Ask the user for delete all defining geometry.") # x lupdate
      VariableDescr = VariableDescr + "\n" + QadMsg.translate("Environment variables", "Integer type")
      VariableDescr = VariableDescr + ", " + QadMsg.translate("Environment variables", "global variable") + "."
      self.__VariableValuesDict[VariableName] = QadVariable(VariableName, int(1), \
                                                            QadVariableTypeEnum.INT, \
                                                            -1, 1, \
                                                            VariableDescr, \
                                                            QadVariableLevelEnum.GLOBAL)

      # DIMSTYLE (str): Sets the name of the current dimensioning style. Project variable.
      VariableName = QadMsg.translate("Environment variables", "DIMSTYLE") # x lupdate
      VariableDescr = QadMsg.translate("Environment variables", "Stores the name of the current dimension style.") # x lupdate
      VariableDescr = VariableDescr + "\n" + QadMsg.translate("Environment variables", "Character type")
      VariableDescr = VariableDescr + ", " + QadMsg.translate("Environment variables", "project variable") + "."
      self.__VariableValuesDict[VariableName] = QadVariable(VariableName, unicode(""), \
                                                            QadVariableTypeEnum.STRING, \
                                                            None, None, \
                                                            VariableDescr, \
                                                            QadVariableLevelEnum.PROJECT)

      # DYNDIGRIP (int): Controls the display of dynamic dimensions when editing grip stretch. Global variable.
      # The DYNDIVIS system variable must be set to 2 to display all dynamic dimensions.
      # The setting is stored as a binary code using the sum of the values
      VariableName = QadMsg.translate("Environment variables", "DYNDIGRIP") # x lupdate
      VariableDescr = QadMsg.translate("Environment variables", "Turns Dynamic Input features on and off." + \
                                       "\n0 = None." + \
                                       "\n1 = Resulting dimension." + \
                                       "\n2 = Length change dimension." + \
                                       "\n4 = Absolute angle dimension." + \
                                       "\n8 = Angle change dimension.") # x lupdate
                                       #"\n16 = Arc radius dimension.") # not supported for now
      VariableDescr = VariableDescr + "\n" + QadMsg.translate("Environment variables", "Integer type")
      VariableDescr = VariableDescr + ", " + QadMsg.translate("Environment variables", "global variable") + "."
      self.__VariableValuesDict[VariableName] = QadVariable(VariableName, int(31), \
                                                            QadVariableTypeEnum.INT, \
                                                            0, 31, \
                                                            VariableDescr, \
                                                            QadVariableLevelEnum.GLOBAL)

      # DYNDIVIS (int): Controls the number of dynamic dimensions displayed when editing grip stretching. Global variable.
      VariableName = QadMsg.translate("Environment variables", "DYNDIVIS") # x lupdate
      VariableDescr = QadMsg.translate("Environment variables", "Controls how many dynamic dimensions are displayed during grip stretch editing." + \
                                       "\n0 = Only the first dynamic dimension in the cycle order." + \
                                       "\n1 = Only the first two dynamic dimensions in the cycle order." + \
                                       "\n2 = All dynamic dimensions, as controlled by the DYNDIGRIP system variable.") # x lupdate
      VariableDescr = VariableDescr + "\n" + QadMsg.translate("Environment variables", "Integer type")
      VariableDescr = VariableDescr + ", " + QadMsg.translate("Environment variables", "global variable") + "."
      self.__VariableValuesDict[VariableName] = QadVariable(VariableName, int(1), \
                                                            QadVariableTypeEnum.INT, \
                                                            0, 2, \
                                                            VariableDescr, \
                                                            QadVariableLevelEnum.GLOBAL)

      # DYNEDITFORECOLOR (str): Sets the color (RGB) of the dynamic input window text. Global variable.
      VariableName = QadMsg.translate("Environment variables", "DYNEDITFORECOLOR") # x lupdate
      VariableDescr = QadMsg.translate("Environment variables", "Dynamic input text color (RGB, #000000 = black).") # x lupdate
      VariableDescr = VariableDescr + "\n" + QadMsg.translate("Environment variables", "Character type")
      VariableDescr = VariableDescr + ", " + QadMsg.translate("Environment variables", "global variable") + "."
      self.__VariableValuesDict[VariableName] = QadVariable(VariableName, unicode("#000000"), \
                                                            QadVariableTypeEnum.COLOR, \
                                                            None, None, \
                                                            VariableDescr, \
                                                            QadVariableLevelEnum.GLOBAL)

      # DYNEDITBACKCOLOR (str): Sets the background color (RGB) of the dynamic input window. Global variable.
      VariableName = QadMsg.translate("Environment variables", "DYNEDITBACKCOLOR") # x lupdate
      VariableDescr = QadMsg.translate("Environment variables", "Dynamic input background text color (RGB, #939393 = gray).") # x lupdate
      VariableDescr = VariableDescr + "\n" + QadMsg.translate("Environment variables", "Character type")
      VariableDescr = VariableDescr + ", " + QadMsg.translate("Environment variables", "global variable") + "."
      self.__VariableValuesDict[VariableName] = QadVariable(VariableName, unicode("#939393"), \
                                                            QadVariableTypeEnum.COLOR, \
                                                            None, None, \
                                                            VariableDescr, \
                                                            QadVariableLevelEnum.GLOBAL)

      # DYNEDITBORDERCOLOR (str): Sets the color (RGB) of the dynamic input window border. Global variable.
      VariableName = QadMsg.translate("Environment variables", "DYNEDITBORDERCOLOR") # x lupdate
      VariableDescr = QadMsg.translate("Environment variables", "Dynamic input border color (RGB, #000000 = black).") # x lupdate
      VariableDescr = VariableDescr + "\n" + QadMsg.translate("Environment variables", "Character type")
      VariableDescr = VariableDescr + ", " + QadMsg.translate("Environment variables", "global variable") + "."
      self.__VariableValuesDict[VariableName] = QadVariable(VariableName, unicode("#000000"), \
                                                            QadVariableTypeEnum.COLOR, \
                                                            None, None, \
                                                            VariableDescr, \
                                                            QadVariableLevelEnum.GLOBAL)

      # DYNMODE (int): Turns dynamic input functions on and off. Global variable.
      VariableName = QadMsg.translate("Environment variables", "DYNMODE") # x lupdate
      VariableDescr = QadMsg.translate("Environment variables", "Turns Dynamic Input features on and off." + \
                                       "\n0 = All Dynamic Input features, including dynamic prompts, off." + \
                                       "\n1 = Pointer input on." + \
                                       "\n2 = Dimensional input on." + \
                                       "\n3 = Both pointer input and dimensional input on.") # x lupdate
      VariableDescr = VariableDescr + "\n" + QadMsg.translate("Environment variables", "Integer type")
      VariableDescr = VariableDescr + ", " + QadMsg.translate("Environment variables", "global variable") + "."
      self.__VariableValuesDict[VariableName] = QadVariable(VariableName, int(3), \
                                                            QadVariableTypeEnum.INT, \
                                                            -3, 3, \
                                                            VariableDescr, \
                                                            QadVariableLevelEnum.GLOBAL)

      # DYNPICOORDS (int): Determines whether the pointer input uses a relative or absolute format for coordinates. Global variable.
      VariableName = QadMsg.translate("Environment variables", "DYNPICOORDS") # x lupdate
      VariableDescr = QadMsg.translate("Environment variables", "Controls whether pointer input uses relative or absolute format for coordinates." + \
                                       "\n0 = Relative." + \
                                       "\n1 = Absolute.") # x lupdate
      VariableDescr = VariableDescr + "\n" + QadMsg.translate("Environment variables", "Integer type")
      VariableDescr = VariableDescr + ", " + QadMsg.translate("Environment variables", "global variable") + "."
      self.__VariableValuesDict[VariableName] = QadVariable(VariableName, int(0), \
                                                            QadVariableTypeEnum.INT, \
                                                            0, 1, \
                                                            VariableDescr, \
                                                            QadVariableLevelEnum.GLOBAL)

      # DYNPIFORMAT (int): Determines whether the pointer input uses a polar or Cartesian format for coordinates. Global variable.
      VariableName = QadMsg.translate("Environment variables", "DYNPIFORMAT") # x lupdate
      VariableDescr = QadMsg.translate("Environment variables", "Controls whether pointer input uses polar or cartesian format for coordinates." + \
                                       "\n0 = Polar." + \
                                       "\n1 = Cartesian.") # x lupdate
      VariableDescr = VariableDescr + "\n" + QadMsg.translate("Environment variables", "Integer type")
      VariableDescr = VariableDescr + ", " + QadMsg.translate("Environment variables", "global variable") + "."
      self.__VariableValuesDict[VariableName] = QadVariable(VariableName, int(0), \
                                                            QadVariableTypeEnum.INT, \
                                                            0, 1, \
                                                            VariableDescr, \
                                                            QadVariableLevelEnum.GLOBAL)

      # DYNPIVIS (int): Controls when pointer input is displayed. Global variable.
      VariableName = QadMsg.translate("Environment variables", "DYNPIVIS") # x lupdate
      VariableDescr = QadMsg.translate("Environment variables", "Controls when pointer input is displayed." + \
                                       "\n1 = Automatically at a prompt for a point." + \
                                       "\n2 = Always.") # x lupdate
                                       #"\n0 = Only when you type at a prompt for a point." + \ not supported, for now
      VariableDescr = VariableDescr + "\n" + QadMsg.translate("Environment variables", "Integer type")
      VariableDescr = VariableDescr + ", " + QadMsg.translate("Environment variables", "global variable") + "."
      self.__VariableValuesDict[VariableName] = QadVariable(VariableName, int(1), \
                                                            QadVariableTypeEnum.INT, \
                                                            0, 2, \
                                                            VariableDescr, \
                                                            QadVariableLevelEnum.GLOBAL)

      # DYNPROMPT (int): Controls the display of prompts in dynamic input descriptions. Global variable.
      VariableName = QadMsg.translate("Environment variables", "DYNPROMPT") # x lupdate
      VariableDescr = QadMsg.translate("Environment variables", "Controls display of prompts in Dynamic Input tooltips." + \
                                       "\n0 = Off." + \
                                       "\n1 = On.") # x lupdate
      VariableDescr = VariableDescr + "\n" + QadMsg.translate("Environment variables", "Integer type")
      VariableDescr = VariableDescr + ", " + QadMsg.translate("Environment variables", "global variable") + "."
      self.__VariableValuesDict[VariableName] = QadVariable(VariableName, int(1), \
                                                            QadVariableTypeEnum.INT, \
                                                            0, 1, \
                                                            VariableDescr, \
                                                            QadVariableLevelEnum.GLOBAL)

      # DYNTOOLTIPS (int): Determines which tooltips the tooltip appearance settings affect. Global variable.
      VariableName = QadMsg.translate("Environment variables", "DYNTOOLTIPS") # x lupdate
      VariableDescr = QadMsg.translate("Environment variables", "Controls which tooltips are affected by tooltip appearance settings." + \
                                       "\n0 = Only Dynamic Input value fields ." + \
                                       "\n1 = All drafting tooltips.") # x lupdate
      VariableDescr = VariableDescr + "\n" + QadMsg.translate("Environment variables", "Integer type")
      VariableDescr = VariableDescr + ", " + QadMsg.translate("Environment variables", "global variable") + "."
      self.__VariableValuesDict[VariableName] = QadVariable(VariableName, int(1), \
                                                            QadVariableTypeEnum.INT, \
                                                            0, 1, \
                                                            VariableDescr, \
                                                            QadVariableLevelEnum.GLOBAL)

      # DYNTRECKINGVECTORCOLOR (str): Sets the color (RGB) of the track vector for dynamic input (extension lines). Global variable.
      VariableName = QadMsg.translate("Environment variables", "DYNTRECKINGVECTORCOLOR") # x lupdate
      VariableDescr = QadMsg.translate("Environment variables", "Autotreck vector color (RGB, #969C9A = gray).") # x lupdate
      VariableDescr = VariableDescr + "\n" + QadMsg.translate("Environment variables", "Character type")
      VariableDescr = VariableDescr + ", " + QadMsg.translate("Environment variables", "global variable") + "."
      self.__VariableValuesDict[VariableName] = QadVariable(VariableName, unicode("#969C9A"), \
                                                            QadVariableTypeEnum.COLOR, \
                                                            None, None, \
                                                            VariableDescr, \
                                                            QadVariableLevelEnum.GLOBAL)

      # EDGEMODE (int): Controls the EXTEND and TRIM commands. Global variable.
      # O = Actual dimensions of reference objects are used
      # 1 = Extensions of reference objects are used (e.g. an arc is considered a circle)
      VariableName = QadMsg.translate("Environment variables", "EDGEMODE") # x lupdate
      VariableDescr = QadMsg.translate("Environment variables", "Controls how the TRIM and EXTEND commands determine cutting and boundary edges:" + \
                                       "\n0 = Uses the selected edge without an extensions." + \
                                       "\n1 = Extends or trims the selected object to an imaginary extension of the cutting or boundary edge.") # x lupdate
      VariableDescr = VariableDescr + "\n" + QadMsg.translate("Environment variables", "Integer type")
      VariableDescr = VariableDescr + ", " + QadMsg.translate("Environment variables", "global variable") + "."
      self.__VariableValuesDict[VariableName] = QadVariable(VariableName, int(0), \
                                                            QadVariableTypeEnum.INT, \
                                                            0, 1, \
                                                            VariableDescr, \
                                                            QadVariableLevelEnum.GLOBAL)

      # ELLIPSEMINSEGMENTQTY (int): minimum number of segments for an ellipse to be recognized. Project variable.
      VariableName = QadMsg.translate("Environment variables", "ELLIPSEMINSEGMENTQTY") # x lupdate
      VariableDescr = QadMsg.translate("Environment variables", "Minimum number of segments to approximate an ellipse.") # x lupdate
      VariableDescr = VariableDescr + "\n" + QadMsg.translate("Environment variables", "Integer type")
      VariableDescr = VariableDescr + ", " + QadMsg.translate("Environment variables", "project variable") + "."
      self.__VariableValuesDict[VariableName] = QadVariable(VariableName, int(12), \
                                                            QadVariableTypeEnum.INT, \
                                                            8, 999, \
                                                            VariableDescr, \
                                                            QadVariableLevelEnum.PROJECT)

      # ELLIPSEARCMINSEGMENTQTY (int): minimum number of segments for an ellipse arc to be recognized. Project variable.
      VariableName = QadMsg.translate("Environment variables", "ELLIPSEARCMINSEGMENTQTY") # x lupdate
      VariableDescr = QadMsg.translate("Environment variables", "Minimum number of segments to approximate an arc of ellipse.") # x lupdate
      VariableDescr = VariableDescr + "\n" + QadMsg.translate("Environment variables", "Integer type")
      VariableDescr = VariableDescr + ", " + QadMsg.translate("Environment variables", "project variable") + "."
      self.__VariableValuesDict[VariableName] = QadVariable(VariableName, int(12), \
                                                            QadVariableTypeEnum.INT, \
                                                            8, 999, \
                                                            VariableDescr, \
                                                            QadVariableLevelEnum.PROJECT)

      # FILLETRAD (float): Radius applied to fillet (degrees). Project variable.
      VariableName = QadMsg.translate("Environment variables", "FILLETRAD") # x lupdate
      VariableDescr = QadMsg.translate("Environment variables", "Stores the current fillet radius.") # x lupdate
      VariableDescr = VariableDescr + "\n" + QadMsg.translate("Environment variables", "Real type")
      VariableDescr = VariableDescr + ", " + QadMsg.translate("Environment variables", "project variable") + "."
      self.__VariableValuesDict[VariableName] = QadVariable(VariableName, float(0.0), \
                                                            QadVariableTypeEnum.FLOAT, \
                                                            0.000001, None, \
                                                            VariableDescr, \
                                                            QadVariableLevelEnum.PROJECT)

      # GRIPCOLOR (str): Sets the color (RGB) of unselected grips. Global variable.
      VariableName = QadMsg.translate("Environment variables", "GRIPCOLOR") # x lupdate
      VariableDescr = QadMsg.translate("Environment variables", "Controls the color of unselected grips (RGB, #100DD6 = blue).") # x lupdate
      VariableDescr = VariableDescr + "\n" + QadMsg.translate("Environment variables", "Character type")
      VariableDescr = VariableDescr + ", " + QadMsg.translate("Environment variables", "global variable") + "."
      self.__VariableValuesDict[VariableName] = QadVariable(VariableName, unicode("#100DD6"), \
                                                            QadVariableTypeEnum.COLOR, \
                                                            None, None, \
                                                            VariableDescr, \
                                                            QadVariableLevelEnum.GLOBAL) # blu

      # GRIPCONTOUR (str): Sets the color (RGB) of the grip border. Global variable.
      VariableName = QadMsg.translate("Environment variables", "GRIPCONTOUR") # x lupdate
      VariableDescr = QadMsg.translate("Environment variables", "Controls the color of the grip contour (RGB, #939393 = gray).") # x lupdate
      VariableDescr = VariableDescr + "\n" + QadMsg.translate("Environment variables", "Character type")
      VariableDescr = VariableDescr + ", " + QadMsg.translate("Environment variables", "global variable") + "."
      self.__VariableValuesDict[VariableName] = QadVariable(VariableName, unicode("#939393"), \
                                                            QadVariableTypeEnum.COLOR, \
                                                            None, None, \
                                                            VariableDescr, \
                                                            QadVariableLevelEnum.GLOBAL) # gray

      # GRIPHOT(str): Sets the color (RGB) of the selected grips. Global variable.
      VariableName = QadMsg.translate("Environment variables", "GRIPHOT") # x lupdate
      VariableDescr = QadMsg.translate("Environment variables", "Controls the color of selected grips (RGB, #FF0000 = red).") # x lupdate
      VariableDescr = VariableDescr + "\n" + QadMsg.translate("Environment variables", "Character type")
      VariableDescr = VariableDescr + ", " + QadMsg.translate("Environment variables", "global variable") + "."
      self.__VariableValuesDict[VariableName] = QadVariable(VariableName, unicode("#FF0000"), \
                                                            QadVariableTypeEnum.COLOR, \
                                                            None, None, \
                                                            VariableDescr, \
                                                            QadVariableLevelEnum.GLOBAL) # red

      # GRIPHOVER(str): Sets the color (RGB) of unselected grips when the cursor stops on them. Global variable.
      VariableName = QadMsg.translate("Environment variables", "GRIPHOVER") # x lupdate
      VariableDescr = QadMsg.translate("Environment variables", "Controls the fill color of an unselected grip when the cursor pauses over it (RGB, #FF7F7F = orange).") # x lupdate
      VariableDescr = VariableDescr + "\n" + QadMsg.translate("Environment variables", "Character type")
      VariableDescr = VariableDescr + ", " + QadMsg.translate("Environment variables", "global variable") + "."
      self.__VariableValuesDict[VariableName] = QadVariable(VariableName, unicode("#FF7F7F"), \
                                                            QadVariableTypeEnum.COLOR, \
                                                            None, None, \
                                                            VariableDescr, \
                                                            QadVariableLevelEnum.GLOBAL) # orange

      # GRIPMULTIFUNCTIONAL (int): Specifies access methods for multifunctional grip options. Global variable.
      VariableName = QadMsg.translate("Environment variables", "GRIPMULTIFUNCTIONAL") # x lupdate
      VariableDescr = QadMsg.translate("Environment variables", "Specifies the access methods to multi-functional grips." + \
                                       "\n0 = Access to multi-functional grips is disabled." + \
                                       "\n2 = Access multi-functional grips with the dynamic menu and the Hot Grip shortcut menu.") # x lupdate
      VariableDescr = VariableDescr + "\n" + QadMsg.translate("Environment variables", "Integer type")
      VariableDescr = VariableDescr + ", " + QadMsg.translate("Environment variables", "global variable") + "."
      self.__VariableValuesDict[VariableName] = QadVariable(VariableName, int(3), \
                                                            QadVariableTypeEnum.INT, \
                                                            0, 3, \
                                                            VariableDescr, \
                                                            QadVariableLevelEnum.GLOBAL)

      # GRIPOBJLIMIT (int): Controls the display of grips based on the number of objects selected. Global variable.
      VariableName = QadMsg.translate("Environment variables", "GRIPOBJLIMIT") # x lupdate
      VariableDescr = QadMsg.translate("Environment variables", "Suppresses the display of grips when the selection set includes more than the specified number of objects." + \
                                       "\nThe valid range is 0 to 32,767. For example, when set to 1, grips are suppressed when more than one object is selected." + \
                                       "\nWhen set to 0, grips are always displayed.") # x lupdate
      VariableDescr = VariableDescr + "\n" + QadMsg.translate("Environment variables", "Integer type")
      VariableDescr = VariableDescr + ", " + QadMsg.translate("Environment variables", "global variable") + "."
      self.__VariableValuesDict[VariableName] = QadVariable(VariableName, int(100), \
                                                            QadVariableTypeEnum.INT, \
                                                            0, 32767, \
                                                            VariableDescr, \
                                                            QadVariableLevelEnum.GLOBAL)

      # GRIPS (int): Controls the display of grips on selected objects. Global variable.
      VariableName = QadMsg.translate("Environment variables", "GRIPS") # x lupdate
      VariableDescr = QadMsg.translate("Environment variables", "Controls the use of selection set grips for the Stretch, Move, Rotate, Scale, and Mirror Grip modes." + \
                                       "\n0 = Hides grips." + \
                                       "\n1 = Displays grips." + \
                                       "\n2 = Displays additional midpoint grips on polyline segments.") # x lupdate
      VariableDescr = VariableDescr + "\n" + QadMsg.translate("Environment variables", "Integer type")
      VariableDescr = VariableDescr + ", " + QadMsg.translate("Environment variables", "global variable") + "."
      self.__VariableValuesDict[VariableName] = QadVariable(VariableName, int(2), \
                                                            QadVariableTypeEnum.INT, \
                                                            0, 2, \
                                                            VariableDescr, \
                                                            QadVariableLevelEnum.GLOBAL)

      # GRIPSIZE (int): Sets the size of the grip symbols in pixels. Global variable.
      VariableName = QadMsg.translate("Environment variables", "GRIPSIZE") # x lupdate
      VariableDescr = QadMsg.translate("Environment variables", "Grip symbol size in pixel.") # x lupdate
      VariableDescr = VariableDescr + "\n" + QadMsg.translate("Environment variables", "Integer type")
      VariableDescr = VariableDescr + ", " + QadMsg.translate("Environment variables", "global variable") + "."
      self.__VariableValuesDict[VariableName] = QadVariable(VariableName, int(5), \
                                                            QadVariableTypeEnum.INT, \
                                                            1, 999, \
                                                            VariableDescr, \
                                                            QadVariableLevelEnum.GLOBAL)

      # INPUTSEARCHDELAY (int): Controls the time elapsed before keyboard features appear on the command line.
      # Global variable.
      VariableName = QadMsg.translate("Environment variables", "INPUTSEARCHDELAY") # x lupdate
      VariableDescr = QadMsg.translate("Environment variables", "Controls the amount of time that elapses before automated keyboard features display at the Command prompt." + \
                                       "\nValid values are real numbers from 100 to 10,000, which represent milliseconds." + \
                                       "\nThe time delay setting in the INPUTSEARCHOPTIONS system variable must be turned on for INPUTSEARCHDELAY to have an effect.") # x lupdate
      VariableDescr = VariableDescr + "\n" + QadMsg.translate("Environment variables", "Integer type")
      VariableDescr = VariableDescr + ", " + QadMsg.translate("Environment variables", "global variable") + "."
      self.__VariableValuesDict[VariableName] = QadVariable(VariableName, int(500), \
                                                            QadVariableTypeEnum.INT, \
                                                            100, 10000, \
                                                            VariableDescr, \
                                                            QadVariableLevelEnum.GLOBAL)

      # INPUTSEARCHOPTIONS (int): Controls the types of automatic keyboard functions available from the command line. Global variable.
      VariableName = QadMsg.translate("Environment variables", "INPUTSEARCHOPTIONS") # x lupdate
      VariableDescr = QadMsg.translate("Environment variables", "Controls what types of automated keyboard features are available at the Command prompt." + \
                                       "\nThe setting is stored as a bitcode using the sum of the following values:" + \
                                       "\n 0 = Turns off all automated keyboard features when typing at the Command prompt." + \
                                       "\n 1 = Turns on any automated keyboard features when typing at the Command prompt." + \
                                       "\n 2 = Automatically appends suggestions as each keystroke is entered after the second keystroke." + \
                                       "\n 4 = Displays a list of suggestions as keystrokes are entered." + \
                                       "\n 8 = Displays the icon of the command or system variable, if available." + \
                                       "\n16 = Excludes the display of system variables.") # x lupdate
      VariableDescr = VariableDescr + "\n" + QadMsg.translate("Environment variables", "Integer type")
      VariableDescr = VariableDescr + ", " + QadMsg.translate("Environment variables", "global variable") + "."
      self.__VariableValuesDict[VariableName] = QadVariable(VariableName, int(15), \
                                                            QadVariableTypeEnum.INT, \
                                                            0, 31, \
                                                            VariableDescr, \
                                                            QadVariableLevelEnum.GLOBAL)

      # MAXARRAY (int): Limits the size of arrays in the ARRAY command. Global variable.
      VariableName = QadMsg.translate("Environment variables", "MAXARRAY") # x lupdate
      VariableDescr = QadMsg.translate("Environment variables", "Limit the Size of arrays in ARRAY command.") # x lupdate
      VariableDescr = VariableDescr + "\n" + QadMsg.translate("Environment variables", "Integer type")
      VariableDescr = VariableDescr + ", " + QadMsg.translate("Environment variables", "global variable") + "."
      self.__VariableValuesDict[VariableName] = QadVariable(VariableName, int(100000), \
                                                            QadVariableTypeEnum.INT, \
                                                            100, 10000000, \
                                                            VariableDescr, \
                                                            QadVariableLevelEnum.GLOBAL)

      # OFFSETDIST (float): Set the default distance for the offset. Project variable.
      # < 0 offset of an object through a point
      # >= 0 offset of an object across distance
      VariableName = QadMsg.translate("Environment variables", "OFFSETDIST") # x lupdate
      VariableDescr = QadMsg.translate("Environment variables", "Sets the default offset distance:" + \
                                       "\n<0 = Offsets an object through a specified point." + \
                                       "\n>=0 =  Sets the default offset distance.") # x lupdate
      VariableDescr = VariableDescr + "\n" + QadMsg.translate("Environment variables", "Real type")
      VariableDescr = VariableDescr + ", " + QadMsg.translate("Environment variables", "project variable") + "."
      self.__VariableValuesDict[VariableName] = QadVariable(VariableName, float(-1.0), \
                                                            QadVariableTypeEnum.FLOAT, \
                                                            None, None, \
                                                            VariableDescr, \
                                                            QadVariableLevelEnum.PROJECT)

      # OFFSETGAPTYPE (int). Global variable.
      # 0 = Extends line segments to their projected intersections
      # 1 = Connects the line segments at their projected intersections.
      #     The radius of each arc segment is equal to the offset distance
      # 2 = Trim line segments at projected intersections.
      #     The perpendicular distance from each peak to its respective vertex
      #     on the original object is equal to the offset distance.
      VariableName = QadMsg.translate("Environment variables", "OFFSETGAPTYPE") # x lupdate
      VariableDescr = QadMsg.translate("Environment variables", "Controls how potential gaps between segments are treated when polylines are offset:" + \
                                       "\n0 = Extends line segments to their projected intersections." + \
                                       "\n1 = Fillets line segments at their projected intersections. The radius of each arc segment is equal to the offset distance." + \
                                       "\n2 = Chamfers line segments at their projected intersections. The perpendicular distance from each chamfer to its corresponding vertex on the original object is equal to the offset distance.") # x lupdate
      VariableDescr = VariableDescr + "\n" + QadMsg.translate("Environment variables", "Integer type")
      VariableDescr = VariableDescr + ", " + QadMsg.translate("Environment variables", "global variable") + "."
      self.__VariableValuesDict[VariableName] = QadVariable(VariableName, int(0), \
                                                            QadVariableTypeEnum.INT, \
                                                            0, 2, \
                                                            VariableDescr, \
                                                            QadVariableLevelEnum.GLOBAL)

      # ORTHOMODE (int). Project variable.
      # 0 = orthogonal cursor movement mode disabled
      # 1 = orthogonal cursor movement mode enabled
      VariableName = QadMsg.translate("Environment variables", "ORTHOMODE") # x lupdate
      VariableDescr = QadMsg.translate("Environment variables", "Constrains cursor movement to the perpendicular." + \
                                       "\nWhen ORTHOMODE is turned on, the cursor can move only horizontally or vertically:" + \
                                       "\n0 = Turns off Ortho mode." + \
                                       "\n1 = Turns on Ortho mode.") # x lupdate
      VariableDescr = VariableDescr + "\n" + QadMsg.translate("Environment variables", "Integer type")
      VariableDescr = VariableDescr + ", " + QadMsg.translate("Environment variables", "project variable") + "."
      self.__VariableValuesDict[VariableName] = QadVariable(VariableName, int(0), \
                                                            QadVariableTypeEnum.INT, \
                                                            0, 1, \
                                                            VariableDescr, \
                                                            QadVariableLevelEnum.PROJECT)

      # OSMODE (int): Sets the object snap (sum of bits). Global variable.
      # 0 = (NON) none
      # 1 = (FIN) end points of each segment
      # 2 = (MED) midpoint
      # 4 = (CEN) centroid of a polygon
      # 8 = (NOD) to point object
      # 16 = (QUA) quadrant point of a polygon
      # 32 = (INT) intersection of an object (also the intermediate vertices of a linestring or polygon)
      # 64 = (INS) object insertion point (same as 8)
      # 128 = (PER) point perpendicular to an object
      # 256 = (TAN) tangent of an arc, a circle, an ellipse, an elliptical arc or a spline
      # 512 = (NEA) closest point of an object
      # 1024 = (C) Clear all object snaps
      # 2048 = (APP) apparent intersection of two objects that do not intersect in 3D space
      #        but which may appear to intersect in the current view
      # 4096 = (EST) Extension : Displays a temporary extension line or arc when moving the cursor to the endpoint of objects,
      #        so that points can be specified on the extension
      # 8192 = (PAR) Parallel: Constrains a line segment, polyline segment, ray, or xline to be parallel to another linear object
      # 16384 = osnap off
      # 65536 = (PR) Chain distance
      # 131072 = intersection on extension
      # 262144 = deferred perpendicular
      # 524288 = deferred tangent
      # 1048576 = polar tracking
      # 2097152 = end points of the entire polyline
      VariableName = QadMsg.translate("Environment variables", "OSMODE") # x lupdate
      VariableDescr = QadMsg.translate("Environment variables", "Sets running object snaps." + \
                                       "\nThe setting is stored as a bitcode using the sum of the following values:" + \
                                       "\n0 = NONe." + \
                                       "\n1 = ENDpoint." + \
                                       "\n2 = MIDpoint." + \
                                       "\n4 = CENter." + \
                                       "\n8 = NODe." + \
                                       "\n16 = QUAdrant." + \
                                       "\n32 = INTersection." + \
                                       "\n64 = INSertion." + \
                                       "\n128 = PERpendicular." + \
                                       "\n256 = TANgent." + \
                                       "\n512 = NEArest." + \
                                       "\n1024 = QUIck." + \
                                       "\n2048 = APParent Intersection." + \
                                       "\n4096 = EXTension." + \
                                       "\n8192 = PARallel." + \
                                       "\n65536 = PRogressive distance (PR[dist])." + \
                                       "\n131072 = Intersection on extension (EXT_INT)." + \
                                       "\n2097152 = Final points on polyline (FIN_PL).") # x lupdate
      VariableDescr = VariableDescr + "\n" + QadMsg.translate("Environment variables", "Integer type")
      VariableDescr = VariableDescr + ", " + QadMsg.translate("Environment variables", "global variable") + "."
      self.__VariableValuesDict[VariableName] = QadVariable(VariableName, int(0), \
                                                            QadVariableTypeEnum.INT, \
                                                            0, None, \
                                                            VariableDescr, \
                                                            QadVariableLevelEnum.GLOBAL)

      # OSPROGRDISTANCE (float): Progressive distance for PR snap. Project variable.
      VariableName = QadMsg.translate("Environment variables", "OSPROGRDISTANCE") # x lupdate
      VariableDescr = QadMsg.translate("Environment variables", "Progressive distance for <Progressive distance> snap mode.") # x lupdate
      VariableDescr = VariableDescr + "\n" + QadMsg.translate("Environment variables", "Real type")
      VariableDescr = VariableDescr + ", " + QadMsg.translate("Environment variables", "project variable") + "."
      self.__VariableValuesDict[VariableName] = QadVariable(VariableName, float(0.0), \
                                                            QadVariableTypeEnum.FLOAT, \
                                                            None, None, \
                                                            VariableDescr, \
                                                            QadVariableLevelEnum.PROJECT)

      # PICKADD (int): Controls whether subsequent selections replace the current selection set or are added to it.
      # Global variable.
      VariableName = QadMsg.translate("Environment variables", "PICKADD") # x lupdate
      VariableDescr = QadMsg.translate("Environment variables", "Controls whether subsequent selections replace the current selection set or add to it." + \
                                       "\n0 = Turns off PICKADD. The objects most recently selected become the selection set. Previously selected objects are removed from the selection set. Add more objects to the selection set by pressing SHIFT while selecting." + \
                                       "\n1 = Turns on PICKADD. Each object selected, either individually or by windowing, is added to the current selection set. To remove objects from the set, press SHIFT while selecting." + \
                                       "\n2 = Turns on PICKADD. Each object selected, either individually or by windowing, is added to the current selection set. To remove objects from the set, press SHIFT while selecting. Keeps objects selected after the SELECT command ends.") # x lupdate
      VariableDescr = VariableDescr + "\n" + QadMsg.translate("Environment variables", "Integer type")
      VariableDescr = VariableDescr + ", " + QadMsg.translate("Environment variables", "global variable") + "."
      self.__VariableValuesDict[VariableName] = QadVariable(VariableName, int(0), \
                                                            QadVariableTypeEnum.INT, \
                                                            0, 2, \
                                                            VariableDescr, \
                                                            QadVariableLevelEnum.GLOBAL)

      # PICKBOX (int): Sets the size in pixels of the object selection distance
      # from the current position of the pointer. Global variable.
      VariableName = QadMsg.translate("Environment variables", "PICKBOX") # x lupdate
      VariableDescr = QadMsg.translate("Environment variables", "Sets the object selection target height, in pixels.") # x lupdate
      VariableDescr = VariableDescr + "\n" + QadMsg.translate("Environment variables", "Integer type")
      VariableDescr = VariableDescr + ", " + QadMsg.translate("Environment variables", "global variable") + "."
      self.__VariableValuesDict[VariableName] = QadVariable(VariableName, int(5), \
                                                            QadVariableTypeEnum.INT, \
                                                            1, 999, \
                                                            VariableDescr, \
                                                            QadVariableLevelEnum.GLOBAL)

      # PICKBOXCOLOR (str): Sets the color (RGB) of the object selection box. Global variable.
      VariableName = QadMsg.translate("Environment variables", "PICKBOXCOLOR") # x lupdate
      VariableDescr = QadMsg.translate("Environment variables", "Sets the object selection target color (RGB, #FF0000 = red).") # x lupdate
      VariableDescr = VariableDescr + "\n" + QadMsg.translate("Environment variables", "Character type")
      VariableDescr = VariableDescr + ", " + QadMsg.translate("Environment variables", "global variable") + "."
      self.__VariableValuesDict[VariableName] = QadVariable(VariableName, unicode("#FF0000"), \
                                                            QadVariableTypeEnum.COLOR, \
                                                            None, None, \
                                                            VariableDescr, \
                                                            QadVariableLevelEnum.GLOBAL) # red

      # PICKFIRST (int): Controls whether objects can be selected before executing a command. Global variable.
      VariableName = QadMsg.translate("Environment variables", "PICKFIRST") # x lupdate
      VariableDescr = QadMsg.translate("Environment variables", "Controls whether you can select objects before you start a command." + \
                                       "\n0 = Off. You can select objects only after you start a command." + \
                                       "\n1 = On. You can also select objects before you start a command.") # x lupdate
      VariableDescr = VariableDescr + "\n" + QadMsg.translate("Environment variables", "Integer type")
      VariableDescr = VariableDescr + ", " + QadMsg.translate("Environment variables", "global variable") + "."
      self.__VariableValuesDict[VariableName] = QadVariable(VariableName, int(1), \
                                                            QadVariableTypeEnum.INT, \
                                                            0, 1, \
                                                            VariableDescr, \
                                                            QadVariableLevelEnum.GLOBAL)

      # POLARADDANG (string): Stores additional angles for polar tracking and polar snapping. Global variable.
      VariableName = QadMsg.translate("Environment variables", "POLARADDANG") # x lupdate
      VariableDescr = QadMsg.translate("Environment variables", "Stores additional angles for polar tracking and polar snap.") # x lupdate
      VariableDescr = VariableDescr + "\n" + QadMsg.translate("Environment variables", "Character type")
      VariableDescr = VariableDescr + ", " + QadMsg.translate("Environment variables", "global variable") + "."
      self.__VariableValuesDict[VariableName] = QadVariable(VariableName, unicode(""), \
                                                            QadVariableTypeEnum.STRING, \
                                                            None, None, \
                                                            VariableDescr, \
                                                            QadVariableLevelEnum.GLOBAL) # red

      # POLARANG (float): increment of the polar angle for polar pointing (degrees). Global variable.
      VariableName = QadMsg.translate("Environment variables", "POLARANG") # x lupdate
      VariableDescr = QadMsg.translate("Environment variables", "Sets the polar angle increment (degree).") # x lupdate
      VariableDescr = VariableDescr + "\n" + QadMsg.translate("Environment variables", "Real type")
      VariableDescr = VariableDescr + ", " + QadMsg.translate("Environment variables", "global variable") + "."
      self.__VariableValuesDict[VariableName] = QadVariable(VariableName, float(90.0), \
                                                            QadVariableTypeEnum.FLOAT, \
                                                            0.000001, 359.999999, \
                                                            VariableDescr, \
                                                            QadVariableLevelEnum.GLOBAL)

      # POLARMODE (int): Controls settings for polar and object snap tracking. Global variable.
      VariableName = QadMsg.translate("Environment variables", "POLARMODE") # x lupdate
      VariableDescr = QadMsg.translate("Environment variables", "Controls settings for polar and object snap tracking." + \
                                       "\nThe setting is stored as a bitcode using the sum of the following values:" + \
                                       "\nPolar angle measurements" + \
                                       "\n0 = Measure polar angles based on current UCS (absolute)" + \
                                       "\n1 = Measure polar angles from selected objects (relative)" + \
                                       "\nObject snap tracking" + \
                                       "\n0 = Track orthogonally only" + \
                                       "\n2 = Use polar tracking settings in object snap tracking" + \
                                       "\nUse additional polar tracking angles" + \
                                       "\n0 = No" + \
                                       "\n4 = Yes" + \
                                       "\nAcquire object snap tracking points" + \
                                       "\n0 = Acquire automatically" + \
                                       "\n8 = Press Shift to acquire") # x lupdate
      VariableDescr = VariableDescr + "\n" + QadMsg.translate("Environment variables", "Integer type")
      VariableDescr = VariableDescr + ", " + QadMsg.translate("Environment variables", "global variable") + "."
      self.__VariableValuesDict[VariableName] = QadVariable(VariableName, int(0), \
                                                            QadVariableTypeEnum.INT, \
                                                            0, 15, \
                                                            VariableDescr, \
                                                            QadVariableLevelEnum.GLOBAL)

      # SELECTIONAREA (int): Controls the effects of the area selection display. Global variable.
      # from the current position of the pointer
      VariableName = QadMsg.translate("Environment variables", "SELECTIONAREA") # x lupdate
      VariableDescr = QadMsg.translate("Environment variables", "Controls the display of effects for selection areas." + \
                                       "\nSelection areas are created by the Window, Crossing, WPolygon, CPolygon, WCircle, CCircle, WObjects, CObjects, WBuffer and CBuffer options of SELECT." + \
                                       "\n0 = Off" + \
                                       "\n1 = On") # x lupdate
      VariableDescr = VariableDescr + "\n" + QadMsg.translate("Environment variables", "Integer type")
      VariableDescr = VariableDescr + ", " + QadMsg.translate("Environment variables", "global variable") + "."
      self.__VariableValuesDict[VariableName] = QadVariable(VariableName, int(1), \
                                                            QadVariableTypeEnum.INT, \
                                                            0, 1, \
                                                            VariableDescr, \
                                                            QadVariableLevelEnum.GLOBAL)

      # SELECTIONAREAOPACITY (int): Controls the effects of the area selection display
      # from the current position of the pointer. Global variable.
      VariableName = QadMsg.translate("Environment variables", "SELECTIONAREAOPACITY") # x lupdate
      VariableDescr = QadMsg.translate("Environment variables", "Controls the transparency of the selection area during window and crossing selection." + \
                                       "\nThe valid range is 0 to 100. The lower the setting, the more transparent the area. A value of 100 makes the area opaque. The SELECTIONAREA system variable must be on.") # x lupdate
      VariableDescr = VariableDescr + "\n" + QadMsg.translate("Environment variables", "Integer type")
      VariableDescr = VariableDescr + ", " + QadMsg.translate("Environment variables", "global variable") + "."
      self.__VariableValuesDict[VariableName] = QadVariable(VariableName, int(25), \
                                                            QadVariableTypeEnum.INT, \
                                                            0, 100, \
                                                            VariableDescr, \
                                                            QadVariableLevelEnum.GLOBAL)

      # SHORTCUTMENU (int): Controls whether the Default, Edit, and Command mode shortcut menus are available
      # in the drawing area. Global variable.
      VariableName = QadMsg.translate("Environment variables", "SHORTCUTMENU") # x lupdate
      VariableDescr = QadMsg.translate("Environment variables", "Controls whether Default, Edit, and Command mode shortcut menus are available in the drawing area." + \
                                       "\nThe setting is stored as a bitcode using the sum of the following values:" + \
                                       "\n0 = Disables all Default, Edit, and Command mode shortcut menus" + \
                                       "\n1 = Enables Default mode shortcut menus" + \
                                       "\n2 = Enables Edit mode shortcut menus" + \
                                       "\n4 = Enables Command mode shortcut menus whenever a command is active" + \
                                       "\n8 = Enables Command mode shortcut menus only when command options are currently available at the Command prompt" + \
                                       "\n16 = Enables the display of a shortcut menu when the right button on the pointing device is held down long enough") # x lupdate
      VariableDescr = VariableDescr + "\n" + QadMsg.translate("Environment variables", "Integer type")
      VariableDescr = VariableDescr + ", " + QadMsg.translate("Environment variables", "global variable") + "."
      self.__VariableValuesDict[VariableName] = QadVariable(VariableName, int(11), \
                                                            QadVariableTypeEnum.INT, \
                                                            0, 64, \
                                                            VariableDescr, \
                                                            QadVariableLevelEnum.GLOBAL)


      # SHORTCUTMENUDURATION (int): Controls whether the Default, Edit, and Command mode shortcut menus are available
      # in the drawing area. Global variable.
      VariableName = QadMsg.translate("Environment variables", "SHORTCUTMENUDURATION") # x lupdate
      VariableDescr = QadMsg.translate("Environment variables", "Specifies how long the right button on a pointing device must be pressed to display a shortcut menu in the drawing area." + \
                                       "\nThe value is expressed in milliseconds, and the valid range is 100 to 10000.") # x lupdate
      VariableDescr = VariableDescr + "\n" + QadMsg.translate("Environment variables", "Integer type")
      VariableDescr = VariableDescr + ", " + QadMsg.translate("Environment variables", "global variable") + "."
      self.__VariableValuesDict[VariableName] = QadVariable(VariableName, int(250), \
                                                            QadVariableTypeEnum.INT, \
                                                            100, 10000, \
                                                            VariableDescr, \
                                                            QadVariableLevelEnum.GLOBAL)

      # SUPPORTPATH (str): Searc path for support files. Global variable.
      default = os.path.abspath(os.path.dirname(__file__) + "\\support")
      VariableName = QadMsg.translate("Environment variables", "SUPPORTPATH") # x lupdate
      VariableDescr = QadMsg.translate("Environment variables", "Searching path for support files.") # x lupdate
      VariableDescr = VariableDescr + "\n" + QadMsg.translate("Environment variables", "Character type")
      VariableDescr = VariableDescr + ", " + QadMsg.translate("Environment variables", "global variable") + "."
      self.__VariableValuesDict[VariableName] = QadVariable(VariableName, default, \
                                                            QadVariableTypeEnum.STRING, \
                                                            None, None, \
                                                            VariableDescr, \
                                                            QadVariableLevelEnum.GLOBAL)

      # ​​SHOWTEXTWINDOW (bool): Show text window at startup. Global variable.
      VariableName = QadMsg.translate("Environment variables", "SHOWTEXTWINDOW") # x lupdate
      VariableDescr = QadMsg.translate("Environment variables", "Show the text window at startup.") # x lupdate
      VariableDescr = VariableDescr + "\n" + QadMsg.translate("Environment variables", "Boolean type")
      VariableDescr = VariableDescr + ", " + QadMsg.translate("Environment variables", "global variable") + "."
      self.__VariableValuesDict[VariableName] = QadVariable(VariableName, True, \
                                                            QadVariableTypeEnum.BOOL, \
                                                            None, None, \
                                                            VariableDescr, \
                                                            QadVariableLevelEnum.GLOBAL)

      # TOLERANCE2APPROXCURVE (float):
      # maximum tolerated error between a real curve and the one approximated by straight segments
      # (in the map-coordinate system). Project variable
      VariableName = QadMsg.translate("Environment variables", "TOLERANCE2APPROXCURVE") # x lupdate
      VariableDescr = QadMsg.translate("Environment variables", "Maximum error approximating a curve to segments.") # x lupdate
      VariableDescr = VariableDescr + "\n" + QadMsg.translate("Environment variables", "Real type")
      VariableDescr = VariableDescr + ", " + QadMsg.translate("Environment variables", "project variable") + "."
      self.__VariableValuesDict[VariableName] = QadVariable(VariableName, float(0.1), \
                                                            QadVariableTypeEnum.FLOAT, \
                                                            0.000001, None, \
                                                            VariableDescr, \
                                                            QadVariableLevelEnum.PROJECT)

      # TOLERANCE2COINCIDENT (float):
      # maximum tolerated error to establish whether two points are coincident
      # (in the map-coordinate system). Project variable
      VariableName = QadMsg.translate("Environment variables", "TOLERANCE2COINCIDENT") # x lupdate
      VariableDescr = QadMsg.translate("Environment variables", "Maximum error approximating two coincident points.") # x lupdate
      VariableDescr = VariableDescr + "\n" + QadMsg.translate("Environment variables", "Real type")
      VariableDescr = VariableDescr + ", " + QadMsg.translate("Environment variables", "project variable") + "."
      self.__VariableValuesDict[VariableName] = QadVariable(VariableName, float(0.001), \
                                                            QadVariableTypeEnum.FLOAT, \
                                                            0, 9999, \
                                                            VariableDescr, \
                                                            QadVariableLevelEnum.PROJECT)

      # TOOLTIPTRANSPARENCY (int): Sets the transparency of the dynamic input window. Global variable.
      VariableName = QadMsg.translate("Environment variables", "TOOLTIPTRANSPARENCY") # x lupdate
      VariableDescr = QadMsg.translate("Environment variables", "Sets the transparency for drafting tooltips." + \
                                       "\nThe valid range is 0 to 100. When a value of 0 is used, the drafting tooltip is opaque." + \
                                       "\nGreater values increase the transparency of the drafting tooltip.") # x lupdate
      VariableDescr = VariableDescr + "\n" + QadMsg.translate("Environment variables", "Integer type")
      VariableDescr = VariableDescr + ", " + QadMsg.translate("Environment variables", "global variable") + "."
      self.__VariableValuesDict[VariableName] = QadVariable(VariableName, int(0), \
                                                            QadVariableTypeEnum.INT, \
                                                            0, 100, \
                                                            VariableDescr, \
                                                            QadVariableLevelEnum.GLOBAL)

      # TOOLTIPSIZE (int):    . Global variable.
      VariableName = QadMsg.translate("Environment variables", "TOOLTIPSIZE") # x lupdate
      VariableDescr = QadMsg.translate("Environment variables", "Sets the display size for drafting tooltips, and dynamic input text." + \
                                       "\nValid range is -3 to 6. Greater values result in larger drafting tooltips, and larger automatic completion text at the Command prompt." + \
                                       "\nNegative values represent smaller sizes than the default.") # x lupdate
      VariableDescr = VariableDescr + "\n" + QadMsg.translate("Environment variables", "Integer type")
      VariableDescr = VariableDescr + ", " + QadMsg.translate("Environment variables", "global variable") + "."
      self.__VariableValuesDict[VariableName] = QadVariable(VariableName, int(0), \
                                                            QadVariableTypeEnum.INT, \
                                                            -3, 6, \
                                                            VariableDescr, \
                                                            QadVariableLevelEnum.GLOBAL)

      # WINDOWAREACOLOR (str): Sets the color (RGB) of the object selection area in window mode. Global variable.
      VariableName = QadMsg.translate("Environment variables", "WINDOWAREACOLOR") # x lupdate
      VariableDescr = QadMsg.translate("Environment variables", "Controls the color of the transparent selection area during window selection (RGB, #007EFF = blu)." + \
                                       "\nThe SELECTIONAREA system variable must be on.") # x lupdate
      VariableDescr = VariableDescr + "\n" + QadMsg.translate("Environment variables", "Character type")
      VariableDescr = VariableDescr + ", " + QadMsg.translate("Environment variables", "global variable") + "."
      self.__VariableValuesDict[VariableName] = QadVariable(VariableName, unicode("#007EFF"), \
                                                            QadVariableTypeEnum.COLOR, \
                                                            None, None, \
                                                            VariableDescr, \
                                                            QadVariableLevelEnum.GLOBAL) # blue


   def getVarNames(self):
      """Returns the list of variable names"""
      return list(self.__VariableValuesDict.keys())


   def set(self, VarName, varValue):
      """Change the value of a variable"""
      UpperVarName = VarName.upper()
      variable = self.getVariable(UpperVarName)

      if variable is None: # if there is no variable
         self.__VariableValuesDict[UpperVarName] = QadVariable(UpperVarName, varValue, \
                                                               QadVariableTypeEnum.UNKNOWN, \
                                                               None, None, \
                                                               "")
      else:
         if type(variable.value) != type(varValue):
            if not((type(variable.value) == unicode or type(variable.value) == str) and
                   (type(varValue) == unicode or type(varValue) == str)):
               return False
         if variable.typeValue == QadVariableTypeEnum.COLOR:
            if len(varValue) == 7: # e.g. "#FF0000"
               if varValue[0] != "#":
                  return False
            else:
               return False
         elif variable.typeValue == QadVariableTypeEnum.FLOAT or \
              variable.typeValue == QadVariableTypeEnum.INT:
            if variable.minNum is not None:
               if varValue < variable.minNum:
                  return False
            if variable.maxNum is not None:
               if varValue > variable.maxNum:
                  return False

         self.__VariableValuesDict[UpperVarName].value = varValue

      return True

   def get(self, VarName, defaultValue = None):
      """Returns the value of a variable"""
      variable = self.getVariable(VarName)
      if variable is None:
         result = defaultValue
      else:
         result = variable.value

      return result


   def getVariable(self, VarName):
      UpperVarName = VarName
      return self.__VariableValuesDict.get(UpperVarName.upper())


   def getDefaultQadIniFilePath(self):
      # gets the automatic path including the file name where to save the qad.ini file
      # if there is a loaded project the path is that of the project
      prjFileInfo = self.__getProjectFileInfo()
      path = "" if prjFileInfo is None else prjFileInfo.absolutePath()
      if len(path) == 0:
         # if there is no project loaded I use the qad installation path
         path = QDir.cleanPath(QgsApplication.qgisSettingsDirPath() + "python/plugins/qad")
         return path + "/" + "qad.ini"
      else:
         return path + "/" + prjFileInfo.baseName() + "_qad.ini"


   def getDefaultQadIniFilePath(self):
      # gets the path including the file name where to save the default qad.ini file
      # I use qad installation path
      path = QDir.cleanPath(QgsApplication.qgisSettingsDirPath() + "python/plugins/qad")
      return path + "/" + "qad.ini"


   def getProjectQadIniFilePath(self):
      # gets the path including the file name where to save the project's qad.ini file
      # if there is a loaded project the path is that of the project
      prjFileInfo = self.__getProjectFileInfo()
      path = "" if prjFileInfo is None else prjFileInfo.absolutePath()
      if len(path) == 0: # if there is no loaded project
         return ""
      else:
         return path + "/" + prjFileInfo.baseName() + "_qad.ini"

   def __getProjectFileInfo(self):
      projectFilePath = QgsProject.instance().absoluteFilePath()
      if len(projectFilePath) == 0:
         return None
      return QFileInfo(projectFilePath)


   def __saveVariables(self, Path, filterOnLevel = None):
      """Save the dictionary of variables to a file, possibly saving only those of the indicated level (global, project)"""
      dir = QFileInfo(Path).absoluteDir()
      if not dir.exists():
         os.makedirs(dir.absolutePath())

      file = open(Path, "w") # opens the file for writing
      for VarName in self.__VariableValuesDict.keys():
         variable = self.getVariable(VarName)
         # if there is a filter that is not satisfied then I skip the variable
         if (filterOnLevel is not None) and (variable is not None) and (filterOnLevel != variable.level):
            continue
         varValue = variable.value
         # I write the value + the type (e.g. var = 5 <type 'int'>)
         if type(varValue) == int:
            varValue = str(varValue) + " <type 'int'>"
         elif type(varValue) == long:
            varValue = str(varValue) + " <type 'long'>"
         elif type(varValue) == float:
            varValue = str(varValue) + " <type 'float'>"
         elif type(varValue) == bool:
            varValue = str(varValue) + " <type 'bool'>"
         else: # string
            varValue = str(varValue) + " <type 'string'>"

         Item = "%s = %s\n" % (VarName, varValue)
         file.write(Item)

      file.close()

   def save(self, Path=""):
      """Save the variable dictionary to file"""
      if Path != "": # If the path is indicated save all the variables in the file
         self.__saveVariables(Path)
         return

      # If the path is not indicated
      projectPath = self.getProjectQadIniFilePath()
      defaultPath = self.getDefaultQadIniFilePath()

      if len(projectPath) == 0: # if there is no current project
         self.__saveVariables(defaultPath) # save all variables in the "qad.ini" file of the qad installation
      else:
         # save all global variables in the "qad.ini" file of the qad installation
         self.__saveVariables(defaultPath, QadVariableLevelEnum.GLOBAL)
         # save all project variables in the "qad.ini" file of the current project
         self.__saveVariables(projectPath, QadVariableLevelEnum.PROJECT)


   def __loadVariables(self, Path, filterOnLevel = None):
      """Load the dictionary of variables from the file, possibly loading only those of the indicated level (global, project)
            Returns True on success, false on error
      """
      if not os.path.exists(Path):
         return False

      file = open(Path, "r") # opens the file for reading
      for line in file:
         # I read the value + the type (e.g. var = 5 <type 'int'>)
         sep = line.rfind(" = ")
         VarName = line[0:sep]
         VarName = VarName.strip(" ") # I remove the spaces before and after
         variable = self.getVariable(VarName)
         # if there is a filter that is not satisfied then I skip the variable
         if (filterOnLevel is not None) and (variable is not None) and (filterOnLevel != variable.level):
            continue

         varValue = line[sep+3:]
         sep = varValue.rfind(" <type '")
         sep2 = varValue.rfind("'>")
         VarType = varValue[sep+8:sep2]
         varValue = varValue[:sep]
         if VarType == "int":
            varValue = qad_utils.str2int(varValue)
            if varValue is None:
               self.set(VarName, int(0))
            else:
               self.set(VarName, varValue)
         elif VarType == "long":
            varValue = qad_utils.str2long(varValue)
            if varValue is None:
               self.set(VarName, long(0))
            else:
               self.set(VarName, varValue)
         elif VarType == "float":
            varValue = qad_utils.str2float(varValue)
            if varValue is None:
               self.set(VarName, float(0))
            else:
               self.set(VarName, varValue)
         elif VarType == "bool":
            varValue = qad_utils.str2bool(varValue)
            if varValue is None:
               self.set(VarName, False)
            else:
               self.set(VarName, varValue)
         else: # string
            self.set(VarName, str(varValue))

      file.close()

      return True


   def load(self, Path=""):
      """Load variable dictionary from file
            Returns True on success, false on error
      """
      # I empty the dictionary and reset it with the default values
      self.__VariableValuesDict.clear()
      self.__init__()


      if Path != "": # If the path is indicated, I load all the variables in the file
         self.__loadVariables(Path)
         return

      # If the path is not indicated
      projectPath = self.getProjectQadIniFilePath()
      defaultPath = self.getDefaultQadIniFilePath()

      if len(projectPath) == 0: # if there is no current project
         self.__loadVariables(defaultPath) # I load all variables into the "qad.ini" file of the qad installation
      else:
         # I load all global variables from the "qad.ini" file of the qad installation
         self.__loadVariables(defaultPath, QadVariableLevelEnum.GLOBAL)
         # I load all project variables into the "qad.ini" file of the current project
         self.__loadVariables(projectPath, QadVariableLevelEnum.PROJECT)

      return True


   # ============================================================================
   # copyTo
   # ============================================================================
   def copyTo(self, dest):
      """Copy the dictionary with the variables to dest"""
      for VarName in self.__VariableValuesDict.keys():
         dest.set(VarName, self.get(VarName))


# ===============================================================================
#  = global variable
# ===============================================================================


def POLARADDANG_to_list(PolarAddAngles, convertToRadians = False):
   strValueList = PolarAddAngles.split(";")
   floatValueList = []
   for strValue in strValueList:
      floatValue = qad_utils.str2float(strValue)
      if floatValue is not None:
         if convertToRadians == True:
            floatValue =  math.radians(floatValue)
         floatValueList.append(floatValue)

   floatValueList.sort()

   return floatValueList

QadVariables = QadVariablesClass()
