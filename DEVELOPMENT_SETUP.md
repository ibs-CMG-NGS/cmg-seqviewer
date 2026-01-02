# 🚀 개발 모드 설정 완료!

## ✅ 추가된 개발 도구

### 📁 새로 생성된 파일들

1. **docs/QUICK_START.md** - 5분 만에 개발 환경 설정
2. **docs/DEVELOPMENT.md** - 상세한 개발 가이드
3. **run_dev.ps1** - 개발용 실행 스크립트
4. **.vscode/launch.json** - VS Code 디버그 설정
5. **.vscode/settings.json** - VS Code 프로젝트 설정
6. **.env.example** - 환경 변수 예제

---

## 🎯 지금 바로 시작하기

### 1️⃣ 가상환경 생성

> ⚠️ **Python이 설치되어 있지 않다면?**  
> → [Python 설치 가이드](docs/PYTHON_INSTALLATION.md) 참고

```powershell
# Windows Python Launcher 사용 (권장)
py -m venv venv

# 또는 python 명령어
python -m venv venv

# 가상환경 활성화
venv\Scripts\activate
```

**문제 발생 시:**
- `py` 명령어를 사용하세요 (Windows 내장)
- Python 설치: https://www.python.org/downloads/
- 자세한 해결 방법: [PYTHON_INSTALLATION.md](docs/PYTHON_INSTALLATION.md)

> ⚠️ **PowerShell 실행 정책 오류 발생 시**  
> ```powershell
> # 실행 정책을 RemoteSigned로 변경 (한 번만 실행)
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```
> 이후 다시 `venv\Scripts\activate` 실행

### 2️⃣ 개발 모드 설치 (중요! ⭐)
```powershell
# 기본 의존성 설치 (권장)
pip install -e .

# 또는 개발 도구 포함 (pytest 등)
pip install -e ".[dev]"
```
이 명령어가 핵심입니다!
- `-e` 옵션으로 **editable install** (편집 가능 설치)
- 코드를 수정해도 **재설치 불필요**
- 개발-테스트 사이클이 훨씬 빠름!

**설치되는 패키지:**
- PyQt6, pandas, numpy, scipy (데이터 분석)
- matplotlib, seaborn (시각화)
- openpyxl (Excel 파일 읽기)
- matplotlib-venn, upsetplot (벤 다이어그램, Upset plot)

### 3️⃣ 실행 방법 (3가지)

#### 방법 A: 개발 스크립트 사용 (권장)
```powershell
# 일반 실행
.\run_dev.ps1

# 테스트 실행
.\run_dev.ps1 -Test

# 디버그 모드
.\run_dev.ps1 -Debug

# 캐시 정리 후 실행
.\run_dev.ps1 -Clean
```

#### 방법 B: 직접 실행
```powershell
# 일반 실행 (가상환경이 제대로 활성화된 경우)
python src\main.py

# 가상환경 Python 명시적 실행 (더 안전함! ⭐)
.\venv\Scripts\python.exe src\main.py
```

> 💡 **Tip**: PowerShell이 가상환경을 제대로 인식하지 못할 때가 있습니다.  
> `.\venv\Scripts\python.exe`를 명시적으로 사용하면 확실합니다!

#### 방법 C: VS Code 디버거
1. VS Code 열기
2. `F5` 키 누르기
3. "Python: RNA-Seq Analyzer (Main)" 선택
4. 디버깅 시작!

---

## 💡 개발 모드의 장점

### Before (일반 설치)
```powershell
pip install .           # 설치
python src\main.py      # 실행
# 코드 수정...
pip install .           # ❌ 재설치 필요!
python src\main.py
```

### After (개발 모드) ⭐
```powershell
pip install -e .        # 한 번만 설치
python src\main.py      # 실행
# 코드 수정...
python src\main.py      # ✅ 바로 실행 가능!
```

---

## 🛠️ 일반적인 개발 워크플로우

```powershell
# 1. 코드 수정
code src\gui\main_window.py

# 2. 저장 (Ctrl+S)

# 3. 실행
.\run_dev.ps1
# 또는 VS Code에서 F5

# 4. 버그 발견 시
# - Breakpoint 설정
# - F5로 디버그 실행
# - 변수 값 확인

# 5. 수정 후 다시 실행
.\run_dev.ps1

# 6. 테스트
.\run_dev.ps1 -Test
```

---

## 📝 자주 사용하는 명령어

### 프로그램 실행
```powershell
.\run_dev.ps1              # 개발 스크립트로 실행
python src\main.py         # 직접 실행
```

### 테스트
```powershell
.\run_dev.ps1 -Test                    # 전체 테스트
python -m pytest test/ -v              # pytest 직접 실행
python -m pytest test/test_fsm.py -v   # 특정 테스트만
```

### 디버깅
```powershell
.\run_dev.ps1 -Debug       # pdb 디버거로 실행
# VS Code에서 F5         # GUI 디버거 (더 편리함!)
```

### 캐시 정리
```powershell
.\run_dev.ps1 -Clean       # 캐시 정리 후 실행
```

---

## 🎨 VS Code 단축키

| 키 | 동작 |
|----|------|
| `F5` | 디버그 시작/계속 |
| `F9` | Breakpoint 토글 |
| `F10` | Step Over (다음 줄) |
| `F11` | Step Into (함수 내부로) |
| `Shift+F11` | Step Out (함수 밖으로) |
| `Ctrl+Shift+F5` | 재시작 |
| `Shift+F5` | 중지 |

---

## 📖 상세 문서

- **[QUICK_START.md](docs/QUICK_START.md)** - 빠른 시작 가이드
- **[DEVELOPMENT.md](docs/DEVELOPMENT.md)** - 상세 개발 가이드
  - Hot Reload 설정
  - Pre-commit Hook
  - 테스트 주도 개발 (TDD)
  - 프로덕션 빌드
- **[FSM_DIAGRAM.md](docs/FSM_DIAGRAM.md)** - FSM 상태 다이어그램

---

## 🔧 문제 해결

### Q: "pip install -e ." 실행 시 오류
```powershell
# setup.py가 있는 디렉토리에서 실행했는지 확인
cd c:\Users\USER\Documents\GitHub\rna-seq-data-view
pip install -e .
```

### Q: "ModuleNotFoundError" 발생
```powershell
# run_dev.ps1 사용 시 자동 해결됨
.\run_dev.ps1

# 또는 수동으로 PYTHONPATH 설정
$env:PYTHONPATH = "$PWD\src"
```

### Q: PowerShell 스크립트 실행 권한 오류
**증상**: `venv\Scripts\activate` 실행 시 "스크립트를 실행할 수 없습니다" 오류

**해결**:
```powershell
# 실행 정책 변경 (한 번만 실행)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 이후 다시 활성화
venv\Scripts\activate
```

### Q: 가상환경 활성화 안 됨
```powershell
# 수동 활성화
venv\Scripts\activate

# 프롬프트에 (venv) 표시되면 성공!
```

### Q: "ModuleNotFoundError: No module named 'PyQt6'" 오류
**증상**: 패키지를 설치했는데도 import 오류 발생

**원인**: 시스템의 다른 Python(예: Miniconda)이 실행되고 있음

**해결**:
```powershell
# 가상환경의 Python을 명시적으로 사용
.\venv\Scripts\python.exe src\main.py

# 또는 run_dev.ps1 사용 (자동으로 처리됨)
.\run_dev.ps1
```

---

## 🎉 다음 단계

1. **개발 시작**
   ```powershell
   .\run_dev.ps1
   ```

2. **첫 번째 수정 해보기**
   - `src/gui/main_window.py` 열기
   - 윈도우 타이틀 변경
   - 저장 후 `.\run_dev.ps1` 실행
   - 변경사항 즉시 확인!

3. **디버거 사용해보기**
   - VS Code에서 `F5`
   - Breakpoint 설정
   - 변수 값 확인

---

## 💬 요약

```powershell
# ✅ 한 번만 하면 됨
pip install -e ".[dev]"

# ✅ 코드 수정 후 매번
.\run_dev.ps1

# 또는 VS Code에서 F5
```

**이제 코드를 수정할 때마다 재설치할 필요가 없습니다!** 🚀

---

**Happy Coding!** 💻✨
