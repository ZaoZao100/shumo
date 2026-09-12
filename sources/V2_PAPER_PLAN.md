# Restrained 图表修订计划

## 叙事骨架

整套图按“数据结构诊断 → 共用储能模型 → 确定性下界 → 日前预测与裕度 → 滚动修正 → 波动电价稳健性”展开。每张图保留原论文中的数据口径、变量含义与结论角色，只统一视觉编码、原生尺寸、输出格式和审查门槛。

## 风格合同

- 数据图：`colorblind` 色板、`clean_open` 版式、白底、细线、克制网格、无图内标题。
- 技术图：现代精致但低装饰，极淡灰节点、细灰边、唯一蓝色焦点，无阴影、无大面积彩色填充。
- 数学示意图：蓝色主结构、灰色约束与参考线、橙色仅标注最优点或关键边界。
- 交付：每图同时提供 350 dpi PNG 与矢量 PDF；原生宽度按最终版面比例预设。

<!-- BEGIN FIGURE_MANIFEST -->
**数据图（matplotlib，restrained 修订版产出 PNG/PDF）：**
- fig_att1_profile
- fig_load_regime_ridgeline
- fig_load_calendar
- fig_regime_shape
- fig_q1_dispatch_stack
- fig_q1_soc_price
- fig_q1_savings_waterfall
- fig_eta_sensitivity
- fig_predictor_mae_bar
- fig_forecast_same_target
- fig_q2_margin_ucurve
- fig_q2_emergency_calendar
- fig_q3_rolling_timeline
- fig_q3_cost_decomp
- fig_q3_interp_check
- fig_q4_price_ridgeline
- fig_q4_price_hovmoller
- fig_q4_fixed_vs_vol
- fig_forecast_decay

**HTML 流程/架构图（restrained 修订版产出 HTML/PDF/PNG）：**
- fig_roadmap
- fig_arch_solver

**TikZ 推导示意图（restrained 修订版产出 TEX/PDF/PNG）：**
- tikz_feasible_q1
- tikz_soc_corridor
- tikz_info_set
<!-- END FIGURE_MANIFEST -->

## 第二轮实际执行（2026-09-12）

以v1审查和原题为基础继续工作。24图的最终图号、图类、源文件、真实Word宽度及保留/微调/重绘/替换结论以本目录FIGURE_PLAN.json为准；它已按正文顺序排序，并纠正原规划对图15（同目标MAE）、图20（月均错位曲线）和图23（提前期变化而非严格衰减）的描述。

优先级：图4/18日期映射、图10瀑布方向、图22量纲比较、图19信息可用区间、图7末端标注；其次图3/8/9/16/17色义与图13交付期口径。最终保留12、微调10、重绘图10、替换图22。图20/23仅同步相关文字，图件保留。

色义合同进一步固定：主量/购电/预报蓝#0072B2，光伏与低载/正向收益青；充电负向区间、费用损耗/风险及基准橙；放电及向下偏离罚费使用中性灰。发布时刻是同一变量的时间索引，使用位置与标签区别，不轮转四色。数值高低色阶可按明确语义使用青/橙，中性灰承担非焦点信息。

不增加图数，不以新颜色、重复图例或冗余注记装饰版面。所有图在v1原框内等比放置；PDF保持29页。常规数据图主体约8.6—9.6pt，图19约7.85pt，数学上下标更小；HTML约9.3—9.7pt。纸面验证优先于源画布字号阈值。

三张TikZ使用既有矢量PDF；图7仅移动t标签并同步.tex，未使用TeX编译器。PNG保留足够纸面分辨率，PDF供矢量引用。不要把保留图写成“本轮重新生成”。

完整逐图结论、前后差异和限制见FIGURE_REVIEW_REPORT.md；逐页记录见review/PAGE_REVIEW_LOG.md；全部公式节点与表格不变，仅7处图件关联措辞修正。图13的扫描/最终执行费用口径及第10页既有[2pt]残留单列，未伪报为已解决。
