# decisions/ 索引

`decisions/`は設計判断をADR（Architecture Decision Record）形式で記録した場所。`known_issues.md`（生きたチェックリスト）とは違い、**その時点の決定を凍結した記録**——後から中身を書き換えず、訂正がある場合は「訂正」として追記する（[01_docs/known_issues.md](../known_issues.md) No.8対応）。

番号（＝作成順）順に並んでいる。

| No. | タイトル | 概要 |
|---|---|---|
| [01](01_import_resolution_rules.md) | import_resolution_rules | プロジェクト全体に共通する「importがなぜ解決できるのか」のルール集 |
| [02](02_root_pyproject_settings.md) | root_pyproject_settings | ルート`pyproject.toml`の設定を1行ずつ解説 |
| [03](03_package_settings_adapter_orchestrator.md) | package_settings_adapter_orchestrator | `orchestrator`・`adapters/`各パッケージの設定・依存関係の整理 |
| [04](04_urgent_fix_camera_pipeline.md) | urgent_fix_camera_pipeline | Step0の緊急修正8件の記録 |
| [05](05_permission_prompt_reduction.md) | permission_prompt_reduction | Claude Codeの権限確認プロンプト削減の設定変更 |
| [06](06_workflow_yaml_usage.md) | workflow_yaml_usage | pipeline（旧workflow.yaml）の書き方・値の渡り方ガイド |
| [07](07_folder_structure_cleanup.md) | folder_structure_cleanup | フォルダ構成の棚卸しと6件の整理 |
| [08](08_plantuml_conversion_design_policy.md) | plantuml_conversion_design_policy | PlantUML→変換（Step6）の設計方針決定 |
| [09](09_async_execute_step.md) | async_execute_step | `execute_step`の非同期化（Step5） |
| [10](10_context_step_history.md) | context_step_history | 各ステップの実行結果履歴を保持する`Context` |
| [11](11_registry_pipeline_validation.md) | registry_pipeline_validation | pipeline実行前の全adapterクラスパス一括検証 |
| [12](12_essential_gaps_found.md) | essential_gaps_found | 必須課題3件の棚卸し（正規実行入口・実機検証・LED二重チェック） |
| [13](13_log_and_artifact_storage_gap.md) | log_and_artifact_storage_gap | 撮影画像・ログの永続化仕様 |
| [14](14_testexecutor_folder.md) | testexecutor_folder | 実行ファイル・ログ・成果物を`testexecutor/`へ集約 |
| [15](15_remove_unused_workflow_yaml.md) | remove_unused_workflow_yaml | 未使用だった`workflow.yaml`実ファイルの削除 |
| [16](16_normalizer_puml_folder.md) | normalizer_puml_folder | `scenario.puml`を`normalizer/puml/`へ移動（⚠[18](18_scenario_puml_ownership.md)でさらに再移動、下記補足参照） |
| [17](17_capture_pipeline_diagram.md) | capture_pipeline_diagram | 変換・実行経路の図をArtifactとして作成・保存する方式の決定 |
| [18](18_scenario_puml_ownership.md) | scenario_puml_ownership | `scenario.puml`を`testexecutor/puml/`へ再移動、所有権の原則を確立 |
| [19](19_orchestrator_demo_class_removal.md) | orchestrator_demo_class_removal | デモ用`Orchestrator`削除、`check_status`アクションへ機能移植 |

## 補足：後から訂正・上書きされた記録

決定は書き換えないが、後から誤りに気づいた場合や方針が変わった場合は、該当ファイルへ日付付きで追記している。最終的な状態を知りたい場合は以下に注意：

- **[01](01_import_resolution_rules.md)・[02](02_root_pyproject_settings.md)**：「workspace memberに登録するだけで自動インストールされる」という当初の誤りを追記で訂正（`normalizer`が実際にはインストールされていなかった件）
- **[04](04_urgent_fix_camera_pipeline.md)**：本物の`CameraController`実装に合わせた追加修正を追記（詳細は[03](03_package_settings_adapter_orchestrator.md)参照）
- **[06](06_workflow_yaml_usage.md)**：`steps`形式の追加（6節）、`params`二重役割の解消（7節、[known_issues.md](../known_issues.md) No.1対応）を追記
- **[07](07_folder_structure_cleanup.md)**：`Readme.md`→`README.md`リネームが別リポジトリ（`usb_camera_adapter`）に伝播していなかった件を追記
- **[16](16_normalizer_puml_folder.md) → [18](18_scenario_puml_ownership.md)**：`scenario.puml`の置き場所は`normalizer/puml/`→さらに`testexecutor/puml/`へ再移動。16は経緯として残しているが、最終状態は18を参照すること
