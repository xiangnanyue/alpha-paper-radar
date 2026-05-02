# Alpha Paper Radar

Alpha Paper Radar 是一个最小可运行的每日论文雷达 MVP：

1. 从 arXiv API 抓取论文元数据
2. 按主题关键词筛选
3. 保存为 JSONL
4. 生成 Markdown 日报草稿
5. 提供 CLI 手动运行
6. 提供 GitHub Actions 手动触发

> 当前版本**不接 OpenAI API**、不解析 PDF、不发邮件、不写 Wiki。

## 环境要求

- Python 3.12+

## 安装

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

## 配置

编辑 `config/topics.yaml`，默认内置 4 个主题：

- quant_finance
- deep_learning_sota
- cross_section_time_series
- llm_progress

## 本地运行

```bash
python -m alpha_paper_radar.cli run --date today
# 或
python -m alpha_paper_radar.cli run --date 2026-05-02
```

输出文件：

- `data/raw/YYYY-MM-DD.jsonl`
- `reports/YYYY-MM-DD.md`

## 测试

```bash
pytest
```

## GitHub Actions 手动运行

1. 打开仓库 `Actions` 页面
2. 选择 workflow `Daily Alpha Paper Radar`
3. 点击 `Run workflow`
4. 可选传入 `run_date`（格式 `YYYY-MM-DD`），留空则使用当天

