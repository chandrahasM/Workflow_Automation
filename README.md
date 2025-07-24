# Mini-Zaps – Filesystem-Backed Workflow Automation Engine

Mini-Zaps is a lightweight clone of products such as Zapier / IFTTT.  It lets you:

* Define multi-step **workflows** (templates).
* Trigger individual **runs** of those workflows with custom data (context).
* Execute steps asynchronously in the background.
* Persist everything as JSON on disk – no external database required.

The example shipping with the repo is an **Invoice Reminder** flow:

1. Wait for *N* seconds (`delay_step`).
2. POST a webhook with invoice details (`send_reminder`).

---

## 1. Quick Start

```bash
# 1. Install requirements
python -m pip install -r requirements.txt

# 2. Start the main FastAPI server (port 8000)
python -m workflow_builder.main
# → Open http://127.0.0.1:8000/docs for interactive Swagger UI

# 3. (Optional) Run the demo end-to-end
python sample_workflow.py      # creates the invoice_reminder workflow
python test_workflow.py        # spins a test subscriber, triggers a run
```

Directory layout generated on first use:

```
.workflows/
├── workflows/   # static templates (one JSON per workflow)
└── runs/        # live executions (one JSON per run)
```

---

## 2. Core Concepts

| Concept   | Stored where | Description |
|-----------|--------------|-------------|
| **Workflow** | `.workflows/workflows/<workflow_id>.json` | Template listing ordered steps and config. |
| **Run**      | `.workflows/runs/<run_id>.json`          | One execution of a workflow with its own context & status. |

`RunStatus` values you will see:

* `pending`    – run object just created (very transient)
* `running`    – engine is currently executing steps
* `completed`  – all steps finished successfully
* `failed`     – a step raised an error
* `paused`     – (reserved, not yet used)

---

## 3. Using the API

Once the server is up (`python -m workflow_builder.main`), open Swagger UI:

```
http://127.0.0.1:8000/docs
```

Key endpoints:

| Method & Path                              | Purpose |
|--------------------------------------------|---------|
| `POST  /api/workflows`                     | Create / update a workflow |
| `GET   /api/workflows`                     | List workflows |
| `POST  /api/workflows/{workflow_id}/trigger` | Start a run with optional context JSON |
| `GET   /api/runs/{run_id}`                 | Poll the run status |
| `GET   /health`                            | Simple health-check |

All request/response schemas are documented interactively in Swagger.

---

## 4. Sample Workflow Definition (Invoice Reminder)

```jsonc
{
  "id": "invoice_reminder",
  "name": "Invoice Reminder Workflow",
  "entry_point": "delay_step",
  "steps": [
    {
      "id": "delay_step",
      "type": "delay",
      "config": { "seconds": 2 },
      "next_step_id": "send_reminder"
    },
    {
      "id": "send_reminder",
      "type": "webhook",
      "config": { "url": "http://127.0.0.1:8001/notify" },
      "next_step_id": null
    }
  ]
}
```

Upload this JSON via `POST /api/workflows` or run `sample_workflow.py` which does it programmatically.

---

## 5. Observing Status Changes – Delay Tweaks

To watch the state machine in action:

1. **Edit the delay** in the workflow file (or resend the definition) to a larger value, e.g. `"seconds": 20`.
2. Trigger a run via Swagger UI.
3. Immediately switch to `GET /api/runs/{run_id}` and keep clicking **Execute** every few seconds:
   * Initially you will see `"status": "running"` and inside `steps` the `delay_step` as `running`.
   * After ~20 s the status flips to `running` on `send_reminder` then the whole run turns `completed`.
4. Set an **invalid webhook URL** (e.g. `http://bad.host`) to see the run end with `"status": "failed"` and an `error` message.

---

## 6. Adding Your Own Step Types

1. Create a connector class in `workflow_builder/connectors/` inheriting from `BaseConnector`.
2. Create a Pydantic config model.
3. Register the pair in `WorkflowEngine.CONNECTOR_MAP`.

The engine will automatically pick it up in workflow definitions.

---

## 7. Development & Tests

* Code is Python 3.13 + Pydantic v2, formatted with **black**.
* `test_workflow.py` is an integration test: starts a dummy subscriber (port 8001), creates the sample workflow, triggers it, and polls until finished.

---

Enjoy automating!
