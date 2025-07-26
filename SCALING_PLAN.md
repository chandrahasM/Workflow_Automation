# Scaling Plan: From Prototype to Production-Grade Workflow Engine

This document outlines a phased approach to harden, scale, and enhance the Mini-Zaps prototype into a reliable, observable, and feature-rich production system. The current implementation is a single-process application with filesystem storage, which is excellent for rapid development but has inherent limitations in concurrency, reliability, and scale.

## Phase 1: Foundational Hardening & Decoupling

The immediate priority is to address the single points of failure and lack of durability. This phase focuses on creating a stable, reliable core.

### 1. Data Layer Transformation

*   **Problem:** The current filesystem storage is not transactional, prone to race conditions, and inefficient for queries. A server crash could leave data in a corrupt state.
*   **Solution:** Migrate all state management (workflows and runs) from JSON files to a transactional, relational database like **PostgreSQL**. 
    *   **Benefits:** This provides ACID guarantees, preventing data corruption. It enables efficient, indexed queries for retrieving runs by status, workflow_id, or date. It also provides a solid foundation for concurrency control using row-level locking.

### 2. Decouple Execution from the API

*   **Problem:** The API server currently uses `asyncio.create_task` to spawn background executions. If the API process crashes, all in-flight workflows are lost. The API's performance is also tied to the overhead of managing these tasks.
*   **Solution:** Introduce a dedicated message broker like **RabbitMQ** or **Redis Streams** to act as a durable task queue. The architecture will be split into two distinct services:
    1.  **API Service:** Its sole responsibility is to handle incoming HTTP requests, validate them, and publish a `start_run` job to the message queue. It remains lightweight and highly responsive for low-latency triggers.
    2.  **Worker Service:** A separate pool of processes that subscribe to the task queue. They pull jobs, execute the workflow logic, and update the database. These workers are completely independent of the API service.

### 3. Reliability & Observability

*   **Problem:** A failed step currently halts the entire workflow with no recourse. Failures are only visible by inspecting logs or the final run status.
*   **Solution:**
    *   **Reliability:** Implement automatic retries with exponential backoff directly within the worker's step execution logic, especially for network-dependent connectors (e.g., webhooks). For runs that consistently fail, move them to a **Dead-Letter Queue (DLQ)** for later inspection and manual intervention.
    *   **Observability:** Instrument the system thoroughly. Implement **structured logging** (JSON format) across all services. Use a library like **Prometheus** to expose key metrics (e.g., run latency, step failure rates, queue depth). Integrate **distributed tracing** (e.g., OpenTelemetry) to trace a request from the initial API call, through the message broker, to its execution in a worker, providing a complete view of the run's lifecycle.

---

## Phase 2: Scaling, Performance & Security

With a reliable foundation, the focus shifts to handling increased load and securing the system.

### 1. High Availability and Horizontal Scalability

*   **Problem:** The current system runs as a single process on a single machine.
*   **Solution:** Containerize the API and Worker services using **Docker**. Deploy them on a container orchestration platform like **Kubernetes**. 
    *   **Benefits:** This allows for independent, horizontal scaling. If API traffic spikes, we can scale up the number of API pods. If the workflow queue grows, we can scale up the number of worker pods. Kubernetes also provides high availability through automatic restarts and health checks. The database should be a managed, replicated instance (e.g., AWS RDS) to ensure it's not a single point of failure.

### 2. Rate Limiting and Throttling

*   **Problem:** The open API is vulnerable to abuse and overload from a single user or misconfigured client.
*   **Solution:** Implement centralized rate limiting using an in-memory datastore like **Redis**. This can be done at the API gateway level (e.g., NGINX) or within a middleware layer in the API service. Limits can be applied per user, per IP, or globally to protect system resources.

### 3. Security Hardening

*   **Problem:** The API is open, and secrets (like webhook URLs) are stored in plain text.
*   **Solution:**
    *   **Authentication/Authorization:** Secure the API using a standard protocol like **OAuth2 / JWT**. Each request would require a valid token, and workflows would be tied to a specific user or tenant.
    *   **Secrets Management:** Integrate a dedicated secrets management service like **HashiCorp Vault** or **AWS Secrets Manager**. Instead of storing sensitive data (API keys, credentials) in the workflow definition, the definition would store a reference to the secret. The worker would then securely retrieve the secret at runtime.

---

## Phase 3: Advanced Engine & Ecosystem Features

This phase focuses on evolving the engine's capabilities to match sophisticated, real-world use cases.

### 1. Event-Driven Architecture with Kafka

*   **Problem:** Triggers are currently limited to direct API calls.
*   **Solution:** Evolve the system to be truly event-driven by integrating with **Apache Kafka**. Workflows could be triggered by consuming messages from specific Kafka topics. 
    *   **Benefits:** This enables powerful, decoupled integrations. For example, a single `user_created` event published to a topic could trigger multiple, separate workflows (e.g., "Onboarding Email Sequence," "Add to CRM," "Provision Analytics Account"). This naturally supports a fan-out model at the trigger level.

### 2. Advanced Workflow Orchestration

*   **Problem:** The current engine is a simple linear state machine.
*   **Solution:** Enhance the workflow definition schema and the engine's logic to support advanced patterns:
    *   **Parallel Execution (Fan-Out/Fan-In):** Allow a step to branch into multiple parallel paths that execute concurrently. A subsequent step could then be configured to "fan-in," waiting for all parallel branches to complete before it proceeds. This is crucial for performance-intensive workflows.
    *   **Conditional Logic:** Introduce conditional steps (`if/else`) that route the workflow down different paths based on the output of previous steps.
    *   **Dynamic Steps:** Allow the parameters of a step, or even the choice of the next step, to be determined dynamically from the run's context.
