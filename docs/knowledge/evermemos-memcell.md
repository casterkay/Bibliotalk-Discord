# MemCell and Boundary Detection

This page explains what a `MemCell` is, how boundary detection works to decide when to create one, and the role of `smart_mask_flag`. It focuses on the data model and the detection algorithm itself.

---

## What Is a MemCell?

A **MemCell** (Memory Cell) is the fundamental unit of raw data in EverMemOS. It represents a bounded segment of a conversation—a coherent slice of raw messages that the system has decided constitutes a complete, extractable unit.

The `MemCell` dataclass is defined in [src/api\_specs/memory\_types.py63-137](https://github.com/EverMind-AI/EverMemOS/blob/19b3c7ba/src/api_specs/memory_types.py#L63-L137)

### MemCell Fields

Field

Type

Description

`user_id_list`

`List[str]`

All user IDs associated with this cell

`original_data`

`List[Dict[str, Any]]`

Normalized message dicts extracted from `RawData`

`timestamp`

`datetime`

Timestamp of the last message in the segment

`event_id`

`Optional[str]`

Assigned by MongoDB on persistence; `None` before save

`group_id`

`Optional[str]`

The conversation group this cell belongs to

`group_name`

`Optional[str]`

Display name for the group

`participants`

`Optional[List[str]]`

Deduplicated speaker IDs from all messages

`type`

`Optional[RawDataType]`

Currently always `RawDataType.CONVERSATION`

`summary`

`Optional[str]`

Short summary; empty for force-split cells, filled by LLM boundary detection

`episode`

`Optional[str]`

Filled later by `EpisodeMemoryExtractor`

`subject`

`Optional[str]`

Filled later by `EpisodeMemoryExtractor`

`foresights`

`Optional[List[Foresight]]`

Filled later by `ForesightExtractor`

`event_log`

`Optional[Any]`

Filled later by `EventLogExtractor`

`extend`

`Optional[Dict[str, Any]]`

Arbitrary extension data

> **Important:** A freshly created `MemCell` contains only raw message data and basic metadata. Fields like `episode`, `subject`, `foresights`, and `event_log` are populated in subsequent extraction stages, not during boundary detection.

Sources: [src/api\_specs/memory\_types.py62-137](https://github.com/EverMind-AI/EverMemOS/blob/19b3c7ba/src/api_specs/memory_types.py#L62-L137)

---

## MemCell in the Pipeline

**MemCell lifecycle diagram**

No (should\_wait=True)

Yes (should\_wait=False)

Raw Messages
(RawData list)

ConvMemCellExtractor
.extract\_memcell()

Boundary
Detected?

Accumulate more messages

MemCell created
(raw data only)

EpisodeMemoryExtractor
→ fills episode, subject

ForesightExtractor
→ fills foresights

EventLogExtractor
→ fills event\_log

\_save\_memcell\_to\_database
(event\_id assigned by MongoDB)

Downstream Memories
(EpisodeMemory, Foresight, EventLog)

Sources: [src/memory\_layer/memcell\_extractor/conv\_memcell\_extractor.py361-541](https://github.com/EverMind-AI/EverMemOS/blob/19b3c7ba/src/memory_layer/memcell_extractor/conv_memcell_extractor.py#L361-L541) [src/memory\_layer/memory\_manager.py75-135](https://github.com/EverMind-AI/EverMemOS/blob/19b3c7ba/src/memory_layer/memory_manager.py#L75-L135) [src/biz\_layer/mem\_memorize.py459-586](https://github.com/EverMind-AI/EverMemOS/blob/19b3c7ba/src/biz_layer/mem_memorize.py#L459-L586)

---

## Boundary Detection

Boundary detection is implemented in `ConvMemCellExtractor` ([src/memory\_layer/memcell\_extractor/conv\_memcell\_extractor.py55-583](https://github.com/EverMind-AI/EverMemOS/blob/19b3c7ba/src/memory_layer/memcell_extractor/conv_memcell_extractor.py#L55-L583)). It decides whether the accumulated conversation history has reached a natural end point that warrants creating a MemCell.

There are two distinct mechanisms: **hard limits** (rule-based) and **LLM-based detection**.

### 1\. Hard Limits (Force Split)

Before calling the LLM, the extractor checks whether raw size thresholds have been exceeded:

Limit

Default Value

Constant

Token limit

8 192 tokens

`DEFAULT_HARD_TOKEN_LIMIT`

Message limit

50 messages

`DEFAULT_HARD_MESSAGE_LIMIT`

Token counting uses tiktoken with the `o200k_base` encoding, applied via `TokenizerFactory`. Each message is counted as `"speaker: content"` to match what is sent to the LLM.

**Force-split logic** ([src/memory\_layer/memcell\_extractor/conv\_memcell\_extractor.py414-470](https://github.com/EverMind-AI/EverMemOS/blob/19b3c7ba/src/memory_layer/memcell_extractor/conv_memcell_extractor.py#L414-L470)):

```
if (total_tokens >= hard_token_limit OR total_messages >= hard_message_limit)
   AND len(history_message_dict_list) >= 2:
    → Force split: create MemCell from history messages
    → New message starts the next accumulation window
    → trigger_type = 'token_limit' or 'message_limit'
```

If the limit is exceeded but there is only one history message (e.g., a single very long message), the force split is skipped and the LLM detection path runs instead.

### 2\. LLM-Based Boundary Detection

When no hard limit is triggered, `_detect_boundary()` is called ([src/memory\_layer/memcell\_extractor/conv\_memcell\_extractor.py279-359](https://github.com/EverMind-AI/EverMemOS/blob/19b3c7ba/src/memory_layer/memcell_extractor/conv_memcell_extractor.py#L279-L359)).

It constructs a prompt from `CONV_BOUNDARY_DETECTION_PROMPT` ([src/memory\_layer/prompts/en/conv\_prompts.py2-66](https://github.com/EverMind-AI/EverMemOS/blob/19b3c7ba/src/memory_layer/prompts/en/conv_prompts.py#L2-L66)) with three inputs:

-   `conversation_history` — formatted text of previous messages
-   `new_messages` — the newly arrived messages
-   `time_gap_info` — human-readable time gap between last history message and first new message

The LLM returns a JSON object, which is parsed into a `BoundaryDetectionResult`:

```
@dataclassclass BoundaryDetectionResult:    should_end: bool    should_wait: bool    reasoning: str    confidence: float    topic_summary: Optional[str]
```

The LLM is called up to 5 times on JSON parse failure. On total failure, `should_end=False` and `should_wait=True` is returned as a safe default.

**Boundary detection decision logic**

Yes, history >= 2 msgs

No

True

False

True

False

extract\_memcell(request)

\_data\_process() each message
(filter unsupported types)

Count tokens
\_count\_tokens()

Force split
threshold exceeded?

Create MemCell
from history\_message\_dict\_list
summary=empty
trigger='token\_limit' or 'message\_limit'

smart\_mask\_flag?

\_detect\_boundary(
  history\[:-1\],
  new\_messages
)

\_detect\_boundary(
  history,
  new\_messages
)

LLMProvider.generate(prompt)
parse JSON → BoundaryDetectionResult

should\_end?

Create MemCell
from history\_message\_dict\_list
summary=topic\_summary
trigger='llm'

Return (None, StatusResult(should\_wait=True))

Return (MemCell, StatusResult(should\_wait=False))

Sources: [src/memory\_layer/memcell\_extractor/conv\_memcell\_extractor.py279-541](https://github.com/EverMind-AI/EverMemOS/blob/19b3c7ba/src/memory_layer/memcell_extractor/conv_memcell_extractor.py#L279-L541) [src/memory\_layer/prompts/en/conv\_prompts.py2-66](https://github.com/EverMind-AI/EverMemOS/blob/19b3c7ba/src/memory_layer/prompts/en/conv_prompts.py#L2-L66)

---

## The `smart_mask_flag`

`smart_mask_flag` controls which portion of the conversation history is shown to the LLM during boundary detection.

Condition

`smart_mask_flag`

History passed to LLM

`len(history_raw_data_list) <= 5`

`False`

Full history

`len(history_raw_data_list) > 5`

`True`

History excluding the last message (`history[:-1]`)

**Purpose:** When history is long, the most recent history message is the one that was just previously processed. By masking it out, the LLM is asked to evaluate the new messages against the context _before_ that last message, reducing recency bias and producing more stable boundary decisions.

The flag is set in two places:

-   `MemoryManager.extract_memcell()` in [src/memory\_layer/memory\_manager.py107-108](https://github.com/EverMind-AI/EverMemOS/blob/19b3c7ba/src/memory_layer/memory_manager.py#L107-L108):

    ```
    smart_mask_flag = len(history_raw_data_list) > 5
    ```

-   `memcell_extraction_from_conversation()` in the evaluation adapter [evaluation/src/adapters/evermemos/stage1\_memcells\_extraction.py264-276](https://github.com/EverMind-AI/EverMemOS/blob/19b3c7ba/evaluation/src/adapters/evermemos/stage1_memcells_extraction.py#L264-L276):

    ```
    if smart_mask and len(history_raw_data_list) > 5:    smart_mask_flag = Trueelse:    smart_mask_flag = False
    ```


Sources: [src/memory\_layer/memory\_manager.py107-118](https://github.com/EverMind-AI/EverMemOS/blob/19b3c7ba/src/memory_layer/memory_manager.py#L107-L118) [src/memory\_layer/memcell\_extractor/conv\_memcell\_extractor.py481-490](https://github.com/EverMind-AI/EverMemOS/blob/19b3c7ba/src/memory_layer/memcell_extractor/conv_memcell_extractor.py#L481-L490) [evaluation/src/adapters/evermemos/stage1\_memcells\_extraction.py264-276](https://github.com/EverMind-AI/EverMemOS/blob/19b3c7ba/evaluation/src/adapters/evermemos/stage1_memcells_extraction.py#L264-L276)

---

## Message Type Filtering

Before boundary detection runs, `_data_process()` normalizes and filters each `RawData` item. Messages with unsupported `msgType` values are dropped entirely (the extractor returns `None`, which is excluded from both history and new message lists).

`msgType`

Behavior

`1` (TEXT)

Kept as-is

`2` (PICTURE)

Content replaced with `"[Image]"`

`3` (VIDEO)

Content replaced with `"[Video]"`

`4` (AUDIO)

Content replaced with `"[Audio]"`

`5` (FILE)

Content replaced with `"[File]"`

`6` (FILES)

Content replaced with `"[File]"`

Any other

Skipped (filtered out)

If the last message in `new_raw_data_list` is an unsupported type (returns `None`), the extractor immediately returns `(None, StatusResult(should_wait=True))` without any further processing.

Sources: [src/memory\_layer/memcell\_extractor/conv\_memcell\_extractor.py543-583](https://github.com/EverMind-AI/EverMemOS/blob/19b3c7ba/src/memory_layer/memcell_extractor/conv_memcell_extractor.py#L543-L583)

---

## `StatusResult` and Accumulation Logic

`StatusResult` is the signal returned alongside a `MemCell` (or `None`). It controls what the caller does next.

```
@dataclassclass StatusResult:    should_wait: bool
```

`should_wait`

`MemCell` returned

Meaning

`True`

`None`

No boundary reached; caller should accumulate the new message into history and wait for the next one

`False`

`MemCell` instance

Boundary reached; caller should process the MemCell and reset the history window

After a force-split MemCell is created, the new message is **not** included in the created MemCell. It becomes the start of the next accumulation window. After an LLM-detected boundary, the new messages that triggered the detection also start the next window (they are not part of the completed MemCell).

Sources: [src/memory\_layer/memcell\_extractor/conv\_memcell\_extractor.py361-541](https://github.com/EverMind-AI/EverMemOS/blob/19b3c7ba/src/memory_layer/memcell_extractor/conv_memcell_extractor.py#L361-L541) [evaluation/src/adapters/evermemos/stage1\_memcells\_extraction.py256-303](https://github.com/EverMind-AI/EverMemOS/blob/19b3c7ba/evaluation/src/adapters/evermemos/stage1_memcells_extraction.py#L256-L303)

---

## Key Classes and Their Relationships

**MemCell extraction class map**

"accepts"

"produces internally"

"creates"

"creates"

"instantiates"

"returns"

ConvMemCellExtractor

+DEFAULT\_HARD\_TOKEN\_LIMIT: int

+DEFAULT\_HARD\_MESSAGE\_LIMIT: int

+hard\_token\_limit: int

+hard\_message\_limit: int

+llm\_provider: LLMProvider

+extract\_memcell(request) : tuple

+\_detect\_boundary(history, new\_messages) : BoundaryDetectionResult

+\_count\_tokens(messages) : int

+\_data\_process(raw\_data) : dict

+\_extract\_participant\_ids(data) : list

ConversationMemCellExtractRequest

+history\_raw\_data\_list: list

+new\_raw\_data\_list: list

+user\_id\_list: list

+group\_id: str

+smart\_mask\_flag: bool

BoundaryDetectionResult

+should\_end: bool

+should\_wait: bool

+reasoning: str

+confidence: float

+topic\_summary: str

StatusResult

+should\_wait: bool

MemCell

+user\_id\_list: list

+original\_data: list

+timestamp: datetime

+event\_id: str

+group\_id: str

+participants: list

+type: RawDataType

+summary: str

+episode: str

+foresights: list

+event\_log: object

MemoryManager\_memory\_layer

+extract\_memcell(history, new, type) : tuple

+extract\_memory(memcell, memory\_type) : object

Sources: [src/memory\_layer/memcell\_extractor/conv\_memcell\_extractor.py39-583](https://github.com/EverMind-AI/EverMemOS/blob/19b3c7ba/src/memory_layer/memcell_extractor/conv_memcell_extractor.py#L39-L583) [src/api\_specs/memory\_types.py62-137](https://github.com/EverMind-AI/EverMemOS/blob/19b3c7ba/src/api_specs/memory_types.py#L62-L137) [src/memory\_layer/memory\_manager.py49-135](https://github.com/EverMind-AI/EverMemOS/blob/19b3c7ba/src/memory_layer/memory_manager.py#L49-L135)
