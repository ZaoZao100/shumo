# -*- coding: utf-8 -*-
"""为 19 张数据图预计算真实数据载荷，逐图落地为 figures/data_<name>.json。

数据来源全部为真实附件与真实模型：
  - user_data/附件1..4.xlsx      经 code/io_layer.load_all() 摄入
  - code/lp_kernel.solve_day_q1  重解问题 1 的 LP（144 段 x/c/s + 145 点 SOC）
  - code/forecast.Forecaster     regime 负载预测、整点预报插值、残差
  - user_data/result2/3.xlsx     交付产物中的逐日紧急购电量
  - figures/*.json               上游已实测的标量（裕度扫描、效率口径、对照指标）
禁止编造：本脚本不写入任何未由上述来源计算/读取的数值。
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
FIG = ROOT / "figures"
sys.path.insert(0, str(ROOT / "code"))

from params import (T, DT_H, E_MIN, E_MAX, E_STEP_MAX, ETA_C, ETA_D,   # noqa: E402
                    ETA_CONVENTIONS, FORECAST_HOURS)
from io_layer import load_all                                          # noqa: E402
from forecast import Forecaster, regime_of, W_LOAD                     # noqa: E402
from lp_kernel import solve_day_q1                                     # noqa: E402
from settle import no_storage_baseline                                 # noqa: E402

DELIVERY_START = dt.date(2025, 2, 1)


def dump(name: str, payload: dict) -> None:
    path = FIG / f"data_{name}.json"
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1)
    print(f"  -> {path.name}")


def read_json(name: str) -> dict:
    with open(FIG / name, encoding="utf-8") as fh:
        return json.load(fh)


def emergency_by_day(fname: str) -> dict:
    """从交付产物读逐日紧急购电量 kWh（日期列为合并单元格，需 ffill）。"""
    df = pd.read_excel(ROOT / "user_data" / fname, sheet_name="紧急购电量")
    df.iloc[:, 0] = df.iloc[:, 0].ffill()
    out = {}
    for d, grp in df.groupby(df.columns[0]):
        key = pd.to_datetime(d).date().isoformat()
        out[key] = float(pd.to_numeric(grp.iloc[:, 2], errors="coerce").fillna(0).sum())
    return out


def main() -> None:
    print("[1/9] 摄入附件 ...")
    att = load_all()
    fc = Forecaster(att)
    dates = att.dates
    slot_h = (np.arange(T) + 1) * DT_H          # 各时段末刻（绝对小时）

    # ---------- 附件1 平均日断面 ----------
    print("[2/9] 附件1 断面 + 问题1 LP ...")
    net1_kwh = (att.load1 - att.pv1) * DT_H
    dump("att1_profile", {
        "slot_h": slot_h.tolist(),
        "price": att.price1.tolist(),
        "load_kw": att.load1.tolist(),
        "pv_kw": att.pv1.tolist(),
        "net_kwh": net1_kwh.tolist(),
        "price_min": float(att.price1.min()), "price_max": float(att.price1.max()),
        "load_daily_kwh": float(att.load1.sum() * DT_H),
        "pv_daily_kwh": float(att.pv1.sum() * DT_H),
    })

    # ---------- 问题1 LP 真实解 ----------
    res = solve_day_q1(net1_kwh, att.price1, eta_c=ETA_C, eta_d=ETA_D, close=True)
    assert res.status == 0, f"Q1 LP status={res.status}"
    base_slot = att.price1 * np.maximum(net1_kwh, 0.0)
    dump("q1_dispatch", {
        "slot_h": slot_h.tolist(),
        "price": att.price1.tolist(),
        "plan_kwh": res.x.tolist(),
        "charge_kwh": res.c.tolist(),
        "discharge_kwh": res.s.tolist(),
        "pv_used_kwh": np.minimum(att.pv1 * DT_H, att.load1 * DT_H).tolist(),
        "load_kwh": (att.load1 * DT_H).tolist(),
        "soc": res.E.tolist(),
        "soc_h": np.concatenate([[0.0], slot_h]).tolist(),
        "obj": float(res.obj),
        "e_min": float(E_MIN), "e_max": float(E_MAX), "e_step_max": float(E_STEP_MAX),
        "cost_slot_opt": (att.price1 * res.x).tolist(),
        "cost_slot_base": base_slot.tolist(),
        "baseline": float(no_storage_baseline(net1_kwh, att.price1)),
        "cycling_kwh": float(res.s.sum()),
    })

    # ---------- 效率口径灵敏度（复算 5 口径）----------
    print("[3/9] 效率五口径复算 ...")
    eta_rows = []
    for key, (ec, ed) in ETA_CONVENTIONS.items():
        r = solve_day_q1(net1_kwh, att.price1, eta_c=ec, eta_d=ed, close=True)
        assert r.status == 0, f"{key} status={r.status}"
        eta_rows.append({"key": key, "eta_c": float(ec), "eta_d": float(ed),
                         "cost": float(r.obj), "cycling_kwh": float(r.s.sum())})
    dump("eta_sensitivity", {"rows": eta_rows,
                             "main": "main",
                             "baseline": float(no_storage_baseline(net1_kwh, att.price1))})

    # ---------- 负载 regime 结构 ----------
    print("[4/9] 负载 regime 与日历 ...")
    daily_kwh = att.load_actual.sum(axis=1) * DT_H
    wd_groups = {w: daily_kwh[[i for i, d in enumerate(dates) if d.weekday() == w]].tolist()
                 for w in range(7)}
    low_idx = [i for i, d in enumerate(dates) if regime_of(d) == "low"]
    high_idx = [i for i, d in enumerate(dates) if regime_of(d) == "high"]
    low_shape = att.load_actual[low_idx].mean(axis=0)
    high_shape = att.load_actual[high_idx].mean(axis=0)
    dump("load_regime", {
        "weekday_daily_kwh": {str(k): v for k, v in wd_groups.items()},
        "weekday_names": ["周一", "周二", "周三", "周四", "周五", "周六", "周日"],
        "n_low": len(low_idx), "n_high": len(high_idx),
        "low_mean_daily_kwh": float(daily_kwh[low_idx].mean()),
        "high_mean_daily_kwh": float(daily_kwh[high_idx].mean()),
    })
    dump("regime_shape", {
        "slot_h": slot_h.tolist(),
        "low_kw": low_shape.tolist(),
        "high_kw": high_shape.tolist(),
        "ratio": (low_shape / high_shape).tolist(),
        "ratio_min": float((low_shape / high_shape).min()),
        "ratio_max": float((low_shape / high_shape).max()),
        "power_ratio": float(low_shape.mean() / high_shape.mean()),
    })
    dump("load_calendar", {
        "dates": [d.isoformat() for d in dates],
        "daily_kwh": daily_kwh.tolist(),
        "iso_weekday": [d.weekday() for d in dates],
        "iso_week": [int(d.isocalendar()[1]) for d in dates],
        "month": [d.month for d in dates],
        "monthly_mean": [float(daily_kwh[[i for i, d in enumerate(dates)
                                          if d.month == m]].mean()) for m in range(1, 13)],
    })

    # ---------- 光伏预报精度：提前期衰减 + 同目标小时 ----------
    # 对齐口径：目标小时 h 的实际功率 = 附件2 中以 h 整点为末刻的那一段（列 h*6-1）；
    # 提前期 j+1 的目标可跨到次日，按次日实际对齐（已复现 DATA_FACTS.by_lead_hour 全 24 点）。
    print("[5/9] 光伏预报精度（提前期 / 同目标小时）...")
    pv_act = att.pv_actual
    act_hour = pv_act[:, np.array([h * 6 - 1 for h in range(1, 25)])]
    lead_abs, lead_n = np.zeros(24), np.zeros(24)
    for di, d in enumerate(dates):
        for ih in FORECAST_HOURS:
            f = att.forecast.get((d, ih))
            if f is None:
                continue
            for j in range(24):                       # 提前期 j+1 小时
                tgt_abs = ih + j + 1
                tgt_day = di + (tgt_abs - 1) // 24
                if tgt_day >= len(dates):
                    continue
                lead_abs[j] += abs(f[j] - act_hour[tgt_day, (tgt_abs - 1) % 24])
                lead_n[j] += 1
    dump("forecast_decay", {
        "lead_h": list(range(1, 25)),
        "mae_kw": [float(lead_abs[j] / lead_n[j]) for j in range(24)],
        "n_samples": lead_n.astype(int).tolist(),
    })
    same_h = list(range(13, 18))
    m0 = [float(np.mean([abs(att.forecast[(d, 0)][h - 1] - act_hour[i, h - 1])
                         for i, d in enumerate(dates)])) for h in same_h]
    m12 = [float(np.mean([abs(att.forecast[(d, 12)][h - 13] - act_hour[i, h - 1])
                          for i, d in enumerate(dates)])) for h in same_h]
    dump("forecast_same_target", {
        "target_hours": same_h,
        "mae_issue0": m0, "mae_issue12": m12,
        "reduction_pct": [float((a - b) / a * 100) for a, b in zip(m0, m12)],
    })

    # ---------- 预测器 MAE 对照（留出期 2 月起）----------
    print("[6/9] 负载预测器留出期 MAE ...")
    d0 = att.date_index[DELIVERY_START]
    regimes = fc.regimes

    def mae_pred(picker) -> float:
        errs = []
        for d in range(d0, len(dates)):
            picks = picker(d)
            hat = att.load_actual[np.array(picks)].mean(axis=0)
            errs.append(np.abs(hat - att.load_actual[d]).mean())
        return float(np.mean(errs))

    same_last = lambda w: (lambda d: [j for j in range(d) if regimes[j] == regimes[d]][-w:])
    dump("predictor_mae", {"rows": [
        {"label": "同 regime\n最近 4 天", "mae": mae_pred(same_last(4)), "group": "same"},
        {"label": "同 regime\n最近 8 天", "mae": mae_pred(same_last(8)), "group": "same"},
        {"label": "同 regime\n上一天", "mae": mae_pred(same_last(1)), "group": "same"},
        {"label": "跨 regime\n最近 7 天", "mae": mae_pred(lambda d: list(range(max(0, d - 7), d))),
         "group": "cross"},
        {"label": "跨 regime\n全历史", "mae": mae_pred(lambda d: list(range(d))), "group": "cross"},
    ], "w_used": W_LOAD})

    # ---------- 插值核查（整点 → 144 段）----------
    print("[7/9] 插值核查 + 滚动时域 ...")
    probe = att.date_index[dt.date(2025, 6, 21)]
    pd_ = dates[probe]
    panels = []
    for ih in FORECAST_HOURS:
        hourly = att.forecast.get((pd_, ih))
        panels.append({
            "issue_hour": ih,
            "hourly_x": (ih + np.arange(1, 25)).tolist(),
            "hourly_kw": (hourly.tolist() if hourly is not None else []),
            "interp_kw": (fc.interp_pv_kwh(probe, ih) / DT_H).tolist(),
        })
    dump("q3_interp_check", {
        "date": pd_.isoformat(),
        "slot_h": slot_h.tolist(),
        "panels": panels,
        "actual_kw": pv_act[probe].tolist(),
        "night_mask": fc.night_mask.astype(int).tolist(),
        "n_night": int(fc.night_mask.sum()),
    })
    # 滚动时域：从交付产物中选择调整绝对量最大的真实日期，避免人为挑选空轨迹。
    plan_df = pd.read_excel(ROOT / "user_data" / "result3.xlsx", sheet_name="计划购电量")
    adj_df = pd.read_excel(ROOT / "user_data" / "result3.xlsx", sheet_name="调整购电量")
    plan_dates = [pd.to_datetime(v).date() for v in plan_df.iloc[:, 0]]
    b_all = plan_df.iloc[:, 1:T + 1].to_numpy(dtype=float)
    a_all = adj_df.iloc[:, 1:T + 1].to_numpy(dtype=float)
    row = int(np.argmax(np.abs(a_all - b_all).sum(axis=1)))
    b_row = b_all[row]
    a_row = a_all[row]
    roll_date = plan_dates[row]
    dump("q3_rolling_timeline", {
        "date": roll_date.isoformat(),
        "slot_h": slot_h.tolist(),
        "issue_hours": list(FORECAST_HOURS),
        "tau": [6 * h for h in FORECAST_HOURS],
        "plan_b_kwh": b_row.tolist(),
        "adjust_a_kwh": a_row.tolist(),
        "d_plus": np.maximum(a_row - b_row, 0).tolist(),
        "d_minus": np.maximum(b_row - a_row, 0).tolist(),
        "price": att.price1.tolist(),
        "T": T, "dt_h": DT_H,
    })

    # ---------- 波动电价：山脊 + Hovmöller ----------
    print("[8/9] 波动电价断面 ...")
    pv_price = att.price_volatile
    dump("q4_price", {
        "slot_h": slot_h.tolist(),
        "monthly_mean_curve": [pv_price[[i for i, d in enumerate(dates)
                                         if d.month == m]].mean(axis=0).tolist()
                               for m in range(1, 13)],
        "month_labels": [f"{m}月" for m in range(1, 13)],
        "fixed_price": att.price1.tolist(),
        "hov": pv_price.tolist(),
        "dates": [d.isoformat() for d in dates],
        "vmin": float(pv_price.min()), "vmax": float(pv_price.max()),
        "mean": float(pv_price.mean()),
        "daily_spread": (pv_price.max(axis=1) - pv_price.min(axis=1)).tolist(),
        "fixed_spread": float(att.price1.max() - att.price1.min()),
    })

    # ---------- 交付产物中的逐日紧急购电量 ----------
    print("[9/9] 交付产物紧急购电量 ...")
    em2 = emergency_by_day("result2.xlsx")
    em3 = emergency_by_day("result3.xlsx")
    delivery = [d for d in dates if d >= DELIVERY_START]
    dump("q2_emergency_calendar", {
        "dates": [d.isoformat() for d in delivery],
        "iso_weekday": [d.weekday() for d in delivery],
        "iso_week": [int(d.isocalendar()[1]) for d in delivery],
        "emergency_q2": [em2.get(d.isoformat(), 0.0) for d in delivery],
        "emergency_q3": [em3.get(d.isoformat(), 0.0) for d in delivery],
        "total_q2": float(sum(em2.values())), "total_q3": float(sum(em3.values())),
    })

    # ---------- 上游标量派生的三张图 ----------
    r1, r2, r3, r4 = (read_json("problem_1_results.json"), read_json("problem_2_results.json"),
                      read_json("problem_3_results.json"), read_json("problem_4_results.json"))
    dump("q1_savings_waterfall", {
        "baseline": r1["no_storage_baseline"],
        "optimal": r1["Q1_objective"],
        "ideal": r1["ideal_objective"],
        "savings": r1["savings_yuan"],
        "savings_pct": r1["savings_pct"],
        "loss_vs_ideal": r1["Q1_objective"] - r1["ideal_objective"],
    })
    sweep = r2["margin_sweep"]
    dump("q2_margin_ucurve", {
        "m": [float(k) for k in sweep],
        "total_cost": [sweep[k]["total_cost"] for k in sweep],
        "emergency_kwh": [sweep[k]["emergency_kwh"] for k in sweep],
        "best_m": r2["best_scalar_margin"],
        "best_cost": r2["best_margin_total_cost"],
    })
    dump("q3_cost_decomp", {
        "strategies": ["S0（仅 0:00 锁定）", "S1（滚动调整）"],
        "components": ["计划购电费", "上调费用", "下调违约费", "紧急购电费"],
        "values": [[r3["S0_plan_cost"], 0.0, 0.0, r3["S0_emergency_cost"]],
                   [r3["S1_plan_cost"], r3["S1_up_cost"], r3["S1_down_cost"],
                    r3["S1_emergency_cost"]]],
        "totals": [r3["S0_total"], r3["S1_total"]],
        "rolling_value": r3["rolling_value_yuan"],
        "total_R_a": r3["S1_total_R_a"],
    })
    cmp_ = r4["comparison_fixed_vs_volatile"]
    dump("q4_fixed_vs_vol", {
        "groups": [
            {"label": "两阶段总费用\n（问题2 → 4-2）", "unit": "万元",
             "fixed": cmp_["Q2_vs_Q4_2_two_stage"]["total_cost"]["fixed"] / 1e4,
             "volatile": cmp_["Q2_vs_Q4_2_two_stage"]["total_cost"]["volatile"] / 1e4},
            {"label": "滚动总费用\n（问题3 → 4-3）", "unit": "万元",
             "fixed": cmp_["Q3_vs_Q4_3_rolling_S1"]["total_cost"]["fixed"] / 1e4,
             "volatile": cmp_["Q3_vs_Q4_3_rolling_S1"]["total_cost"]["volatile"] / 1e4},
            {"label": "两阶段循环量\n（问题2 → 4-2）", "unit": "GWh",
             "fixed": cmp_["Q2_vs_Q4_2_two_stage"]["cycling_kwh"]["fixed"] / 1e6,
             "volatile": cmp_["Q2_vs_Q4_2_two_stage"]["cycling_kwh"]["volatile"] / 1e6},
            {"label": "滚动循环量\n（问题3 → 4-3）", "unit": "GWh",
             "fixed": cmp_["Q3_vs_Q4_3_rolling_S1"]["cycling_kwh"]["fixed"] / 1e6,
             "volatile": cmp_["Q3_vs_Q4_3_rolling_S1"]["cycling_kwh"]["volatile"] / 1e6},
            {"label": "滚动紧急购电量\n（问题3 → 4-3）", "unit": "万kWh",
             "fixed": cmp_["Q3_vs_Q4_3_rolling_S1"]["emergency_kwh"]["fixed"] / 1e4,
             "volatile": cmp_["Q3_vs_Q4_3_rolling_S1"]["emergency_kwh"]["volatile"] / 1e4},
            {"label": "日内价差\n（附件1 → 附件4）", "unit": "元/kWh",
             "fixed": cmp_["intraday_price_spread_yuan"]["fixed"],
             "volatile": cmp_["intraday_price_spread_yuan"]["volatile"]},
        ],
        "low_price_plan_share": cmp_["low_price_plan_share_volatile"],
        "value_of_price_info": r4["value_of_price_info_yuan"],
        "value_of_price_info_pct": r4["value_of_price_info_pct"],
    })
    print("完成：所有载荷已写入 figures/data_*.json")


if __name__ == "__main__":
    main()
