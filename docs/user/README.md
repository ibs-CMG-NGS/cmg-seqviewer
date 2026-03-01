# 사용자 가이드 (User Documentation)

> 📘 CMG-SeqViewer의 설치, 사용법, 문제 해결 가이드

## 📚 문서 목록

### 시작하기
| 문서 | 설명 | 난이도 |
|------|------|--------|
| [설치 가이드](installation.md) | Windows/macOS 설치 및 첫 실행 | ⭐ 기초 |
| [빠른 시작](quick-start.md) | 5분 만에 첫 분석 완료 | ⭐ 기초 |

### 기능 사용법
| 문서 | 설명 | 난이도 |
|------|------|--------|
| [사용자 매뉴얼](user-guide.md) | 전체 기능 상세 설명 | ⭐⭐ 중급 |
| [컬럼 매핑 가이드](COLUMN_MAPPING_GUIDE.md) | Excel 데이터 임포트 | ⭐ 기초 |

### 문제 해결
| 문서 | 설명 | 난이도 |
|------|------|--------|
| [FAQ](faq.md) | 자주 묻는 질문 | ⭐ 기초 |
| [문제 해결](troubleshooting.md) | 일반적인 문제 및 해결책 | ⭐⭐ 중급 |

---

## 🚀 빠른 탐색

### 처음 사용하시나요?

**단계별 가이드**:
1. [시스템 요구사항 확인](installation.md#시스템-요구사항)
2. [프로그램 설치](installation.md#설치-방법)
3. [첫 실행 및 확인](installation.md#첫-실행)
4. [빠른 시작 튜토리얼](quick-start.md) (작성 예정)

### 데이터 분석하기

**RNA-Seq 분석**:
1. Excel 파일 준비 (컬럼: gene_id, log2FC, adj.p.value)
2. File → Import Dataset
3. Filter Panel에서 필터 설정 (예: adj.p < 0.05, |log2FC| > 1)
4. Visualization → Volcano Plot

**GO/KEGG 분석**:
1. GO/KEGG 결과 Excel 파일 준비
2. File → Import Dataset (Data Type: GO/KEGG)
3. GO/KEGG → Clustering (Jaccard 또는 Kappa)
4. GO/KEGG → Network Visualization

자세한 내용: [사용자 매뉴얼](user-guide.md) (작성 예정)

### 문제가 있나요?

**설치 문제**:
- Windows: [설치 가이드 - Windows 문제](installation.md#windows-문제)
- macOS: [설치 가이드 - macOS 문제](installation.md#macos-문제)

**사용 중 문제**:
- [FAQ](faq.md) 확인 (작성 예정)
- [문제 해결 가이드](troubleshooting.md) (작성 예정)
- [GitHub Issues](https://github.com/ibs-CMG-NGS/cmg-seqviewer/issues)

---

## 📖 주요 기능 가이드

### 데이터 관리
- **데이터 임포트**: [컬럼 매핑 가이드](COLUMN_MAPPING_GUIDE.md)
- **데이터셋 관리**: [사용자 매뉴얼 - 데이터셋 관리](user-guide.md#데이터셋-관리) (작성 예정)
- **외부 데이터 폴더** (v1.2.0+): [설치 가이드 - 외부 데이터](installation.md) (작성 예정)

### 필터링
- **기본 필터**: adj.p-value, log2FC 임계값
- **방향 필터**: Up, Down, Both
- **유전자 리스트**: 특정 유전자만 필터링

### 시각화
- **Volcano Plot**: 전체 DE 결과 시각화
- **Heatmap**: 발현 패턴 클러스터링
- **Venn Diagram**: 데이터셋 간 교집합
- **GO/KEGG 시각화**: Dot Plot, Bar Chart, Network

### 통계 분석
- **Fisher's Exact Test**: 유전자 리스트 enrichment
- **GSEA Lite**: Gene set enrichment
- **Multi-dataset Comparison**: 2-5 데이터셋 비교

### 내보내기
- **Excel**: .xlsx 형식
- **CSV/TSV**: 텍스트 형식
- **이미지**: PNG, SVG (시각화)

---

## 💡 팁과 트릭

### 효율적인 워크플로우

**1. 필터 프리셋 활용**:
- 자주 사용하는 필터 조합 저장 (작성 예정)
- 빠른 필터 전환

**2. 바로가기 키**:
- `Ctrl+O`: 파일 열기
- `Ctrl+S`: 내보내기
- `F1`: 도움말
- `Ctrl+W`: 탭 닫기

**3. 데이터셋 재명명**:
- Dataset Manager에서 더블클릭
- 모든 탭에서 자동 업데이트

**4. 외부 데이터 폴더** (v1.2.0+):
- 실행 파일 옆 `data/` 폴더 사용
- 배포 후 데이터 추가 가능
- Database Browser → Open Data Folder

### 대용량 데이터 처리

**메모리 절약**:
- 필터링 먼저 적용
- 불필요한 탭 닫기
- 데이터 분할 (10만 행 이하 권장)

**성능 향상**:
- SSD에 데이터 저장
- 백그라운드 프로그램 최소화
- RAM 8GB 이상 권장

---

## 🎓 튜토리얼 (작성 예정)

### 초급
1. **첫 분석**: 샘플 데이터로 Volcano Plot 그리기
2. **필터링**: adj.p < 0.05, |log2FC| > 1 유전자 찾기
3. **내보내기**: 결과를 Excel로 저장

### 중급
1. **Heatmap**: 클러스터링과 색상 조정
2. **Venn Diagram**: 3개 데이터셋 교집합 분석
3. **GO Clustering**: Jaccard similarity로 GO 그룹화

### 고급
1. **Multi-dataset Comparison**: 5개 데이터셋 통계 비교
2. **Custom Gene Set**: 사용자 정의 유전자 세트로 GSEA
3. **Batch Processing**: 여러 파일 자동 분석 (작성 예정)

---

## 🔗 관련 문서

### 개발자용
- [개발 환경 설정](../developer/setup.md)
- [프로젝트 아키텍처](../developer/architecture.md) (작성 예정)

### 배포 담당자용
- [빌드 가이드](../deployment/build-guide.md)
- [배포 가이드](../deployment/deployment.md)

### 기타
- [CHANGELOG](../archive/CHANGELOG.md) - 버전별 변경사항
- [GitHub Repository](https://github.com/ibs-CMG-NGS/cmg-seqviewer)

---

## 📞 지원

### 도움이 필요하신가요?

**순서대로 시도하세요**:
1. [FAQ](faq.md) 확인 (작성 예정)
2. [문제 해결 가이드](troubleshooting.md) 확인 (작성 예정)
3. [GitHub Issues](https://github.com/ibs-CMG-NGS/cmg-seqviewer/issues) 검색
4. 새 Issue 생성 (로그 파일 첨부)

**Issue 생성 시 포함할 정보**:
- OS 및 버전 (Windows 10, macOS 14.0 등)
- CMG-SeqViewer 버전
- 오류 메시지 (스크린샷)
- 로그 파일 (`logs/` 폴더의 최신 파일)
- 재현 단계

---

**마지막 업데이트**: 2026-03-01  
**버전**: v1.2.0
