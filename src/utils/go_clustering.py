"""
GO Term Clustering using Jaccard Similarity + Hierarchical Clustering

유사한 GO Term을 Jaccard Similarity 기반 계층적 군집화로 클러스터링합니다.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Set, Tuple, Optional
import logging
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.spatial.distance import squareform
from sklearn.metrics import pairwise_distances

from models.standard_columns import StandardColumns


class GOClustering:
    """GO Term 클러스터링 클래스 (Jaccard Similarity + Hierarchical Clustering)"""
    
    def __init__(self, similarity_threshold: float = 0.7):
        """
        Args:
            similarity_threshold: Jaccard similarity 임계값 (기본값: 0.7)
                                 높을수록 더 타이트한 클러스터 생성
        """
        self.logger = logging.getLogger(__name__)
        self.similarity_threshold = similarity_threshold
    
    def _calculate_jaccard_similarity_matrix(self, gene_sets: List[Set[str]]) -> np.ndarray:
        """
        모든 GO Term 쌍에 대해 Jaccard Similarity를 계산하여 N x N 유사도 행렬 생성
        
        Jaccard Similarity = |A ∩ B| / |A ∪ B|
        
        Args:
            gene_sets: 각 GO Term의 유전자 집합 리스트
            
        Returns:
            N x N Jaccard similarity matrix
        """
        n_terms = len(gene_sets)
        self.logger.info(f"Calculating Jaccard similarity matrix for {n_terms} terms...")
        
        # Vectorization을 위해 binary matrix 생성
        # 모든 유전자 추출
        all_genes = sorted(set().union(*gene_sets))
        gene_to_idx = {gene: idx for idx, gene in enumerate(all_genes)}
        n_genes = len(all_genes)
        
        # Binary matrix: [n_terms, n_genes]
        binary_matrix = np.zeros((n_terms, n_genes), dtype=np.int8)
        
        for term_idx, gene_set in enumerate(gene_sets):
            for gene in gene_set:
                gene_idx = gene_to_idx[gene]
                binary_matrix[term_idx, gene_idx] = 1
        
        # Jaccard distance를 pairwise로 계산
        # sklearn의 pairwise_distances를 사용 (jaccard metric)
        # distance = 1 - similarity이므로 변환 필요
        jaccard_distance = pairwise_distances(binary_matrix, metric='jaccard')
        jaccard_similarity = 1 - jaccard_distance
        
        # NaN 처리 (empty sets)
        jaccard_similarity = np.nan_to_num(jaccard_similarity, nan=0.0)
        
        self.logger.info(f"Similarity matrix calculated: shape={jaccard_similarity.shape}")
        
        return jaccard_similarity
    
    def cluster_terms(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[int, List[int]]]:
        """
        GO Term을 Jaccard Similarity 기반 계층적 군집화로 클러스터링
        
        Args:
            df: GO/KEGG 분석 결과 DataFrame (_gene_set 컬럼 필요)
            
        Returns:
            (클러스터 정보가 추가된 DataFrame, {cluster_id: [term_indices]})
        """
        # Reset index at the start to ensure consistent positional indexing
        df = df.reset_index(drop=True)
        
        if '_gene_set' not in df.columns:
            self.logger.warning("_gene_set column not found, skipping clustering")
            df = df.copy()
            df['cluster_id'] = range(len(df))
            df['is_representative'] = True
            df['representative_term'] = df[StandardColumns.DESCRIPTION] if StandardColumns.DESCRIPTION in df.columns else ''
            return df, {i: [i] for i in range(len(df))}
        
        if len(df) == 0:
            self.logger.warning("Empty DataFrame, skipping clustering")
            return df.copy(), {}
        
        # 유전자 집합 추출
        gene_sets = [row['_gene_set'] if isinstance(row['_gene_set'], set) else set() 
                     for _, row in df.iterrows()]
        
        # 빈 gene set 필터링
        valid_indices = [i for i, gs in enumerate(gene_sets) if len(gs) > 0]
        
        if len(valid_indices) == 0:
            self.logger.warning("No valid gene sets found - treating each term as separate cluster")
            df = df.copy()
            df['cluster_id'] = range(len(df))
            df['is_representative'] = True
            if StandardColumns.DESCRIPTION in df.columns:
                df['representative_term'] = df[StandardColumns.DESCRIPTION]
            else:
                df['representative_term'] = [f"Term {i}" for i in range(len(df))]
            return df, {i: [i] for i in range(len(df))}
        
        # 1. Similarity Matrix 계산
        valid_gene_sets = [gene_sets[i] for i in valid_indices]
        similarity_matrix = self._calculate_jaccard_similarity_matrix(valid_gene_sets)
        
        # 2. Hierarchical Clustering
        # Distance = 1 - Similarity
        distance_matrix = 1 - similarity_matrix
        
        # condensed distance matrix로 변환 (상삼각행렬을 1D 배열로)
        condensed_distance = squareform(distance_matrix, checks=False)
        
        # Hierarchical clustering (average linkage)
        self.logger.info("Performing hierarchical clustering...")
        linkage_matrix = linkage(condensed_distance, method='average')
        
        # 3. Cut tree at similarity threshold
        # distance_threshold = 1 - similarity_threshold
        distance_threshold = 1 - self.similarity_threshold
        cluster_labels = fcluster(linkage_matrix, t=distance_threshold, criterion='distance')
        
        # 4. 클러스터 딕셔너리 생성
        clusters = {}
        for idx, cluster_id in enumerate(cluster_labels):
            original_idx = valid_indices[idx]
            if cluster_id not in clusters:
                clusters[cluster_id] = []
            clusters[cluster_id].append(original_idx)

        self.logger.info(f"Created {len(clusters)} clusters from {len(valid_indices)} valid terms")

        # Filter out singleton clusters (size == 1) from the returned clusters mapping.
        # Terms that belong to singleton clusters will keep cluster_id = -1 in the
        # resulting DataFrame so the UI can treat them as singletons.
        filtered_clusters = {cid: idxs for cid, idxs in clusters.items() if len(idxs) > 1}

        # 5. Representative Term 선정 (only for clusters with size > 1)
        df_result = self._add_cluster_info(df, filtered_clusters, valid_indices)

        return df_result, filtered_clusters
    
    def _add_cluster_info(self, df: pd.DataFrame, 
                          clusters: Dict[int, List[int]],
                          valid_indices: List[int]) -> pd.DataFrame:
        """
        DataFrame에 클러스터 정보 추가
        
        Args:
            df: 원본 DataFrame
            clusters: {cluster_id: [term_indices]} 딕셔너리
            valid_indices: 유효한 term의 인덱스 리스트
            
        Returns:
            클러스터 정보가 추가된 DataFrame
        """
        df_result = df.copy()
        
        # Index is already reset in cluster_terms, so positional access works correctly
        
        # 초기화
        df_result['cluster_id'] = -1
        df_result['is_representative'] = False
        df_result['representative_term'] = ''
        
        # 각 클러스터에서 대표 term 선정
        for cluster_id, term_indices in clusters.items():
            # term_indices are positional indices from enumerate() in cluster_terms
            cluster_df = df_result.iloc[term_indices]
            
            # FDR/P-value가 가장 낮은 term을 대표로 선정
            if StandardColumns.FDR in cluster_df.columns:
                # idxmin returns label index, need to convert to position
                best_label_idx = cluster_df[StandardColumns.FDR].idxmin()
            elif StandardColumns.PVALUE_GO in cluster_df.columns:
                best_label_idx = cluster_df[StandardColumns.PVALUE_GO].idxmin()
            else:
                # FDR/P-value가 없으면 첫 번째 term 선택
                best_label_idx = term_indices[0]
            
            # 대표 term 정보
            if StandardColumns.DESCRIPTION in df_result.columns:
                representative_term = df_result.loc[best_label_idx, StandardColumns.DESCRIPTION]
            else:
                representative_term = f"Cluster {cluster_id}"
            
            # 클러스터 ID 및 대표 여부 설정
            for idx in term_indices:
                df_result.at[idx, 'cluster_id'] = cluster_id
                df_result.at[idx, 'representative_term'] = representative_term
                df_result.at[idx, 'is_representative'] = (idx == best_label_idx)
        
        return df_result
    
    def get_representative_terms(self, df: pd.DataFrame, top_n: Optional[int] = None) -> pd.DataFrame:
        """
        각 클러스터에서 대표 GO Term만 추출
        
        Args:
            df: 클러스터 정보가 포함된 DataFrame
            top_n: 반환할 최대 term 수 (None이면 모두 반환)
            
        Returns:
            대표 term들의 DataFrame
        """
        if 'is_representative' not in df.columns:
            self.logger.warning("is_representative column not found")
            return df.copy()
        
        # 대표 term만 필터링
        representative_df = df[df['is_representative'] == True].copy()
        
        # FDR로 정렬
        if StandardColumns.FDR in representative_df.columns:
            representative_df = representative_df.sort_values(StandardColumns.FDR)
        
        # top_n 개만 선택
        if top_n:
            representative_df = representative_df.head(top_n)
        
        self.logger.info(f"Selected {len(representative_df)} representative terms")
        
        return representative_df
    
    def calculate_cluster_statistics(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        각 클러스터의 통계 정보 계산
        
        Args:
            df: 클러스터 정보가 포함된 DataFrame
            
        Returns:
            클러스터 통계 DataFrame
        """
        if 'cluster_id' not in df.columns:
            self.logger.warning("cluster_id column not found")
            return pd.DataFrame()
        
        cluster_stats = []
        
        for cluster_id in df['cluster_id'].unique():
            if cluster_id < 0:  # invalid cluster
                continue
            
            cluster_df = df[df['cluster_id'] == cluster_id]
            
            # 클러스터 내 모든 유전자 수집
            all_genes = set()
            if '_gene_set' in cluster_df.columns:
                for gene_set in cluster_df['_gene_set']:
                    if isinstance(gene_set, set):
                        all_genes.update(gene_set)
            
            stats = {
                'cluster_id': cluster_id,
                'n_terms': len(cluster_df),
                'n_unique_genes': len(all_genes),
                'representative_term': cluster_df[cluster_df['is_representative'] == True][StandardColumns.DESCRIPTION].iloc[0] 
                                      if StandardColumns.DESCRIPTION in cluster_df.columns and any(cluster_df['is_representative']) 
                                      else '',
            }
            
            # FDR 통계
            if StandardColumns.FDR in cluster_df.columns:
                stats['min_fdr'] = cluster_df[StandardColumns.FDR].min()
                stats['max_fdr'] = cluster_df[StandardColumns.FDR].max()
                stats['avg_fdr'] = cluster_df[StandardColumns.FDR].mean()
            
            # Gene count 통계
            if StandardColumns.GENE_COUNT in cluster_df.columns:
                stats['avg_gene_count'] = cluster_df[StandardColumns.GENE_COUNT].mean()
            
            cluster_stats.append(stats)
        
        result_df = pd.DataFrame(cluster_stats)
        
        # min_fdr로 정렬
        if 'min_fdr' in result_df.columns:
            result_df = result_df.sort_values('min_fdr')
        
        return result_df
