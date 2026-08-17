import asyncio

import pytest

from orchestrator.orchestrator import GenericOrchestrator
from orchestrator_test_support.fake_pipeline_adapter import FakePipelineAdapter

FAKE_ADAPTER_PATH = "orchestrator_test_support.fake_pipeline_adapter.FakePipelineAdapter"


@pytest.fixture(autouse=True)
def reset_fake_adapter_events():
    """FakePipelineAdapter.eventsはクラス変数（複数インスタンス間で共有）なので、
    テストごとに初期化してから実行する。"""
    FakePipelineAdapter.events.clear()
    yield
    FakePipelineAdapter.events.clear()


def write_workflow(tmp_path, pipeline: list[dict]) -> str:
    import yaml

    config_path = tmp_path / "workflow.yaml"
    config_path.write_text(
        yaml.safe_dump({"pipeline": pipeline}, allow_unicode=True),
        encoding="utf-8",
    )
    return str(config_path)


def test_execute_pipeline_success(tmp_path):
    config_path = write_workflow(
        tmp_path,
        [
            {
                "name": "Fake成功ステップ",
                "adapter": FAKE_ADAPTER_PATH,
                "action": "do_something",
                "params": {},
            }
        ],
    )

    orchestrator = GenericOrchestrator(config_path=config_path)
    result = asyncio.run(orchestrator.execute_pipeline())

    assert result is True
    assert FakePipelineAdapter.events == ["setup", "execute:do_something", "teardown"]


def test_execute_pipeline_multiple_steps_runs_in_order(tmp_path):
    config_path = write_workflow(
        tmp_path,
        [
            {
                "name": "ステップ1",
                "adapter": FAKE_ADAPTER_PATH,
                "action": "step1",
                "params": {},
            },
            {
                "name": "ステップ2",
                "adapter": FAKE_ADAPTER_PATH,
                "action": "step2",
                "params": {},
            },
        ],
    )

    orchestrator = GenericOrchestrator(config_path=config_path)
    result = asyncio.run(orchestrator.execute_pipeline())

    assert result is True
    assert FakePipelineAdapter.events == [
        "setup",
        "execute:step1",
        "teardown",
        "setup",
        "execute:step2",
        "teardown",
    ]


def test_execute_pipeline_setup_failure_stops_and_returns_false(tmp_path):
    config_path = write_workflow(
        tmp_path,
        [
            {
                "name": "setup失敗ステップ",
                "adapter": FAKE_ADAPTER_PATH,
                "action": "do_something",
                "params": {"setup_should_fail": True},
            }
        ],
    )

    orchestrator = GenericOrchestrator(config_path=config_path)
    result = asyncio.run(orchestrator.execute_pipeline())

    assert result is False
    # setup()はBaseAdapter.__enter__内で例外化されるため、execute_stepまで到達しない
    assert FakePipelineAdapter.events == ["setup"]


def test_execute_pipeline_execute_step_raises_returns_false_but_teardown_runs(tmp_path):
    config_path = write_workflow(
        tmp_path,
        [
            {
                "name": "execute失敗ステップ",
                "adapter": FAKE_ADAPTER_PATH,
                "action": "do_something",
                "params": {"execute_should_raise": True},
            }
        ],
    )

    orchestrator = GenericOrchestrator(config_path=config_path)
    result = asyncio.run(orchestrator.execute_pipeline())

    assert result is False
    # with構文の中で例外が起きるので、teardown（__exit__）までは実行される
    assert FakePipelineAdapter.events == ["setup", "execute:do_something", "teardown"]


def test_execute_pipeline_adapter_not_subclass_of_base_adapter_returns_false(tmp_path):
    config_path = write_workflow(
        tmp_path,
        [
            {
                "name": "不正なadapter指定",
                "adapter": "builtins.dict",
                "action": "do_something",
                "params": {},
            }
        ],
    )

    orchestrator = GenericOrchestrator(config_path=config_path)
    result = asyncio.run(orchestrator.execute_pipeline())

    assert result is False


def test_execute_pipeline_missing_yaml_file_returns_false(tmp_path):
    missing_path = str(tmp_path / "does_not_exist.yaml")

    orchestrator = GenericOrchestrator(config_path=missing_path)
    result = asyncio.run(orchestrator.execute_pipeline())

    assert result is False


def test_execute_pipeline_empty_pipeline_returns_true(tmp_path):
    config_path = write_workflow(tmp_path, [])

    orchestrator = GenericOrchestrator(config_path=config_path)
    result = asyncio.run(orchestrator.execute_pipeline())

    assert result is True
    assert FakePipelineAdapter.events == []
