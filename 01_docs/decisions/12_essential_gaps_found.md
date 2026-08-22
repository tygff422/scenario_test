# 12_essential_gaps_found

- 日付: 2026-08-22
- 関連: [implementation_plan.md](../implementation_plan.md)（プロジェクトの最終ゴール定義）
- ステータス: 完了（3件とも対応・実機で確認済み）

## 背景

Step0〜7完了後、「プロジェクト全体を実行する正規の手段」について確認したところ、実は存在しないことが判明した。これをきっかけに、他に必須の抜け漏れが無いかコード全体を検索して棚卸しした。

## 見つかった必須課題（3件）

### 1. プロジェクト全体を実行する正規の入口が無い

`implementation_plan.md`冒頭の目標（`PlantUMLシナリオ -> 変換 -> Orchestrator -> Adapter -> Controller`の一気通貫）に対し、部品（`GenericOrchestrator`・`normalizer.converter`・`Context`・`registry`）は揃っているが、それらを1つに繋いで動かすファイルが無い。`orchestrator/main.py`はデモ用`Orchestrator`（CameraAdapter固定、YAML/PlantUML不使用）を動かすだけの別経路。

**このプロジェクトの目的（設計する力を身につける）に対して、動くゴールが実際に手元に無い状態**という意味で必須。

### 2. `GenericOrchestrator`が実機カメラで一度も検証されていない

コード全体を検索した結果、`GenericOrchestrator`を実機カメラ経由で使っている箇所がゼロだった。

```text
@pytest.mark.hardware が付いたテストは2件のみ：
- integrationtest/test_dynamic_import.py … importlibを手動で叩くだけ（GenericOrchestrator不使用）
- integrationtest/test_integration.py    … デモ用Orchestrator（CameraAdapter固定）を使用
```

Step5（非同期化）・Step6（steps形式）・Step7（context/registry）は全て`GenericOrchestrator`への変更だったにもかかわらず、実機での動作確認は一度もされていない（Fake経由のテストのみ）。`steps`形式（同一インスタンスの使い回し）は特に、実機カメラの再接続コスト回避が動機だったのに、その動機自体が実機で確認されていない。

### 3. LED二重チェックのバグ（デモ用Orchestrator経路）

`orchestrator/main.py`実行時、`CameraAdapter.setup()`内の`check_device_status()`（1回目）と、`Orchestrator.execute()`内の`adapter.check_device_status()`（2回目）で、LED点灯判定が2回実行されている（＝2回撮影している）。1回で十分なはずで、無駄な撮影が発生している。

## 対応内容（2026-08-22、同日中に完了）

### 1. 正規の実行入口：`run_scenario.py`

プロジェクトルートに新規作成。`normalizer/config/scenario.puml`（入力シナリオ）→`normalizer.converter`→`GenericOrchestrator.execute()`の一気通貫を実行する。

```bash
uv run python run_scenario.py
```

**実機で実行し、exit code 0を確認済み。** `orchestrator/main.py`（デモ用`Orchestrator`固定経路）とは別物として共存させた（同名衝突を避けるため`main.py`ではなく`run_scenario.py`という名前にした）。

### 2. `GenericOrchestrator`の実機検証

`integrationtest/test_integration.py`に`test_generic_orchestrator_with_real_camera_adapter`（`@pytest.mark.hardware`）を追加。実際にこの端末で実機カメラが利用可能なことが判明し、`uv run pytest -m hardware -q`で**3件全てPASS**（既存2件＋新規1件）。

副次的に、`GenericOrchestrator`・`run_scenario.py`双方で、`execute_step`の戻り値（`frame`のnumpy配列）をログにそのまま出力すると大量の数値列がログに流れる問題を発見。`_summarize_result()`（配列は`<array shape=...>`に要約）をそれぞれに追加して解消した。

### 3. LED二重チェックのバグ

`CameraAdapter.setup()`から`check_device_status()`の呼び出しを削除し、`open()`のみに変更（[06_workflow_yaml_usage.md](06_workflow_yaml_usage.md)・[04_urgent_fix_camera_pipeline.md](04_urgent_fix_camera_pipeline.md)に追記済み）。LED確認は呼び出し元（デモ用`Orchestrator.execute()`）が引き続き自分で行う。

## 確認

`uv run pytest -m "not hardware" -q` → `40 passed, 3 deselected`
`uv run pytest -m hardware -q` → `3 passed`（実機カメラで実行、退行なし）
