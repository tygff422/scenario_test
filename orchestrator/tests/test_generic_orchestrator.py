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


# --- execute(): 既にパース済みのpipeline(list[dict])を直接渡すインターフェース ---
# normalizer.converter.convert()の戻り値をそのまま渡せることを想定している。


def test_execute_accepts_pipeline_list_directly_without_config_path():
    # config_pathを渡さずに構築できる（execute()はファイルを一切読まない）
    orchestrator = GenericOrchestrator()

    pipeline = [
        {
            "name": "Fake成功ステップ",
            "adapter": FAKE_ADAPTER_PATH,
            "action": "do_something",
            "params": {},
        }
    ]

    result = asyncio.run(orchestrator.execute(pipeline))

    assert result is True
    assert FakePipelineAdapter.events == ["setup", "execute:do_something", "teardown"]


def test_execute_pipeline_without_config_path_returns_false():
    orchestrator = GenericOrchestrator()
    result = asyncio.run(orchestrator.execute_pipeline())

    assert result is False


# --- steps形式: 同一Adapterインスタンスで複数アクションを連続実行する ---


def test_execute_steps_format_reuses_same_instance_setup_teardown_once():
    orchestrator = GenericOrchestrator()

    pipeline = [
        {
            "name": "連続実行セッション",
            "adapter": FAKE_ADAPTER_PATH,
            "params": {},
            "steps": [
                {"action": "step1", "params": {}},
                {"action": "step2", "params": {}},
            ],
        }
    ]

    result = asyncio.run(orchestrator.execute(pipeline))

    assert result is True
    # setup/teardownが1回ずつだけ呼ばれ、その間に2アクション実行されている
    assert FakePipelineAdapter.events == [
        "setup",
        "execute:step1",
        "execute:step2",
        "teardown",
    ]


def test_execute_steps_format_raise_stops_remaining_substeps_but_teardown_runs():
    orchestrator = GenericOrchestrator()

    pipeline = [
        {
            "name": "途中で失敗するセッション",
            "adapter": FAKE_ADAPTER_PATH,
            "params": {},
            "steps": [
                {"action": "step1", "params": {"execute_should_raise": True}},
                {"action": "step2", "params": {}},
            ],
        }
    ]

    result = asyncio.run(orchestrator.execute(pipeline))

    assert result is False
    # step1で例外 -> step2は実行されないが、withを抜けるのでteardownは呼ばれる
    assert FakePipelineAdapter.events == ["setup", "execute:step1", "teardown"]


def test_execute_stops_before_any_step_when_pipeline_has_invalid_adapter():
    # registry.validate_pipeline()による事前検証: 1つでも不正なadapterがあれば、
    # 正常なステップも含めて何一つ実行されない（実行途中で一部だけ実行済み、を防ぐ）
    FakePipelineAdapter.events.clear()
    orchestrator = GenericOrchestrator()

    pipeline = [
        {
            "name": "正常なステップ（本来は実行されるはず）",
            "adapter": FAKE_ADAPTER_PATH,
            "action": "do_something",
            "params": {},
        },
        {
            "name": "不正なadapter指定",
            "adapter": "builtins.dict",
            "action": "do_something",
            "params": {},
        },
    ]

    result = asyncio.run(orchestrator.execute(pipeline))

    assert result is False
    # 正常なステップも含めて、setupすら1度も呼ばれていない
    assert FakePipelineAdapter.events == []


def test_execute_mixes_legacy_and_steps_format_in_same_pipeline():
    orchestrator = GenericOrchestrator()

    pipeline = [
        {
            "name": "従来形式ステップ",
            "adapter": FAKE_ADAPTER_PATH,
            "action": "legacy_action",
            "params": {},
        },
        {
            "name": "steps形式セッション",
            "adapter": FAKE_ADAPTER_PATH,
            "params": {},
            "steps": [{"action": "new_action", "params": {}}],
        },
    ]

    result = asyncio.run(orchestrator.execute(pipeline))

    assert result is True
    assert FakePipelineAdapter.events == [
        "setup",
        "execute:legacy_action",
        "teardown",
        "setup",
        "execute:new_action",
        "teardown",
    ]
