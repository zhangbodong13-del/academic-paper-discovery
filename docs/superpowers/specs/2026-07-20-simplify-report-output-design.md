# Simplify Academic Paper Discovery Output Design

**Date:** 2026-07-20  
**Status:** Approved for planning

## Goal

Simplify every generated deliverable so readers see recommendations and actionable links without search-process metadata. Remove source-status data throughout the application, preserve source-failure isolation, merge paper and code links into the comparison table, and keep README examples synchronized.

## User-visible report contract

Render Markdown sections in this order:

1. 必读
2. 强相关
3. 拓展阅读
4. 论文对比表
5. 局限与下一步

Do not render these sections:

- 检索假设
- 检索式
- 论文网址
- 数据源检索状态

The comparison table contains these columns:

| Column | Content |
| --- | --- |
| 序号 | Stable number shared with the recommendation lists |
| 分组 | 必读、强相关或拓展阅读 |
| 论文 | Paper title |
| 作者 | Available author metadata or 未核验 |
| 年份 | Verified year or 未核验 |
| 期刊/会议 | Verified venue or 未核验 |
| 推荐理由 | Concise ranking explanation |
| 论文链接 | Clickable Markdown link such as `[论文](URL)` or `未找到` |
| 开源代码 | Clickable Markdown link such as `[代码](URL)` or `未找到` |

Prefer DOI or official publisher/CVF landing pages for the paper link. Use a discovered repository or project URL for the code link. Do not derive or guess URLs.

## Data model and serialization

Remove `SourceStatus` and `SearchResult.source_statuses` from the public and internal result models. Generated JSON must not contain source-status fields. CSV remains paper-oriented and contains paper/code link columns where supported by its current schema.

Adapters return discovered papers without exposing status objects. The pipeline aggregates successful paper lists and does not retain per-source success, failure, count, message, or timing metadata.

This is an intentional breaking change. No deprecated compatibility field or migration alias will remain.

## Data flow and failure handling

1. Build the query plan internally for adapter requests and ranking; do not render it in the final report.
2. Call each configured source independently.
3. If one source fails, catch the source-level exception and continue with remaining sources.
4. Deduplicate, rank, and group all successfully returned papers.
5. Render recommendations and the combined comparison/link table.
6. If every source fails or returns no usable paper, emit an empty report with the normal section structure and a generic limitation statement. Do not expose source names or failure details.

The CLI prints only the generated artifact paths. It does not print per-source status lines or a status heading.

## Documentation and skill resources

Update these surfaces together:

- `SKILL.md`: describe the new fixed output order and remove the transparency/status reporting requirement.
- `references/output-contract.md`: define the combined table and clickable link cells.
- `references/source-policy.md`: retain failure isolation but remove status state definitions and reporting obligations.
- `assets/report-template.md`: match the five-section report structure.
- `README.md`: update example output, feature list, and usage notes.
- `agents/openai.yaml`: regenerate only if its prompt or description conflicts with the revised skill.

## Testing strategy

Use test-driven development for the behavioral change:

1. Add or revise tests first so the current implementation fails on the new contract.
2. Cover model validation and JSON serialization without status fields.
3. Cover pipeline continuation after one adapter raises an exception.
4. Cover CLI output without source-status text.
5. Cover Markdown section order, absence of removed headings, and clickable paper/code links inside the table.
6. Cover missing paper or code URLs as `未找到`.
7. Cover the all-sources-fail/empty-result report.
8. Update end-to-end fixtures and documentation/skill-file assertions.
9. Run the complete test suite before publication.

For skill-level validation, first capture the current Skill's baseline output against a representative request, then rerun an equivalent request after the edits and verify the new report contract.

## Repository and publication workflow

The intended remote is `https://github.com/zhangbodong13-del/academic-paper-discovery`.

Implement on `codex/simplify-report-output`, create focused commits, push the branch, and open a draft pull request. Do not push directly to the default branch. Before publication, reconcile this local source snapshot with the remote repository history; the current workspace repository has no commits or configured remote, and HTTPS/SSH cloning was unavailable during design capture because of TLS/host-key failures.

## Acceptance criteria

- Markdown contains exactly the five requested top-level sections in the specified order.
- The comparison table contains clickable paper and code links and replaces the separate URL section.
- Search assumptions and query text are absent from Markdown; the internal query plan may remain in JSON for reproducibility.
- Source-status information is absent from Markdown, JSON, CLI output, and internal result models.
- No source-status model or result field remains.
- A failed source does not stop other sources.
- README and bundled Skill resources describe the implemented behavior.
- All tests pass.
- Changes are pushed to the approved GitHub repository through a feature branch and draft pull request.
