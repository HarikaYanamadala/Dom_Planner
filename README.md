# Nestlé DOM — Hybrid QAOA + MILP

Nestlé Distributed Order Management Challenge — Quantum Optimization Solution

Team: **Convergence**

**Live app:** [domplanner-convergence.streamlit.app](https://domplanner-convergence.streamlit.app)

---

## Overview

Nestlé's Distributed Order Management (DOM) problem focuses on selecting
the best alternate distribution center (DC) when the default DC cannot
completely fulfil an order, to maximize fulfilment value while accounting
for shipping costs and penalties associated with unmet demand.

This repository implements the DOM problem as a combinatorial assignment
model and evaluates the performance of four solvers against the brute-force
certified optimal solution.

| Solver | Type | Description |
|---|---|---|
| Baseline 1 | No optimization | Strict default-DC, never diverts |
| Baseline 2 | Heuristic | Greedy sequential divert (≥5% fill or 100-case hurdle) |
| **QAOA** | Quantum (simulated) | XY-mixer QUBO formulation, CVaR-optimized |
| **MILP** | Exact classical | Full 7-constraint PoC formulation (PuLP + CBC) |

The four solvers were evaluated over five planning dates (2024-06-17,
06-19, 06-21, 06-23, and 06-25), using date window and filtered focus
orders. Performance was measured using objective value, optimality gap,
fill rate, runtime, and precision, recall, and F1-score against the
certified-optimum assignment.

## Headline result

QAOA matched the certified optimum on all five planning dates, achieving
an F1-score of 1.00 with a 0% optimality gap. The complete methodology,
experimental results, and noise-sensitivity analysis are presented in the
accompanying technical report.

## Repo structure

```
.
├── dom-planner-app/                   # Interactive planner-view Streamlit app
│   ├── app.py                          # Streamlit app entry point
│   ├── requirements.txt                # App dependencies
│   └── readme.md                       # Component-by-component app documentation
│
├── notebook/                          # Main runnable notebook
│   └── Nestle-DOM-(QAOA+MILP).ipynb
│
├── Report/                            # Full technical report
│   └── Nestle-DOM-Technical-Report.pdf
│
├── Results/                           # Solver outputs across 5 planning dates
│   ├── figures/                        # Figures 1-8 (attached in report)
│   ├── comparison_all_dates.csv
│   ├── order_level_all_dates.csv
│   ├── qubit_scaling_all_dates.csv
│   ├── robustness_all_dates.csv
│   ├── robustness_summary_all_dates.csv
│   ├── run_summary_all_dates.csv
│   └── noise_study_all_dates.csv
│
├── .gitignore
├── README.md                          # This file
└── requirements.txt                   # Root dependencies for the notebook
```

## Data

The notebook expects 5 input files and 2 optional ground-truth files,
joined on distribution center, SKU, and date:

**Required inputs:**
- `input_order_data.csv` — customer orders with material, quantity, and date
- `input_capacity_planning.csv` — DC inventory over time (SKU × DC × date)
- `input_dock_capacity.csv` — DC dock utilization limits (DC × date)
- `input_shipping_cost_data.csv` — freight cost table (ZIP × DC)
- `input_throughput_capacity.csv` — case-pick / pallet-pick throughput (DC × date)

**Optional ground truth (for the §1 planner-history diagnostic):**
- `output_order_level_data_GROUND_TRUTH.csv`
- `output_order_sku_level_data_GROUND_TRUTH.csv`

Data files are not included in this repo (proprietary to the challenge
data pack). Upload them when prompted by the notebook.

## Running the notebook

The notebook is designed for Google Colab:

1. Open `notebook/Nestle-DOM-(QAOA+MILP).ipynb` in Colab
2. Runtime → Run all
3. When prompted, upload the 7 CSV files from the challenge data pack
4. Runtime: ~15 minutes end-to-end on free Colab CPU

Results are saved to `Results/` — CSVs for cumulative outputs and PNGs
for figures.

## Running the app

The Streamlit app renders the notebook's JSON output for planners:

**Live URL:** [domplanner-convergence.streamlit.app](https://domplanner-convergence.streamlit.app)

**Local:**
```bash
cd dom-planner-app
pip install -r requirements.txt
streamlit run app.py
```

See `dom-planner-app/readme.md` for component-by-component documentation.

## Business rules implemented

The optimizer respects the following business rules from Nestlé's PoC
methodology:

- Focus order window: 3-10 days after current date
- Insufficient default-DC inventory filter
- FTL vs LTL classification
- Weekend PGI exclusion (Saturday/Sunday)
- Revised PGI (weekend orders shifted to next Monday)
- 3-day rolling throughput relief
- 5-day forward inventory reserve at alternate DC
- 5% fill-rate increase divert hurdle (or 100 cases minimum)
- Case-pick and pallet-pick capacity constraints
- Dock capacity per DC-date

Rules requiring data not in the challenge pack (regional holiday calendar,
SKU forecast availability at alternate DC) are documented as scope
simplifications in the report.
