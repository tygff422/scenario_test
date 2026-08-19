from dataclasses import dataclass, field
from typing import Any


@dataclass
class StepResult:
    """1回のexecute_step()呼び出しの結果を1件記録する。"""

    name: str  # pipeline要素のnameフィールド（steps形式ならセッション名）
    action: str  # 実行したaction
    result: dict[str, Any]  # execute_step()の戻り値


@dataclass
class Context:
    """パイプライン実行中の各ステップの結果を、実行順に貯める入れ物。

    v0では「後から参照できるように保持する」だけ。ステップ間でparamsへ
    自動的に前の結果を注入する機能（テンプレート的な置換）は、必要になったら拡張する。
    """

    history: list[StepResult] = field(default_factory=list)

    def record(self, name: str, action: str, result: dict[str, Any]) -> None:
        self.history.append(StepResult(name=name, action=action, result=result))

    def last_result_for(self, action: str) -> dict[str, Any] | None:
        """指定actionの直近の結果を取得する。見つからなければNone。"""
        for entry in reversed(self.history):
            if entry.action == action:
                return entry.result
        return None
