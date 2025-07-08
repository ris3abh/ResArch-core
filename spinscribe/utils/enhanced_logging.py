# ─── FILE: spinscribe/utils/enhanced_logging.py ─────────────────
"""
Enhanced logging system for SpinScribe with real-time monitoring.
NEW FILE - Add this to your project.
"""

import logging
import sys
import time
from typing import Dict, Any, Optional
from datetime import datetime
import json
from pathlib import Path
import threading
from contextlib import contextmanager

class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors and emojis for better readability."""
    
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
    }
    
    EMOJIS = {
        'DEBUG': '🔍',
        'INFO': '✅',
        'WARNING': '⚠️',
        'ERROR': '❌',
        'CRITICAL': '💥',
    }
    
    RESET = '\033[0m'
    
    def format(self, record):
        color = self.COLORS.get(record.levelname, '')
        emoji = self.EMOJIS.get(record.levelname, '')
        reset = self.RESET
        
        timestamp = datetime.fromtimestamp(record.created).strftime('%H:%M:%S.%f')[:-3]
        formatted = f"{color}{emoji} {timestamp} [{record.levelname:8}] {record.name:<20} {reset}{record.getMessage()}"
        
        if record.exc_info:
            formatted += f"\n{self.formatException(record.exc_info)}"
        
        return formatted

class WorkflowTracker:
    """Tracks workflow progress and agent states in real-time."""
    
    def __init__(self):
        self.workflow_states: Dict[str, Dict[str, Any]] = {}
        self.checkpoint_events: list = []
        self.agent_activities: Dict[str, list] = {}
        self.start_time = time.time()
        self._lock = threading.Lock()
    
    def start_workflow(self, workflow_id: str, details: Dict[str, Any]):
        """Track workflow start."""
        with self._lock:
            self.workflow_states[workflow_id] = {
                'status': 'started',
                'start_time': time.time(),
                'details': details,
                'current_stage': 'initialization',
                'agents_involved': [],
                'checkpoints_created': 0,
                'checkpoints_resolved': 0
            }
            
        logger = logging.getLogger('workflow_tracker')
        logger.info(f"🚀 WORKFLOW STARTED: {workflow_id}")
        logger.info(f"📋 Details: {json.dumps(details, indent=2)}")
    
    def update_stage(self, workflow_id: str, stage: str, agent: str = None):
        """Update current workflow stage."""
        with self._lock:
            if workflow_id in self.workflow_states:
                self.workflow_states[workflow_id]['current_stage'] = stage
                if agent and agent not in self.workflow_states[workflow_id]['agents_involved']:
                    self.workflow_states[workflow_id]['agents_involved'].append(agent)
        
        logger = logging.getLogger('workflow_tracker')
        logger.info(f"🔄 STAGE UPDATE: {workflow_id} → {stage}" + (f" (Agent: {agent})" if agent else ""))
    
    def track_checkpoint(self, workflow_id: str, checkpoint_id: str, checkpoint_type: str, status: str):
        """Track checkpoint events."""
        event = {
            'workflow_id': workflow_id,
            'checkpoint_id': checkpoint_id,
            'checkpoint_type': checkpoint_type,
            'status': status,
            'timestamp': time.time()
        }
        
        with self._lock:
            self.checkpoint_events.append(event)
            if workflow_id in self.workflow_states:
                if status == 'created':
                    self.workflow_states[workflow_id]['checkpoints_created'] += 1
                elif status in ['approved', 'rejected', 'needs_revision']:
                    self.workflow_states[workflow_id]['checkpoints_resolved'] += 1
        
        logger = logging.getLogger('checkpoint_tracker')
        logger.info(f"✋ CHECKPOINT {status.upper()}: {checkpoint_type} ({checkpoint_id[:8]}...)")
    
    def track_agent_activity(self, agent_name: str, activity: str, details: Dict[str, Any] = None):
        """Track individual agent activities."""
        activity_record = {
            'activity': activity,
            'timestamp': time.time(),
            'details': details or {}
        }
        
        with self._lock:
            if agent_name not in self.agent_activities:
                self.agent_activities[agent_name] = []
            self.agent_activities[agent_name].append(activity_record)
        
        logger = logging.getLogger(f'agent.{agent_name}')
        logger.info(f"🤖 AGENT ACTIVITY: {activity}" + (f" - {details}" if details else ""))
    
    def get_status_summary(self) -> Dict[str, Any]:
        """Get current status summary."""
        with self._lock:
            return {
                'runtime_seconds': time.time() - self.start_time,
                'active_workflows': len([w for w in self.workflow_states.values() if w['status'] != 'completed']),
                'total_checkpoints': len(self.checkpoint_events),
                'active_agents': len(self.agent_activities),
                'workflow_states': dict(self.workflow_states),
                'recent_checkpoints': self.checkpoint_events[-5:] if self.checkpoint_events else []
            }

# Global workflow tracker instance
workflow_tracker = WorkflowTracker()

def setup_enhanced_logging(log_level: str = "INFO", enable_file_logging: bool = True) -> None:
    """Setup enhanced logging with real-time monitoring."""
    
    # Create logs directory
    logs_dir = Path("./logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(ColoredFormatter())
    console_handler.setLevel(getattr(logging, log_level.upper()))
    root_logger.addHandler(console_handler)
    
    # File handler for detailed logs
    if enable_file_logging:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_handler = logging.FileHandler(
            logs_dir / f"spinscribe_detailed_{timestamp}.log",
            encoding='utf-8'
        )
        file_formatter = logging.Formatter(
            '%(asctime)s [%(levelname)8s] %(name)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(logging.DEBUG)
        root_logger.addHandler(file_handler)
    
    # Setup specific loggers with appropriate levels
    loggers_config = {
        'spinscribe': logging.INFO,
        'workflow_tracker': logging.INFO,
        'checkpoint_tracker': logging.INFO,
        'agent': logging.INFO,
        'camel': logging.WARNING,  # Reduce CAMEL noise
        'qdrant_client': logging.WARNING,
        'openai': logging.WARNING,
        'httpx': logging.WARNING,
    }
    
    for logger_name, level in loggers_config.items():
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)
    
    # Log system startup
    main_logger = logging.getLogger('spinscribe.system')
    main_logger.info("🔧 Enhanced logging system initialized")
    main_logger.info(f"📊 Log level: {log_level}")

@contextmanager
def log_execution_time(operation_name: str, logger_name: str = 'spinscribe.timing'):
    """Context manager to log execution time of operations."""
    logger = logging.getLogger(logger_name)
    start_time = time.time()
    
    logger.info(f"⏱️ START: {operation_name}")
    try:
        yield
        duration = time.time() - start_time
        logger.info(f"✅ COMPLETED: {operation_name} in {duration:.2f}s")
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"❌ FAILED: {operation_name} after {duration:.2f}s - {str(e)}")
        raise
