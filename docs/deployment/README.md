# 배포 가이드 (Deployment Documentation)

> 🚀 CMG-SeqViewer 빌드, 배포, 릴리스 관리 가이드

## 📚 문서 목록

| 문서 | 설명 | 대상 |
|------|------|------|
| [빌드 가이드](build-guide.md) | Windows/macOS 실행 파일 빌드 | 빌드 담당자 |
| [배포 가이드](deployment.md) | GitHub Release 및 CI/CD | 릴리스 매니저 |
| [내부 배포 가이드](internal-distribution.md) | 조직 내부 배포 (작성 예정) | 내부 배포 담당자 |

---

## 🚀 빠른 시작

### Windows 빌드 및 배포 (5단계)

```powershell
# 1. 환경 준비
cd C:\path\to\cmg-seqviewer
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 2. 빌드
.\build.ps1
# 또는: pyinstaller --clean rna-seq-viewer.spec

# 3. 테스트
.\dist\CMG-SeqViewer\CMG-SeqViewer.exe

# 4. 압축
Compress-Archive -Path "dist\CMG-SeqViewer" -DestinationPath "CMG-SeqViewer-v1.2.0-Windows.zip"

# 5. GitHub Release 업로드
# GitHub → Releases → Draft new release
```

### macOS 빌드 및 배포 (5단계)

```bash
# 1. 환경 준비
cd /path/to/cmg-seqviewer
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 2. 빌드
chmod +x build-macos.sh
./build-macos.sh
# 또는: pyinstaller --clean cmg-seqviewer-macos.spec

# 3. 테스트
open dist/CMG-SeqViewer.app

# 4. DMG 생성
hdiutil create -volname "CMG-SeqViewer" -srcfolder dist/CMG-SeqViewer.app -ov -format UDZO CMG-SeqViewer-v1.2.0-macOS.dmg

# 5. GitHub Release 업로드
```

---

## 📦 빌드 프로세스

### Windows 빌드

**빌드 도구**: PyInstaller

**출력**:
- `dist\CMG-SeqViewer\` - 폴더 형태 (권장)
- `dist\CMG-SeqViewer.exe` - 단일 파일 (선택사항)

**주요 파일**:
- `rna-seq-viewer.spec` - PyInstaller 설정
- `build.ps1` - 자동 빌드 스크립트

자세한 내용: [빌드 가이드 - Windows 빌드](build-guide.md#windows-빌드)

### macOS 빌드

**빌드 도구**: PyInstaller

**출력**:
- `dist/CMG-SeqViewer.app` - macOS 앱 번들

**주요 파일**:
- `cmg-seqviewer-macos.spec` - PyInstaller 설정
- `build-macos.sh` - 자동 빌드 스크립트

자세한 내용: [빌드 가이드 - macOS 빌드](build-guide.md#macos-빌드)

---

## 🎯 배포 방식

### Option 1: Portable 배포 ⭐ 권장

**장점**:
- ✅ 설치 불필요 (압축 해제만)
- ✅ USB/네트워크 드라이브에서 실행 가능
- ✅ 여러 버전 동시 사용
- ✅ 관리자 권한 불필요

**용도**:
- 연구실 환경
- 빠른 테스트
- 버전 비교

**생성 방법**:
```powershell
# Windows
Compress-Archive -Path "dist\CMG-SeqViewer" -DestinationPath "CMG-SeqViewer-Portable.zip"

# macOS
zip -r CMG-SeqViewer-macOS.zip dist/CMG-SeqViewer.app
```

### Option 2: Installer 배포

**장점**:
- ✅ 전문적인 설치 경험
- ✅ 시작 메뉴/바탕화면 자동 등록
- ✅ 자동 업데이트 구현 가능

**용도**:
- 최종 사용자 배포
- 대규모 조직

**생성 방법**:
- Windows: Inno Setup 사용
- macOS: PKG 또는 DMG

자세한 내용: [빌드 가이드 - 설치 프로그램 생성](build-guide.md#설치-프로그램-생성)

---

## 📋 릴리스 프로세스

### 수동 릴리스

**1. 버전 업데이트**:
```python
# src/main.py
__version__ = "1.2.0"
```

**2. CHANGELOG 업데이트**:
```markdown
## [1.2.0] - 2026-03-01

### Added
- External data folder support
- Gene annotation context menu
```

**3. Git 태그 생성**:
```powershell
git tag -a v1.2.0 -m "Release v1.2.0: External data folder & gene annotation"
git push origin v1.2.0
```

**4. GitHub Release 생성**:
- Releases → Draft new release
- 태그: v1.2.0
- 빌드 파일 업로드

### CI/CD 자동 릴리스

**GitHub Actions 사용**:
- 태그 푸시 시 자동 빌드
- Windows + macOS 병렬 빌드
- Release 자동 생성 및 파일 업로드

**워크플로우**: `.github/workflows/build.yml`

자세한 내용: [배포 가이드 - CI/CD 워크플로우](deployment.md#cicd-워크플로우)

---

## 🔐 코드 서명

### Windows 코드 서명

**필요사항**:
- 코드 서명 인증서 ($75-150/년)
- SignTool.exe (Windows SDK)

**서명 방법**:
```powershell
signtool sign /f certificate.pfx /p password /t http://timestamp.digicert.com dist\CMG-SeqViewer.exe
```

**장점**:
- Windows Defender 경고 감소
- 사용자 신뢰도 향상

### macOS 코드 서명 및 공증

**필요사항**:
- Apple Developer Account ($99/년)
- Developer ID Application Certificate

**서명 방법**:
```bash
codesign --deep --force --verify --verbose \
         --sign "Developer ID Application: Your Name (TEAMID)" \
         --options runtime \
         dist/CMG-SeqViewer.app
```

**공증 (Notarization)**:
```bash
xcrun notarytool submit CMG-SeqViewer.zip \
  --apple-id your-email@example.com \
  --team-id TEAMID \
  --password app-specific-password \
  --wait

xcrun stapler staple dist/CMG-SeqViewer.app
```

자세한 내용: [빌드 가이드 - 코드 서명](build-guide.md#코드-서명)

---

## ✅ 배포 체크리스트

### 빌드 전
- [ ] 모든 테스트 통과
- [ ] 버전 번호 업데이트
- [ ] CHANGELOG 작성
- [ ] Pre-loaded datasets 준비 (내부용)
- [ ] 의존성 최신화

### 빌드 중
- [ ] 가상환경 활성화
- [ ] 빌드 스크립트 실행
- [ ] 빌드 오류 없음
- [ ] 경고 메시지 검토

### 빌드 후
- [ ] 로컬 실행 테스트
- [ ] 다른 PC 테스트 (Python 없는 환경)
- [ ] 모든 기능 동작 확인
- [ ] 로그 파일 생성 확인

### 배포 전
- [ ] 파일 압축 (ZIP/DMG)
- [ ] Installer 생성 (선택사항)
- [ ] 코드 서명 (선택사항)
- [ ] README 파일 포함
- [ ] Git 태그 생성

### 배포 후
- [ ] GitHub Releases 업로드
- [ ] 릴리스 노트 작성
- [ ] 다운로드 링크 테스트
- [ ] 사용자 문서 업데이트

전체 체크리스트: [배포 가이드 - 배포 체크리스트](deployment.md#배포-체크리스트)

---

## 🔧 문제 해결

### 빌드 문제

**모듈 없음 오류**:
```python
# .spec 파일의 hiddenimports에 추가
hiddenimports=[
    'missing_module',
]
```

**DLL 오류**:
```powershell
# Visual C++ Redistributable 필요
# https://aka.ms/vs/17/release/vc_redist.x64.exe
```

**파일 크기 큰 문제**:
```python
# .spec 파일에서 불필요한 패키지 제외
excludes=[
    'tkinter',
    'matplotlib.tests',
]
```

### 배포 문제

**Git 푸시 실패**:
```powershell
git pull origin main --rebase
git push origin main
```

**GitHub Actions 실패**:
- YAML 문법 검증
- 태그 형식 확인 (v1.2.0)
- Actions 탭에서 로그 확인

**Release 생성 안됨**:
- Workflow permissions 확인
- `startsWith(github.ref, 'refs/tags/')` 조건 확인

전체 문제 해결: [빌드 가이드 - 문제 해결](build-guide.md#문제-해결)

---

## 📊 릴리스 전략

### 버전 관리 (Semantic Versioning)

**MAJOR.MINOR.PATCH** (예: 1.2.0)

- **MAJOR**: 하위 호환성 깨지는 변경 (2.0.0)
- **MINOR**: 새 기능 추가 (1.3.0)
- **PATCH**: 버그 수정 (1.2.1)

### 릴리스 주기

**Patch 릴리스**:
- 주기: 필요 시 (critical bug)
- 예: v1.2.0 → v1.2.1

**Minor 릴리스**:
- 주기: 2-4주
- 예: v1.2.0 → v1.3.0

**Major 릴리스**:
- 주기: 3-6개월
- 예: v1.x.x → v2.0.0

### 브랜치 전략

```
main (stable)
  ├── develop (integration)
  │   ├── feature/external-data-folder
  │   ├── feature/gene-annotation
  │   └── feature/atac-seq
  └── hotfix/critical-bug
```

---

## 🔗 관련 문서

### 사용자용
- [설치 가이드](../user/installation.md)
- [사용자 매뉴얼](../user/user-guide.md) (작성 예정)

### 개발자용
- [개발 환경 설정](../developer/setup.md)
- [기여 가이드](../developer/contributing.md) (작성 예정)

### 기타
- [CHANGELOG](../archive/CHANGELOG.md)
- [GitHub Actions 가이드](https://docs.github.com/en/actions)

---

## 📝 작성 예정 문서

- [ ] internal-distribution.md - 내부 배포 가이드
- [ ] release-notes-template.md - 릴리스 노트 템플릿
- [ ] ci-cd-setup.md - CI/CD 상세 설정

---

**마지막 업데이트**: 2026-03-01  
**버전**: v1.2.0
