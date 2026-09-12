# -*- coding: utf-8 -*-
"""逐日配对费用差的时间序列不确定性分析。

使用7日循环移动块自助法保留周内相关性。置信区间针对当前334日交付期的
平均日费用差及其同期总额；它不是独立样本外验证。
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parent.parent
_RESULTS = _ROOT / "results"
_FIG = _ROOT / "figures"
SEED = 20260912
BLOCK_LENGTH = 7
N_BOOT = 10000


def _season(month: int) -> str:
    if month in (12, 1, 2):
        return "冬季"
    if month in (3, 4, 5):
        return "春季"
    if month in (6, 7, 8):
        return "夏季"
    return "秋季"


def moving_block_ci(values: np.ndarray, block_length: int = BLOCK_LENGTH,
                    n_boot: int = N_BOOT, seed: int = SEED) -> dict:
    """循环移动块自助95%区间；每次抽取整块并截取到原序列长度。"""
    x = np.asarray(values, float)
    n = x.size
    if n == 0:
        raise ValueError("费用差序列为空")
    rng = np.random.default_rng(seed)
    n_blocks = int(np.ceil(n / block_length))
    starts = rng.integers(0, n, size=(n_boot, n_blocks))
    offsets = np.arange(block_length)
    idx = (starts[:, :, None] + offsets[None, None, :]) % n
    samples = x[idx.reshape(n_boot, -1)[:, :n]]
    means = samples.mean(axis=1)
    totals = samples.sum(axis=1)
    return {
        "n_days": int(n),
        "block_length_days": int(block_length),
        "bootstrap_replicates": int(n_boot),
        "seed": int(seed),
        "mean_daily_difference_yuan": float(x.mean()),
        "mean_daily_ci95_yuan": [float(v) for v in np.quantile(means, [0.025, 0.975])],
        "period_total_difference_yuan": float(x.sum()),
        "period_total_ci95_yuan": [float(v) for v in np.quantile(totals, [0.025, 0.975])],
        "median_daily_difference_yuan": float(np.median(x)),
        "positive_day_share": float(np.mean(x > 0)),
        "stable_positive_under_block_ci": bool(np.quantile(totals, 0.025) > 0),
    }


def _group_summary(df: pd.DataFrame, group_col: str) -> list[dict]:
    rows = []
    for label, g in df.groupby(group_col, sort=False):
        rows.append({
            group_col: label,
            "n_days": int(len(g)),
            "saving_vs_q3_s0_yuan": float(g["saving_vs_q3_s0_yuan"].sum()),
            "saving_vs_q2_yuan": float(g["saving_vs_q2_yuan"].sum()),
            "mean_daily_saving_vs_s0_yuan": float(g["saving_vs_q3_s0_yuan"].mean()),
            "mean_daily_saving_vs_q2_yuan": float(g["saving_vs_q2_yuan"].mean()),
            "positive_day_share_vs_s0": float((g["saving_vs_q3_s0_yuan"] > 0).mean()),
            "positive_day_share_vs_q2": float((g["saving_vs_q2_yuan"] > 0).mean()),
        })
    return rows


def run() -> dict:
    q2 = pd.read_csv(_RESULTS / "q2_daily_costs.csv")
    q3 = pd.read_csv(_RESULTS / "q3_daily_costs.csv")
    df = q2.merge(q3, on="date", validate="one_to_one")
    df["date"] = pd.to_datetime(df["date"])
    df["saving_vs_q3_s0_yuan"] = df["q3_s0_total_cost"] - df["q3_s1_total_cost"]
    df["saving_vs_q2_yuan"] = df["q2_total_cost"] - df["q3_s1_total_cost"]
    df["season"] = df["date"].dt.month.map(_season)
    threshold = float(df["actual_net_energy_kwh"].quantile(0.95))
    df["extreme_net_demand_day"] = df["actual_net_energy_kwh"] >= threshold

    ci_s0 = moving_block_ci(df["saving_vs_q3_s0_yuan"].to_numpy(), seed=SEED)
    ci_q2 = moving_block_ci(df["saving_vs_q2_yuan"].to_numpy(), seed=SEED + 1)
    seasonal = _group_summary(df, "season")
    extreme = _group_summary(df.assign(
        extreme_group=np.where(df["extreme_net_demand_day"], "净负荷能量最高5%", "其余95%")),
        "extreme_group")

    result = {
        "method": "7日循环移动块自助法；逐日配对费用差；双侧百分位95%置信区间",
        "scope": "2025-02-01至2025-12-31共334日；同一交付期用于参数选择与评价，非独立测试集",
        "saving_vs_q3_internal_s0": ci_s0,
        "saving_vs_q2_two_stage": ci_q2,
        "seasonal_performance": seasonal,
        "extreme_day_definition": f"按实际日净负荷能量的交付期95%分位数划分，阈值={threshold:.6f} kWh",
        "extreme_day_performance": extreme,
        "improvement_stability_statement": (
            "两项费用差的块自助95%区间下界均大于0，支持在当前交付期与所设重采样方法下总体改进稳定。"
            if ci_s0["stable_positive_under_block_ci"] and ci_q2["stable_positive_under_block_ci"]
            else "至少一项费用差的块自助95%区间包含0，不能声称改进在当前交付期内稳定为正。"
        ),
    }

    _RESULTS.mkdir(exist_ok=True)
    df.to_csv(_RESULTS / "daily_paired_cost_differences.csv", index=False)
    pd.DataFrame(seasonal).to_csv(_RESULTS / "seasonal_performance.csv", index=False)
    pd.DataFrame(extreme).to_csv(_RESULTS / "extreme_day_performance.csv", index=False)
    (_RESULTS / "statistical_uncertainty.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    q3_path = _FIG / "problem_3_results.json"
    if q3_path.is_file():
        q3_result = json.loads(q3_path.read_text(encoding="utf-8"))
        q3_result["saving_vs_q3_internal_S0_yuan"] = round(ci_s0["period_total_difference_yuan"], 2)
        q3_result["saving_vs_Q2_two_stage_yuan"] = round(ci_q2["period_total_difference_yuan"], 2)
        q3_result["statistical_uncertainty"] = result
        q3_path.write_text(json.dumps(q3_result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
