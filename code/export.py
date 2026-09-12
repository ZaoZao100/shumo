# -*- coding: utf-8 -*-
"""结果导出层（§6.2 item 8）。

按模板列序 1:1 填充（模板标签有排印错位，按位置写不按标签重排）；紧急购电表做连续区间合并。
模板列头从 user_data/result*.xlsx 现读现用，保证 sheet 名/列序/行数与模板一致。
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from params import T, DT_MIN, E_INIT, SOC_BUCKET_H

_ROOT = Path(__file__).resolve().parent.parent
_TEMPLATE = _ROOT / "user_data"
_SLOTS_PER_BUCKET = SOC_BUCKET_H * 60 // DT_MIN     # 24 段/4小时桶
_N_BUCKET = T // _SLOTS_PER_BUCKET                   # 6 桶


def _template_cols(fname: str, sheet: str) -> list:
    df = pd.read_excel(_TEMPLATE / fname, sheet_name=sheet, nrows=0)
    return list(df.columns)


def _slot_label(minute_start: int, minute_end: int) -> str:
    def hm(m):
        h, mm = divmod(m, 60)
        if h >= 24:
            return f"{h - 24}:{mm:02d}+1"
        return f"{h}:{mm:02d}"
    return f"{hm(minute_start)}-{hm(minute_end)}"


# ---------------- 宽表：计划/调整购电量（334×147）----------------
def build_wide_plan(fname: str, sheet: str, dates: list,
                    plan: np.ndarray, daily_cost: np.ndarray) -> pd.DataFrame:
    cols = _template_cols(fname, sheet)
    n = len(dates)
    assert plan.shape == (n, T)
    data = {}
    data[cols[0]] = [d.isoformat() for d in dates]
    for j in range(T):
        data[cols[1 + j]] = plan[:, j]
    data[cols[T + 1]] = plan.sum(axis=1)         # 全天购电量
    data[cols[T + 2]] = daily_cost               # 全天购电费
    return pd.DataFrame(data, columns=cols)


# ---------------- 充放电量表（6 桶/日）----------------
def build_soc_table(fname: str, sheet: str, dates: list,
                    charge: np.ndarray, discharge: np.ndarray,
                    E0: np.ndarray, ET: np.ndarray, single_day: bool = False) -> pd.DataFrame:
    cols = _template_cols(fname, sheet)
    bucket_labels = [_slot_label(b * SOC_BUCKET_H * 60, (b + 1) * SOC_BUCKET_H * 60)
                     for b in range(_N_BUCKET)]
    rows = []
    for di, d in enumerate(dates):
        c_day = charge[di].reshape(_N_BUCKET, _SLOTS_PER_BUCKET).sum(axis=1)
        s_day = discharge[di].reshape(_N_BUCKET, _SLOTS_PER_BUCKET).sum(axis=1)
        for b in range(_N_BUCKET):
            row = {c: None for c in cols}
            if not single_day:
                row[cols[0]] = d.isoformat() if b == 0 else None
                base = 1
            else:
                base = 0
            row[cols[base + 0]] = bucket_labels[b]      # 时间段
            row[cols[base + 1]] = float(c_day[b])       # 充电量
            row[cols[base + 2]] = float(s_day[b])       # 放电量
            # 时刻/储电量：仅前两行填 0:00 / 24:00 端点 SOC
            if b == 0:
                row[cols[base + 3]] = "0:00"
                row[cols[base + 4]] = float(E0[di])
            elif b == 1:
                row[cols[base + 3]] = "24:00"
                row[cols[base + 4]] = float(ET[di])
            rows.append(row)
    return pd.DataFrame(rows, columns=cols)


# ---------------- 紧急购电量表（连续区间合并）----------------
def build_emergency_table(fname: str, sheet: str, dates: list,
                          emergency: np.ndarray, thresh: float = 1e-6) -> pd.DataFrame:
    cols = _template_cols(fname, sheet)
    rows = []
    for di, d in enumerate(dates):
        u = emergency[di]
        runs = _merge_runs(u, thresh)
        first = True
        for (a, bnd, tot) in runs:
            row = {c: None for c in cols}
            row[cols[0]] = d.isoformat() if first else None
            label = _slot_label(a * DT_MIN, (bnd + 1) * DT_MIN)
            row[cols[1]] = label
            row[cols[2]] = float(tot)
            rows.append(row)
            first = False
    if not rows:                                   # 全年无紧急购电：写一行占位说明
        row = {c: None for c in cols}
        row[cols[1]] = "无"
        rows.append(row)
    return pd.DataFrame(rows, columns=cols)


def build_interval_audit(dates: list, load_kwh: np.ndarray, pv_kwh: np.ndarray,
                         plan_kwh: np.ndarray, charge: np.ndarray, discharge: np.ndarray,
                         emergency: np.ndarray, curtailment: np.ndarray,
                         soc: np.ndarray, original_plan_kwh: np.ndarray = None) -> pd.DataFrame:
    """生成逐10分钟可复算审计表；功率列由电量/Δt反算，不改变交付模板主表。"""
    n = len(dates)
    assert all(a.shape == (n, T) for a in
               (load_kwh, pv_kwh, plan_kwh, charge, discharge, emergency, curtailment))
    assert soc.shape == (n, T + 1)
    data = {
        "日期": np.repeat([d.isoformat() for d in dates], T),
        "时段序号": np.tile(np.arange(T), n),
        "时段": np.tile([_slot_label(t * DT_MIN, (t + 1) * DT_MIN) for t in range(T)], n),
        "实际负载L_kWh": load_kwh.reshape(-1),
        "实际光伏G_kWh": pv_kwh.reshape(-1),
        "执行购电_kWh": plan_kwh.reshape(-1),
        "充电_kWh": charge.reshape(-1),
        "放电_kWh": discharge.reshape(-1),
        "紧急购电_kWh": emergency.reshape(-1),
        "弃光q_kWh": curtailment.reshape(-1),
        "SOC期初_kWh": soc[:, :-1].reshape(-1),
        "SOC期末_kWh": soc[:, 1:].reshape(-1),
        "充电功率_kW": (charge / (DT_MIN / 60)).reshape(-1),
        "放电功率_kW": (discharge / (DT_MIN / 60)).reshape(-1),
    }
    if original_plan_kwh is not None:
        assert original_plan_kwh.shape == (n, T)
        data["0点原计划_kWh"] = original_plan_kwh.reshape(-1)
    return pd.DataFrame(data)


def _merge_runs(u: np.ndarray, thresh: float):
    """把连续缺电的 10 分钟段合并为区间，返回 [(start_idx, end_idx, sum)]。"""
    runs = []
    i = 0
    n = len(u)
    while i < n:
        if u[i] > thresh:
            j = i
            tot = 0.0
            while j < n and u[j] > thresh:
                tot += u[j]
                j += 1
            runs.append((i, j - 1, tot))
            i = j
        else:
            i += 1
    return runs


# ---------------- 顶层写出 ----------------
def write_result1(path: Path, x: np.ndarray, charge: np.ndarray, discharge: np.ndarray,
                  curtailment: np.ndarray, E: np.ndarray,
                  load_kwh: np.ndarray, pv_kwh: np.ndarray) -> None:
    """result1.xlsx：计划购电量(144) + 充放电量(6 桶)。"""
    cols_plan = _template_cols("result1.xlsx", "计划购电量")
    df_plan = pd.DataFrame({cols_plan[0]: _template_cols_values("result1.xlsx", "计划购电量"),
                            cols_plan[1]: x})
    dates = [None]
    df_soc = build_soc_table("result1.xlsx", "充放电量", [_Dummy()],
                             charge[None, :], discharge[None, :],
                             np.array([E[0]]), np.array([E[-1]]), single_day=True)
    audit = build_interval_audit([_Dummy()], load_kwh[None, :], pv_kwh[None, :],
                                 x[None, :], charge[None, :], discharge[None, :],
                                 np.zeros((1, T)), curtailment[None, :], E[None, :])
    with pd.ExcelWriter(path, engine="openpyxl") as w:
        df_plan.to_excel(w, sheet_name="计划购电量", index=False)
        df_soc.to_excel(w, sheet_name="充放电量", index=False)
        audit.to_excel(w, sheet_name="逐时段审计", index=False)


class _Dummy:
    def isoformat(self):
        return ""


def _template_cols_values(fname: str, sheet: str) -> list:
    """读取模板首列（时间段标签）原样返回。"""
    df = pd.read_excel(_TEMPLATE / fname, sheet_name=sheet)
    return list(df.iloc[:, 0])
