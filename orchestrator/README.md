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

### 既にパース済みのpipelineを直接渡す：`execute()`

`execute_pipeline()`はYAMLファイルを読む前提だが、`normalizer.converter.convert()`のようにメモリ上で
`list[dict]`を作った場合は、ファイルに書き出さず直接`execute()`へ渡せる（Step6、[08](../01_docs/decisions/08_plantuml_conversion_design_policy.md)）。

```python
import asyncio

from normalizer.converter import convert, load_mapping
from orchestrator.orchestrator import GenericOrchestrator

lifecycle_labels, action_mapping = load_mapping("normalizer/config/mapping.yaml")
pipeline = convert(plantuml_text, lifecycle_labels, action_mapping)

orchestrator = GenericOrchestrator()  # config_path不要
result = asyncio.run(orchestrator.execute(pipeline))
```

`execute_pipeline()`は内部で「YAMLを読む→`execute()`を呼ぶ」だけの薄いラッパーになっている。

### 実行結果を後から参照する：`Context`

`execute()`は各ステップの`execute_step()`の結果を`self.context`（`orchestrator.context.Context`）に記録する。
呼び出しのたびにリセットされる（前回実行の履歴は引き継がない）。

```python
await orchestrator.execute(pipeline)

for entry in orchestrator.context.history:       # 実行順のlist[StepResult]
    print(entry.name, entry.action, entry.result)

orchestrator.context.last_result_for("capture")  # 指定actionの直近の結果（無ければNone）
```

v0では「後から参照できる」だけで、前のステップの結果を次のステップの`params`へ自動的に注入する機能（テンプレート的な置換）は無い。必要になったら拡張する。

### 実行前にadapterクラスパスを一括検証する：`registry.py`

`execute()`は実行を始める前に、pipeline内の全`adapter`クラスパスが正しくロードできるかを
`registry.validate_pipeline()`で一括検証する。1つでも不正なら、**どのステップも実行せずに**`False`を返す
（実行途中で発覚して一部のステップだけ実行済み、という事故を防ぐ）。

```python
from orchestrator.registry import validate_pipeline

errors = validate_pipeline(pipeline)  # 空リストなら全て正常
```

`load_adapter_class(class_path)`（動的import + BaseAdapterサブクラス検証）が、事前検証と
実行時ロードの両方から呼ばれる共通ロジック。

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

`steps`キーを使うと、同一Adapterインスタンス（setup/teardownは1回だけ）で複数アクションを連続実行できる。
詳細は[06_workflow_yaml_usage.md](../01_docs/decisions/06_workflow_yaml_usage.md)を参照。

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
- `test_context.py`：`Context`の`record`/`last_result_for`単体、および`GenericOrchestrator.execute()`が
  各ステップの結果を正しく記録すること（steps形式で上書きされないこと、呼び出しのたびにリセットされること）を検証
- `test_registry.py`：`load_adapter_class`/`validate_pipeline`の単体テスト
  （正常系、adapter指定漏れ、BaseAdapter非継承、存在しないモジュール、複数エラーの収集）

実機（USBカメラ）を使った動作確認は`main.py`、または`integrationtest/`の`@pytest.mark.hardware`が
付いたテストを参照。

## 依存関係

詳細な設計判断・依存の理由は[01_docs/decisions/](../01_docs/decisions/)を参照。

- `adapter-core`：`GenericOrchestrator`が`BaseAdapter`として利用（抽象への依存）
- `usb-camera-adapter`：`Orchestrator`が`CameraAdapter`を直接利用（具体への依存）
