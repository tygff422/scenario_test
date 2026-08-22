# 新しいAdapterパッケージを追加するガイド

新しいデバイス種別（例：Audio、File、HTTP等）をこのフレームワークに追加する時の手順をまとめたもの。`usb_camera_adapter`（CameraAdapter/CameraController）を作った時の型をなぞる形になっている。

このガイドは「今どうすればいいか」を示す生きた文書。各ステップの詳しい経緯・理由は`decisions/`内の該当ドキュメントにリンクしている。

## 全体の流れ

```text
1. 新パッケージを作る
2. Controller → Adapter の順で実装
3. pyproject.tomlを作り、rootに登録する
4. Fakeを作り、テストを書く
5. mapping.yamlに変換ルールを追記する
6. Orchestrator側は無改修（設計上の到達点）
7. scenario.pumlを更新し、成果物ディレクトリが必要なら注入パターンを踏襲する
8. ドキュメント化する
```

---

## 1. 新パッケージを作る

`adapters/<name>_adapter/`に、`usb_camera_adapter`と同じ構成を作る。別リポジトリにする必然性は無い（`usb_camera_adapter`が別リポジトリなのは元々別プロジェクトだった経緯によるもので、意図した設計原則ではない。[03](decisions/03_package_settings_adapter_orchestrator.md)参照）。モノレポ内で完結させてよい。

```text
adapters/<name>_adapter/
  pyproject.toml
  .python-version
  README.md
  .gitignore
  src/
    <name>_controller/<name>_controller.py   ← 実I/O層
    <name>_adapter/<name>_adapter.py          ← BaseAdapter実装
    interfaces/__init__.py                     ← <Name>ControllerInterface（契約）
  tests/
    test_<name>_adapter.py
    test_support/<name>_mock_controller.py    ← Fake
```

## 2. Controller → Adapterの順で実装する

**Controllerが先。** 実際のI/Oを1つずつ行うだけの層（sync）。

```python
class AudioController:
    def open(self) -> bool: ...
    def release(self) -> None: ...
    def record(self, duration_sec: float) -> bytes | None: ...
    def save_recording(self, data, audio_dir=None) -> Path | None: ...
```

**Adapterは`BaseAdapter`（`adapter_core.baseadapter`）を継承**する。

```python
class AudioAdapter(BaseAdapter):
    def setup(self) -> bool:
        return self.controller.open()   # openのみ。確認処理を混ぜない

    async def execute_step(self, action, params) -> dict:  # 必ずasync def（09参照）
        data = await asyncio.to_thread(self.controller.record, params.get("duration_sec", 3))
        return {"status": "SUCCESS" if data else "FAILED", ...}

    def teardown(self) -> None:
        self.controller.release()
```

**設計ルール**（過去の失敗から学んだもの）：

- `setup()`は接続確認のみに絞る。「確認」を複数箇所で重複してやらない
  （`CameraAdapter.setup()`が`Orchestrator.execute()`と二重にLED確認していたバグの教訓、[12](decisions/12_essential_gaps_found.md)）
- `execute_step()`は必ず`async def`。ブロッキングI/Oは`asyncio.to_thread`で分離（[09](decisions/09_async_execute_step.md)）
- `params`のキー設計・constructorとexecute_stepの使い分けは[06](decisions/06_workflow_yaml_usage.md)を参照
- InterfaceとFakeは、本物のControllerに合わせる（Fakeの都合でInterfaceを緩めない、Liskov置換。[03](decisions/03_package_settings_adapter_orchestrator.md)）

## 3. pyproject.tomlを作り、rootに登録する

```toml
# adapters/<name>_adapter/pyproject.toml（usb_camera_adapterの例に倣う）
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
[project]
name = "<name>-adapter"
dependencies = [...]
[dependency-groups]
dev = ["pytest>=9.1.1"]
[tool.hatch.build.targets.wheel]
packages = ["src/<name>_controller", "src/<name>_adapter", "src/interfaces"]
[tool.uv.sources]
adapter-core = { workspace = true }
```

```toml
# ルートpyproject.toml：3箇所すべてに追加が必要
[project] dependencies = [..., "<name>-adapter"]
[tool.uv.workspace] members = [..., "adapters/<name>_adapter"]
[tool.uv.sources] <name>-adapter = { workspace = true }
```

**要注意**：`members`に足すだけでは共有venvにインストールされない。`dependencies`への明示登録も必須（`normalizer`追加時に実際に踏んだ落とし穴、[01](decisions/01_import_resolution_rules.md)訂正参照）。

## 4. Fakeを作り、テストを書く

`<name>_mock_controller.py`（Interfaceを実装したFake）を`tests/test_support/`に置き、実機なしで`setup → execute_step → teardown`のライフサイクルを検証する。実機依存のテストは`@pytest.mark.hardware`で分離（[03](decisions/03_package_settings_adapter_orchestrator.md)）。

## 5. mapping.yamlに変換ルールを追記する

`normalizer/config/mapping.yaml`にエントリを足すだけ。コード変更は不要（[08](decisions/08_plantuml_conversion_design_policy.md)）。

```yaml
lifecycle_labels:
  - "マイク接続"
  - "マイク切断"
action_mapping:
  "音声録音":
    adapter: "audio_adapter.audio_adapter.AudioAdapter"
    action: "record"
    params:
      duration_sec: 3
```

## 6. Orchestrator側は無改修（この設計の到達点）

`GenericOrchestrator`・`registry.py`（事前検証）・`context.py`（結果履歴）は全てクラスパス文字列ベースで汎用化されているため、新しいAdapterを追加してもこれらのファイルには一切手を入れない（[10](decisions/10_context_step_history.md)・[11](decisions/11_registry_pipeline_validation.md)）。同じ接続で複数アクションを実行したい場合は`steps`形式が使える（[06](decisions/06_workflow_yaml_usage.md)）。

## 7. scenario.pumlを更新し、必要なら成果物ディレクトリを注入する

`normalizer/config/scenario.puml`にシナリオを追記して実機で通す。録音ファイル等の成果物を残したい場合、`CameraController`の`img_dir`と同じパターンを踏襲する：

```text
Controller: audio_dirパラメータを受け取れるようにする（未指定時は後方互換のデフォルト）
Adapter:    configからaudio_dirを中継するだけ
run_scenario.py: 実行直前にpipelineのparamsへtestexecutor/audio/の絶対パスを注入
```

詳細と設計理由は[13](decisions/13_log_and_artifact_storage_gap.md)・[14](decisions/14_testexecutor_folder.md)を参照。

## 8. ドキュメント化する

`01_docs/decisions/`に新規番号でdecisionを作り、Controller/Adapterの設計判断を記録する。`01_docs/implementation_plan.md`の進捗欄も更新する。
