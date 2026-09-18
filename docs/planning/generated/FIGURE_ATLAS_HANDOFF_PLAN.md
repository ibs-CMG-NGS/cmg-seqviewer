# Figure-atlas handoff plan for cmg-seqviewer

## 1. 목적

cmg-seqviewer는 더 이상 논문용 그림의 전체 workflow를 내부에서 모두 처리하는 단일 시스템으로 설계하지 않는다. 대신, cmg-seqviewer는 각 figure에 대해 재현 가능한 결과물 번들(bundle)을 생성하는 producer 역할을 맡고, figure-atlas는 그 번들을 받아 publish, README 생성, verification를 수행하는 downstream pipeline으로 분리한다.

이 구조의 핵심 목표는 다음과 같다.

- cmg-seqviewer는 분석 데이터와 시각화 설정을 기반으로 그림을 생성한다.
- 생성된 그림은 재현 가능한 산출물로 패키징된다.
- figure-atlas는 그 산출물을 표준 방식으로 정리하고 검증한다.
- 두 시스템의 책임이 명확해져 유지보수성과 재현성이 높아진다.

---

## 2. 왜 이 구조가 필요한가

기존의 figure 품질 개선 계획은 cmg-seqviewer 내부에서 스타일, export, 재현성, round-trip 편집까지 모두 담당하는 방향으로 진행되기 쉽다. 그러나 실제로는 다음과 같은 문제가 있다.

- plotting 기능과 publication workflow가 한 시스템 안에 섞여 복잡도가 높아진다.
- 그림 스타일, 레이아웃, 검증, 출판 정리 로직이 서로 얽혀 변경 비용이 커진다.
- 논문 제출 단계에서 필요한 검증·배포·메타데이터 관리가 시각화 코드와 분리되어야 한다.

따라서 figure-atlas로 책임을 분리하면 다음과 같은 장점이 있다.

### 장점

1. 책임 분리
   - cmg-seqviewer: 데이터 처리, plotting, 시각화 설정
   - figure-atlas: 배포, 정리, README, 검증, publish

2. 재현성 향상
   - 그림 생성 스크립트, 데이터, 통계, 메타데이터가 함께 패키징되어 재실행 가능하다.

3. 유지보수성 향상
   - 시각화 로직과 출판/검증 로직이 분리되어 변경 범위가 줄어든다.

4. 협업 확장성
   - 분석팀, 시각화팀, 출판팀이 각각 다른 단계에 집중할 수 있다.

5. 향후 확장 용이성
   - multi-panel assembling, style preset, round-trip editing 같은 기능을 figure-atlas 쪽으로 점진적으로 확장할 수 있다.

---

## 3. 시스템 책임 분리

### cmg-seqviewer의 역할

cmg-seqviewer는 다음을 담당한다.

- 현재 분석 데이터 로딩
- 적절한 visualization 생성
- plot parameters 저장/복원
- 현재 figure에 대한 데이터, 통계, 스타일 정보를 수집
- figure-atlas로 넘길 수 있는 bundle 생성

### figure-atlas의 역할

figure-atlas는 다음을 담당한다.

- bundle를 수집한다.
- publish 구조로 정리한다.
- README를 생성한다.
- 파일 누락 여부와 형식 유효성을 검증한다.
- 필요 시 여러 figure를 묶어 atlas 형태로 배포한다.

---

## 4. 첫 번째 구현 목표

처음부터 전체 시스템을 완성하려 하지 말고, 다음 사항만 먼저 구현한다.

- 하나의 plot에 대해 재현 가능한 bundle를 export할 수 있다.
- 해당 bundle에는 스크립트, 데이터, 이미지, 메타데이터가 포함된다.
- figure-atlas가 그 bundle를 그대로 ingest할 수 있다.

이 단계는 “single-figure bundle export”를 목표로 한다.

---

## 5. figure bundle의 최소 계약

각 figure에 대해 외부 파이프라인이 제출해야 하는 결과물은 다음과 같다.

### 필수 산출물

- 실행 가능한 Python 스크립트
- 데이터 파일
- 통계/요약 테이블 파일
- 최종 이미지 파일
  - .png
  - .pdf
  - .svg
- YAML 메타데이터

### 권장 디렉터리 구조

```text
figure_bundle/
  scripts/
    figure.py
  inputs/
    data.csv
    statistics.csv
  outputs/
    figure.png
    figure.pdf
    figure.svg
  metadata/
    metadata.yaml
```

---

## 6. 메타데이터 스키마

메타데이터 YAML에는 최소한 다음 필드가 들어가야 한다.

- figure_id
- figure_title
- figure_slug
- plot_type
- source_stem
- input_files
- output_files
- statistics_tables
- plot_params
- dataset_name
- claim_boundary
- created_at
- app_version

이 스키마는 figure-atlas가 publish/verify 단계에서 바로 사용할 수 있도록 단순하게 유지한다.

---

## 7. cmg-seqviewer에서 구현할 내용

### 7.1 새 모듈

다음 파일을 추가한다.

- src/utils/figure_bundle_export.py

이 모듈은 bundle 생성의 핵심 엔진이다.

### 7.2 담당 기능

- plot context 수집
- bundle 디렉터리 생성
- 데이터 파일 저장
- 이미지 저장
- YAML 메타데이터 작성
- 재생성용 Python 스크립트 생성
- 생성 결과 검증

### 7.3 함수 형태

예시 인터페이스는 아래와 같다.

```python
export_figure_bundle(context, output_dir, figure_slug, figure_title, plot_type)
```

여기서 context는 다음 정보를 포함하는 dict 또는 dataclass이다.

- figure
- dataframe
- plot_params
- dataset_name
- plot_type
- figure_title
- figure_slug
- source_stem
- notes

---

## 8. UI 연결 방식

### 8.1 공통 plot dialog

공통 기반 클래스인 [src/gui/base_plot_dialog.py](src/gui/base_plot_dialog.py)에 “Export Figure Bundle” 버튼을 추가한다.

이 버튼은 다음 순서로 동작한다.

1. 현재 figure 객체를 읽는다.
2. 현재 plot의 데이터와 파라미터를 수집한다.
3. exporter를 호출한다.
4. 결과 폴더 경로를 사용자에게 알려준다.

### 8.2 visualization widget

[src/gui/visualization_dialog.py](src/gui/visualization_dialog.py) 내 위젯도 bundle context를 제공하는 메서드를 갖도록 한다.

예를 들어 다음과 같은 메서드를 제공한다.

```python
get_bundle_context()
```

이 메서드는 현재 figure, dataframe, plot_params, title 등을 반환한다.

### 8.3 main window

[src/gui/main_window.py](src/gui/main_window.py)에서는 현재 선택된 pinned plot tab 기준으로 bundle export를 수행할 수 있게 한다.

즉, 사용자가 현재 열린 plot에서 바로 “Export Figure Bundle”를 실행할 수 있어야 한다.

---

## 9. project provenance 확장

기존의 [src/utils/project_io.py](src/utils/project_io.py)에는 plot_type과 plot_params가 저장된다. 이 구조를 확장해 bundle 관련 메타데이터를 함께 남기면 이후 재현성 분석이 쉬워진다.

예를 들어 다음과 같은 필드를 추가할 수 있다.

- last_exported_bundle_path
- last_exported_figure_slug
- last_exported_at

이 단계는 필수는 아니지만, 이후 사용자 경험과 추적성 측면에서 매우 유용하다.

---

## 10. 재생성 스크립트 생성 방식

bundle 안의 scripts/figure.py는 bundle가 독립적으로 실행될 수 있도록 작성한다.

이 스크립트는 다음 역할을 한다.

- bundle 내부의 data.csv를 읽는다.
- 저장된 plot_params를 로드한다.
- 동일한 plotting 로직으로 figure를 다시 그린다.
- 동일한 이미지 파일들을 다시 저장한다.

초기 구현에서는 “완전히 독립적인 plotting 함수”를 만드는 대신,
기존 cmg-seqviewer plotting 코드와 저장된 파라미터를 재활용하는 방식으로 충분하다.

---

## 11. 검증 방식

첫 구현에서 가장 중요한 것은 실제로 bundle가 잘 생성되는지 확인하는 것이다.

### 검증 항목

1. bundle 디렉터리가 정상적으로 생성되는가
2. 스크립트, 데이터, 이미지, YAML이 모두 포함되는가
3. 생성된 스크립트를 독립 실행해도 동일한 결과물이 나오나
4. figure-atlas가 해당 디렉터리를 그대로 ingest할 수 있나

### 권장 검증 환경

- headless mode
- Qt offscreen backend
- 대표 plot 하나를 대상으로 먼저 검증

---

## 12. 기술적 난이도

이 구조는 구현 관점에서 비교적 현실적이지만, 몇 가지 난이도 요소가 있다.

### 낮은 난이도

- bundle 디렉터리 생성
- 파일 저장
- YAML 메타데이터 작성
- 기본 image export

이 부분은 비교적 구현이 간단하다.

### 중간 난이도

- 기존 plot dialog와 widget에서 bundle context를 일관되게 추출하는 작업
- plot_params와 dataframe를 bundle에 적절히 직렬화하는 작업
- 재생성 스크립트를 독립 실행 가능하게 만드는 작업

### 높은 난이도

- 모든 plot type에 대해 같은 방식으로 일반화하는 작업
- style preset과 layout까지 포함한 round-trip export
- multi-panel figure assembly

따라서 첫 단계에서는 “대표 plot 하나”에만 집중하는 것이 가장 현실적이다.

---

## 13. 구현 우선순위

### Phase 1: MVP

- 하나의 plot type를 대상으로 export bundle 생성
- 기본 데이터/이미지/메타데이터/스크립트 출력
- UI에서 바로 실행 가능

### Phase 2: 확장

- 여러 plot type로 일반화
- 통계 테이블 자동 수집
- 보다 풍부한 metadata schema

### Phase 3: 고도화

- multi-panel figure assembly
- style preset 적용
- figure-atlas와 자동 연동
- round-trip 재편집 가능성

---

## 14. 기대 효과

이 방식을 도입하면 다음과 같은 효과를 기대할 수 있다.

- 재현 가능한 figure 저장이 가능해진다.
- 논문 제출용 산출물 관리가 쉬워진다.
- 시각화 코드와 출판 workflow가 분리되어 관리가 명확해진다.
- 이후 figure-atlas 확장 시에도 기반 구조를 재사용할 수 있다.
- 분석팀과 출판팀 간 협업이 더 명확해진다.

---

## 15. 권장 결론

cmg-seqviewer는 figure-atlas로 넘어갈 “figure bundle producer”로 설계하는 것이 가장 합리적이다. 첫 단계는 단순하고 실용적인 방식으로 시작하되, 이후 확장 가능성을 열어 두는 것이 중요하다.

즉,

- cmg-seqviewer는 그림을 생성하고 패키징한다.
- figure-atlas는 그 패키지를 정리하고 검증한다.

이 분리는 구현 난이도와 유지보수성 측면 모두에서 균형이 좋다.
