"""
RNA+ATAC-seq 통합 분석 직접 테스트 스크립트

GUI 없이 MultiOmicsIntegrator를 직접 호출하여 분석 결과를 검증합니다.

사용법:
    python test_integration_direct.py

데이터:
    RNA-seq : data/datasets/D1_vs_Control_DE.parquet
    ATAC-seq: examples/pairwise/1D_vs_CONTROL/final_da_result.xlsx  (gene_name 컬럼 포함)
"""

import sys
from pathlib import Path

# src 경로를 PYTHONPATH에 추가
sys.path.insert(0, str(Path(__file__).parent / "src"))

import pandas as pd

from utils.atac_seq_loader import ATACSeqLoader
from utils.multi_omics_integrator import MultiOmicsIntegrator
from models.standard_columns import StandardColumns

# ──────────────────────────────────────────────
# 1. 데이터 로드
# ──────────────────────────────────────────────
print("=" * 60)
print("1. 데이터 로드")
print("=" * 60)

# RNA-seq DE (parquet)
rna_path = Path("data/datasets/D1_vs_Control_DE.parquet")
rna_df = pd.read_parquet(rna_path)
print(f"RNA-seq : {rna_path.name}  →  {rna_df.shape[0]:,} 유전자")
print(f"  컬럼: {rna_df.columns.tolist()}")

# ATAC-seq DA (Excel — gene_name 포함)
atac_loader = ATACSeqLoader()
atac_path = Path("examples/pairwise/1D_vs_CONTROL/final_da_result.xlsx")
atac_dataset = atac_loader.load(atac_path)
atac_df = atac_dataset.dataframe
print(f"\nATAC-seq: {atac_path.name}  →  {atac_df.shape[0]:,} peaks")
print(f"  컬럼: {atac_df.columns.tolist()}")

# nearest_gene 값 확인
ng_col = StandardColumns.NEAREST_GENE
print(f"\n  nearest_gene 샘플 (첫 10개): {atac_df[ng_col].head(10).tolist()}")
valid_ng = atac_df[ng_col].notna() & (atac_df[ng_col] != "")
print(f"  유효한 nearest_gene 수: {valid_ng.sum():,} / {len(atac_df):,}")

# ──────────────────────────────────────────────
# 2. 통합 분석 — nearest_gene 방법
# ──────────────────────────────────────────────
print("\n" + "=" * 60)
print("2. integrate_by_nearest_gene()")
print("=" * 60)

integrator = MultiOmicsIntegrator(
    rna_padj_cutoff=0.05,
    rna_lfc_cutoff=1.0,
    atac_padj_cutoff=0.05,
    atac_lfc_cutoff=1.0,
)

result_ng = integrator.integrate_by_nearest_gene(rna_df, atac_df)
print(f"결과 shape: {result_ng.shape}")
print(f"컬럼: {result_ng.columns.tolist()}")
print()
print(result_ng.head(10).to_string(index=False))

print("\n[concordance 분포]")
if 'concordance' in result_ng.columns:
    print(result_ng['concordance'].value_counts().to_string())
else:
    print("  'concordance' 컬럼 없음")

# ──────────────────────────────────────────────
# 3. 통합 분석 — promoter 방법 (TSS ±2000bp)
# ──────────────────────────────────────────────
print("\n" + "=" * 60)
print("3. integrate_by_promoter(tss_window=2000)")
print("=" * 60)

if StandardColumns.DISTANCE_TO_TSS in atac_df.columns:
    result_promo = integrator.integrate_by_promoter(rna_df, atac_df, tss_window=2000)
    print(f"결과 shape: {result_promo.shape}")
    print()
    print(result_promo.head(10).to_string(index=False))

    print("\n[concordance 분포]")
    if 'concordance' in result_promo.columns:
        print(result_promo['concordance'].value_counts().to_string())
else:
    print(f"  distance_to_tss 컬럼 없음 → 건너뜀")

# ──────────────────────────────────────────────
# 4. 유의미한 결과 필터링 (concordant 유전자)
# ──────────────────────────────────────────────
print("\n" + "=" * 60)
print("4. Concordant 유전자 (RNA↑+ATAC↑ 또는 RNA↓+ATAC↓)")
print("=" * 60)

if 'concordance' in result_ng.columns:
    concordant = result_ng[result_ng['concordance'].isin(['concordant_up', 'concordant_down'])]
    print(f"Concordant 유전자 수: {len(concordant):,}")
    print()
    print(concordant.head(20).to_string(index=False))

    # CSV로 저장
    out_path = Path("test_integration_result.csv")
    result_ng.to_csv(out_path, index=False)
    print(f"\n전체 결과를 '{out_path}'에 저장했습니다.")
