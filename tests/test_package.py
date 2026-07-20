from typer.testing import CliRunner

from academic_paper_discovery.cli import app


def test_cli_reports_version() -> None:
    result = CliRunner().invoke(app, ["version"])

    assert result.exit_code == 0
    assert result.stdout.strip() == "academic-paper-discovery 0.1.0"
