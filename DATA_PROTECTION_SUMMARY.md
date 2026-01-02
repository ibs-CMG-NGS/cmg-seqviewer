# 🔒 Data Protection Summary

## ✅ 적용 완료 사항

### 1. .gitignore 설정
```gitignore
# Internal research data - NOT for public repository
database/datasets/*.parquet
database/metadata.json

# Keep directory structure
!database/.gitkeep
!database/datasets/.gitkeep
```

**효과**: 
- ✅ 13개 .parquet 파일 모두 git에서 제외
- ✅ metadata.json 제외 (샘플명 등 민감정보 보호)
- ✅ 디렉토리 구조는 유지 (.gitkeep 파일)

---

## 📊 검증 결과

### Git Status 확인
```powershell
git status | Select-String "parquet"
# 결과: (비어있음) ✅ 성공
```

### Staged Files 확인
```
A  database/.gitkeep            # ✅ 트래킹됨
A  database/README.md            # ✅ 트래킹됨  
A  database/datasets/.gitkeep    # ✅ 트래킹됨
```

**❌ 트래킹 안 됨 (의도된 동작)**:
- database/datasets/*.parquet (13개 파일)
- database/metadata.json

---

## 📂 파일 구조

### Public Repository (GitHub)
```
database/
├── .gitkeep                  # ✅ 공개 (디렉토리 유지용)
├── README.md                 # ✅ 공개 (사용 안내)
└── datasets/
    └── .gitkeep              # ✅ 공개 (디렉토리 유지용)
```

### Internal Version (로컬/배포판)
```
database/
├── .gitkeep                  
├── README.md                 
├── metadata.json             # ❌ 비공개 (내부 전용)
└── datasets/
    ├── .gitkeep
    ├── 03d529ad-*.parquet    # ❌ 비공개 (연구 데이터)
    ├── 22eab765-*.parquet    # ❌ 비공개
    ├── ... (11개 more)       # ❌ 비공개
```

---

## 🛡️ 보안 전략

### Public Users (GitHub 다운로드)
1. 소스 코드 전체 다운로드 ✅
2. 앱 실행 시 database/ 폴더 비어있음
3. **Excel 파일 직접 로드하여 사용** (기본 기능)
4. 모든 분석 기능 정상 작동

### Internal Users (연구단 내부)
**방법 1 - 수동 빌드 (권장)**:
```powershell
# 내부 컴퓨터에서 빌드 (데이터 포함)
pyinstaller --clean rna-seq-viewer.spec
# → dist/CMG-SeqViewer/database/datasets/*.parquet 자동 포함

# 내부 배포
Compress-Archive -Path "dist\CMG-SeqViewer" `
                 -DestinationPath "CMG-SeqViewer-Internal-v1.0.0.zip"
```

**방법 2 - 데이터 분리**:
- 코드: GitHub에서 다운로드
- 데이터: 내부 서버에서 별도 다운로드 (`database-package.zip`)

**방법 3 - Private Repository**:
- `cmg-seqviewer` (Public) - 코드
- `cmg-seqviewer-data` (Private) - 데이터
- Git submodule로 연결

자세한 내용: [docs/INTERNAL_DISTRIBUTION.md](docs/INTERNAL_DISTRIBUTION.md)

---

## 📋 관련 문서

| 문서 | 대상 | 내용 |
|------|------|------|
| `database/README.md` | Public/Internal | Public 사용자 안내, 데이터 포맷 설명 |
| `docs/INTERNAL_DISTRIBUTION.md` | Internal | 내부 배포 방법 4가지 상세 안내 |
| `UPLOAD_CHECKLIST.md` | Maintainer | GitHub 업로드 전 검증 절차 |
| `README.md` | Public | 설치 안내 (데이터 보호 노트 포함) |

---

## ✅ 최종 확인 사항

### GitHub Push 전 체크리스트

- [x] `.gitignore`에 `database/datasets/*.parquet` 추가
- [x] `.gitignore`에 `database/metadata.json` 추가
- [x] `database/.gitkeep` 생성
- [x] `database/datasets/.gitkeep` 생성
- [x] `database/README.md` 작성 (Public 사용 안내)
- [x] `docs/INTERNAL_DISTRIBUTION.md` 작성 (내부 배포 가이드)
- [x] `git status | Select-String "parquet"` 결과 비어있음 확인
- [x] `git status --short | Select-String "database"` 확인:
  - ✅ `.gitkeep` 파일들만 staged
  - ✅ README.md만 staged
  - ❌ .parquet 파일 없음
  - ❌ metadata.json 없음

### 테스트 시나리오

1. **Public User 시나리오**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/cmg-seqviewer.git
   # database/ 폴더: .gitkeep, README.md만 존재
   # → Excel 파일 로드하여 사용
   ```

2. **Internal User 시나리오**:
   ```bash
   # 방법 1: 내부 빌드 다운로드
   # → database/*.parquet 포함됨
   
   # 방법 2: GitHub + 내부 데이터 패키지
   git clone ...
   # + 내부 서버에서 database.zip 다운로드 및 압축 해제
   ```

---

## 🚨 긴급 상황 대처

### 실수로 데이터를 Push한 경우

```powershell
# 1. 히스토리에서 완전 제거
git filter-branch --force --index-filter \
  "git rm -rf --cached --ignore-unmatch database/datasets/" \
  HEAD

# 2. Force push (주의: 협업자에게 사전 공지)
git push origin --force --all

# 3. GitHub 캐시 정리
# Settings → General → Danger Zone → Delete repository (극단적 경우)
# 또는 GitHub Support에 민감 데이터 제거 요청
```

### GitHub Secrets 유출 방지

- ❌ `.parquet` 파일을 GitHub Secrets에 저장하지 말 것 (크기 제한)
- ❌ metadata.json에 민감 정보 포함 시 절대 공개 저장소에 커밋 금지
- ✅ 내부 배포는 수동 빌드 또는 내부 파일 서버 사용 권장

---

## 📞 문의

- **데이터 보호 관련**: [your-security-team@organization.edu]
- **내부 배포 관련**: [data-admin@organization.edu]
- **기술 지원**: [dev-support@organization.edu]

---

## 🎯 결론

✅ **데이터 보호 성공**:
- Public repository에 연구 데이터 **절대 노출 안 됨**
- 내부 배포 경로 **명확히 문서화됨**
- Public/Internal 사용자 모두 **정상 작동** 가능

✅ **Ready for GitHub Upload**:
```powershell
git commit -m "Initial commit - Data-protected version"
git remote add origin https://github.com/YOUR_USERNAME/cmg-seqviewer.git
git push -u origin master
```
