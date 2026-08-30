"""testexecutor配下で使うパスをまとめた場所。

run_scenario.pyから切り出したもの（2026-08-29 worklog参照）。
どこにも依存しない、一番下の存在。
"""

from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = THIS_DIR.parent

SCENARIO_PATH = THIS_DIR / "puml" / "scenario.puml"
LOG_DIR = THIS_DIR / "logs"
IMG_DIR = THIS_DIR / "img"

# mapping.yamlはnormalizer自身の持ち物なので、ここでは持たない。
# normalizer.converter.load_mapping()が自分のデフォルト位置を知っている
# （01_docs/decisions/18_scenario_puml_ownership.md参照）。
