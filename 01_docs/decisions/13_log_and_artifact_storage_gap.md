# 13_log_and_artifact_storage_gap

- 日付: 2026-08-22
- 関連: [12_essential_gaps_found.md](12_essential_gaps_found.md)（前回の必須課題棚卸し）
- ステータス: 完了（実機で確認済み）

## 背景

`run_scenario.py`を実機で動かして確認した際、「撮影」アクションを実行しているのに、撮影した画像がファイルとして保存されないことに気づいた。ログも標準出力のみで、実行後に何も残らない。[12](12_essential_gaps_found.md)と同種の「動くはずのことが実は動いていない」欠陥として追加で記録する。

## 見つかった課題

### 1. 撮影した画像が保存されていない

`CameraAdapter.execute_step("capture", ...)`は`camera_controller.capture()`のみ呼んでおり、`camera_controller.save_capture()`/`save_roi_capture()`を呼んでいない。撮影したframeは`Context.history`にオブジェクトとして残るだけで、プロセス終了と同時に消える。「撮影する」という名前のアクションの成果物が、実際には何も残らない状態。

`save_capture()`自体は実装済み（`adapters/usb_camera_adapter/img/`に固定ファイル名`capture.png`で保存）だが、実行パイプラインからは呼ばれていない。

### 2. ログの永続化ポリシーが無い

`loguru`は標準出力にのみ出力しており、ファイルへの書き出し設定が無い。実行を終えると、何を検査してどうなったかの記録が一切残らない。

## 未確定（仕様として決めること）

| # | 論点 |
|---|---|
| 1 | 成果物（画像）の保存先：`adapters/usb_camera_adapter/img/`固定のままでよいか、実行ごとに分けるか |
| 2 | 成果物のファイル名：固定名（上書きされる）か、実行日時等を含めて残すか |
| 3 | どのタイミングで保存するか：`execute_step`内で自動保存するか、呼び出し側（`run_scenario.py`等）が明示的に指示するか |
| 4 | ログの保存先：ファイルに書き出すか、標準出力のみで良しとするか |
| 5 | ログを書き出す場合のローテーション・保持期間 |

## 決定した仕様

| # | 論点 | 決定 |
|---|---|---|
| 1 | 成果物の保存先 | `adapters/usb_camera_adapter/img/`のまま（変更なし） |
| 2 | 成果物のファイル名 | 実行ごとにタイムスタンプ付き（`capture_20260822_155955_199.png`、ミリ秒まで含め同一実行内の衝突も回避） |
| 3 | 保存タイミング | `CameraAdapter.execute_step("capture")`内で自動保存（呼び出し側の指示不要） |
| 4 | ログの保存先 | `logs/run_YYYYMMDD_HHMMSS.log`にファイルへも書き出す（標準出力はそのまま維持、追加のsink） |
| 5 | ローテーション | 今回は未対応（都度新規ファイルが増えていく。必要になったら`logger.add(..., retention=...)`等で対応） |

## 実装内容

- `CameraControllerInterface.save_capture`：戻り値を`None`→`Path | None`に変更（保存先パスを返す）
- `CameraController.save_capture`/`save_roi_capture`：`frame is None`時に処理を続行してしまう既存バグを修正（早期return追加）。`_make_img_path`にミリ秒精度のタイムスタンプを追加
- `CameraMockController.save_capture`（Fake）：契約に合わせて`Path | None`を返すよう変更（実際の保存はしない、Liskov置換を維持）
- `CameraAdapter.execute_step("capture")`：撮影後に`save_capture()`を呼び、結果dictに`saved_path`を追加
- `run_scenario.py`：`_setup_file_logging()`でタイムスタンプ付きログファイルを`logs/`に出力
- `.gitignore`（ルート）に`logs/`を追加

## 確認

実機で`run_scenario.py`を実行し、以下を確認：
- `img/capture_20260822_155955_199.png`が生成される
- `logs/run_20260822_155922.log`が生成され、日本語も文字化けせず記録される（コンソール表示の文字化けはWindowsターミナルの表示上の問題で、ファイルには影響しない）
- 実行結果に`saved_path`として実際の保存先パスが入る

`uv run pytest -m "not hardware" -q` → `40 passed, 3 deselected`（退行なし）
