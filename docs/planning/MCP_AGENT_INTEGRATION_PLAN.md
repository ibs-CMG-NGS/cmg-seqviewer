# CMG-SeqViewer MCP / AI Agent Integration Plan

- **상태**: 계획 (Phase 0 시작 전)
- **목표 버전**: v1.4.x 이후 (별도 `cmg-seqviewer-mcp` optional extra)
- **작성일**: 2026-10-21
- **관련 문서**: [CLI 도움말](../user/help/19-command-line-interface.md) · [파이프라인 연동](../developer/pipeline-integration.md) · [Expression Summary](../user/help/21-expression-summary.md)

---

## 1. Goal

연구자가 **자신이 구독 중인 AI 클라이언트**(Claude Desktop, Cursor 등)에서 자연어로
cmg-seqviewer의 분석을 실행하고 결과를 확인할 수 있게 한다.

- 기존 GUI 기능은 그대로 유지
- CLI와 MCP가 **동일한 headless 서비스 계층**을 사용
- AI가 도움말·스키마를 참조해 **사용법을 안내**하면서 작업
- v1은 GUI 없이 동작하는 **headless MCP**를 목표로 함
- MCP 서버 자체는 LLM을 호출하지 않음 — 연구자의 AI 클라이언트가 tool을 호출

## 2. Non-goals (v1)

- GUI를 AI가 직접 조작하는 live control
- 세포 단위 raw expression 탐색
- MCP 서버 자체에서 LLM/API 호출
- 모든 GUI 기능의 CLI/MCP 노출
- 원격/멀티유저 MCP 서버
- GO/KEGG enrichment의 완전 자동화 (v1.1 이후)

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

### 7.5 Output Contract

- 텍스트: JSON
  ```json
  {
    "schema_version": "1.0",
    "handle": "...",
    "summary": {...},
    "artifact_path": "...",
    "warnings": []
  }
  ```
- 이미지: MCP `ImageContent` (PNG)
- 대용량 테이블: preview N행 + `row_count` + `artifact_path`
- 오류: 구조화된 `{error_code, message, hint}`

### 7.6 Security

- stdio only, workspace root allowlist
- path traversal 차단 (`..`, 절대경로 정책)
- 기본 read-only, `--allow-write` opt-in
- 네트워크는 enrichment에만 허용
- timeout / max rows / max image size
- AI 클라이언트로 tool 결과가 전송됨을 문서화
- 민감 데이터는 사용자가 workspace를 지정해 통제

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
- 보안/privacy 섹션
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
- 최소 1개 AI 클라이언트(Claude Desktop 또는 Cursor)에서 end-to-end 검증

## 13. Risks

- 대용량 dataset을 AI context에 넣을 수 없음 → preview/artifact 필수
- headless 플롯과 GUI 플롯의 파라미터 기본값 불일치 → 동일 renderer/params 사용
- enrichment 네트워크/캐시 지연 → v1에서 optional
- MCP 클라이언트별 tool 지원 차이 → 초기 1–2개 클라이언트만 공식 지원
- GUI bridge의 보안/복잡도 → v2로 연기
- WSLg GUI 제약 → MCP headless로 우회, bridge는 비권장
- MCP SDK/스펙 변경 → 버전 pin + 호환성 테스트

## 14. Decisions

확정된 기본값:

1. **v1 범위**: headless 결과(JSON + PNG + artifact)만. GUI bridge는 Phase 3 선택.
2. **공식 지원 클라이언트**: Claude Desktop + Cursor.
3. **v1 필수 plot**: volcano, heatmap, PCA, composition, expression_dot.
4. **GO/KEGG enrichment**: v1.1 (v1은 기존 결과 조회/필터만).
5. **쓰기 권한**: 기본 read-only + export 허용 (DB import/삭제는 opt-in).
6. **패키징**: 별도 `cmg-seqviewer-mcp` 콘솔 스크립트 + `[mcp]` optional extra.

추가 협의 가능:

- HPC/원격 MCP 필요 여부
- enrichment를 v1에 포함할지
- GUI bridge를 어느 시점에 넣을지

## 15. Next Actions

1. Phase 0: tool schema 초안 + Claude Desktop/Cursor 설정 프로토타입
2. Phase 1: `src/services/` 추출, CLI 확장, headless plot/export 테스트
3. Phase 2: `cmg-seqviewer-mcp` stdio 서버 + resources/prompts
4. Phase 3 이후: GUI bridge, enrichment, 추가 클라이언트
