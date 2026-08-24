# 15_remove_unused_workflow_yaml

- 日付: 2026-08-24
- 関連: [08_plantuml_conversion_design_policy.md](08_plantuml_conversion_design_policy.md)（execute()メモリ直渡しの決定）
- ステータス: 完了

## 背景

`testexecutor/run_scenario.py`の仕組みを説明していた際、「`normalizer/config/workflow.yaml`は今も必要か」という質問があり、コード全体を検索したところ**実ファイルとして読んでいる箇所がゼロ**だと判明した。

```text
workflow.yamlが生きてた頃：GenericOrchestrator.execute_pipeline()がファイルを読んで実行してた
今：run_scenario.pyはexecute()（メモリ直渡し）を使い、ファイルを一切経由しない
```

`normalizer/config/workflow.yaml`は、`execute_pipeline()`（ファイル駆動）がまだ本線だった頃（Step2〜6初期）の手書きサンプルが、`execute()`（メモリ直渡し、Step6決定）へ移行した後も削除されずに残っていた成果物。本番設定っぽく見えるのに実際は使われていない、紛らわしい状態だった。

## 対応

- `normalizer/config/workflow.yaml`を削除
- `orchestrator/README.md`：`execute_pipeline()`のコード例のパスを汎用的なプレースホルダーに変更し、「このファイルは現存しない・`testexecutor/run_scenario.py`は`execute()`を使っている」旨を注記
- `implementation_plan.md`：実装済みリストの記載を`normalizer/config/scenario.puml`に修正
- `decisions/01・06・07・08`は当時の状態を正しく記録した歴史的記録として、変更せずそのまま残す

## 確認

`uv run pytest -m "not hardware" -q`で退行が無いことを確認（`execute_pipeline()`のテストは自前で一時ファイルを作るため、このファイル削除の影響を受けない）。
