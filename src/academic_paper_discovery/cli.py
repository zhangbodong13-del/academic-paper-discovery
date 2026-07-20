"""中文命令行入口。"""

from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path
from typing import Annotated

import typer
from pydantic import ValidationError

from academic_paper_discovery import __version__
from academic_paper_discovery.adapters.arxiv import ArxivSource
from academic_paper_discovery.adapters.base import AdapterResult, PaperSource
from academic_paper_discovery.adapters.crossref import CrossrefSource
from academic_paper_discovery.adapters.dblp import DblpSource
from academic_paper_discovery.adapters.europe_pmc import EuropePmcSource
from academic_paper_discovery.adapters.openalex import OpenAlexSource
from academic_paper_discovery.adapters.semantic_scholar import SemanticScholarSource
from academic_paper_discovery.http import MetadataHttpClient
from academic_paper_discovery.models import Paper, PaperLink, SearchRequest
from academic_paper_discovery.pipeline import SearchPipeline
from academic_paper_discovery.reporting import render_markdown, write_csv, write_json


app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    help="多来源学术论文发现、筛选与对比工具。",
)


@app.callback()
def main() -> None:
    """多来源学术论文发现、筛选与对比工具。"""


@app.command(help="显示当前版本。")
def version() -> None:
    typer.echo(f"academic-paper-discovery {__version__}")


@app.command(help="检索论文并生成中文报告、CSV 和 JSON。")
def search(
    request: Annotated[
        Path,
        typer.Option(
            "--request",
            "-r",
            help="UTF-8 JSON 请求文件。",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
        ),
    ],
    output: Annotated[
        Path,
        typer.Option(
            "--output",
            "-o",
            help="报告输出目录；会生成 report.md、report.csv、report.json。",
        ),
    ],
    offline_fixture: Annotated[
        bool,
        typer.Option(
            "--offline-fixture",
            help="只用于测试和演示；使用内置离线数据，不代表实时检索结果。",
        ),
    ] = False,
) -> None:
    """执行一次元数据检索；数据源局部失败不会令命令失败。"""

    try:
        search_request = _load_request(request)
    except (OSError, ValueError, json.JSONDecodeError, ValidationError) as error:
        typer.echo(f"请求文件无效：{error}")
        raise typer.Exit(code=2) from error

    client: MetadataHttpClient | None = None
    if offline_fixture:
        sources: list[PaperSource] = [_OfflineFixtureSource(), _OfflineFailureSource()]
    else:
        client = MetadataHttpClient()
        sources = _build_live_sources(client)

    try:
        result = SearchPipeline(sources, current_year=date.today().year).run(
            search_request
        )
    finally:
        if client is not None:
            client.close()

    try:
        output.mkdir(parents=True, exist_ok=True)
        markdown_path = output / "report.md"
        markdown_path.write_text(render_markdown(result), encoding="utf-8")
        csv_path = write_csv(result, output / "report.csv")
        json_path = write_json(result, output / "report.json")
    except OSError as error:
        typer.echo(f"无法写入报告：{error}")
        raise typer.Exit(code=2) from error

    typer.echo("检索完成，已生成：")
    typer.echo(f"- Markdown：{markdown_path}")
    typer.echo(f"- CSV：{csv_path}")
    typer.echo(f"- JSON：{json_path}")


def _load_request(path: Path) -> SearchRequest:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("请求 JSON 顶层必须是对象")
    values = dict(payload)
    topic = values.pop("topic", None)
    if not isinstance(topic, str) or not topic.strip():
        raise ValueError("缺少非空字符串字段 topic")

    has_year_from = "year_from" in values
    has_year_to = "year_to" in values
    if not has_year_from and not has_year_to:
        return SearchRequest.with_defaults(
            topic=topic,
            current_year=date.today().year,
            **values,
        )
    if has_year_from != has_year_to:
        raise ValueError("year_from 和 year_to 必须同时提供")
    return SearchRequest.model_validate({"topic": topic, **values})


def _build_live_sources(client: MetadataHttpClient) -> list[PaperSource]:
    return [
        CrossrefSource(client=client, mailto=os.environ.get("CROSSREF_MAILTO")),
        EuropePmcSource(client=client),
        ArxivSource(client=client),
        DblpSource(client=client),
        OpenAlexSource(client=client, api_key=os.environ.get("OPENALEX_API_KEY")),
        SemanticScholarSource(
            client=client,
            api_key=os.environ.get("SEMANTIC_SCHOLAR_API_KEY"),
        ),
    ]


class _OfflineFixtureSource:
    name = "offline-fixture"

    def search(self, plan, request) -> AdapterResult:
        paper = Paper(
            title=f"{request.topic}：离线示例论文",
            authors=["示例作者"],
            year=request.year_to,
            venue="示例期刊",
            abstract=f"用于演示 {request.topic} 检索报告的本地元数据。",
            doi="10.0000/offline-demo",
            links=[
                PaperLink(
                    kind="演示页面",
                    url="https://example.org/offline-demo",
                    source=self.name,
                )
            ],
            source_names=[self.name],
        )
        return AdapterResult(papers=[paper])


class _OfflineFailureSource:
    name = "offline-failure"

    def search(self, plan, request) -> AdapterResult:
        raise RuntimeError("用于验证局部失败降级的离线示例")
