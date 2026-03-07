Timestamp Correspondence

API responses return extracted memories that inherit their timestamp from the source MemCell memory_api.md:261-266 . Each memory type (episodic_memory, foresight, event_log) includes this timestamp field.
MemCell vs Message vs API Response

    Original messages have create_time when stored memory.py:291-383
    MemCell groups multiple messages after boundary detection and gets its own timestamp memory_types.py:72-77
    API response returns extracted memories (Episode/Foresight/EventLog) that inherit the MemCell's timestamp memory.py:574-580

MemCell Timestamp Calculation

The MemCell timestamp is calculated from the last message in the boundary-detected segment:

# From conv_memcell_extractor.py
ts_value = history_message_dict_list[-1].get("timestamp")
timestamp = dt_from_iso_format(ts_value)

conv_memcell_extractor.py:498-500

Summary

    API timestamp = MemCell timestamp (inherited by extracted memories)
    Response items = Extracted memories (Episode/Foresight/EventLog), not MemCells
    MemCell timestamp = Timestamp of the last message in the boundary-detected segment

This design ensures all memories derived from the same conversation segment share a consistent timestamp representing when that segment concluded.
