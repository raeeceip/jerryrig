"""Progress tracking and monitoring system for distributed repository processing."""

import time
import uuid
import asyncio
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

from ..utils.logger import get_logger

logger = get_logger(__name__)


class WorkflowStatus(Enum):
    """Workflow status enumeration."""
    PENDING = "pending"
    CHUNKING = "chunking"
    ANALYZING = "analyzing"
    MIGRATING = "migrating"
    AGGREGATING = "aggregating"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ProgressMetrics:
    """Progress metrics for tracking workflow execution."""
    total_files: int = 0
    processed_files: int = 0
    successful_files: int = 0
    failed_files: int = 0
    total_chunks: int = 0
    processed_chunks: int = 0
    start_time: float = field(default_factory=time.time)
    last_update: float = field(default_factory=time.time)
    estimated_completion: Optional[float] = None
    
    @property
    def progress_percentage(self) -> float:
        """Calculate progress percentage."""
        if self.total_files == 0:
            return 0.0
        return (self.processed_files / self.total_files) * 100
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.processed_files == 0:
            return 0.0
        return (self.successful_files / self.processed_files) * 100
    
    @property
    def elapsed_time(self) -> float:
        """Calculate elapsed time in seconds."""
        return time.time() - self.start_time
    
    @property
    def estimated_remaining_time(self) -> Optional[float]:
        """Estimate remaining time in seconds."""
        if self.processed_files == 0 or self.total_files == 0:
            return None
        
        elapsed = self.elapsed_time
        rate = self.processed_files / elapsed
        remaining_files = self.total_files - self.processed_files
        
        if rate > 0:
            return remaining_files / rate
        return None


@dataclass
class WorkflowEvent:
    """Event in the workflow execution."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: str = ""
    timestamp: float = field(default_factory=time.time)
    event_type: str = ""
    agent_id: str = ""
    message: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    level: str = "INFO"  # INFO, WARNING, ERROR


class ProgressTracker:
    """Central progress tracking system for distributed repository processing."""
    
    def __init__(self):
        self.workflows: Dict[str, Dict[str, Any]] = {}
        self.event_handlers: List[Callable[[WorkflowEvent], None]] = []
        self.active_monitors: Dict[str, asyncio.Task] = {}
        
    def start_workflow(self, correlation_id: str, request_data: Dict[str, Any]) -> None:
        """Start tracking a new workflow."""
        self.workflows[correlation_id] = {
            "correlation_id": correlation_id,
            "status": WorkflowStatus.PENDING,
            "request_data": request_data,
            "metrics": ProgressMetrics(),
            "events": [],
            "agents": {},  # Track agent assignments
            "chunks": {},  # Track chunk processing
            "start_time": time.time(),
            "completion_time": None,
            "error": None
        }
        
        self._emit_event(
            correlation_id=correlation_id,
            event_type="workflow_started",
            message=f"Started workflow for repository: {request_data.get('repository_url', 'unknown')}",
            data={"request": request_data}
        )
        
        logger.info(f"Started tracking workflow: {correlation_id}")
    
    def update_workflow_status(self, correlation_id: str, status: WorkflowStatus, message: str = "") -> None:
        """Update the status of a workflow."""
        if correlation_id not in self.workflows:
            logger.warning(f"Workflow {correlation_id} not found for status update")
            return
        
        workflow = self.workflows[correlation_id]
        old_status = workflow["status"]
        workflow["status"] = status
        workflow["last_update"] = time.time()
        
        if status == WorkflowStatus.COMPLETED:
            workflow["completion_time"] = time.time()
        
        self._emit_event(
            correlation_id=correlation_id,
            event_type="status_changed",
            message=message or f"Status changed from {old_status.value} to {status.value}",
            data={"old_status": old_status.value, "new_status": status.value}
        )
        
        logger.info(f"Workflow {correlation_id}: {old_status.value} -> {status.value}")
    
    def update_chunking_progress(self, correlation_id: str, total_chunks: int, chunk_data: List[Dict[str, Any]]) -> None:
        """Update progress after chunking phase."""
        if correlation_id not in self.workflows:
            return
        
        workflow = self.workflows[correlation_id]
        metrics = workflow["metrics"]
        
        # Update metrics
        metrics.total_chunks = total_chunks
        metrics.total_files = sum(chunk.get('file_count', 0) for chunk in chunk_data)
        
        # Store chunk information
        for chunk in chunk_data:
            chunk_id = chunk.get('chunk_id', 0)
            workflow["chunks"][chunk_id] = {
                "chunk_data": chunk,
                "status": "pending",
                "assigned_agents": {},
                "start_time": None,
                "completion_time": None,
                "results": {}
            }
        
        self._emit_event(
            correlation_id=correlation_id,
            event_type="chunking_completed",
            message=f"Repository chunked into {total_chunks} chunks with {metrics.total_files} total files",
            data={"total_chunks": total_chunks, "total_files": metrics.total_files}
        )
    
    def update_chunk_analysis(self, correlation_id: str, chunk_id: int, agent_id: str, analysis_result: Dict[str, Any]) -> None:
        """Update progress for chunk analysis."""
        if correlation_id not in self.workflows:
            return
        
        workflow = self.workflows[correlation_id]
        
        if chunk_id in workflow["chunks"]:
            chunk_info = workflow["chunks"][chunk_id]
            chunk_info["assigned_agents"]["analyzer"] = agent_id
            chunk_info["results"]["analysis"] = analysis_result
            
            if chunk_info["status"] == "pending":
                chunk_info["status"] = "analyzing"
                chunk_info["start_time"] = time.time()
        
        self._emit_event(
            correlation_id=correlation_id,
            event_type="chunk_analyzed",
            agent_id=agent_id,
            message=f"Chunk {chunk_id} analyzed by {agent_id}",
            data={"chunk_id": chunk_id, "analysis": analysis_result}
        )
    
    def update_chunk_migration(self, correlation_id: str, chunk_id: int, agent_id: str, migration_result: Dict[str, Any]) -> None:
        """Update progress for chunk migration."""
        if correlation_id not in self.workflows:
            return
        
        workflow = self.workflows[correlation_id]
        metrics = workflow["metrics"]
        
        if chunk_id in workflow["chunks"]:
            chunk_info = workflow["chunks"][chunk_id]
            chunk_info["assigned_agents"]["migrator"] = agent_id
            chunk_info["results"]["migration"] = migration_result
            chunk_info["status"] = "completed"
            chunk_info["completion_time"] = time.time()
            
            # Update overall metrics
            chunk_migration = migration_result.get("chunk_migration", {})
            successful = chunk_migration.get("successful_migrations", 0)
            failed = chunk_migration.get("failed_migrations", 0)
            
            metrics.processed_chunks += 1
            metrics.processed_files += successful + failed
            metrics.successful_files += successful
            metrics.failed_files += failed
            metrics.last_update = time.time()
        
        self._emit_event(
            correlation_id=correlation_id,
            event_type="chunk_migrated",
            agent_id=agent_id,
            message=f"Chunk {chunk_id} migrated by {agent_id}",
            data={"chunk_id": chunk_id, "migration": migration_result}
        )
        
        # Check if all chunks are completed
        if metrics.processed_chunks == metrics.total_chunks:
            self.update_workflow_status(correlation_id, WorkflowStatus.AGGREGATING, "All chunks processed, starting aggregation")
    
    def complete_workflow(self, correlation_id: str, final_result: Dict[str, Any]) -> None:
        """Mark workflow as completed with final results."""
        if correlation_id not in self.workflows:
            return
        
        workflow = self.workflows[correlation_id]
        workflow["final_result"] = final_result
        workflow["completion_time"] = time.time()
        
        self.update_workflow_status(correlation_id, WorkflowStatus.COMPLETED, "Workflow completed successfully")
        
        # Stop monitoring if active
        if correlation_id in self.active_monitors:
            self.active_monitors[correlation_id].cancel()
            del self.active_monitors[correlation_id]
    
    def fail_workflow(self, correlation_id: str, error: str) -> None:
        """Mark workflow as failed with error information."""
        if correlation_id not in self.workflows:
            return
        
        workflow = self.workflows[correlation_id]
        workflow["error"] = error
        workflow["completion_time"] = time.time()
        
        self.update_workflow_status(correlation_id, WorkflowStatus.FAILED, f"Workflow failed: {error}")
        
        self._emit_event(
            correlation_id=correlation_id,
            event_type="workflow_failed",
            message=f"Workflow failed: {error}",
            data={"error": error},
            level="ERROR"
        )
        
        # Stop monitoring if active
        if correlation_id in self.active_monitors:
            self.active_monitors[correlation_id].cancel()
            del self.active_monitors[correlation_id]
    
    def get_workflow_status(self, correlation_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of a workflow."""
        if correlation_id not in self.workflows:
            return None
        
        workflow = self.workflows[correlation_id]
        metrics = workflow["metrics"]
        
        return {
            "correlation_id": correlation_id,
            "status": workflow["status"].value,
            "progress_percentage": metrics.progress_percentage,
            "success_rate": metrics.success_rate,
            "elapsed_time": metrics.elapsed_time,
            "estimated_remaining_time": metrics.estimated_remaining_time,
            "total_files": metrics.total_files,
            "processed_files": metrics.processed_files,
            "successful_files": metrics.successful_files,
            "failed_files": metrics.failed_files,
            "total_chunks": metrics.total_chunks,
            "processed_chunks": metrics.processed_chunks,
            "start_time": workflow["start_time"],
            "completion_time": workflow.get("completion_time"),
            "error": workflow.get("error")
        }
    
    def get_workflow_events(self, correlation_id: str, limit: int = 50) -> List[WorkflowEvent]:
        """Get recent events for a workflow."""
        if correlation_id not in self.workflows:
            return []
        
        events = self.workflows[correlation_id]["events"]
        return events[-limit:] if len(events) > limit else events
    
    def get_active_workflows(self) -> List[Dict[str, Any]]:
        """Get all active workflows."""
        active_statuses = {WorkflowStatus.PENDING, WorkflowStatus.CHUNKING, WorkflowStatus.ANALYZING, WorkflowStatus.MIGRATING, WorkflowStatus.AGGREGATING}
        
        active_workflows = []
        for correlation_id, workflow in self.workflows.items():
            if workflow["status"] in active_statuses:
                status = self.get_workflow_status(correlation_id)
                if status:
                    active_workflows.append(status)
        
        return active_workflows
    
    def start_monitoring(self, correlation_id: str, update_interval: float = 30.0) -> None:
        """Start monitoring a workflow with periodic updates."""
        if correlation_id in self.active_monitors:
            return  # Already monitoring
        
        async def monitor():
            while correlation_id in self.workflows:
                workflow = self.workflows[correlation_id]
                
                if workflow["status"] in {WorkflowStatus.COMPLETED, WorkflowStatus.FAILED, WorkflowStatus.CANCELLED}:
                    break
                
                # Emit periodic status update
                status_info = self.get_workflow_status(correlation_id)
                if status_info:
                    self._emit_event(
                        correlation_id=correlation_id,
                        event_type="status_update",
                        message=f"Progress: {status_info['progress_percentage']:.1f}% - {status_info['processed_files']}/{status_info['total_files']} files",
                        data=status_info
                    )
                
                await asyncio.sleep(update_interval)
        
        task = asyncio.create_task(monitor())
        self.active_monitors[correlation_id] = task
        
        logger.info(f"Started monitoring workflow: {correlation_id}")
    
    def add_event_handler(self, handler: Callable[[WorkflowEvent], None]) -> None:
        """Add an event handler for workflow events."""
        self.event_handlers.append(handler)
    
    def _emit_event(self, correlation_id: str, event_type: str, message: str, 
                   agent_id: str = "", data: Optional[Dict[str, Any]] = None, level: str = "INFO") -> None:
        """Emit a workflow event."""
        event = WorkflowEvent(
            correlation_id=correlation_id,
            event_type=event_type,
            agent_id=agent_id,
            message=message,
            data=data or {},
            level=level
        )
        
        # Store event in workflow
        if correlation_id in self.workflows:
            self.workflows[correlation_id]["events"].append(event)
        
        # Notify event handlers
        for handler in self.event_handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Error in event handler: {e}")


class ProgressReporter:
    """Reports progress to various outputs (console, file, API, etc.)."""
    
    def __init__(self, tracker: ProgressTracker):
        self.tracker = tracker
        self.tracker.add_event_handler(self._handle_event)
    
    def _handle_event(self, event: WorkflowEvent) -> None:
        """Handle workflow events for reporting."""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(event.timestamp))
        
        if event.level == "ERROR":
            logger.error(f"[{timestamp}] {event.correlation_id[:8]}: {event.message}")
        elif event.level == "WARNING":
            logger.warning(f"[{timestamp}] {event.correlation_id[:8]}: {event.message}")
        else:
            logger.info(f"[{timestamp}] {event.correlation_id[:8]}: {event.message}")
    
    def print_workflow_summary(self, correlation_id: str) -> None:
        """Print a summary of workflow progress."""
        status = self.tracker.get_workflow_status(correlation_id)
        if not status:
            print(f"Workflow {correlation_id} not found")
            return
        
        print(f"\n=== Workflow Summary ===")
        print(f"ID: {correlation_id}")
        print(f"Status: {status['status']}")
        print(f"Progress: {status['progress_percentage']:.1f}%")
        print(f"Files: {status['processed_files']}/{status['total_files']}")
        print(f"Success Rate: {status['success_rate']:.1f}%")
        print(f"Elapsed Time: {status['elapsed_time']:.1f}s")
        
        if status['estimated_remaining_time']:
            print(f"Estimated Remaining: {status['estimated_remaining_time']:.1f}s")
        
        if status['error']:
            print(f"Error: {status['error']}")
        
        print("========================\n")
    
    def print_active_workflows(self) -> None:
        """Print summary of all active workflows."""
        active_workflows = self.tracker.get_active_workflows()
        
        if not active_workflows:
            print("No active workflows")
            return
        
        print(f"\n=== Active Workflows ({len(active_workflows)}) ===")
        for workflow in active_workflows:
            print(f"{workflow['correlation_id'][:8]}: {workflow['status']} - {workflow['progress_percentage']:.1f}%")
        print("=====================================\n")


# Global progress tracker instance
_global_tracker = None

def get_progress_tracker() -> ProgressTracker:
    """Get the global progress tracker instance."""
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = ProgressTracker()
    return _global_tracker