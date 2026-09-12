# Q4 Python Code Review

> **Status**: passed_with_warnings
> **Reviewer**: python-code-reviewer
> **Date**: 2026-09-12
> **Scripts reviewed**: `code/problem4.py`, `code/problem2.py`, `code/problem3.py`, `code/forecast.py`, `code/constraint_audit.py`

## Pass Items

1. ✅ `code/problem4.py` uses Attachment 1 fixed prices for the first-day prediction fallback instead of actual day-0 volatile prices.
2. ✅ Q4-2 calls the revised Q2 planner/executor with continuous SOC, explicit curtailment and a final 6000 kWh target.
3. ✅ Q4-3 calls the revised point-prediction rolling routine; its JSON explicitly states that the method is not stochastic MPC.
4. ✅ `code/constraint_audit.py` re-opened `result4-2.xlsx` and `result4-3.xlsx` and reported 23 and 26 checks respectively, both with 0 failures.
5. ✅ Q4-2/Q4-3 exact trace balance residuals are below $2\times10^{-9}$ kWh, year-end SOC is 6000 kWh, and `max(min(c,s))=0`.
6. ✅ Known-price and predicted-price totals were both rerun and saved: 14766939.34 and 14841188.78 yuan; their difference is 74249.44 yuan.
7. ✅ The refreshed `figures/data_q4_fixed_vs_vol.json` is generated from the new result JSONs, not hand-entered chart values.

## Constraint Direction Review

| File:line | Direction | LHS | RHS | Expected physical meaning |
|---|---|---|---|---|
| `code/lp_kernel.py:150-176` | `==` | $x+u+G+s$ | $L+c+q$ | Q4-2 energy conservation |
| `code/lp_kernel.py:268-283` | `==` | $a+u+G+s$ | $L+c+q$ | Q4-3 rolling balance |
| `code/lp_kernel.py:285-290` | `==` | terminal SOC increment | target minus current SOC | final closure |
| `code/constraint_audit.py:126` | `≤` | exported kW conversion error | tolerance | unit consistency |

## Failed / Repaired Items

The day-0 actual-price fallback was replaced by an available prior. Text and figures were repaired to avoid attributing joint price changes to one causal factor.

## Remaining Risks

The known-price case is an information-rich comparison, not a forecast-feasible base case; mean, spread and temporal volatility can change together.

## Run Instructions

`\.venv\Scripts\python.exe code\problem4.py`

## Expected Outputs

`user_data/result4-2.xlsx`, `user_data/result4-3.xlsx`, `figures/problem_4_results.json`

## Recommended Next Skill

`consistency-auditor`
