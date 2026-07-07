# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# Copyright (c) 2026 ScyllaDB

"""Regression tests for the SCT-440 bounded-delivery ArgusEventPostman fix.

SCT-440: at teardown a queued Severity.ERROR failure event was silently dropped
because the inherited BaseEventsProcess.stop() only sets stop_event and joins the
thread — it never drains the aggregator's outbound_queue. The fix adds a stop()
override on ArgusEventPostman that drains pending events (ERROR/CRITICAL first)
before an honest bounded join.
"""

import time
import logging
import threading
import unittest.mock

import pytest
import requests

from sdcm.sct_events import Severity
from sdcm.sct_events.argus import ArgusEventAggregator, ArgusEventPostman
from sdcm.sct_events.events_processes import EVENTS_ARGUS_AGGREGATOR_ID, EventsProcessesRegistry


def _argus_event(severity: Severity, event_id: str, message: str) -> dict:
    """Mirror the payload dict ArgusEventCollector builds (sdcm/sct_events/argus.py:55-71).

    ``severity`` is stored as its enum *name* (a string), which is why ERROR/CRITICAL-first
    ordering cannot be a bare string sort.
    """
    return {
        "run_id": "test-run",
        "severity": severity.name,
        "ts": 0.0,
        "duration": None,
        "event_id": event_id,
        "event_type": "TestFrameworkEvent",
        "message": message,
    }


@pytest.fixture
def registry(tmp_path):
    return EventsProcessesRegistry(log_dir=str(tmp_path))


@pytest.fixture
def argus_pipeline(registry):
    """A started-but-not-enabled postman plus a (non-started) aggregator it can resolve.

    The aggregator is registered without ``start()`` on purpose: its ``run()`` needs the full
    upstream annotator/main-device pipeline, which is out of scope here — the test only needs its
    ``outbound_queue`` populated. The postman is started so ``stop()``/``join()`` are valid, but
    left disabled so ``run()`` parks on ``enabled.wait()`` and never consumes the queue itself;
    only the stop path (the code under test) may drain it. The Argus client is mocked — no network.
    """
    aggregator = ArgusEventAggregator(_registry=registry)
    registry._registry_dict[EVENTS_ARGUS_AGGREGATOR_ID] = aggregator

    postman = ArgusEventPostman(_registry=registry)
    postman._argus_client = unittest.mock.MagicMock()
    postman.start()
    try:
        yield aggregator, postman
    finally:
        postman.terminate()
        postman.join(timeout=5)


def test_stop_drains_pending_events_error_first(argus_pipeline):
    """SCT-440 reproducer: events queued for delivery must be drained (ERROR-first) on stop().

    On the unfixed code the inherited stop() never drains the aggregator's outbound_queue, so the
    queued ERROR event is silently dropped and submit_event is never called — this test fails.
    The fix's stop() override drains the queue, ERROR/CRITICAL first — then this test passes.
    """
    aggregator, postman = argus_pipeline

    aggregator.outbound_queue.put(_argus_event(Severity.WARNING, "w1", "warn"))
    aggregator.outbound_queue.put(_argus_event(Severity.ERROR, "e1", "boom"))

    postman.stop(timeout=10)

    submitted_ids = [call.args[0]["event_id"] for call in postman._argus_client.submit_event.call_args_list]

    assert "e1" in submitted_ids, "the queued ERROR event was dropped on stop() (SCT-440 regression)"
    assert "w1" in submitted_ids, "the queued WARNING event was dropped on stop()"
    assert submitted_ids.index("e1") < submitted_ids.index("w1"), "ERROR must be drained before WARNING"


def test_stop_bounded_when_submit_hangs(argus_pipeline, monkeypatch):
    """SCT-440 invariant (a): stop() stays bounded even when a submit_event POST hangs forever.

    The bounded-join worker in _submit_with_deadline must abandon (not await) a submit that blocks
    past the deadline, so stop(timeout=10) returns quickly instead of hanging the whole teardown.
    """
    aggregator, postman = argus_pipeline

    monkeypatch.setattr("sdcm.sct_events.argus.ARGUS_POSTMAN_SUBMIT_DEADLINE", 0.2)
    monkeypatch.setattr("sdcm.sct_events.argus.ARGUS_POSTMAN_DRAIN_TIMEOUT", 0.3)

    blocker = threading.Event()  # never set within the test body -> the submit worker blocks forever
    postman._argus_client.submit_event.side_effect = lambda *a, **k: blocker.wait()

    aggregator.outbound_queue.put(_argus_event(Severity.ERROR, "e1", "boom"))

    try:
        started = time.monotonic()
        postman.stop(timeout=10)
        elapsed = time.monotonic() - started

        # The bound IS the proof of abandonment: had stop() awaited the worker it would block on the
        # never-set blocker effectively forever, so a prompt return means the worker was abandoned.
        assert elapsed < 2, f"stop() must abandon (not await) the hung submit worker, took {elapsed:.2f}s"
        assert postman._argus_client.submit_event.called, "the drain must have attempted the submit"
        assert not postman.is_alive(), "the postman thread must be stopped"
    finally:
        blocker.set()  # release the abandoned daemon worker so it exits cleanly


def test_timeout_logged_and_continues(argus_pipeline, monkeypatch, caplog):
    """SCT-440 invariant (c): a submit that raises a timeout is logged (F3 verbose_suppress) and the
    drain advances to the next event -- no new visibility layer, no hang.
    """
    aggregator, postman = argus_pipeline

    monkeypatch.setattr("sdcm.sct_events.argus.ARGUS_POSTMAN_SUBMIT_DEADLINE", 1.0)
    monkeypatch.setattr("sdcm.sct_events.argus.ARGUS_POSTMAN_DRAIN_TIMEOUT", 2.0)

    postman._argus_client.submit_event.side_effect = [requests.exceptions.ReadTimeout("boom"), None]

    aggregator.outbound_queue.put(_argus_event(Severity.ERROR, "e1", "boom"))
    aggregator.outbound_queue.put(_argus_event(Severity.ERROR, "e2", "recovered"))

    caplog.set_level(logging.ERROR, logger="sdcm.sct_events.events_processes")

    postman.stop(timeout=10)

    assert postman._argus_client.submit_event.call_count == 2, (
        "both events must be attempted (drain advanced past the failure)"
    )
    assert any("failed to post" in record.getMessage() for record in caplog.records), (
        "the timeout must be logged via the existing verbose_suppress path"
    )
