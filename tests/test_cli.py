import json

from typer.testing import CliRunner

from academic_paper_discovery.cli import app


runner = CliRunner()


def test_help_is_chinese() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "多来源学术论文发现" in result.stdout
    assert "检索论文并生成中文报告" in result.stdout
    assert "Install completion" not in result.stdout


def test_offline_fixture_writes_markdown_only_and_survives_partial_failure(
    tmp_path,
) -> None:
    request_path = tmp_path / "request.json"
    output_path = tmp_path / "result"

    request_path.write_text(
        json.dumps(
            {"topic": "机器人显微镜自动对焦"},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "search",
            "--request",
            str(request_path),
            "--output",
            str(output_path),
            "--offline-fixture",
        ],
    )

    assert result.exit_code == 0, result.stdout

    assert result.stdout.splitlines() == [
        "检索完成，已生成：",
        f"- Markdown：{output_path / 'report.md'}",
    ]

    markdown_path = output_path / "report.md"
    csv_path = output_path / "report.csv"
    json_path = output_path / "report.json"

    assert markdown_path.exists()
    assert not csv_path.exists()
    assert not json_path.exists()

    report = markdown_path.read_text(encoding="utf-8")

    assert "## 论文对比表" in report
    assert "## 必读" not in report
    assert "## 强相关" not in report
    assert "## 拓展阅读" not in report
    assert "## 局限与下一步" not in report

    assert "影响力指标" in report
    assert "创新点" in report
    assert "[论文](https://doi.org/10.0000/offline-demo)" in report


def test_invalid_request_returns_nonzero_with_chinese_error(
    tmp_path,
) -> None:
    request_path = tmp_path / "invalid.json"
    request_path.write_text("{}", encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "search",
            "--request",
            str(request_path),
            "--output",
            str(tmp_path / "result"),
            "--offline-fixture",
        ],
    )

    assert result.exit_code != 0
    assert "请求文件无效" in result.stdout