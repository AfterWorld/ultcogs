"""
crewbattles/logger.py
Enhanced logging system for crew management
"""

import logging
from pathlib import Path
from typing import Optional, Any
import datetime

from .constants import CrewSettings


class EnhancedCrewLogger:
    """Enhanced logging with structured output and file rotation"""
    
    def __init__(self, cog_name: str, data_path: Path):
        self.cog_name = cog_name
        self.data_path = data_path
        self.log_dir = data_path / "Logs"
        self.log_dir.mkdir(exist_ok=True)
        
        # Setup structured logging
        self.logger = logging.getLogger(f"{cog_name}_Enhanced")
        self._setup_logger()
    
    def _setup_logger(self):
        """Setup enhanced file logging with rotation"""
        if not self.logger.handlers:  # Avoid duplicate handlers
            log_file = self.log_dir / "crew_enhanced.log"
            
            # Create rotating file handler
            try:
                from logging.handlers import RotatingFileHandler
                handler = RotatingFileHandler(
                    log_file, 
                    maxBytes=CrewSettings.LOG_MAX_BYTES, 
                    backupCount=CrewSettings.LOG_BACKUP_COUNT, 
                    encoding='utf-8'
                )
            except ImportError:
                # Fallback to regular file handler
                handler = logging.FileHandler(log_file, encoding='utf-8')
            
            formatter = logging.Formatter(
                '[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def log_crew_action(
        self, 
        action: str, 
        guild_id: int, 
        user_id: Optional[int] = None, 
        crew_name: Optional[str] = None, 
        **kwargs
    ):
        """Log structured crew actions with context"""
        # Build structured message
        message_parts = [f"CREW_ACTION: {action}"]
        
        if crew_name:
            message_parts.append(f"Crew: {crew_name}")
        if user_id:
            message_parts.append(f"User: {user_id}")
        
        message_parts.append(f"Guild: {guild_id}")
        
        # Add additional context
        if kwargs:
            details = ", ".join([f"{k}={v}" for k, v in kwargs.items()])
            message_parts.append(f"Details: {details}")
        
        message = " | ".join(message_parts)
        
        self.logger.info(message)
        print(f"[CREW_LOG] {message}")
    
    def log_error_with_context(
        self, 
        error: Exception, 
        context: str, 
        guild_id: Optional[int] = None,
        user_id: Optional[int] = None,
        **kwargs
    ):
        """Log errors with additional context"""
        message_parts = [f"ERROR: {context}"]
        message_parts.append(f"Exception: {type(error).__name__}: {str(error)}")
        
        if guild_id:
            message_parts.append(f"Guild: {guild_id}")
        if user_id:
            message_parts.append(f"User: {user_id}")
        
        if kwargs:
            details = ", ".join([f"{k}={v}" for k, v in kwargs.items()])
            message_parts.append(f"Context: {details}")
        
        message = " | ".join(message_parts)
        
        self.logger.error(message)
        print(f"[ERROR] {message}")
    
    def log_performance(
        self, 
        operation: str, 
        duration: float, 
        guild_id: Optional[int] = None,
        **kwargs
    ):
        """Log performance metrics"""
        message_parts = [f"PERFORMANCE: {operation}"]
        message_parts.append(f"Duration: {duration:.3f}s")
        
        if guild_id:
            message_parts.append(f"Guild: {guild_id}")
        
        if kwargs:
            details = ", ".join([f"{k}={v}" for k, v in kwargs.items()])
            message_parts.append(f"Metrics: {details}")
        
        message = " | ".join(message_parts)
        
        # Log as warning if operation is slow
        if duration > 5.0:
            self.logger.warning(f"SLOW_OPERATION: {message}")
        else:
            self.logger.info(message)
        
        print(f"[PERF] {message}")
    
    def log_data_operation(
        self, 
        operation: str, 
        guild_id: int, 
        success: bool,
        **kwargs
    ):
        """Log data operations (save, load, backup, etc.)"""
        status = "SUCCESS" if success else "FAILED"
        message_parts = [f"DATA_OP: {operation} - {status}"]
        message_parts.append(f"Guild: {guild_id}")
        
        if kwargs:
            details = ", ".join([f"{k}={v}" for k, v in kwargs.items()])
            message_parts.append(f"Details: {details}")
        
        message = " | ".join(message_parts)
        
        if success:
            self.logger.info(message)
        else:
            self.logger.error(message)
        
        print(f"[DATA] {message}")
    
    def log_user_action(
        self, 
        action: str, 
        user_id: int, 
        guild_id: int,
        success: bool = True,
        **kwargs
    ):
        """Log user-initiated actions"""
        status = "SUCCESS" if success else "FAILED"
        message_parts = [f"USER_ACTION: {action} - {status}"]
        message_parts.append(f"User: {user_id}")
        message_parts.append(f"Guild: {guild_id}")
        
        if kwargs:
            details = ", ".join([f"{k}={v}" for k, v in kwargs.items()])
            message_parts.append(f"Details: {details}")
        
        message = " | ".join(message_parts)
        
        if success:
            self.logger.info(message)
        else:
            self.logger.warning(message)
        
        print(f"[USER] {message}")
    
    def log_system_event(self, event: str, **kwargs):
        """Log system-level events"""
        message_parts = [f"SYSTEM: {event}"]
        
        if kwargs:
            details = ", ".join([f"{k}={v}" for k, v in kwargs.items()])
            message_parts.append(f"Details: {details}")
        
        message = " | ".join(message_parts)
        
        self.logger.info(message)
        print(f"[SYSTEM] {message}")
    
    def info(self, message: str):
        """Log info message"""
        self.logger.info(message)
        print(f"[INFO] [Enhanced] {message}")
    
    def warning(self, message: str):
        """Log warning message"""
        self.logger.warning(message)
        print(f"[WARNING] [Enhanced] {message}")
    
    def error(self, message: str):
        """Log error message"""
        self.logger.error(message)
        print(f"[ERROR] [Enhanced] {message}")
    
    def debug(self, message: str):
        """Log debug message"""
        self.logger.debug(message)
        print(f"[DEBUG] [Enhanced] {message}")
    
    def get_recent_logs(self, lines: int = 50) -> list:
        """Get recent log entries"""
        try:
            log_file = self.log_dir / "crew_enhanced.log"
            if log_file.exists():
                with open(log_file, 'r', encoding='utf-8') as f:
                    return f.readlines()[-lines:]
            return []
        except Exception as e:
            self.error(f"Failed to read recent logs: {e}")
            return []
    
    def clear_old_logs(self, days_to_keep: int = 30):
        """Clear log files older than specified days"""
        try:
            cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days_to_keep)
            
            for log_file in self.log_dir.glob("*.log*"):
                file_time = datetime.datetime.fromtimestamp(log_file.stat().st_mtime)
                if file_time < cutoff_date:
                    log_file.unlink()
                    self.info(f"Removed old log file: {log_file}")
        except Exception as e:
            self.error(f"Error cleaning up old logs: {e}")


# Decorator for logging function calls
def log_function_call(logger: EnhancedCrewLogger):
    """Decorator to log function calls with timing"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            import time
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                logger.log_performance(
                    f"{func.__name__}", 
                    duration,
                    args_count=len(args),
                    kwargs_count=len(kwargs)
                )
                
                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.log_error_with_context(
                    e, 
                    f"Function {func.__name__} failed",
                    duration=duration
                )
                raise
        
        return wrapper
    return decorator