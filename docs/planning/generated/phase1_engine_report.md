# Phase 1 — Enrichment Engine: 모듈 구현 보고서 (G002)

- Date: 2026-09-03 (UTC+09:00) · Repo: `/home/ygkim/cmg-seqviewer`
- Authority: `docs/planning/ON_GO_ENRICHMENT_IMPLEMENTATION_PLAN.md` v1.1 (§10-1 Phase 1, §8 파일 맵, §11 G 해소, §12 테스트)
- 기준: Phase 0 PoC 게이트 통과 (P0-1..P0-7, ADR-1..5 확정)

---

## Summary

Phase 1 엔진 계층 구현 완료. 신규 모듈 5개 + 테스트 인프라(pytest.ini/conftest/fixtures) + 컨버터 단일
진실원천 리팩터(go_kegg_loader) + 데이터로더 fold 중복 제거 + drift 수정(F9 회귀 세트 green).

**테스트 현황**: 전체 `pytest` 146 passed (네트워크 4건은 `-m network` 별도, 오프라인 1건 `-m offline`).

| 파일 | 역할 | 테스트 |
|---|---|---|
| `src/models/enrichment_models.py` | EnrichmentRequest/Result/ErrorKind (직렬화 recipe) | 커버 (analyzer 15) |
| `src/utils/enrichment_analyzer.py` | EnrichmentAnalyzer (ORA/라우팅/표준 변환/prerank 인터페이스) | 19 (analyzer+converter+통합) |
| `src/utils/enrichment_cache.py` | CacheManager (원자적·사이드카·TTL·스트림필터·detect_online) | 26 |
| `src/utils/gene_id_mapper.py` | SymbolMapper (gene_info 로컬 우선 + mygene fallback + 역매핑) | 21 |
| `src/utils/deg_input.py` | DEG 3소스 추출 + ranked 인터페이스 (A6 casing) | 45 |
| `src/utils/go_kegg_loader.py` | `standardize_go_dataframe()` 단일 진실원천 승격 + [;/,] 정규화(A5) | 커버 (converter 16) |
| `src/utils/data_path_config.py` | `get_app_data_dir()`/`get_enrichment_cache_dir()` (ADR-3 3A) | 커버 |
| `pytest.ini`/`test/conftest.py`/`fixtures` | 마커 network/offline/qt + block_network 구성 | — |
| `src/utils/data_loader.py` | fold 중복 제거 — 공용 함수 위임 (§6.5) | 회귀 green |

## 제약/결정

1. **KEGG term_id 4A 기본** (§6.6/A1, P0-2 실측): 온라인 KEGG Term에 hsa id 없음(0/107) → term_id 빈 값,
   `^hsa\d+` 방어적 파싱만. 클러스터링/네트워크는 description+`_gene_set` 키(P0-5 검증). 4B(KEGG REST)는 미채택(옵션).
2. **statsmodels pin 결정 실행**: goatools ↔ statsmodels 0.15 비호환(P0-3) → venv를 0.14.6으로 고정 + requirements/setup
   `statsmodels>=0.14.0,<0.15`. pandas 3.0.5와 0.14.6 호환 확인. 미니-fixture fdr_bh 손계산 대조 테스트로 퇴행 방지.
3. **goatools 1.6.5 API 실측 반영**: `GOEnrichmentStudyNS`(구 goea_go_enrich_nss), `get_ns2assc()`(구 get_assoc_nss),
   `methods=['fdr_bh']`(fisher_scipy 문자열 제거). plan §6.2/§15 문서 갱신.
4. **Gene2GoReader gzip 미지원 실측**: 캐시는 gzip 저장, 소비자용 plain tsv를 mtime 기반 1회 압축해제
   (`_plain_gene2go`) — PoC의 `e2go_human.tsv` 경로와 동일.
5. **라벨 왕복 수정 (§6.3)**: 기존 `_extract_direction_ontology`가 `UP_KEGG`/`DOWN_KEGG`(방향-프리픽스)를
   TOTAL로 오독 → 공용 파서에 프리픽스 분기 추가(기존 KEGG_UP/UP_BP 관례 보존하는 순수 상위집합). 왕복 테스트 고정.
6. **P0-6 drift 수정**: `is_significant` @property→메서드(2클래스), `Dataset(column_mapping=)` 추가(원본→표준 rename,
   기존 호출자 무영향). `test_get_filtered_data` 산술 자가모순(데이터상 3행) 기대값 정정 2→3 (주석 문서화).
7. **2A 가드** (G8/ADR-2): `enrich_ora`는 background 지정+auto/online 시 로컬 강제 + W2 경고; `_enrichr_call` 시그니처에
   background 없음. `-m network` Speedrichr 라우팅 pin 테스트 추가.
8. **mouse (A3)**: GO 온라인 라이브러리 부재(P0-7) → engine=online/auto여도 mouse GO는 GOATOOLS 로컬 강제 + W1;
   mouse KEGG(`KEGG_2019_Mouse`)는 온라인 허용.
9. **오프라인 KEGG (F3)**: ADR-1 Option 1 → local/offline에서 KEGG는 비활성 + W1 안내 (ErrorKind.OFFLINE_KEGG
   분류 준비, enrich_ora는 부분 결과+경고 반환).
10. **enrich_prerank**: 인터페이스 선언만 (Phase 4 §10-4 구현 — plan G16).

## 수용 기준 (P1-1..P1-7)

| 기준 | 결과 | 근거 |
|---|---|---|
| **P1-1** 표준화 파이프라인 동일 출력 (리팩터 회귀) | PASS | `standardize_go_dataframe` == 기존 메서드 순차 호출 (프레임 동등 단언) + 전체 스위트 146 green (기존 로더 경로 포함) |
| **P1-2** ORA → §6.3~6.6 계약 | PASS | converter 16: 다구분자 `_gene_set`/라벨 왕복/ratio/fold/term_id 정책/canonical description/로더 재통과 |
| **P1-3** 3종 DEG 입력 추출 단위 | PASS | deg_input 45: 경계/방향/빈 입력/변종 컬럼 폴백(BH 포함)/casing/결정성 |
| **P1-4** 오프라인 매핑 (gene_info 캐시만) | PASS | mapper 21: mygene 실호출 금지 fixture, 로컬+synonym 매핑, pickle sha 재사용/무효화; block_network 오프라인 1건 |
| **P1-5** 캐시 원자성·TTL | PASS | cache 26(24+2 network): .tmp 잔존 없음, 사이드카/sha256, TTL fresh/stale/실패 유지+W2, 종별 스트림 필터, 동시 dedupe — 경계 리뷰(gen-1) 후 픽스처 실형식 재생성 반영 재파라미터화 완료 |
| **P1-6** mock 기반 net-path green (마커 분리) | PASS | 기본 **146 passed** (network 제외, 2026-09-03 재실행), `-m network` 4 passed, `-m offline` 1 passed |
| **P1-7** (4B 채택 시) KEGG REST mock | N/A | 4B 미채택(옵션 유지) — 4A 기본 검증 (P1-2 커버) |

## 추가 검증 (architect 필수항목 응답)

1. **2A 가드 + Speedrichr pin** — `test_background_forces_local` + `-m network` `test_speedrichr_route_pinned`
   (gseapy 1.3.1 소스에 speedrichr/background 라우팅 경로 존재 확인 + _enrichr_call에 background 파라미터 부재 단언).
2. **statsmodels pin + fdr_bh 레퍼런스** — venv 0.14.6, requirements/setup `<0.15`; `TestGoatoolsIntegration`이
   mini-obo+sample gene2go로 goatools p값을 scipy two-sided fisher + statsmodels fdr_bh 독립 계산과 대조.
3. **clean-process 메모리 실측** — `/tmp/phase1_memmeas/report.json`: 실다운로드(obo 30MB/1.95s, gene2go 1.38GB/79.6s, gene_info 1.57GB/106.3s, 스트림 필터 RSS 증가 0) 후 로컬 GO 분석 계층 집계 증가 **+33MB**(obo파싱+assoc+매퍼+NS init+run) — P3-6 ≤800MB 상한 대비 여유. 실 GOATOOLS run: 446,674 annotations/20,363 genes/17,987 GOs → 6,736 terms.
4. **실데이터 로컬 경로 e2e** — 동일 캐시로 `EnrichmentAnalyzer.enrich_ora(local)`+`to_standard`: 10.5s+2.8s → 9,999행(BP/CC/MF 3,333 each), term_id 100% GO, `_gene_set` 9,999/9,999, 경고 0건. (fdr<0.05 0건은 self-background 기대 — Phase 2가 DE 전체 배경 전달.)
5. **drift 수정으로 F9 회귀 세트 green** — 23 passed (test_models/test_statistics/test_fsm/test_figure_bundle_export).
6. **실데이터 매핑 픽스(통합 실측 발견)**: NCBI gene_info 헤더는 `#Format:`/`#tax_id` 주석 — `comment='#'+header=None` 위치 기반 읽기로 교체(PoC 레시피 재검증, 픽스처도 실형식 갱신).
7. **GOATOOLS 전체 로컬 경로 실측** — `TestGoatoolsIntegration` + 라이브 로컬 GO 런(메모리 측정 스크립트 내).
8. **경계 리뷰(gen-1) 반영 하드닝 배치**: cache 필터 테스트 재파라미터화(실 NCBI 픽스처), `requirements/setup`에 `goatools>=1.6.0` 추가, `ErrorKind.DOWNLOAD` 로컬 경로 분류 + 예외에 warnings 첨부(EMPTY/NETWORK 포함), `engine_effective` 스탬프→`engine_used` 유도, plain gene2go tsv 원자적 쓰기, SymbolMapper 'nan' 문자열 가드, detect_online 응답 상태 검사, enrich_ora 경계 A6 casing, setup.py 3.9 클래스파이어 제거. **재검증: 146+4+1 전부 green.**

## G 해소

G2(캐시 경로 3A) · G3(deg_input 3소스) · G4(_gene_set) · G5(라벨/Dataset 규칙) · G6(ratio/fold 단일화) ·
G7(KEGG term_id 4A) · G8(2A 가드) · G9(로컬 매핑/오프라인) · G10(mouse taxid 10090) · G13(테스트 인프라/gate) ·
G14(ErrorKind 명시 UX) · G15(메타데이터/recipe) · G16(prerank 인터페이스) · A1/A4/A5/A6 · F1/F4/F7/F8

## 남은 Phase 2 의존

- Worker 재설계(G12 — EnrichmentWorker), Dialog(모드 배너/배경/F10 툴팁), main_window/presenter 등록,
  help/docs 동기화(A7 명칭 구분), pytest-qt e2e.
- 4B(KEGG REST)는 Phase 1에서 미채택 — 필요 시 후속.
- 로컬 population: v1 self-background(Phase 2가 "DE 테이블 전체 유전자"를 background로 전달 — §6.2 ADR-2 2A).