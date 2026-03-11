# CMG-SeqViewer 기여 가이드 (Contributing Guide)

> 🤝 CMG-SeqViewer 프로젝트에 기여하는 방법을 안내합니다

## 목차

1. [환영합니다!](#환영합니다)
2. [기여 방법](#기여-방법)
3. [개발 환경 설정](#개발-환경-설정)
4. [코딩 스타일](#코딩-스타일)
5. [Pull Request 가이드](#pull-request-가이드)
6. [이슈 리포팅](#이슈-리포팅)
7. [커뮤니케이션](#커뮤니케이션)

---

## 환영합니다!

CMG-SeqViewer는 오픈소스 프로젝트이며, 여러분의 기여를 환영합니다!

**기여 가능한 분야**:
- 🐛 버그 수정
- ✨ 새 기능 개발
- 📝 문서 개선
- 🧪 테스트 작성
- 🌐 번역 (한국어/영어)
- 🎨 UI/UX 개선

**기여자 혜택**:
- GitHub Contributors 목록에 이름 표시
- 릴리즈 노트에 감사 인사
- 오픈소스 경력 구축

---

## 기여 방법

### 1. 코드 기여 워크플로우

```
1. Fork 프로젝트
   ↓
2. 로컬에 Clone
   ↓
3. Feature 브랜치 생성
   ↓
4. 코드 작성 및 테스트
   ↓
5. Commit (Conventional Commits)
   ↓
6. Push to Fork
   ↓
7. Pull Request 생성
   ↓
8. Code Review
   ↓
9. Merge (또는 수정 요청)
```

### 2. 문서 기여

**방법 1: GitHub Web UI**
1. 문서 파일 (`docs/*.md`) 찾기
2. 연필 아이콘 클릭 (Edit this file)
3. Markdown 수정
4. "Propose changes" 버튼
5. 자동으로 Fork + PR 생성

**방법 2: 로컬 편집**
```bash
git clone https://github.com/YOUR_USERNAME/cmg-seqviewer.git
cd cmg-seqviewer
# 문서 수정
git add docs/
git commit -m "docs: update installation guide"
git push origin main
# GitHub에서 PR 생성
```

### 3. 이슈 기여

- 버그 발견 시 이슈 생성
- 기능 제안
- 문서 개선 제안
- 질문 (Discussions 권장)

---

## 개발 환경 설정

### 1. Fork 및 Clone

**GitHub에서 Fork**:
1. https://github.com/ibs-CMG-NGS/cmg-seqviewer
2. 우측 상단 "Fork" 버튼 클릭

**로컬에 Clone**:
```bash
git clone https://github.com/YOUR_USERNAME/cmg-seqviewer.git
cd cmg-seqviewer
```

**Upstream 추가** (원본 저장소):
```bash
git remote add upstream https://github.com/ibs-CMG-NGS/cmg-seqviewer.git
git remote -v
# origin    https://github.com/YOUR_USERNAME/cmg-seqviewer.git (fetch)
# upstream  https://github.com/ibs-CMG-NGS/cmg-seqviewer.git (fetch)
```

### 2. 가상환경 및 의존성

**Windows (PowerShell)**:
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -r requirements-dev.txt  # 개발 의존성
```

**macOS/Linux**:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

**개발 의존성** (`requirements-dev.txt`):
```
pytest>=7.0.0
pytest-qt>=4.0.0
pytest-cov>=4.0.0
flake8>=6.0.0
black>=23.0.0
mypy>=1.0.0
sphinx>=5.0.0  # 문서 빌드
```

### 3. Editable Install

```bash
pip install -e .
```

**효과**:
- `src/` 수정 시 즉시 반영
- 재설치 불필요
- 개발 편의성 향상

### 4. VS Code 설정

**`.vscode/settings.json`**:
```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "python.testing.pytestEnabled": true,
  "python.testing.unittestEnabled": false
}
```

---

## 코딩 스타일

### 1. Python 스타일 가이드

**기본**: [PEP 8](https://peps.python.org/pep-0008/)

**핵심 규칙**:

**Indentation**: 4 spaces (탭 아님)
```python
def my_function():
    if condition:
        do_something()
```

**Line Length**: 최대 100자 (PEP 8: 79, 우리는 100)
```python
# Good
result = some_function(
    argument1, argument2, argument3
)

# Bad (너무 긴 줄)
result = some_function(argument1, argument2, argument3, argument4, argument5, argument6)
```

**Naming Conventions**:
```python
# Classes: PascalCase
class DatasetModel:
    pass

# Functions/Variables: snake_case
def apply_filter(adj_p_value, log2fc_threshold):
    filtered_data = ...

# Constants: UPPER_CASE
MAX_DATASETS = 5
DEFAULT_THRESHOLD = 0.05

# Private: _leading_underscore
def _internal_helper():
    pass
```

**Imports**:
```python
# 1. 표준 라이브러리
import os
import sys
from pathlib import Path

# 2. 서드파티
import pandas as pd
import numpy as np
from PyQt6.QtWidgets import QWidget

# 3. 로컬 모듈
from src.models.dataset_model import DatasetModel
from src.utils.validators import validate_dataframe
```

**Docstrings**: Google Style
```python
def apply_filter(df: pd.DataFrame, threshold: float, direction: str) -> pd.DataFrame:
    """
    Apply filtering to differential expression data.
    
    Args:
        df: Input dataframe with DE results
        threshold: Adjusted p-value threshold (e.g., 0.05)
        direction: Regulation direction ("up", "down", or "both")
    
    Returns:
        Filtered dataframe
    
    Raises:
        ValueError: If direction is invalid
    
    Example:
        >>> df_filtered = apply_filter(df, 0.05, "both")
    """
    if direction not in ["up", "down", "both"]:
        raise ValueError(f"Invalid direction: {direction}")
    
    # 필터링 로직
    ...
    return df_filtered
```

**Type Hints** (권장):
```python
from typing import List, Dict, Optional, Tuple

def get_gene_list(df: pd.DataFrame, column: str) -> List[str]:
    """Extract gene list from dataframe"""
    return df[column].tolist()

def find_dataset(name: str) -> Optional[DatasetModel]:
    """Find dataset by name (may return None)"""
    return self.datasets.get(name)

def parse_config(file_path: str) -> Dict[str, any]:
    """Parse configuration file"""
    ...
```

### 2. Code Formatting

**Black** (자동 포맷터):
```bash
# 전체 프로젝트
black src/

# 특정 파일
black src/models/dataset_model.py

# 확인 (실제 수정 안함)
black --check src/
```

**flake8** (린터):
```bash
# 전체 프로젝트
flake8 src/

# 설정 (.flake8)
[flake8]
max-line-length = 100
exclude = .git,__pycache__,venv
ignore = E203,W503  # Black과 충돌하는 규칙 무시
```

**mypy** (타입 체커):
```bash
mypy src/
```

### 3. Commit 메시지

**Conventional Commits** 사용:

**형식**:
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Type**:
- `feat`: 새 기능
- `fix`: 버그 수정
- `docs`: 문서 변경
- `style`: 코드 스타일 (포맷팅, 세미콜론 등)
- `refactor`: 리팩토링 (기능 변경 없음)
- `test`: 테스트 추가/수정
- `chore`: 빌드, 설정 등

**Scope** (선택사항):
- `core`: 핵심 로직
- `gui`: GUI 컴포넌트
- `models`: 데이터 모델
- `utils`: 유틸리티
- `docs`: 문서

**예시**:
```bash
# 간단한 버그 수정
git commit -m "fix(gui): resolve volcano plot color mapping issue"

# 새 기능 (상세 설명)
git commit -m "feat(analysis): add hypergeometric test for gene enrichment

Implemented hypergeometric test in utils/statistics.py.
Added corresponding UI in analysis menu.
Updated tests in test/test_statistics.py.

Closes #42"

# 문서 업데이트
git commit -m "docs: update installation guide for macOS Sonoma"

# 리팩토링
git commit -m "refactor(models): extract filtering logic to separate class"
```

**Rules**:
- Subject는 명령형 (Add, Fix, Update)
- Subject는 소문자로 시작
- Subject 끝에 마침표 없음
- 50자 이내 (Subject)
- Body는 72자마다 줄바꿈
- Why/What을 설명 (How는 코드에서)

---

## Pull Request 가이드

### 1. 브랜치 전략

**브랜치 이름**:
```
<type>/<short-description>

예시:
feature/add-gsea-analysis
fix/volcano-plot-crash
docs/update-contributing-guide
refactor/cleanup-filter-logic
```

**생성**:
```bash
git checkout -b feature/add-hypergeometric-test
```

### 2. PR 생성 전 체크리스트

**코드**:
- [ ] 모든 테스트 통과 (`pytest`)
- [ ] 새 기능에 테스트 추가
- [ ] Linting 통과 (`flake8`)
- [ ] Formatting 적용 (`black`)
- [ ] Type hints 추가 (가능한 경우)

**문서**:
- [ ] Docstring 작성/업데이트
- [ ] README 업데이트 (필요시)
- [ ] CHANGELOG.md 업데이트 (Unreleased 섹션)

**Git**:
- [ ] Conventional Commits 형식
- [ ] 논리적인 커밋 단위
- [ ] 최신 main 브랜치 반영 (`git rebase`)

### 3. PR 템플릿

**제목**:
```
feat(analysis): Add hypergeometric test for gene set enrichment
```

**설명**:
```markdown
## 변경 사항

Hypergeometric test를 통한 gene set enrichment 분석 기능 추가

## 구현 내용

- `src/utils/statistics.py`에 `hypergeometric_test()` 함수 추가
- `src/gui/hypergeometric_dialog.py`에 UI 다이얼로그 추가
- Analysis 메뉴에 "Hypergeometric Test" 항목 추가
- `test/test_statistics.py`에 단위 테스트 추가

## 테스트

- [x] 단위 테스트 통과
- [x] 수동 테스트 완료 (Sample data)
- [x] Edge cases 검증 (빈 리스트, 중복 등)

## 스크린샷

(UI 변경 시 스크린샷 첨부)

## 관련 이슈

Closes #42
Relates to #38

## 체크리스트

- [x] PEP 8 준수
- [x] Docstring 작성
- [x] CHANGELOG.md 업데이트
- [x] 테스트 추가
- [x] 로컬에서 테스트 통과
```

### 4. Code Review 프로세스

**Reviewer 역할**:
1. 코드 품질 확인
2. 테스트 커버리지 확인
3. 문서화 확인
4. 버그 가능성 검토
5. 아키텍처 적합성 검토

**Contributor 역할**:
1. 피드백에 대응
2. 요청된 수정사항 반영
3. 토론 참여

**Approval 기준**:
- 최소 1명의 Maintainer 승인
- CI 테스트 통과
- 충돌 해결

### 5. Merge 후

**Fork 동기화**:
```bash
# Upstream 최신 변경사항 가져오기
git checkout main
git fetch upstream
git merge upstream/main

# Fork에 Push
git push origin main
```

**브랜치 정리**:
```bash
# 로컬 브랜치 삭제
git branch -d feature/my-feature

# 원격 브랜치 삭제
git push origin --delete feature/my-feature
```

---

## 이슈 리포팅

### 1. 버그 리포트

**제목**:
```
[Bug] Volcano plot crashes on datasets with missing adj.p values
```

**템플릿**:
```markdown
## 버그 설명

Volcano plot 생성 시 adj.p.value 컬럼에 NaN이 있으면 프로그램이 크래시합니다.

## 재현 방법

1. 데이터셋 로드 (adj.p.value에 NaN 포함)
2. Visualization → Volcano Plot
3. Generate 버튼 클릭
4. 오류 발생

## 예상 동작

NaN 값을 자동으로 필터링하거나 경고 메시지 표시

## 실제 동작

```
TypeError: unsupported operand type(s) for -: 'str' and 'float'
```

## 환경

- OS: Windows 11
- Python: 3.11.5
- CMG-SeqViewer: v1.2.0
- PyQt6: 6.6.1

## 추가 정보

- 샘플 데이터: (첨부 또는 링크)
- 로그 파일: (첨부)
```

### 2. 기능 제안

**제목**:
```
[Feature] Add support for multi-sample heatmap
```

**템플릿**:
```markdown
## 기능 설명

현재 Heatmap은 단일 컬럼(log2FC)만 지원하지만, 여러 샘플의 발현 값을 동시에 표시할 수 있으면 좋겠습니다.

## 사용 사례

RNA-seq 데이터에 여러 샘플(Sample1, Sample2, ...)의 normalized count가 있을 때:
1. 유전자를 행으로
2. 샘플을 열으로
3. 발현 수준을 색상으로 표시

## 제안하는 구현

- Heatmap 다이얼로그에 "Multi-column mode" 체크박스
- 컬럼 다중 선택 UI (QListWidget)
- seaborn.clustermap 사용

## 대안

- 현재: Excel에서 수동으로 heatmap 생성
- 단점: 클러스터링 안됨, 번거로움

## 우선순위

Medium - 자주 필요하지는 않지만 유용함
```

### 3. 문서 이슈

**예시**:
```markdown
## 문제

Installation guide에 macOS Sonoma (14.0+)에서 Gatekeeper 우회 방법이 업데이트 필요합니다.

## 제안

현재 문서: "시스템 환경설정 → 보안 및 개인 정보 보호 → 확인 없이 열기"

macOS Sonoma: "시스템 설정 → 개인 정보 보호 및 보안 → 보안 → App 관리"

## 위치

`docs/user/installation.md`, line 42
```

---

## 커뮤니케이션

### 1. GitHub Discussions

**사용 용도**:
- 일반 질문 (Q&A)
- 아이디어 토론
- 사용 사례 공유
- 커뮤니티 교류

**카테고리**:
- **Q&A**: 사용법 질문
- **Ideas**: 기능 제안 토론
- **Show and tell**: 성과 공유
- **General**: 일반 토론

**URL**: https://github.com/ibs-CMG-NGS/cmg-seqviewer/discussions

### 2. 이슈 vs Discussions

**이슈 (Issues)**:
- 버그 리포트
- 확정된 기능 요청
- 문서 수정 요청
- 작업 추적

**Discussions**:
- "이런 기능이 가능한가요?"
- "어떻게 하는지 모르겠어요"
- "이런 방식은 어떨까요?"

### 3. 코드 리뷰 에티켓

**Reviewer**:
- ✅ 건설적인 피드백
- ✅ 구체적인 제안
- ✅ 칭찬도 함께
- ❌ 비난 금지
- ❌ "왜 이렇게 했어?" (대신: "이유를 알려주시겠어요?")

**Contributor**:
- ✅ 피드백에 감사
- ✅ 불분명한 점 질문
- ✅ 토론 참여
- ❌ 방어적 태도 금지

---

## 라이선스

CMG-SeqViewer에 기여하시면 [MIT License](../LICENSE)에 동의하신 것으로 간주됩니다.

---

## 감사합니다!

여러분의 기여가 CMG-SeqViewer를 더 나은 도구로 만듭니다. 🎉

**도움이 필요하신가요?**
- [GitHub Discussions](https://github.com/ibs-CMG-NGS/cmg-seqviewer/discussions)
- [Email](mailto:cmg-seqviewer@example.com) (작성 예정)

---

**마지막 업데이트**: 2026-03-01  
**버전**: v1.2.0
