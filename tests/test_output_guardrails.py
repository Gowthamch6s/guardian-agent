from app.guardrails.output_guardrails import (
    FAITHFULNESS_BLOCK_THRESHOLD,
    faithfulness_check,
    scrub_pii_from_response,
    toxicity_check,
)


def test_scrub_pii_from_response_masks_card_to_last_four():
    scrubbed, finding = scrub_pii_from_response("Your card 4111111111111111 was charged.")
    assert "4111111111111111" not in scrubbed
    assert "1111" in scrubbed
    assert finding.fired is True


def test_scrub_pii_from_response_no_op_on_clean_text():
    scrubbed, finding = scrub_pii_from_response("Your balance is $42.00.")
    assert scrubbed == "Your balance is $42.00."
    assert finding.fired is False


def test_toxicity_check_fires_on_banned_words():
    assert toxicity_check("Don't be an idiot about it.").fired is True
    assert toxicity_check("Happy to help with that.").fired is False


def test_faithfulness_check_fires_below_threshold_using_fake_judge():
    fake_llm = lambda prompt: '{"faithfulness": 0.1}'
    result = faithfulness_check("balance is $50", "your balance is $50,000", call_llm=fake_llm)
    assert result.score == 0.1
    assert result.finding.fired is True


def test_faithfulness_check_passes_above_threshold_using_fake_judge():
    fake_llm = lambda prompt: '{"faithfulness": 0.95}'
    result = faithfulness_check("balance is $50", "your balance is $50", call_llm=fake_llm)
    assert result.score == 0.95
    assert result.finding.fired is False
    assert result.score >= FAITHFULNESS_BLOCK_THRESHOLD
