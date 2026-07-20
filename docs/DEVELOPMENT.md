# 开发与命令行说明

本文档面向需要修改代码、运行测试或直接使用命令行的开发者。普通使用者只需阅读项目根目录的 `README.md`。

## D 盘开发环境

本项目当前约定把代码、虚拟环境、依赖缓存、请求和报告输出放在 D 盘：

```powershell
Set-Location D:\academic-paper-discovery
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]" --cache-dir D:\academic-paper-discovery\.cache\pip
```

可选 API Key 可通过当前终端环境设置，也可以参照 `.env.example`。免 Key 基础来源不依赖这些变量。

## 命令行请求

创建 `D:\academic-paper-discovery\requests\request.json`：

```json
{
  "topic": "机器人显微镜自动对焦",
  "expanded_queries": ["robot microscope autofocus"],
  "limit": 20,
  "target_venues": ["Nature Methods", "IEEE Transactions on Robotics"]
}
```

未提供年份时，程序使用当前年份及之前四年的默认五年范围，并在报告中记录该假设。

运行：

```powershell
.\.venv\Scripts\academic-paper-discovery.exe search `
  --request D:\academic-paper-discovery\requests\request.json `
  --output D:\academic-paper-discovery\outputs\robot-autofocus
```

输出目录包含：

- `report.md`：中文分层推荐、对比表、完整网址和数据源状态；
- `report.csv`：适合 Excel 的 UTF-8 BOM 表格；
- `report.json`：完整请求、检索式、元数据、评分分项和来源状态。

`--offline-fixture` 只用于自动测试和功能演示。它会明确显示“不是实时检索结果”，不能用来生成正式文献报告。

## 数据源

- 默认免 Key：Crossref、Europe PMC、arXiv、DBLP；
- 可选增强：OpenAlex、Semantic Scholar，需要相应 API Key；
- Codex 还可以按领域补充出版方官网、OpenReview、CVF Open Access 等网页来源。

每个来源独立记录“成功、失败、跳过”状态。来源局部失败不会中断整个任务。

## 运行测试

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

更详细的规则：

- `references/output-contract.md`：报告结构和网址格式；
- `references/ranking-policy.md`：相关性排序规则；
- `references/source-policy.md`：数据源与状态定义。
