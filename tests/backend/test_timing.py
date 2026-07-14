"""
Tests unitaires : ai_engine/services/timing.py (instrumentation du pipeline d'analyse IA).
"""
import logging

from ai_engine.services.timing import StepTimer, estimate_tokens, log_step


def test_estimate_tokens_uses_four_chars_per_token_heuristic():
    assert estimate_tokens("a" * 400) == 100


def test_estimate_tokens_never_returns_zero_for_non_empty_text():
    assert estimate_tokens("a") == 1


def test_step_timer_elapsed_is_non_negative_and_monotonic():
    timer = StepTimer()
    first = timer.elapsed()
    second = timer.elapsed()
    assert first >= 0
    assert second >= first


def test_log_step_emits_structured_pipeline_log(caplog):
    with caplog.at_level(logging.INFO, logger="ai_engine.timing"):
        log_step("prompt_build", 0.123, system_chars=100, user_chars=50)

    assert len(caplog.records) == 1
    message = caplog.records[0].getMessage()
    assert "[PIPELINE]" in message
    assert "step=prompt_build" in message
    assert "duration=0.123s" in message
    assert "system_chars=100" in message
    assert "user_chars=50" in message
