"""プロジェクト全体を実行する正規の入口。

PlantUMLシナリオ -> normalizer.converter -> GenericOrchestrator -> Adapter -> Controller
の一気通貫を実行する（01_docs/decisions/12_essential_gaps_found.md 課題1の対応）。

実行ファイル・ログ出力先・成果物（撮影画像）出力先を、このtestexecutor/フォルダに
まとめている（01_docs/decisions/14_testexecutor_folder.md参照）。

使い方:
    uv run python testexecutor/run_scenario.py
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

from loguru import logger

from normalizer.converter import convert, load_mapping
from orchestrator.orchestrator import GenericOrchestrator

THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = THIS_DIR.parent

SCENARIO_PATH = PROJECT_ROOT / "normalizer" / "puml" / "scenario.puml"
MAPPING_PATH = PROJECT_ROOT / "normalizer" / "config" / "mapping.yaml"
LOG_DIR = THIS_DIR / "logs"
IMG_DIR = THIS_DIR / "img"


def _setup_file_logging() -> Path:
    """実行ごとにタイムスタンプ付きのログファイルを残す（01_docs/decisions/13参照）。
    標準出力へのログ出力はそのまま維持し、ファイルにも同じログを書き出す（追加のsink）。
    """
    LOG_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = LOG_DIR / f"run_{timestamp}.log"
    logger.add(log_path, encoding="utf-8")
    logger.info(f"ログファイル: {log_path}")
    return log_path


def _inject_img_dir(pipeline: list[dict]) -> None:
    """撮影系ステップのparamsに、testexecutor/img/への出力先を注入する。

    CameraController側はimg_dir未指定なら自パッケージ内img/へ保存する後方互換動作のまま。
    scenario_test（呼び出し側）だけが、ここで出力先を上書きする。
    """
    IMG_DIR.mkdir(exist_ok=True)
    for step in pipeline:
        if step.get("action") == "capture":
            step.setdefault("params", {})["img_dir"] = str(IMG_DIR)


async def run() -> bool:
    _setup_file_logging()
    plantuml_text = SCENARIO_PATH.read_text(encoding="utf-8")
    lifecycle_labels, action_mapping = load_mapping(MAPPING_PATH)

    pipeline = convert(plantuml_text, lifecycle_labels, action_mapping)
    _inject_img_dir(pipeline)
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
