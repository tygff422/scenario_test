"""プロジェクト全体を実行する正規の入口。

PlantUMLシナリオ -> normalizer.converter -> GenericOrchestrator -> Adapter -> Controller
の一気通貫を実行する（01_docs/decisions/12_essential_gaps_found.md 課題1の対応）。

使い方:
    uv run python run_scenario.py
"""

import asyncio
import sys
from pathlib import Path

from loguru import logger

from normalizer.converter import convert, load_mapping
from orchestrator.orchestrator import GenericOrchestrator

BASE_DIR = Path(__file__).parent
SCENARIO_PATH = BASE_DIR / "normalizer" / "config" / "scenario.puml"
MAPPING_PATH = BASE_DIR / "normalizer" / "config" / "mapping.yaml"


async def run() -> bool:
    plantuml_text = SCENARIO_PATH.read_text(encoding="utf-8")
    lifecycle_labels, action_mapping = load_mapping(MAPPING_PATH)

    pipeline = convert(plantuml_text, lifecycle_labels, action_mapping)
    logger.info(f"シナリオ変換完了: {SCENARIO_PATH.name} -> {len(pipeline)}ステップ")

    orchestrator = GenericOrchestrator()
    result = await orchestrator.execute(pipeline)

    for entry in orchestrator.context.history:
        logger.info(f"[実行結果] {entry.name} / {entry.action} / {_summarize(entry.result)}")

    return result


def _summarize(result: dict) -> dict:
    """ログ出力用に、frame等の巨大な値を要約する（numpy配列の中身をそのまま出さない）"""
    summary = {}
    for key, value in result.items():
        if hasattr(value, "shape"):
            summary[key] = f"<array shape={value.shape}>"
        else:
            summary[key] = value
    return summary


if __name__ == "__main__":
    success = asyncio.run(run())
    sys.exit(0 if success else 1)
