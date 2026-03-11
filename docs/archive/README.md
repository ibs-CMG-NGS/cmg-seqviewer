# 보관 문서 (Archive)

> 📁 레거시 문서, 변경 이력, 이전 버전 관련 자료

## 📚 문서 목록

### 변경 이력
| 문서 | 설명 | 기간 |
|------|------|------|
| [CHANGELOG.md](CHANGELOG.md) | 전체 버전 변경사항 (v1.0.0~현재) | 2025-12-01 ~ 현재 |

### 레거시 문서
| 문서 | 원본 위치 | 보관 사유 |
|------|----------|-----------|
| UPDATE_2025_12_09.md | docs/ | CHANGELOG.md로 통합 |
| UPDATE_2025_12_09_PART4.md | docs/ | CHANGELOG.md로 통합 |
| UPDATE_2025_12_09_PART5.md | docs/ | CHANGELOG.md로 통합 |
| UPDATE_2025_12_09_PART6.md | docs/ | CHANGELOG.md로 통합 |
| UPDATE_2025_12_10_PART7.md | docs/ | CHANGELOG.md로 통합 |
| UPDATE_2025_12_10_PART8.md | docs/ | CHANGELOG.md로 통합 |
| UPDATE_2025_12_10_PART9.md | docs/ | CHANGELOG.md로 통합 |

---

## 📖 CHANGELOG

전체 버전 변경사항은 [CHANGELOG.md](CHANGELOG.md)를 참조하세요.

### 주요 마일스톤

**v1.0.0** (2025-12-01)
- 🎉 첫 공개 릴리스
- FSM 기반 아키텍처
- 기본 RNA-seq 분석 기능

**v1.0.6** (2025-12-15)
- 🔧 GO/KEGG Clustering 안정화
- 🎨 Network visualization 개선
- 🐛 다수의 버그 수정

**v1.0.11** (2026-01-01)
- 🎨 크로스 플랫폼 UI 통합 (Light theme)
- 🍎 macOS 다크 모드 이슈 해결
- 📊 로그 터미널 고정 크기

**v1.2.0** (2026-03-01)
- 🆕 외부 데이터 폴더 지원
- 🔗 Gene/GO/KEGG 컨텍스트 메뉴
- 🔄 데이터베이스 새로고침
- 📚 문서 재구성

---

## 🗂️ 레거시 문서 보관

### UPDATE 파일 통합 (2026-03-01)

**보관된 파일** (9개):
```
docs/
├── UPDATE_2025_12_09.md          → CHANGELOG.md v1.0.5-v1.0.6
├── UPDATE_2025_12_09_PART4.md    → CHANGELOG.md v1.0.6
├── UPDATE_2025_12_09_PART5.md    → CHANGELOG.md v1.0.6
├── UPDATE_2025_12_09_PART6.md    → CHANGELOG.md v1.0.7
├── UPDATE_2025_12_10_PART7.md    → CHANGELOG.md v1.0.8
├── UPDATE_2025_12_10_PART8.md    → CHANGELOG.md v1.0.9
└── UPDATE_2025_12_10_PART9.md    → CHANGELOG.md v1.0.10-v1.0.11
```

**통합 사유**:
- 파편화된 업데이트 노트
- 버전별 변경사항 추적 어려움
- Keep a Changelog 형식으로 표준화

**새 구조**:
- [CHANGELOG.md](CHANGELOG.md) - 단일 통합 파일
- Keep a Changelog 형식
- Added/Changed/Fixed 섹션으로 명확한 구분

### 빌드 가이드 통합 (2026-03-01)

**보관된 파일** (4개):
```
root/
├── BUILD.md                  → docs/deployment/build-guide.md
├── BUILD_MACOS.md           → docs/deployment/build-guide.md
├── DEPLOYMENT.md            → docs/deployment/build-guide.md + deployment.md
└── DISTRIBUTION.md          → docs/deployment/build-guide.md
```

**통합 사유**:
- 중복된 내용 (Windows/macOS 빌드)
- 배포 방식 분산
- 단일 소스 오브 트루스 부재

**새 구조**:
- [docs/deployment/build-guide.md](../deployment/build-guide.md) - 빌드 통합
- [docs/deployment/deployment.md](../deployment/deployment.md) - 배포 프로세스

### 개발 가이드 통합 (2026-03-01)

**보관된 파일** (3개):
```
root/ & docs/
├── DEVELOPMENT_SETUP.md     → docs/developer/setup.md
├── docs/DEVELOPMENT.md      → docs/developer/setup.md
└── docs/QUICK_START.md      → docs/developer/setup.md
```

**통합 사유**:
- 개발 환경 설정 중복
- 빠른 시작과 상세 가이드 분리 불필요
- 혼란스러운 문서 구조

**새 구조**:
- [docs/developer/setup.md](../developer/setup.md) - 개발자 통합 가이드

---

## 📊 문서 재구성 이력

### Phase 1: 폴더 구조 생성 (2026-03-01)

**생성된 폴더**:
```
docs/
├── user/              # 사용자 가이드
├── developer/         # 개발자 가이드
├── deployment/        # 배포 가이드
├── planning/          # 기획 문서
└── archive/           # 보관 문서
    └── legacy/        # 레거시 파일
```

### Phase 2: CHANGELOG 통합 (2026-03-01)

**작업**:
- 9개 UPDATE 파일 → 단일 CHANGELOG.md
- Keep a Changelog 형식 적용
- v1.0.0 ~ v1.2.0 (13개 버전) 통합

### Phase 3: 빌드 가이드 통합 (2026-03-01)

**작업**:
- BUILD.md + BUILD_MACOS.md + DEPLOYMENT.md + DISTRIBUTION.md
- → docs/deployment/build-guide.md (26KB)
- → docs/deployment/deployment.md (22KB)

### Phase 4: 개발 가이드 통합 (2026-03-01)

**작업**:
- DEVELOPMENT_SETUP.md + DEVELOPMENT.md + QUICK_START.md
- → docs/developer/setup.md (23KB)

### Phase 5: 사용자 가이드 작성 (2026-03-01)

**작업**:
- docs/user/installation.md 생성 (18KB)
- Windows/macOS 설치 통합

### Phase 6: README 인덱스 생성 (2026-03-01)

**작업**:
- docs/README.md - 전체 문서 인덱스
- docs/user/README.md - 사용자 문서 인덱스
- docs/developer/README.md - 개발자 문서 인덱스
- docs/deployment/README.md - 배포 문서 인덱스
- docs/planning/README.md - 기획 문서 인덱스
- docs/archive/README.md - 보관 문서 인덱스

---

## 🔍 레거시 파일 찾기

### 원본 파일 위치

레거시 파일은 향후 `docs/archive/legacy/` 폴더로 이동될 예정입니다.

**현재 위치**:
- UPDATE 파일: `docs/UPDATE_2025_12_*.md`
- 빌드 가이드: 루트의 `BUILD*.md`, `DEPLOYMENT.md`, `DISTRIBUTION.md`
- 개발 가이드: 루트의 `DEVELOPMENT_SETUP.md`, `docs/DEVELOPMENT.md`, `docs/QUICK_START.md`

**이동 계획**:
```
docs/archive/legacy/
├── update/
│   ├── UPDATE_2025_12_09.md
│   ├── UPDATE_2025_12_09_PART4.md
│   └── ... (9 files)
├── build/
│   ├── BUILD.md
│   ├── BUILD_MACOS.md
│   ├── DEPLOYMENT.md
│   └── DISTRIBUTION.md
└── development/
    ├── DEVELOPMENT_SETUP.md
    ├── DEVELOPMENT.md
    └── QUICK_START.md
```

---

## 📝 변경 이력 규칙

### Commit 메시지

**문서 정리**:
```
docs: reorganize documentation structure

- Create user/, developer/, deployment/, planning/, archive/ folders
- Consolidate 9 UPDATE files into CHANGELOG.md
- Merge BUILD guides into deployment/build-guide.md
```

**레거시 보관**:
```
docs: move legacy files to archive/legacy/

- Move UPDATE_2025_12_*.md to archive/legacy/update/
- Move old BUILD*.md to archive/legacy/build/
- Update links in README
```

### CHANGELOG 작성

**형식**:
```markdown
## [1.2.0] - 2026-03-01

### Added
- New feature description

### Changed
- Changed behavior description

### Fixed
- Bug fix description

### Deprecated
- Deprecated feature (to be removed)

### Removed
- Removed feature

### Security
- Security fix
```

**참고**: [Keep a Changelog](https://keepachangelog.com/)

---

## 🔗 관련 문서

- [CHANGELOG](CHANGELOG.md) - 전체 변경사항
- [문서 인덱스](../README.md) - 전체 문서 구조
- [최근 업데이트](../RECENT_UPDATES.md) - 최신 변경사항

---

**마지막 업데이트**: 2026-03-01  
**상태**: 문서 재구성 진행 중
