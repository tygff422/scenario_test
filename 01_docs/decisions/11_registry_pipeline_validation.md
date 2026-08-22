# 11_registry_pipeline_validation

- 日付: 2026-08-22
- 関連Step: Step7（最終統合） / [10_context_step_history.md](10_context_step_history.md)（context.py）
- ステータス: 完了

## 背景

`GenericOrchestrator`は各ステップを実行する時に初めて`adapter`クラスパスをロードしていた。そのため、pipelineの3番目のステップのクラスパスが間違っていても、1・2番目は実際に実行されてから3番目でエラーになる、という事故が起きうる状態だった。実行前に全ステップのクラスパスを一括検証する`registry.py`を追加した。

## 決定事項

### 置き場所：`orchestrator/src/orchestrator/registry.py`

`normalizer`ではなく`orchestrator`配下に置いた。検証対象がAdapterクラスパスのロード可否であり、`normalizer`（PlantUML→dict変換）はクラスの実在を関知しないため。`context.py`と同じ判断基準。

### 中身

```python
def load_adapter_class(class_path: str) -> Type[BaseAdapter]:
    """動的import + BaseAdapterサブクラス検証（従来GenericOrchestrator._load_adapterにあったロジック）"""
    ...

def validate_pipeline(pipeline: list[dict]) -> list[str]:
    """pipeline内の全adapterクラスパスを検証し、エラーメッセージのlistを返す。空なら全て正常。"""
    ...
```

`GenericOrchestrator._load_adapter`（インスタンスメソッド）は廃止し、`registry.load_adapter_class`（モジュール関数）に一本化した。事前検証（`validate_pipeline`）と実行時ロード（ループ内）の両方がこの同じ関数を呼ぶ。

### `execute()`への組み込み

```python
async def execute(self, pipeline: list[dict]) -> bool:
    self.context = Context()

    errors = validate_pipeline(pipeline)
    if errors:
        for error in errors:
            logger.error(f"[事前検証エラー] {error}")
        return False

    # ここから従来通りのループ
    ...
```

1つでも不正なadapterクラスパスがあれば、**どのステップも実行せずに**`False`を返す。正常なステップの実行結果と混ざって「一部だけ実行された状態」になることを防ぐ。

## テスト

- `orchestrator/tests/test_registry.py`（新規）：`load_adapter_class`/`validate_pipeline`の単体テスト。
  正常系、adapter指定漏れ、BaseAdapter非継承、存在しないモジュール、複数エラーの収集を検証
- `orchestrator/tests/test_generic_orchestrator.py`：正常なステップと不正なステップが混在する
  pipelineで、正常な方も含めて`setup`すら1度も呼ばれないことを検証（フェイルファストの確認）

## 確認

`uv run pytest -m "not hardware" -q` → `40 passed, 2 deselected`（退行なし）。
