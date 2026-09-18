"""
SymbolMapper 단위 테스트 (plan §12 매퍼, G9 — offline/mock 필수, G13).

로컬 gene_info(gzip TSV) 파싱·taxid 필터·Synonyms 별칭 매핑, pickle 캐시
재사용/무효화(sha256), mygene fallback(mock)을 검증한다. 실제 네트워크 호출은
절대 발생하지 않는다 — autouse 픽스처가 mygene.MyGeneInfo를 차단한다.
"""
import gzip
import hashlib
import logging
from pathlib import Path

import mygene
import pytest

from utils.gene_id_mapper import SymbolMapper


# --------------------------------------------------------------------------
# helpers / fakes
# --------------------------------------------------------------------------

def _sha256(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _write_gene_info(root: Path, taxid: int, rows, filename: str) -> Path:
    """gzipped gene_info TSV(헤더: tax_id, GeneID, Symbol, Synonyms) 작성."""
    path = root / filename
    with gzip.open(path, "wt", encoding="utf-8", newline="") as fh:
        fh.write("tax_id\tGeneID\tSymbol\tSynonyms\n")
        for r in rows:
            fh.write("\t".join(str(c) for c in r) + "\n")
    return path


HUMAN_ROWS = [
    (9606, 7157, "TP53", "P53|LFS1"),
    (9606, 672, "BRCA1", "RNF53"),
]
MOUSE_ROWS = [
    (10090, 22099, "Trp73", "Tp73|P73"),      # P0-7: alias Tp73 -> Trp73
    (10090, 12189, "Brca1", "Rnf53"),
]


class FakeCacheManager:
    """utils.enrichment_cache.CacheManager 계약(ensure_gene_info/sidecar) 최소 구현."""

    def __init__(self, cache_dir: Path):
        self.cache_dir = Path(cache_dir)
        self._gene_info = {}
        self._sidecars = {}

    def ensure_gene_info(self, organism: str) -> Path:
        return self._gene_info[organism]

    def sidecar(self, path) -> dict:
        return self._sidecars[Path(path)]

    def install(self, organism: str, path: Path):
        path = Path(path)
        self._gene_info[organism] = path
        self._sidecars[path] = {
            "sha256": _sha256(path),
            "version": "test",
            "fetched_at": "2026-09-03T00:00:00Z",
        }

    def reinstall(self, organism: str, path: Path):
        """같은 경로에 새 내용 + 새 sidecar sha 설치(무효화 시나리오)."""
        self.install(organism, path)


class _NotFoundClient:
    """mygene mock: 모든 조회를 notfound 처리(로컬 miss가 온라인으로 이어져도 안전)."""

    def querymany(self, qterms, **kwargs):
        return [{"query": q, "notfound": True} for q in qterms]


@pytest.fixture(autouse=True)
def _no_live_mygene(monkeypatch):
    """테스트 중 실수로라도 live mygene 호출이 발생하면 실패시킨다(G13/offline)."""

    class _Blocked:
        def querymany(self, *args, **kwargs):
            raise AssertionError("live mygene call attempted in offline test")

    monkeypatch.setattr(mygene, "MyGeneInfo", lambda: _Blocked())


def _install_notfound_mygene(monkeypatch):
    monkeypatch.setattr(mygene, "MyGeneInfo", lambda: _NotFoundClient())


def _make_mapper(cache_manager, organism="human", **kwargs):
    return SymbolMapper(cache_manager, organism=organism, **kwargs)


# --------------------------------------------------------------------------
# normalize_symbol (A6: species-aware casing)
# --------------------------------------------------------------------------

class TestNormalizeSymbol:
    def test_human_upper(self, tmp_path):
        cm = FakeCacheManager(tmp_path)
        assert _make_mapper(cm, "human").normalize_symbol("Tp53") == "TP53"

    def test_mouse_title(self, tmp_path):
        cm = FakeCacheManager(tmp_path)
        mapper = _make_mapper(cm, "mouse")
        assert mapper.normalize_symbol("TP53") == "Tp53"
        assert mapper.normalize_symbol("tp73") == "Tp73"

    def test_unsupported_organism(self, tmp_path):
        cm = FakeCacheManager(tmp_path)
        with pytest.raises(ValueError):
            _make_mapper(cm, "yeast")


# --------------------------------------------------------------------------
# local gene_info mapping (1차, offline)
# --------------------------------------------------------------------------

class TestLocalMapping:
    def test_primary_symbol_mapping(self, tmp_path):
        gi = _write_gene_info(tmp_path, 9606, HUMAN_ROWS, "gene_info_9606.tsv.gz")
        cm = FakeCacheManager(tmp_path)
        cm.install("human", gi)
        mapper = _make_mapper(cm, "human")

        result = mapper.map_symbols(["tp53", "BRCA1"])  # 대소문자 변형 입력도 매칭
        assert result == {"TP53": 7157, "BRCA1": 672}

    def test_synonym_mapping_mouse(self, tmp_path):
        """P0-7: mouse alias Tp73 → Trp73(GeneID 22099)이 Synonyms로 매핑된다."""
        gi = _write_gene_info(tmp_path, 10090, MOUSE_ROWS, "gene_info_10090.tsv.gz")
        cm = FakeCacheManager(tmp_path)
        cm.install("mouse", gi)
        mapper = _make_mapper(cm, "mouse")

        assert mapper.map_symbols(["Tp73"]) == {"Tp73": 22099}
        assert mapper.map_symbols(["BRCA1"])["Brca1"] == 12189  # 결과 키는 mouse casing
        assert mapper.map_symbols(["BRCA1"]) == {"Brca1": 12189}

    def test_both_primary_and_synonym_work(self, tmp_path):
        gi = _write_gene_info(tmp_path, 9606, HUMAN_ROWS, "gene_info_9606.tsv.gz")
        cm = FakeCacheManager(tmp_path)
        cm.install("human", gi)
        mapper = _make_mapper(cm, "human")
        assert mapper.map_symbols(["P53"]) == {"P53": 7157}   # alias
        assert mapper.map_symbols(["LFS1"]) == {"LFS1": 7157}  # 두 번째 alias

    def test_taxid_filter(self, tmp_path, monkeypatch):
        """9606+10090 혼합 파일에서 organism별로 자기 taxid 행만 매핑한다."""
        _install_notfound_mygene(monkeypatch)  # miss는 온라인으로 새지 않게 notfound 처리
        gi = _write_gene_info(tmp_path, 0, HUMAN_ROWS + MOUSE_ROWS, "gene_info_mixed.tsv.gz")
        cm = FakeCacheManager(tmp_path)
        cm.install("human", gi)
        cm.install("mouse", gi)

        human = _make_mapper(cm, "human")
        assert human.map_symbols(["Trp73", "TP53"]) == {"TRP73": None, "TP53": 7157}

        mouse = _make_mapper(cm, "mouse")
        assert mouse.map_symbols(["Trp73", "TP53"]) == {"Trp73": 22099, "Tp53": None}
        assert mouse.map_symbols(["P53"]) == {"P53": None}  # mouse에는 없는 human alias

    def test_ncbi_dash_meaning_no_synonyms(self, tmp_path):
        """NCBI의 '-' (별칭 없음) 표기는 매핑을 오염시키지 않는다."""
        gi = _write_gene_info(tmp_path, 9606, [(9606, 999, "GENEX", "-")], "gi_dash.tsv.gz")
        cm = FakeCacheManager(tmp_path)
        cm.install("human", gi)
        mapper = _make_mapper(cm, "human")
        assert mapper.map_symbols(["GENEX"]) == {"GENEX": 999}
        assert "NOT_A_GENE" not in mapper._load_map()  # '-'가 심볼로 들어가지 않음


# --------------------------------------------------------------------------
# pickle mapping cache (재사용: sha 일치 / 무효화: sha 불일치, 원자적 쓰기)
# --------------------------------------------------------------------------

class TestMappingCache:
    def _installed_human(self, tmp_path):
        gi = _write_gene_info(tmp_path, 9606, HUMAN_ROWS, "gene_info_9606.tsv.gz")
        cm = FakeCacheManager(tmp_path)
        cm.install("human", gi)
        return cm

    def test_cache_file_path(self, tmp_path):
        cm = self._installed_human(tmp_path)
        mapper = _make_mapper(cm, "human")
        assert mapper.cache_file() == Path(tmp_path) / "mapping" / "9606.pickle"
        assert _make_mapper(cm, "mouse").cache_file() == Path(tmp_path) / "mapping" / "10090.pickle"

    def test_pickle_reused_when_sha_matches(self, tmp_path, monkeypatch):
        """두 번째 인스턴스는 gene_info 재파싱 없이 pickle을 재사용한다."""
        cm = self._installed_human(tmp_path)
        calls = []
        orig = SymbolMapper._build_map_from_gene_info

        def counting(self, path):
            calls.append(path)
            return orig(self, path)

        monkeypatch.setattr(SymbolMapper, "_build_map_from_gene_info", counting)

        first = _make_mapper(cm, "human")
        assert first.map_symbols(["TP53"]) == {"TP53": 7157}
        assert len(calls) == 1

        second = _make_mapper(cm, "human")  # 새 인스턴스: 메모리 캐시 없음 → pickle 경로 검증
        assert second.map_symbols(["BRCA1"]) == {"BRCA1": 672}
        assert len(calls) == 1  # gene_info 재읽기 없음

    def test_invalidated_when_sha_mismatch(self, tmp_path, monkeypatch):
        """gene_info 내용 변경(sha 불일치) → pickle 폐기·재빌드."""
        cm = self._installed_human(tmp_path)
        mapper = _make_mapper(cm, "human")
        assert mapper.map_symbols(["TP53"]) == {"TP53": 7157}

        # gene_info에 새 유전자 추가 → sidecar sha 갱신
        gi2 = _write_gene_info(
            tmp_path, 9606, HUMAN_ROWS + [(9606, 12345, "NEWGENE", "")],
            "gene_info_9606.tsv.gz",  # 같은 경로, 다른 내용
        )
        cm.reinstall("human", gi2)

        result = mapper.map_symbols(["NEWGENE", "TP53"])
        assert result == {"NEWGENE": 12345, "TP53": 7157}

    def test_no_tmp_leftovers_after_build(self, tmp_path):
        cm = self._installed_human(tmp_path)
        mapper = _make_mapper(cm, "human")
        mapper.map_symbols(["TP53"])
        mapping_dir = Path(tmp_path) / "mapping"
        leftovers = [p.name for p in mapping_dir.iterdir() if p.name.endswith(".tmp")]
        assert leftovers == []


# --------------------------------------------------------------------------
# mygene fallback (2차, online — 전부 mock)
# --------------------------------------------------------------------------

class TestMygeneFallback:
    def _human_mapper(self, tmp_path):
        gi = _write_gene_info(tmp_path, 9606, HUMAN_ROWS, "gene_info_9606.tsv.gz")
        cm = FakeCacheManager(tmp_path)
        cm.install("human", gi)
        return _make_mapper(cm, "human")

    def test_fallback_maps_local_miss(self, tmp_path, monkeypatch):
        class _HitClient:
            def querymany(self, qterms, **kwargs):
                assert kwargs["scopes"] == "symbol"
                assert kwargs["species"] == 9606
                # mygene은 'entrezgene'을 str로 반환할 수 있다
                return [{"query": q, "entrezgene": "12345"} for q in qterms]

        monkeypatch.setattr(mygene, "MyGeneInfo", lambda: _HitClient())
        mapper = self._human_mapper(tmp_path)
        assert mapper.map_symbols(["NOTLOCAL"]) == {"NOTLOCAL": 12345}

    def test_fallback_handles_single_dict_reply(self, tmp_path, monkeypatch):
        class _SingleClient:
            def querymany(self, qterms, **kwargs):
                return {"query": qterms[0], "entrezgene": 9999}  # list 아닌 dict

        monkeypatch.setattr(mygene, "MyGeneInfo", lambda: _SingleClient())
        mapper = self._human_mapper(tmp_path)
        assert mapper.map_symbols(["ONLYONE"]) == {"ONLYONE": 9999}

    def test_fallback_notfound_and_hit_mixed(self, tmp_path, monkeypatch):
        class _MixedClient:
            def querymany(self, qterms, **kwargs):
                reply = []
                for q in qterms:
                    if q == "REALGENE":
                        reply.append({"query": q, "entrezgene": 7777})
                    else:
                        reply.append({"query": q, "notfound": True})
                return reply

        monkeypatch.setattr(mygene, "MyGeneInfo", lambda: _MixedClient())
        mapper = self._human_mapper(tmp_path)
        res = mapper.map_symbols(["REALGENE", "GHOST"])
        assert res == {"REALGENE": 7777, "GHOST": None}

    def test_fallback_failure_is_safe(self, tmp_path, monkeypatch, caplog):
        class _BoomClient:
            def querymany(self, *args, **kwargs):
                raise RuntimeError("mygene down")

        monkeypatch.setattr(mygene, "MyGeneInfo", lambda: _BoomClient())
        mapper = self._human_mapper(tmp_path)
        with caplog.at_level(logging.WARNING, logger="utils.gene_id_mapper"):
            res = mapper.map_symbols(["NOTLOCAL"])  # 크래시 없이 None
        assert res == {"NOTLOCAL": None}
        assert "mygene" in caplog.text

    def test_local_hit_does_not_call_mygene(self, tmp_path, monkeypatch):
        """로컬에서 전부 해결되면 mygene이 절대 호출되지 않는다(offline 원칙)."""
        called = []
        monkeypatch.setattr(
            mygene, "MyGeneInfo",
            lambda: type("_X", (), {"querymany": lambda *a, **k: called.append(1) or []})(),
        )
        mapper = self._human_mapper(tmp_path)
        assert mapper.map_symbols(["TP53", "BRCA1"]) == {"TP53": 7157, "BRCA1": 672}
        assert called == []


# --------------------------------------------------------------------------
# 결과 형태: dedupe / mapped_entrez / mapped_count(0건) / 빈 입력
# --------------------------------------------------------------------------

class TestResultShapes:
    def _mapper(self, tmp_path, rows=HUMAN_ROWS, organism="human"):
        gi = _write_gene_info(tmp_path, 9606 if organism == "human" else 10090,
                              rows, f"gene_info_{organism}.tsv.gz")
        cm = FakeCacheManager(tmp_path)
        cm.install(organism, gi)
        return _make_mapper(cm, organism)

    def test_dedupe_by_normalized_symbol(self, tmp_path, monkeypatch):
        _install_notfound_mygene(monkeypatch)
        mapper = self._mapper(tmp_path)
        res = mapper.map_symbols(["TP53", "tp53", "Tp53", "BRCA1"])
        assert res == {"TP53": 7157, "BRCA1": 672}  # 정규화 심볼 키, 중복 제거

    def test_mapped_entrez_convenience(self, tmp_path, monkeypatch):
        _install_notfound_mygene(monkeypatch)
        mapper = self._mapper(tmp_path)
        assert mapper.mapped_entrez(["TP53", "BRCA1", "NOPE"]) == [7157, 672]
        assert mapper.mapped_entrez(["NOPE", "GHOST"]) == []  # 순서·None 무시

    def test_mapped_count_zero_no_raise(self, tmp_path, monkeypatch):
        """매핑 0건: map_symbols는 all-None dict·mapped_count 0 — raise하지 않는다(G14)."""
        _install_notfound_mygene(monkeypatch)
        mapper = self._mapper(tmp_path)
        res = mapper.map_symbols(["NOPE", "GHOST"])
        assert res == {"NOPE": None, "GHOST": None}
        assert mapper.mapped_count(["NOPE", "GHOST"]) == 0
        assert mapper.mapped_count(["TP53"]) == 1

    def test_empty_input(self, tmp_path):
        mapper = self._mapper(tmp_path)
        assert mapper.map_symbols([]) == {}
        assert mapper.mapped_entrez([]) == []
        assert mapper.mapped_count([]) == 0
