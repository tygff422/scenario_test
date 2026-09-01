import asyncio

import pytest

from orchestrator.orchestrator import GenericOrchestrator
from camera_adapter.camera_adapter import CameraAdapter
from camera_controller.camera_controller import CameraController


# tests/test_integration.py
def test_workspace_import():
    # sys.path に直書きせず、uv のパッケージ解決だけで通るか検証
    # インスタンス化のみで実機はopenしないため、hardwareマーカー不要
    orchestrator = GenericOrchestrator()
    adapter = CameraAdapter()
    controller = CameraController()
    assert orchestrator is not None
    assert adapter is not None
    assert controller is not None


@pytest.mark.hardware
def test_generic_orchestrator_with_real_camera_adapter():
    # GenericOrchestrator（YAML/PlantUML駆動の本線）を実機カメラで検証する。
    # 01_docs/decisions/12_essential_gaps_found.md 課題2の対応
    # （これまでGenericOrchestratorはFake経由でしか検証されていなかった）。
    pipeline = [
        {
            "name": "カメラ画像撮影",
            "adapter": "camera_adapter.camera_adapter.CameraAdapter",
            "action": "capture",
            "params": {"resolution": [640, 480]},
        }
    ]

    orchestrator = GenericOrchestrator()
    result = asyncio.run(orchestrator.execute(pipeline))

    assert result is True
    assert orchestrator.context.history[0].result["status"] == "SUCCESS"


@pytest.mark.hardware
def test_generic_orchestrator_check_status_with_real_camera_adapter():
    # 以前はデモ用Orchestrator経由でしか実機検証できなかったLED確認（check_device_status）を、
    # GenericOrchestratorのaction経由で実機検証する（01_docs/decisions/19参照）。
    pipeline = [
        {
            "name": "カメラLED確認",
            "adapter": "camera_adapter.camera_adapter.CameraAdapter",
            "action": "check_status",
            "params": {},
        }
    ]

    orchestrator = GenericOrchestrator()
    result = asyncio.run(orchestrator.execute(pipeline))

    assert result is True
    # READY/NOT_READYどちらでも「ステップ自体は成功した」ことだけを確認する
    # （実機のLED実点灯状態はテスト実行環境に依存するため断定しない）
    assert orchestrator.context.history[0].result["status"] in ("READY", "NOT_READY")
