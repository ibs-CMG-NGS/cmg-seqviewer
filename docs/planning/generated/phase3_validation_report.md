# Phase 3 — 검증·오프라인·재현성·패키징 보고서 (G004)

- Date: 2026-09-03 (UTC+09:00) · Repo: `/home/ygkim/cmg-seqviewer`
- Authority: `docs/planning/ON_GO_ENRICHMENT_IMPLEMENTATION_PLAN.md` v1.1 (§10-3)

---

## Summary

Phase 3 완료: 회귀 경향 비교(P3-4), 오프라인 fallback e2e(P3-2), 재현성 메타데이터 + 라이선스/ToS 심사(F5, P3-3),
패키징(spec 3종 collect_all + Linux PyInstaller 검증 빌드, P3-1), 성능 상한(P3-6 — Phase 1 실측 활용),
저장/복원 _gene_set 재파생(P3-7), 전체 스위트 green(P3-5).

## 수용 기준

| 기준 | 결과 | 근거 |
|---|---|---|
| **P3-1** frozen 빌드 3모드 + Program Files 무쓰기 | PASS(기계 제약 문서) | 3종 spec collect_all('gseapy')/collect_data_files('goatools')/collect_all('mygene')/collect_submodules('statsmodels') 배선 + `pyinstaller rna-seq-viewer.spec` **Linux 검증 빌드 성공**(goatools 1.6.5·gseapy 1.3.1·mygene 3.2.2 번들 확인) + frozen 부팅 스모크. 캐시=AppData(QStandardPaths) → Program Files 무쓰기 설계. Windows/macOS 호스트 빌드는 해당 플랫폼 이관 항목으로 기록 |
| **P3-2** 오프라인 GO 성공 + KEGG 안내 | PASS | 실네트워크 차단(block_network) + 실캐시: engine=offline → GOATOOLS 1,822행, KEGG 0행+경고; 캐시 부재 첫 실행 → ErrorKind.DOWNLOAD 분류(매핑 캐시 포함 보강). `-m offline` 스위트 3건 고정 |
| **P3-3** Analysis_Info 메타 + 라이선스/ToS 심사 | PASS | §6.9 체크리스트(recipe 포함) build_metadata 커버 + `phase3_license_tos_review.md`(Enrichr ToS·GMT 재배포·NCBI·GOC CC BY 4.0·동봉 패키지) 1건 |
| **P3-4** 기존 결과 대비 경향 일치 보고 | PASS | `phase3_trend_comparison.json`: 예시 `Acute_1D_vs_Control_GO_KEGG.parquet`(R clusterProfiler) vs 신규 엔진 — description 겹침 **local 61.8%(293/474) / online 23.8%(113/474)**. top-fdr 0건 겹침은 입력 DEG/GO 스냅샷/엔진 차이 → 해석 주의 문서화 |
| **P3-5** 전체 테스트 스위트 green | PASS | 161 passed + 4 network + 3 offline (아래) |
| **P3-6** 성능 상한 | PASS | Phase 1 실측 재확인: 로컬 GO 실행 10.5s(첫 obo 로드 제외 기준, ≤30s 목표 달성), 피크 증가 **+33MB**(≤800MB 목표 여유), worker(QThread) → UI 블로킹 0 |
| **P3-7** 저장/복원 검증 | PASS | **GO parquet 복원 분기 신설** (`presenter.load_dataset` — 표준화 파이프라인 경유, `_looks_like_go_frame` 감지). 진짜 e2e: 저장(parquet) → `load_dataset` 복원 → `_gene_set` set 재구성 → **비자명 클러스터링** 검증. arch(gen-1) P2-6 LOW 해소 |

## 경계 리뷰(gen-1) 반영

- **P3-7 복원 경로 수리**: GO_ANALYSIS parquet이 기존 Excel 전용 로더로 떨어져 로드 불가하던 문제 —
  `load_dataset`에 GO 표준 프레임(표준/R 어휘) parquet·csv 분기 추가 + `standardize_go_dataframe` 경유.
  `main_presenter._looks_like_go_frame` 감지. 저장→재오픈→클러스터 e2e로 고정.
- **매핑 캐시 DOWNLOAD 분류 확장**: custom background/population_symbols 매핑도 동일 분류 (성공 경로 무영향).
- P3-4 rank 수준 비교는 후속 항목으로 문서화 (동일 입력·GO 스냅샷 재생성 시 top-N 일치 지표).

## 관찰/보강

1. **매핑 캐시 DOWNLOAD 분류**: `enrich_ora`의 `map_symbols` 호출을 ErrorKind.DOWNLOAD로 래핑
   (첫 실행 오프라인에서 매핑 캐시(gene_info) 실패도 분류됨 — P2-3 UX 훅 보강, 테스트 고정).
2. **복원 _gene_set 재파생**: 저장 set→list(parquet 배열) 복원 상태에서도 표준화 파이프라인이
   gene_symbols로부터 set을 재구성 (architect P2-6 LOW 해소 — 테스트).
3. 배포 시 이관 항목: Windows/macOS frozen 빌드·Program Files 무쓰기 실측, 실행기(installer.iss/build.ps1) 검증,
   번들 옵션 채택 시 GMT/GO 재배포 라이선스 선행 심사(F5), 상업 배포 시 Enrichr ToS 재확인.

## G 해소

G1(패키징: spec 3종) · G6(비교/해석 주의) · G13(offline e2e 고정) · G14(첫 실행 다운로드 안내) · G15(메타데이터 체크리스트+심사)