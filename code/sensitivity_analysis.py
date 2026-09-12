# -*- coding: utf-8 -*-
"""敏感度分析（§5.6 / 假设问责表）：四项独立重算，落 figures/sensitivity_results.json。

1. efficiency_convention  —— GL-C3 五种效率口径下 Q1 平均日目标（eta·eta↑ → 费用↓）。
2. W_load_window          —— 同 regime 负载预测窗口 W∈{2,3,4,6,8} 的留出期 MAE（证 W=4）。
3. lead_time_pv_mae       —— 午后 PV 预报 MAE vs 提前期（发布 0/6/12h 早于午后窗；18h 发布已
                             在窗后=「预报过去」剔除。提前期↑→MAE↑，证多时刻滚动预报价值，L6）。
4. scalar_margin_sweep    —— 全年标量裕度 m 扫描的 U 形（P2-C4：m↑ → 紧急购电↓）。
所有信息集严格 j<d，与主模型同口径（不泄漏）。
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from params import DT_H, ETA_CONVENTIONS, N_DAYS_DELIVERY
from io_layer import load_all
from forecast import Forecaster, LOW_WEEKDAYS
from lp_kernel import solve_day_q1
from problem2 import delivery_indices, operational_indices, scalar_margin_year, _MARGINS

_ROOT = Path(__file__).resolve().parent.parent
_FIG = _ROOT / "figures"
_W_GRID = [2, 3, 4, 6, 8]
_ISSUE_HOURS = [0, 6, 12, 18]
_AFTERNOON_FROM = 78          # 午后窗起始段（0基）：slot78 起始时刻 = 78·Δt = 13:00


def efficiency_convention(att) -> dict:
    """Q1 平均日：五种 (eta_c,eta_d) 口径的最优目标（元）。"""
    net = (att.load1 - att.pv1) * DT_H
    price = att.price1
    out = {}
    for name, (ec, ed) in ETA_CONVENTIONS.items():
        r = solve_day_q1(net, price, eta_c=ec, eta_d=ed, close=True)
        out[name] = {"eta_c": ec, "eta_d": ed, "objective": round(float(r.obj), 2)}
    return out


def _regime_of_idx(d):
    return "low" if d.weekday() in LOW_WEEKDAYS else "high"


def w_load_window(att, dvidx, w_grid=_W_GRID) -> dict:
    """同 regime 最近 W 天负载均值的留出期 MAE（kW）；严格 j<d。"""
    dates = att.dates
    regimes = np.array([_regime_of_idx(d) for d in dates])
    load_kw = att.load_actual
    dv = set(dvidx)
    out = {}
    for w in w_grid:
        errs = []
        for i in range(len(dates)):
            if i not in dv:
                continue
            r = regimes[i]
            same = [j for j in range(i) if regimes[j] == r]
            picks = same[-w:] if same else list(range(max(0, i - w), i))
            if not picks:
                continue
            pred = load_kw[np.array(picks)].mean(axis=0)
            errs.append(np.abs(pred - load_kw[i]))
        out[str(w)] = round(float(np.concatenate(errs).mean()), 2) if errs else None
    return out


def lead_time_pv_mae(att, fc, dvidx, issue_hours=_ISSUE_HOURS) -> dict:
    """午后 PV 预报 MAE（kW）vs 提前期。发布时刻 h 到午后窗起点（13:00）的提前期
    = 13-h（h<13 时有效）；h>=13 的发布已在午后窗内/后（「预报过去」），插值把整段午后
    钳到日落后≈0，MAE 是伪值，故标 out_of_window 不计入方向判定。提前期↑→MAE↑（L6）。"""
    out = {}
    aft = np.arange(fc.T) >= _AFTERNOON_FROM
    aft_start_h = _AFTERNOON_FROM * DT_H              # 午后窗起点钟点 = 13.0
    for h in issue_hours:
        if h >= aft_start_h:                         # 发布已在午后窗内/后 → 非提前预报
            out[f"{h}h"] = {"lead_time_h": None, "mae_kw": None, "out_of_window": True}
            continue
        errs = []
        for i in dvidx:
            g_kw = fc.interp_pv_kwh(i, h) / DT_H
            errs.append(np.abs(g_kw - att.pv_actual[i])[aft])
        mae = round(float(np.concatenate(errs).mean()), 2) if errs else None
        out[f"{h}h"] = {"lead_time_h": round(aft_start_h - h, 2), "mae_kw": mae,
                        "out_of_window": False}
    return out


def scalar_margin_sweep(att, fc, dvidx, margins=_MARGINS) -> dict:
    """全年标量裕度 U 形：净输入 (1+m)ℓ̂-ĝ 求 Q1 LP → 因果结算（附件1 电价）。"""
    price_of = lambda i: att.price1
    runidx = operational_indices(att)
    dvset = set(dvidx)
    out = {}
    for m in margins:
        tot, em = scalar_margin_year(att, fc, price_of, runidx, m, delivery_set=dvset)
        out[f"{m:.2f}"] = {"total_cost": round(tot, 2), "emergency_kwh": round(em, 2)}
    best = min(out, key=lambda k: out[k]["total_cost"])
    return {"sweep": out, "interior_optimum_m": float(best)}


def run() -> dict:
    att = load_all()
    fc = Forecaster(att)
    dvidx = delivery_indices(att)
    assert len(dvidx) == N_DAYS_DELIVERY, f"交付天数 {len(dvidx)} != {N_DAYS_DELIVERY}"

    eff = efficiency_convention(att)
    wwin = w_load_window(att, dvidx)
    lead = lead_time_pv_mae(att, fc, dvidx)
    margin = scalar_margin_sweep(att, fc, dvidx)

    eta_pairs = sorted(
        ((v["eta_c"] * v["eta_d"], v["objective"]) for v in eff.values()))
    eff_sign = -1 if eta_pairs[-1][1] < eta_pairs[0][1] else 1     # eta↑ → cost↓ 期望 -1
    w_vals = [(int(k), v) for k, v in wwin.items() if v is not None]
    # 仅用窗前发布（有真实提前期）判方向；按提前期升序，最长提前期 MAE 应 > 最短提前期 MAE
    lead_pts = sorted((v["lead_time_h"], v["mae_kw"]) for v in lead.values()
                      if not v["out_of_window"] and v["mae_kw"] is not None)
    lead_sign = 0
    if len(lead_pts) >= 2:
        lead_sign = 1 if lead_pts[-1][1] > lead_pts[0][1] else (
            -1 if lead_pts[-1][1] < lead_pts[0][1] else 0)  # 提前期↑ → MAE↑ 期望 +1
    sw = margin["sweep"]
    m_keys = sorted(sw, key=float)
    em_first, em_last = sw[m_keys[0]]["emergency_kwh"], sw[m_keys[-1]]["emergency_kwh"]
    margin_sign = -1 if em_last < em_first else 1                  # m↑ → 紧急↓ 期望 -1

    logic_probes = {
        "bounds": [],
        "monotonic": [
            {"more": "eta_c*eta_d", "then": "Q1_total_cost",
             "observed_sign": eff_sign, "expect_dir": "decreasing", "expect_sign": -1},
            {"more": "lead_time_hours", "then": "pv_forecast_MAE",
             "observed_sign": lead_sign, "expect_dir": "increasing", "expect_sign": 1},
            {"more": "reserve_margin_m", "then": "annual_emergency_kwh",
             "observed_sign": margin_sign, "expect_dir": "decreasing", "expect_sign": -1},
        ],
    }

    best_w = min(w_vals, key=lambda kv: kv[1])[0] if w_vals else None
    results = {
        "analysis": "敏感度：效率口径 / 预测窗口 W / 光伏提前期 / 标量裕度 U 形",
        "efficiency_convention": eff,
        "W_load_window_mae_kw": wwin,
        "best_W_by_mae": best_w,
        "lead_time_pv_mae_kw": lead,
        "scalar_margin": margin,
        "logic_probes": logic_probes,
    }
    _FIG.mkdir(exist_ok=True)
    (_FIG / "sensitivity_results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    return results


if __name__ == "__main__":
    r = run()
    print("效率口径目标:", {k: v["objective"] for k, v in r["efficiency_convention"].items()})
    print("W 窗口 MAE(kW):", r["W_load_window_mae_kw"], "→ best W =", r["best_W_by_mae"])
    print("午后 PV MAE(kW) vs 提前期:",
          {k: (f"lead={v['lead_time_h']}h MAE={v['mae_kw']}" if not v["out_of_window"]
               else "窗后剔除") for k, v in r["lead_time_pv_mae_kw"].items()})
    print("标量裕度内点最优 m =", r["scalar_margin"]["interior_optimum_m"])
    for mm, vv in r["scalar_margin"]["sweep"].items():
        print(f"   m={mm}: 费用 {vv['total_cost']:.0f}  紧急 {vv['emergency_kwh']:.0f}")
