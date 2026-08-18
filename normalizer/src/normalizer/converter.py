import re
from pathlib import Path

import yaml

# `:テキスト;` の行だけを拾う（start/stop/@startuml等は無視）
STEP_LINE = re.compile(r"^:(.+);$")


def load_mapping(path: str | Path) -> tuple[set[str], dict[str, dict]]:
    """変換ルールYAML（lifecycle_labels / action_mapping）を読み込む。

    ファイルを読むのはここだけに閉じ込め、convert()自体は純粋関数のまま保つ。
    """
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

        step = dict(action_mapping[label])
        step["name"] = label
        pipeline.append(step)

    return pipeline
