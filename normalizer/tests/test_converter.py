from pathlib import Path

import pytest

from normalizer.converter import convert, load_mapping

# convert()自体はファイルを読まない純粋関数なので、テストでは本番のmapping.yamlに
# 依存しない小さな変換ルールをその場で用意する（mapping.yamlの中身が変わってもテストは壊れない）。
LIFECYCLE_LABELS = {"カメラ接続", "カメラ切断"}
ACTION_MAPPING = {
    "カメラ画像撮影": {
        "adapter": "camera_adapter.camera_adapter.CameraAdapter",
        "action": "capture",
        "params": {"resolution": [640, 480]},
    },
}


def test_convert_full_scenario_produces_expected_pipeline():
    plantuml_text = """
@startuml
start
:カメラ接続;
:カメラ画像撮影;
:カメラ切断;
stop
@enduml
"""
    result = convert(plantuml_text, LIFECYCLE_LABELS, ACTION_MAPPING)

    assert result == [
        {
            "name": "カメラ画像撮影",
            "adapter": "camera_adapter.camera_adapter.CameraAdapter",
            "action": "capture",
            "params": {"resolution": [640, 480]},
        }
    ]


def test_convert_unknown_label_raises_value_error():
    plantuml_text = """
@startuml
start
:未知の処理;
stop
@enduml
"""
    with pytest.raises(ValueError, match="未対応のステップです: 未知の処理"):
        convert(plantuml_text, LIFECYCLE_LABELS, ACTION_MAPPING)


def test_convert_lifecycle_only_returns_empty_pipeline():
    plantuml_text = """
@startuml
start
:カメラ接続;
:カメラ切断;
stop
@enduml
"""
    assert convert(plantuml_text, LIFECYCLE_LABELS, ACTION_MAPPING) == []


def test_convert_empty_text_returns_empty_pipeline():
    assert convert("", LIFECYCLE_LABELS, ACTION_MAPPING) == []


def test_convert_ignores_non_step_lines():
    # @startuml/start/stop/@enduml、空行、`:`で始まらない行は無視される
    plantuml_text = """
@startuml
title 無視されるはずのタイトル行
start
:カメラ画像撮影;
stop
@enduml
"""
    result = convert(plantuml_text, LIFECYCLE_LABELS, ACTION_MAPPING)
    assert len(result) == 1
    assert result[0]["name"] == "カメラ画像撮影"


# --- load_mapping(): 本番のmapping.yamlを実際に読み込むテスト ---

MAPPING_PATH = Path(__file__).parent.parent / "config" / "mapping.yaml"


def test_load_mapping_reads_real_mapping_yaml():
    lifecycle_labels, action_mapping = load_mapping(MAPPING_PATH)

    assert lifecycle_labels == {"カメラ接続", "カメラ切断"}
    assert action_mapping == {
        "カメラ画像撮影": {
            "adapter": "camera_adapter.camera_adapter.CameraAdapter",
            "action": "capture",
            "params": {"resolution": [640, 480]},
        }
    }


def test_load_mapping_output_is_usable_directly_by_convert():
    # load_mapping()の戻り値をそのままconvert()に渡せることを確認する結合テスト
    lifecycle_labels, action_mapping = load_mapping(MAPPING_PATH)

    plantuml_text = """
@startuml
start
:カメラ接続;
:カメラ画像撮影;
:カメラ切断;
stop
@enduml
"""
    result = convert(plantuml_text, lifecycle_labels, action_mapping)
    assert len(result) == 1
    assert result[0]["action"] == "capture"
