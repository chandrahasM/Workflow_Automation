import asyncio
import logging
import uuid
from typing import Dict, Any, List, Optional, Type, TypeVar
from datetime import datetime

from workflow_builder.models.workflow import WorkflowDefinition, StepDefinition, StepType
from workflow_builder.models.run import WorkflowRun, RunStatus, StepStatus
from workflow_builder.storage.base import Storage
from workflow_builder.connectors.base import BaseConnector
from workflow_builder.connectors.delay import DelayConnector, DelayConfig
from workflow_builder.connectors.webhook import WebhookConnector, WebhookConfig

logger = logging.getLogger(__name__)

class WorkflowEngine:
    """Orchestrates workflow execution"""
    
    # Map step types to their connector classes
    CONNECTOR_MAP = {
        StepType.DELAY: (DelayConnector, DelayConfig),
        StepType.WEBHOOK: (WebhookConnector, WebhookConfig)
    }
    
    def __init__(self, workflow_storage: Storage[WorkflowDefinition], run_storage: Storage[WorkflowRun]):
        """Initialize the workflow engine
        
        Args:
            workflow_storage: Storage backend for workflows
            run_storage: Storage backend for runs
        """
        self.workflow_storage = workflow_storage
        self.run_storage = run_storage
    
    async def start_workflow(self, workflow_id: str, context: Optional[Dict[str, Any]] = None) -> WorkflowRun:
        """Start a new workflow execution
        
        Args:
            workflow_id: ID of the workflow to start
            context: Initial context for the workflow
            
        Returns:
            The created workflow run
        """
        # Get the workflow definition
        workflow = await self.workflow_storage.get_workflow(workflow_id)

        # Create a new run
        run = WorkflowRun(run_id=str(uuid.uuid4()), workflow_id=workflow_id, status=RunStatus.PENDING)
        run = await self.run_storage.create_run(run)
        run.context = context or {}
        run.current_step_id = workflow.entry_point
        run.status = RunStatus.RUNNING
        run.started_at = datetime.utcnow()
        
        # Initialize all steps as pending
        for step in workflow.steps:
            run.add_step(step.id)
        
        # Save the initial run state
        await self.run_storage.update_run(run)
        
        # Start execution in the background
        asyncio.create_task(self._execute_workflow(run.run_id))
        
        return run
    
    async def _execute_workflow(self, run_id: str) -> None:
        logger.info(f"Starting background execution for run {run_id}")
        """Execute a workflow run
        
        Args:
            run_id: ID of the run to execute
        """
        try:
            # Get the run and workflow
            run = await self.run_storage.get_run(run_id)
            workflow = await self.workflow_storage.get_workflow(run.workflow_id)
            
            # Process each step
            while run.current_step_id:
                step_id = run.current_step_id
                step_def = next((s for s in workflow.steps if s.id == step_id), None)
                
                if not step_def:
                    raise ValueError(f"Step {step_id} not found in workflow {workflow.id}")
                
                # Mark step as running
                run.start_step(step_id)
                await self.run_storage.update_run(run)
                
                try:
                    # Execute the step
                    logger.info(f"Executing step {step_id} of workflow {workflow.id}")
                    output = await self._execute_step(step_def, run.context)
                    
                    # Update context with step output
                    if output:
                        run.update_context(**output)
                    
                    # Mark step as completed
                    run.complete_step(step_id, output)
                    
                    # Move to next step
                    run.current_step_id = step_def.next_step_id
                    
                except Exception as e:
                    logger.error(f"Error executing step {step_id}: {str(e)}", exc_info=True)
                    run.fail_step(step_id, str(e))
                    run.status = RunStatus.FAILED
                    run.error = f"Step {step_id} failed: {str(e)}"
                    run.completed_at = datetime.utcnow()
                    await self.run_storage.update_run(run)
                    return
                
                # Save the updated run
                await self.run_storage.update_run(run)
            
            # If we get here, the workflow completed successfully
            run.status = RunStatus.COMPLETED
            run.completed_at = datetime.utcnow()
            await self.run_storage.update_run(run)
            logger.info(f"Background execution for run {run_id} completed successfully.")
            
        except Exception as e:
            logger.error(f"CRITICAL: Unhandled error in background execution for run {run_id}: {str(e)}", exc_info=True)
            try:
                run = await self.run_storage.get_run(run_id)
                if run:
                    run.status = RunStatus.FAILED
                    run.error = str(e)
                    run.completed_at = datetime.utcnow()
                    await self.run_storage.update_run(run)
            except Exception as update_error:
                logger.error(f"Failed to update failed run status: {str(update_error)}", exc_info=True)
    
    async def _execute_step(self, step_def: StepDefinition, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single workflow step
        
        Args:
            step_def: Step definition
            context: Current workflow context
            
        Returns:
            Step output to be merged into the workflow context
        """
        # Get the connector class and config class for this step type
        connector_cls, config_cls = self.CONNECTOR_MAP.get(step_def.type, (None, None))
        if not connector_cls or not config_cls:
            raise ValueError(f"Unsupported step type: {step_def.type}")
        
        # Create the connector config from the step config
        config = config_cls(**step_def.config)
        
        # Create and execute the connector
        connector = connector_cls(config)
        result = await connector.execute(context)
        
        # Return the result to be merged into the context
        return result
    
    async def get_run_status(self, run_id: str) -> WorkflowRun:
        """Get the status of a workflow run
        
        Args:
            run_id: ID of the run
            
        Returns:
            The workflow run status
        """
        return await self.storage.get_run(run_id)
    
    async def list_workflow_runs(self, workflow_id: str) -> List[WorkflowRun]:
        """List all runs for a workflow
        
        Args:
            workflow_id: ID of the workflow
            
        Returns:
            List of workflow runs, ordered by creation time (newest first)
        """
        return await self.storage.list_runs(workflow_id=workflow_id)
