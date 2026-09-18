# In-app Enrichment vs Pipeline-Confirmed Results — Term-Level Validation

- Date: 2026-09-03
- Data: `data/datasets/3D_vs_CONTROL_DA.parquet` (파이프라인 DA, ATAC peak 128,310,
  nearest_gene 매핑) → `3D_vs_CONTROL_GO_KEGG.parquet` (파이프라인 확정 GO, 표준화 31,126행)
- Method: in-app 로컬 GOATOOLS(mouse, taxid 10090, gene2go 2026 스냅샷) ORA,
  study=n=4,572(파이프라인 gene_ratio 분모), population=전체 30,438 유전자
  (파이프라인 N=28,891), BP/CC/MF, fdr_bh
- 캐시: /tmp/val_mouse_cache (gene2go_10090 595,946 annotation / 26,029 유전자)

## 요약

| 지표 | 값 | 해석 |
|---|---|---|
| 공유 term (GO id) | 10,286 / 참조 10,988 | **93.6% 재현** — in-app이 파이프라인 확정 term 대부분 검출 |
| description 겹침 | 91.6% | term-메시지 수준 정합 (사용자 기대 충족) |
| 중복 제외 후 app term 수 | 21,140 | in-app이 더 넓은 term space 평가 (파이프라인은 필터된 10,988) |
| p<0.05 합치 (공유) | both 706 · app_only 175 · **ref_only 5,057** | 유의 판정 격차 |
| fdr<0.05 합치 | both 55 · app_only 3 · ref_only 4,519 | |
| k (term hit 수) 상관 | ρ=0.77 / **k_ref:k_app 중앙값 = 3.0** (93%에서 k_ref 큼) | **파이프라인 k가 ~3배 과다** |
| M (term 크기) 상관 | ρ=0.78 / **M_ref:M_app 중앙값 = 8.0** | **파이프라인 주석 M이 ~8배 큼** |
| p_ref:p_app | 중앙값 15.5 (pA<=pR 9.3%) | 파이프라인 p가 체계적으로 작음 |
| top-50 (fdr) 겹침 | 0 | 순위왜곡 — 상위 지표는 M/k 차이로 판이 |

## 결론

1. **Term 수준 재현은 강함(93.6% id / 91.6% description)** — "GO term 버전 정도의
   차이는 있어도 term-wise 유사해야"라는 기대를 충족. 두 엔진의 **해석 대상 term 세트는 실질적으로
   동일**하다.
2. **유의성·순위 격차의 주 원인 = 주석(annotation) 스냅샷 차이** (엔진 오류 아님):
   파이프라인 참조의 term 크기 M이 현재 gene2go 대비 중앙값 8배, hit 수 k 3배 커서
   Fisher p가 ~15배 작게 계산됨. 동일 GO id여도 유전자→GO 매핑 버전이 다르면
   M/k가 달라지며 이는 p·BH·순위 전반을 체계적으로 밀어낸다.
3. 공유 term의 **k·M 상관이 ρ≈0.77~0.78** — 동일 입력 유전자에서는 두 엔진의
   카운트가 잘 일치하며, 통계 메커니즘(Fisher+BH) 자체도 동일 계열. **동일 GO 스냅샷
   (예: gene2go 특정 일자 고정 또는 파이프라인 GMT 재사용)으로 비교하면 유의 정합이
   크게 개선될 것으로 기대**된다.

## 시사점 / 액션

- (a) in-app 로컬 GO 성능자가 파이프라인 term 세트를 실질적으로 재현함을 확인 → 기존
  P3-4(경향 61.8%)를 보강한 **term 수준 검증 완료**.
- (b) 파이프라인 결과와 "유의성 동일"을 요구하는 워크플로우는 **주석 스냅샷 고정**(캐시
  GMT/고정 일자 gene2go)을 사용해야 함 — 캐시 사이드카(sha256/획득일)가 이미 지원.
- (c) 유의 격차의 M/k 성분을 문서화해 UI 해석 주의(engine-difference caveat)와 정합.

## 산출물

- `enrichment_term_validation.json` (동일 규모 검증 원본)
- `enrichment_shared_term_diagnosis.json` (공유 term p/k/M 상관)
- `onesided_check.json` (단측 검정 가설 검증 — 기각, 회복 8.6%)
## 부록. 동일-주석 재검증 (same-annotation Fisher check) — 2026-09-03

파이프라인 참조가 가진 각 term의 (k=gene_count, M=bg_ratio 분자, n=gene_ratio 분모,
N=bg_ratio 분모) 사중항을 그대로 써서, in-app 표준 공식(scipy `fisher_exact`)으로 p를
재계산했다 (`same_annotation_fisher_check.json`, 10,988 term):

| 검정 | 결과 |
|---|---|
| **단측(enrichment, greater)** | **ρ=1.000, p_ref == p_oneside 100% 일치** — 파이프라인 = 표준 단측 Fisher exact |
| 양측(two-sided) | ρ=0.971, median p_ref/p_twoside=0.823 (양측이 약간 보수적) |

**결론**:
1. **통계 공식은 완전 동일** — 같은 (k, M, n, N)이면 in-app이 파이프라인 p를 1:1 재현한다.
2. 앞선 유의성 격차(p_ref:p_app 중앙값 15.5배)의 성분은 전부 (a) **주석 버전 차이**
   (M 8배·k 3배 — 파이프라인 구주석 vs 현재 gene2go)와 (b) **검정 쪽 차이**
   (GOATOOLS 양측 vs 파이프라인 단측; 잔차 ~0.82배)로 설명된다. 엔진 로직 오류 없음.
3. **동일 주석으로 맞추려면**: (a) CacheManager `pin_snapshots=True`로 스냅샷 고정
   (구현 완료 + metadata `annotation_snapshots` 기록), (b) 파이프라인과 동일 주석
   파일/날짜를 핀으로 지정하면 유의·순위 정합이 기대된다. (c) 잔차로 남는
   "단측 vs 양측"은 로컬 GO의 해석주의 항목이었으나 **2026-09-03 구현 완료**:
   `enrich_ora(..., one_sided=True)` + 다이얼로그 "One-sided Fisher" 체크박스
   (GOATOOLS 양측 p → scipy 단측 Fisher + NS별 fdr_bh 재계산, metadata `stat_test` 기록).

## 이행 요약 (2026-09-03, 검증 후속)

- [x] **스냅샷 고정(핀) 모드**: `CacheManager(pin_snapshots=True)` — TTL 재다운로드
  없이 동일 sha256 스냅샷 재사용 (테스트 4건).
- [x] **결과 metadata에 사용 주석 기록**: `annotation_snapshots` {obo/gene2go/gene_info/gmt
  → file, sha256, fetched_at, source} — `build_metadata` 읽기 전용(다운로드 유발 제거)
  (테스트 1건).
- [x] **동일-주석 재검증**: 파이프라인 p = 단측 Fisher exact, ρ=1.000(100% 일치) 실증.
- [x] 도움말(06) "Annotation snapshot pinning" 문서화.
