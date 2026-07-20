# 数据源与检索边界

## 默认免 Key 来源

- Crossref：跨学科出版物元数据和 DOI。
- Europe PMC：生命科学与医学论文元数据。
- arXiv：预印本元数据；忽略响应中的 PDF 下载链接，不访问 PDF。
- DBLP：计算机科学期刊和会议出版物元数据。

## 可选增强来源

- OpenAlex：需要 `OPENALEX_API_KEY`。
- Semantic Scholar：需要 `SEMANTIC_SCHOLAR_API_KEY`。

没有相应 Key 时不调用对应可选来源。可按领域需要通过出版方官网、OpenReview、CVF Open Access 或其他可用学术工具补充检索。

## 故障隔离

任何来源失败都不应阻止已成功来源进入去重和排序。继续使用其他可用结果，并在报告的“局限与下一步”说明来源覆盖可能不完整。

## 内容边界

只允许请求 JSON、XML、Atom 或纯文本元数据。可以记录 DOI、出版方落地页、预印本页面、代码和项目网页，但不自动访问或下载论文正文和 PDF。不得从标题模式猜测不存在的 DOI 或网址。
