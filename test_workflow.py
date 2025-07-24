"""
Test script for the workflow builder.
This script:
1. Creates a sample workflow
2. Starts a subscriber server to receive webhook notifications
3. Triggers the workflow with test data
"""
import asyncio
import uvicorn
import threading
import time
import requests
from fastapi import FastAPI, Request
from pydantic import BaseModel

# Configuration
WORKFLOW_API_URL = "http://localhost:8000"
SUBSCRIBER_PORT = 8001

# Simple subscriber server to receive webhook notifications
subscriber_app = FastAPI()

class WebhookData(BaseModel):
    to: str
    subject: str
    message: str
    invoice_id: str
    amount: str
    due_date: str
    customer_name: str

@subscriber_app.post("/notify")
async def notify(webhook_data: WebhookData):
    print("\n=== Webhook Notification Received ===")
    print(f"To: {webhook_data.to}")
    print(f"Subject: {webhook_data.subject}")
    print(f"Message: {webhook_data.message}")
    print(f"Invoice ID: {webhook_data.invoice_id}")
    print(f"Amount: {webhook_data.amount}")
    print(f"Due Date: {webhook_data.due_date}")
    print(f"Customer: {webhook_data.customer_name}")
    print("================================\n")
    return {"status": "received"}

def run_subscriber():
    """Run the subscriber server in a separate thread"""
    config = uvicorn.Config(
        app=subscriber_app,
        host="0.0.0.0",
        port=SUBSCRIBER_PORT,
        log_level="info"
    )
    server = uvicorn.Server(config)
    asyncio.run(server.serve())

async def test_workflow():
    # Start the subscriber server in a separate thread
    print("Starting subscriber server...")
    subscriber_thread = threading.Thread(target=run_subscriber, daemon=True)
    subscriber_thread.start()
    
    # Wait for subscriber to start
    time.sleep(2)
    
    # Create the sample workflow
    print("Creating sample workflow...")
    from sample_workflow import create_sample_workflow
    workflow_id = await create_sample_workflow()
    
    # Test data for the workflow
    test_data = {
        "customer_email": "customer@example.com",
        "invoice_id": "INV-2023-001",
        "amount": "$150.00",
        "due_date": "2023-07-15",
        "customer_name": "John Doe"
    }
    
    # Trigger the workflow
    print("\nTriggering workflow...")
    response = requests.post(
        f"{WORKFLOW_API_URL}/api/workflows/{workflow_id}/trigger",
        json={"context": test_data}
    )
    if response.status_code == 202:
        run_data = response.json()
        print(f"Successfully triggered workflow. Run ID: {run_data['run_id']}")
        run_id = run_data['run_id']
    else:
        print(f"Error triggering workflow: {response.status_code} {response.text}")
        return
    
    print("Waiting for workflow to complete...")
    
    # Poll for workflow completion
    max_attempts = 10
    for _ in range(max_attempts):
        time.sleep(1)
        response = requests.get(f"{WORKFLOW_API_URL}/api/runs/{run_id}")
        if response.status_code == 200:
            run = response.json()
            status = run["status"]
            print(f"Workflow status: {status}")
            
            if status in ["completed", "failed"]:
                if status == "failed":
                    print(f"Error: {run.get('error')}")
                break
    else:
        print("Timed out waiting for workflow to complete")
    
    print("\nTest complete! Press Ctrl+C to exit.")
    
    # Keep the subscriber running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")

if __name__ == "__main__":
    asyncio.run(test_workflow())
