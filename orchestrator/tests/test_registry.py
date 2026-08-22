from orchestrator.registry import load_adapter_class, validate_pipeline
from orchestrator_test_support.fake_pipeline_adapter import FakePipelineAdapter

FAKE_ADAPTER_PATH = "orchestrator_test_support.fake_pipeline_adapter.FakePipelineAdapter"


def test_load_adapter_class_returns_the_class():
    cls = load_adapter_class(FAKE_ADAPTER_PATH)
    assert cls is FakePipelineAdapter


def test_load_adapter_class_raises_for_non_base_adapter_subclass():
    try:
        load_adapter_class("builtins.dict")
        assert False, "TypeErrorが発生するはず"
    except TypeError:
        pass


def test_validate_pipeline_returns_empty_list_for_valid_pipeline():
    pipeline = [
        {"name": "ステップ1", "adapter": FAKE_ADAPTER_PATH, "action": "a", "params": {}},
        {"name": "ステップ2", "adapter": FAKE_ADAPTER_PATH, "action": "b", "params": {}},
    ]
    assert validate_pipeline(pipeline) == []


def test_validate_pipeline_reports_missing_adapter_key():
    pipeline = [{"name": "adapter指定漏れ", "action": "a", "params": {}}]
    errors = validate_pipeline(pipeline)
    assert len(errors) == 1
    assert "adapter指定漏れ" in errors[0]


def test_validate_pipeline_reports_non_base_adapter_subclass():
    pipeline = [{"name": "不正なadapter", "adapter": "builtins.dict", "params": {}}]
    errors = validate_pipeline(pipeline)
    assert len(errors) == 1
    assert "builtins.dict" in errors[0]


def test_validate_pipeline_reports_nonexistent_module():
    pipeline = [
        {"name": "存在しないモジュール", "adapter": "no_such_module.NoSuchClass", "params": {}}
    ]
    errors = validate_pipeline(pipeline)
    assert len(errors) == 1


def test_validate_pipeline_collects_all_errors_not_just_first():
    pipeline = [
        {"name": "不正1", "adapter": "builtins.dict", "params": {}},
        {"name": "正常", "adapter": FAKE_ADAPTER_PATH, "action": "a", "params": {}},
        {"name": "不正2", "adapter": "builtins.list", "params": {}},
    ]
    errors = validate_pipeline(pipeline)
    assert len(errors) == 2
