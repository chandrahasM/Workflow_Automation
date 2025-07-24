# Design Notes: Mini-Zaps Engine

This document covers the core design decisions, focusing on extensibility and the trade-offs made to keep the initial implementation simple.

### How to Add New Connectors

For the end users, creating a new workflow using existing step types—like `delay` and `webhook`—only requires writing a new JSON definition.

For developers looking to add a fundamentally **new type of step** to the engine, a capability that doesn't exist yet (e.g., "send an email" or "write to a Google Sheet"). This process requires writing Python code to teach the engine what to do when it encounters the new step type in a workflow's JSON. The process involves three small pieces:

First, define the step's configuration schema by creating a new Pydantic model that inherits from `ConnectorConfig`. This model defines the fields that a user must provide in the workflow definition's `config` block for that step. For an email connector, this might include fields for the recipient, subject, and body templates.

Second, create the connector class itself, inheriting from `BaseConnector`. This class must implement a single async `execute` method. This is where the core logic lives. It receives the current run's context, performs its action—like connecting to an SMTP server and sending the email—and can optionally return a dictionary of output data to be merged back into the run's context for subsequent steps to use.

Finally, register the new connector. This is done by adding a single entry to the `CONNECTOR_MAP` dictionary in the `WorkflowEngine`. You map a `StepType` enum value to a tuple containing your new connector class and its config model. The engine handles the rest, automatically routing steps of that type to your new connector for execution.

### Trade-offs and Simplifications

To deliver a working prototype quickly, several significant trade-offs were made, primarily favouring simplicity over production-readiness.

The most obvious is the storage layer. Using the local filesystem with individual JSON files for each workflow and run is incredibly simple and has zero dependencies, but it's not robust. It's prone to race conditions with concurrent writes and is highly inefficient for querying, as listing runs requires a full directory scan. A real implementation would use a transactional database like Postgres to ensure data integrity and enable efficient lookups.

Execution is handled by a simple, in-memory `asyncio.create_task`. This works for a single-process application but is not durable. If the application crashes or restarts, any workflows that were in the middle of executing are lost forever. A production system would use a persistent message broker like RabbitMQ or Redis with dedicated worker processes. This would decouple the API from the execution and ensure that tasks are not lost on restart.

Error handling is also minimal. A step fails, the entire run is marked as `failed`, and execution stops. There is no concept of automatic retries with exponential backoff, which is critical for steps involving network requests like webhooks. There's also no dead-letter queue for runs that fail consistently, which would be necessary for later inspection and manual intervention.

Finally, configuration and security were intentionally omitted. Storage paths are hardcoded, and the API is completely open. A production version would need to source these from environment variables and implement standard authentication and authorization mechanisms.
