# Phase 2 — UI: EnrichmentAnalysisDialog + Worker 재설계 보고서 (G003)

- Date: 2026-09-03 (UTC+09:00) · Repo: `/home/ygkim/cmg-seqviewer`
- Authority: `docs/planning/ON_GO_ENRICHMENT_IMPLEMENTATION_PLAN.md` v1.1 (§10-2 Phase 2, §8 파일 맵)

---

## Summary

Phase 2 UI 완료: 분석 다이얼로그 + EnrichmentWorker 재설계 + 메뉴/발표자 등록 + help/docs 동기화.
전체 스위트 **154 passed + 4 network** (기존 146 + 다이얼로그 e2e 8).

| 파일 | 변경 | 확인 |
|---|---|---|
| `src/workers/go_workers.py` | TODO 스텁 `GOEnrichmentWorker` → `EnrichmentWorker(QThread)` (progress/result_ready(EnrichmentResult)/failed(ErrorPayload)+cancel); `GOClusteringWorker` 유지 | e2e + 스위트 |
| `src/gui/enrichment_analysis_dialog.py` (신규) | 소스 탭 3종, 임계값, 종(mouse 로컬 배너 A3), 라이브러리(F10 툴팁), 모드(Auto 표/오프라인 배너 F3/QSettings 토글 F1), background 파일, 진행/취소/요약 | pytest-qt 8 |
| `src/gui/main_window.py` | Analysis 메뉴 `🧬 GO/KEGG Enrichment Analysis...` (GSEA Lite 직후), `_on_enrichment_analysis`, P2-1 활성화 훅 | P2-1 검증 |
| `src/presenters/main_presenter.py` | `register_enrichment_result(result)` — unique name/등록/탭/`dataset_loaded`/audit + `enrichment_recipe` (G11/A2/F6) | e2e |
| `src/gui/help_dialog.py` | F1 신규 섹션 + **GSEA Lite(Wilcoxon) vs GSEA prerank(gseapy) 명칭 구분 (A7)** | — |
| `docs/user/user-guide.md` | enrichment 섹션(모드/background/프라이버시/캐시/KEGG 제약/Python 3.10+/A7) | — |
| `test/test_enrichment_dialog.py` (신규) | pytest-qt e2e 8건 (+보강 2건) | 10 passed |

## 경계 리뷰(gen-1) 반영 하드닝 (architect P2-1/P2-2/P3)

- **population 분리**: `enrich_ora(population_symbols=)` 파라미터 신설 — custom background(2A 강제)와 DE 전체
  population을 분리. worker는 source=dataset에서 engine 무관(자동 라우팅·mouse 포함) population_symbols 전달.
  온라인 경로는 미사용(2A 미발동 테스트 고정).
- **QThread 수명**: closeEvent에서 cancel→wait(15s)→terminate (부분 결과 폐기, destroy-while-running 크래시 방지).
- **F1 QSettings 기록**: 엔진 선택 변경 시 `enrichment/engine`·`enrichment/offline` 기록 (읽기 전용이던 토글 폐쇄).
- **오류 UX 테스트 보강**: EMPTY_RESULT / NO_INPUT_GENES 페이로드 → 다이얼로그 요약 표시 파라미터화 테스트.
- P3 잔여(비차단): restored `_gene_set` list 재복원은 Phase 3 P3-7에서 검증; GOClusteringWorker kappa 파라미터는
  plan §8 "유지" 대상 pre-existing 코드로 유지(문서화).

## 수용 기준 (P2-1..P2-6)

| 기준 | 결과 | 근거 |
|---|---|---|
| **P2-1** 메뉴 DE 로드 시 활성, GO_ANALYSIS 비활성 | PASS | offscreen MainWindow 실측: 초기 disabled → DE 로드 True → GO_ANALYSIS False |
| **P2-2** 3소스 → Dataset 등록 → 탭 → Bar/Dot/Cluster/Network 재사용 | PASS | e2e 3소스 각각 등록 + `GOBarChartDialog/GODotPlotDialog/GONetworkDialog` 크래시 없음 |
| **P2-3** 오프라인/빈 결과/타임아웃/rate-limit/매핑 0건 명시 UX, **KEGG 배너 ADR-1 정합** | PASS | ErrorPayload(kind)별 다이얼로그 안내; DOWNLOAD(캐시 부재 첫 실행) 테스트; offline KEGG 미포함→안내(F3) |
| **P2-4** 취소 시 부분 결과 폐기, 크래시 없음 | PASS | cancel e2e: cancelled 플래그 + 미등록 확인 |
| **P2-5** help/docs 동기화(명칭 구분 포함) | PASS | help_dialog 섹션 + A7 + user-guide 업데이트 |
| **P2-6** 저장/복원 시 행 복원 + recipe 보존 | PASS(범위) | v1 non-goal(A2/F6): in-memory Dataset은 파일 기반 기존 GO_ANALYSIS 경로로 복원, `metadata['enrichment_recipe']` JSON-safe 직렬화 + 등록 시 보존(e2e 어서트) — 자동 재실행 없음(안내만) |

## G 해소

G11(등록/명칭) · G12(Worker 재설계) · G14(ErrorKind별 UX) · A2(recipe) · A3(mouse 배너) ·
A4(Auto 라우팅 표기) · A7(GSEA 명칭) · F1(QSettings offline 토글) · F3(KEGG 배너 정합) ·
F10(ontology당 1개 툴팁) · CLAUDE.md 규칙(help/docs 동기화)

## Phase 3 의존

- 요구사항/spec 3종 — requirements/setup 이미 엔진 의존성 반영(Phase 1); spec `collect_all` 등 Phase 3.
- 오프라인 fallback e2e(block_network + 실차단), 재현성 메타데이터 Analysis_Info, 라이선스/ToS 심사(F5),
  frozen 빌드 검증(Program Files 무쓰기 — ADR-3), 성능 상한(P3-6 — Phase 1에서 +33MB 실측 선행),
  기존 결과 경향 비교(P3-4), 프로젝트 저장/복원(P3-7).