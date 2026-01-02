"""
Logger Module for RNA-Seq Data Analysis Program

사용자 활동 기록 및 실시간 피드백을 위한 로깅 시스템을 제공합니다.

Features:
    - Audit Log: 사용자 활동 기록 (필터링, 분석, 데이터 로드 등)
    - 실시간 피드백: 작업 결과 요약 표시
    - 파일 및 GUI 로그 핸들러 지원
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
from PyQt6.QtCore import QObject, pyqtSignal


class LogLevel:
    """로그 레벨 정의"""
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


class AuditLogger:
    """
    감사 로거 (Audit Logger)
    
    사용자의 모든 활동을 시간과 함께 기록합니다.
    """
    
    def __init__(self, log_file: Optional[Path] = None):
        """
        Args:
            log_file: 로그 파일 경로 (None이면 파일 로깅 비활성화)
        """
        self.logger = logging.getLogger("audit")
        self.logger.setLevel(logging.INFO)
        
        # 기존 핸들러 제거
        self.logger.handlers.clear()
        
        # 파일 핸들러 추가
        if log_file:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.INFO)
            file_formatter = logging.Formatter(
                '%(asctime)s | %(levelname)-8s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)
    
    def log_action(self, action: str, details: Optional[dict] = None, duration: Optional[float] = None):
        """
        사용자 활동 기록
        
        Args:
            action: 활동 설명 (예: "Filtering", "Data Load", "Plot Created")
            details: 활동 상세 정보 (예: {"adj_pvalue": 0.01, "log2fc": 1.5})
            duration: 작업 소요 시간 (초)
        """
        msg_parts = [action]
        
        if details:
            detail_str = ", ".join([f"{k}={v}" for k, v in details.items()])
            msg_parts.append(f"({detail_str})")
        
        if duration is not None:
            msg_parts.append(f"[{duration:.2f}s]")
        
        message = " ".join(msg_parts)
        self.logger.info(message)
        
        return message


class QtLogHandler(logging.Handler, QObject):
    """
    PyQt6용 로그 핸들러
    
    로그 메시지를 Qt Signal로 방출하여 GUI에서 표시할 수 있도록 합니다.
    """
    
    log_signal = pyqtSignal(str, int)  # (message, level)
    
    def __init__(self):
        logging.Handler.__init__(self)
        QObject.__init__(self)
        
        # atexit 에러 방지를 위한 속성
        self.flushOnClose = False
        
        # 로그 포맷터 설정
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s: %(message)s',
            datefmt='%H:%M:%S'
        )
        self.setFormatter(formatter)
    
    def emit(self, record: logging.LogRecord):
        """로그 레코드 방출"""
        try:
            msg = self.format(record)
            self.log_signal.emit(msg, record.levelno)
        except Exception:
            self.handleError(record)
    
    def close(self):
        """핸들러 종료"""
        try:
            # Signal 연결 해제
            self.log_signal.disconnect()
        except Exception:
            pass
        super().close()


class LogBuffer:
    """
    로그 버퍼
    
    최근 N개의 로그 메시지를 메모리에 유지합니다.
    """
    
    def __init__(self, max_size: int = 1000):
        """
        Args:
            max_size: 버퍼 최대 크기
        """
        self.max_size = max_size
        self.buffer: list[tuple[str, int, datetime]] = []  # (message, level, timestamp)
    
    def add(self, message: str, level: int):
        """로그 메시지 추가"""
        timestamp = datetime.now()
        self.buffer.append((message, level, timestamp))
        
        # 버퍼 크기 제한
        if len(self.buffer) > self.max_size:
            self.buffer.pop(0)
    
    def get_recent(self, n: int = 100) -> list[tuple[str, int, datetime]]:
        """최근 N개의 로그 메시지 반환"""
        return self.buffer[-n:]
    
    def clear(self):
        """버퍼 초기화"""
        self.buffer.clear()
    
    def search(self, keyword: str) -> list[tuple[str, int, datetime]]:
        """키워드로 로그 검색"""
        return [(msg, level, ts) for msg, level, ts in self.buffer 
                if keyword.lower() in msg.lower()]


def setup_logger(log_dir: Optional[Path] = None) -> logging.Logger:
    """
    전역 로거 설정
    
    Args:
        log_dir: 로그 파일 저장 디렉토리 (None이면 현재 작업 디렉토리/logs)
        
    Returns:
        설정된 루트 로거
    """
    # 로그 디렉토리 설정
    if log_dir is None:
        log_dir = Path.cwd() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # 루트 로거 가져오기
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    
    # 기존 핸들러 제거
    logger.handlers.clear()
    
    # 콘솔 핸들러
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '%(levelname)-8s | %(name)-20s | %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # 파일 핸들러 (상세 로그)
    log_file = log_dir / f"rna_seq_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)-20s | %(funcName)-20s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    logger.info(f"Logger initialized. Log file: {log_file}")
    
    return logger


def get_audit_logger() -> AuditLogger:
    """감사 로거 인스턴스 반환 (싱글톤)"""
    if not hasattr(get_audit_logger, "_instance"):
        log_dir = Path.cwd() / "logs"
        audit_log_file = log_dir / f"audit_{datetime.now().strftime('%Y%m%d')}.log"
        get_audit_logger._instance = AuditLogger(audit_log_file)
    return get_audit_logger._instance
