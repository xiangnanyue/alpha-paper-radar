# Alpha Paper Radar

Alpha Paper Radar 已升级为“论文状态追踪系统”MVP：

1. 从 arXiv API 抓取论文元数据（标准库实现）
2. 按主题关键词筛选
3. 保存当日原始候选为 JSONL
4. 合并到长期 registry（`data/state/paper_registry.json`）
5. 基于 canonical arXiv ID 去重（如 `2605.01234v1` 与 `2605.01234v2`）
6. 生成结构化 Markdown 日报（new / updated / carry-over / suppressed）

> 当前版本**不接 OpenAI API**、不解析 PDF、不发邮件、不写 Wiki。

## 输出路径

- `data/raw/YYYY-MM-DD.jsonl`
- `data/state/paper_registry.json`
- `reports/YYYY-MM-DD.md`

## 配置

- 主题配置：`config/topics.yaml`
- 报告策略：`config/reporting.toml`

`config/reporting.toml` 默认：

```toml
dedupe_window_days = 14
carryover_cooldown_days = 7
max_carryover_papers = 3
min_new_papers_for_email = 3
```

## 本地运行

```bash
PYTHONPATH=src python -m alpha_paper_radar.cli run --date today
```

## 测试

```bash
PYTHONPATH=src python -m unittest discover -s tests
```
