"""ログをファイルにも残す設定。

run_scenario.pyから切り出したもの（2026-08-29 worklog参照）。
paths.pyのLOG_DIRに依存する。
"""

from datetime import datetime
from pathlib import Path

from loguru import logger

from paths import LOG_DIR


def setup_file_logging() -> Path:
    """実行ごとにタイムスタンプ付きのログファイルを残す（01_docs/decisions/13参照）。
    標準出力へのログ出力はそのまま維持し、ファイルにも同じログを書き出す（追加のsink）。
    """
    LOG_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = LOG_DIR / f"run_{timestamp}.log"
    logger.add(log_path, encoding="utf-8")
    logger.info(f"ログファイル: {log_path}")
    return log_path
