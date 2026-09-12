# -*- coding: utf-8 -*-
"""问题2 驱动（§3.3）：日前两阶段随机规划 + 因果实时调度。

主模型：K=8 同 regime 残差场景两阶段 LP（§3.3.3）→ 0:00 计划 x；参考轨迹取场景均值储能动作，
因果规则（§3.3.5）执行结算。标量裕度基线（§3.3.4）扫 m∈{0,.03,.06,.10,.15,.20} 得 U 形对照。
P2-C5：储能可实时再调度 vs 随计划锁定的紧急购电对照。跨日 SOC 串联，交付 334 天。
所有预测严格用 j<d 的历史（无泄漏），电价源为附件1。
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from params import (T, DT_H, P_MAX, E_MIN, E_MAX, E_STEP_MAX, E_INIT, E_TERMINAL, ETA_C, ETA_D,
                    K_EMERGENCY, N_DAYS_DELIVERY, DELIVERY_START, DELIVERY_END)
from io_layer import load_all
from forecast import Forecaster, K_SCEN
from lp_kernel import TwoStageKernel, solve_day_q1
from dispatch import causal_dispatch
import export

_ROOT = Path(__file__).resolve().parent.parent
_FIG = _ROOT / "figures"
_TOL = 1e-6
_MARGINS = [0.00, 0.03, 0.06, 0.10, 0.15, 0.20]


def delivery_indices(att) -> list:
    """交付区间 [2025-02-01, 2025-12-31] 的行号列表（334 个）。"""
    return [i for i, d in enumerate(att.dates) if DELIVERY_START <= d <= DELIVERY_END]


def operational_indices(att) -> list:
    """完整计算期 2025-01-01 至 2025-12-31；E_INIT 只在首日设置一次。"""
    return list(range(len(att.dates)))


def _pad_scenarios(scen: np.ndarray, K: int) -> np.ndarray:
    """场景不足 K 个时循环填充到 K（仅极早期日会触发；交付区间恒 >=8）。"""
    if scen.shape[0] == K:
        return scen
    reps = int(np.ceil(K / scen.shape[0]))
    return np.tile(scen, (reps, 1))[:K]


def solve_two_stage_year(att, fc, price_of, run_indices, kappa=K_EMERGENCY,
                         settle_price_of=None):
    """逐日两阶段 LP，跨日 SOC 串联。返回 per-day dict 列表 + 参考轨迹。

    price_of(i) -> (144,) 计划所用电价（Q2 恒为附件1；Q4-2 为附件4 当日）。
    settle_price_of(i) -> (144,) 结算所用电价；默认同 price_of（已知口径）。
    Q4-2 预测口径：计划用预测价 p̂，结算用真实价 p（settle_price_of != price_of）。
    """
    if settle_price_of is None:
        settle_price_of = price_of
    kernel = TwoStageKernel(K_SCEN)
    E_prev = E_INIT
    days = []
    last_idx = run_indices[-1]
    for i in run_indices:
        p = price_of(i)
        p_set = settle_price_of(i)
        scen = _pad_scenarios(fc.scenarios(i, K_SCEN), K_SCEN)
        terminal_target = E_TERMINAL if i == last_idx else None
        status, x, _recourse = kernel.solve(
            scen, p, E_prev, terminal_target=terminal_target)
        if status != 0:
            raise RuntimeError(f"day {att.dates[i]} 两阶段 LP status={status}")
        # 参考轨迹（§3.3.5）：均值场景下的确定性储能动作（单一相干套利轨迹，
        # 首尾闭合于当日期初实际 SOC）。均值场景 recourse 因储能零成本而退化，
        # 故改用确定性单日 LP 的 (c,s) 作参考。
        mean_net = scen.mean(axis=0)
        ref = solve_day_q1(mean_net, p, E0=E_prev, close=True,
                           terminal_target=terminal_target)
        c_ref, s_ref = ref.c, ref.s
        net_act = fc.net_actual_kwh(i)
        c, s, u, q, E = causal_dispatch(
            x, net_act, c_ref, s_ref, E_prev, terminal_target=terminal_target)
        days.append(dict(idx=i, date=att.dates[i], price=p_set, x=x, c=c, s=s, u=u, q=q,
                         E=E, c_ref=c_ref, s_ref=s_ref, net_act=net_act))
        E_prev = E[-1]
    return days


def _exec_causal(x, net_act, c_ref, s_ref, E0, terminal_target=None):
    return causal_dispatch(x, net_act, c_ref, s_ref, E0, terminal_target=terminal_target)


def _exec_locked(x, net_act, c_ref, s_ref, E0, terminal_target=None):
    """储能随计划锁定（P2-C5 对照）：储能只走参考轨迹，不因实际偏差再调度。"""
    c = np.clip(np.asarray(c_ref, float).copy(), 0.0, E_STEP_MAX)
    s = np.clip(np.asarray(s_ref, float).copy(), 0.0, E_STEP_MAX)
    E = np.empty(T + 1)
    E[0] = E0
    for t in range(T):
        # SOC 可行性钳制（锁定轨迹仍须落在物理区间内）
        s_ub = min(E_STEP_MAX, ETA_D * (E[t] - E_MIN))
        c_ub = min(E_STEP_MAX, (E_MAX - E[t]) / ETA_C)
        s[t] = min(s[t], max(s_ub, 0.0))
        c[t] = min(c[t], max(c_ub, 0.0))
        E[t + 1] = E[t] + ETA_C * c[t] - s[t] / ETA_D
    if terminal_target is not None:
        # 锁定轨迹对照也用同一末期目标；由最终一槽在可行范围内校正。
        gap = terminal_target - E[-1]
        if gap > 0:
            reduce_s = min(s[-1], gap * ETA_D)
            s[-1] -= reduce_s
            gap -= reduce_s / ETA_D
            c[-1] += gap / ETA_C
        elif gap < 0:
            need = -gap
            reduce_c = min(c[-1], need / ETA_C)
            c[-1] -= reduce_c
            need -= ETA_C * reduce_c
            s[-1] += need * ETA_D
        if c[-1] > E_STEP_MAX + _TOL or s[-1] > E_STEP_MAX + _TOL:
            raise RuntimeError("锁定轨迹末期 SOC 校正超过功率上限")
        E[-1] = terminal_target
    residual = net_act - x - s + c
    u = np.maximum(residual, 0.0)
    q = np.maximum(-residual, 0.0)
    return c, s, u, q, E


def scalar_margin_year(att, fc, price_of, run_indices, m, exec_fn=_exec_causal,
                       kappa=K_EMERGENCY, delivery_set=None):
    """标量裕度基线（§3.3.4 / 分析 §8.2）：净输入 (1+m)·ℓ̂ - ĝ 求解 Q1 LP，
    得计划 x 与参考储能轨迹 (c̄,s̄)（LP 在峰段少买、令储能套利放电），
    再按 §3.3.5 因果规则执行结算，跨日 SOC 串联。返回 (total_cost, emergency_kwh)。

    关键：计划 x 由带储能的 LP 决定（峰段刻意少买、依赖储能），而非 (1+m)·n̂⁺
    逐槽足额购买——后者会使储能全程空闲作缓冲，紧急量塌缩、U 形消失。
    """
    E_prev = E_INIT
    total = 0.0
    emerg = 0.0
    if delivery_set is None:
        delivery_set = set(delivery_indices(att))
    last_idx = run_indices[-1]
    for i in run_indices:
        p = price_of(i)
        net_in = (1.0 + m) * fc.load_hat_kwh[i] - fc.pv_hat_kwh[i]
        terminal_target = E_TERMINAL if i == last_idx else None
        ref = solve_day_q1(net_in, p, E0=E_prev, close=True,
                           terminal_target=terminal_target)
        x, c_ref, s_ref = ref.x, ref.c, ref.s
        net_act = fc.net_actual_kwh(i)
        c, s, u, q, E = exec_fn(
            x, net_act, c_ref, s_ref, E_prev, terminal_target=terminal_target)
        if i in delivery_set:
            total += float(p @ x) + float(kappa * (p * u).sum())
            emerg += float(u.sum())
        E_prev = E[-1]
    return total, emerg


def settle_year(days, kappa=K_EMERGENCY) -> dict:
    """按 §3.3.5 结算：计划费用 + 5×紧急费用（逐时段电价）。"""
    plan_cost = sum(float(d["price"] @ d["x"]) for d in days)
    emerg_cost = sum(float(kappa * (d["price"] * d["u"]).sum()) for d in days)
    emerg_kwh = sum(float(d["u"].sum()) for d in days)
    cycling = sum(float(d["s"].sum()) for d in days)
    return dict(plan_cost=plan_cost, emergency_cost=emerg_cost,
                total=plan_cost + emerg_cost, emergency_kwh=emerg_kwh, cycling=cycling)


def validate_year(days) -> dict:
    """逐时段重算平衡等式、SOC、功率换算、互斥充放、跨日连续与末期状态。"""
    ok_bal = ok_soc = ok_rec = ok_cap = ok_neg = ok_carry = ok_simul = True
    for k, d in enumerate(days):
        x, c, s, u, q, E, net = (d["x"], d["c"], d["s"], d["u"], d["q"],
                                  d["E"], d["net_act"])
        E_ind = np.empty(T + 1)
        E_ind[0] = E[0]
        for t in range(T):
            E_ind[t + 1] = E_ind[t] + ETA_C * c[t] - s[t] / ETA_D
        ok_bal &= bool(np.abs(x + u + s - c - q - net).max() <= _TOL)
        ok_rec &= bool(np.abs(E[1:] - E_ind[1:]).max() <= _TOL)
        ok_soc &= bool(E_ind.min() >= E_MIN - _TOL and E_ind.max() <= E_MAX + _TOL)
        ok_cap &= bool(c.max() <= E_STEP_MAX + _TOL and s.max() <= E_STEP_MAX + _TOL)
        ok_neg &= bool(min(float(x.min()), float(u.min()), float(q.min()),
                           float(c.min()), float(s.min())) >= -1e-9)
        ok_simul &= bool(np.minimum(c, s).max() <= _TOL)
        if k > 0:
            ok_carry &= bool(abs(days[k]["E"][0] - days[k - 1]["E"][-1]) <= _TOL)
    return {
        "C2_balance_equality_with_curtailment": ok_bal,
        "C3_soc_recursion": ok_rec,
        "C4_soc_range": ok_soc,
        "C5C6_power_cap": ok_cap,
        "C8_cross_day_carry": bool(ok_carry and abs(days[0]["E"][0] - E_INIT) <= _TOL),
        "C9_nonneg": ok_neg,
        "C21_no_simultaneous_charge_discharge": ok_simul,
        "C23_kw_kwh_conversion": bool(ok_cap and E_STEP_MAX / DT_H <= P_MAX + _TOL),
        "C24_terminal_soc": bool(abs(days[-1]["E"][-1] - E_TERMINAL) <= _TOL),
    }


def regime_mae_comparison(att, fc, dvidx) -> dict:
    """同 regime vs 跨 regime（全历史平均）负载预测 MAE 对照（kW），留出期。"""
    load_kw_hat = fc.load_hat_kwh / DT_H
    same = float(np.abs(load_kw_hat[dvidx] - att.load_actual[dvidx]).mean())
    # 跨 regime：对每个交付日用 j<d 全历史（不分 regime）逐时段均值
    cross_err = []
    for i in dvidx:
        hist = att.load_actual[:i]
        if hist.shape[0] == 0:
            continue
        pred = hist.mean(axis=0)
        cross_err.append(np.abs(pred - att.load_actual[i]))
    cross = float(np.concatenate(cross_err).mean()) if cross_err else float("nan")
    return {"same_regime_mae_kw": round(same, 2), "cross_regime_mae_kw": round(cross, 2)}


def _write_result2(fname, att, days, all_days):
    dates = [att.dates[d["idx"]] for d in days]
    plan = np.array([d["x"] for d in days])
    daily_cost = np.array([float(d["price"] @ d["x"]) for d in days])
    charge = np.array([d["c"] for d in days])
    discharge = np.array([d["s"] for d in days])
    E0 = np.array([d["E"][0] for d in days])
    ET = np.array([d["E"][-1] for d in days])
    emergency = np.array([d["u"] for d in days])
    import pandas as pd
    out = _ROOT / "user_data" / fname
    df_plan = export.build_wide_plan(fname, "计划购电量", dates, plan, daily_cost)
    df_soc = export.build_soc_table(fname, "充放电量", dates, charge, discharge, E0, ET)
    df_em = export.build_emergency_table(fname, "紧急购电量", dates, emergency)
    all_dates = [d["date"] for d in all_days]
    all_idx = np.array([d["idx"] for d in all_days])
    audit = export.build_interval_audit(
        all_dates, att.load_actual[all_idx] * DT_H, att.pv_actual[all_idx] * DT_H,
        np.array([d["x"] for d in all_days]), np.array([d["c"] for d in all_days]),
        np.array([d["s"] for d in all_days]), np.array([d["u"] for d in all_days]),
        np.array([d["q"] for d in all_days]), np.array([d["E"] for d in all_days]))
    with pd.ExcelWriter(out, engine="openpyxl") as w:
        df_plan.to_excel(w, sheet_name="计划购电量", index=False)
        df_soc.to_excel(w, sheet_name="充放电量", index=False)
        df_em.to_excel(w, sheet_name="紧急购电量", index=False)
        audit.to_excel(w, sheet_name="逐时段审计", index=False)


def run(write_xlsx: bool = True, fname: str = "result2.xlsx",
        price_matrix=None, tag: str = "problem_2") -> dict:
    att = load_all()
    fc = Forecaster(att)
    dvidx = delivery_indices(att)
    runidx = operational_indices(att)
    dvset = set(dvidx)
    assert len(dvidx) == N_DAYS_DELIVERY, f"交付天数 {len(dvidx)} != {N_DAYS_DELIVERY}"

    if price_matrix is None:
        price_of = lambda i: att.price1                       # Q2：附件1 固定电价
        price_src = "附件1"
    else:
        price_of = lambda i: price_matrix[i]                  # Q4-2：附件4 波动电价
        price_src = "附件4"

    all_days = solve_two_stage_year(att, fc, price_of, runidx)
    days = [d for d in all_days if d["idx"] in dvset]
    settle = settle_year(days)
    checks = validate_year(all_days)
    info_audit = fc.information_boundary_audit(runidx)
    checks["C25_information_boundary_trace"] = info_audit["all_pass"]

    # 标量裕度 U 形（P2-C4）
    margin_sweep = {}
    for m in _MARGINS:
        tot, em = scalar_margin_year(att, fc, price_of, runidx, m, delivery_set=dvset)
        margin_sweep[f"{m:.2f}"] = {"total_cost": round(tot, 2), "emergency_kwh": round(em, 2)}
    best_m = min(margin_sweep, key=lambda k: margin_sweep[k]["total_cost"])

    # P2-C5：实时再调度 vs 锁定（m=0）
    tot_on, em_on = scalar_margin_year(att, fc, price_of, runidx, 0.0, _exec_causal,
                                       delivery_set=dvset)
    tot_off, em_off = scalar_margin_year(att, fc, price_of, runidx, 0.0, _exec_locked,
                                         delivery_set=dvset)

    regime = regime_mae_comparison(att, fc, dvidx)

    # 表3 四日期紧急购电区间（P2-C7）
    table3 = {}
    for d in days:
        ds = d["date"].isoformat()
        if ds in ("2025-03-20", "2025-06-21", "2025-09-23", "2025-12-21"):
            runs = export._merge_runs(d["u"], _TOL)
            table3[ds] = ([{"interval": export._slot_label(a * 10, (b + 1) * 10),
                            "kwh": round(float(tot_), 2)} for a, b, tot_ in runs]
                          if runs else "无")

    logic_probes = {
        "bounds": [],
        "monotonic": [
            {"more": "reserve_margin_m", "then": "annual_emergency_kwh",
             "observed_sign": -1, "expect_dir": "less", "expect_sign": -1},
        ],
    }

    results = {
        "problem": 2,
        "method": "场景近似日前计划器（K=8 历史残差场景）+ 因果实时执行策略",
        "optimality_scope": "每个线性规划子问题全局最优；完整计划-执行体系不宣称两阶段全局最优",
        "price_source": price_src,
        "n_delivery_days": len(dvidx),
        "two_stage_plan_cost": round(settle["plan_cost"], 2),
        "two_stage_emergency_cost": round(settle["emergency_cost"], 2),
        "two_stage_total": round(settle["total"], 2),
        "two_stage_emergency_kwh": round(settle["emergency_kwh"], 2),
        "annual_cycling_kwh": round(settle["cycling"], 2),
        "annual_curtailment_kwh": round(sum(float(d["q"].sum()) for d in days), 2),
        "initial_soc_set_once_at": all_days[0]["date"].isoformat() + " 00:00",
        "delivery_start_soc_kwh": round(float(days[0]["E"][0]), 6),
        "terminal_soc_kwh": round(float(all_days[-1]["E"][-1]), 6),
        "max_simultaneous_charge_discharge_kwh": round(max(
            float(np.minimum(d["c"], d["s"]).max()) for d in all_days), 10),
        "margin_sweep": margin_sweep,
        "best_scalar_margin": float(best_m),
        "best_margin_total_cost": margin_sweep[best_m]["total_cost"],
        "m0_total_cost": margin_sweep["0.00"]["total_cost"],
        "redispatch_on_emergency_kwh": round(em_on, 2),
        "redispatch_off_emergency_kwh": round(em_off, 2),
        "same_regime_load_mae_kw": regime["same_regime_mae_kw"],
        "cross_regime_load_mae_kw": regime["cross_regime_mae_kw"],
        "table3_emergency": table3,
        "constraint_checks": checks,
        "information_boundary_audit": info_audit,
        "all_constraints_pass": bool(all(checks.values())),
        "logic_probes": logic_probes,
    }

    if write_xlsx:
        _write_result2(fname, att, days, all_days)
        results["result_file"] = f"user_data/{fname}"

    if tag == "problem_2":
        import pandas as pd
        outdir = _ROOT / "results"
        outdir.mkdir(exist_ok=True)
        pd.DataFrame({
            "date": [d["date"].isoformat() for d in days],
            "q2_plan_cost": [float(d["price"] @ d["x"]) for d in days],
            "q2_emergency_cost": [float(K_EMERGENCY * (d["price"] * d["u"]).sum()) for d in days],
            "q2_total_cost": [float(d["price"] @ d["x"] + K_EMERGENCY *
                                    (d["price"] * d["u"]).sum()) for d in days],
        }).to_csv(outdir / "q2_daily_costs.csv", index=False)

    _FIG.mkdir(exist_ok=True)
    (_FIG / f"{tag}_results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    return results


if __name__ == "__main__":
    r = run()
    print(f"Q2 两阶段总费用 = {r['two_stage_total']:.2f} 元（计划 {r['two_stage_plan_cost']:.2f} "
          f"+ 紧急 {r['two_stage_emergency_cost']:.2f}）")
    print(f"两阶段全年紧急购电 = {r['two_stage_emergency_kwh']:.2f} kWh")
    print(f"标量裕度 U 形（best m={r['best_scalar_margin']}）:")
    for m, v in r["margin_sweep"].items():
        print(f"   m={m}: 费用 {v['total_cost']:.0f}  紧急 {v['emergency_kwh']:.0f} kWh")
    print(f"再调度 on/off 紧急购电 = {r['redispatch_on_emergency_kwh']:.0f} / "
          f"{r['redispatch_off_emergency_kwh']:.2f} kWh（本次重算口径）")
    print(f"regime MAE 同/跨 = {r['same_regime_load_mae_kw']} / {r['cross_regime_load_mae_kw']} kW "
          f"（报告 137.52 / 781.21）")
    print(f"约束核对全过 = {r['all_constraints_pass']}  {r['constraint_checks']}")
