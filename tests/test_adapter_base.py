import httpx
import pytest
import respx

from academic_paper_discovery.adapters.base import AdapterResult
from academic_paper_discovery.http import MetadataHttpClient, MetadataOnlyError
from academic_paper_discovery.models import Paper


def test_adapter_result_contains_only_papers() -> None:
    result = AdapterResult(papers=[Paper(title="A Study")])

    assert result.papers[0].title == "A Study"
    assert result.model_dump() == {
        "papers": [
            {
                **result.papers[0].model_dump(),
            }
        ]
    }


@respx.mock
def test_http_client_rejects_pdf_response() -> None:
    respx.get("https://example.org/paper").mock(
        return_value=httpx.Response(
            200,
            headers={"Content-Type": "application/pdf"},
            content=b"%PDF-1.7",
        )
    )

    with MetadataHttpClient() as client:
        with pytest.raises(MetadataOnlyError, match="不允许下载论文或 PDF"):
            client.get("https://example.org/paper")


@respx.mock
def test_http_client_accepts_json_metadata() -> None:
    respx.get("https://example.org/metadata").mock(
        return_value=httpx.Response(
            200,
            headers={"Content-Type": "application/json"},
            content=b'{"ok":true}',
        )
    )

    with MetadataHttpClient() as client:
        payload = client.get("https://example.org/metadata")

    assert payload.body == b'{"ok":true}'
    assert payload.content_type == "application/json"
