# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 QAD grip color management

                              -------------------
        begin                : 2016-17-02
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
from qgis.PyQt.QtWidgets import QDialog
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui  import *
from qgis.core import *
from qgis.utils import *
from qgis.gui import *


from .qad_gripcolor_ui import Ui_GripColor_Dialog

from .qad_msg import QadMsg, qadShowPluginPDFHelp
from . import qad_utils


#######################################################################################
# Class that manages the graphical interface for grip colors
class QadGripColorDialog(QDialog, QObject, Ui_GripColor_Dialog):
   def __init__(self, plugIn, parent, gripColor, gripHot, gripHover, gripContour):
      self.plugIn = plugIn
      self.iface = self.plugIn.iface.mainWindow()

      QDialog.__init__(self, parent)

      self.gripColor   = gripColor
      self.gripHot     = gripHot
      self.gripHover   = gripHover
      self.gripContour = gripContour

      self.setupUi(self)
      self.setWindowTitle(QadMsg.getQADTitle() + " - " + self.windowTitle())

      # Inizializzazione dei colori
      self.init_colors()


   def setupUi(self, Dialog):
      Ui_GripColor_Dialog.setupUi(self, self)
      # add the qgis button QgsColorButton called unselectedGripColor
      # which inherits the position of unselectedGripColorDummy (which is hidden)
      self.unselectedGripColorDummy.setHidden(True)
      self.unselectedGripColor = QgsColorButton(self.unselectedGripColorDummy.parent())
      self.unselectedGripColor.setGeometry(self.unselectedGripColorDummy.geometry())
      self.unselectedGripColor.setObjectName("unselectedGripColor")
      # add the qgis QgsColorButton button called selectedGripColor
      # which inherits the position of selectedGripColorDummy (which is hidden)
      self.selectedGripColorDummy.setHidden(True)
      self.selectedGripColor = QgsColorButton(self.selectedGripColorDummy.parent())
      self.selectedGripColor.setGeometry(self.selectedGripColorDummy.geometry())
      self.selectedGripColor.setObjectName("selectedGripColor")
      # add the qgis QgsColorButton button called hoverGripColor
      # which inherits the position of hoverGripColorDummy (which is hidden)
      self.hoverGripColorDummy.setHidden(True)
      self.hoverGripColor = QgsColorButton(self.hoverGripColorDummy.parent())
      self.hoverGripColor.setGeometry(self.hoverGripColorDummy.geometry())
      self.hoverGripColor.setObjectName("hoverGripColor")
      # add the qgis QgsColorButton button called contourGripColor
      # which inherits the position of contourGripColorDummy (which is hidden)
      self.contourGripColorDummy.setHidden(True)
      self.contourGripColor = QgsColorButton(self.contourGripColorDummy.parent())
      self.contourGripColor.setGeometry(self.contourGripColorDummy.geometry())
      self.contourGripColor.setObjectName("contourGripColor")


   # ============================================================================
   # init_colors
   # ============================================================================
   def init_colors(self):
      # Inizializzazione dei colori
      self.unselectedGripColor.setColor(QColor(self.gripColor))
      self.selectedGripColor.setColor(QColor(self.gripHot))
      self.hoverGripColor.setColor(QColor(self.gripHover))
      self.contourGripColor.setColor(QColor(self.gripContour))


   def ButtonBOX_Accepted(self):
      self.gripColor = self.unselectedGripColor.color().name()
      self.gripHot = self.selectedGripColor.color().name()
      self.gripHover = self.hoverGripColor.color().name()
      self.gripContour = self.contourGripColor.color().name()

      QDialog.accept(self)


   def ButtonHELP_Pressed(self):
      qadShowPluginPDFHelp(QadMsg.translate("Help", ""))
