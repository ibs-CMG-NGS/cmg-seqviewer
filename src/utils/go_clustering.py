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
        
        # Jaccard distance를 pairwise로 계산 (numpy 구현)
        # Jaccard distance = 1 - |A ∩ B| / |A ∪ B|
        # binary matrix에서: intersection = dot product, union = sum(a) + sum(b) - dot
        intersection = binary_matrix @ binary_matrix.T          # (n_terms, n_terms)
        row_sums     = binary_matrix.sum(axis=1, keepdims=True)  # (n_terms, 1)
        union        = row_sums + row_sums.T - intersection      # (n_terms, n_terms)
        with np.errstate(invalid='ignore', divide='ignore'):
            jaccard_distance = np.where(union == 0, 1.0, 1.0 - intersection / union)
        jaccard_similarity = 1.0 - jaccard_distance
        
        # NaN 처리 (empty sets)
        jaccard_similarity = np.nan_to_num(jaccard_similarity, nan=0.0)
        
        self.logger.info(f"Similarity matrix calculated: shape={jaccard_similarity.shape}")
        
        return jaccard_similarity
    
    def cluster_terms(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[int, List[int]]]:
        """
        GO Term을 Jaccard Similarity 기반 계층적 군집화로 클러스터링.

        fit(비싼 Jaccard 유사도 + linkage 1회) + cut(임계값에서 트리 절단, 즉시) 의 래퍼.
        임계값만 바꿔가며 재군집하려면 fit() 한 번 후 cut(threshold) 를 반복 호출하면 된다.

        Returns:
            (클러스터 정보가 추가된 DataFrame, {cluster_id: [term_indices]})
        """
        self.fit(df)
        return self.cut(self.similarity_threshold)

    def fit(self, df: pd.DataFrame) -> 'GOClustering':
        """유전자 집합으로 Jaccard 유사도 + average-linkage 트리를 '한 번' 계산해 캐시한다.

        이후 cut(threshold) 는 이 캐시된 linkage 를 잘라내기만 하므로 매우 빠르다.
        _gene_set 이 없거나 유효 term 이 없으면 '자명한(각자 클러스터)' 상태로 fit 한다.
        """
        df = df.reset_index(drop=True)
        self._df = df
        self._linkage_matrix = None
        self._valid_indices = []
        self._trivial = False   # True 면 각 term 이 자기 자신 클러스터(군집 불가)

        if '_gene_set' not in df.columns or len(df) == 0:
            if '_gene_set' not in df.columns:
                self.logger.warning("_gene_set column not found, skipping clustering")
            self._trivial = True
            return self

        gene_sets = [row if isinstance(row, set) else set() for row in df['_gene_set']]
        self._valid_indices = [i for i, gs in enumerate(gene_sets) if len(gs) > 0]
        if len(self._valid_indices) == 0:
            self.logger.warning("No valid gene sets found - each term becomes its own cluster")
            self._trivial = True
            return self

        valid_gene_sets = [gene_sets[i] for i in self._valid_indices]
        similarity_matrix = self._calculate_jaccard_similarity_matrix(valid_gene_sets)
        distance_matrix = 1 - similarity_matrix
        condensed_distance = squareform(distance_matrix, checks=False)
        self.logger.info("Building linkage (average) once; cuts are now instant...")
        self._linkage_matrix = linkage(condensed_distance, method='average')
        return self

    def cut(self, similarity_threshold: Optional[float] = None
            ) -> Tuple[pd.DataFrame, Dict[int, List[int]]]:
        """캐시된 linkage 를 유사도 임계값에서 잘라 (clustered_df, clusters) 반환 (빠름).

        fit() 을 먼저 호출해야 한다. similarity_threshold 를 주면 self 값도 갱신한다.
        """
        if similarity_threshold is not None:
            self.similarity_threshold = similarity_threshold
        if getattr(self, '_df', None) is None:
            raise RuntimeError("cut() called before fit()")

        df = self._df
        # 자명한 경우: 각 term 을 개별 클러스터로
        if self._trivial or self._linkage_matrix is None:
            df = df.copy()
            df['cluster_id'] = range(len(df))
            df['is_representative'] = True
            if StandardColumns.DESCRIPTION in df.columns:
                df['representative_term'] = df[StandardColumns.DESCRIPTION]
            else:
                df['representative_term'] = [f"Term {i}" for i in range(len(df))]
            return df, {i: [i] for i in range(len(df))}

        # 트리 절단 (거리 = 1 - 유사도)
        distance_threshold = 1 - self.similarity_threshold
        cluster_labels = fcluster(self._linkage_matrix, t=distance_threshold, criterion='distance')

        clusters: Dict[int, List[int]] = {}
        for idx, cluster_id in enumerate(cluster_labels):
            clusters.setdefault(int(cluster_id), []).append(self._valid_indices[idx])

        # 크기 1(singleton)은 제외 — 해당 term 은 df 에서 cluster_id = -1 로 남는다
        filtered_clusters = {cid: idxs for cid, idxs in clusters.items() if len(idxs) > 1}
        df_result = self._add_cluster_info(df, filtered_clusters, self._valid_indices)
        return df_result, filtered_clusters

    def cluster_counts(self, thresholds) -> list:
        """여러 임계값에서 (threshold, n_clusters, n_singletons) 를 빠르게 계산 (sweep 용).

        fit() 이후 호출. linkage 재사용이라 임계값 목록 전체가 즉시 계산된다.
        """
        out = []
        if getattr(self, '_linkage_matrix', None) is None:
            return out
        for t in thresholds:
            labels = fcluster(self._linkage_matrix, t=1 - float(t), criterion='distance')
            sizes: Dict[int, int] = {}
            for lb in labels:
                sizes[int(lb)] = sizes.get(int(lb), 0) + 1
            n_clusters = sum(1 for s in sizes.values() if s > 1)
            n_singletons = sum(1 for s in sizes.values() if s == 1)
            out.append((float(t), n_clusters, n_singletons))
        return out
    
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
