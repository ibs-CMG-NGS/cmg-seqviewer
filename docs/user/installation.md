# CMG-SeqViewer 설치 가이드 (Installation Guide)

> **목적**: CMG-SeqViewer를 Windows와 macOS에 설치하고 실행하는 방법을 설명합니다.

## 목차
1. [시스템 요구사항](#시스템-요구사항)
2. [설치 방법](#설치-방법)
3. [첫 실행](#첫-실행)
4. [Python 개발 환경 설정](#python-개발-환경-설정-선택사항)
5. [문제 해결](#문제-해결)

---

## 시스템 요구사항

### Windows

| 항목 | 최소 요구사항 | 권장 사양 |
|------|--------------|----------|
| **OS** | Windows 10 (64-bit) | Windows 11 |
| **메모리** | 4GB RAM | 8GB RAM 이상 |
| **디스플레이** | 1280x720 | 1920x1080 |
| **저장공간** | 500MB | 1GB 이상 |
| **추가 요구사항** | Microsoft Visual C++ Redistributable | - |

### macOS

| 항목 | 최소 요구사항 | 권장 사양 |
|------|--------------|----------|
| **OS** | macOS 13.0 Ventura | macOS 14.0 Sonoma 이상 |
| **CPU** | Intel x86_64 또는 Apple Silicon (M1/M2/M3) | Apple Silicon |
| **메모리** | 4GB RAM | 8GB RAM 이상 |
| **디스플레이** | 1280x720 | 1920x1080 |
| **저장공간** | 500MB | 1GB 이상 |

> ⚠️ **macOS 참고**: PyQt6는 macOS 13.0+ 필요. 구버전 macOS는 소스 빌드 필요 (PyQt5 사용).

---

## 설치 방법

### Option 1: 실행 파일 다운로드 (권장) ⭐

최종 사용자에게 가장 간편한 방법입니다. Python 설치 불필요!

#### Windows 설치

**1단계: 다운로드**
- [GitHub Releases](https://github.com/ibs-CMG-NGS/cmg-seqviewer/releases)에서 최신 릴리스 선택
- `CMG-SeqViewer-Windows-Portable.zip` 다운로드

**2단계: 압축 해제**
```powershell
# 다운로드 폴더에서 압축 해제
# 또는 탐색기에서 우클릭 → "압축 풀기"

# 예: C:\Tools\CMG-SeqViewer\ 로 압축 해제
```

**3단계: 실행**
```powershell
# 압축 해제한 폴더로 이동
cd C:\Tools\CMG-SeqViewer

# 실행 파일 실행
.\CMG-SeqViewer.exe
```

**바로가기 만들기** (선택사항):
1. `CMG-SeqViewer.exe` 우클릭 → "바로가기 만들기"
2. 바로가기를 바탕화면으로 이동
3. 이제 바탕화면에서 바로 실행 가능!

#### macOS 설치

**1단계: 다운로드**
- [GitHub Releases](https://github.com/ibs-CMG-NGS/cmg-seqviewer/releases)에서 최신 릴리스 선택
- `CMG-SeqViewer-macOS.dmg` 다운로드

**2단계: 설치**
```bash
# DMG 파일 더블클릭하여 마운트
# 또는 터미널에서:
open CMG-SeqViewer-macOS.dmg

# CMG-SeqViewer.app을 Applications 폴더로 드래그
```

**3단계: Gatekeeper 우회** (서명되지 않은 앱)
```bash
# 방법 1: 우클릭으로 열기 (가장 쉬움)
# 1. CMG-SeqViewer.app 우클릭 (또는 Control+클릭)
# 2. "열기" 선택
# 3. "열기" 확인 (최초 1회만)

# 방법 2: 터미널 명령어
xattr -cr /Applications/CMG-SeqViewer.app
```

**4단계: 실행**
```bash
# Finder에서 더블클릭
# 또는 터미널에서:
open /Applications/CMG-SeqViewer.app
```

---

### Option 2: Python에서 실행 (개발자용)

Python 환경에서 직접 실행하거나 개발하려면 이 방법을 사용하세요.

#### 사전 요구사항
- **Python 3.9 이상** (3.10+ 권장)
- **pip** (Python 패키지 매니저)
- **Git** (소스 코드 다운로드용)

> Python이 설치되어 있지 않다면? → [Python 설치 가이드](#python-설치)

#### Windows

```powershell
# 1. 저장소 클론
git clone https://github.com/ibs-CMG-NGS/cmg-seqviewer.git
cd cmg-seqviewer

# 2. 가상환경 생성 및 활성화
python -m venv venv
.\venv\Scripts\Activate.ps1

# PowerShell 실행 정책 오류 시:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 3. 패키지 설치
pip install -r requirements.txt

# 4. 실행
python src\main.py
```

#### macOS/Linux

```bash
# 1. 저장소 클론
git clone https://github.com/ibs-CMG-NGS/cmg-seqviewer.git
cd cmg-seqviewer

# 2. 가상환경 생성 및 활성화
python3 -m venv venv
source venv/bin/activate

# 3. 패키지 설치
pip install -r requirements.txt

# 4. 실행
python src/main.py
```

---

## 첫 실행

### Windows 첫 실행

#### 백신 경고 (Windows Defender)

**증상**: "Windows의 PC 보호" 경고 표시

**원인**: 서명되지 않은 실행 파일

**해결**:
1. "추가 정보" 클릭
2. "실행" 버튼 클릭
3. 프로그램 실행됨

> 안전합니다! 오픈소스 코드로 직접 확인 가능합니다.

#### Visual C++ Redistributable 오류

**증상**: "VCRUNTIME140.dll을 찾을 수 없습니다"

**해결**:
1. [Microsoft Visual C++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe) 다운로드
2. 설치
3. PC 재시작
4. CMG-SeqViewer 다시 실행

### macOS 첫 실행

#### Gatekeeper 경고

**증상**: "열 수 없습니다. 개발자를 확인할 수 없습니다"

**해결 방법 1: 우클릭으로 열기** (⭐ 권장):
1. `CMG-SeqViewer.app` 우클릭 (또는 Control+클릭)
2. "열기" 선택
3. "열기" 버튼 클릭
4. 이후부터는 일반적으로 더블클릭으로 실행 가능

**해결 방법 2: 시스템 환경설정**:
1. 더블클릭 시도 (경고 발생)
2. 시스템 환경설정 → 보안 및 개인 정보 보호 → 일반
3. "확인 없이 열기" 버튼 클릭
4. 확인

**해결 방법 3: 터미널 명령어**:
```bash
# quarantine 속성 제거
xattr -cr /Applications/CMG-SeqViewer.app

# 확인
xattr -l /Applications/CMG-SeqViewer.app
# 출력 없으면 성공
```

#### 앱이 응답하지 않음

**증상**: 더블클릭 시 아무 반응 없음

**해결**:

**1. 콘솔에서 오류 확인**:
```bash
# 터미널에서 직접 실행
/Applications/CMG-SeqViewer.app/Contents/MacOS/CMG-SeqViewer

# 오류 메시지 확인
```

**2. 실행 권한 확인**:
```bash
# 실행 권한 확인
ls -l /Applications/CMG-SeqViewer.app/Contents/MacOS/CMG-SeqViewer

# -rwxr-xr-x 형태여야 함
# x가 없으면 권한 추가:
chmod +x /Applications/CMG-SeqViewer.app/Contents/MacOS/CMG-SeqViewer
```

**3. quarantine 제거**:
```bash
xattr -cr /Applications/CMG-SeqViewer.app
```

### 첫 실행 후 확인사항

프로그램이 정상적으로 실행되면:

1. **메인 윈도우 확인**:
   - 상단: 메뉴바 (File, Edit, View, Analysis, Help)
   - 왼쪽: Filter Panel (필터 설정)
   - 중앙: 탭 인터페이스 (데이터 표시)
   - 하단: Log Terminal (활동 로그)

2. **Help 메뉴 확인**:
   - `Help` → `Documentation` (F1) 클릭
   - 도움말 다이얼로그 표시 확인

3. **샘플 데이터 로드** (선택사항):
   - `File` → `Import Dataset` 선택
   - Excel 파일 선택 (.xlsx, .xls)
   - 데이터가 탭에 표시되는지 확인

---

## Python 개발 환경 설정 (선택사항)

소스 코드를 수정하거나 개발에 참여하려면 Python 개발 환경이 필요합니다.

### Python 설치

#### Windows

**방법 1: 공식 웹사이트** (⭐ 권장):
1. https://www.python.org/downloads/ 방문
2. Python 3.10 이상 다운로드
3. 설치 시 **"Add Python to PATH"** 반드시 체크!
4. 설치 완료 후 확인:
   ```powershell
   python --version
   # Python 3.10.x 출력되어야 함
   ```

**방법 2: Microsoft Store**:
1. Microsoft Store 열기
2. "Python 3.11" 검색
3. 설치 버튼 클릭
4. 자동으로 PATH 설정됨

**방법 3: Chocolatey**:
```powershell
# Chocolatey 설치 (한 번만)
Set-ExecutionPolicy Bypass -Scope Process -Force
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# Python 설치
choco install python -y

# 터미널 재시작 후 확인
python --version
```

#### macOS

**방법 1: Homebrew** (⭐ 권장):
```bash
# Homebrew 설치 (한 번만)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Python 설치
brew install python@3.10

# 확인
python3 --version
```

**방법 2: 공식 웹사이트**:
1. https://www.python.org/downloads/ 방문
2. macOS용 Python 3.10 이상 다운로드
3. 설치 프로그램 실행
4. 확인:
   ```bash
   python3 --version
   ```

### 개발 모드 설치

```powershell
# Windows
cd path\to\cmg-seqviewer
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -e ".[dev]"

# macOS/Linux
cd path/to/cmg-seqviewer
python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
```

**개발 모드 장점**:
- ✅ 코드 수정 후 재설치 불필요
- ✅ 빠른 개발-테스트 사이클
- ✅ 디버깅 용이

자세한 내용: [개발자 가이드](../developer/setup.md)

---

## 문제 해결

### Windows 문제

#### "python을 찾을 수 없습니다"

**원인**: Python이 설치되지 않았거나 PATH에 없음

**해결**:
```powershell
# Python 설치 여부 확인
py --version           # Windows Python Launcher
python --version       # 일반 python 명령어

# 위 명령어 모두 실패 시 Python 설치 필요
# → Python 설치 섹션 참고
```

#### PowerShell 실행 정책 오류

**증상**: `venv\Scripts\activate` 실행 시 오류

**해결**:
```powershell
# 실행 정책 변경 (한 번만)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 다시 시도
.\venv\Scripts\Activate.ps1
```

#### 가상환경 활성화 안됨

**해결**:
```powershell
# 가상환경 Python 직접 사용
.\venv\Scripts\python.exe src\main.py

# 또는 가상환경 재생성
Remove-Item -Recurse -Force venv
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

#### DLL 오류 (VCRUNTIME140.dll)

**해결**:
1. [Microsoft Visual C++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe) 다운로드
2. 설치
3. PC 재시작

### macOS 문제

#### "손상되어 열 수 없습니다"

**원인**: Gatekeeper 차단

**해결**:
```bash
# quarantine 제거
xattr -cr /Applications/CMG-SeqViewer.app

# Gatekeeper 임시 비활성화 (신중히 사용)
sudo spctl --master-disable
# 앱 실행 후:
sudo spctl --master-enable
```

#### "Library not loaded" 오류

**원인**: PyInstaller가 일부 라이브러리 누락

**해결**:
```bash
# 소스에서 실행
git clone https://github.com/ibs-CMG-NGS/cmg-seqviewer.git
cd cmg-seqviewer
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python src/main.py
```

#### Python3 설치되어 있지만 명령어 안됨

**해결**:
```bash
# Homebrew Python 사용
brew install python@3.10

# PATH 확인
which python3
# /usr/local/bin/python3 또는 /opt/homebrew/bin/python3

# .zshrc 또는 .bash_profile에 추가
export PATH="/opt/homebrew/bin:$PATH"
source ~/.zshrc
```

### 공통 문제

#### 데이터가 로드되지 않음

**증상**: Excel 파일 선택했는데 데이터 표시 안됨

**해결**:
1. 로그 확인 (하단 Log Terminal)
2. Excel 파일 형식 확인 (.xlsx, .xls만 지원)
3. 파일 권한 확인 (읽기 권한 있어야 함)
4. 파일 경로에 한글 있으면 영문 경로로 이동

#### 프로그램이 느림

**원인**: 큰 데이터셋 (10만 행 이상)

**해결**:
1. 필터링 먼저 적용 (adj.p-value < 0.05)
2. 데이터를 여러 파일로 분할
3. 메모리 부족 시 RAM 증설 고려

#### 시각화 창이 안 열림

**해결**:
1. matplotlib 백엔드 확인
2. 로그에서 오류 메시지 확인
3. 프로그램 재시작
4. 문제 지속 시 GitHub Issue 생성

---

## 추가 도움말

### 사용자 가이드
- [빠른 시작 가이드](./quick-start.md) - 5분 만에 시작하기
- [사용자 매뉴얼](./user-guide.md) - 전체 기능 설명
- [컬럼 매핑 가이드](./column-mapping.md) - 데이터 임포트 가이드

### 개발자 가이드
- [개발 환경 설정](../developer/setup.md) - 개발 환경 구축
- [프로젝트 구조](../developer/architecture.md) - 코드 구조 이해
- [기여 가이드](../developer/contributing.md) - Pull Request 작성

### 배포 가이드
- [빌드 가이드](../deployment/build-guide.md) - 실행 파일 빌드
- [배포 가이드](../deployment/deployment.md) - GitHub Release 생성

### 기타
- [FAQ](./faq.md) - 자주 묻는 질문
- [CHANGELOG](../archive/CHANGELOG.md) - 버전별 변경사항
- [GitHub Issues](https://github.com/ibs-CMG-NGS/cmg-seqviewer/issues) - 버그 리포트 및 기능 요청

---

## 지원

문제가 해결되지 않으면:

1. **로그 파일 확인**: `logs/` 폴더의 최신 로그 파일
2. **GitHub Issues**: https://github.com/ibs-CMG-NGS/cmg-seqviewer/issues
   - 검색하여 동일한 문제 있는지 확인
   - 없으면 새 Issue 생성 (로그 첨부)
3. **이메일 문의**: (조직 내부 연락처)

---

## 라이선스

CMG-SeqViewer는 MIT 라이선스로 배포됩니다.

자세한 내용: [LICENSE](../../LICENSE)
