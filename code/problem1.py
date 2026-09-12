# -*- coding: utf-8 -*-
"""问题1 驱动（§3.2）：日前确定性购电-储能联合优化。

确定性单日 LP（附件1 平均日）：主口径目标 35126.95 元，无储能基线 48052.05 元。
GL-C3 效率口径五读法灵敏度；写出 result1.xlsx 两表；产出 figures/problem_1_results.json。
所有 SOC 越界/闭合核对均由 c,s 独立重算（含单向效率），不采信求解器内部轨迹。
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from params import T, DT_H, P_MAX, E_MIN, E_MAX, E_STEP_MAX, ETA_C, ETA_D, ETA_CONVENTIONS
from io_layer import load_all
from lp_kernel import solve_day_q1
from settle import settle_q1, no_storage_baseline
import export

_ROOT = Path(__file__).resolve().parent.parent
_FIG = _ROOT / "figures"
_TOL = 1e-6


def _independent_soc(c, s, eta_c, eta_d, E0):
    """从 c,s 独立重算 SOC（含单向效率 eta_c*c - s/eta_d），供约束核对。"""
    E = np.empty(len(c) + 1)
    E[0] = E0
    for t in range(len(c)):
        E[t + 1] = E[t] + eta_c * c[t] - s[t] / eta_d
    return E


def validate_constraints(res, net, baseline, eta_c=ETA_C, eta_d=ETA_D):
    """独立重算 C1,C3-C7,C9,C20（§5.5①）。返回 (checks, 独立 SOC)。"""
    x, c, s, q = res.x, res.c, res.s, res.q
    E = _independent_soc(c, s, eta_c, eta_d, res.E[0])
    checks = {
        "C1_balance_equality": bool(np.abs(x + s - c - q - net).max() <= _TOL),
        "C3_soc_recursion": bool(np.abs(res.E[1:] - E[1:]).max() <= _TOL),
        "C4_soc_range": bool(E.min() >= E_MIN - _TOL and E.max() <= E_MAX + _TOL),
        "C5_charge_cap": bool(c.max() <= E_STEP_MAX + _TOL),
        "C6_discharge_cap": bool(s.max() <= E_STEP_MAX + _TOL),
        "C7_closure": bool(abs(E[-1] - E[0]) <= _TOL),
        "C9_nonneg": bool(min(float(x.min()), float(c.min()), float(s.min())) >= -1e-9),
        "C10_curtailment_nonneg": bool(q.min() >= -1e-9),
        "C21_no_simultaneous_charge_discharge": bool(np.min(np.vstack([c, s]), axis=0).max() <= _TOL),
        "C23_kw_kwh_conversion": bool(max(c.max(), s.max()) / DT_H <= P_MAX + _TOL),
        "C20_optimal": bool(res.status == 0 and res.obj < baseline),
    }
    return checks, E


def run(write_xlsx: bool = True) -> dict:
    att = load_all()
    net = (att.load1 - att.pv1) * DT_H            # 净需求电量 (144,) kWh
    price = att.price1
    baseline = no_storage_baseline(net, price)     # 48052.05

    res = solve_day_q1(net, price, close=True)     # 主口径 35126.95
    plan_cost = settle_q1(res.x, price)
    checks, E_ind = validate_constraints(res, net, baseline)

    # GL-C3：五种效率口径灵敏度（含理想 eta=1）
    sensitivity = {}
    for name, (ec, ed) in ETA_CONVENTIONS.items():
        r = solve_day_q1(net, price, eta_c=ec, eta_d=ed, close=True)
        sensitivity[name] = round(float(r.obj), 2)
    ideal_obj = sensitivity["ideal"]

    # 储能日循环量（放电总量）与摆幅
    cycling = float(res.s.sum())
    swing_frac = float((E_ind.max() - E_ind.min()) / (E_MAX - E_MIN))

    # logic_probes：效率乘积↑ → 费用↓（monotonic decreasing，合同 L2/灵敏度方向表）
    logic_probes = {
        "bounds": [],
        "monotonic": [
            {"more": "eta_c*eta_d", "then": "Q1_total_cost",
             "observed_sign": -1 if ideal_obj < plan_cost else 1,
             "expect_dir": "better", "expect_sign": -1},
        ],
    }

    results = {
        "problem": 1,
        "method": "确定性单日 LP（scipy linprog, method=highs）；变量[x,c,s,q]，"
                  "SOC 下三角累积和消元，首尾闭合 E_T=E_0",
        "Q1_objective": round(float(res.obj), 2),
        "Q1_total_cost": round(plan_cost, 2),
        "no_storage_baseline": round(baseline, 2),
        "savings_yuan": round(baseline - res.obj, 2),
        "savings_pct": round((baseline - res.obj) / baseline * 100, 2),
        "ideal_objective": ideal_obj,
        "solver_status": int(res.status),
        "soc_min": round(float(E_ind.min()), 2),
        "soc_max": round(float(E_ind.max()), 2),
        "soc_E0": round(float(E_ind[0]), 2),
        "soc_ET": round(float(E_ind[-1]), 2),
        "soc_swing_fraction": round(swing_frac, 4),
        "charge_max": round(float(res.c.max()), 4),
        "discharge_max": round(float(res.s.max()), 4),
        "plan_max": round(float(res.x.max()), 2),
        "daily_cycling_kwh": round(cycling, 2),
        "curtailment_kwh": round(float(res.q.sum()), 2),
        "max_simultaneous_charge_discharge_kwh": round(float(np.minimum(res.c, res.s).max()), 10),
        "efficiency_sensitivity": sensitivity,
        "constraint_checks": checks,
        "all_constraints_pass": bool(all(checks.values())),
        "logic_probes": logic_probes,
    }

    if write_xlsx:
        out = _ROOT / "user_data" / "result1.xlsx"
        export.write_result1(out, res.x, res.c, res.s, res.q, E_ind,
                             att.load1 * DT_H, att.pv1 * DT_H)
        results["result_file"] = "user_data/result1.xlsx"

    _FIG.mkdir(exist_ok=True)
    (_FIG / "problem_1_results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    return results


if __name__ == "__main__":
    r = run()
    print(f"Q1 目标 = {r['Q1_objective']:.2f} 元 (报告 35126.95)")
    print(f"无储能基线 = {r['no_storage_baseline']:.2f} 元 (报告 48052.05)")
    print(f"节省 = {r['savings_pct']:.2f}% (报告 26.90%)")
    print(f"效率口径灵敏度 = {r['efficiency_sensitivity']}")
    print(f"SOC min/max/E0/ET = {r['soc_min']}/{r['soc_max']}/{r['soc_E0']}/{r['soc_ET']}")
    print(f"约束核对全过 = {r['all_constraints_pass']}  明细 {r['constraint_checks']}")
