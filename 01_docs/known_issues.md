# 既知の課題（実装・設計）

`decisions/`が「その時点の決定を凍結した記録」であるのに対し、これは**まだ解決していない技術的負債の生きたチェックリスト**。解決したら都度チェックを付ける。各項目は「決まってること／決まってないこと／問題点／改善案」で整理している。

ロードマップ本線（Step0〜7）と必須課題4件（[12](decisions/12_essential_gaps_found.md)・[13](decisions/13_log_and_artifact_storage_gap.md)・[14](decisions/14_testexecutor_folder.md)）は完了済み。以下はそれとは別に残っている課題（2026-08-22時点）。

## 1. `params`の二重役割仕様

- [ ] 未対応
- **決まってること**：従来形式（1要素=1アクション）は後方互換のため維持。`steps`形式では既に分離済み（[06](decisions/06_workflow_yaml_usage.md)）
- **決まってないこと**：従来形式をいつか廃止するか、常に`steps`形式に統一するか
- **問題点**：同じ`params`キーが「コンストラクタ用」と「execute_step用」の2つの意味を持つ。ドキュメントを読まないと気づけない暗黙知
- **改善案**：a) `converter.py`が常に`steps`形式で出力するよう統一し、従来形式を段階的に非推奨化　b) 現状維持（実害が出るまで様子見）

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

- [ ] 未対応
- **決まってること**：ログファイル自体はUTF-8で正常。表示だけの問題と特定済み
- **決まってないこと**：直すかどうか
- **問題点**：Windows Terminalのcodepage起因で読みづらい
- **改善案**：a) `run_scenario.py`冒頭で`sys.stdout.reconfigure(encoding="utf-8")`　b) 無視してよい（実害はログファイルには無い）

## 6. 2リポジトリ構成の運用リスク

- [ ] 未対応
- **決まってること**：`usb_camera_adapter`は別リポジトリのまま維持（元々別プロジェクトだった経緯を尊重）
- **決まってないこと**：このリスクをどう構造的に緩和するか
- **問題点**：cross-cutting変更のたびに2回コミットが要り、片方忘れる事故が**実際に発生済み**（`Readme.md`リネームの件、[07](decisions/07_folder_structure_cleanup.md)の訂正参照）
- **改善案**：a) 「〇〇を触ったら別リポジトリ側も確認する」をチェックリスト化する運用ルール　b) 将来的な統合（1モノレポ化）も選択肢だが未決定

## 7. デモ用`Orchestrator`と`GenericOrchestrator`の役割重複

- [ ] 未対応
- **決まってること**：両方残す方針（Step5で「対象外のまま維持」と明記済み）
- **決まってないこと**：最終的にどうするか
- **問題点**：実質`GenericOrchestrator`が上位互換なのに、名前が紛らわしい`Orchestrator`が並存し続けてる
- **改善案**：a) `DemoOrchestrator`等に改名し役割を明確化　b) docstringで「本線は`GenericOrchestrator`」と明記　c) 思い切って削除（git historyに残るので復元可能）
