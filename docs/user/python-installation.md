# Python 설치 및 환경 설정 문제 해결

## ❌ 문제: "Python was not found"

### 원인
1. Python이 설치되지 않았거나
2. Python이 시스템 PATH에 등록되지 않음
3. 잘못된 Python 경로 사용

---

## ✅ 해결 방법

### 방법 1: Python이 설치되어 있는지 확인

```powershell
# Python 버전 확인 (여러 방법 시도)
python --version
python3 --version
py --version           # Windows Python Launcher
py -3 --version        # Python 3 지정
```

위 명령어 중 **하나라도 작동하면** Python이 설치되어 있는 것입니다.

---

### 방법 2: Python Launcher 사용 (Windows 권장) ⭐

Windows에는 `py` 명령어가 내장되어 있습니다:

```powershell
# py 명령어로 가상환경 생성
py -m venv venv

# 가상환경 활성화
venv\Scripts\activate

# 개발 모드 설치
pip install -e ".[dev]"
```

**이 방법이 가장 간단합니다!**

---

### 방법 3: Python 설치 경로 직접 지정

Python이 설치되어 있지만 PATH에 없는 경우:

```powershell
# Python 설치 경로 찾기
where.exe python
# 또는
Get-Command python -ErrorAction SilentlyContinue

# 일반적인 설치 경로들:
# C:\Python39\python.exe
# C:\Python310\python.exe
# C:\Users\USER\AppData\Local\Programs\Python\Python39\python.exe
# C:\Program Files\Python39\python.exe

# 직접 경로 지정하여 가상환경 생성
C:\Python39\python.exe -m venv venv
# 또는 본인의 Python 경로 사용
```

---

### 방법 4: Python 새로 설치 (설치되지 않은 경우)

#### A. 공식 웹사이트에서 다운로드 (권장)

1. **다운로드**: https://www.python.org/downloads/
2. **버전 선택**: Python 3.9 이상 (3.11 권장)
3. **설치 시 중요!** ⭐
   - ✅ **"Add Python to PATH"** 체크박스 **반드시 선택**
   - ✅ "Install for all users" (선택사항)
   - ✅ "Install pip" (기본 선택됨)

4. **설치 확인**:
   ```powershell
   python --version
   # 또는
   py --version
   ```

#### B. Microsoft Store에서 설치 (간편)

1. Microsoft Store 열기
2. "Python 3.11" 검색
3. 설치 버튼 클릭
4. 설치 후 확인:
   ```powershell
   python --version
   ```

#### C. Chocolatey 패키지 매니저 사용

```powershell
# Chocolatey 설치 (한 번만)
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# Python 설치
choco install python -y

# 터미널 재시작 후 확인
python --version
```

---

## 🔧 PATH 설정 (수동)

Python이 설치되어 있지만 PATH에 없는 경우:

### 임시 설정 (현재 세션만)
```powershell
# Python 설치 경로를 찾아서
$env:Path += ";C:\Python39;C:\Python39\Scripts"
python --version
```

### 영구 설정 (권장)

1. **시스템 환경 변수 열기**:
   ```powershell
   # GUI로 열기
   rundll32 sysdm.cpl,EditEnvironmentVariables
   ```

2. **사용자 변수** 섹션에서 `Path` 선택 → **편집**

3. **새로 만들기** 클릭하고 Python 경로 추가:
   ```
   C:\Python39
   C:\Python39\Scripts
   ```
   (본인의 Python 설치 경로로 변경)

4. **확인** → **확인** → **PowerShell 재시작**

5. 확인:
   ```powershell
   python --version
   ```

---

## 🎯 추천 설치 방법 (단계별)

### 1단계: Python 설치
```powershell
# Microsoft Store에서 설치 (가장 간단)
# 또는 https://www.python.org 에서 다운로드
```

### 2단계: 설치 확인
```powershell
# 어떤 명령어든 작동하면 OK
python --version
py --version
python3 --version
```

### 3단계: 가상환경 생성
```powershell
# 작동하는 명령어 사용
py -m venv venv
# 또는
python -m venv venv
```

### 4단계: 활성화 및 설치
```powershell
venv\Scripts\activate
pip install -e ".[dev]"
```

---

## 📋 설치 후 체크리스트

```powershell
# ✅ 1. Python 설치 확인
py --version
# 출력 예: Python 3.11.5

# ✅ 2. pip 확인
py -m pip --version
# 출력 예: pip 23.3.1

# ✅ 3. 가상환경 생성
py -m venv venv

# ✅ 4. 가상환경 활성화
venv\Scripts\activate
# 프롬프트에 (venv) 표시되면 성공!

# ✅ 5. pip 업그레이드
python -m pip install --upgrade pip

# ✅ 6. 개발 모드 설치
pip install -e ".[dev]"

# ✅ 7. 실행!
.\run_dev.ps1
```

---

## 🚨 자주 발생하는 오류

### 오류 1: "python was not found"
**해결**: `py` 명령어 사용
```powershell
py -m venv venv
```

### 오류 2: "'venv' is not recognized"
**해결**: Python 재설치 시 "Add to PATH" 체크

### 오류 3: "Access is denied"
**해결**: 관리자 권한으로 PowerShell 실행
```powershell
# PowerShell을 관리자 권한으로 실행
Start-Process powershell -Verb runAs
```

### 오류 4: "Execution policy" 오류
**해결**:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

## 💡 빠른 해결 (요약)

대부분의 경우 이것으로 해결됩니다:

```powershell
# 1. py 명령어 사용 (Windows)
py -m venv venv

# 2. 가상환경 활성화
venv\Scripts\activate

# 3. 개발 모드 설치
pip install -e ".[dev]"

# 4. 실행
.\run_dev.ps1
```

**py 명령어도 안 되면** → Python 설치 필요:
- https://www.python.org/downloads/
- "Add Python to PATH" 체크 필수!

---

## 📞 추가 도움말

설치 후에도 문제가 계속되면:

1. **터미널 재시작** (중요!)
2. **컴퓨터 재부팅**
3. Python 완전 제거 후 재설치

---

## 🎉 설치 성공 후

```powershell
# 이제 다음 명령어로 개발 시작!
py -m venv venv
venv\Scripts\activate
pip install -e ".[dev]"
.\run_dev.ps1
```

**Good luck!** 🚀
