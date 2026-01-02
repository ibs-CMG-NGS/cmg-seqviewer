"""
Finite State Machine (FSM) for RNA-Seq Data Analysis Program

이 모듈은 프로그램의 상태 관리를 위한 유한 상태 머신을 정의합니다.

States (상태):
    - IDLE: 초기 상태, 사용자 입력 대기
    - LOADING_DATA: 데이터셋 로딩 중
    - DATA_LOADED: 데이터셋 로드 완료
    - FILTERING: 필터링 작업 수행 중
    - FILTER_COMPLETE: 필터링 완료
    - ANALYZING: 통계 분석 수행 중 (Fisher's test, GSEA 등)
    - ANALYSIS_COMPLETE: 분석 완료
    - COMPARING: 다중 데이터셋 비교 중
    - COMPARISON_COMPLETE: 비교 완료
    - PLOTTING: 시각화 생성 중
    - EXPORTING: 데이터 내보내기 중
    - ERROR: 오류 상태

Transitions (전이):
    각 상태 간 전환은 이벤트에 의해 트리거됩니다.
    예: load_data 이벤트 → IDLE에서 LOADING_DATA로 전환
"""

from enum import Enum, auto
from typing import Callable, Dict, Optional, Set
from dataclasses import dataclass
import logging


class State(Enum):
    """프로그램 상태 정의"""
    IDLE = auto()                    # 초기 상태
    LOADING_DATA = auto()            # 데이터 로딩 중
    DATA_LOADED = auto()             # 데이터 로드 완료
    FILTERING = auto()               # 필터링 중
    FILTER_COMPLETE = auto()         # 필터링 완료
    ANALYZING = auto()               # 통계 분석 중
    ANALYSIS_COMPLETE = auto()       # 분석 완료
    COMPARING = auto()               # 다중 데이터셋 비교 중
    COMPARISON_COMPLETE = auto()     # 비교 완료
    CLUSTERING_GO = auto()           # GO Term 클러스터링 중
    CLUSTERING_COMPLETE = auto()     # 클러스터링 완료
    PLOTTING = auto()                # 시각화 생성 중
    EXPORTING = auto()               # 데이터 내보내기 중
    ERROR = auto()                   # 오류 상태


class Event(Enum):
    """상태 전환을 트리거하는 이벤트"""
    LOAD_DATA = auto()               # 데이터 로드 시작
    DATA_LOAD_SUCCESS = auto()       # 데이터 로드 성공
    DATA_LOAD_FAILED = auto()        # 데이터 로드 실패
    START_FILTER = auto()            # 필터링 시작
    FILTER_SUCCESS = auto()          # 필터링 성공
    FILTER_FAILED = auto()           # 필터링 실패
    START_ANALYSIS = auto()          # 분석 시작
    ANALYSIS_SUCCESS = auto()        # 분석 성공
    ANALYSIS_FAILED = auto()         # 분석 실패
    START_COMPARISON = auto()        # 비교 시작
    COMPARISON_SUCCESS = auto()      # 비교 성공
    COMPARISON_FAILED = auto()       # 비교 실패
    START_CLUSTERING = auto()        # GO Term 클러스터링 시작
    CLUSTERING_SUCCESS = auto()      # 클러스터링 성공
    CLUSTERING_FAILED = auto()       # 클러스터링 실패
    START_PLOT = auto()              # 시각화 시작
    PLOT_COMPLETE = auto()           # 시각화 완료
    START_EXPORT = auto()            # 내보내기 시작
    EXPORT_COMPLETE = auto()         # 내보내기 완료
    RESET = auto()                   # 초기 상태로 리셋
    ERROR_OCCURRED = auto()          # 오류 발생
    ERROR_RESOLVED = auto()          # 오류 해결


@dataclass
class Transition:
    """상태 전환 정의"""
    from_state: State
    event: Event
    to_state: State
    callback: Optional[Callable] = None  # 전환 시 실행할 콜백 함수


class FSM:
    """
    유한 상태 머신 (Finite State Machine)
    
    프로그램의 상태를 관리하고, 이벤트에 따라 상태 전환을 수행합니다.
    각 전환 시 로깅을 수행하고, 등록된 콜백 함수를 실행합니다.
    """
    
    def __init__(self, initial_state: State = State.IDLE):
        """
        FSM 초기화
        
        Args:
            initial_state: 초기 상태 (기본값: State.IDLE)
        """
        self.current_state = initial_state
        self.logger = logging.getLogger(__name__)
        
        # 상태 전환 테이블: {(from_state, event): Transition}
        self.transitions: Dict[tuple[State, Event], Transition] = {}
        
        # 상태 진입/이탈 시 실행할 콜백
        self.on_enter_callbacks: Dict[State, list[Callable]] = {}
        self.on_exit_callbacks: Dict[State, list[Callable]] = {}
        
        # 상태 변경 리스너 (GUI 업데이트 등)
        self.state_change_listeners: list[Callable[[State, State], None]] = []
        
        # 기본 전환 규칙 등록
        self._register_default_transitions()
        
        self.logger.info(f"FSM initialized with state: {self.current_state.name}")
    
    def _register_default_transitions(self):
        """기본 상태 전환 규칙 등록"""
        
        # IDLE 상태에서의 전환
        self.add_transition(State.IDLE, Event.LOAD_DATA, State.LOADING_DATA)
        self.add_transition(State.IDLE, Event.START_FILTER, State.FILTERING)  # 데이터 로드 후 IDLE로 돌아간 경우 대비
        
        # LOADING_DATA 상태에서의 전환
        self.add_transition(State.LOADING_DATA, Event.DATA_LOAD_SUCCESS, State.DATA_LOADED)
        self.add_transition(State.LOADING_DATA, Event.DATA_LOAD_FAILED, State.ERROR)
        
        # DATA_LOADED 상태에서의 전환
        self.add_transition(State.DATA_LOADED, Event.START_FILTER, State.FILTERING)
        self.add_transition(State.DATA_LOADED, Event.START_ANALYSIS, State.ANALYZING)
        self.add_transition(State.DATA_LOADED, Event.START_COMPARISON, State.COMPARING)
        self.add_transition(State.DATA_LOADED, Event.START_PLOT, State.PLOTTING)
        self.add_transition(State.DATA_LOADED, Event.START_EXPORT, State.EXPORTING)
        self.add_transition(State.DATA_LOADED, Event.LOAD_DATA, State.LOADING_DATA)
        
        # FILTERING 상태에서의 전환
        self.add_transition(State.FILTERING, Event.FILTER_SUCCESS, State.FILTER_COMPLETE)
        self.add_transition(State.FILTERING, Event.FILTER_FAILED, State.ERROR)
        
        # FILTER_COMPLETE 상태에서의 전환
        self.add_transition(State.FILTER_COMPLETE, Event.START_FILTER, State.FILTERING)
        self.add_transition(State.FILTER_COMPLETE, Event.START_ANALYSIS, State.ANALYZING)
        self.add_transition(State.FILTER_COMPLETE, Event.START_PLOT, State.PLOTTING)
        self.add_transition(State.FILTER_COMPLETE, Event.START_EXPORT, State.EXPORTING)
        self.add_transition(State.FILTER_COMPLETE, Event.LOAD_DATA, State.LOADING_DATA)  # 새 데이터셋 로드 허용
        self.add_transition(State.FILTER_COMPLETE, Event.RESET, State.DATA_LOADED)
        
        # ANALYZING 상태에서의 전환
        self.add_transition(State.ANALYZING, Event.ANALYSIS_SUCCESS, State.ANALYSIS_COMPLETE)
        self.add_transition(State.ANALYZING, Event.ANALYSIS_FAILED, State.ERROR)
        
        # ANALYSIS_COMPLETE 상태에서의 전환
        self.add_transition(State.ANALYSIS_COMPLETE, Event.START_ANALYSIS, State.ANALYZING)  # 다른 분석 실행 허용
        self.add_transition(State.ANALYSIS_COMPLETE, Event.START_FILTER, State.FILTERING)  # 필터링 허용
        self.add_transition(State.ANALYSIS_COMPLETE, Event.START_PLOT, State.PLOTTING)
        self.add_transition(State.ANALYSIS_COMPLETE, Event.START_EXPORT, State.EXPORTING)
        self.add_transition(State.ANALYSIS_COMPLETE, Event.LOAD_DATA, State.LOADING_DATA)  # 새 데이터셋 로드 허용
        self.add_transition(State.ANALYSIS_COMPLETE, Event.RESET, State.DATA_LOADED)
        
        # COMPARING 상태에서의 전환
        self.add_transition(State.COMPARING, Event.COMPARISON_SUCCESS, State.COMPARISON_COMPLETE)
        self.add_transition(State.COMPARING, Event.COMPARISON_FAILED, State.ERROR)
        
        # COMPARISON_COMPLETE 상태에서의 전환
        self.add_transition(State.COMPARISON_COMPLETE, Event.START_PLOT, State.PLOTTING)
        self.add_transition(State.COMPARISON_COMPLETE, Event.START_EXPORT, State.EXPORTING)
        self.add_transition(State.COMPARISON_COMPLETE, Event.RESET, State.DATA_LOADED)
        
        # PLOTTING 상태에서의 전환
        self.add_transition(State.PLOTTING, Event.PLOT_COMPLETE, State.DATA_LOADED)
        
        # EXPORTING 상태에서의 전환
        self.add_transition(State.EXPORTING, Event.EXPORT_COMPLETE, State.DATA_LOADED)
        
        # ERROR 상태에서의 전환
        self.add_transition(State.ERROR, Event.ERROR_RESOLVED, State.IDLE)
        self.add_transition(State.ERROR, Event.RESET, State.IDLE)
        
        # 모든 상태에서 ERROR로 전환 가능
        for state in State:
            if state != State.ERROR:
                self.add_transition(state, Event.ERROR_OCCURRED, State.ERROR)
    
    def add_transition(self, from_state: State, event: Event, to_state: State, 
                      callback: Optional[Callable] = None):
        """
        새로운 상태 전환 규칙 추가
        
        Args:
            from_state: 시작 상태
            event: 전환을 트리거하는 이벤트
            to_state: 목표 상태
            callback: 전환 시 실행할 콜백 함수 (선택사항)
        """
        transition = Transition(from_state, event, to_state, callback)
        self.transitions[(from_state, event)] = transition
        self.logger.debug(f"Transition added: {from_state.name} --[{event.name}]--> {to_state.name}")
    
    def trigger(self, event: Event, **kwargs) -> bool:
        """
        이벤트를 트리거하여 상태 전환 시도
        
        Args:
            event: 발생한 이벤트
            **kwargs: 콜백 함수에 전달할 추가 인자
            
        Returns:
            bool: 전환 성공 여부
        """
        key = (self.current_state, event)
        
        if key not in self.transitions:
            self.logger.warning(
                f"Invalid transition: {self.current_state.name} with event {event.name}"
            )
            return False
        
        transition = self.transitions[key]
        old_state = self.current_state
        new_state = transition.to_state
        
        # 상태 이탈 콜백 실행
        self._execute_callbacks(self.on_exit_callbacks.get(old_state, []), **kwargs)
        
        # 상태 전환
        self.current_state = new_state
        self.logger.info(
            f"State transition: {old_state.name} --[{event.name}]--> {new_state.name}"
        )
        
        # 전환 콜백 실행
        if transition.callback:
            transition.callback(**kwargs)
        
        # 상태 진입 콜백 실행
        self._execute_callbacks(self.on_enter_callbacks.get(new_state, []), **kwargs)
        
        # 상태 변경 리스너 알림
        for listener in self.state_change_listeners:
            listener(old_state, new_state)
        
        return True
    
    def _execute_callbacks(self, callbacks: list[Callable], **kwargs):
        """콜백 함수 리스트 실행"""
        for callback in callbacks:
            try:
                callback(**kwargs)
            except Exception as e:
                self.logger.error(f"Callback execution failed: {e}", exc_info=True)
    
    def register_on_enter(self, state: State, callback: Callable):
        """상태 진입 시 실행할 콜백 등록"""
        if state not in self.on_enter_callbacks:
            self.on_enter_callbacks[state] = []
        self.on_enter_callbacks[state].append(callback)
    
    def register_on_exit(self, state: State, callback: Callable):
        """상태 이탈 시 실행할 콜백 등록"""
        if state not in self.on_exit_callbacks:
            self.on_exit_callbacks[state] = []
        self.on_exit_callbacks[state].append(callback)
    
    def add_state_change_listener(self, listener: Callable[[State, State], None]):
        """상태 변경 리스너 추가 (GUI 업데이트 등)"""
        self.state_change_listeners.append(listener)
    
    def can_trigger(self, event: Event) -> bool:
        """현재 상태에서 특정 이벤트를 트리거할 수 있는지 확인"""
        return (self.current_state, event) in self.transitions
    
    def get_available_events(self) -> Set[Event]:
        """현재 상태에서 가능한 이벤트 목록 반환"""
        return {event for (state, event) in self.transitions.keys() 
                if state == self.current_state}
    
    def reset(self):
        """FSM을 초기 상태로 리셋"""
        old_state = self.current_state
        self.current_state = State.IDLE
        self.logger.info(f"FSM reset: {old_state.name} --> {State.IDLE.name}")
        
        for listener in self.state_change_listeners:
            listener(old_state, State.IDLE)
