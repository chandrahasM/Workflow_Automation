from abc import ABC, abstractmethod
from typing import Dict, List, Optional, TypeVar, Generic, Any, Type, ClassVar
from workflow_builder.models.base import WorkflowBaseModel as BaseModel
from pydantic import ConfigDict
from datetime import datetime, timezone
from uuid import UUID, uuid4

from workflow_builder.models.workflow import WorkflowDefinition
from workflow_builder.models.run import WorkflowRun, RunStatus

T = TypeVar('T', bound=BaseModel)

class StorageError(Exception):
    """Base exception for storage-related errors"""
    pass

class NotFoundError(StorageError):
    """Raised when a requested entity is not found"""
    pass

class AlreadyExistsError(StorageError):
    """Raised when trying to create an entity that already exists"""
    pass

class Storage(ABC, Generic[T]):
    """Abstract base class for storage backends"""
    model_class: ClassVar[Type[T]]
    
    # Workflow methods
    @abstractmethod
    async def get_workflow(self, workflow_id: str) -> WorkflowDefinition:
        """
        Get a workflow definition by ID
        
        Args:
            workflow_id: The ID of the workflow definition to retrieve
            
        Returns:
            The retrieved workflow definition
            
        Raises:
            NotFoundError: If no workflow definition with the given ID exists
        """
        pass
    
    @abstractmethod
    async def list_workflows(self, **filters: Any) -> List[WorkflowDefinition]:
        """
        List workflow definitions with optional filtering
        
        Args:
            **filters: Key-value pairs to filter the results
            
        Returns:
            List of matching workflow definitions
        """
        pass
    
    @abstractmethod
    async def create_workflow(self, workflow: WorkflowDefinition) -> WorkflowDefinition:
        """
        Create a new workflow definition
        
        Args:
            workflow: The workflow definition to create
            
        Returns:
            The created workflow definition with any generated fields populated
            
        Raises:
            AlreadyExistsError: If a workflow definition with the same ID already exists
        """
        pass
    
    @abstractmethod
    async def update_workflow(self, workflow: WorkflowDefinition) -> WorkflowDefinition:
        """
        Update an existing workflow definition
        
        Args:
            workflow: The workflow definition with updated values
            
        Returns:
            The updated workflow definition
            
        Raises:
            NotFoundError: If no workflow definition with the given ID exists
        """
        pass
    
    @abstractmethod
    async def delete_workflow(self, workflow_id: str) -> bool:
        """
        Delete a workflow definition by ID
        
        Args:
            workflow_id: The ID of the workflow definition to delete
            
        Returns:
            True if the workflow definition was deleted, False if it didn't exist
        """
        pass
    
    async def get_workflow_or_none(self, workflow_id: str) -> Optional[WorkflowDefinition]:
        """
        Get a workflow definition by ID, returning None if not found
        
        Args:
            workflow_id: The ID of the workflow definition to retrieve
            
        Returns:
            The workflow definition if found, otherwise None
        """
        try:
            return await self.get_workflow(workflow_id)
        except NotFoundError:
            return None
    
    # Run methods
    @abstractmethod
    async def get_run(self, run_id: str) -> WorkflowRun:
        """Get a workflow run by ID"""
        pass
    
    @abstractmethod
    async def update_run(self, run: WorkflowRun) -> None:
        """Update a workflow run"""
        pass
    
    @abstractmethod
    async def list_runs(self, workflow_id: Optional[str] = None) -> List[WorkflowRun]:
        """List workflow runs, optionally filtered by workflow_id"""
        pass
