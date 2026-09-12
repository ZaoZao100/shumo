# 数学建模论文与图表

固定文件名交付，以 Git 提交追溯修改；不再创建版本目录。

- `paper/补齐约束.docx`、`paper/补齐约束.pdf`：当前成果，26张图、28页；基于用户指定的v2文档重建。
- 本轮重绘7张原图、微调4张图的落位、保留13张，新增能量流与统计收益2张。
- `FIGURE_REVIEW_REPORT.md`：本轮逐图审查、差异与限制。
- `review/current_final_audit.json`：90项结构、数据及原文件保护检查。
- `review/current_figures/`：26组PNG与PDF渲染对照；`review/current_pages/`：完整28页论文渲染。
- `figures/`：源代码、数据、可编辑Draw.io、SVG、TikZ及PNG/PDF；有效26图清单以`FIGURE_PLAN.json`为准，其他文件为历史产物。
- `provenance/input_paper.docx`：用户指定v2的构建输入；`original/`及外部历史文件保持不变。
- `code/`、`user_data/`、`results/`、`sources/`：既有模型、附件和统计依据。本轮未重跑模型。

## 重建

使用安装了numpy、matplotlib、Pillow、lxml、PyMuPDF等依赖的Python，以及具备Playwright的Node、Microsoft Edge和Microsoft Word。中文字体需要Microsoft YaHei。

1. `python figures/gen_paper_refresh.py`：重建6张本轮数据图。
2. `python tools/build_diagrams.py`、`node tools/render_diagrams.cjs`：生成3张技术图源文件及渲染输出。Draw.io与SVG来自同一坐标定义，PDF使用Chromium矢量打印，不是原生Draw.io导出。
3. `python tools/build_paper.py`：从保护的输入DOCX构建当前论文、重编号、检查公式与表格。
4. PowerShell运行 `./tools/export_word.ps1`，再运行 `python tools/render_paper.py`，导出PDF和页面图。渲染器使用已配置的documents技能工具，需要对应运行时路径。
5. 查看所有变化图及完整页图，再运行 `python tools/audit_paper.py`。`tools/write_review.py`记录本轮已完成的人工审阅，不能代替未来的视觉检查。

三张TikZ保留真实矢量PDF与tex；本环境未重新编译。历史组合绘图脚本可能覆盖当前图，不应作为本轮构建入口。`provenance/migration_tools/`含旧迁移代码，其中math_corrections.py由当前构建复用。

本轮权威证据均使用current_前缀；旧review/pages、figure_pairs及其他历史审计仍保留，不能用来判断当前页数和图数。

参考学习：[CUMCM-Archive](https://github.com/yushugulao/CUMCM-Archive)。参考下载件不纳入仓库；学习记录保留在仓库中。
