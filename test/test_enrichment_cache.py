"""Unit tests for src/utils/enrichment_cache.py (plan §6.8, F1/F7/F8, §12 cache tests).

Bulk of the suite runs offline against monkeypatched downloads; live network
tests are marked ``@pytest.mark.network`` and self-skip when unreachable.
"""

import gzip
import hashlib
import io
import logging
import os
import threading
import time
from datetime import datetime
from pathlib import Path

import pytest
import requests

from utils.enrichment_cache import (
    ENRICHR_LIBRARY_URL,
    GENE2GO_URL,
    GENE_INFO_URL,
    OBO_URL,
    CacheManager,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Fakes & helpers
# ---------------------------------------------------------------------------
class FakeResponse:
    """Minimal requests.Response stand-in for monkeypatched downloads."""

    def __init__(self, payload=b"", status=200, raw=None):
        self._payload = payload
        self.status_code = status
        self.raw = raw

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}", response=self)

    def iter_content(self, chunk_size=8192):
        for i in range(0, len(self._payload), chunk_size):
            yield self._payload[i : i + chunk_size]

    def close(self):
        pass


class RawStream(io.BytesIO):
    """BytesIO stand-in for ``requests.Response.raw`` (gzip payload)."""

    decode_content = True


def _gz_bytes(name):
    with open(FIXTURES_DIR / name, "rb") as fh:
        return fh.read()


def _read_gz_lines(path):
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        return fh.read().splitlines()


def _assert_no_tmp(cache_dir):
    leftovers = sorted(str(p) for p in Path(cache_dir).rglob("*.tmp"))
    assert leftovers == [], f"leftover .tmp files: {leftovers}"


# ---------------------------------------------------------------------------
# Thin API: has() / sidecar() / defaults
# ---------------------------------------------------------------------------
def test_default_ttl_days(tmp_path):
    cm = CacheManager(tmp_path)
    assert cm.ttl_days == {"obo": 30, "gene2go": 30, "gene_info": 30, "gmt": 90}


def test_ttl_days_override_merges_defaults(tmp_path):
    cm = CacheManager(tmp_path, ttl_days={"gmt": 7})
    assert cm.ttl_days["obo"] == 30
    assert cm.ttl_days["gmt"] == 7


def test_has_and_sidecar_defaults(tmp_path):
    cm = CacheManager(tmp_path)
    hit = Path(tmp_path) / "a.txt"
    hit.write_text("x", encoding="utf-8")
    assert cm.has("a.txt") == hit
    assert cm.has("nope.txt") is None
    assert cm.sidecar(hit) == {}
    assert cm.sidecar(Path(tmp_path) / "missing.obo") == {}


def test_unsupported_organism_raises(tmp_path):
    cm = CacheManager(tmp_path)
    with pytest.raises(ValueError, match="unsupported organism"):
        cm.ensure_obo("rat")
    with pytest.raises(ValueError, match="unsupported organism"):
        cm.ensure_gene2go("rat")
    with pytest.raises(ValueError, match="unsupported organism"):
        cm.ensure_gene_info("Rat")


def test_ensure_gmt_rejects_empty_name(tmp_path):
    cm = CacheManager(tmp_path)
    with pytest.raises(ValueError, match="library_name"):
        cm.ensure_gmt("")


# ---------------------------------------------------------------------------
# Atomic writes: no .tmp left behind, no dest on failure
# ---------------------------------------------------------------------------
def test_atomic_write_failure_leaves_no_tmp_or_dest(tmp_path, monkeypatch):
    cm = CacheManager(tmp_path)

    def exploding(url, timeout):
        resp = FakeResponse(payload=b"partial")
        orig_iter = resp.iter_content

        def iter_content(chunk_size=8192):
            yield b"partial-data"
            raise RuntimeError("simulated mid-download failure")

        resp.iter_content = iter_content
        return resp

    monkeypatch.setattr(cm, "_http_get", exploding)
    with pytest.raises(RuntimeError, match="mid-download"):
        cm.ensure_gmt("KEGG_2021_Human")
    assert not (Path(tmp_path) / "KEGG_2021_Human.gmt").exists()
    _assert_no_tmp(tmp_path)


def test_filtered_download_failure_leaves_no_tmp(tmp_path, monkeypatch):
    cm = CacheManager(tmp_path)

    class ExplodingRaw(io.BytesIO):
        decode_content = True

        def __init__(self, data):
            super().__init__(data)
            self._reads = 0

        def read(self, size=-1):
            self._reads += 1
            if self._reads > 2:
                raise OSError("simulated mid-stream failure")
            return super().read(size)

    def fake_get(url, timeout):
        return FakeResponse(raw=ExplodingRaw(_gz_bytes("gene2go_sample.gz")))

    monkeypatch.setattr(cm, "_http_get", fake_get)
    with pytest.raises(OSError, match="mid-stream"):
        cm.ensure_gene2go("human")
    assert not (Path(tmp_path) / "gene2go_9606.gz").exists()
    _assert_no_tmp(tmp_path)


# ---------------------------------------------------------------------------
# Sidecar metadata
# ---------------------------------------------------------------------------
def test_sidecar_metadata_after_download(tmp_path, monkeypatch):
    cm = CacheManager(tmp_path)
    payload = b"format-version: 1.0\nontology: go\n"
    monkeypatch.setattr(cm, "_http_get", lambda url, timeout: FakeResponse(payload=payload))
    dest = cm.ensure_obo("human")
    assert dest == Path(tmp_path) / "go-basic.obo"
    assert dest.read_bytes() == payload

    meta = cm.sidecar(dest)
    assert meta["version"] == "1"
    assert meta["source"] == OBO_URL
    assert meta["sha256"] == hashlib.sha256(payload).hexdigest()
    assert meta["bytes"] == len(payload)
    # ISO 8601 UTC timestamp that actually parses
    fetched = datetime.fromisoformat(meta["fetched_at"])
    assert fetched.tzinfo is not None
    assert meta["sha256"] == hashlib.sha256(dest.read_bytes()).hexdigest()
    _assert_no_tmp(tmp_path)


# ---------------------------------------------------------------------------
# TTL (F7): fresh -> no download; stale -> redownload; stale+fail -> W2 keep
# ---------------------------------------------------------------------------
def test_fresh_file_skips_download(tmp_path, monkeypatch):
    cm = CacheManager(tmp_path)
    dest = Path(tmp_path) / "go-basic.obo"
    dest.write_bytes(b"old-obo")
    now = time.time()
    os.utime(dest, (now, now))

    def should_not_be_called(url, timeout):
        raise AssertionError("download must not run for a fresh cache entry")

    monkeypatch.setattr(cm, "_http_get", should_not_be_called)
    got = cm.ensure_obo("human")
    assert got == dest
    assert dest.read_bytes() == b"old-obo"
    _assert_no_tmp(tmp_path)


def test_stale_file_triggers_redownload(tmp_path, monkeypatch):
    cm = CacheManager(tmp_path)
    dest = Path(tmp_path) / "go-basic.obo"
    dest.write_bytes(b"old-obo")
    old = time.time() - 40 * 86400  # beyond the 30-day default
    os.utime(dest, (old, old))

    payload = b"format-version: 1.1\nupdated\n"
    calls = []

    def fake_get(url, timeout):
        calls.append(url)
        return FakeResponse(payload=payload)

    monkeypatch.setattr(cm, "_http_get", fake_get)
    got = cm.ensure_obo("human")
    assert got == dest
    assert dest.read_bytes() == payload
    assert calls == [OBO_URL]
    assert cm.sidecar(dest)["sha256"] == hashlib.sha256(payload).hexdigest()
    _assert_no_tmp(tmp_path)


def test_stale_download_failure_keeps_old_and_warns_w2(tmp_path, monkeypatch, caplog):
    cm = CacheManager(tmp_path)
    dest = Path(tmp_path) / "go-basic.obo"
    dest.write_bytes(b"old-obo")
    sentinel = dest.read_bytes()
    old = time.time() - 40 * 86400
    os.utime(dest, (old, old))

    attempts = []
    sleeps = []

    def fake_get(url, **kwargs):
        attempts.append(url)
        raise requests.exceptions.ConnectionError("simulated outage")

    monkeypatch.setattr(requests, "get", fake_get)
    monkeypatch.setattr(time, "sleep", lambda s: sleeps.append(s))

    with caplog.at_level(logging.WARNING, logger="utils.enrichment_cache"):
        got = cm.ensure_obo("human")
    assert got == dest
    assert dest.read_bytes() == sentinel  # stale copy is never deleted
    assert len(attempts) == 3  # retried up to 3 attempts
    assert sleeps == [0.5, 1.0]  # backoff (0.5s, 1s) between the 3 attempts
    assert any("W2" in record.getMessage() for record in caplog.records)
    _assert_no_tmp(tmp_path)


def test_ttl_days_override_controls_freshness(tmp_path, monkeypatch):
    cm = CacheManager(tmp_path, ttl_days={"gmt": 0})
    payload = b"a\t-\tb\n"
    monkeypatch.setattr(cm, "_http_get", lambda url, timeout: FakeResponse(payload=payload))
    cm.ensure_gmt("KEGG_2021_Human")

    calls = []

    def fake_get2(url, timeout):
        calls.append(url)
        return FakeResponse(payload=payload)

    monkeypatch.setattr(cm, "_http_get", fake_get2)
    cm.ensure_gmt("KEGG_2021_Human")  # ttl 0 -> immediately stale -> redownload
    assert len(calls) == 1


# ---------------------------------------------------------------------------
# Per-species streaming filters (G9)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("organism,expected", [("human", "9606"), ("mouse", "10090")])
def test_ensure_gene2go_filters_by_taxid(tmp_path, monkeypatch, caplog, organism, expected):
    cm = CacheManager(tmp_path)
    gz_data = _gz_bytes("gene2go_sample.gz")
    monkeypatch.setattr(cm, "_http_get", lambda url, timeout: FakeResponse(raw=RawStream(gz_data)))
    with caplog.at_level(logging.INFO, logger="utils.enrichment_cache"):
        dest = cm.ensure_gene2go(organism)
    assert dest.name == f"gene2go_{expected}.gz"
    rows = _read_gz_lines(dest)
    taxids = [row.split("\t")[0] for row in rows]
    assert taxids
    assert all(t == expected for t in taxids)
    assert "7955" not in taxids  # other-species rows filtered out
    assert "kept 3/8" in caplog.text  # filtered row count logged
    assert cm.sidecar(dest)["source"] == GENE2GO_URL
    _assert_no_tmp(tmp_path)


@pytest.mark.parametrize(
    "organism,expected,marker,kept",
    [
        # 실형식(NCBI '#Format:'/'#tax_id' 주석 + 10컬럼) 픽스처 기준 (2026-09-03 재생성)
        ("human", "9606", "BRCA1 DNA repair associated", "kept 4/8"),
        ("mouse", "10090", "transformation related protein 53", "kept 1/8"),
    ],
)
def test_ensure_gene_info_filters_by_taxid_keeps_synonyms(
    tmp_path, monkeypatch, caplog, organism, expected, marker, kept
):
    cm = CacheManager(tmp_path)
    gz_data = _gz_bytes("gene_info_sample.gz")
    monkeypatch.setattr(cm, "_http_get", lambda url, timeout: FakeResponse(raw=RawStream(gz_data)))
    with caplog.at_level(logging.INFO, logger="utils.enrichment_cache"):
        dest = cm.ensure_gene_info(organism)
    assert dest.name == f"gene_info_{expected}.tsv.gz"
    text = "\n".join(_read_gz_lines(dest))
    taxids = [row.split("\t")[0] for row in text.splitlines()]
    assert taxids
    assert all(t == expected for t in taxids)
    assert "7955" not in text  # other-species rows filtered out
    assert marker in text  # Synonyms column retained verbatim
    assert kept in caplog.text
    assert cm.sidecar(dest)["source"] == GENE_INFO_URL
    _assert_no_tmp(tmp_path)


# ---------------------------------------------------------------------------
# GMT downloads (verbatim text, .gmt extension)
# ---------------------------------------------------------------------------
def test_ensure_gmt_saves_verbatim(tmp_path, monkeypatch):
    cm = CacheManager(tmp_path)
    payload = "TERM1\tdesc\tGENE1\tGENE2\nTERM2\t-\tGENE3\n"
    monkeypatch.setattr(cm, "_http_get", lambda url, timeout: FakeResponse(payload=payload.encode()))
    dest = cm.ensure_gmt("KEGG_2021_Human")
    assert dest.name == "KEGG_2021_Human.gmt"
    assert dest.read_text(encoding="utf-8") == payload
    meta = cm.sidecar(dest)
    assert meta["source"] == ENRICHR_LIBRARY_URL.format(name="KEGG_2021_Human")
    assert meta["sha256"] == hashlib.sha256(payload.encode()).hexdigest()
    _assert_no_tmp(tmp_path)


def test_ensure_gmt_sanitizes_library_name(tmp_path, monkeypatch):
    cm = CacheManager(tmp_path)
    monkeypatch.setattr(cm, "_http_get", lambda url, timeout: FakeResponse(payload=b"x\n"))
    dest = cm.ensure_gmt("../Bad Name")
    assert dest.name == ".._Bad_Name.gmt"  # single component: no traversal
    assert dest.parent == Path(tmp_path)  # no path traversal outside cache dir
    meta = cm.sidecar(dest)
    assert "Bad%20Name" in meta["source"]  # URL-encoded library name
    _assert_no_tmp(tmp_path)


# ---------------------------------------------------------------------------
# detect_online (F1)
# ---------------------------------------------------------------------------
def test_detect_online_true_when_reachable(monkeypatch, tmp_path):
    monkeypatch.setattr(
        requests.sessions.Session,
        "request",
        lambda self, method, url, **kwargs: FakeResponse(status=200),
    )
    assert CacheManager(tmp_path).detect_online() is True


def test_detect_online_false_on_connection_error(monkeypatch, tmp_path):
    def boom(self, method, url, **kwargs):
        raise requests.exceptions.ConnectionError("down")

    monkeypatch.setattr(requests.sessions.Session, "request", boom)
    assert CacheManager(tmp_path).detect_online() is False


@pytest.mark.offline
def test_detect_online_false_when_network_blocked(tmp_path, block_network):
    assert CacheManager(tmp_path).detect_online(timeout=0.5) is False


def test_detect_online_keeps_env_proxies_enabled(monkeypatch, tmp_path):
    captured = {}

    def fake_get(self, url, **kwargs):
        captured["trust_env"] = self.trust_env
        captured["timeout"] = kwargs.get("timeout")
        return FakeResponse(status=200)

    monkeypatch.setattr(requests.sessions.Session, "get", fake_get)
    assert CacheManager(tmp_path).detect_online(timeout=2.5) is True
    assert captured["trust_env"] is True  # HTTPS_PROXY env stays honored
    assert captured["timeout"] == 2.5


# ---------------------------------------------------------------------------
# Duplicate / concurrent ensure calls -> single download
# ---------------------------------------------------------------------------
def test_sequential_ensure_single_download(tmp_path, monkeypatch):
    cm = CacheManager(tmp_path)
    calls = []
    monkeypatch.setattr(
        cm, "_http_get", lambda url, timeout: (calls.append(url), FakeResponse(payload=b"a\t-\tb\n"))[1]
    )
    first = cm.ensure_gmt("KEGG_2021_Human")
    second = cm.ensure_gmt("KEGG_2021_Human")
    assert first == second
    assert len(calls) == 1
    _assert_no_tmp(tmp_path)


def test_concurrent_ensure_single_download(tmp_path, monkeypatch):
    cm = CacheManager(Path(tmp_path) / "cache")
    calls = []
    calls_lock = threading.Lock()

    def fake_get(url, timeout):
        with calls_lock:
            calls.append(url)
        time.sleep(0.05)  # keep both racing threads in the download window
        return FakeResponse(payload=b"a\t-\tb\n")

    monkeypatch.setattr(cm, "_http_get", fake_get)

    results = []
    errors = []
    barrier = threading.Barrier(2)

    def worker():
        try:
            barrier.wait(timeout=5)
            results.append(cm.ensure_gmt("KEGG_2021_Human"))
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    t1 = threading.Thread(target=worker)
    t2 = threading.Thread(target=worker)
    t1.start()
    t2.start()
    t1.join(timeout=15)
    t2.join(timeout=15)
    assert not errors
    assert len(results) == 2
    assert results[0] == results[1]
    assert len(calls) == 1  # per-key lock + freshness -> single download
    _assert_no_tmp(Path(tmp_path) / "cache")


# ---------------------------------------------------------------------------
# Live network smoke tests (skippable)
# ---------------------------------------------------------------------------
@pytest.mark.network
def test_detect_online_live(tmp_path):
    cm = CacheManager(tmp_path)
    if not cm.detect_online(timeout=5.0):
        pytest.skip("Enrichr unreachable; skipping live network test")
    assert True


@pytest.mark.network
def test_ensure_obo_live(tmp_path):
    cm = CacheManager(tmp_path)
    try:
        dest = cm.ensure_obo("human")
    except requests.RequestException as exc:
        pytest.skip(f"live OBO download failed: {exc}")
    assert dest.exists()
    assert dest.name == "go-basic.obo"
    meta = cm.sidecar(dest)
    assert meta["sha256"] == hashlib.sha256(dest.read_bytes()).hexdigest()
    _assert_no_tmp(tmp_path)


# --------------------------------------------------------------------------
# 재현성: 스냅샷 핀 모드 + 증명 (검증 리포트 — 주석 버전 고정)
# --------------------------------------------------------------------------

def test_pin_snapshots_prevents_ttl_redownload(tmp_path):
    """고정 모드: stale mtime이어도 재다운로드 없이 같은 스냅샷 사용."""
    import os, time
    cache = CacheManager(tmp_path, pin_snapshots=True)
    dest = tmp_path / "gene2go_9606.gz"
    dest.write_bytes(b"OLD")
    old = time.time() - 400 * 86400
    os.utime(dest, (old, old))

    calls = []
    def _dl(dest):
        calls.append(dest)
        raise AssertionError("pinned: downloader must not run")
    path = cache._ensure("gene2go_9606.gz", "gene2go", _dl)
    assert path == dest and not calls
    assert path.read_bytes() == b"OLD"


def test_pin_snapshots_downloads_once_when_missing(tmp_path):
    cache = CacheManager(tmp_path, pin_snapshots=True)
    calls = []
    dest = tmp_path / "go-basic.obo"
    def _dl(d):
        calls.append(d); d.write_bytes(b"NEW")
    out = cache._ensure("go-basic.obo", "obo", _dl)
    assert out == dest and len(calls) == 1
    cache._ensure("go-basic.obo", "obo", lambda d: calls.append(d))
    assert len(calls) == 1


def test_snapshot_provenance_reads_sidecar(tmp_path):
    cache = CacheManager(tmp_path)
    dest = tmp_path / "go-basic.obo"
    dest.write_bytes(b"data")
    cache._write_sidecar(dest, "http://example/obo", "abc123", 4)
    prov = cache.snapshot_provenance("go-basic.obo")
    assert prov["file"] == "go-basic.obo"
    assert prov["sha256"] == "abc123"
    assert prov["source"] == "http://example/obo"
    assert cache.snapshot_provenance("missing.gz") == {}


def test_default_mode_still_ttl_refreshes(tmp_path):
    """비고정(기본)은 기존 TTL 동작 유지 — stale이면 재다운로드."""
    import os, time
    cache = CacheManager(tmp_path, pin_snapshots=False)
    dest = tmp_path / "go-basic.obo"
    dest.write_bytes(b"OLD")
    old = time.time() - 400 * 86400
    os.utime(dest, (old, old))
    calls = []
    def _dl(d):
        calls.append(d); d.write_bytes(b"NEW")
    cache._ensure("go-basic.obo", "obo", _dl)
    assert len(calls) == 1 and dest.read_bytes() == b"NEW"
