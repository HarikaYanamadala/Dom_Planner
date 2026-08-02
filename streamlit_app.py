"""Nestlé DOM — Planner View (Streamlit + Gemini)

Reads solver output JSON produced by the notebook, shows recommended
reassignments with AI-generated plain-English explanations for planners.

Run locally:      streamlit run streamlit_app.py
Deploy:           push to GitHub, connect at https://share.streamlit.io
"""

import json
import io
from datetime import datetime

import streamlit as st
import pandas as pd

# =========================================================================
# Page configuration
# =========================================================================

st.set_page_config(
    page_title="Nestlé DOM Planner View",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =========================================================================
# Demo data (used when nothing is uploaded — app is usable out of the box)
# =========================================================================

DEMO_DATA = {
    "meta": {
        "current_date": "2024-06-17",
        "n_orders_reviewed": 5,
        "n_qubits": 20,
        "certified_optimum": 982777,
        "generated_at": "2026-08-01T00:00:00",
    },
    "comparison": [
        {"solver": "Baseline 1: default DC", "profit": 118065, "gap_pct": 87.99,
         "fill_rate": 0.086, "diverts": 0, "precision": 0.0, "recall": 0.0, "f1": 0.0,
         "runtime_s": 0.01},
        {"solver": "Baseline 2: greedy", "profit": 980970, "gap_pct": 0.18,
         "fill_rate": 0.888, "diverts": 4, "precision": 1.0, "recall": 0.8, "f1": 0.889,
         "runtime_s": 0.02},
        {"solver": "QAOA (quantum)", "profit": 982777, "gap_pct": 0.00,
         "fill_rate": 0.890, "diverts": 5, "precision": 1.0, "recall": 1.0, "f1": 1.0,
         "runtime_s": 24.3},
        {"solver": "MILP (classical, 7-constraint PoC)", "profit": 980970, "gap_pct": 0.18,
         "fill_rate": 0.888, "diverts": 4, "precision": 1.0, "recall": 0.8, "f1": 0.889,
         "runtime_s": 1.2},
    ],
    "orders": [
        {
            "order_id": "8029881894", "default_dc": "5420", "chosen_dc": "5641",
            "action": "divert", "revenue_delta": 42000, "freight_delta": 600,
            "penalty_delta": -8000, "fill_before_pct": 50, "fill_after_pct": 95,
            "cases_demanded": 2422, "profit_delta": 49400,
        },
        {
            "order_id": "8029889814", "default_dc": "5410", "chosen_dc": "5420",
            "action": "divert", "revenue_delta": 87000, "freight_delta": -1200,
            "penalty_delta": -15000, "fill_before_pct": 45, "fill_after_pct": 98,
            "cases_demanded": 7372, "profit_delta": 103200,
        },
        {
            "order_id": "8029884906", "default_dc": "5410", "chosen_dc": "5420",
            "action": "divert", "revenue_delta": 32000, "freight_delta": 400,
            "penalty_delta": -6000, "fill_before_pct": 55, "fill_after_pct": 92,
            "cases_demanded": 3667, "profit_delta": 37600,
        },
        {
            "order_id": "8029495964", "default_dc": "5410", "chosen_dc": "5490",
            "action": "divert", "revenue_delta": 51000, "freight_delta": 900,
            "penalty_delta": -11000, "fill_before_pct": 40, "fill_after_pct": 96,
            "cases_demanded": 5714, "profit_delta": 61100,
        },
        {
            "order_id": "8029597603", "default_dc": "5083", "chosen_dc": "5420",
            "action": "divert", "revenue_delta": 8000, "freight_delta": -300,
            "penalty_delta": -2500, "fill_before_pct": 60, "fill_after_pct": 100,
            "cases_demanded": 1197, "profit_delta": 10800,
        },
    ],
}

# =========================================================================
# AI explanation via Gemini (falls back to rule-based when no key)
# =========================================================================

def build_prompt(order):
    """Turn an order's impact numbers into a prompt for Gemini."""
    return f"""You are a Nestlé supply chain planner. Explain in ONE sentence (max 35 words)
why the following order should be diverted. Use plain business language. Do NOT say "the
model" or "the algorithm" — speak as an analyst would to a colleague.

Facts:
- Order: {order['order_id']}
- Currently assigned to DC: {order['default_dc']}
- Recommended DC: {order['chosen_dc']}
- Cases in this order: {order['cases_demanded']:,}
- Fill rate: {order['fill_before_pct']}% → {order['fill_after_pct']}%
- Revenue impact: ${order['revenue_delta']:+,.0f}
- Freight impact: ${order['freight_delta']:+,.0f}
- Penalty avoided: ${-order['penalty_delta']:,.0f}
- Net profit change: ${order['profit_delta']:+,.0f}

Focus on the single biggest reason (usually the largest dollar impact). Be direct."""


def generate_ai_explanation(order, api_key):
    """Call Gemini to explain a recommended divert."""
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(build_prompt(order))
        return response.text.strip()
    except ImportError:
        return "Install google-generativeai to enable AI explanations."
    except Exception as e:
        return f"Gemini API error: {e}. Falling back to rule-based explanation.\n\n" + \
               generate_rule_based_explanation(order)


def generate_rule_based_explanation(order):
    """Fallback: template-based explanation when no API key is provided."""
    fill_lift = order['fill_after_pct'] - order['fill_before_pct']
    biggest_gain = max(
        ("revenue", order['revenue_delta']),
        ("penalty avoidance", -order['penalty_delta']),
        key=lambda kv: abs(kv[1]),
    )
    reason = biggest_gain[0]
    if reason == "revenue":
        return (f"Reassign to DC {order['chosen_dc']}: fill rate lifts from "
                f"{order['fill_before_pct']}% to {order['fill_after_pct']}% "
                f"(+{fill_lift} pp), unlocking ${order['revenue_delta']:,.0f} in revenue "
                f"that would otherwise be lost.")
    else:
        return (f"Reassign to DC {order['chosen_dc']}: avoids "
                f"${-order['penalty_delta']:,.0f} in shortfall penalties "
                f"by lifting fill from {order['fill_before_pct']}% to "
                f"{order['fill_after_pct']}%.")

# =========================================================================
# Session state — cache explanations so buttons don't re-hit the API
# =========================================================================

if "explanations" not in st.session_state:
    st.session_state.explanations = {}

# =========================================================================
# Sidebar — settings and data source
# =========================================================================

with st.sidebar:
    st.markdown("### 🚚 Nestlé DOM Planner")
    st.caption("WISER 2026 · Deliverable 6")

    st.markdown("---")
    st.markdown("**AI explanations**")

    # Auto-pull the API key from Streamlit secrets when deployed
    # (Set GEMINI_API_KEY in Streamlit Cloud → Settings → Secrets)
    try:
        default_key = st.secrets.get("GEMINI_API_KEY", "")
    except Exception:
        default_key = ""

    api_key = st.text_input(
        "Google Gemini API key",
        type="password",
        value=default_key,
        help="Get one free at https://ai.google.dev/ — no card required. "
             "Leave blank to use rule-based fallback.",
    )
    if not api_key:
        st.caption("⚠️  No key → rule-based explanations")
    elif default_key:
        st.caption("✅ Using Gemini (from deployment secrets)")
    else:
        st.caption("✅ Using Gemini")

    st.markdown("---")
    st.markdown("**Data source**")
    data_source = st.radio(
        "Choose one:",
        ["Demo data", "Upload solver_output.json"],
        label_visibility="collapsed",
    )
    solver_data = None
    if data_source == "Upload solver_output.json":
        uploaded = st.file_uploader(
            "Export from the notebook (see §11 in the ipynb).",
            type="json",
        )
        if uploaded:
            try:
                solver_data = json.load(uploaded)
                st.success(f"Loaded {len(solver_data.get('orders', []))} orders")
            except Exception as e:
                st.error(f"Couldn't parse: {e}")
        else:
            st.info("Upload the JSON, or switch to demo data above.")
    if solver_data is None and data_source == "Demo data":
        solver_data = DEMO_DATA

    st.markdown("---")
    st.caption(f"Generated: {solver_data['meta']['generated_at'][:10] if solver_data else '—'}")

# =========================================================================
# Main area — header + summary metrics
# =========================================================================

st.title("Recommended Reassignments")
st.caption(f"Planning date: **{solver_data['meta']['current_date']}** · "
           f"{solver_data['meta']['n_orders_reviewed']} focus orders reviewed")

# Metrics row
total_divert_upside = sum(o['profit_delta'] for o in solver_data['orders']
                          if o['action'] == 'divert')
n_diverts = sum(1 for o in solver_data['orders'] if o['action'] == 'divert')
avg_fill_lift = (sum(o['fill_after_pct'] - o['fill_before_pct']
                     for o in solver_data['orders']) /
                 max(len(solver_data['orders']), 1))

m1, m2, m3, m4 = st.columns(4)
m1.metric("Additional profit if approved", f"${total_divert_upside:,.0f}")
m2.metric("Diverts recommended", f"{n_diverts} of {len(solver_data['orders'])}")
m3.metric("Average fill lift", f"+{avg_fill_lift:.0f} pp")
m4.metric("Certified optimum", f"${solver_data['meta']['certified_optimum']:,.0f}")

# =========================================================================
# Comparison table (solver bakeoff)
# =========================================================================

with st.expander("Solver comparison (technical detail)", expanded=False):
    st.caption("How each solver did against the certified optimum on this subinstance.")
    cmp_df = pd.DataFrame(solver_data['comparison'])
    cmp_df["profit"] = cmp_df["profit"].apply(lambda v: f"${v:,.0f}")
    cmp_df["gap_pct"] = cmp_df["gap_pct"].apply(lambda v: f"{v:.2f}%")
    cmp_df["fill_rate"] = cmp_df["fill_rate"].apply(lambda v: f"{v:.1%}")
    cmp_df["runtime_s"] = cmp_df["runtime_s"].apply(lambda v: f"{v:.2f}s")
    for col in ("precision", "recall", "f1"):
        cmp_df[col] = cmp_df[col].apply(lambda v: f"{v:.2f}")
    st.dataframe(cmp_df, use_container_width=True, hide_index=True)

# =========================================================================
# Per-order recommendations
# =========================================================================

st.markdown("### Per-order recommendations")

for order in solver_data['orders']:
    action_label = {"divert": "🔄 DIVERT", "keep": "✓ KEEP", "drop": "⚠ DO NOT SHIP"}[order['action']]
    with st.container(border=True):
        top_cols = st.columns([2, 2, 3, 1.5])
        top_cols[0].markdown(f"**Order ...{order['order_id'][-6:]}**")
        top_cols[0].caption(f"{order['cases_demanded']:,} cases")

        top_cols[1].markdown(f"**{order['default_dc']} → {order['chosen_dc']}**")
        top_cols[1].caption(action_label)

        with top_cols[2]:
            impact_cols = st.columns(3)
            impact_cols[0].metric(
                "Revenue",
                f"${order['revenue_delta']:+,.0f}",
                delta_color="normal" if order['revenue_delta'] > 0 else "inverse",
            )
            impact_cols[1].metric(
                "Freight",
                f"${order['freight_delta']:+,.0f}",
                delta_color="inverse" if order['freight_delta'] > 0 else "normal",
            )
            impact_cols[2].metric(
                "Fill rate",
                f"{order['fill_after_pct']}%",
                f"+{order['fill_after_pct'] - order['fill_before_pct']} pp",
            )

        with top_cols[3]:
            explain_key = f"explain_{order['order_id']}"
            if st.button("💡 Explain", key=explain_key, use_container_width=True):
                with st.spinner("Thinking..."):
                    if api_key:
                        st.session_state.explanations[order['order_id']] = \
                            generate_ai_explanation(order, api_key)
                    else:
                        st.session_state.explanations[order['order_id']] = \
                            generate_rule_based_explanation(order)

        # Show cached explanation if present
        if order['order_id'] in st.session_state.explanations:
            st.info(st.session_state.explanations[order['order_id']])

# =========================================================================
# Bulk-explain button — generate all at once
# =========================================================================

with st.container():
    col1, col2 = st.columns([1, 3])
    if col1.button("💡 Explain all orders", use_container_width=True):
        with st.spinner(f"Generating {len(solver_data['orders'])} explanations..."):
            for order in solver_data['orders']:
                if order['order_id'] not in st.session_state.explanations:
                    if api_key:
                        st.session_state.explanations[order['order_id']] = \
                            generate_ai_explanation(order, api_key)
                    else:
                        st.session_state.explanations[order['order_id']] = \
                            generate_rule_based_explanation(order)
        st.rerun()

    if col2.button("🗑 Clear explanations", use_container_width=True):
        st.session_state.explanations = {}
        st.rerun()

# =========================================================================
# Downloadable HTML planner view
# =========================================================================

def render_planner_html(data, explanations):
    """One-page HTML report a planner can print or email."""
    order_rows = "".join([
        f"""
        <tr>
          <td>...{o['order_id'][-6:]}</td>
          <td class="mono">{o['default_dc']} → {o['chosen_dc']}</td>
          <td class="num">{o['fill_before_pct']}% → <strong>{o['fill_after_pct']}%</strong></td>
          <td class="num"><span class="gain">+${o['profit_delta']:,.0f}</span></td>
          <td>{explanations.get(o['order_id'], '—')}</td>
        </tr>"""
        for o in data['orders']
    ])
    total_gain = sum(o['profit_delta'] for o in data['orders'])
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Nestlé DOM Planner View</title>
<style>
  body {{ font: 14px/1.5 system-ui, sans-serif; color: #1a1a1a;
         max-width: 1000px; margin: 32px auto; padding: 0 24px; background: #faf8f4; }}
  h1 {{ font-size: 22px; margin-bottom: 4px; }}
  .lede {{ color: #666; font-size: 13px; margin-bottom: 24px; }}
  .kpis {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 20px; }}
  .kpi {{ background: white; padding: 12px 14px; border: 1px solid #d8d4cc; border-radius: 4px; }}
  .kpi .label {{ font-size: 10px; text-transform: uppercase; color: #666; letter-spacing: .04em; }}
  .kpi .value {{ font-size: 20px; font-weight: 600; margin-top: 2px; }}
  table {{ width: 100%; background: white; border-collapse: collapse; font-size: 13px; }}
  th, td {{ padding: 8px 10px; text-align: left; border-bottom: 1px solid #d8d4cc; vertical-align: top; }}
  th {{ background: #efece6; font-size: 11px; text-transform: uppercase;
        letter-spacing: .04em; color: #666; }}
  td.mono {{ font-family: SF Mono, Menlo, monospace; }}
  td.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  .gain {{ color: #167a3a; font-weight: 600; }}
  footer {{ margin-top: 24px; padding-top: 12px; border-top: 1px solid #d8d4cc;
            font-size: 11px; color: #666; }}
</style>
</head><body>
<h1>Distributed Order Management — Recommended Reassignments</h1>
<div class="lede">Planning date <strong>{data['meta']['current_date']}</strong>.
{data['meta']['n_orders_reviewed']} focus orders reviewed. Prepared by the WISER 2026 QAOA arm.</div>

<div class="kpis">
  <div class="kpi"><div class="label">Additional profit if approved</div>
       <div class="value">+${total_gain:,.0f}</div></div>
  <div class="kpi"><div class="label">Diverts recommended</div>
       <div class="value">{sum(1 for o in data['orders'] if o['action']=='divert')}
       of {len(data['orders'])}</div></div>
  <div class="kpi"><div class="label">Certified optimum</div>
       <div class="value">${data['meta']['certified_optimum']:,.0f}</div></div>
  <div class="kpi"><div class="label">Report generated</div>
       <div class="value">{datetime.now().strftime('%Y-%m-%d')}</div></div>
</div>

<table>
  <thead><tr><th>Order</th><th>Default → Recommended</th><th style="text-align:right">Fill</th>
             <th style="text-align:right">Profit gain</th><th>Why</th></tr></thead>
  <tbody>{order_rows}</tbody>
</table>

<footer>Nestlé DOM · WISER Quantum+AI 2026 · Solver: QAOA + MILP + Baselines</footer>
</body></html>"""

st.markdown("---")
st.markdown("### Export for planner sign-off")
html = render_planner_html(solver_data, st.session_state.explanations)
st.download_button(
    "📄 Download planner view (HTML)",
    data=html,
    file_name=f"planner_view_{solver_data['meta']['current_date']}.html",
    mime="text/html",
    use_container_width=False,
)
st.caption("Print-friendly one-pager including all AI explanations shown above.")

# =========================================================================
# Footer
# =========================================================================

st.markdown("---")
st.caption("Built for the Nestlé <> WISER Quantum+AI 2026 Challenge. "
           "Model-agnostic: works with QAOA, MILP, or any solver whose output "
           "matches the notebook's export schema.")
