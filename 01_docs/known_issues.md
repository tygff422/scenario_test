# 既知の課題（実装・設計）

`decisions/`が「その時点の決定を凍結した記録」であるのに対し、これは**まだ解決していない技術的負債の生きたチェックリスト**。解決したら都度チェックを付ける。詳しい経緯は各項目からリンクしているdecisionを参照。

ロードマップ本線（Step0〜7）と必須課題4件（[12](decisions/12_essential_gaps_found.md)・[13](decisions/13_log_and_artifact_storage_gap.md)・[14](decisions/14_testexecutor_folder.md)）は完了済み。以下はそれとは別に残っている課題（2026-08-22時点）。

- [ ] **`params`の二重役割仕様**：従来形式（1要素=1アクション）の`params`が、Adapterのコンストラクタとexecute_step両方に渡る仕様のまま。`steps`形式では解消済みだが、後方互換のため従来形式はそのまま残している（[06](decisions/06_workflow_yaml_usage.md)）
- [ ] **テスト範囲が薄い**：実シナリオが撮影1パターンのみで、`steps`形式・複数Adapter連携は理論上動くだけで実例で証明されていない。`CameraController`自体（一番下のI/O層）にも自動テストが無い（`test_camera_controller.py`は手動実行スクリプト）。カバレッジ計測（pytest-cov等）も未導入
- [ ] **CI・静的解析が無い**：型ヒントは書かれているがmypy等の型チェック・lintは未導入。GitHub Actions等のCIも無く、テスト実行は手動運用に依存している
- [ ] **ログローテーション未対応**：`testexecutor/logs/`が実行のたびに増え続ける（[13](decisions/13_log_and_artifact_storage_gap.md)で保留と明記済み）
- [ ] **コンソール表示の文字化け**：Windowsターミナルのcodepage起因。ログファイル自体（UTF-8）には影響しないため優先度は低い
- [ ] **2リポジトリ構成の運用リスク**：root（`scenario_test`）と`usb_camera_adapter`が別リポジトリのため、cross-cutting変更のたびに2回コミットが要る。`Readme.md`リネームが片方に未反映のまま気づかず残っていた実例あり（[07](decisions/07_folder_structure_cleanup.md)の訂正参照）
- [ ] **デモ用`Orchestrator`と`GenericOrchestrator`の役割重複**：`GenericOrchestrator`が機能的に上位互換になった今も、デモ用`Orchestrator`（CameraAdapter固定クラス）が整理されずに並存している。非推奨化するか、デモ用として明確に位置づけ直すかの判断が未了
