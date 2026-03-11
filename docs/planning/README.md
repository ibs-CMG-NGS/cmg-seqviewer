# 기획 문서 (Planning Documentation)

> 📋 CMG-SeqViewer의 미래 계획 및 로드맵

## 📚 문서 목록

| 문서 | 설명 | 상태 | 우선순위 |
|------|------|------|---------|
| [ATAC-seq 통합 계획](ATAC_SEQ_INTEGRATION_PLAN.md) | 멀티오믹스 통합 로드맵 | ✅ 완료 | 높음 |

---

## 🎯 현재 기획

### ATAC-seq 통합 (v2.0.0)

**목표**: RNA-seq + ATAC-seq 멀티오믹스 분석 플랫폼

**Phase 1: ATAC-seq Standalone** (1주)
- ATAC-seq 데이터 전용 탭 인터페이스
- Peak 필터링 (FDR, fold change, distance to TSS)
- Peak 시각화 (Volcano, Genomic distribution, Heatmap)

**Phase 2: Multi-omics Integration** (1주)
- RNA-seq + ATAC-seq 동시 로드
- 유전자-Peak 연결 (nearest, promoter, enhancer)
- 통합 시각화 (Scatter, Quadrant, Integrated heatmap)

**상세 계획**: [ATAC-seq 통합 계획](ATAC_SEQ_INTEGRATION_PLAN.md)

---

## 🗺️ 로드맵

### v1.2.0 (현재) - External Data Folder
- ✅ 외부 데이터 폴더 지원
- ✅ Gene/GO/KEGG 컨텍스트 메뉴
- ✅ 데이터베이스 새로고침 기능

### v1.3.0 (계획) - UI/UX 개선
- [ ] 다크 모드 지원
- [ ] 사용자 설정 저장 (필터 프리셋, 색상 테마)
- [ ] 드래그 앤 드롭 개선
- [ ] Recent files 확장 (10 → 20)

### v1.4.0 (계획) - 고급 통계
- [ ] DESeq2 결과 직접 임포트
- [ ] EdgeR 결과 지원
- [ ] Batch effect correction
- [ ] PCA/t-SNE visualization

### v2.0.0 (장기) - Multi-omics
- [ ] ATAC-seq 통합 (Phase 1, 2)
- [ ] ChIP-seq 지원 (Phase 3)
- [ ] Hi-C 데이터 통합 (Phase 4)
- [ ] 멀티오믹스 네트워크

---

## 💡 아이디어 백로그

### 사용자 요청 기능
| 기능 | 설명 | 투표 | 우선순위 |
|------|------|------|---------|
| 플러그인 시스템 | 사용자 정의 분석 모듈 | 5 | 중 |
| 클라우드 저장소 | Google Drive, Dropbox 연동 | 3 | 낮음 |
| 협업 기능 | 공유 링크, 주석 기능 | 2 | 낮음 |
| R 통합 | R 스크립트 실행 | 8 | 높음 |

### 기술 개선
| 개선사항 | 설명 | 상태 |
|---------|------|------|
| 성능 최적화 | 대용량 데이터 처리 (100만 행+) | 검토 중 |
| 메모리 최적화 | Lazy loading, 청크 처리 | 계획 |
| GPU 가속 | CUDA 기반 통계 계산 | 아이디어 |

---

## 📊 우선순위 매트릭스

```
높은 가치 │ v1.3.0 UI/UX    │ v2.0.0 ATAC-seq
         │                │
         │ 플러그인 시스템   │ R 통합
─────────┼─────────────────┼──────────────────
낮은 가치 │ 클라우드 저장소  │ GPU 가속
         │                │
         └────────────────┴──────────────────
          낮은 노력        높은 노력
```

**우선순위**:
1. **v2.0.0 ATAC-seq** (높은 가치, 높은 노력) - 전략적 중요성
2. **v1.3.0 UI/UX** (높은 가치, 낮은 노력) - 빠른 개선
3. **R 통합** (높은 가치, 높은 노력) - 사용자 요청 많음

---

## 🎨 디자인 문서

### UI/UX 개선안 (v1.3.0)

**다크 모드**:
- 배경: #1e1e1e
- 텍스트: #e0e0e0
- 강조: #007acc
- 토글: Settings → Appearance → Dark Mode

**필터 프리셋**:
```python
# 사용자 정의 프리셋 저장
presets = {
    "Significant": {"padj": 0.05, "log2fc": 1},
    "Highly DE": {"padj": 0.01, "log2fc": 2},
    "Custom": {"padj": 0.1, "log2fc": 0.5}
}
```

**색상 테마**:
- Default (현재)
- Colorblind-friendly
- High contrast
- Custom (사용자 정의)

### 데이터 모델 확장 (v2.0.0)

**ATAC-seq Peak**:
```python
@dataclass
class ATACPeak:
    chromosome: str
    start: int
    end: int
    peak_id: str
    score: float
    fold_change: float
    fdr: float
    nearest_gene: str
    distance_to_tss: int
    peak_type: str  # promoter, enhancer, intergenic
```

**Multi-omics Link**:
```python
@dataclass
class MultiOmicsLink:
    rna_gene: str
    atac_peak: str
    correlation: float
    p_value: float
    link_type: str  # nearest, promoter, enhancer
```

---

## 📅 릴리스 일정

### 2026년 계획

| 분기 | 버전 | 주요 기능 | 예상 릴리스 |
|-----|------|---------|-----------|
| Q1 | v1.2.0 | External data folder | ✅ 2026-03-01 |
| Q1 | v1.2.1 | Bug fixes | 2026-03-15 |
| Q2 | v1.3.0 | UI/UX 개선 | 2026-04-30 |
| Q2 | v1.4.0 | 고급 통계 | 2026-06-30 |
| Q3-Q4 | v2.0.0 | ATAC-seq 통합 | 2026-09-30 |

---

## 🤝 커뮤니티 피드백

### 피드백 수집 방법
1. **GitHub Issues**: 버그 리포트, 기능 요청
2. **GitHub Discussions**: 일반 논의
3. **사용자 설문조사**: 분기별 (작성 예정)

### 주요 피드백 (예시)
- ✅ "외부 데이터 폴더 필요" → v1.2.0에 구현
- 🔄 "다크 모드 지원" → v1.3.0 계획
- 📋 "ATAC-seq 분석 필요" → v2.0.0 계획

---

## 📝 작성 예정 문서

- [ ] v1.3.0-ui-ux-design.md - UI/UX 디자인 상세
- [ ] v1.4.0-statistics-spec.md - 통계 기능 스펙
- [ ] plugin-system-design.md - 플러그인 아키텍처
- [ ] r-integration-design.md - R 통합 설계

---

## 🔗 관련 문서

- [ATAC-seq 통합 계획](ATAC_SEQ_INTEGRATION_PLAN.md) - 상세 로드맵
- [아키텍처](../developer/architecture.md) - 현재 시스템 구조 (작성 예정)
- [CHANGELOG](../archive/CHANGELOG.md) - 과거 변경사항

---

**마지막 업데이트**: 2026-03-01  
**담당**: 기획팀
