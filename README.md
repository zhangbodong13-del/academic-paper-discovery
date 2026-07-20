# 学术论文发现 Skill

`academic-paper-discovery` 是一个面向 Codex 的中文多来源论文发现 Skill。它把中英文检索式、元数据聚合、版本去重、透明排序和 B+C 中文报告组织成一条可审计流程。

本项目只获取论文元数据和公开网页链接，**不下载论文正文或 PDF**。结果受检索式、年份、数据源覆盖和服务状态影响，不应表述为穷尽性检索。

## 快速使用

把下面这段提示词中的“研究主题”替换成你的主题：

```text
使用 $academic-paper-discovery，围绕“研究主题”进行多来源论文检索。

要求：
- 年份：未指定则明确说明默认范围
- 数量：20 篇
- 优先来源：Nature、Science、相关子刊及本领域重要期刊和会议
- 输出：必读、强相关、拓展阅读
- 同时生成论文对比表
- 将完整论文网址按表格序号列在表格后面
- 说明实际检索成功和失败的数据源
```

示例：

```text
使用 $academic-paper-discovery，检索 2022–2026 年机器人显微自动对焦论文，优先综述和开源代码。
```

## D 盘安装

下面的示例把项目、虚拟环境、缓存、请求和输出都放在 D 盘：

```powershell
Set-Location D:\academic-paper-discovery
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]" --cache-dir D:\academic-paper-discovery\.cache\pip
```

可选 Key 放入当前终端环境或参照 `.env.example` 配置。免 Key 基础来源不依赖这些变量。

## 命令行使用

创建 `D:\academic-paper-discovery\requests\request.json`：

```json
{
  "topic": "机器人显微镜自动对焦",
  "expanded_queries": ["robot microscope autofocus"],
  "limit": 20,
  "target_venues": ["Nature Methods", "IEEE Transactions on Robotics"]
}
```

未提供年份时，程序使用“当前年份及之前四年”的默认五年范围，并在报告中明确记录。运行：

```powershell
.\.venv\Scripts\academic-paper-discovery.exe search `
  --request D:\academic-paper-discovery\requests\request.json `
  --output D:\academic-paper-discovery\outputs\robot-autofocus
```

输出目录包含：

- `report.md`：必读、强相关、拓展阅读、对比表、表后完整网址、数据源状态与局限；
- `report.csv`：适合 Excel 的 UTF-8 BOM 表格；
- `report.json`：完整请求、检索式、元数据、评分分项和来源状态。

`--offline-fixture` 仅供测试和演示，会明确显示“不是实时检索结果”，不能用作正式文献检索。

## 数据源

- 默认免 Key：Crossref、Europe PMC、arXiv、DBLP；
- 可选增强：OpenAlex、Semantic Scholar，需要相应 API Key；
- Codex 可按研究领域补充出版方官网、OpenReview、CVF Open Access 等网页检索，并把补充来源的真实成功或失败状态写入报告。

来源某次失败不会中断其他来源。最终报告逐项显示实际“成功、失败、跳过”状态，不能把未调用来源写成成功。

## 开发验证

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

更详细的输出、排序和来源规则见 `references/output-contract.md`、`references/ranking-policy.md`、`references/source-policy.md`。
