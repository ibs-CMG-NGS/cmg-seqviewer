"""
Excel 파일 구조 진단 스크립트
원본 파일의 컬럼 구조를 확인하여 NaN 컬럼이 파일 자체의 문제인지 확인합니다.
"""

import pandas as pd
import sys
from pathlib import Path

def diagnose_excel(file_path: str, sheet_name=None):
    """Excel 파일 진단"""
    print("=" * 80)
    print(f"File: {file_path}")
    print("=" * 80)
    
    # 1. 원본 그대로 읽기 (아무 처리 없이)
    if sheet_name:
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        print(f"\nSheet: {sheet_name}")
    else:
        df = pd.read_excel(file_path)
        print("\nSheet: (First sheet)")
    
    print(f"\n{'=' * 80}")
    print("ORIGINAL COLUMNS (as read by pandas)")
    print(f"{'=' * 80}")
    print(f"Total columns: {len(df.columns)}")
    print("\nColumn list:")
    for i, col in enumerate(df.columns):
        col_type = type(col).__name__
        col_str = str(col)
        if pd.isna(col):
            print(f"  [{i:2d}] <NaN> (type: {col_type})")
        elif col_str.startswith('Unnamed:'):
            print(f"  [{i:2d}] '{col}' (type: {col_type}) <- UNNAMED COLUMN")
        else:
            print(f"  [{i:2d}] '{col}' (type: {col_type})")
    
    # 2. 첫 3행 데이터 확인
    print(f"\n{'=' * 80}")
    print("FIRST 3 ROWS")
    print(f"{'=' * 80}")
    print(df.head(3).to_string())
    
    # 3. 컬럼별 데이터 타입 및 NaN 비율
    print(f"\n{'=' * 80}")
    print("COLUMN DETAILS")
    print(f"{'=' * 80}")
    for i, col in enumerate(df.columns):
        dtype = df[col].dtype
        null_count = df[col].isna().sum()
        null_pct = (null_count / len(df)) * 100
        
        # 첫 값 확인
        first_val = df[col].iloc[0] if len(df) > 0 else None
        
        col_name = str(col) if not pd.isna(col) else "<NaN>"
        print(f"[{i:2d}] {col_name:30s} | dtype: {str(dtype):10s} | "
              f"NaN: {null_count:5d}/{len(df)} ({null_pct:5.1f}%) | "
              f"First value: {first_val}")
    
    # 4. 컬럼명에 공백이나 특수문자 확인
    print(f"\n{'=' * 80}")
    print("COLUMN NAME ANALYSIS")
    print(f"{'=' * 80}")
    for i, col in enumerate(df.columns):
        if pd.isna(col):
            print(f"[{i:2d}] WARNING: Column name is NaN")
        else:
            col_str = str(col)
            issues = []
            if col_str.startswith(' ') or col_str.endswith(' '):
                issues.append(f"Has leading/trailing spaces: '{col_str}'")
            if '\n' in col_str or '\r' in col_str:
                issues.append("Contains newline characters")
            if col_str.startswith('Unnamed:'):
                issues.append("Pandas auto-generated unnamed column")
            
            if issues:
                print(f"[{i:2d}] '{col_str}'")
                for issue in issues:
                    print(f"     -> {issue}")
    
    # 5. 첫 번째 행이 실제 헤더인지 확인
    print(f"\n{'=' * 80}")
    print("HEADER VALIDATION")
    print(f"{'=' * 80}")
    print("First row values (현재 헤더로 사용된 값):")
    print(list(df.columns))
    print("\nSecond row values (첫 번째 데이터 행):")
    if len(df) > 0:
        print(df.iloc[0].to_list())
    
    return df


if __name__ == "__main__":
    print("=" * 80)
    print("GO/KEGG Excel File Diagnostic Tool")
    print("=" * 80)
    
    # 파일 경로 입력
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        file_path = input("\nEnter Excel file path: ").strip('"').strip("'")
    
    if not Path(file_path).exists():
        print(f"\nERROR: File not found: {file_path}")
        sys.exit(1)
    
    # 시트 선택
    try:
        excel_file = pd.ExcelFile(file_path)
        print(f"\nAvailable sheets ({len(excel_file.sheet_names)}):")
        for i, sheet in enumerate(excel_file.sheet_names):
            print(f"  [{i}] {sheet}")
        
        sheet_input = input("\nEnter sheet name or number (or press Enter for first sheet): ").strip()
        
        if sheet_input == "":
            sheet_name = None
        elif sheet_input.isdigit():
            sheet_name = excel_file.sheet_names[int(sheet_input)]
        else:
            sheet_name = sheet_input
        
        # 진단 실행
        df = diagnose_excel(file_path, sheet_name)
        
        # 추가 분석 제안
        print(f"\n{'=' * 80}")
        print("RECOMMENDATIONS")
        print(f"{'=' * 80}")
        
        unnamed_cols = [col for col in df.columns if str(col).startswith('Unnamed:')]
        nan_cols = [i for i, col in enumerate(df.columns) if pd.isna(col)]
        
        if unnamed_cols:
            print(f"\n⚠️  Found {len(unnamed_cols)} unnamed columns: {unnamed_cols}")
            print("   -> 원본 Excel 파일에 빈 컬럼이 있을 가능성이 높습니다.")
            print("   -> Excel에서 해당 컬럼을 삭제하거나 이름을 지정하세요.")
        
        if nan_cols:
            print(f"\n⚠️  Found {len(nan_cols)} NaN column names at positions: {nan_cols}")
            print("   -> 이는 파일 자체의 문제일 가능성이 높습니다.")
            print("   -> Excel 파일에서 해당 위치의 헤더를 확인하세요.")
        
        # 데이터 저장 옵션
        save = input("\n\nSave cleaned DataFrame to CSV for inspection? (y/n): ").strip().lower()
        if save == 'y':
            output_path = Path(file_path).stem + "_diagnostic.csv"
            df.to_csv(output_path, index=False)
            print(f"\n✅ Saved to: {output_path}")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
