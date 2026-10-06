import pytest

from src.merger import merge
from src.models import SubdomainRecord


@pytest.fixture
def record_a():
    return SubdomainRecord(fqdn="www.ejemplo.com", sources=["crt"], first_seen="2023-01-01")


@pytest.fixture
def record_b():
    return SubdomainRecord(fqdn="www.ejemplo.com", sources=["rapid"], first_seen="2022-06-15")


def test_merge_deduplicates_same_fqdn(record_a, record_b):
    resultado = merge([record_a, record_b])
    assert len(resultado) == 1
    assert set(resultado[0].sources) == {"crt", "rapid"}


def test_merge_keeps_oldest_first_seen():
    r1 = SubdomainRecord(fqdn="api.ejemplo.com", sources=["crt"], first_seen="2023-01-01")
    r2 = SubdomainRecord(fqdn="api.ejemplo.com", sources=["wayback"], first_seen="2021-05-10")
    resultado = merge([r1, r2])
    assert len(resultado) == 1
    assert resultado[0].first_seen == "2021-05-10"


def test_merge_sorts_by_source_count():
    r1 = SubdomainRecord(fqdn="uno.ejemplo.com", sources=["crt"], first_seen="2023-01-01")
    r2 = SubdomainRecord(fqdn="dos.ejemplo.com", sources=["crt"], first_seen="2023-01-01")
    r3 = SubdomainRecord(fqdn="dos.ejemplo.com", sources=["rapid"], first_seen="2023-01-01")
    resultado = merge([r1, r2, r3])
    assert resultado[0].fqdn == "dos.ejemplo.com"
    assert len(resultado[0].sources) == 2
    assert resultado[1].fqdn == "uno.ejemplo.com"


def test_merge_normalizes_wildcard():
    r = SubdomainRecord(fqdn="*.api.ejemplo.com", sources=["crt"], first_seen="2023-01-01")
    resultado = merge([r])
    assert len(resultado) == 1
    assert resultado[0].fqdn == "api.ejemplo.com"


def test_merge_empty_input():
    assert merge([]) == []
