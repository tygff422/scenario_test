# 02_root_pyproject_settings

- 日付: 2026-08-12
- 関連: [01_import_resolution_rules.md](01_import_resolution_rules.md)（前提となる全体ルール）
- 位置づけ: リポジトリルート（`scenario_test/pyproject.toml`）の設定を1行ずつ解説する。

## 現在の内容

```toml
[project]
name = "scenario-test"
version = "0.1.0"
requires-python = "~=3.11.0"
dependencies = [
    "pytest>=9.1.1",
    "orchestrator",
    "usb-camera-adapter",
]

[tool.uv]
package = false

[tool.uv.workspace]
members = [
    "orchestrator",
    "adapters/usb_camera_adapter",
    "adapters/core",
]

[tool.uv.sources]
orchestrator = { workspace = true }
usb-camera-adapter = { workspace = true }
```

## `[project] dependencies` ── 直接依存だけを書く

PEP 621標準のフィールド。「このプロジェクトのコードが直接importするもの」だけを書く。間接依存（依存の依存）は書かない。ここに書かれた3つは、root直下の`main.py`や`integrationtest/`が直接触るもの。

**書かないとどうなるか**：[01](01_import_resolution_rules.md)のルール1の通り、ワークスペースメンバーである以上、rootの`dependencies`に書かなくても共有venvにはインストールされる（`adapter-core`はrootのdependenciesに無いが動いている、が実例）。ただし「rootのコードが直接使うもの」を明示するという metadata としての正しさは失われる。rootが直接使わないもの（`adapter-core`）は書かない、というのが今回の判断。

## `[tool.uv] package = false` ── 自分自身は配布物ではないという宣言

uvは`[build-system]`セクションの有無で、そのフォルダをパッケージとしてビルドすべきかを自動推論する：

```text
[build-system] がある  → デフォルトで package = true（パッケージとしてビルド・インストール）
[build-system] がない → デフォルトで package = false（ビルドしない）
```

root（`scenario_test`）には`[build-system]`が無い。デフォルトのままなら`package=false`相当になるはずだが、**明示的に書いている**のは「これは意図的な選択であり、書き忘れではない」ことをコードとして残すため。

**なぜfalseにしているか**：`scenario_test`は`main.py`を持つ「アプリの入り口・ワークスペースの取りまとめ役」であって、他プロジェクトから`pip install scenario-test`されることを想定した再利用可能なライブラリではない。`orchestrator`・`usb-camera-adapter`・`adapter-core`は「配布・再利用されうるライブラリ」、root（`scenario_test`）は「それらを束ねて動かすだけのアプリ」という役割の違いが表れている。

## `[tool.uv.workspace] members` ── ローカルの兄弟パッケージの登録簿

ここに書かれたパスは「独自の`pyproject.toml`を持つ、ワークスペース内のローカルパッケージ」として扱われる。これにより：
- 全メンバーの依存関係が1つの`uv.lock`にまとめて解決される
- 全メンバーが1つの共有`.venv`にeditableインストールされる
- 他のメンバーから`{ workspace = true }`で参照できるようになる

**加えないと何が困るか**：`adapters/core/pyproject.toml`を作っても`members`に追加し忘れると、`usb-camera-adapter`側の`[tool.uv.sources] adapter-core = { workspace = true }`が参照先を見つけられずエラーになる。「フォルダとして存在する」ことと「ワークスペースの一員として認識される」ことは別で、`members`への登録が両者を繋ぐ。

## `[tool.uv.sources] xxx = { workspace = true }` ── 取得元の上書き指定

`dependencies`に名前を書いただけでは、uvはデフォルトで**PyPI（公開パッケージ置き場）からその名前のパッケージを探す**。`orchestrator`や`usb-camera-adapter`という名前はPyPIには存在しないので、そのままでは解決に失敗する。

`{ workspace = true }`は「この名前の依存は、PyPIではなくこのワークスペースのメンバーから取得しろ」という指定。`dependencies`と`sources`は**セットで初めて意味を持つ**：

| 状態 | 結果 |
|---|---|
| `dependencies`のみ、`sources`なし | PyPIを探しに行って失敗する（存在しない名前のため） |
| `sources`のみ、`dependencies`なし | 何の効果も持たない死んだ記述になる（[04](04_urgent_fix_camera_pipeline.md)項目3・4で実際に発見した不具合の原因） |
| 両方揃っている | ワークスペース内のローカルパッケージとして正しく解決される |

## rootとその他のパッケージの非対称性まとめ

| | root（`scenario_test`） | `orchestrator`/`usb-camera-adapter`/`adapter-core` |
|---|---|---|
| `[build-system]` | 無し | あり（hatchling） |
| `package` | `false`（明示） | `true`相当（デフォルトのまま、書かない） |
| 役割 | アプリ・ワークスペースの取りまとめ | 配布・再利用可能なライブラリ |
| `dependencies`に書くもの | 自分が直接使うワークスペースメンバーのみ | 自分が直接importする全て（外部・内部問わず） |

個別パッケージ（`orchestrator`等）の設定詳細は[03_package_settings_adapter_orchestrator.md](03_package_settings_adapter_orchestrator.md)を参照。
