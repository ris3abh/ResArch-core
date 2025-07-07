# File: spinscribe/utils/logging_config.py
"""
Clean logging configuration for SpinScribe that shows only important messages.
"""

import logging
import logging.config
from pathlib import Path

def setup_clean_logging(log_file: str = None, show_agent_communication: bool = True) -> None:
    """
    Set up clean logging that shows only important SpinScribe messages and agent communication.
    
    Args:
        log_file: Optional log file path
        show_agent_communication: Whether to show agent communication messages
    """
    
    # Create logs directory if needed
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Logging configuration
    config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'clean': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'datefmt': '%H:%M:%S'
            },
            'agent_communication': {
                'format': '🤖 %(levelname)s - %(name)s: %(message)s'
            },
            'detailed': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s'
            }
        },
        'handlers': {
            'console': {
                'level': 'INFO',
                'class': 'logging.StreamHandler',
                'formatter': 'clean'
            }
        },
        'loggers': {
            # SpinScribe loggers - show important messages
            'spinscribe': {
                'handlers': ['console'],
                'level': 'INFO',
                'propagate': False
            },
            '__main__': {
                'handlers': ['console'],
                'level': 'INFO',
                'propagate': False
            },
            'scripts': {
                'handlers': ['console'],
                'level': 'INFO',
                'propagate': False
            },
            
            # CAMEL loggers - reduce noise but show important workflow messages
            'camel.agents.chat_agent': {
                'handlers': ['console'],
                'level': 'INFO' if show_agent_communication else 'WARNING',
                'propagate': False
            },
            'camel.societies.workforce': {
                'handlers': ['console'],
                'level': 'INFO',
                'propagate': False
            },
            'camel.tasks': {
                'handlers': ['console'],
                'level': 'INFO',
                'propagate': False
            },
            'camel.toolkits.task_planning_toolkit': {
                'handlers': ['console'],
                'level': 'INFO',
                'propagate': False
            },
            
            # Suppress noisy loggers
            'httpcore': {
                'handlers': [],
                'level': 'WARNING',
                'propagate': False
            },
            'openai': {
                'handlers': [],
                'level': 'WARNING',
                'propagate': False
            },
            'urllib3': {
                'handlers': [],
                'level': 'WARNING',
                'propagate': False
            },
            'asyncio': {
                'handlers': [],
                'level': 'WARNING',
                'propagate': False
            }
        },
        'root': {
            'level': 'WARNING',
            'handlers': ['console']
        }
    }
    
    # Add file handler if log file specified
    if log_file:
        config['handlers']['file'] = {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': log_file,
            'formatter': 'detailed'
        }
        # Add file handler to all SpinScribe loggers
        for logger_name in ['spinscribe', '__main__', 'scripts']:
            config['loggers'][logger_name]['handlers'].append('file')
    
    # Apply configuration
    logging.config.dictConfig(config)
    
    # Log startup message
    logger = logging.getLogger('spinscribe')
    logger.info("🚀 SpinScribe logging initialized - showing clean output")