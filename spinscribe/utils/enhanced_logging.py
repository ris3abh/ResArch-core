# ─── COMPLETE FIXED FILE: spinscribe/utils/enhanced_logging.py ───

"""
Enhanced logging utilities for SpinScribe workflow tracking.
COMPLETE FIXED VERSION with comprehensive tracking and fallbacks.
"""

import logging
import time
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from contextlib import contextmanager
from pathlib import Path

# Global workflow tracker instance
workflow_tracker = None

class WorkflowTracker:
    """
    Tracks workflow execution stages and performance metrics.
    """
    
    def __init__(self):
        self.workflows = {}
        self.stage_history = {}
        self.performance_metrics = {}
        
    def start_workflow(self, workflow_id: str, metadata: Dict[str, Any] = None):
        """
        Start tracking a new workflow.
        
        Args:
            workflow_id: Unique workflow identifier
            metadata: Optional workflow metadata
        """
        try:
            self.workflows[workflow_id] = {
                "id": workflow_id,
                "start_time": time.time(),
                "current_stage": "initialized",
                "stages": [],
                "metadata": metadata or {},
                "status": "running"
            }
            
            self.stage_history[workflow_id] = []
            
            logging.info(f"🚀 Workflow started: {workflow_id}")
            
        except Exception as e:
            logging.warning(f"⚠️ Failed to start workflow tracking: {e}")
    
    def update_stage(self, workflow_id: str, stage: str, data: Dict[str, Any] = None):
        """
        Update the current stage of a workflow.
        
        Args:
            workflow_id: Workflow identifier
            stage: Current stage name
            data: Optional stage data
        """
        try:
            if workflow_id not in self.workflows:
                # Create workflow if it doesn't exist
                self.start_workflow(workflow_id, {"auto_created": True})
            
            workflow = self.workflows[workflow_id]
            previous_stage = workflow.get("current_stage")
            current_time = time.time()
            
            # Record stage transition
            stage_info = {
                "stage": stage,
                "timestamp": current_time,
                "previous_stage": previous_stage,
                "data": data or {}
            }
            
            workflow["current_stage"] = stage
            workflow["stages"].append(stage_info)
            
            if workflow_id not in self.stage_history:
                self.stage_history[workflow_id] = []
            
            self.stage_history[workflow_id].append(stage_info)
            
            # Calculate stage duration if there was a previous stage
            if previous_stage and len(workflow["stages"]) > 1:
                previous_timestamp = workflow["stages"][-2]["timestamp"]
                duration = current_time - previous_timestamp
                stage_info["duration"] = duration
                
                logging.info(f"📊 {workflow_id}: {previous_stage} → {stage} ({duration:.2f}s)")
            else:
                logging.info(f"📊 {workflow_id}: → {stage}")
                
        except Exception as e:
            logging.warning(f"⚠️ Failed to update workflow stage: {e}")
    
    def complete_workflow(self, workflow_id: str, status: str = "completed", 
                         final_data: Dict[str, Any] = None):
        """
        Mark a workflow as completed.
        
        Args:
            workflow_id: Workflow identifier
            status: Final status (completed, failed, cancelled)
            final_data: Optional final data
        """
        try:
            if workflow_id not in self.workflows:
                logging.warning(f"⚠️ Workflow not found for completion: {workflow_id}")
                return
            
            workflow = self.workflows[workflow_id]
            end_time = time.time()
            total_duration = end_time - workflow["start_time"]
            
            workflow.update({
                "end_time": end_time,
                "total_duration": total_duration,
                "status": status,
                "final_data": final_data or {}
            })
            
            # Record performance metrics
            self._record_performance_metrics(workflow_id, workflow)
            
            logging.info(f"✅ Workflow {status}: {workflow_id} ({total_duration:.2f}s)")
            
        except Exception as e:
            logging.warning(f"⚠️ Failed to complete workflow tracking: {e}")
    
    def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current status of a workflow.
        
        Args:
            workflow_id: Workflow identifier
            
        Returns:
            Workflow status information
        """
        try:
            workflow = self.workflows.get(workflow_id)
            if not workflow:
                return None
            
            current_time = time.time()
            elapsed_time = current_time - workflow["start_time"]
            
            return {
                "id": workflow_id,
                "current_stage": workflow["current_stage"],
                "status": workflow["status"],
                "elapsed_time": elapsed_time,
                "total_stages": len(workflow["stages"]),
                "metadata": workflow["metadata"]
            }
            
        except Exception as e:
            logging.warning(f"⚠️ Failed to get workflow status: {e}")
            return None
    
    def get_all_workflows(self) -> List[Dict[str, Any]]:
        """
        Get status of all tracked workflows.
        
        Returns:
            List of workflow status information
        """
        try:
            return [
                self.get_workflow_status(workflow_id)
                for workflow_id in self.workflows.keys()
            ]
        except Exception as e:
            logging.warning(f"⚠️ Failed to get all workflows: {e}")
            return []
    
    def _record_performance_metrics(self, workflow_id: str, workflow: Dict[str, Any]):
        """
        Record performance metrics for analysis.
        
        Args:
            workflow_id: Workflow identifier
            workflow: Workflow data
        """
        try:
            metrics = {
                "workflow_id": workflow_id,
                "total_duration": workflow.get("total_duration", 0),
                "stage_count": len(workflow.get("stages", [])),
                "status": workflow.get("status", "unknown"),
                "timestamp": time.time()
            }
            
            # Calculate stage durations
            stages = workflow.get("stages", [])
            stage_durations = {}
            
            for i, stage in enumerate(stages):
                if "duration" in stage:
                    stage_name = stage["stage"]
                    stage_durations[stage_name] = stage["duration"]
            
            metrics["stage_durations"] = stage_durations
            
            if workflow_id not in self.performance_metrics:
                self.performance_metrics[workflow_id] = []
            
            self.performance_metrics[workflow_id].append(metrics)
            
        except Exception as e:
            logging.warning(f"⚠️ Failed to record performance metrics: {e}")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """
        Get performance summary across all workflows.
        
        Returns:
            Performance summary statistics
        """
        try:
            if not self.performance_metrics:
                return {"message": "No performance data available"}
            
            all_metrics = []
            for workflow_metrics in self.performance_metrics.values():
                all_metrics.extend(workflow_metrics)
            
            if not all_metrics:
                return {"message": "No completed workflows"}
            
            # Calculate summary statistics
            durations = [m["total_duration"] for m in all_metrics if m.get("total_duration")]
            stage_counts = [m["stage_count"] for m in all_metrics if m.get("stage_count")]
            
            summary = {
                "total_workflows": len(all_metrics),
                "completed_workflows": len([m for m in all_metrics if m.get("status") == "completed"]),
                "failed_workflows": len([m for m in all_metrics if m.get("status") == "failed"]),
                "average_duration": sum(durations) / len(durations) if durations else 0,
                "average_stages": sum(stage_counts) / len(stage_counts) if stage_counts else 0
            }
            
            if durations:
                summary.update({
                    "min_duration": min(durations),
                    "max_duration": max(durations)
                })
            
            return summary
            
        except Exception as e:
            logging.warning(f"⚠️ Failed to get performance summary: {e}")
            return {"error": str(e)}


class MockWorkflowTracker:
    """Fallback tracker when full implementation fails."""
    
    def start_workflow(self, workflow_id: str, metadata: Dict[str, Any] = None):
        logging.info(f"🚀 Mock workflow started: {workflow_id}")
    
    def update_stage(self, workflow_id: str, stage: str, data: Dict[str, Any] = None):
        logging.info(f"📊 Mock workflow stage: {workflow_id} → {stage}")
    
    def complete_workflow(self, workflow_id: str, status: str = "completed", 
                         final_data: Dict[str, Any] = None):
        logging.info(f"✅ Mock workflow completed: {workflow_id} ({status})")
    
    def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        return {"id": workflow_id, "status": "mock", "current_stage": "unknown"}
    
    def get_all_workflows(self) -> List[Dict[str, Any]]:
        return []
    
    def get_performance_summary(self) -> Dict[str, Any]:
        return {"message": "Mock tracker - no performance data"}


@contextmanager
def log_execution_time(operation_name: str):
    """
    Context manager to log execution time of operations.
    
    Args:
        operation_name: Name of the operation being timed
    """
    start_time = time.time()
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"⏱️ Starting: {operation_name}")
        yield
        
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"❌ Failed: {operation_name} ({duration:.2f}s) - {e}")
        raise
        
    else:
        duration = time.time() - start_time
        logger.info(f"✅ Completed: {operation_name} ({duration:.2f}s)")


def setup_enhanced_logging(log_level: str = "INFO", 
                          enable_file_logging: bool = True,
                          log_file_path: str = None):
    """
    Setup enhanced logging configuration.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        enable_file_logging: Whether to enable file logging
        log_file_path: Custom log file path
    """
    global workflow_tracker
    
    try:
        # Configure logging format
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        
        # Configure root logger
        logging.basicConfig(
            level=getattr(logging, log_level.upper(), logging.INFO),
            format=log_format,
            force=True
        )
        
        # Setup file logging if enabled
        if enable_file_logging:
            try:
                if not log_file_path:
                    # Default log file path
                    log_dir = Path("logs")
                    log_dir.mkdir(exist_ok=True)
                    log_file_path = log_dir / "spinscribe.log"
                
                file_handler = logging.FileHandler(log_file_path)
                file_handler.setFormatter(logging.Formatter(log_format))
                logging.getLogger().addHandler(file_handler)
                
                logging.info(f"✅ File logging enabled: {log_file_path}")
                
            except Exception as e:
                logging.warning(f"⚠️ File logging setup failed: {e}")
        
        # Initialize workflow tracker
        try:
            workflow_tracker = WorkflowTracker()
            logging.info("✅ Enhanced logging and workflow tracking initialized")
        except Exception as e:
            logging.warning(f"⚠️ Workflow tracker initialization failed: {e}")
            workflow_tracker = MockWorkflowTracker()
            logging.info("✅ Mock workflow tracker initialized")
        
        return True
        
    except Exception as e:
        print(f"❌ Enhanced logging setup failed: {e}")
        # Fallback to basic logging
        logging.basicConfig(level=logging.INFO)
        workflow_tracker = MockWorkflowTracker()
        return False


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with enhanced configuration.
    
    Args:
        name: Logger name
        
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


def log_workflow_event(workflow_id: str, event: str, data: Dict[str, Any] = None):
    """
    Log a workflow event with structured data.
    
    Args:
        workflow_id: Workflow identifier
        event: Event description
        data: Optional event data
    """
    try:
        logger = logging.getLogger(__name__)
        event_data = {
            "workflow_id": workflow_id,
            "event": event,
            "timestamp": datetime.now().isoformat(),
            "data": data or {}
        }
        
        logger.info(f"📝 Workflow Event: {json.dumps(event_data)}")
        
    except Exception as e:
        logging.warning(f"⚠️ Failed to log workflow event: {e}")


def create_workflow_logger(workflow_id: str) -> logging.Logger:
    """
    Create a logger specific to a workflow.
    
    Args:
        workflow_id: Workflow identifier
        
    Returns:
        Workflow-specific logger
    """
    try:
        logger_name = f"spinscribe.workflow.{workflow_id}"
        logger = logging.getLogger(logger_name)
        
        # Add workflow ID to all log messages
        class WorkflowAdapter(logging.LoggerAdapter):
            def process(self, msg, kwargs):
                return f"[{workflow_id}] {msg}", kwargs
        
        return WorkflowAdapter(logger, {})
        
    except Exception as e:
        logging.warning(f"⚠️ Failed to create workflow logger: {e}")
        return logging.getLogger(__name__)


def export_workflow_logs(workflow_id: str = None, 
                        output_file: str = None) -> Optional[str]:
    """
    Export workflow logs to a file.
    
    Args:
        workflow_id: Specific workflow to export, or None for all
        output_file: Output file path
        
    Returns:
        Path to exported file or None if failed
    """
    try:
        global workflow_tracker
        
        if not workflow_tracker:
            logging.warning("⚠️ No workflow tracker available for export")
            return None
        
        # Determine output file
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"workflow_logs_{timestamp}.json"
        
        # Gather export data
        if workflow_id:
            workflows = [workflow_tracker.get_workflow_status(workflow_id)]
            workflows = [w for w in workflows if w is not None]
        else:
            workflows = workflow_tracker.get_all_workflows()
        
        export_data = {
            "export_timestamp": datetime.now().isoformat(),
            "workflow_count": len(workflows),
            "workflows": workflows,
            "performance_summary": workflow_tracker.get_performance_summary()
        }
        
        # Write to file
        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        logging.info(f"✅ Workflow logs exported: {output_file}")
        return output_file
        
    except Exception as e:
        logging.error(f"❌ Failed to export workflow logs: {e}")
        return None


def monitor_workflow_performance(workflow_id: str, 
                               alert_threshold: float = 300.0) -> Dict[str, Any]:
    """
    Monitor workflow performance and generate alerts.
    
    Args:
        workflow_id: Workflow to monitor
        alert_threshold: Alert if workflow exceeds this duration (seconds)
        
    Returns:
        Monitoring results
    """
    try:
        global workflow_tracker
        
        if not workflow_tracker:
            return {"error": "No workflow tracker available"}
        
        status = workflow_tracker.get_workflow_status(workflow_id)
        if not status:
            return {"error": f"Workflow not found: {workflow_id}"}
        
        elapsed_time = status.get("elapsed_time", 0)
        current_stage = status.get("current_stage", "unknown")
        
        monitoring_result = {
            "workflow_id": workflow_id,
            "current_stage": current_stage,
            "elapsed_time": elapsed_time,
            "alert_threshold": alert_threshold,
            "status": "normal"
        }
        
        # Check for performance alerts
        if elapsed_time > alert_threshold:
            monitoring_result["status"] = "alert"
            monitoring_result["alert_message"] = f"Workflow exceeding threshold ({elapsed_time:.1f}s > {alert_threshold:.1f}s)"
            logging.warning(f"⚠️ Performance Alert: {monitoring_result['alert_message']}")
        
        # Check for stuck workflows
        if status.get("status") == "running" and elapsed_time > alert_threshold * 2:
            monitoring_result["status"] = "critical"
            monitoring_result["alert_message"] = f"Workflow may be stuck in stage: {current_stage}"
            logging.error(f"🚨 Critical Alert: {monitoring_result['alert_message']}")
        
        return monitoring_result
        
    except Exception as e:
        logging.error(f"❌ Failed to monitor workflow performance: {e}")
        return {"error": str(e)}


def cleanup_old_workflows(max_age_hours: int = 24) -> int:
    """
    Clean up old workflow tracking data.
    
    Args:
        max_age_hours: Maximum age of workflows to keep (hours)
        
    Returns:
        Number of workflows cleaned up
    """
    try:
        global workflow_tracker
        
        if not workflow_tracker or not hasattr(workflow_tracker, 'workflows'):
            return 0
        
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        cleaned_count = 0
        
        workflows_to_remove = []
        
        for workflow_id, workflow in workflow_tracker.workflows.items():
            workflow_age = current_time - workflow.get("start_time", current_time)
            
            if workflow_age > max_age_seconds and workflow.get("status") in ["completed", "failed", "cancelled"]:
                workflows_to_remove.append(workflow_id)
        
        # Remove old workflows
        for workflow_id in workflows_to_remove:
            del workflow_tracker.workflows[workflow_id]
            
            # Clean up related data
            if workflow_id in workflow_tracker.stage_history:
                del workflow_tracker.stage_history[workflow_id]
            
            if workflow_id in workflow_tracker.performance_metrics:
                del workflow_tracker.performance_metrics[workflow_id]
            
            cleaned_count += 1
        
        if cleaned_count > 0:
            logging.info(f"🧹 Cleaned up {cleaned_count} old workflows (>{max_age_hours}h)")
        
        return cleaned_count
        
    except Exception as e:
        logging.error(f"❌ Failed to cleanup old workflows: {e}")
        return 0


# Initialize workflow tracker on module import
if workflow_tracker is None:
    try:
        workflow_tracker = WorkflowTracker()
    except Exception:
        workflow_tracker = MockWorkflowTracker()


def test_enhanced_logging():
    """Test the enhanced logging functionality."""
    try:
        print("🧪 Testing Enhanced Logging")
        
        # Test setup
        setup_result = setup_enhanced_logging("INFO", False)
        print(f"✅ Setup completed: {setup_result}")
        
        # Test workflow tracking
        test_workflow_id = "test-workflow-123"
        
        global workflow_tracker
        workflow_tracker.start_workflow(test_workflow_id, {"test": True})
        print(f"✅ Workflow started: {test_workflow_id}")
        
        workflow_tracker.update_stage(test_workflow_id, "testing")
        print("✅ Stage updated")
        
        workflow_tracker.complete_workflow(test_workflow_id, "completed")
        print("✅ Workflow completed")
        
        # Test status retrieval
        status = workflow_tracker.get_workflow_status(test_workflow_id)
        print(f"✅ Status retrieved: {status['status']}")
        
        # Test performance summary
        summary = workflow_tracker.get_performance_summary()
        print(f"✅ Performance summary: {summary.get('total_workflows', 0)} workflows")
        
        return {
            "success": True,
            "setup_successful": setup_result,
            "workflow_tracked": True,
            "status_retrieved": bool(status),
            "performance_summary": summary
        }
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    # Run test
    test_result = test_enhanced_logging()
    print("\n" + "="*60)
    print("Enhanced Logging Test Complete")
    print("="*60)
    print(f"Success: {test_result.get('success', False)}")
    if test_result.get('success'):
        print("✅ Enhanced logging operational")
        print(f"📊 Performance tracking available")
    else:
        print(f"❌ Error: {test_result.get('error', 'Unknown')}")