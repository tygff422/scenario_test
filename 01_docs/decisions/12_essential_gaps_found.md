# 12_essential_gaps_found

- 日付: 2026-08-22
- 関連: [implementation_plan.md](../implementation_plan.md)（プロジェクトの最終ゴール定義）
- ステータス: 課題を記録（対応はこれから）

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

## 対応方針

3件とも対応する。順番は次のタスクから着手する。
