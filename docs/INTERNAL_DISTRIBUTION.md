# Internal Data Distribution Guide

## 목적

Public GitHub repository에는 연구 데이터를 올리지 않으면서, 내부 연구단에는 데이터가 포함된 버전을 배포하는 방법을 안내합니다.

---

## 🔒 보안 전략

### Public Repository (GitHub)
- ✅ 소스 코드 전체 공개
- ✅ 애플리케이션 로직, UI, 분석 알고리즘
- ✅ 문서, 빌드 스크립트
- ❌ 실제 연구 데이터 (.parquet 파일)
- ❌ 데이터셋 메타데이터 (샘플명 등)

### Internal Distribution
- ✅ 위 모든 것 포함
- ✅ Pre-loaded datasets (database/datasets/*.parquet)
- ✅ Dataset metadata (database/metadata.json)

---

## 📦 배포 방법

### 방법 1: 수동 빌드 (가장 간단)

#### Windows 내부 배포판 생성

```powershell
# 1. 가상환경 활성화
venv\Scripts\activate

# 2. PyInstaller로 빌드 (database 폴더 자동 포함됨)
pyinstaller --clean rna-seq-viewer.spec

# 3. 빌드 결과 확인
# dist/CMG-SeqViewer/database/datasets/ 에 .parquet 파일들이 포함되어 있어야 함
Get-ChildItem -Recurse dist\CMG-SeqViewer\database\datasets\

# 4. 내부 배포용 ZIP 생성
Compress-Archive -Path "dist\CMG-SeqViewer" -DestinationPath "CMG-SeqViewer-Internal-v1.0.0.zip"

# 5. 내부 파일 서버나 SharePoint에 업로드
# \\internal-server\software\CMG-SeqViewer\
```

#### macOS 내부 배포판 생성

```bash
# 1. 가상환경 활성화
source venv/bin/activate

# 2. PyInstaller로 빌드
pyinstaller --clean cmg-seqviewer-macos.spec

# 3. DMG 생성
hdiutil create -volname "CMG-SeqViewer-Internal" \
               -srcfolder dist/CMG-SeqViewer.app \
               -ov -format UDZO \
               CMG-SeqViewer-Internal-v1.0.0.dmg

# 4. 내부 서버에 업로드
```

---

### 방법 2: 데이터 분리 배포 (보안성 높음)

코드와 데이터를 완전히 분리하여 배포합니다.

#### 2-1. Public 코드 패키지

사용자가 GitHub에서 직접 다운로드:
```powershell
git clone https://github.com/YOUR_USERNAME/cmg-seqviewer.git
cd cmg-seqviewer
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

#### 2-2. Internal 데이터 패키지 생성

```powershell
# 데이터만 별도 패키징
Compress-Archive -Path "database\datasets\*", "database\metadata.json" `
                 -DestinationPath "CMG-SeqViewer-Data-v1.0.0.zip"
```

**배포 구조:**
```
\\internal-server\CMG-SeqViewer\
├── README-Internal.txt          # 설치 안내
└── CMG-SeqViewer-Data-v1.0.0.zip
    └── database/
        ├── datasets/
        │   └── *.parquet        # 연구 데이터
        └── metadata.json        # 데이터셋 정보
```

**README-Internal.txt 내용:**
```text
CMG-SeqViewer Internal Data Package
====================================

Installation Steps:
1. Clone from GitHub:
   git clone https://github.com/YOUR_USERNAME/cmg-seqviewer.git
   cd cmg-seqviewer

2. Extract this data package into the project root:
   - Unzip CMG-SeqViewer-Data-v1.0.0.zip
   - Copy database/* to cmg-seqviewer/database/

3. Setup and run:
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   python src\main.py

Your pre-loaded datasets will appear in "Database Browser".
```

---

### 방법 3: Private Data Repository (대규모 팀용)

GitHub Organization 내에 Private repository를 추가로 생성합니다.

#### 3-1. 두 개의 Repository 생성

**Public Repository** (코드):
```
https://github.com/YOUR_ORG/cmg-seqviewer
- 소스 코드
- 문서
- 빌드 스크립트
- database/.gitkeep (빈 폴더 구조)
```

**Private Repository** (데이터):
```
https://github.com/YOUR_ORG/cmg-seqviewer-data (Private!)
- database/datasets/*.parquet
- database/metadata.json
- README.md (데이터 설명)
```

#### 3-2. Git Submodule 사용

```powershell
# 메인 프로젝트에 데이터 저장소를 submodule로 추가
cd cmg-seqviewer
git submodule add https://github.com/YOUR_ORG/cmg-seqviewer-data.git database-private

# 심볼릭 링크 생성 (개발 시)
# Windows (관리자 권한 필요)
New-Item -ItemType SymbolicLink -Path "database\datasets" -Target "database-private\datasets"

# 또는 간단히 복사
Copy-Item -Recurse database-private\* database\
```

**내부 팀원 설치 과정:**
```powershell
# 1. 메인 저장소 클론
git clone https://github.com/YOUR_ORG/cmg-seqviewer.git
cd cmg-seqviewer

# 2. Submodule 초기화 (Private repo 접근 권한 필요)
git submodule init
git submodule update

# 3. 데이터 복사
Copy-Item -Recurse database-private\* database\

# 4. 실행
python src\main.py
```

---

### 방법 4: GitHub Actions with Secrets (자동화)

Private 데이터를 GitHub Secrets에 암호화하여 저장하고, 내부 빌드 시에만 포함시킵니다.

#### 4-1. 데이터 암호화

```powershell
# 1. 데이터 압축
Compress-Archive -Path "database\datasets\*", "database\metadata.json" `
                 -DestinationPath "database-encrypted.zip"

# 2. Base64 인코딩
$bytes = [System.IO.File]::ReadAllBytes("database-encrypted.zip")
$base64 = [Convert]::ToBase64String($bytes)
$base64 | Out-File "database-base64.txt"

# 3. GitHub Secrets에 저장
# Repository → Settings → Secrets and variables → Actions
# New repository secret: DATABASE_PACKAGE
# Value: (database-base64.txt 내용 붙여넣기)
```

#### 4-2. Workflow 수정

`.github/workflows/build-internal.yml` 생성:

```yaml
name: Build CMG-SeqViewer (Internal with Data)

on:
  workflow_dispatch:  # 수동 실행만 가능
    inputs:
      include_data:
        description: 'Include internal data'
        required: true
        default: 'true'
        type: boolean

jobs:
  build-internal:
    runs-on: windows-latest
    if: github.event.inputs.include_data == 'true'
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Decode and extract internal data
        env:
          DATABASE_PACKAGE: ${{ secrets.DATABASE_PACKAGE }}
        run: |
          $bytes = [Convert]::FromBase64String($env:DATABASE_PACKAGE)
          [IO.File]::WriteAllBytes("database.zip", $bytes)
          Expand-Archive -Path "database.zip" -DestinationPath "database" -Force
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pyinstaller pillow
      
      - name: Build with data
        run: pyinstaller --clean rna-seq-viewer.spec
      
      - name: Create internal ZIP
        run: |
          Compress-Archive -Path "dist\CMG-SeqViewer" `
                           -DestinationPath "CMG-SeqViewer-Internal-${{ github.ref_name }}.zip"
      
      - name: Upload artifact (DO NOT make public!)
        uses: actions/upload-artifact@v3
        with:
          name: CMG-SeqViewer-Internal
          path: CMG-SeqViewer-Internal-*.zip
          retention-days: 7  # 자동 삭제
```

**사용법:**
1. Repository → Actions → "Build CMG-SeqViewer (Internal with Data)"
2. Run workflow → 체크박스 확인
3. 빌드 완료 후 Artifacts에서 다운로드
4. 내부 서버에 수동 업로드

---

## ✅ 권장 방법 비교

| 방법 | 난이도 | 보안성 | 자동화 | 추천 대상 |
|------|--------|--------|--------|-----------|
| **1. 수동 빌드** | ⭐ 쉬움 | ⭐⭐⭐ 높음 | ❌ | 소규모 팀 (1-5명) |
| **2. 데이터 분리** | ⭐⭐ 보통 | ⭐⭐⭐⭐ 매우높음 | ❌ | 중규모 팀 (5-20명) |
| **3. Private Repo** | ⭐⭐⭐ 복잡 | ⭐⭐⭐⭐⭐ 최고 | ✅ | 대규모 팀 (20명+) |
| **4. GitHub Secrets** | ⭐⭐⭐⭐ 매우복잡 | ⭐⭐⭐⭐ 매우높음 | ✅ | CI/CD 필수 팀 |

### 🎯 추천: 방법 1 (수동 빌드)

**이유:**
- ✅ 설정 간단 (즉시 사용 가능)
- ✅ 완벽한 데이터 통제
- ✅ GitHub에 데이터 절대 노출 안 됨
- ✅ 소규모 연구단에 적합

**단점:**
- 수동 빌드 필요 (자동화 없음)
- 각 플랫폼별로 빌드 환경 필요

---

## 🔐 보안 체크리스트

### Git에 데이터가 올라가지 않았는지 확인

```powershell
# 1. .gitignore가 제대로 적용되었는지 확인
git status

# 아래가 표시되면 안 됨:
# ❌ database/datasets/*.parquet
# ❌ database/metadata.json

# 2. Git 히스토리에 데이터가 없는지 확인
git log --all --full-history -- "database/datasets/*.parquet"
# 결과가 비어있어야 함

# 3. 만약 실수로 커밋했다면 제거
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch database/datasets/*.parquet" \
  --prune-empty --tag-name-filter cat -- --all
```

### GitHub에 Push 전 최종 확인

```powershell
# 1. Dry-run으로 무엇이 push될지 확인
git push --dry-run origin main

# 2. 로컬 저장소 크기 확인
Get-ChildItem -Recurse | Measure-Object -Property Length -Sum
# 데이터 제외 시 <50MB 정도여야 함

# 3. .git 폴더에 큰 파일이 없는지 확인
git verify-pack -v .git/objects/pack/*.idx | 
  Sort-Object -Property @{Expression={$_.split(' ')[2]}} -Descending | 
  Select-Object -First 10
```

---

## 📋 내부 배포 체크리스트

### 빌드 전
- [ ] 최신 코드로 업데이트 (`git pull`)
- [ ] 데이터 파일들이 `database/datasets/`에 존재
- [ ] `metadata.json` 파일 존재 및 유효성 확인
- [ ] 버전 번호 확인 (`src/version.py` 또는 `setup.py`)

### 빌드 후
- [ ] `dist/CMG-SeqViewer/database/datasets/*.parquet` 파일 존재 확인
- [ ] 실행 파일 테스트 (`CMG-SeqViewer.exe` 또는 `.app` 실행)
- [ ] Database Browser에 데이터셋 표시 확인
- [ ] 각 데이터셋 로드 테스트

### 배포 전
- [ ] 내부 배포판임을 파일명에 명시 (`-Internal-` 포함)
- [ ] README-Internal.txt 포함 (설치 안내)
- [ ] 버전 번호 및 빌드 날짜 기록
- [ ] 내부 서버/SharePoint에만 업로드

---

## 🆘 문제 해결

### "Database folder is empty" 경고

**원인**: .gitignore에 의해 데이터가 제외됨  
**해결**:
```powershell
# 현재 폴더 확인
Get-ChildItem database\datasets\

# .parquet 파일이 없다면 백업에서 복원
Copy-Item -Recurse \\backup-server\cmg-seqviewer\database\* database\
```

### GitHub에 실수로 데이터가 Push됨

**긴급 조치**:
```powershell
# 1. 해당 커밋 되돌리기 (아직 push 안 했다면)
git reset --soft HEAD~1

# 2. 이미 push했다면 히스토리에서 완전 제거
git filter-branch --force --index-filter \
  "git rm -rf --cached --ignore-unmatch database/datasets/" \
  HEAD

# 3. Force push (주의: 협업 시 팀원들에게 공지)
git push origin --force --all

# 4. GitHub에서 캐시 정리 요청 (필요시)
# Settings → Options → Danger Zone → Delete this repository (극단적 경우)
```

### 빌드에 데이터가 포함 안 됨

**원인**: spec 파일에 `datas` 설정 누락  
**확인**:
```python
# rna-seq-viewer.spec
datas=[
    ('database', 'database'),  # 이 줄이 있어야 함
],
```

---

## 📞 지원

내부 배포 관련 문의: [your-internal-contact@organization.edu]

데이터 접근 권한 요청: [data-admin@organization.edu]
