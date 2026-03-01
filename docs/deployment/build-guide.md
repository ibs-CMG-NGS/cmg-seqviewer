# CMG-SeqViewer 빌드 가이드 (Build Guide)

> **목적**: CMG-SeqViewer를 플랫폼별 실행 파일로 빌드하고 배포하는 방법을 설명합니다.

## 목차
1. [Windows 빌드](#windows-빌드)
2. [macOS 빌드](#macos-빌드)
3. [배포 방식](#배포-방식)
4. [설치 프로그램 생성](#설치-프로그램-생성)
5. [코드 서명](#코드-서명)
6. [문제 해결](#문제-해결)

---

## Windows 빌드

### 사전 요구사항
- **Python 3.9 이상** (3.10+ 권장)
- **Git** (버전 관리)
- **가상환경** (venv 또는 conda)

### 환경 준비
```powershell
# 1. 저장소 클론 (이미 있으면 생략)
git clone <repository-url>
cd rna-seq-data-view

# 2. 가상환경 생성 및 활성화
python -m venv venv
.\venv\Scripts\Activate.ps1

# 3. 의존성 설치
pip install -r requirements.txt
pip install -r requirements-dev.txt  # PyInstaller 포함
```

### 빌드 방법

#### ⭐ 방법 1: 자동 빌드 (권장)
```powershell
# PowerShell 스크립트 실행
.\build.ps1
```

**출력 결과**:
- `dist\CMG-SeqViewer\` - 폴더 형태 (빠른 실행)
- `dist\CMG-SeqViewer.exe` - 단일 파일 (선택적)

#### 방법 2: 수동 빌드

**폴더 형태** (권장 - 빠른 실행):
```powershell
pyinstaller --clean --noconfirm rna-seq-viewer.spec
```

**단일 파일** (배포 편리):
```powershell
pyinstaller --clean --noconfirm rna-seq-viewer-onefile.spec
```

#### 방법 3: 명령줄 직접 빌드
```powershell
# 폴더 형태
pyinstaller --name="CMG-SeqViewer" --windowed --onedir src/main.py

# 단일 파일
pyinstaller --name="CMG-SeqViewer" --windowed --onefile src/main.py
```

### 빌드 옵션 설명

| 옵션 | 설명 | 용도 |
|------|------|------|
| `--windowed` | 콘솔 창 숨김 | GUI 전용 앱 |
| `--onedir` | 폴더 형태 생성 | 빠른 실행, 여러 파일 |
| `--onefile` | 단일 실행 파일 | 배포 편리, 실행 느림 |
| `--clean` | 이전 빌드 캐시 삭제 | 클린 빌드 |
| `--noconfirm` | 확인 없이 덮어쓰기 | 자동화 |
| `--icon=icon.ico` | 아이콘 지정 | 커스텀 아이콘 |

### 빌드 결과물 구조

**폴더 형태 (`dist\CMG-SeqViewer\`)**:
```
CMG-SeqViewer/
├── CMG-SeqViewer.exe       # 메인 실행 파일
├── _internal/              # PyInstaller 내부 파일
│   ├── *.dll              # 필요한 DLL들
│   ├── Python DLLs/       # Python 라이브러리
│   └── ...
├── data/                   # 외부 데이터 폴더 (사용자 추가용)
│   ├── .gitkeep
│   ├── README.txt
│   └── datasets/          # 사용자 parquet 파일
└── database/              # Pre-loaded datasets
    ├── metadata.json      # 데이터셋 메타데이터
    └── datasets/          # Pre-loaded parquet 파일들
        ├── dataset1.parquet
        └── dataset2.parquet
```

**단일 파일 (`dist\CMG-SeqViewer.exe`)**:
- 모든 라이브러리가 단일 파일에 압축
- 첫 실행 시 임시 폴더에 압축 해제 (느림)
- `database/` 폴더는 임시 폴더에 생성

### Pre-loaded Datasets 관리

#### 배포 전 데이터 준비
빌드하기 **전**에 `database/` 폴더에 데이터셋을 추가하세요:

```powershell
# 옵션 1: 프로그램에서 Import
# 1. python src/main.py 실행
# 2. Database Browser → Import Dataset
# 3. 원하는 데이터 추가

# 옵션 2: 직접 파일 복사
# database/datasets/에 .parquet 파일 복사
# database/metadata.json 수동 편집
```

#### 배포판에 포함되는 파일
- `database/metadata.json` - 데이터셋 메타데이터
- `database/datasets/*.parquet` - Parquet 형식 데이터 파일

#### 사용자 데이터 추가 (v1.2.0+)
배포 후 사용자는 **외부 데이터 폴더**를 사용할 수 있습니다:

1. **실행 파일 옆 `data/` 폴더** (우선순위 1)
   - `CMG-SeqViewer.exe`와 같은 위치
   - `data/datasets/` - Parquet 파일
   - `data/metadata.json` - 메타데이터

2. **내장 `database/` 폴더** (우선순위 2)
   - Pre-loaded datasets (읽기 전용)

**사용자가 데이터 추가하는 방법**:
- File → Database Browser → Import Dataset
- 또는 `data/datasets/`에 파일 + 메타데이터 직접 추가
- Database Browser의 **Open Data Folder** 버튼으로 폴더 열기

### 아이콘 추가 (선택사항)
```powershell
# PNG를 ICO로 변환
pip install pillow
python -c "from PIL import Image; img = Image.open('logo.png'); img.save('icon.ico')"

# .spec 파일에 아이콘 경로 추가
# icon='icon.ico'
```

### 빌드 테스트
```powershell
# 로컬 테스트
.\dist\CMG-SeqViewer\CMG-SeqViewer.exe

# 다른 PC에서 테스트 (Python 없는 환경) - 권장
# USB나 네트워크로 dist 폴더 복사 후 실행
```

---

## macOS 빌드

### 사전 요구사항
- **macOS**: 10.13 (High Sierra) 이상
- **Python 3.9 이상**
- **Xcode Command Line Tools**: 코드 서명용 (선택사항)
  ```bash
  xcode-select --install
  ```

### 환경 준비
```bash
# 1. 저장소 클론
git clone <repository-url>
cd rna-seq-data-view

# 2. 가상환경 생성 및 활성화
python3 -m venv venv
source venv/bin/activate

# 3. 의존성 설치
pip3 install -r requirements.txt
pip3 install -r requirements-dev.txt
```

### 빌드 방법

#### ⭐ 방법 1: 자동 빌드 (권장)
```bash
# 실행 권한 부여 (최초 1회)
chmod +x build-macos.sh

# 빌드 실행
./build-macos.sh
```

#### 방법 2: 수동 빌드
```bash
# 이전 빌드 정리
rm -rf build dist

# PyInstaller 실행
pyinstaller --clean --noconfirm cmg-seqviewer-macos.spec
```

### 빌드 결과물 구조

**`.app` 번들**:
```
dist/CMG-SeqViewer.app/
├── Contents/
│   ├── MacOS/
│   │   └── CMG-SeqViewer              # 실행 파일
│   ├── Resources/
│   │   ├── database/                  # Pre-loaded datasets
│   │   │   ├── metadata.json
│   │   │   └── datasets/*.parquet
│   │   ├── data/                      # 외부 데이터 폴더
│   │   │   ├── .gitkeep
│   │   │   └── datasets/
│   │   ├── cmg-seqviewer.icns        # 아이콘
│   │   └── (기타 리소스)
│   ├── Frameworks/                    # Python 라이브러리
│   │   ├── Python.framework/
│   │   └── *.dylib
│   └── Info.plist                     # 앱 메타데이터
```

### macOS 아이콘 생성 (선택사항)
```bash
# PNG를 ICNS로 변환
mkdir icon.iconset
sips -z 16 16     logo.png --out icon.iconset/icon_16x16.png
sips -z 32 32     logo.png --out icon.iconset/icon_16x16@2x.png
sips -z 32 32     logo.png --out icon.iconset/icon_32x32.png
sips -z 64 64     logo.png --out icon.iconset/icon_32x32@2x.png
sips -z 128 128   logo.png --out icon.iconset/icon_128x128.png
sips -z 256 256   logo.png --out icon.iconset/icon_128x128@2x.png
sips -z 256 256   logo.png --out icon.iconset/icon_256x256.png
sips -z 512 512   logo.png --out icon.iconset/icon_256x256@2x.png
sips -z 512 512   logo.png --out icon.iconset/icon_512x512.png
sips -z 1024 1024 logo.png --out icon.iconset/icon_512x512@2x.png

# ICNS 생성
iconutil -c icns icon.iconset
```

---

## 배포 방식

### Windows 배포

#### Option 1: Portable 배포 ⭐ 권장
```powershell
# 폴더 압축
Compress-Archive -Path "dist\CMG-SeqViewer" -DestinationPath "CMG-SeqViewer_v1.2_Portable.zip"
```

**장점**:
- ✅ 즉시 실행 (압축 해제만)
- ✅ USB/네트워크 드라이브에서 실행 가능
- ✅ 여러 버전 동시 사용 가능
- ✅ 관리자 권한 불필요
- ✅ 완전 삭제 용이 (폴더 삭제)

**단점**:
- ❌ 바로가기 수동 생성
- ❌ 자동 업데이트 없음

**사용 시나리오**:
- 연구실 여러 컴퓨터에서 작업
- 빠른 테스트/프로토타입
- 다양한 버전 비교 필요

#### Option 2: 단일 파일 배포
```powershell
# 단일 EXE만 배포
Copy-Item "dist\CMG-SeqViewer.exe" -Destination "releases\"
```

**장점**: 단일 파일로 배포 간편  
**단점**: 첫 실행 시 압축 해제로 느림

### macOS 배포

#### Option 1: .app 번들 직접 배포
```bash
# .app 폴더 압축
cd dist
zip -r CMG-SeqViewer_macOS.zip CMG-SeqViewer.app
```

**장점**:
- ✅ 간단하고 빠름
- ✅ 파일 크기 작음

**단점**:
- ❌ Gatekeeper 경고 (서명 안됨)
- ❌ 전문성 부족

**사용자 설치 방법**:
```bash
# 압축 해제
unzip CMG-SeqViewer_macOS.zip

# Applications 폴더로 이동
mv CMG-SeqViewer.app /Applications/

# Gatekeeper 우회 (서명 안된 경우)
xattr -cr /Applications/CMG-SeqViewer.app
```

#### Option 2: DMG 이미지 생성 ⭐ 권장
```bash
# 기본 DMG 생성
hdiutil create -volname "CMG-SeqViewer" \
               -srcfolder dist/CMG-SeqViewer.app \
               -ov -format UDZO \
               CMG-SeqViewer.dmg

# 고급 DMG (create-dmg 도구 사용)
# https://github.com/create-dmg/create-dmg
brew install create-dmg

create-dmg \
  --volname "CMG-SeqViewer" \
  --volicon "cmg-seqviewer.icns" \
  --window-pos 200 120 \
  --window-size 800 400 \
  --icon-size 100 \
  --icon "CMG-SeqViewer.app" 200 190 \
  --hide-extension "CMG-SeqViewer.app" \
  --app-drop-link 600 185 \
  "CMG-SeqViewer.dmg" \
  "dist/"
```

**장점**:
- ✅ 전문적인 배포 방식
- ✅ Applications 폴더 바로가기 포함 가능
- ✅ 커스텀 배경/레이아웃
- ✅ macOS 표준 설치 방식

#### Option 3: PKG 설치 패키지
```bash
# pkgbuild 사용
pkgbuild --root dist/CMG-SeqViewer.app \
         --identifier com.yourorg.cmgseqviewer \
         --version 1.2.0 \
         --install-location /Applications/CMG-SeqViewer.app \
         CMG-SeqViewer.pkg
```

**장점**:
- ✅ 정식 설치 프로그램
- ✅ 자동 업데이트 가능

**단점**:
- ❌ 더 복잡한 제작 과정

---

## 설치 프로그램 생성

### Windows: Inno Setup Installer

#### 필요 도구
- **Inno Setup**: https://jrsoftware.org/isdl.php (무료)

#### 설치
```powershell
# Chocolatey 사용
choco install innosetup

# 또는 수동 다운로드 및 설치
```

#### Installer 빌드
```powershell
# installer.iss 파일 기반 빌드
iscc installer.iss

# 결과물: installer_output\CMG-SeqViewer_Setup_1.2.0.exe
```

#### installer.iss 파일 예제
```iss
[Setup]
AppName=CMG-SeqViewer
AppVersion=1.2.0
DefaultDirName={pf}\CMG-SeqViewer
DefaultGroupName=CMG-SeqViewer
UninstallDisplayIcon={app}\CMG-SeqViewer.exe
Compression=lzma2
SolidCompression=yes
OutputDir=installer_output
OutputBaseFilename=CMG-SeqViewer_Setup_1.2.0

[Files]
Source: "dist\CMG-SeqViewer\*"; DestDir: "{app}"; Flags: recursesubdirs

[Icons]
Name: "{group}\CMG-SeqViewer"; Filename: "{app}\CMG-SeqViewer.exe"
Name: "{commondesktop}\CMG-SeqViewer"; Filename: "{app}\CMG-SeqViewer.exe"

[Run]
Filename: "{app}\CMG-SeqViewer.exe"; Description: "Launch CMG-SeqViewer"; Flags: nowait postinstall skipifsilent
```

#### 테스트
```powershell
# 설치 테스트
.\installer_output\CMG-SeqViewer_Setup_1.2.0.exe

# 확인 사항:
# - C:\Program Files\CMG-SeqViewer\ 설치됨
# - 시작 메뉴에 등록
# - 바탕화면 바로가기 생성
# - 제어판 > 프로그램 추가/제거에 표시
```

### 대안: NSIS, Advanced Installer
- **NSIS**: https://nsis.sourceforge.io/ (무료, 스크립트 기반)
- **Advanced Installer**: https://www.advancedinstaller.com/ (GUI, 유료/무료)

---

## 코드 서명

### Windows 코드 서명

#### 필요한 것
- **코드 서명 인증서**: Comodo, Sectigo, DigiCert 등
- **비용**: 개인 $75-150/년, 조직 $200-400/년

#### 서명 방법
```powershell
# SignTool.exe 사용 (Windows SDK 포함)
# C:\Program Files (x86)\Windows Kits\10\bin\<version>\x64\signtool.exe

signtool sign /f certificate.pfx /p password /t http://timestamp.digicert.com dist\CMG-SeqViewer.exe

# 서명 확인
signtool verify /pa dist\CMG-SeqViewer.exe
```

#### EV (Extended Validation) 서명
- **비용**: $300-500/년
- **장점**: 즉시 SmartScreen 통과 (경고 없음)
- **필요**: USB 토큰 (물리적 보안)

### macOS 코드 서명

#### 필요한 것
- **Apple Developer Account**: $99/년
- **Developer ID Application Certificate**: Xcode에서 발급

#### 서명 방법
```bash
# 1. 서명 ID 확인
security find-identity -v -p codesigning

# 2. .app 번들 서명
codesign --deep --force --verify --verbose \
         --sign "Developer ID Application: Your Name (TEAMID)" \
         --options runtime \
         dist/CMG-SeqViewer.app

# 3. 서명 확인
codesign --verify --verbose dist/CMG-SeqViewer.app
spctl -a -t exec -vv dist/CMG-SeqViewer.app
```

#### Notarization (공증)
macOS 10.15+ 에서 Gatekeeper 통과하려면 공증 필요:

```bash
# 1. .app을 ZIP으로 압축
ditto -c -k --keepParent dist/CMG-SeqViewer.app CMG-SeqViewer.zip

# 2. 공증 요청
xcrun notarytool submit CMG-SeqViewer.zip \
  --apple-id your-email@example.com \
  --team-id TEAMID \
  --password app-specific-password \
  --wait

# 3. 공증 확인
xcrun notarytool info <submission-id> \
  --apple-id your-email@example.com \
  --team-id TEAMID \
  --password app-specific-password

# 4. Staple 첨부
xcrun stapler staple dist/CMG-SeqViewer.app
```

---

## 문제 해결

### Windows 문제

#### 1. 모듈을 찾을 수 없다는 오류
**증상**: `ModuleNotFoundError: No module named 'xxx'`

**해결**:
```python
# .spec 파일의 hiddenimports에 추가
hiddenimports=[
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'openpyxl',
    'scipy.special._cdflib',
    # 누락된 모듈 추가
],
```

#### 2. DLL 오류
**증상**: `The program can't start because xxx.dll is missing`

**해결**:
```powershell
# Microsoft Visual C++ Redistributable 설치
# https://aka.ms/vs/17/release/vc_redist.x64.exe
```

#### 3. 파일 크기가 너무 큼
**해결**:
```python
# .spec 파일에서 불필요한 패키지 제외
excludes=[
    'tkinter',
    'matplotlib.tests',
    'numpy.tests',
    'pandas.tests',
    'PIL',
    'PySide2',
    'PySide6',
],
```

#### 4. 백신 프로그램 경고
**원인**: 서명되지 않은 실행 파일

**해결**:
- 코드 서명 인증서 구매 및 서명
- 또는 백신 제외 목록에 추가
- Windows Defender: 설정 > 업데이트 및 보안 > Windows 보안 > 바이러스 및 위협 방지 > 설정 관리 > 제외 추가

#### 5. 실행이 너무 느림 (onefile)
**원인**: 첫 실행 시 임시 폴더에 압축 해제

**해결**:
```powershell
# onedir 방식 사용 (폴더 형태)
pyinstaller --onedir --windowed src/main.py
```

### macOS 문제

#### 1. Gatekeeper 경고
**증상**: "Cannot be opened because the developer cannot be verified"

**해결 (사용자)**:
```bash
# 1. System Preferences → Security & Privacy → General
# "Open Anyway" 클릭

# 2. 또는 터미널에서:
xattr -cr /Applications/CMG-SeqViewer.app
```

**해결 (개발자)**: 코드 서명 및 공증

#### 2. 라이브러리 경로 오류
**증상**: `dyld: Library not loaded`

**해결**:
```bash
# .spec 파일에 라이브러리 경로 추가
datas=[
    ('/path/to/library.dylib', 'Frameworks'),
],
```

#### 3. Python framework 오류
**해결**:
```bash
# Python을 framework 빌드로 재설치
# Homebrew Python 사용 권장
brew install python@3.10
```

### 공통 문제

#### 1. 데이터 파일을 찾을 수 없음
**원인**: 상대 경로 문제

**해결**:
```python
# main.py에서 올바른 경로 사용
import sys
import os

if getattr(sys, 'frozen', False):
    # PyInstaller 실행 파일
    base_path = sys._MEIPASS
else:
    # 일반 Python 실행
    base_path = os.path.dirname(__file__)

database_path = os.path.join(base_path, 'database')
```

#### 2. 환경 변수 문제
```python
# .spec 파일에서 환경 변수 설정
import os
os.environ['QT_QPA_PLATFORM'] = 'windows'  # Windows
# os.environ['QT_QPA_PLATFORM'] = 'cocoa'  # macOS
```

---

## 배포 체크리스트

### 빌드 전
- [ ] 모든 테스트 통과 확인
- [ ] 버전 번호 업데이트 (`__version__` in `main.py`)
- [ ] Pre-loaded datasets 준비 (`database/datasets/`)
- [ ] 아이콘 파일 준비 (선택사항)
- [ ] 의존성 최신화 (`pip list --outdated`)

### 빌드 중
- [ ] 가상환경 활성화 확인
- [ ] 빌드 스크립트 실행 또는 수동 빌드
- [ ] 빌드 오류 없음 확인
- [ ] 경고 메시지 검토 (`warn-rna-seq-viewer.txt`)

### 빌드 후
- [ ] 로컬에서 실행 테스트
- [ ] 다른 PC에서 테스트 (Python 없는 환경)
- [ ] 모든 기능 동작 확인
  - [ ] 데이터 로드
  - [ ] 필터링
  - [ ] 시각화
  - [ ] Export
  - [ ] Database Browser
  - [ ] External data folder (v1.2.0+)
- [ ] Pre-loaded datasets 표시 확인
- [ ] 로그 파일 생성 확인 (`logs/`)

### 배포 전
- [ ] 파일 압축 (ZIP 또는 DMG)
- [ ] Installer 생성 (선택사항)
- [ ] 코드 서명 (선택사항, 권장)
- [ ] README 파일 작성 (설치 방법, 시스템 요구사항)
- [ ] CHANGELOG 업데이트
- [ ] Git 태그 생성 (`v1.2.0`)

### 배포
- [ ] GitHub Releases에 업로드
- [ ] 릴리스 노트 작성
- [ ] 다운로드 링크 공유
- [ ] 사용자 문서 업데이트

---

## 추천 배포 전략

### Phase 1: 내부 테스트
- **Portable 버전만** 사용
- 빠른 반복 개발
- 연구실 내부 테스트

### Phase 2: 베타 릴리스
- **Portable + Installer** 제공
- 사용자 선택 가능
- 피드백 수집

### Phase 3: 정식 릴리스
- **Installer (권장) + Portable (고급)** 제공
- 디지털 서명 적용 (권장)
- 자동 업데이트 구현 (선택사항)

### CMG-SeqViewer의 경우
연구 도구 특성상 **Portable 방식이 더 적합**:

**이유**:
1. 연구자들은 유연성 필요 (여러 PC, USB, 서버)
2. 빠른 배포/업데이트 중요
3. 버전 간 비교 필요
4. 설치 권한 문제 없음

**Installer는 다음 경우에만 필요**:
- 대규모 조직 배포
- 비기술 사용자 대상
- 자동 업데이트 필수
- 전문적인 이미지 중요

---

## 참고 자료

- **PyInstaller 문서**: https://pyinstaller.org/
- **Inno Setup**: https://jrsoftware.org/
- **create-dmg**: https://github.com/create-dmg/create-dmg
- **Apple 코드 서명 가이드**: https://developer.apple.com/support/code-signing/
- **Windows 코드 서명**: https://docs.microsoft.com/en-us/windows/win32/seccrypto/cryptography-tools

---

## 다음 단계

빌드가 완료되었다면:
1. [사용자 가이드](../user/README.md) - 최종 사용자 문서 확인
2. [배포 가이드](./deployment.md) - 배포 프로세스 상세 정보
3. [CHANGELOG](../archive/CHANGELOG.md) - 버전별 변경사항 확인
