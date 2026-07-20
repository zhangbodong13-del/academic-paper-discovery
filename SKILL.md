---
name: academic-paper-discovery
description: Use when a user requests a literature search, must-read paper recommendations, venue-focused discovery, a research landscape review, or a structured paper table with verified metadata links and transparent source coverage.
---

# 学术论文发现

围绕用户研究主题执行多来源论文检索、去重、筛选、排序和中文报告。默认生成“必读、强相关、拓展阅读”三层推荐、统一论文对比表，以及紧随表格且序号一致的完整论文网址。

## 核心约束

- 只检索和保存论文元数据及公开网页链接，**不下载论文正文或 PDF**。
- 不把有限数据源结果描述成“全部论文”或“穷尽检索”。
- 不猜测 DOI、作者、年份、期刊、引用量或网址；缺失字段写“未核验”或“未找到”。
- 逐项报告本次运行中真实“成功、失败、跳过”的数据源及原因。
- 一个来源失败时继续处理其他来源，并在局限部分说明覆盖缺口。

## 工作流程

### 1. 明确检索约束

从用户请求提取研究主题、同义词、年份、数量、目标期刊/会议、排除词，以及是否优先综述、代码、正式发表版本或高相关结果。

未指定年份时使用当前年份及之前四年的默认五年范围，并在报告“检索假设”中明确写出。未指定数量时默认 20 篇。

### 2. 构建中英文检索式

保留用户原始主题，再补充必要的中英文同义词、缩写和领域术语。不要用未经用户授权的概念扩展改变研究问题。记录最终检索式、目标期刊/会议和排除词，保证检索可复核。

### 3. 选择并运行来源

默认通过本项目 CLI 检索 Crossref、Europe PMC、arXiv、DBLP。配置 Key 后可增加 OpenAlex 和 Semantic Scholar。根据领域需要，可使用 Codex 可用的学术检索工具或网页检索补充 Nature、Science、相关子刊、出版方官网、OpenReview、CVF Open Access 及重要期刊和会议。

运行本地 CLI：

```powershell
academic-paper-discovery search --request <UTF-8请求.json> --output <D盘输出目录>
```

不得使用 `--offline-fixture` 生成正式结果；该参数只用于测试和演示。

详细来源边界和状态规则见 `references/source-policy.md`。

### 4. 去重、合并与透明排序

优先用 DOI、arXiv ID 和规范化标题识别重复；合并预印本与正式版本时保留所有可用来源和网址。低置信度重复只标记，不强行合并。

排序必须以主题相关性为主，目标期刊/会议、多来源交叉验证、正式版本、代码、时效和年龄归一化引用影响为辅。不得只按引用量排序。详细规则见 `references/ranking-policy.md`。

### 5. 输出 B+C 中文报告

固定按以下顺序输出：

1. 检索假设
2. 检索式
3. 必读
4. 强相关
5. 拓展阅读
6. 论文对比表
7. 论文网址
8. 数据源检索状态
9. 局限与下一步

论文网址必须紧跟对比表。每一项沿用表格序号和标题，并逐行列出完整 DOI、出版方、预印本、代码或项目网址。具体格式见 `references/output-contract.md`，可复用 `assets/report-template.md`。

## 交付前检查

- 数量和年份是否符合用户要求，默认值是否已经明确说明？
- “必读、强相关、拓展阅读”和对比表是否同时存在？
- 完整网址是否在表格之后，序号是否一一对应？
- 成功、失败、跳过的数据源是否来自实际运行状态？
- 是否清楚声明不下载论文正文或 PDF，并说明检索局限？
