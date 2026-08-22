# 04_urgent_fix_camera_pipeline

- 日付: 2026-08-10
- 関連Step: Step0（緊急修正） / [implementation_plan.md](../implementation_plan.md)
- ステータス: 完了（1〜8すべて修正済み。8は[03_package_settings_adapter_orchestrator.md](03_package_settings_adapter_orchestrator.md)の作業で本物のCameraControllerに合わせて解消）

## 背景

`workflow.yaml` -> `GenericOrchestrator` -> `CameraAdapter` の経路が、Fakeを使った単体テストで一度も通されていなかった。そのため、実際にパイプラインを動かすと8件のバグが連鎖して発覚した。

## 見つかった問題と対応

### 1. `GenericOrchestrator.execute_pipeline`に`self`がない
- 症状: 呼び出した瞬間 `TypeError`
- 対応: **修正済み**。`def execute_pipeline(self) -> bool:` に修正（[orchestrator.py:55](../../orchestrator/src/orchestrator.py#L55)）

### 2. `workflow.yaml`のキー名とコードの読み取りキーが不一致
- 症状: `workflow.yaml`は`adapter:`、コードは`adapter_class`を読んでいて`None`になる
- 対応: **修正済み**。最終的に `adapter` に統一（`adapter_class`案も出したが、「`adapter`の方が自然」という判断で採用せず）。`workflow.yaml`のキー、`orchestrator.py`の`step_info.get("adapter")`、メソッド名`_load_adapter`をすべて`adapter`ベースで揃えた。

#### 検討した選択肢
- 案A: YAMLのキーを`adapter_class`に変更（値がクラスパス文字列であることを明示）
- 案B: YAMLのキーは`adapter`のまま、コード側を合わせる
- **採用: 案B**。理由: Phase9で`registry.py`によるアダプタ登録名という概念が入る可能性を見越して`adapter_class`を提案したが、現時点でその設計は存在せず、シンプルさを優先。将来登録名の概念が必要になった時点で改めてキー名を見直す。

### 3. クラスパスの書き方が2種類混在（長い形式 / 短い形式）
- 症状: `workflow.yaml`・`test_dynamic_import.py`は`adapters.usb_camera_adapter.src.camera_adapter.camera_adapter.CameraAdapter`という長いパス、実コードの大半は`camera_adapter.camera_adapter`という短いパスを使用
- 対応: **修正済み**。短い形式を正とする方針で合意し適用。理由は`usb_camera_adapter/pyproject.toml`の`[tool.hatch.build.targets.wheel] packages`設定が短い形式と一致しているため。
  - `workflow.yaml`の`adapter`値を`camera_adapter.camera_adapter.CameraAdapter`に変更
  - `test_dynamic_import.py`の`class_path`を同様に短い形式へ変更、不要になった`sys.path.insert(0, ".")`を削除

#### 検討過程で見つかった付随の問題（対応済み）
- `interfaces.py`と`test_support/`が`packages`一覧に含まれておらず、正式ビルド時に`ModuleNotFoundError`になりうる
  → **修正済み**。`interfaces.py`を`src/interfaces/__init__.py`へ変換（既存の`from interfaces import ...`はそのまま動く）、`test_support/`に`__init__.py`を追加。`pyproject.toml`の`packages`に両方追加
- `orchestrator/pyproject.toml`の`dependencies`に`usb-camera-adapter`が宣言されていない（`tool.uv.sources`だけでは依存として成立しない）。ルートの共有venvで偶然動いているだけ
  → **修正済み**。`dependencies`に`usb-camera-adapter`を追加

#### 新たに見つかった、未対応の周辺課題（次アクション向け・今回は対応せず）
- `camera_adapter.py`の`from adapters.baseadapter import BaseAdapter`は、短い形式でも長い形式でもない第三の書き方（リポジトリルートがsys.pathにある前提）。いずれ統一を検討
- `test_support/`（Fake/Mock置き場）が製品用wheelに含まれる状態になった。テスト専用コードを配布物に含めるかどうかは設計判断が必要

### 4. `CameraAdapter.__init__`が`config`引数を受け取れない
- 症状: `GenericOrchestrator`は`cls(config=params)`で生成するが、`CameraAdapter.__init__(self, camera_controller=None)`は`camera_controller`しか受けない
- 対応: **修正済み**。`config`と`camera_controller`の両方を受け取れるようにし、`camera_controller`が渡されなければ`config`から組み立てる形にした。DI（テスト時のFake差し込み）とYAML駆動生成を両立させる狙い。

```python
def __init__(self, config: dict[str, Any] | None = None, camera_controller=None):
    if camera_controller is not None:
        self.camera_controller = camera_controller
    else:
        device_id = (config or {}).get("device_id", 0)
        self.camera_controller = CameraController(device_id=device_id)
```

### 5. `self.controller`というタイポ
- 症状: `__init__`では`self.camera_controller`を設定しているのに、`setup()`と`execute_step()`は`self.controller`を参照し`AttributeError`
- 対応: **修正済み**。`self.camera_controller`に統一（[camera_adapter.py:26](../../adapters/usb_camera_adapter/src/camera_adapter/camera_adapter.py#L26), [camera_adapter.py:45](../../adapters/usb_camera_adapter/src/camera_adapter/camera_adapter.py#L45)）
- 注意: 項目6の適用により`setup()`側も動くようになった

### 6. `CameraController`に`check_device_status()`が存在しない
- 症状: `setup()`が存在しないメソッドを呼んでいる
- 対応: **修正済み**。`CameraController`に新規メソッドは足さず、`CameraAdapter`が既に持つ`check_device_status()`（`is_led_on`ベースの正しい実装、[camera_adapter.py:64-66](../../adapters/usb_camera_adapter/src/camera_adapter/camera_adapter.py#L64-L66)）を`setup()`から呼ぶ形にした。`test_camera_adapter.py`の`test_adapter_check_device_status()`が既にこのAdapterレベルのメソッドをテストしており、実装意図と一致する。

```python
# setup() 内、修正案
status = self.check_device_status()
```

**2026-08-22追記**：この対応が結果的にバグの原因になっていた。デモ用`Orchestrator.execute()`も独自に`check_device_status()`を呼ぶため、1回の実行で2回撮影してしまっていた。`setup()`からは`check_device_status()`の呼び出しを外し、接続（`open()`）のみに戻した（[12_essential_gaps_found.md](12_essential_gaps_found.md)、[06_workflow_yaml_usage.md](06_workflow_yaml_usage.md)参照）。

### 7. `cv2.VideoCapture`のAPI名の誤り
- 症状: `is_opened()`ではなく`isOpened()`が正しいAPI
- 対応: **修正済み**（[camera_controller.py:38](../../adapters/usb_camera_adapter/src/camera_controller/camera_controller.py#L38)）

### 8. `interfaces.py`の抽象メソッドと実装のシグネチャ不一致
- 症状: `save_capture(self)` / `is_led_on(self)`が引数なしで宣言されているが、実装は`frame`や`roi, threshold`を必須要求
- 対応: **未適用（方針のみ決定）**。実装に合わせて抽象側を修正する方針。

```python
@abstractmethod
def save_capture(self, frame) -> None: ...

@abstractmethod
def is_led_on(self, roi: tuple[int, int, int, int], threshold: int) -> bool: ...
```

## 保留・次アクション

- 項目8（`interfaces.py`のシグネチャ不一致）は説明のみで未適用。Step4（インターフェース健全化）で対応予定
- `adapters.baseadapter`の第三の import 形式の統一、`test_support`を製品wheelに含めるかどうかの設計判断、が新たな検討課題として残っている
