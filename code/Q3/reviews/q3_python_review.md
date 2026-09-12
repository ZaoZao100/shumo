# Q3 Python Code Review

> **Status**: passed_with_warnings
> **Reviewer**: python-code-reviewer
> **Date**: 2026-09-12
> **Scripts reviewed**: `code/problem3.py`, `code/lp_kernel.py`, `code/forecast.py`, `code/statistical_uncertainty.py`, `code/constraint_audit.py`

## Pass Items

1. ✅ `code/problem3.py:41-79` freezes past intervals and re-solves only the remaining horizon at 0:00, 6:00, 12:00 and 18:00.
2. ✅ `code/lp_kernel.py:246-309` includes $a,d^+,d^-,c,s,u,q$ and enforces both balance and deviation identities as equalities.
3. ✅ `code/problem3.py:115-120` applies the final SOC target only on 31 December while carrying SOC continuously through January and the delivery period.
4. ✅ `code/problem3.py:177-178` audits power conversion and terminal SOC; `code/problem3.py:313` reports `max(min(c,s))=0` after normalization.
5. ✅ `code/problem3.py:254` saves the information-boundary audit, and `code/forecast.py` no longer constructs a night mask from future actual PV.
6. ✅ `code/statistical_uncertainty.py:33-54` uses a fixed-seed 7-day circular moving-block bootstrap and writes paired, seasonal, extreme-day and JSON outputs.
7. ✅ `code/constraint_audit.py` reported 26 checks with 0 failures for `result3.xlsx`; reconstructed base plan cost equals 12517803.35 yuan.

## Constraint Direction Review

| File:line | Direction | LHS | RHS | Expected physical meaning |
|---|---|---|---|---|
| `code/lp_kernel.py:268-283` | `==` | $a+u+G+s$ | $L+c+q$ | rolling-horizon predicted balance |
| `code/lp_kernel.py:276-283` | `==` | $a-b$ | $d^+-d^-$ | adjustment decomposition |
| `code/lp_kernel.py:285-290` | `==` | terminal SOC increment | target minus current SOC | final-day closure |
| `code/problem3.py:174-178` | `≤` | residuals and caps | audit tolerance/physical limits | execution feasibility |

## Failed / Repaired Items

The former actual-PV night mask was removed. The method label was repaired from stochastic/MPC wording to “点预测滚动优化”.

## Remaining Risks

Forecast-release marginal values are not separately identified, and R-a/R-b retain a stated interpretation ambiguity.

## Run Instructions

`\.venv\Scripts\python.exe code\problem3.py` then `\.venv\Scripts\python.exe code\statistical_uncertainty.py`

## Expected Outputs

`user_data/result3.xlsx`, `figures/problem_3_results.json`, `results/q3_daily_costs.csv`, `results/statistical_uncertainty.json`

## Recommended Next Skill

`consistency-auditor`
