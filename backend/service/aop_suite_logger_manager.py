import threading
from typing import Dict, Optional
from flask import session
from .aop_suite_logger import AOPSuiteLogger

class AOPSuiteLoggerManager:
    """Session-aware logger manager for maintaining logger state per user session"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized') or not self._initialized:
            # Store loggers by session ID
            self._session_loggers: Dict[str, AOPSuiteLogger] = {}
            self._initialized = True
    
    def get_session_id(self) -> str:
        """Get or create session ID from Flask session"""
        if 'session_id' not in session:
            # This will be set when user starts a project
            return None
        return session['session_id']
    
    def start_project_session(self, project_name: str) -> str:
        """Start a new project session with given name"""
        logger = AOPSuiteLogger()
        # Override session_id to include project name
        logger.session_id = f"{project_name}_{logger.session_id}"
        
        # Store in Flask session
        session['session_id'] = logger.session_id
        session['project_name'] = project_name
        session.permanent = False  # Session expires when browser closes
        
        # Store logger
        self._session_loggers[logger.session_id] = logger
        
        return logger.session_id
    
    def get_current_logger(self) -> Optional[AOPSuiteLogger]:
        """Get the current session logger"""
        session_id = self.get_session_id()
        if not session_id:
            return None
        
        if session_id not in self._session_loggers:
            # Session exists but logger was cleaned up, recreate
            logger = AOPSuiteLogger()
            logger.session_id = session_id
            self._session_loggers[session_id] = logger
        
        return self._session_loggers[session_id]
    
    def get_project_name(self) -> Optional[str]:
        """Get current project name from session"""
        return session.get('project_name')
    
    def end_session(self) -> None:
        """End current session and cleanup"""
        session_id = self.get_session_id()
        if session_id and session_id in self._session_loggers:
            del self._session_loggers[session_id]
        session.clear()
    
    def clear_current_session_log(self):
        """Clear the current session log"""
        logger = self.get_current_logger()
        if logger:
            logger.clear_log()
    
    def cleanup_expired_sessions(self):
        """Clean up old sessions (called periodically)"""
        # Keep only recent sessions (last 24 hours)
        from datetime import datetime, timedelta
        cutoff = datetime.now() - timedelta(hours=24)
        
        expired_sessions = []
        for session_id, logger in self._session_loggers.items():
            if logger.entries and logger.entries[0].timestamp < cutoff:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            del self._session_loggers[session_id]

# Global singleton instance
logger_manager = AOPSuiteLoggerManager()
