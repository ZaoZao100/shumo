# -*- coding: utf-8 -*-
"""19 张数据图的共用底座：restrained 版式初始化 + 真实载荷读取 + 统一导出。

载荷缺失一律抛错（不静默降级为空图），保证「图必须由真实数据生成」。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIG = ROOT / "figures"
sys.path.insert(0, str(ROOT))

from _utils.plot_utils import (setup_style, set_paper_placement, save_fig,   # noqa: E402
                               PALETTES, PALETTE, COLORS, _lighten, auto_legend,
                               shared_legend, consolidate_shared_legends,
                               declutter_axes, dynamic_limits, uncertainty_band,
                               draw_vector_heatmap, smart_labels)

setup_style(palette="auto")

# 项目标记由共享工具读取时会为“去指纹”轮转预设色序。restrained 合同要求
# 主色稳定为蓝，因此在风格初始化后恢复 Wong 色板的语义顺序，并同步默认色环。
from cycler import cycler  # noqa: E402
import matplotlib as mpl  # noqa: E402

PALETTE[:] = list(PALETTES["colorblind"])
mpl.rcParams["axes.prop_cycle"] = cycler(color=PALETTE)
COLORS["primary"] = PALETTE[0]
COLORS["secondary"] = PALETTE[1]
COLORS["accent"] = PALETTE[2]
COLORS["up"] = PALETTE[2]
COLORS["down"] = PALETTE[1]
COLORS["highlight"] = PALETTE[1]

# 统一语义映射：蓝=主模型/主轨迹，橙=风险/阈值，青=正向或替代方案，
# 其余系列只在确有分组语义时使用。填充均由同色系变浅获得。
C = {
    "blue_main": PALETTE[0],
    "blue_secondary": PALETTE[5],
    "red_strong": PALETTE[1],
    "red_1": _lighten(PALETTE[1], 0.78),
    "red_2": _lighten(PALETTE[1], 0.52),
    "green_2": _lighten(PALETTE[2], 0.60),
    "green_3": PALETTE[2],
    "gold": PALETTE[6],
    "teal": PALETTE[2],
    "violet": PALETTE[3],
    "neutral_black": COLORS["dark"],
    "neutral_dark": COLORS["text"],
    "neutral_mid": COLORS["ref_line"],
    "neutral_light": COLORS["grid"],
}
M = ("o", "s", "^", "D", "P", "X")

# 原生画布贴近最终插图宽度，避免插入论文后整体缩小、有效字号跌破 8 pt。
WIDTH_WIDE = 6.0
WIDTH_SQUARE = 5.0
WIDTH_TALL = 3.6


def load(name: str) -> dict:
    path = FIG / f"data_{name}.json"
    if not path.exists():
        raise FileNotFoundError(f"缺少真实数据载荷 {path.name}，请先运行 figures/prep_fig_data.py")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def finish(fig, name: str, width_fraction: float | None = None) -> Path:
    out = FIG / f"{name}.png"
    pdf = FIG / f"{name}.pdf"
    set_paper_placement(fig, width_fraction)
    save_fig(fig, str(out))
    fig.savefig(pdf, format="pdf", bbox_inches=None, pad_inches=0.15)
    print(f"  -> {pdf.name}, {out.name}")
    return out
