# 论文图表布局规划

基于用户指定的 v2 文档，以 Git 记录修订。保持 24 张原有图的叙事位置，新增能量流与统计收益图，合计 26 张。

以 150 mm 对应 5.91 in 为新图画布宽度，9 pt 源文字约等于 9 pt 论文文字。保留原图采用其实际可读尺寸。

数据图的数值只从现有 JSON/CSV 读取；费用分解转为差额贡献，月电价转为统一坐标的十二面板；不生成虚构滚动中间轨迹。

<!-- BEGIN FIGURE_MANIFEST -->

**数据图（matplotlib；paper-figure）：**

- fig_att1_profile | claim=附件具有稳定的日内型与清晰的峰谷时段 | source=figures/data_att1_profile.json | section=数据分析 | language=zh | format=pdf,png | layout=single-landscape

- fig_load_regime_ridgeline | claim=负载日型存在可分的双制度结构 | source=figures/data_load_regime.json | section=数据分析 | language=zh | format=pdf,png | layout=single-landscape

- fig_load_calendar | claim=高低载制度在日历上呈稳定块状切换 | source=figures/data_load_calendar.json | section=数据分析 | language=zh | format=pdf,png | layout=single-landscape

- fig_regime_shape | claim=高载型不仅水平更高，峰段形状也不同 | source=figures/data_regime_shape.json | section=数据分析 | language=zh | format=pdf,png | layout=single-landscape

- fig_q1_dispatch_stack | claim=储能把谷时购电转移到峰时使用 | source=figures/data_q1_dispatch.json | section=问题一结果 | language=zh | format=pdf,png | layout=single-landscape

- fig_q1_soc_price | claim=电池在低价段充电并在高价段释放 | source=figures/data_q1_dispatch.json | section=问题一结果 | language=zh | format=pdf,png | layout=single-landscape

- fig_q1_savings_waterfall | claim=节省主要来自峰谷套利并扣除效率损耗 | source=figures/data_q1_savings_waterfall.json | section=问题一结果 | language=zh | format=pdf,png | layout=single-landscape

- fig_eta_sensitivity | claim=结论对合理效率扰动保持稳定 | source=figures/data_eta_sensitivity.json | section=问题一稳健性 | language=zh | format=pdf,png | layout=single-landscape

- fig_predictor_mae_bar | claim=日型分组预测器在两类日型上更稳健 | source=figures/data_predictor_mae.json | section=问题二预测器选择 | language=zh | format=pdf,png | layout=single-landscape

- fig_q2_margin_ucurve | claim=当前候选网格的最优裕度为0.03；扫描与最终Q2执行口径应区分 | source=figures/data_q2_margin_ucurve.json | section=问题二裕度扫描 | language=zh | format=pdf,png | layout=single-landscape

- fig_forecast_same_target | claim=较晚发布的预报对同一目标小时更准确 | source=figures/data_forecast_same_target.json | section=问题三预报信息价值 | language=zh | format=pdf,png | layout=single-landscape

- fig_q3_rolling_timeline | claim=同一日的原计划与最终执行量、调整方向及幅度 | source=figures/data_q3_rolling_timeline.json | section=问题三方法 | language=zh | format=pdf,png | layout=single-landscape

- fig_q3_cost_decomp | claim=购电费用下降与新增调整费共同构成净节省 | source=figures/data_q3_cost_decomp.json | section=问题三结果 | language=zh | format=pdf,png | layout=single-landscape

- fig_q2_emergency_calendar | claim=紧急购电是局部事件而非全年持续现象 | source=figures/data_q2_emergency_calendar.json | section=问题二结果 | language=zh | format=pdf,png | layout=single-landscape

- fig_q3_interp_check | claim=插值结果保持日内形状并满足边界约束 | source=figures/data_q3_interp_check.json | section=问题三数据处理 | language=zh | format=pdf,png | layout=single-landscape

- fig_q4_price_ridgeline | claim=十二个月均价格在统一绝对坐标下与固定价格比较 | source=figures/data_q4_price.json | section=问题四价格结构 | language=zh | format=pdf,png | layout=single-landscape

- fig_q4_price_hovmoller | claim=高价带沿季节和日内峰段形成可追踪结构 | source=figures/data_q4_price.json | section=问题四价格结构 | language=zh | format=pdf,png | layout=single-landscape

- fig_q4_fixed_vs_vol | claim=价格波动改变成本结构但不推翻滚动策略优势 | source=figures/data_q4_fixed_vs_vol.json | section=问题四结果 | language=zh | format=pdf,png | layout=single-landscape

- fig_forecast_decay | claim=长提前期误差总体更大，局部有回落；不声称严格单调 | source=figures/data_forecast_decay.json | section=敏感度分析 | language=zh | format=pdf,png | layout=single-landscape

- fig_rolling_benefit_uncertainty | claim=总收益区间与分季节收益不等于逐日占优 | source=sources/statistical_uncertainty.json | section=9.2 | language=zh | format=pdf,png | layout=single-landscape

**DrawIO 确定性技术图：**

- fig_roadmap | claim=统一线性规划内核支撑四个递进子问题 | source=figures/fig_roadmap.drawio | section=问题重述后 | language=zh | format=drawio,pdf,png | layout=single-landscape

- fig_energy_flow | claim=交流母线收支与效率作用位置 | source=code/params.py,code/lp_kernel.py | section=3.2 | language=zh | format=drawio,pdf,png | layout=single-landscape

- fig_arch_solver | claim=模块化实现使四问共享同一组参数和约束口径 | source=figures/fig_arch_solver.drawio | section=模型实现 | language=zh | format=drawio,pdf,png | layout=single-landscape

**TikZ 精确图：**

- tikz_feasible_q1 | claim=概念性有界多面体上存在顶点最优解，非约束数值投影 | source=figures/tikz_feasible_q1.tex | section=问题一模型建立 | language=zh | format=tex,pdf,png | layout=single-landscape

- tikz_soc_corridor | claim=可行储能轨迹受走廊、斜率和闭合三重约束 | source=figures/tikz_soc_corridor.tex | section=问题一模型建立 | language=zh | format=tex,pdf,png | layout=single-landscape

- tikz_info_set | claim=滚动决策严格服从随时间推进的因果信息边界 | source=figures/tikz_info_set.tex | section=问题三模型建立 | language=zh | format=tex,pdf,png | layout=single-landscape

**总数：** DATA=20, DRAWIO=3, TIKZ=3, ILLUSTRATION=0, OPTIONAL=0, ALL=26

<!-- END FIGURE_MANIFEST -->