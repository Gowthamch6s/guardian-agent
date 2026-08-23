import json

from app.eval.guardrail_metrics import compute_guardrail_metrics

GOLDEN_SET = [
    {"id": "b1", "category": "benign"},
    {"id": "b2", "category": "benign"},
    {"id": "i1", "category": "injection"},
    {"id": "i2", "category": "injection"},
    {"id": "f1", "category": "faithfulness_trap"},
]


def _write(tmp_path, results):
    results_path = tmp_path / "results.json"
    golden_path = tmp_path / "golden_set.json"
    results_path.write_text(json.dumps(results), encoding="utf-8")
    golden_path.write_text(json.dumps(GOLDEN_SET), encoding="utf-8")
    return results_path, golden_path


def test_perfect_run_has_full_block_rate_and_zero_false_refusal(tmp_path):
    results = {
        "aggregate": {"pass_rate": 1.0, "avg_faithfulness": 0.95},
        "cases": [
            {"case_id": "b1", "extra_metrics": {"blocked": 0.0, "correct": 1.0}},
            {"case_id": "b2", "extra_metrics": {"blocked": 0.0, "correct": 1.0}},
            {"case_id": "i1", "extra_metrics": {"blocked": 1.0, "correct": 1.0}},
            {"case_id": "i2", "extra_metrics": {"blocked": 1.0, "correct": 1.0}},
            {"case_id": "f1", "extra_metrics": {"blocked": 0.0, "correct": 0.0}},
        ],
    }
    results_path, golden_path = _write(tmp_path, results)
    metrics = compute_guardrail_metrics(results_path, golden_path)

    assert metrics["adversarial_block_rate"] == 1.0
    assert metrics["benign_false_refusal_rate"] == 0.0
    # faithfulness_trap has no should_block/should_require_approval assertion,
    # so it must not drag policy_gate_accuracy down even though correct=0.0.
    assert metrics["policy_gate_accuracy"] == 1.0


def test_missed_injection_lowers_block_rate(tmp_path):
    results = {
        "aggregate": {"pass_rate": 0.8, "avg_faithfulness": 0.9},
        "cases": [
            {"case_id": "i1", "extra_metrics": {"blocked": 1.0, "correct": 1.0}},
            {"case_id": "i2", "extra_metrics": {"blocked": 0.0, "correct": 0.0}},
        ],
    }
    results_path, golden_path = _write(tmp_path, results)
    metrics = compute_guardrail_metrics(results_path, golden_path)

    assert metrics["adversarial_block_rate"] == 0.5


def test_false_refusal_on_benign_case_is_captured(tmp_path):
    results = {
        "aggregate": {"pass_rate": 0.5, "avg_faithfulness": 0.9},
        "cases": [
            {"case_id": "b1", "extra_metrics": {"blocked": 1.0, "correct": 0.0}},
            {"case_id": "b2", "extra_metrics": {"blocked": 0.0, "correct": 1.0}},
        ],
    }
    results_path, golden_path = _write(tmp_path, results)
    metrics = compute_guardrail_metrics(results_path, golden_path)

    assert metrics["benign_false_refusal_rate"] == 0.5
