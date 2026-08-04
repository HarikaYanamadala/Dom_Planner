# Nestlé DOM - Hybrid QAOA + MILP

WISER Global Quantum+AI Program 2026 - Nestlé × WISER

Challenge 4:Quantum Optimization for Distributed Order Management

Team: **The Convergents**

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
│   ├── requirements.txt               # App dependencies                      
│   └── app.py                         # code for app
│   └── Planner views of each date                        
│
├── notebook/                          # Main runnable notebook
│   └── Nestle_DOM_QAOA_MILP.ipynb
│
├── Report/                            # Full technical report
│   └── Nestle_DOM_Technical_Report.pdf
│   └── The_Convergents_DOM.pptx
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
├── README.md                         
└── requirements.txt                   # Root dependencies for the notebook
```

## Data

The notebook expects 5 input files and 2 optional ground-truth files,
joined on distribution center, SKU, and date:

| File | Contents |
|---|---|
| `input_order_data.csv` | Open orders: order ID, SKU demand, default DC, PGI date, revenue |
| `input_capacity_planning.csv` | Available inventory by DC / SKU / date |
| `input_dock_capacity.csv` | Dock appointment capacity per DC, per date |
| `input_shipping_cost_data.csv` | Shipping cost per (order, candidate DC) pair |
| `input_throughput_capacity.csv` | Case-pick / pallet-pick capacity per DC, per date |
| `output_order_level_data_ground_truth.csv` *(optional)* | Historical planner decisions, order-level |
| `output_order_sku_level_data_ground_truth.csv` *(optional)* | Historical planner decisions, SKU-level |

Data files are not included in this repo (proprietary to the challenge
data pack). Upload them when prompted by the notebook.

## Results

Every solver run exports its results to CSV via a `save_result()` helper built
into the notebook - each date you run gets its own file, and everything also
folds into a cumulative `*_all_dates.csv` per table (re-running a date replaces
just that date's rows, so nothing duplicates). The `Results/` folder here holds
the cumulative files across all 5 target dates:

| File | What's in it |
|---|---|
| `comparison_all_dates.csv` | Objective, gap, fill rate, penalty, shipping, precision/recall/F1 - one row per solver per date |
| `order_level_all_dates.csv` | Order-by-order DC picks, every solver vs. the certified optimum |
| `qubit_scaling_all_dates.csv` | Qubit count and classical search-space size, projected across order counts |
| `robustness_all_dates.csv` | QAOA results across 5 random seeds, per date |
| `robustness_summary_all_dates.csv` | Mean ± std of the above, per solver per date |
| `run_summary_all_dates.csv` | One-row-per-date scalar snapshot (certified optimum, baselines, MILP, QAOA) |
| `noise_study_all_dates.csv` | QAOA constraint-preservation under simulated two-qubit gate error (12-qubit instance) |

## Deliverables / Artifacts

- 📓 [`notebook/Nestle_DOM_QAOA_MILP.ipynb`](notebook/Nestle-DOM-(QAOA+MILP).ipynb) - End-to-end executable notebook
- 📄 [`Report/Nestle_DOM_Technical_Report.pdf`](Report/Nestle-DOM-Technical-Report.pdf) - full technical report (business summary, formulation, results, scaling & noise analysis, key insights)
- 📊 `Results/*.csv` - raw solver outputs backing every chart/table in the report
- 🖥️ **[Interactive Planner View App](#planner-view-app)** - Visual planning interface
- 🖼️ [`Report/The_Convergents_DOM.pptx`](Report/The_Convergents_DOM.pptx)- *Slide Deck - DOM Planner presentation*

## Planner View App
The DOM_Planner App is delivered here as an **interactive
Streamlit app** rather than a static page, so a planner can actually explore the
results instead of just reading a summary.

**🔗 Live app: https://domplanner-convergence.streamlit.app **

**Features and Capabilities:**
- Pick any of the 5 planning dates and drill into that date's results
- Step through each diverted order's details - which DC it moved to and why
- Compare solvers (baselines, QAOA, MILP) side by side with built-in charts
- Read an AI-generated executive summary of that date's results
- See key insights and links back to the project's other deliverables
- **Download a self-contained HTML snapshot of the planner view for any selected date**


Source code, its own setup notes, and app-specific dependencies live in
[`dom-planner-app/`](dom-planner-app/). To run it locally:

```bash
cd dom-planner-app
pip install -r requirements.txt
streamlit run app.py
```

## Running the notebook

1. Open [`notebook/Nestle-DOM-(QAOA+MILP).ipynb`](notebook/Nestle-DOM-(QAOA+MILP).ipynb)
   in Google Colab (or Jupyter with the packages in the root `requirements.txt`
   installed).
2. Place the 7 input CSVs in a Google Drive folder; update `DRIVE_FOLDER` in the
   "Point to the CSVs" cell.
3. In the "Configure and build" cell, set `cfg.current_date` to the planning date
   you want to run (one of the 5 target dates, or any date present in the data).
4. Run all cells top to bottom. Results save automatically to `Results/` under
   your Drive folder.
5. Repeat steps 3–4 for each additional date you want to compare.
6. The notebook's results section reads back everything saved so far and
   builds a cross-date comparison.

## Requirements

- **[`requirements.txt`](requirements.txt)**:
  - `qiskit==2.5.1`, `qiskit-aer==0.17.2` - QAOA circuit construction and simulation
  - `pulp==2.9.0` — MILP formulation, solved via the bundled CBC solver
  - `pandas`, `numpy`, `matplotlib` - data handling and plotting

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

## Team

**The Convergents**

*Harika Yanamadala*

*Induja Bhanu Kodavati*
