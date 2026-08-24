# 16_normalizer_puml_folder

- 日付: 2026-08-24
- 関連: [15_remove_unused_workflow_yaml.md](15_remove_unused_workflow_yaml.md)
- ステータス: 完了

## 背景

`scenario.puml`が`normalizer/config/`に置かれていたが、`config/`は本来「設定・変換ルール」（`mapping.yaml`）の置き場であり、PlantUMLシナリオ（図・入力データ）とは性質が違う。今後複数の`.puml`ファイルを追加していく運用を見据え、置き場を分けたいという要望があった。

## 決定

`normalizer/puml/`を新設し、`scenario.puml`をここへ移動した。フォルダ名は拡張子そのままの`puml`を採用（`activity`等、特定の図種類を示す名前は将来別種のPlantUML図を置く可能性を狭めるため見送った）。

```text
normalizer/
  config/
    mapping.yaml     ← 変換ルール
  puml/
    scenario.puml    ← シナリオ本体（今後複数追加していく）
```

`testexecutor/run_scenario.py`の`SCENARIO_PATH`を`normalizer/puml/scenario.puml`に変更。`mapping.yaml`は対象外（`config/`のまま）。

## 確認

`uv run pytest -m "not hardware" -q` → `40 passed, 3 deselected`（退行なし）。実機で`testexecutor/run_scenario.py`を実行し、`exit code 0`・撮影成功を確認済み。
