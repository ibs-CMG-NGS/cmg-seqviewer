"""
Enrichment engine models (plan G12/A2/F6).

- EnrichmentRequest : 직렬화 가능한 분석 요청 — `metadata['enrichment_recipe']` 재실행 경로 (A2/F6).
- EnrichmentResult  : 엔진 결과 — worker → presenter → Dataset 등록에 사용 (G12).
- ErrorKind         : 실패 분류 — 명시적 UX용 (G14).

데이터프레임 컬럼 계약은 §6.3~6.6 (StandardColumns + `_gene_set`)이며
`enrichment_analyzer.EnrichmentAnalyzer.to_standard()`가 생성한다.
"""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd


class ErrorKind(str, Enum):
    """실패 분류 (G14 — 조용한 fallback 금지)."""

    MAPPING = "mapping"                # 매핑 0건 → 분석 진행 불가 (G9)
    NO_INPUT_GENES = "no_input_genes"  # 입력 DEG 없음 (임계값 결과 0)
    NETWORK = "network"                # online 경로 네트워크 실패
    DOWNLOAD = "download"              # 캐시 다운로드 실패 (오프라인 + 캐시 부재)
    EMPTY_RESULT = "empty_result"      # 결과 0행
    OFFLINE_KEGG = "offline_kegg"      # 오프라인 KEGG 비활성 (F3 — ADR-1 결과 종속)
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


# direction 값 (유효성 검증용)
VALID_DIRECTIONS = ("UP", "DOWN", "TOTAL")
# ontology 값
VALID_ONTOLOGIES = ("BP", "CC", "MF", "KEGG")
# 엔진 모드
VALID_ENGINES = ("auto", "online", "local", "offline")
# 종
VALID_ORGANISMS = ("human", "mouse")


@dataclass
class EnrichmentRequest:
    """분석 요청 (직렬화 가능 — enrichment_recipe 계약, A2/F6)."""

    source: str                          # "dataset" | "paste" | "meta"
    # source ① 단일 DE 데이터셋
    dataset_name: Optional[str] = None
    # 공통 임계값 (source ① 필터 / source ③ meta 컷오프)
    fc_min: Optional[float] = None       # abs(log2fc) >= fc_min
    fdr_max: Optional[float] = None      # adj_pvalue <= fdr_max
    direction: str = "TOTAL"             # UP | DOWN | TOTAL
    # source ② 붙여넣기 / ① 필터 결과 심볼 목록
    gene_list: List[str] = field(default_factory=list)
    # source ③ meta-signature
    meta_cutoff: Optional[float] = None  # meta_fdr_fisher <= cutoff (컬럼 부재 시 BH 폴백)
    meta_direction_required: bool = False  # meta_direction concordant 권장
    # 종/라이브러리/엔진 (A3/A4)
    organism: str = "human"              # human | mouse (mouse는 로컬 우선 — A3)
    libraries: List[str] = field(default_factory=list)  # ["BP","CC","MF","KEGG"] (F10: 동일 ontology 1개)
    engine: str = "auto"                 # auto | online | local | offline
    background: Optional[List[str]] = None  # 커스텀 background → 로컬 강제 (G8/ADR-2 2A)
    # Phase 4 prerank (G16) — [(symbol, score)]
    ranked: Optional[List[Tuple[str, float]]] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> List[str]:
        """요청 유효성 검사 — 문제 목록 반환 (빈 목록 = 유효)."""
        problems = []
        if self.source not in ("dataset", "paste", "meta"):
            problems.append(f"unknown source: {self.source}")
        if self.direction not in VALID_DIRECTIONS:
            problems.append(f"invalid direction: {self.direction}")
        if self.organism not in VALID_ORGANISMS:
            problems.append(f"invalid organism: {self.organism}")
        if self.engine not in VALID_ENGINES:
            problems.append(f"invalid engine: {self.engine}")
        for lib in self.libraries:
            if lib not in VALID_ONTOLOGIES:
                problems.append(f"invalid library: {lib}")
        if self.source == "dataset" and not self.dataset_name:
            problems.append("dataset source requires dataset_name")
        if self.source == "meta" and self.meta_cutoff is None:
            problems.append("meta source requires meta_cutoff")
        return problems

    def to_recipe_dict(self) -> Dict[str, Any]:
        """JSON-safe recipe (metadata['enrichment_recipe'])."""
        d = asdict(self)
        if d.get("ranked") is not None:
            d["ranked"] = [[sym, float(score)] for sym, score in d["ranked"]]
        return d

    @classmethod
    def from_recipe_dict(cls, d: Dict[str, Any]) -> "EnrichmentRequest":
        """recipe dict → 요청 (metadata['enrichment_recipe']에서 복원)."""
        data = dict(d)
        ranked = data.get("ranked")
        if ranked is not None:
            data["ranked"] = [(str(sym), float(score)) for sym, score in ranked]
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class EnrichmentResult:
    """엔진 실행 결과 (G12 — finished(EnrichmentResult))."""

    dataframe: pd.DataFrame           # 표준 병합 프레임 (§6.3~6.6)
    request: EnrichmentRequest
    metadata: Dict[str, Any] = field(default_factory=dict)  # §6.9 재현성 메타데이터
    warnings: List[str] = field(default_factory=list)       # W1/W2
    engine_used: str = "auto"         # 실제 사용 엔진 (auto 라우팅 결과)
    dataset_name: str = ""            # "Enrichment: {입력명}" (§6.3)

    def to_recipe_dict(self) -> Dict[str, Any]:
        """결과 재실행 레시피 (metadata['enrichment_recipe']에 기록용)."""
        return self.request.to_recipe_dict()
