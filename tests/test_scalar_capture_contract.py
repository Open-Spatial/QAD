from __future__ import annotations

import sys
from types import SimpleNamespace
from pathlib import Path

QAD_PARENT = Path(__file__).resolve().parents[2]
if str(QAD_PARENT) not in sys.path:
    sys.path.insert(0, str(QAD_PARENT))

from QAD import qad_commands
from QAD.qad_scalar_capture import QadScalarCaptureCommand
from QAD.qad_textwindow import QadInputModeEnum, QadInputTypeEnum


def test_point_or_angle_capture_without_keywords_omits_keyword_input() -> None:
    command = QadScalarCaptureCommand(
        None,
        prompt="Specify text angle: ",
        input_type="point_or_angle_or_keyword",
        default=None,
        keywords="",
        input_mode=QadInputModeEnum.NONE,
        allow_null=False,
    )
    prompts = []
    command.waitFor = lambda *args: prompts.append(args)

    assert command.run() is False

    assert prompts[0][1] == QadInputTypeEnum.POINT2D | QadInputTypeEnum.ANGLE
    assert prompts[0][3] == ""


def test_run_scalar_capture_accepts_point_or_angle_without_keywords(monkeypatch) -> None:
    captured = {}

    class _CaptureCommand:
        def __init__(self, plugin, **kwargs) -> None:
            captured.update(plugin=plugin, **kwargs)

        def run(self) -> bool:
            return False

    monkeypatch.setattr(qad_commands, "QadScalarCaptureCommand", _CaptureCommand)
    plugin = SimpleNamespace(clearEntityGripPoints=lambda: None)
    commands = object.__new__(qad_commands.QadCommandsClass)
    commands.plugIn = plugin
    commands.actualCommand = None
    commands.usedCmdNames = SimpleNamespace(setUsed=lambda _name: None)

    assert commands.runScalarCapture(
        lambda _result: None,
        prompt="Specify text angle: ",
        input_type="point_or_angle_or_keyword",
    )

    assert captured["input_type"] == "point_or_angle_or_keyword"
    assert captured["keywords"] == ""


def test_keyword_capture_still_requires_keywords() -> None:
    commands = object.__new__(qad_commands.QadCommandsClass)
    commands.actualCommand = None
    results = []

    started = commands.runScalarCapture(
        results.append,
        prompt="Specify option: ",
        input_type="keyword",
    )

    assert started is False
    assert results[0].status == "failed"
    assert results[0].message == "Keyword input requires keywords."
