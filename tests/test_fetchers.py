import httpx
import pytest
import respx

from src.fetchers.crt_fetcher import fetch_crt
from src.fetchers.rapid_fetcher import fetch_rapid
from src.fetchers.wayback_fetcher import fetch_wayback


CRT_URL = "https://crt.sh/"
WAYBACK_URL = "https://web.archive.org/cdx/search/cdx"
RAPID_URL = "https://rapiddns.io/subdomain/ejemplo.com"


@pytest.mark.asyncio
@respx.mock
async def test_crt_fetcher_parses_response():
    payload = [
        {
            "name_value": "api.ejemplo.com\nmail.ejemplo.com",
            "not_before": "2022-03-01T00:00:00",
        }
    ]
    respx.get(CRT_URL).mock(return_value=httpx.Response(200, json=payload))

    records = await fetch_crt("ejemplo.com")

    assert len(records) == 2
    fqdns = sorted(r.fqdn for r in records)
    assert fqdns == ["api.ejemplo.com", "mail.ejemplo.com"]
    for record in records:
        assert record.sources == ["crt"]
        assert record.first_seen == "2022-03-01"


@pytest.mark.asyncio
@respx.mock
async def test_wayback_fetcher_parses_response():
    payload = [
        ["original", "timestamp"],
        ["http://api.ejemplo.com/path", "20210101120000"],
    ]
    respx.get(WAYBACK_URL).mock(return_value=httpx.Response(200, json=payload))

    records = await fetch_wayback("ejemplo.com")

    assert len(records) == 1
    record = records[0]
    assert record.fqdn == "api.ejemplo.com"
    assert record.first_seen == "2021-01-01"
    assert record.sources == ["wayback"]


@pytest.mark.asyncio
@respx.mock
async def test_rapid_fetcher_returns_empty_on_error():
    respx.get(RAPID_URL).mock(
        side_effect=httpx.RequestError("fallo de red simulado")
    )

    records = await fetch_rapid("ejemplo.com")

    assert records == []
