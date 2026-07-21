# 开发与命令行说明

本文档面向需要修改代码、运行测试或直接使用命令行的开发者。

## 安装开发环境

创建虚拟环境：

`python -m venv .venv`

安装项目依赖：

`.\.venv\Scripts\python.exe -m pip install -e ".[dev]"`

## 请求文件

检索请求使用 UTF-8 编码的 `request.json`。

常用字段包括：

- `topic`：研究主题
- `year_from`：起始年份
- `year_to`：结束年份
- `limit`：论文数量上限
- `prefer_code`：是否优先带开源代码的论文
- `high_relevance_only`：是否只保留高相关论文

未指定年份时，程序采用当前年份及之前四年的默认五年范围。

## 运行检索

命令格式：

`.\.venv\Scripts\academic-paper-discovery.exe search --request ".\request.json" --output ".\output"`

输出目录只包含：

`report.md`

报告中包含一张论文对比表，字段包括影响力指标、得分、创新点、论文链接和开源代码。

## 离线演示

离线测试命令需要增加：

`--offline-fixture`

该参数只用于测试和演示，不能作为正式论文检索结果。

## 影响力指标

本地指标文件位于：

`src/academic_paper_discovery/data/impact_metrics.json`

远程指标表可以通过环境变量 `IMPACT_METRICS_URL` 配置。

无法核验的影响力指标统一显示为“未核验”。

## 运行测试

运行全部测试：

`.\.venv\Scripts\python.exe -m pytest -q`