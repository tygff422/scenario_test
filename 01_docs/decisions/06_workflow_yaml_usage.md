# 06_workflow_yaml_usage

- 日付: 2026-08-13（2026-08-17: Step5の非同期化を反映して一部更新）
- 関連: [03_package_settings_adapter_orchestrator.md](03_package_settings_adapter_orchestrator.md)（GenericOrchestratorの依存関係）・[04_urgent_fix_camera_pipeline.md](04_urgent_fix_camera_pipeline.md)（`adapter`キー名を確定した経緯）・[09_async_execute_step.md](09_async_execute_step.md)（execute_stepの非同期化）・[orchestrator/README.md](../../orchestrator/README.md)（実行手順の要約）
- 位置づけ: `normalizer/config/workflow.yaml`の書き方・値の渡り方・Adapterのライフサイクルとの対応関係をまとめた使い方ガイド。新しいAdapterを追加する人向けのリファレンス。

## 1. 基本構造

```yaml
pipeline:
  - name: "カメラ画像撮影"
    adapter: "camera_adapter.camera_adapter.CameraAdapter"
    action: "capture"
    params:
      resolution: [640, 480]
```

`pipeline`はリストで、各要素（1ステップ）が1つのAdapterインスタンスに対応する。`GenericOrchestrator.execute_pipeline()`が先頭から順に処理する。複数ステップを並べれば、異なるAdapterを順番に実行できる（後述「AudioAdapterを追加する例」）。

## 2. 各キーの意味と渡り方

| キー | 型 | 用途 |
|---|---|---|
| `name` | str | ログ表示用のラベル。処理には使われない |
| `adapter` | str | Adapterクラスのimportパス（**短い形式**、[01](01_import_resolution_rules.md)ルール3参照）。`importlib.import_module` + `getattr`で動的ロードされ、`BaseAdapter`のサブクラスかを実行時検証する（違えば`TypeError`） |
| `action` | str | `execute_step(action=...)`にそのまま渡される。Adapter側が`if action == "..."`で分岐して解釈する |
| `params` | dict | **1つのdictが2箇所に渡る**（次項参照） |

### `params`は「コンストラクタ用」と「execute_step用」を兼ねる

```python
adapter: BaseAdapter = cls(config=params)          # ①コンストラクタへ
result = adapter.execute_step(action=action, params=params)  # ②execute_stepへ
```

`workflow.yaml`のキーは`params`ひとつだが、実体としては①インスタンス生成時の設定（`device_id`のような「接続先を決める値」）と、②実行時の引数（`resolution`のような「その1回の動作に対する値」）の両方が同じdictにフラットに混在する。CameraAdapterの実装では

```python
def __init__(self, config=None, ...):
    device_id = (config or {}).get("device_id", 0)   # ← ①として使用

def execute_step(self, action, params):
    resolution = params.get("resolution")            # ← ②として使用
```

のように、Adapter側の実装が「このキーは①、このキーは②」と選り分けている。YAML上はキー名の使い分けルールは無いので、**Adapterを書く人が`__init__`と`execute_step`のどちらでそのキーを読むかを自分で決めて実装する**必要がある。

## 3. 1ステップの実行ライフサイクル

```text
cls(config=params) でインスタンス生成
  ↓
with adapter:                          ← BaseAdapter.__enter__（sync）
    setup() が呼ばれる                    「接続」+「使える状態か確認」はここに書く（sync）
    ↓
    await execute_step(action, params)   YAMLで指定した「実際の1アクション」だけをここに書く（async）
    ↓
                                        ← BaseAdapter.__exit__（sync）
    teardown() が呼ばれる                 「解放」はここに書く（例外時も必ず呼ばれる、sync）
```

**Step5の非同期化（[09](09_async_execute_step.md)）を反映**：`setup()`/`teardown()`はsyncのまま、`execute_step()`だけが`async def`になり、`GenericOrchestrator`側は`await adapter.execute_step(...)`で呼ぶ。新しくAdapterを書く場合、`execute_step`は必ず`async def`で実装する必要がある（`BaseAdapter`の抽象メソッドが`async def`のため）。

**重要**：`connect`・`is_ready確認`・`release`はYAMLの`action`として書かない。これらは`setup()`/`teardown()`の中身として実装し、`with`文（`BaseAdapter.__enter__`/`__exit__`）経由で自動的に呼ばれる。YAMLの`action`に書くのは「setupが終わった後にやりたい実際の仕事」だけでよい。

CameraAdapterの対応：

| ライフサイクル段階 | CameraAdapterでの実装 |
|---|---|
| `setup()` | `open()`（OpenCVでカメラ接続）→ `check_device_status()`（LEDのROIを見てREADY判定） |
| `execute_step("capture", params)` | 撮影のみ。`action`が`"capture"`以外なら`ValueError` |
| `teardown()` | `camera_controller.release()` |

## 4. 新しいAdapterを追加する手順

1. `BaseAdapter`（`adapter_core.baseadapter`）を継承し、`setup()` / `execute_step()` / `teardown()` を実装する
   - `setup()`：接続 + 使える状態かの確認 → `bool`を返す（`False`なら`with`に入った時点で`RuntimeError`）。sync
   - `execute_step()`：**`async def`で実装する**（[09](09_async_execute_step.md)）。対応する`action`ごとに分岐。
     未対応の`action`は`ValueError`を投げる（CameraAdapterに倣う）。ブロッキングするI/O呼び出し（ファイル・
     ネットワーク・OpenCV等）は`asyncio.to_thread`で包み、他の非同期処理を止めないようにする
   - `teardown()`：リソース解放。例外は`BaseAdapter.__exit__`側でログに残されるだけで再送出はされない。sync
2. 対応する`pyproject.toml`の`[tool.hatch.build.targets.wheel] packages`にモジュールを追加し、ワークスペースへ`uv sync`で反映する（[03](03_package_settings_adapter_orchestrator.md)参照）
3. `workflow.yaml`の`pipeline`にステップを追記する（`adapter`は短い形式のimportパスで）

### 例：AudioAdapterを追加する場合

```python
import asyncio


class AudioAdapter(BaseAdapter):
    def __init__(self, config=None):
        device_id = (config or {}).get("device_id", 0)
        self.controller = AudioController(device_id=device_id)

    def setup(self) -> bool:
        if not self.controller.open():
            return False
        self._is_ready = self.controller.is_ready()
        return self._is_ready

    async def execute_step(self, action, params) -> dict:
        if action == "record":
            data = await asyncio.to_thread(
                self.controller.record, params.get("duration_sec", 3)
            )
            return {"status": "SUCCESS" if data else "FAILED", "data": data}
        raise ValueError(f"未対応のアクションです: {action}")

    def teardown(self) -> None:
        self.controller.release()
```

```yaml
pipeline:
  - name: "カメラ画像撮影"
    adapter: "camera_adapter.camera_adapter.CameraAdapter"
    action: "capture"
    params:
      resolution: [640, 480]

  - name: "音声録音"
    adapter: "audio_adapter.audio_adapter.AudioAdapter"
    action: "record"
    params:
      duration_sec: 3
```

CameraAdapterと全く同じ骨格（setup=接続+確認、execute_step=1アクション、teardown=解放）をなぞるだけで、既存の`GenericOrchestrator`はコード変更なしに新しいAdapterを実行できる。

## 5. エラー時の挙動

いずれかのステップ（クラスロード・`setup`・`execute_step`のどこでも）で例外が発生すると、`GenericOrchestrator.execute_pipeline()`はその場でパイプライン全体を中断し`False`を返す。**リトライや後続ステップのスキップといった細かい制御は無い**（全断のみ）。個別ステップの再試行やエラー時の代替処理が必要になったら、ここを拡張する必要がある。

## 6. 既知の制約（今後の拡張ポイント）

**現状はYAMLの1ステップ＝新規インスタンス生成＋setup→execute_step→teardownの1サイクル**という設計になっている。

```text
もし「1回connectして、captureを2回行ってからrelease」のように
同じ接続を使い回して複数アクションを連続実行したい場合、
今のままではワークフローに2ステップ書くと、
ステップごとに新規インスタンスが生成されるため
1ステップ目でopen→capture→release、2ステップ目でまたopen→capture→release
と、毎回接続し直しになってしまう。
```

これは意図的に今のスコープ外としている（YAGNI）。ロードマップのStep7（最終統合・`registry.py`/`context.py`の導入）で、同じAdapterインスタンスを複数ステップにまたがって使い回す仕組みが必要になったタイミングで再検討する、という拡張性として残していることを明記しておく。
