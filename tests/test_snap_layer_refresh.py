from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

QAD_PARENT = Path(__file__).resolve().parents[2]
if str(QAD_PARENT) not in sys.path:
    sys.path.insert(0, str(QAD_PARENT))

from QAD import qad_getpoint
from QAD import qad_utils
from QAD.qad_getpoint import QadGetPoint


class _Signal:
    def __init__(self) -> None:
        self._slots = []

    def connect(self, slot) -> None:
        self._slots.append(slot)

    def disconnect(self, slot) -> None:
        self._slots = [candidate for candidate in self._slots if candidate != slot]

    def emit(self) -> None:
        for slot in tuple(self._slots):
            slot()


class _SnappingUtils:
    def __init__(self) -> None:
        self.configChanged = _Signal()


class _Canvas:
    def __init__(self) -> None:
        self.layersChanged = _Signal()
        self._snapping_utils = _SnappingUtils()
        self.layers = []

    def snappingUtils(self) -> _SnappingUtils:
        return self._snapping_utils


class _Snapper:
    def __init__(self) -> None:
        self.layers = []

    def setSnapLayers(self, layers) -> None:
        self.layers = list(layers)


class _PointTool:
    def __init__(self) -> None:
        self.canvas = _Canvas()
        self._QadGetPoint__QadSnapper = _Snapper()

    def setSnapLayersFromQgis(self) -> None:
        QadGetPoint.setSnapLayersFromQgis(self)


def test_qad_point_tool_refreshes_snap_layers_after_canvas_layer_changes(monkeypatch) -> None:
    point_tool = _PointTool()
    node_layer = object()
    other_layer = object()
    monkeypatch.setattr(
        qad_getpoint.qad_utils,
        "getSnappableVectorLayers",
        lambda canvas: canvas.layers,
    )

    QadGetPoint.connectSnapLayerRefresh(point_tool)
    point_tool.canvas.layers = [node_layer]
    point_tool.canvas.layersChanged.emit()
    assert point_tool._QadGetPoint__QadSnapper.layers == [node_layer]

    point_tool.canvas.layers = [other_layer]
    point_tool.canvas.snappingUtils().configChanged.emit()
    assert point_tool._QadGetPoint__QadSnapper.layers == [other_layer]

    QadGetPoint.disconnectSnapLayerRefresh(point_tool)
    point_tool.canvas.layers = [node_layer]
    point_tool.canvas.layersChanged.emit()
    point_tool.canvas.snappingUtils().configChanged.emit()
    assert point_tool._QadGetPoint__QadSnapper.layers == [other_layer]


class _Layer:
    def __init__(self, properties=None) -> None:
        self._properties = properties or {}

    def customProperty(self, key, default=None):
        return self._properties.get(key, default)

    def type(self):
        return 1

    def hasScaleBasedVisibility(self):
        return False


class _CanvasConfig:
    def enabled(self):
        return False

    def mode(self):
        return 0


class _CanvasSnappingUtils:
    def config(self):
        return _CanvasConfig()


class _LayerCanvas:
    def __init__(self, layers) -> None:
        self._layers = layers

    def snappingUtils(self):
        return _CanvasSnappingUtils()

    def layers(self):
        return list(self._layers)


def test_display_only_layers_are_removed_from_qad_snap_targets(monkeypatch) -> None:
    source_layer = _Layer()
    highlight_layer = _Layer({"qad_disable_snapping": True})
    monkeypatch.setattr(qad_utils, "QgsMapLayer", SimpleNamespace(VectorLayer=1))

    layers = qad_utils.getSnappableVectorLayers(
        _LayerCanvas([source_layer, highlight_layer])
    )

    assert layers == [source_layer]
