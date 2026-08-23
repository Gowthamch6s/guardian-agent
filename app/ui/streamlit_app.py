"""Streamlit demo: a chat tab with a live guardrail trace, plus an eval-history
dashboard tab -- the point of both is to make "continuously evaluated and
guardrailed" *visible* rather than something you have to take on trust from
a green CI checkmark.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# `streamlit run` puts this file's own directory on sys.path, and file reads
# below are relative to the process's cwd -- neither is guaranteed to be the
# repo root depending on how/where `streamlit run` was launched from. Resolve
# everything off this file's own location instead of trusting either one.
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

import streamlit as st

from app.agent.graph import run_agent
from app.agent.tools import list_account_ids

st.set_page_config(page_title="Guardian", page_icon="🛡️", layout="wide")

BASELINE_PATH = REPO_ROOT / "app/eval/baseline_metrics.json"
LATEST_METRICS_PATH = REPO_ROOT / "eval_results/guardrail_metrics.json"
RESULTS_MD_PATH = REPO_ROOT / "eval_results/RESULTS.md"

METRIC_LABELS = {
    "pass_rate": "Overall pass rate",
    "avg_faithfulness": "Avg. faithfulness (LLM-judge)",
    "adversarial_block_rate": "Adversarial block rate",
    "benign_false_refusal_rate": "Benign false-refusal rate",
    "policy_gate_accuracy": "Policy-gate accuracy",
}

chat_tab, eval_tab = st.tabs(["Chat with Guardian", "Eval Dashboard"])

with chat_tab:
    st.title("Guardian — Banking Ops Assistant")
    st.caption("Every reply below passes through the same input/output guardrails and policy gate as the CI eval suite.")

    account_id = st.selectbox("Account", options=list_account_ids())
    user_message = st.text_area("Message", placeholder="e.g. What's my balance?")

    if st.button("Send", type="primary") and user_message.strip():
        with st.spinner("Guardian is thinking..."):
            state = run_agent(account_id=account_id, user_message=user_message)

        st.markdown("#### Response")
        st.info(state.final_response)

        cols = st.columns(4)
        cols[0].metric("Intent", state.intent or "-")
        cols[1].metric("Blocked", "Yes" if state.blocked else "No")
        cols[2].metric("Needs human approval", "Yes" if state.requires_human_approval else "No")
        cols[3].metric("Block reason", state.block_reason or "-")

        with st.expander("Guardrail trace (what ran, and why)", expanded=True):
            for entry in state.guardrail_trace:
                icon = "🔴" if entry["outcome"] == "fired" else "🟢"
                st.write(f"{icon} **{entry['guardrail']}** — {entry['outcome']}" + (f" ({entry['detail']})" if entry["detail"] else ""))

with eval_tab:
    st.title("Continuous Eval Dashboard")
    st.caption("The same numbers app/eval/gate.py checks in CI, read from the most recent local eval run.")

    if not LATEST_METRICS_PATH.exists():
        st.warning(
            "No eval run found yet. Run `python -m app.eval.run_eval && python -m app.eval.guardrail_metrics` "
            "locally (needs Ollama running) to populate this dashboard."
        )
    else:
        latest = json.loads(LATEST_METRICS_PATH.read_text(encoding="utf-8"))
        baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8")) if BASELINE_PATH.exists() else {}

        cols = st.columns(len(METRIC_LABELS))
        for col, (key, label) in zip(cols, METRIC_LABELS.items()):
            value = latest.get(key)
            base = baseline.get(key)
            delta = None if (value is None or base is None) else round(value - base, 3)
            col.metric(label, f"{value:.2%}" if value is not None else "-", delta=delta)

        if RESULTS_MD_PATH.exists():
            with st.expander("Per-case results"):
                st.markdown(RESULTS_MD_PATH.read_text(encoding="utf-8"))
