"""
Main Presenter for RNA-Seq Data Analysis Program

MVP (Model-View-Presenter) 패턴의 Presenter 구현
GUI 로직과 비즈니스 로직을 분리합니다.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd
from PyQt6.QtCore import QObject, pyqtSignal, Qt

from core.fsm import FSM, State, Event
from core.logger import get_audit_logger
from models.data_models import Dataset, FilterCriteria, ComparisonResult, FilterMode, DatasetType
from models.standard_columns import StandardColumns
from utils.data_loader import DataLoader
from utils.statistics import StatisticalAnalyzer
from gui.workers import DataLoadWorker, FilterWorker, AnalysisWorker


class MainPresenter(QObject):
    """
    메인 Presenter
    
    View(GUI)와 Model(데이터/비즈니스 로직) 사이의 중재자 역할을 합니다.
    FSM을 통해 상태를 관리하고, 비즈니스 로직을 실행합니다.
    """
    
    # Signals
    dataset_loaded = pyqtSignal(str, Dataset)  # dataset_name, dataset
    filter_completed = pyqtSignal(pd.DataFrame, str)  # filtered_data, tab_name
    analysis_completed = pyqtSignal(dict, str)  # result, analysis_type
    comparison_completed = pyqtSignal(ComparisonResult)
    error_occurred = pyqtSignal(str)  # error_message
    progress_updated = pyqtSignal(int)  # progress percentage
    
    def __init__(self, view):
        """
        Args:
            view: MainWindow 인스턴스
        """
        super().__init__()
        
        self.view = view
        self.logger = logging.getLogger(__name__)
        self.audit_logger = get_audit_logger()
        
        # FSM 초기화
        self.fsm = FSM(initial_state=State.IDLE)
        
        # 데이터 저장소
        self.datasets: Dict[str, Dataset] = {}
        self.current_dataset: Optional[Dataset] = None
        
        # 유틸리티
        self.data_loader = DataLoader()
        self.analyzer = StatisticalAnalyzer()
        
        # FSM 콜백 등록
        self._register_fsm_callbacks()
        
        # Worker 참조 (비동기 작업)
        self.active_workers: List[QObject] = []
    
    def _register_fsm_callbacks(self):
        """FSM 상태 진입/이탈 콜백 등록"""
        # LOADING_DATA 진입 시
        self.fsm.register_on_enter(State.LOADING_DATA, self._on_loading_started)
        
        # FILTERING 진입 시
        self.fsm.register_on_enter(State.FILTERING, self._on_filtering_started)
        
        # ANALYZING 진입 시
        self.fsm.register_on_enter(State.ANALYZING, self._on_analyzing_started)
        
        # ERROR 진입 시
        self.fsm.register_on_enter(State.ERROR, self._on_error_state)
    
    def _on_loading_started(self, **kwargs):
        """데이터 로딩 시작"""
        self.logger.info("Data loading started")
    
    def _on_filtering_started(self, **kwargs):
        """필터링 시작"""
        self.logger.info("Filtering started")
    
    def _on_analyzing_started(self, **kwargs):
        """분석 시작"""
        self.logger.info("Analysis started")
    
    def _on_error_state(self, **kwargs):
        """오류 상태 진입"""
        error_msg = kwargs.get('error_message', 'Unknown error occurred')
        self.logger.error(f"Error state: {error_msg}")
        self.error_occurred.emit(error_msg)
    
    def load_dataset(self, file_path: Path, dataset_name: Optional[str] = None, custom_name: Optional[str] = None):
        """
        데이터셋 로드 (비동기)
        
        Args:
            file_path: Excel 파일 경로
            dataset_name: 데이터셋 이름 (None이면 파일명 사용) - deprecated, use custom_name
            custom_name: 사용자 지정 이름 (우선순위 최상위)
        """
        import time
        start_time = time.time()
        
        # custom_name이 있으면 우선 사용
        final_name = custom_name or dataset_name
        
        # 상태 전환
        if not self.fsm.trigger(Event.LOAD_DATA):
            self.logger.warning("Cannot load data in current state")
            return
        
        # Audit log
        self.audit_logger.log_action(
            "Load Dataset",
            details={'file': str(file_path), 'name': final_name or file_path.stem}
        )
        
        try:
            # 먼저 파일 타입을 빠르게 감지 (첫 번째 시트만 확인)
            try:
                test_df = pd.read_excel(file_path, nrows=10)  # 첫 10행만 읽어서 타입 감지
                detected_type = self.data_loader._detect_dataset_type(test_df)
                self.logger.info(f"Quick type detection: {detected_type.value}")
                
                # GO/KEGG 타입이면 전용 로더 사용
                if detected_type == DatasetType.GO_ANALYSIS:
                    from utils.go_kegg_loader import GOKEGGLoader
                    loader = GOKEGGLoader()
                    dataset = loader.load_from_excel(file_path, final_name or file_path.stem)
                    
                    # 데이터셋 저장
                    unique_name = self.view.dataset_manager._generate_unique_name(dataset.name)
                    dataset.name = unique_name
                    self.datasets[unique_name] = dataset
                    self.current_dataset = dataset
                    
                    # 상태 전환
                    self.fsm.trigger(Event.DATA_LOAD_SUCCESS)
                    
                    # Signal 방출
                    self.dataset_loaded.emit(dataset.name, dataset)
                    
                    # GUI 업데이트
                    self._update_view_with_dataset(dataset)
                    self.view._update_comparison_panel_datasets()
                    
                    # Audit log
                    duration = time.time() - start_time
                    summary = dataset.get_summary()
                    self.audit_logger.log_action(
                        "Dataset Loaded",
                        details={
                            'rows': summary.get('row_count', 0),
                            'type': dataset.dataset_type.value
                        },
                        duration=duration
                    )
                    
                    self.logger.info(f"GO/KEGG dataset '{dataset.name}' loaded successfully with {len(dataset.dataframe) if dataset.dataframe is not None else 0} terms")
                    return
            except Exception as e:
                self.logger.warning(f"Quick type detection failed: {e}, using standard loader")
            
            # DE 데이터셋은 기존 로더 사용
            # 컬럼 매핑 콜백 함수
            def column_mapper_callback(df, dataset_type, auto_mapping):
                from gui.column_mapper_dialog import ColumnMapperDialog
                dialog = ColumnMapperDialog(df, dataset_type, auto_mapping, self.view)
                
                if dialog.exec():
                    mapping = dialog.get_mapping()
                    
                    # 사용자가 저장 옵션을 선택한 경우
                    if dialog.should_save_mapping():
                        self.data_loader.save_custom_mapping(dataset_type, mapping)
                        self.logger.info("User mapping saved for future use")
                    
                    return mapping
                else:
                    return None
            
            # 동기 방식으로 로드 (나중에 Worker로 변경 가능)
            dataset = self.data_loader.load_from_excel(
                file_path, 
                final_name,  # custom_name 또는 dataset_name 사용
                column_mapper_callback=column_mapper_callback
            )
            
            # 데이터셋 저장 (고유 이름 생성)
            unique_name = self.view.dataset_manager._generate_unique_name(dataset.name)
            dataset.name = unique_name
            self.datasets[unique_name] = dataset
            self.current_dataset = dataset
            
            # 상태 전환
            self.fsm.trigger(Event.DATA_LOAD_SUCCESS)
            
            # Signal 방출
            self.dataset_loaded.emit(dataset.name, dataset)
            
            # GUI 업데이트
            self._update_view_with_dataset(dataset)
            
            # Comparison panel 업데이트
            self.view._update_comparison_panel_datasets()
            
            # Audit log
            duration = time.time() - start_time
            summary = dataset.get_summary()
            self.audit_logger.log_action(
                "Dataset Loaded",
                details={
                    'rows': summary.get('row_count', 0),
                    'type': dataset.dataset_type.value
                },
                duration=duration
            )
            
            self.logger.info(f"Dataset '{dataset.name}' loaded successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to load dataset: {e}", exc_info=True)
            self.fsm.trigger(Event.DATA_LOAD_FAILED)
            self.error_occurred.emit(f"Failed to load dataset: {str(e)}")
    
    def load_gene_list(self, file_path: Path):
        """유전자 리스트 파일 로드"""
        try:
            genes = self.data_loader.load_gene_list_from_file(file_path)
            
            # Filter panel에 설정
            self.view.filter_panel.set_gene_list(genes)
            
            self.audit_logger.log_action(
                "Gene List Loaded",
                details={'file': str(file_path), 'count': len(genes)}
            )
            
            self.logger.info(f"Loaded {len(genes)} genes from file")
            
        except Exception as e:
            self.logger.error(f"Failed to load gene list: {e}")
            self.error_occurred.emit(f"Failed to load gene list: {str(e)}")
    
    def switch_dataset(self, dataset_name: str):
        """현재 데이터셋 전환"""
        if dataset_name in self.datasets:
            self.current_dataset = self.datasets[dataset_name]
            # add_to_manager=False로 호출하여 중복 추가 방지
            self._update_view_with_dataset(self.current_dataset, add_to_manager=False)
            
            self.audit_logger.log_action(
                "Dataset Switched",
                details={'dataset': dataset_name}
            )
            
            self.logger.info(f"Switched to dataset: {dataset_name}")
        else:
            self.logger.warning(f"Dataset not found: {dataset_name}")
    
    def apply_filter(self, criteria: FilterCriteria):
        """
        필터 적용
        
        Args:
            criteria: 필터링 기준 (mode, gene_list 또는 통계값 포함)
        """
        import time
        start_time = time.time()
        
        if self.current_dataset is None:
            self.error_occurred.emit("No dataset loaded")
            return
        
        # 상태 전환
        if not self.fsm.trigger(Event.START_FILTER):
            self.logger.warning("Cannot filter in current state")
            return
        
        # Audit log
        self.audit_logger.log_action(
            "Apply Filter",
            details=criteria.to_dict()
        )
        
        try:
            # 필터링 모드에 따라 다르게 처리
            if criteria.mode == FilterMode.GENE_LIST:
                # Gene List 모드
                if not criteria.gene_list:
                    self.error_occurred.emit("Gene list is empty")
                    self.fsm.trigger(Event.FILTER_FAILED)
                    return
                
                filtered_df = self._filter_by_gene_list(criteria.gene_list)
                tab_name = f"Filtered: Gene List ({len(criteria.gene_list)} genes)"
                
            else:  # FilterMode.STATISTICAL
                # Statistical 모드 - 데이터셋 타입에 따라 다르게 처리
                dataset_type = self.current_dataset.dataset_type
                
                if dataset_type == DatasetType.DIFFERENTIAL_EXPRESSION:
                    # DE 데이터: adj_pvalue와 log2fc 사용
                    filtered_df = self._filter_by_statistics(
                        adj_pvalue_max=criteria.adj_pvalue_max,
                        log2fc_min=criteria.log2fc_min,
                        fdr_max=None  # DE에서는 사용 안함
                    )
                    tab_name = f"Filtered: p≤{criteria.adj_pvalue_max}, |FC|≥{criteria.log2fc_min}"
                
                elif dataset_type == DatasetType.GO_ANALYSIS:
                    # GO 데이터: fdr, ontology, direction 사용
                    filtered_df = self._filter_by_statistics(
                        adj_pvalue_max=None,  # GO에서는 사용 안함
                        log2fc_min=None,      # GO에서는 사용 안함
                        fdr_max=criteria.fdr_max,
                        ontology=criteria.ontology,
                        go_direction=criteria.go_direction
                    )
                    # 탭 이름에 필터 정보 포함 (유효숫자 줄이기)
                    filters = []
                    if criteria.fdr_max is not None:
                        # FDR 값을 과학적 표기법 또는 적절한 자릿수로 표시
                        if criteria.fdr_max < 0.001:
                            filters.append(f"FDR≤{criteria.fdr_max:.1e}")
                        else:
                            filters.append(f"FDR≤{criteria.fdr_max:.3f}")
                    if criteria.ontology != "All":
                        filters.append(criteria.ontology)
                    if criteria.go_direction != "All":
                        filters.append(criteria.go_direction)
                    tab_name = f"Filtered: {', '.join(filters)}"
                
                else:
                    self.error_occurred.emit(f"Unsupported dataset type: {dataset_type.value}")
                    self.fsm.trigger(Event.FILTER_FAILED)
                    return
            
            # 빈 결과 체크
            if filtered_df.empty:
                self.logger.warning("Filter returned no results")
                # 에러 상태로 가지 않고 정보 메시지만 표시
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.information(
                    None,
                    "No Results",
                    "No data matches the current filter criteria.\nPlease adjust your filter settings."
                )
                # SUCCESS로 전환하되 빈 결과 그대로 반환 (에러 상태 진입 방지)
                self.fsm.trigger(Event.FILTER_SUCCESS)
                return
            
            # 상태 전환
            self.fsm.trigger(Event.FILTER_SUCCESS)
            
            # Signal 방출 (GUI에서 탭 생성 처리)
            self.filter_completed.emit(filtered_df, tab_name)
            
            # Audit log
            duration = time.time() - start_time
            self.audit_logger.log_action(
                "Filtering Completed",
                details={'result_count': len(filtered_df)},
                duration=duration
            )
            
            self.logger.info(f"Filter applied: {len(filtered_df)} rows")
            
        except Exception as e:
            self.logger.error(f"Filtering failed: {e}", exc_info=True)
            self.fsm.trigger(Event.FILTER_FAILED)
            self.error_occurred.emit(f"Filtering failed: {str(e)}")
    
    def _filter_by_gene_list(self, gene_list: List[str]) -> pd.DataFrame:
        """
        유전자 리스트로 필터링 (입력 순서 유지)
        
        Args:
            gene_list: 유전자 ID/Symbol 리스트 (순서 유지됨)
            
        Returns:
            필터링된 DataFrame (gene_list 순서대로 정렬)
        """
        df = self.current_dataset.dataframe
        
        # Symbol 컬럼 우선 사용 (DE 데이터셋), 없으면 GENE_ID 사용
        if StandardColumns.SYMBOL in df.columns:
            gene_col = StandardColumns.SYMBOL
        elif StandardColumns.GENE_ID in df.columns:
            gene_col = StandardColumns.GENE_ID
        else:
            self.logger.error(f"Available columns: {df.columns.tolist()}")
            raise ValueError(f"Neither '{StandardColumns.SYMBOL}' nor '{StandardColumns.GENE_ID}' column found in dataset")
        
        # 대소문자 무시 매칭을 위한 딕셔너리
        # {소문자 유전자명: 원본 행 인덱스들}
        gene_to_indices = {}
        for idx, gene in enumerate(df[gene_col]):
            gene_lower = str(gene).lower()
            if gene_lower not in gene_to_indices:
                gene_to_indices[gene_lower] = []
            gene_to_indices[gene_lower].append(idx)
        
        # gene_list 순서대로 행 수집
        matched_indices = []
        for gene in gene_list:
            gene_lower = gene.lower()
            if gene_lower in gene_to_indices:
                matched_indices.extend(gene_to_indices[gene_lower])
        
        # 중복 제거 (순서 유지)
        seen = set()
        ordered_indices = []
        for idx in matched_indices:
            if idx not in seen:
                seen.add(idx)
                ordered_indices.append(idx)
        
        # DataFrame 재구성 (순서 유지)
        filtered = df.iloc[ordered_indices].copy()
        
        self.logger.info(
            f"Gene list filter: {len(filtered)}/{len(df)} rows matched, "
            f"order preserved from input list"
        )
        
        return filtered
    
    def _filter_by_statistics(self, adj_pvalue_max: Optional[float] = None, 
                               log2fc_min: Optional[float] = None, 
                               fdr_max: Optional[float] = None,
                               ontology: Optional[str] = None,
                               go_direction: Optional[str] = None) -> pd.DataFrame:
        """
        통계값으로 필터링 (p-value, FC)
        
        Args:
            adj_pvalue_max: 최대 adjusted p-value (DE용, optional)
            log2fc_min: 최소 절대 log2 Fold Change (DE용, optional)
            fdr_max: 최대 FDR (GO analysis용, optional)
            ontology: Ontology 필터 (GO용, optional) - "All", "BP", "MF", "CC", "KEGG"
            go_direction: Direction 필터 (GO용, optional) - "All", "UP", "DOWN", "TOTAL"
            
        Returns:
            필터링된 DataFrame
        """
        dataset_type = self.current_dataset.dataset_type
        df = self.current_dataset.dataframe.copy()
        
        if dataset_type == DatasetType.DIFFERENTIAL_EXPRESSION:
            # DE 데이터 필터링 (표준 컬럼명 직접 사용)
            adj_pval_col = StandardColumns.ADJ_PVALUE
            log2fc_col = StandardColumns.LOG2FC
            
            if not all([adj_pval_col in df.columns, log2fc_col in df.columns]):
                self.logger.error(f"Available columns: {df.columns.tolist()}")
                raise ValueError(f"Required columns not found: {adj_pval_col}, {log2fc_col}")
            
            mask = (df[adj_pval_col] <= adj_pvalue_max) & (abs(df[log2fc_col]) >= log2fc_min)
            filtered = df[mask]
            
            self.logger.info(
                f"Statistical filter (DE): {len(filtered)}/{len(df)} rows "
                f"(p≤{adj_pvalue_max}, |FC|≥{log2fc_min})"
            )
            
        elif dataset_type == DatasetType.GO_ANALYSIS:
            # GO 데이터 필터링 (표준 컬럼명 직접 사용)
            fdr_col = StandardColumns.FDR
            
            if fdr_col not in df.columns:
                self.logger.error(f"Available columns: {df.columns.tolist()}")
                raise ValueError(f"FDR column not found: {fdr_col}")
            
            # FDR 필터
            mask = df[fdr_col] <= fdr_max
            
            # Ontology 필터
            if ontology and ontology != "All":
                ontology_col = StandardColumns.ONTOLOGY
                if ontology_col in df.columns:
                    mask = mask & (df[ontology_col].str.upper() == ontology.upper())
            
            # Gene Set 필터 (UP/DOWN/TOTAL DEG)
            if go_direction and go_direction != "All":
                gene_set_col = StandardColumns.GENE_SET
                if gene_set_col in df.columns:
                    mask = mask & (df[gene_set_col].str.upper() == go_direction.upper())
            
            filtered = df[mask]
            
            filter_desc = f"FDR≤{fdr_max}"
            if ontology and ontology != "All":
                filter_desc += f", {ontology}"
            if go_direction and go_direction != "All":
                filter_desc += f", {go_direction}"
            
            self.logger.info(
                f"Statistical filter (GO): {len(filtered)}/{len(df)} rows ({filter_desc})"
            )
        else:
            raise ValueError(f"Cannot filter dataset type: {dataset_type.value}")
        
        return filtered
    
    def run_analysis(self, analysis_type: str, gene_list: List[str], 
                     adj_pvalue_cutoff: float = 0.05, log2fc_cutoff: float = 1.0):
        """
        통계 분석 실행
        
        Args:
            analysis_type: 분석 타입 ("fisher", "gsea")
            gene_list: 관심 유전자 리스트
            adj_pvalue_cutoff: Adjusted p-value 임계값 (Fisher's test용)
            log2fc_cutoff: log2 Fold Change 임계값 (Fisher's test용)
        """
        import time
        start_time = time.time()
        
        if self.current_dataset is None:
            self.error_occurred.emit("No dataset loaded")
            return
        
        if not gene_list:
            self.error_occurred.emit("No genes provided for analysis")
            return
        
        # 상태 전환
        if not self.fsm.trigger(Event.START_ANALYSIS):
            self.logger.warning("Cannot analyze in current state")
            return
        
        # Audit log
        self.audit_logger.log_action(
            f"{analysis_type.upper()} Analysis",
            details={'gene_count': len(gene_list)}
        )
        
        try:
            # 분석 실행
            if analysis_type == "fisher":
                result = self.analyzer.fisher_exact_test(
                    gene_list, self.current_dataset,
                    adj_pvalue_cutoff=adj_pvalue_cutoff,
                    log2fc_cutoff=log2fc_cutoff
                )
            elif analysis_type == "gsea":
                result = self.analyzer.gsea_lite(
                    gene_list, self.current_dataset,
                    adj_pvalue_cutoff=adj_pvalue_cutoff
                )
            else:
                raise ValueError(f"Unknown analysis type: {analysis_type}")
            
            # 상태 전환
            self.fsm.trigger(Event.ANALYSIS_SUCCESS)
            
            # Signal 방출
            self.analysis_completed.emit(result, analysis_type)
            
            # 분석 로그 저장
            log_file_path = self._save_analysis_log(analysis_type, gene_list, result, 
                                                     adj_pvalue_cutoff, log2fc_cutoff)
            
            # 결과 표시 (로그 파일 경로 포함)
            self._show_analysis_result(result, analysis_type, log_file_path)
            
            # Audit log
            duration = time.time() - start_time
            self.audit_logger.log_action(
                f"{analysis_type.upper()} Completed",
                details={'pvalue': result.get('pvalue', 'N/A')},
                duration=duration
            )
            
            self.logger.info(f"{analysis_type} analysis completed")
            
        except Exception as e:
            self.logger.error(f"Analysis failed: {e}", exc_info=True)
            self.fsm.trigger(Event.ANALYSIS_FAILED)
            self.error_occurred.emit(f"Analysis failed: {str(e)}")
    
    def compare_datasets(self, dataset_names: List[str]):
        """
        다중 데이터셋 비교
        
        Args:
            dataset_names: 비교할 데이터셋 이름 리스트
        """
        import time
        start_time = time.time()
        
        # 상태 전환
        if not self.fsm.trigger(Event.START_COMPARISON):
            self.logger.warning("Cannot compare in current state")
            return
        
        # Audit log
        self.audit_logger.log_action(
            "Compare Datasets",
            details={'datasets': dataset_names, 'count': len(dataset_names)}
        )
        
        try:
            # 데이터셋 가져오기
            datasets = [self.datasets[name] for name in dataset_names 
                       if name in self.datasets]
            
            if len(datasets) < 2:
                raise ValueError("At least 2 datasets required for comparison")
            
            # 비교 실행
            result = self.analyzer.compare_datasets(datasets)
            
            # 상태 전환
            self.fsm.trigger(Event.COMPARISON_SUCCESS)
            
            # Signal 방출
            self.comparison_completed.emit(result)
            
            # 결과 표시
            self._show_comparison_result(result)
            
            # Audit log
            duration = time.time() - start_time
            self.audit_logger.log_action(
                "Comparison Completed",
                details={
                    'common_genes': len(result.common_genes),
                    'total_genes': result.metadata.get('total_genes', 0)
                },
                duration=duration
            )
            
            self.logger.info("Dataset comparison completed")
            
        except Exception as e:
            self.logger.error(f"Comparison failed: {e}", exc_info=True)
            self.fsm.trigger(Event.COMPARISON_FAILED)
            self.error_occurred.emit(f"Comparison failed: {str(e)}")
    
    def export_data(self, file_path: Path, table_widget):
        """
        데이터 내보내기
        
        Args:
            file_path: 저장 경로
            table_widget: QTableWidget
        """
        import time
        start_time = time.time()
        
        # Audit log
        self.audit_logger.log_action(
            "Export Data",
            details={'file': str(file_path)}
        )
        
        try:
            # QTableWidget에서 데이터 추출
            df = self._table_to_dataframe(table_widget)
            
            # 파일 형식에 따라 저장
            if file_path.suffix == '.csv':
                df.to_csv(file_path, index=False)
            elif file_path.suffix == '.tsv':
                df.to_csv(file_path, sep='\t', index=False)
            elif file_path.suffix in ['.xlsx', '.xls']:
                df.to_excel(file_path, index=False)
            else:
                raise ValueError(f"Unsupported file format: {file_path.suffix}")
            
            # Audit log
            duration = time.time() - start_time
            self.audit_logger.log_action(
                "Export Completed",
                details={'rows': len(df), 'format': file_path.suffix},
                duration=duration
            )
            
            self.logger.info(f"Data exported to {file_path}")
            
        except Exception as e:
            self.logger.error(f"Export failed: {e}", exc_info=True)
            self.error_occurred.emit(f"Export failed: {str(e)}")
    
    def _update_view_with_dataset(self, dataset: Dataset, add_to_manager: bool = True):
        """
        데이터셋으로 뷰 업데이트
        
        Args:
            dataset: 업데이트할 Dataset 객체
            add_to_manager: Dataset Manager에 추가 여부 (False면 기존 항목 유지)
        """
        if dataset.dataframe is not None:
            # "Whole Dataset" 탭 찾기 및 업데이트
            for i in range(self.view.data_tabs.count()):
                tab_name = self.view.data_tabs.tabText(i)
                if tab_name == "Whole Dataset":
                    table = self.view.data_tabs.widget(i)
                    if table:
                        self.view.populate_table(table, dataset.dataframe, dataset)
                    break
            else:
                # "Whole Dataset" 탭이 없으면 첫 번째 탭 업데이트
                table = self.view.data_tabs.widget(0)
                if table:
                    self.view.populate_table(table, dataset.dataframe, dataset)
            
            # Dataset manager 업데이트 (신규 로드 시에만)
            if add_to_manager:
                metadata = {
                    'file_path': str(dataset.file_path) if dataset.file_path else '',
                    'dataset_type': dataset.dataset_type.value,
                    'row_count': len(dataset.dataframe),
                    'column_count': len(dataset.dataframe.columns)
                }
                self.view.dataset_manager.add_dataset(dataset.name, metadata=metadata)
    
    def _create_result_tab(self, df: pd.DataFrame, tab_name: str):
        """결과 탭 생성"""
        table = self.view._create_data_tab(tab_name)
        # 현재 데이터셋 정보 전달
        self.view.populate_table(table, df, self.current_dataset)
        
        # 새 탭으로 전환
        self.view.data_tabs.setCurrentWidget(table)
    
    def _table_to_dataframe(self, table_widget) -> pd.DataFrame:
        """QTableWidget를 DataFrame으로 변환"""
        rows = table_widget.rowCount()
        cols = table_widget.columnCount()
        
        # 헤더
        headers = [table_widget.horizontalHeaderItem(i).text() 
                  for i in range(cols)]
        
        # 데이터
        data = []
        for i in range(rows):
            row_data = []
            for j in range(cols):
                item = table_widget.item(i, j)
                row_data.append(item.text() if item else "")
            data.append(row_data)
        
        return pd.DataFrame(data, columns=headers)
    
    def _save_analysis_log(self, analysis_type: str, gene_list: List[str], 
                          result: dict, adj_pvalue_cutoff: float, log2fc_cutoff: float):
        """
        분석 결과를 로그 파일로 저장
        
        Args:
            analysis_type: 분석 타입
            gene_list: 입력 유전자 리스트
            result: 분석 결과
            adj_pvalue_cutoff: p-value 임계값
            log2fc_cutoff: log2FC 임계값
        """
        from datetime import datetime
        from pathlib import Path
        
        # 로그 디렉토리 생성
        log_dir = Path("analysis_logs")
        log_dir.mkdir(exist_ok=True)
        
        # 로그 파일명: analysis_type_YYYYMMDD_HHMMSS.txt
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"{analysis_type}_{timestamp}.txt"
        
        try:
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write(f"{analysis_type.upper()} ANALYSIS LOG\n")
                f.write("=" * 80 + "\n\n")
                
                # 분석 정보
                f.write(f"Date/Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Analysis Type: {analysis_type.upper()}\n")
                f.write(f"Dataset: {self.current_dataset.name}\n")
                f.write(f"Dataset Type: {self.current_dataset.dataset_type.value}\n\n")
                
                # 설정 정보
                f.write("-" * 80 + "\n")
                f.write("SETTINGS\n")
                f.write("-" * 80 + "\n")
                f.write(f"Adjusted p-value cutoff: {adj_pvalue_cutoff}\n")
                f.write(f"log2 Fold Change cutoff: {log2fc_cutoff}\n\n")
                
                # 입력 유전자 리스트
                f.write("-" * 80 + "\n")
                f.write(f"INPUT GENE LIST ({len(gene_list)} genes)\n")
                f.write("-" * 80 + "\n")
                for gene in gene_list:
                    f.write(f"{gene}\n")
                f.write("\n")
                
                # 분석 결과
                f.write("-" * 80 + "\n")
                f.write("RESULTS\n")
                f.write("-" * 80 + "\n")
                
                if analysis_type == "fisher":
                    f.write(f"P-value: {result['pvalue']:.4e}\n")
                    f.write(f"Odds Ratio: {result['odds_ratio']:.2f}\n")
                    f.write(f"Enrichment Fold: {result['enrichment_fold']:.2f}\n")
                    f.write(f"Significant: {'Yes' if result['significant'] else 'No'}\n\n")
                    
                    f.write(f"In Gene List (Significant): {result['in_list_significant']}\n")
                    f.write(f"In Gene List (Total): {result['in_list_total']}\n")
                    f.write(f"Dataset (Significant): {result['dataset_significant']}\n")
                    f.write(f"Dataset (Total): {result['dataset_total']}\n\n")
                    
                    f.write("Contingency Table:\n")
                    table = result['contingency_table']
                    f.write(f"  In List & Significant:     {table[0][0]}\n")
                    f.write(f"  In List & Not Significant: {table[0][1]}\n")
                    f.write(f"  Not in List & Significant: {table[1][0]}\n")
                    f.write(f"  Not in List & Not Sig:     {table[1][1]}\n")
                    
                elif analysis_type == "gsea":
                    f.write(f"Mean log2FC: {result['mean_log2fc']:.3f}\n")
                    f.write(f"Median log2FC: {result['median_log2fc']:.3f}\n")
                    f.write(f"Wilcoxon p-value: {result['wilcoxon_pvalue']:.4e}\n")
                    f.write(f"Enrichment Direction: {result['enrichment_direction']}\n\n")
                    
                    f.write(f"Up-regulated (significant): {result['upregulated_count']}\n")
                    f.write(f"Down-regulated (significant): {result['downregulated_count']}\n")
                    f.write(f"Total significant: {result['significant_count']}\n")
                    f.write(f"Total genes in list: {result['total_count']}\n")
                
                f.write("\n" + "=" * 80 + "\n")
            
            self.logger.info(f"Analysis log saved to {log_file}")
            return str(log_file.absolute())
            
        except Exception as e:
            self.logger.error(f"Failed to save analysis log: {e}", exc_info=True)
            return None
    
    def _show_analysis_result(self, result: dict, analysis_type: str, log_file_path: Optional[str] = None):
        """분석 결과 표시 (다이얼로그)"""
        from PyQt6.QtWidgets import QMessageBox
        
        if analysis_type == "fisher":
            # Prepare HTML fragments outside f-string to avoid backslash issues
            sig_span = '<span style="color: green;">Significant</span>'
            not_sig_span = '<span style="color: red;">Not significant</span>'
            result_text = sig_span if result['significant'] else not_sig_span
            
            message = (
                f"<h3>Fisher's Exact Test Result</h3>"
                f"<p><b>P-value:</b> {result['pvalue']:.4e}</p>"
                f"<p><b>Odds Ratio:</b> {result['odds_ratio']:.2f}</p>"
                f"<p><b>Significant genes in list:</b> {result['in_list_significant']} / {result['in_list_total']}</p>"
                f"<p><b>Total significant genes:</b> {result['dataset_significant']} / {result['dataset_total']}</p>"
                f"<p><b>Enrichment fold:</b> {result['enrichment_fold']:.2f}</p>"
                f"<p><b>Result:</b> {result_text}</p>"
            )
            
            if log_file_path:
                message += f"<hr><p><small>📝 Analysis log saved to:<br><code>{log_file_path}</code></small></p>"
        elif analysis_type == "gsea":
            message = (
                f"<h3>GSEA Lite Result</h3>"
                f"<p><b>Mean log2FC:</b> {result['mean_log2fc']:.2f}</p>"
                f"<p><b>Median log2FC:</b> {result['median_log2fc']:.2f}</p>"
                f"<p><b>Upregulated:</b> {result['upregulated_count']}</p>"
                f"<p><b>Downregulated:</b> {result['downregulated_count']}</p>"
                f"<p><b>Significant:</b> {result['significant_count']} / {result['total_count']}</p>"
                f"<p><b>Enrichment direction:</b> {result['enrichment_direction']}</p>"
                f"<p><b>Wilcoxon p-value:</b> {result.get('wilcoxon_pvalue', 'N/A')}</p>"
            )
            
            if log_file_path:
                message += f"<hr><p><small>📝 Analysis log saved to:<br><code>{log_file_path}</code></small></p>"
        else:
            message = str(result)
        
        msg_box = QMessageBox(self.view)
        msg_box.setWindowTitle(f"{analysis_type.upper()} Analysis Result")
        msg_box.setTextFormat(Qt.TextFormat.RichText)
        msg_box.setText(message)
        msg_box.exec()
    
    def _show_comparison_result(self, result: ComparisonResult):
        """비교 결과 표시"""
        if result.comparison_table is not None:
            tab_name = "Comparison Result"
            self._create_result_tab(result.comparison_table, tab_name)
    
    # ========== GO/KEGG Analysis Methods ==========
    
    def load_go_kegg_data(self, file_paths: List[Path], is_excel: bool = True, 
                          dataset_name: str = "GO/KEGG Analysis"):
        """
        GO/KEGG 분석 결과 로딩
        
        Args:
            file_paths: 파일 경로 리스트
            is_excel: Excel 파일 여부 (False면 CSV 파일들)
            dataset_name: 데이터셋 이름
        """
        try:
            from utils.go_kegg_loader import GOKEGGLoader
            
            loader = GOKEGGLoader()
            
            if is_excel:
                # 단일 Excel 파일
                dataset = loader.load_from_excel(file_paths[0], name=dataset_name)
            else:
                # 여러 CSV 파일
                dataset = loader.load_from_csv_files(file_paths, name=dataset_name)
            
            # 데이터셋 저장 (고유 이름 생성)
            unique_name = self.view.dataset_manager._generate_unique_name(dataset.name)
            dataset.name = unique_name
            self.datasets[unique_name] = dataset
            self.current_dataset = dataset
            
            # GUI 업데이트 (Whole Dataset 탭에 표시)
            self._update_view_with_dataset(dataset)
            
            # Comparison panel 업데이트
            self.view._update_comparison_panel_datasets()
            
            # 신호 발생
            self.dataset_loaded.emit(dataset.name, dataset)
            
            n_terms = len(dataset.dataframe) if dataset.dataframe is not None else 0
            self.logger.info(f"GO/KEGG data loaded: {n_terms} terms")
            self.audit_logger.log_action("GO/KEGG Data Loaded", 
                                        details={"name": dataset.name, "rows": n_terms})
            
        except Exception as e:
            self.logger.error(f"Failed to load GO/KEGG data: {e}", exc_info=True)
            self.error_occurred.emit(f"Failed to load GO/KEGG data:\n{str(e)}")
    
    def cluster_go_terms(self, dataset: Dataset, kappa_threshold: float = 0.4,
                         total_genes: Optional[int] = None):
        """
        GO Term 클러스터링 시작
        
        Args:
            dataset: GO/KEGG 데이터셋
            kappa_threshold: Kappa statistic 임계값
            total_genes: 전체 유전자 수
        """
        if dataset.dataset_type != DatasetType.GO_ANALYSIS:
            self.error_occurred.emit("Clustering is only available for GO/KEGG datasets")
            return
        
        if dataset.dataframe is None:
            self.error_occurred.emit("Dataset has no data")
            return
        
        try:
            # FSM 상태 전환
            self.fsm.trigger(Event.START_CLUSTERING)
            
            # Worker 시작
            from workers.go_workers import GOClusteringWorker
            
            self.clustering_worker = GOClusteringWorker(
                df=dataset.dataframe,
                kappa_threshold=kappa_threshold,
                total_genes=total_genes
            )
            
            self.clustering_worker.progress.connect(self.progress_updated.emit)
            self.clustering_worker.finished.connect(self._on_clustering_finished)
            self.clustering_worker.error.connect(self._on_clustering_error)
            
            self.clustering_worker.start()
            
            self.logger.info(f"Started GO term clustering (threshold={kappa_threshold})")
            
        except Exception as e:
            self.logger.error(f"Failed to start clustering: {e}", exc_info=True)
            self.fsm.trigger(Event.CLUSTERING_FAILED)
            self.error_occurred.emit(f"Failed to start clustering:\n{str(e)}")
    
    def _on_clustering_finished(self, clustered_df: pd.DataFrame, clusters: Dict):
        """클러스터링 완료 처리"""
        try:
            # FSM 상태 전환 (현재 상태가 CLUSTERING인 경우에만)
            try:
                self.fsm.trigger(Event.CLUSTERING_SUCCESS)
            except Exception as fsm_error:
                self.logger.warning(f"FSM transition ignored: {fsm_error}")
            
            # cluster_id 컬럼 확인 및 정렬
            if 'cluster_id' in clustered_df.columns:
                clustered_df = clustered_df.sort_values('cluster_id', ascending=True)
            
            # 결과를 새 탭에 표시 - "Clustered: " 접두사 사용
            tab_name = f"Clustered: {len(clusters)} clusters"
            
            # View에 결과 전달 (filter_completed 시그널 재사용)
            self.filter_completed.emit(clustered_df, tab_name)
            
            self.logger.info(f"Clustering completed: {len(clusters)} clusters from {len(clustered_df)} terms")
            self.audit_logger.log_action("GO Clustering Completed", 
                                        details={"n_clusters": len(clusters), "n_terms": len(clustered_df)})
            
            # 결과 다이얼로그 표시
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(
                self.view,
                "Clustering Complete",
                f"Successfully clustered {len(clustered_df)} GO terms into {len(clusters)} clusters.\n\n"
                f"Results sorted by cluster and displayed in new tab: '{tab_name}'"
            )
            
        except Exception as e:
            self.logger.error(f"Failed to process clustering results: {e}", exc_info=True)
            self.error_occurred.emit(f"Failed to process clustering results:\n{str(e)}")
    
    def _on_clustering_error(self, error_message: str):
        """클러스터링 오류 처리"""
        self.fsm.trigger(Event.CLUSTERING_FAILED)
        self.logger.error(f"Clustering error: {error_message}")
        self.error_occurred.emit(f"Clustering failed:\n{error_message}")
    
    def filter_go_kegg_data(
        self,
        dataset: Dataset,
        fdr_threshold: Optional[float] = None,
        ontologies: Optional[List[str]] = None,
        direction: Optional[str] = None,
        gene_count_range: Optional[tuple] = None,
        description_filter: Optional[tuple] = None
    ):
        """
        GO/KEGG 데이터 필터링
        
        Args:
            dataset: 필터링할 Dataset
            fdr_threshold: FDR 임계값 (None이면 필터링하지 않음)
            ontologies: 포함할 Ontology 리스트 (예: ['BP', 'CC'])
            direction: 방향 필터 ('UP', 'DOWN', 'TOTAL', None=모두)
            gene_count_range: Gene count 범위 (min, max) 튜플
            description_filter: Description 검색 (keyword, case_sensitive) 튜플
        """
        try:
            if dataset.dataframe is None:
                raise ValueError("Dataset has no data")
            
            df = dataset.dataframe.copy()
            original_count = len(df)
            
            # FDR 필터
            if fdr_threshold is not None and StandardColumns.FDR in df.columns:
                df = df[df[StandardColumns.FDR] <= fdr_threshold]
                self.logger.debug(f"After FDR filter: {len(df)} terms")
            
            # Ontology 필터
            if ontologies and StandardColumns.ONTOLOGY in df.columns:
                df = df[df[StandardColumns.ONTOLOGY].isin(ontologies)]
                self.logger.debug(f"After Ontology filter: {len(df)} terms")
            
            # Direction 필터
            if direction and StandardColumns.DIRECTION in df.columns:
                df = df[df[StandardColumns.DIRECTION] == direction]
                self.logger.debug(f"After Direction filter: {len(df)} terms")
            
            # Gene count 범위 필터
            if gene_count_range and StandardColumns.GENE_COUNT in df.columns:
                min_genes, max_genes = gene_count_range
                df = df[
                    (df[StandardColumns.GENE_COUNT] >= min_genes) &
                    (df[StandardColumns.GENE_COUNT] <= max_genes)
                ]
                self.logger.debug(f"After gene count filter: {len(df)} terms")
            
            # Description 검색 필터
            if description_filter and StandardColumns.DESCRIPTION in df.columns:
                keyword, case_sensitive = description_filter
                if keyword:
                    df = df[df[StandardColumns.DESCRIPTION].str.contains(
                        keyword, case=case_sensitive, na=False
                    )]
                    self.logger.debug(f"After description filter: {len(df)} terms")
            
            # 결과 로깅
            filtered_count = len(df)
            self.logger.info(
                f"GO/KEGG filtering: {original_count} → {filtered_count} terms "
                f"({filtered_count/original_count*100:.1f}%)"
            )
            
            # Audit log
            self.audit_logger.log_action(
                action="filter_go_kegg",
                details={
                    "dataset": dataset.name,
                    "original_count": original_count,
                    "filtered_count": filtered_count,
                    "fdr_threshold": fdr_threshold,
                    "ontologies": ontologies,
                    "direction": direction,
                    "gene_count_range": gene_count_range,
                    "description_keyword": description_filter[0] if description_filter else None
                }
            )
            
            # 탭 이름 생성 (Advanced Filter와 동일한 형식)
            filters = []
            if fdr_threshold is not None:
                # FDR 값을 과학적 표기법 또는 적절한 자릿수로 표시
                if fdr_threshold < 0.001:
                    filters.append(f"FDR≤{fdr_threshold:.1e}")
                else:
                    filters.append(f"FDR≤{fdr_threshold:.3f}")
            if ontologies and len(ontologies) < 4:  # 전체 선택이 아닌 경우만
                filters.append("+".join(ontologies))
            if direction:
                filters.append(direction)
            if gene_count_range:
                min_g, max_g = gene_count_range
                filters.append(f"genes:{min_g}-{max_g}")
            if description_filter and description_filter[0]:
                keyword = description_filter[0][:20]  # 최대 20자
                filters.append(f'"{keyword}"')
            
            # 필터 조건이 있으면 표시, 없으면 "All"
            if filters:
                tab_name = f"Filtered: {', '.join(filters)}"
            else:
                tab_name = f"Filtered: All ({filtered_count} terms)"
            
            self.filter_completed.emit(df, tab_name)
            
        except Exception as e:
            error_msg = f"Failed to filter GO/KEGG data: {str(e)}"
            self.logger.exception(error_msg)
            self.error_occurred.emit(error_msg)
