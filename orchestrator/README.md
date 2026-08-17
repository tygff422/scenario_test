# orchestrator

シナリオ実行エンジン。ワークスペース内の他パッケージ（`usb-camera-adapter`, `adapter-core`）が実装する
`BaseAdapter`派生クラスを呼び出し、一連の処理を実行する役割を持つ。

## 収録クラス

`src/orchestrator/orchestrator.py`に、性格の異なる2つのクラスが同居している。

### `Orchestrator`（デモ用の具体クラス）

`CameraAdapter`を名指しでハードコードした、動作確認用の最小実装。

```python
from orchestrator.orchestrator import Orchestrator
from camera_adapter.camera_adapter import CameraAdapter

orchestrator = Orchestrator(adapter=CameraAdapter())
result = orchestrator.execute()  # デバイス状態を1回チェックしてbool を返す
```

`with adapter:`でAdapterのコンテキスト管理に入り、`check_device_status()`が`"READY"`を返せば`True`。
例外発生時もキャッチしてlogに残し`False`を返す。

### `GenericOrchestrator`（YAML駆動の汎用実装）

`adapter-core`の`BaseAdapter`（＝契約・抽象）としか会話しない。YAMLファイルに書かれた
パイプライン定義を読み込み、ステップごとに指定されたAdapterクラスを**動的import**して実行する。

```python
import asyncio

from orchestrator.orchestrator import GenericOrchestrator

orchestrator = GenericOrchestrator(config_path="normalizer/config/workflow.yaml")
result = asyncio.run(orchestrator.execute_pipeline())  # 全ステップ成功でTrue
```

`execute_pipeline()`はasync（Step5で非同期化済み）。`setup()`/`teardown()`（`with`構文）はsyncのままで、`execute_step()`だけが`await`対象。`BaseAdapter`を実装する側も`execute_step`を`async def`にする必要がある。

#### workflow.yamlの書式

```yaml
pipeline:
  - name: "カメラ画像撮影"
    adapter: "camera_adapter.camera_adapter.CameraAdapter"  # クラスパス（短い形式）
    action: "capture"
    params:
      resolution: [640, 480]
```

- `adapter`：`importlib.import_module` + `getattr`で動的ロードするクラスパス。
  `BaseAdapter`のサブクラスであることを実行時に検証する（違えば`TypeError`）
- `action` / `params`：`adapter.execute_step(action=action, params=params)`にそのまま渡される
- 各ステップは`cls(config=params)`でインスタンス化され、`with adapter:`
  （`BaseAdapter.__enter__`/`__exit__` = `setup()`/`teardown()`）の中で`execute_step()`が呼ばれる
- いずれかのステップで例外が発生した場合、そこでパイプライン全体を中断し`False`を返す
  （後続ステップは実行されない）

## テスト

```bash
pytest orchestrator/tests -m "not hardware"
```

- `test_orchestrator.py`：`Orchestrator`をMagicMockで検証（正常系/異常系/例外系）
- `test_generic_orchestrator.py`：`GenericOrchestrator`を`tests/orchestrator_test_support/fake_pipeline_adapter.py`の
  `FakePipelineAdapter`（`BaseAdapter`実装のFake）で検証。実機なしでパイプライン全体の配線
  （動的import → setup → execute_step → teardown、および各失敗パターン）を確認する

  Fakeパッケージ名は`test_support`ではなく`orchestrator_test_support`にしている点に注意。
  `adapters/usb_camera_adapter/tests/test_support/`と同名にすると、両方の`tests/`を1回の
  pytest実行にまとめたときに、prependモードでのモジュール名衝突（後から集められた方の
  `test_support`が解決できなくなる）が発生するため、パッケージごとに名前を分けている。

実機（USBカメラ）を使った動作確認は`main.py`、または`integrationtest/`の`@pytest.mark.hardware`が
付いたテストを参照。

## 依存関係

詳細な設計判断・依存の理由は[01_docs/decisions/](../01_docs/decisions/)を参照。

- `adapter-core`：`GenericOrchestrator`が`BaseAdapter`として利用（抽象への依存）
- `usb-camera-adapter`：`Orchestrator`が`CameraAdapter`を直接利用（具体への依存）
