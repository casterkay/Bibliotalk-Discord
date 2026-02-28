# Nova-Act Overview

## Purpose and Scope

This document provides a high-level introduction to the Nova Act SDK, an AI agent system for automating browser-based workflows. It covers the fundamental architecture, key concepts, and how major components interact.

For detailed information on specific subsystems, see:

-   Architecture details: [Architecture Overview](/aws/nova-act/1.1-architecture-overview)
-   Installation and authentication: [Installation and Setup](/aws/nova-act/1.2-installation-and-setup)
-   Getting started: [Quick Start Guide](/aws/nova-act/1.3-quick-start-guide)
-   Client API: [NovaAct Client](/aws/nova-act/2.1-novaact-client)
-   Browser automation: [Browser Automation](/aws/nova-act/3-browser-automation)
-   Advanced features: [Advanced Features](/aws/nova-act/5-advanced-features)

## What is Nova Act?

Nova Act is a Python SDK that enables developers to build AI agents that automate web browser tasks using natural language instructions. The system combines the Amazon Nova Act AI model with Playwright-based browser automation to execute complex multi-step workflows.

**Core Capabilities:**

-   Natural language task execution via `act()` method
-   Structured data extraction via `act_get()` method
-   Multi-step workflow orchestration with AWS integration
-   Human-in-the-loop (HITL) callbacks for human approval or intervention
-   Custom tool integration beyond the browser
-   Security controls (file access, URL guardrails)
-   Comprehensive observability (logging, telemetry, HTML reports)

**Key Design Principles:**

-   Separation between orchestration (`NovaAct` client) and execution (`ActDispatcher`)
-   Pluggable backend authentication (API key via `StarburstBackend`, AWS IAM via `SunburstBackend`)
-   Stateless AI model interactions with immutable state objects (`Act`, `Step`, `Program`)
-   Extensible actuator pattern for browser control
-   Fail-fast validation with detailed error hierarchy

Sources: [README.md1-42](https://github.com/aws/nova-act/blob/84e8ef56/README.md#L1-L42) [README.md95-110](https://github.com/aws/nova-act/blob/84e8ef56/README.md#L95-L110) [src/nova\_act/\_\_init\_\_.py27-102](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/__init__.py#L27-L102)

## System Architecture

The following diagram shows how the major subsystems connect from the user interface layer down to the browser and AI service:

Supporting Systems

External Services

Backend Layer

Browser Layer

State Objects

Execution Layer

Core Client Layer

User Interface

CLI: act command

Python SDK API

Sample Scripts

NovaAct  
(nova\_act.py)

NovaStateController  
(pause/cancel)

ActDispatcher  
(act\_dispatcher.py)

ProgramRunner  
(program\_runner.py)

NovaActInterpreter  
(nova\_act\_interpreter.py)

Act  
(act.py)

Step  
(step.py)

Program  
(program.py)

DefaultNovaLocalBrowserActuator  
(default\_nova\_local\_browser\_actuator.py)

PlaywrightInstanceManager  
(playwright\_manager.py)

Playwright Page Object

Backend Factory  
(backend.py)

StarburstBackend  
API key auth

SunburstBackend  
AWS IAM auth

Amazon Nova Act Service  
AI Model

Input Validation  
(input\_validation.py)

Error Hierarchy  
(act\_errors.py, errors.py)

Workflow Context  
(workflow.py)

RunInfoCompiler  
(run\_info\_compiler.py)

**Component Responsibilities:**

Component

Primary Responsibility

Key Files

`NovaAct`

Main client API, lifecycle management, context manager

[nova\_act.py](https://github.com/aws/nova-act/blob/84e8ef56/nova_act.py)

`ActDispatcher`

Orchestrates observation-action loop, manages act execution

[act\_dispatcher.py](https://github.com/aws/nova-act/blob/84e8ef56/act_dispatcher.py)

`ProgramRunner`

Executes compiled programs, invokes actuator and tools

[program\_runner.py](https://github.com/aws/nova-act/blob/84e8ef56/program_runner.py)

`DefaultNovaLocalBrowserActuator`

Controls Playwright browser, performs agent actions

[default\_nova\_local\_browser\_actuator.py](https://github.com/aws/nova-act/blob/84e8ef56/default_nova_local_browser_actuator.py)

`Backend` subclasses

Communicate with Nova Act service, handle authentication

[starburst\_backend.py](https://github.com/aws/nova-act/blob/84e8ef56/starburst_backend.py) [sunburst\_backend.py](https://github.com/aws/nova-act/blob/84e8ef56/sunburst_backend.py)

`Workflow`

AWS workflow integration, context management

[workflow.py](https://github.com/aws/nova-act/blob/84e8ef56/workflow.py)

Input Validators

Validate prompts, timeouts, paths, screen resolution

[input\_validation.py](https://github.com/aws/nova-act/blob/84e8ef56/input_validation.py)

`RunInfoCompiler`

Generate HTML/JSON logs and session reports

[run\_info\_compiler.py](https://github.com/aws/nova-act/blob/84e8ef56/run_info_compiler.py)

Sources: Diagram 1 from high-level overview, [src/nova\_act/\_\_init\_\_.py27-102](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/__init__.py#L27-L102) [README.md95-232](https://github.com/aws/nova-act/blob/84e8ef56/README.md#L95-L232)

## Key Concepts

### Acts, Steps, and Programs

The execution model follows a hierarchical state machine:

Act  
User prompt + session context

Step 1  
Observation → Model → Program

Step 2  
Observation → Model → Program

Step 3  
Observation → Model → Program

Program 1  
List of Calls

Program 2  
List of Calls

Program 3  
List of Calls

Call: agent\_click(...)

Call: agent\_type(...)

Call: agent\_scroll(...)

Call: agent\_wait(...)

**Definitions:**

-   **Act**: Represents a complete task execution initiated by an `act()` or `act_get()` call. Contains the user prompt, session metadata, and accumulates steps until task completion. Immutable once created.
    
-   **Step**: Represents one iteration of the observation-action loop. Contains:
    
    -   `ModelInput`: Browser observation (screenshot + DOM) sent to AI model
    -   `ModelOutput`: Program AST returned by AI model
    -   Compiled `Program` ready for execution
-   **Program**: A list of executable `Call` objects derived from the AI model's output. Each call invokes either an agent action (browser manipulation) or a custom tool.
    
-   **Call**: A single function invocation with arguments, representing one atomic operation like `agent_click(element_id)` or `custom_tool(param1, param2)`.
    

Sources: [README.md388-425](https://github.com/aws/nova-act/blob/84e8ef56/README.md#L388-L425) Diagram 6 from high-level overview, [src/nova\_act/types/act.py](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/types/act.py) [src/nova\_act/types/step.py](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/types/step.py) [src/nova\_act/types/program.py](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/types/program.py)

### Authentication Methods

Nova Act supports two authentication paths, selected automatically based on configuration:

Authentication Type

Backend Class

Configuration

Use Case

**API Key**

`StarburstBackend`

`nova_act_api_key` parameter or `NOVA_ACT_API_KEY` env var

Playground and developer tools (nova.amazon.com)

**AWS IAM**

`SunburstBackend`

AWS credentials via boto3, used when `Workflow` is provided

Production workflows deployed to AWS

The `Backend Factory` automatically selects the appropriate backend:

-   If a `Workflow` context is provided → `SunburstBackend` with AWS credentials
-   Otherwise → `StarburstBackend` with API key authentication

Sources: [README.md56-75](https://github.com/aws/nova-act/blob/84e8ef56/README.md#L56-L75) [README.md205-313](https://github.com/aws/nova-act/blob/84e8ef56/README.md#L205-L313) Diagram 4 from high-level overview

### Browser Actuators

The actuator pattern abstracts browser control:

BrowserActuatorBase  
(interface/browser.py)  
Abstract interface

DefaultNovaLocalBrowserActuator  
(default/default\_nova\_local\_browser\_actuator.py)  
Playwright-based implementation

ExtensionActuator  
(extension.py)  
Deprecated

Agent Actions:  
agent\_click()  
agent\_type()  
agent\_scroll()  
agent\_press\_key()  
agent\_wait()  
agent\_cursor\_position()

Playwright Page API  
Underlying automation

**Key Methods:**

-   `take_observation()`: Captures screenshot and DOM for model input
-   `execute_agent_action()`: Performs browser actions like click, type, scroll
-   `start()` / `stop()`: Manage browser lifecycle

The `DefaultNovaLocalBrowserActuator` is the standard implementation, using Playwright to control a local Chrome/Chromium instance.

Sources: [src/nova\_act/tools/browser/interface/browser.py](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/tools/browser/interface/browser.py) [src/nova\_act/tools/browser/default/default\_nova\_local\_browser\_actuator.py](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/tools/browser/default/default_nova_local_browser_actuator.py) [README.md926-996](https://github.com/aws/nova-act/blob/84e8ef56/README.md#L926-L996)

## Execution Flow

The following sequence shows a complete execution from `act()` call to browser actions:

BrowserActuatorProgramRunnerActDispatcherBackendInputValidatorNovaAct ClientUserBrowserActuatorProgramRunnerActDispatcherBackendInputValidatorNovaAct ClientUserCreates Program from ASTalt\[If error orreturnstatement\]loop\[For each call in program\]alt\[Taskcompleted\]loop\[Until task complete or timeout\]act(prompt, timeout, max\_steps)validate\_prompt(prompt)validate\_timeout(timeout)validate\_step\_limit(max\_steps)create\_act(prompt)act\_iddispatch(act)take\_observation()BrowserObservationstep(observation)Call AI modelStep with program ASTinterpret\_ast(statements)run(program, actuator, tools)execute\_agent\_action()CallResultBreak executionProgramResultBreak loopupdate\_act(status)ActResultcompile\_run\_info()ActResult with metadata

**Key Points:**

1.  **Validation First**: Input validation occurs before any backend calls
2.  **Stateless Iterations**: Each step is independent, model receives fresh observation
3.  **AST Interpretation**: Model output (AST) is parsed into executable `Program`
4.  **Atomic Execution**: Programs execute call-by-call until completion or error
5.  **Comprehensive Logging**: All execution traces compiled into HTML/JSON reports

Sources: Diagram 2 from high-level overview, [README.md95-110](https://github.com/aws/nova-act/blob/84e8ef56/README.md#L95-L110) [README.md954-996](https://github.com/aws/nova-act/blob/84e8ef56/README.md#L954-L996)

## Error Handling Architecture

Nova Act provides a comprehensive error taxonomy for precise error handling:

Python Exception

NovaActError  
Client lifecycle errors

ActError  
Act execution errors

Lifecycle Errors:  
StartFailed  
StopFailed  
PauseFailed

ValidationFailed:  
ClientNotStarted  
InvalidInputLength  
InvalidScreenResolution  
InvalidPath  
InvalidTimeout  
InvalidMaxSteps

Authentication:  
AuthError  
IAMAuthError

ActAgentError:  
ActAgentFailed  
ActInvalidModelGenerationError  
ActExceededMaxStepsError

ActExecutionError:  
ActActuationError  
ActCanceledError  
ActToolError  
ActStateGuardrailError

ActAPIError:  
ActClientError (4xx)  
ActServerError (5xx)  
ActTimeoutError

**Error Categories:**

Category

When Raised

Retry Strategy

`NovaActError`

Client lifecycle issues (start/stop/validation)

Fix configuration, restart client

`ActAgentError`

AI model cannot complete task

Rephrase prompt, break into smaller steps

`ActExecutionError`

Local execution failures

Check actuator state, review guardrails

`ActClientError` (4xx)

Invalid requests to service

Fix request parameters

`ActServerError` (5xx)

Service-side failures

Retry with backoff

**Exception Handling Pattern:**

```
from nova_act import NovaAct, ActAgentError, ActTimeoutError

with NovaAct(starting_page="https://example.com") as nova:
    try:
        result = nova.act("Complete task")
    except ActAgentError as e:
        # Model couldn't complete - refine prompt
        result = nova.act("Complete task with more specific instructions")
    except ActTimeoutError:
        # Task took too long - increase timeout or break into steps
        pass
```

Sources: [src/nova\_act/types/act\_errors.py](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/types/act_errors.py) [src/nova\_act/types/errors.py](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/types/errors.py) [README.md515-527](https://github.com/aws/nova-act/blob/84e8ef56/README.md#L515-L527) Diagram 3 from high-level overview

## Extension Points

Nova Act provides multiple extension mechanisms:

Observability

Security Controls

Tool System

Human Integration

Workflow Integration

NovaAct Client

@workflow decorator  
(workflow.py)

Workflow context manager

Python ContextVars

HumanInputCallbacksBase  
(human\_input\_callback.py)

approve() callback

ui\_takeover() callback

@tool decorator  
(strands)

Custom tools list

MCP Integration

SecurityOptions  
(features.py)

allowed\_file\_open\_paths  
allowed\_file\_upload\_paths

state\_guardrail callback

StopHook interface

S3Writer  
(s3\_writer.py)

event\_callback

**Extension Points:**

1.  **Workflows**: Use `@workflow` decorator or `Workflow` context manager for AWS integration
2.  **Human-in-the-Loop**: Implement `HumanInputCallbacksBase` for approval/takeover patterns
3.  **Custom Tools**: Use `@tool` decorator to expose Python functions to the agent
4.  **Security Guardrails**: Provide `state_guardrail` callback to control URL navigation
5.  **Observability Hooks**: Implement `StopHook` interface (e.g., `S3Writer`) for custom logging

**Example Integration:**

```
from nova_act import NovaAct, workflow, tool, SecurityOptions

@tool
def get_customer_data(customer_id: str) -> dict:
    """Custom tool accessible to agent"""
    return {"id": customer_id, "name": "Example"}

@workflow(workflow_definition_name="my-workflow")
def main():
    with NovaAct(
        starting_page="https://example.com",
        tools=[get_customer_data],
        security_options=SecurityOptions(
            allowed_file_upload_paths=["/safe/path/*"]
        )
    ) as nova:
        nova.act("Process customer data")
```

Sources: [README.md205-313](https://github.com/aws/nova-act/blob/84e8ef56/README.md#L205-L313) [README.md446-494](https://github.com/aws/nova-act/blob/84e8ef56/README.md#L446-L494) [README.md496-514](https://github.com/aws/nova-act/blob/84e8ef56/README.md#L496-L514) [README.md617-675](https://github.com/aws/nova-act/blob/84e8ef56/README.md#L617-L675) [README.md836-870](https://github.com/aws/nova-act/blob/84e8ef56/README.md#L836-L870) Diagram 5 from high-level overview

## Configuration and Lifecycle

The `NovaAct` client follows a standard lifecycle pattern:

**Initialization Parameters:**

Parameter

Type

Purpose

`starting_page`

str

Initial URL (http/https/file)

`headless`

bool

Run browser without UI

`user_data_dir`

str

Chrome profile directory path

`clone_user_data_dir`

bool

Whether to clone profile before use

`nova_act_api_key`

str

API key for authentication

`workflow`

Workflow

AWS workflow context

`tools`

list

Custom tools for agent

`human_input_callbacks`

HumanInputCallbacksBase

HITL implementation

`security_options`

SecurityOptions

File access and guardrails

`state_guardrail`

callable

URL validation callback

`logs_directory`

str

Output directory for logs/videos

`record_video`

bool

Enable session recording

`proxy`

dict

Proxy configuration

**Lifecycle Modes:**

```
# Context manager (recommended)
with NovaAct(starting_page="https://example.com") as nova:
    result = nova.act("Complete task")
    # Automatic cleanup on exit

# Manual lifecycle
nova = NovaAct(starting_page="https://example.com")
nova.start()
try:
    result = nova.act("Complete task")
finally:
    nova.stop()
```

**State Control:**

-   `pause()`: Pause current execution (Ctrl+X in terminal)
-   `cancel()`: Cancel and mark as failed (Ctrl+C in terminal)
-   `NovaStateController`: Internal component managing pause/cancel state

Sources: [README.md929-948](https://github.com/aws/nova-act/blob/84e8ef56/README.md#L929-L948) [README.md95-130](https://github.com/aws/nova-act/blob/84e8ef56/README.md#L95-L130) [src/nova\_act/nova\_act.py](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/nova_act.py)

## Data Flow and State Management

The following shows how data flows through the system:

User Input:  
prompt, config

Act State:  
id, session\_id,  
prompt, steps\[\]

Step State:  
ModelInput  
ModelOutput

ModelInput:  
screenshot,  
DOM tree,  
context

ModelOutput:  
program AST,  
status

Program:  
Call objects

Results:  
ActResult,  
ActMetadata,  
HTML report,  
JSON logs

**Key Characteristics:**

-   **Immutable State Objects**: `Act`, `Step`, and `Program` are immutable after creation
-   **Append-Only Steps**: Steps are accumulated in the `Act` object, never modified
-   **Stateless Model**: Each model call receives complete observation, no hidden state
-   **Comprehensive Metadata**: `ActMetadata` tracks timing, step counts, errors
-   **Multiple Output Formats**: HTML (human-readable), JSON (machine-readable)

Sources: Diagram 6 from high-level overview, [src/nova\_act/types/act.py](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/types/act.py) [src/nova\_act/types/step.py](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/types/step.py) [src/nova\_act/types/act\_result.py](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/types/act_result.py) [src/nova\_act/types/act\_metadata.py](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/types/act_metadata.py)

## Version and Platform Support

**Current Version:** 3.0.0.0

**Supported Platforms:**

-   macOS Sierra+
-   Ubuntu 22.04+
-   Windows 10+ (via WSL2)

**Python Requirement:** 3.10 or above

**Browser Support:**

-   Google Chrome (recommended)
-   Chromium (default, installed via Playwright)

**Language Support:** English

Sources: [src/nova\_act/\_\_version\_\_.py14](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/__version__.py#L14-L14) [README.md43-48](https://github.com/aws/nova-act/blob/84e8ef56/README.md#L43-L48) [FAQ.md79-81](https://github.com/aws/nova-act/blob/84e8ef56/FAQ.md#L79-L81)
