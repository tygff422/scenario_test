# 14_testexecutor_folder

- 日付: 2026-08-22
- 関連: [12_essential_gaps_found.md](12_essential_gaps_found.md)（run_scenario.py作成）・[13_log_and_artifact_storage_gap.md](13_log_and_artifact_storage_gap.md)（ログ・成果物の永続化仕様）
- ステータス: 完了（実機で確認済み）

## 背景

実行ファイル（`run_scenario.py`）・ログ出力先（`logs/`）・成果物出力先（`img/`）がそれぞれ別々の場所に散らばっていた（ルート直下、`adapters/usb_camera_adapter/img/`）。この3つを1つの独立したフォルダにまとめたいという要望を受け、`scenario_test`直下に`testexecutor/`を新設した。

## 変更後の構成

```text
scenario_test/
  testexecutor/
    run_scenario.py   ← ルートから移動
    logs/              ← ルートのlogs/から移動
    img/               ← adapters/usb_camera_adapter/img/から移動（保存先を変更）
```

実行コマンドは`uv run python testexecutor/run_scenario.py`に変わった。

## 決定事項

### `testexecutor/`はパッケージ化しない

`pyproject.toml`は作らず、スクリプト＋生成物フォルダの単純な置き場とした。他のコードから`testexecutor`をimportする必要が無く、workspace memberに加える理由が無いため（[01](01_import_resolution_rules.md)・[02](02_root_pyproject_settings.md)の「membersに登録しただけでは自動インストールされない」を踏まえ、不要な登録を増やさない）。

### 画像保存先の変更：`CameraController`に`img_dir`を追加（後方互換）

保存処理の実体（`CameraController.save_capture`）は別リポジトリ`usb_camera_adapter`にあり、従来は自パッケージ内`img/`に決め打ちしていた。`scenario_test`側の都合（`testexecutor/img/`）をこのパッケージにハードコードすると、`usb_camera_adapter`単体としての再利用性を損なう。

```python
# camera_controller.py
def __init__(self, device_id: int = 0, img_dir: str | Path | None = None):
    ...
    self._img_dir = Path(img_dir) if img_dir is not None else None

def _make_img_path(self, img_name) -> Path:
    img_dir = self._img_dir or (Path(__file__).resolve().parent.parent.parent / "img")
    ...
```

`img_dir`未指定時は従来通りの動作（自パッケージ内`img/`）を維持し、`usb_camera_adapter`を単体で使う場合の後方互換性を保った。`CameraAdapter.__init__`は`config`から`img_dir`を読み取り、`CameraController`へ引き継ぐ。

### 出力先の指定は`run_scenario.py`側の責務

`mapping.yaml`には`testexecutor/img/`のような環境依存パスを書き込まない（[06](06_workflow_yaml_usage.md)・[08](08_plantuml_conversion_design_policy.md)の「normalizerは実行環境の詳細を知らない」という分離を維持するため）。代わりに`run_scenario.py`が、変換後の`pipeline`に対して`action == "capture"`のステップの`params`へ`img_dir`（`testexecutor/img/`の絶対パス）を実行直前に注入する（`_inject_img_dir()`）。

```python
def _inject_img_dir(pipeline: list[dict]) -> None:
    for step in pipeline:
        if step.get("action") == "capture":
            step.setdefault("params", {})["img_dir"] = str(IMG_DIR)
```

## 確認

実機で`uv run python testexecutor/run_scenario.py`を実行し、以下を確認：
- `testexecutor/img/capture_*.png`が生成される
- `testexecutor/logs/run_*.log`が生成される
- 旧保存先（`adapters/usb_camera_adapter/img/`）には新規ファイルが増えない

`uv run pytest -m "not hardware" -q` → `40 passed, 3 deselected`（退行なし）
