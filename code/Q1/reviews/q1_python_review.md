# Q1 Python Code Review

> **Status**: passed
> **Reviewer**: python-code-reviewer
> **Date**: 2026-09-12
> **Scripts reviewed**: `code/problem1.py`, `code/lp_kernel.py`, `code/export.py`, `code/constraint_audit.py`

## Pass Items

1. ✅ `code/lp_kernel.py:60` declares Q1 variables `[x,c,s,q]`; `code/lp_kernel.py:86-100` submits an equality matrix to HiGHS, so curtailment is explicit rather than hidden in an inequality.
2. ✅ `code/problem1.py:57` converts load and photovoltaic power to interval energy with `DT_H=1/6`, and `code/problem1.py:49` checks the reverse kWh-to-kW conversion against 5000 kW.
3. ✅ `code/lp_kernel.py:90-95` adds terminal SOC equality when the daily closure is requested; exported Q1 SOC is 6000 kWh at both endpoints.
4. ✅ `code/lp_kernel.py:38-54` implements the documented charge/discharge normalization; `code/problem1.py:107` reports `max(min(c,s))=0` for the rerun.
5. ✅ `code/export.py` writes `user_data/result1.xlsx` with a “逐时段审计” sheet containing actual load, actual PV, $x,c,s,q$ and SOC endpoints; the workbook opened successfully after generation.
6. ✅ `code/constraint_audit.py` independently re-opened the workbook and reported 19 Q1 checks with 0 failures; maximum absolute balance residual was below $10^{-9}$ kWh.
7. ✅ `python -m compileall -q code figures` completed without syntax errors under the documented virtual environment.

## Constraint Direction Review

| File:line | Direction | LHS | RHS | Expected physical meaning |
|---|---|---|---|---|
| `code/lp_kernel.py:75-86` | `==` | $x+G+s$ | $L+c+q$ | interval energy conservation |
| `code/lp_kernel.py:69-73` | `≤` | cumulative SOC increment | $E_{max}-E_0$ | SOC upper bound |
| `code/lp_kernel.py:69-73` | `≥` | cumulative SOC increment | $E_{min}-E_0$ | SOC lower bound |
| `code/lp_kernel.py:90-95` | `==` | terminal SOC increment | target minus initial SOC | daily closure |
| `code/problem1.py:49` | `≤` | interval charge/discharge divided by $\Delta t$ | 5000 kW | power cap |

## Failed / Repaired Items

None remaining after the explicit-curtailment, unit, closure, and simultaneous-charge/discharge repairs.

## Remaining Risks

The efficiency interpretation remains a stated problem ambiguity; five conventions are reported rather than silently selecting an alternative.

## Run Instructions

`\.venv\Scripts\python.exe code\problem1.py`

## Expected Outputs

`user_data/result1.xlsx`, `figures/problem_1_results.json`

## Recommended Next Skill

`consistency-auditor`
