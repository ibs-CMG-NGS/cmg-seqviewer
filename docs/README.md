# CMG-SeqViewer Documentation

> 📚 **CMG-SeqViewer**의 통합 문서 저장소입니다. 사용자, 개발자, 배포 관련 모든 문서를 제공합니다.

## 📂 문서 구조

```
docs/
├── user/              # 사용자 가이드
│   ├── installation.md         # 설치 가이드
│   ├── quick-start.md         # 빠른 시작 (작성 예정)
│   ├── user-guide.md          # 전체 사용자 매뉴얼 (작성 예정)
│   ├── COLUMN_MAPPING_GUIDE.md # 컬럼 매핑 가이드
│   └── README.md              # 사용자 문서 인덱스
│
├── developer/         # 개발자 가이드
│   ├── setup.md               # 개발 환경 설정
│   ├── architecture.md        # 아키텍처 설명 (작성 예정)
│   ├── contributing.md        # 기여 가이드 (작성 예정)
│   └── README.md              # 개발자 문서 인덱스
│
├── deployment/        # 배포 가이드
│   ├── build-guide.md         # 빌드 가이드
│   ├── deployment.md          # 배포 프로세스
│   ├── internal-distribution.md # 내부 배포 (작성 예정)
│   └── README.md              # 배포 문서 인덱스
│
├── planning/          # 기획 문서
│   ├── ATAC_SEQ_INTEGRATION_PLAN.md # ATAC-seq 통합 계획
│   └── README.md              # 기획 문서 인덱스
│
└── archive/           # 보관 문서
    ├── CHANGELOG.md           # 전체 변경 이력
    ├── legacy/                # 레거시 문서
    └── README.md              # 보관 문서 인덱스
```

---

## 🎯 빠른 탐색

### 👤 사용자

**처음 사용하시나요?**
1. [설치 가이드](user/installation.md) - Windows/macOS 설치 방법
2. [빠른 시작](user/quick-start.md) - 5분 만에 첫 분석 (작성 예정)
3. [사용자 매뉴얼](user/user-guide.md) - 전체 기능 설명 (작성 예정)

**데이터 임포트 문제?**
- [컬럼 매핑 가이드](user/COLUMN_MAPPING_GUIDE.md) - Excel 파일 형식 안내

**문제 해결**
- [FAQ](user/faq.md) - 자주 묻는 질문 (작성 예정)
- [설치 가이드 - 문제 해결 섹션](user/installation.md#문제-해결)

### 👨‍💻 개발자

**개발 환경 설정**
1. [개발자 설정 가이드](developer/setup.md) - 환경 구축 (5분)
2. [프로젝트 아키텍처](developer/architecture.md) - 코드 구조 이해 (작성 예정)
3. [기여 가이드](developer/contributing.md) - Pull Request 작성 (작성 예정)

**코드 이해**
- [FSM 다이어그램](FSM_DIAGRAM.md) - 상태 머신 구조
- [데이터베이스 가이드](DATABASE_GUIDE.md) - DB 스키마
- API 문서 (작성 예정)

### 🚀 배포 담당자

**빌드 및 배포**
1. [빌드 가이드](deployment/build-guide.md) - 실행 파일 생성
2. [배포 가이드](deployment/deployment.md) - GitHub Release 프로세스
3. [내부 배포 가이드](deployment/internal-distribution.md) - 조직 내부 배포 (작성 예정)

**릴리스 관리**
- [CHANGELOG](archive/CHANGELOG.md) - 버전별 변경사항
- [릴리스 체크리스트](deployment/deployment.md#배포-체크리스트)

### 📋 기획자

**미래 계획**
- [ATAC-seq 통합 계획](planning/ATAC_SEQ_INTEGRATION_PLAN.md) - 멀티오믹스 로드맵

---

## 📑 전체 문서 목록

### 사용자 문서
| 문서 | 설명 | 상태 |
|------|------|------|
| [installation.md](user/installation.md) | Windows/macOS 설치 가이드 | ✅ 완료 |
| [quick-start.md](user/quick-start.md) | 5분 빠른 시작 | 📝 작성 예정 |
| [user-guide.md](user/user-guide.md) | 전체 기능 사용법 | 📝 작성 예정 |
| [COLUMN_MAPPING_GUIDE.md](user/COLUMN_MAPPING_GUIDE.md) | 데이터 임포트 가이드 | ✅ 완료 |
| [faq.md](user/faq.md) | 자주 묻는 질문 | 📝 작성 예정 |

### 개발자 문서
| 문서 | 설명 | 상태 |
|------|------|------|
| [setup.md](developer/setup.md) | 개발 환경 설정 | ✅ 완료 |
| [architecture.md](developer/architecture.md) | 아키텍처 설명 | 📝 작성 예정 |
| [contributing.md](developer/contributing.md) | 기여 가이드 | 📝 작성 예정 |
| [testing.md](developer/testing.md) | 테스트 작성 가이드 | 📝 작성 예정 |
| [FSM_DIAGRAM.md](FSM_DIAGRAM.md) | FSM 상태 다이어그램 | ✅ 완료 |

### 배포 문서
| 문서 | 설명 | 상태 |
|------|------|------|
| [build-guide.md](deployment/build-guide.md) | Windows/macOS 빌드 | ✅ 완료 |
| [deployment.md](deployment/deployment.md) | GitHub 배포 프로세스 | ✅ 완료 |
| [internal-distribution.md](deployment/internal-distribution.md) | 내부 배포 가이드 | 📝 작성 예정 |

### 기획 문서
| 문서 | 설명 | 상태 |
|------|------|------|
| [ATAC_SEQ_INTEGRATION_PLAN.md](planning/ATAC_SEQ_INTEGRATION_PLAN.md) | ATAC-seq 통합 계획 | ✅ 완료 |

### 보관 문서
| 문서 | 설명 | 상태 |
|------|------|------|
| [CHANGELOG.md](archive/CHANGELOG.md) | 버전별 변경사항 | ✅ 완료 |
| [RECENT_UPDATES.md](RECENT_UPDATES.md) | 최근 업데이트 | ✅ 완료 |

---

## 🔍 주제별 가이드

### 설치 및 시작
1. [시스템 요구사항](user/installation.md#시스템-요구사항)
2. [Windows 설치](user/installation.md#windows-설치)
3. [macOS 설치](user/installation.md#macos-설치)
4. [Python 환경 설정](user/installation.md#python-개발-환경-설정-선택사항)
5. [첫 실행](user/installation.md#첫-실행)

### 개발 시작
1. [개발 환경 빠른 시작](developer/setup.md#빠른-시작-5분)
2. [VS Code 설정](developer/setup.md#vs-code-통합-개발-환경)
3. [개발 모드 이해](developer/setup.md#개발-모드)
4. [디버깅 방법](developer/setup.md#디버깅)
5. [테스트 실행](developer/setup.md#테스트)

### 빌드 및 배포
1. [Windows 빌드](deployment/build-guide.md#windows-빌드)
2. [macOS 빌드](deployment/build-guide.md#macos-빌드)
3. [배포 준비](deployment/deployment.md#배포-전-준비)
4. [GitHub 릴리스](deployment/deployment.md#릴리스-생성)
5. [CI/CD 설정](deployment/deployment.md#cicd-워크플로우)

### 문제 해결
1. [설치 문제](user/installation.md#문제-해결)
2. [개발 환경 문제](developer/setup.md#문제-해결)
3. [빌드 문제](deployment/build-guide.md#문제-해결)
4. [배포 문제](deployment/deployment.md#문제-해결)

---

## 📝 문서 작성 가이드

### 새 문서 작성 시

**파일명 규칙**:
- 소문자 + 하이픈: `user-guide.md`
- 예외: 기존 대문자 파일 (CHANGELOG.md, README.md)

**문서 구조**:
```markdown
# 제목

> **목적**: 이 문서가 다루는 내용 한 줄 요약

## 목차
1. [섹션 1](#섹션-1)
2. [섹션 2](#섹션-2)

---

## 섹션 1

내용...

---

## 다음 단계

관련 문서 링크
```

**마크다운 스타일**:
- 코드 블록에 언어 지정: ` ```python `, ` ```powershell `
- 경로는 백틱: `src/main.py`
- 강조: **굵게**, *기울임*
- 이모지 사용 권장: ✅ ❌ ⚠️ 💡 🚀 📝

---

## 🔄 문서 업데이트 이력

| 날짜 | 변경사항 | 담당자 |
|------|---------|--------|
| 2026-03-01 | 문서 구조 재편성 (user/, developer/, deployment/, planning/, archive/) | - |
| 2026-03-01 | CHANGELOG.md 통합 (9개 UPDATE 파일) | - |
| 2026-03-01 | 빌드 가이드 통합 (BUILD.md, BUILD_MACOS.md 등) | - |
| 2026-03-01 | 배포 가이드 통합 (DEPLOYMENT.md, UPLOAD_CHECKLIST.md) | - |
| 2026-03-01 | 개발자 가이드 통합 (DEVELOPMENT_SETUP.md 등) | - |
| 2026-03-01 | 설치 가이드 작성 (installation.md) | - |

---

## 📞 기여 및 피드백

### 오타 발견 또는 개선 제안
1. [GitHub Issues](https://github.com/ibs-CMG-NGS/cmg-seqviewer/issues) 생성
2. 라벨: `documentation` 추가
3. 구체적인 설명과 제안사항 작성

### Pull Request
1. 문서 수정 후 PR 생성
2. 제목: `docs: 문서명 - 변경사항`
3. 예: `docs: installation.md - macOS 설치 섹션 추가`

---

## 📚 외부 참고 자료

- **Python 공식 문서**: https://docs.python.org/3/
- **PyQt6 문서**: https://www.riverbankcomputing.com/static/Docs/PyQt6/
- **pandas 문서**: https://pandas.pydata.org/docs/
- **matplotlib 문서**: https://matplotlib.org/stable/
- **GitHub Actions 가이드**: https://docs.github.com/en/actions

---

**마지막 업데이트**: 2026-03-01  
**버전**: v1.2.0 (feature/external-data-folder)
