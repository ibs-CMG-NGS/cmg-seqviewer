# fig-atlas-template 가이드

이 저장소는 논문용 그림을 재현 가능하게 만들고, 정리하고, 검증하는 데 초점을 둔 템플릿입니다.

이 패키지는 “그림을 그리는 라이브러리”라기보다, 논문 그림 작업의 관리·배포·검증 체계를 표준화하는 프레임워크에 가깝습니다.

---

## 1. 이 패키지가 해결하려는 문제

논문 그림 작업은 보통 다음 단계로 진행됩니다.

1. 분석 결과를 생성한다.
2. 결과를 바탕으로 그림을 만든다.
3. PNG/PDF/SVG 파일을 저장한다.
4. 논문용으로 정리하고 README를 작성한다.
5. 여러 번 수정하거나 재실행할 때 재현 가능하도록 추적한다.
6. 제출 전 누락된 파일이나 빈 파일이 없는지 점검한다.

이 템플릿은 특히 3~6단계의 관리 작업을 자동화합니다.

---

## 2. 핵심 아이디어

이 패키지는 그림을 세 가지 관점으로 분리합니다.

- 무엇을 그릴지: FigureSpec
- 어떻게 그릴지: 분석 스크립트
- 어디에 정리할지: publish/verify 단계

즉, 그림의 “의미”, “생성 방식”, “출력 형태”를 분리해 관리합니다.

재현성의 핵심은, 패널 단위의 생성 로직과 최종 figure의 조립·스타일링 로직을 분리하는 것입니다.
외부 파이프라인은 패널 수준의 그림을 재현 가능하게 생성하고,
figure-atlas는 그 패널들을 모아 최종 서브패널 레이아웃, 크기, 축 라벨, 범례, 여백 등을 조정해 완성하는 구조가 가장 안정적입니다.

---

## 3. 주요 구성 요소

### 3.1 FigureSpec

FigureSpec는 각 그림의 선언서입니다.

다음 정보를 담습니다.

- 그림 번호
- 제목
- 어떤 분석 코드가 이 그림을 만들었는지
- 패널별 설명
- 통계 테이블 경로
- 이 그림이 말할 수 있는 범위

이 정보는 [fig_atlas/spec.py](fig_atlas/spec.py)에서 정의됩니다.

### 3.2 설정

[config.yaml](config.yaml)에는 프로젝트 전반의 설정이 들어갑니다.

- 그림 수
- 데이터 경로
- 출력 포맷
- 기타 기본 옵션

환경 변수로 경로를 오버라이드할 수 있어, 로컬 머신에 종속되지 않게 관리할 수 있습니다.

### 3.3 분석 스크립트

[analysis](analysis) 폴더에는 실제 그림을 생성하는 코드가 들어갑니다.

이 코드는 데이터 처리, plotting, 파일 저장을 담당합니다.

### 3.4 publish 단계

[publish.py](fig_atlas/publish.py)는 생성된 그림 파일을 정리된 폴더로 복사합니다.

각 그림은 [figures](figures) 아래에 별도 폴더로 배치되며, 그 안에 README도 자동 생성됩니다.

### 3.5 verify 단계

[verify.py](fig_atlas/verify.py)는 그림 폴더, 각 파일, README가 모두 존재하고 비어 있지 않은지 검사합니다.

검사 결과는 [manifests](manifests) 아래 CSV로 저장됩니다.

---

## 4. 실제 사용 흐름

### 4.1 프로젝트 설정

먼저 [config.yaml](config.yaml)에서 그림 수와 경로를 지정합니다.

### 4.2 그림 선언

[figure_specs](figure_specs) 아래에 각 그림의 선언 파일을 추가합니다.

예를 들어 Figure 1, Figure 2를 각각 별도 파일로 선언할 수 있습니다.

### 4.3 분석 코드 작성

[analysis](analysis) 폴더에 실제 그림 생성 스크립트를 작성합니다.

이 스크립트는 데이터 분석 결과를 읽고, 그림 파일을 생성합니다.

### 4.4 publish 실행

[scripts/build_atlas.py](scripts/build_atlas.py)를 실행하면,
선언된 모든 그림이 정리된 atlas 형태로 배포됩니다.

### 4.5 verify 실행

[scripts/verify_atlas.py](scripts/verify_atlas.py)를 실행하면,
결과가 완성되었는지 자동 검사합니다.

---

## 5. 논문 workflow에서 왜 유용한가

이 패키지는 다음 상황에서 특히 유용합니다.

- 논문에 그림이 여러 개일 때
- 같은 그림을 여러 번 수정하고 재생산해야 할 때
- 협업 중 그림 파일과 코드가 분산돼 있을 때
- 제출 전 그림 누락 여부를 확인하고 싶을 때
- 재현 가능한 산출물을 남기고 싶을 때

즉, “그림 하나”보다 “논문 전체 그림 세트”를 관리하는 데 더 적합합니다.

---

## 6. 실제 예시

예를 들어 논문에 Figure 1이 있고, 그 안에 패널 a, b, c가 있다고 가정해 봅니다.

이때는 보통 다음처럼 나누어 생각하면 좋습니다.

- 패널의 의미: FigureSpec
  - a: 주요 결과 요약
  - b: 대조군 비교
  - c: 분포/민감도 확인

- 패널의 배치와 스타일: 분석 스크립트
  - 2열 2행 레이아웃
  - 패널 라벨 위치
  - 축 범위와 색상 설정

즉, 패널이 무엇을 말하는지와, 화면에서 어떻게 배치되는지는 분리해서 관리하는 것이 깔끔합니다.

다음은 a, b, c 패널이 있는 예시입니다.

### FigureSpec 예시

```python
from fig_atlas import FigureSpec

SPEC = FigureSpec(
    number=1,
    slug="example_subpanels",
    title="Example figure with panels a, b, and c",
    source_stem="outputs/figures/figure1_heatmap",
    primary_code="analysis/example_analysis.py",
    panel_notes=[
        "Panel a: overview of condition-level differences.",
        "Panel b: per-sample comparison with one highlighted outlier.",
        "Panel c: summary statistics for the same dataset.",
    ],
)
```

### plotting 코드 예시

```python
import matplotlib.pyplot as plt
import numpy as np

fig, axes = plt.subplots(1, 3, figsize=(12, 3.8))
fig.suptitle("Example figure with panels a, b, and c")

axes[0].plot([0, 1, 2], [1, 2, 1], marker="o")
axes[0].set_title("a")

axes[1].scatter([0.1, 0.4, 0.8], [0.2, 0.5, 0.7])
axes[1].set_title("b")

axes[2].bar([0, 1, 2], [0.3, 0.8, 0.6])
axes[2].set_title("c")

plt.tight_layout()
```

---

## 7. 이 패키지를 어디에 쓰면 좋은가

### 좋은 경우

- 논문 그림을 반복적으로 생성하는 연구 workflow
- 여러 그림을 한 번에 관리해야 하는 프로젝트
- 파이프라인 형태로 그림을 재생산하는 상황
- 재현성 있는 산출물을 남기고 싶은 상황

### 과할 수 있는 경우

- 그림이 1개만 있고, 매우 단순한 작업만 하는 경우
- 이미 잘 정리된 개인 workflow가 있고, 추가 관리 계층이 불필요한 경우

이 경우에는 도구 자체가 다소 무거울 수 있습니다.

---

## 8. 외부 분석 파이프라인과 연결하는 방법

실무적으로는 이 패키지를 다음처럼 쓰는 것이 가장 자연스럽습니다.

### 8.1 외부 파이프라인에서 준비해야 할 계약

분석(+plotting) 스크립트와 입력 데이터가 별도의 파이프라인에 있다면,
그 파이프라인은 이 패키지와 다음 계약을 맞춰야 합니다.

- 입력 데이터는 외부 파이프라인이 읽는다.
- 그림 파일은 `source_stem` 기준으로 생성한다.
  - 예: `outputs/figures/figure1_heatmap.png`
  - 예: `outputs/figures/figure1_heatmap.pdf`
  - 예: `outputs/figures/figure1_heatmap.svg`
- 추가적인 통계 표가 있으면 `supplementary_tables/` 아래로 준비한다.
- `FigureSpec`와 동일한 메타데이터를 외부 파이프라인 문서나 YAML 계약서로 함께 남긴다.

이 패키지에는 그 계약을 시작하기 위한 템플릿이 들어 있습니다.

- [manifests/external_pipeline_contract_template.yaml](manifests/external_pipeline_contract_template.yaml)
- [scripts/prepare_external_pipeline.py](scripts/prepare_external_pipeline.py)

예를 들어 다음처럼 실행하면 계약 파일을 만들 수 있습니다.

```bash
python scripts/prepare_external_pipeline.py --number 1 --slug example_subpanels --title "Example figure with panels a, b, and c"
```

### 8.2 권장 워크플로우

1. 외부 파이프라인이 입력 데이터를 읽는다.
2. 분석 결과를 생성한다.
3. 그림 파일을 `source_stem` 기준으로 저장한다.
4. 필요하면 supplementary table을 생성한다.
5. 이 패키지의 `build_atlas.py`가 그 결과를 publish한다.
6. `verify_atlas.py`가 완료 여부를 확인한다.

이 방식은 “분석 로직”과 “atlas 관리 로직”을 분리해 유지보수성을 높여 줍니다.

### 8.3 왜 이 방식이 좋은가

- 분석 파이프라인은 자신의 책임에만 집중할 수 있다.
- atlas 패키지는 결과물을 수집하고 정리하는 역할만 맡는다.
- 논문용 그림의 재현성 추적이 쉬워진다.
- 나중에 다른 파이프라인으로 교체해도 atlas 계약만 맞추면 된다.

실무적으로는 외부 파이프라인이 생성한 결과물의 경로와 메타데이터를 YAML 또는 JSON으로 남겨 두는 것이 가장 좋습니다.

### 8.4 더 확장된 제안: 결과물 번들(export bundle)

더 깔끔한 방식은, 외부 프로그램이 “그림 생성 결과물 번들”을 한 번에 내보내는 것입니다.

이때 중요한 역할 분리는 다음과 같습니다.

- 외부 파이프라인은 개별 패널(plot) 수준의 산출물을 만든다.
  - 예: 패널 a, 패널 b, 패널 c 각각의 그림 파일 또는 그림 객체
  - 각 패널에 필요한 데이터, 통계, 메타데이터를 함께 제공한다.
- figure-atlas 쪽의 assembly 단계는 그 패널들을 모아 최종 서브패널 구성(예: a/b/c 레이아웃)을 만든다.
  - 즉, “어떤 패널을 어디에 배치할지”는 atlas/assembly 단계에서 관리하는 것이 자연스럽다.
  - 스타일, 레이아웃, 패널 라벨, 제목 배치 같은 것은 이 단계에서 결정하는 것이 좋다.

즉, 외부 파이프라인은 “개별 plot을 생산”하고,
figure-atlas는 “그 Plot들을 조합해서 논문 Figure를 완성”하는 역할로 나누는 것이 가장 깔끔합니다.

이 구조를 적용하면, 외부 파이프라인은 데이터 분석과 패널 단위 시각화에 집중하고,
figure-atlas는 최종 figure assembly, publishing, README/manifest 생성, 검증에 집중할 수 있습니다.

예를 들어 다음과 같은 묶음을 만드는 겁니다.

- `figure.py` 또는 `plotting_script.py`
  - 실제 그림을 만든 코드
- `data.csv` 또는 `statistics.csv`
  - 사용한 원본 데이터나 요약 통계
- `metadata.yaml`
  - 그림 제목, 패널 설명, 데이터 출처, 생성 시간, 소프트웨어 버전 등
- `figure.png`, `figure.pdf`, `figure.svg`
  - 최종 출력 파일

이렇게 하면 이 패키지는 “번들”을 받아서 다음 작업을 수행합니다.

1. 그림 파일을 정리된 atlas 폴더로 복사한다.
2. 메타데이터를 읽어 FigureSpec와 연결한다.
3. README와 manifest를 자동 생성한다.
4. 검증 단계에서 누락 여부와 무결성을 확인한다.

이 구조는 특히 다음 경우에 강합니다.

- 외부 분석 소프트웨어가 별도로 존재할 때
- 여러 팀이 서로 다른 도구로 그림을 생성할 때
- 결과물을 재사용하거나 나중에 다시 재현해야 할 때
- 그림 생성 스크립트와 입력 데이터의 추적성을 높이고 싶을 때

즉, 외부 프로그램은 “그림을 만든다”는 역할만 맡고,
이 패키지는 “그림을 논문용 아틀라스로 정리한다”는 역할만 맡는 형태가 가장 자연스럽습니다.

이 패턴을 구현하려면, 외부 프로그램이 내보내는 번들에 다음 항목이 들어가면 좋습니다.

상세한 전달용 체크리스트는 [manifests/external_pipeline_requirements.md](manifests/external_pipeline_requirements.md)에서 확인할 수 있습니다.

- `script_path`: 생성 스크립트의 상대 경로
- `input_files`: 사용한 데이터 파일 목록
- `output_files`: 생성된 그림 파일 목록
- `metadata`: 패널 설명, claim boundary, 통계 표 경로 등

이 구조를 기준으로 나중에는 `import_bundle()` 같은 단계가 들어가면,
이 패키지는 외부 파이프라인에서 나온 결과물을 자동으로 받아 처리할 수 있습니다.

1. 기존 분석 코드나 plotting 코드는 유지한다.
2. 그림마다 FigureSpec를 추가한다.
3. publish/verify 단계만 이 패키지로 관리한다.
4. 논문 제출 전 atlas 검증을 자동으로 실행한다.

즉, “그림 그리는 로직”은 그대로 두고, “논문용 산출물 관리”만 이 템플릿으로 가져오는 방식이 가장 실용적입니다.

---

## 9. 빠른 시작

다음 순서로 시작하면 됩니다.

```bash
python scripts/build_atlas.py
python scripts/verify_atlas.py
```

또는 Snakemake를 쓰면 더 큰 파이프라인으로 연결할 수 있습니다.

```bash
snakemake --dry-run
snakemake all --cores 4
```

---

## 10. 요약

이 저장소의 핵심 가치는 다음 세 가지입니다.

- 논문 그림을 선언형으로 관리한다.
- 생성/배포/검증 흐름을 표준화한다.
- 재현성 있는 그림 산출물을 유지하기 쉽게 만든다.

즉, 이 패키지는 “그림을 그리는 도구”라기보다 “논문 그림 workflow를 체계화하는 템플릿”입니다.
