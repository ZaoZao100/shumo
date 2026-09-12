# -*- coding: utf-8 -*-
"""费用结算（§6.2 item 6；MC9 双口径）。

Q1 单项、Q2 两项、Q3/Q4-3 三项。三段式费用核 φ 按 §1.3 双口径：
  R-b（主）: p·min(a,b) + 1.5 p·dp + 0.5 p·dm
  R-a（对照，P3-C2 逐字）: p·b + 1.5 p·dp + 0.5 p·dm
其中 a=最终执行计划、b=0:00 原始计划、dp=max(a-b,0)、dm=max(b-a,0)。
与 §5.5① 的 C11/C12/C12a 费用恒等式逐字一致。
"""
from __future__ import annotations

import numpy as np

from params import K_EMERGENCY, LAM_UP, LAM_DN


def settle_q1(x: np.ndarray, price: np.ndarray) -> float:
    """问题1：仅计划购电费用 sum(p_t x_t)。"""
    return float(price @ x)


def settle_q2(x: np.ndarray, u: np.ndarray, price: np.ndarray,
              kappa: float = K_EMERGENCY) -> dict:
    """问题2：计划购电费用 + 紧急购电费用（κ 倍缺电时段电价）。"""
    plan_cost = float(price @ x)
    emergency_cost = float(kappa * (price * u).sum())
    return dict(plan_cost=plan_cost, emergency_cost=emergency_cost,
                total=plan_cost + emergency_cost)


def settle_q3(a: np.ndarray, b: np.ndarray, u: np.ndarray, price: np.ndarray,
              fee_convention: str = "R_b",
              lam_up: float = LAM_UP, lam_dn: float = LAM_DN,
              kappa: float = K_EMERGENCY) -> dict:
    """问题3/4-3：三段式费用（计划基价 + 调整偏差 + 紧急购电），双口径。"""
    dp = np.maximum(a - b, 0.0)
    dm = np.maximum(b - a, 0.0)
    up_cost = float(lam_up * (price * dp).sum())
    dn_cost = float(lam_dn * (price * dm).sum())
    emergency_cost = float(kappa * (price * u).sum())
    if fee_convention == "R_b":
        base_cost = float(price @ np.minimum(a, b))
    elif fee_convention == "R_a":
        base_cost = float(price @ b)
    else:
        raise ValueError(f"未知 fee_convention: {fee_convention}")
    adjust_cost = up_cost + dn_cost
    total = base_cost + adjust_cost + emergency_cost
    return dict(base_cost=base_cost, up_cost=up_cost, dn_cost=dn_cost,
                adjust_cost=adjust_cost, emergency_cost=emergency_cost,
                total=total, dp=dp, dm=dm)


def no_storage_baseline(net_demand: np.ndarray, price: np.ndarray) -> float:
    """无储能基线：sum(p_t max(net_t,0))。"""
    return float((price * np.maximum(net_demand, 0.0)).sum())
