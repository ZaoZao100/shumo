# -*- coding: utf-8 -*-
"""独立约束审计（§5.5 / C1-C22）：只从**交付产物** result*.xlsx 重算，不采信内存解。

设计原则
--------
* 数据源＝五个输出表 + 附件（仅取电价/实际负载光伏）。绝不 import 各 problem 的求解结果。
* SOC 一律带单向效率重算：E_{k+1}=E_k+η_c·c_k − s_k/η_d（把充放电量当净变化累加即判错）。
* 交付模板把储能压成 6 个 4 小时桶。桶边界 SOC 是逐槽轨迹在 4h 处的**精确抽样**
  （求和线性、效率为常数 ⇒ E_桶末 = E_槽末），故端点/跨日/闭合核对精确；区间/功率上限
  在桶粒度核（越界必要条件），并如实标注粒度。
* 计划量、Q3 计划/调整量为逐槽交付 ⇒ 计划费用、Q3 偏差恒等式(dp−dm==a−b)逐槽精确核。
* 末尾把可精确重算的标量（计划费用、SOC 端点）与 figures/*_results.json 对账。

退出码：全过 0，任一硬核对失败 1。
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from params import (T, DT_H, P_MAX, E_MIN, E_MAX, E_INIT, E_TERMINAL, ETA_C, ETA_D, E_STEP_MAX,
                    SOC_BUCKET_H, DT_MIN, N_DAYS_DELIVERY, PARAM_TUPLE_C18)
from io_layer import load_all

_ROOT = Path(__file__).resolve().parent.parent
_DATA = _ROOT / "user_data"
_FIG = _ROOT / "figures"

_TOL = 1e-6
_COST_TOL = 0.05                                    # 元：容许 round(2) 往返误差
_BAL_TOL = 1e-3                                     # kWh：日/桶级平衡容差
_SLOTS_PER_BUCKET = SOC_BUCKET_H * 60 // DT_MIN     # 24 段/桶
_N_BUCKET = T // _SLOTS_PER_BUCKET                  # 6 桶
_BUCKET_CAP = _SLOTS_PER_BUCKET * E_STEP_MAX        # 桶级充放上限 = 24·(5000/6)


# ------------------------- 交付表读取（严格按 export.py 列序） -------------------------
def _read_wide_plan(fname: str, sheet: str) -> tuple[list, np.ndarray, np.ndarray, np.ndarray]:
    """宽表：返回 (dates, plan[n,144], daily_total[n], daily_cost[n])。列序 = 日期,144 槽,合计,费用。"""
    df = pd.read_excel(_DATA / fname, sheet_name=sheet)
    cols = list(df.columns)
    dates = [pd.to_datetime(v).date() for v in df[cols[0]]]
    plan = df[cols[1:1 + T]].to_numpy(dtype=float)
    daily_total = df[cols[T + 1]].to_numpy(dtype=float)
    daily_cost = df[cols[T + 2]].to_numpy(dtype=float)
    return dates, plan, daily_total, daily_cost


def _read_soc_buckets(fname: str, single_day: bool) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """充放电量表：返回 (charge[n,6], discharge[n,6], E0[n], ET[n])。

    多日：列 = 日期,时间段,充电,放电,时刻,储电量；每 6 行一日，b0 填 0:00 端点、b1 填 24:00 端点。
    单日(result1)：无日期列，列 = 时间段,充电,放电,时刻,储电量。
    """
    df = pd.read_excel(_DATA / fname, sheet_name="充放电量")
    cols = list(df.columns)
    base = 0 if single_day else 1
    charge_col, dis_col, soc_col = cols[base + 1], cols[base + 2], cols[base + 4]
    chg = df[charge_col].to_numpy(dtype=float)
    dis = df[dis_col].to_numpy(dtype=float)
    soc = df[soc_col].to_numpy(dtype=float)
    n = len(df) // _N_BUCKET
    chg = chg.reshape(n, _N_BUCKET)
    dis = dis.reshape(n, _N_BUCKET)
    soc = soc.reshape(n, _N_BUCKET)
    E0 = soc[:, 0]                                   # 每日 b0 行 = 0:00 端点
    ET = soc[:, 1]                                   # 每日 b1 行 = 24:00 端点
    return chg, dis, E0, ET


def _read_emergency_total(fname: str) -> float:
    """紧急购电量表：全年总量 kWh（第 3 列求和；『无』占位行 NaN 自然跳过）。"""
    df = pd.read_excel(_DATA / fname, sheet_name="紧急购电量")
    vals = pd.to_numeric(df[df.columns[2]], errors="coerce").to_numpy(dtype=float)
    return float(np.nansum(vals))


def _recon_soc(chg_day: np.ndarray, dis_day: np.ndarray, E0: float) -> np.ndarray:
    """桶级 SOC 重算（含单向效率）：E[k+1]=E[k]+η_c·c_k − s_k/η_d，返回长度 7。"""
    E = np.empty(_N_BUCKET + 1)
    E[0] = E0
    for k in range(_N_BUCKET):
        E[k + 1] = E[k] + ETA_C * chg_day[k] - dis_day[k] / ETA_D
    return E


def _load_fig(fname: str, key: str):
    p = _FIG / fname
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8")).get(key)


def _audit_interval_trace(fname: str, expect_terminal: bool) -> tuple[dict, dict]:
    """从新增逐时段审计表精确核对等式平衡、SOC、互斥、功率换算与端点。"""
    df = pd.read_excel(_DATA / fname, sheet_name="逐时段审计")
    c = df["充电_kWh"].to_numpy(float)
    s = df["放电_kWh"].to_numpy(float)
    u = df["紧急购电_kWh"].to_numpy(float)
    q = df["弃光q_kWh"].to_numpy(float)
    x = df["执行购电_kWh"].to_numpy(float)
    load = df["实际负载L_kWh"].to_numpy(float)
    pv = df["实际光伏G_kWh"].to_numpy(float)
    e0 = df["SOC期初_kWh"].to_numpy(float)
    e1 = df["SOC期末_kWh"].to_numpy(float)
    pc = df["充电功率_kW"].to_numpy(float)
    ps = df["放电功率_kW"].to_numpy(float)
    residual = x + pv + u + s - load - c - q
    prefix = f"{fname}_exact"
    checks = {
        f"{prefix}_balance_equality": bool(np.max(np.abs(residual)) <= _BAL_TOL),
        f"{prefix}_soc_recursion": bool(np.max(np.abs(e1 - (e0 + ETA_C*c - s/ETA_D))) <= _BAL_TOL),
        f"{prefix}_soc_range": bool(e0.min() >= E_MIN-_BAL_TOL and e1.max() <= E_MAX+_BAL_TOL),
        f"{prefix}_cross_interval_continuity": bool(np.max(np.abs(e0[1:] - e1[:-1])) <= _BAL_TOL),
        f"{prefix}_initial_soc_once": bool(abs(e0[0] - E_INIT) <= _BAL_TOL),
        f"{prefix}_terminal_soc": bool((not expect_terminal) or abs(e1[-1]-E_TERMINAL) <= _BAL_TOL),
        f"{prefix}_curtailment_nonnegative": bool(q.min() >= -1e-9),
        f"{prefix}_no_simultaneous_charge_discharge": bool(np.minimum(c, s).max() <= _TOL),
        f"{prefix}_energy_cap": bool(max(c.max(), s.max()) <= E_STEP_MAX + _TOL),
        f"{prefix}_kw_kwh_conversion": bool(
            max(np.max(np.abs(pc-c/DT_H)), np.max(np.abs(ps-s/DT_H))) <= _TOL
            and max(pc.max(), ps.max()) <= P_MAX + _TOL),
    }
    metrics = {
        "n_intervals": int(len(df)),
        "max_balance_abs_kwh": float(np.max(np.abs(residual))),
        "max_simultaneous_kwh": float(np.minimum(c, s).max()),
        "curtailment_total_kwh": float(q.sum()),
        "initial_soc_kwh": float(e0[0]),
        "terminal_soc_kwh": float(e1[-1]),
    }
    return checks, metrics


def _soc_checks_multi(chg, dis, E0, ET, checks: dict, prefix: str) -> None:
    """跨日 SOC 桶级重算：C3 端点递推、C4 区间、C7 单日闭合(不查)、C8 跨日串联、C5C6 桶级功率。

    端点递推：由桶充放独立重算的当日末 SOC 必须 == 表内 24:00 端点（证效率被正确带入）。
    """
    n = chg.shape[0]
    ok_rec = ok_range = ok_cap = ok_carry = True
    Efinals = np.empty(n)
    for i in range(n):
        E = _recon_soc(chg[i], dis[i], E0[i])
        Efinals[i] = E[-1]
        ok_rec &= bool(abs(E[-1] - ET[i]) <= max(_TOL, 1e-6 * abs(ET[i])))
        ok_range &= bool(E.min() >= E_MIN - _BAL_TOL and E.max() <= E_MAX + _BAL_TOL)
        ok_cap &= bool(chg[i].max() <= _BUCKET_CAP + _TOL and dis[i].max() <= _BUCKET_CAP + _TOL)
    for i in range(1, n):
        ok_carry &= bool(abs(E0[i] - ET[i - 1]) <= _BAL_TOL)
    checks[f"{prefix}_C3_soc_endpoint_recursion"] = ok_rec
    checks[f"{prefix}_C4_soc_range_bucketwise"] = ok_range
    checks[f"{prefix}_C5C6_bucket_power_cap"] = ok_cap
    # 主表从2月交付期开始，首日SOC来自1月末；全年首次E_INIT由逐时段审计表另查。
    checks[f"{prefix}_C8_delivery_cross_day_carry"] = bool(ok_carry)


def audit_result1() -> dict:
    """result1：确定性 Q1 单日。C1 平衡(桶级必要条件)、C3 递推、C4 区间、C5C6 上限、
    C7 首尾闭合、C9 非负、计划费用对账。"""
    att = load_all()
    checks: dict = {}
    df = pd.read_excel(_DATA / "result1.xlsx", sheet_name="计划购电量")
    x = df[df.columns[1]].to_numpy(dtype=float)      # 144 槽计划购电量 kWh
    checks["R1_C9_plan_nonneg"] = bool(x.min() >= -1e-9)
    checks["R1_plan_len_144"] = bool(x.shape[0] == T)

    chg, dis, E0, ET = _read_soc_buckets("result1.xlsx", single_day=True)
    E = _recon_soc(chg[0], dis[0], E0[0])
    checks["R1_C3_soc_endpoint_recursion"] = bool(abs(E[-1] - ET[0]) <= _TOL)
    checks["R1_C4_soc_range_bucketwise"] = bool(E.min() >= E_MIN - _BAL_TOL and
                                                E.max() <= E_MAX + _BAL_TOL)
    checks["R1_C5C6_bucket_power_cap"] = bool(chg[0].max() <= _BUCKET_CAP + _TOL and
                                              dis[0].max() <= _BUCKET_CAP + _TOL)
    checks["R1_C7_closure"] = bool(abs(E[-1] - E[0]) <= _BAL_TOL and abs(E0[0] - E_INIT) <= _TOL)
    checks["R1_C9_storage_nonneg"] = bool(chg.min() >= -1e-9 and dis.min() >= -1e-9)

    # C1 平衡（桶级必要条件）：Σ_bucket(x + s − c) ≥ Σ_bucket net（无紧急机制，须硬满足）
    att_ = load_all()
    net = (att_.load1 - att_.pv1) * DT_H             # 144 净需求 kWh
    net_b = net.reshape(_N_BUCKET, _SLOTS_PER_BUCKET).sum(axis=1)
    x_b = x.reshape(_N_BUCKET, _SLOTS_PER_BUCKET).sum(axis=1)
    supply_minus_net_b = x_b + dis[0] - chg[0] - net_b
    checks["R1_C1_balance_bucket"] = bool(supply_minus_net_b.min() >= -_BAL_TOL)

    # 计划费用对账：Σ price·x（附件1）↔ figures Q1_total_cost
    recomputed = float(att_.price1 @ x)
    fig = _load_fig("problem_1_results.json", "Q1_total_cost")
    checks["R1_plan_cost_matches_figure"] = bool(
        fig is not None and abs(round(recomputed, 2) - fig) <= _COST_TOL)
    exact_checks, exact_metrics = _audit_interval_trace("result1.xlsx", expect_terminal=True)
    checks.update(exact_checks)
    return {"file": "result1.xlsx", "recomputed_plan_cost": round(recomputed, 2),
            "figure_plan_cost": fig, "exact_trace_metrics": exact_metrics, "checks": checks}


def _read_emergency_by_date(fname: str) -> dict:
    """紧急购电量表 → {date: 当日紧急总量 kWh}（日期列 ffill；『无』占位 NaN 跳过）。"""
    df = pd.read_excel(_DATA / fname, sheet_name="紧急购电量")
    cols = list(df.columns)
    d = df[cols[0]].ffill()
    v = pd.to_numeric(df[cols[2]], errors="coerce")
    out: dict = {}
    for di, vi in zip(d, v):
        if pd.isna(di) or pd.isna(vi):
            continue
        key = pd.to_datetime(di).date()
        out[key] = out.get(key, 0.0) + float(vi)
    return out


def _price_lookup(att, volatile: bool):
    if volatile:
        return lambda dt: att.price_volatile[att.date_index[dt]]
    return lambda dt: att.price1


def audit_multiday(fname: str, is_q3: bool, volatile: bool,
                   fig_file: str, plan_cost_key: str,
                   emergency_min: float = 1e4) -> dict:
    """result2/3/4-* 共用审计。逐槽读计划(与 Q3 调整)、桶级读储能、按日读紧急。

    C9 非负、C3/C4/C5C6/C8 桶级 SOC、C22 紧急量>阈值、日级平衡必要条件、计划费用对账；
    Q3 另核 C11/C12 偏差恒等式(dp−dm==a−b) 与 计划/调整费用列 = price·b / price·a。
    """
    att = load_all()
    price_of = _price_lookup(att, volatile)
    checks: dict = {}

    dates, plan, day_tot, day_cost = _read_wide_plan(fname, "计划购电量")
    n = len(dates)
    checks[f"{fname}_n_days_334"] = bool(n == N_DAYS_DELIVERY)
    checks[f"{fname}_plan_len_144"] = bool(plan.shape[1] == T)
    checks[f"{fname}_C9_plan_nonneg"] = bool(plan.min() >= -1e-9)
    # 全天购电量列 == 逐槽和（模板一致性）
    checks[f"{fname}_daily_total_matches_sum"] = bool(
        np.abs(day_tot - plan.sum(axis=1)).max() <= _BAL_TOL)

    if is_q3:
        _da, adj, _at, adj_cost = _read_wide_plan(fname, "调整购电量")
        checks[f"{fname}_adjust_nonneg"] = bool(adj.min() >= -1e-9)
        exec_plan = adj                                  # 执行量 = 调整量 a
        b_plan = plan                                    # 原始计划 b
        dp = np.maximum(exec_plan - b_plan, 0.0)
        dm = np.maximum(b_plan - exec_plan, 0.0)
        checks[f"{fname}_C11C12_dev_identity"] = bool(
            np.abs((dp - dm) - (exec_plan - b_plan)).max() <= _TOL)
    else:
        exec_plan = plan                                 # Q2 执行量 = 计划量

    chg, dis, E0, ET = _read_soc_buckets(fname, single_day=False)
    checks[f"{fname}_C9_storage_nonneg"] = bool(chg.min() >= -1e-9 and dis.min() >= -1e-9)
    _soc_checks_multi(chg, dis, E0, ET, checks, fname)

    emerg_by_date = _read_emergency_by_date(fname)
    emerg_total = float(sum(emerg_by_date.values()))
    # 紧急购电非零只作描述量，不能作为无数据泄漏的充分判据。
    checks[f"{fname}_emergency_total_nonnegative"] = bool(emerg_total >= -_TOL)

    # 日级平衡必要条件：Σ_day(执行计划 + 紧急 + 放 − 充) ≥ Σ_day 实际净需求
    worst = np.inf
    for i, dt in enumerate(dates):
        ridx = att.date_index[dt]
        net_day = float(((att.load_actual[ridx] - att.pv_actual[ridx]) * DT_H).sum())
        u_day = emerg_by_date.get(dt, 0.0)
        supply = float(exec_plan[i].sum()) + u_day + float(dis[i].sum()) - float(chg[i].sum())
        worst = min(worst, supply - net_day)
    checks[f"{fname}_balance_daily_necessary"] = bool(worst >= -_BAL_TOL)

    # 计划费用对账：Σ_day price·(执行计划) ↔ figures 计划/基价键
    recomputed_plan = sum(float(price_of(dt) @ exec_plan[i]) for i, dt in enumerate(dates))
    if is_q3:
        # Q3 计划费用键 = base_cost = Σ price·min(a,b)（R-b 主口径）
        recomputed_base = sum(
            float(price_of(dt) @ np.minimum(exec_plan[i], b_plan[i])) for i, dt in enumerate(dates))
        recon_for_key = recomputed_base
        # 附加：计划/调整费用列 == price·b / price·a
        col_b_ok = np.abs(day_cost - np.array(
            [float(price_of(dt) @ b_plan[i]) for i, dt in enumerate(dates)])).max() <= _COST_TOL
        col_a_ok = np.abs(adj_cost - np.array(
            [float(price_of(dt) @ exec_plan[i]) for i, dt in enumerate(dates)])).max() <= _COST_TOL
        checks[f"{fname}_plan_cost_col_matches"] = bool(col_b_ok)
        checks[f"{fname}_adjust_cost_col_matches"] = bool(col_a_ok)
    else:
        recon_for_key = recomputed_plan
        # 全天购电费列 == price·x
        col_ok = np.abs(day_cost - np.array(
            [float(price_of(dt) @ plan[i]) for i, dt in enumerate(dates)])).max() <= _COST_TOL
        checks[f"{fname}_daily_cost_col_matches"] = bool(col_ok)

    fig = _load_fig(fig_file, plan_cost_key)
    checks[f"{fname}_plan_cost_matches_figure"] = bool(
        fig is not None and abs(round(recon_for_key, 2) - fig) <= max(_COST_TOL, 1e-6 * abs(fig)))

    exact_checks, exact_metrics = _audit_interval_trace(fname, expect_terminal=True)
    checks.update(exact_checks)

    return {"file": fname, "n_days": n, "emergency_total_kwh": round(emerg_total, 2),
            "recomputed_plan_cost_key": round(recon_for_key, 2), "figure_plan_cost": fig,
            "worst_daily_balance_kwh": round(float(worst), 4),
            "exact_trace_metrics": exact_metrics, "checks": checks}


def run() -> dict:
    report: dict = {
        "audit": "约束复算审计（以result*.xlsx逐时段审计表为主，带单向效率SOC递推）",
        "soc_resolution_note": "模板主表保留6×4h汇总；新增逐时段审计表按10分钟精确核对"
                               "平衡等式、SOC递推、互斥充放、功率换算、跨日连续和末期SOC",
        "files": {},
    }
    # GL-C1：参数元组逐字核对（防凑整/替换）
    gl_c1 = bool(PARAM_TUPLE_C18 == (1200, 10800, 5000, 6000, 0.9, 0.9, 5, 1.5, 0.5))

    r1 = audit_result1()
    r2 = audit_multiday("result2.xlsx", is_q3=False, volatile=False,
                        fig_file="problem_2_results.json", plan_cost_key="two_stage_plan_cost")
    r3 = audit_multiday("result3.xlsx", is_q3=True, volatile=False,
                        fig_file="problem_3_results.json", plan_cost_key="S1_plan_cost")
    r42 = audit_multiday("result4-2.xlsx", is_q3=False, volatile=True,
                         fig_file="problem_4_2_results.json", plan_cost_key="two_stage_plan_cost")
    r43 = audit_multiday("result4-3.xlsx", is_q3=True, volatile=True,
                         fig_file="problem_4_3_results.json", plan_cost_key="S1_plan_cost")

    all_checks = {"GL_C1_param_tuple_verbatim": gl_c1}
    for r in (r1, r2, r3, r42, r43):
        report["files"][r["file"]] = r
        all_checks.update(r["checks"])

    # 信息边界用预测器索引轨迹核对；不再以紧急购电是否非零代替泄漏审计。
    for tag in ("problem_2_results.json", "problem_3_results.json",
                "problem_4_2_results.json", "problem_4_3_results.json"):
        p = _FIG / tag
        key = f"{tag}_information_boundary"
        if p.is_file():
            info = json.loads(p.read_text(encoding="utf-8")).get("information_boundary_audit", {})
            all_checks[key] = bool(info.get("all_pass"))
        else:
            all_checks[key] = False

    failed = [k for k, v in all_checks.items() if not v]
    report["global_checks"] = {"GL_C1_param_tuple_verbatim": gl_c1}
    report["n_checks"] = len(all_checks)
    report["n_failed"] = len(failed)
    report["failed_checks"] = failed
    report["all_pass"] = bool(not failed)

    _FIG.mkdir(exist_ok=True)
    (_FIG / "constraint_audit_results.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    rep = run()
    print(f"===== 约束复算审计（逐时段结果 + 信息索引轨迹）=====")
    for fname, r in rep["files"].items():
        n_fail = sum(1 for v in r["checks"].values() if not v)
        print(f"  {fname}: {len(r['checks'])} 项，{n_fail} 失败", end="")
        if "recomputed_plan_cost_key" in r:
            print(f"；计划费用重算 {r['recomputed_plan_cost_key']} vs 图 {r['figure_plan_cost']}"
                  f"；最差日平衡 {r.get('worst_daily_balance_kwh')} kWh"
                  f"；紧急 {r.get('emergency_total_kwh')} kWh")
        else:
            print(f"；计划费用重算 {r['recomputed_plan_cost']} vs 图 {r['figure_plan_cost']}")
    print(f"GL-C1 参数元组逐字 = {rep['global_checks']['GL_C1_param_tuple_verbatim']}")
    print(f"合计 {rep['n_checks']} 项核对，{rep['n_failed']} 失败；全过 = {rep['all_pass']}")
    if not rep["all_pass"]:
        print(f"失败项: {rep['failed_checks']}")
    sys.exit(0 if rep["all_pass"] else 1)
