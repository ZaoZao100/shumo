# -*- coding: utf-8 -*-
"""附件摄入层（§6.2 item 2）。

读入五个数据文件（附件1-4），执行 C17 的行数与唯一值断言；附件2 读两个 sheet；
附件3 的日期列 ffill 后断言 365 个唯一值。每个 read_excel 均显式带 sheet_name=。
所有功率/电价矩阵按 10 分钟时段 0..143 的列序 1:1 对齐（列标签为时段末刻）。
"""
from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from params import T, N_DAYS_YEAR, FORECAST_HORIZON_H, FORECAST_HOURS

_ROOT = Path(__file__).resolve().parent.parent
_DATA = _ROOT / "user_data"


def _to_hour(value) -> int:
    """把附件3 的『预报时刻』规整为整点小时 0/6/12/18。"""
    if isinstance(value, (int, np.integer)):
        return int(value)
    if isinstance(value, float):
        return int(round(value))
    if isinstance(value, _dt.time):
        return value.hour
    if isinstance(value, (_dt.datetime, pd.Timestamp)):
        return value.hour
    text = str(value).strip()
    for sep in (":", "："):
        if sep in text:
            return int(text.split(sep)[0])
    return int(float(text))


def _to_date(value) -> _dt.date:
    ts = pd.to_datetime(value)
    return ts.date()


@dataclass
class Attachments:
    price1: np.ndarray          # 附件1 电价 (144,) 元/kWh
    load1: np.ndarray           # 附件1 小区负载 (144,) kW
    pv1: np.ndarray             # 附件1 光伏预测功率 (144,) kW
    dates: list                 # 365 个 date（按附件2 行序）
    date_index: dict            # date -> 行号 0..364
    load_actual: np.ndarray     # 附件2 小区负载 (365,144) kW
    pv_actual: np.ndarray       # 附件2 光伏实际功率 (365,144) kW
    price_volatile: np.ndarray  # 附件4 波动电价 (365,144) 元/kWh
    forecast: dict              # {(date, hour): np.ndarray(24,)} 整点光伏预报 kW


def _read_matrix(path: Path, sheet: str) -> tuple[list, np.ndarray]:
    """读『日期\\时间』宽表：返回 (date 列表, (n,144) 矩阵)。"""
    df = pd.read_excel(path, sheet_name=sheet)
    dates = [_to_date(v) for v in df.iloc[:, 0]]
    matrix = df.iloc[:, 1:T + 1].to_numpy(dtype=float)
    return dates, matrix


def load_all() -> Attachments:
    # ---- 附件1：平均日断面（144 行）----
    att1 = pd.read_excel(_DATA / "附件1.xlsx", sheet_name="Sheet1")
    assert att1.shape[0] == T, f"附件1 应 {T} 行，得 {att1.shape[0]}"
    price1 = att1["电价"].to_numpy(dtype=float)
    load1 = att1["小区负载"].to_numpy(dtype=float)
    pv1 = att1["光伏发电预测功率"].to_numpy(dtype=float)

    # ---- 附件2：两个 sheet（小区负载 + 光伏发电实际功率）----
    load_dates, load_actual = _read_matrix(_DATA / "附件2.xlsx", "小区负载")
    pv_dates, pv_actual = _read_matrix(_DATA / "附件2.xlsx", "光伏发电实际功率")
    assert load_actual.shape[0] == N_DAYS_YEAR, f"附件2 负载应 {N_DAYS_YEAR} 行"
    assert pv_actual.shape[0] == N_DAYS_YEAR, f"附件2 光伏应 {N_DAYS_YEAR} 行"
    assert load_dates == pv_dates, "附件2 两 sheet 日期列不一致"
    assert load_actual.shape[1] == T and pv_actual.shape[1] == T

    # ---- 附件4：波动电价（365 行）----
    vol_dates, price_volatile = _read_matrix(_DATA / "附件4.xlsx", "Sheet1")
    assert price_volatile.shape[0] == N_DAYS_YEAR, f"附件4 应 {N_DAYS_YEAR} 行"
    assert vol_dates == load_dates, "附件4 日期列与附件2 不一致"

    # ---- 附件3：整点光伏预报（1460 行 = 365×4），日期列 ffill ----
    att3 = pd.read_excel(_DATA / "附件3.xlsx", sheet_name="Sheet1")
    att3["日期"] = att3["日期"].ffill()
    assert att3.shape[0] == N_DAYS_YEAR * len(FORECAST_HOURS), \
        f"附件3 应 {N_DAYS_YEAR * len(FORECAST_HOURS)} 行，得 {att3.shape[0]}"
    assert att3["日期"].nunique() == N_DAYS_YEAR, \
        f"附件3 日期唯一值应 {N_DAYS_YEAR}，得 {att3['日期'].nunique()}"
    fc_cols = [c for c in att3.columns if str(c).startswith("预报") and "小时" in str(c)]
    assert len(fc_cols) == FORECAST_HORIZON_H, f"附件3 预报小时列应 {FORECAST_HORIZON_H}"
    forecast: dict = {}
    for _, row in att3.iterrows():
        key = (_to_date(row["日期"]), _to_hour(row["预报时刻"]))
        forecast[key] = row[fc_cols].to_numpy(dtype=float)

    dates = load_dates
    date_index = {d: i for i, d in enumerate(dates)}
    assert len(date_index) == N_DAYS_YEAR, "附件2 日期存在重复"
    assert dates == sorted(dates), "附件2 日期非升序"

    return Attachments(
        price1=price1, load1=load1, pv1=pv1,
        dates=dates, date_index=date_index,
        load_actual=load_actual, pv_actual=pv_actual,
        price_volatile=price_volatile, forecast=forecast,
    )


if __name__ == "__main__":
    att = load_all()
    print("附件1 price/load/pv shape:", att.price1.shape, att.load1.shape, att.pv1.shape)
    print("附件1 电价范围: %.4f .. %.4f 均值 %.6f" %
          (att.price1.min(), att.price1.max(), att.price1.mean()))
    print("附件2 load_actual:", att.load_actual.shape, "pv_actual:", att.pv_actual.shape)
    print("附件4 price_volatile:", att.price_volatile.shape,
          "范围 %.4f .. %.4f 均值 %.6f" %
          (att.price_volatile.min(), att.price_volatile.max(), att.price_volatile.mean()))
    print("附件3 forecast 条目:", len(att.forecast),
          "（应 = 365×4 =", N_DAYS_YEAR * len(FORECAST_HOURS), "）")
    print("日期范围:", att.dates[0], "..", att.dates[-1], "共", len(att.dates))
    # C17 汇总
    print("C17 OK: att1=%d att2_load=%d att2_pv=%d att3_rows=%d att3_uniq=%d att4=%d" %
          (att.price1.shape[0], att.load_actual.shape[0], att.pv_actual.shape[0],
           N_DAYS_YEAR * len(FORECAST_HOURS), N_DAYS_YEAR, att.price_volatile.shape[0]))
