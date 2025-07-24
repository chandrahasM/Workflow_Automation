import os
import logging
import uuid
from datetime import datetime
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from workflow_builder.engine import WorkflowEngine
from workflow_builder.models.workflow import WorkflowDefinition, WorkflowStatus, StepDefinition, StepType
from workflow_builder.models.run import WorkflowRun, RunStatus
from workflow_builder.storage.filesystem import FilesystemStorage

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize storage and engine
workflow_storage = FilesystemStorage.for_workflows(".workflows")
run_storage = FilesystemStorage.for_runs(".workflows")
engine = WorkflowEngine(workflow_storage=workflow_storage, run_storage=run_storage)

# Create FastAPI app
app = FastAPI(
    title="Mini-Zaps Workflow API",
    description="A simple workflow automation API similar to Zapier",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response Models
class CreateWorkflowRequest(BaseModel):
    name: str
    description: Optional[str] = None
    steps: List[Dict[str, Any]]
    entry_point: str

class TriggerWorkflowRequest(BaseModel):
    context: Dict[str, Any] = {}

class WorkflowResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime

class RunResponse(BaseModel):
    run_id: str
    workflow_id: str
    status: str
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None

# API Endpoints
@app.post("/api/workflows", response_model=WorkflowDefinition, status_code=201)
async def create_workflow(workflow: WorkflowDefinition):
    """Create a new workflow"""
    return await workflow_storage.create_workflow(workflow)

@app.get("/api/workflows", response_model=List[WorkflowDefinition])
async def get_workflows():
    """Get all workflows"""
    return await workflow_storage.list_workflows()

@app.get("/api/workflows/{workflow_id}", response_model=WorkflowDefinition)
async def get_workflow(workflow_id: str):
    """Get a specific workflow by ID"""
    return await workflow_storage.get_workflow(workflow_id)

@app.post("/api/workflows/{workflow_id}/trigger", response_model=WorkflowRun, status_code=202)
async def trigger_run(workflow_id: str, trigger_request: TriggerWorkflowRequest):
    """Trigger a workflow run"""
    run = await engine.start_workflow(workflow_id, trigger_request.context)
    return run

@app.get("/api/runs/{run_id}", response_model=WorkflowRun)
async def get_run_status(run_id: str):
    """Get the status of a specific workflow run"""
    return await run_storage.get_run(run_id)

@app.get("/api/workflows/{workflow_id}/runs", response_model=List[WorkflowRun])
async def get_runs_for_workflow(workflow_id: str):
    """Get all runs for a specific workflow"""
    return await run_storage.list_runs(workflow_id=workflow_id)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
