# -*- coding: utf-8 -*-
"""LP 内核（§6.2 item 4；MC1/MC2/MC3）。

共用储能—购电内核，SOC 区间用累积和（下三角）矩阵表达以消去 E_t 变量，只留 x,c,s,u。
两阶段随机规划矩阵预构造一次，循环内只更新右端项（RHS）与目标系数。
求解器统一 scipy.optimize.linprog(method="highs")，别无其它主求解器。
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import scipy.sparse as sp
from scipy.optimize import linprog

from params import T, E_MIN, E_MAX, E_STEP_MAX, ETA_C, ETA_D, K_EMERGENCY

_TOL = 1e-6


def _tril_ones(n: int) -> np.ndarray:
    """下三角全 1 矩阵 L：CS_t = sum_{i<=t} v_i = (L @ v)_t。"""
    return np.tril(np.ones((n, n)))


# ------------------------------------------------------------------ 问题1：确定性单日 LP
@dataclass
class DayResult:
    status: int
    obj: float
    x: np.ndarray
    c: np.ndarray
    s: np.ndarray
    q: np.ndarray            # 显式弃光/弃电量 kWh
    E: np.ndarray            # (T+1,) 含 E_0


def normalize_charge_discharge(c: np.ndarray, s: np.ndarray,
                               eta_c: float = ETA_C, eta_d: float = ETA_D):
    """逐时段消去同时充放，保持 SOC 增量不变。

    对任一 c_t>0,s_t>0，令 δ=min(c_t,s_t/(η_cη_d))，再取
    c'_t=c_t-δ、s'_t=s_t-η_cη_dδ。SOC 增量完全不变，净供给增加
    δ(1-η_cη_d)，由显式弃电变量吸收，因此可行性与购电费用不变。
    """
    c2 = np.asarray(c, dtype=float).copy()
    s2 = np.asarray(s, dtype=float).copy()
    delta = np.minimum(c2, s2 / (eta_c * eta_d))
    c2 -= delta
    s2 -= eta_c * eta_d * delta
    c2[np.abs(c2) < 1e-9] = 0.0
    s2[np.abs(s2) < 1e-9] = 0.0
    return c2, s2


def solve_day_q1(net_demand: np.ndarray, price: np.ndarray,
                 eta_c: float = ETA_C, eta_d: float = ETA_D,
                 E0: float = None, close: bool = True,
                 terminal_target: float = None) -> DayResult:
    """确定性日前 LP：min sum p_t x_t；变量 [x,c,s,q]，无紧急购电。

    平衡等式: x_t+s_t-c_t-q_t=net_t；SOC 递推 E_t=E_{t-1}+eta_c*c_t-s_t/eta_d；
    区间 [E_MIN,E_MAX]；close=True 施加 E_T=E_0（问题1 首尾闭合 K6）。
    """
    from params import E_INIT
    if E0 is None:
        E0 = E_INIT
    n = T
    L = _tril_ones(n)
    # 变量块 [x(n) | c(n) | s(n) | q(n)]，q 为显式弃光/弃电量
    Z = np.zeros((n, n))
    I = np.eye(n)
    # 平衡等式: x + s - c - q = net
    A_bal = np.hstack([I, -I, I, -I])
    b_bal = net_demand
    # SOC 上界: eta_c*L@c - (1/eta_d)*L@s <= E_MAX - E0
    soc_c = eta_c * L
    soc_s = -(1.0 / eta_d) * L
    A_socU = np.hstack([Z, soc_c, soc_s, Z])
    b_socU = np.full(n, E_MAX - E0)
    # SOC 下界: -(...) <= -(E_MIN - E0)
    A_socL = np.hstack([Z, -soc_c, -soc_s, Z])
    b_socL = np.full(n, -(E_MIN - E0))
    A_ub = np.vstack([A_socU, A_socL])
    b_ub = np.concatenate([b_socU, b_socL])
    A_eq_rows = [A_bal]
    b_eq_parts = [b_bal]
    # 首尾闭合（等式）: sum(eta_c*c - s/eta_d) = 0
    if close:
        target = E0 if terminal_target is None else terminal_target
        row = np.concatenate([np.zeros(n), eta_c * np.ones(n),
                              -(1.0 / eta_d) * np.ones(n), np.zeros(n)])
        A_eq_rows.append(row.reshape(1, -1))
        b_eq_parts.append(np.array([target - E0]))
    A_eq = np.vstack(A_eq_rows)
    b_eq = np.concatenate(b_eq_parts)
    cost = np.concatenate([price, np.zeros(3 * n)])
    bounds = ([(0, None)] * n + [(0, E_STEP_MAX)] * n
              + [(0, E_STEP_MAX)] * n + [(0, None)] * n)
    res = linprog(cost, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq,
                  bounds=bounds, method="highs")
    if not res.success:
        return DayResult(status=int(res.status), obj=float("nan"),
                         x=np.zeros(n), c=np.zeros(n), s=np.zeros(n), q=np.zeros(n),
                         E=np.full(n + 1, E0))
    x = res.x[:n]
    c = res.x[n:2 * n]
    s = res.x[2 * n:3 * n]
    c, s = normalize_charge_discharge(c, s, eta_c, eta_d)
    q = x + s - c - net_demand
    q[np.abs(q) < 1e-8] = 0.0
    E = _soc_traj(c, s, eta_c, eta_d, E0)
    return DayResult(status=0, obj=float(res.fun), x=x, c=c, s=s, q=q, E=E)


def _soc_traj(c: np.ndarray, s: np.ndarray, eta_c: float, eta_d: float, E0: float) -> np.ndarray:
    E = np.empty(len(c) + 1)
    E[0] = E0
    for t in range(len(c)):
        E_prev = E[t]
        E[t + 1] = E_prev + eta_c * c[t] - s[t] / eta_d
    return E


# ------------------------------------------------------------------ 问题2：两阶段随机规划
class TwoStageKernel:
    """两阶段随机规划矩阵预构造（MC3）。

    变量: [x(T) | 场景0: c s u q | 场景1: c s u q | ...]，K 个等概率场景。
    第一阶段 x 对全部场景共用（非预期性），第二阶段每场景独立 recourse。
    A_ub 只依赖 (T,K,eta_c,eta_d)，预构造一次；求解时只换 b_ub / cost / SOC-RHS。
    """

    def __init__(self, K: int, eta_c: float = ETA_C, eta_d: float = ETA_D):
        self.K = K
        self.eta_c = eta_c
        self.eta_d = eta_d
        self.n_var = T + K * 4 * T
        self._build()

    def _build(self) -> None:
        n = T
        K = self.K
        L = _tril_ones(n)
        I = sp.eye(n, format="csr")
        Z = sp.csr_matrix((n, n))
        Lc = sp.csr_matrix(self.eta_c * L)
        Ls = sp.csr_matrix(-(1.0 / self.eta_d) * L)
        # 不等式仅含 SOC 上/下界；供需平衡改为含显式弃电 q 的等式。
        X_ub = sp.vstack([Z, Z], format="csr")
        S_ub = sp.vstack([
            sp.hstack([Lc, Ls, Z, Z], format="csr"),
            sp.hstack([-Lc, -Ls, Z, Z], format="csr"),
        ], format="csr")
        ub_grid = []
        for k in range(K):
            row = [X_ub] + [None] * K
            row[k + 1] = S_ub
            ub_grid.append(row)
        self.A_ub = sp.bmat(ub_grid, format="csr")

        X_eq = I
        S_eq = sp.hstack([-I, I, I, -I], format="csr")  # x-c+s+u-q=net
        eq_grid = []
        for k in range(K):
            row = [X_eq] + [None] * K
            row[k + 1] = S_eq
            eq_grid.append(row)
        self.A_balance_eq = sp.bmat(eq_grid, format="csr")
        self._L = L

    def _bounds(self):
        n = T
        bounds = [(0, None)] * n
        for _k in range(self.K):
            bounds += ([(0, E_STEP_MAX)] * n + [(0, E_STEP_MAX)] * n
                       + [(0, None)] * n + [(0, None)] * n)
        return bounds

    def solve(self, scenarios_net: np.ndarray, price: np.ndarray, E0: float,
              pi: np.ndarray = None, kappa: float = K_EMERGENCY,
              terminal_target: float = None):
        """求解一日两阶段 LP。

        scenarios_net: (K,T) 各场景净需求；price: (T,)；E0: 期初实际 SOC。
        返回 (status, x, recourse) 其中 recourse[k]=(c_k,s_k,u_k,q_k)。
        """
        n = T
        K = self.K
        if pi is None:
            pi = np.full(K, 1.0 / K)
        assert scenarios_net.shape == (K, n)
        # b_ub
        b_parts = []
        for k in range(K):
            b_socU = np.full(n, E_MAX - E0)
            b_socL = np.full(n, -(E_MIN - E0))
            b_parts.append(np.concatenate([b_socU, b_socL]))
        b_ub = np.concatenate(b_parts)
        A_eq = self.A_balance_eq
        b_eq = scenarios_net.reshape(-1)
        if terminal_target is not None:
            rows = []
            for k in range(K):
                row = sp.lil_matrix((1, self.n_var))
                base = n + k * 4 * n
                row[0, base:base + n] = self.eta_c
                row[0, base + n:base + 2 * n] = -(1.0 / self.eta_d)
                rows.append(row.tocsr())
            A_eq = sp.vstack([A_eq] + rows, format="csr")
            b_eq = np.concatenate([b_eq, np.full(K, terminal_target - E0)])
        # cost：x → price；每场景 u → pi_k*kappa*price；c,s → 0
        cost = np.zeros(self.n_var)
        cost[:n] = price
        for k in range(K):
            base = n + k * 4 * n
            cost[base + 2 * n: base + 3 * n] = pi[k] * kappa * price
        res = linprog(cost, A_ub=self.A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq,
                      bounds=self._bounds(),
                      method="highs")
        if not res.success:
            return int(res.status), None, None
        x = res.x[:n]
        recourse = []
        for k in range(K):
            base = n + k * 4 * n
            ck = res.x[base: base + n]
            sk = res.x[base + n: base + 2 * n]
            uk = res.x[base + 2 * n: base + 3 * n]
            ck, sk = normalize_charge_discharge(ck, sk, self.eta_c, self.eta_d)
            qk = x + uk + sk - ck - scenarios_net[k]
            qk[np.abs(qk) < 1e-8] = 0.0
            recourse.append((ck, sk, uk, qk))
        return 0, x, recourse


# ------------------------------------------------------------------ 问题3/4-3：滚动时域调整 LP
def solve_adjust(free_from: int, b_plan: np.ndarray, net_hat: np.ndarray,
                 price: np.ndarray, E_start: float,
                 eta_c: float = ETA_C, eta_d: float = ETA_D,
                 lam_up: float = None, lam_dn: float = None,
                 kappa: float = K_EMERGENCY, fee_convention: str = "R_b",
                 terminal_target: float = None):
    """时刻 h 的调整子问题（§3.4.1）：只优化 t >= free_from 的时段。

    变量（仅未发生时段 m=T-free_from 个）：[a|dp|dm|c|s|u|q]，q 为显式弃电量。
    偏差线性化 a-b = dp - dm（MC6）；三段式费用双口径（MC9，fee_convention 分支）。
    返回 (status, a_full, dp_full, dm_full, c_m, s_m, u_m)。
    """
    from params import LAM_UP, LAM_DN
    if lam_up is None:
        lam_up = LAM_UP
    if lam_dn is None:
        lam_dn = LAM_DN
    m = T - free_from
    if m == 0:
        return 0, b_plan.copy(), np.zeros(T), np.zeros(T), \
            np.zeros(0), np.zeros(0), np.zeros(0), np.zeros(0)
    L = _tril_ones(m)
    I = np.eye(m)
    Z = np.zeros((m, m))
    p = price[free_from:]
    b = b_plan[free_from:]
    nh = net_hat[free_from:]
    # 顺序 [a | dp | dm | c | s | u | q]，每块 m 列，共 7m
    def blk(*mats):
        return np.hstack(list(mats))
    # 平衡等式: a + u + s - c - q = nh
    A_bal = blk(I, Z, Z, -I, I, I, -I)
    b_bal = nh
    # 偏差等式: a - b = dp - dm → a - dp + dm = b
    A_dev = blk(I, -I, I, Z, Z, Z, Z)
    b_dev = b
    # SOC 上/下（期初 E_start）
    soc_c = eta_c * L
    soc_s = -(1.0 / eta_d) * L
    A_socU = blk(Z, Z, Z, soc_c, soc_s, Z, Z)
    b_socU = np.full(m, E_MAX - E_start)
    A_socL = blk(Z, Z, Z, -soc_c, -soc_s, Z, Z)
    b_socL = np.full(m, -(E_MIN - E_start))
    A_ub = np.vstack([A_socU, A_socL])
    b_ub = np.concatenate([b_socU, b_socL])
    A_eq_rows = [A_bal, A_dev]
    b_eq_parts = [b_bal, b_dev]
    if terminal_target is not None:
        row = blk(Z[:1], Z[:1], Z[:1], eta_c * np.ones((1, m)),
                  -(1.0 / eta_d) * np.ones((1, m)), Z[:1], Z[:1])
        A_eq_rows.append(row)
        b_eq_parts.append(np.array([terminal_target - E_start]))
    A_eq = np.vstack(A_eq_rows)
    b_eq = np.concatenate(b_eq_parts)
    # 目标（费用核 φ，双口径）：
    #   R-b: p*min(a,b) + 1.5 p dp + 0.5 p dm = p*b + 1.5 p dp - 0.5 p dm（min(a,b)=b-dm）
    #        对优化而言常数 p*b 可留，系数： dp:+1.5p, dm:-0.5p
    #   R-a: p*b + 1.5 p dp + 0.5 p dm；系数 dp:+1.5p, dm:+0.5p
    cost = np.zeros(7 * m)
    if fee_convention == "R_b":
        cost[m:2 * m] = lam_up * p          # dp
        cost[2 * m:3 * m] = -lam_dn * p     # dm（min(a,b) 口径）
    elif fee_convention == "R_a":
        cost[m:2 * m] = lam_up * p
        cost[2 * m:3 * m] = lam_dn * p
    else:
        raise ValueError(f"未知 fee_convention: {fee_convention}")
    cost[5 * m:6 * m] = kappa * p           # u
    bounds = ([(0, None)] * m + [(0, None)] * m + [(0, None)] * m
              + [(0, E_STEP_MAX)] * m + [(0, E_STEP_MAX)] * m
              + [(0, None)] * m + [(0, None)] * m)
    res = linprog(cost, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq,
                  bounds=bounds, method="highs")
    if not res.success:
        return int(res.status), None, None, None, None, None, None, None
    a_m = res.x[:m]
    dp_m = res.x[m:2 * m]
    dm_m = res.x[2 * m:3 * m]
    c_m = res.x[3 * m:4 * m]
    s_m = res.x[4 * m:5 * m]
    u_m = res.x[5 * m:6 * m]
    c_m, s_m = normalize_charge_discharge(c_m, s_m, eta_c, eta_d)
    q_m = a_m + u_m + s_m - c_m - nh
    q_m[np.abs(q_m) < 1e-8] = 0.0
    a_full = b_plan.copy()
    a_full[free_from:] = a_m
    dp_full = np.zeros(T)
    dm_full = np.zeros(T)
    dp_full[free_from:] = dp_m
    dm_full[free_from:] = dm_m
    return 0, a_full, dp_full, dm_full, c_m, s_m, u_m, q_m


if __name__ == "__main__":
    # 冒烟测试：附件1 上的确定性 Q1 与最优性下界
    from io_layer import load_all
    att = load_all()
    dt_h = __import__("params").DT_H
    net = (att.load1 - att.pv1) * dt_h
    price = att.price1
    baseline = float(np.sum(price * np.maximum(net, 0.0)))
    res = solve_day_q1(net, price, close=True)
    print(f"Q1 status={res.status} obj={res.obj:.2f} baseline={baseline:.2f}")
    print(f"SOC min={res.E.min():.2f} max={res.E.max():.2f} E0={res.E[0]:.1f} ET={res.E[-1]:.1f}")
    print(f"c_max={res.c.max():.2f} s_max={res.s.max():.2f} E_step_max={E_STEP_MAX:.4f}")
