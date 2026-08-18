# 03_package_settings_adapter_orchestrator

- 日付: 2026-08-12
- 関連: [01_import_resolution_rules.md](01_import_resolution_rules.md)・[02_root_pyproject_settings.md](02_root_pyproject_settings.md)
- 位置づけ: root以外の構成要素（`orchestrator`・`adapters/usb_camera_adapter`・`adapters/core`）それぞれの設定・依存関係・作業中に決めたルールをまとめる。

## 全体依存関係グラフ

（2026-08-17更新：`normalizer`を追加）

```
                    scenario_test (root)
                 /         |            \
          orchestrator  normalizer   usb-camera-adapter
                  \                    /
                   \                  /
                    adapter-core（末端・誰にも依存しない）
```

非循環（acyclic）な階層構造。`adapter-core`が一番下の共通基盤で、`orchestrator`と`usb-camera-adapter`の両方がそこへ向かって依存する。`normalizer`は現時点でどのワークスペースメンバーにも依存しない独立した葉（`adapter-core`にも依存しない）。

| パッケージ | 直接依存（外部） | 直接依存（内部・workspace） | 役割 |
|---|---|---|---|
| `orchestrator` | loguru, pyyaml（dev: pytest） | usb-camera-adapter, adapter-core | シナリオ実行エンジン |
| `usb-camera-adapter`（別git管理） | loguru, numpy, opencv-python（dev: pytest） | adapter-core | USBカメラの実機I/O実装 |
| `adapter-core` | loguru | なし（末端） | 全アダプタ共通の抽象基盤（`BaseAdapter`） |
| `normalizer` | pyyaml（dev: pytest） | なし | PlantUML→pipeline変換（[08](08_plantuml_conversion_design_policy.md)） |

### なぜ`orchestrator`は2つも内部依存を持つのか

`orchestrator/src/orchestrator/orchestrator.py`には性格の違う2つのクラスが同居している。
- **`GenericOrchestrator`**：`adapter-core`の`BaseAdapter`（＝契約・抽象）としか会話しない。`workflow.yaml`のクラスパス文字列を実行時に`importlib`で動的ロードするので、コード上は`usb-camera-adapter`を一切importしない。依存の理由は`adapter-core`だけで説明できる。
- **`Orchestrator`**（デモ用の具体クラス）：`__init__`内で`from camera_adapter.camera_adapter import CameraAdapter`と、`CameraAdapter`を名指しでハードコードしている。これが`usb-camera-adapter`への依存が必要な理由。

「抽象にしか依存しない設計」と「具体に直接依存する設計」が同じファイルに同居しているため、パッケージ全体としては両方を`dependencies`に書く必要がある。

## Adapter/Controllerは別パッケージではない

`CameraController`は独立した`pyproject.toml`を持たない。`usb-camera-adapter`という1つの配布物（1つのpyproject.toml）の中に、`camera_adapter`・`camera_controller`・`interfaces`という3つの独立したimport可能サブパッケージが同居している。

```
usb-camera-adapter（1つのpyproject.toml = 1つの配布単位）
 ├─ camera_adapter    （importable package）
 ├─ camera_controller （importable package）
 └─ interfaces        （importable package）
```

「Adapter/Controllerという設計上の役割分担」と「pyproject.tomlという配布単位の境界」は別の軸。両方が常にセットで使われる（`CameraAdapter`は`CameraController`なしに存在意義がない）ため、同じ配布単位にまとめている。将来「同じControllerを複数の違うAdapterから使い回したい」というニーズが出てきたら、そのとき初めて分離を検討すればよい。

## `orchestrator/pyproject.toml`

（2026-08-17更新：`pytest`を`dependency-groups.dev`へ分離した後の状態）

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "orchestrator"
version = "0.1.0"
requires-python = "~=3.11.0"
dependencies = [
    "loguru>=0.7.3",
    "pyyaml>=6.0.3",
    "usb-camera-adapter",
    "adapter-core",
]

[dependency-groups]
dev = [
    "pytest>=9.1.1",
]

[tool.hatch.build.targets.wheel]
packages = ["src/orchestrator"]

[tool.uv.sources]
usb-camera-adapter = { workspace = true }
adapter-core = { workspace = true }
```

| セクション | 必須／任意 | 意味 |
|---|---|---|
| `[build-system]` | 必須 | 無いとuvが「パッケージではなくアプリ」と推論してしまう |
| `[project] name` | 必須 | 他パッケージから`dependencies`/`sources`で参照される名前 |
| `requires-python` | 任意（推奨） | `~=3.11.0`＝3.11.x限定 |
| `dependencies` | 必須 | 直接importする5つを過不足なく列挙 |
| `[tool.hatch.build.targets.wheel] packages` | 必須 | どのフォルダを配布物として含めるか＝import名の正体 |
| `[tool.uv.sources]` | ローカル依存がある時だけ必須 | `usb-camera-adapter`/`adapter-core`はPyPIに無い名前なので、workspaceから取得することを明示 |

### 決定：`packages = ["src"]` → `["src/orchestrator"]`への変更

**背景**：当初`packages = ["src"]`となっており、import名が文字通り`src`になっていた（`from src.orchestrator import Orchestrator`）。これは他パッケージの「サブフォルダ名がそのままimport名になる」規約と異なる、4つ目の矛盾した書き方だった。

**問題点**：`src`という名前は一般的すぎる。将来、別の単一モジュールパッケージも`packages=["src"]`を採用すると、2つのパッケージが同じ`src`という名前を主張し合い衝突する。

**決定**：`orchestrator/src/orchestrator.py` → `orchestrator/src/orchestrator/orchestrator.py`に変更し、`packages = ["src/orchestrator"]`とした。import文は`from orchestrator.orchestrator import Orchestrator`に統一（`test_orchestrator.py`, `integrationtest/test_integration.py`, `orchestrator/main.py`の3箇所を修正）。これで全パッケージが「サブフォルダ名＝import名」の同じ規約に揃った。

## `adapters/usb_camera_adapter/pyproject.toml`

（2026-08-17更新：`pytest`を`dependency-groups.dev`へ分離した後の状態）

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "usb-camera-adapter"
version = "0.1.0"
requires-python = "~=3.11.0"
dependencies = [
    "loguru>=0.7.3",
    "numpy>=2.4.6",
    "opencv-python>=5.0.0.93",
    "adapter-core",
]

[dependency-groups]
dev = [
    "pytest>=9.1.1",
]

[tool.hatch.build.targets.wheel]
packages = ["src/camera_adapter", "src/camera_controller", "src/interfaces"]

[tool.uv.sources]
adapter-core = { workspace = true }
```

`orchestrator`との違いは2点。`packages`に3つ列挙している点（Adapter/Controller/Interfaceをまとめて面倒を見ている）と、`[tool.uv.sources]`が`adapter-core`だけである点（`usb-camera-adapter`は`orchestrator`に依存していない＝依存が一方向で循環していないことの裏付け）。

### 決定：`interfaces.py`と`test_support/`を`packages`に追加

**背景**：`interfaces.py`（`from interfaces import ...`）と`test_support/`（`from test_support.camera_mock_controller import ...`）が当初`packages`に含まれておらず、正式ビルド時に`ModuleNotFoundError`になる恐れがあった。

**`interfaces.py`への対応**：`src/interfaces.py`（単一ファイル）を`src/interfaces/__init__.py`（フォルダ＋`__init__.py`）に変換し、`packages`に`"src/interfaces"`を追加。既存の`from interfaces import CameraControllerInterface`はそのまま動く。

**`test_support/`への対応**：packagesに加える案ではなく、**`src/test_support/` → `tests/test_support/`へ移動**する方を最終的に採用（詳細は次項）。

### 決定：`test_support/`は`src/`ではなく`tests/`に置く

**検討した選択肢**：
- 案A：`test_support`も`packages`に加えて配布物に含める（一時的にこれで運用）
- 案B：`tests/`配下に移動し、`packages`から外す（**採用**）

**採用理由**：`test_support`はテスト専用のFake（`CameraMockController`）であり、本番の配布物（wheel）に混ぜるべきではない。`tests/`配下に`__init__.py`の無い状態で置けば、pytestの標準動作（[01](01_import_resolution_rules.md)ルール4のprependモード）だけで`from test_support.camera_mock_controller import ...`が**コード変更なしに**解決される。設定追加も不要で、本番コードとテスト専用コードの境界が物理的な置き場所だけで表現できる。

### 決定：`interfaces.py`のシグネチャを「本物」に合わせる

**背景**：`interfaces.py`の`save_capture`/`is_led_on`が引数なしで宣言されていたが、実装（`CameraController`）は`frame`や`roi, threshold`を必須要求していた。さらに調べると`CameraMockController.save_capture`も引数なしで、**実装同士も食い違っていた**（Fakeがinterfaceに合わせてしまっていた）。

**決定**：`CameraController`（本物）を正とし、`interfaces.py`と`CameraMockController`の両方をそれに合わせた。

```python
# interfaces.py
@abstractmethod
def save_capture(self, frame) -> None: ...
@abstractmethod
def is_led_on(self, roi: tuple[int, int, int, int], threshold: int) -> bool: ...
```

**理由**：interfaceは「本番でどう振る舞うべきか」の契約であるべきで、Fakeは本番の代役である以上、Fakeの都合でinterfaceを緩めるのは本末転倒。本物とinterfaceを合わせた上で、Fake側をinterfaceに追従させることで、Liskov置換（Fakeは本物の代わりに使えて当然）を保った。

## `adapters/core/pyproject.toml`（一番シンプルな例）

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "adapter-core"
version = "0.1.0"
requires-python = "~=3.11.0"
dependencies = [
    "loguru>=0.7.3",
]

[tool.hatch.build.targets.wheel]
packages = ["src/adapter_core"]
```

`[tool.uv.sources]`が無い。`adapter-core`は他のどのローカルパッケージにも依存していない「末端」だから。**`[tool.uv.sources]`はローカルのworkspaceメンバーに依存する時だけ書けばよい**、という一番分かりやすい実例。

## `normalizer/pyproject.toml`（もう1つの葉。ただし外部依存が1つある例）

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "normalizer"
version = "0.1.0"
requires-python = "~=3.11.0"
dependencies = [
    "pyyaml>=6.0.3",
]

[dependency-groups]
dev = [
    "pytest>=9.1.1",
]

[tool.hatch.build.targets.wheel]
packages = ["src/normalizer"]
```

`adapter-core`と同じく「末端」（`[tool.uv.sources]`が不要）だが、`adapter-core`が`loguru`のみだったのに対し、`normalizer`は`config/mapping.yaml`を読むために`pyyaml`が要る点が違う。**重要な注意点**：`members`に登録しただけではrootの`dependencies`に依存として現れないため共有venvにインストールされない（[01](01_import_resolution_rules.md)の訂正、[02](02_root_pyproject_settings.md)参照）。`normalizer`はrootの`[project] dependencies`にも明示的に追加している。

### 決定：`BaseAdapter`を`adapters/baseadapter.py`から独立パッケージへ切り出し

**背景**：`from adapters.baseadapter import BaseAdapter`という書き方は、リポジトリルートがsys.pathに乗っているときだけ成立する「第三の形式」だった（[01](01_import_resolution_rules.md)参照）。`usb_camera_adapter`は独立git管理のリポジトリなのに、その中身（`camera_adapter.py`）がリポジトリの物理的な置き場所（scenario_testルート直下に`adapters/baseadapter.py`がある前提）に暗黙に依存しており、切り出し元の事情を引きずっていた。

**決定**：`BaseAdapter`を`adapters/core/`という新しいワークスペースメンバーに切り出し、`orchestrator`・`usb-camera-adapter`の両方から正式な依存として参照する形にした（`adapters/baseadapter.py`・`adapters/__init__.py`は削除。`adapters/`は現在、サブパッケージを格納するだけのフォルダ）。

**配布範囲についての判断**：`adapter-core`は今のところモノレポ内にしか存在しない（独立git管理ではない）。`usb-camera-adapter`を本当に別プロジェクトへ持ち出すには`adapter-core`も別途配布可能にする必要が残るが、**現時点では外部で使う予定がないため、モノレポ内で十分**と判断（必要になったタイミングで切り出す）。

## `integrationtest/`の扱いと運用方針

ルート直下の独立したpytestルート。どのワークスペースメンバーの`tests/`にも属さない。`orchestrator/tests`や`adapters/usb_camera_adapter/tests`が「そのパッケージ単体をFake/Mockで検証する」場所なのに対し、`integrationtest/`は**パッケージ境界をまたいで組み合わせて検証する**場所という役割分担。

**課題**：`test_integration.py`・`test_dynamic_import.py`はどちらも実機のUSBカメラが無いと正しく検証できないが、それを区別する仕組み（`pytest.mark`やマーカー登録）が無い。

**推奨する対応（未適用）**：

```toml
# ルートpyproject.tomlに追加する案
[tool.pytest.ini_options]
markers = [
    "hardware: 実機USBカメラが必要なテスト",
]
```

```python
@pytest.mark.hardware
def test_dynamic_import_camera_adapter():
    ...
```

これにより`pytest -m "not hardware"`で通常のFakeベーステストだけを実行し、`pytest -m hardware`で実機確認を明示的に分離できる。`integrationtest/`の置き場所自体（ルート直下）は適切なので、移動は不要。

## Fake（test_support相当）置き場の今後の方針

将来LED/Fileアダプタ等でもFakeが必要になったとき、**パッケージごとに個別配置する**方針とした（`usb_camera_adapter/tests/test_support/`と同じパターンを複製する）。共通のテストユーティリティパッケージ化は、実際に2つ以上のパッケージで同じFakeが必要になったタイミングで再検討する。
