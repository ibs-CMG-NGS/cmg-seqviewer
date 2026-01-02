# CMG-SeqViewer - Build Instructions

## 빌드 방법 (Building Executable)

### 준비사항
1. Python 3.9 이상
2. 모든 의존성 패키지 설치
3. PyInstaller 설치

### 방법 1: 자동 빌드 (권장)

PowerShell에서 실행:
```powershell
.\build.ps1
```

### 방법 2: 수동 빌드

#### 폴더 형태 EXE (빠른 실행, 여러 파일)
```powershell
pyinstaller --clean --noconfirm rna-seq-viewer.spec
```

출력 위치: `dist\CMG-SeqViewer\CMG-SeqViewer.exe`

#### 단일 파일 EXE (느린 실행, 하나의 파일)
```powershell
pyinstaller --clean --noconfirm rna-seq-viewer-onefile.spec
```

출력 위치: `dist\CMG-SeqViewer.exe`

### 방법 3: 명령줄로 직접 빌드

```powershell
# 폴더 형태
pyinstaller --name="CMG-SeqViewer" --windowed --onedir src/main.py

# 단일 파일
pyinstaller --name="CMG-SeqViewer" --windowed --onefile src/main.py
```

## 빌드 옵션 설명

- `--windowed` (또는 `--noconsole`): 콘솔 창을 숨김 (GUI 전용)
- `--onedir`: 폴더 형태로 생성 (실행 속도 빠름, 여러 파일)
- `--onefile`: 단일 실행 파일 생성 (배포 편리, 실행 속도 느림)
- `--clean`: 이전 빌드 캐시 삭제
- `--noconfirm`: 확인 없이 덮어쓰기
- `--icon=icon.ico`: 아이콘 지정 (선택사항)

## 문제 해결

### 1. 모듈을 찾을 수 없다는 오류
`.spec` 파일의 `hiddenimports`에 누락된 모듈 추가:
```python
hiddenimports=[
    'your_missing_module',
]
```

### 2. 실행 시 DLL 오류
Windows Redistributable 설치 필요:
- [Microsoft Visual C++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe)

### 3. 파일 크기가 너무 큼
불필요한 패키지 제외:
```python
excludes=[
    'tkinter',
    'matplotlib.tests',
    'numpy.tests',
    'pandas.tests',
]
```

### 4. 실행이 너무 느림 (onefile)
`--onedir` 옵션 사용 (폴더 형태) 권장

## 배포

### 폴더 형태 배포
`dist\CMG-SeqViewer` 폴더 전체를 압축하여 배포
- **포함 내용**: 
  - CMG-SeqViewer.exe (메인 실행 파일)
  - 라이브러리 파일들 (DLL 등)
  - database/ (Pre-loaded datasets) ✅

### 단일 파일 배포
`dist\CMG-SeqViewer.exe` 파일만 배포
- **주의**: onefile 버전도 database 폴더가 내장되어 있지만, 첫 실행 시 임시 폴더에 압축 해제됨

## Pre-loaded Datasets 관리

### 배포 전 데이터셋 준비
빌드하기 전에 `database/` 폴더에 원하는 데이터셋을 추가하세요:
```powershell
# 프로그램 실행 후 Database Browser에서 데이터셋 import
# 또는 직접 database/datasets/ 폴더에 .parquet 파일 추가
```

### 배포판에 포함되는 파일
- `database/metadata.json` - 데이터셋 메타데이터
- `database/datasets/*.parquet` - Parquet 형식의 데이터셋 파일들

### 사용자 데이터 추가
배포 후 사용자는 프로그램에서 추가 데이터셋을 import 가능:
- File → Database Browser → Import Dataset
- 사용자가 추가한 데이터는 사용자의 로컬 database 폴더에 저장됨

## 참고
- PyInstaller 공식 문서: https://pyinstaller.org/
- 첫 실행 시 백신 소프트웨어가 경고할 수 있음 (정상)
- Windows Defender에서 제외 목록에 추가 권장
