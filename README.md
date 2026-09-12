# 数学建模论文与图表

当前工作目录采用固定文件名，通过 Git 提交记录后续修改，不再创建 revision 或 v1/v2/v3 工作副本。

- `paper/补齐约束.docx`、`paper/补齐约束.pdf`：当前论文，直接复制此前最新成果；27 张图、30 页 PDF。用户已要求暂停图表修改，本次仅迁入 Git，并不代表视觉效果已获认可。
- `figures/`：图件 PNG/PDF、绘图脚本、数据快照、HTML 和 TikZ 源码。
- `code/`、`user_data/`、`results/`、`modeling/`：模型代码、题目附件与结果、建模说明。
- `FIGURE_PLAN.json`、`PAPER_PLAN.md`、`FIGURE_REVIEW_REPORT.md`：已有规划和审查记录。
- `review/`：既有审计与实际渲染截图，完整论文页图位于 `review/pages/`。
- `original/补齐约束.docx`：原始论文，供追溯，不作编辑入口。
- `sources/`：此前修订所用来源快照。
- `provenance/`：迁入清单、校验记录及历史一次性迁移脚本。

## 后续工作

直接修改当前目录内文件，审阅差异后执行 `git add`、`git commit`、`git push`。旧工作区保留原样，不再作为后续编辑入口。

历史报告、规划和来源快照中的版本名、旧绝对路径是当时记录，保留原文，不表示需要维护多套版本。`provenance/migration_tools/` 依赖旧目录，仅供追溯，不应作为当前构建入口执行。

现有数据图通常可由对应的 `figures/gen_fig_*.py` 读取同目录数据快照生成；`gen_v3_figures.py` 是历史命名的组合绘图脚本，执行会覆盖其对应图件。Python 依赖涉及 numpy、pandas、scipy、matplotlib、Pillow、openpyxl 等，中文字体需本机安装。此提交没有重跑模型或重绘图件。

三张 TikZ 图保留真实矢量 PDF 与 tex；重新编译需要合适的 TeX 环境。Word 导出入口为 `tools/export_word.ps1`，需要 Windows 和 Microsoft Word。

参考学习仓库：https://github.com/yushugulao/CUMCM-Archive 。参考论文下载件不纳入此仓库。
