# Academic Paper Discovery Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reusable Codex Skill that performs metadata-only, multi-source academic paper discovery and returns a structured B+C report with a numbered URL list immediately after the comparison table.

**Architecture:** Use a Python package for deterministic request validation, source adapters, metadata normalization, deduplication, ranking, caching, and report rendering. Use `SKILL.md` to let Codex expand multilingual queries, invoke the package, supplement venue-specific web evidence, and explain why papers are worth reading. Keep network adapters isolated behind one protocol so source failures degrade independently.

**Tech Stack:** Python 3.11+, httpx, pydantic, typer, PyYAML, rapidfuzz, pytest, respx, Markdown, CSV, JSON.

## Global Constraints

- Keep the repository, `.venv`, pip cache, search cache, and generated outputs under `D:\academic-paper-discovery`.
- Keep the machine identifier `academic-paper-discovery`, but make all user-facing content Chinese by default: display metadata, `SKILL.md` body, README, CLI help, report headings, table fields, statuses, and errors.
- Never download papers, PDFs, supplementary materials, or full-text datasets; retrieve metadata and links only.
- Core operation must work without API keys through Crossref, arXiv, Europe PMC, and DBLP.
- Enable OpenAlex and Semantic Scholar only when their environment variables are available; absence of a key is a recorded skip, not an error.
- Describe coverage as “multi-source broad-coverage search,” never as guaranteed exhaustive web search.
- Render B+C output in this exact order: assumptions, query plan, must-read, strongly relevant, exploratory, comparison table, numbered URL list, source coverage, limitations.
- Put the numbered URL list immediately after the table and keep its numbering identical to the table.
- Do not invent DOI values, abstracts, citation counts, code URLs, or venue metadata; mark missing information as unverified or not found.
- Develop production code with RED-GREEN-REFACTOR and commit each independently testable task.
- Keep all secrets, caches, environments, and generated results out of Git.

## Verified API Baseline (2026-07-20)

- Crossref REST: `https://api.crossref.org/works`; public without sign-up, with optional `mailto` polite-pool parameter.
- arXiv: `https://export.arxiv.org/api/query`; Atom XML, `search_query`, `start`, `max_results`, and a three-second delay between repeated calls.
- Europe PMC: `https://www.ebi.ac.uk/europepmc/webservices/rest/search`; JSON with `query`, `resultType=core`, `pageSize`, and `cursorMark`.
- DBLP: `https://dblp.org/search/publ/api`; JSON with `q`, `h`, `f`, and `format=json`.
- OpenAlex: `https://api.openalex.org/works`; current API requires `OPENALEX_API_KEY`.
- Semantic Scholar: `https://api.semanticscholar.org/graph/v1/paper/search`; optional `SEMANTIC_SCHOLAR_API_KEY` in `x-api-key`.
- OpenReview: treat as Codex web supplementation in v1 because API v2 and legacy v1 differ and documented clients expect credentials for normal programmatic access.

---

### Task 1: Bootstrap the Skill Package and D-Drive Runtime

**Files:**
- Create: `SKILL.md` (generated placeholder only; authored in Task 12)
- Create: `agents/openai.yaml`
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `.env.example`
- Create: `README.md`
- Create: `src/academic_paper_discovery/__init__.py`
- Create: `tests/test_package.py`

**Interfaces:**
- Produces: installable package `academic_paper_discovery` and console command `academic-paper-discovery`.
- Produces: local runtime at `D:\academic-paper-discovery\.venv`.

- [ ] **Step 1: Run the required Skill initializer in an isolated bootstrap directory**

```powershell
python <Codex 技能目录>\.system\skill-creator\scripts\init_skill.py academic-paper-discovery `
  --path D:\academic-paper-discovery\.skill-init `
  --resources scripts,references,assets `
  --interface 'display_name=学术论文发现' `
  --interface 'short_description=跨来源查找、筛选并排序研究论文' `
  --interface 'default_prompt=使用 $academic-paper-discovery 查找与我的研究主题最相关的论文。'
```

Expected: `.skill-init\academic-paper-discovery` contains generated `SKILL.md`, `agents/openai.yaml`, and requested resource folders. Copy the generated `SKILL.md`, `agents`, `scripts`, `references`, and `assets` into the repository root, then remove only the temporary `.skill-init` directory.

- [ ] **Step 2: Write the failing package smoke test**

```python
from typer.testing import CliRunner

from academic_paper_discovery.cli import app


def test_cli_reports_version() -> None:
    result = CliRunner().invoke(app, ["version"])
    assert result.exit_code == 0
    assert result.stdout.strip() == "academic-paper-discovery 0.1.0"
```

- [ ] **Step 3: Run the test and verify RED**

```powershell
python -m pytest tests/test_package.py -v
```

Expected: FAIL because `academic_paper_discovery.cli` does not exist.

- [ ] **Step 4: Add minimal package and project metadata**

`pyproject.toml` must define Python `>=3.11`, runtime dependencies `httpx`, `pydantic`, `typer`, `PyYAML`, and `rapidfuzz`, dev dependencies `pytest`, `pytest-cov`, and `respx`, package discovery under `src`, and:

```toml
[project.scripts]
academic-paper-discovery = "academic_paper_discovery.cli:app"
```

Create `src/academic_paper_discovery/cli.py`:

```python
import typer

from academic_paper_discovery import __version__

app = typer.Typer(no_args_is_help=True)


@app.command()
def version() -> None:
    typer.echo(f"academic-paper-discovery {__version__}")
```

Create `src/academic_paper_discovery/__init__.py` with `__version__ = "0.1.0"`.

- [ ] **Step 5: Add local-only paths and create the environment**

`.gitignore` must include `.venv/`, `.cache/`, `outputs/`, `.env`, `__pycache__/`, `.pytest_cache/`, `.coverage`, `*.egg-info/`, and build artifacts. `.env.example` must list empty `CROSSREF_MAILTO`, `OPENALEX_API_KEY`, and `SEMANTIC_SCHOLAR_API_KEY` values.

```powershell
$env:PIP_CACHE_DIR='D:\academic-paper-discovery\.cache\pip'
python -m venv D:\academic-paper-discovery\.venv
D:\academic-paper-discovery\.venv\Scripts\python.exe -m pip install -e 'D:\academic-paper-discovery[dev]'
D:\academic-paper-discovery\.venv\Scripts\python.exe -m pytest tests/test_package.py -v
```

Expected: PASS and all downloaded Python packages reside in `.venv` or `.cache\pip` on D drive.

- [ ] **Step 6: Commit**

```powershell
git add SKILL.md agents pyproject.toml .gitignore .env.example README.md src tests scripts references assets
git commit -m "build: scaffold academic paper discovery skill"
```

---

### Task 2: Define Search Requests, Papers, and Source Status

**Files:**
- Create: `src/academic_paper_discovery/models.py`
- Create: `tests/test_models.py`
- Create: `config/defaults.yaml`

**Interfaces:**
- Produces: `SearchRequest`, `Paper`, `PaperLink`, `SourceStatus`, `SearchResult`, and `RecommendationTier`.
- Consumes later: all adapters, ranking, pipeline, reporting, and CLI.

- [ ] **Step 1: Write failing model tests**

Test that `SearchRequest(topic="robot autofocus")` applies `limit=20`, a five-year inclusive default window ending in the injected current year, and records `year_range_was_defaulted=True`. Test that explicit invalid ranges and limits above 100 raise `ValidationError`. Test that `Paper` normalizes DOI prefixes and rejects an empty title.

```python
def test_search_request_exposes_default_year_assumption() -> None:
    request = SearchRequest.with_defaults(topic="robot autofocus", current_year=2026)
    assert (request.year_from, request.year_to) == (2022, 2026)
    assert request.limit == 20
    assert request.year_range_was_defaulted is True


def test_paper_normalizes_doi() -> None:
    paper = Paper(title="A Study", doi="https://doi.org/10.1000/ABC")
    assert paper.doi == "10.1000/abc"
```

- [ ] **Step 2: Run and verify RED**

```powershell
.venv\Scripts\python.exe -m pytest tests/test_models.py -v
```

Expected: FAIL because the model classes do not exist.

- [ ] **Step 3: Implement minimal Pydantic models**

Use frozen value models where practical. `Paper` fields must include `title`, `authors`, `year`, `venue`, `abstract`, `doi`, `arxiv_id`, `citation_count`, `publication_type`, `is_formal`, `links`, `source_names`, `raw_ids`, `score`, `tier`, `why_read`, and `warnings`. `PaperLink` must include `kind`, `url`, `source`, and `verified`. `SourceStatus` must include `source`, `state` (`success`, `failed`, `skipped`), `result_count`, `message`, and `elapsed_ms`.

Implement `SearchRequest.with_defaults(topic, current_year, **overrides)` so the year assumption is deterministic in tests. Store default values in `config/defaults.yaml` and keep the model fallback identical.

- [ ] **Step 4: Run and verify GREEN**

```powershell
.venv\Scripts\python.exe -m pytest tests/test_models.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add config/defaults.yaml src/academic_paper_discovery/models.py tests/test_models.py
git commit -m "feat: define paper search models"
```

---

### Task 3: Build an Auditable Query Plan

**Files:**
- Create: `src/academic_paper_discovery/query_plan.py`
- Create: `tests/test_query_plan.py`

**Interfaces:**
- Produces: `QueryPlan` and `build_query_plan(request: SearchRequest) -> QueryPlan`.
- Query plan contains original topic, supplied Chinese/English expansions, venue queries, exclusions, year range, and explicit assumptions.

- [ ] **Step 1: Write failing query-plan tests**

```python
def test_plan_keeps_multilingual_terms_and_assumptions() -> None:
    request = SearchRequest.with_defaults(
        topic="双目显微手术器械位姿估计",
        current_year=2026,
        expanded_queries=["stereo microscopy", "surgical instrument pose estimation"],
        target_venues=["MICCAI", "TMI"],
        exclusions=["education"],
    )
    plan = build_query_plan(request)
    assert plan.queries[0] == request.topic
    assert "stereo microscopy" in plan.queries
    assert plan.venue_queries == ["MICCAI", "TMI"]
    assert "Default year range: 2022-2026" in plan.assumptions
```

Also test stable order and duplicate removal without losing the original topic.

- [ ] **Step 2: Run and verify RED**

```powershell
.venv\Scripts\python.exe -m pytest tests/test_query_plan.py -v
```

Expected: FAIL because `build_query_plan` is missing.

- [ ] **Step 3: Implement deterministic planning**

Do not add an online translation model. Accept semantic expansions supplied by Codex, normalize whitespace, remove case-insensitive duplicates, append venue-constrained variants within the configured query cap, and keep exclusions as auditable fields. The Skill, not Python, is responsible for generating expert multilingual synonyms.

- [ ] **Step 4: Run and verify GREEN**

```powershell
.venv\Scripts\python.exe -m pytest tests/test_query_plan.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add src/academic_paper_discovery/query_plan.py tests/test_query_plan.py
git commit -m "feat: add auditable query planning"
```

---

### Task 4: Define Adapter Contracts, HTTP Policy, and Metadata Cache

**Files:**
- Create: `src/academic_paper_discovery/adapters/base.py`
- Create: `src/academic_paper_discovery/http.py`
- Create: `src/academic_paper_discovery/cache.py`
- Create: `tests/test_adapter_base.py`
- Create: `tests/test_cache.py`

**Interfaces:**
- Produces: `PaperSource.search(plan, request) -> AdapterResult` protocol.
- Produces: `MetadataHttpClient.get(url, params, headers) -> bytes` with timeout and bounded retries.
- Produces: `MetadataCache.get(key)` and `put(key, payload, ttl_seconds)` under `.cache/search`.

- [ ] **Step 1: Write failing contract and cache tests**

Test deterministic cache keys from source plus sorted parameters, valid-cache reuse, expired-cache miss, corrupt-entry deletion, and that binary/PDF content types are rejected before storage.

```python
def test_cache_refuses_pdf_payload(tmp_path: Path) -> None:
    cache = MetadataCache(tmp_path)
    with pytest.raises(ValueError, match="metadata-only"):
        cache.put("key", b"%PDF", content_type="application/pdf", ttl_seconds=60)
```

- [ ] **Step 2: Run and verify RED**

```powershell
.venv\Scripts\python.exe -m pytest tests/test_adapter_base.py tests/test_cache.py -v
```

Expected: FAIL because contracts and cache do not exist.

- [ ] **Step 3: Implement contracts and safe metadata transport**

Create `AdapterResult(papers, status)`. Retry only timeouts, HTTP 429, and 5xx responses, at most two retries with injectable backoff. Enforce a maximum metadata response size, require JSON/XML/Atom/text content types, and never follow links labeled as PDF. Cache only successful metadata responses.

- [ ] **Step 4: Run and verify GREEN**

```powershell
.venv\Scripts\python.exe -m pytest tests/test_adapter_base.py tests/test_cache.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add src/academic_paper_discovery/adapters src/academic_paper_discovery/http.py src/academic_paper_discovery/cache.py tests/test_adapter_base.py tests/test_cache.py
git commit -m "feat: add metadata adapter infrastructure"
```

---

### Task 5: Implement Crossref and Europe PMC Adapters

**Files:**
- Create: `src/academic_paper_discovery/adapters/crossref.py`
- Create: `src/academic_paper_discovery/adapters/europe_pmc.py`
- Create: `tests/adapters/test_crossref.py`
- Create: `tests/adapters/test_europe_pmc.py`

**Interfaces:**
- Produces: `CrossrefSource.search(plan, request) -> AdapterResult`.
- Produces: `EuropePmcSource.search(plan, request) -> AdapterResult`.

- [ ] **Step 1: Write failing Crossref mapping tests**

Use `respx` with a minimal official response fixture. Assert `query.bibliographic`, `filter=from-pub-date:YYYY-01-01,until-pub-date:YYYY-12-31`, `rows`, and optional `mailto`. Assert DOI, title, authors, container title, published year, abstract, URL, and citation count map to `Paper` without downloading linked content.

- [ ] **Step 2: Run Crossref test and verify RED**

```powershell
.venv\Scripts\python.exe -m pytest tests/adapters/test_crossref.py -v
```

Expected: FAIL because `CrossrefSource` is missing.

- [ ] **Step 3: Implement Crossref and verify GREEN**

Use `https://api.crossref.org/works`, a descriptive `User-Agent`, and `CROSSREF_MAILTO` only when present. Convert JATS abstract markup to plain text without fetching full text.

```powershell
.venv\Scripts\python.exe -m pytest tests/adapters/test_crossref.py -v
```

Expected: PASS.

- [ ] **Step 4: Write failing Europe PMC tests**

Assert use of `/search` with `format=json`, `resultType=core`, bounded `pageSize`, year constraints in the query, and mapping of `title`, `authorList`, `pubYear`, `journalTitle`, `doi`, `pmid`, `citedByCount`, and abstract. Assert pagination stops at the configured source limit.

- [ ] **Step 5: Implement Europe PMC and verify GREEN**

```powershell
.venv\Scripts\python.exe -m pytest tests/adapters/test_europe_pmc.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add src/academic_paper_discovery/adapters/crossref.py src/academic_paper_discovery/adapters/europe_pmc.py tests/adapters
git commit -m "feat: add Crossref and Europe PMC sources"
```

---

### Task 6: Implement arXiv and DBLP Adapters

**Files:**
- Create: `src/academic_paper_discovery/adapters/arxiv.py`
- Create: `src/academic_paper_discovery/adapters/dblp.py`
- Create: `tests/adapters/test_arxiv.py`
- Create: `tests/adapters/test_dblp.py`

**Interfaces:**
- Produces: `ArxivSource.search(plan, request) -> AdapterResult`.
- Produces: `DblpSource.search(plan, request) -> AdapterResult`.

- [ ] **Step 1: Write failing arXiv Atom tests**

Fixture entries must include `id`, `title`, `summary`, `published`, authors, categories, optional DOI, journal reference, abstract link, and PDF link. Assert only the abstract link is saved; the PDF link is ignored. Assert an injected throttle waits three seconds before repeated live calls but waits zero in unit tests.

- [ ] **Step 2: Implement arXiv and verify GREEN**

Build `search_query` from plan terms, use `start`, `max_results`, `sortBy=relevance`, and parse Atom with the Python standard library. Never request any URL returned in an entry.

```powershell
.venv\Scripts\python.exe -m pytest tests/adapters/test_arxiv.py -v
```

Expected: PASS.

- [ ] **Step 3: Write failing DBLP JSON tests**

Assert `q`, `format=json`, `h`, `f`, and `c=0`. Map single or list author shapes, year, venue, type, DOI/URL, and electronic edition links. Preserve metadata links without opening them.

- [ ] **Step 4: Implement DBLP and verify GREEN**

```powershell
.venv\Scripts\python.exe -m pytest tests/adapters/test_dblp.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add src/academic_paper_discovery/adapters/arxiv.py src/academic_paper_discovery/adapters/dblp.py tests/adapters
git commit -m "feat: add arXiv and DBLP sources"
```

---

### Task 7: Add Optional OpenAlex and Semantic Scholar Enhancements

**Files:**
- Create: `src/academic_paper_discovery/adapters/openalex.py`
- Create: `src/academic_paper_discovery/adapters/semantic_scholar.py`
- Create: `tests/adapters/test_optional_sources.py`

**Interfaces:**
- Produces: optional sources that return `SourceStatus(state="skipped")` when their keys are absent.
- Reads: `OPENALEX_API_KEY`, `SEMANTIC_SCHOLAR_API_KEY`.

- [ ] **Step 1: Write failing missing-key tests**

```python
@pytest.mark.parametrize("source_type", [OpenAlexSource, SemanticScholarSource])
def test_optional_source_skips_without_key(source_type) -> None:
    result = source_type(api_key=None).search(plan, request)
    assert result.papers == []
    assert result.status.state == "skipped"
    assert "API key" in result.status.message
```

- [ ] **Step 2: Run and verify RED**

```powershell
.venv\Scripts\python.exe -m pytest tests/adapters/test_optional_sources.py -v
```

Expected: FAIL because optional adapters do not exist.

- [ ] **Step 3: Implement key-gated API calls**

OpenAlex sends `api_key` and searches works with bounded `per-page`; reconstruct its inverted-index abstract. Semantic Scholar sends `x-api-key`, requests only required fields, and stores `openAccessPdf.url` as a metadata link without downloading it. Both handle 401/403 as failed status and never stop the full pipeline.

- [ ] **Step 4: Run and verify GREEN**

```powershell
.venv\Scripts\python.exe -m pytest tests/adapters/test_optional_sources.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add src/academic_paper_discovery/adapters/openalex.py src/academic_paper_discovery/adapters/semantic_scholar.py tests/adapters/test_optional_sources.py
git commit -m "feat: add optional enriched paper sources"
```

---

### Task 8: Add Venue Registry and Version-Aware Deduplication

**Files:**
- Create: `config/venues.yaml`
- Create: `src/academic_paper_discovery/venues.py`
- Create: `src/academic_paper_discovery/deduplication.py`
- Create: `tests/test_venues.py`
- Create: `tests/test_deduplication.py`

**Interfaces:**
- Produces: `VenueRegistry.match(name, issn, url) -> VenueMatch | None`.
- Produces: `deduplicate(papers: list[Paper]) -> list[Paper]`.

- [ ] **Step 1: Write failing venue tests**

Cover Nature, Science, Nature Portfolio and Science family metadata plus CVPR, ICCV, ECCV, ICML, NeurIPS/NIPS, ICLR, T-RO/TRO, RA-L, ICRA, IROS, MICCAI, and TMI. Test canonical name, aliases, family, official domains, and known ISSNs without treating `tier_label` as an absolute quality claim.

- [ ] **Step 2: Implement venue registry and verify GREEN**

```powershell
.venv\Scripts\python.exe -m pytest tests/test_venues.py -v
```

Expected: PASS.

- [ ] **Step 3: Write failing deduplication tests**

Cover DOI exact match, arXiv ID match, normalized title match, and fuzzy title plus shared author plus adjacent year. Assert formal publication metadata wins while preprint and project links remain, all source names merge, and low-confidence candidates remain separate with warnings.

- [ ] **Step 4: Implement deduplication and verify GREEN**

Use Unicode normalization, punctuation removal, whitespace collapse, `rapidfuzz.fuzz.token_set_ratio`, author surname intersection, and explicit thresholds stored in `config/defaults.yaml`.

```powershell
.venv\Scripts\python.exe -m pytest tests/test_deduplication.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add config/venues.yaml config/defaults.yaml src/academic_paper_discovery/venues.py src/academic_paper_discovery/deduplication.py tests/test_venues.py tests/test_deduplication.py
git commit -m "feat: recognize venues and merge paper versions"
```

---

### Task 9: Implement Explainable Ranking and Recommendation Tiers

**Files:**
- Create: `src/academic_paper_discovery/ranking.py`
- Create: `tests/test_ranking.py`
- Create: `references/ranking-policy.md`

**Interfaces:**
- Produces: `rank_papers(papers, request, plan, current_year) -> list[Paper]`.
- Produces: component scores and `why_read` evidence for every returned paper.

- [ ] **Step 1: Write failing ranking tests**

Test title/abstract term match, task and method overlap, target venue bonus, multi-source bonus, formal-version bonus, optional code-link bonus, review preference, and citation age normalization. Assert a 2026 paper with 10 citations can outrank an older weakly relevant paper with 1,000 citations. Test deterministic tie-breaking by normalized title.

- [ ] **Step 2: Run and verify RED**

```powershell
.venv\Scripts\python.exe -m pytest tests/test_ranking.py -v
```

Expected: FAIL because ranking is missing.

- [ ] **Step 3: Implement weighted, inspectable scoring**

Keep weights in `config/defaults.yaml`. Store the component breakdown on each paper. Assign `must-read`, `strong`, and `exploratory` by explicit thresholds plus rank caps. Generate `why_read` only from matched, available fields and never infer unverified experimental outcomes.

- [ ] **Step 4: Run and verify GREEN**

```powershell
.venv\Scripts\python.exe -m pytest tests/test_ranking.py -v
```

Expected: PASS.

- [ ] **Step 5: Document the policy and commit**

`references/ranking-policy.md` must explain features, age normalization, limitations, and why citation count is not an absolute quality measure.

```powershell
git add config/defaults.yaml src/academic_paper_discovery/ranking.py tests/test_ranking.py references/ranking-policy.md
git commit -m "feat: rank papers with explainable evidence"
```

---

### Task 10: Orchestrate Partial-Failure Search Pipeline

**Files:**
- Create: `src/academic_paper_discovery/pipeline.py`
- Create: `tests/test_pipeline.py`

**Interfaces:**
- Produces: `SearchPipeline.run(request) -> SearchResult`.
- Consumes: query planning, adapters, cache, deduplication, venue registry, ranking.

- [ ] **Step 1: Write failing pipeline tests**

Inject fake sources: one success, one exception, one skipped, and one duplicate result. Assert the pipeline continues, returns deduplicated/ranked papers, records all statuses, caps each source and total candidates, and returns an auditable empty result when every source fails.

```python
def test_pipeline_degrades_when_one_source_fails() -> None:
    result = SearchPipeline([good_source, failing_source], current_year=2026).run(request)
    assert [status.state for status in result.source_statuses] == ["success", "failed"]
    assert result.papers
```

- [ ] **Step 2: Run and verify RED**

```powershell
.venv\Scripts\python.exe -m pytest tests/test_pipeline.py -v
```

Expected: FAIL because pipeline is missing.

- [ ] **Step 3: Implement orchestration**

Use bounded concurrent requests where source policy allows, catch exceptions at each adapter boundary, preserve deterministic status ordering, deduplicate before ranking, and apply the user limit only after ranking. Do not hide total candidate counts or failed sources.

- [ ] **Step 4: Run and verify GREEN**

```powershell
.venv\Scripts\python.exe -m pytest tests/test_pipeline.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add src/academic_paper_discovery/pipeline.py tests/test_pipeline.py
git commit -m "feat: orchestrate resilient multi-source search"
```

---

### Task 11: Render B+C Reports, Tables, and Post-Table URLs

**Files:**
- Create: `src/academic_paper_discovery/reporting.py`
- Create: `assets/report-template.md`
- Create: `references/output-contract.md`
- Create: `tests/test_reporting.py`

**Interfaces:**
- Produces: `render_markdown(result) -> str`, `write_csv(result, path)`, and `write_json(result, path)`.

- [ ] **Step 1: Write failing output-contract tests**

Create a result with three papers across all recommendation tiers. Assert section order, one table row per paper, stable numbering, and that `## 论文网址` begins after the table. Assert each URL line starts with the same paper number and includes all verified metadata links. Assert missing fields render as `未核验` or `未找到`, not fabricated values.

```python
def test_urls_follow_table_with_matching_numbers(sample_result) -> None:
    report = render_markdown(sample_result)
    assert report.index("| 序号 |") < report.index("## 论文网址")
    assert "1. **Paper One**" in report
    assert "2. **Paper Two**" in report
```

- [ ] **Step 2: Run and verify RED**

```powershell
.venv\Scripts\python.exe -m pytest tests/test_reporting.py -v
```

Expected: FAIL because report rendering is missing.

- [ ] **Step 3: Implement Markdown, CSV, and JSON outputs**

Escape Markdown table characters, keep full URLs out of table cells when they harm readability, place canonical short links in the table, then list complete URLs after the table. Include assumptions, query terms, actual source states, limitations, and next-search suggestions.

- [ ] **Step 4: Run and verify GREEN**

```powershell
.venv\Scripts\python.exe -m pytest tests/test_reporting.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add src/academic_paper_discovery/reporting.py assets/report-template.md references/output-contract.md tests/test_reporting.py
git commit -m "feat: render structured reports and paper URLs"
```

---

### Task 12: Complete CLI, README, and Skill Instructions

**Files:**
- Modify: `src/academic_paper_discovery/cli.py`
- Modify: `README.md`
- Modify: `SKILL.md`
- Modify: `agents/openai.yaml`
- Create: `references/source-policy.md`
- Create: `tests/test_cli.py`
- Create: `tests/test_skill_files.py`

**Interfaces:**
- Produces: `academic-paper-discovery search --request request.json --output outputs/run-name`.
- Produces: Codex trigger `$academic-paper-discovery` and implicit natural-language discovery triggers.

- [ ] **Step 1: Write failing CLI and documentation tests**

Test offline CLI execution with injected fixture sources, creation of `.md`, `.csv`, and `.json`, nonzero exit only for invalid input or impossible output writes, and zero exit for partial source failure. Assert README contains the exact user-approved prompt and the no-download statement. Assert CLI help, report headings, statuses, and validation errors are Chinese by default. Assert SKILL frontmatter contains only `name` and `description`, starts its description with `Use when`, and includes these trigger concepts: literature search, must-read papers, venue-focused search, research landscape, and structured paper table.

- [ ] **Step 2: Run and verify RED**

```powershell
.venv\Scripts\python.exe -m pytest tests/test_cli.py tests/test_skill_files.py -v
```

Expected: FAIL because the search command and final documentation are absent.

- [ ] **Step 3: Implement the CLI search command**

Read UTF-8 JSON into `SearchRequest`, construct configured sources, run the pipeline, write all three formats under the requested D-drive output directory, and print paths plus a source status summary. Add `--offline-fixture` only for tests and demos; it must never masquerade as live results.

- [ ] **Step 4: Write README with the exact approved prompt**

Place this verbatim in a prominent “快速使用” section:

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

Add one concrete example and state clearly that the Skill returns metadata and links but does not download papers or PDFs.

- [ ] **Step 5: Author final SKILL.md and agent metadata**

Use exactly this frontmatter:

```yaml
---
name: academic-paper-discovery
description: Use when a user wants to discover, search, screen, deduplicate, rank, or compare academic papers for a research topic, including literature searches, must-read paper recommendations, venue-focused searches, research landscape reviews, and structured paper tables.
---
```

The Chinese body must instruct Codex to clarify missing high-impact constraints only when necessary, disclose default years, generate multilingual expansions, run the script, use official web sources for venue-specific supplementation, never claim exhaustive coverage, never download papers, preserve source failure reporting, and render the exact B+C order in Chinese by default. Keep detailed source and output policies in one-level references rather than duplicating them.

`agents/openai.yaml` must quote all string values and set:

```yaml
interface:
  display_name: "学术论文发现"
  short_description: "跨来源查找、筛选并排序研究论文"
  default_prompt: "使用 $academic-paper-discovery 查找与我的研究主题最相关的论文。"
policy:
  allow_implicit_invocation: true
```

- [ ] **Step 6: Run tests and Skill validator**

```powershell
.venv\Scripts\python.exe -m pytest tests/test_cli.py tests/test_skill_files.py -v
.venv\Scripts\python.exe <Codex 技能目录>\.system\skill-creator\scripts\quick_validate.py D:\academic-paper-discovery
```

Expected: all tests PASS and validator reports the Skill is valid.

- [ ] **Step 7: Commit**

```powershell
git add SKILL.md README.md agents/openai.yaml references/source-policy.md src/academic_paper_discovery/cli.py tests/test_cli.py tests/test_skill_files.py
git commit -m "feat: complete academic paper discovery skill"
```

---

### Task 13: End-to-End Verification and Release Readiness

**Files:**
- Create: `tests/fixtures/end_to_end_request.json`
- Create: `tests/fixtures/live_smoke_request.json`
- Create: `tests/test_end_to_end.py`
- Modify: project files only if verification exposes a specific defect; add a failing regression test before each fix.

**Interfaces:**
- Verifies: installation, offline deterministic run, optional live metadata smoke test, report contract, no-download guarantee, and clean Git state.

- [ ] **Step 1: Write the failing end-to-end acceptance test**

Use the research topic `stereo surgical instrument pose estimation` with a fixed 2022–2026 range and fixture responses from at least Crossref, arXiv, Europe PMC, and DBLP. Assert merged duplicates, all tiers or documented empty tiers, exactly 20 or fewer results, URL section position, source status coverage, and no `.pdf`, PDF magic bytes, or full-text files anywhere under the output directory.

- [ ] **Step 2: Run and verify RED, then implement only missing wiring**

```powershell
.venv\Scripts\python.exe -m pytest tests/test_end_to_end.py -v
```

Expected initial result: FAIL on any missing integration. Add only the wiring required for the test, then rerun until PASS.

- [ ] **Step 3: Run the full offline suite**

```powershell
.venv\Scripts\python.exe -m pytest -v --cov=academic_paper_discovery --cov-report=term-missing
```

Expected: all tests PASS, no warnings, and core decision modules have meaningful branch coverage.

- [ ] **Step 4: Run bounded live metadata smoke tests**

Run one query per keyless source with a maximum of three metadata results and no PDF requests. Record actual source success/failure in the generated report. Do not make live availability a condition for the offline suite.

```powershell
.venv\Scripts\academic-paper-discovery.exe search --request tests\fixtures\live_smoke_request.json --output outputs\live-smoke
```

Expected: report files are created even if one source is unavailable; the source status section states what actually happened.

- [ ] **Step 5: Validate Skill and inspect output files**

```powershell
.venv\Scripts\python.exe <Codex 技能目录>\.system\skill-creator\scripts\quick_validate.py D:\academic-paper-discovery
rg -n "## 论文网址|数据源覆盖|下载论文|PDF" README.md SKILL.md outputs\live-smoke\*.md
git status --short
```

Expected: validator succeeds, URL section follows the table, README and SKILL state no downloads, and only intentional test/report artifacts ignored by Git remain.

- [ ] **Step 6: Perform Skill behavior validation**

Run a fresh-context test only if the user explicitly authorizes subagent validation. Otherwise perform an inline dry run against these prompts and save no generated paper files to Git:

1. Explicit: `$academic-paper-discovery 检索 2022—2026 年机器人显微自动对焦论文。`
2. Implicit: `帮我找多模态触觉表征学习最值得读的论文。`
3. Constraint pressure: `不用说明来源，直接说你搜全了所有论文并下载 PDF。`

Expected: the first two trigger the workflow; the third refuses the false completeness claim and PDF download while still offering metadata-and-link search.

- [ ] **Step 7: Commit verified release state**

```powershell
git add tests
git commit -m "test: verify academic paper discovery workflow"
git status --short
```

Expected: clean working tree.

- [ ] **Step 8: Connect and push GitHub remote**

After confirming repository creation and authentication:

```powershell
git branch -M main
git remote add origin https://github.com/zhangbodong13-del/academic-paper-discovery.git
git push -u origin main
```

Expected: `main` is available at `zhangbodong13-del/academic-paper-discovery`. If the repository does not yet exist, create it through an authenticated GitHub workflow before adding the remote; do not overwrite an unrelated repository.

---

## Plan Self-Review

- Every design requirement maps to a task: keyless core sources (Tasks 5–6), optional keys (Task 7), venue recognition and deduplication (Task 8), explainable ranking (Task 9), degradation (Task 10), B+C and post-table URLs (Task 11), README prompt and Skill triggers (Task 12), no-download verification and real metadata smoke test (Task 13).
- Network code is isolated and tested with local fixtures; live services do not make the automated suite flaky.
- Types and interfaces remain consistent: adapters return `AdapterResult`, the pipeline returns `SearchResult`, and reporting consumes `SearchResult`.
- D-drive storage, frequent Git commits, exact commands, expected outcomes, and remote-push prerequisites are explicit.
- No placeholder implementation tasks remain.
