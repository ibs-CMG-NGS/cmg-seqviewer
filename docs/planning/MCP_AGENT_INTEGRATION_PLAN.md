# CMG-SeqViewer MCP / AI Agent Integration Plan

- **상태**: 계획 (Phase 0 시작 전)
- **목표 버전**: v1.4.x 이후 (별도 `cmg-seqviewer-mcp` optional extra)
- **작성일**: 2026-10-21
- **관련 문서**: [CLI 도움말](../user/help/19-command-line-interface.md) · [파이프라인 연동](../developer/pipeline-integration.md) · [Expression Summary](../user/help/21-expression-summary.md)

> **Privacy warning (중요)**
> MCP tool의 출력은 **AI 클라이언트로 전달되며**, 클라이언트/모델 제공자에 따라
> 로그·보관·학습에 사용될 수 있습니다. MCP 서버는 이 클라이언트 측 처리를 통제할 수
> 없습니다. 식별 가능한 인간 데이터에는 기관 IRB/DPIA 검토 없이 MCP를 켜지 마세요.
> 기본 정책은 **schema-only**(값 미전송)이며, row preview·이미지·집계값은 프로젝트별
> 명시적 opt-in이 필요합니다. 민감 데이터는 로컬 모델 또는 MCP 비활성화를 권장합니다.

---

## 1. Goal

연구자가 **자신이 구독 중인 AI 클라이언트**(Claude Desktop, Cursor 등)에서 자연어로
cmg-seqviewer의 분석을 실행하고 결과를 확인할 수 있게 한다.

- 기존 GUI 기능은 그대로 유지
- CLI와 MCP가 **동일한 headless 서비스 계층**을 사용
- AI가 도움말·스키마를 참조해 **사용법을 안내**하면서 작업
- v1은 GUI 없이 동작하는 **headless MCP**를 목표로 함
- MCP 서버 자체는 LLM을 호출하지 않음 — 연구자의 AI 클라이언트가 tool을 호출
- **데이터 최소 노출이 기본**: schema-only 정책, row/이미지/집계는 프로젝트별 opt-in

## 2. Non-goals (v1)

- GUI를 AI가 직접 조작하는 live control
- 세포 단위 raw expression 탐색
- MCP 서버 자체에서 LLM/API 호출
- 모든 GUI 기능의 CLI/MCP 노출
- 원격/멀티유저 MCP 서버
- GO/KEGG enrichment의 완전 자동화 (v1.1 이후)
- AI 클라이언트로 raw table/full dataset을 기본 전송하는 것
- 클라이언트 측 데이터 보관·학습 정책을 MCP 서버가 보장하는 것

## 3. Current State

| 영역 | 현재 | 판단 |
|------|------|------|
| CLI | `load/filter/run/batch` (`src/cli.py`) | 자동화 기반은 있음. `list/describe/summary/query/plot/export/compare` 확장 필요 |
| 필터 | `MainPresenter.compute_filtered_df` | GUI 결합. 순수 `FilterService`로 추출 필요 |
| 플롯 | `src/plots/*.py` 렌더러가 Qt 비의존 | **핵심 자산**. Agg로 headless 이미지 생성 가능 |
| DB | `DatabaseManager` import/load/search/export | MCP tool로 노출 가능 |
| 도움말 | `docs/user/help/*.md` | MCP **resources**로 그대로 제공 가능 |
| MCP/서버 | 없음 | `mcp` SDK를 optional extra로 추가 |

### 현재 CLI의 한계

- `load --json`은 타입/행수/컬럼/유효성만 반환
- `filter`는 statistical 모드만 지원 (gene list/keyword/column subset 미지원)
- `summary`, `query`, `plot`, `export`, `compare`, `datasets`, `schema` 명령 없음
- 플롯은 GUI 다이얼로그에서만 실행
- `MainPresenter`를 `SimpleNamespace`로 인스턴스화해 필터만 재사용하는 구조 — MCP에
  그대로 쓰기에는 취약

## 4. Architecture

```
AI client (MCP 지원)
   │ stdio
   ▼
cmg-seqviewer-mcp
   │
   ├── DatasetService
   ├── FilterService
   ├── PlotService
   ├── AnalysisService
   └── HelpService
   │
   ├── 기존 loaders / database_manager
   ├── plots.registry + matplotlib Agg + figure_export
   └── docs/user/help + schema docs

cmg-seqviewer-cli ── 같은 서비스 계층
GUI ─────────────── 기존 유지 (필요 시 서비스 계층 점진적 공유)
```

**원칙**

- MCP는 CLI stdout 파서가 아니라 서비스 API를 직접 호출
- CLI는 서비스의 검증/CI/fallback 인터페이스
- 대용량 결과는 요약 + 파일 artifact + pagination
- 플롯은 GUI와 동일한 renderer/params 사용
- MCP 서버는 상태를 가질 수 있지만, tool 입력은 항상 `dataset_handle`로 명시

## 5. Proposed Service Layer

```
src/services/
├── __init__.py
├── dataset_service.py   # load/list/describe/query/export
├── filter_service.py    # statistical/gene list/keyword/column subset
├── plot_service.py      # plot_type + params -> PNG/SVG/PDF
├── analysis_service.py  # compare/enrichment (옵션)
└── help_service.py      # F1 help/schema 조회
```

- `DatasetService.load()`는 `Dataset` + `handle(UUID)` 반환
- `FilterService`는 `MainPresenter`에서 순수 로직 추출
- `PlotService`는 `plots.registry.render_to_figure()` + `figure_export.save_figure()` 사용
- `AnalysisService`는 v1에서 `compare_datasets` 우선, enrichment는 optional
- 서비스 반환값은 JSON 직렬화 가능한 dict + artifact path + (플롯) PNG bytes

### Dataset handle

- MCP 세션 내 in-memory registry: `handle -> Dataset`
- `list_datasets`로 현재 handle 목록 확인
- `close_dataset(handle)`로 명시 해제 (선택)
- CLI는 상태를 갖지 않음 — 각 명령이 파일을 다시 읽음

## 6. CLI Expansion

기존 명령/옵션은 유지하고 추가:

```
cmg-seqviewer-cli datasets list|describe
cmg-seqviewer-cli load <file> --json
cmg-seqviewer-cli filter <file> --mode statistical|gene-list|keyword|column-subset ...
cmg-seqviewer-cli summary <file> --json
cmg-seqviewer-cli query <file> --columns ... --limit ... --offset ...
cmg-seqviewer-cli plot <file> --plot-type volcano --params-json '{...}' --out out.png
cmg-seqviewer-cli export <file> --format csv|xlsx|parquet --out out.csv
cmg-seqviewer-cli compare <file1> <file2> ... --json
cmg-seqviewer-cli schema|help
```

- 모든 명령에 `--json`/`--out` 규약
- headless 플롯은 `matplotlib.use("Agg")` 사용
- exit code: 0 성공, 1 실패 (기존 규약 유지)

## 7. MCP Server v1

### 7.1 Transport / Packaging

- 기본 **stdio** (외부 포트 없음)
- `cmg-seqviewer-mcp` 콘솔 스크립트
- `mcp` SDK는 **optional extra** (`pip install "cmg-seqviewer[mcp]"`)
- HTTP/SSE는 v2 이후 (localhost + token)
- 공식 지원 클라이언트(v1): **Claude Desktop + Cursor**

### 7.2 Tools

| Tool | 입력/출력 |
|------|-----------|
| `list_datasets` | session/db dataset 목록 |
| `load_dataset` | path 또는 db_id → `handle`, summary |
| `describe_dataset` | handle → type/rows/columns/dtypes/metadata/preview |
| `filter_dataset` | handle + mode/criteria → 새 handle, rows_before/after |
| `summarize_dataset` | handle + group_by → 타입별 통계 |
| `query_rows` | columns/filters/limit/offset → rows preview |
| `plot` | handle + plot_type/params/out_path → image + file path |
| `export_table` | handle + format/out_path |
| `compare_datasets` | handles + method → table/summary |
| `get_help` | topic → 도움말 markdown |

**plot_type (v1 우선순위)**

- `volcano`
- `heatmap`
- `pca`
- `composition`
- `expression_dot`
- (v1.1) `go_dot`, `go_bar`, `multi_group_heatmap`, `gene_expression_bar`

### 7.3 Resources

- `help://index`
- `help://section/{slug}` — F1 도움말 (`docs/user/help/*.md`)
- `schema://dataset/{dataset_type}` — 필수/권장 컬럼
- `docs://pipeline-integration` — 파이프라인 연동 규격
- `workflow://de-analysis`
- `workflow://expression-summary`
- `workflow://composition`

### 7.4 Prompts

- “DE 분석: load → filter → volcano → summary”
- “Expression Summary: gene 검색 → dot plot”
- “Composition: PropRatio/FDR 해석”
- “여러 dataset 비교”
- “이 데이터셋에 맞는 필터/플롯 추천”

### 7.5 Output Contract (privacy-first)

- 기본 응답은 **schema/count/aggregate만** 포함하고 **row 값은 포함하지 않는다.**
  ```json
  {
    "schema_version": "1.0",
    "handle": "...",
    "dataset_type": "differential_expression",
    "row_count": 24506,
    "columns": [{"name": "gene_id", "dtype": "string"}, ...],
    "summary": {"significant_genes": 342},
    "data_policy": "schema_only",
    "warnings": []
  }
  ```
- `query_rows`/preview는 `allow_row_preview=true` + 프로젝트별 동의가 있을 때만
  소량(기본 20행, 최대 100행) 반환한다.
- 이미지(`plot`)는 gene/cell type/condition 라벨을 포함할 수 있으므로
  `allow_images=true` opt-in일 때만 반환한다.
- 대용량 테이블은 **preview + row_count + artifact_path**만 반환한다.
- artifact path는 workspace 상대경로 + SHA-256을 반환하고, 절대경로/사용자명은
  기본적으로 노출하지 않는다.
- 오류: 구조화된 `{error_code, message, hint}` (데이터 값 미포함)

### 7.6 Security

- stdio only, workspace root allowlist
- path traversal 차단 (`..`, 절대경로 정책)
- 기본 read-only, `--allow-write` opt-in
- 네트워크는 enrichment에만 허용
- timeout / max rows / max image size
- **AI 클라이언트 측 데이터 처리(보관/학습/전송)는 MCP 서버가 통제할 수 없음**을
  설정 화면과 문서에 명시
- 민감 데이터는 사용자가 workspace를 지정해 통제
- tool 호출 감사 로그(로컬 JSONL, 기본 on, 값 미기록)
- `CMG_MCP_DISABLE=1` / config `enabled=false` kill switch

### 7.7 Privacy & Data Governance

#### 위협 모델

- MCP tool 결과는 **AI 클라이언트로 전송**되고, 클라이언트가 이를 모델 제공자에게
  보낼 수 있다.
- 클라이언트/모델 제공자의 보관·학습·전송 정책은 앱이 보장할 수 없다.
- 따라서 “데이터가 로컬에만 있다”는 보장은 **MCP 사용 시 성립하지 않는다.**

#### 데이터 노출 레벨

| Level | 이름 | 반환 내용 | 기본 |
|-------|------|-----------|------|
| L0 | `schema_only` | 컬럼명, dtype, row/column count, metadata | ✅ 기본 |
| L1 | `aggregate` | 그룹별 count/평균/top-N 등 집계값 | opt-in |
| L2 | `preview` | 사용자가 지정한 소량 row preview (≤100) | opt-in (per dataset) |
| L3 | `full` | 전체 테이블 | **MCP 미지원** (CLI/로컬 파일 사용) |

- `ai_data_policy` 기본값은 **`schema_only`**.
- `aggregate`/`preview`/`allow_images`는 프로젝트별 config에 명시적으로 기록.
- 데이터셋별 `ai_access` 플래그(예: `deny`, `schema_only`, `aggregate`, `preview`)를
  manifest/metadata에 둘 수 있다.

#### 동의·감사

- MCP 서버는 workspace별 `.cmg-mcp-policy.json`(또는 사용자 config) 없이는
  `schema_only`로만 동작한다.
- 첫 `load_dataset` 시 정책 파일이 없으면 **schema-only로 시작**하고,
  더 높은 레벨은 사용자가 명시적으로 설정해야 한다.
- 감사 로그: `~/.cmg-seqviewer/mcp_audit.jsonl`
  - 기록: timestamp, tool, dataset hash, data_policy, response bytes
  - 미기록: 실제 데이터 값, 절대경로, 사용자명

#### 민감 데이터 권장

- 식별 가능한 인간 데이터: **기관 IRB/DPIA 검토 후** 사용, 기본 MCP 비활성.
- 가능하면 **로컬 모델**(Ollama/llama.cpp 등) 또는 기관 승인 모델 사용.
- Claude Desktop/Cursor 등 클라우드 클라이언트는 제공자의 데이터 정책을 확인.
- MCP가 필요 없으면 `CMG_MCP_DISABLE=1` 또는 optional extra 미설치.

#### 이미지·플롯 주의

- Volcano/heatmap/dot plot 이미지에는 gene symbol, cell type, condition명이 포함될 수
  있다. `allow_images=false`가 기본이며, 켤 때 경고를 표시한다.
- “집계값만” 사용하더라도 top-N gene list는 민감할 수 있으므로 `aggregate`도
  프로젝트별 opt-in으로 둔다.

## 8. Optional GUI Bridge (Phase 3)

- 실행 중인 GUI에 `QLocalServer` 또는 localhost HTTP + token
- `open_in_gui(handle)`, `show_plot_in_gui(...)`, `apply_filter_in_gui(...)`
- GUI가 꺼져 있으면 headless 결과로 fallback
- WSLg 환경에서는 GUI bridge를 권장하지 않음 (현재 알려진 팝업/커서 제약)

## 9. Testing

- `test_services_*.py`: service 단위 테스트
- `test_cli_*.py`: CLI JSON/exit code/출력 포맷
- `test_mcp_server.py`: stdio JSON-RPC tool 호출 (테스트 클라이언트)
- `test_plot_service.py`: Agg 렌더 smoke + 파일 생성
- 대용량 pagination/preview 테스트
- 기존 GUI 테스트 유지 (전체 pytest)
- 최소 1개 실제 AI 클라이언트 end-to-end 수동 검증

## 10. Docs

- `docs/planning/MCP_AGENT_INTEGRATION_PLAN.md` — 본 문서
- `docs/developer/mcp-integration.md` — tool/resource 스키마, 클라이언트 설정
- `docs/user/help/` — “AI Agent / MCP” 사용자 안내
  - Tips/FAQ가 마지막이 되도록 **22번 앞**에 배치하고 Tips/FAQ를 한 칸씩 뒤로 조정
- 보안/privacy 섹션 (`docs/developer/mcp-privacy.md`)
- 데이터 노출 레벨·동의·감사 로그·로컬 모델 권장
- 클라이언트 설정 예시 (Claude Desktop, Cursor)

## 11. Phases & Estimates

| Phase | 내용 | 예상 |
|------|------|------|
| 0 | 결정·tool schema·client 호환성 | 2–3일 |
| 1 | headless services + CLI 확장 + 테스트 | 1–2주 |
| 2 | MCP server v1 (stdio, tools/resources/prompts) | 1주 |
| 3 | (선택) GUI bridge | 1–2주 |
| 4 | packaging/docs/security | 3–5일 |

Phase 3 제외 시 **2–3주**, 포함 시 **4–5주** (1인 기준).

## 12. Acceptance Criteria

- 기존 GUI 기능/테스트 유지
- CLI가 서비스 계층을 통해 `load→filter→plot→export` 수행
- MCP 클라이언트에서 동일 workflow를 headless로 실행
- 플롯 이미지가 AI 클라이언트에 표시되고 파일로 저장됨
- 도움말/스키마 resource로 AI가 사용법을 안내
- MCP 서버가 workspace 밖 접근/쓰기를 기본 차단
- 기본 `schema_only`에서 row 값/이미지가 응답에 포함되지 않음
- `preview`/`aggregate`/이미지는 명시적 opt-in 없이는 거부됨
- 감사 로그가 기록되고 절대경로/사용자명이 노출되지 않음
- 최소 1개 AI 클라이언트(Claude Desktop 또는 Cursor)에서 end-to-end 검증

## 13. Risks

- **데이터 유출/클라이언트 보관·학습**: MCP tool 결과는 AI 클라이언트로 전송됨 → 기본 schema-only, opt-in, 로컬 모델 권장
- 대용량 dataset을 AI context에 넣을 수 없음 → preview/artifact 필수
- headless 플롯과 GUI 플롯의 파라미터 기본값 불일치 → 동일 renderer/params 사용
- enrichment 네트워크/캐시 지연 → v1에서 optional
- MCP 클라이언트별 tool 지원 차이 → 초기 1–2개 클라이언트만 공식 지원
- GUI bridge의 보안/복잡도 → v2로 연기
- WSLg GUI 제약 → MCP headless로 우회, bridge는 비권장
- MCP SDK/스펙 변경 → 버전 pin + 호환성 테스트

## 14. Decisions

확정된 기본값:

1. **v1 범위**: headless 결과(JSON + opt-in PNG + artifact)만. GUI bridge는 Phase 3 선택.
2. **공식 지원 클라이언트**: Claude Desktop + Cursor.
3. **v1 필수 plot**: volcano, heatmap, PCA, composition, expression_dot.
4. **GO/KEGG enrichment**: v1.1 (v1은 기존 결과 조회/필터만).
5. **쓰기 권한**: 기본 read-only + export 허용 (DB import/삭제는 opt-in).
6. **패키징**: 별도 `cmg-seqviewer-mcp` 콘솔 스크립트 + `[mcp]` optional extra.
7. **데이터 정책 기본값**: `schema_only` (row/image/aggregate는 프로젝트별 opt-in), MCP는 기본 비활성·optional extra.

추가 협의 가능:

- HPC/원격 MCP 필요 여부
- enrichment를 v1에 포함할지
- GUI bridge를 어느 시점에 넣을지

## 15. Next Actions

1. Phase 0: **privacy threat model/데이터 노출 레벨 리뷰** + tool schema 초안 + Claude Desktop/Cursor 설정 프로토타입
2. Phase 1: `src/services/` 추출, CLI 확장, headless plot/export 테스트
3. Phase 2: `cmg-seqviewer-mcp` stdio 서버 + resources/prompts
4. Phase 3 이후: GUI bridge, enrichment, 추가 클라이언트
5. 모든 Phase에서 privacy acceptance criteria(7.7) 충족 여부를 릴리스 게이트로 확인
