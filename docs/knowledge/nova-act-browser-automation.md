# Browser Automation

## Purpose and Scope

This document provides an overview of NovaAct's browser automation system, covering the actuation architecture, Playwright integration, and browser lifecycle management. Browser automation is the foundation that enables NovaAct to execute natural language commands by controlling a web browser programmatically.

For detailed information on specific aspects of browser automation:

-   Browser actuation interfaces and implementations: see [Browser Actuation Architecture](/aws/nova-act/3.1-browser-actuator-architecture)
-   Playwright lifecycle, launch modes, and cross-platform considerations: see [Playwright Integration](/aws/nova-act/3.2-playwright-integration)
-   Browser configuration options and settings: see [Browser Configuration](/aws/nova-act/3.3-browser-configuration)

---

## Actuation Architecture

NovaAct uses a layered architecture to abstract browser control operations. At the top level, the `NovaAct` client class delegates all browser automation to a `BrowserActuatorBase` implementation.

### Architecture Hierarchy

**Sources:** [src/nova\_act/nova\_act.py29-45](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/nova_act.py#L29-L45) [src/nova\_act/tools/browser/interface/browser.py](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/tools/browser/interface/browser.py)

### BrowserActuatorBase Interface

The `BrowserActuatorBase` interface defines the contract for browser control implementations. Located at [src/nova\_act/tools/browser/interface/browser.py](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/tools/browser/interface/browser.py) any actuator must provide:

Method/Property

Description

`started`

Boolean property indicating if the browser has been launched

`start(starting_page, session_logs_directory)`

Initialize and launch the browser with the specified starting page and log directory

`stop()`

Shut down the browser and clean up resources

**Sources:** [src/nova\_act/tools/browser/interface/browser.py](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/tools/browser/interface/browser.py) [src/nova\_act/nova\_act.py342-386](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/nova_act.py#L342-L386)

### PlaywrightPageManagerBase Interface

The `PlaywrightPageManagerBase` interface extends `BrowserActuatorBase` to provide access to Playwright page objects. Located at [src/nova\_act/tools/browser/interface/playwright\_pages.py](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/tools/browser/interface/playwright_pages.py) it defines:

Method/Property

Description

`pages`

List of all Playwright `Page` objects in the browser context

`get_page(index)`

Retrieve a specific page by index, or the active page if `index == -1`

This interface enables users to access Playwright's `Page` API directly for operations that require low-level control, such as typing sensitive information like passwords.

**Sources:** [src/nova\_act/tools/browser/interface/playwright\_pages.py](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/tools/browser/interface/playwright_pages.py) [src/nova\_act/nova\_act.py465-513](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/nova_act.py#L465-L513)

### DefaultNovaLocalBrowserActuator

`DefaultNovaLocalBrowserActuator` is the primary implementation of the actuation interfaces, located at [src/nova\_act/tools/browser/default/default\_nova\_local\_browser\_actuator.py](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/tools/browser/default/default_nova_local_browser_actuator.py) It wraps a `PlaywrightInstanceManager` to handle browser lifecycle operations.

The `NovaAct` client initializes the actuator during construction:

```
# From NovaAct.__init__ at line 133
actuator: ManagedActuatorType | BrowserActuatorBase = DefaultNovaLocalBrowserActuator
```

Users can customize browser automation by:

1.  Passing a custom actuator type that subclasses `DefaultNovaLocalBrowserActuator` [src/nova\_act/nova\_act.py350-365](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/nova_act.py#L350-L365)
2.  Passing a custom actuator instance that implements `BrowserActuatorBase` [src/nova\_act/nova\_act.py366-371](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/nova_act.py#L366-L371)

**Warning:** Custom actuators that deviate from NovaAct's standard observation and I/O formats may impact AI model performance. This warning is logged at [src/nova\_act/nova\_act.py352-356](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/nova_act.py#L352-L356) and [src/nova\_act/nova\_act.py367-369](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/nova_act.py#L367-L369)

**Sources:** [src/nova\_act/tools/browser/default/default\_nova\_local\_browser\_actuator.py](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/tools/browser/default/default_nova_local_browser_actuator.py) [src/nova\_act/nova\_act.py40-42](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/nova_act.py#L40-L42) [src/nova\_act/nova\_act.py133](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/nova_act.py#L133-L133) [src/nova\_act/nova\_act.py350-371](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/nova_act.py#L350-L371)

### ExtensionActuator (Deprecated)

The `ExtensionActuator`, located at [src/nova\_act/impl/extension.py](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/impl/extension.py) is deprecated and falls back to `DefaultNovaLocalBrowserActuator`:

```
if actuator is ExtensionActuator:
    _LOGGER.warning(
        "`ExtensionActuator` is deprecated and no longer has any effect. "
        "Falling back to default behavior."
    )
    actuator = DefaultNovaLocalBrowserActuator
```

**Sources:** [src/nova\_act/impl/extension.py](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/impl/extension.py) [src/nova\_act/nova\_act.py29](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/nova_act.py#L29-L29) [src/nova\_act/nova\_act.py239-243](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/nova_act.py#L239-L243)

---

## Playwright Integration

NovaAct uses [Playwright](https://playwright.dev/python/) for browser automation. The `PlaywrightInstanceManager` class, located at [src/nova\_act/impl/playwright.py](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/impl/playwright.py) encapsulates all Playwright-specific operations, including browser lifecycle management, page access, and context control.

### PlaywrightInstanceManager Responsibilities

Playwright API Resources

PlaywrightInstanceManager Class

creates/connects

launches/attaches

initializes

closes

stops if owned

returns

provides access

returns active

start()

stop()

get\_page(index)

context property

main\_page property

playwright.sync\_api.Playwright

playwright.sync\_api.BrowserContext

playwright.sync\_api.Page list

**Sources:** [src/nova\_act/impl/playwright.py](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/impl/playwright.py) [src/nova\_act/nova\_act.py23](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/nova_act.py#L23-L23)

### Browser Lifecycle

The lifecycle follows a strict initialization and teardown sequence managed by `PlaywrightInstanceManager`:

1.  **Initialization** via `PlaywrightInstanceOptions` [src/nova\_act/tools/browser/default/playwright\_instance\_options.py](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/tools/browser/default/playwright_instance_options.py)
    
    -   Configure options: headless mode, screen dimensions, user agent, video recording
    -   Set browser launch parameters: Chrome channel, user data directory, proxy settings
    -   Validate configuration (e.g., CDP mode cannot record video)
    -   Options are created in `NovaAct.__init__` at [src/nova\_act/nova\_act.py320-339](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/nova_act.py#L320-L339)
2.  **Start** via `DefaultNovaLocalBrowserActuator.start()` [src/nova\_act/tools/browser/default/default\_nova\_local\_browser\_actuator.py](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/tools/browser/default/default_nova_local_browser_actuator.py)
    
    -   Create or attach Playwright instance
    -   Launch browser or connect to CDP endpoint
    -   Initialize browser context with configured options
    -   Navigate to starting page if provided
    -   Called from `NovaAct.start()` at [src/nova\_act/nova\_act.py601](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/nova_act.py#L601-L601)
3.  **Stop** via `DefaultNovaLocalBrowserActuator.stop()` [src/nova\_act/tools/browser/default/default\_nova\_local\_browser\_actuator.py](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/tools/browser/default/default_nova_local_browser_actuator.py)
    
    -   Rename and save video recordings (if enabled)
    -   Close browser context (if owned)
    -   Terminate launched Chrome process (if applicable)
    -   Stop Playwright instance (if owned)
    -   Called from `NovaAct.stop()` at [src/nova\_act/nova\_act.py656](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/nova_act.py#L656-L656)

**Sources:** [src/nova\_act/tools/browser/default/default\_nova\_local\_browser\_actuator.py](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/tools/browser/default/default_nova_local_browser_actuator.py) [src/nova\_act/tools/browser/default/playwright\_instance\_options.py](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/tools/browser/default/playwright_instance_options.py) [src/nova\_act/nova\_act.py320-339](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/nova_act.py#L320-L339) [src/nova\_act/nova\_act.py579-618](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/nova_act.py#L579-L618) [src/nova\_act/nova\_act.py652-672](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/nova_act.py#L652-L672)

### Page Management

The `PlaywrightInstanceManager` tracks the active page and provides indexed access to all pages in the browser context:

Property/Method

Description

`main_page`

Returns the active page (equivalent to `get_page(-1)`)

`get_page(index)`

Returns page at specified index; `-1` returns active page

`pages`

Returns all pages from `BrowserContext.pages`

`_active_page`

Internal property that returns the last page in the context

Pages are tracked in the order they appear in the `BrowserContext.pages` list from Playwright's API. The active page is always the last page in this list, accessed via `self._context.pages[-1]`.

**Sources:** [src/nova\_act/impl/playwright.py](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/impl/playwright.py) [src/nova\_act/tools/browser/interface/playwright\_pages.py](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/tools/browser/interface/playwright_pages.py)

---

## Browser Launch Modes

NovaAct supports three distinct browser launch modes, each suited to different use cases:

### Launch Mode Comparison

Launch Mode Decision Logic

No

Yes

Yes

No

DefaultNovaLocalBrowserActuator.start()

cdp\_endpoint\_url  
provided?

use\_default\_chrome\_browser  
\== True?

Direct Launch Mode  
playwright.chromium  
.launch\_persistent\_context()

Default Chrome Mode  
macOS only  
Launch Chrome binary  
then connect\_over\_cdp()

CDP Connection Mode  
playwright.chromium  
.connect\_over\_cdp()

Browser ready  
BrowserContext created

**Sources:** [src/nova\_act/impl/playwright.py](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/impl/playwright.py) [src/nova\_act/tools/browser/default/default\_nova\_local\_browser\_actuator.py](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/tools/browser/default/default_nova_local_browser_actuator.py)

### 1\. Direct Launch Mode

**When used:** No `cdp_endpoint_url` provided and `use_default_chrome_browser=False` (default)

**Process:**

1.  Install Playwright browser binaries if needed (via `_maybe_install_playwright()`)
2.  Configure launch arguments (window size, headless mode, etc.) based on `PlaywrightInstanceOptions`
3.  Launch browser with `playwright.chromium.launch_persistent_context()`
4.  Initialize user agent (auto-detected with custom suffix "NovaAct")
5.  Configure video recording if `record_video=True` in options

**Key features:**

-   Full control over browser configuration via `PlaywrightInstanceOptions`
-   Supports video recording in `session_logs_directory`
-   Supports custom Chrome channels via `chrome_channel` parameter
-   Falls back to Chromium if specified channel unavailable
-   Uses persistent context with `user_data_dir` for session state

**Sources:** [src/nova\_act/impl/playwright.py](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/impl/playwright.py) [src/nova\_act/tools/browser/default/playwright\_instance\_options.py](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/tools/browser/default/playwright_instance_options.py) [README.md83-88](https://github.com/aws/nova-act/blob/84e8ef56/README.md#L83-L88)

### 2\. CDP Connection Mode

**When used:** `cdp_endpoint_url` parameter is provided to `NovaAct.__init__`

**Process:**

1.  Connect to browser via `playwright.chromium.connect_over_cdp(cdp_endpoint_url)`
2.  Attach to first available context from browser
3.  Set custom user agent header if `user_agent` parameter provided
4.  Either create new page or reuse existing page based on `cdp_use_existing_page` flag

**Limitations validated at initialization:**

-   Cannot record video (validation at [src/nova\_act/impl/inputs.py](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/impl/inputs.py))
-   Cannot specify `profile_directory` (validation at [src/nova\_act/impl/inputs.py](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/impl/inputs.py))
-   Cannot configure `proxy` settings (validation at [src/nova\_act/impl/inputs.py](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/impl/inputs.py))

**Use cases:**

-   Connecting to Amazon Bedrock AgentCore Browser Tool (see [README.md587-593](https://github.com/aws/nova-act/blob/84e8ef56/README.md#L587-L593))
-   Connecting to remote browser instances
-   Debugging headless sessions via remote debugging port

**Sources:** [src/nova\_act/impl/playwright.py](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/impl/playwright.py) [src/nova\_act/nova\_act.py128-130](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/nova_act.py#L128-L130) [src/nova\_act/impl/inputs.py](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/impl/inputs.py) [README.md567-585](https://github.com/aws/nova-act/blob/84e8ef56/README.md#L567-L585)

### 3\. Default Chrome Browser Mode (macOS Only)

**When used:** `use_default_chrome_browser=True` parameter passed to `NovaAct.__init__`

**Process:**

1.  Quit existing Chrome instances using system commands
2.  Launch Chrome binary at `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome` with remote debugging enabled
3.  Wait for debugger endpoint WebSocket URL to become available
4.  Connect via CDP using discovered WebSocket URL with `connect_over_cdp()`

**Use case:** Using system-installed Chrome with existing extensions and security features

**Requirements and Limitations:**

-   macOS only (validated at [src/nova\_act/impl/inputs.py](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/impl/inputs.py))
-   Same limitations as CDP connection mode (no video, no proxy, no profile\_directory)
-   Requires Chrome to be fully quit before launching
-   Must use `clone_user_data_dir=False` (validated at [src/nova\_act/impl/inputs.py](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/impl/inputs.py))
-   Must provide `user_data_dir` with files copied from system Chrome profile
-   See setup instructions at [README.md331-363](https://github.com/aws/nova-act/blob/84e8ef56/README.md#L331-L363)

**Sources:** [src/nova\_act/impl/playwright.py](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/impl/playwright.py) [src/nova\_act/nova\_act.py148](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/nova_act.py#L148-L148) [src/nova\_act/impl/inputs.py](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/impl/inputs.py) [README.md331-363](https://github.com/aws/nova-act/blob/84e8ef56/README.md#L331-L363)

---

## Page Access from NovaAct Client

The `NovaAct` client provides convenient properties for accessing Playwright pages:

### Page Access API Call Chain

access

access

call

calls get\_page(-1)

validates & delegates

validates & delegates

delegates

returns

indexes

accesses

User Code

NovaAct.page property  
nova\_act.py:465-474

NovaAct.pages property  
nova\_act.py:495-513

NovaAct.get\_page(index)  
nova\_act.py:476-493

BrowserActuatorBase.get\_page()

PlaywrightPageManagerBase.pages

PlaywrightInstanceManager  
.get\_page(index)

PlaywrightInstanceManager  
.context.pages

playwright.sync\_api  
.BrowserContext.pages

**Sources:** [src/nova\_act/nova\_act.py465-513](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/nova_act.py#L465-L513) [src/nova\_act/tools/browser/interface/playwright\_pages.py](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/tools/browser/interface/playwright_pages.py)

### Usage Examples

**Get the current page:**

```
from nova_act import NovaAct

n = NovaAct(starting_page="https://example.com")
n.start()

# Access the current page (equivalent to get_page(-1))
page = n.page  # Returns playwright.sync_api.Page
```

**Get all pages:**

```
# List all open pages in the browser context
all_pages = n.pages  # Returns list[playwright.sync_api.Page]
```

**Get a specific page by index:**

```
# Get the first page (0-indexed)
first_page = n.get_page(0)

# Get the last/active page
active_page = n.get_page(-1)  # Same as n.page
```

**Type sensitive information directly:**

```
# For passwords, use Playwright Page API directly (never in prompts)
# This prevents sensitive data from being sent to the model
n.act("click on the password field")
n.page.keyboard.type("my-secret-password")  # Uses Playwright, not sent to model
n.act("click sign in")
```

See detailed password handling example at [README.md366-380](https://github.com/aws/nova-act/blob/84e8ef56/README.md#L366-L380)

**Sources:** [src/nova\_act/nova\_act.py465-493](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/nova_act.py#L465-L493) [README.md366-380](https://github.com/aws/nova-act/blob/84e8ef56/README.md#L366-L380) [README.md662-671](https://github.com/aws/nova-act/blob/84e8ef56/README.md#L662-L671)

### Type Checking and Error Handling

The page access methods include validation to ensure the actuator supports Playwright page access:

```
# From NovaAct.get_page() at line 486-490
if not isinstance(self._actuator, PlaywrightPageManagerBase):
    raise ValidationFailed(
        "Did you implement a non-playwright actuator? If so, you must get your own page object directly.\n"
        "If you are using playwright, ensure you are implementing PlaywrightPageManagerBase to get page access"
    )
```

This validation ensures that:

1.  Custom actuators implementing only `BrowserActuatorBase` fail with a clear error message
2.  Users are guided to implement `PlaywrightPageManagerBase` for Playwright support
3.  The error occurs at page access time, not at initialization

The same validation is applied in:

-   `NovaAct.get_page()` at [src/nova\_act/nova\_act.py486-490](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/nova_act.py#L486-L490)
-   `NovaAct.pages` property at [src/nova\_act/nova\_act.py506-510](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/nova_act.py#L506-L510)

**Sources:** [src/nova\_act/nova\_act.py486-490](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/nova_act.py#L486-L490) [src/nova\_act/nova\_act.py506-510](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/nova_act.py#L506-L510)

---

## Browser State Tracking

The `PlaywrightInstanceManager` uses the `started` property to track browser state by checking if the browser context exists:

```
@property
def started(self) -> bool:
    """Check if the client is started."""
    return self._context is not None
```

This property is propagated through the actuator to the `NovaAct` client:

```
# From NovaAct at line 461-463
@property
def started(self) -> bool:
    return self._actuator.started and self._session_id is not None
```

Operations that require a started browser check this property and raise `ClientNotStarted` if `False`:

Method

Check Location

Error Raised

`NovaAct.act()`

[src/nova\_act/nova\_act.py712-713](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/nova_act.py#L712-L713)

`ClientNotStarted`

`NovaAct.get_page()`

[src/nova\_act/nova\_act.py483-484](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/nova_act.py#L483-L484)

`ClientNotStarted`

`NovaAct.pages`

[src/nova\_act/nova\_act.py503-504](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/nova_act.py#L503-L504)

`ClientNotStarted`

`NovaAct.go_to_url()`

[src/nova\_act/nova\_act.py520-521](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/nova_act.py#L520-L521)

`ClientNotStarted`

`NovaAct.dispatcher`

[src/nova\_act/nova\_act.py528-529](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/nova_act.py#L528-L529)

`ClientNotStarted`

`NovaAct.get_session_id()`

[src/nova\_act/nova\_act.py541-542](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/nova_act.py#L541-L542)

`ClientNotStarted`

**Sources:** [src/nova\_act/impl/playwright.py](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/impl/playwright.py) [src/nova\_act/nova\_act.py461-463](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/nova_act.py#L461-L463) [src/nova\_act/nova\_act.py483-484](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/nova_act.py#L483-L484) [src/nova\_act/nova\_act.py503-504](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/nova_act.py#L503-L504) [src/nova\_act/nova\_act.py520-521](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/nova_act.py#L520-L521) [src/nova\_act/nova\_act.py528-529](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/nova_act.py#L528-L529) [src/nova\_act/nova\_act.py541-542](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/nova_act.py#L541-L542) [src/nova\_act/nova\_act.py712-713](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/nova_act.py#L712-L713)

---

## Configuration Integration

Browser configuration is encapsulated in the `PlaywrightInstanceOptions` dataclass at [src/nova\_act/tools/browser/default/playwright\_instance\_options.py](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/tools/browser/default/playwright_instance_options.py) which is passed to `DefaultNovaLocalBrowserActuator` during initialization. This options object consolidates all browser settings:

Option Category

Parameters

**Display**

`screen_width`, `screen_height`, `headless`

**Browser Identity**

`chrome_channel`, `user_agent`

**Session State**

`user_data_dir`, `profile_directory`

**CDP Connection**

`cdp_endpoint_url`, `cdp_headers`, `cdp_use_existing_page`

**Recording**

`record_video` (requires `logs_directory`)

**Network**

`proxy`, `ignore_https_errors`

**Navigation**

`starting_page`, `go_to_url_timeout`

**System Integration**

`use_default_chrome_browser`, `user_browser_args`

The options object is created in `NovaAct.__init__` at [src/nova\_act/nova\_act.py320-339](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/nova_act.py#L320-L339) and passed to the actuator constructor at [src/nova\_act/nova\_act.py359-361](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/nova_act.py#L359-L361)

**Environment Variable Overrides:**

-   `NOVA_ACT_CHROME_CHANNEL` - Override Chrome channel [src/nova\_act/nova\_act.py245](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/nova_act.py#L245-L245)
-   `NOVA_ACT_HEADLESS` - Enable headless mode [src/nova\_act/nova\_act.py246](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/nova_act.py#L246-L246)
-   `NOVA_ACT_BROWSER_ARGS` - Additional browser launch arguments [src/nova\_act/nova\_act.py315](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/nova_act.py#L315-L315)

For detailed information on these configuration options, see [Browser Configuration](/aws/nova-act/3.3-browser-configuration).

**Sources:** [src/nova\_act/tools/browser/default/playwright\_instance\_options.py](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/tools/browser/default/playwright_instance_options.py) [src/nova\_act/nova\_act.py245-246](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/nova_act.py#L245-L246) [src/nova\_act/nova\_act.py315](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/nova_act.py#L315-L315) [src/nova\_act/nova\_act.py320-339](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/nova_act.py#L320-L339) [src/nova\_act/nova\_act.py359-361](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/nova_act.py#L359-L361)

---

## Error Handling

Browser automation operations can fail in several ways:

Error Type

When Raised

Recovery

`StartFailed`

Browser fails to launch or connect

Check browser installation, CDP endpoint, or system resources

`StopFailed`

Browser fails to shut down cleanly

May require manual process termination

`ClientNotStarted`

Operations attempted before `start()` called

Call `start()` before using browser

`InvalidPlaywrightState`

Browser context in unexpected state

Restart the client

`PageNotFoundError`

Requested page index not found

Check available pages with `NovaAct.pages`

`ValidationFailed`

Invalid configuration (e.g., video recording with CDP)

Adjust configuration parameters

**Sources:** [src/nova\_act/impl/playwright.py27-33](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/impl/playwright.py#L27-L33) [src/nova\_act/nova\_act.py481](https://github.com/aws/nova-act/blob/84e8ef56/src/nova_act/nova_act.py#L481-L481)
