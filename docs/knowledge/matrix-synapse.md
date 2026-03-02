# Core Server Components

This document provides an overview of the fundamental components that make up the core of a Synapse homeserver. These components are responsible for handling server startup, request processing, state management, and data storage. For more specific details about individual subsystems like the Federation System, see [Federation System](/matrix-org/synapse/3-federation-system), or for details about Event and State Management, see [Event and State Management](/matrix-org/synapse/2.4-event-and-state-management).

## Server Initialization and Configuration

When Synapse starts, it follows a structured initialization process that sets up all required components and starts listening for client and federation requests.

setup()

Load HomeServerConfig

Create SynapseHomeServer

Setup Logging

hs.setup()

Register Start Callback

Start Reactor

hs.start\_listening()

Start HTTP Listeners

The central component for server initialization is the `SynapseHomeServer` class which extends `HomeServer` and handles the configuration of HTTP listeners and resources.

The startup sequence begins with the `setup()` function in the homeserver.py file:

1.  Configuration loading (via `HomeServerConfig`)
2.  Creation of a `SynapseHomeServer` instance
3.  Setup of logging
4.  Component initialization through `hs.setup()`
5.  Registration of a start callback
6.  Starting the Twisted reactor
7.  Configuring and starting HTTP listeners

Sources: [synapse/app/homeserver.py289-346](https://github.com/matrix-org/synapse/blob/be65a8ec/synapse/app/homeserver.py#L289-L346) [synapse/app/homeserver.py77-152](https://github.com/matrix-org/synapse/blob/be65a8ec/synapse/app/homeserver.py#L77-L152) [synapse/app/homeserver.py242-286](https://github.com/matrix-org/synapse/blob/be65a8ec/synapse/app/homeserver.py#L242-L286) [synapse/app/\_base.py112-128](https://github.com/matrix-org/synapse/blob/be65a8ec/synapse/app/_base.py#L112-L128)

### Configuration System

Synapse's configuration is managed by a hierarchical system of `Config` classes, each responsible for a specific aspect of the server:

HomeServerConfig

+config: Dict

+parse\_config\_dict()

+read\_config()

RootConfig

+config\_files: List\[str\]

+read\_config()

+generate\_config()

ServerConfig

+server\_name: str

+listeners: List\[ListenerConfig\]

+bind\_addresses: List\[str\]

LoggingConfig

DatabaseConfig

MediaConfig

RegistrationConfig

Config

+section: str

+read\_config(config)

+parse\_size(value)

+parse\_duration(value)

Each configuration class has a dedicated section and responsibility, with `ServerConfig` handling core settings like server name, listeners, and binding addresses.

Sources: [synapse/config/\_base.py154-192](https://github.com/matrix-org/synapse/blob/be65a8ec/synapse/config/_base.py#L154-L192) [synapse/config/server.py290-393](https://github.com/matrix-org/synapse/blob/be65a8ec/synapse/config/server.py#L290-L393) [synapse/config/logger.py47-73](https://github.com/matrix-org/synapse/blob/be65a8ec/synapse/config/logger.py#L47-L73)

## HTTP Request Handling

Synapse uses a Twisted-based HTTP server for processing client and federation requests. The request handling system routes incoming requests to the appropriate handlers and returns responses.

Client HTTP Request

HTTP Listener

SynapseRequest

Resource Tree

JsonResource

Find Handler by Path/Method

Servlet Callback

Process Request

HTTP Response

Key components in this flow:

1.  **HTTP Listeners**: Configured in `start_listening()` to accept connections
2.  **SynapseRequest**: Extends Twisted's Request with metrics, logging, and context
3.  **Resource Tree**: Routes requests based on path
4.  **JsonResource**: Handles JSON API requests and responses
5.  **Servlets**: Process specific types of requests

The `_listener_http` method in `SynapseHomeServer` configures HTTP listeners with appropriate resources:

```
def _listener_http(self, config, listener_config):    # Configure HTTP resources based on listener type    resources = {"/health": HealthResource()}        # Add resources based on configuration    for res in listener_config.http_options.resources:        for name in res.names:            resources.update(self._configure_named_resource(name, res.compress))        # Create the resource tree and start listening    root_resource = create_resource_tree(resources, root_resource)    ports = listen_http(self, listener_config, root_resource, ...)    return ports
```

The `JsonResource` class is central to request routing:

```
def register_paths(self, method, path_patterns, callback, servlet_classname):    # Register handler for HTTP method and path patterns    for path_pattern in path_patterns:        self._routes.setdefault(path_pattern, {})[method] = _PathEntry(            callback, servlet_classname        ) def _get_handler_for_request(self, request):    # Find the appropriate handler for a request    request_path = request.path.decode("ascii")    request_method = request.method        for path_pattern, methods in self._routes.items():        match = path_pattern.match(request_path)        if match:            path_entry = methods.get(request_method)            if path_entry:                return path_entry.callback, path_entry.servlet_classname, match.groupdict()        # No handler found    raise UnrecognizedRequestError(code=404)
```

Sources: [synapse/app/homeserver.py80-151](https://github.com/matrix-org/synapse/blob/be65a8ec/synapse/app/homeserver.py#L80-L151) [synapse/http/server.py425-550](https://github.com/matrix-org/synapse/blob/be65a8ec/synapse/http/server.py#L425-L550) [synapse/http/site.py52-78](https://github.com/matrix-org/synapse/blob/be65a8ec/synapse/http/site.py#L52-L78)

## Core Functional Components

The `HomeServer` class serves as a central provider for the various functional components that implement Matrix homeserver capabilities:

HomeServer

+get\_auth\_handler()

+get\_room\_handler()

+get\_event\_creation\_handler()

+get\_federation\_handler()

+get\_sync\_handler()

+get\_presence\_handler()

+get\_device\_handler()

+get\_e2e\_keys\_handler()

+get\_datastores()

AuthHandler

+validate\_token()

+register\_user()

+login()

RoomHandler

+create\_room()

+update\_room\_summary()

+get\_room\_data()

EventCreationHandler

+create\_event()

+handle\_new\_client\_event()

+send\_event()

FederationHandler

SyncHandler

PresenceHandler

DeviceHandler

E2eKeysHandler

DataStores

MainStore

StateStore

Each component handles a specific area of functionality:

Component

Responsibility

`AuthHandler`

User authentication, registration, access tokens

`RoomHandler`

Room creation and management

`EventCreationHandler`

Creating and sending room events

`FederationHandler`

Communication with other homeservers

`SyncHandler`

Client synchronization (the `/sync` endpoint)

`PresenceHandler`

User online/offline status management

`DeviceHandler`

Client device tracking and management

`E2eKeysHandler`

End-to-end encryption key management

These components implement the core business logic of a Matrix homeserver and interact with the storage layer and each other to provide a complete implementation of the Matrix protocol.

Sources: Architecture diagrams from input, [synapse/server.py](https://github.com/matrix-org/synapse/blob/be65a8ec/synapse/server.py) (implied from context)

## Storage Layer

The storage layer in Synapse follows a modular, composable design with specialized store classes for different types of data:

DataStore

+get\_events()

+get\_state\_ids\_for\_event()

+persist\_event()

+store\_room()

+get\_users\_in\_room()

SQLBaseStore

+db\_pool: DatabasePool

+\_invalidate\_state\_caches()

+process\_replication\_rows()

EventsStore

+get\_event()

+persist\_events()

StateStore

+get\_state\_ids\_for\_event()

+get\_state\_group\_for\_events()

UserDirectoryStore

RegistrationStore

RoomMemberStore

PusherStore

DatabasePool

+engine: Engine

+execute()

+execute\_batch()

Engine

The storage architecture is organized as:

1.  **SQLBaseStore**: Base class with common database functionality
2.  **Specialized Stores**: Mixins for specific data types (events, state, users, etc.)
3.  **DataStore**: Combines all store mixins into a complete data access layer
4.  **DatabasePool**: Manages database connections and executes SQL queries
5.  **Engine**: Abstracts database backend differences (SQLite vs PostgreSQL)

The `SQLBaseStore` provides core database functionality:

```
class SQLBaseStore(metaclass=ABCMeta):    """Base class for data stores that holds helper functions."""        db_pool: DatabasePool        def __init__(self, database, db_conn, hs):        self.hs = hs        self._clock = hs.get_clock()        self.database_engine = database.engine        self.db_pool = database        def process_replication_rows(self, stream_name, instance_name, token, rows):        """Processes incoming replication data to invalidate caches."""        pass            def _invalidate_state_caches(self, room_id, members_changed):        """Invalidates caches based on state changes."""        # Invalidate various caches
```

The storage structure allows for flexibility in how data is stored and accessed, with specialized stores for different types of data that can be composed together.

Sources: [synapse/storage/\_\_init\_\_.py16-37](https://github.com/matrix-org/synapse/blob/be65a8ec/synapse/storage/__init__.py#L16-L37) [synapse/storage/\_base.py33-191](https://github.com/matrix-org/synapse/blob/be65a8ec/synapse/storage/_base.py#L33-L191) [synapse/storage/roommember.py26-55](https://github.com/matrix-org/synapse/blob/be65a8ec/synapse/storage/roommember.py#L26-L55)

## Listeners and Request Processing

Synapse uses a configurable listener system to accept different types of connections:

SynapseHomeServer

Listeners

+List\[ListenerConfig\]

HttpListener

+port: int

+bind\_addresses: List\[str\]

+tls: bool

+type: "http"

+resources: List\[ResourceConfig\]

ManholeListener

+port: int

+bind\_addresses: List\[str\]

+type: "manhole"

MetricsListener

+port: int

+bind\_addresses: List\[str\]

+type: "metrics"

ClientResource

+register\_servlets()

+handle\_requests()

FederationResource

MediaResource

KeyResource

The listener configuration enables Synapse to serve different APIs on different ports or interfaces:

Listener Type

Purpose

`http`

Handles HTTP requests for client, federation, media, etc.

`manhole`

Provides SSH access for debugging (development/admin use)

`metrics`

Exposes Prometheus metrics

HTTP listeners can serve multiple resource types:

Resource

Endpoints

Purpose

`client`

`/_matrix/client/*`

Client-server API

`federation`

`/_matrix/federation/*`

Server-server API

`media`

`/_matrix/media/*`

Media repository

`keys`

`/_matrix/key/*`

Server key distribution

`metrics`

`/metrics`

Prometheus metrics

This modular design allows for flexible deployment configurations, including worker-based setups where different processes handle different types of requests.

Sources: [synapse/config/server.py170-259](https://github.com/matrix-org/synapse/blob/be65a8ec/synapse/config/server.py#L170-L259) [synapse/app/homeserver.py80-151](https://github.com/matrix-org/synapse/blob/be65a8ec/synapse/app/homeserver.py#L80-L151)

## Event Processing Pipeline

At the core of Synapse is the event processing pipeline, which handles events from both local clients and federation:

POST /room/send

/send transaction

Local Client

Client API

Remote Server

Federation API

Event Creation Handler

Federation Event Handler

Auth Rules Check

State Resolution

Event Persistence

Notifier

Sync Handler

Push Rule Evaluator

Federation Sender

This pipeline ensures that events are properly validated, authorized, and distributed to all interested parties:

1.  **Event Creation**: Events are created from client requests or received from federation
2.  **Auth Rules**: The event is checked against the room's auth rules
3.  **State Resolution**: The room state is resolved (especially important for conflict resolution)
4.  **Event Persistence**: The event is stored in the database
5.  **Notification**: Interested parties are notified about the new event
6.  **Distribution**: The event is sent to clients via sync and to other servers via federation

This event flow is central to Matrix's distributed nature, allowing for consistent state across the federation.

Sources: Event Flow diagram from input

## Summary

The Core Server Components of Synapse provide the foundation for a Matrix homeserver. They handle server initialization, request processing, event handling, state management, and data storage. These components work together to implement the Matrix protocol's client-server and server-server APIs.

The modular architecture allows for flexibility in deployment, from single-process instances to distributed worker setups, while maintaining the core functionality required for a Matrix homeserver.

Sources: [synapse/app/homeserver.py](https://github.com/matrix-org/synapse/blob/be65a8ec/synapse/app/homeserver.py) [synapse/storage/\_\_init\_\_.py](https://github.com/matrix-org/synapse/blob/be65a8ec/synapse/storage/__init__.py) [synapse/http/server.py](https://github.com/matrix-org/synapse/blob/be65a8ec/synapse/http/server.py) [synapse/config/server.py](https://github.com/matrix-org/synapse/blob/be65a8ec/synapse/config/server.py)
