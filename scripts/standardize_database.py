"""
Database Standardization Script

기존 database 파일들을 표준 컬럼명으로 변환하여 재저장합니다.
"""

import sys
from pathlib import Path
sys.path.insert(0, 'src')

import pandas as pd
from utils.database_manager import DatabaseManager
from utils.data_loader import DataLoader
from models.data_models import DatasetType
from models.standard_columns import StandardColumns

def standardize_database():
    """모든 database 파일을 표준 컬럼명으로 변환"""
    
    db_manager = DatabaseManager()
    loader = DataLoader()
    
    # 모든 dataset 메타데이터 로드
    all_metadata = db_manager.get_all_metadata()
    
    print(f"Found {len(all_metadata)} datasets to standardize")
    print("=" * 70)
    
    converted = 0
    skipped = 0
    errors = 0
    
    for metadata in all_metadata:
        try:
            print(f"\nProcessing: {metadata.alias}")
            
            # Parquet 파일 로드
            file_path = db_manager.datasets_dir / Path(metadata.file_path).name
            
            if not file_path.exists():
                print(f"  ❌ File not found: {file_path}")
                errors += 1
                continue
            
            df = pd.read_parquet(file_path)
            print(f"  📊 Original columns: {list(df.columns)[:10]}")
            
            # 이미 표준화되어 있는지 확인 (gene_id, symbol, lfcse, stat 모두 체크)
            required_standard = [StandardColumns.GENE_ID, StandardColumns.SYMBOL, StandardColumns.LOG2FC, 
                                 StandardColumns.ADJ_PVALUE, StandardColumns.LFCSE, StandardColumns.STAT]
            if all(col in df.columns for col in required_standard):
                print(f"  ✅ Already standardized, skipping...")
                skipped += 1
                continue
            
            # 표준화 수행
            auto_mapping = loader._map_columns(df, metadata.dataset_type)
            df_std, original_columns = loader._standardize_columns(df, auto_mapping, metadata.dataset_type)
            
            print(f"  🔄 Standardized columns: {list(df_std.columns)[:10]}")
            print(f"  📝 Mapping: {original_columns}")
            
            # 동일한 파일명으로 덮어쓰기
            df_std.to_parquet(file_path, engine='pyarrow', compression='snappy')
            print(f"  ✅ Saved standardized data")
            
            converted += 1
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
            errors += 1
    
    print("\n" + "=" * 70)
    print(f"\n📊 Summary:")
    print(f"  ✅ Converted: {converted}")
    print(f"  ⏭️  Skipped (already standard): {skipped}")
    print(f"  ❌ Errors: {errors}")
    print(f"  📁 Total: {len(all_metadata)}")
    
    if converted > 0:
        print(f"\n✨ Successfully standardized {converted} database files!")
        print(f"   Database files now use standard column names.")
    
    if errors > 0:
        print(f"\n⚠️  {errors} files had errors during conversion.")
    
    return converted, skipped, errors

if __name__ == "__main__":
    print("🔧 CMG-SeqViewer Database Standardization")
    print("=" * 70)
    print("\nThis script will convert all database files to use standard column names.")
    print("Original files will be overwritten with standardized versions.\n")
    
    response = input("Continue? (y/n): ")
    if response.lower() != 'y':
        print("❌ Cancelled by user")
        sys.exit(0)
    
    print("\n🚀 Starting standardization...")
    converted, skipped, errors = standardize_database()
    
    if errors == 0:
        print("\n✅ Database standardization complete!")
        print("   You can now run the program without conversion overhead.")
    else:
        print("\n⚠️  Standardization completed with some errors.")
        print("   Check the output above for details.")
