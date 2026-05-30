# 개발 환경 설정 가이드

## 🛠️ 개발 모드 설정

개발 중에는 코드를 수정할 때마다 재설치할 필요 없이 바로 테스트할 수 있는 **editable install** 방식을 사용하세요.

### 방법 1: pip editable install (권장)

```powershell
# 1. 가상환경 생성 및 활성화
python -m venv venv
venv\Scripts\activate

# 2. 개발 모드로 설치 (-e 옵션 = editable)
pip install -e .

# 또는 개발 의존성 포함
pip install -e ".[dev]"

# 3. 코드 수정 후 바로 실행 가능!
python src\main.py
# 또는 어디서나
rna-seq-analyzer
```

**장점:**
- ✅ 코드 수정 후 재설치 불필요
- ✅ 어디서나 `import` 가능
- ✅ Entry point 명령어 사용 가능

### 방법 2: PYTHONPATH 설정 (간단)

#### PowerShell에서 임시 설정:
```powershell
# 현재 세션에서만 유효
$env:PYTHONPATH = "C:\Users\USER\Documents\GitHub\rna-seq-data-view\src"
python src\main.py
```

#### 영구 설정 (추천하지 않음):
```powershell
# 시스템 환경변수에 추가
[System.Environment]::SetEnvironmentVariable("PYTHONPATH", "C:\Users\USER\Documents\GitHub\rna-seq-data-view\src", "User")
```

### 방법 3: VS Code 통합 개발 환경

프로젝트 루트에 `.vscode/launch.json` 생성:

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: RNA-Seq Analyzer",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/src/main.py",
            "console": "integratedTerminal",
            "env": {
                "PYTHONPATH": "${workspaceFolder}/src"
            },
            "cwd": "${workspaceFolder}"
        },
        {
            "name": "Python: Current File",
            "type": "python",
            "request": "launch",
            "program": "${file}",
            "console": "integratedTerminal",
            "env": {
                "PYTHONPATH": "${workspaceFolder}/src"
            }
        }
    ]
}
```

**사용법:**
1. VS Code에서 `F5` 누르기
2. "Python: RNA-Seq Analyzer" 선택
3. 디버거로 실행!

---

## 🔄 개발 워크플로우

### 일반적인 개발 사이클:

```powershell
# 1. 코드 수정 (예: src/gui/main_window.py)

# 2. 바로 실행 (재설치 불필요!)
python src\main.py

# 3. 문제 발견 시 디버깅
python -m pdb src\main.py

# 4. 테스트 실행
python -m pytest test/test_fsm.py -v

# 5. 로그 확인
cat logs\rna_seq_*.log
```

### Hot Reload 스크립트 (선택사항)

파일 변경 감지 자동 재시작:

```powershell
# watchdog 설치
pip install watchdog

# 감시 스크립트 실행
watchmedo auto-restart --patterns="*.py" --recursive -- python src\main.py
```

---

## 📝 개발 모드 vs 배포 모드

| 항목 | 개발 모드 | 배포 모드 |
|------|----------|----------|
| 설치 | `pip install -e .` | `pip install .` |
| 수정 반영 | 즉시 | 재설치 필요 |
| 디버깅 | 쉬움 | 어려움 |
| 로그 레벨 | DEBUG | INFO |
| 의존성 | `[dev]` 포함 | 최소한만 |

---

## 🐛 디버깅 팁

### 1. Python 내장 디버거 (pdb)

```python
# 코드에 breakpoint 추가
import pdb; pdb.set_trace()

# 또는 Python 3.7+
breakpoint()
```

### 2. VS Code 디버거 사용

- 라인 옆 클릭 → Breakpoint 설정
- `F5` → 디버그 시작
- `F10` → Step Over
- `F11` → Step Into

### 3. 로그 레벨 조정

`src/main.py` 수정:
```python
# 개발 모드에서는 DEBUG 레벨 사용
logger = setup_logger()
logger.setLevel(logging.DEBUG)  # 상세 로그
```

### 4. GUI 디버깅

```python
# 메인 윈도우에서 콘솔 출력 확인
from PyQt6.QtCore import qDebug
qDebug("Debug message")

# 또는 stderr로 출력
import sys
print("Debug:", value, file=sys.stderr)
```

---

## 🧪 테스트 주도 개발 (TDD)

### 1. 새 기능 추가 전 테스트 작성

```python
# test/test_new_feature.py
def test_new_feature():
    # 기대하는 동작 정의
    assert new_feature() == expected_result
```

### 2. 기능 구현

```python
# src/utils/new_feature.py
def new_feature():
    # 구현
    return result
```

### 3. 테스트 실행

```powershell
# 특정 테스트만 실행
python -m pytest test/test_new_feature.py -v

# 커버리지 확인
python -m pytest --cov=src test/
```

---

## 📦 의존성 관리

### 개발 의존성 추가

```powershell
# 새 패키지 설치
pip install new-package

# requirements.txt 업데이트
pip freeze > requirements.txt

# 또는 선택적으로
echo "new-package>=1.0.0" >> requirements.txt
```

### 깔끔한 환경 유지

```powershell
# 가상환경 재생성
deactivate
Remove-Item -Recurse -Force venv
python -m venv venv
venv\Scripts\activate
pip install -e ".[dev]"
```

---

## 🚀 프로덕션 빌드

개발 완료 후 배포용 빌드:

```powershell
# 1. 테스트 전체 실행
python -m pytest test/ -v

# 2. 코드 품질 검사
flake8 src/
black --check src/

# 3. 타입 체크
mypy src/

# 4. 배포용 설치
pip install .

# 5. 실행 파일 생성 (옵션)
pip install pyinstaller
pyinstaller --onefile --windowed src/main.py
```

---

## 💡 개발 효율 향상 팁

### 1. Pre-commit Hook 설정

```powershell
# pre-commit 설치
pip install pre-commit

# .pre-commit-config.yaml 생성 (프로젝트 루트)
```

내용:
```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.0.0
    hooks:
      - id: black
  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
```

설치:
```powershell
pre-commit install
```

### 2. 빠른 실행 스크립트

`run_dev.ps1` 생성:
```powershell
# 개발 모드 실행 스크립트
$ErrorActionPreference = "Stop"

Write-Host "Starting RNA-Seq Analyzer (Dev Mode)..." -ForegroundColor Green

# 가상환경 활성화 확인
if (-not $env:VIRTUAL_ENV) {
    .\venv\Scripts\Activate.ps1
}

# PYTHONPATH 설정
$env:PYTHONPATH = "$PWD\src"

# 실행
python src\main.py

# 종료 시 로그 표시
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error occurred. Check logs:" -ForegroundColor Red
    Get-ChildItem logs\*.log | Sort-Object LastWriteTime -Descending | Select-Object -First 1 | Get-Content -Tail 20
}
```

사용:
```powershell
.\run_dev.ps1
```

### 3. 코드 자동 포맷팅

```powershell
# Black으로 전체 코드 포맷팅
black src/

# 특정 파일만
black src/gui/main_window.py
```

---

## 🎯 추천 개발 환경 설정 (Best Practice)

```powershell
# 1. 가상환경 생성
python -m venv venv
venv\Scripts\activate

# 2. 개발 모드 설치
pip install -e ".[dev]"

# 3. VS Code 설정 확인
code .vscode/launch.json
code .vscode/settings.json

# 4. 개발 시작!
code .
# F5로 디버그 실행
```

이제 코드 수정 → 저장 → F5 → 테스트 사이클을 빠르게 반복할 수 있습니다! 🚀
