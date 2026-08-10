"""
Tests for the failure-event consumer wiring added to startup_event
(2026-08-10 Stage 3 close-out).

FailureConsumer and DLQRemediationConsumer existed as handler classes
since Stage 3 first landed, but nothing ever connected either to RabbitMQ
or started consuming - see OS42_REPAIR_PLAN.md's Stage 3 reconciliation
notes. No real RabbitMQ/Redis/Postgres is available in this environment,
so every external connection is mocked here; this verifies the wiring
LOGIC (which consumers get created, which event types each is registered
for, that the DLQ consumer's publisher gets set, that both get connected
and started as background tasks) rather than a live end-to-end run
against real infrastructure - that's explicitly still needed per
STAGE3_COMPLETION_REPORT.md's own "What's Still Needed" list.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import app.main as main_module


def _mock_event_consumer() -> MagicMock:
    """EventConsumer.register_handler is sync in the real class; only
    connect/disconnect/start_consuming are async - mismatching that with a
    blanket AsyncMock would leave register_handler's return value an
    unawaited coroutine (harmless for assertions, but a noisy warning)."""
    m = MagicMock()
    m.connect = AsyncMock()
    m.disconnect = AsyncMock()
    m.start_consuming = AsyncMock()
    return m


@pytest.mark.asyncio
async def test_startup_wires_both_failure_consumers():
    failure_consumer_mock = _mock_event_consumer()
    dlq_consumer_mock = _mock_event_consumer()
    publisher_mock = MagicMock()
    publisher_mock.connect = AsyncMock()
    publisher_mock.disconnect = AsyncMock()

    with patch("app.main.RedisStateStore") as MockRedis, \
         patch("app.main.PostgresStateStore") as MockPostgres, \
         patch("app.main.TransitionEmitter") as MockEmitter, \
         patch("app.main.EventConsumer", side_effect=[failure_consumer_mock, dlq_consumer_mock]), \
         patch("app.main.EventPublisher", return_value=publisher_mock), \
         patch("app.main.DLQRemediationConsumer") as MockDLQConsumer, \
         patch.object(main_module, "_consumer_tasks", []):

        MockRedis.return_value.connect = AsyncMock()
        MockPostgres.return_value.connect = AsyncMock()
        MockEmitter.return_value.connect = AsyncMock()
        dlq_handler_mock = MockDLQConsumer.return_value

        await main_module.startup_event()
        await asyncio.sleep(0)  # let the newly created consumer tasks run once

        # Failure consumer: registered for both event types it should handle
        registered_types = [c.args[0] for c in failure_consumer_mock.register_handler.call_args_list]
        assert "failure.detected" in registered_types
        assert "failure.recovered" in registered_types

        # DLQ remediation consumer: registered for failure.detected only
        dlq_registered_types = [c.args[0] for c in dlq_consumer_mock.register_handler.call_args_list]
        assert dlq_registered_types == ["failure.detected"]

        # DLQ handler's publisher wired to the real EventPublisher instance -
        # this is exactly the assignment that was missing before this fix
        # (DLQRemediationConsumer.publisher defaults to None).
        assert dlq_handler_mock.publisher is publisher_mock

        # Both consumers and the publisher actually connected
        failure_consumer_mock.connect.assert_awaited_once()
        dlq_consumer_mock.connect.assert_awaited_once()
        publisher_mock.connect.assert_awaited_once()

        # Both started consuming as background tasks, not awaited inline
        # (start_consuming() runs an internal loop that would otherwise
        # block startup_event from ever returning)
        assert len(main_module._consumer_tasks) == 2
        for task in main_module._consumer_tasks:
            assert isinstance(task, asyncio.Task)

        # Cleanup while the patched _consumer_tasks list is still the active
        # one (patch.object restores the original, empty list on __exit__,
        # so this has to happen before the `with` block ends).
        for task in main_module._consumer_tasks:
            task.cancel()
