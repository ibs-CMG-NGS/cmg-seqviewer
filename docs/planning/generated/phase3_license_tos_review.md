# Enrichment Engine 라이선스/ToS 심사 보고서 (F5 — P3-3)

- Date: 2026-09-03 · Repo: `/home/ygkim/cmg-seqviewer`
- 범위: 신규 엔진이 사용하는 외부 데이터/서비스 — Enrichr(maayanlab.cloud), Enrichr GMT 텍스트 더미,
  NCBI gene2go/gene_info, GO ontology (go-basic.obo), goatools/gseapy/mygene 패키지.

---

## 1. Enrichr 서비스 ToS (maayanlab.cloud/Enrichr)

| 항목 | 평가 |
|---|---|
| 서비스 | 하버드 Ma'ayan Lab 실험 서비스 (Enrichr) — 무료, 계정 불요 |
| 결과 재배포 | 분석 결과(자체 시각화/테이블)는 결과물로서 사용자 소유 — 앱 내 표시/Export는 일반적 활용. **Enrichr 자체 산출물 재배포**는 비권장; 결과 DB 대량 재배포는 서비스 약관 위반 소지 |
| 대량 호출 | Rate-limit 존재 경고 — 엔진은 결과 캐시(동일 입력 재호출 방지) + 재시도 backoff로 준수. UI에 rate-limit 오류 안내 경로(NETWORK) 마련 |
| 상업적 이용 | 연구용 무료 제공이 주류; **상업 배포 시 약관 재확인 필요** (배포 검토 시 사전 심사 항목) |
| 개인정보 | 온라인 모드는 **DEG 심볼만 전송** (배경/표현량 안 보냄) — docs/user에 프라이버시 고지 포함 |

**결론**: 앱 기본 사용(심볼 전송 → 결과 표시/Export)은 허용 범위. 대량/상업적 재배포 필요 시 재심사.

## 2. Enrichr GMT 텍스트 더미 (geneSetLibrary 파일)

| 항목 | 평가 |
|---|---|
| 성격 | Enrichr 서비스가 제공하는 gene-set snapshot (GMT 텍스트) — 라이선스 발간체(NCBI GOA 등) 파생 |
| 재배포 | **GMT 파일 자체를 설치기에 번들 재배포하는 것은 미검토** — v1은 런타임 다운로드(§6.8)로 번들 회피. 번들 옵션(Phase 3 선택) 채택 시 GOA/KEGG 원출처 라이선스 심사 선행 |
| 캐시 | 다운로드 캐시(AppData)는 사용자 기계 국한 — 사용자 개인 캐시이므로 재배포 아님 |
| 갱신 | TTL 90일 자동 갱신 — 스냅샷 최신성 주기 확인 |

**결론**: v1(런타임 다운로드+사용자 캐시)은 재배포 없음 → 허용. 번들 시 선행 심사 요구를 Phase 3에 기록.

## 3. NCBI gene2go / gene_info

| 항목 | 평가 |
|---|---|
| 원출처 | NCBI Gene — 퍼블릭 도메인(US 정부 저작물) / NCBI 이용약관 |
| 재배포 | NCBI 데이터 재배포는 일반적으로 허용이나 **언급·버전 명시 의무** 존재 — 다운로드 매니저가 source URL + sha256 + 획득일을 사이드카로 기록(§6.8) |
| 사용 조건 | 상업·비상업 모두 허용 (출처 표기 요구). 대량 서버 제공 시 NCBI 권고사항 준수 |
| 스냅샷 | gene2go/gene_info는 수시 갱신 — TTL 30일 + 자동 갱신 + sha256 검증으로 재현성 유지 |

**결론**: 허용. 사이드카 메타데이터(출처/해시/일자)가 준수를 입증.

## 4. GO ontology (go-basic.obo)

GO Consortium (GOC) — **CC BY 4.0**. 출처 표기 + 변경 표기 조건. 컨버터/메타데이터에
obo 획득일/출처 기록으로 준수. GOC 라이선스 사본은 캐시 사이드카에 url 포함.

## 5. 오픈소스 패키지

| 패키지 | 라이선스 | 비고 |
|---|---|---|
| gseapy 1.3.1 | BSD-2 | ok |
| goatools 1.6.5 | BSD-3 | ok |
| mygene 3.2.2 | BSD-3 | 에이전트는 사용자 요청 시 원격 서비스 호출 — 서비스 ToS(MyGene.info)는 비상업 연구용 무료, 상업 시 문의 문서화 |
| statsmodels 0.14.6 | BSD-3 | ok |
| requests / PyQt6 / pandas / numpy | Apache-2.0 / GPL3+/BSD/… | 기존 배포 라이선스와 동일 |

## 6. 결론 (F5)

- v1 설계(런타임 다운로드 + 사용자 캐시 + 사이드카 메타)는 **재배포 이슈를 회피**하며 사용은 수용 가능.
- **재배포(번들) 수행 시**: GO(CC BY 4.0 출처 표기), GMT(원출처 재심사), mygene(서비스 약관) 3건 선행 심사 필수.
- **상업 배포 검토 시**: Enrichr ToS 재확인 + 브랜드(출처) 표기 정책 수립.
- 앱 docs(user-guide)에 온라인 전송 데이터(심볼만)와 캐시 위치/TTL 고지 포함됨.