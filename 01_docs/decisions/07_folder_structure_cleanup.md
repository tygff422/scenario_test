# 07_folder_structure_cleanup

- 日付: 2026-08-13
- 関連Step: implementation_planの「現時点で残っている未完了タスク」（設計自体ではなく構成の掃除）
- ステータス: 完了

## 背景

全体のフォルダ構成を棚卸しし、これまでの決定（[01](01_import_resolution_rules.md)〜[06](06_workflow_yaml_usage.md)）と実際の状態にズレが無いかを確認した。見つかった6件はいずれも「動作には影響しないが放置すると混乱の元になる」類のもので、全て修正した。

## 修正した項目

### 1. `orchestrator/.python-version`が`3.13`になっていた

他の2箇所（ルート・`usb_camera_adapter`）は`3.11.4`、全`pyproject.toml`も`requires-python = "~=3.11.0"`で統一されているのに、ここだけ`uv init`直後の初期値が残っていたと思われる。**`3.11.4`に統一**。

### 2. ルート直下の`main.py`が未使用の`uv init`雛形のまま残っていた

`print("Hello from scenario-test!")`だけの中身で、`[project.scripts]`等どこからも参照されておらず、ルート`pyproject.toml`は`[tool.uv] package = false`（アプリ扱い・配布物ではない）。実際の実行入口は`orchestrator/main.py`であり、同名ファイルが2つ存在することで紛らわしかったため**削除**。ルートから直接実行したい入口が今後必要になれば、その時点で改めて作る。

### 3. 古いegg-infoビルド成果物が2つ残っていた

`adapters/usb_camera_adapter/src/`に`usb_camera_adapter.egg-info`と`usb_camera_controller.egg-info`の2つが存在していた。後者は現行の`pyproject.toml`（`name = "usb-camera-adapter"`という1パッケージのみ）には対応しない名前で、`camera_controller`がまだ独立パッケージだった頃の名残と推測される。中身も`Requires-Python: >=3.13`と、現行の`~=3.11.0`と食い違う古い状態のままだった。`*.egg-info`は`.gitignore`済みで再生成可能な成果物のため、両方とも**削除**。

### 4. `adapters/core/`だけ`.python-version`が無かった

他の2ワークスペースメンバーに合わせて`3.11.4`で**新規作成**。

### 5. `orchestrator/.gitignore`がルートの`.gitignore`とほぼ重複していた

内容は`img/`の行が無いだけで他はルートと同一。ルートの`.gitignore`は全ワークスペースへ再帰適用されるため実質不要な二重管理だった。**削除**。

### 6. `adapters/usb_camera_adapter/Readme.md`だけ表記が違った

ルート・`orchestrator/`は`README.md`（大文字）に対しここだけ`Readme.md`。**`README.md`にリネーム**（Windowsの大文字小文字を区別しないファイルシステム対策として、一旦別名を経由する2段階リネームで実施）。

## 確認

- `uv sync` → 成功（`.python-version`変更後も解決に問題なし）
- `uv run pytest -m "not hardware" -q` → `14 passed, 2 deselected`（修正前と同じ結果、退行なし）

## 対象外とした項目（意図的に残したもの）

- `adapters/usb_camera_adapter/img/`：実行時に生成されるカメラ撮影画像。`.gitignore`済みで想定通りの挙動（[03](03_package_settings_adapter_orchestrator.md)参照）
- `normalizer/`が現状`config/workflow.yaml`しか持たない点：Phase6/9（PlantUML→DSL変換、`normalizer.py`本体）が未着手なための想定内の状態（[implementation_plan.md](../implementation_plan.md)参照）
