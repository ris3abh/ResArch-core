# File: spinscribe/utils/proper_workforce_async.py (NEW APPROACH)
"""
Proper async integration with CAMEL Workforce using their native async methods.
Uses CAMEL's built-in process_task_async instead of intervention methods.
"""

import asyncio
import logging
import time
from typing import Any, Dict, Optional
from camel.tasks import Task
from camel.societies.workforce import Workforce

logger = logging.getLogger(__name__)

class ProperAsyncWorkforce:
    """
    Proper async wrapper that uses CAMEL's native async methods.
    No thread pools or event loop hacks - just proper async integration.
    """
    
    def __init__(self, workforce: Workforce, timeout_seconds: int = 1800):
        self.workforce = workforce
        self.timeout_seconds = timeout_seconds
    
    async def process_task_properly(self, task: Task) -> Task:
        """
        Process task using CAMEL's native async method.
        
        Args:
            task: The task to process
            
        Returns:
            Processed task with results
        """
        logger.info(f"🔄 Starting proper async task processing: {task.id}")
        start_time = time.time()
        
        try:
            # **FIX 1: Use CAMEL's native async method**
            logger.info("⚡ Using CAMEL's native process_task_async method")
            
            # This should work without event loop conflicts
            result = await asyncio.wait_for(
                self.workforce.process_task_async(task),
                timeout=self.timeout_seconds
            )
            
            duration = time.time() - start_time
            logger.info(f"✅ Task processing completed in {duration:.1f}s")
            return result
            
        except asyncio.TimeoutError:
            duration = time.time() - start_time
            logger.error(f"⏰ Task processing timed out after {duration:.1f}s")
            raise
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"💥 Task processing failed after {duration:.1f}s: {e}")
            raise

# Simple wrapper function
def create_proper_async_workforce(workforce: Workforce, timeout_seconds: int = 1800) -> ProperAsyncWorkforce:
    """Create a proper async workforce wrapper."""
    return ProperAsyncWorkforce(workforce, timeout_seconds)