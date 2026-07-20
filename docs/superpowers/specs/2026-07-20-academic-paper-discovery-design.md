# Academic Paper Discovery Skill 设计规范

## 1. 目标

创建可复用的 Codex Skill `academic-paper-discovery`。用户输入研究方向、问题描述、中英文关键词或筛选条件后，Skill 通过多来源广覆盖检索，找出真正值得阅读且可能支持研究工作的论文。

本项目聚焦论文发现、检索、筛选、去重、排序与解释，不下载论文或 PDF，不负责绕过付费墙或建立大型本地文献管理系统。“全网检索”统一表述为“多来源广覆盖检索”，不宣称绝对覆盖全部互联网论文。

Skill 的机器标识保留为符合 Codex 命名规范的 `academic-paper-discovery`；用户可见内容默认使用中文，包括显示名称、`SKILL.md` 正文、README、CLI 帮助、报告标题、字段名、状态说明和错误提示。检索输入继续支持中文、英文及中英文混合关键词。

## 2. 已确认的产品形态

采用 B+C 组合输出：

1. 结构化报告：分为“必读”“强相关”“拓展阅读”。
2. 结构化表格：便于用户复制、筛选和继续整理。
3. 网址清单：紧跟在表格后面，按表格序号逐条列出论文正式页面、DOI、预印本、项目页或代码页等可核验网址。
4. 检索审计：列出查询词、默认筛选条件、成功来源、失败来源及降级情况。

每篇论文至少包含：标题、作者、年份、期刊或会议、论文类型、研究问题、主要方法、核心贡献、相关性解释、推荐级别、DOI/URL、代码或项目页（如有）以及数据来源。

## 3. 使用示例

- “检索 2022—2026 年双目显微图像中的手术夹爪六自由度位姿估计论文。”
- “寻找机器人显微自动对焦的必读论文，优先综述和开源代码。”
- “检索因果表征学习论文，只看 Nature、Science 及其子刊和顶级机器学习会议。”
- “stereo surgical instrument pose estimation 双目，包含跨领域可迁移方法。”

如果用户未指定年份，使用可解释的默认时间窗口，并在报告开头明确写出该默认值。

## 4. 推荐架构

采用 Python 检索核心与 Codex 编排相结合的混合架构。

### 4.1 Python 检索核心

Python 提供确定性、可测试的能力：

- 读取并校验检索请求。
- 调用公开数据源适配器。
- 标准化论文元数据。
- 合并版本并去重。
- 计算相关性和质量分层。
- 输出 Markdown 报告、CSV/JSON 数据及网址清单。
- 缓存请求并记录数据源状态。

### 4.2 Codex 编排

`SKILL.md` 指导 Codex：

- 理解自然语言研究问题并生成可审计的中英文查询计划。
- 调用 Python 脚本完成基础检索。
- 使用当前可用的学术工具或网页搜索补漏。
- 核验重点期刊、会议及官方页面。
- 基于摘要和来源证据解释“为什么值得读”。
- 将补充结果重新送入统一的规范化、去重和报告流程。

该边界让稳定的数据处理留在代码中，让需要语义判断和适应当前互联网状态的工作留给 Codex。

## 5. 数据来源

第一版优先实现无需 API Key 即可使用的稳定来源：

- Crossref
- arXiv
- Europe PMC / PubMed 公共接口
- DBLP

通过可选适配器或 Codex 网页补漏支持：

- OpenAlex（当前官方 API 要求免费 API Key）
- Semantic Scholar
- OpenReview
- CVF Open Access
- Nature、Science 及出版商官网
- IEEE、ACM、Springer 等正式出版页面
- 常规网页搜索

实现前核验各来源在当前日期的官方 API 文档、速率限制、robots 和使用条款。任一来源失败时不得终止整个任务；结果必须记录失败类型并继续使用其他来源。

## 6. API Key 与本地存储

- 核心检索默认无需 API Key。
- Key 只作为速率、稳定性或字段完整度增强项。
- Key 只能从环境变量读取，仓库仅提供 `.env.example`。
- `.env`、缓存、运行结果和虚拟环境不得提交到 Git。
- 项目、虚拟环境、依赖缓存、检索缓存和生成结果均保存在 `D:\academic-paper-discovery` 内。
- Python 虚拟环境使用 `D:\academic-paper-discovery\.venv`。
- pip 缓存使用 `D:\academic-paper-discovery\.cache\pip`。
- 检索缓存使用 `D:\academic-paper-discovery\.cache\search`。
- 默认输出使用 `D:\academic-paper-discovery\outputs`。

## 7. 查询计划

真正检索前生成并展示：

1. 用户原始问题。
2. 中文与英文核心概念。
3. 同义词、缩写和全称。
4. 上位词、下位词及相邻学科表达。
5. 任务词、方法词和应用场景词。
6. 重点 venue 限定查询。
7. 排除词。
8. 年份、数量、论文类型、代码偏好和跨领域偏好。

查询计划属于最终报告的一部分，不能作为不可见的黑盒步骤。

## 8. 两阶段检索

### 8.1 阶段一：广泛召回

- 对多个来源分批查询多组表达。
- 限制单来源最大结果数和总分页数。
- 收集标题、摘要、作者、年份、venue、DOI、URL、引用信息、开放获取状态和来源标记。
- 保留原始记录以便审计。
- 对失败、限速和字段缺失执行降级处理。

### 8.2 阶段二：筛选与排序

评分由可解释特征组成：

- 标题和摘要相关性。
- 核心概念、任务、方法和场景匹配。
- venue 匹配与论文类型。
- 多来源交叉出现。
- 正式版本优先级。
- 代码或项目页加分。
- 发表时间和经过时间归一化的引用信息。

不得把引用量直接当成绝对质量。新论文和老论文按发表时间分组或归一化比较。最终结果同时输出总分、分层和简短推荐理由。

## 9. 去重与版本合并

匹配顺序：

1. DOI 精确匹配。
2. arXiv ID 精确匹配。
3. 标准化标题精确匹配。
4. 标题模糊匹配加作者和年份约束。
5. 其他可靠标识符。

同一论文的 arXiv、会议官网、OpenReview、作者主页和出版商版本合并为一个记录。展示时优先正式发表版本，同时保留合法预印本与项目链接。冲突字段保留来源追踪，并按来源可靠性选择展示值。

## 10. Venue Registry

使用可维护的 `config/venues.yaml`，而不是只依赖标题字符串。每个 venue 记录：

- `canonical_name`
- `aliases`
- `type`
- `publisher`
- `family`
- `tier_label`
- `official_domains`
- `issn`

首批覆盖 Nature、Science 及其相关子刊，并包括 CVPR、ICCV、ECCV、ICML、NeurIPS、ICLR、T-RO、RA-L、ICRA、IROS、MICCAI 和 TMI。Registry 可由用户扩展，不把首批名单写死为唯一范围。

## 11. 输出契约

Markdown 输出顺序固定如下：

1. 检索范围与默认假设。
2. 查询计划。
3. 必读论文。
4. 强相关论文。
5. 拓展阅读。
6. 结构化对比表。
7. 论文网址清单。
8. 数据源覆盖与失败说明。
9. 方法限制与下一轮检索建议。

网址清单必须位于表格后，序号与表格保持一致。不得伪造 DOI、引用量、代码地址或摘要内容；缺失字段明确标记为“未核验”或“未找到”。

## 12. 代码结构

```text
academic-paper-discovery/
├── SKILL.md
├── README.md
├── agents/openai.yaml
├── pyproject.toml
├── .env.example
├── .gitignore
├── config/
│   ├── venues.yaml
│   └── defaults.yaml
├── scripts/
│   └── search_papers.py
├── src/academic_paper_discovery/
│   ├── models.py
│   ├── query_plan.py
│   ├── pipeline.py
│   ├── deduplication.py
│   ├── ranking.py
│   ├── reporting.py
│   ├── cache.py
│   └── adapters/
├── references/
│   ├── source-policy.md
│   ├── ranking-policy.md
│   └── output-contract.md
├── assets/
│   └── report-template.md
├── tests/
└── docs/superpowers/
    ├── specs/
    └── plans/
```

每个适配器实现统一接口，返回规范化前的来源记录和结构化状态。核心模型、去重、排序、报告与网络访问相互隔离，以支持离线单元测试。

## 13. 技术选择

- Python 3.11 或更高版本。
- `httpx`：HTTP 客户端。
- `pydantic`：输入与论文模型校验。
- `typer`：命令行接口。
- `PyYAML`：配置读取。
- `rapidfuzz`：标题模糊匹配。
- `pytest` 与 `respx`：单元测试和 HTTP 适配器测试。
- Markdown、CSV 和 JSON：输出格式。

不引入数据库、向量数据库、浏览器自动化或大型机器学习模型作为第一版的必需依赖。

## 14. 错误处理

- 网络超时、限速、服务错误和无效响应转换为统一的来源状态。
- 适配器只报告自身失败，不抛出导致整个管线终止的未处理异常。
- 缓存损坏时忽略单条缓存并重新请求。
- 无任何结果时输出查询审计和改进建议，而不是空表格。
- 字段冲突、低置信度去重和非官方链接在结果中显式标记。

## 15. 测试与验收

开发遵循测试先行：先写失败测试并确认失败原因，再实现最小代码使其通过。

验收至少覆盖：

- 中英文和混合关键词查询计划。
- 无年份输入时的显式默认值。
- 多适配器部分失败时继续运行。
- DOI、arXiv ID、标题及作者年份组合去重。
- 正式版本优先与预印本链接保留。
- 新旧论文引用信息的时间处理。
- venue 别名和 ISSN 识别。
- B+C Markdown 报告及表后网址清单顺序。
- CSV/JSON 输出。
- 无 API Key 的离线模拟测试和真实公开接口冒烟测试。
- `skill-creator` 的结构校验。
- 至少一个真实研究问题的端到端试用。

## 16. Git 与可视化工作方式

- 仓库路径：`D:\academic-paper-discovery`。
- VS Code 打开该目录，所有同步到 D 盘的修改可实时查看。
- 按设计、脚手架、核心模型、适配器、去重排序、报告、Skill 文档和最终验证等里程碑分别提交。
- 提交信息采用清晰的 Conventional Commits 风格。
- 远程目标：`zhangbodong13-del/academic-paper-discovery`。
- 创建或连接远程仓库后推送当前分支；任何密钥和本地缓存均不得进入远程仓库。

## 17. README 用户入口

仓库根目录保留一份面向使用者的 `README.md`。README 在显眼位置解释 Skill 的用途、安装方法和最短调用方式，并原样提供以下可复制提示词：

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

README 同时给出一个替换了“研究主题”的具体示例，并提醒用户：显式使用 `$academic-paper-discovery` 最可靠，自然语言检索请求也可以触发 Skill。

## 18. 不在第一版范围内

- 下载论文、PDF、补充材料或全文数据集。
- 绕过登录、验证码或付费墙。
- 全文解析和全文向量库。
- Zotero 等文献管理器同步。
- 定时监控和自动邮件提醒。
- 声称搜索结果绝对完整。
