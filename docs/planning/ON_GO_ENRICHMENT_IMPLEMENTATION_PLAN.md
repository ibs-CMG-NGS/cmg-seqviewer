# CMG-SeqViewer On-the-Fly GO/KEGG Enrichment Engine — 실행 계획 (RALPLAN-DR, deliberate mode)

**버전: v1.1 (rev 1)** — Architect/WATCH·Critic(ITERATE) pass 1 리뷰 반영(2026-09-02)

- 대상 repo: `/mnt/c/Users/KimYG/github/cmg-seqviewer` (Python 3.9+, PyQt6, PyInstaller 배포)
- 참조 문서: `docs/planning/ONLINE_ENRICHMENT_ANALYSIS_PLAN.md` (G1~G16 갭 분석)
- 상태: **승인됨 (2026-09-02)** — ralplan 합의 완료 (Architect CLEAR/APPROVE · Critic OKAY). 실행은 ultragoal(Phase 0 PoC)부터.

---

## Revision Log (pass 1)

| ID | 리뷰 지적 | 반영 위치(§) | 반영 요약 |
|---|---|---|---|
| A1 | Enrichr KEGG Term에 hsa ID 부재 → `^hsa\d+` 추출 불가 | §6.6, §5 ADR-4, §10-0 P0-2, §11 | term_id 기본=빈 값(클러스터링/네트워크는 `_gene_set` 기반이라 피해 제한적—확인), KEGG REST name→ID 매핑을 Phase 1 선택 보강, 합성 ID는 최후 수단. P0-2에 KEGG Term 구조 실측 항목 추가 |
| A2 | 파일 없는 enrichment Dataset의 프로젝트 저장/복원 정책 미정 | §6.3, §7, §10-3 P3-7 | `metadata['enrichment_recipe']`에 직렬화 요청 기록(재실행 경로 확보); v1 non-goal=저장 시 재실행/자동 복원(행 데이터 복원만, 기존 GO_ANALYSIS와 동일) |
| A3 | mouse 온라인: Enrichr GO 라이브러리는 human 기반 | §6.2, §10-0 P0-7, §11 | mouse=로컬 우선(GOATOOLS taxid 10090 + gene2go_mouse), 온라인 mouse 라이브러리 존재 P0 실측, `ortholog_mapper.py` 재사용은 Phase 4 |
| A4 | Auto 라우팅 규칙·description 대소문자 불일치 미정의 | §6.2(새 Auto 라우팅 표 + canonical description 정책), §10-2 | Auto=온라인 우선(background 미지정 시)/로컬(background 지정·오프라인); description은 term_id 기준 obo/GMT name 우선 통일, Enrichr Term은 fallback |
| A5 | `_parse_gene_symbols`가 `/`만 split | §6.4, §12 | 컨버터에서 `[;/,]` 다구분자 정규화 후 `/` 재조인 + 단위 테스트 |
| A6 | 온라인 전송 전 심볼 UPPERCASE 정규화를 ①에도 적용 | §6.1, §6.2 | all 소스에서 species-aware casing(인간=UPPER, mouse=Title)을 Enrichr 전송 전 적용 + 테스트 |
| A7 | 기존 GSEA Lite와 gseapy prerank 명칭 구분 | §10-4, §10-2(도움말), §19 | "GSEA Lite(Wilcoxon, statistics.py:110)" vs "GSEA prerank(gseapy, 국제 gene set)" 명칭·도움말 구분 |
| F1 | --offline 메커니즘 미정(main.py argparse 부재) | §6.8, §8, §12 | **결정: main.py argparse 확장 없음** — `CacheManager.detect_online()` API + QSettings 토글 + 다이얼로그 모드 배너. `test/conftest.py`의 `block_network`(requests/socket monkeypatch) 픽스처로 offline 시뮬레이션 |
| F2 | 성능/메모리 수용 기준 부재 | §10-0 P0-3, §10-3 P3-6 | PoC에서 GOATOOLS wall-time/피크 메모리 실측 기록; Phase 3 상한(로컬 GO ≤30s 첫 로드 제외, 피크 메모리 증가 ≤800MB, UI 블로킹 0) |
| F3 | 오프라인 KEGG UX가 ADR-1 결과에 비종속 | §7, §9, §10-2 P2-3 | "KEGG 오프라인 지원 여부는 ADR-1 종속 — Option 2 채택 시 배너 재결정" 명시 |
| F4 | pytest 마커 등록 파일 부재 | §8, §12 | 신규 `pytest.ini`(`network`/`offline`/`qt` 마커) |
| F5 | 라이선스/ToS 부재 | §17, §10-3(P3-3 옆) | Enrichr ToS·GMT 재배포, NCBI gene2go/gene_info 이용약관 심사 항목 추가 |
| F6 | 프로젝트 저장/로드 관계 미정 | §7, §6.3 | A2와 정합: v1 non-goal(재실행 복원), recipe 기록만 |
| F7 | stale TTL 기본값 미정 | §6.8 | TTL 기본 obo/gene2go 30일·GMT 90일, 만료 시 자동 재다운로드·실패 시 기존 캐시+경고(W2) |
| F8 | obo 크기 표기 오류 | §6.8 | "(.obo.gz 압축 ~8MB; 비압축 ~30-40MB — PoC 실측)" |
| F9 | 회귀 테스트 목록 누락 | §12, §10-0 P0-6 | `test_figure_bundle_export.py` 추가 |
| F10 | (direction×ontology)당 라이브러리 1개 제약의 UI 미표면화 | §10-2, §6.3 | 체크박스 disable+툴팁 |
| F11 | PoC Python 버전 명시 | §10-0, §11(G1) | pandas 3.x의 Python 요구사항(3.10+) 실측, docs/user 설치 가이드 영향 확인 |
| (정보) | meta_fdr_fisher는 main_window.py:2192-2194 BH 파생; meta_log2fc_mean/meta_log2fe_mean 변종 공존; GO viz 서브메뉴 ~617-632 | §6.1, §16, §8 | deg_input은 컬럼 기준 구현(+ BH 폴백), 변종 폴백 매핑, main_window 행 번호 정정 |

---

## 1. Summary

사용자가 로드된 RNA-seq DE 데이터셋(또는 붙여넣은 gene list, 또는 `Comparison: Statistics`의 meta-signature)에서 DEG를 추출하고, **gseapy Enrichr API(온라인)** 와 **GOATOOLS(로컬)** 기반으로 GO/KEGG enrichment를 즉석 수행한 뒤, 결과를 **기존 StandardColumns 구조 + `_gene_set` set 컬럼**으로 변환하여 **기존 Bar Chart / Dot Plot / Clustering / Network 다이얼로그에서 그대로 재사용**하는 엔진을 임베딩한다.

핵심 설계 결정:
- **DEG 입력 추상화 3종**(단일 DE 데이터셋 필터 추출 / 붙여넣기 gene list / meta-signature) + **gseapy.prerank 경로**(Phase 4, M4b early aggregation용)를 하나의 `EnrichmentAnalyzer` API로 통합 (G3/G16).
- 결과는 **1회 실행 → 1개 `DatasetType.GO_ANALYSIS` Dataset**(단일 병합 DataFrame)으로 묶고, 행마다 `gene_set` 라벨(`UP_BP`, `DOWN_KEGG`, `TOTAL_MF` 등)을 부여 — 기존 `GOKEGGLoader` 멀티시트 병합 관행과 동일 규칙 (G5).
- GO 로컬 엔진은 GOATOOLS(우선), 온라인은 Enrichr, **커스텀 background가 필요한 경우 로컬 경로(`gseapy.enrich` + 캐시 GMT/GOATOOLS)로 강제** (G8). mouse는 로컬 우선(§6.2).
- **캐시 경로는 쓰기 가능한 AppDataLocation**(`QStandardPaths` 기반, `data_path_config.py` 확장) — `~/.cmg_seqviewer/` 신설 금지 (G2).
- **Phase 0 PoC가 Phase 1 착수의 하드 게이트**. pandas 3.0.3 호환·Python 버전 실측·Enrichr 실호출·4개 시각화/클러스터링 다이얼로그 sanity를 통과해야 진행.
- **KEGG 오프라인 지원 여부는 ADR-1 결과에 종속**(Option 2 채택 시 재결정, §9/F3).

예상 규모: 코드 재사용 ~75%(기존 시각화·로딩 파이프라인), 신규 순수 파이썬 모듈 5개 + 테스트 인프라(pytest.ini/conftest.py), GUI 1개, 테스트 5묶음.

---

## 2. Intent Diff (참조 계획 대비 변경점)

| # | 참조 계획의 주장 | 이 계획의 수정/확정 | 근거 |
|---|---|---|---|
| D1 | 캐시 경로 `~/.cmg_seqviewer/` | **기각**. `data_path_config.py`에 `get_app_data_dir()`/`get_enrichment_cache_dir()` 추가(AppDataLocation). 기존 `~/.rna_seq_analyzer/`, `QSettings("RNASeqDataView")` 규칙에 통합 | G2 |
| D2 | "GOATOOLS 완전 오프라인" | mygene(온라인) 의존 자가모순 → **NCBI `gene_info.gz` 로컬 매핑 캐시**(`gene_id_mapper.py`)를 Phase 1 필수로. 온라인 매핑은 fallback | G9 |
| D3 | "DE 전체 유전자를 background로" | 온라인 Enrichr는 커스텀 background 비지원 가능성 → **모드 강제 정책**: background 지정 시 로컬 엔진만 허용 | G8 |
| D4 | `DatasetManagerWidget` 명칭 | 없음. 실제 통합은 `DatasetTreePanel` + `main_presenter.load_go_kegg_data()` 패턴 → 신규 `register_enrichment_result()` | G11 |
| D5 | `GOEnrichmentWorker(gene_list, background, organism)` 유지 | 시그니처 재설계: `EnrichmentWorker(EnrichmentRequest)` → `finished(EnrichmentResult)` | G12 |
| D6 | 컬럼 매핑 표만 제시 | 멀티시트 gene_set 라벨 규칙(§6.3), `_gene_set`(§6.4), ratio(§6.5), KEGG term_id(§6.6) 신설 | G4/G5/G6/G7 |
| D7 | fold_enrichment 미언급 | **캐시 GMT에서 term 크기(M) 산출**로 온라인 결과에도 bg_ratio/fold_enrichment 계산 (기존 `_compute_fold_enrichment` 재사용) | G6 |
| D8 | "DE 결과 파일 로드" | **메모리 내 로드 데이터셋 재사용**: 필터 임계값/붙여넣기/meta-signature 3소스 | G3 |
| D9 | GSEA 없음 | `enrich_prerank()` 인터페이스를 Phase 1에 선언(구현 Phase 4) → M4b 정합 | G16 |
| D10 | 프로젝트 저장 정책 미정 | enrichment Dataset은 행 데이터로 복원(기존 GO_ANALYSIS 동일), 재실행은 v1 non-goal — `metadata['enrichment_recipe']`로 재실행 경로만 기록 | A2/F6 |
| D11 | mouse 온라인 라이브러리 사용 전제 | mouse=**로컬 우선**, 온라인 mouse 라이브러리 실측 후 허용, ortholog 매핑 통한 온라인은 Phase 4 | A3 |

---

## 3. Principles (3~5)

1. **Reuse over rewrite.** enrichment 결과는 반드시 기존 StandardColumns + `GOKEGGLoader` 표준화 파이프라인을 통과시킨다. 새 시각화/새 로딩 경로를 만들지 않는다. (G4/G5/G6)
2. **Offline is a promise, not a slogan.** "로컬/오프라인"이라 주장하는 경로는 온라인 API(mygene 포함)에 무단 의존하지 않는다. 로컬 매핑 캐시·명시적 다운로드 매니저·감지 API로 뒷받침한다. (G9/F1)
3. **PoC before commitment.** 엔진 선택·의존성 버전·Python 요구사항은 Phase 0 PoC 통과 전에 확정 금지. 실패 시 Option 2로 즉시 전환할 수 있게 옵션을 열어둔다. (F11)
4. **Deterministic and auditable.** 모든 실행(엔진 버전, obo/gene2go/GMT 획득 일자·sha256, 임계값, 입력/배경 크기, species, 타임스탬프, 재실행 recipe)을 metadata와 Analysis_Info 관행에 기록한다. (G15/A2)
5. **Network is a failure mode.** 모든 네트워크 경로는 mock-first 테스트, 타임아웃/rate-limit/빈 결과/매핑 0건에 대한 명시적 UX. 조용한 fallback(fake 성공) 금지. (G13/G14)

---

## 4. Decision Drivers (top 3)

1. **통계 정확성 vs 구현 단순성**: 커스텀 background(G8)·오프라인 주장(G9)·mouse 온라인 한계(A3)가 Enrichr·mygene과 충돌 → 로컬 계산 경로를 정직하게 설계하고, 모드별 보장 범위를 UI에 명시.
2. **기존 다이얼로그 재사용 보존**: Bar/Dot/Clustering/Network는 (term_id, gene_ratio, bg_ratio, fold_enrichment, `_gene_set`) 계약에 의존 → 계약을 단위 테스트로 고정(다구분자 정규화 포함, A5).
3. **pandas 3.0.3 + Python 3.9+ 서약 + PyInstaller 배포 가능성**: 신규 의존성이 현재 venv(pandas 3.0.3, numpy 2.4.6)에 설치·동작하고 3종 spec으로 프리징 가능해야 함. PoC에서 Python 버전 실측(pandas 3.x는 3.10+ 요구 가능성, F11). 불가 시 Option 2로 전환.

---

## 5. Viable Options (pros/cons 포함)

### Option 1 — 하이브리드 3엔진 (권장 기본값)
`GOATOOLS`(로컬 GO) + `gseapy.enrichr`(온라인 GO/KEGG) + `gseapy.enrich`(로컬 GMT, 커스텀 background·KEGG GMT 캐시).

- **Pros**: GO 로컬 통계 엄밀성(GO DAG·최신 gene2go, `fdr_bh` 다중보정); 온라인 속도·DB 다양성; 커스텀 background는 로컬 경로로 정확 계산; 캐시 GMT로 온라인 결과에도 bg_ratio/fold_enrichment 산출(§6.5).
- **Cons**: 엔진 3개 테스트·패키징 면; obo 로딩 메모리(§6.8·F2 상한); 온라인/로컬 결과 수치 상이(해석 주의 표기); **KEGG 오프라인 미지원**(G14).

### Option 2 — gseapy 단일 엔진 (PoC 실패 시 fallback)
`enrichr`(온라인) + `enrich`(캐시 GMT 로컬, 커스텀 background, **KEGG 오프라인 포함**). GOATOOLS 미사용.

- **Pros**: 한 엔진·단일 GMT 캐시 체계로 KEGG 오프라인까지 커버(코드/패키징 단순, obo 메모리 불필요); GMT 스냅샷 고정으로 재현성 좋음.
- **Cons**: GO DAG 구조·gene2go 동적 어노테이션 반영 상실; KEGG GMT(Enrichr 텍스트 더미) 라이선스·최신성 검토 필요(F5); GO 시맨틱 비교가 기존 `final_go_result.xlsx`와 달라 수치 정합성 저하.
- **채택 시 파급**: Phase 2의 "오프라인=GO 전용(KEGG 비활성)" 배너가 "캐시 GMT 기반 KEGG 로컬 가능"으로 **재결정**(F3).

**전환 규칙**: Phase 0 PoC에서 (a) pandas 3.0.3/Python 버전에 goatools 설치·임포트 실패, 또는 (b) GOATOOLS 결과가 컨버터 계약을 만족 못 하는 경우 → Option 2 단일화. (유일 옵션 아님 — 둘 다 viable)

### Option 3 — Enrichr 온라인 단독 (기각)
근거: 오프라인 약속 붕괴(G9), 커스텀 background 불가(G8), rate-limit·프라이버시·mouse 라이브러리 한계(A3) → 기각.

### 배경(background) 정책 옵션 — ADR-2
- **2A (권장)**: background 미지정 → 온라인·로컬 모두 가능(각각 Enrichr 고정 universe / DE 테이블 전체 유전자). background **지정 시 로컬 엔진 강제** + 다이얼로그 경고. 온라인 결과 해석에 "Enrichr 고정 universe 기준" 명시.
- **2B**: background 무관 항상 로컬 계산 — 재현성 최고, 온라인 속도 이점 상실. PoC에서 enrichr background 파라미터 실효 검증 후 2A/2B 확정.

### 캐시 경로 옵션 — ADR-3
- **3A (권장)**: `QStandardPaths.AppDataLocation` 기반(Win `%APPDATA%/CMG-SeqViewer/cache`, mac `~/Library/Application Support/CMG-SeqViewer/cache`). frozen 환경 쓰기 보장. `data_path_config.py` 통합.
- **3B**: `get_external_data_dir()` 확장 — frozen 시 `Program Files` 아래라 쓰기 불가 → 기각.
- **3C**: `~/.cmg_seqviewer/` — 기존 규칙과 난립 → 기각. (참조 계획 원안)

### KEGG term_id 옵션 — ADR-4 (A1 반영)
- **4A (권장 기본)**: GO는 `GO:\d{7}` 추출. **KEGG 온라인 Term에는 hsa ID가 없는 것이 실측 전제**(G7·A1) → term_id **빈 값** 기본. 다운스트림 영향은 제한적: 클러스터링/네트워크는 `_gene_set`·description 기반(go_clustering_dialog/`GONetworkDialog` 검증됨). `^hsa\d+`는 방어적 파싱(존재 시에만 채택)으로 유지.
- **4B (선택 보강, Phase 1)**: KEGG REST `rest.kegg.jp/find/pathway/<term name>` name→ID 검색으로 `hsa#####` 채움(온라인, throttle·캐시, 실패 조용히 빈 값 유지).
- **4C (최후 수단)**: 빈 term_id가 다운스트림을 파괴하는 경우에만 결정적 해시 합성 ID(`KEGG:<hash8>`) + metadata `synthetic=true`.

---

## 6. 아키텍처 및 데이터 구조 설계

### 6.1 DEG 입력 추상화 (G3/G16) — `src/utils/deg_input.py`

공통 출력: `DegInput` dataclass `{symbols: List[str], direction, species, meta: Dict, ranked: Optional[List[Tuple[str, float]]]}`.

| 소스 | 추출 규칙 | 비고 |
|---|---|---|
| ① 단일 DE 데이터셋 | `dataset.dataframe`에 필터 임계값(ⓐ `abs(log2fc) >= fc_min`, ⓑ `adj_pvalue <= fdr_max`, ⓒ direction UP/DOWN) 적용 후 `symbol` 컬럼 수집. alias 자동매핑(`logfc→log2fc`, `padj→adj_pvalue`)은 `data_loader.py`가 처리. **Enrichr 전송 전 species-aware casing 정규화**(인간=UPPER, mouse=Title — A6) | 기본 경로 |
| ② 붙여넣기 gene list | `parse_gene_list(text)`: 줄/콤마/탭/세미콜론 분리, species-aware casing, 중복 제거, 빈 심볼·비유전자 토큰 경고 | direction=TOTAL |
| ③ meta-signature | `Comparison: Statistics` 시트: `meta_fdr_fisher <= cutoff` (+`meta_log2fc_mean`/`meta_log2fe_mean` **변종 폴백 매핑**, 부호로 UP/DOWN, `meta_direction` concordant 권장). **`meta_fdr_fisher`는 meta_stats 산출물이 아니라 시트 빌드 시 BH 파생(main_window.py:2192-2194)이므로 deg_input은 컬럼 존재 기준으로 구현, 부재 시 `meta_pvalue_fisher`에 BH 직접 적용 폴백** | Phase 4에서 prerank |
| ④ (Phase 4) ranked | `meta_z` 또는 `-log10(meta_pvalue_fisher) × sign(meta_log2fc_mean)` → `gseapy.prerank` (M4b) | 인터페이스만 Phase 1에 선언 |

### 6.2 엔진 API·라우팅·species — `src/utils/enrichment_analyzer.py`

```python
class EnrichmentAnalyzer:
    def enrich_ora(self, genes, background, organism, libraries, engine) -> pd.DataFrame
    def enrich_prerank(self, ranked, organism, libraries) -> pd.DataFrame   # Phase 4
    def to_standard(self, raw, gene_set_label, ...) -> pd.DataFrame         # §6.3~6.6
    @staticmethod
    def libraries_for(organism) -> dict  # {BP: ..., CC: ..., MF: ..., KEGG: ...}
```

- **species 정책 (A3)**: Human — 온라인(Enrichr GO/KEGG) + 로컬(GOATOOLS taxid 9606). **Mouse — 로컬 우선**(GOATOOLS taxid 10090 + `gene2go_mouse`, symbol은 Title-case). 온라인 mouse 라이브러리(예: `GO_Biological_Process_2023`가 human 기반인지)는 **P0-7에서 실측** 후 허용 여부 결정. `ortholog_mapper.py:48`(ortholog_map.csv.gz) 재사용으로 mouse 심볼→human 라이브러리는 **Phase 4 범위**. 심볼 casing은 species-aware(§6.1, A6).
- **Auto 라우팅 규칙 (A4)** — 모드=Auto일 때:
  | 조건 | 경로 |
  |---|---|
  | background 미지정 && 온라인 가능(`detect_online()`) | Enrichr 온라인(GO+KEGG) |
  | background 지정 ∥ 오프라인 | 로컬: GO=GOATOOLS, KEGG=v1 비활성(Option 2면 캐시 GMT) |
  | 온라인 불가 && 캐시 부재 | 사전 안내 후 중단(다운로드 가이드) |
- **description canonical 정책 (A4)**: 동일 term_id는 엔진 무관 동일 description이 되도록 **term_id 기준 정규화** — 우선순위: GOATOOLS obo name > 캐시 GMT name > Enrichr Term(원본). 대소문자·괄호 표기 차이(Enrichr Title-Case vs GOATOOLS 소문자)는 term_id를 조인 키로 통일하고 표시 description은 위 우선순위로 하나만 채택. 기본 비교/조인 키는 항상 term_id(또는 없는 KEGG 행은 description+`_gene_set`).
- 온라인: `gseapy.enrichr(gene_list=symbols_normalized, ...)` — 심볼만 전송. rate-limit 대비 결과 캐시(§6.8).
- 로컬 GO: `GOEnrichmentStudy`(goatools) — assoc=`gene2go`+SymbolMapper(§6.7), `propagate_counts=True`, `methods=['fdr_bh']  # (PoC 확정 2026-09-02: goatools 1.6.5는 fisher_scipy 문자열 제거 — Fisher가 고정 기저 검정)`.
- 로컬 커스텀 background/KEGG GMT: `gseapy.enrich(gene_list, gene_sets=cached_gmt, background=bg, ...)`.

### 6.3 멀티시트 → 단일 Dataset 규칙 (G5) — ADR-B

1회 실행 결과를 **1개의 `DatasetType.GO_ANALYSIS` Dataset**(이름 `Enrichment: {입력명}`)로 생성. Excel 로더가 여러 시트를 하나의 `gene_set` 컬럼 DataFrame으로 병합하는 관행과 동일하게 **단일 병합 DataFrame**: 행 = (direction × ontology × library × term).

- `gene_set` 라벨: `{direction}_{ontology}` — direction ∈ {UP, DOWN, TOTAL}, ontology ∈ {BP, CC, MF, KEGG}. 예: `UP_BP`, `DOWN_BP`, `UP_KEGG`, `TOTAL_MF`. KEGG는 별도 방향 요청 없으면 `TOTAL_KEGG`.
- `direction`/`ontology`는 기존 `_extract_direction_ontology`로 라벨에서 파싱 → 기존 GO 필터(`_on_filter_go_results`)와 호환.
- **v1 제약**: (direction×ontology)당 라이브러리 1개. 같은 ontology의 2개 라이브러리는 별도 실행 안내 — **Phase 2에서 체크박스 disable+툴팁으로 표면화**(F10).
- **프로젝트 저장/복원 (A2/F6)**: enrichment Dataset은 기존 설정/복원 경로(행 데이터)로 복원되며, `metadata['enrichment_recipe']`에 직렬화된 `EnrichmentRequest`(JSON-safe)를 기록해 재실행 경로를 보존한다. **자동 재실행은 v1 non-goal**(저장 시 "Export 권장 + recipe 보존" 안내만).
- Dataset 등록: 신규 `main_presenter.register_enrichment_result()` — `_generate_unique_name` → `self.datasets[name]` → `_update_view_with_dataset` → `dataset_loaded` emit → audit log (G11).

### 6.4 `_gene_set` set 컬럼 (G4/A5)

- gseapy `Genes`는 `;` 구분, GOATOOLS 기여 유전자는 리스트 → **컨버터에서 `re.split(r'[;/,]')` 다구분자 정규화 후 `/`로 재조인**(`_parse_gene_symbols`·클러스터링 폴백이 `/` split이므로 — A5) → 기존 `_parse_gene_symbols`로 Python `set` 컬럼 `_gene_set` 생성. 다구분자 정규화는 단위 테스트 필수.
- GOATOOLS 경로: Entrez 기준 출력 → SymbolMapper 역매핑으로 심볼 복원 후 동일 규칙. 매핑 실패 심볼은 경고(W1).
- `_gene_set`이 전 행 빈 set이면 로거 경고(W1)를 탐지 지표로(클러스터링 무력화 감지).

### 6.5 gene_ratio / bg_ratio / fold_enrichment (G6)

- `gene_ratio`: gseapy `Overlap`("k/n") 그대로 `'k/n'` 문자열(기존 컨벤션). GOATOOLS는 k(term 히트)/n(DEG 수) 계산해 동일 포맷.
- `bg_ratio`: 분자 M = **캐시 GMT의 해당 term 유전자 수**(온라인 결과도), 또는 GOATOOLS `assoc` term 크기. 분모 N = background 크기(로컬=지정 background 수; 온라인=캐시 GMT universe 크기). `'M/N'` 문자열.
- `fold_enrichment`: `_compute_fold_enrichment`(go_kegg_loader 1개, data_loader.py:428-460 중복) 재사용 — **중복 제거 리팩터**(§8.1).
- gseapy `Odds Ratio`/`Combined Score`는 추가 컬럼으로 보존.

### 6.6 term_id (G7/A1) — ADR-4

- GO: Term 문자열에서 `GO:\d{7}` 추출(Enrichr `Term` 괄호 안 / GOATOOLS obo ID).
- KEGG: **온라인 Term에는 hsa ID 부재가 전제** → 기본=빈 값. 방어적 `^hsa\d+` 파싱(존재 시 채택), **Phase 1에서 KEGG REST name→ID 매핑(4B)을 선택 보강**(온라인·throttle·캐시, 실패 시 조용히 빈 값). 다운스트림은 description+`_gene_set` 키로 동작(클러스터링/네트워크 — 실측 확인). P0-2에서 KEGG Term 구조 기록.

### 6.7 Symbol→Entrez 매핑 (G9) — `src/utils/gene_id_mapper.py`

- 1차(오프라인): NCBI `gene_info.gz`(Human/Mouse 필터, `gene2go`와 동일 출처) → 로컬 매핑 테이블, taxid 필터.
- 2차(fallback, 온라인): mygene `querymany(scopes='symbol', species=..., fields='entrezgene')`.
- 결과 캐시: AppDataLocation cache `mapping/`에 pickle+버전 파일(기존 규칙과 혼재 금지).
- 매핑 0건 시 **분석 중단**(진행 불가 UX, G14) — 조용히 진행 금지.

### 6.8 캐시/다운로드 매니저 (G1/G2/F1/F7/F8) — `src/utils/enrichment_cache.py`

- `CacheManager(cache_dir)` (기본: `data_path_config.get_enrichment_cache_dir()`):
  - `ensure_obo(organism)` → `go-basic.obo` (**.obo.gz 압축 ~8MB; 비압축 ~30-40MB — PoC 실측**, F8), `ensure_gene2go(organism)` → `gene2go_<taxid>.gz`, `ensure_gene_info(organism)`, `ensure_gmt(library)` → Enrichr GMT 텍스트 더미(`https://maayanlab.cloud/Enrichr/geneSetLibrary?mode=text&libraryName=...`).
  - **원자적 쓰기**(`.tmp`→rename), 사이드카 메타(`version/source/url/fetched_at/sha256`).
  - **TTL 기본값 (F7)**: obo/gene2go 30일, GMT 90일. 만료 시 **자동 재다운로드 시도**, 실패하면 기존 캐시 사용 + 경고(W2) — 사용자 확인 절차 없음(비파괴).
  - **네트워크 감지 API (F1)**: `detect_online(timeout=3s)` — requests/socket 헤드 요청. **CLI(`main.py` argparse) 확장 없음**: 오프라인 강제는 QSettings(`RNASeqDataView/enrichment/offline`) 토글 + 다이얼로그 모드 배너로만 구현(피처 폭 최소).
  - 프로세스 내 obo 1회 로드 캐시(세션 재사용), proxy env(`HTTPS_PROXY`) 존중, 타임아웃/재시도(backoff).
- **번들 vs 런타임**: v1은 **런타임 다운로드**(빌드 크기·CI 영향 없음, G1). 번들 옵션(Phase 3 선택) — 이 경우 NCBI/GMT 재배포 라이선스 심사(F5) 선행.

### 6.9 재현성 메타데이터 (G15/A2)

`EnrichmentResult.metadata`(→ `dataset.metadata`)와 Export **Analysis_Info 시트 관행**에 기록: engine 버전, Enrichr 라이브러리명+조회일, obo/gene2go/GMT 획득일·sha256, species, 임계값(fc/fdr/direction), 입력 DEG 수, background 크기/모드, meta 입력 시 결합 데이터셋 목록, 실행 타임스탬프, 경고 목록, **`enrichment_recipe`(재실행 직렬화 요청)**. DataFrame에는 넣지 않음(로더가 info 시트 skip).

---

## 7. In scope / Out of scope

**In scope (v1)**
- 온라인 Enrichr + 로컬 GOATOOLS + 로컬 GMT(gseapy.enrich) 3경로, Human 우선·Mouse 로컬
- DEG 입력 3소스(단일 DE / 붙여넣기 / meta-signature ORA)
- StandardColumns 변환 + `_gene_set` + gene_set 라벨 + fold_enrichment + 분석별 metadata(recipe 포함)
- 신규 다이얼로그 + Worker 재설계 + 기존 4개 시각화/클러스터링 다이얼로그 재사용 확인
- 오프라인/에러/빈 결과 UX, 결과 Export(기존 파이프라인), PyInstaller 3종 spec
- F1 help_dialog + docs/user 동기화 (CLAUDE.md 규칙)

**Non-goals (명시적 제외)**
- GSEA prerank UI·Meta prerank(M4b) → **Phase 4** (인터페이스만 Phase 1)
- cross-species meta(M2 ortholog → enrichment), ortholog 기반 mouse 온라인 → Phase 4
- Reactome/기타 라이브러리 노출 — GO BP/CC/MF + KEGG만, "라이브러리명 직접 입력" 고급 옵션 보류
- 커스텀 GMT 업로드 — v1 제외(Phase 4 후보)
- t-SNE/UMAP, GOATOOLS 수치를 R 파이프라인과 완전 동일화(엔진 차이는 해석 주의 명시)
- **KEGG 오프라인(v1 기본)** — ADR-1 Option 2 채택 시 "캐시 GMT 기반 KEGG 로컬"로 **재결정**(F3)
- **프로젝트 저장 시 enrichment 재실행·자동 복원** — 행 데이터 복원만, `enrichment_recipe` 기록으로 재실행 경로만 보존(F6/A2)
- CLI `--offline` 플래그 — QSettings 토글 + 감지 API로 대체(F1)

---

## 8. File-level changes

### 신규 파일
| 파일 | 역할 |
|---|---|
| `src/utils/enrichment_analyzer.py` | 엔진 API(ORA+prerank), 자동 라우팅, StandardColumns 컨버터, term_id 파싱, 라이브러리 테이블, ratio 계산, description canonical 정책 |
| `src/utils/deg_input.py` | DEG 입력 3소스 + ranked 추출, species-aware casing (G3/G16/A6) |
| `src/utils/gene_id_mapper.py` | symbol→Entrez 로컬(gene_info) + mygene fallback (G9) |
| `src/utils/enrichment_cache.py` | obo/gene2go/gene_info/GMT 다운로드·검증·원자적 캐시·TTL·`detect_online()` (G1/G2/F1/F7/F8) |
| `src/models/enrichment_models.py` | `EnrichmentRequest`(직렬화 가능), `EnrichmentResult`, `ErrorKind` (G12/A2) |
| `src/gui/enrichment_analysis_dialog.py` | 분석 다이얼로그(소스/임계값/종/라이브러리/모드/배경/진행/취소/결과 요약) (G14) |
| `pytest.ini` | 마커 등록(`network`/`offline`/`qt`) (F4) |
| `test/conftest.py` | `block_network` 픽스처(requests/socket monkeypatch — offline 시뮬레이션) (F1) |
| `test/test_enrichment_converter.py`, `test_deg_input.py`, `test_enrichment_analyzer.py`, `test_enrichment_cache.py`, `test_enrichment_dialog.py` (+`test/fixtures/`) | 단위/통합/e2e, mock 픽스처 (G13) |

### 수정 파일
| 파일 | 변경 | 갭 |
|---|---|---|
| `src/utils/go_kegg_loader.py` | `_standardize_columns`+`_parse_gene_symbols`+`_extract_direction_ontology`+`_compute_fold_enrichment` → public `standardize_go_dataframe()` 승격(동작 동일, 기존 메서드 위임). 중복 `_compute_fold_enrichment` 단일화 | G4/G5/G6 |
| `src/utils/data_path_config.py` | `get_app_data_dir()`/`get_enrichment_cache_dir()` (AppDataLocation) | G2 |
| `src/workers/go_workers.py` | `GOEnrichmentWorker` → `EnrichmentWorker(EnrichmentRequest)`; `finished(object)=EnrichmentResult`; `GOClusteringWorker` 유지 | G12 |
| `src/gui/main_window.py` | Analysis 메뉴(GSEA Lite 직후, ~450줄)에 `🧬 GO/KEGG Enrichment Analysis...` + `_on_enrichment_analysis()`. GO viz 서브메뉴(~617-632)·`_on_go_visualization`(5327) 무변경 | G3/G11 |
| `src/presenters/main_presenter.py` | `register_enrichment_result(result)` — 등록·unique name·`_update_view_with_dataset`·`dataset_loaded`·audit log (`load_go_kegg_data` 패턴, G11) | G11 |
| `requirements.txt`, `setup.py` | `gseapy>=1.1.0`, `goatools>=1.6.0`, `mygene>=3.2.0`, `statsmodels>=0.14.0,<0.15`  # goatools fdr_bh 전용 — 0.15 sandbox.multicomp.multipletests 제거(PoC P0-3), `requests>=2.28.0` (버전+Python 요구사항 PoC 확정) | G1/F11 |
| `rna-seq-viewer.spec`, `rna-seq-viewer-onefile.spec`, `cmg-seqviewer-macos.spec` | `collect_all('gseapy')`, `collect_data_files('goatools')`, `collect_all('mygene')`, `collect_submodules('statsmodels')` + hiddenimports 증설 | G1 |
| `src/gui/help_dialog.py` | F1 새 섹션 + shortcut 테이블; **GSEA Lite(Wilcoxon) vs GSEA prerank(gseapy) 명칭 구분**(A7) | CLAUDE.md/A7 |
| `docs/user/user-guide.md` (+ `quick-start.md`) | 온라인/로컬/오프라인 모드, background·프라이버시·캐시·KEGG 오프라인 제약·Python 버전 요구 | CLAUDE.md/G14/F11 |

`src/main.py` **무변경**(CLI 확장 없음 — F1 결정).

---

## 9. Sequencing and dependencies

```
Phase 0 PoC ──(gate 통과)──▶ Phase 1 엔진 ──▶ Phase 2 UI ──▶ Phase 3 검증/오프라인/패키징 ──▶ Phase 4 M4b prerank
```

- Phase 1은 Phase 0 확정 버전·엔진 선택(ADR-1/2/4)·Python 요구사항을 입력값으로 사용.
- Phase 2는 Phase 1의 `EnrichmentResult` 계약 의존(모델 선행).
- **F3 의존성**: Phase 2의 "오프라인 KEGG 비활성" 배너는 **ADR-1 결과에 종속** — Option 2 채택 시 배너를 "캐시 GMT 기반 KEGG 로컬 가능"으로 재결정(Phase 2 착수 시점에 ADR-1 확정이 선행돼야 함).
- Phase 3 PyInstaller 작업은 Phase 0 설치 검증 버전 사용. Phase 4는 Phase 1 `enrich_prerank()` 인터페이스 + Phase 2 입력 소스 ③ 선택기 위에 얹힘.

---

## 10. Phased implementation plan (Phase 0~4)

### Phase 0 — PoC / 기술검증 (하드 게이트)
**방법**: scratch venv(또는 프로젝트 venv 사본)에서 순서대로.

1. **Python 버전 확인(F11)**: venv Python 버전 실측(3.9~3.12). pandas 3.x가 3.10+를 요구하면 `requirements.txt`·`docs/user/python-installation.md`·`installation.md` 영향 기록. `pip install gseapy goatools mygene statsmodels requests` → `python -c "import ..."` + pipdeptree로 pandas 3.0.3 충돌 여부, 버전 고정값 기록.
2. **실제 `gseapy.enrichr()` 1회**(`GO_Biological_Process_2023`+`KEGG_2021_Human`, gene list 100개): 반환 컬럼, `Overlap` 포맷, `Genes` 구분자, **KEGG Term 구조 실측(hsa ID 유무 — A1)**, `background=` 실효성(G8).
3. **GOATOOLS 로컬**: go-basic.obo + gene2go_human 다운로드 → `GOEnrichmentStudy` 100유전자. **wall-time·피크 메모리 실측 기록(F2)**. `gene_info.gz` 로컬 매핑 smoke test(G9).
4. **컨버터 sanity**: 두 엔진 결과 → §6.3~6.6 규칙 → 어서트: `_gene_set` 비어있지 않음(G4/A5), ratio/fold 산출(G6), 라벨→direction/ontology(G5), term_id 상태 분류(G7/A1), description canonical(A4).
5. **다이얼로그 호환**: 변환 DataFrame을 Bar/Dot/Clustering/Network 4종에 열어 크래시 없음 + 클러스터링 겹침 ≥1쌍 병합.
6. **회귀**: `pytest test/test_models.py test/test_statistics.py test/test_fsm.py test/test_figure_bundle_export.py` 통과(F9) — 신규 의존성 추가 후에도 기존 4종 회귀 없음.
7. **Mouse 실측(A3)**: GOATOOLS taxid 10090 + mouse 심볼(Title-case) 로컬 실행, 온라인 mouse 라이브러리 존재 여부 기록.

**수용 기준**
- [P0-1] 5개 패키지 설치·임포트 성공, 버전·Python 버전 고정값 문서화 (pandas 3.0.3 호환, F11).
- [P0-2] enrichr 실호출: 컬럼/포맷/background 실효성 + **KEGG Term 구조** 기록.
- [P0-3] GOATOOLS 로컬 성공 + **wall-time/피크 메모리 실측 기록**(F2); gene_info 로컬 매핑 성공.
- [P0-4] 컨버터 어서트(다구분자 정규화 포함) 5종 통과.
- [P0-5] 4개 다이얼로그 스모크 통과, 클러스터링 병합 ≥1쌍.
- [P0-6] 기존 테스트 회귀 없음(figure bundle 포함, F9).
- [P0-7] Mouse 로컬 GOATOOLS + casing 실측 완료(A3).

**실패 시**: 중단 후 `0-Main` 블로커 보고 — (a) pandas/Python 불일치 → Option 2 또는 버전 고정 우회, (b) GOATOOLS 계약 불만족 → Option 2, (c) enrichr background 무실효 → ADR-2 확정. **Phase 1 착수 금지.**

### Phase 1 — EnrichmentAnalyzer + 매핑/캐시 (엔진)
**파일**: `enrichment_analyzer.py`, `deg_input.py`, `gene_id_mapper.py`, `enrichment_cache.py`, `enrichment_models.py`, `go_kegg_loader.py`(리팩터), `data_path_config.py`(확장), `pytest.ini`, `test/conftest.py`, 테스트 4묶음 + `test/fixtures/`.

작업:
1. `go_kegg_loader.py` 파이프라인 승격(동작 보존 회귀 확인) — 컨버터 단일 진실원천.
2. `CacheManager` 구현: 원자적 쓰기·사이드카·**TTL 30/90일·자동 재다운로드(F7)**·`detect_online()`(F1)·proxy.
3. `SymbolMapper`: gene_info 로컬 우선, mygene fallback, species-aware casing(A6).
4. `EnrichmentAnalyzer.enrich_ora()`+`to_standard()`+라이브러리 테이블(Human; Mouse는 P0-7 실측값)+**Auto 라우팅·description canonical(A4)**.
5. `deg_input.py` 3소스(meta 컬럼 폴백 포함) + ranked 인터페이스 선언.
6. `EnrichmentRequest/Result` 모델(serializable, `enrichment_recipe` 포함).
7. 단위/통합 테스트(mock 필수, offline monkeypatch 픽스처).

**수용 기준**
- [P1-1] `standardize_go_dataframe()` 기존 로더와 완전 동일 출력(리팩터 회귀).
- [P1-2] ORA 결과 → §6.3~6.6 계약 충족(다구분자 `_gene_set`·라벨·ratio·fold·term_id 정책·canonical description).
- [P1-3] 3종 DEG 입력 추출 단위 테스트(경계/방향/빈 입력/변종 컬럼 폴백).
- [P1-4] 오프라인 매핑 성공(`--offline` 대신 `block_network` 픽스처로 네트워크 차단 상태에서 gene_info 캐시만으로 매핑).
- [P1-5] 캐시 원자성·TTL 테스트(잔여 `.tmp` 없음, sha256 실패 재다운로드, TTL 만료 자동 재다운로드).
- [P1-6] mock 기반 net-path 테스트 green (network/offline 마커 분리).
- [P1-7] (4B 채택 시) KEGG REST name→ID 매핑 mock 테스트 green, 실패 시 빈 값 유지.

**G 해소**: G2 G3 G4 G5 G6 G7 G8 G9 G10 G13 G15 + A1 A4 A5 A6 F1 F4 F7 F8

### Phase 2 — UI (다이얼로그 + Worker 재설계)
**파일**: `go_workers.py`(교체), `enrichment_analysis_dialog.py`, `main_window.py`, `main_presenter.py`, `help_dialog.py`, `docs/user/*.md`, `test_enrichment_dialog.py`.

작업:
1. `EnrichmentWorker(QThread)` — progress/finished(EnrichmentResult)/error; 부분 실패는 warnings 수집; 취소 플래그.
2. `EnrichmentAnalysisDialog`: 입력 소스 탭(현재 DE / 붙여넣기 / Comparison: Statistics), 임계값(FC/FDR/방향), species(Human/Mouse — mouse는 로컬 배너), 라이브러리 체크박스(GO BP/CC/MF + KEGG, **동일 ontology 다중 선택 disable+툴팁 — F10**), 모드(Auto/온라인/로컬/오프라인 + Auto 라우팅 규칙 표기), background 표시+커스텀 파일, 진행바+취소, 완료 요약. **모드 배너: "오프라인=GO 전용(KEGG 비활성)" — 단 ADR-1 결과 종속(F3)**; QSettings offline 토글 연동(F1).
3. `main_window` 메뉴 항목 + `_on_enrichment_analysis()`; `main_presenter.register_enrichment_result()`.
4. 완료 후 결과 Dataset → 새 탭 + DatasetTreePanel 등록 → 기존 GO 시각화 메뉴 재사용. `enrichment_recipe` metadata 기록(A2).
5. F1 help + docs/user(모드·engine·명칭 구분 GSEA Lite vs prerank 포함, A7) + shortcut 테이블.
6. pytest-qt e2e(mock): 3소스 각각, 취소, 오류/빈 결과, 오프라인 KEGG 비활성, 캐시 부재 첫 실행 안내.

**수용 기준**
- [P2-1] 메뉴 항목 DE 로드 시 활성, GO_ANALYSIS에서 비활성.
- [P2-2] 3소스 각각 → Dataset 등록 → 새 탭 → Bar/Dot/Cluster/Network/Filter 재사용(수동 QA + pytest-qt).
- [P2-3] 오프라인/빈 결과/타임아웃/rate-limit/매핑 0건 각각 명시적 UX; **KEGG 배너가 ADR-1 결과와 정합(F3)**.
- [P2-4] 취소 시 부분 결과 폐기(또는 명시적 저장 옵션), worker 크래시 없음.
- [P2-5] help/docs 동기화(명칭 구분 포함) 체크리스트 통과.
- [P2-6] 프로젝트 저장/복원 시 enrichment Dataset 행 복원 + recipe 보존 확인(A2).

**G 해소**: G11 G12 G14 + A2 A3 A4 A7 F3 F10 + CLAUDE.md 규칙

### Phase 3 — 검증·오프라인 fallback·재현성·패키징
**파일**: `requirements.txt`, `setup.py`, spec 3종, `build.ps1`/`build-macos.sh`(검증), `installer.iss`(검증), Export 파이프라인 확인.

작업:
1. **회귀 검증**: 동일 gene list로 기존 `examples/Acute_1D_vs_Control_GO_KEGG.parquet`(또는 `final_go_result.xlsx`) vs 신규 엔진 — 경향 일치 확인(엔진 차이는 해석 주의 문서화).
2. **오프라인 fallback e2e**: `block_network` + 실제 네트워크 차단 상태에서 GO 실행 성공, KEGG 안내, 첫 실행 다운로드 가이드(proxy env).
3. **재현성 메타데이터**: Analysis_Info 체크리스트(§6.9) + **라이선스/ToS 심사(F5)**: Enrichr ToS(결과 재배포·대량 호출), GMT(Enrichr 텍스트 더미) 재배포, NCBI gene2go/gene_info 이용약관 → 문서화.
4. **패키징**: requirements/setup 반영 → `build.ps1` frozen 빌드 → `Program Files` **무쓰기** 확인(캐시=AppData) + 3종 spec `--collect-all`.
5. observability: audit_log + 로그(라이브러리별 소요시간·실패 사유).

**수용 기준**
- [P3-1] frozen 빌드에서 온라인/로컬/오프라인 3모드 동작, Program Files 무쓰기.
- [P3-2] 오프라인 GO 실행 성공 + KEGG 명시적 안내(ADR-1 종속 배너와 정합).
- [P3-3] Analysis_Info 메타데이터 완전성 + **라이선스/ToS 심사 보고서 1건(F5)**.
- [P3-4] 기존 결과 대비 경향 일치 보고서 1건.
- [P3-5] 전체 테스트 스위트 green.
- [P3-6] **성능 상한(F2)**: 로컬 GO 실행 ≤30초(첫 obo 로드 제외), 피크 메모리 증가 ≤800MB, UI 스레드 블로킹 0.
- [P3-7] 프로젝트 저장/복원 검증(A2).

**G 해소**: G1 G6 G13 G14 G15

### Phase 4 — M4b 메타 연동 (GSEA prerank)
**파일**: `enrichment_analyzer.py`(`enrich_prerank` 구현), `deg_input.py`(④ ranked), `enrichment_analysis_dialog.py`(meta 소스 prerank 옵션), help/docs 보강.

작업:
1. `meta_z`/`-log10(meta_pvalue_fisher)×sign(meta_log2fc_mean)` ranked → `gseapy.prerank(gene_sets=캐시 GMT)` — 동일 라벨 규칙으로 Dataset 생성(NES 등 컬럼 보존).
2. **명칭 구분(A7)**: 기존 "GSEA Lite"(Wilcoxon, statistics.py:110)와 "GSEA prerank"(gseapy, 국제 gene set)를 메뉴·도움말·tooltip에서 명시 구분.
3. meta 입력 기록(결합 데이터셋·임계값)을 §6.9에 추가.
4. cross-species 순서 문서화: 종 상이 시 M2(ortholog) → meta-signature → enrichment(M4a는 종 불문 별도 경로, 범위 밖).

**수용 기준**
- [P4-1] prerank mock 테스트 green, 표준 컨버터 통과.
- [P4-2] meta 소스 prerank/ORA 선택 결과 차이 문서화.
- [P4-3] M4b 수용 기준(META_ANALYSIS_PLAN.md) 정합.

**G 해소**: G16

---

## 11. G1~G16 해소 맵 (v1.1 갱신)

| 갭 | 내용 | 해소 위치 |
|---|---|---|
| G1 | 패키징·요구사항·Python 버전 | Phase 0 P0-1/P0-2(Python 실측 F11), Phase 3 작업4, §8(spec 3종·requirements·setup·--collect-all) |
| G2 | 캐시 경로 | §6.8, ADR-3(3A), `data_path_config.py`(Phase 1) |
| G3 | DEG 입력 재사용 | §6.1 ①, Phase 1 `deg_input.py`, Phase 2 소스 탭 |
| G4 | `_gene_set` set 컬럼 | §6.4(다구분자 A5), P0-4, Phase 1 컨버터 |
| G5 | gene_set 라벨 + Dataset 규칙 | §6.3, ADR-B, Phase 1 |
| G6 | bg_ratio/fold_enrichment | §6.5(캐시 GMT 크기), `_compute_fold_enrichment` 재사용·중복 제거 |
| G7 | KEGG term_id | §6.6, ADR-4(4A/4B), P0-2 실측(A1) |
| G8 | Enrichr 커스텀 background | ADR-2(2A), §6.2(로컬 강제), P0-2 실측 |
| G9 | mygene 의존 → 오프라인 붕괴 | §6.7 gene_info 로컬 캐시, P1-4 |
| G10 | Mouse 디테일 | §6.2(로컬 우선 A3), P0-7, taxid 10090 |
| G11 | 명칭 오류 | §6.3, `register_enrichment_result()` + `DatasetTreePanel`(Phase 2) |
| G12 | Worker 시그니처 | §6.2, Phase 2 `EnrichmentWorker`/`EnrichmentResult` |
| G13 | 테스트 전략 | §12(conftest·pytest.ini·mock 픽스처) |
| G14 | 에러/빈 결과/오프라인 KEGG UX | Phase 2 P2-3(ADR-1 종속 F3), Phase 3 P3-2 |
| G15 | 재현성 메타데이터 | §6.9(recipe 포함), Phase 3 P3-3 |
| G16 | meta 입력 + prerank(M4b) | §6.1 ③/④, Phase 1 인터페이스 + Phase 4 |

---

## 12. Expanded test plan (unit / integration / e2e / observability)

네트워크 테스트는 **mock 필수**(G13): `test/fixtures/enrichr_response_go_bp.json`, `enrichr_response_kegg.json`, `mygene_reply.json`, `gene2go_sample.gz`, `gene_info_sample.gz`, `mini-obo.obo`, `sample_gmt.gmt`(기존 `test/sample_gene_set.gmt` 재활용). 마커: `network`(실제 호출, 기본 제외), `offline`(차단 상태), `qt`(pytest-qt) — **`pytest.ini`에서 등록(F4)**. offline 시뮬레이션은 `test/conftest.py`의 `block_network`(requests+urllib+socket monkeypatch) 픽스처(F1).

| 레벨 | 대상 | 핵심 케이스 |
|---|---|---|
| Unit | 컨버터 | 매핑 표 전 항목; **`[;/,]` 다구분자 정규화 후 `_gene_set` 정확성(A5)**; 라벨→direction/ontology; GO term_id·KEGG 빈 값/방어적 hsa/4B REST; fold 수식(0 분모·NaN); description canonical(A4); 기존 로더 동일성 회귀 |
| Unit | DEG 입력 | 임계값 경계; 방향; 빈 결과; 붙여넣기 파서; **species-aware casing(인간 UPPER/mouse Title, A6)**; meta 컬럼 부재·`meta_log2fe/mean` 변종 폴백; ranked 부호 규칙 |
| Unit | 캐시 | 원자적 쓰기; sha256 검증; **TTL 만료 자동 재다운로드/실패 시 기존 캐시+W2(F7)**; `detect_online()`·`block_network` 분기; proxy env; 동시 요청 dedupe |
| Unit | 매퍼 | gene_info 로컬 정확도(taxid 필터); mygene mock; 매핑 0건→ErrorKind.MAPPING |
| Integration | 엔진 | mock enrichr → `to_standard()` 전체 파이프라인; GOATOOLS mini-obo+sample gene2go 로컬(fisher+fdr_bh 손계산 대조); gseapy.enrich 커스텀 background; KEGG REST mock(4B); meta ③ 경로 |
| e2e | 다이얼로그 (pytest-qt) | 3소스 각각 → worker(mock) → Dataset 등록 → 탭 생성 → 기존 시각화 호출 크래시 없음; 취소; 오류/빈 결과/오프라인 KEGG 비활성; 캐시 부재 첫 실행 안내 |
| Observability | 로그/메타 | §6.9 필드 체크리스트(recipe 포함); audit_log 항목; 소요시간·부분 실패 warnings; 결정성(같은 입력 2회 → 같은 결과·메타) |

회귀: `pytest test/test_models.py test/test_statistics.py test/test_fsm.py test/test_figure_bundle_export.py`(F9) 모든 Phase에서 green.

---

## 13. Pre-mortem (실패 시나리오 3건)

1. **"pandas 3.0.3·Python 버전 불일치로 PoC 좌초"** — gseapy/goatools가 구버전 pandas pin 또는 Python 3.10+ 요구로 설치·임포트 실패(F11). → PoC venv에서 버전 조합 재시도(최신 gseapy/goatools); 실패 시 **Option 2 전환**(gseapy는 numpy/pandas 의존이 옅어 성공 확률 높음); 최후 수단: 순수 `requests` 기반 최소 Enrichr 클라이언트 + 로컬 GMT Fisher 직접 구현(의존성 1개, "스냅샷 기준" 정직 명시). 어떤 경우든 **Phase 1 미착수**.
2. **"오프라인 약속 붕괴"** — mygene·gene_info·Enrichr 모두 차단된 실험실 네트워크에서 첫 실행 다운로드 불가. → Phase 1부터 gene_info 로컬 캐시 필수(P1-4), 다운로드 매니저 proxy/재시도/수동 가이드, 불가 시 **번들 옵션**(gene_info/obo/gene2go 설치기 포함, 빌드 크기 ~50MB — Phase 3 선택, **라이선스 심사 선행 F5**). UI는 "완전 오프라인=사전 캐시 필요" 정직 표기(G14), 조용한 온라인 사용 금지.
3. **"기존 GO 다이얼로그 호환 깨짐"** — KEGG term_id 빈 값·`_gene_set` 분리자 불일치·fold NaN으로 클러스터링 전체 singleton·Dot Plot 스케일 붕괴. → Phase 0 P0-5 4개 다이얼로그 강제 스모크(실패 시 Phase 1 금지), 컨버터 계약 단위 테스트 고정(다구분자 포함), Phase 3 기존 parquet과 시각적 회귀 비교. `_gene_set` 빈 set 로거 경고(W1)를 탐지 지표로.

---

## 14. Acceptance criteria (계획 수준) — 전체 게이트

- **파일별 변경 목록 구체적**: 신규 6모듈+다이얼로그+pytest.ini+conftest.py, 수정 8파일(main.py 무변경) — §8.
- **G1~G16 전 항목 추적**: §11 매핑 테이블.
- **PoC 명시적 게이트**: P0-1~P0-7, 실패 시 중단 규칙(§10.0).
- **pandas 3.0.3 + Python 버전 검증 절차**: P0-1 + Phase 0 ①(Python 실측 F11) + Phase 1/3 회귀.
- **DEG 입력 3소스 + prerank 경로**: §6.1.
- **멀티시트 데이터셋 규칙**: §6.3(라벨/`_gene_set`/term_id/fold/description canonical/recipe).
- **패키징·캐시 경로**: Phase 3 + ADR-3 3A.
- **오프라인 UX(ADR-1 종속)**: Phase 2/3.
- **help/doc 동기화 + GSEA 명칭 구분**: Phase 2 작업 5.
- **성능 상한·라이선스 심사**: Phase 3 P3-6/P3-3(F2/F5).

## 15. Verification

| Phase | 명령/방법 |
|---|---|
| 0 | `python -m venv .venv-poc && pip install gseapy goatools mygene statsmodels requests && python -c "import ..."` + `python --version`; enrichr 실호출/GOATOOLS 실행 + **time·memory 측정(F2)**; 컨버터 어서트; `pytest test/test_models.py test/test_statistics.py test/test_figure_bundle_export.py` (goatools deep import: `from goatools.goea.go_enrichment_ns import GOEnrichmentStudyNS` — PoC 확정 경로) |
| 1 | `pytest test/test_enrichment_converter.py test/test_deg_input.py test/test_enrichment_analyzer.py test/test_enrichment_cache.py -m "not network"`; `pytest -m offline`(block_network 픽스처) |
| 2 | `pytest test/test_enrichment_dialog.py` (pytest-qt); 수동 QA(메뉴 활성화→3소스→시각화→취소→오류 toast→프로젝트 저장/복원) |
| 3 | `powershell -File build.ps1` → frozen 스모크(오프라인 포함, Program Files 무쓰기); `pip install -r requirements.txt` 클린 venv; 전체 `pytest`; 성능 상한 측정 |
| 4 | `pytest -m network`(실제 호출 1회)·prerank mock; M4b 정합 체크 |

## 16. Escalation / Risk Gate

- **Gate 1 (Phase 0→1, 하드)**: P0-1~P0-7 미통과 시 착수 금지 — `0-Main` 블로커+옵션(§5 Option 2) 보고 후 재계획.
- **Gate 2 (Phase 1→2, 소프트)**: 컨버터 계약·3소스 추출 테스트 green. 소스 ③는 컬럼 기준 구현(Gate 2 폴백 매핑: `meta_fdr_fisher` 부재 시 `meta_pvalue_fisher` BH 파생, `meta_log2fc_mean`/`meta_log2fe_mean` 변종).
- **Gate 3 (Phase 3 패키징)**: frozen 3모드 스모크·성능 상한·라이선스 심사 통과 필요. **ADR-1 결과(Option 2 여부)는 Phase 2 착수 전 확정** — KEGG 배너와 정합(F3).
- 승인 게이트(배포/머지)는 본 Planner 범위 밖 — 계획 산출로 종료.

## 17. Risks and mitigations

| 위험 | 확률/영향 | 완화 |
|---|---|---|
| pandas 3.0.3·Python 버전 ↔ 신규 엔진 비호환 | 높음/높음 | Phase 0 게이트(F11), Option 2 fallback, 버전 고정, 최후 requests 클라이언트 |
| Enrichr background 비지원으로 통계 해석 오류 | 높음/중 | ADR-2 모드 강제 + UI 해석 주의 + P0-2 실측 |
| mygene/다운로드 차단 실험실 | 중/높음 | gene_info 로컬 캐시(P1-4), proxy/수동 다운로드, 번들 옵션(Phase 3) |
| 빈 term_id·set 불일치로 클러스터링 무력화 | 중/높음 | §6.4 다구분자 정규화 + P0-5 스모크 + 단위 테스트 고정(A1/A5) |
| GOATOOLS 메모리(obo) | 중/중 | 세션 1회 로드 + **P3-6 상한(≤800MB 증가) 측정(F2)** + worker 격리 |
| **Enrichr ToS·GMT 재배포·NCBI gene2go/gene_info 라이선스 (F5)** | 중/중 | Phase 3 P3-3 라이선스/ToS 심사 보고서, 번들 시 선행 심사, 결과 재배포·대량 호출 정책 명시 |
| Rate-limit/타임아웃 | 중/중 | 결과 캐시(동일 입력 재호출 방지), backoff 재시도, 실패 라이브러리만 재시도 |
| meta 컬럼명 변형 | 중/중 | 컬럼 기준 구현 + 변종 폴백(BH 파생 포함) |
| frozen 환경 Program Files 쓰기 | 높음/높음 | ADR-3 3A + Phase 3 무쓰기 검증 |
| help/docs 드리프트 | 중/낮음 | Phase 2 작업 5(help+docs 동시 갱신, GSEA 명칭 구분 포함) |

## 18. ADR candidates (실행 권한자 확정 필요)

| # | 결정 | 옵션 | 권장 | 확정 시점 |
|---|---|---|---|---|
| ADR-1 | 로컬 GO 엔진 | (a) GOATOOLS / (b) gseapy.enrich+캐시 GMT 단일화 | (a), PoC 실패 시 (b); **KEGG 오프라인·Phase 2 배너는 이 결과 종속(F3)** | Phase 0 게이트 |
| ADR-2 | background 정책 | 2A 모드 강제 / 2B 항상 로컬 | 2A(P0-2 실측 후) | Phase 0~1 |
| ADR-3 | 캐시 경로 | 3A AppDataLocation / 3B data_dir / 3C ~/.cmg_seqviewer | 3A | Phase 1 착수 전 |
| ADR-4 | KEGG term_id | 4A 빈 값(description+`_gene_set` 키) / 4B KEGG REST 보강 / 4C 합성 ID | 4A 기본+4B 선택 / 4C는 파괴 시(A1) | Phase 0/1 |
| ADR-5 | 오프라인 강제 메커니즘 | (a) main.py argparse / (b) QSettings+detect_online | (b) — CLI 확장 없음(F1) | Phase 1 |

## 19. Handoff

- **Phase 0**: executor에게 PoC 스크립트(venv 생성→Python/패키지 실측→실호출→GOATOOLS(시간·메모리)→컨버터 어서트→다이얼로그 스모크→mouse 실측) 위임. 결과 보고서를 architect가 검토해 ADR-1/2/4 확정.
- **Phase 1~2**: executor에게 모듈 슬라이스 위임(캐시→매퍼→analyzer→컨버터→deg_input→worker→dialog). architect가 컨버터 계약·`standardize_go_dataframe()` 리팩터 리뷰. `pytest.ini`/`conftest.py`는 Phase 1 시작과 동시에 생성.
- **Phase 3**: critic이 패키징·오프라인·라이선스·성능 상한 검증 계획 비판 후 executor 실행.
- **Phase 4**: M4b 정합은 META_ANALYSIS_PLAN 소유자와 협의 후 executor. GSEA 프레젠테이션 명칭 구분(A7)은 Phase 2 도움말부터 적용.
- 계획 갱신·우선순위 변경 시 `0-Main`과 조율.

---

# 부록 A. RALPLAN-DR 요약 (compact, v1.1)

- **의도**: 로드된 DE 데이터셋/붙여넣기/meta-signature에서 DEG를 즉석 추출하여 gseapy Enrichr(온라인)+GOATOOLS(로컬)로 GO/KEGG enrichment 수행, StandardColumns+`_gene_set` 계약으로 변환해 기존 4개 GO 다이얼로그 재사용.
- **핵심 결정**: ① DEG 입력 3소스+prerank 인터페이스 단일화(G3/G16) ② 결과=1 Dataset 단일 병합 + `direction_ontology` 라벨(G5) ③ 로컬 매핑 캐시로 오프라인 정직화(G9) ④ 커스텀 background=로컬 강제(G8) ⑤ 캐시=AppDataLocation(G2) ⑥ mouse=로컬 우선(A3) ⑦ `enrichment_recipe` metadata로 재실행 경로 보존·재실행은 non-goal(A2/F6) ⑧ Phase 0 하드 게이트(pandas 3.0.3+Python 실측·enrichr 실호출·KEGG Term 구조(4A 기준)·4개 다이얼로그 스모크·시간/메모리).
- **ADR 권장**: ADR-1(a), ADR-2(2A), ADR-3(3A), ADR-4(4A+4B), ADR-5(b: CLI 확장 없음). KEGG 오프라인·Phase 2 배너는 ADR-1 종속(F3).
- **인프라**: pytest.ini(마커), conftest.py(block_network) 신설; main.py 무변경; 라이선스/ToS 심사 Phase 3(F5); 성능 상한 Phase 3(F2).
- **게이트**: P0-1~P0-7 미통과 시 Phase 1 착수 금지(Option 2 전환·블로커 보고).
- **추적**: G1~G16 §11 테이블, A1~A7/F1~F11 Revision Log 표로 해소. READ-ONLY 검증 완료, 파일 무변경.
