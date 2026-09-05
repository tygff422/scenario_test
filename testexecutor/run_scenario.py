"""プロジェクト全体を実行する正規の入口。

PlantUMLシナリオ -> normalizer.converter -> GenericOrchestrator -> Adapter -> Controller
の一気通貫を実行する（01_docs/decisions/12_essential_gaps_found.md 課題1の対応）。

実行ファイル・ログ出力先・成果物（撮影画像）出力先を、このtestexecutor/フォルダに
まとめている（01_docs/decisions/14_testexecutor_folder.md参照）。パス管理は
paths.py、ログ設定はlogging_setup.pyに切り出してある（2026-08-29 worklog参照）。

使い方:
    uv run python testexecutor/run_scenario.py
"""

import asyncio
import sys

# Windows Terminalでのコンソール表示文字化け対策（01_docs/known_issues.md No.5対応）。
# ログファイル自体はUTF-8で正常なので、これは表示だけの問題。loguruの既定シンクは
# sys.stderr（sys.stdoutではない）なので、両方をUTF-8に固定しておく。
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

from loguru import logger

from adapter_core.logging_utils import summarize_result
from normalizer.converter import convert, load_mapping
from orchestrator.orchestrator import GenericOrchestrator

from logging_setup import setup_file_logging
from paths import IMG_DIR, SCENARIO_PATH


def _inject_img_dir(pipeline: list[dict]) -> None:
    """撮影系ステップのparamsに、testexecutor/img/への出力先を注入する。

    CameraController側はimg_dir未指定なら自パッケージ内img/へ保存する後方互換動作のまま。
    scenario_test（呼び出し側）だけが、ここで出力先を上書きする。

    convert()の出力は常にsteps形式（01_docs/known_issues.md No.1対応）なので、actionは
    トップレベルではなくsteps[].actionを見る。img_dirはコンストラクタ用の値（CameraAdapter.
    __init__が読む）なので、トップレベルのparams（コンストラクタ専用）に注入する。
    """
    IMG_DIR.mkdir(exist_ok=True)
    for step in pipeline:
        actions = [sub_step.get("action") for sub_step in step.get("steps", [])]
        if "capture" in actions:
            step.setdefault("params", {})["img_dir"] = str(IMG_DIR)


async def run() -> bool:
    setup_file_logging()
    plantuml_text = SCENARIO_PATH.read_text(encoding="utf-8")
    lifecycle_labels, action_mapping = load_mapping()

    pipeline = convert(plantuml_text, lifecycle_labels, action_mapping)
    _inject_img_dir(pipeline)
    logger.info(f"シナリオ変換完了: {SCENARIO_PATH.name} -> {len(pipeline)}ステップ")

    orchestrator = GenericOrchestrator()
    result = await orchestrator.execute(pipeline)

    for entry in orchestrator.context.history:
        logger.info(f"[実行結果] {entry.name} / {entry.action} / {summarize_result(entry.result)}")

    return result


if __name__ == "__main__":
    success = asyncio.run(run())
    sys.exit(0 if success else 1)
