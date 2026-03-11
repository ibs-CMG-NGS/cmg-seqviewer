"""
Data Path Configuration

외부 데이터 폴더 경로를 관리하는 유틸리티입니다.
빌드 후 사용자가 parquet 파일을 추가할 수 있는 경로를 제공합니다.
"""

import sys
import logging
from pathlib import Path
from typing import List


class DataPathConfig:
    """
    데이터 경로 설정 관리
    
    우선순위:
    1. 외부 데이터 폴더 (실행 파일 위치/data)
    2. 레거시 데이터베이스 폴더 (./database) - 하위 호환성
    """
    
    @staticmethod
    def get_external_data_dir() -> Path:
        """
        외부 데이터 폴더 경로 반환
        
        사용자가 배포 후 parquet 파일을 추가하는 폴더입니다.
        
        Returns:
            Path: 외부 데이터 디렉토리 경로
            
        Examples:
            - Frozen (PyInstaller): C:\\Program Files\\CMG-SeqViewer\\data
            - Development: C:\\...\\rna-seq-data-view\\data
        """
        if getattr(sys, 'frozen', False):
            # PyInstaller로 패키징된 경우
            # Windows: C:\Program Files\CMG-SeqViewer\CMG-SeqViewer.exe
            # macOS: /Applications/CMG-SeqViewer.app/Contents/MacOS/CMG-SeqViewer
            base_path = Path(sys.executable).parent
        else:
            # 개발 환경
            base_path = Path(__file__).parent.parent.parent
        
        return base_path / "data"
    
    @staticmethod
    def get_legacy_database_dir() -> Path:
        """
        레거시 데이터베이스 폴더 경로 반환 (하위 호환성)
        
        기존 버전과의 호환성을 위해 유지됩니다.
        
        Returns:
            Path: 레거시 데이터베이스 디렉토리 경로
        """
        if getattr(sys, 'frozen', False):
            # PyInstaller로 패키징된 경우 (_MEIPASS는 임시 폴더)
            base_path = Path(sys._MEIPASS)
        else:
            # 개발 환경
            base_path = Path(__file__).parent.parent.parent
        
        return base_path / "database"
    
    @staticmethod
    def get_all_data_dirs() -> List[Path]:
        """
        모든 데이터 디렉토리 경로를 우선순위 순으로 반환
        
        Returns:
            List[Path]: 데이터 디렉토리 경로 리스트 (우선순위 순)
        """
        return [
            DataPathConfig.get_external_data_dir(),  # 1순위: 외부 데이터
            DataPathConfig.get_legacy_database_dir(),  # 2순위: 레거시
        ]
    
    @staticmethod
    def get_external_datasets_dir() -> Path:
        """외부 데이터의 datasets 서브폴더"""
        return DataPathConfig.get_external_data_dir() / "datasets"
    
    @staticmethod
    def get_external_metadata_file() -> Path:
        """외부 데이터의 metadata.json 파일"""
        return DataPathConfig.get_external_data_dir() / "metadata.json"
    
    @staticmethod
    def ensure_external_data_structure():
        """
        외부 데이터 폴더 구조를 생성합니다.
        
        생성 구조:
        - data/
        - data/datasets/
        - data/README.txt (사용 안내)
        """
        logger = logging.getLogger(__name__)
        
        external_dir = DataPathConfig.get_external_data_dir()
        datasets_dir = DataPathConfig.get_external_datasets_dir()
        readme_file = external_dir / "README.txt"
        
        # 디렉토리 생성
        external_dir.mkdir(parents=True, exist_ok=True)
        datasets_dir.mkdir(parents=True, exist_ok=True)
        
        # README.txt 생성 (없는 경우만)
        if not readme_file.exists():
            readme_content = """CMG-SeqViewer External Data Folder
================================================================================

이 폴더는 CMG-SeqViewer에서 사용할 pre-loaded dataset을 저장하는 곳입니다.

사용 방법:
-----------
1. Parquet 파일(.parquet)을 datasets/ 폴더에 복사합니다.
2. 앱을 재시작하거나 Database Browser에서 "Refresh" 버튼을 클릭합니다.
3. Database Browser에서 자동으로 인식되어 사용할 수 있습니다.

폴더 구조:
-----------
data/
├── README.txt          (이 파일)
├── datasets/           (Parquet 파일을 여기에 추가)
│   ├── example1.parquet
│   ├── example2.parquet
│   └── ...
└── metadata.json       (자동 생성됨)

주의사항:
-----------
- 파일명은 영문/숫자 권장 (한글 가능하나 호환성 고려)
- Parquet 파일만 인식됩니다 (.parquet 확장자)
- 메타데이터(dataset 이름, 설명)는 자동으로 생성됩니다
- metadata.json은 수동으로 편집 가능합니다

파일 형식:
-----------
- Differential Expression (DE) 분석 결과
- GO/KEGG Enrichment 분석 결과
→ 자동으로 타입이 감지됩니다

문제 해결:
-----------
- 파일이 인식되지 않으면: Refresh 버튼 클릭
- 메타데이터가 잘못되었으면: metadata.json 삭제 후 재시작
- 더 많은 정보: https://github.com/ibs-CMG-NGS/cmg-seqviewer

================================================================================
"""
            try:
                with open(readme_file, 'w', encoding='utf-8') as f:
                    f.write(readme_content)
                logger.info(f"Created README.txt in external data folder: {readme_file}")
            except Exception as e:
                logger.warning(f"Failed to create README.txt: {e}")
        
        logger.info(f"External data structure ensured: {external_dir}")
