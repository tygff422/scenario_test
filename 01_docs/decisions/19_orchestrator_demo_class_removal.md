# 19_orchestrator_demo_class_removal

- 日付: 2026-09-01
- 関連: [known_issues.md](../known_issues.md)（No.7・No.10）・[12_essential_gaps_found.md](12_essential_gaps_found.md)（`Orchestrator`が「本線とは別経路」と判明した経緯）・[03_package_settings_adapter_orchestrator.md](03_package_settings_adapter_orchestrator.md)（`orchestrator`の依存関係）
- ステータス: 完了（実機確認済み）

## 背景

`orchestrator/src/orchestrator/orchestrator.py`には性格の異なる2クラスが同居していた：

- `Orchestrator`（デモ用）：`CameraAdapter`を名指しでハードコードし、`check_device_status()`（LED点灯確認）を1回呼ぶだけの最小実装。sync。
- `GenericOrchestrator`（本線）：`BaseAdapter`（抽象）としか会話せず、YAML/pipelineから動的importで任意のAdapterを実行する汎用エンジン。async。

`orchestrator/README.md`には元々「`Orchestrator`（デモ用の具体クラス）」と明記されており、[12_essential_gaps_found.md](12_essential_gaps_found.md)でも「`orchestrator/main.py`はデモ用`Orchestrator`を動かすだけの別経路」と位置づけられていた。`testexecutor/run_scenario.py`（正規の実行入口）が確立した今、`Orchestrator`は本線と並存する重複クラスとして[known_issues.md](../known_issues.md) No.7に挙げられていた。

## 検討した論点

素朴に「デモ用だから消す」と決める前に、「`Orchestrator`と`GenericOrchestrator`は本当に重複なのか、単に役割が違うだけではないか」を確認した。結論：

- `Orchestrator.execute()`が呼ぶ`check_device_status()`（LED点灯確認、`CameraController.is_led_on()`によるROI画像の明るさ判定）は、当時`CameraAdapter.execute_step()`では`"capture"`アクションしか対応しておらず、`GenericOrchestrator`経由では到達できない機能だった。
- そのため単純比較では「役割が違う」ように見えるが、これは`Orchestrator`という別クラスが本質的に必要なのではなく、**`execute_step()`に`check_status`アクションが配線されていなかっただけ**、という機能ギャップだと判断した。
- 副次的に、`orchestrator/pyproject.toml`が`usb-camera-adapter`（具体パッケージ）に依存していたのも、`Orchestrator`が`CameraAdapter`を直接importしていたことが原因と判明。`GenericOrchestrator`自体は`adapter-core`（`BaseAdapter`）としか会話しないため、本来この依存は不要だった。

## 決定・対応内容

1. **機能を先に移植**：`CameraAdapter.execute_step()`に`action == "check_status"`を追加し、`check_device_status()`を呼べるようにした（`adapters/usb_camera_adapter/src/camera_adapter/camera_adapter.py`）
2. **`Orchestrator`クラスを削除**：`orchestrator/src/orchestrator/orchestrator.py`から`Orchestrator`を削除し、`GenericOrchestrator`のみを残した
3. **`orchestrator/main.py`を削除**：`Orchestrator`専用の実行スクリプトのため不要に
4. **`orchestrator/tests/test_orchestrator.py`を削除**：`Orchestrator`をMagicMockで検証していた3テスト
5. **`integrationtest/test_integration.py`を更新**：
   - `test_workspace_import`：`Orchestrator`ではなく`GenericOrchestrator`のインスタンス化を検証する形に変更（workspace importの健全性確認という目的自体は維持）
   - `test_orchestrator_adapter_controller`（`Orchestrator`のLED確認を実機検証）を削除し、代わりに`test_generic_orchestrator_check_status_with_real_camera_adapter`を新設：`GenericOrchestrator`経由で`check_status`アクションを実機検証する（LED確認機能の実機カバレッジ自体は失っていない）
6. **`orchestrator/pyproject.toml`から`usb-camera-adapter`依存を削除**：`orchestrator`パッケージが名実ともに`adapter-core`（抽象）のみに依存する形になった
7. **`orchestrator/README.md`を更新**：`Orchestrator`セクションを削除し、依存関係の記載を修正

## 保留にしたこと（[known_issues.md](../known_issues.md) No.10）

`CameraAdapter`には`execute_step()`経由のAPIとは別に、`open()`/`release()`/`is_opened()`/`capture()`/`is_led_on()`等の直接メソッド群が今も残っている（`adapters/usb_camera_adapter/tests/test_camera_adapter.py`が単体テストとして使用中）。今回`Orchestrator`という「利用者の1つ」は無くなったが、この直接メソッド群自体の整理（削除するか、テストの書き方ごと見直すか）は範囲外とし、No.10として引き続き保留。

## 確認

- `uv sync`：`orchestrator`パッケージが`usb-camera-adapter`無しで再ビルドされることを確認
- `uv run pytest -m "not hardware" -q` → `38 passed, 3 deselected`（`test_orchestrator.py`の3件削除分を除き退行なし）
- `uv run pytest -m hardware -q` → `3 passed`（`test_generic_orchestrator_check_status_with_real_camera_adapter`含め実機で全件成功）
