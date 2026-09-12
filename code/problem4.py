# -*- coding: utf-8 -*-
"""问题4 驱动（§3.5）：实时波动电价（附件4）下重构问题2/3 + 固定/波动对照。

电价从确定参数升级为时变量 p_{d,t}（附件4，365×144）。保留 Q2/Q3 全部结构，
仅替换电价向量。P4-C1 电价信息假设双口径：
  主口径（已知）：0:00 已知当日 p_{d,t}（乐观界）——直接把 Q2/Q3 电价源换附件4 重跑。
  第二口径（需预测）：p̂_{d,t}=同 regime 最近 W 天同时段均价（严格 j<d），计划用 p̂、
    结算用真实 p；两口径费用差即「价格信息的价值」。
P4-C2/C3 交付 result4-2.xlsx / result4-3.xlsx（复用 problem2/problem3 的 price_matrix）。
P4-C4 在同一 334 天集合对照固定（附件1）vs 波动（附件4）的总费用、循环量、紧急量。
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from params import T, DT_H, K_EMERGENCY, N_DAYS_DELIVERY
from io_layer import load_all
from forecast import Forecaster, W_LOAD
from problem2 import delivery_indices, operational_indices, solve_two_stage_year, settle_year
import problem2
import problem3

_ROOT = Path(__file__).resolve().parent.parent
_FIG = _ROOT / "figures"


def build_price_forecast(att, fc) -> np.ndarray:
    """价格点预测 p̂ (365,144)：同 regime 最近 W 天同时段均价，信息集严格 j<d（无泄漏）。

    与 forecast._load_forecast_kwh 的 regime/窗口口径完全一致，仅把被平均量换成附件4 电价。
    """
    n = len(att.dates)
    phat = np.zeros((n, T))
    for d in range(n):
        r = fc.regimes[d]
        same = [j for j in range(d) if fc.regimes[j] == r]
        if same:
            picks = same[-W_LOAD:]
        else:
            picks = list(range(max(0, d - W_LOAD), d))     # 保底最近若干天（不泄漏）
        if not picks:
            phat[d] = att.price1                           # d=0 使用附件1已给定分时价先验
        else:
            phat[d] = att.price_volatile[np.array(picks)].mean(axis=0)
    return phat


def price_forecast_mae(phat: np.ndarray, vol: np.ndarray, dvidx: list) -> float:
    """交付期价格预测 MAE（元/kWh）：逐时段 |p̂-p| 全体均值。"""
    idx = np.array(dvidx)
    return float(np.abs(phat[idx] - vol[idx]).mean())


def _read_fixed_metrics(fname: str, keys: list) -> dict:
    """从 figures/<fname> 只取所需标量键（程序内读取，不载入全文）。缺文件/键返回 None 值。"""
    p = _FIG / fname
    if not p.is_file():
        return {k: None for k in keys}
    data = json.loads(p.read_text(encoding="utf-8"))
    return {k: data.get(k) for k in keys}


def _intraday_spread(price_row: np.ndarray) -> float:
    return float(price_row.max() - price_row.min())


def _low_price_plan_share(days) -> float:
    """峰谷价差利用率：计划购电量落在当日低价（低于日内中位价）时段的占比。"""
    lo_kwh = 0.0
    tot_kwh = 0.0
    for d in days:
        p = d["price"]
        x = d["x"]
        med = float(np.median(p))
        lo_kwh += float(x[p < med].sum())
        tot_kwh += float(x.sum())
    return lo_kwh / tot_kwh if tot_kwh > 0 else float("nan")


def run(write_xlsx: bool = True) -> dict:
    att = load_all()
    fc = Forecaster(att)
    dvidx = delivery_indices(att)
    runidx = operational_indices(att)
    dvset = set(dvidx)
    assert len(dvidx) == N_DAYS_DELIVERY, f"交付天数 {len(dvidx)} != {N_DAYS_DELIVERY}"

    vol = att.price_volatile                     # 附件4 (365,144)
    phat = build_price_forecast(att, fc)         # 同 regime W=4 均价预测（无泄漏）
    price_mae = price_forecast_mae(phat, vol, dvidx)

    # ---- 主口径（0:00 已知波动电价）：重跑 Q2 与 Q3 全流程，电价源换附件4 ----
    q4_2 = problem2.run(write_xlsx=write_xlsx, fname="result4-2.xlsx",
                        price_matrix=vol, tag="problem_4_2")
    q4_3 = problem3.run(write_xlsx=write_xlsx, fname="result4-3.xlsx",
                        price_matrix=vol, tag="problem_4_3")

    # ---- 第二口径（需预测）：计划用 p̂，结算用真实 p；价格信息的价值 ----
    vol_of = lambda i: vol[i]
    phat_of = lambda i: phat[i]
    all_days_pred = solve_two_stage_year(att, fc, phat_of, runidx, settle_price_of=vol_of)
    days_pred = [d for d in all_days_pred if d["idx"] in dvset]
    pred = settle_year(days_pred)
    known_total = q4_2["two_stage_total"]
    value_of_price_info = pred["total"] - known_total     # >0：预测口径更贵（信息有价值）
    low_price_share = _low_price_plan_share(days_pred)

    # ---- P4-C4 固定（附件1）vs 波动（附件4）对照，同一 334 天集合 ----
    q2_fixed = _read_fixed_metrics("problem_2_results.json",
                                   ["two_stage_total", "annual_cycling_kwh",
                                    "two_stage_emergency_kwh"])
    q3_fixed = _read_fixed_metrics("problem_3_results.json",
                                   ["S1_total", "S1_cycling_kwh", "S1_emergency_kwh"])
    idx = np.array(dvidx)
    spread_fixed = float(np.mean([_intraday_spread(att.price1) for _ in idx]))
    spread_vol = float(np.mean([_intraday_spread(vol[i]) for i in idx]))

    comparison = {
        "Q2_vs_Q4_2_two_stage": {
            "total_cost": {"fixed": q2_fixed["two_stage_total"],
                           "volatile": q4_2["two_stage_total"]},
            "cycling_kwh": {"fixed": q2_fixed["annual_cycling_kwh"],
                            "volatile": q4_2["annual_cycling_kwh"]},
            "emergency_kwh": {"fixed": q2_fixed["two_stage_emergency_kwh"],
                              "volatile": q4_2["two_stage_emergency_kwh"]},
        },
        "Q3_vs_Q4_3_rolling_S1": {
            "total_cost": {"fixed": q3_fixed["S1_total"],
                           "volatile": q4_3["S1_total"]},
            "cycling_kwh": {"fixed": q3_fixed["S1_cycling_kwh"],
                            "volatile": q4_3["S1_cycling_kwh"]},
            "emergency_kwh": {"fixed": q3_fixed["S1_emergency_kwh"],
                              "volatile": q4_3["S1_emergency_kwh"]},
        },
        "intraday_price_spread_yuan": {"fixed": round(spread_fixed, 4),
                                       "volatile": round(spread_vol, 4)},
        "low_price_plan_share_volatile": round(low_price_share, 4),
    }

    # 循环量方向探针（LOGIC_CONTRACT monotonic: peak_valley_spread↑ → cycling↑）
    cyc_fixed = q2_fixed["annual_cycling_kwh"]
    cyc_vol = q4_2["annual_cycling_kwh"]
    cyc_sign = 0
    if cyc_fixed is not None and cyc_vol is not None:
        cyc_sign = 1 if cyc_vol > cyc_fixed else (-1 if cyc_vol < cyc_fixed else 0)
    logic_probes = {
        "bounds": [],
        "monotonic": [
            {"more": "peak_valley_spread", "then": "storage_cycling",
             "observed_sign": cyc_sign, "expect_dir": "increasing", "expect_sign": 1},
            {"more": "price_forecast_error", "then": "total_cost",
             "observed_sign": 1 if value_of_price_info > 0 else -1,
             "expect_dir": "increasing", "expect_sign": 1},
        ],
    }

    results = {
        "problem": 4,
        "method": "附件4波动电价重构Q2/Q3（场景近似日前计划器 + 点预测滚动优化）+ 电价信息双口径 + 固定/波动对照",
        "price_source": "附件4",
        "n_delivery_days": len(dvidx),
        "price_info_conventions": {
            "main_known": "0:00 已知当日波动电价 p_{d,t}（乐观界）",
            "second_predicted": "p̂_{d,t}=同 regime 最近 W=4 天同时段均价（严格 j<d），结算用真实 p",
        },
        "price_forecast_mae_yuan_per_kwh": round(price_mae, 6),
        "Q4_2_two_stage_total_known": round(q4_2["two_stage_total"], 2),
        "Q4_2_two_stage_emergency_kwh": round(q4_2["two_stage_emergency_kwh"], 2),
        "Q4_2_annual_cycling_kwh": round(q4_2["annual_cycling_kwh"], 2),
        "Q4_2_two_stage_total_predicted": round(pred["total"], 2),
        "value_of_price_info_yuan": round(value_of_price_info, 2),
        "value_of_price_info_pct": round(value_of_price_info / known_total * 100, 4)
        if known_total else None,
        "Q4_3_S1_total_known": round(q4_3["S1_total"], 2),
        "Q4_3_S1_emergency_kwh": round(q4_3["S1_emergency_kwh"], 2),
        "Q4_3_S1_cycling_kwh": round(q4_3["S1_cycling_kwh"], 2),
        "Q4_3_rolling_value_yuan": q4_3["rolling_value_yuan"],
        "comparison_fixed_vs_volatile": comparison,
        "cycling_increases_under_volatility": bool(cyc_sign > 0),
        "result_files": ["user_data/result4-2.xlsx", "user_data/result4-3.xlsx"],
        "q4_2_all_constraints_pass": q4_2["all_constraints_pass"],
        "q4_3_all_constraints_pass": q4_3["all_constraints_pass"],
        "logic_probes": logic_probes,
    }

    _FIG.mkdir(exist_ok=True)
    (_FIG / "problem_4_results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    return results


if __name__ == "__main__":
    r = run()
    print(f"Q4 价格预测 MAE = {r['price_forecast_mae_yuan_per_kwh']:.6f} 元/kWh")
    print(f"Q4-2 两阶段总费用（已知）= {r['Q4_2_two_stage_total_known']:.2f}；"
          f"（预测）= {r['Q4_2_two_stage_total_predicted']:.2f}")
    print(f"价格信息的价值 = {r['value_of_price_info_yuan']:.2f} 元 "
          f"（{r['value_of_price_info_pct']}%）")
    print(f"Q4-3 S1 总费用（已知）= {r['Q4_3_S1_total_known']:.2f}；"
          f"紧急 {r['Q4_3_S1_emergency_kwh']:.2f} kWh")
    cmp2 = r["comparison_fixed_vs_volatile"]["Q2_vs_Q4_2_two_stage"]
    print(f"固定 vs 波动（Q2/4-2）总费用 {cmp2['total_cost']['fixed']} → {cmp2['total_cost']['volatile']}；"
          f"循环 {cmp2['cycling_kwh']['fixed']} → {cmp2['cycling_kwh']['volatile']}")
    print(f"日内价差 固定/波动 = {r['comparison_fixed_vs_volatile']['intraday_price_spread_yuan']}")
    print(f"波动下循环量上升 = {r['cycling_increases_under_volatility']}")
