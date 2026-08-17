from unittest.mock import MagicMock
from orchestrator.orchestrator import Orchestrator


def test_orchestrator_execute_when_ready():
    mock_adapter = MagicMock()
    mock_adapter_context = MagicMock()
    mock_adapter_context.check_device_status.return_value = "READY"
    mock_adapter.__enter__.return_value = mock_adapter_context

    orchestrator = Orchestrator(adapter=mock_adapter)
    result = orchestrator.execute()

    assert result is True
    mock_adapter_context.check_device_status.assert_called_once()

def test_orchestrator_execute_when_not_ready():
    mock_adapter = MagicMock()
    mock_adapter_context = MagicMock()
    mock_adapter_context.check_device_status.return_value = "NOT_READY"
    mock_adapter.__enter__.return_value = mock_adapter_context

    orchestrator = Orchestrator(adapter=mock_adapter)
    result = orchestrator.execute()

    assert result is False
    mock_adapter_context.check_device_status.assert_called_once()

def test_orchestrator_execute_when_exception_raised():
    mock_adapter = MagicMock()
    mock_adapter_context = MagicMock()
    mock_adapter_context.check_device_status.side_effect = Exception("mock_adapter/Error発生")
    mock_adapter.__enter__.return_value = mock_adapter_context

    orchestrator = Orchestrator(adapter=mock_adapter)
    result = orchestrator.execute()

    assert result is False
    mock_adapter_context.check_device_status.assert_called_once()
