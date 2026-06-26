# CMG-SeqViewer - 배포 방식 비교

## 배포 옵션

### Option 1: Portable (현재 구현됨) ⭐ 권장
**파일**: `CMG-SeqViewer_v1.0_Portable.zip`

**장점**:
- ✅ 즉시 실행 (압축 해제만)
- ✅ USB/네트워크 드라이브에서 실행 가능
- ✅ 여러 버전 동시 사용 가능
- ✅ 관리자 권한 불필요
- ✅ 완전 삭제 용이

**단점**:
- ❌ 바로가기 수동 생성
- ❌ 자동 업데이트 없음

**사용 시나리오**:
- 연구실 여러 컴퓨터에서 작업
- 빠른 테스트/프로토타입
- 다양한 버전 비교 필요

---

### Option 2: Installer (선택사항)
**파일**: `CMG-SeqViewer_Setup_v1.0.exe`

**장점**:
- ✅ 전문적인 설치 경험
- ✅ 시작 메뉴/바탕화면 자동 등록
- ✅ 프로그램 목록에 표시
- ✅ 자동 업데이트 구현 가능

**단점**:
- ❌ 설치 시간 소요
- ❌ 관리자 권한 필요
- ❌ 이동 불가 (USB에서 실행 안됨)

**사용 시나리오**:
- 최종 사용자 배포 (연구실 외부)
- 정식 릴리스
- 대규모 조직 배포

---

## 추천 전략: Dual Distribution

### 1단계: Portable 버전 (빠른 배포)
```powershell
# 현재 방식
.\build.ps1
Compress-Archive -Path "dist\CMG-SeqViewer" -DestinationPath "CMG-SeqViewer_v1.0_Portable.zip"
```

### 2단계: Installer (정식 릴리스)
```powershell
# Inno Setup 설치 필요
# https://jrsoftware.org/isdl.php

# Installer 빌드
iscc installer.iss

# 결과물: installer_output\CMG-SeqViewer_Setup_1.0.0.exe
```

---

## Installer 제작 방법

### 필요 도구
- **Inno Setup**: https://jrsoftware.org/isdl.php (무료)
- 또는 **NSIS**: https://nsis.sourceforge.io/ (무료)
- 또는 **Advanced Installer**: https://www.advancedinstaller.com/ (유료/무료)

### 단계별 가이드

#### 1. Inno Setup 설치
```powershell
# Chocolatey 사용 (옵션)
choco install innosetup

# 또는 수동 다운로드
# https://jrsoftware.org/isdl.php
```

#### 2. Installer 빌드
```powershell
# installer.iss 파일 편집 (GUID 생성 필요)
# Tools → Generate GUID in Inno Setup

# 빌드
iscc installer.iss

# 결과물: installer_output\CMG-SeqViewer_Setup_1.0.0.exe
```

#### 3. 테스트
```powershell
# 설치 테스트
.\installer_output\CMG-SeqViewer_Setup_1.0.0.exe

# 확인 사항:
# - C:\Program Files\CMG-SeqViewer\ 설치됨
# - 시작 메뉴에 등록
# - 바탕화면 바로가기 (옵션)
# - 제어판 > 프로그램 추가/제거에 표시
```

---

## 디지털 서명 (선택사항)

백신 경고를 줄이려면 코드 서명 인증서 필요:

### 비용
- **개인**: $75-150/년 (Comodo, Sectigo)
- **조직**: $200-400/년
- **EV 서명**: $300-500/년 (즉시 SmartScreen 통과)

### 서명 방법
```powershell
# SignTool.exe (Windows SDK 포함)
signtool sign /f certificate.pfx /p password /t http://timestamp.digicert.com CMG-SeqViewer.exe
```

---

## 권장 배포 전략

### Phase 1: 내부 테스트
- **Portable 버전만** 사용
- 빠른 반복 개발
- 다양한 환경 테스트

### Phase 2: 베타 릴리스
- **Portable + Installer** 제공
- 사용자 선택 가능
- 피드백 수집

### Phase 3: 정식 릴리스
- **Installer (권장) + Portable (고급)** 제공
- 디지털 서명 적용
- 자동 업데이트 구현

---

## 현재 상태

✅ **구현 완료**:
- Portable EXE (onedir)
- Portable EXE (onefile)
- Pre-loaded datasets 포함
- 아이콘 포함

🔧 **추가 구현 가능**:
- Inno Setup installer (installer.iss 제공됨)
- 자동 업데이트 시스템
- 디지털 서명

---

## 결론

**CMG-SeqViewer 같은 연구 도구는 Portable 방식이 더 적합합니다.**

이유:
1. 연구자들은 유연성 필요 (여러 PC, USB, 서버)
2. 빠른 배포/업데이트 중요
3. 버전 간 비교 필요
4. 설치 권한 문제 없음

**Installer는 다음 경우에만 필요**:
- 대규모 조직 배포
- 비기술 사용자 대상
- 자동 업데이트 필수
- 전문적인 이미지 중요
