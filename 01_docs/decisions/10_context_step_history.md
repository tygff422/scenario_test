# 10_context_step_history

- 日付: 2026-08-19
- 関連Step: Step7（最終統合） / [06_workflow_yaml_usage.md](06_workflow_yaml_usage.md)（steps形式）
- ステータス: 完了（v0）

## 背景

`GenericOrchestrator.execute()`は各ステップの`execute_step()`の戻り値をログに出すだけで捨てていた。前のステップの結果を後から参照したい（デバッグ・テスト・将来のステップ間連携）というニーズに対応するため、`context.py`を追加した。

## 決定事項

### `Context`は「実行履歴を貯めるだけの入れ物」（v0）

`orchestrator/src/orchestrator/context.py`に追加。

```python
@dataclass
class StepResult:
    name: str
    action: str
    result: dict[str, Any]

@dataclass
class Context:
    history: list[StepResult] = field(default_factory=list)

    def record(self, name: str, action: str, result: dict[str, Any]) -> None:
        self.history.append(StepResult(name=name, action=action, result=result))

    def last_result_for(self, action: str) -> dict[str, Any] | None:
        for entry in reversed(self.history):
            if entry.action == action:
                return entry.result
        return None
```

**あえてやらなかったこと**：前のステップの結果を次のステップの`params`へ自動的に注入する機能（テンプレート的な置換、例：`"${previous.result.frame}"`のような構文）は実装しない。実際にそれが必要なPlantUMLシナリオが出てきた時点で拡張する（YAGNI、これまでの一連の決定と同じ方針）。

### `dict`ではなく`list`（履歴）にした理由

`steps`形式では同じ`name`（セッション名）の中で複数actionが実行される。`name`をキーにした`dict`だと2回目以降の結果が1回目を上書きしてしまうため、`list`で全履歴を残す設計にした。`last_result_for(action)`で「指定actionの直近の結果」を取得できるようにし、最低限の検索性は確保した。

### `GenericOrchestrator`への組み込み

- `__init__`で`self.context = Context()`を生成
- `execute(pipeline)`の冒頭で`self.context = Context()`にリセット（呼び出しのたびに前回の履歴を引き継がない）
- 従来形式・`steps`形式のどちらの分岐でも、各`execute_step()`呼び出し直後に`self.context.record(...)`する

呼び出し側は実行後に`orchestrator.context.history`または`orchestrator.context.last_result_for(action)`で参照する。

## テスト

`orchestrator/tests/test_context.py`を新規追加。

- `Context.record`/`last_result_for`の単体テスト
- `execute()`が従来形式で正しく1件記録すること
- `execute()`が`steps`形式で複数件を上書きせず記録すること
- `execute()`を2回呼んだ際に履歴がリセットされること

## 確認

`uv run pytest -m "not hardware" -q` → `32 passed, 2 deselected`（退行なし）。
