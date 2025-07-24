"""
Sample workflow definition for invoice reminder use case.
This script creates a workflow that:
1. Waits for 5 seconds (simulating a delay)
2. Sends a reminder email via webhook
"""
import asyncio
import json
import os
import shutil
from workflow_builder.storage.filesystem import FilesystemStorage
from workflow_builder.engine import WorkflowEngine
from workflow_builder.models.workflow import WorkflowDefinition, StepDefinition, StepType

async def create_sample_workflow():
    # Initialize storage and engine
    storage_dir = ".workflows"
    # Clean up previous runs to ensure the script is idempotent
    if os.path.exists(storage_dir):
        shutil.rmtree(storage_dir)
    workflow_storage = FilesystemStorage.for_workflows(storage_dir)
    run_storage = FilesystemStorage.for_runs(storage_dir)
    engine = WorkflowEngine(workflow_storage=workflow_storage, run_storage=run_storage)
    
    # Define the workflow
    workflow_id = "invoice_reminder"
    workflow = {
        "name": "Invoice Reminder Workflow",
        "description": "Sends a reminder email for overdue invoices",
        "entry_point": "delay_step",
        "steps": [
            {
                "id": "delay_step",
                "type": "delay",
                "config": {
                    "seconds": 2  # 2 seconds
                },
                "next_step_id": "send_reminder"
            },
            {
                "id": "send_reminder",
                "type": "webhook",
                "config": {
                    "url": "http://localhost:8001/notify",
                    "method": "POST",
                    "headers": {
                        "Content-Type": "application/json"
                    },
                    "body": {
                        "to": "{{customer_email}}",
                        "subject": "Invoice Overdue Reminder",
                        "message": "Your invoice {{invoice_id}} is overdue since {{due_date}}. Please make payment.",
                        "invoice_id": "{{invoice_id}}",
                        "amount": "{{amount}}",
                        "due_date": "{{due_date}}",
                        "customer_name": "{{customer_name}}"
                    }
                }
            }
        ]
    }
    
    # Convert to WorkflowDefinition
    steps = []
    for step in workflow["steps"]:
        steps.append(StepDefinition(
            id=step["id"],
            type=StepType(step["type"]),
            config=step["config"],
            next_step_id=step.get("next_step_id")
        ))
    
    workflow_def = WorkflowDefinition(
        id=workflow_id,
        name=workflow["name"],
        description=workflow["description"],
        entry_point=workflow["entry_point"],
        steps=steps
    )
    
    # Save the workflow
    await workflow_storage.create_workflow(workflow_def)
    print(f"Created workflow: {workflow_id}")
    
    # Example of how to trigger the workflow
    context = {
        "customer_email": "customer@example.com",
        "invoice_id": "INV-12345",
        "amount": "$150.00",
        "due_date": "2023-01-15",
        "customer_name": "John Doe"
    }
    
    # Start the workflow
    run = await engine.start_workflow(workflow_id, context)
    print(f"Started workflow run: {run.run_id}")
    
    return workflow_id

if __name__ == "__main__":
    asyncio.run(create_sample_workflow())
