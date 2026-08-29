# 18_scenario_puml_ownership

- 日付: 2026-08-29
- 関連: [16_normalizer_puml_folder.md](16_normalizer_puml_folder.md)（訂正対象）
- ステータス: 完了

## 背景

`capture_pipeline_map.html`でプロジェクト構成の図を解説していた際、「`scenario.puml`が`normalizer/`配下にあるのは不自然では？実際に使っているのは`testexecutor`では」という指摘があった。コードを確認したところ、指摘の通りだった。

## 確認した事実

```python
# normalizer/src/normalizer/converter.py
def convert(plantuml_text: str, lifecycle_labels, action_mapping) -> list[dict]:
    ...
```

`convert()`は`plantuml_text`という**文字列**を受け取るだけで、`scenario.puml`というファイルの存在自体を一切知らない。実際にファイルを開いているのは`testexecutor/run_scenario.py`の`SCENARIO_PATH.read_text()`。

```text
mapping.yaml   → normalizer自身が読む（load_mapping()の中でopen()する）   → normalizerの持ち物
scenario.puml  → testexecutorが読む（normalizerはtextとして受け取るだけ） → testexecutorの持ち物
```

この2つのファイルは、これまで「PlantUML関連だから」という見た目の理由で同じ`normalizer/`配下にまとめて置いていたが、実際のファイルI/Oの所有者は異なっていた。

## 決定：依存の向きに合わせて所有者ごとにフォルダを分ける

```text
testexecutor --使う--> normalizer（importして呼び出す。一方通行）
```

この依存関係を踏まえ、「呼び出す側（testexecutor）が選ぶ入力データは、呼び出す側の持ち物」という原則を採用した。

```text
testexecutor/
  run_scenario.py
  puml/scenario.puml   ← normalizer/から移動。testexecutor自身が読むファイル
  img/, logs/

normalizer/
  config/mapping.yaml   ← そのまま。normalizer自身が読むファイル
  src/normalizer/converter.py
```

`testexecutor/run_scenario.py`の`SCENARIO_PATH`を`THIS_DIR / "puml" / "scenario.puml"`に変更（`PROJECT_ROOT`経由ではなく、自分の直下を指すよう単純化）。

## 影響範囲・対応内容

- `testexecutor/run_scenario.py`：`SCENARIO_PATH`変更
- `01_docs/capture_pipeline_map.html`：フォルダ一覧を`normalizer/`→`testexecutor/`へ移動、日付更新
- `01_docs/implementation_plan.md`：実装済みリストの記載を修正
- `01_docs/new_adapter_package_guide.md`：`normalizer/puml/`への言及を`testexecutor/puml/`に修正
- `01_docs/decisions/16_normalizer_puml_folder.md`：内容は変更せず、末尾に訂正の追記のみ（過去の記録を書き換えない方針）

## 確認

実機で`testexecutor/run_scenario.py`を実行し、`exit code 0`・撮影成功（`saved_path`が新しいimg/に生成）を確認。`uv run pytest -m "not hardware" -q`も退行なし。
