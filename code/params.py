# -*- coding: utf-8 -*-
"""参数集中定义（编码第一步，MC10）。

所有题面原始参数从 PROBLEM_FACTS.json 现场读入（§6.2 要求），派生量在此现场计算，
禁止在任何其它模块出现裸数字字面量。导出单一 PARAMS 字典与同名模块级常量。
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_FACTS_PATH = _ROOT / "PROBLEM_FACTS.json"


def _load_facts() -> dict:
    with _FACTS_PATH.open(encoding="utf-8-sig") as handle:
        return json.load(handle)


_FACTS = _load_facts()


def _by_id(section: str) -> dict:
    return {item["id"]: item["value"] for item in _FACTS[section]}


_STORAGE = _by_id("storage")
_MULT = _by_id("price_multipliers")
_TEMPORAL = _by_id("temporal")

# ---- 题面原始参数（逐字取自 PROBLEM_FACTS.json，不硬编码数值）----
E_CAP = _STORAGE["E_cap_max"]          # 额定容量 kWh
P_MAX = _STORAGE["P_ch_dis_max"]       # 最大充放电功率 kW
E_INIT = _STORAGE["E_init"]            # 2025-01-01 0:00 初始储电量 kWh
E_MIN = _STORAGE["E_min"]              # 储电量下限 kWh
E_MAX = _STORAGE["E_max"]              # 储电量上限 kWh
ETA_PCT = _STORAGE["eta_pct"]          # 充放电效率（百分数）

K_EMERGENCY = _MULT["k_emergency"]     # 紧急购电倍数 κ
K_SHORTFALL_PCT = _MULT["k_shortfall_pct"]   # 计划高于调整的违约电价（百分比）
K_EXCESS = _MULT["k_excess"]           # 调整高于计划的超出部分倍数

DT_MIN = _TEMPORAL["dt_minutes"]       # 决策时段长度（分钟）
DATA_YEAR = _TEMPORAL["data_year"]
FORECAST_HOURS = [
    _TEMPORAL["forecast_hour_0"],
    _TEMPORAL["forecast_hour_1"],
    _TEMPORAL["forecast_hour_2"],
    _TEMPORAL["forecast_hour_3"],
]
FORECAST_HORIZON_H = _TEMPORAL["forecast_horizon_h"]
SOC_BUCKET_H = _TEMPORAL["soc_report_bucket_h"]

# ---- 派生量（现场计算，禁止字面量）----
DT_H = DT_MIN / 60                              # 时段长（小时）= 1/6
T = int(24 * 60 // DT_MIN)                       # 每日时段数 = 144
E_STEP_MAX = P_MAX * DT_H                        # 单时段充放电量上限 = 5000*(10/60)
ETA = ETA_PCT / 100                              # 效率小数形式 = 0.9
ETA_C = ETA                                      # 主口径：单向各 0.9
ETA_D = ETA
E_TERMINAL = E_INIT                              # 2025-12-31 24:00 末期目标，防止期末放空
LAM_UP = K_EXCESS                               # 上调倍数 1.5
LAM_DN = K_SHORTFALL_PCT / 100                  # 下调倍数 0.5
CRITICAL_FRACTILE = (K_EMERGENCY - 1) / K_EMERGENCY  # 报童临界分位数 0.8

# 交付区间：2025-02-01 .. 2025-12-31（334 天）；1 月只作历史预热窗
_FEB, _DAY1, _DEC, _DAY31 = 2, 1, 12, 31
DELIVERY_START = date(DATA_YEAR, _FEB, _DAY1)
DELIVERY_END = date(DATA_YEAR, _DEC, _DAY31)
N_DAYS_DELIVERY = (DELIVERY_END - DELIVERY_START).days + 1
N_DAYS_YEAR = (date(DATA_YEAR, _DEC, _DAY31) - date(DATA_YEAR, _DAY1, _DAY1)).days + 1

# 效率口径（GL-C3 四读法 + 理想）：(eta_c, eta_d)
ETA_CONVENTIONS = {
    "main": (ETA, ETA),
    "roundtrip": (ETA ** 0.5, ETA ** 0.5),
    "charge_only": (ETA, 1.0),
    "discharge_only": (1.0, ETA),
    "ideal": (1.0, 1.0),
}

# 报告 §5.5⓪ 参数口径元组（C18 逐字核对）
PARAM_TUPLE_C18 = (E_MIN, E_MAX, P_MAX, E_INIT, ETA_C, ETA_D,
                   K_EMERGENCY, LAM_UP, LAM_DN)

_REPORT = _FACTS["report_spec"]
TABLE1_INTERVALS = _REPORT["table1_intervals"]
TABLE2_BUCKETS = _REPORT["table2_buckets"]
TABLE3_DATES = _REPORT["table3_dates"]

PARAMS = dict(
    E_CAP=E_CAP, P_MAX=P_MAX, E_INIT=E_INIT, E_MIN=E_MIN, E_MAX=E_MAX,
    E_TERMINAL=E_TERMINAL,
    ETA_PCT=ETA_PCT, ETA=ETA, ETA_C=ETA_C, ETA_D=ETA_D,
    K_EMERGENCY=K_EMERGENCY, LAM_UP=LAM_UP, LAM_DN=LAM_DN,
    DT_MIN=DT_MIN, DT_H=DT_H, T=T, E_STEP_MAX=E_STEP_MAX,
    FORECAST_HOURS=FORECAST_HOURS, FORECAST_HORIZON_H=FORECAST_HORIZON_H,
    SOC_BUCKET_H=SOC_BUCKET_H, CRITICAL_FRACTILE=CRITICAL_FRACTILE,
    DATA_YEAR=DATA_YEAR, N_DAYS_DELIVERY=N_DAYS_DELIVERY, N_DAYS_YEAR=N_DAYS_YEAR,
    DELIVERY_START=DELIVERY_START.isoformat(), DELIVERY_END=DELIVERY_END.isoformat(),
)


def _self_check() -> None:
    """口径一致性断言（C18 与派生量），import 即校验，出错立即中止。"""
    assert PARAM_TUPLE_C18 == (1200, 10800, 5000, 6000, 0.9, 0.9, 5, 1.5, 0.5), \
        f"C18 参数口径不符: {PARAM_TUPLE_C18}"
    assert T == 144, f"每日时段数应为 144，得 {T}"
    assert abs(E_STEP_MAX - P_MAX * DT_H) < 1e-9
    assert abs(CRITICAL_FRACTILE - 0.8) < 1e-12
    assert N_DAYS_DELIVERY == 334, f"交付天数应为 334，得 {N_DAYS_DELIVERY}"
    assert N_DAYS_YEAR == 365, f"数据年天数应为 365，得 {N_DAYS_YEAR}"


_self_check()


if __name__ == "__main__":
    for key, value in PARAMS.items():
        print(f"{key} = {value}")
