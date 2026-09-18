# F1 도움말 시스템 전면 개편 — 검토 및 실행 계획

- Date: 2026-09-03 (UTC+09:00) · Repo: `/home/ygkim/cmg-seqviewer`
- 상태: 검토 완료 → 도입 실행 (본 문서는 계획 + 이행 로그)

---

## 1. 현황 검토 (스크립트 방식의 단점)

현재 F1 도움말은 `src/gui/help_dialog.py`(121.8KB) 하나의 Python 파일에
**20여 개 `_get_*` 메서드가 HTML 문자열을 조립**해 `QTextBrowser.setHtml()`로 렌더합니다.

단점:
- **관리성**: 도움말 수정/추가 = Python 파일 편집 + HTML 문자열 이스케이프 (diff/review가 코드와 콘텐츠를 구분 못함).
- **편집성**: 편집기 미리보기·문법 검사 불가, 마크다운 생산성 없음.
- **구조**: TOC/섹션 분리·검색 재사용 어려움, docs(웹/문서)와 분리된 이중 관리.
- **확장성**: 위키형 운영(문서 파일 단위 PR/리뷰) 불가.

검증: PyQt6 6.11 `QTextBrowser.setMarkdown()`은 **헤딩/리스트/볼드/코드블록/GFM 표**를
네이티브 렌더 (의존성 추가 불필요).

## 2. 설계 (Markdown 파일 1원본 + Qt 렌더, wiki 운용)

- **콘텐츠 1원본**: `docs/user/help/NN-slug.md` (18개 섹션, 파일명 번호로 정렬).
  - 기존 20개 `_get_*` HTML → Markdown 자동 이관(1차) 후 자유 편집 (전폭적 콘텐츠 수정은 MD에서 진행).
  - GSEA/Enrichment 섹션은 **영문 유지**(분석 UI 영문화 요구와 정합); 나머지 섹션 언어는 기존 그대로.
- **뷰어**: `help_dialog.py` 재작성 — `HelpDialog` (F1, main_window import 유지):
  - 좌: 검색 필터(QLineEdit) + TOC(QListWidget, 파일 `#` 제목), 우: `QTextBrowser.setMarkdown(파일본문)`.
  - 경로 해석: 개발 `docs/user/help/`(repo 루트) → frozen 번들(`sys.executable` 기준 후보) → 부재 시 안내.
- **패키징**: spec 3종 datas에 `('docs/user/help', 'docs/user/help')` 추가.
- **docs 정합**: `docs/user/user-guide.md`(장문)와 `docs/user/help/*.md`(조각) 동일 MD 생태계 — single source.

## 3. 이행 단계

1. `docs/planning/HELP_SYSTEM_OVERHAUL_PLAN.md` (본 문서) — 검토/설계/수용기준.
2. 뷰어 재작성: `src/gui/help_dialog.py` (TOC+검색+setMarkdown, 기존 `HelpDialog(parent)` 시그니처 유지).
3. HTML→MD 이관 스크립트로 `docs/user/help/NN-slug.md` 18개 생성 (내용 보존 우선).
4. spec 3종 datas 추가.
5. 테스트: `test/test_help_dialog.py` (pytest-qt) — 구성·파일 수·제목·렌더 smoke·검색 필터·폴백.
6. 전체 스위트 green 확인 + 헤드리스 실렌더 검증.

## 4. 수용 기준

- [H1] F1 → `HelpDialog` 동일 진입점, 기존 섹션 18개 전부 마크다운 파일로 제공.
- [H2] 뷰어는 `setMarkdown` 렌더 (헤딩/리스트/표 표시), 외부 링크 오픈.
- [H3] TOC 위 검색 필터로 섹션 필터 (wiki 느낌).
- [H4] frozen 번들(datas) 포함 + 경로 폴백 시 크래시 없음.
- [H5] 전체 테스트 스위트 green + 신규 smoke 테스트 추가.
- [H6] GSEA/Enrichment 섹션 영문 유지 확인.

## 5. 이행 완료 (2026-09-03)

| 항목 | 상태 | 근거 |
|---|---|---|
| H1 | ✅ | `docs/user/help/NN-slug.md` 18개 이관(`scripts/help_html_to_md.py`로 1차 생성), F1→`HelpDialog(self)` 동일 |
| H2 | ✅ | `QTextBrowser.setMarkdown()` (PyQt6 네이티브, GFM 표 렌더 실측) |
| H3 | ✅ | 검색 필터 추가(테스트 `test_search_filter`) |
| H4 | ✅ | spec 3종 datas에 `('docs/user/help','docs/user/help')` + 경로 폴백(테스트 `test_missing_dir_fallback`) |
| H5 | ✅ | `test/test_help_dialog.py` 13건 + 전체 스위트 **184+4+3 green** |
| H6 | ✅ | 신규 Enrichment/A7 섹션(`06-go-enrichment-analysis.md`) 한글 0자 |

## 5b. 후속 작업 (콘텐츠 심화 — 2026-09-03)

- **재구성 + 영문 단일화**: 19개 섹션 재번호(01~19 토픽 정렬), 전체 한글 0자(검증 테스트 고정).
- **스크린샷 첨부**: `assets/*.png` 6장 (실데이터 기반 offscreen 렌더, std 30~74 비균일 검증) —
  01 메인윈도우 / 05 차트 4종 + 클러스터링 / 06 Enrichment 다이얼로그. 뷰어 `baseUrl`로 로컬 이미지 렌더.
- **워크플로우 예시**: 05(파이프라인 엔드투엔드), 06(Enrichment + meta/ORA/prerank), 07(GO Term Comparison 재작성·예시).
- **운영 환경 실배포 캡처 교체(외부 호스트 필요)**: 배포된 Windows/macOS 빌드에서 동일 파일명으로
  재캡처 → `docs/user/help/assets/` 덮어쓰기 (마크다운 참조 불변). WSL 헤드리스에서는 불가한 추적 항목.
- 구 `_get_*` HTML 문자열 메서드 전부 제거 (help_dialog.py 121.8KB → 6.2KB).