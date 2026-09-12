# -*- coding: utf-8 -*-
"""预测层（§6.2 item 3；MC4 regime、MC7 插值）。

- regime：周五/周六 = 低负载日（weekday() in (4,5)），其余高负载日。
- 负载预测：同 regime 最近 W=4 天历史均值，信息集严格 j < cutoff_day。
- 光伏插值：只用相应发布时间的附件3整点预报插值到144段并截为非负。
- 残差场景：同 regime 最近 K=8 天的整条残差向量（保留日内相关性）。
所有日前历史索引满足 j<d；第1天无历史时使用附件1给出的典型负载先验，不回填当天实际值。
"""
from __future__ import annotations

import numpy as np

from params import T, DT_H, FORECAST_HOURS

W_LOAD = 4          # 负载预测窗口（同 regime 最近天数）
K_SCEN = 8          # 场景数（同 regime 最近天数）
LOW_WEEKDAYS = (4, 5)   # 周五/周六


def regime_of(d) -> str:
    """日类型：低（周五/周六）或高。"""
    return "low" if d.weekday() in LOW_WEEKDAYS else "high"


class Forecaster:
    """预计算全 365 天的负载/光伏点预测与残差，供各问共享（regime 一致，L4）。"""

    def __init__(self, att):
        self.att = att
        self.T = T
        self.dt_h = DT_H
        self.dates = att.dates
        self.n = len(self.dates)
        self.regimes = np.array([regime_of(d) for d in self.dates])
        # 不使用全年实际光伏构造夜间掩码，避免把未来实测信息带入预测。
        self.night_mask = np.zeros(T, dtype=bool)
        self.load_history_max_idx = np.full(self.n, -1, dtype=int)
        self._precompute()

    # -------- 光伏整点预报插值（MC7）--------
    def interp_pv_kwh(self, date_idx: int, issue_hour: int) -> np.ndarray:
        """附件3 (日期, 预报时刻=issue_hour) 的 24 整点值插值到 144 段电量(kWh)。"""
        d = self.dates[date_idx]
        hourly = self.att.forecast.get((d, issue_hour))
        if hourly is None:
            hourly = np.zeros(24)
        xp = issue_hour + np.arange(1, 25)          # 预报覆盖的绝对小时（整点）
        slot_times = (np.arange(self.T) + 1) * self.dt_h  # 各段末刻绝对小时 t·Δt (t=1..144)
        g_kw = np.interp(slot_times, xp, hourly)     # 线性插值，边界外钳制
        g_kw = np.maximum(g_kw, 0.0)                 # 非负
        return g_kw * self.dt_h                      # 转电量 kWh

    def _precompute(self) -> None:
        T_ = self.T
        n = self.n
        dt = self.dt_h
        load_act = self.att.load_actual
        pv_act = self.att.pv_actual
        # 光伏点预测（0:00 发布）逐日
        self.pv_hat_kwh = np.zeros((n, T_))
        for d in range(n):
            self.pv_hat_kwh[d] = self.interp_pv_kwh(d, FORECAST_HOURS[0])
        # 负载点预测（同 regime 最近 W 天均值，j < d）
        self.load_hat_kwh = np.zeros((n, T_))
        for d in range(n):
            self.load_hat_kwh[d] = self._load_forecast_kwh(d)
        # 残差（实际 - 点预测，均为 kWh）
        self.res_load_kwh = load_act * dt - self.load_hat_kwh
        self.res_pv_kwh = pv_act * dt - self.pv_hat_kwh
        # 点预测净需求（用于因果参考与标量裕度基线）
        self.net_hat_kwh = self.load_hat_kwh - self.pv_hat_kwh

    def _load_forecast_kwh(self, d: int) -> np.ndarray:
        """同 regime 最近 W 天负载均值(kWh)；不足则用可得的最近历史（保底不泄漏）。"""
        r = self.regimes[d]
        same = [j for j in range(d) if self.regimes[j] == r]
        if len(same) >= 1:
            picks = same[-W_LOAD:]
        else:
            picks = list(range(max(0, d - W_LOAD), d))   # 保底：最近若干天（任一 regime）
        if not picks:
            self.load_history_max_idx[d] = -1
            return self.att.load1 * self.dt_h            # d=0 无历史：使用已给典型日先验
        self.load_history_max_idx[d] = max(picks)
        return self.att.load_actual[np.array(picks)].mean(axis=0) * self.dt_h

    # -------- 残差场景集（MC3）--------
    def scenarios(self, date_idx: int, K: int = K_SCEN) -> np.ndarray:
        """构造 date_idx 日的 K 个净需求场景 (K,144)，取同 regime 最近 K 天残差。"""
        d = date_idx
        r = self.regimes[d]
        same = [j for j in range(d) if self.regimes[j] == r]
        picks = same[-K:] if len(same) >= K else same[:]
        if not picks:                                    # 无同 regime 历史（极早期）
            return self.net_hat_kwh[d][None, :].copy()
        base = self.net_hat_kwh[d]
        scen = np.empty((len(picks), self.T))
        for i, j in enumerate(picks):
            scen[i] = base + self.res_load_kwh[j] - self.res_pv_kwh[j]
        return scen

    def net_actual_kwh(self, date_idx: int) -> np.ndarray:
        """当日实际净需求 (144,) kWh = (实际负载 - 实际光伏)·Δt。"""
        return (self.att.load_actual[date_idx] - self.att.pv_actual[date_idx]) * self.dt_h

    def information_boundary_audit(self, indices: list[int]) -> dict:
        """核对日前负载与场景历史索引均早于目标日；紧急购电量不作为泄漏判据。"""
        load_ok = all(self.load_history_max_idx[i] < i for i in indices)
        scenario_max = []
        scenario_ok = True
        for i in indices:
            same = [j for j in range(i) if self.regimes[j] == self.regimes[i]]
            picks = same[-K_SCEN:] if len(same) >= K_SCEN else same
            mx = max(picks) if picks else -1
            scenario_max.append(mx)
            scenario_ok &= mx < i
        return {
            "load_history_j_lt_d": bool(load_ok),
            "scenario_history_j_lt_d": bool(scenario_ok),
            "pv_source": "附件3中与决策时刻相同的已发布预报行",
            "day0_prior": "附件1典型负载；未使用2025-01-01实际负载回填",
            "max_load_history_index_gap": int(min(i - self.load_history_max_idx[i]
                                                   for i in indices)),
            "max_scenario_history_index_gap": int(min(i - m for i, m in zip(indices, scenario_max))),
            "all_pass": bool(load_ok and scenario_ok),
        }

    def net_hat_at_hour(self, date_idx: int, issue_hour: int) -> np.ndarray:
        """时刻 issue_hour 用最新光伏预报 + regime 负载预测得到的净需求预测 (144,) kWh。"""
        pv_h = self.interp_pv_kwh(date_idx, issue_hour)
        return self.load_hat_kwh[date_idx] - pv_h


if __name__ == "__main__":
    from io_layer import load_all
    att = load_all()
    fc = Forecaster(att)
    print("夜间掩码时段数:", int(fc.night_mask.sum()), "/", T)
    # 0:00 光伏预报整体 MAE (kW) 应 ≈ 181.31
    dt = fc.dt_h
    pv_hat_kw = fc.pv_hat_kwh / dt
    mae_pv = np.abs(pv_hat_kw - att.pv_actual).mean()
    print(f"0:00 光伏预报 MAE = {mae_pv:.2f} kW (报告 ≈ 181.31)")
    # regime 计数：应 104 低（52 周五 + 52 周六）
    n_low = int((fc.regimes == "low").sum())
    print(f"低负载日数 = {n_low} (报告 104)")
    # 同 regime vs 跨 regime 负载预测 MAE 对照（留出期近似）
    idx = att.date_index
    import datetime as d_
    feb1 = idx[d_.date(2025, 2, 1)]
    load_kw_hat = fc.load_hat_kwh / dt
    mae_load = np.abs(load_kw_hat[feb1:] - att.load_actual[feb1:]).mean()
    print(f"同 regime 负载预测 MAE(Feb+) = {mae_load:.2f} kW (报告同 regime 137.52)")
    sc = fc.scenarios(feb1)
    print(f"Feb-01 场景数 = {sc.shape[0]} (应 8)， net_hat 和 = {fc.net_hat_kwh[feb1].sum():.1f} kWh")
