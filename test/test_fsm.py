"""
Unit tests for FSM (Finite State Machine)
"""

import pytest
from core.fsm import FSM, State, Event


class TestFSM:
    """FSM 테스트"""
    
    def test_initial_state(self):
        """초기 상태 테스트"""
        fsm = FSM()
        assert fsm.current_state == State.IDLE
    
    def test_valid_transition(self):
        """유효한 상태 전환 테스트"""
        fsm = FSM()
        result = fsm.trigger(Event.LOAD_DATA)
        assert result is True
        assert fsm.current_state == State.LOADING_DATA
    
    def test_invalid_transition(self):
        """유효하지 않은 상태 전환 테스트"""
        fsm = FSM()
        result = fsm.trigger(Event.FILTER_SUCCESS)  # IDLE에서 불가능한 전환
        assert result is False
        assert fsm.current_state == State.IDLE
    
    def test_transition_chain(self):
        """연속 상태 전환 테스트"""
        fsm = FSM()
        
        # IDLE -> LOADING_DATA -> DATA_LOADED
        fsm.trigger(Event.LOAD_DATA)
        assert fsm.current_state == State.LOADING_DATA
        
        fsm.trigger(Event.DATA_LOAD_SUCCESS)
        assert fsm.current_state == State.DATA_LOADED
        
        # DATA_LOADED -> FILTERING -> FILTER_COMPLETE
        fsm.trigger(Event.START_FILTER)
        assert fsm.current_state == State.FILTERING
        
        fsm.trigger(Event.FILTER_SUCCESS)
        assert fsm.current_state == State.FILTER_COMPLETE
    
    def test_error_state(self):
        """오류 상태 전환 테스트"""
        fsm = FSM()
        
        fsm.trigger(Event.LOAD_DATA)
        fsm.trigger(Event.DATA_LOAD_FAILED)
        assert fsm.current_state == State.ERROR
        
        # ERROR에서 IDLE로 복구
        fsm.trigger(Event.ERROR_RESOLVED)
        assert fsm.current_state == State.IDLE
    
    def test_callback_execution(self):
        """콜백 실행 테스트"""
        fsm = FSM()
        callback_executed = []
        
        def test_callback(**kwargs):
            callback_executed.append(True)
        
        # 상태 진입 콜백 등록
        fsm.register_on_enter(State.LOADING_DATA, test_callback)
        
        fsm.trigger(Event.LOAD_DATA)
        assert len(callback_executed) == 1
    
    def test_can_trigger(self):
        """이벤트 트리거 가능 여부 테스트"""
        fsm = FSM()
        
        assert fsm.can_trigger(Event.LOAD_DATA) is True
        assert fsm.can_trigger(Event.FILTER_SUCCESS) is False
    
    def test_get_available_events(self):
        """사용 가능한 이벤트 목록 테스트"""
        fsm = FSM()
        events = fsm.get_available_events()
        
        assert Event.LOAD_DATA in events
        assert Event.ERROR_OCCURRED in events
    
    def test_reset(self):
        """FSM 리셋 테스트"""
        fsm = FSM()
        
        fsm.trigger(Event.LOAD_DATA)
        assert fsm.current_state != State.IDLE
        
        fsm.reset()
        assert fsm.current_state == State.IDLE


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
