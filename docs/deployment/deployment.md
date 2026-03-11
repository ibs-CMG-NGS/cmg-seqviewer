# CMG-SeqViewer 배포 가이드 (Deployment Guide)

> **목적**: CMG-SeqViewer를 GitHub에 릴리스하고, 사용자에게 배포하는 전체 프로세스를 설명합니다.

## 목차
1. [배포 전 준비](#배포-전-준비)
2. [데이터 보안](#데이터-보안)
3. [GitHub 업로드](#github-업로드)
4. [릴리스 생성](#릴리스-생성)
5. [CI/CD 워크플로우](#cicd-워크플로우)
6. [배포 후 작업](#배포-후-작업)
7. [문제 해결](#문제-해결)

---

## 배포 전 준비

### 필수 파일 체크리스트

#### 코드 및 설정 파일
- [ ] `README.md` - 최신 기능 반영
- [ ] `LICENSE` - 라이센스 파일 (MIT 권장)
- [ ] `.gitignore` - 제외할 파일 설정 (venv, build, **내부 데이터**)
- [ ] `requirements.txt` - 프로덕션 의존성
- [ ] `requirements-dev.txt` - 개발 의존성 (PyInstaller 포함)

#### 빌드 설정
- [ ] `rna-seq-viewer.spec` - Windows 빌드 설정
- [ ] `cmg-seqviewer-macos.spec` - macOS 빌드 설정 (있는 경우)
- [ ] `build.ps1` - Windows 자동 빌드 스크립트
- [ ] `build-macos.sh` - macOS 자동 빌드 스크립트 (있는 경우)

#### 문서
- [ ] `docs/` 폴더 구조 정리
  - [ ] `docs/user/` - 사용자 가이드
  - [ ] `docs/developer/` - 개발자 가이드
  - [ ] `docs/deployment/` - 배포 가이드
  - [ ] `docs/archive/CHANGELOG.md` - 버전 변경사항

#### CI/CD (선택사항, 권장)
- [ ] `.github/workflows/build.yml` - GitHub Actions 워크플로우

### 코드 품질 검증

```powershell
# 1. 모든 테스트 통과 확인
python -m pytest test/

# 2. 코드 스타일 검사 (선택사항)
pip install flake8
flake8 src/ --max-line-length=120

# 3. 타입 검사 (선택사항)
pip install mypy
mypy src/

# 4. 로컬 빌드 테스트
.\build.ps1

# 5. 빌드된 실행 파일 테스트
.\dist\CMG-SeqViewer\CMG-SeqViewer.exe
```

### 버전 관리

#### 1. 버전 번호 업데이트

**시맨틱 버저닝 (Semantic Versioning)**:
- `MAJOR.MINOR.PATCH` (예: `1.2.0`)
- **MAJOR**: 하위 호환성 깨지는 변경
- **MINOR**: 새 기능 추가 (하위 호환)
- **PATCH**: 버그 수정

**업데이트 위치**:
```python
# src/main.py
__version__ = "1.2.0"

# setup.py (있는 경우)
version="1.2.0"

# installer.iss (Inno Setup 사용 시)
#define MyAppVersion "1.2.0"
```

#### 2. CHANGELOG 작성

`docs/archive/CHANGELOG.md` 업데이트:

```markdown
## [1.2.0] - 2026-01-15

### Added
- External data folder support (`data/` directory)
- Gene annotation context menu (NCBI, GeneCards, Ensembl, etc.)
- GO/KEGG annotation context menu with ID extraction
- Database refresh functionality

### Changed
- Multi-path database system (data/ + database/)
- Database Browser UI improvements
- Help dialog with Gene Annotation section

### Fixed
- Metadata auto-generation bug (removed feature)
- Database refresh now reloads metadata correctly
```

---

## 데이터 보안

### 🔒 중요: 내부 연구 데이터 보호

공개 저장소에 업로드하기 전 **반드시** 내부 데이터가 제외되었는지 확인하세요.

#### .gitignore 설정 확인

```gitignore
# .gitignore

# Internal research data - DO NOT COMMIT
database/datasets/*.parquet
database/metadata.json
data/datasets/*.parquet
data/metadata.json

# Keep directory structure
!database/.gitkeep
!database/datasets/.gitkeep
!data/.gitkeep
!data/datasets/.gitkeep

# Build outputs
build/
dist/
*.spec.backup

# Python
venv/
__pycache__/
*.pyc

# IDE
.vscode/
.idea/

# Logs
logs/
*.log
```

#### 데이터 보호 검증

```powershell
# 1. .parquet 파일이 staging되지 않았는지 확인
git status | Select-String "parquet"
# 출력: 없어야 함

# 2. metadata.json이 staging되지 않았는지 확인
git status | Select-String "metadata.json"
# 출력: 없어야 함 (또는 database/README.md 언급만)

# 3. Git 히스토리에 데이터가 없는지 확인
git log --all --full-history -- "database/datasets/*.parquet"
# 출력: 없어야 함

# 4. 저장소 크기 확인 (데이터 없으면 작아야 함)
git count-objects -vH
# size-pack: < 50 MiB 권장

# 5. Push 전 마지막 확인
git diff --stat --cached origin/main
# .parquet 파일이 나타나면 안됨
```

#### 🛑 데이터 발견 시 대처

```powershell
# Staging에서 제거
git reset HEAD database/datasets/*.parquet
git reset HEAD database/metadata.json

# 이미 커밋된 경우 (주의: 히스토리 재작성)
git filter-branch --force --index-filter \
  "git rm -rf --cached --ignore-unmatch database/datasets/" \
  HEAD

# 또는 git-filter-repo 사용 (권장)
pip install git-filter-repo
git filter-repo --path database/datasets/ --invert-paths
```

### 내부 데이터 배포 방법

내부 연구 데이터는 **별도로 배포**하세요:

1. **Portable 버전에 포함**:
   ```powershell
   # 빌드 전에 database/datasets/에 데이터 추가
   # 빌드 후 내부용으로만 배포
   ```

2. **별도 데이터 패키지**:
   ```powershell
   # 데이터만 압축
   Compress-Archive -Path "database/datasets/*" -DestinationPath "CMG-SeqViewer-InternalData.zip"
   
   # 내부 사용자에게만 제공
   # 사용자는 data/ 폴더에 압축 해제
   ```

3. **네트워크 공유**:
   - 조직 내부 네트워크 드라이브에 데이터 저장
   - 사용자가 실행 파일 옆 `data/` 폴더에 심볼릭 링크 생성

자세한 내용: `docs/deployment/internal-distribution.md` 참고

---

## GitHub 업로드

### Phase 1: 로컬 Git 준비

```powershell
# 1. 프로젝트 폴더로 이동
cd C:\Users\USER\Documents\GitHub\rna-seq-data-view

# 2. Git 상태 확인 (이미 초기화된 경우)
git status

# 3. 초기화 안된 경우
git init
git branch -M main

# 4. 변경사항 추가
git add .

# 5. 커밋
git commit -m "feat: Release v1.2.0 - External data folder & gene annotation

Features:
- External data folder support (data/ directory with priority over database/)
- Gene annotation context menu (NCBI, GeneCards, Ensembl, UniProt, Google Scholar)
- GO/KEGG annotation context menu with automatic ID extraction
- Database refresh and open data folder buttons
- Help documentation with Gene Annotation section

Technical:
- Multi-path database system with DataPathConfig
- Metadata reload on refresh (no auto-generation)
- File source tracking for debugging
- Context menu with intelligent column detection

Documentation:
- Reorganized docs/ structure (user/, developer/, deployment/, planning/, archive/)
- Consolidated CHANGELOG.md (v1.0.0 through v1.2.0)
- Build guide consolidation
- Developer setup guide
- User guides"
```

### Phase 2: GitHub 저장소 생성

**GitHub 웹에서**:

1. https://github.com/new 방문
2. 저장소 설정:
   - **이름**: `cmg-seqviewer` (권장) 또는 `rna-seq-data-view`
   - **설명**: "Desktop application for RNA-Seq differential expression analysis with GO/KEGG pathway enrichment and gene annotation"
   - **가시성**: Public (무료 CI/CD) 또는 Private
3. **중요**: 다음 옵션 체크 해제
   - ❌ Initialize this repository with a README
   - ❌ Add .gitignore
   - ❌ Choose a license
4. "Create repository" 클릭

### Phase 3: 로컬과 원격 연결

```powershell
# 1. Remote 추가 (YOUR_USERNAME을 실제 GitHub 사용자명으로 교체)
git remote add origin https://github.com/YOUR_USERNAME/cmg-seqviewer.git

# 2. Remote 확인
git remote -v
# origin  https://github.com/YOUR_USERNAME/cmg-seqviewer.git (fetch)
# origin  https://github.com/YOUR_USERNAME/cmg-seqviewer.git (push)

# 3. Push
git push -u origin main

# 인증 필요 시: Personal Access Token 사용
# https://github.com/settings/tokens에서 생성
# Scopes: repo (전체 저장소 접근)
```

### Phase 4: 저장소 설정 (GitHub 웹)

1. **Topics 추가**:
   - 저장소 페이지 → About 옆 ⚙️ 클릭
   - Topics: `rna-seq`, `bioinformatics`, `data-visualization`, `pyqt6`, `go-analysis`, `kegg-pathway`, `python`, `genomics`, `gene-annotation`

2. **Description 설정**:
   - "Desktop app for RNA-Seq analysis with GO/KEGG clustering, gene annotation, and interactive visualizations"

3. **Website** (선택사항):
   - 문서 사이트가 있으면 추가

---

## 릴리스 생성

### 수동 릴리스

#### 1. Git 태그 생성

```powershell
# Annotated tag 생성 (권장)
git tag -a v1.2.0 -m "Release v1.2.0: External Data Folder & Gene Annotation

🆕 Major Features:
- External data folder support (data/ directory)
- Gene annotation context menu (5 databases)
- GO/KEGG annotation context menu (7+ databases)
- Database refresh and folder management
- Intelligent column type detection

📊 Improvements:
- Multi-path database system (data/ priority over database/)
- Metadata reload on refresh
- Context menu auto-detects gene/GO/KEGG columns
- Help dialog with comprehensive Gene Annotation section

📖 Documentation:
- Reorganized docs structure
- Consolidated CHANGELOG
- Updated build and deployment guides

🐛 Bug Fixes:
- Removed auto-metadata generation (caused data duplication)
- Database refresh now properly reloads metadata"

# 태그 확인
git tag -l

# 태그 푸시
git push origin v1.2.0
```

#### 2. GitHub Release 생성

**GitHub 웹에서**:

1. 저장소 → Releases → "Draft a new release"
2. 설정:
   - **Tag**: `v1.2.0` (방금 생성한 태그)
   - **Title**: "v1.2.0 - External Data Folder & Gene Annotation"
   - **Description**: 태그 메시지 복사 + 추가 정보
3. **Assets 업로드**:
   ```powershell
   # 로컬에서 빌드
   .\build.ps1
   
   # Windows Portable ZIP 생성
   Compress-Archive -Path "dist\CMG-SeqViewer" -DestinationPath "CMG-SeqViewer-v1.2.0-Windows-Portable.zip"
   
   # macOS (있는 경우)
   # ./build-macos.sh
   # hdiutil create -volname "CMG-SeqViewer" -srcfolder dist/CMG-SeqViewer.app -ov -format UDZO CMG-SeqViewer-v1.2.0-macOS.dmg
   ```
4. ZIP/DMG 파일을 드래그하여 업로드
5. "Publish release" 클릭

---

## CI/CD 워크플로우

### GitHub Actions 설정

#### .github/workflows/build.yml

```yaml
name: Build CMG-SeqViewer

on:
  push:
    tags:
      - 'v*'  # v1.0.0, v1.2.0 등에 트리거

jobs:
  build-windows:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      
      - name: Build with PyInstaller
        run: |
          pyinstaller --clean --noconfirm rna-seq-viewer.spec
      
      - name: Create ZIP
        run: |
          Compress-Archive -Path "dist\CMG-SeqViewer" -DestinationPath "CMG-SeqViewer-Windows.zip"
      
      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: windows-build
          path: CMG-SeqViewer-Windows.zip

  build-macos:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      
      - name: Build with PyInstaller
        run: |
          pyinstaller --clean --noconfirm cmg-seqviewer-macos.spec
      
      - name: Create DMG
        run: |
          hdiutil create -volname "CMG-SeqViewer" -srcfolder dist/CMG-SeqViewer.app -ov -format UDZO CMG-SeqViewer-macOS.dmg
      
      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: macos-build
          path: CMG-SeqViewer-macOS.dmg

  create-release:
    needs: [build-windows, build-macos]
    runs-on: ubuntu-latest
    if: startsWith(github.ref, 'refs/tags/')
    steps:
      - name: Download Windows build
        uses: actions/download-artifact@v4
        with:
          name: windows-build
      
      - name: Download macOS build
        uses: actions/download-artifact@v4
        with:
          name: macos-build
      
      - name: Create Release
        uses: softprops/action-gh-release@v1
        with:
          files: |
            CMG-SeqViewer-Windows.zip
            CMG-SeqViewer-macOS.dmg
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### 워크플로우 작동 방식

1. **트리거**: `v*` 형태의 태그가 푸시되면 자동 실행
2. **병렬 빌드**:
   - `build-windows`: Windows 실행 파일 빌드 (15-20분)
   - `build-macos`: macOS .app 빌드 (15-20분)
3. **릴리스 생성**:
   - 두 빌드 완료 후 실행
   - GitHub Release 자동 생성
   - 빌드 결과물 자동 업로드

### 워크플로우 모니터링

```powershell
# 1. 태그 푸시
git push origin v1.2.0

# 2. GitHub에서 확인
# Repository → Actions 탭
# - 워크플로우 실행 확인
# - 각 job 로그 확인
# - 15-20분 후 완료

# 3. Release 확인
# Repository → Releases
# - v1.2.0 릴리스 자동 생성 확인
# - Windows ZIP, macOS DMG 다운로드 가능
```

### 비용 (GitHub Actions)

- **Public 저장소**: 무제한 무료
- **Private 저장소**: 2,000분/월 무료, 이후 $0.008/분
- **권장**: Public으로 만들어 무료 사용

---

## 배포 후 작업

### 즉시 (Day 1)

#### 1. 다운로드 테스트
```powershell
# GitHub Release에서 다운로드
# Windows: CMG-SeqViewer-Windows.zip
# macOS: CMG-SeqViewer-macOS.dmg

# 압축 해제 및 실행 테스트
# - Python 없는 PC에서 테스트 권장
# - 모든 기능 동작 확인
```

#### 2. README 배지 추가 (선택사항)
```markdown
<!-- README.md 상단에 추가 -->
[![Build Status](https://github.com/YOUR_USERNAME/cmg-seqviewer/workflows/Build%20CMG-SeqViewer/badge.svg)](https://github.com/YOUR_USERNAME/cmg-seqviewer/actions)
[![Release](https://img.shields.io/github/v/release/YOUR_USERNAME/cmg-seqviewer)](https://github.com/YOUR_USERNAME/cmg-seqviewer/releases)
[![License](https://img.shields.io/github/license/YOUR_USERNAME/cmg-seqviewer)](LICENSE)
```

#### 3. Issue 템플릿 생성
```markdown
<!-- .github/ISSUE_TEMPLATE/bug_report.md -->
---
name: Bug Report
about: Create a report to help us improve
title: '[BUG] '
labels: bug
assignees: ''
---

**Describe the bug**
A clear and concise description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:
1. Go to '...'
2. Click on '...'
3. See error

**Expected behavior**
What you expected to happen.

**Screenshots**
If applicable, add screenshots.

**Environment:**
- OS: [e.g., Windows 10, macOS 13]
- Version: [e.g., v1.2.0]

**Additional context**
Any other information about the problem.
```

### 단기 (Week 1)

#### 1. 문서 개선
- [ ] 스크린샷 추가 (README, 사용자 가이드)
- [ ] 데모 비디오 녹화 (선택사항)
- [ ] FAQ 작성 (예상 질문)

#### 2. 커뮤니티 설정
- [ ] GitHub Discussions 활성화
- [ ] CONTRIBUTING.md 작성
- [ ] CODE_OF_CONDUCT.md 추가

#### 3. 홍보 (선택사항)
- Twitter/LinkedIn에 공유
- 관련 포럼/커뮤니티에 소개
- 바이오인포매틱스 Slack/Discord 채널

### 중기 (Month 1)

#### 1. 사용자 피드백
- [ ] Issue 모니터링
- [ ] 버그 우선순위 설정
- [ ] Feature request 검토

#### 2. 분석
- [ ] 다운로드 통계 확인 (Insights → Traffic)
- [ ] Star/Fork 성장 추적
- [ ] Actions 사용량 모니터링

#### 3. 반복 개발
- [ ] v1.2.1 버그 수정 릴리스 계획
- [ ] v1.3.0 기능 추가 계획
- [ ] Roadmap 공개 (ROADMAP.md 또는 Projects)

---

## 문제 해결

### Git 푸시 실패

**증상**: `git push` 시 "rejected" 오류

**원인**: 원격에 로컬에 없는 커밋이 있음

**해결**:
```powershell
# 1. 원격 변경사항 가져오기
git pull origin main --rebase

# 2. 충돌 해결 (있는 경우)
# 충돌 파일 수정 후:
git add .
git rebase --continue

# 3. 다시 푸시
git push origin main
```

### GitHub Actions 워크플로우 실행 안됨

**증상**: 태그 푸시했는데 Actions 트리거 안됨

**원인**: 
1. YAML 문법 오류
2. 태그 형식 불일치 (`v` 접두사 없음)
3. 워크플로우 파일 경로 오류

**해결**:
```powershell
# 1. YAML 문법 검증
# https://www.yamllint.com/ 에서 .github/workflows/build.yml 검증

# 2. 태그 확인
git tag -l
# v1.2.0 형태여야 함 (v 접두사 필수)

# 3. 워크플로우 파일 경로 확인
ls .github/workflows/
# build.yml이 있어야 함

# 4. Actions 탭에서 오류 확인
# Repository → Actions → 실패한 워크플로우 클릭 → 로그 확인
```

### 빌드 실패 (특정 플랫폼)

**증상**: Windows는 성공, macOS는 실패 (또는 반대)

**원인**: 플랫폼별 의존성 문제

**해결**:
```yaml
# .github/workflows/build.yml 수정

# hiddenimports 추가
- name: Build with PyInstaller
  run: |
    # .spec 파일에 누락된 모듈 추가
    pyinstaller --hidden-import=missing_module --clean rna-seq-viewer.spec

# 또는 의존성 설치 단계에서:
- name: Install platform-specific dependencies
  run: |
    pip install pyobjc-framework-Cocoa  # macOS 전용
  if: runner.os == 'macOS'
```

### Release 생성 안됨

**증상**: 빌드는 성공했는데 Release가 생성되지 않음

**원인**: `create-release` job 조건 불만족

**해결**:
```yaml
# .github/workflows/build.yml 확인

create-release:
  if: startsWith(github.ref, 'refs/tags/')  # 이 조건 확인
  
# Repository Settings → Actions → General → Workflow permissions
# "Read and write permissions" 선택
```

### 다운로드한 실행 파일이 작동 안함

**증상**: 사용자가 다운로드한 .exe가 실행되지 않음

**원인**:
1. Microsoft Visual C++ Redistributable 누락
2. 백신 프로그램 차단
3. 빌드 오류

**해결**:

**사용자 안내 (README에 추가)**:
```markdown
## 시스템 요구사항

### Windows
- **Windows 10/11** (64-bit)
- **Microsoft Visual C++ Redistributable**: [다운로드](https://aka.ms/vs/17/release/vc_redist.x64.exe)
- **백신 경고**: 서명되지 않은 실행 파일이므로 Windows Defender가 경고할 수 있습니다. "추가 정보" → "실행"을 선택하세요.

### macOS
- **macOS 10.13 (High Sierra) 이상**
- **Gatekeeper 우회**: `xattr -cr /Applications/CMG-SeqViewer.app` 실행
```

### 저장소 크기가 너무 큼

**증상**: 저장소가 100MB 이상

**원인**: 잘못 커밋된 바이너리 파일

**해결**:
```powershell
# 큰 파일 찾기
git rev-list --objects --all | git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' | sed -n 's/^blob //p' | sort --numeric-sort --key=2 | tail -n 10

# 히스토리에서 제거 (주의: 히스토리 재작성)
git filter-repo --path-glob '*.parquet' --invert-paths
git filter-repo --path-glob 'dist/*' --invert-paths

# Force push (주의!)
git push origin main --force
```

---

## 베스트 프랙티스

### 릴리스 주기

**버그 수정 릴리스 (Patch)**:
- 주기: 필요 시 (critical bug 발견 시 즉시)
- 버전: v1.2.0 → v1.2.1

**기능 추가 릴리스 (Minor)**:
- 주기: 2-4주마다
- 버전: v1.2.0 → v1.3.0

**주요 변경 릴리스 (Major)**:
- 주기: 3-6개월마다
- 버전: v1.x.x → v2.0.0

### 릴리스 노트 작성

**좋은 예**:
```markdown
## v1.2.0 - 2026-01-15

### 🆕 Added
- External data folder support for post-deployment dataset management
- Gene annotation context menu with 5 major databases (NCBI, GeneCards, etc.)
- GO/KEGG annotation context menu with automatic ID extraction
- Database refresh button to reload metadata without restart

### 🔧 Changed
- Database system now supports multiple paths (data/ and database/)
- Help dialog includes new Gene Annotation section with usage examples

### 🐛 Fixed
- Removed auto-metadata generation that caused data duplication bugs
- Database refresh now properly reloads metadata.json

### 📖 Documentation
- Reorganized docs/ structure for better navigation
- Consolidated CHANGELOG from scattered UPDATE files

### ⚠️ Breaking Changes
None

### 📦 Assets
- Windows: CMG-SeqViewer-v1.2.0-Windows-Portable.zip
- macOS: CMG-SeqViewer-v1.2.0-macOS.dmg
```

**나쁜 예**:
```markdown
## v1.2.0
- Some fixes
- Added stuff
- Updated things
```

### 커밋 메시지 규칙

**Conventional Commits** 사용 권장:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Type**:
- `feat`: 새 기능
- `fix`: 버그 수정
- `docs`: 문서 변경
- `style`: 코드 포맷팅 (기능 변경 없음)
- `refactor`: 리팩토링
- `test`: 테스트 추가/수정
- `chore`: 빌드, 설정 등

**예시**:
```powershell
git commit -m "feat(database): add external data folder support

- Implement DataPathConfig for multi-path database
- Add data/ directory with priority over database/
- Update Database Browser with refresh and open folder buttons

Closes #123"
```

---

## 다음 단계

배포가 완료되었다면:

1. [사용자 가이드](../user/README.md) - 최종 사용자 문서 확인
2. [빌드 가이드](./build-guide.md) - 빌드 프로세스 상세 정보
3. [개발자 가이드](../developer/setup.md) - 개발 환경 설정
4. [CHANGELOG](../archive/CHANGELOG.md) - 버전별 변경사항

---

## 참고 자료

- **GitHub Docs**: https://docs.github.com/
- **GitHub Actions**: https://docs.github.com/en/actions
- **Semantic Versioning**: https://semver.org/
- **Keep a Changelog**: https://keepachangelog.com/
- **Conventional Commits**: https://www.conventionalcommits.org/
