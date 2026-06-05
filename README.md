# Alpha Paper Radar

Alpha Paper Radar 是一个轻量级的 arXiv 论文雷达，用来按固定主题抓取论文元数据、做关键词筛选、追踪论文状态，并生成每天可以直接阅读的 Markdown 报告。

这个仓库目前定位为 **MVP 论文状态追踪系统**：重点不是自动写长评或接入大模型，而是把每日新增、更新、继续关注和重复抑制的论文稳定整理出来，方便人工阅读 `reports/` 目录中的日报。

> 当前版本**不接 OpenAI API**、不解析 PDF、不发邮件、不写 Wiki，也不需要任何密钥即可运行。

## 这个项目做什么

一次运行会完成以下流程：

1. 从 arXiv API 抓取配置主题下的论文元数据（标准库实现）。
2. 按主题关键词筛选候选论文。
3. 将当日原始候选保存为 JSONL。
4. 合并到长期论文状态 registry。
5. 基于 canonical arXiv ID 去重（例如 `2605.01234v1` 与 `2605.01234v2` 会归并到同一篇论文）。
6. 生成结构化 Markdown 日报，包含：
   - Executive Summary
   - New Papers
   - Updated Papers
   - Carry-over Papers
   - Suppressed Duplicates

每条抓取到的论文记录在排序功能实现前都会保留 `priority="unscored"`。

## 目录与输出

```text
config/
  topics.yaml             # 跟踪主题、arXiv 分类和关键词
  reporting.toml          # 报告生成与 carry-over 策略

data/raw/
  YYYY-MM-DD.jsonl        # 每日筛选后的原始候选论文元数据

data/state/
  paper_registry.json     # 固定 registry 路径，用于跨日期追踪论文状态

reports/
  YYYY-MM-DD.md           # 每日阅读报告
  conclude_YYYYMMDD.md    # 人工整理的阶段性总结（如有）

src/alpha_paper_radar/    # CLI、抓取、筛选、registry、报告渲染代码
tests/                    # 单元测试
```

稳定输出路径：

- `data/raw/YYYY-MM-DD.jsonl`
- `data/state/paper_registry.json`
- `reports/YYYY-MM-DD.md`

## 如何阅读已有报告

如果你只是想跟踪论文，不一定需要先运行程序。推荐直接从 `reports/` 开始：

1. 打开最新日期的 `reports/YYYY-MM-DD.md`。
2. 先读 `Executive Summary`：快速查看当天新增、更新、carry-over 和重复抑制数量。
3. 再读 `Top picks`：这是当天最值得优先扫读的论文入口。
4. 按需进入以下分区：
   - `New Papers`：首次进入 radar 的论文。
   - `Updated Papers`：已有论文发布了新版本或元数据更新。
   - `Carry-over Papers`：仍值得继续关注、但当天不是新增或更新的论文。
   - `Suppressed Duplicates`：被去重逻辑抑制的重复记录数量。
5. 每篇论文条目通常包含 canonical ID、作者、匹配主题、发布时间/更新时间、推荐原因和建议动作。

当前推荐的人工阅读方式是：每天看 `Executive Summary` 和 `Top picks`，只对标记为 `Read now` 或与你主题强相关的论文继续打开 arXiv 原文。

## 跟踪主题配置

主题配置位于 `config/topics.yaml`。当前内置主题包括：

- `quant_finance`：组合优化、因子投资、风险预测、资产配置等量化金融方向。
- `deep_learning_sota`：SOTA、benchmark、foundation model、diffusion、MoE、long-context 等深度学习进展。
- `cross_section_time_series`：截面、面板、时间序列、资产定价和预测回归。
- `llm_progress`：LLM、reasoning、agent、RAG、tool use、多模态等方向。

每个主题由 arXiv 分类、关键词和 `max_results` 控制。修改主题后可以先运行配置校验：

```bash
PYTHONPATH=src python -m alpha_paper_radar.cli validate-config --path config/topics.yaml
```

## 报告策略配置

报告策略位于 `config/reporting.toml`，默认配置为：

```toml
dedupe_window_days = 14
carryover_cooldown_days = 7
max_carryover_papers = 3
min_new_papers_for_email = 3
```

说明：

- `dedupe_window_days`：重复论文抑制窗口。
- `carryover_cooldown_days`：同一篇 carry-over 论文再次出现前的冷却天数。
- `max_carryover_papers`：单日报告最多展示的 carry-over 数量。
- `min_new_papers_for_email`：为未来邮件功能保留的阈值；当前 MVP 不发送邮件。

## 本地运行

### 1. 准备环境

项目需要 Python 3.11+。

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

### 2. 生成今天的报告

```bash
PYTHONPATH=src python -m alpha_paper_radar.cli run --date today
```

### 3. 指定日期运行

```bash
PYTHONPATH=src python -m alpha_paper_radar.cli run --date 2026-05-28
```

### 4. 试运行（不写入文件）

```bash
PYTHONPATH=src python -m alpha_paper_radar.cli run --date today --dry-run
```

### 5. 临时限制每个主题抓取数量

```bash
PYTHONPATH=src python -m alpha_paper_radar.cli run --date today --max-results-override 10
```


## BAAI 热门论文工作流（独立于 arXiv）

新增的 BAAI 热门论文流程不会写入 arXiv 的稳定输出路径，而是使用单独目录：

```text
data/baai_hot/raw/YYYY-MM-DD.jsonl          # 当天从 BAAI 日榜/周榜抓到并去重后的热度论文快照
data/baai_hot/state/paper_registry.json    # BAAI 热门论文增量状态和热度历史
reports/baai_hot/YYYY-MM-DD.md             # BAAI 热门论文日报
```

运行命令：

```bash
PYTHONPATH=src python -m alpha_paper_radar.cli run-baai-hot --date today
```

流程设计：

1. 抓取 `https://hub.baai.ac.cn/papers` 的日榜，保留热度值 `>= 50` 的论文。
2. 抓取 `https://hub.baai.ac.cn/papers?model=hotness&time=week` 的周榜，保留热度值 `>= 500` 的论文。
3. 按 BAAI 论文详情页 ID 去重；同一论文同时出现在日榜和周榜时，只保留一条记录，并记录来源列表与最高热度。
4. 读取详情页补充 PDF 链接；如果只想测试列表抓取，可用 `--skip-pdf` 跳过详情页访问。
5. 复用 `config/topics.yaml` 中已有关键词做主题命中标记，但不复用 arXiv 的抓取、registry 或报告路径。
6. 增量合并到 `data/baai_hot/state/paper_registry.json`：历史论文不会重复新增，只会更新 `latest_hotness`、`peak_hotness`、`hotness_delta` 和逐日 `observations`。
7. 生成每日 Markdown 报告，重点列出：
   - `Fast Rising Papers`：热度相对上次观察上升最快的论文。
   - `Latest Papers`：近 14 天发表的最新热门论文。
   - `Topic Matches`：命中既有关注主题关键词的论文。

试运行（不写文件）：

```bash
PYTHONPATH=src python -m alpha_paper_radar.cli run-baai-hot --date today --dry-run --skip-pdf
```

## 测试

```bash
PYTHONPATH=src python -m unittest discover -s tests
```

也可以使用 pytest：

```bash
PYTHONPATH=src pytest
```

## 公开仓库前的安全检查

当前 MVP 不需要 API key，仓库中也不应包含密钥。公开前重点检查以下内容：

- `.env` 已在 `.gitignore` 中忽略。
- `.env.example` 只保留占位说明，不包含真实密钥。
- 代码没有读取 OpenAI、邮件、Wiki 等第三方服务密钥。
- `data/raw/` 和 `reports/` 保存的是 arXiv 元数据与人工阅读报告，不应放入私人笔记、账号信息或未授权内容。
- 提交前可以运行下面的快速扫描命令：

```bash
rg -n --hidden -g '!**/.git/**' -i "(api[_-]?key|password|credential|private[_ -]?key|BEGIN .*PRIVATE KEY|sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]+|github_pat_[A-Za-z0-9_]+|xox[baprs]-[A-Za-z0-9-]+|AKIA[0-9A-Z]{16})" .
```

如果该命令只命中 `.gitignore`、`.env.example`、文档里的安全说明，通常表示没有发现明显的密钥泄露迹象。若命中真实值，或在 `data/`、`reports/` 中发现私人笔记和账号信息，请先移除并轮换对应密钥，再公开仓库。

## 当前不包含的功能

为保持 MVP 简单，本项目当前明确不包含：

- OpenAI API 或其他 LLM API 集成。
- PDF 下载或 PDF 内容解析。
- 邮件推送。
- Wiki/Notion/知识库自动发布。
- 自动论文打分排序。

这些功能可以后续独立扩展，但不应影响当前稳定输出路径和日报结构。
