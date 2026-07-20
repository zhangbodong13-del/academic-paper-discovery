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


def test_offline_fixture_writes_all_formats_and_survives_partial_failure(
    tmp_path,
) -> None:
    request_path = tmp_path / "request.json"
    output_path = tmp_path / "result"
    request_path.write_text(
        json.dumps({"topic": "机器人显微镜自动对焦"}, ensure_ascii=False),
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
        f"- CSV：{output_path / 'report.csv'}",
        f"- JSON：{output_path / 'report.json'}",
    ]
    assert "数据源实际状态" not in result.stdout
    assert "offline-fixture：成功" not in result.stdout
    assert "offline-failure：失败" not in result.stdout
    assert (output_path / "report.md").exists()
    assert (output_path / "report.csv").exists()
    assert (output_path / "report.json").exists()
    report = (output_path / "report.md").read_text(encoding="utf-8")
    assert "## 论文网址" not in report
    assert "## 数据源检索状态" not in report
    assert "[论文](https://doi.org/10.0000/offline-demo)" in report


def test_invalid_request_returns_nonzero_with_chinese_error(tmp_path) -> None:
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
