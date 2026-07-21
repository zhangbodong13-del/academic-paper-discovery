---
name: academic-paper-discovery
description: Use when a user requests a literature search, paper recommendations, venue-focused discovery, research landscape review, or a structured comparison table with verified academic metadata and links.
---

# Academic Paper Discovery

围绕用户的研究主题执行多来源论文检索、去重、筛选、排序，并生成中文 Markdown 论文对比表。

## 核心约束

- 只检索论文元数据和公开网页链接，不下载论文正文或 PDF。
- 不把有限数据源的结果描述成“全部论文”或“穷尽检索”。
- 不猜测 DOI、作者、年份、期刊、会议、影响力指标或网址。
- 缺少可靠证据时写“未核验”。
- 缺少论文或代码链接时写“未找到”。
- 单个数据源失败时继续使用其他数据源。

## 工作流程

### 1. 解析用户需求

提取：

- 研究主题；
- 中英文同义词和缩写；
- 年份范围；
- 返回数量；
- 目标期刊或会议；
- 排除关键词；
- 是否优先综述、代码、实时方法或正式发表版本。

未指定年份时，默认采用当前年份及之前四年的五年范围。

未指定数量时，默认上限为 20 篇。

### 2. 构建检索式

保留用户原始研究主题，并补充必要的：

- 英文翻译；
- 常见缩写；
- 领域术语；
- 同义表达。

不得擅自扩大或改变用户的研究问题。

### 3. 运行论文检索

优先通过项目提供的 Python CLI 检索：

- Crossref；
- Europe PMC；
- arXiv；
- DBLP；
- OpenAlex；
- Semantic Scholar。

运行命令：

```powershell
academic-paper-discovery search `
  --request <UTF-8请求文件.json> `
  --output <输出目录>