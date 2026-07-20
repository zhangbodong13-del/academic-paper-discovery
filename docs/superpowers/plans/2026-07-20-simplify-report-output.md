# Simplify Report Output Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove source-status data throughout the application and replace the multi-section Markdown report with recommendation tiers plus one comparison table containing clickable paper and code links.

**Architecture:** Keep `QueryPlan` as internal retrieval/ranking data, but reduce each adapter result to papers only. The pipeline preserves per-source failure isolation by converting a failed future to an empty `AdapterResult`; reporting selects one primary paper URL and one code URL per paper and renders both as Markdown links in the table.

**Tech Stack:** Python 3.11+, Pydantic 2, Typer, httpx, pytest, Markdown, Git/GitHub.

## Global Constraints

- Render Markdown headings in exactly this order: `必读`, `强相关`, `拓展阅读`, `论文对比表`, `局限与下一步`.
- Do not render `检索假设`, `检索式`, `论文网址`, or `数据源检索状态`.
- Remove source-status information from models, adapters, Markdown, JSON, and CLI output with no compatibility alias.
- Keep `QueryPlan` internal and retain `SearchResult.query_plan` in JSON for reproducibility.
- Continue after any single source failure without exposing source names or failure details.
- Render paper/code cells as `[论文](URL)` and `[代码](URL)`; render `未找到` when missing and never guess URLs.
- Update `SKILL.md`, references, template, README, and tests together.
- Publish through `codex/simplify-report-output` and a draft pull request; do not push directly to the default branch.

---

## File Map

- `src/academic_paper_discovery/models.py`: remove the source-status schema and result field.
- `src/academic_paper_discovery/adapters/base.py`: make `AdapterResult` a papers-only boundary.
- `src/academic_paper_discovery/adapters/{crossref,europe_pmc,arxiv,dblp,openalex,semantic_scholar}.py`: stop constructing statuses and return papers or an empty result.
- `src/academic_paper_discovery/pipeline.py`: silently isolate source exceptions and aggregate papers only.
- `src/academic_paper_discovery/reporting.py`: implement the five-section report and combined link table; align CSV columns.
- `src/academic_paper_discovery/cli.py`: remove status imports, fixture statuses, and status console output.
- `tests/`: specify the new model, adapter, pipeline, report, CLI, and end-to-end contracts.
- `SKILL.md`, `references/*.md`, `assets/report-template.md`, `README.md`, `agents/openai.yaml`: synchronize Skill instructions and examples.

### Task 1: Capture the Baseline and Specify the Core Contract

**Files:**
- Modify: `tests/test_models.py`
- Modify: `tests/test_adapter_base.py`
- Modify: `tests/test_pipeline.py`

**Interfaces:**
- Consumes: existing `SearchRequest`, `Paper`, `AdapterResult`, and `SearchPipeline`.
- Produces: tests requiring `AdapterResult(papers: list[Paper])` and `SearchResult` without `source_statuses`.

- [ ] **Step 1: Run a baseline Skill scenario without revised instructions**

Use a fresh subagent with this task-local prompt and the current Skill path:

```text
Use $academic-paper-discovery at C:\Users\Administrator\Documents\论文检索skill to prepare a three-paper report. Include one DOI link, one GitHub code link, and one paper without a code link.
```

Record whether the output contains `检索假设`, `检索式`, a separate `论文网址`, or `数据源检索状态`. Expected baseline failure: the current Skill requires all four unwanted sections and separates links from the table.

- [ ] **Step 2: Write failing model and adapter-result tests**

Add to `tests/test_models.py`:

```python
from academic_paper_discovery.models import SearchResult


def test_search_result_serialization_has_no_source_statuses() -> None:
    request = SearchRequest.with_defaults(topic="robot autofocus", current_year=2026)
    result = SearchResult(request=request)

    assert "source_statuses" not in result.model_dump(mode="json")
```

Replace the status-based test in `tests/test_adapter_base.py` with:

```python
def test_adapter_result_contains_only_papers() -> None:
    result = AdapterResult(papers=[Paper(title="A Study")])

    assert result.papers[0].title == "A Study"
    assert result.model_dump() == {"papers": [{
        **result.papers[0].model_dump(),
    }]}
```

- [ ] **Step 3: Write failing pipeline tests for silent degradation**

Refactor fixtures in `tests/test_pipeline.py` so successful sources return `AdapterResult(papers=[...])`, skipped optional sources return `AdapterResult()`, and failing sources raise. Assert:

```python
def test_pipeline_continues_after_source_failure_without_status_data() -> None:
    request = SearchRequest.with_defaults(
        topic="robot microscope autofocus",
        current_year=2026,
        year_from=2020,
        year_to=2026,
    )
    result = SearchPipeline(
        [GoodSource(), FailingSource(), SkippedSource()],
        current_year=2026,
    ).run(request)

    assert len(result.papers) == 1
    assert result.papers[0].source_names == ["good", "good-secondary"]
    assert "source_statuses" not in result.model_dump(mode="json")
    assert result.query_plan["original_topic"] == "robot microscope autofocus"


def test_pipeline_returns_empty_result_when_all_sources_fail() -> None:
    request = SearchRequest.with_defaults(topic="robot autofocus", current_year=2026)

    result = SearchPipeline([FailingSource()], current_year=2026).run(request)

    assert result.papers == []
    assert result.query_plan["assumptions"] == ["默认年份范围：2022-2026"]
    assert "source_statuses" not in result.model_dump(mode="json")
```

- [ ] **Step 4: Run the focused tests and verify RED**

Run:

```powershell
.\.venv-academic-paper-discovery\Scripts\python.exe -m pytest tests/test_models.py tests/test_adapter_base.py tests/test_pipeline.py -q
```

Expected: failures caused by the required `AdapterResult.status` field and serialized `source_statuses`.

- [ ] **Step 5: Commit the RED tests**

```powershell
git add tests/test_models.py tests/test_adapter_base.py tests/test_pipeline.py
git commit -m "test: specify status-free search results"
```

### Task 2: Remove Status Types and Preserve Pipeline Isolation

**Files:**
- Modify: `src/academic_paper_discovery/models.py`
- Modify: `src/academic_paper_discovery/adapters/base.py`
- Modify: `src/academic_paper_discovery/pipeline.py`

**Interfaces:**
- Consumes: `PaperSource.search(plan, request) -> AdapterResult`.
- Produces: `AdapterResult(papers: list[Paper])`; `SearchResult` fields `request`, `papers`, `query_plan`, and `total_candidates`.

- [ ] **Step 1: Remove `SourceStatus` and simplify `SearchResult`**

Delete `SourceStatus` from `models.py`. Define the result model as:

```python
class SearchResult(BaseModel):
    """完整检索结果。"""

    model_config = ConfigDict(extra="forbid")

    request: SearchRequest
    papers: list[Paper] = Field(default_factory=list)
    query_plan: dict[str, object] = Field(default_factory=dict)
    total_candidates: int = Field(default=0, ge=0)
```

- [ ] **Step 2: Make `AdapterResult` papers-only**

Update `adapters/base.py`:

```python
from academic_paper_discovery.models import Paper, SearchRequest


class AdapterResult(BaseModel):
    """单一来源返回的论文元数据。"""

    model_config = ConfigDict(extra="forbid")

    papers: list[Paper] = Field(default_factory=list)
```

- [ ] **Step 3: Convert failed futures to empty results**

Remove the `SourceStatus` import and `source_statuses=` argument from `pipeline.py`. Use:

```python
for future in as_completed(futures):
    index = futures[future]
    try:
        results[index] = future.result()
    except Exception:  # 每个外部来源都有独立故障边界。
        results[index] = AdapterResult()
```

Return `SearchResult` with only:

```python
return SearchResult(
    request=request,
    papers=ranked[: request.limit],
    query_plan=plan.model_dump(mode="json"),
    total_candidates=len(candidates),
)
```

- [ ] **Step 4: Run focused tests and verify GREEN**

Run the Task 1 command. Expected: all selected tests pass.

- [ ] **Step 5: Commit the core implementation**

```powershell
git add src/academic_paper_discovery/models.py src/academic_paper_discovery/adapters/base.py src/academic_paper_discovery/pipeline.py
git commit -m "refactor: remove source status results"
```

### Task 3: Simplify All Source Adapters

**Files:**
- Modify: `src/academic_paper_discovery/adapters/crossref.py`
- Modify: `src/academic_paper_discovery/adapters/europe_pmc.py`
- Modify: `src/academic_paper_discovery/adapters/arxiv.py`
- Modify: `src/academic_paper_discovery/adapters/dblp.py`
- Modify: `src/academic_paper_discovery/adapters/openalex.py`
- Modify: `src/academic_paper_discovery/adapters/semantic_scholar.py`
- Modify: `tests/adapters/test_crossref.py`
- Modify: `tests/adapters/test_europe_pmc.py`
- Modify: `tests/adapters/test_arxiv.py`
- Modify: `tests/adapters/test_optional_sources.py`

**Interfaces:**
- Consumes: `AdapterResult(papers=...)` from Task 2.
- Produces: paper metadata on success, partial papers after handled request errors, and `AdapterResult()` when an optional source is unavailable.

- [ ] **Step 1: Rewrite adapter tests before implementation**

Remove all `.status` assertions. Use paper-only assertions such as:

```python
assert result.papers[0].title == "Robot Microscope Autofocus"
assert len(result.papers) == 1
```

Change the no-key optional-source test to:

```python
@pytest.mark.parametrize("source_type", [OpenAlexSource, SemanticScholarSource])
def test_optional_source_returns_empty_result_without_key(source_type) -> None:
    request, plan = _request_and_plan()

    result = source_type(client=None, api_key=None).search(plan, request)

    assert result == AdapterResult()
```

- [ ] **Step 2: Verify adapter tests fail**

```powershell
.\.venv-academic-paper-discovery\Scripts\python.exe -m pytest tests/adapters -q
```

Expected: import/constructor failures involving `SourceStatus` or removed `status`.

- [ ] **Step 3: Remove timing/status construction from default adapters**

For Crossref, Europe PMC, arXiv, and DBLP:

- remove `time` and `SourceStatus` imports;
- remove `started` and `_elapsed_ms`;
- keep the existing metadata loops and mappers;
- return `AdapterResult(papers=papers)` on both normal completion and caught request/parse exceptions.

Each `search` method ends with this exact failure/success shape:

```python
        except Exception:
            return AdapterResult(papers=papers)

        return AdapterResult(papers=papers)
```

- [ ] **Step 4: Remove status helpers from optional adapters**

For OpenAlex and Semantic Scholar:

```python
if not self.api_key or self.client is None:
    return AdapterResult()
```

After the existing query loop:

```python
        except Exception:
            return AdapterResult(papers=papers)

        return AdapterResult(papers=papers)
```

Delete `_status_result`, `time`, and `SourceStatus` from both modules.

- [ ] **Step 5: Run adapter tests and verify GREEN**

Run the Step 2 command. Expected: all adapter tests pass.

- [ ] **Step 6: Commit adapter simplification**

```powershell
git add src/academic_paper_discovery/adapters tests/adapters
git commit -m "refactor: return paper-only adapter results"
```

### Task 4: Merge Clickable Paper and Code Links Into the Table

**Files:**
- Modify: `tests/test_reporting.py`
- Modify: `src/academic_paper_discovery/reporting.py`

**Interfaces:**
- Consumes: `Paper.doi` and `Paper.links`.
- Produces: `_primary_paper_url(paper) -> str | None`, `_code_url(paper) -> str | None`, and the five-section Markdown report.

- [ ] **Step 1: Replace reporting tests with the new output contract**

Build `sample_result` without statuses. Add assertions:

```python
def test_markdown_has_only_requested_sections_in_order(sample_result: SearchResult) -> None:
    report = render_markdown(sample_result)
    headings = [
        "## 必读",
        "## 强相关",
        "## 拓展阅读",
        "## 论文对比表",
        "## 局限与下一步",
    ]

    assert [report.index(value) for value in headings] == sorted(
        report.index(value) for value in headings
    )
    for removed in ("## 检索假设", "## 检索式", "## 论文网址", "## 数据源检索状态"):
        assert removed not in report


def test_table_contains_clickable_paper_and_code_links(sample_result: SearchResult) -> None:
    report = render_markdown(sample_result)

    assert "| 论文链接 | 开源代码 |" in report
    assert "[论文](https://doi.org/10.1000/one)" in report
    assert "[代码](https://github.com/example/paper-one)" in report
    assert report.count("未找到") >= 1
```

Update CSV/JSON assertions:

```python
assert rows[0]["论文链接"] == "https://doi.org/10.1000/one"
assert rows[0]["开源代码"] == "https://github.com/example/paper-one"
assert "source_statuses" not in payload
assert "query_plan" in payload
```

- [ ] **Step 2: Run reporting tests and verify RED**

```powershell
.\.venv-academic-paper-discovery\Scripts\python.exe -m pytest tests/test_reporting.py -q
```

Expected: old headings remain, separate URL section remains, and link columns are absent.

- [ ] **Step 3: Implement primary-paper and code URL selection**

In `reporting.py`, remove `SourceStatus`, `STATE_LABELS`, `_render_status`, and `_string_list`. Add:

```python
CODE_HOSTS = ("github.com", "gitlab.com", "codeberg.org")


def _code_url(paper: Paper) -> str | None:
    for link in paper.links:
        kind = link.kind.casefold()
        url = link.url.casefold()
        if "code" in kind or any(host in url for host in CODE_HOSTS):
            return link.url
    return None


def _primary_paper_url(paper: Paper) -> str | None:
    if paper.doi:
        return f"https://doi.org/{paper.doi}"
    code_url = _code_url(paper)
    for link in paper.links:
        if link.url != code_url:
            return link.url
    return None


def _markdown_link(label: str, url: str | None) -> str:
    return f"[{label}]({url})" if url else "未找到"
```

- [ ] **Step 4: Render only five sections and one combined table**

Start the report with the title, metadata-only notice, and tier loops. Render this table header:

```python
lines.extend(
    [
        "",
        "## 论文对比表",
        "",
        "| 序号 | 分组 | 论文 | 作者 | 年份 | 期刊/会议 | 得分 | 推荐理由 | 论文链接 | 开源代码 |",
        "| ---: | --- | --- | --- | ---: | --- | ---: | --- | --- | --- |",
    ]
)
```

Append `_markdown_link("论文", _primary_paper_url(paper))` and `_markdown_link("代码", _code_url(paper))` as the last two cells. Remove the separate URL and source-status blocks. Keep only `## 局限与下一步` after the table.

- [ ] **Step 5: Align CSV columns**

Replace `完整网址` with `论文链接` and `开源代码` in `fieldnames` and each row:

```python
"论文链接": _primary_paper_url(paper) or "未找到",
"开源代码": _code_url(paper) or "未找到",
```

- [ ] **Step 6: Run reporting tests and verify GREEN**

Run the Step 2 command. Expected: all reporting tests pass.

- [ ] **Step 7: Commit reporting changes**

```powershell
git add src/academic_paper_discovery/reporting.py tests/test_reporting.py
git commit -m "feat: merge clickable links into paper table"
```

### Task 5: Remove CLI Status Output and Update End-to-End Behavior

**Files:**
- Modify: `src/academic_paper_discovery/cli.py`
- Modify: `tests/test_cli.py`
- Modify: `tests/test_end_to_end.py`
- Modify: `tests/test_adapter_base.py`

**Interfaces:**
- Consumes: status-free `SearchResult` and `AdapterResult`.
- Produces: CLI output listing only generated files; offline fixture still demonstrates partial failure tolerance.

- [ ] **Step 1: Write failing CLI and end-to-end assertions**

In `tests/test_cli.py`, keep the offline fixture and assert:

```python
assert "数据源实际状态" not in result.stdout
assert "offline-fixture：成功" not in result.stdout
assert "offline-failure：失败" not in result.stdout
report = (output_path / "report.md").read_text(encoding="utf-8")
assert "## 论文网址" not in report
assert "## 数据源检索状态" not in report
assert "[论文](https://doi.org/10.0000/offline-demo)" in report
```

In `tests/test_end_to_end.py`, remove status assertions and add:

```python
payload = json.loads((output / "report.json").read_text(encoding="utf-8"))
assert "source_statuses" not in payload
assert "## 论文网址" not in report
assert "## 数据源检索状态" not in report
assert "| 论文链接 | 开源代码 |" in report
```

- [ ] **Step 2: Verify RED**

```powershell
.\.venv-academic-paper-discovery\Scripts\python.exe -m pytest tests/test_cli.py tests/test_end_to_end.py -q
```

Expected: old CLI status lines and old Markdown sections cause failures.

- [ ] **Step 3: Simplify CLI imports, output, and fixtures**

Remove `SourceStatus` from imports. Delete:

```python
typer.echo("数据源实际状态：")
state_labels = {"success": "成功", "failed": "失败", "skipped": "跳过"}
for status in result.source_statuses:
    details = status.message or f"{status.result_count} 篇"
    typer.echo(f"- {status.source}：{state_labels[status.state]}（{details}）")
```

Return the offline success fixture as `AdapterResult(papers=[paper])`. Keep `_OfflineFailureSource.search` raising `RuntimeError` so pipeline isolation remains exercised.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run the Step 2 command. Expected: both test modules pass.

- [ ] **Step 5: Commit CLI and end-to-end changes**

```powershell
git add src/academic_paper_discovery/cli.py tests/test_cli.py tests/test_end_to_end.py tests/test_adapter_base.py
git commit -m "refactor: remove source status CLI output"
```

### Task 6: Synchronize Skill Instructions, Template, and README

**Files:**
- Modify: `SKILL.md`
- Modify: `references/output-contract.md`
- Modify: `references/source-policy.md`
- Modify: `assets/report-template.md`
- Modify: `README.md`
- Modify: `agents/openai.yaml` only if its prompt conflicts
- Modify: `tests/test_skill_files.py`

**Interfaces:**
- Consumes: the implemented five-section output contract.
- Produces: discoverable Skill instructions and user documentation matching runtime behavior.

- [ ] **Step 1: Write failing documentation assertions**

Update `tests/test_skill_files.py` to assert:

```python
assert "论文链接" in output_contract
assert "开源代码" in output_contract
assert "[论文](URL)" in output_contract
assert "[代码](URL)" in output_contract
for removed in ("## 检索假设", "## 检索式", "## 论文网址", "## 数据源检索状态"):
    assert removed not in report_template
assert "论文网址必须紧跟对比表" not in skill_text
assert "数据源检索状态" not in readme_text
```

- [ ] **Step 2: Verify RED**

```powershell
.\.venv-academic-paper-discovery\Scripts\python.exe -m pytest tests/test_skill_files.py -q
```

Expected: current documentation still requires removed sections.

- [ ] **Step 3: Rewrite the Skill output contract**

In `SKILL.md`, replace the old nine-section list with:

```markdown
固定按以下顺序输出：

1. 必读
2. 强相关
3. 拓展阅读
4. 论文对比表
5. 局限与下一步

论文对比表必须包含可点击的 `[论文](URL)` 与 `[代码](URL)` 单元格；没有已发现链接时写“未找到”。不要单独生成检索假设、检索式、论文网址或数据源状态章节。
```

Remove requirements to expose status outcomes. Retain the metadata-only/no-PDF and non-exhaustiveness constraints.

- [ ] **Step 4: Update references, template, and README**

Make `assets/report-template.md` contain only:

```markdown
# 论文检索报告：{研究主题}

> 只检索论文元数据和公开网页链接，不下载论文正文或 PDF。

## 必读

## 强相关

## 拓展阅读

## 论文对比表

| 序号 | 分组 | 论文 | 作者 | 年份 | 期刊/会议 | 得分 | 推荐理由 | 论文链接 | 开源代码 |
| ---: | --- | --- | --- | ---: | --- | ---: | --- | --- | --- |

## 局限与下一步
```

Update `references/output-contract.md` and README examples to use clickable table cells. In `references/source-policy.md`, retain the instruction to continue after a failure but delete the success/failed/skipped state definitions and reporting rules.

- [ ] **Step 5: Validate `agents/openai.yaml`**

Search it for removed terms:

```powershell
rg -n "检索假设|检索式|论文网址|数据源检索状态|source status" agents/openai.yaml
```

Expected: no matches. If matches exist, regenerate it with the Skill Creator generator using the existing display name and a default prompt that asks for tiered recommendations plus one clickable comparison table.

- [ ] **Step 6: Run documentation tests and Skill validation**

```powershell
.\.venv-academic-paper-discovery\Scripts\python.exe -m pytest tests/test_skill_files.py -q
python "C:\Users\Administrator\.codex\skills\.system\skill-creator\scripts\quick_validate.py" "."
```

Expected: tests pass and validator reports a valid Skill.

- [ ] **Step 7: Commit documentation changes**

```powershell
git add SKILL.md README.md references assets agents/openai.yaml tests/test_skill_files.py
git commit -m "docs: simplify paper discovery report contract"
```

### Task 7: Full Verification, Forward Test, Deployment, and GitHub Publication

**Files:**
- Verify: all project files
- Sync after verification: `C:\Users\Administrator\.codex\skills\academic-paper-discovery`
- Publish: `https://github.com/zhangbodong13-del/academic-paper-discovery`

**Interfaces:**
- Consumes: all prior task outputs.
- Produces: verified installed Skill, pushed feature branch, and draft pull request.

- [ ] **Step 1: Run the complete automated suite**

```powershell
.\.venv-academic-paper-discovery\Scripts\python.exe -m pytest -q
```

Expected: all tests pass with zero failures.

- [ ] **Step 2: Scan for forbidden source-status and report-section remnants**

```powershell
rg -n "SourceStatus|source_statuses|数据源检索状态|## 论文网址|## 检索假设|## 检索式" src tests SKILL.md README.md references assets
```

Expected: no runtime/documentation matches. Test assertions that explicitly verify absence may match and must be manually confirmed.

- [ ] **Step 3: Forward-test the revised Skill**

Use a fresh subagent with:

```text
Use $academic-paper-discovery at C:\Users\Administrator\Documents\论文检索skill to prepare a three-paper report. Include one DOI link, one GitHub code link, and one paper without a code link.
```

Verify the output has only the five approved sections, paper/code links are clickable inside the table, missing code is `未找到`, and no source status appears.

- [ ] **Step 4: Sync the verified Skill into the installed Skill directory**

After explicit filesystem approval, copy only project/Skill files and exclude `.git`, virtual environments, generated search reports, and test caches. Re-run `quick_validate.py` against `C:\Users\Administrator\.codex\skills\academic-paper-discovery`.

- [ ] **Step 5: Reconcile with the GitHub remote history**

Retry a clean clone into a new directory:

```powershell
git -c http.sslBackend=openssl clone https://github.com/zhangbodong13-del/academic-paper-discovery.git academic-paper-discovery-publish
```

Expected: clone succeeds. Create `codex/simplify-report-output` in that clone, copy the verified changed project files, and rerun the full test suite there. Do not overwrite the remote default branch or push unrelated local root history.

- [ ] **Step 6: Publish intentionally**

Use **REQUIRED SUB-SKILL:** `github:yeet`. Confirm the diff contains only source, tests, Skill resources, README, specification, and plan. Commit any transplanted changes with the focused messages from earlier tasks, push `codex/simplify-report-output`, and open a draft PR.

- [ ] **Step 7: Final verification before completion**

Use **REQUIRED SUB-SKILL:** `superpowers:verification-before-completion`. Confirm the pushed branch SHA, draft PR URL, full test result, installed Skill validation, and absence of generated reports or virtual environments from the Git diff.
