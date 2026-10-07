from app.services import _ground_report


def test_report_uses_only_text_and_exact_counts():
    turns = [{"followup": False}] * 5 + [{"followup": True}] * 4
    out = _ground_report({
        "summary": "The answer is relevant. Spoken English is confident. This suggests a listening/processing issue.",
        "strengths": ["Clear technical examples", "Fluent spoken English"],
        "communication_summary": "Excellent pronunciation.",
        "plan_7_days": [{"day": 7, "task": "Practise using the 8 questions from this session."}],
    }, turns)
    assert out["summary"] == "The answer is relevant."
    assert "Spoken English" not in str(out["strengths"])
    assert "8 questions" not in out["plan_7_days"][0]["task"]
    assert "5 main questions and 4 follow-ups" in out["plan_7_days"][0]["task"]
    assert out["session_counts"] == {"main_questions": 5, "followups": 4, "total_answers": 9}
    assert out["evidence_basis"] == "answer_text"
    assert "not assessed" in out["communication_summary"]
