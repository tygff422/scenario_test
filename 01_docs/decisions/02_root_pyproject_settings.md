# 02_root_pyproject_settings

- 日付: 2026-08-12
- 関連: [01_import_resolution_rules.md](01_import_resolution_rules.md)（前提となる全体ルール）
- 位置づけ: リポジトリルート（`scenario_test/pyproject.toml`）の設定を1行ずつ解説する。

## 現在の内容

（2026-08-17更新：`pytest`を`dependency-groups.dev`へ分離、`normalizer`を追加した後の状態）

```toml
[project]
name = "scenario-test"
version = "0.1.0"
requires-python = "~=3.11.0"
dependencies = [
    "orchestrator",
    "usb-camera-adapter",
    "normalizer",
]

[dependency-groups]
dev = [
    "pytest>=9.1.1",
]

[tool.uv]
package = false

[tool.uv.workspace]
members = [
    "orchestrator",
    "adapters/usb_camera_adapter",
    "adapters/core",
    "normalizer",
]

[tool.uv.sources]
orchestrator = { workspace = true }
usb-camera-adapter = { workspace = true }
normalizer = { workspace = true }
```

`pytest`は本番`dependencies`ではなく開発用の`[dependency-groups] dev`に分離した（本番の配布物には不要な、開発時にしか使わない依存のため）。

## `[project] dependencies` ── 直接依存だけを書く、が実は「共有venvに入るかどうか」も左右する

PEP 621標準のフィールド。「このプロジェクトのコードが直接importするもの」だけを書く。間接依存（依存の依存）は書かない。ここに書かれた3つは、`integrationtest/`や各パッケージのコードが直接触るもの。

**書かないとどうなるか**：ここが当初の理解と違っていたので訂正する（[01](01_import_resolution_rules.md)の追記も参照）。「ワークスペースメンバーに登録さえすれば自動的に共有venvへインストールされる」というのは誤りで、**実際には root から辿れる依存関係のどこかにそのパッケージ名が現れて初めてインストールされる**。

- `adapter-core`がrootの`dependencies`に無くても動いていたのは、`orchestrator`・`usb-camera-adapter`側の`dependencies`に`adapter-core`が書かれていて、それをrootが依存しているために**間接的に**入ってきていたから
- `normalizer`を`[tool.uv.workspace] members`にだけ追加してrootの`dependencies`には追加し忘れた際、実際に`uv sync`しても`.venv`にインストールされず、`import normalizer`が名前空間パッケージ扱いになって`ModuleNotFoundError`相当の壊れ方をした（2026-08-17に実際に遭遇）

**結論**：rootが直接使わないもの（`adapter-core`）は書かなくてよいが、それは「他の誰かがそれに依存しているから間接的に入る」場合に限る。**どこからも依存されないパッケージは、たとえworkspace membersに登録しても、明示的にどこかのdependenciesへ加えない限りインストールされない**。

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
- 全メンバーの依存関係が1つの`uv.lock`にまとめて解決される（＝ビルド対象・解決対象として認識される）
- 他のメンバーから`{ workspace = true }`で参照できるようになる
- **ただし共有`.venv`へ実際にeditableインストールされるのは、root（または他のメンバー）の`dependencies`から辿れるパッケージだけ**。`members`への登録は「参照可能にする」ことと「ビルド解決の対象にする」ことまでしかせず、「実際にインストールする」のは別の話（上の`[project] dependencies`の節を参照）。`normalizer`をこの節にだけ追加してインストールされなかった件が実例

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
