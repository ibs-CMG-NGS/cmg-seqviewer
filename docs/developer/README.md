# 개발자 가이드 (Developer Documentation)

> 👨‍💻 CMG-SeqViewer 개발 환경 설정, 코드 구조, 기여 방법

## 📚 문서 목록

### 시작하기
| 문서 | 설명 | 난이도 |
|------|------|--------|
| [개발 환경 설정](setup.md) | Python 환경 구축 및 실행 | ⭐ 기초 |
| [프로젝트 구조](architecture.md) | 코드베이스 이해 | ⭐⭐ 중급 |

### 개발 가이드
| 문서 | 설명 | 난이도 |
|------|------|--------|
| [기여 가이드](contributing.md) | Pull Request 작성 | ⭐⭐ 중급 |
| [테스트 가이드](testing.md) | 테스트 작성 및 실행 | ⭐⭐ 중급 |
| [API 문서](api.md) | 주요 클래스 및 함수 | ⭐⭐⭐ 고급 |
| [파이프라인 연동 가이드](pipeline-integration.md) | R 파이프라인 → 앱 직결 규격 | ⭐⭐ 중급 |

### 아키텍처
| 문서 | 설명 | 난이도 |
|------|------|--------|
| [FSM 다이어그램](../FSM_DIAGRAM.md) | 상태 머신 구조 | ⭐⭐⭐ 고급 |
| [데이터베이스 가이드](../DATABASE_GUIDE.md) | DB 스키마 및 쿼리 | ⭐⭐ 중급 |

---

## 🚀 빠른 시작

### 5분 만에 개발 환경 설정

```powershell
# 1. 저장소 클론
git clone https://github.com/ibs-CMG-NGS/cmg-seqviewer.git
cd cmg-seqviewer

# 2. 가상환경 생성
python -m venv venv
.\venv\Scripts\Activate.ps1  # Windows
# source venv/bin/activate    # macOS/Linux

# 3. 개발 모드 설치
pip install -e ".[dev]"

# 4. 실행
python src\main.py
```

자세한 내용: [개발 환경 설정](setup.md)

---

## 🏗️ 프로젝트 구조

```
rna-seq-data-view/
├── src/                    # 소스 코드
│   ├── main.py            # 진입점
│   ├── core/              # 핵심 컴포넌트
│   │   ├── fsm.py        # Finite State Machine
│   │   └── logger.py     # 로깅 시스템
│   ├── models/            # 데이터 모델
│   ├── gui/               # GUI 컴포넌트
│   │   ├── main_window.py
│   │   ├── filter_panel.py
│   │   └── workers.py    # 비동기 작업
│   ├── presenters/        # 비즈니스 로직
│   ├── utils/             # 유틸리티
│   │   ├── data_loader.py
│   │   ├── database_manager.py
│   │   └── statistics.py
│   └── workers/           # QThread 워커
├── test/                   # 테스트
│   ├── test_fsm.py
│   ├── test_models.py
│   └── test_statistics.py
├── docs/                   # 문서
├── database/              # Pre-loaded datasets (legacy)
├── data/                  # External data folder
├── logs/                  # 로그 파일
├── requirements.txt       # 프로덕션 의존성
├── requirements-dev.txt   # 개발 의존성
└── setup.py              # 패키지 설정
```

---

## 💻 개발 워크플로우

### 일반적인 개발 사이클

```powershell
# 1. 기능 브랜치 생성
git checkout -b feature/new-feature

# 2. 코드 수정
code src/gui/main_window.py

# 3. 실행 및 테스트
python src\main.py

# 4. 테스트 작성
code test/test_new_feature.py
pytest test/test_new_feature.py -v

# 5. 코드 스타일 검사
flake8 src/
black src/ --check

# 6. 커밋
git add .
git commit -m "feat: Add new feature"

# 7. 푸시 및 PR
git push origin feature/new-feature
```

### 개발 도구

**필수**:
- Python 3.9+ (3.10+ 권장)
- Git
- 코드 에디터 (VS Code 권장)

**권장**:
- pytest (테스팅)
- flake8 (린팅)
- black (포매팅)
- mypy (타입 체킹)

---

## 🧩 아키텍처 패턴

### MVP (Model-View-Presenter)

```
┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│    Model    │ ←─────→ │  Presenter  │ ←─────→ │    View     │
│ (데이터 모델) │         │ (비즈니스 로직)│         │  (PyQt GUI)  │
└─────────────┘         └─────────────┘         └─────────────┘
```

- **Model**: `src/models/` - 데이터 구조
- **View**: `src/gui/` - PyQt6 GUI
- **Presenter**: `src/presenters/` - 로직 조정

### FSM (Finite State Machine)

상태 관리:
- **12개 상태**: INITIAL, LOADED, FILTERED 등
- **18개 이벤트**: LOAD_DATA, APPLY_FILTER 등
- **상태 전환**: 명시적이고 예측 가능

자세한 내용: [FSM 다이어그램](../FSM_DIAGRAM.md)

### Async Processing

QThread 기반:
- 무거운 작업은 워커 스레드에서 실행
- GUI 프리징 방지
- 진행률 업데이트

예시: `src/gui/workers.py`

---

## 🧪 테스팅

### 테스트 실행

```powershell
# 모든 테스트
pytest test/ -v

# 특정 파일
pytest test/test_fsm.py -v

# 커버리지
pytest test/ --cov=src --cov-report=html
```

### 테스트 작성

```python
# test/test_example.py
import pytest
from src.utils.database_manager import DatabaseManager

class TestDatabaseManager:
    @pytest.fixture
    def db_manager(self):
        manager = DatabaseManager()
        yield manager
        manager.close()
    
    def test_load_datasets(self, db_manager):
        datasets = db_manager.get_all_datasets()
        assert isinstance(datasets, list)
```

---

## 🎨 코드 스타일

### PEP 8 준수

```powershell
# 스타일 검사
flake8 src/ --max-line-length=120

# 자동 포매팅
black src/ --line-length=100
```

### Docstring

```python
def process_data(data: List[Dict], threshold: float = 0.05) -> Optional[pd.DataFrame]:
    """
    데이터 처리 함수
    
    Args:
        data: 입력 데이터 리스트
        threshold: 필터링 임계값
    
    Returns:
        처리된 DataFrame 또는 None
    
    Raises:
        ValueError: data가 비어있을 때
    """
    if not data:
        raise ValueError("Data cannot be empty")
    return pd.DataFrame(data)
```

---

## 🔧 디버깅

### VS Code 디버거

**launch.json 설정**:
```json
{
    "name": "Python: RNA-Seq Analyzer",
    "type": "debugpy",
    "request": "launch",
    "program": "${workspaceFolder}/src/main.py",
    "console": "integratedTerminal"
}
```

**사용법**:
1. Breakpoint 설정 (라인 클릭)
2. F5 (디버그 시작)
3. 변수 확인, 단계별 실행

### 로깅

```python
from core.logger import get_logger

logger = get_logger(__name__)

logger.debug("디버그 메시지")
logger.info("정보 메시지")
logger.warning("경고 메시지")
logger.error("오류 메시지")
```

로그 파일: `logs/rna_seq_YYYYMMDD_HHMMSS.log`

---

## 📦 의존성 관리

### requirements.txt

**프로덕션 의존성**:
```
PyQt6>=6.10.0
pandas>=3.0.0
numpy>=2.4.0
matplotlib>=3.7.0
scipy>=1.11.0
```

### requirements-dev.txt

**개발 의존성**:
```
pytest>=7.0.0
pytest-cov>=4.0.0
flake8>=6.0.0
black>=23.0.0
mypy>=1.0.0
```

### 패키지 추가

```powershell
# 프로덕션 패키지
pip install new-package
pip freeze | grep new-package >> requirements.txt

# 개발 패키지
pip install dev-package
echo "dev-package>=1.0.0" >> requirements-dev.txt
```

---

## 🤝 기여 가이드

### Pull Request 프로세스

1. **Fork & Clone**
2. **Feature Branch** 생성
3. **코드 작성** 및 테스트
4. **커밋** (Conventional Commits)
5. **Push** 및 **PR 생성**
6. **코드 리뷰** 대응
7. **Merge**

자세한 내용: [기여 가이드](contributing.md) (작성 예정)

### Commit 메시지 규칙

**Conventional Commits**:
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Type**:
- `feat`: 새 기능
- `fix`: 버그 수정
- `docs`: 문서 변경
- `style`: 코드 포맷팅
- `refactor`: 리팩토링
- `test`: 테스트 추가/수정
- `chore`: 빌드, 설정 등

**예시**:
```
feat(database): add external data folder support

- Implement DataPathConfig for multi-path database
- Add data/ directory with priority over database/
- Update Database Browser with refresh button

Closes #123
```

---

## 🔗 유용한 리소스

### 공식 문서
- [Python](https://docs.python.org/3/)
- [PyQt6](https://www.riverbankcomputing.com/static/Docs/PyQt6/)
- [pandas](https://pandas.pydata.org/docs/)
- [matplotlib](https://matplotlib.org/stable/)

### 커뮤니티
- [GitHub Discussions](https://github.com/ibs-CMG-NGS/cmg-seqviewer/discussions)
- [Issues](https://github.com/ibs-CMG-NGS/cmg-seqviewer/issues)

### 관련 프로젝트
- [ClueGO](http://www.ici.upmc.fr/cluego/) - GO clustering inspiration
- [Enrichr](https://maayanlab.cloud/Enrichr/) - Enrichment analysis

---

## 📝 작성 예정 문서

- [ ] architecture.md - 상세 아키텍처 설명
- [ ] contributing.md - 기여 가이드
- [ ] testing.md - 테스트 작성 가이드
- [ ] api.md - API 레퍼런스
- [ ] performance.md - 성능 최적화 가이드

---

**마지막 업데이트**: 2026-03-01  
**버전**: v1.2.0
