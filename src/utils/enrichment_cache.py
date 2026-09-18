"""
Cache / download layer for the GO & KEGG enrichment engine (plan §6.8, G1/G2/F1/F7/F8).

Owns runtime downloads of GO, NCBI, and Enrichr assets with:
- atomic writes (``<dest>.tmp`` -> ``os.replace``) and atomic sidecar metadata
  (``<dest>.meta.json`` with version/source/fetched_at/sha256/bytes),
- TTL-based refresh (F7): fresh copies are reused without network access,
  stale copies trigger an automatic re-download, and a failed refresh keeps
  the stale copy with a W2 warning instead of deleting it,
- per-species streaming filters for the multi-GB gzipped NCBI tables (G9):
  the source archive is decompressed and filtered line-by-line, so memory use
  stays O(line) regardless of source size,
- ``detect_online`` (F1): a probe request that honors HTTPS_PROXY env vars
  (trust_env is left enabled) and treats every failure as offline,
- retries with backoff (0.5s / 1s / 2s) on network errors and timeouts, and
  an in-process per-key lock so concurrent ``ensure_*`` calls download once.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import logging
import os
import re
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, Optional
from urllib.parse import quote

import requests

# ---------------------------------------------------------------------------
# Module constants (data sources)
# ---------------------------------------------------------------------------
OBO_URL = "https://geneontology.org/ontology/go-basic.obo"
OBO_GZ_URL = "https://geneontology.org/ontology/go-basic.obo.gz"
GENE2GO_URL = "https://ftp.ncbi.nih.gov/gene/DATA/gene2go.gz"
GENE_INFO_URL = "https://ftp.ncbi.nih.gov/gene/DATA/gene_info.gz"
ENRICHR_LIBRARY_URL = "https://maayanlab.cloud/Enrichr/geneSetLibrary?mode=text&libraryName={name}"
ENRICHR_PROBE_URL = "https://maayanlab.cloud/Enrichr/"

GENE2GO_KEY = "gene2go_%s.gz"
GENE_INFO_KEY = "gene_info_%s.tsv.gz"

# F7: TTL defaults (days) — NCBI/GO assets 30, Enrichr GMT libs 90.
DEFAULT_TTL_DAYS: Dict[str, int] = {"obo": 30, "gene2go": 30, "gene_info": 30, "gmt": 90}

MAX_DOWNLOAD_ATTEMPTS = 3
BACKOFF_SECONDS = (0.5, 1.0, 2.0)  # sleep before retry attempts 2 and 3
DOWNLOAD_CONNECT_TIMEOUT = 10.0
DOWNLOAD_READ_TIMEOUT = 60.0
CHUNK_SIZE = 64 * 1024

SIDECAR_VERSION = "1"

_TAXIDS = {"human": "9606", "mouse": "10090"}

_LOGGER = logging.getLogger(__name__)


def _safe_library_name(library_name: str) -> str:
    """Filesystem-safe key for an Enrichr library name (keeps .gmt extension sane)."""
    return re.sub(r"[^A-Za-z0-9_.\-]", "_", library_name)


def _close_resp(resp: requests.Response) -> None:
    """Close a response defensively (a closed GzipFile may already have closed raw)."""
    try:
        resp.close()
    except Exception:  # pragma: no cover - defensive
        pass


class CacheManager:
    """Cached downloader for GO/NCBI/Enrichr assets (plan §6.8)."""

    def __init__(
        self,
        cache_dir: Path,
        ttl_days: Optional[Dict[str, int]] = None,
        logger: Optional[logging.Logger] = None,
        pin_snapshots: bool = False,
    ):
        """pin_snapshots=True → 주석 스냅샷 고정 모드 (재현성).

        고정 모드에서는 캐시 파일이 존재하면 TTL이 지나도 재다운로드하지 않고
        그 스냅샷(sha256)을 계속 사용한다. 갱신하려면 캐시 파일을 직접 삭제.
        분석 결과 metadata('annotation_snapshots')에 사용 스냅샷의
        sha256/획득일이 기록되어 재현 경로를 보존한다.
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl_days: Dict[str, int] = {**DEFAULT_TTL_DAYS, **(ttl_days or {})}
        self.pin_snapshots: bool = pin_snapshots
        self._logger = logger or _LOGGER
        self._locks: Dict[str, threading.Lock] = {}
        self._locks_guard = threading.Lock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def detect_online(self, timeout: float = 3.0) -> bool:
        """Probe Enrichr (F1). Any exception means offline.

        Uses ``requests.Session()`` with trust_env left enabled so
        HTTPS_PROXY / HTTP_PROXY environment variables are honored.
        """
        try:
            session = requests.Session()
            try:
                resp = session.get(ENRICHR_PROBE_URL, timeout=timeout)
                resp.raise_for_status()   # 4xx/5xx는 오프라인 취급 (architect P3)
                resp.close()
            finally:
                session.close()
            return True
        except Exception:
            return False

    def ensure_obo(self, organism: str) -> Path:
        self._taxid(organism)  # validate species; the OBO file itself is species-neutral
        return self._ensure("go-basic.obo", "obo", lambda dest: self._download_obo(dest))

    def ensure_gene2go(self, organism: str) -> Path:
        taxid = self._taxid(organism)
        rel = GENE2GO_KEY % taxid
        return self._ensure(
            rel, "gene2go", lambda dest: self._download_filtered(dest, GENE2GO_URL, taxid, "gene2go")
        )

    def ensure_gene_info(self, organism: str) -> Path:
        taxid = self._taxid(organism)
        rel = GENE_INFO_KEY % taxid
        return self._ensure(
            rel, "gene_info", lambda dest: self._download_filtered(dest, GENE_INFO_URL, taxid, "gene_info")
        )

    def ensure_gmt(self, library_name: str) -> Path:
        if not library_name or not str(library_name).strip():
            raise ValueError("library_name must not be empty")
        rel = f"{_safe_library_name(library_name)}.gmt"
        return self._ensure(rel, "gmt", lambda dest: self._download_gmt(dest, library_name))

    def has(self, relative_key: str) -> Optional[Path]:
        """Resolve <cache_dir>/<key> if it exists, else None."""
        path = self.cache_dir / relative_key
        return path if path.exists() else None

    def snapshot_provenance(self, relative_key: str) -> dict:
        """캐시 파일의 스냅샷 증명: {file, source, fetched_at, sha256, bytes, pinned}.

        파일이 없거나 사이드카가 없으면 {} 반환.
        """
        path = self.cache_dir / relative_key
        if not path.exists():
            return {}
        meta = self.sidecar(path)
        if not meta:
            return {"file": relative_key, "note": "sidecar missing"}
        return {**meta, "file": relative_key}

    def sidecar(self, path: Path) -> dict:
        """Read <path>.meta.json; return {} when missing or unreadable."""
        meta_path = Path(str(path) + ".meta.json")
        if not meta_path.exists():
            return {}
        try:
            data = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    # ------------------------------------------------------------------
    # Ensure orchestration: lock -> freshness -> download -> W2 fallback
    # ------------------------------------------------------------------
    def _ensure(self, rel_key: str, ttl_key: str, downloader: Callable[[Path], None]) -> Path:
        with self._lock_for(rel_key):
            dest = self.cache_dir / rel_key
            if self._is_fresh(dest, ttl_key):
                self._logger.debug("cache hit (fresh): %s", dest)
                return dest
            try:
                downloader(dest)
            except Exception as exc:  # noqa: BLE001 - re-download/keep logic is generic
                if dest.exists():
                    # F7: failed refresh keeps the stale copy and warns (W2 marker).
                    self._logger.warning(
                        "W2: failed to refresh %s (%s: %s); keeping stale cached copy",
                        dest, type(exc).__name__, exc,
                    )
                    return dest
                raise
            return dest

    def _is_fresh(self, dest: Path, ttl_key: str) -> bool:
        if not dest.exists():
            return False
        if self.pin_snapshots:
            return True   # 고정 모드: 존재하면 항상 fresh — 같은 스냅샷 재현
        ttl_days = self.ttl_days.get(ttl_key, DEFAULT_TTL_DAYS.get(ttl_key, 30))
        return (time.time() - dest.stat().st_mtime) < ttl_days * 86400

    def _lock_for(self, key: str) -> threading.Lock:
        with self._locks_guard:
            lock = self._locks.get(key)
            if lock is None:
                lock = threading.Lock()
                self._locks[key] = lock
            return lock

    # ------------------------------------------------------------------
    # Downloaders
    # ------------------------------------------------------------------
    def _http_get(self, url: str, timeout) -> requests.Response:
        """Streaming GET with retries + backoff on network errors/timeouts (F7)."""
        last_exc: Optional[Exception] = None
        for attempt in range(MAX_DOWNLOAD_ATTEMPTS):
            try:
                return requests.get(
                    url, timeout=timeout, stream=True, headers={"Accept-Encoding": "identity"}
                )
            except (requests.RequestException, OSError) as exc:
                last_exc = exc
                if attempt < MAX_DOWNLOAD_ATTEMPTS - 1:
                    time.sleep(BACKOFF_SECONDS[attempt])
        assert last_exc is not None
        raise last_exc

    def _download_obo(self, dest: Path) -> None:
        resp = self._http_get(OBO_URL, self._timeout())
        source_url = OBO_URL
        decompress = False
        if resp.status_code in (403, 404):
            # F8: plain variant unavailable -> try the .gz variant once.
            _close_resp(resp)
            resp = self._http_get(OBO_GZ_URL, self._timeout())
            source_url = OBO_GZ_URL
            decompress = True
        try:
            resp.raise_for_status()
            self._run_download(dest, source_url, self._plain_writer(resp, decompress=decompress))
        finally:
            _close_resp(resp)

    def _download_gmt(self, dest: Path, library_name: str) -> None:
        url = ENRICHR_LIBRARY_URL.format(name=quote(library_name, safe=""))
        resp = self._http_get(url, self._timeout())
        try:
            resp.raise_for_status()
            self._run_download(dest, url, self._plain_writer(resp, decompress=False))
        finally:
            _close_resp(resp)

    def _download_filtered(self, dest: Path, url: str, taxid: str, label: str) -> None:
        """Stream-filter a gzipped NCBI table by tax_id (G9, memory promise).

        The source archive is decompressed line-by-line and only matching
        rows are written into the gzip'd per-species output. All columns
        (including gene_info's Synonyms) are kept verbatim.
        """
        resp = self._http_get(url, self._timeout())
        try:
            resp.raise_for_status()
        except Exception:
            _close_resp(resp)
            raise
        kept = 0
        total = 0
        target = str(taxid).encode("ascii")

        def writer(fh) -> None:
            nonlocal kept, total
            gz_in = gzip.GzipFile(fileobj=resp.raw, mode="rb")
            gz_out = gzip.GzipFile(fileobj=fh, mode="wb")
            try:
                for line in gz_in:
                    total += 1
                    if line.split(b"\t", 1)[0] == target:
                        gz_out.write(line)
                        kept += 1
            finally:
                gz_in.close()
                gz_out.close()

        try:
            self._run_download(dest, url, writer)
        finally:
            _close_resp(resp)
        self._logger.info(
            "%s: filtered taxid %s: kept %d/%d rows -> %s", label, taxid, kept, total, dest
        )

    def _plain_writer(self, resp: requests.Response, decompress: bool) -> Callable:
        def writer(fh) -> None:
            if decompress:
                gz_in = gzip.GzipFile(fileobj=resp.raw, mode="rb")
                try:
                    while True:
                        chunk = gz_in.read(CHUNK_SIZE)
                        if not chunk:
                            break
                        fh.write(chunk)
                finally:
                    gz_in.close()
            else:
                for chunk in resp.iter_content(chunk_size=CHUNK_SIZE):
                    if chunk:
                        fh.write(chunk)

        return writer

    # ------------------------------------------------------------------
    # Atomic commit + sidecar metadata
    # ------------------------------------------------------------------
    def _run_download(self, dest: Path, source_url: str, writer: Callable[[object], None]) -> None:
        """Write <dest>.tmp via writer, then commit atomically; never leave .tmp behind."""
        tmp = Path(str(dest) + ".tmp")
        try:
            with open(tmp, "wb") as fh:
                writer(fh)
            self._finalize(dest, tmp, source_url)
        except BaseException:
            self._remove_tmp(tmp)
            raise

    def _finalize(self, dest: Path, tmp: Path, source_url: str) -> None:
        # sha256 of the bytes we are about to commit (before rename, F7).
        sha256_hex = self._sha256_file(tmp)
        os.replace(tmp, dest)  # atomic rename
        size_bytes = dest.stat().st_size
        self._write_sidecar(dest, source_url, sha256_hex, size_bytes)
        self._logger.info(
            "cached %s (%d bytes, sha256=%s) from %s",
            dest, size_bytes, sha256_hex[:12], source_url,
        )

    def _sha256_file(self, path: Path) -> str:
        hasher = hashlib.sha256()
        with open(path, "rb") as fh:
            while True:
                chunk = fh.read(CHUNK_SIZE)
                if not chunk:
                    break
                hasher.update(chunk)
        return hasher.hexdigest()

    def _write_sidecar(self, dest: Path, source_url: str, sha256_hex: str, size_bytes: int) -> None:
        meta = {
            "version": SIDECAR_VERSION,
            "source": source_url,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "sha256": sha256_hex,
            "bytes": size_bytes,
        }
        meta_path = Path(str(dest) + ".meta.json")
        tmp = Path(str(meta_path) + ".tmp")
        tmp.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, meta_path)  # atomic sidecar write

    @staticmethod
    def _remove_tmp(tmp: Path) -> None:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _taxid(organism: str) -> str:
        taxid = _TAXIDS.get(organism.lower()) if isinstance(organism, str) else None
        if taxid is None:
            raise ValueError(
                f"unsupported organism {organism!r}; expected 'human' or 'mouse'"
            )
        return taxid

    @staticmethod
    def _timeout() -> tuple:
        return (DOWNLOAD_CONNECT_TIMEOUT, DOWNLOAD_READ_TIMEOUT)
