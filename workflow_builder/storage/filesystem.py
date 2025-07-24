import json
import os
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any, Type, TypeVar, Generic, ClassVar, cast
from pydantic import BaseModel
import shutil
from datetime import datetime, timezone

from .base import Storage, StorageError, NotFoundError, AlreadyExistsError
from ..models.workflow import WorkflowDefinition
from ..models.run import WorkflowRun, RunStatus, StepRun

T = TypeVar('T', bound=BaseModel)

class FilesystemStorage(Storage[T]):
    """Filesystem-based storage for workflows and runs"""

    def __init__(self, base_dir: str, model_class: Type[T], entity_name: str):
        """Initialize the filesystem storage.

        Args:
            base_dir: Base directory for storing all data.
            model_class: The Pydantic model class this storage handles.
            entity_name: The name of the entity (e.g., 'workflows', 'runs').
        """
        self.base_dir = Path(base_dir)
        self._model_class = model_class
        self.storage_dir = self.base_dir / entity_name
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def for_workflows(cls, base_dir: str) -> 'Storage[WorkflowDefinition]':
        """Create a storage instance for WorkflowDefinition."""
        return cls(base_dir, WorkflowDefinition, 'workflows')

    @classmethod
    def for_runs(cls, base_dir: str) -> 'Storage[WorkflowRun]':
        """Create a storage instance for WorkflowRun."""
        return cls(base_dir, WorkflowRun, 'runs')

    # --- Generic Methods ---
    async def _create(self, entity: T) -> T:
        entity_id = getattr(entity, 'id', None) or getattr(entity, 'run_id', None)
        if not entity_id:
            raise ValueError("Entity must have an 'id' or 'run_id' attribute.")
        entity_file = self.storage_dir / f"{entity_id}.json"
        if entity_file.exists():
            raise AlreadyExistsError(f"{self._model_class.__name__} with ID {entity_id} already exists.")
        entity_file.write_text(entity.model_dump_json(indent=4))
        return entity

    async def _get(self, id: str) -> T:
        entity_file = self.storage_dir / f"{id}.json"
        if not entity_file.exists():
            raise NotFoundError(f"{self._model_class.__name__} with ID {id} not found.")
        return self._model_class.model_validate_json(entity_file.read_text())

    async def _update(self, entity: T) -> T:
        entity_id = getattr(entity, 'id', None) or getattr(entity, 'run_id', None)
        if not entity_id:
            raise ValueError("Entity must have an 'id' or 'run_id' attribute.")
        entity_file = self.storage_dir / f"{entity_id}.json"
        if not entity_file.exists():
            raise NotFoundError(f"{self._model_class.__name__} with ID {entity_id} not found.")
        entity_file.write_text(entity.model_dump_json(indent=4))
        return entity

    async def _delete(self, id: str) -> None:
        entity_file = self.storage_dir / f"{id}.json"
        if not entity_file.exists():
            raise NotFoundError(f"{self._model_class.__name__} with ID {id} not found.")
        entity_file.unlink()

    async def create(self, entity: T) -> T:
        """Generic create method for compatibility."""
        return await self._create(entity)

    async def _list(self, **filters: Any) -> List[T]:
        entities = []
        for entity_file in self.storage_dir.glob("*.json"):
            try:
                entity = self._model_class.model_validate_json(entity_file.read_text())
                if all(getattr(entity, key, None) == value for key, value in filters.items()):
                    entities.append(entity)
            except (json.JSONDecodeError, Exception):
                continue
        return entities

    # --- Abstract Method Implementations ---
    async def create_workflow(self, workflow: WorkflowDefinition) -> WorkflowDefinition:
        return await self._create(workflow)

    async def create_run(self, run: WorkflowRun) -> WorkflowRun:
        return await self._create(run)

    async def get_workflow(self, workflow_id: str) -> WorkflowDefinition:
        return await self._get(workflow_id)

    async def update_workflow(self, workflow: WorkflowDefinition) -> WorkflowDefinition:
        return await self._update(workflow)

    async def delete_workflow(self, workflow_id: str) -> bool:
        await self._delete(workflow_id)
        return True

    async def list_workflows(self, **filters: Any) -> List[WorkflowDefinition]:
        return await self._list(**filters)

    async def get_run(self, run_id: str) -> WorkflowRun:
        return await self._get(run_id)

    async def update_run(self, run: WorkflowRun) -> None:
        await self._update(run)

    async def list_runs(self, workflow_id: Optional[str] = None) -> List[WorkflowRun]:
        filters = {"workflow_id": workflow_id} if workflow_id else {}
        return await self._list(**filters)
