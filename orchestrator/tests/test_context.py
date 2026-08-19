import asyncio

from orchestrator.context import Context
from orchestrator.orchestrator import GenericOrchestrator
from orchestrator_test_support.fake_pipeline_adapter import FakePipelineAdapter

FAKE_ADAPTER_PATH = "orchestrator_test_support.fake_pipeline_adapter.FakePipelineAdapter"


def test_context_record_and_last_result_for():
    context = Context()

    context.record(name="ステップA", action="capture", result={"status": "SUCCESS", "n": 1})
    context.record(name="ステップB", action="capture", result={"status": "SUCCESS", "n": 2})

    assert len(context.history) == 2
    # last_result_forは「直近」を返す -> 2件目
    assert context.last_result_for("capture") == {"status": "SUCCESS", "n": 2}


def test_context_last_result_for_returns_none_when_not_found():
    context = Context()
    assert context.last_result_for("未実行のaction") is None


def test_execute_records_history_for_legacy_format():
    FakePipelineAdapter.events.clear()
    orchestrator = GenericOrchestrator()

    pipeline = [
        {
            "name": "従来形式ステップ",
            "adapter": FAKE_ADAPTER_PATH,
            "action": "do_something",
            "params": {},
        }
    ]

    asyncio.run(orchestrator.execute(pipeline))

    assert len(orchestrator.context.history) == 1
    entry = orchestrator.context.history[0]
    assert entry.name == "従来形式ステップ"
    assert entry.action == "do_something"
    assert entry.result == {"status": "SUCCESS", "action": "do_something"}


def test_execute_records_history_for_steps_format_without_overwriting():
    FakePipelineAdapter.events.clear()
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

    asyncio.run(orchestrator.execute(pipeline))

    # 同じnameでも2件とも履歴に残る（上書きされない）
    assert len(orchestrator.context.history) == 2
    assert [entry.action for entry in orchestrator.context.history] == ["step1", "step2"]
    assert all(entry.name == "連続実行セッション" for entry in orchestrator.context.history)


def test_execute_resets_context_between_calls():
    FakePipelineAdapter.events.clear()
    orchestrator = GenericOrchestrator()

    pipeline = [
        {
            "name": "ステップ",
            "adapter": FAKE_ADAPTER_PATH,
            "action": "do_something",
            "params": {},
        }
    ]

    asyncio.run(orchestrator.execute(pipeline))
    assert len(orchestrator.context.history) == 1

    # 2回目の実行では前回の履歴が引き継がれず、リセットされる
    asyncio.run(orchestrator.execute(pipeline))
    assert len(orchestrator.context.history) == 1
