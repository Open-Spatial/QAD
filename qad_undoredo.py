# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 functions for undo and redo

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
# QadUndoRecordTypeEnum class.
# ===============================================================================
class QadUndoRecordTypeEnum():
   NONE     = 0     # none
   COMMAND  = 1     # single command
   BEGIN    = 2     # start of a group of commands
   END      = 3     # end of a group of commands
   BOOKMARK = 4     # bookmark flag, it means that it is a sign to which
                     # you can return


# ===============================================================================
# QadUndoRecord class to manage an UNDO recording
# ===============================================================================
class QadUndoRecord():


   def __init__(self):
      self.text = "" # descrizione operazione
      self.undoType = QadUndoRecordTypeEnum.NONE # undo type (see QadUndoRecordTypeEnum)
      self.layerList = None # list of layers involved in the editing command


   def setUndoType(self, text = "", undoType = QadUndoRecordTypeEnum.NONE):
      # a typology of undo marker is being set up
      self.text = text
      self.layerList = None # list of layers involved in the editing command
      self.undoType = undoType


   def layerAt(self, layerId):
      # returns the position in the list 0-based), -1 if not found
      if self.layerList is not None and self.undoType == QadUndoRecordTypeEnum.COMMAND:
         for j in range(0, len(self.layerList), 1):
            if self.layerList[j].id() == layerId:
               return j
      return -1


   def clearByLayer(self, layerId):
      # delete the layer <layerId> from the list
      pos = self.layerAt(layerId)
      if pos >= 0:
         del self.layerList[pos]


   def beginEditCommand(self, text, layerList):
      # you are starting a command involving a list of layers
      self.text = text # descrizione operazione
      self.undoType = QadUndoRecordTypeEnum.COMMAND
      # <parameter> contains the list of layers involved in the editing command
      self.layerList = []
      for layer in layerList: # I copy the list
         if self.layerAt(layer.id()) == -1: # I do not allow layer duplications
            layer.beginEditCommand(text)
            self.layerList.append(layer)


   def destroyEditCommand(self):
      # a command involving a list of layers is being destroyed
      if self.layerList is not None and self.undoType == QadUndoRecordTypeEnum.COMMAND:
         for layer in self.layerList:
            layer.destroyEditCommand() # Destroy active command and reverts all changes in it
         return True
      else:
         return False


   def endEditCommand(self, canvas):
      # a command involving a list of layers is being concluded
      if self.layerList is not None and self.undoType == QadUndoRecordTypeEnum.COMMAND:
         for layer in self.layerList:
            layer.endEditCommand()
            layer.triggerRepaint()
         canvas.refresh()


   def undoEditCommand(self, canvas = None):
      # you are doing an UNDO of a command involving a list of layers
      if self.layerList is not None and self.undoType == QadUndoRecordTypeEnum.COMMAND:
         for layer in self.layerList:
            layer.undoStack().undo()
         if canvas is not None:
            canvas.refresh()


   def redoEditCommand(self, canvas = None):
      # you are doing a REDO of a command involving a list of layers
      if self.layerList is not None and self.undoType == QadUndoRecordTypeEnum.COMMAND:
         for layer in self.layerList:
            layer.undoStack().redo()
         if canvas is not None:
            canvas.refresh()


   def addLayer(self, layer):
      # you are adding a layer to the current command
      if self.undoType != QadUndoRecordTypeEnum.COMMAND: # it must be a command
         return False
      if self.layerAt(layer.id()) == -1: # I do not allow layer duplications
         layer.beginEditCommand(self.text)
         self.layerList.append(layer)


# ===============================================================================
# QadUndoStack class to manage the operations stack
# ===============================================================================
class QadUndoStack():


   def __init__(self):
      self.UndoRecordList = [] # list of undo records
      self.index = -1


   def clear(self):
      del self.UndoRecordList[:] # I empty the list
      self.index = -1


   def clearByLayer(self, layerId):
      # delete the layer <layerId> from the undo record list
      for i in range(len(self.UndoRecordList) - 1, -1, -1):
         UndoRecord = self.UndoRecordList[i]
         if UndoRecord.undoType == QadUndoRecordTypeEnum.COMMAND:
            UndoRecord.clearByLayer(layerId)
            if len(UndoRecord.layerList) == 0:
               # delete the (empty) layer list involved in the editing command
               del self.UndoRecordList[i]
               if self.index >= i: # update the pointer
                  self.index = self.index - 1


   def insertBeginGroup(self, text):
      UndoRecord = QadUndoRecord()
      UndoRecord.setUndoType(text, QadUndoRecordTypeEnum.BEGIN)
      self.UndoRecordList.append(UndoRecord)
      self.index = len(self.UndoRecordList) - 1
      return True


   def getOpenGroupPos(self, endGroupPos):
      # from the end group position <endgroupPos> searces for the group start position
      # -1 if not found
      openFlag = 0
      for i in range(endGroupPos, -1, -1):
         UndoRecord = self.UndoRecordList[i]
         if UndoRecord.undoType == QadUndoRecordTypeEnum.BEGIN:
            openFlag = openFlag + 1
            if openFlag >= 0:
               return i
         elif UndoRecord.undoType == QadUndoRecordTypeEnum.END:
            openFlag = openFlag - 1
      return -1


   def getEndGroupPos(self, beginGroupPos):
      # from the group start position <endgroupPos> searces for the group start position
      # -1 if not found
      closeFlag = 0
      for i in range(beginGroupPos, len(self.UndoRecordList), 1):
         UndoRecord = self.UndoRecordList[i]
         if UndoRecord.undoType == QadUndoRecordTypeEnum.BEGIN:
            closeFlag = closeFlag - 1
         elif UndoRecord.undoType == QadUndoRecordTypeEnum.END:
            closeFlag = closeFlag + 1
            if closeFlag >= 0:
               return i
      return -1


   def insertEndGroup(self):
      # you cannot insert an end group if you have not left a group open
      openGroupPos = self.getOpenGroupPos(len(self.UndoRecordList) - 1)
      if openGroupPos == -1:
         return False

      UndoRecord = QadUndoRecord()
      UndoRecord.setUndoType(self.UndoRecordList[openGroupPos].text, QadUndoRecordTypeEnum.END)
      self.UndoRecordList.append(UndoRecord)
      self.index = len(self.UndoRecordList) - 1
      return True


   def beginEditCommand(self, text, layerList):
      tot = len(self.UndoRecordList)
      if tot > 0 and self.index < tot - 1:
         del self.UndoRecordList[self.index + 1 :] # gate to the end

      UndoRecord = QadUndoRecord()
      UndoRecord.beginEditCommand(text, layerList)
      self.UndoRecordList.append(UndoRecord)
      self.index = len(self.UndoRecordList) - 1


   def destroyEditCommand(self):
      if len(self.UndoRecordList) > 0:
         UndoRecord = self.UndoRecordList[-1]
         if UndoRecord.destroyEditCommand():
            del self.UndoRecordList[-1]
            self.index = self.index - 1


   def endEditCommand(self, canvas):
      if len(self.UndoRecordList) > 0:
         UndoRecord = self.UndoRecordList[-1]
         UndoRecord.endEditCommand(canvas)


   def moveOnFirstUndoRecord(self):
      # moves the cursor from the current position to the beginning
      # and stops when it finds a record of type END or COMMAND
      while self.index >= 0:
         UndoRecord = self.UndoRecordList[self.index]
         if UndoRecord.undoType == QadUndoRecordTypeEnum.END or \
            UndoRecord.undoType == QadUndoRecordTypeEnum.COMMAND:
            return True
         self.index = self.index - 1
      return False

   def undoEditCommand(self, canvas = None, nTimes = 1):
      for i in range(0, nTimes, 1):
         # I'm looking for the first record where it makes sense to do UNDO
         if self.moveOnFirstUndoRecord() == False:
            break
         UndoRecord = self.UndoRecordList[self.index]
         # if I encounter an end-group I have to go to the begin-group
         if UndoRecord.undoType == QadUndoRecordTypeEnum.END:
            openGroupPos = self.getOpenGroupPos(self.index)
            while self.index >= openGroupPos:
               UndoRecord.undoEditCommand(None) # without refreshing
               self.index = self.index - 1
               if self.moveOnFirstUndoRecord() == False:
                  break
               UndoRecord = self.UndoRecordList[self.index]
         else:
            UndoRecord.undoEditCommand(None)
            self.index = self.index - 1

      if canvas is not None:
         canvas.refresh()


   def moveOnFirstRedoRecord(self):
      # moves the cursor from the current position to the end
      # and stops when it finds a record of type BEGIN or COMMAND
      tot = len(self.UndoRecordList) - 1
      while self.index < tot:
         self.index = self.index + 1
         UndoRecord = self.UndoRecordList[self.index]
         if UndoRecord.undoType == QadUndoRecordTypeEnum.BEGIN or \
            UndoRecord.undoType == QadUndoRecordTypeEnum.COMMAND:
            return True
      return False

   def redoEditCommand(self, canvas = None, nTimes = 1):
      for i in range(0, nTimes, 1):
         # I'm looking for the first record where it makes sense to do REDO
         if self.moveOnFirstRedoRecord() == False:
            break
         UndoRecord = self.UndoRecordList[self.index]
         # if I encounter a begin-group I have to go to the end-group
         if UndoRecord.undoType == QadUndoRecordTypeEnum.BEGIN:
            endGroupPos = self.getEndGroupPos(self.index)
            while self.index <= endGroupPos:
               UndoRecord.redoEditCommand(None) # without refresh
               if self.moveOnFirstRedoRecord() == False:
                  break
               UndoRecord = self.UndoRecordList[self.index]
         else:
            UndoRecord.redoEditCommand(None)

      if canvas is not None:
         canvas.refresh()


   def addLayerToLastEditCommand(self, text, layer):
      if len(self.UndoRecordList) > 0:
         self.UndoRecordList[-1].addLayer(layer)


   def isUndoAble(self):
      # searces for a COMMAND record from the current position to the beginning
      i = self.index
      while i >= 0:
         UndoRecord = self.UndoRecordList[i]
         if UndoRecord.undoType == QadUndoRecordTypeEnum.COMMAND:
            return True
         i = i - 1
      return False


   def isRedoAble(self):
      # searces for a record of type COMMAND from the current position to the end
      i = self.index + 1
      tot = len(self.UndoRecordList)
      while i < tot:
         UndoRecord = self.UndoRecordList[i]
         if UndoRecord.undoType == QadUndoRecordTypeEnum.COMMAND:
            return True
         i = i + 1
      return False

   # ===============================================================================
   # BOOKMARK - BEGINNING
   # ===============================================================================

   def undoUntilBookmark(self, canvas):
      if self.index == -1:
         return
      for i in range(self.index, -1, -1):
         UndoRecord = self.UndoRecordList[i]
         if UndoRecord.undoType == QadUndoRecordTypeEnum.BOOKMARK:
            break

         UndoRecord.undoEditCommand(None) # without refresh
      self.index = i - 1

      canvas.refresh()


   def redoUntilBookmark(self, canvas):
      for i in range(self.index + 1, len(self.UndoRecordList), 1):
         UndoRecord = self.UndoRecordList[i]
         if UndoRecord.undoType == QadUndoRecordTypeEnum.BOOKMARK:
            break
         UndoRecord.redoEditCommand(None) # without refresh
      self.index = i

      canvas.refresh()


   def getPrevBookmarkPos(self, pos):
      # from position <pos> searces for the previous bookmark position
      # -1 if not found
      for i in range(pos - 1, -1, -1):
         UndoRecord = self.UndoRecordList[i]
         if UndoRecord.undoType == QadUndoRecordTypeEnum.BOOKMARK:
            return i
      return -1


   def insertBookmark(self, text):
      # you cannot insert a bookmark inside a begin-end group
      if self.getOpenGroupPos(self.index) >= 0:
         return False

      tot = len(self.UndoRecordList)
      if tot > 0 and self.index < tot - 1:
         del self.UndoRecordList[self.index + 1 :] # gate to the end

      UndoRecord = QadUndoRecord()
      UndoRecord.setUndoType(text, QadUndoRecordTypeEnum.BOOKMARK)
      self.UndoRecordList.append(UndoRecord)
      self.index = len(self.UndoRecordList) - 1
      return True

   # ===============================================================================
   # BOOKMARK - END
   # ===============================================================================