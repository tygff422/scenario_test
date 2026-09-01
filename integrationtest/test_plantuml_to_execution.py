"""PlantUML -> normalizer.converter -> GenericOrchestrator.execute() の
一連の流れを、実機なしで通しで検証する統合テスト。

integrationtest/はパッケージ境界をまたいで組み合わせて検証する場所
（01_docs/decisions/03_package_settings_adapter_orchestrator.md参照）。

FakePipelineAdapter（orchestrator/tests/orchestrator_test_support/）は
そのtests/配下でしかimportできない（01_docs/decisions/01_import_resolution_rules.md
ルール4：pytestのprependモードはテストファイルのディレクトリ限定でsys.pathに効く）ため、
このテスト専用の軽量なFakeをこのファイル内に定義する。
"""

import asyncio
from typing import Any, ClassVar, Dict

from adapter_core.baseadapter import BaseAdapter
from normalizer.converter import convert
from orchestrator.orchestrator import GenericOrchestrator


class FakeSensorAdapter(BaseAdapter):
    """このテスト専用のFake。GenericOrchestratorから動的importで呼ばれる。"""

    events: ClassVar[list[str]] = []

    def __init__(self, config: Dict[str, Any] | None = None):
        self.config = config or {}

    def setup(self) -> bool:
        FakeSensorAdapter.events.append("setup")
        return True

    async def execute_step(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        FakeSensorAdapter.events.append(f"execute:{action}")
        return {"status": "SUCCESS", "action": action}

    def teardown(self) -> None:
        FakeSensorAdapter.events.append("teardown")


# convert()に渡す変換ルール（本番のnormalizer/config/mapping.yamlとは別の、このテスト専用のルール）
LIFECYCLE_LABELS = {"センサー接続", "センサー切断"}
ACTION_MAPPING = {
    "センサー計測": {
        "adapter": "test_plantuml_to_execution.FakeSensorAdapter",
        "action": "measure",
        "params": {},
    },
}


def test_plantuml_to_execution_end_to_end():
    FakeSensorAdapter.events.clear()

    plantuml_text = """
@startuml
start
:センサー接続;
:センサー計測;
:センサー切断;
stop
@enduml
"""
    # ① PlantUML -> pipeline（list[dict]）変換（出力は常にsteps形式、01_docs/known_issues.md No.1対応）
    pipeline = convert(plantuml_text, LIFECYCLE_LABELS, ACTION_MAPPING)
    assert pipeline == [
        {
            "name": "センサー計測",
            "adapter": "test_plantuml_to_execution.FakeSensorAdapter",
            "params": {},
            "steps": [{"action": "measure", "params": {}}],
        }
    ]

    # ② 変換結果をファイルに書き出さず、そのままGenericOrchestrator.execute()へ渡す
    orchestrator = GenericOrchestrator()
    result = asyncio.run(orchestrator.execute(pipeline))

    # ③ Adapterのライフサイクル通りに実行されたことを確認
    assert result is True
    assert FakeSensorAdapter.events == ["setup", "execute:measure", "teardown"]
