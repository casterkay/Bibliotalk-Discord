/// <reference path="../pb_data/types.d.ts" />

// PocketBase migration format is intentionally verbose; include stable IDs for determinism.
migrate((db) => {
  const dao = new Dao(db);

  const now = "2026-03-03 00:00:00.000Z";

  const agents = new Collection({
    id: "btagents0000001",
    created: now,
    updated: now,
    name: "agents",
    type: "base",
    system: false,
    schema: [
      { system: false, id: "btagnuuid000001", name: "uuid", type: "text", required: true, presentable: false, unique: true, options: { min: null, max: null, pattern: "" } },
      { system: false, id: "btagnkind000001", name: "kind", type: "text", required: true, presentable: false, unique: false, options: { min: null, max: null, pattern: "" } },
      { system: false, id: "btagnname000001", name: "display_name", type: "text", required: true, presentable: false, unique: false, options: { min: null, max: null, pattern: "" } },
      { system: false, id: "btagnmxid00001", name: "matrix_user_id", type: "text", required: true, presentable: false, unique: true, options: { min: null, max: null, pattern: "" } },
      { system: false, id: "btagnprmp00001", name: "persona_prompt", type: "text", required: true, presentable: false, unique: false, options: { min: null, max: null, pattern: "" } },
      { system: false, id: "btagnllm000001", name: "llm_model", type: "text", required: true, presentable: false, unique: false, options: { min: null, max: null, pattern: "" } },
      { system: false, id: "btagnact000001", name: "is_active", type: "bool", required: false, presentable: false, unique: false, options: {} }
    ],
    indexes: [
      "CREATE UNIQUE INDEX IF NOT EXISTS idx_agents_uuid ON agents (uuid)",
      "CREATE UNIQUE INDEX IF NOT EXISTS idx_agents_matrix_user_id ON agents (matrix_user_id)"
    ],
    listRule: null,
    viewRule: null,
    createRule: null,
    updateRule: null,
    deleteRule: null,
    options: {}
  });
  dao.saveCollection(agents);

  const agentEmos = new Collection({
    id: "btemosconf00001",
    created: now,
    updated: now,
    name: "agent_emos_config",
    type: "base",
    system: false,
    schema: [
      { system: false, id: "btemosagid00001", name: "agent_uuid", type: "text", required: true, presentable: false, unique: true, options: { min: null, max: null, pattern: "" } },
      { system: false, id: "btemosbase00001", name: "emos_base_url", type: "text", required: true, presentable: false, unique: false, options: { min: null, max: null, pattern: "" } },
      { system: false, id: "btemoskey000001", name: "emos_api_key", type: "text", required: false, presentable: false, unique: false, options: { min: null, max: null, pattern: "" } },
      { system: false, id: "btemoskeye0001", name: "emos_api_key_encrypted", type: "text", required: false, presentable: false, unique: false, options: { min: null, max: null, pattern: "" } },
      { system: false, id: "btemostnt000001", name: "tenant_prefix", type: "text", required: true, presentable: false, unique: true, options: { min: null, max: null, pattern: "" } }
    ],
    indexes: [
      "CREATE UNIQUE INDEX IF NOT EXISTS idx_agent_emos_agent_uuid ON agent_emos_config (agent_uuid)",
      "CREATE UNIQUE INDEX IF NOT EXISTS idx_agent_emos_tenant_prefix ON agent_emos_config (tenant_prefix)"
    ],
    listRule: null,
    viewRule: null,
    createRule: null,
    updateRule: null,
    deleteRule: null,
    options: {}
  });
  dao.saveCollection(agentEmos);

  const profileRooms = new Collection({
    id: "btprofilerm0001",
    created: now,
    updated: now,
    name: "profile_rooms",
    type: "base",
    system: false,
    schema: [
      { system: false, id: "btproagid000001", name: "agent_uuid", type: "text", required: true, presentable: false, unique: true, options: { min: null, max: null, pattern: "" } },
      { system: false, id: "btprormid00001", name: "matrix_room_id", type: "text", required: true, presentable: false, unique: true, options: { min: null, max: null, pattern: "" } }
    ],
    indexes: [
      "CREATE UNIQUE INDEX IF NOT EXISTS idx_profile_rooms_agent_uuid ON profile_rooms (agent_uuid)",
      "CREATE UNIQUE INDEX IF NOT EXISTS idx_profile_rooms_matrix_room_id ON profile_rooms (matrix_room_id)"
    ],
    listRule: null,
    viewRule: null,
    createRule: null,
    updateRule: null,
    deleteRule: null,
    options: {}
  });
  dao.saveCollection(profileRooms);

  const sources = new Collection({
    id: "btsources0000001",
    created: now,
    updated: now,
    name: "sources",
    type: "base",
    system: false,
    schema: [
      { system: false, id: "btsrcuuid000001", name: "uuid", type: "text", required: true, presentable: false, unique: true, options: { min: null, max: null, pattern: "" } },
      { system: false, id: "btsrcagid000001", name: "agent_uuid", type: "text", required: true, presentable: false, unique: false, options: { min: null, max: null, pattern: "" } },
      { system: false, id: "btsrcplat000001", name: "platform", type: "text", required: true, presentable: false, unique: false, options: { min: null, max: null, pattern: "" } },
      { system: false, id: "btsrcext000001", name: "external_id", type: "text", required: true, presentable: false, unique: false, options: { min: null, max: null, pattern: "" } },
      { system: false, id: "btsrcurl000001", name: "external_url", type: "text", required: false, presentable: false, unique: false, options: { min: null, max: null, pattern: "" } },
      { system: false, id: "btsrcttl000001", name: "title", type: "text", required: true, presentable: false, unique: false, options: { min: null, max: null, pattern: "" } },
      { system: false, id: "btsrcaut000001", name: "author", type: "text", required: false, presentable: false, unique: false, options: { min: null, max: null, pattern: "" } },
      { system: false, id: "btsrcpub000001", name: "published_at", type: "text", required: false, presentable: false, unique: false, options: { min: null, max: null, pattern: "" } },
      { system: false, id: "btsrcraw000001", name: "raw_meta", type: "json", required: false, presentable: false, unique: false, options: { maxSize: 5000000 } },
      { system: false, id: "btsrcgid0000001", name: "emos_group_id", type: "text", required: true, presentable: false, unique: true, options: { min: null, max: null, pattern: "" } }
    ],
    indexes: [
      "CREATE UNIQUE INDEX IF NOT EXISTS idx_sources_uuid ON sources (uuid)",
      "CREATE UNIQUE INDEX IF NOT EXISTS idx_sources_emos_group_id ON sources (emos_group_id)"
    ],
    listRule: null,
    viewRule: null,
    createRule: null,
    updateRule: null,
    deleteRule: null,
    options: {}
  });
  dao.saveCollection(sources);

  const segments = new Collection({
    id: "btsegments000001",
    created: now,
    updated: now,
    name: "segments",
    type: "base",
    system: false,
    schema: [
      { system: false, id: "btseguuid000001", name: "uuid", type: "text", required: true, presentable: false, unique: true, options: { min: null, max: null, pattern: "" } },
      { system: false, id: "btsegagid000001", name: "agent_uuid", type: "text", required: true, presentable: false, unique: false, options: { min: null, max: null, pattern: "" } },
      { system: false, id: "btsegsid000001", name: "source_uuid", type: "text", required: true, presentable: false, unique: false, options: { min: null, max: null, pattern: "" } },
      { system: false, id: "btsegpla0000001", name: "platform", type: "text", required: true, presentable: false, unique: false, options: { min: null, max: null, pattern: "" } },
      { system: false, id: "btsegseq0000001", name: "seq", type: "number", required: true, presentable: false, unique: false, options: { min: 0, max: null, noDecimal: true } },
      { system: false, id: "btsegtxt0000001", name: "text", type: "text", required: true, presentable: false, unique: false, options: { min: null, max: null, pattern: "" } },
      { system: false, id: "btsegspr0000001", name: "speaker", type: "text", required: false, presentable: false, unique: false, options: { min: null, max: null, pattern: "" } },
      { system: false, id: "btsegstm0000001", name: "start_ms", type: "number", required: false, presentable: false, unique: false, options: { min: 0, max: null, noDecimal: true } },
      { system: false, id: "btsegetm0000001", name: "end_ms", type: "number", required: false, presentable: false, unique: false, options: { min: 0, max: null, noDecimal: true } },
      { system: false, id: "btsegsha0000001", name: "sha256", type: "text", required: true, presentable: false, unique: false, options: { min: null, max: null, pattern: "" } },
      { system: false, id: "btsegmid0000001", name: "emos_message_id", type: "text", required: true, presentable: false, unique: true, options: { min: null, max: null, pattern: "" } },
      { system: false, id: "btsegttl0000001", name: "source_title", type: "text", required: false, presentable: false, unique: false, options: { min: null, max: null, pattern: "" } },
      { system: false, id: "btsegurl0000001", name: "source_url", type: "text", required: false, presentable: false, unique: false, options: { min: null, max: null, pattern: "" } },
      { system: false, id: "btsegeid0000001", name: "matrix_event_id", type: "text", required: false, presentable: false, unique: false, options: { min: null, max: null, pattern: "" } }
    ],
    indexes: [
      "CREATE UNIQUE INDEX IF NOT EXISTS idx_segments_uuid ON segments (uuid)",
      "CREATE UNIQUE INDEX IF NOT EXISTS idx_segments_emos_message_id ON segments (emos_message_id)",
      "CREATE INDEX IF NOT EXISTS idx_segments_source_uuid_seq ON segments (source_uuid, seq)"
    ],
    listRule: null,
    viewRule: null,
    createRule: null,
    updateRule: null,
    deleteRule: null,
    options: {}
  });
  dao.saveCollection(segments);

  const chatHistory = new Collection({
    id: "btchathist00001",
    created: now,
    updated: now,
    name: "chat_history",
    type: "base",
    system: false,
    schema: [
      { system: false, id: "btchuuid0000001", name: "uuid", type: "text", required: true, presentable: false, unique: true, options: { min: null, max: null, pattern: "" } },
      { system: false, id: "btchrmid0000001", name: "matrix_room_id", type: "text", required: true, presentable: false, unique: false, options: { min: null, max: null, pattern: "" } },
      { system: false, id: "btchagid0000001", name: "sender_agent_uuid", type: "text", required: false, presentable: false, unique: false, options: { min: null, max: null, pattern: "" } },
      { system: false, id: "btchmxid0000001", name: "sender_matrix_user_id", type: "text", required: true, presentable: false, unique: false, options: { min: null, max: null, pattern: "" } },
      { system: false, id: "btchevid0000001", name: "matrix_event_id", type: "text", required: false, presentable: false, unique: false, options: { min: null, max: null, pattern: "" } },
      { system: false, id: "btchmod0000001", name: "modality", type: "text", required: true, presentable: false, unique: false, options: { min: null, max: null, pattern: "" } },
      { system: false, id: "btchcont0000001", name: "content", type: "text", required: true, presentable: false, unique: false, options: { min: null, max: null, pattern: "" } },
      { system: false, id: "btchcite0000001", name: "citations", type: "json", required: false, presentable: false, unique: false, options: { maxSize: 5000000 } }
    ],
    indexes: [
      "CREATE UNIQUE INDEX IF NOT EXISTS idx_chat_history_uuid ON chat_history (uuid)"
    ],
    listRule: null,
    viewRule: null,
    createRule: null,
    updateRule: null,
    deleteRule: null,
    options: {}
  });
  dao.saveCollection(chatHistory);
}, (db) => {
  const dao = new Dao(db);
  [
    "btchathist00001",
    "btsegments000001",
    "btsources0000001",
    "btprofilerm0001",
    "btemosconf00001",
    "btagents0000001"
  ].forEach((id) => {
    const c = dao.findCollectionByNameOrId(id);
    if (c) {
      dao.deleteCollection(c);
    }
  });
});
