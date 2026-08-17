# 01_import_resolution_rules

- 日付: 2026-08-12
- 関連: [04_urgent_fix_camera_pipeline.md](04_urgent_fix_camera_pipeline.md)（この理解のきっかけになった一連の修正）
- 位置づけ: プロジェクト全体に共通する「importがなぜ解決できるのか」のルール集。個別パッケージの設定は[02](02_root_pyproject_settings.md)・[03](03_package_settings_adapter_orchestrator.md)を参照。

## 背景

`workflow.yaml` -> `GenericOrchestrator` -> `CameraAdapter`の緊急修正（[04](04_urgent_fix_camera_pipeline.md)）を進める中で、同じプロジェクト内に複数のimportの書き方（長い形式・短い形式・第三の形式）が混在していることが分かった。なぜ特定の書き方だけが動き、他は動かないのかを整理する必要があった。

## 三層構造：このプロジェクトでimportが解決される3つのゾーン

| ゾーン | 該当箇所 | 解決の仕組み | 有効範囲 |
|---|---|---|---|
| **本番コード**（`pyproject.toml`の`packages`に宣言あり） | `camera_adapter`, `camera_controller`, `interfaces`, `adapter_core`, `orchestrator` | `uv sync`でワークスペース全体が**1つの共有`.venv`**にeditableインストールされる | リポジトリ内どこからでもimport可能 |
| **テスト専用コード**（`tests/`配下、`packages`宣言なし） | `test_support` | pytestの標準動作（prependモード）が、テストファイルの属するディレクトリをsys.pathに挿入する | **そのtests/ディレクトリ内のみ**有効。他のtests/からは見えない |
| **設定・データ** | `normalizer/config/workflow.yaml` | Pythonパッケージではない。`open()`で読むファイル | import経路と無関係 |

## ルール1：1つのワークスペース＝1つの共有venv

`[tool.uv.workspace]`に登録された全メンバー（`orchestrator`, `adapters/usb_camera_adapter`, `adapters/core`）は、`uv sync`実行時に**1つの`.venv`**へまとめてeditableインストールされる。これは実際に`adapters/core`を`members`に追加しただけで（rootの`dependencies`には未追加のまま）`uv sync`のログに

```
+ adapter-core==0.1.0 (from file:///.../adapters/core)
```

と表示され、自動でインストールされたことで確認済み。

**帰結**：ワークスペース内のどのパッケージも、他のワークスペースメンバーが「たまたま」インストールされていれば、自分の`dependencies`に書いていなくてもimportできてしまう。これが「動く」ことと「正しく宣言されている」ことが乖離する根本原因。

## ルール2：「動く」≠「正しく依存が宣言されている」

[04](04_urgent_fix_camera_pipeline.md)で見つかった項目3・4はこの典型例：
- `orchestrator`が`camera_adapter`をimportしているのに、`orchestrator/pyproject.toml`の`dependencies`に`usb-camera-adapter`が無かった
- それでも動いていたのは、rootの`dependencies`に`usb-camera-adapter`が直接書かれていて、共有venvに結局入っていたから

**判断基準**：「今動くか」ではなく「そのパッケージ単体を取り出しても動くように、依存が過不足なく宣言されているか」を基準にする。

## ルール3：import名の書き方は3種類あったが、短い形式に統一する

| 形式 | 例 | 成立条件 | 採用状況 |
|---|---|---|---|
| 短い形式（採用） | `camera_adapter.camera_adapter.CameraAdapter` | `pyproject.toml`の`packages`にそのサブフォルダ名が宣言されている | ✅ 全パッケージで統一済み |
| 長い形式（廃止） | `adapters.usb_camera_adapter.src.camera_adapter.camera_adapter.CameraAdapter` | リポジトリのディレクトリ構造をそのまま辿る。`__init__.py`が全階層に無くても名前空間パッケージとして偶然通ることがあった | ❌ `workflow.yaml`・`test_dynamic_import.py`から除去済み |
| 第三の形式（廃止） | `from adapters.baseadapter import BaseAdapter` | リポジトリルートがsys.pathに乗っている前提の中途半端な形式 | ❌ `adapter_core.baseadapter`への切り出しで解消（[03](03_package_settings_adapter_orchestrator.md)参照） |

短い形式を正とした理由：`pyproject.toml`の`[tool.hatch.build.targets.wheel] packages`設定と一致しており、既存コードの大多数もこれに従っていたため。

## ルール4：pytestは無設定（デフォルトのprependモード）で動いている

プロジェクト内に`pytest.ini`も`[tool.pytest.ini_options]`も一切存在しない。つまり全て**pytestのデフォルト動作**だけで解決されている。

- pytestの実行は、テストファイルを集めたディレクトリごとに独立した「rootdir」を持つ
- テストファイルの置かれたディレクトリに`__init__.py`が無ければ、pytestは**そのディレクトリ自体をsys.pathの先頭に挿入する**（prependモード）
- これにより`adapters/usb_camera_adapter/tests/test_camera_adapter.py`が集められると、`tests/`がsys.pathに追加され、`tests/test_support/camera_mock_controller.py`が`test_support.camera_mock_controller`として解決できる
- この効果は**そのテスト実行の間・そのディレクトリ構成だからこそ**成立するローカルなルールで、共有venv全体には一切影響しない（`integrationtest/`から`test_support`はimportできない）

## 運用ルール（今後もこれに従う）

1. 本番コードにしたいものは`pyproject.toml`の`packages`に追加し、依存する側の`dependencies`にも明示する
2. テスト専用にしたいものは`tests/`配下に置くだけでよい（`packages`宣言も追加設定も不要）。これにより配布物に混ざらない
3. 新しいimportを書くときは「短い形式（サブフォルダ名.モジュール名）」に統一する
4. 「動くかどうか」ではなく「依存が明示されているか」を判断基準にする
