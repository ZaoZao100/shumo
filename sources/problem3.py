# -*- coding: utf-8 -*-
"""问题3 驱动（§3.4）：多时刻滚动预报下的调整决策 + 三段式费用。

滚动时域 MPC：决策时刻 H={0,6,12,18}h（τ={0,36,72,108} 段）。0:00 用带裕度 LP 出计划 b；
h=6,12,18 用 solve_adjust 只重优化未发生时段 t>τ(h)（P3-C1），预报源严格取「预报时刻==h」行。
每决策窗 [τ(h),τ(h+1)) 内按 §3.3.5 因果规则执行；跨日 SOC 串联。
三段式费用双口径：R-b 主口径 p·min(a,b)+1.5p·d⁺+0.5p·d⁻；R-a 对照。
S0（仅 0:00 锁定）vs S1（滚动）在同一 334 天集合对照（§5.4）。电价源为附件1。
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from params import (T, DT_H, P_MAX, E_MIN, E_MAX, E_STEP_MAX, E_INIT, E_TERMINAL, ETA_C, ETA_D,
                    K_EMERGENCY, LAM_UP, LAM_DN, N_DAYS_DELIVERY)
from io_layer import load_all
from forecast import Forecaster
from lp_kernel import solve_day_q1, solve_adjust
from dispatch import causal_step, causal_dispatch
from settle import settle_q3
import export

_ROOT = Path(__file__).resolve().parent.parent
_FIG = _ROOT / "figures"
_TOL = 1e-6
_H = [0, 6, 12, 18]
_TAU = [0, 36, 72, 108]
_ENDS = [36, 72, 108, 144]
_M_PLAN = 0.03          # 0:00 计划裕度（沿用 Q2 内点最优；L3：不得按均值刚好配平）


def _net_in_at_hour(fc, i, h, m=_M_PLAN):
    """时刻 h 发布预报下的带裕度净需求输入 (1+m)·ℓ̂ - ĝ^(h)（kWh）。"""
    return (1.0 + m) * fc.load_hat_kwh[i] - fc.interp_pv_kwh(i, h)


def rolling_day(fc, i, price, E_start, fee_convention="R_b", m=_M_PLAN,
                terminal_target=None):
    """策略 S1：单日四时刻滚动。返回 dict(b, a, c, s, u, E)。"""
    net_act = fc.net_actual_kwh(i)
    a_exec = np.zeros(T)
    c_ref = np.zeros(T)
    s_ref = np.zeros(T)
    c_out = np.zeros(T)
    s_out = np.zeros(T)
    u_out = np.zeros(T)
    q_out = np.zeros(T)
    E = np.empty(T + 1)
    E[0] = E_start
    b = None
    for (h, tau, end) in zip(_H, _TAU, _ENDS):
        net_in = _net_in_at_hour(fc, i, h, m)
        if h == 0:
            res = solve_day_q1(net_in, price, E0=E_start, close=True,
                               terminal_target=terminal_target)
            if res.status != 0:
                raise RuntimeError(f"day {fc.dates[i]} 0:00 LP status={res.status}")
            b = res.x.copy()
            c_ref[:] = res.c
            s_ref[:] = res.s
            a_win = res.x
        else:
            st, a_full, _dp, _dm, c_m, s_m, _u_m, _q_m = solve_adjust(
                tau, b, net_in, price, E[tau], fee_convention=fee_convention,
                terminal_target=terminal_target)
            if st != 0:
                raise RuntimeError(f"day {fc.dates[i]} h={h} adjust status={st}")
            a_win = a_full
            c_ref[tau:] = c_m
            s_ref[tau:] = s_m
        a_exec[tau:end] = a_win[tau:end]
        for t in range(tau, end):
            c_out[t], s_out[t], u_out[t], q_out[t], E[t + 1] = causal_step(
                a_exec[t], net_act[t], c_ref[t], s_ref[t], E[t],
                terminal_target=terminal_target,
                remaining_steps_after=T - t - 1 if terminal_target is not None else None)
    return dict(idx=i, date=fc.dates[i], price=price, b=b, a=a_exec,
                c=c_out, s=s_out, u=u_out, q=q_out, E=E, net_act=net_act)


def s0_day(fc, i, price, E_start, m=_M_PLAN, terminal_target=None):
    """策略 S0：仅 0:00 计划锁定全天，无调整，缺口全由紧急购电覆盖。"""
    net_in = _net_in_at_hour(fc, i, 0, m)
    res = solve_day_q1(net_in, price, E0=E_start, close=True,
                       terminal_target=terminal_target)
    if res.status != 0:
        raise RuntimeError(f"day {fc.dates[i]} S0 LP status={res.status}")
    b = res.x
    c, s, u, q, E = causal_dispatch(
        b, fc.net_actual_kwh(i), res.c, res.s, E_start, terminal_target=terminal_target)
    return dict(idx=i, date=fc.dates[i], price=price, b=b, a=b.copy(),
                c=c, s=s, u=u, q=q, E=E, net_act=fc.net_actual_kwh(i))


def _settle_day(d, fee_convention="R_b"):
    """单日三段式结算，返回 settle_q3 dict。"""
    return settle_q3(d["a"], d["b"], d["u"], d["price"], fee_convention=fee_convention)


def run_strategy(fc, price_of, run_indices, strategy="S1", fee_convention="R_b", m=_M_PLAN,
                 delivery_set=None):
    """逐日执行 S0/S1，跨日 SOC 串联。返回 (days, 结算汇总 dict)。"""
    E_prev = E_INIT
    days = []
    day_fn = rolling_day if strategy == "S1" else s0_day
    if delivery_set is None:
        from problem2 import delivery_indices
        delivery_set = set(delivery_indices(fc.att))
    last_idx = run_indices[-1]
    for i in run_indices:
        p = price_of(i)
        terminal_target = E_TERMINAL if i == last_idx else None
        if strategy == "S1":
            d = day_fn(fc, i, p, E_prev, fee_convention=fee_convention, m=m,
                       terminal_target=terminal_target)
        else:
            d = day_fn(fc, i, p, E_prev, m=m, terminal_target=terminal_target)
        days.append(d)
        E_prev = d["E"][-1]
    base = up = dn = emerg = emerg_kwh = cyc = 0.0
    plan_kwh = 0.0
    for d in days:
        if d["idx"] not in delivery_set:
            continue
        sd = _settle_day(d, fee_convention)
        base += sd["base_cost"]; up += sd["up_cost"]; dn += sd["dn_cost"]
        emerg += sd["emergency_cost"]
        emerg_kwh += float(d["u"].sum())
        cyc += float(d["s"].sum())
        plan_kwh += float(d["a"].sum())
    total = base + up + dn + emerg
    summary = dict(base_cost=base, up_cost=up, dn_cost=dn, adjust_cost=up + dn,
                   emergency_cost=emerg, total=total, emergency_kwh=emerg_kwh,
                   cycling=cyc, plan_kwh=plan_kwh)
    return days, summary


def validate_year(days, fee_convention="R_b") -> dict:
    """独立重算 C1,C3,C4,C5,C6,C9,C11/C12（费用恒等式）,C8 跨日串联,P3-C1 因果边界。"""
    ok_bal = ok_soc = ok_rec = ok_cap = ok_neg = ok_carry = ok_dev = ok_fee = ok_simul = True
    for k, d in enumerate(days):
        a, c, s, u, q, E, net, b = (d["a"], d["c"], d["s"], d["u"], d["q"], d["E"],
                                 d["net_act"], d["b"])
        E_ind = np.empty(T + 1); E_ind[0] = E[0]
        for t in range(T):
            E_ind[t + 1] = E_ind[t] + ETA_C * c[t] - s[t] / ETA_D
        ok_bal &= bool(np.abs(a + u + s - c - q - net).max() <= _TOL)
        ok_rec &= bool(np.abs(E[1:] - E_ind[1:]).max() <= _TOL)
        ok_soc &= bool(E_ind.min() >= E_MIN - _TOL and E_ind.max() <= E_MAX + _TOL)
        ok_cap &= bool(c.max() <= E_STEP_MAX + _TOL and s.max() <= E_STEP_MAX + _TOL)
        ok_neg &= bool(min(float(a.min()), float(u.min()), float(q.min()),
                           float(c.min()), float(s.min())) >= -1e-9)
        ok_simul &= bool(np.minimum(c, s).max() <= _TOL)
        # 费用恒等式 C11/C12：dp-dm == a-b 且 φ 三项重算一致
        dp = np.maximum(a - b, 0.0); dm = np.maximum(b - a, 0.0)
        ok_dev &= bool(np.abs((dp - dm) - (a - b)).max() <= _TOL)
        sd = settle_q3(a, b, u, d["price"], fee_convention=fee_convention)
        if fee_convention == "R_b":
            base_chk = float(d["price"] @ np.minimum(a, b))
        else:
            base_chk = float(d["price"] @ b)
        ok_fee &= bool(abs(sd["base_cost"] - base_chk) <= 1e-3)
        if k > 0:
            ok_carry &= bool(abs(days[k]["E"][0] - days[k - 1]["E"][-1]) <= _TOL)
    return {
        "C1_balance_equality_with_curtailment": ok_bal,
        "C3_soc_recursion": ok_rec,
        "C4_soc_range": ok_soc,
        "C5C6_power_cap": ok_cap,
        "C9_nonneg": ok_neg,
        "C8_cross_day_carry": bool(ok_carry and abs(days[0]["E"][0] - E_INIT) <= _TOL),
        "C11C12_fee_identity": bool(ok_dev and ok_fee),
        "C21_no_simultaneous_charge_discharge": ok_simul,
        "C23_kw_kwh_conversion": bool(ok_cap and E_STEP_MAX / DT_H <= P_MAX + _TOL),
        "C24_terminal_soc": bool(abs(days[-1]["E"][-1] - E_TERMINAL) <= _TOL),
    }


def leadtime_mae(fc, dvidx) -> dict:
    """光伏预报提前期 MAE（kW）：同一目标时段用 0:00 vs 12:00 预报误差降幅证据（P3-C4）。"""
    err0 = []
    err12 = []
    for i in dvidx:
        g0 = fc.interp_pv_kwh(i, 0) / DT_H
        g12 = fc.interp_pv_kwh(i, 12) / DT_H
        act = fc.att.pv_actual[i]
        aft = np.arange(T) >= 78          # 13:00 起（含午后光伏）
        err0.append(np.abs(g0 - act)[aft])
        err12.append(np.abs(g12 - act)[aft])
    e0 = float(np.concatenate(err0).mean())
    e12 = float(np.concatenate(err12).mean())
    return {"pv_mae_0h_afternoon_kw": round(e0, 2),
            "pv_mae_12h_afternoon_kw": round(e12, 2),
            "reduction_pct": round((e0 - e12) / e0 * 100, 1) if e0 > 0 else 0.0}


def _write_result3(fname, fc, days, all_days):
    import pandas as pd
    dates = [d["date"] for d in days]
    b = np.array([d["b"] for d in days])
    a = np.array([d["a"] for d in days])
    charge = np.array([d["c"] for d in days])
    discharge = np.array([d["s"] for d in days])
    E0 = np.array([d["E"][0] for d in days])
    ET = np.array([d["E"][-1] for d in days])
    emergency = np.array([d["u"] for d in days])
    b_cost = np.array([float(d["price"] @ d["b"]) for d in days])
    a_cost = np.array([float(d["price"] @ d["a"]) for d in days])
    df_plan = export.build_wide_plan(fname, "计划购电量", dates, b, b_cost)
    df_adj = export.build_wide_plan(fname, "调整购电量", dates, a, a_cost)
    df_soc = export.build_soc_table(fname, "充放电量", dates, charge, discharge, E0, ET)
    df_em = export.build_emergency_table(fname, "紧急购电量", dates, emergency)
    all_dates = [d["date"] for d in all_days]
    all_idx = np.array([d["idx"] for d in all_days])
    audit = export.build_interval_audit(
        all_dates, fc.att.load_actual[all_idx] * DT_H, fc.att.pv_actual[all_idx] * DT_H,
        np.array([d["a"] for d in all_days]), np.array([d["c"] for d in all_days]),
        np.array([d["s"] for d in all_days]), np.array([d["u"] for d in all_days]),
        np.array([d["q"] for d in all_days]), np.array([d["E"] for d in all_days]),
        original_plan_kwh=np.array([d["b"] for d in all_days]))
    out = _ROOT / "user_data" / fname
    with pd.ExcelWriter(out, engine="openpyxl") as w:
        df_plan.to_excel(w, sheet_name="计划购电量", index=False)
        df_adj.to_excel(w, sheet_name="调整购电量", index=False)
        df_soc.to_excel(w, sheet_name="充放电量", index=False)
        df_em.to_excel(w, sheet_name="紧急购电量", index=False)
        audit.to_excel(w, sheet_name="逐时段审计", index=False)


def run(write_xlsx: bool = True, fname: str = "result3.xlsx",
        price_matrix=None, tag: str = "problem_3") -> dict:
    att = load_all()
    fc = Forecaster(att)
    from problem2 import delivery_indices, operational_indices
    dvidx = delivery_indices(att)
    runidx = operational_indices(att)
    dvset = set(dvidx)
    assert len(dvidx) == N_DAYS_DELIVERY, f"交付天数 {len(dvidx)} != {N_DAYS_DELIVERY}"

    if price_matrix is None:
        price_of = lambda i: att.price1
        price_src = "附件1"
    else:
        price_of = lambda i: price_matrix[i]
        price_src = "附件4"

    # 主口径 R-b（S1 滚动）
    all_days, s1 = run_strategy(fc, price_of, runidx, "S1", "R_b", delivery_set=dvset)
    days = [d for d in all_days if d["idx"] in dvset]
    checks = validate_year(all_days, "R_b")
    info_audit = fc.information_boundary_audit(runidx)
    checks["C25_information_boundary_trace"] = info_audit["all_pass"]
    # 对照口径 R-a（S1 滚动，仅费用）
    _days_ra, s1_ra = run_strategy(fc, price_of, runidx, "S1", "R_a", delivery_set=dvset)
    # S0 对照（仅 0:00 锁定；无调整费用，缺口全紧急）
    all_days_s0, s0 = run_strategy(fc, price_of, runidx, "S0", "R_b", delivery_set=dvset)

    lead = leadtime_mae(fc, dvidx)
    rolling_value = s0["total"] - s1["total"]     # >0 表示滚动有净收益

    # 表3 四日期紧急购电区间（同 Q2 口径）
    table3 = {}
    for d in days:
        ds = d["date"].isoformat()
        if ds in ("2025-03-20", "2025-06-21", "2025-09-23", "2025-12-21"):
            runs = export._merge_runs(d["u"], _TOL)
            table3[ds] = ([{"interval": export._slot_label(a_ * 10, (b_ + 1) * 10),
                            "kwh": round(float(t_), 2)} for a_, b_, t_ in runs]
                          if runs else "无")

    logic_probes = {
        "bounds": [],
        "monotonic": [
            {"more": "rolling_adjustment_S1", "then": "total_cost_vs_S0",
             "observed_sign": -1 if rolling_value > 0 else 1,
             "expect_dir": "less", "expect_sign": -1},
        ],
    }

    results = {
        "problem": 3,
        "method": "点预测滚动优化（H={0,6,12,18}，只改未发生时段）+ 三段式费用双口径 + 因果执行",
        "method_scope": "点预测滚动优化，不是随机MPC；各线性规划子问题全局最优",
        "price_source": price_src,
        "n_delivery_days": len(dvidx),
        "fee_convention_main": "R_b",
        "S1_plan_cost": round(s1["base_cost"], 2),
        "S1_adjust_cost": round(s1["adjust_cost"], 2),
        "S1_up_cost": round(s1["up_cost"], 2),
        "S1_down_cost": round(s1["dn_cost"], 2),
        "S1_emergency_cost": round(s1["emergency_cost"], 2),
        "S1_total": round(s1["total"], 2),
        "S1_emergency_kwh": round(s1["emergency_kwh"], 2),
        "S1_cycling_kwh": round(s1["cycling"], 2),
        "S1_curtailment_kwh": round(sum(float(d["q"].sum()) for d in days), 2),
        "S1_total_R_a": round(s1_ra["total"], 2),
        "S0_plan_cost": round(s0["base_cost"], 2),
        "S0_emergency_cost": round(s0["emergency_cost"], 2),
        "S0_total": round(s0["total"], 2),
        "S0_emergency_kwh": round(s0["emergency_kwh"], 2),
        "rolling_value_yuan": round(rolling_value, 2),
        "rolling_beneficial": bool(rolling_value > 0),
        "leadtime_mae": lead,
        "table3_emergency": table3,
        "constraint_checks": checks,
        "information_boundary_audit": info_audit,
        "initial_soc_set_once_at": all_days[0]["date"].isoformat() + " 00:00",
        "delivery_start_soc_kwh": round(float(days[0]["E"][0]), 6),
        "terminal_soc_kwh": round(float(all_days[-1]["E"][-1]), 6),
        "max_simultaneous_charge_discharge_kwh": round(max(
            float(np.minimum(d["c"], d["s"]).max()) for d in all_days), 10),
        "all_constraints_pass": bool(all(checks.values())),
        "logic_probes": logic_probes,
    }

    if write_xlsx:
        _write_result3(fname, fc, days, all_days)
        results["result_file"] = f"user_data/{fname}"

    if tag == "problem_3":
        import pandas as pd
        outdir = _ROOT / "results"
        outdir.mkdir(exist_ok=True)
        s0_days = [d for d in all_days_s0 if d["idx"] in dvset]
        rows = []
        for d1, d0 in zip(days, s0_days):
            sd1 = _settle_day(d1, "R_b")
            sd0 = _settle_day(d0, "R_b")
            rows.append({
                "date": d1["date"].isoformat(),
                "q3_s0_total_cost": sd0["total"],
                "q3_s1_total_cost": sd1["total"],
                "actual_net_energy_kwh": float(d1["net_act"].sum()),
            })
        pd.DataFrame(rows).to_csv(outdir / "q3_daily_costs.csv", index=False)

    _FIG.mkdir(exist_ok=True)
    (_FIG / f"{tag}_results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    return results


if __name__ == "__main__":
    r = run()
    print(f"Q3 S1 总费用 = {r['S1_total']:.2f} 元（计划 {r['S1_plan_cost']:.2f} "
          f"+ 调整 {r['S1_adjust_cost']:.2f} + 紧急 {r['S1_emergency_cost']:.2f}）")
    print(f"Q3 S1 紧急购电 = {r['S1_emergency_kwh']:.2f} kWh；循环 {r['S1_cycling_kwh']:.2f} kWh")
    print(f"S0 仅0:00 总费用 = {r['S0_total']:.2f}（紧急 {r['S0_emergency_kwh']:.2f} kWh）")
    print(f"滚动净收益 S0-S1 = {r['rolling_value_yuan']:.2f} 元（>0 滚动有益={r['rolling_beneficial']}）")
    print(f"R-a 对照总费用 = {r['S1_total_R_a']:.2f}")
    print(f"提前期 MAE 午后 0h/12h = {r['leadtime_mae']['pv_mae_0h_afternoon_kw']}/"
          f"{r['leadtime_mae']['pv_mae_12h_afternoon_kw']} kW（降 {r['leadtime_mae']['reduction_pct']}%）")
    print(f"约束核对全过 = {r['all_constraints_pass']}  {r['constraint_checks']}")
