from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Union, Type, TypeVar, Generic
from pydantic import BaseModel, Field, ConfigDict, model_validator, field_validator
from typing_extensions import Self

class RunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"

class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

class StepRun(BaseModel):
    """Represents the execution of a single step in a workflow run"""
    model_config = ConfigDict(extra='forbid')
    
    step_id: str = Field(..., description="ID of the step definition")
    status: StepStatus = Field(default=StepStatus.PENDING, description="Current status of the step")
    start_time: Optional[datetime] = Field(default=None, description="When the step started executing")
    end_time: Optional[datetime] = Field(default=None, description="When the step finished executing")
    error: Optional[str] = Field(default=None, description="Error message if the step failed")
    output: Optional[Dict[str, Any]] = Field(default=None, description="Output from the step execution")
    
    @property
    def duration_seconds(self) -> Optional[float]:
        """Get the duration of the step in seconds"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

class WorkflowRun(BaseModel):
    """Represents a single execution of a workflow"""
    model_config = ConfigDict(extra='forbid')
    
    run_id: str = Field(..., description="Unique identifier for this run")
    workflow_id: str = Field(..., description="ID of the workflow being executed")
    status: RunStatus = Field(default=RunStatus.PENDING, description="Current status of the run")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), 
        description="When the run was created"
    )
    started_at: Optional[datetime] = Field(default=None, description="When the run started executing")
    completed_at: Optional[datetime] = Field(default=None, description="When the run completed")
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Context data available to all steps in the workflow"
    )
    steps: Dict[str, StepRun] = Field(
        default_factory=dict,
        description="Execution details for each step in the workflow"
    )
    current_step_id: Optional[str] = Field(
        default=None,
        description="ID of the current or next step to execute"
    )
    error: Optional[str] = Field(default=None, description="Error message if the run failed")
    
    @property
    def duration_seconds(self) -> Optional[float]:
        """Get the duration of the workflow run in seconds"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    @field_validator('created_at', 'started_at', 'completed_at', mode='before')
    @classmethod
    def ensure_timezone(cls, v: Optional[Union[datetime, str]]) -> Optional[datetime]:
        """Ensure datetimes are timezone-aware, handling both str and datetime inputs."""
        if v is None:
            return None
        if isinstance(v, str):
            # Pydantic v2 doesn't automatically parse strings to datetimes in validators
            # anymore, so we have to do it manually.
            try:
                v = datetime.fromisoformat(v.replace('Z', '+00:00'))
            except (ValueError, TypeError):
                # If parsing fails, let Pydantic's default validation handle it.
                # This allows for more complex validation scenarios if needed.
                return v

        # Now, v is guaranteed to be a datetime object if it was a valid string.
        if isinstance(v, datetime):
            if v.tzinfo is None:
                return v.replace(tzinfo=timezone.utc)
            return v.astimezone(timezone.utc)
        return v
    
    def add_step(self, step_id: str) -> None:
        """Add a new step to the run"""
        if step_id not in self.steps:
            self.steps[step_id] = StepRun(step_id=step_id)
    
    def start_step(self, step_id: str) -> None:
        """Mark a step as started"""
        if step_id not in self.steps:
            self.add_step(step_id)
        self.steps[step_id].status = StepStatus.RUNNING
        self.steps[step_id].start_time = datetime.now(timezone.utc)
        
        # Update run status if needed
        if self.status == RunStatus.PENDING:
            self.status = RunStatus.RUNNING
            self.started_at = datetime.now(timezone.utc)
    
    def complete_step(self, step_id: str, output: Optional[Dict[str, Any]] = None) -> None:
        """Mark a step as completed"""
        if step_id in self.steps:
            self.steps[step_id].status = StepStatus.COMPLETED
            self.steps[step_id].end_time = datetime.now(timezone.utc)
            self.steps[step_id].output = output or {}
    
    def fail_step(self, step_id: str, error: str) -> None:
        """Mark a step as failed"""
        if step_id in self.steps:
            self.steps[step_id].status = StepStatus.FAILED
            self.steps[step_id].end_time = datetime.now(timezone.utc)
            self.steps[step_id].error = error
            
            # Update run status
            self.status = RunStatus.FAILED
            self.completed_at = datetime.now(timezone.utc)
            self.error = error
    
    def complete_run(self) -> None:
        """Mark the run as completed successfully"""
        self.status = RunStatus.COMPLETED
        self.completed_at = datetime.now(timezone.utc)
    
    def update_context(self, **updates: Any) -> None:
        """Update the workflow context with new values"""
        self.context.update(updates)
    
    def get_step(self, step_id: str) -> Optional[StepRun]:
        """Get a step by ID"""
        return self.steps.get(step_id)
    
    def get_current_step(self) -> Optional[StepRun]:
        """Get the current step"""
        if self.current_step_id:
            return self.get_step(self.current_step_id)
        return None
