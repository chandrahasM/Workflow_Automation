from typing import List, Dict, Any, Optional, Set
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from enum import Enum
from datetime import datetime

class WorkflowStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"

class StepType(str, Enum):
    DELAY = "delay"
    WEBHOOK = "webhook"

class StepDefinition(BaseModel):
    """Definition of a single step in a workflow"""
    model_config = ConfigDict(extra='forbid')
    
    id: str = Field(..., description="Unique identifier for the step")
    type: StepType = Field(..., description="Type of the step")
    config: Dict[str, Any] = Field(..., description="Configuration for the step")
    next_step_id: Optional[str] = Field(
        default=None,
        description="ID of the next step to execute (for conditional flows)"
    )

class WorkflowDefinition(BaseModel):
    """Definition of a workflow"""
    model_config = ConfigDict(extra='forbid')
    
    id: str = Field(..., description="Unique identifier for the workflow")
    name: str = Field(..., description="Human-readable name of the workflow")
    description: Optional[str] = Field(default=None, description="Description of the workflow")
    entry_point: str = Field(..., description="ID of the first step to execute")
    steps: List[StepDefinition] = Field(..., description="List of steps in the workflow")
    status: WorkflowStatus = Field(
        default=WorkflowStatus.ACTIVE,
        description="Current status of the workflow"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow, description="When the workflow was created")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="When the workflow was last updated")
    
    @field_validator('steps')
    @classmethod
    def validate_steps(cls, steps: List[StepDefinition]) -> List[StepDefinition]:
        """Validate that all step IDs are unique"""
        step_ids = [step.id for step in steps]
        if len(step_ids) != len(set(step_ids)):
            raise ValueError("Step IDs must be unique within a workflow")
        return steps
    
    @model_validator(mode='after')
    def validate_entry_point(self) -> 'WorkflowDefinition':
        """Validate that entry_point exists in steps"""
        step_ids = {step.id for step in self.steps}
        if self.entry_point not in step_ids:
            raise ValueError(f"entry_point '{self.entry_point}' must be a valid step ID")
        
        # Validate next_step_id references
        for step in self.steps:
            if step.next_step_id is not None and step.next_step_id not in step_ids:
                raise ValueError(f"next_step_id '{step.next_step_id}' in step '{step.id}' is not a valid step ID")
        
        return self
    
    def get_step(self, step_id: str) -> Optional[StepDefinition]:
        """Get a step by ID"""
        return next((step for step in self.steps if step.id == step_id), None)
    
    def get_next_step_id(self, current_step_id: str) -> Optional[str]:
        """Get the next step ID after the current step"""
        current_step = self.get_step(current_step_id)
        if current_step is None:
            return None
        return current_step.next_step_id
