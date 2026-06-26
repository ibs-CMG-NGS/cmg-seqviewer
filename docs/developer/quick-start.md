# Quick Start Guide - 개발 환경 설정

## 🚀 5분 만에 개발 환경 설정하기

### Step 1: 가상환경 생성 및 활성화
```powershell
# 프로젝트 디렉토리로 이동
cd c:\Users\USER\Documents\GitHub\rna-seq-data-view

# 가상환경 생성
python -m venv venv

# 가상환경 활성화
venv\Scripts\activate
```

> ⚠️ **PowerShell 실행 정책 오류 시**  
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```
> 실행 후 다시 `venv\Scripts\activate`

### Step 2: 개발 모드로 설치 ⭐
```powershell
# editable install (코드 수정 시 재설치 불필요!)
pip install -e .

# 또는 개발 도구 포함
pip install -e ".[dev]"
```

**설치 완료까지**: 약 1-2분 소요 (인터넷 속도에 따라 다름)

### Step 3: 실행!
```powershell
# 방법 1: 가상환경 Python 명시적 실행 (가장 안전함! ⭐)
.\venv\Scripts\python.exe src\main.py

# 방법 2: 일반 실행 (가상환경 활성화 시)
python src\main.py

# 방법 3: 개발 스크립트 사용 (권장)
.\run_dev.ps1

# 방법 4: VS Code에서 F5
# (VS Code를 열고 F5 키를 누르세요)
```

> 💡 **Tip**: 가상환경이 제대로 인식 안 될 때는  
> `.\venv\Scripts\python.exe src\main.py` 사용!

---

## 💡 개발 모드 vs 일반 설치

### 개발 모드 (`pip install -e .`)
```powershell
pip install -e .
python src\main.py  # ✅ 코드 수정 후 바로 실행 가능!
```

**장점:**
- ✅ 코드 수정 후 **재설치 불필요**
- ✅ 디버깅 용이
- ✅ 빠른 개발 사이클

### 일반 설치 (`pip install .`)
```powershell
pip install .
rna-seq-analyzer  # 시스템 어디서나 실행 가능
```

**단점:**
- ❌ 코드 수정 시 **매번 재설치** 필요
- ❌ 개발 중에는 비효율적

---

## 🛠️ 개발 워크플로우

### 일반적인 개발 과정:

```powershell
# 1. 코드 수정
code src\gui\main_window.py

# 2. 바로 실행 (재설치 없음!)
.\run_dev.ps1

# 3. 테스트
.\run_dev.ps1 -Test

# 4. 캐시 정리 후 실행
.\run_dev.ps1 -Clean
```

### VS Code 사용 시:

1. **F5** - 프로그램 디버그 실행
2. **Ctrl+Shift+F5** - 디버거 없이 실행
3. 코드에 **Breakpoint** 설정 (라인 번호 왼쪽 클릭)
4. 변수 값 확인, 단계별 실행 가능

---

## 📝 자주 사용하는 명령어

```powershell
# 프로그램 실행
python src\main.py
.\run_dev.ps1

# 테스트 실행
python -m pytest test/ -v
.\run_dev.ps1 -Test

# 특정 테스트만
python -m pytest test/test_fsm.py -v

# 디버그 모드 실행
python -m pdb src\main.py
.\run_dev.ps1 -Debug

# 코드 포맷팅 (black 설치 필요)
black src/

# 코드 품질 검사 (flake8 설치 필요)
flake8 src/
```

---

## 🔧 run_dev.ps1 스크립트 사용법

개발을 편리하게 해주는 PowerShell 스크립트입니다.

### 기본 사용:
```powershell
# 일반 실행
.\run_dev.ps1

# 옵션:
.\run_dev.ps1 -Test     # 테스트 실행
.\run_dev.ps1 -Debug    # 디버거로 실행
.\run_dev.ps1 -Clean    # 캐시 정리 후 실행
```

### 스크립트가 자동으로 수행하는 작업:
- ✅ 가상환경 활성화 확인
- ✅ PYTHONPATH 자동 설정
- ✅ 오류 발생 시 최근 로그 표시
- ✅ 색상 출력으로 가독성 향상

---

## 🎯 핵심 포인트

### ✅ DO (권장)
```powershell
# 개발 모드 설치
pip install -e .

# 코드 수정 후 바로 실행
python src\main.py

# 정기적으로 테스트 실행
python -m pytest test/ -v
```

### ❌ DON'T (비권장)
```powershell
# 일반 설치 (개발 중)
pip install .  # ❌ 코드 수정마다 재설치 필요

# 테스트 없이 배포
# ❌ 항상 테스트 후 배포!
```

---

## 🐛 문제 해결

### 문제 1: PowerShell 스크립트 실행 권한 오류
**증상**: "스크립트를 실행할 수 없으므로..." 오류

**해결**:
```powershell
# 실행 정책 변경 (한 번만)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 다시 가상환경 활성화
venv\Scripts\activate
```

### 문제 2: "ModuleNotFoundError: No module named 'PyQt6'"
**증상**: 패키지 설치 후에도 import 오류

**원인**: 시스템의 다른 Python이 실행됨 (예: Miniconda)

**해결**:
```powershell
# 가상환경 Python을 명시적으로 사용
.\venv\Scripts\python.exe src\main.py

# 또는 run_dev.ps1 사용
.\run_dev.ps1
```

### 문제 3: PYTHONPATH 문제
**증상**: "ModuleNotFoundError" (PyQt6가 아닌 경우)

**해결**:
```powershell
# PYTHONPATH 설정 확인
$env:PYTHONPATH

# run_dev.ps1 사용 (자동 설정)
.\run_dev.ps1
```

### 문제 4: 가상환경이 활성화되지 않음
**해결**:
```powershell
# 수동 활성화
venv\Scripts\activate

# 프롬프트에 (venv) 표시 확인
```

### 문제 5: 패키지를 찾을 수 없음
**해결**:
```powershell
# 개발 의존성 재설치
pip install -e ".[dev]"

# 또는 기본 의존성만
pip install -e .
```

---

## 📚 추가 학습 자료

- [DEVELOPMENT.md](DEVELOPMENT.md) - 상세한 개발 가이드
- [README.md](../README.md) - 프로젝트 전체 설명
- [FSM_DIAGRAM.md](FSM_DIAGRAM.md) - FSM 상태 다이어그램

---

**이제 개발을 시작하세요!** 🚀

```powershell
# 1. 가상환경 활성화
venv\Scripts\activate

# 2. 개발 모드 설치 (한 번만)
pip install -e .

# 3. 개발 시작!
.\run_dev.ps1
```
