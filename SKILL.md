---
name: academic-paper-discovery
description: Use when a user requests a literature search, paper recommendations, venue-focused discovery, a research landscape review, or a structured comparison table with verified academic metadata and links.
---

# Academic Paper Discovery

围绕用户研究主题执行多来源论文检索、去重、筛选和排序，并生成中文 Markdown 报告。

## 核心约束

- 只检索论文元数据和公开网页链接，不下载论文正文或 PDF。
- 不猜测 DOI、作者、年份、期刊、会议、影响力指标或网址。
- 无法核验的信息写“未核验”。
- 未找到的论文或代码链接写“未找到”。
- 单个数据源失败时继续处理其他来源。

## 工作流程

1. 解析研究主题、年份、数量、目标期刊或会议和排除词。
2. 构建必要的中英文检索词。
3. 运行多个学术元数据来源。
4. 根据 DOI、arXiv ID 和规范化标题去重。
5. 根据主题相关性、年份、正式发表状态、引用信息和代码链接评分。
6. 从摘要或可信元数据中提取创新点。
7. 从本地或远程结构化指标表匹配影响力指标。

## 输出要求

最终只生成一个 `report.md`。

报告中只允许出现：

```markdown
## 论文对比表
```

表格列依次为：

```text
序号
分组
论文
作者
年份
期刊/会议
影响力指标
得分
创新点
论文链接
开源代码
```

只输出以下两类论文：

- 必读
- 强相关

满足要求的论文有多少就输出多少，不使用低相关论文凑数量。

论文链接使用 `[论文](URL)`，代码链接使用 `[代码](URL)`。

## 交付前检查

- 创新点来自摘要或可信元数据。
- 未核验的信息没有被猜测。
- 最终只生成 `report.md`。
- 报告中只包含一张论文对比表。