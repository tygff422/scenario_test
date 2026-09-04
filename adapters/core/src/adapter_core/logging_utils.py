"""ログ出力用のちょっとした整形ユーティリティ。

orchestrator.pyのGenericOrchestratorとtestexecutor/run_scenario.pyの両方が、
execute_stepの戻り値をログに出す前に同じ処理（numpy配列などの巨大な値を要約する）を
必要とするため、adapter_coreに共通関数として切り出した（01_docs/known_issues.md No.9対応）。
"""

from typing import Any, Dict


def summarize_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """ログ出力用に、frame(numpy配列)等の巨大な値を要約する（中身をそのまま出さない）。

    shape属性を持つ値（numpy配列等）だけを"<array shape=...>"に置き換え、
    それ以外の値はそのまま返す。
    """
    return {
        key: (f"<array shape={value.shape}>" if hasattr(value, "shape") else value)
        for key, value in result.items()
    }
