<div align="center">

# Academic Paper Discovery

### 多来源学术论文检索与筛选 Skill

输入研究主题，自动检索、去重、评分并生成中文论文对比表。

[![Codex Skill](https://img.shields.io/badge/Codex-Skill-111827?style=flat-square)](https://github.com/zhangbodong13-del/academic-paper-discovery)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Output](https://img.shields.io/badge/Output-Markdown-000000?style=flat-square&logo=markdown)](#输出示例)
[![Metadata Only](https://img.shields.io/badge/Policy-Metadata%20Only-16A34A?style=flat-square)](#注意事项)

</div>

---

## 能做什么

- 从 Crossref、Europe PMC、arXiv、DBLP、OpenAlex 和 Semantic Scholar 检索论文
- 自动合并重复论文
- 根据相关性、年份、正式发表状态、引用信息和代码链接评分
- 只保留“必读”和“强相关”论文
- 从摘要中提取论文创新点
- 匹配期刊或会议影响力指标
- 提供论文链接和开源代码链接
- 最终只生成一个 `report.md`

---

## 安装 Skill

在 Codex 中输入：

```text
使用 $skill-installer 安装这个 GitHub Skill：

https://github.com/zhangbodong13-del/academic-paper-discovery
```

安装完成后重新启动 Codex。

---

## 使用实例

### 示例一：机器人显微镜自动对焦

```text
使用 $academic-paper-discovery，检索 2022—2026 年机器人显微镜自动对焦论文。

要求：
- 关注双目视差、图像模糊和深度学习方法
- 优先推荐综述和带开源代码的论文
- 只保留必读和强相关论文
- 不使用低相关论文凑数量
```

### 示例二：夹爪位姿估计

```text
使用 $academic-paper-discovery，检索机器人夹爪六自由度位姿估计论文。

要求：
- 年份为 2020—2026
- 关注 RGB、双目图像、深度图和关键点方法
- 排除只做目标检测、不预测位姿的论文
- 优先实时部署和带 GitHub 代码的工作
```

### 示例三：视觉触觉多模态学习

```text
使用 $academic-paper-discovery，检索视觉与触觉多模态学习论文。

要求：
- 关注跨模态对比学习和自监督学习
- 优先 CVPR、ICCV、ECCV、NeurIPS 和 ICML
- 优先有公开代码和数据集的论文
- 数量上限为 30 篇
```

---

## 输出示例

最终报告只包含一张论文对比表：

| 序号 | 分组 | 论文 | 作者 | 年份 | 期刊/会议 | 影响力指标 | 得分 | 创新点 | 论文链接 | 开源代码 |
| ---: | --- | --- | --- | ---: | --- | --- | ---: | --- | --- | --- |
| 1 | 必读 | 示例论文 A | 作者甲等 | 2026 | CVPR | CCF A / CORE A* | 0.931 | 摘要提取：本文提出一种新的跨模态方法。 | [论文](https://example.org) | [代码](https://github.com/example/project) |
| 2 | 强相关 | 示例论文 B | 作者乙等 | 2025 | 示例期刊 | 未核验 | 0.812 | 未核验 | [论文](https://example.org) | 未找到 |

> 表格内容仅用于展示格式，不代表真实检索结果。
<img width="1327" height="900" alt="image" src="https://github.com/user-attachments/assets/eaf64eed-9f1b-49d5-9cc7-d0c6dd6c357b" />

---



---

## 注意事项

- 只检索论文元数据和公开网页链接
- 不下载论文正文或 PDF
- 不猜测 DOI、作者、年份、期刊或影响因子
- 无法核验的信息会显示“未核验”
- 没有找到的论文或代码链接会显示“未找到”
- 正式引用论文前，建议打开 DOI 或出版方页面再次确认

---

<div align="center">

**后续开发正在进行<img width="1149" height="1369" alt="ChatGPT Image 2026年7月21日 17_27_22" src="https://github.com/user-attachments/assets/14c1c19e-710e-4042-8019-6755523c7389" />
**

</div>
