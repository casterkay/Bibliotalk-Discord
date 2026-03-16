<!--
SYNC IMPACT REPORT
==================
Version change: (none) → 1.0.0 (MAJOR — initial ratification)

Modified principles: N/A (initial adoption)

Added sections:
  - Core Principles (7 principles)
  - Engineering Standards
  - Development Workflow
  - Governance

Removed sections: N/A

Templates requiring updates:
  - .specify/templates/plan-template.md ✅ no changes needed
    (Constitution Check section already references constitution generically)
  - .specify/templates/spec-template.md ✅ no changes needed
    (User stories + acceptance scenarios align with Principle III)
  - .specify/templates/tasks-template.md ✅ no changes needed
    (Phased delivery aligns with Principle V; test-first notes
    align with Principle III)
  - .specify/templates/commands/*.md — no command files found
  - .specify/templates/agent-file-template.md ✅ no changes needed

Follow-up TODOs: None
==================
-->

# Bibliotalk Constitution (Successor Scope)

## Core Principles

### I. Design-First Architecture

Every feature MUST begin with explicit system design before any
implementation code is written.

- A feature specification (`spec.md`) and implementation plan
  (`plan.md`) MUST exist and be approved before coding starts.
- Data models, API contracts, and service boundaries MUST be
  defined in design artifacts — not discovered during implementation.
- Architectural decisions MUST be documented with rationale and
  trade-offs considered. Undocumented decisions are technical debt.
- Cross-service interactions (collector, Discord bots, EverMemOS)
  MUST have explicit contract definitions before integration work begins.

**Rationale**: The successor system integrates YouTube discovery,
EverMemOS memory, and Discord delivery. Upfront design prevents
idempotency failures, citation errors, and operational fragility.

### II. Test-Driven Quality

Code MUST be validated through tests written before or alongside
implementation. Quality gates are non-negotiable.

- Unit tests MUST accompany all business logic (agent behavior,
  ingestion transforms, citation validation, EMOS client ops).
- Contract tests MUST exist for every cross-service boundary
  (EMOS API calls, YouTube discovery adapters, Discord posting).
- Integration tests MUST cover critical user journeys (private chat
  with a figure bot, feed posting for a newly ingested video).
- Tests MUST be deterministic, independently runnable, and fast.
  Flaky tests MUST be fixed or removed — never ignored.
- Code coverage is a guide, not a goal. Focus coverage on
  correctness-critical paths (citation grounding, message routing,
  auth flows).

**Rationale**: A multi-agent system with external service
dependencies has a large surface area for subtle bugs. Disciplined
testing catches regressions early and enables confident refactoring.

### III. Contract-Driven Integration

Service boundaries MUST be defined by explicit, versioned contracts
that both producer and consumer validate against.

- Every HTTP endpoint (FastAPI appservice routes, EMOS REST calls)
  MUST have a Pydantic schema or equivalent typed contract.
- Discord inbound/outbound message shapes (DM chat, thread posting)
  MUST be represented by typed models at the bot boundary.
- Breaking contract changes MUST follow semantic versioning and
  require migration documentation.

**Rationale**: The successor integrates EverMemOS, YouTube adapters,
and Discord APIs. Explicit contracts make failures visible early and
prevent silent grounding/citation regressions.

### IV. Incremental Delivery

Features MUST be delivered in independently testable, deployable
increments aligned with user story priorities.

- Each user story MUST be implementable, testable, and deployable
  without depending on incomplete peer stories.
- MVP functionality MUST work end-to-end before expansion:
  - continuous YouTube transcript ingest into EverMemOS
  - Discord feed posting (one thread per video)
  - grounded DM chat with citations
- Every increment MUST leave the system in a working state.
  Partial features behind incomplete code paths are prohibited —
  use feature flags if staged rollout is needed.
- Implementation phases from the project blueprint MUST be
  respected as dependency boundaries.

**Rationale**: Continuous ingestion + idempotent posting + grounded
DM chat is the value core. Shipping these first validates the system.

### V. Observable Systems

Production and development environments MUST provide sufficient
observability to diagnose issues without ad-hoc debugging.

- All service entry points (poll loops, ingest runs, Discord handlers)
  MUST emit structured logs with correlation IDs.
- External API calls (EverMemOS, YouTube via adapters, Discord) MUST
  log request/response metadata (status, latency, error codes) without
  leaking sensitive content.
- Agent decision traces (ADK tool calls, memory retrievals, citation
  selections) MUST be capturable for debugging and quality review.
- Error states MUST produce actionable log entries — not silent
  failures or generic exception messages.

**Rationale**: Multi-agent systems with async workflows and external
dependencies are notoriously difficult to debug. Structured
observability turns opaque failures into diagnosable incidents.

### VI. Principled Simplicity

Complexity MUST be justified. The simplest solution that meets
requirements is the correct one.

- YAGNI: Do not build for hypothetical future requirements. Build
  for the current phase of the implementation roadmap.
- Abstractions MUST earn their existence by serving at least two
  concrete use cases. Single-use abstractions are premature.
- Prefer standard library and framework primitives over custom
  implementations.
- Every deviation from the simplest approach MUST be documented in
  a Complexity Tracking table with the rejected simpler alternative
  and reason for rejection.

**Rationale**: Complex multi-service architectures naturally
accumulate accidental complexity. Active resistance to unnecessary
abstraction keeps the codebase navigable and development velocity
high.

## Engineering Standards

- **Type Safety**: All Python code MUST use type annotations.
  Pydantic models MUST be used for data validation at service
  boundaries. `Any` types are prohibited in public interfaces.
- **Code Style**: All code MUST pass project linting and formatting
  checks (ruff for Python, eslint/prettier for Node.js) with zero
  warnings. Linter rules are not suggestions.
- **Security**: Credentials, tokens, and secrets MUST never appear
  in source code or logs. Environment-based configuration MUST be
  used for all sensitive values. EverMemOS API keys and Discord bot
  tokens MUST be loaded from environment variables or a secrets manager.
- **Error Handling**: Use typed exceptions for recoverable errors.
  Bare `except:` and `except Exception:` without re-raise or
  specific handling are prohibited. External API failures MUST have
  retry logic with exponential backoff.

## Development Workflow

- **Branch Strategy**: One feature branch per implementation phase
  or user story. Branches MUST be short-lived and merge to `main`
  via pull request.
- **Commit Discipline**: Each commit MUST leave the project in a
  buildable, testable state. Commits MUST have descriptive messages
  following conventional commit format (`feat:`, `fix:`, `docs:`,
  `refactor:`, `test:`, `chore:`).
- **Review Gates**: All pull requests MUST pass automated tests and
  linting before merge. Constitution compliance MUST be verified
  during review.
- **Specification Workflow**: The SpecKit pipeline (`/speckit.specify`
  → `/speckit.plan` → `/speckit.tasks` → `/speckit.implement`) MUST
  be followed for all non-trivial features. Hotfixes and single-file
  bug fixes are exempt.
- **Incremental Validation**: After completing each implementation
  phase, the system MUST be validated end-to-end against the
  corresponding user story acceptance scenarios before proceeding
  to the next phase.

## Governance

- This constitution supersedes all other development practices and
  guidelines. Conflicts between this document and other guidance
  MUST be resolved in favor of the constitution.
- Amendments require: (1) a written proposal documenting the change
  and rationale, (2) review against existing principles for
  consistency, and (3) a version bump following semantic versioning
  (MAJOR for principle removals/redefinitions, MINOR for additions/
  expansions, PATCH for clarifications/wording fixes).
- All pull requests and code reviews MUST verify compliance with
  applicable principles. Non-compliance MUST be flagged and resolved
  before merge.
- Constitution compliance reviews SHOULD be conducted at the start
  of each new implementation phase to ensure alignment as the system
  evolves.

**Version**: 1.0.0 | **Ratified**: 2026-02-28 | **Last Amended**: 2026-02-28
