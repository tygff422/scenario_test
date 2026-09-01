import re
from pathlib import Path

import yaml

# `:テキスト;` の行だけを拾う（start/stop/@startuml等は無視）
STEP_LINE = re.compile(r"^:(.+);$")

# mapping.yamlはnormalizer自身が読むファイル（呼び出し側の持ち物ではない）なので、
# デフォルトの場所を自分で知っておく。CameraController.img_dirと同じパターン
# （01_docs/decisions/18_scenario_puml_ownership.md参照）。
DEFAULT_MAPPING_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "mapping.yaml"


def load_mapping(path: str | Path | None = None) -> tuple[set[str], dict[str, dict]]:
    """変換ルールYAML（lifecycle_labels / action_mapping）を読み込む。

    pathを省略すると、normalizer自身のconfig/mapping.yamlを読む（後方互換のデフォルト）。
    テスト等で別のYAMLを読ませたい場合はpathを明示的に渡して上書きできる。
    ファイルを読むのはここだけに閉じ込め、convert()自体は純粋関数のまま保つ。
    """
    path = path if path is not None else DEFAULT_MAPPING_PATH

    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    lifecycle_labels = set(raw.get("lifecycle_labels", []))
    action_mapping = raw.get("action_mapping", {})
    return lifecycle_labels, action_mapping


def convert(
    plantuml_text: str,
    lifecycle_labels: set[str],
    action_mapping: dict[str, dict],
) -> list[dict]:
    """PlantUML風テキストを、workflow.yamlのpipeline相当のlist[dict]に変換する。

    ファイルは一切読み書きしない純粋関数。変換ルール（lifecycle_labels/action_mapping）は
    呼び出し側がload_mapping()等で用意して渡す。YAMLへの書き出しも呼び出し側の責務。

    出力は常にsteps形式（01_docs/known_issues.md No.1対応）。トップレベルのparamsは
    コンストラクタ専用、steps[].paramsはexecute_step専用に分離され、1つのparamsが
    2つの意味を兼ねる曖昧さが構造的に無くなる（GenericOrchestrator側は従来形式も
    後方互換で読めるが、convert()はもう出力しない）。
    """
    pipeline: list[dict] = []

    for raw_line in plantuml_text.splitlines():
        line = raw_line.strip()
        matched = STEP_LINE.match(line)
        if not matched:
            continue  # start/stop/@startuml等、ステップ行でないものは無視

        label = matched.group(1)

        if label in lifecycle_labels:
            continue  # connect/disconnect相当。setup/teardownが暗黙に処理する

        if label not in action_mapping:
            raise ValueError(f"未対応のステップです: {label}")

        entry = action_mapping[label]
        pipeline.append({
            "name": label,
            "adapter": entry["adapter"],
            "params": {},
            "steps": [
                {"action": entry["action"], "params": entry.get("params", {})}
            ],
        })

    return pipeline
