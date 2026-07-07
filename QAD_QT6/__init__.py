"""
/***************************************************************************
 QAD
                                 A QGIS plugin
 Layer selection through graphical objects
                             -------------------
        begin                : 2019-09-16
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
 This script initializes the plugin, making it known to QGIS.
"""

import builtins
from qgis.PyQt.QtCore import Qt, QItemSelectionModel, QMetaType
from qgis.PyQt.QtGui import QColor, QFont, QPainter, QPalette, QTextCursor
from qgis.PyQt.QtWidgets import QAbstractItemView, QDialog, QDialogButtonBox, QFrame, QHeaderView, QLayout, QListView, QMessageBox, QSizePolicy, QToolButton


if not hasattr(builtins, "unicode"):
    builtins.unicode = str


def _set_qt_compat_alias(name, value):
    if hasattr(Qt, name):
        return
    try:
        setattr(Qt, name, value)
    except Exception:
        pass


def _set_class_compat_alias(target, name, value):
    if hasattr(target, name):
        return
    try:
        setattr(target, name, value)
    except Exception:
        pass


def _install_qt_compat_aliases():
    color_aliases = {
        "black": QColor(Qt.GlobalColor.black),
        "white": QColor(Qt.GlobalColor.white),
        "lightGray": QColor(Qt.GlobalColor.lightGray),
        "gray": QColor(Qt.GlobalColor.gray),
        "blue": QColor(Qt.GlobalColor.blue),
        "red": QColor(Qt.GlobalColor.red),
    }
    for name, value in color_aliases.items():
        _set_qt_compat_alias(name, value)

    enum_aliases = {
        "Widget": Qt.WindowType.Widget,
        "ToolTip": Qt.WindowType.ToolTip,
        "WindowStaysOnTopHint": Qt.WindowType.WindowStaysOnTopHint,
        "WindowModal": Qt.WindowModality.WindowModal,
        "ApplicationModal": Qt.WindowModality.ApplicationModal,
        "NonModal": Qt.WindowModality.NonModal,
        "TopDockWidgetArea": Qt.DockWidgetArea.TopDockWidgetArea,
        "BottomDockWidgetArea": Qt.DockWidgetArea.BottomDockWidgetArea,
        "ScrollBarAlwaysOff": Qt.ScrollBarPolicy.ScrollBarAlwaysOff,
        "TextEditorInteraction": Qt.TextInteractionFlag.TextEditorInteraction,
        "MatchStartsWith": Qt.MatchFlag.MatchStartsWith,
        "AlignCenter": Qt.AlignmentFlag.AlignCenter,
        "AlignLeading": Qt.AlignmentFlag.AlignLeading,
        "AlignLeft": Qt.AlignmentFlag.AlignLeft,
        "AlignTop": Qt.AlignmentFlag.AlignTop,
        "SolidLine": Qt.PenStyle.SolidLine,
        "DashLine": Qt.PenStyle.DashLine,
        "DashDotLine": Qt.PenStyle.DashDotLine,
        "DotLine": Qt.PenStyle.DotLine,
        "RoundCap": Qt.PenCapStyle.RoundCap,
        "Checked": Qt.CheckState.Checked,
        "Unchecked": Qt.CheckState.Unchecked,
        "LeftButton": Qt.MouseButton.LeftButton,
        "RightButton": Qt.MouseButton.RightButton,
        "ShiftModifier": Qt.KeyboardModifier.ShiftModifier,
        "ControlModifier": Qt.KeyboardModifier.ControlModifier,
        "MetaModifier": Qt.KeyboardModifier.MetaModifier,
        "NoModifier": Qt.KeyboardModifier.NoModifier,
        "ArrowCursor": Qt.CursorShape.ArrowCursor,
        "BlankCursor": Qt.CursorShape.BlankCursor,
        "WaitCursor": Qt.CursorShape.WaitCursor,
        "Horizontal": Qt.Orientation.Horizontal,
        "WA_DeleteOnClose": Qt.WidgetAttribute.WA_DeleteOnClose,
        "CustomContextMenu": Qt.ContextMenuPolicy.CustomContextMenu,
        "DefaultContextMenu": Qt.ContextMenuPolicy.DefaultContextMenu,
        "AutoText": Qt.TextFormat.AutoText,
        "TextSingleLine": Qt.TextFlag.TextSingleLine,
        "ItemIsEnabled": Qt.ItemFlag.ItemIsEnabled,
        "ItemIsSelectable": Qt.ItemFlag.ItemIsSelectable,
    }
    for name, value in enum_aliases.items():
        _set_qt_compat_alias(name, value)

    for key_name in (
        "Key_9", "Key_A", "Key_AltGr", "Key_Backspace", "Key_Backtab",
        "Key_C", "Key_Comma", "Key_D", "Key_Delete", "Key_Down",
        "Key_End", "Key_Enter", "Key_Escape", "Key_F10", "Key_F11",
        "Key_F12", "Key_F2", "Key_F3", "Key_F8", "Key_Home", "Key_Left",
        "Key_P", "Key_PageDown", "Key_PageUp", "Key_Return", "Key_Right",
        "Key_Space", "Key_Tab", "Key_Up", "Key_X", "Key_Y",
    ):
        if hasattr(Qt.Key, key_name):
            _set_qt_compat_alias(key_name, getattr(Qt.Key, key_name))

    class_aliases = (
        (QSizePolicy, {
            "Fixed": QSizePolicy.Policy.Fixed,
            "Minimum": QSizePolicy.Policy.Minimum,
            "Maximum": QSizePolicy.Policy.Maximum,
            "Preferred": QSizePolicy.Policy.Preferred,
            "Expanding": QSizePolicy.Policy.Expanding,
            "MinimumExpanding": QSizePolicy.Policy.MinimumExpanding,
            "Ignored": QSizePolicy.Policy.Ignored,
        }),
        (QFont, {
            "Normal": QFont.Weight.Normal,
            "Bold": QFont.Weight.Bold,
        }),
        (QPainter, {
            "Antialiasing": QPainter.RenderHint.Antialiasing,
            "TextAntialiasing": QPainter.RenderHint.TextAntialiasing,
            "SmoothPixmapTransform": QPainter.RenderHint.SmoothPixmapTransform,
            "LosslessImageRendering": QPainter.RenderHint.LosslessImageRendering,
        }),
        (QTextCursor, {
            "MoveAnchor": QTextCursor.MoveMode.MoveAnchor,
            "KeepAnchor": QTextCursor.MoveMode.KeepAnchor,
            "Start": QTextCursor.MoveOperation.Start,
            "End": QTextCursor.MoveOperation.End,
            "Left": QTextCursor.MoveOperation.Left,
            "Right": QTextCursor.MoveOperation.Right,
            "WordLeft": QTextCursor.MoveOperation.WordLeft,
            "WordRight": QTextCursor.MoveOperation.WordRight,
            "StartOfBlock": QTextCursor.MoveOperation.StartOfBlock,
            "EndOfBlock": QTextCursor.MoveOperation.EndOfBlock,
        }),
        (QAbstractItemView, {
            "NoEditTriggers": QAbstractItemView.EditTrigger.NoEditTriggers,
            "SelectRows": QAbstractItemView.SelectionBehavior.SelectRows,
            "SelectItems": QAbstractItemView.SelectionBehavior.SelectItems,
            "SingleSelection": QAbstractItemView.SelectionMode.SingleSelection,
            "MultiSelection": QAbstractItemView.SelectionMode.MultiSelection,
        }),
        (QItemSelectionModel, {
            "NoUpdate": QItemSelectionModel.SelectionFlag.NoUpdate,
            "Clear": QItemSelectionModel.SelectionFlag.Clear,
            "Select": QItemSelectionModel.SelectionFlag.Select,
            "Deselect": QItemSelectionModel.SelectionFlag.Deselect,
            "Toggle": QItemSelectionModel.SelectionFlag.Toggle,
            "Current": QItemSelectionModel.SelectionFlag.Current,
            "Rows": QItemSelectionModel.SelectionFlag.Rows,
            "Columns": QItemSelectionModel.SelectionFlag.Columns,
            "SelectCurrent": QItemSelectionModel.SelectionFlag.SelectCurrent,
            "ToggleCurrent": QItemSelectionModel.SelectionFlag.ToggleCurrent,
            "ClearAndSelect": QItemSelectionModel.SelectionFlag.ClearAndSelect,
        }),
        (QDialog, {
            "Accepted": QDialog.DialogCode.Accepted,
            "Rejected": QDialog.DialogCode.Rejected,
        }),
        (QHeaderView, {
            "ResizeToContents": QHeaderView.ResizeMode.ResizeToContents,
            "Interactive": QHeaderView.ResizeMode.Interactive,
        }),
        (QDialogButtonBox, {
            "Ok": QDialogButtonBox.StandardButton.Ok,
            "Cancel": QDialogButtonBox.StandardButton.Cancel,
            "Apply": QDialogButtonBox.StandardButton.Apply,
            "Help": QDialogButtonBox.StandardButton.Help,
        }),
        (QMessageBox, {
            "Ok": QMessageBox.StandardButton.Ok,
            "Cancel": QMessageBox.StandardButton.Cancel,
            "Yes": QMessageBox.StandardButton.Yes,
            "No": QMessageBox.StandardButton.No,
            "Save": QMessageBox.StandardButton.Save,
            "Close": QMessageBox.StandardButton.Close,
            "Abort": QMessageBox.StandardButton.Abort,
            "Retry": QMessageBox.StandardButton.Retry,
            "Ignore": QMessageBox.StandardButton.Ignore,
        }),
        (QToolButton, {
            "DelayedPopup": QToolButton.ToolButtonPopupMode.DelayedPopup,
            "MenuButtonPopup": QToolButton.ToolButtonPopupMode.MenuButtonPopup,
            "InstantPopup": QToolButton.ToolButtonPopupMode.InstantPopup,
        }),
        (QListView, {
            "ListMode": QListView.ViewMode.ListMode,
            "IconMode": QListView.ViewMode.IconMode,
        }),
        (QFrame, {
            "Box": QFrame.Shape.Box,
            "HLine": QFrame.Shape.HLine,
            "Sunken": QFrame.Shadow.Sunken,
        }),
        (QLayout, {
            "SetMinimumSize": QLayout.SizeConstraint.SetMinimumSize,
        }),
        (QMetaType, {
            "Bool": QMetaType.Type.Bool,
            "Int": QMetaType.Type.Int,
            "UInt": QMetaType.Type.UInt,
            "LongLong": QMetaType.Type.LongLong,
            "ULongLong": QMetaType.Type.ULongLong,
            "Double": QMetaType.Type.Double,
            "QString": QMetaType.Type.QString,
        }),
        (QPalette, {
            "Active": QPalette.ColorGroup.Active,
            "Inactive": QPalette.ColorGroup.Inactive,
            "Disabled": QPalette.ColorGroup.Disabled,
            "ToolTipText": QPalette.ColorRole.ToolTipText,
            "ToolTipBase": QPalette.ColorRole.ToolTipBase,
            "WindowText": QPalette.ColorRole.WindowText,
            "Window": QPalette.ColorRole.Window,
            "Base": QPalette.ColorRole.Base,
            "Text": QPalette.ColorRole.Text,
            "Button": QPalette.ColorRole.Button,
            "ButtonText": QPalette.ColorRole.ButtonText,
            "Highlight": QPalette.ColorRole.Highlight,
            "HighlightedText": QPalette.ColorRole.HighlightedText,
        }),
    )
    for target, aliases in class_aliases:
        for name, value in aliases.items():
            _set_class_compat_alias(target, name, value)


_install_qt_compat_aliases()


def classFactory(iface):

    # load Qad class from file qad
    from .qad import Qad
    return Qad(iface)
