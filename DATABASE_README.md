# CMG-SeqViewer - Pre-loaded Datasets

이 배포판에는 미리 로드된 데이터셋이 포함되어 있습니다.

## 포함된 데이터셋 확인

프로그램 실행 후:
1. **File** → **Database Browser** 메뉴 클릭
2. 저장된 데이터셋 목록 확인
3. 데이터셋 선택 후 **Load** 버튼으로 불러오기

## 데이터셋 추가하기

### 방법 1: 프로그램 내에서 추가
1. **File** → **Database Browser** 열기
2. **Import Dataset** 버튼 클릭
3. Excel/CSV 파일 선택
4. 메타데이터 입력 후 저장

### 방법 2: 직접 파일 추가 (고급)
1. 프로그램 종료
2. `database/datasets/` 폴더에 `.parquet` 파일 복사
3. `database/metadata.json` 파일 수동 편집
4. 프로그램 재실행

## 데이터 위치

### 배포판에 포함된 데이터
- Windows: 실행 파일과 같은 폴더의 `database/` 디렉토리
- 읽기 전용 (배포판 원본 보존)

### 사용자가 추가한 데이터
프로그램에서 새로 추가한 데이터셋은:
- Windows: `%LOCALAPPDATA%\CMG-SeqViewer\database\`
- 사용자 권한으로 읽기/쓰기 가능

## 데이터셋 관리

### 삭제
Database Browser에서 데이터셋 선택 후 **Delete** 버튼

### 편집
Database Browser에서 데이터셋 선택 후 **Edit** 버튼
- 별칭(Alias) 수정
- 설명(Description) 수정
- 태그(Tags) 추가/제거

### 검색
Database Browser의 검색 상자에서:
- 이름, 별칭, 설명, 태그로 검색 가능
- 데이터셋 타입으로 필터링 가능

## 성능

Pre-loaded 데이터셋은 **Parquet 형식**으로 저장되어:
- ✅ **15-30배 빠른 로딩 속도** (Excel 대비)
- ✅ **압축으로 작은 파일 크기**
- ✅ **컬럼별 최적화된 저장**
- ✅ **메타데이터 포함**

## 문제 해결

### 데이터셋이 보이지 않음
1. `database/` 폴더가 실행 파일과 같은 위치에 있는지 확인
2. `database/metadata.json` 파일이 있는지 확인
3. 프로그램 재시작

### 데이터를 추가할 수 없음
- 배포판의 database 폴더는 읽기 전용일 수 있음
- 프로그램 내에서 Import 기능 사용 (자동으로 쓰기 가능한 위치에 저장됨)

### 데이터가 손상됨
1. 원본 배포판의 `database/` 폴더 복사
2. 기존 database 폴더 교체
