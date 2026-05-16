"""Tests for verifier offline mode. No LLM needed."""
from backend.agents.verifier import verify_offline


def test_keeps_valid_marker():
    answer = "Maç öncesi pasta önerilir [T1]."
    trace = [{"tool": "search_sport_kb", "result": {"text": "pasta pre-match"}}]
    out = verify_offline(answer, trace)
    assert "[T1]" in out["verified_answer"]
    assert out["removed_claims"] == []
    assert out["verification_score"] == 1.0


def test_strips_out_of_bounds_marker():
    answer = "Pasta yiyin [T1]. Kahve için [T9]."  # T9 invalid (only 1 tool called)
    trace = [{"tool": "search_sport_kb", "result": {"text": "pasta"}}]
    out = verify_offline(answer, trace)
    assert "[T1]" in out["verified_answer"]
    assert "[T9]" not in out["verified_answer"]
    assert any("kahve" in c.lower() for c in out["removed_claims"])
    assert out["verification_score"] < 1.0


def test_no_tools_no_markers_passes():
    answer = "Merhaba, sana nasıl yardımcı olabilirim?"
    out = verify_offline(answer, tool_trace=[])
    assert out["verified_answer"] == answer
    assert out["verification_score"] == 1.0


def test_no_tools_with_markers_strips_all():
    answer = "Bu doğru [T1]. Bu da doğru [T2]."
    out = verify_offline(answer, tool_trace=[])
    assert out["verified_answer"] == ""
    assert len(out["removed_claims"]) == 2


def test_empty_answer_returns_empty():
    out = verify_offline("", tool_trace=[])
    assert out["verified_answer"] == ""
    assert out["verification_score"] == 1.0


def test_marker_zero_is_invalid():
    answer = "İddia [T0]."
    trace = [{"tool": "x", "result": {}}]
    out = verify_offline(answer, trace)
    assert out["verified_answer"] == ""
