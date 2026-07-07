"""
Genomic annotation 카테고리 정규화 · 색상 · 정렬 (단일 소스).

ATAC peak의 annotation 문자열(HOMER/ChIPseeker 형식)을 대분류 카테고리로 통일하고,
카테고리별 고정 색상과 표준 정렬 순서를 제공한다. GenomicDistributionDialog(단일 pie)와
AnnotationComparisonDialog(다중 누적 막대)가 이 모듈을 공유해 표기·색상을 일치시킨다.
"""
from typing import Iterable, List

# 원본 표기(괄호 제거·소문자) → 표준 카테고리명
_CANONICAL = {
    'promoter': 'Promoter',
    'promoter-tss': 'Promoter',
    'distal intergenic': 'Distal Intergenic',
    'intergenic': 'Intergenic',
    'intron': 'Intron',
    'exon': 'Exon',
    'cds': 'Exon',
    "3' utr": "3' UTR",
    "5' utr": "5' UTR",
    'downstream': 'Downstream',
    'tts': 'TTS',
    'enhancer': 'Enhancer',
}

# 표준 정렬 순서 (참조 그림의 feature 나열 관례)
_CANONICAL_ORDER = [
    'Promoter', "5' UTR", "3' UTR", 'Exon', 'Intron',
    'Downstream', 'TTS', 'Distal Intergenic', 'Intergenic', 'Enhancer',
]

# 카테고리별 고정 색상 (참조 그림 C 팔레트 근사)
CATEGORY_COLORS = {
    'Promoter':          '#5b9bd5',  # 파랑
    "5' UTR":            '#93c47d',  # 초록
    "3' UTR":            '#f4a2a2',  # 살몬
    'Exon':              '#e69138',  # 주황
    'Intron':            '#b4a7d6',  # 연보라
    'Downstream':        '#3d5a99',  # 남색
    'TTS':               '#c27ba0',  # 자주
    'Distal Intergenic': '#ffd966',  # 노랑
    'Intergenic':        '#f9cb9c',  # 연주황
    'Enhancer':          '#76a5af',  # 청록
}

# 표준에 없는 카테고리에 순서대로 배정할 fallback 팔레트
_FALLBACK_COLORS = [
    '#a6a6a6', '#8c8c8c', '#bcbd22', '#17becf', '#7f7f7f',
    '#c49c94', '#dbdb8d', '#9edae5', '#c7c7c7', '#f7b6d2',
]


def normalize_annotation(raw) -> str:
    """세부 annotation 문자열을 표준 대분류로 정규화.

    예) "intron (ENSMUSG..., intron 1 of 15)" → "Intron"
        "Promoter (<=1kb)" / "Promoter-TSS (Gata1)" → "Promoter"
        "Distal Intergenic" → "Distal Intergenic"
    """
    if not isinstance(raw, str) or not raw.strip():
        return "Unknown"
    stripped = raw.split('(')[0].strip()
    canonical = _CANONICAL.get(stripped.lower())
    if canonical:
        return canonical
    # 미정의 표기: 첫 글자만 대문자로 (기존 동작 유지)
    return stripped[0].upper() + stripped[1:] if stripped else "Unknown"


def order_categories(cats: Iterable[str]) -> List[str]:
    """표준 순서를 앞에, 미정의 카테고리는 알파벳순으로 뒤에 배치."""
    present = set(cats)
    ordered = [c for c in _CANONICAL_ORDER if c in present]
    extras = sorted(present - set(ordered))
    return ordered + extras


def color_for_category(cat: str, fallback_index: int = 0) -> str:
    """카테고리 고정 색상, 없으면 fallback 팔레트에서 순환 배정."""
    if cat in CATEGORY_COLORS:
        return CATEGORY_COLORS[cat]
    return _FALLBACK_COLORS[fallback_index % len(_FALLBACK_COLORS)]
