"""
ErrorHandler 단위 테스트

특히 새로 추가된 ``track_step_error`` 헬퍼의 동작을 검증한다.
- debug_mode=True 면 예외를 다시 raise 한다
- debug_mode=False 면 첫 max_error_logs 회까지 로그를 남기고 카운트만 증가시킨다
"""

import logging

import pytest
from wicked_zerg_challenger.error_handler import ErrorHandler


class TestTrackStepError:
    def test_debug_mode_reraises(self):
        eh = ErrorHandler(debug_mode=True)
        with pytest.raises(ValueError, match="boom"):
            eh.track_step_error("Subsystem", ValueError("boom"))

    def test_production_mode_swallows_and_counts(self):
        eh = ErrorHandler(debug_mode=False)
        eh.track_step_error("Subsystem", RuntimeError("fail #1"))
        eh.track_step_error("Subsystem", RuntimeError("fail #2"))
        assert eh.error_counts["Subsystem"] == 2

    def test_log_suppression_after_max_logs(self, caplog):
        eh = ErrorHandler(debug_mode=False)
        eh.max_error_logs = 2
        with caplog.at_level(logging.ERROR, logger="ErrorHandler"):
            eh.track_step_error("Spammy", RuntimeError("first"))
            eh.track_step_error("Spammy", RuntimeError("second"))
            eh.track_step_error("Spammy", RuntimeError("third"))
        # First two failures are logged plus a "Suppressing further" notice on the 2nd.
        # The 3rd should NOT add a new "failed" log line.
        failed_logs = [r for r in caplog.records if "Spammy failed" in r.message]
        assert len(failed_logs) == 2
        assert eh.error_counts["Spammy"] == 3

    def test_independent_keys_tracked_separately(self):
        eh = ErrorHandler(debug_mode=False)
        eh.track_step_error("A", RuntimeError("a"))
        eh.track_step_error("B", RuntimeError("b"))
        eh.track_step_error("A", RuntimeError("a2"))
        assert eh.error_counts["A"] == 2
        assert eh.error_counts["B"] == 1

    def test_summary_reflects_tracked_errors(self):
        eh = ErrorHandler(debug_mode=False)
        eh.track_step_error("X", RuntimeError("x"))
        summary = eh.get_error_summary()
        assert summary == {"X": 1}
