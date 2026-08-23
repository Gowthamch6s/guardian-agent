# Guardian — Guardrailed & Continuously-Evaluated Banking Ops Agent

Guardian is a LangGraph support/ops assistant for a fictional bank ("Meridian
Bank") that can answer account questions and execute actions with real
consequences (refund a transaction, freeze a card, change contact info) via
mocked tools. The point of the project isn't the agent's capability — it's
everything wrapped around it: input/output guardrails, a deterministic
action-authorization policy, a golden-set eval harness, and a GitHub Actions
CI gate that fails a pull request if the agent's safety/quality metrics
regress.

## Why this exists

Most agent demos show what an LLM agent *can do*. This one is about what has
to be true before you'd trust one with actions that cost real money: that
its behavior is continuously measured, that regressions are caught before
they ship, and that not every guardrail should be another LLM call.

## Architecture

```
input_guardrail -> classify_intent -> [policy_gate ->] tool/faq -> output_guardrail -> finalize
```

- **Input guardrails** (`app/guardrails/input_guardrails.py`): a fast regex
  layer catches obvious prompt-injection phrasing; an LLM classifier catches
  paraphrased attempts the regex misses (only called if the regex didn't
  already fire); PII (SSN/card numbers) is redacted before any LLM call.
- **Action-authorization policy** (`app/guardrails/policies.py`): plain,
  unit-tested business rules — not an LLM call — decide whether a refund,
  card freeze, or contact-info change needs human approval before it
  executes.
- **Output guardrails** (`app/guardrails/output_guardrails.py`): an
  *independent* LLM-judge call (reusing
  [agent-observability-kit](https://github.com/Gowthamch6s/agent-observability-kit)'s
  `LLMJudge`) checks the drafted response for faithfulness against the real
  tool result/policy text before it ships — the agent never grades its own
  answer. A toxicity heuristic and a PII-in-output scrubber run alongside it.

## Continuous evaluation

`app/eval/golden_set.json` is ~35 hand-written cases across categories:
benign requests, prompt-injection/jailbreak attempts, social-engineering
attempts to talk around the policy gate, off-topic asks, messages containing
PII, and "faithfulness trap" questions the policy facts don't actually
cover. `app/eval/run_eval.py` runs every case through the real graph and
scores it with `agent_observability_kit.eval.run_eval` (MLflow-logged,
tagged with the git commit). `app/eval/guardrail_metrics.py` rolls the
per-case results up by category into the numbers that actually matter for a
guardrail system: adversarial block rate, benign false-refusal rate, average
faithfulness, and policy-gate accuracy.

## The CI gate

`app/eval/gate.py` compares a fresh eval run to a committed
`baseline_metrics.json`. One metric — `adversarial_block_rate` — has a hard
floor of 100%, no tolerance. The rest compare to baseline with a small
tolerance band, because LLM-judged scores have run-to-run noise and an
exact-match gate would just be flaky. `.github/workflows/eval-gate.yml` runs
this on every PR and posts the results table as a PR comment;
`.github/workflows/unit-tests.yml` runs the deterministic guardrail/policy
tests (no API key, no LLM calls) on every push.

## Running it locally

```bash
# needs Ollama running locally (https://ollama.com) with a model pulled --
# no API key, no account, no cost:
ollama pull llama3.2

python -m venv .venv && .venv/Scripts/activate  # or source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env  # defaults already point at ollama:llama3.2

pytest tests/ -q                              # deterministic guardrail tests, no LLM needed
python -m app.eval.run_eval                    # runs the golden set through the real agent
python -m app.eval.guardrail_metrics           # rolls results up into guardrail-specific rates
python -m app.eval.gate                        # compares to the committed baseline
streamlit run app/ui/streamlit_app.py          # chat UI with a live guardrail trace + eval dashboard
```

CI (`eval-gate.yml`) installs Ollama fresh on the runner and pulls a smaller
model tag (`llama3.2`) purely for wall-clock time -- no secret to configure,
because there's no API key in this project at all.

## Stack

LangGraph, LangChain, Ollama, Pydantic, MLflow, Streamlit, `agent-observability-kit`.
