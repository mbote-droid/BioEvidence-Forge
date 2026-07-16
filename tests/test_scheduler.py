from threading import Event

from bioevidence.pipeline import RunResult
from bioevidence.reporting import ReportResult
from bioevidence.scheduler import PeriodicRunner
from bioevidence.storage import StorageResult


class Pipeline:
    def __init__(self):
        self.calls = 0

    def run(self, topic):
        self.calls += 1
        return RunResult(topic, 0, StorageResult(0, "x"), ReportResult(None, 0, "x"), "x")


def runner(interval=1):
    return PeriodicRunner(Pipeline(), "topic", interval)


class TestScheduler:
    def test_minimum_interval(self):
        assert runner()._interval_seconds == 60

    def test_interval_converts_minutes(self):
        assert runner(2)._interval_seconds == 120

    def test_run_once_calls_pipeline(self):
        value = runner()
        value.run_once()
        assert value._pipeline.calls == 1

    def test_run_once_returns_topic(self):
        assert runner().run_once().topic == "topic"

    def test_blank_topic_falls_back(self):
        assert PeriodicRunner(Pipeline(), "", 1)._topic == "general biomedical research"

    def test_stopped_runner_does_nothing(self):
        event = Event()
        event.set()
        value = runner()
        value.run_forever(event)
        assert value._pipeline.calls == 0

    def test_callback_gets_result(self):
        event = Event()
        received = []
        value = runner()
        value._interval_seconds = 0
        value.run_forever(event, lambda result: (received.append(result), event.set()))
        assert len(received) == 1

    def test_callback_error_is_contained(self):
        event = Event()
        value = runner()
        value._interval_seconds = 0
        value.run_forever(event, lambda result: (event.set(), (_ for _ in ()).throw(ValueError())))
        assert value._pipeline.calls == 1

    def test_topic_is_retained(self):
        assert runner()._topic == "topic"

    def test_result_message_exists(self):
        assert runner().run_once().message
