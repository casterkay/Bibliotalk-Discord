# A2A Protocol Overview

This document provides a comprehensive introduction to the Agent2Agent (A2A) Protocol, explaining its purpose, architecture, core components, and position within the AI agent ecosystem. It is designed for developers and architects who want to understand A2A's capabilities and determine how to integrate it into their systems.

For detailed explanations of fundamental concepts like Tasks, Messages, and Agent Cards, see [Key Concepts](/google/A2A/1.1-key-concepts). For the complete technical specification of data structures and operations, see [Protocol Specification](/google/A2A/2-protocol-specification). For implementation guidance using official SDKs, see [SDK Implementations](/google/A2A/4-sdk-implementations).

---

## What is A2A?

The Agent2Agent (A2A) Protocol is an open standard that enables communication and interoperability between independent AI agent systems. It addresses a critical challenge in the AI ecosystem: allowing agents built on different frameworks (LangGraph, CrewAI, Semantic Kernel, etc.), by different vendors, and running on separate infrastructure to discover each other, negotiate capabilities, and collaborate on tasks.

**Key Characteristic:** A2A enables agents to work together **as agents**, not merely as tools. Agents interact based on declared capabilities without exposing internal state, memory, proprietary logic, or tool implementations.

**Governance:** Originally developed by Google and donated to the Linux Foundation, A2A is governed by a Technical Steering Committee comprising 8 major technology companies (Google, Microsoft, Cisco, AWS, Salesforce, ServiceNow, SAP, IBM) with contributions from 170+ partners.

**Primary Goals:**

Goal

Description

**Interoperability**

Bridge communication gaps between disparate agentic systems

**Discovery**

Enable dynamic capability discovery via Agent Cards at well-known URIs

**Collaboration**

Support task delegation, context exchange, and multi-turn interactions

**Flexibility**

Provide multiple interaction modes: synchronous, streaming (SSE), asynchronous (push notifications)

**Security**

Align with enterprise standards (OAuth2, OIDC, mTLS, API keys)

**Opacity**

Preserve agent autonomy without requiring internal state sharing

Sources: [docs/specification.md15-43](https://github.com/google/A2A/blob/629190ae/docs/specification.md#L15-L43) [README.md48-80](https://github.com/google/A2A/blob/629190ae/README.md#L48-L80)

---

## Design Philosophy and Guiding Principles

A2A's design reflects five core principles that distinguish it from traditional API-based integration approaches:

Resulting Capabilities

A2A Guiding Principles

Simple:  
Reuse HTTP, JSON-RPC 2.0, SSE

Enterprise Ready:  
Standard auth, observability

Async First:  
Long-running tasks, HITL

Modality Agnostic:  
Text, files, structured data

Opaque Execution:  
No internal state exposure

Easy adoption via  
familiar web standards

Production-grade  
security & monitoring

Human-in-the-loop  
multi-turn conversations

Rich media exchange  
beyond text

Vendor independence  
& IP protection

**Protocol Neutrality:** The canonical data model is defined in Protocol Buffers ([specification/a2a.proto](https://github.com/google/A2A/blob/629190ae/specification/a2a.proto)), ensuring a single source of truth independent of any specific transport protocol. This proto definition generates JSON Schema artifacts and drives all SDK implementations.

Sources: [docs/specification.md35-42](https://github.com/google/A2A/blob/629190ae/docs/specification.md#L35-L42) [docs/specification.md107-126](https://github.com/google/A2A/blob/629190ae/docs/specification.md#L107-L126)

---

## Three-Layer Architecture

A2A employs a three-layer architecture that separates concerns and enables extensibility:

Layer 3: Protocol Bindings  
(Concrete implementations)

Layer 2: Abstract Operations  
(Protocol-agnostic methods)

Layer 1: Canonical Data Model  
(specification/a2a.proto)

defines

defines

defines

Task

Message

AgentCard

Part

Artifact

StreamResponse

TaskStatus

AgentSkill

SendMessage

SendStreamingMessage

GetTask

ListTasks

CancelTask

SubscribeToTask

Push Notification APIs

JSON-RPC 2.0  
over HTTP/SSE

gRPC  
over HTTP/2

HTTP+JSON/REST

**Layer 1: Canonical Data Model** ([specification/a2a.proto](https://github.com/google/A2A/blob/629190ae/specification/a2a.proto)) defines Protocol Buffer messages that all implementations must understand. This includes `Task`, `Message`, `AgentCard`, `Part`, `Artifact`, `TaskStatus`, and related structures. The proto file is the **normative source of truth** for the protocol.

**Layer 2: Abstract Operations** describes fundamental capabilities independent of transport: `SendMessage`, `SendStreamingMessage`, `GetTask`, `ListTasks`, `CancelTask`, `SubscribeToTask`, and push notification configuration methods. These operations are documented in [docs/specification.md149-431](https://github.com/google/A2A/blob/629190ae/docs/specification.md#L149-L431)

**Layer 3: Protocol Bindings** maps abstract operations to concrete protocols:

-   **JSON-RPC 2.0**: Over HTTP with Server-Sent Events for streaming
-   **gRPC**: Over HTTP/2 with bidirectional streaming
-   **HTTP+JSON/REST**: RESTful endpoints with standard HTTP verbs

This architecture ensures that new protocol bindings can be added without modifying the data model, and that interoperability is maintained through the shared canonical definitions.

Sources: [docs/specification.md45-106](https://github.com/google/A2A/blob/629190ae/docs/specification.md#L45-L106) [docs/specification.md107-126](https://github.com/google/A2A/blob/629190ae/docs/specification.md#L107-L126)

---

## Core Protocol Components

The following diagram maps natural language concepts to their concrete Protocol Buffer message definitions:

SDK Usage

specification/a2a.proto Messages

Human Concepts

Agent's  
business card

Unit of work  
with state

Communication  
turn

Content  
piece

Output  
result

AgentCard

Task

Message

Part

Artifact

A2AClient.discover()

AgentExecutor.execute()

send\_message()

TextPart, DataPart

task.artifacts

### AgentCard

The `AgentCard` message ([specification/a2a.proto](https://github.com/google/A2A/blob/629190ae/specification/a2a.proto)) is a JSON metadata document published at `/.well-known/agent-card.json` that describes an agent's identity and capabilities:

Field

Type

Purpose

`name`

`string`

Human-readable agent name

`description`

`string`

Agent's purpose and functionality

`version`

`string`

Agent Card schema version

`supported_interfaces`

`AgentInterface[]`

Service endpoints with protocol bindings

`capabilities`

`AgentCapabilities`

Feature flags: streaming, push\_notifications, extended\_agent\_card, extensions

`skills`

`AgentSkill[]`

Declared skills with input/output modes

`security_schemes`

`map<string, SecurityScheme>`

Authentication methods (OAuth2, mTLS, API keys)

`default_input_modes`

`string[]`

Supported MIME types for input

`default_output_modes`

`string[]`

Supported MIME types for output

### Task

The `Task` message represents a stateful unit of work with a defined lifecycle:

Field

Type

Purpose

`id`

`string`

Unique server-generated identifier

`context_id`

`string`

Groups related tasks/messages in a conversation

`status`

`TaskStatus`

Current state (SUBMITTED, WORKING, COMPLETED, etc.)

`artifacts`

`Artifact[]`

Outputs produced during execution

`history`

`Message[]`

Conversation history

`metadata`

`google.protobuf.Struct`

Custom key-value data

Task states follow a state machine defined in [docs/specification.md628-737](https://github.com/google/A2A/blob/629190ae/docs/specification.md#L628-L737) with terminal states (COMPLETED, FAILED, CANCELED, REJECTED) and interrupted states (INPUT\_REQUIRED, AUTH\_REQUIRED).

### Message

The `Message` type represents a single communication turn:

Field

Type

Purpose

`message_id`

`string`

Unique message identifier

`role`

`Role`

USER or AGENT

`parts`

`Part[]`

Content pieces (text, files, structured data)

`context_id`

`string`

Conversational context grouping

`task_id`

`string`

Associated task (for multi-turn)

`reference_task_ids`

`string[]`

Related tasks for context sharing

### Part

The `Part` message is a union type for content:

-   `TextPart`: Plain text with optional `media_type`
-   `DataPart`: Structured JSON data
-   `RawPart`: Raw bytes with `media_type` and optional `filename`
-   `UrlPart`: Reference to external resource

### Artifact

The `Artifact` message represents a tangible output:

Field

Type

Purpose

`parts`

`Part[]`

Content of the artifact

`metadata`

`google.protobuf.Struct`

Additional metadata

Sources: [docs/specification.md127-147](https://github.com/google/A2A/blob/629190ae/docs/specification.md#L127-L147) [docs/specification.md738-983](https://github.com/google/A2A/blob/629190ae/docs/specification.md#L738-L983)

---

## Agent Discovery and Capabilities

A2A uses a standardized discovery mechanism inspired by OAuth2's well-known URI pattern:

"A2A Server""/.well-known/agent-card.json""A2AClient""A2A Server""/.well-known/agent-card.json""A2AClient"Parse capabilities:\- supported\_interfaces\- skills\- security\_schemesalt\[Extended Card Supported\]Select protocol bindingand prepare requestGET /.well-known/agent-card.jsonAgentCard (public)AuthenticateAuth tokenGetExtendedAgentCardAgentCard (extended)

**Discovery Flow:**

1.  **Public Agent Card**: Client fetches `/.well-known/agent-card.json` (unauthenticated)
2.  **Capability Assessment**: Client parses `capabilities` field to determine:
    -   `streaming`: Whether `SendStreamingMessage` and `SubscribeToTask` are supported
    -   `push_notifications`: Whether webhook-based updates are available
    -   `extended_agent_card`: Whether authenticated extended cards can be fetched
    -   `extensions`: List of supported extension URIs
3.  **Extended Card (Optional)**: If `capabilities.extended_agent_card` is `true`, client can authenticate and call `GetExtendedAgentCard` to retrieve additional skills or configuration
4.  **Protocol Selection**: Client chooses from `supported_interfaces` based on preference (JSON-RPC, gRPC, or REST)

**AgentSkill Declaration:**

Each skill in the Agent Card includes:

-   `id`: Unique skill identifier
-   `name` and `description`: Human-readable metadata
-   `tags`: Categorization (e.g., "search", "analytics")
-   `input_modes` and `output_modes`: Supported MIME types for this specific skill
-   `examples`: Sample usage patterns

Sources: [docs/specification.md1078-1210](https://github.com/google/A2A/blob/629190ae/docs/specification.md#L1078-L1210) [docs/specification.md406-430](https://github.com/google/A2A/blob/629190ae/docs/specification.md#L406-L430)

---

## Task-Based Communication Model

A2A uses a **Task-centric** model where all agent interactions revolve around stateful task objects:

TaskCreation

TaskProcessing

Client discovers agent

POST message

Need user input

User responds

Need credentials

Auth provided

Success

Error

Cancellation

Agent rejects

Discovery

SendMessage

SUBMITTED

WORKING

INPUT\_REQUIRED

AUTH\_REQUIRED

COMPLETED

FAILED

CANCELED

REJECTED

UpdateMechanism

Polling

Repeat

GetTask

Streaming

SendStreamingMessage

TaskStatusUpdateEvent

TaskArtifactUpdateEvent

Push

CreatePushNotificationConfig

WebhookPOST

**Task Lifecycle States:**

State

Category

Description

`SUBMITTED`

Initial

Task created, queued for processing

`WORKING`

Active

Agent actively processing

`INPUT_REQUIRED`

Interrupted

Multi-turn: awaiting user input

`AUTH_REQUIRED`

Interrupted

Awaiting additional authentication

`COMPLETED`

Terminal

Successfully finished

`FAILED`

Terminal

Error occurred

`CANCELED`

Terminal

Client-requested cancellation

`REJECTED`

Terminal

Agent declined to process

**Context Identifiers:**

The `context_id` field logically groups related tasks and messages. When a client sends a message without a `context_id`, the agent generates one and includes it in the response. Subsequent messages in the same conversation should include this `context_id` to maintain continuity.

**Multi-Turn Interactions:**

To continue a conversation, clients send new messages with both `context_id` (for conversation context) and `task_id` (for task-specific state). The agent can then:

-   Access previous conversation history
-   Update the existing task's status and artifacts
-   Request additional input via `INPUT_REQUIRED` state

Sources: [docs/specification.md583-627](https://github.com/google/A2A/blob/629190ae/docs/specification.md#L583-L627) [docs/specification.md628-737](https://github.com/google/A2A/blob/629190ae/docs/specification.md#L628-L737)

---

## Interaction Patterns

A2A supports three primary update delivery mechanisms:

Push Notification Pattern

Client: CreatePushNotificationConfig

Server: Stores webhook URL

Server: POST StreamResponse to webhook

Client: Receives updates

Streaming Pattern (SSE)

Client: SendStreamingMessage

Server: Returns Task

Server: TaskStatusUpdateEvent

Server: TaskArtifactUpdateEvent

Server: Close stream (terminal state)

Polling Pattern

Client: SendMessage

Server: Returns Task (WORKING)

Client: GetTask (repeated)

Server: Returns updated Task

### Synchronous Request-Response

**Method:** `SendMessage` with `blocking: true`

The operation waits until the task reaches a terminal or interrupted state before returning. Suitable for quick interactions but may timeout for long-running tasks.

### Streaming Updates

**Methods:** `SendStreamingMessage`, `SubscribeToTask`

Uses Server-Sent Events (SSE) for real-time updates. The stream contains:

-   Initial `Task` object
-   Incremental `TaskStatusUpdateEvent` messages
-   Incremental `TaskArtifactUpdateEvent` messages (with `append` flag for streaming content)
-   Stream closes when task reaches terminal state

The `SubscribeToTask` operation allows reattachment to an existing task's stream, useful for reconnection after network interruptions.

### Push Notifications (Webhooks)

**Methods:** `CreateTaskPushNotificationConfig`, `GetTaskPushNotificationConfig`, `ListTaskPushNotificationConfigs`, `DeleteTaskPushNotificationConfig`

Client provides a webhook URL. The agent POSTs `StreamResponse` payloads to this URL as task updates occur. Suitable for long-running tasks or disconnected scenarios where maintaining an SSE connection is impractical.

**Webhook Payload:** The webhook receives POST requests with bodies containing `StreamResponse` objects (same structure as SSE events).

Sources: [docs/specification.md161-214](https://github.com/google/A2A/blob/629190ae/docs/specification.md#L161-L214) [docs/specification.md289-338](https://github.com/google/A2A/blob/629190ae/docs/specification.md#L289-L338) [docs/specification.md1211-1466](https://github.com/google/A2A/blob/629190ae/docs/specification.md#L1211-L1466)

---

## Protocol Bindings

### JSON-RPC 2.0 Binding

**Endpoint Pattern:** `POST /<base-path>`

**Method Names:**

-   `message/send` → `SendMessage`
-   `message/stream` → `SendStreamingMessage` (returns SSE)
-   `tasks/get` → `GetTask`
-   `tasks/list` → `ListTasks`
-   `tasks/cancel` → `CancelTask`
-   `tasks/subscribe` → `SubscribeToTask` (returns SSE)
-   `tasks/push-notification-config/set` → `CreateTaskPushNotificationConfig`
-   `tasks/push-notification-config/get` → `GetTaskPushNotificationConfig`
-   `tasks/push-notification-config/list` → `ListTaskPushNotificationConfigs`
-   `tasks/push-notification-config/delete` → `DeleteTaskPushNotificationConfig`

**Request Format:**

```
{
  "jsonrpc": "2.0",
  "id": "req-123",
  "method": "message/send",
  "params": { /* SendMessageRequest fields */ }
}
```

**Service Parameters:** Transmitted via HTTP headers:

-   `A2A-Version`: Protocol version (e.g., "0.3")
-   `A2A-Extensions`: Comma-separated extension URIs

Detailed at [docs/specification.md1554-2002](https://github.com/google/A2A/blob/629190ae/docs/specification.md#L1554-L2002)

### gRPC Binding

**Service Definition:** `A2AService` in [specification/a2a.proto](https://github.com/google/A2A/blob/629190ae/specification/a2a.proto)

**RPC Methods:**

-   `SendMessage(SendMessageRequest) returns (SendMessageResponse)`
-   `SendStreamingMessage(SendMessageRequest) returns (stream StreamResponse)`
-   `GetTask(GetTaskRequest) returns (Task)`
-   `ListTasks(ListTasksRequest) returns (ListTasksResponse)`
-   `CancelTask(CancelTaskRequest) returns (Task)`
-   `SubscribeToTask(SubscribeToTaskRequest) returns (stream StreamResponse)`
-   Push notification config methods

**Service Parameters:** Transmitted via gRPC metadata.

Detailed at [docs/specification.md2003-2403](https://github.com/google/A2A/blob/629190ae/docs/specification.md#L2003-L2403)

### HTTP+JSON/REST Binding

**Endpoint Patterns:**

-   `POST /v1/messages` → `SendMessage`
-   `POST /v1/messages:stream` → `SendStreamingMessage`
-   `GET /v1/tasks/{taskId}` → `GetTask`
-   `GET /v1/tasks` → `ListTasks`
-   `POST /v1/tasks/{taskId}:cancel` → `CancelTask`
-   `POST /v1/tasks/{taskId}:subscribe` → `SubscribeToTask`
-   Task push notification config endpoints under `/v1/tasks/{taskId}/push-notification-configs`

**Service Parameters:** Transmitted via HTTP headers.

Detailed at [docs/specification.md2404-2819](https://github.com/google/A2A/blob/629190ae/docs/specification.md#L2404-L2819)

Sources: [docs/specification.md1467-1553](https://github.com/google/A2A/blob/629190ae/docs/specification.md#L1467-L1553)

---

## Security and Authentication

A2A aligns with enterprise web security practices:

Implementation Points

AgentCard.security\_schemes

OAuth2  
(authorization\_code, client\_credentials)

OpenID Connect

API Key  
(header, query, cookie)

Mutual TLS

HTTP Authentication  
(Basic, Bearer)

TLS/HTTPS  
(required for production)

Agent Card Signatures  
(JWS for integrity)

Push Notification Auth  
(per-config credentials)

Per-Skill Requirements  
(AgentSkill.security)

**Authentication Methods:**

All authentication schemes are declared in the Agent Card's `security_schemes` map, following OpenAPI 3.0 security scheme definitions:

Scheme Type

Use Case

`oauth2`

Delegated authorization with scopes

`openIdConnect`

Identity verification + authorization

`apiKey`

Simple token-based auth (header, query, cookie)

`mutualTLS`

Certificate-based mutual authentication

`http`

Basic or Bearer token authentication

**Agent Card Signature:**

The Agent Card can include a `signature` field containing a JSON Web Signature (JWS) to ensure integrity and authenticity. Clients verify the signature using the agent's public key.

**Per-Skill Security:**

Individual skills can declare specific security requirements in `AgentSkill.security`, allowing fine-grained access control.

**Push Notification Security:**

Push notification configurations include authentication parameters (`security_scheme`, `credentials`) so the agent can authenticate when POSTing to client webhooks.

Sources: [docs/specification.md2820-3324](https://github.com/google/A2A/blob/629190ae/docs/specification.md#L2820-L3324)

---

## Extension System

A2A provides a standardized extension mechanism for custom functionality:

**Extension Declaration:**

Agent Cards declare supported extensions in `AgentCard.extensions`:

```
extensions {
  uri: "https://example.com/extensions/geolocation/v1"
  name: "Geolocation Context"
  description: "Adds lat/long to messages"
  required: false
}
```

**Extension Usage:**

Clients signal extension usage via the `A2A-Extensions` service parameter (header):

```
A2A-Extensions: https://example.com/extensions/geolocation/v1
```

**Extension Points:**

Extensions can add custom fields to:

-   `Message` objects (via `extensions` field)
-   `Artifact` objects (via `extensions` field)
-   `TaskStatus` objects (via `extensions` field)

**Extension Validation:**

If an agent declares an extension with `required: true`, clients **MUST** include it in requests or receive an `ExtensionSupportRequiredError`.

Sources: [docs/specification.md3325-3526](https://github.com/google/A2A/blob/629190ae/docs/specification.md#L3325-L3526)

---

## Repository Structure

The A2A repository is organized into the following key directories:

Generated Artifacts

github.com/a2aproject/A2A

orchestrates

orchestrates

orchestrates

triggers

specification/  
a2a.proto (normative)  
json/a2a.json (generated)

docs/  
specification.md  
topics/  
tutorials/

types/  
TypeScript types (generated)

samples/  
python/ (example agents)

scripts/  
build\_docs.sh  
build\_llms\_full.sh

.github/workflows/  
CI/CD automation

JSON Schema

a2a-protocol.org  
(MkDocs site)

llms-full.txt  
(LLM-optimized)

**Key Directories:**

Directory

Purpose

`specification/`

Contains `a2a.proto` (normative) and `json/a2a.json` (generated at build time)

`docs/`

Human-readable specification, conceptual guides, tutorials, and sample documentation

`docs/topics/`

Deep-dive guides on discovery, task lifecycle, security, extensions

`docs/tutorials/`

Step-by-step implementation guides

`types/`

TypeScript type definitions generated from proto

`samples/`

Example A2A agents and clients

`scripts/`

Build automation (documentation, JSON Schema generation)

`.github/`

CI/CD workflows for linting, testing, documentation deployment

**Build Process:**

The canonical proto file drives all artifact generation:

1.  `protoc` with `protoc-gen-jsonschema` generates `specification/json/a2a.json`
2.  `buf` generates code for SDK repositories via cross-repository dispatch
3.  MkDocs builds the website from Markdown documentation
4.  `scripts/build_llms_full.sh` consolidates documentation into `docs/llms-full.txt` for LLM consumption

Sources: [README.md1-129](https://github.com/google/A2A/blob/629190ae/README.md#L1-L129) [docs/specification.md107-126](https://github.com/google/A2A/blob/629190ae/docs/specification.md#L107-L126)

---

## Relationship to Other Standards

### A2A and Model Context Protocol (MCP)

A2A and MCP are **complementary** standards that address different layers of agent architecture:

Aspect

Model Context Protocol (MCP)

Agent2Agent (A2A)

**Scope**

Agent-to-tool communication

Agent-to-agent communication

**Purpose**

Connects agents to data sources, APIs, and tools

Connects agents to other agents

**Use Case**

An agent queries a database, calls an API, or accesses local files

An agent delegates a task to another agent

**Interaction Model**

Synchronous tool invocation

Task-based asynchronous collaboration

**State Management**

Stateless (per invocation)

Stateful (Task lifecycle)

**Integration Pattern:**

Agents can use MCP internally to access tools/resources while using A2A externally to collaborate with other agents. For example:

1.  A client agent receives a user request
2.  The agent uses MCP to query its local database
3.  The agent uses A2A to delegate specialized processing to a remote agent
4.  The remote agent completes the task and returns results via A2A
5.  The client agent uses MCP to store results in its database

A2A focuses on enabling agents to work together as autonomous entities, while MCP enables agents to access the tools they need to perform their work.

Sources: [README.md121-131](https://github.com/google/A2A/blob/629190ae/README.md#L121-L131) [docs/index.md120-131](https://github.com/google/A2A/blob/629190ae/docs/index.md#L120-L131)

---

## Summary

The A2A Protocol provides a production-ready standard for agent interoperability with:

-   **Canonical data model** in Protocol Buffers ([specification/a2a.proto](https://github.com/google/A2A/blob/629190ae/specification/a2a.proto))
-   **Three protocol bindings**: JSON-RPC 2.0, gRPC, HTTP+JSON/REST
-   **Task-centric** interaction model with stateful lifecycle management
-   **Standardized discovery** via Agent Cards at `/.well-known/agent-card.json`
-   **Flexible update delivery**: polling, streaming (SSE), push notifications
-   **Enterprise security**: OAuth2, OIDC, mTLS, API keys
-   **Extensibility** via formal extension mechanism

The protocol is governed by the Linux Foundation with contributions from 8 founding companies and 170+ partners, with official SDKs for Python, JavaScript, Java, Go, and .NET.

For implementation details, see [SDK Implementations](/google/A2A/4-sdk-implementations). For conceptual deep-dives, see [Key Concepts](/google/A2A/1.1-key-concepts). For complete technical specifications, see [Protocol Specification](/google/A2A/2-protocol-specification).

Sources: [docs/specification.md1-126](https://github.com/google/A2A/blob/629190ae/docs/specification.md#L1-L126) [README.md1-129](https://github.com/google/A2A/blob/629190ae/README.md#L1-L129) [docs/llms.txt1-82](https://github.com/google/A2A/blob/629190ae/docs/llms.txt#L1-L82)
