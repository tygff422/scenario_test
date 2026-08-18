# 08_plantuml_conversion_design_policy

- 日付: 2026-08-17
- 関連Step: Step6（PlantUML風DSL変換） / [06_workflow_yaml_usage.md](06_workflow_yaml_usage.md)（既知の制約セクション）
- ステータス: 方針決定（実装はまだ）

## 背景

Step6（`converter.py`）に着手する前に、配置場所・YAMLスキーマの拡張方針・PlantUMLマッピングの実装粒度について方針をすり合わせた。

## 決定事項

### 1. `converter.py`の配置場所

`normalizer/`配下に置く。既に`normalizer/config/workflow.yaml`が存在しており、学習計画（Phase9最終形）でも`normalizer.py`と`converter.py`が並んで挙げられているため。他パッケージと同じ型（`pyproject.toml` + `src/normalizer/`）を踏襲する想定。

```text
normalizer/
  pyproject.toml          （未作成）
  src/
    normalizer/
      __init__.py
      converter.py         ← PlantUML → IR変換
  config/
    workflow.yaml          （既存）
```

**未確定**：`pyproject.toml`新規作成・ルートworkspaceへの登録タイミングは、実際に`converter.py`を書き始める時。

### 2. `workflow.yaml`のスキーマは現状維持（最小実装優先）

`steps`ネスト構造（1つのAdapterインスタンスに複数アクションを持たせる案）は**今は導入しない**。`GenericOrchestrator`は無改修のまま、`converter.py`が現行の`pipeline: [{name, adapter, action, params}]`形式のlist[dict]をそのまま出力する。スキーマ拡張は、実際にそれが必要なPlantUMLシナリオ（例：同じ接続で複数回actionしたい）が出てきた時点で行う。

### 3. PlantUMLマッピングも最小実装から

固定辞書（`ACTION_MAPPING: dict[str, dict]`）＋`:テキスト;`行を拾う正規表現1本（`^:(.+);$`）から開始する。

```python
import re

ACTION_MAPPING: dict[str, dict] = {
    "カメラ画像撮影": {
        "adapter": "camera_adapter.camera_adapter.CameraAdapter",
        "action": "capture",
        "params": {"resolution": [640, 480]},
    },
}

STEP_LINE = re.compile(r"^:(.+);$")

def convert(plantuml_text: str) -> list[dict]:
    pipeline = []
    for raw_line in plantuml_text.splitlines():
        line = raw_line.strip()
        matched = STEP_LINE.match(line)
        if not matched:
            continue
        label = matched.group(1)
        if label not in ACTION_MAPPING:
            raise ValueError(f"未対応のステップです: {label}")
        step = dict(ACTION_MAPPING[label])
        step["name"] = label
        pipeline.append(step)
    return pipeline
```

`start`/`stop`/`@startuml`/`@enduml`は無視する（マッチしない行は単純にスキップ）。if/else分岐や数値入りパターン（「2秒待つ」等）は最初のバージョンには含めない。

## 未確定（今後決めること）

| # | 論点 |
|---|---|
| 2 | converterの出力をファイルに書き出すか、メモリ上のdictを直接`GenericOrchestrator`へ渡すか（現状はファイルパスしか受け取れない制約がある） |
| 4 | 同一Adapterインスタンスを複数アクションで使い回す仕組み（`steps`ネスト導入）をいつ着手するか |

## 決定事項の追記（2026-08-17、実装完了）

### 1. 「接続」「切断」見出し行の扱い：無視リスト方式（案A）を採用

`lifecycle_labels`（後述のmapping.yaml内）に列挙した見出しは、`convert()`内で読み飛ばす（パイプラインに追加しない）。setup/teardownが暗黙に処理するため。

### 3. マッピング辞書の置き場所：YAML外出しを採用

当初`converter.py`内にPythonのdict/setとして直書きしていたが、「PlantUMLの変換ルールは設定として外に出したい」という当初構想に立ち返り、`normalizer/config/mapping.yaml`に外出しした。

```yaml
lifecycle_labels:
  - "カメラ接続"
  - "カメラ切断"

action_mapping:
  "カメラ画像撮影":
    adapter: "camera_adapter.camera_adapter.CameraAdapter"
    action: "capture"
    params:
      resolution: [640, 480]
```

`converter.py`は`load_mapping(path) -> (lifecycle_labels, action_mapping)`（YAMLを読むI/O）と`convert(plantuml_text, lifecycle_labels, action_mapping) -> list[dict]`（変換ロジック本体、純粋関数）に分離した。`convert()`のユニットテストは本番`mapping.yaml`に依存しない自前の小さなルールを使い、`load_mapping()`は実ファイルを読む専用テストで検証する。

### 全体像の整理（当初の想定とのズレを解消）

「`workflow.yaml`にPlantUMLの変換ルールを書く」という当初のイメージと、「`workflow.yaml`は実行フロー（IRの出力）そのもの」という実装がズレていたため、ファイルの役割を明確化した。

```text
①mapping.yaml（変換ルール、人が編集） ─┐
                                       ├─▶ convert() ─▶ ③workflow.yaml相当のdict
②PlantUMLテキスト ─────────────────────┘        （将来的にはこれが自動生成の出力になる。今は③はまだ手書きのまま）
```

## 「同一Adapterインスタンスを複数アクションで使い回す」問題の詳細（設計メモ）

`GenericOrchestrator.execute_pipeline()`はステップごとに新規インスタンスを生成し、`with adapter:`で毎回`setup()`→`teardown()`を行う。そのため、同じ`adapter`を指すステップを2つ並べても「接続→撮影→切断」を2回繰り返すだけで、「1回接続して2回撮影してから切断する」という動きにはならない。

解決には、Orchestrator側に「このNステップは同じインスタンスを共有する」というグルーピング概念が必要（`steps`ネスト案）。

```python
adapter = cls(config=params)
with adapter:                       # setup() は1回だけ
    for action_step in grouped_steps:
        adapter.execute_step(action_step.action, action_step.params)
    # teardown() も1回だけ
```

実際にPlantUMLシナリオでこの形が必要になった時点で着手する（現時点では見送り）。
