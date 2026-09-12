# -*- coding: utf-8 -*-
"""统一调度入口（§6.2）：跑齐问题 1-4 + 敏感度，汇总 figures/all_results.json。

用法：
  python main.py            # 跑齐 1,2,3,4 + sensitivity，并汇总 all_results.json
  python main.py 1          # 仅问题 1
  python main.py 2 3        # 问题 2、3
  python main.py sensitivity
  python main.py aggregate  # 不重算，仅从已有 figures/*_results.json 汇总
各问结果写 figures/problem_<k>_results.json 与 user_data/result*.xlsx（由各驱动自负）。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_FIG = _ROOT / "figures"

_STAGES = {
    "1": ("problem1", "figures/problem_1_results.json"),
    "2": ("problem2", "figures/problem_2_results.json"),
    "3": ("problem3", "figures/problem_3_results.json"),
    "4": ("problem4", "figures/problem_4_results.json"),
    "sensitivity": ("sensitivity_analysis", "figures/sensitivity_results.json"),
    "statistics": ("statistical_uncertainty", "results/statistical_uncertainty.json"),
}


def _run_stage(key: str) -> None:
    mod_name, _out = _STAGES[key]
    mod = __import__(mod_name)
    print(f"===== 运行 {mod_name} =====", flush=True)
    mod.run()


def _merge_probes(dst: dict, probes) -> None:
    if not isinstance(probes, dict):
        return
    for k in ("bounds", "monotonic"):
        vals = probes.get(k)
        if isinstance(vals, list):
            dst[k].extend(vals)


def aggregate() -> dict:
    """从 figures/problem_*_results.json 汇总紧凑摘要 + 合并 logic_probes。不载入巨表。"""
    merged_probes = {"bounds": [], "monotonic": []}
    summary = {}
    for k in ("1", "2", "3", "4"):
        path = _ROOT / _STAGES[k][1]
        if not path.is_file():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        _merge_probes(merged_probes, data.get("logic_probes"))
        summary[f"problem_{k}"] = {
            "method": data.get("method"),
            "price_source": data.get("price_source"),
            "all_constraints_pass": data.get("all_constraints_pass"),
        }
    # 关键跨问指标（标量，供人工/审计快速核对；不与 Q1 soc_* 键名冲突）
    def _get(fname, key):
        p = _FIG / fname
        return json.loads(p.read_text(encoding="utf-8")).get(key) if p.is_file() else None

    all_results = {
        "pipeline": "2026 CUMCM C 微网电力调控：Q1 确定性 LP / Q2 两阶段随机 / Q3 滚动 MPC / Q4 波动电价重构",
        "solver": "scipy.optimize.linprog(method='highs')",
        "delivery_range": "2025-02-01 .. 2025-12-31 (334 天)",
        "stage_summary": summary,
        "headline": {
            "Q1_total_cost": _get("problem_1_results.json", "Q1_total_cost"),
            "Q1_no_storage_baseline": _get("problem_1_results.json", "no_storage_baseline"),
            "Q2_two_stage_total": _get("problem_2_results.json", "two_stage_total"),
            "Q2_best_scalar_margin": _get("problem_2_results.json", "best_scalar_margin"),
            "Q3_S1_total": _get("problem_3_results.json", "S1_total"),
            "Q3_rolling_value_yuan": _get("problem_3_results.json", "rolling_value_yuan"),
            "Q3_saving_vs_Q2_yuan": _get("problem_3_results.json", "saving_vs_Q2_two_stage_yuan"),
            "Q4_2_total_known": _get("problem_4_results.json", "Q4_2_two_stage_total_known"),
            "Q4_value_of_price_info_yuan": _get("problem_4_results.json", "value_of_price_info_yuan"),
        },
        "logic_probes": merged_probes,
    }
    _FIG.mkdir(exist_ok=True)
    (_FIG / "all_results.json").write_text(
        json.dumps(all_results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已汇总 figures/all_results.json（{len(merged_probes['monotonic'])} 条方向探针）")
    return all_results


def run() -> None:
    args = [a for a in sys.argv[1:] if a.strip()]
    if not args:
        order = ["1", "2", "3", "4", "sensitivity", "statistics"]
    elif args == ["aggregate"]:
        aggregate()
        return
    else:
        order = args
    for key in order:
        if key not in _STAGES:
            raise SystemExit(f"未知阶段 {key!r}；可选 {list(_STAGES)} 或 aggregate")
        _run_stage(key)
    aggregate()


if __name__ == "__main__":
    run()
