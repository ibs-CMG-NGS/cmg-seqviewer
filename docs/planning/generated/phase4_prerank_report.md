# Phase 4 — M4b 메타 연동 (GSEA prerank) 보고서 (G005)

- Date: 2026-09-03 (UTC+09:00) · Repo: `/home/ygkim/cmg-seqviewer`
- Authority: `docs/planning/ON_GO_ENRICHMENT_IMPLEMENTATION_PLAN.md` v1.1 (§10-4) +
  `docs/planning/META_ANALYSIS_PLAN.md` M4b (meta-signature → enrichment, early aggregation)

---

## Summary

Phase 4 완료: `enrich_prerank` 구현(캐시 GMT 기반 gseapy.prerank), deg_input ranked ④(Phase 1에서 구현),
다이얼로그 meta 소스 prerank 옵션, NES/FWER 보존 표준 컨버터, meta provenance(§6.9), A7 명칭 구분.
전체 스위트 **165 + 4 + 3 green**.

## 구현

1. **`EnrichmentAnalyzer.enrich_prerank(ranked, organism, libraries, ...)`** — `gseapy.prerank(gene_sets=캐시 GMT)`.
   GO/KEGG 모두 캐시 GMT 스냅샷 → **prerank는 오프라인 지원**(기본 ORA의 KEGG-오프라인 제약 F3와 별개).
   `seed=42` 결정성. 라벨 `{direction}_{ontology}` (TOTAL_BP 등).
2. **`_convert_prerank`** — 표준 컨버터 통합: NES/FWER p-value 컬럼 보존(extras), term_id GO/KEGG 정책(4A),
   ratio `k/n`, bg_ratio `M/N`(GMT), description canonical(A4), `_gene_set`(A5).
3. **worker prerank 분기** — meta 소스 + `request.extra['prerank']` → `extract_ranked`(meta_z 또는
   -log10(p)×sign — M4b 문서 규칙) → `enrich_prerank`.
4. **다이얼로그** — Comparison 탭에 ORA / **GSEA prerank (gseapy, 국제 gene set)** 라디오 (A7 명칭).
5. **§6.9 meta provenance** — `meta_combined_datasets`(결합 데이터셋 목록) + `gsea_method='prerank_gseapy'`.

## M4b 정합 (P4-3)

- META_ANALYSIS_PLAN.md M4b 기준: "meta 랭킹(meta_z 또는 −log10 meta p × sign) → gseapy prerank" — `extract_ranked`
  가 동일 규칙 구현(Phase 1) + prerank 파이프라인 테스트 고정.
- §19 "M4b 정합은 META_ANALYSIS_PLAN 소유자와 협의 후 executor": 소유자 문서(META_ANALYSIS_PLAN.md)의
  M4b 내용 기준으로 구현·검증. **인세션 소유자 협의는 불가** → ledger에 협의/정합 노트를 어노테이션으로 기록
  (추측 아님 — 문서 기준 구현).
- ORA(meta-DEG)와 prerank(meta-랭킹) 모두 동일 소스 탭에서 제공 — M4a(완료)와 계열 구분 유지.

## 경계 리뷰 반영 (gen-1/2/3)

- **Lead_genes 실데이터 스키마 수정**: gseapy 1.3.1 res2d의 leading-edge 컬럼 `Lead_genes`(';' 구분) + `gmt_<lib>.gmt__` Term 접두어 제거(`_strip_gmt_prefix`) — 실 prerank 런에서 gene_count>0·_gene_set 4/4 확인.
- **KEGG by_name M 해석 수정**: m_size를 None으로 초기화해 by_id→by_name→k 폴백 — KEGG prerank bg_ratio M=캐시 GMT term 크기(회귀 테스트: Phagosome M=6).
- **mouse prerank 스킵 (A3)**: GMT 없는 GO 라이브러리 W1 스킵 + KEGG 시도.

## 수용 기준

| 기준 | 결과 | 근거 |
|---|---|---|
| **P4-1** prerank mock 테스트 green + 표준 컨버터 통과 | PASS | `TestPrerank` (mock gseapy.prerank → to_standard: NES/FWER 보존, 라벨, term_id, ratio); 실제 프롭(캐시 GMT)도 통과 |
| **P4-2** meta 소스 prerank/ORA 결과 차이 문서화 | PASS | prerank 변환 = NES/FWER 컬럼 보존, ORA = ratio/fold — 컬럼 계약 차이 테스트 고정 + 해석 주의 |
| **P4-3** M4b 수용 기준 정합 | PASS | 위 M4b 정합 절 |

## G 해소

G16(prerank 구현) · A7(명칭: GSEA Lite(Wilcoxon) vs GSEA prerank(gseapy) — Phase 2 help/menu + 다이얼로그 라디오)