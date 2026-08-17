import pytest

from orchestrator.orchestrator import Orchestrator
from camera_adapter.camera_adapter import CameraAdapter
from camera_controller.camera_controller import CameraController


# tests/test_integration.py
def test_workspace_import():
    # sys.path に直書きせず、uv のパッケージ解決だけで通るか検証
    # インスタンス化のみで実機はopenしないため、hardwareマーカー不要
    orchestrator = Orchestrator()
    adapter = CameraAdapter()
    controller = CameraController()
    assert orchestrator is not None
    assert adapter is not None
    assert controller is not None

@pytest.mark.hardware
def test_orchestrator_adapter_controller():
    orchestrator = Orchestrator()
    adapter = CameraAdapter()
    controller = CameraController()

    result = orchestrator.execute()
    assert result is True
