# CMG-SeqViewer 개발자 가이드 (Developer Setup)

> **목적**: CMG-SeqViewer의 개발 환경을 설정하고, 코드 수정 및 테스트하는 방법을 설명합니다.

## 목차
1. [빠른 시작](#빠른-시작-5분)
2. [상세 설정](#상세-설정)
3. [개발 모드](#개발-모드)
4. [개발 워크플로우](#개발-워크플로우)
5. [디버깅](#디버깅)
6. [테스트](#테스트)
7. [코드 스타일](#코드-스타일)
8. [문제 해결](#문제-해결)

---

## 빠른 시작 (5분)

### 전제 조건
- **Python 3.9 이상** (3.10+ 권장)
- **Git** (버전 관리)
- **Visual Studio Code** (권장 에디터, 선택사항)

> Python이 설치되어 있지 않다면? → [Python 설치 가이드](../user/installation.md)

### 1단계: 저장소 클론

```powershell
# GitHub에서 클론
git clone https://github.com/YOUR_USERNAME/cmg-seqviewer.git
cd cmg-seqviewer

# 또는 로컬 폴더에서 시작
cd C:\Users\USER\Documents\GitHub\rna-seq-data-view
```

### 2단계: 가상환경 생성 및 활성화

```powershell
# 가상환경 생성
python -m venv venv

# 가상환경 활성화 (Windows)
.\venv\Scripts\Activate.ps1

# macOS/Linux
source venv/bin/activate
```

> ⚠️ **PowerShell 실행 정책 오류 시**:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

### 3단계: 의존성 설치 (개발 모드)

```powershell
# 개발 모드로 설치 (editable install)
pip install -e .

# 또는 개발 도구 포함 (pytest, flake8 등)
pip install -e ".[dev]"
```

**설치되는 주요 패키지**:
- **PyQt6** (6.10+) - GUI 프레임워크
- **pandas** (3.0+) - 데이터 처리
- **numpy** (2.4+) - 수치 계산
- **scipy** - 통계 분석
- **matplotlib**, **seaborn** - 시각화
- **openpyxl** - Excel 파일 읽기
- **matplotlib-venn**, **upsetplot** - 벤 다이어그램, Upset plot
- **networkx** - GO/KEGG 네트워크 시각화

### 4단계: 실행!

#### Windows

```powershell
# 방법 1: 가상환경 Python 명시적 실행 (⭐ 가장 안전)
.\venv\Scripts\python.exe src\main.py

# 방법 2: 일반 실행 (가상환경 활성화 시)
python src\main.py

# 방법 3: 개발 스크립트 사용 (권장)
.\run_dev.ps1

# 방법 4: VS Code에서 F5 (디버깅)
```

#### macOS/Linux

```bash
# 방법 1: 가상환경 Python 명시적 실행
./venv/bin/python src/main.py

# 방법 2: 일반 실행
python src/main.py

# 방법 3: 개발 스크립트 사용
./run_dev.sh  # 있는 경우
```

> 💡 **Tip**: 가상환경이 제대로 인식되지 않을 때는 가상환경의 Python을 명시적으로 사용하세요!

---

## 상세 설정

### VS Code 통합 개발 환경

#### 1. VS Code 확장 설치 (권장)

- **Python** (Microsoft) - Python 언어 지원
- **Pylance** (Microsoft) - Python 언어 서버
- **Python Debugger** (Microsoft) - 디버깅 지원

#### 2. 설정 파일 생성

**`.vscode/launch.json`** (디버그 설정):
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: RNA-Seq Analyzer (Main)",
            "type": "debugpy",
            "request": "launch",
            "program": "${workspaceFolder}/src/main.py",
            "console": "integratedTerminal",
            "env": {
                "PYTHONPATH": "${workspaceFolder}/src"
            },
            "cwd": "${workspaceFolder}",
            "justMyCode": true
        },
        {
            "name": "Python: Current File",
            "type": "debugpy",
            "request": "launch",
            "program": "${file}",
            "console": "integratedTerminal",
            "env": {
                "PYTHONPATH": "${workspaceFolder}/src"
            },
            "cwd": "${workspaceFolder}"
        },
        {
            "name": "Python: Test (pytest)",
            "type": "debugpy",
            "request": "launch",
            "module": "pytest",
            "args": [
                "test/",
                "-v",
                "--tb=short"
            ],
            "console": "integratedTerminal",
            "env": {
                "PYTHONPATH": "${workspaceFolder}/src"
            },
            "cwd": "${workspaceFolder}"
        }
    ]
}
```

**`.vscode/settings.json`** (프로젝트 설정):
```json
{
    "python.defaultInterpreterPath": "${workspaceFolder}/venv/Scripts/python.exe",
    "python.analysis.extraPaths": [
        "${workspaceFolder}/src"
    ],
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": [
        "test",
        "-v"
    ],
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.linting.flake8Args": [
        "--max-line-length=120"
    ],
    "python.formatting.provider": "black",
    "python.formatting.blackArgs": [
        "--line-length=100"
    ],
    "editor.formatOnSave": false,
    "editor.rulers": [100, 120],
    "files.exclude": {
        "**/__pycache__": true,
        "**/*.pyc": true,
        "build/": true,
        "dist/": true
    }
}
```

#### 3. VS Code 사용법

**디버깅**:
1. 코드에 **Breakpoint** 설정 (라인 번호 왼쪽 클릭)
2. **F5** 또는 상단 메뉴 → Run → Start Debugging
3. 변수 값 확인, 단계별 실행 (F10, F11)

**단축키**:
- `F5` - 디버그 실행
- `Ctrl+Shift+F5` - 디버거 없이 실행
- `F9` - Breakpoint 토글
- `F10` - Step Over (다음 라인)
- `F11` - Step Into (함수 내부로)
- `Shift+F11` - Step Out (함수 밖으로)

### run_dev.ps1 스크립트 (Windows 전용)

개발을 편리하게 해주는 PowerShell 스크립트입니다.

#### 기본 사용법

```powershell
# 일반 실행
.\run_dev.ps1

# 테스트 실행
.\run_dev.ps1 -Test

# 디버거로 실행
.\run_dev.ps1 -Debug

# 캐시 정리 후 실행
.\run_dev.ps1 -Clean

# 빌드
.\run_dev.ps1 -Build
```

#### 스크립트가 자동으로 수행하는 작업
- ✅ 가상환경 활성화 확인
- ✅ PYTHONPATH 자동 설정
- ✅ 로그 디렉토리 생성
- ✅ `__pycache__` 정리 (Clean 옵션)

---

## 개발 모드

### 개발 모드 vs 일반 설치

#### ⭐ 개발 모드 (`pip install -e .`)

**장점**:
- ✅ 코드 수정 후 **재설치 불필요**
- ✅ 디버깅 용이 (소스 코드 직접 참조)
- ✅ 빠른 개발 사이클
- ✅ Entry point 명령어 사용 가능

**사용**:
```powershell
pip install -e .
python src\main.py  # ✅ 코드 수정 후 바로 실행 가능!
```

#### 일반 설치 (`pip install .`)

**장점**:
- 시스템 어디서나 실행 가능
- 배포 환경과 동일

**단점**:
- ❌ 코드 수정 시 **매번 재설치** 필요
- ❌ 개발 중에는 비효율적

**사용**:
```powershell
pip install .
rna-seq-analyzer  # 어디서나 실행
```

### PYTHONPATH 설정 (대안)

#### PowerShell (임시)
```powershell
# 현재 세션에서만 유효
$env:PYTHONPATH = "C:\Users\USER\Documents\GitHub\rna-seq-data-view\src"
python src\main.py
```

#### Bash (임시)
```bash
export PYTHONPATH="/path/to/rna-seq-data-view/src"
python src/main.py
```

> **권장하지 않음**: 개발 모드 설치가 더 편리합니다.

---

## 개발 워크플로우

### 일반적인 개발 사이클

```powershell
# 1. 기능 브랜치 생성
git checkout -b feature/new-feature

# 2. 코드 수정
code src\gui\main_window.py

# 3. 저장 (Ctrl+S)

# 4. 실행 및 테스트
.\run_dev.ps1

# 5. 버그 발견 시 디버깅
# VS Code에서 F5 또는:
python -m pdb src\main.py

# 6. 유닛 테스트 실행
pytest test/ -v

# 7. 특정 테스트만 실행
pytest test/test_fsm.py -v

# 8. 코드 스타일 검사
flake8 src/

# 9. 커밋
git add .
git commit -m "feat: Add new feature"

# 10. 푸시
git push origin feature/new-feature
```

### Hot Reload (선택사항)

파일 변경 시 자동 재시작:

```powershell
# watchdog 설치
pip install watchdog

# 감시 스크립트 실행
watchmedo auto-restart --patterns="*.py" --recursive -- python src\main.py
```

---

## 디버깅

### 1. Python 내장 디버거 (pdb)

```python
# 코드에 breakpoint 추가
import pdb; pdb.set_trace()

# 또는 Python 3.7+
breakpoint()
```

**pdb 명령어**:
- `n` (next) - 다음 라인
- `s` (step) - 함수 내부로
- `c` (continue) - 계속 실행
- `p variable` - 변수 출력
- `l` (list) - 소스 코드 보기
- `q` (quit) - 종료

### 2. VS Code 디버거 (권장)

**장점**:
- GUI로 변수 확인
- Call stack 탐색
- Watch 표현식 추가
- Conditional breakpoint

**사용법**:
1. 라인 옆 클릭 → Breakpoint 설정
2. `F5` → 디버그 시작
3. 왼쪽 패널에서 변수, Call stack 확인

### 3. 로그 활용

```python
# src/core/logger.py 사용
from core.logger import get_logger

logger = get_logger(__name__)

# 로그 레벨별 사용
logger.debug("디버그 정보")
logger.info("일반 정보")
logger.warning("경고")
logger.error("오류")
logger.critical("치명적 오류")
```

**로그 파일 위치**: `logs/rna_seq_YYYYMMDD_HHMMSS.log`

### 4. Qt 디버깅

```python
# Qt 이벤트 디버깅
import sys
from PyQt6.QtCore import qDebug, qWarning, qCritical

qDebug("Debug message")
qWarning("Warning message")
qCritical("Critical message")

# Qt 이벤트 루프 디버깅
app.exec()  # 여기에 breakpoint 설정
```

---

## 테스트

### pytest 사용

#### 기본 테스트 실행

```powershell
# 모든 테스트 실행
pytest test/ -v

# 특정 파일 테스트
pytest test/test_fsm.py -v

# 특정 테스트 함수만
pytest test/test_fsm.py::test_initial_state -v

# 마커별 실행
pytest -m slow  # @pytest.mark.slow로 표시된 테스트만

# 커버리지 측정
pytest test/ --cov=src --cov-report=html
```

#### VS Code에서 테스트

1. 왼쪽 패널 → Testing (비커 아이콘)
2. "Configure Python Tests" → pytest 선택
3. 테스트 목록에서 실행할 테스트 선택
4. 우클릭 → Run Test 또는 Debug Test

### 테스트 작성

**테스트 파일 예시** (`test/test_example.py`):

```python
import pytest
from src.utils.database_manager import DatabaseManager

class TestDatabaseManager:
    @pytest.fixture
    def db_manager(self):
        """각 테스트마다 새로운 DB 매니저 생성"""
        manager = DatabaseManager()
        yield manager
        # 테스트 후 정리
        manager.close()
    
    def test_load_datasets(self, db_manager):
        """데이터셋 로드 테스트"""
        datasets = db_manager.get_all_datasets()
        assert isinstance(datasets, list)
        assert len(datasets) >= 0
    
    def test_import_dataset(self, db_manager, tmp_path):
        """데이터셋 임포트 테스트"""
        # 테스트 데이터 생성
        test_file = tmp_path / "test.xlsx"
        # ... 테스트 데이터 작성
        
        result = db_manager.import_dataset(str(test_file))
        assert result is True
```

### GUI 테스트 (선택사항)

```python
import pytest
from PyQt6.QtWidgets import QApplication
from src.gui.main_window import MainWindow

@pytest.fixture(scope="session")
def qapp():
    """QApplication fixture"""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
    app.quit()

def test_main_window(qapp):
    """메인 윈도우 생성 테스트"""
    window = MainWindow()
    assert window.windowTitle() == "CMG-SeqViewer"
    window.close()
```

---

## 코드 스타일

### PEP 8 준수

```powershell
# flake8 설치
pip install flake8

# 코드 스타일 검사
flake8 src/

# 특정 규칙 무시
flake8 src/ --ignore=E501,W503

# 최대 줄 길이 설정
flake8 src/ --max-line-length=120
```

### Black 포매터 (선택사항)

```powershell
# black 설치
pip install black

# 코드 포맷팅
black src/

# 줄 길이 설정
black src/ --line-length=100

# 미리보기 (실제 수정 안함)
black src/ --check --diff
```

### Type Hints (선택사항)

```python
from typing import List, Optional, Dict

def process_data(data: List[Dict], threshold: float = 0.05) -> Optional[pd.DataFrame]:
    """
    데이터 처리 함수
    
    Args:
        data: 입력 데이터 리스트
        threshold: 필터링 임계값
    
    Returns:
        처리된 DataFrame 또는 None
    """
    if not data:
        return None
    return pd.DataFrame(data)
```

**mypy로 타입 검사**:
```powershell
pip install mypy
mypy src/
```

### Docstring 규칙

```python
def complex_function(param1: str, param2: int, param3: Optional[bool] = None) -> Dict:
    """
    복잡한 함수 예시
    
    Args:
        param1: 첫 번째 매개변수 설명
        param2: 두 번째 매개변수 설명
        param3: 선택적 매개변수 (기본값: None)
    
    Returns:
        결과 딕셔너리
    
    Raises:
        ValueError: param2가 음수일 때
    
    Example:
        >>> complex_function("test", 5)
        {'result': 'success'}
    """
    if param2 < 0:
        raise ValueError("param2 must be non-negative")
    
    return {'result': 'success', 'param1': param1}
```

---

## 문제 해결

### 가상환경 활성화 안됨

**증상**: `venv\Scripts\activate` 실행 시 오류

**해결** (Windows):
```powershell
# PowerShell 실행 정책 변경
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 또는 우회
.\venv\Scripts\python.exe src\main.py
```

### 모듈 import 오류

**증상**: `ModuleNotFoundError: No module named 'src'`

**해결**:
```powershell
# 방법 1: 개발 모드 재설치
pip install -e .

# 방법 2: PYTHONPATH 설정
$env:PYTHONPATH = "C:\path\to\rna-seq-data-view\src"

# 방법 3: VS Code launch.json에 env 추가
"env": {"PYTHONPATH": "${workspaceFolder}/src"}
```

### PyQt6 import 오류

**증상**: `ModuleNotFoundError: No module named 'PyQt6'`

**해결**:
```powershell
# PyQt6 재설치
pip uninstall PyQt6 PyQt6-Qt6 PyQt6-sip
pip install PyQt6

# 가상환경 확인
where python
# venv의 python이어야 함
```

### 디버거 연결 안됨

**증상**: VS Code에서 F5 눌러도 실행 안됨

**해결**:
```json
// .vscode/launch.json 확인
{
    "type": "debugpy",  // "python"이 아니라 "debugpy"
    "request": "launch",
    "program": "${workspaceFolder}/src/main.py",
}

// debugpy 설치 확인
pip install debugpy
```

### 테스트 실행 안됨

**증상**: `pytest` 명령어를 찾을 수 없음

**해결**:
```powershell
# pytest 설치
pip install pytest

# 또는 개발 의존성 전체 설치
pip install -e ".[dev]"

# Python 모듈로 실행
python -m pytest test/ -v
```

### Hot Reload 안됨

**증상**: 코드 수정해도 반영 안됨

**원인**: 일반 설치 모드 (`pip install .`)

**해결**:
```powershell
# 개발 모드로 재설치
pip uninstall rna-seq-data-analyzer
pip install -e .
```

### 빌드 실패

**증상**: `pyinstaller` 명령어 오류

**해결**:
```powershell
# PyInstaller 재설치
pip install --upgrade pyinstaller

# 캐시 정리
rm -r build dist __pycache__

# 다시 빌드
pyinstaller --clean rna-seq-viewer.spec
```

---

## 다음 단계

개발 환경 설정이 완료되었다면:

1. [프로젝트 구조](./project-structure.md) - 코드베이스 이해
2. [아키텍처 가이드](./architecture.md) - FSM, MVP 패턴 학습
3. [기여 가이드](./contributing.md) - Pull Request 작성 방법
4. [빌드 가이드](../deployment/build-guide.md) - 실행 파일 생성
5. [테스트 가이드](./testing.md) - 테스트 작성 및 실행

---

## 참고 자료

- **Python 공식 문서**: https://docs.python.org/3/
- **PyQt6 문서**: https://www.riverbankcomputing.com/static/Docs/PyQt6/
- **pytest 문서**: https://docs.pytest.org/
- **PEP 8 스타일 가이드**: https://peps.python.org/pep-0008/
- **Black 포매터**: https://black.readthedocs.io/
