from typing import Any, ClassVar, Dict

from adapter_core.baseadapter import BaseAdapter


class FakePipelineAdapter(BaseAdapter):
    """GenericOrchestratorのE2Eテスト用Fake。

    workflow.yamlのadapterに"orchestrator_test_support.fake_pipeline_adapter.FakePipelineAdapter"を
    指定することで、実機（CameraAdapter等）なしにパイプライン全体の配線
    （動的import -> setup -> execute_step -> teardown）を検証できる。

    GenericOrchestratorはステップごとに`cls(config=params)`で新しいインスタンスを
    生成するため、呼び出し履歴はテスト側から見えるようクラス変数に記録する。
    テストの冒頭で`FakePipelineAdapter.events.clear()`してから使うこと。
    """

    events: ClassVar[list[str]] = []

    def __init__(self, config: Dict[str, Any] | None = None):
        self.config = config or {}

    def setup(self) -> bool:
        FakePipelineAdapter.events.append("setup")
        return not self.config.get("setup_should_fail", False)

    def execute_step(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        FakePipelineAdapter.events.append(f"execute:{action}")
        if params.get("execute_should_raise", False):
            raise RuntimeError("FakePipelineAdapter: 意図的なexecute_step失敗")
        return {"status": "SUCCESS", "action": action}

    def teardown(self) -> None:
        FakePipelineAdapter.events.append("teardown")
