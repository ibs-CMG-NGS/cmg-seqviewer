# CMG-SeqViewer 배포 가이드 (Deployment Guide)

이 문서는 CMG-SeqViewer를 Windows 실행 파일(.exe)로 배포하는 방법을 설명합니다.

## 목차
1. [사전 요구사항](#사전-요구사항)
2. [PyInstaller를 이용한 빌드](#pyinstaller를-이용한-빌드)
3. [cx_Freeze를 이용한 빌드 (대안)](#cx_freeze를-이용한-빌드-대안)
4. [설치 프로그램 생성](#설치-프로그램-생성)
5. [문제 해결](#문제-해결)
6. [배포 체크리스트](#배포-체크리스트)

---

## 사전 요구사항

### 필수 소프트웨어
- **Python 3.8 이상** (3.10 권장)
- **Git** (소스코드 관리)
- **가상환경** (venv 또는 conda)

### 프로젝트 준비
```powershell
# 1. 저장소 클론 (이미 클론한 경우 생략)
git clone <repository-url>
cd rna-seq-data-view

# 2. 가상환경 생성 및 활성화
python -m venv venv
.\venv\Scripts\Activate.ps1

# 3. 의존성 설치
pip install -r requirements.txt
```

---

## PyInstaller를 이용한 빌드

### 1. PyInstaller 설치
```powershell
pip install pyinstaller
```

### 2. 애플리케이션 아이콘 준비 (선택사항)
- `.ico` 파일 준비 (256x256 픽셀 권장)
- 프로젝트 루트에 `icon.ico`로 저장
- 아이콘이 없으면 기본 Python 아이콘 사용

```powershell
# PNG에서 ICO 변환 (pillow 필요)
pip install pillow
python -c "from PIL import Image; img = Image.open('logo.png'); img.save('icon.ico')"
```

### 3. spec 파일 생성 및 수정

#### 기본 spec 파일 생성:
```powershell
pyi-makespec --onefile --windowed --name="CMG-SeqViewer" main.py
```

#### CMG-SeqViewer.spec 파일 수정:
```python
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        # 필요한 데이터 파일 추가
        ('src', 'src'),  # src 폴더 전체 포함
        # 샘플 데이터가 있다면:
        # ('data', 'data'),
    ],
    hiddenimports=[
        'PyQt6',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'pandas',
        'numpy',
        'openpyxl',  # Excel 파일 지원
        'matplotlib',
        'scipy',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',  # 사용하지 않는 패키지 제외
        'PIL',
        'PySide2',
        'PySide6',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='CMG-SeqViewer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # 압축 (선택사항, 파일 크기 줄임)
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 콘솔 창 숨김 (GUI 앱)
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico',  # 아이콘 파일 경로
)
```

### 4. 빌드 실행
```powershell
# spec 파일 기반 빌드
pyinstaller CMG-SeqViewer.spec --clean

# 빌드 완료 후 실행 파일 위치:
# dist\CMG-SeqViewer.exe
```

### 5. 빌드 테스트
```powershell
# 실행 파일 테스트
.\dist\CMG-SeqViewer.exe

# 다른 PC에서도 테스트 권장 (Python이 설치되지 않은 환경)
```

### 빌드 옵션 설명

#### 단일 파일 vs 폴더 배포
```powershell
# 단일 exe 파일 (권장)
pyinstaller --onefile --windowed main.py

# 폴더 형태 (더 빠른 실행 속도)
pyinstaller --onedir --windowed main.py
```

| 옵션 | 장점 | 단점 |
|------|------|------|
| `--onefile` | 배포 간편 (단일 파일) | 첫 실행 시 압축 해제로 느림 |
| `--onedir` | 빠른 실행 속도 | 여러 파일 관리 필요 |

---

## cx_Freeze를 이용한 빌드 (대안)

PyInstaller 대신 cx_Freeze를 사용할 수도 있습니다.

### 1. cx_Freeze 설치
```powershell
pip install cx_Freeze
```

### 2. setup.py 파일 생성
```python
# setup.py
import sys
from cx_Freeze import setup, Executable

# 의존성 패키지
build_exe_options = {
    "packages": [
        "PyQt6",
        "pandas",
        "numpy",
        "openpyxl",
        "matplotlib",
        "scipy",
    ],
    "include_files": [
        ("src", "src"),  # src 폴더 포함
    ],
    "excludes": ["tkinter", "PIL"],
}

# GUI 앱 설정
base = None
if sys.platform == "win32":
    base = "Win32GUI"  # 콘솔 창 숨김

setup(
    name="CMG-SeqViewer",
    version="1.0.0",
    description="RNA-Seq Data Analysis and Visualization Tool",
    options={"build_exe": build_exe_options},
    executables=[
        Executable(
            "main.py",
            base=base,
            target_name="CMG-SeqViewer.exe",
            icon="icon.ico",  # 아이콘 (선택사항)
        )
    ],
)
```

### 3. 빌드 실행
```powershell
python setup.py build

# 빌드 결과: build\exe.win-amd64-3.10\ 폴더
```

---

## 설치 프로그램 생성

단일 exe 파일도 좋지만, 전문적인 설치 프로그램을 만들면 더욱 좋습니다.

### Inno Setup 사용 (무료, 오픈소스)

#### 1. Inno Setup 설치
- [Inno Setup 다운로드](https://jrsoftware.org/isdl.php)
- 최신 버전 설치 (Inno Setup 6.x)

#### 2. installer.iss 파일 생성
```ini
; CMG-SeqViewer Installer Script

#define MyAppName "CMG-SeqViewer"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Your Organization"
#define MyAppURL "https://yourwebsite.com"
#define MyAppExeName "CMG-SeqViewer.exe"

[Setup]
; 기본 설정
AppId={{UNIQUE-GUID-HERE}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
; 라이센스 파일 (있는 경우)
; LicenseFile=LICENSE.txt
; README 파일 (있는 경우)
; InfoBeforeFile=README.txt
OutputDir=installer
OutputBaseFilename=CMG-SeqViewer-Setup-{#MyAppVersion}
SetupIconFile=icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
; 64비트 설치
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; PyInstaller --onefile 결과물
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
; 또는 --onedir 결과물 전체
; Source: "dist\CMG-SeqViewer\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; 문서 파일
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "DEPLOYMENT.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Name: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
```

#### 3. 고유 GUID 생성
```powershell
# PowerShell에서 GUID 생성
[guid]::NewGuid().ToString()
```
생성된 GUID를 `AppId` 줄에 붙여넣기

#### 4. 설치 프로그램 빌드
1. Inno Setup Compiler 실행
2. `File > Open` → `installer.iss` 선택
3. `Build > Compile` (또는 F9)
4. 결과물: `installer\CMG-SeqViewer-Setup-1.0.0.exe`

---

## 문제 해결

### 일반적인 문제

#### 1. "ModuleNotFoundError" 발생
```powershell
# spec 파일의 hiddenimports에 누락된 모듈 추가
hiddenimports=[
    'PyQt6.sip',
    'openpyxl.cell._writer',
    # 에러 메시지에 나온 모듈 추가
],
```

#### 2. 실행 시 "DLL load failed" 에러
```powershell
# Visual C++ Redistributable 필요
# 다운로드: https://aka.ms/vs/17/release/vc_redist.x64.exe
# 또는 installer.iss에 포함:

[Files]
Source: "vc_redist.x64.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall

[Run]
Filename: "{tmp}\vc_redist.x64.exe"; Parameters: "/quiet /norestart"; StatusMsg: "Installing Visual C++ Redistributable..."; Flags: skipifdoesntexist
```

#### 3. 파일 크기가 너무 큼
```python
# spec 파일 최적화
excludes=[
    'tkinter',
    'PIL',
    'PySide2',
    'PySide6',
    'test',
    'unittest',
    'distutils',
],

# UPX 압축 활성화
upx=True,
```

#### 4. 데이터 파일이 포함되지 않음
```python
# spec 파일의 datas 섹션 확인
datas=[
    ('src', 'src'),
    ('resources', 'resources'),  # 리소스 파일 있는 경우
],
```

#### 5. 한글 경로 문제
```python
# main.py 시작 부분에 추가
import sys
import os

# 실행 파일의 경로 설정
if getattr(sys, 'frozen', False):
    application_path = sys._MEIPASS
else:
    application_path = os.path.dirname(os.path.abspath(__file__))

os.chdir(application_path)
```

---

## 배포 체크리스트

### 빌드 전 확인사항
- [ ] 모든 기능이 정상 작동하는지 테스트
- [ ] requirements.txt가 최신 상태인지 확인
- [ ] 버전 번호 업데이트 (setup.py, installer.iss)
- [ ] 아이콘 파일 준비 (256x256 .ico)
- [ ] README.md 최신화
- [ ] 라이센스 파일 확인

### 빌드 후 테스트
- [ ] exe 파일 단독 실행 테스트
- [ ] Python이 설치되지 않은 PC에서 테스트
- [ ] 샘플 데이터 로드 테스트
- [ ] 모든 메뉴/기능 동작 확인
- [ ] 필터링 기능 테스트 (up/down/both)
- [ ] Export 기능 테스트
- [ ] 에러 로그 확인

### 설치 프로그램 테스트
- [ ] 설치 과정이 정상적인지 확인
- [ ] 바탕화면 바로가기 생성 확인
- [ ] 시작 메뉴 등록 확인
- [ ] 제거 프로그램에서 삭제 테스트
- [ ] 재설치 테스트

### 배포 준비
- [ ] 릴리스 노트 작성
- [ ] 사용자 매뉴얼 준비
- [ ] 설치 가이드 작성
- [ ] 최종 배포 파일 백업
- [ ] GitHub Release 또는 배포 사이트 업로드

---

## 추가 참고사항

### 자동화 스크립트
배포 과정을 자동화하려면 다음 PowerShell 스크립트를 사용할 수 있습니다:

```powershell
# build-release.ps1
param(
    [string]$Version = "1.0.0"
)

Write-Host "CMG-SeqViewer Build Script v$Version" -ForegroundColor Green

# 1. 이전 빌드 정리
Write-Host "Cleaning previous builds..." -ForegroundColor Yellow
if (Test-Path "build") { Remove-Item -Recurse -Force build }
if (Test-Path "dist") { Remove-Item -Recurse -Force dist }

# 2. PyInstaller 빌드
Write-Host "Building with PyInstaller..." -ForegroundColor Yellow
pyinstaller CMG-SeqViewer.spec --clean
if ($LASTEXITCODE -ne 0) {
    Write-Host "Build failed!" -ForegroundColor Red
    exit 1
}

# 3. 실행 파일 테스트
Write-Host "Testing executable..." -ForegroundColor Yellow
Start-Process "dist\CMG-SeqViewer.exe" -Wait

# 4. Inno Setup 빌드 (설치 프로그램)
Write-Host "Creating installer..." -ForegroundColor Yellow
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installer creation failed!" -ForegroundColor Red
    exit 1
}

Write-Host "Build completed successfully!" -ForegroundColor Green
Write-Host "Executable: dist\CMG-SeqViewer.exe"
Write-Host "Installer: installer\CMG-SeqViewer-Setup-$Version.exe"
```

사용법:
```powershell
.\build-release.ps1 -Version "1.0.0"
```

### 디버그 모드 빌드
문제 발생 시 디버그 정보를 얻으려면:
```powershell
# 콘솔 창 표시 (에러 메시지 확인용)
pyinstaller --onefile --console main.py

# 또는 spec 파일에서:
console=True,  # False → True로 변경
```

---

## 요약

1. **PyInstaller 권장**: PyQt6와 가장 호환성이 좋음
2. **단일 파일 배포**: `--onefile` 옵션 사용 (배포 편의성)
3. **Inno Setup**: 전문적인 설치 프로그램 생성
4. **철저한 테스트**: 다양한 환경에서 테스트 필수
5. **자동화**: 스크립트로 빌드 과정 자동화

---

**문의사항이나 문제가 발생하면 GitHub Issues에 등록해주세요.**
