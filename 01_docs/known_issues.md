# 既知の課題（実装・設計）

`decisions/`が「その時点の決定を凍結した記録」であるのに対し、これは**まだ解決していない技術的負債の生きたチェックリスト**。解決したら都度チェックを付ける。各項目は「決まってること／決まってないこと／問題点／改善案」で整理している。

ロードマップ本線（Step0〜7）と必須課題4件（[12](decisions/12_essential_gaps_found.md)・[13](decisions/13_log_and_artifact_storage_gap.md)・[14](decisions/14_testexecutor_folder.md)）は完了済み。以下はそれとは別に残っている課題（2026-08-22時点）。

## 1. `params`の二重役割仕様

- [x] 対応済み（2026-09-01）
- **決まってること（最終）**：`normalizer.converter.convert()`が常に`steps`形式で出力するよう変更（改善案a採用）。`GenericOrchestrator`自体は従来形式も引き続き受け付ける後方互換のまま（`mapping.yaml`の書式も変更なし、変換後の出力だけをsteps形式に統一）
- **問題点（解消済み）**：同じ`params`キーが「コンストラクタ用」と「execute_step用」の2つの意味を持っていた点は、`convert()`の出力が常に分離された形になったことで実質解消
- 詳細：[06_workflow_yaml_usage.md 7節](decisions/06_workflow_yaml_usage.md)

## 2. テスト範囲が薄い

- [ ] 未対応
- **決まってること**：Fakeベースの単体テスト、hardwareマーカー分離は機能済み
- **決まってないこと**：カバレッジ目標、`CameraController`自体のテスト方針、複数シナリオE2Eをいつやるか
- **問題点**：実証されてるのは「撮影1パターン」のみ。`steps`形式・複数Adapter連携は理論上動くだけ。`CameraController`は自動テストゼロ（`test_camera_controller.py`は手動実行スクリプト）
- **改善案**：a) pytest-cov導入で可視化　b) `_make_img_path`等の純粋ロジック部分だけでも単体テスト化　c) mapping.yamlに2つ目のシナリオ（Audio等）を足して複数Adapter連携を実証

## 3. CI・静的解析が無い

- [ ] 未対応
- **決まってること**：無し（全て手動でpytest実行）
- **決まってないこと**：mypy/lint導入するか、GitHub Actions設定するか
- **問題点**：型ヒントはあるのに検証されてない。CIが無いので「テスト忘れてpush」のリスクは構造的には残ってる（今回は毎回手動確認してたので実害無し）
- **改善案**：優先度順に a) ruff（lint+format、軽量）　b) mypy　c) GitHub Actionsでpush時自動テスト

## 4. ログローテーション未対応

- [ ] 未対応
- **決まってること**：`testexecutor/logs/`に実行ごと新規ファイル作成（[13](decisions/13_log_and_artifact_storage_gap.md)で明記済み）
- **決まってないこと**：保持期間・自動削除の要否
- **問題点**：実行を繰り返すとファイルが無限に増える
- **改善案**：a) loguruの`retention`オプション（例：`retention="30 days"`）　b) 優先度低いので放置でも実害小さい

## 5. コンソール表示の文字化け

- [x] 対応済み（2026-09-05）
- **決まってること（最終）**：`run_scenario.py`冒頭で`sys.stdout`/`sys.stderr`両方を`reconfigure(encoding="utf-8")`（改善案a採用、ただし当初案の`sys.stdout`のみでは不十分と判明——loguruの既定シンクは`sys.stderr`のため、両方の固定が必要だった）
- 詳細：`testexecutor/run_scenario.py`冒頭

## 6. 2リポジトリ構成の運用リスク

- [x] 対応済み（2026-09-05）
- **決まってること（最終）**：「`usb_camera_adapter`配下を触ったら、そのリポジトリでも独立してcommit・pushする」という運用ルールを`CLAUDE.md`にチェックリスト化（改善案a採用）。モノレポ統合（改善案b）は見送り
- 詳細：[CLAUDE.md「2リポジトリ構成の運用ルール」](../CLAUDE.md)

## 7. デモ用`Orchestrator`と`GenericOrchestrator`の役割重複

- [x] 対応済み（2026-09-01）
- **決まってること（最終）**：`Orchestrator`を削除（改善案c採用）。ただし削除前に、`Orchestrator`にしか無かった機能（LED点灯確認`check_device_status()`）を`CameraAdapter.execute_step()`の`check_status`アクションとして`GenericOrchestrator`経由で使えるように移植してから削除した（機能自体は失っていない）
- **問題点（解消済み）**：`orchestrator/pyproject.toml`が`usb-camera-adapter`に依存していた原因も`Orchestrator`だったため、削除に伴いこの依存も解消。`orchestrator`パッケージが名実ともに`adapter-core`（抽象）のみに依存する形になった
- 詳細：[19_orchestrator_demo_class_removal.md](decisions/19_orchestrator_demo_class_removal.md)

## 8. `decisions/`が17件になっていて索引が無い

- [x] 対応済み（2026-09-04）
- **決まってること（最終）**：`01_docs/decisions/README.md`を新規作成。番号・タイトル・1行概要の表に加え、後から訂正・再移動された記録（01/02、04、06、07、16→18）を補足として明記した
- 詳細：[decisions/README.md](decisions/README.md)

## 9. `_summarize_result()`/`_summarize()`の重複

- [x] 対応済み（2026-09-04）
- **決まってること（最終）**：`adapter_core`に共通関数`summarize_result()`を切り出し（改善案採用）。`orchestrator.py`の`_summarize_result()`と`run_scenario.py`の`_summarize()`を削除し、両方が`adapter_core.logging_utils.summarize_result`を呼ぶ形に統一
- 詳細：新規`adapters/core/src/adapter_core/logging_utils.py`

## 10. `CameraAdapter`が2つのAPIを持っている

- [x] 対応済み（2026-09-04）
- **決まってること（最終）**：`CameraAdapter`の直接メソッド群（`open()`/`release()`/`is_opened()`/`capture()`/`save_capture()`/`is_led_on()`）を削除（改善案a採用）。`setup()`内の`self.open()`は`self.camera_controller.open()`に変更。正式な入口は`execute_step()`のみになった
- **問題点（解消済み）**：`test_camera_adapter.py`をFake（`CameraMockController`）＋`execute_step()`経由の検証に書き換え。実機テスト・本番経路（`run_scenario.py`）とも回帰なしを確認
- 詳細：`adapters/usb_camera_adapter`（別リポジトリ）の該当commit。`check_device_status()`は`execute_step("check_status")`の内部実装として存続
