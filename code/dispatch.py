# -*- coding: utf-8 -*-
"""因果实时调度规则（§3.3.5；MC8）。

在时刻 t 只使用：当前实际 SOC E_prev、0:00 计划 x_t、参考调度 (c̄_t,s̄_t) 与已实现的
实际负载/光伏。逐时段前推，先调充/放的净方向以避免同时段既增充又增放，缺口以紧急购电补足。
"""
from __future__ import annotations

import numpy as np

from params import T, E_MIN, E_MAX, E_STEP_MAX, ETA_C, ETA_D
from lp_kernel import normalize_charge_discharge


def causal_step(x_t: float, net_t: float, c_ref_t: float, s_ref_t: float,
                E_prev: float, eta_c: float = ETA_C, eta_d: float = ETA_D,
                terminal_target: float = None, remaining_steps_after: int = None):
    """单时段因果调度。返回 (c_t,s_t,u_t,q_t,E_next)。

    只用当前已实现净需求、当前 SOC 与既有计划。q_t 显式吸收富余；若给定全年末期
    目标，则用可达走廊保证在剩余时段内仍能回到目标，不读取未来真实负载或光伏。
    """
    c_ref_t, s_ref_t = (v[0] for v in normalize_charge_discharge(
        np.array([c_ref_t]), np.array([s_ref_t]), eta_c, eta_d))
    # 计划净供给 = x + s̄ - c̄；δ>0 表示实际比计划更缺电
    delta = net_t - (x_t + s_ref_t - c_ref_t)
    # 物理充放上限（含 SOC 余量）
    s_ub = max(min(E_STEP_MAX, eta_d * (E_prev - E_MIN)), 0.0)
    c_ub = max(min(E_STEP_MAX, (E_MAX - E_prev) / eta_c), 0.0)
    if delta > 0:
        # 先减充电，再补放电（净多放 delta，不同时增充增放）
        c_t = max(c_ref_t - delta, 0.0)
        extra_dis = max(delta - c_ref_t, 0.0)
        s_t = float(np.clip(s_ref_t + extra_dis, 0.0, s_ub))
        c_t = float(np.clip(c_t, 0.0, c_ub))
    else:
        a = -delta
        # 先减放电，再补充电（净多充 a）
        s_t = max(s_ref_t - a, 0.0)
        extra_chg = max(a - s_ref_t, 0.0)
        c_t = float(np.clip(c_ref_t + extra_chg, 0.0, c_ub))
        s_t = float(np.clip(s_t, 0.0, s_ub))
    E_next = E_prev + eta_c * c_t - s_t / eta_d

    # 全年末期 SOC 可达走廊。最后一段 remaining_steps_after=0 时强制 E_next=target。
    if terminal_target is not None:
        if remaining_steps_after is None or remaining_steps_after < 0:
            raise ValueError("terminal_target 需要非负 remaining_steps_after")
        lo = max(E_MIN, terminal_target - remaining_steps_after * eta_c * E_STEP_MAX)
        hi = min(E_MAX, terminal_target + remaining_steps_after * E_STEP_MAX / eta_d)
        if E_next < lo - 1e-9:
            need = lo - E_next
            reduce_s = min(s_t, need * eta_d)
            s_t -= reduce_s
            need -= reduce_s / eta_d
            if need > 1e-9:
                c_t += need / eta_c
        elif E_next > hi + 1e-9:
            need = E_next - hi
            reduce_c = min(c_t, need / eta_c)
            c_t -= reduce_c
            need -= eta_c * reduce_c
            if need > 1e-9:
                s_t += need * eta_d
        c_t = float(np.clip(c_t, 0.0, c_ub))
        s_t = float(np.clip(s_t, 0.0, s_ub))
        c_t, s_t = (v[0] for v in normalize_charge_discharge(
            np.array([c_t]), np.array([s_t]), eta_c, eta_d))
        E_next = E_prev + eta_c * c_t - s_t / eta_d
        if E_next < lo - 1e-6 or E_next > hi + 1e-6:
            raise RuntimeError("末期 SOC 可达走廊执行失败")

    residual = net_t - x_t - s_t + c_t
    u_t = max(residual, 0.0)
    q_t = max(-residual, 0.0)
    return float(c_t), float(s_t), float(u_t), float(q_t), float(E_next)


def causal_dispatch(x_plan: np.ndarray, net_actual: np.ndarray,
                    c_ref: np.ndarray, s_ref: np.ndarray, E0: float,
                    eta_c: float = ETA_C, eta_d: float = ETA_D,
                    terminal_target: float = None):
    """执行因果调度，返回 (c,s,u,q,E)；E 长度 T+1 含 E0。"""
    c = np.zeros(T)
    s = np.zeros(T)
    u = np.zeros(T)
    q = np.zeros(T)
    E = np.empty(T + 1)
    E[0] = E0
    for t in range(T):
        c[t], s[t], u[t], q[t], E[t + 1] = causal_step(
            x_plan[t], net_actual[t], c_ref[t], s_ref[t], E[t], eta_c, eta_d,
            terminal_target=terminal_target,
            remaining_steps_after=T - t - 1 if terminal_target is not None else None)
    return c, s, u, q, E


def reference_from_recourse(recourse, pi: np.ndarray = None):
    """参考轨迹 = 各场景 recourse 储能动作的期望（均值场景储能动作）。"""
    K = len(recourse)
    if pi is None:
        pi = np.full(K, 1.0 / K)
    c_ref = np.zeros(T)
    s_ref = np.zeros(T)
    for k, item in enumerate(recourse):
        ck, sk = item[0], item[1]
        c_ref += pi[k] * ck
        s_ref += pi[k] * sk
    return c_ref, s_ref
