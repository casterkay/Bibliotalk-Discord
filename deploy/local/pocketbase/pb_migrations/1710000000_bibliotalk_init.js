/// <reference path="../pb_data/types.d.ts" />

// PocketBase migration format is intentionally verbose; include stable IDs for determinism.
migrate((app) => {
  const now = "2026-03-03 00:00:00.000Z";

  const agents = new Collection({
    id: "btagents0000001",
    created: now,
    updated: now,
    name: "agents",
    type: "base",
    system: false,
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
  agents.fields.add(
    new TextField({ name: "uuid", required: true }),
    new TextField({ name: "kind", required: true }),
    new TextField({ name: "display_name", required: true }),
    new TextField({ name: "matrix_user_id", required: true }),
    new TextField({ name: "persona_prompt", required: true }),
    new TextField({ name: "llm_model", required: true }),
    new BoolField({ name: "is_active" })
  );
  app.save(agents);

  const agentEmos = new Collection({
    id: "btemosconf00001",
    created: now,
    updated: now,
    name: "agent_emos_config",
    type: "base",
    system: false,
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
  agentEmos.fields.add(
    new TextField({ name: "agent_uuid", required: true }),
    new TextField({ name: "emos_base_url", required: true }),
    new TextField({ name: "emos_api_key" }),
    new TextField({ name: "emos_api_key_encrypted" }),
    new TextField({ name: "tenant_prefix", required: true })
  );
  app.save(agentEmos);

  const profileRooms = new Collection({
    id: "btprofilerm0001",
    created: now,
    updated: now,
    name: "profile_rooms",
    type: "base",
    system: false,
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
  profileRooms.fields.add(
    new TextField({ name: "agent_uuid", required: true }),
    new TextField({ name: "matrix_room_id", required: true })
  );
  app.save(profileRooms);

  const sources = new Collection({
    id: "btsources0000001",
    created: now,
    updated: now,
    name: "sources",
    type: "base",
    system: false,
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
  sources.fields.add(
    new TextField({ name: "uuid", required: true }),
    new TextField({ name: "agent_uuid", required: true }),
    new TextField({ name: "platform", required: true }),
    new TextField({ name: "external_id", required: true }),
    new TextField({ name: "external_url" }),
    new TextField({ name: "title", required: true }),
    new TextField({ name: "author" }),
    new TextField({ name: "published_at" }),
    new JSONField({ name: "raw_meta", maxSize: 5000000 }),
    new TextField({ name: "emos_group_id", required: true })
  );
  app.save(sources);

  const segments = new Collection({
    id: "btsegments000001",
    created: now,
    updated: now,
    name: "segments",
    type: "base",
    system: false,
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
  segments.fields.add(
    new TextField({ name: "uuid", required: true }),
    new TextField({ name: "agent_uuid", required: true }),
    new TextField({ name: "source_uuid", required: true }),
    new TextField({ name: "platform", required: true }),
    new NumberField({ name: "seq", required: true, min: 0, noDecimal: true }),
    new TextField({ name: "text", required: true }),
    new TextField({ name: "speaker" }),
    new NumberField({ name: "start_ms", min: 0, noDecimal: true }),
    new NumberField({ name: "end_ms", min: 0, noDecimal: true }),
    new TextField({ name: "sha256", required: true }),
    new TextField({ name: "emos_message_id", required: true }),
    new TextField({ name: "source_title" }),
    new TextField({ name: "source_url" }),
    new TextField({ name: "matrix_event_id" })
  );
  app.save(segments);

  const chatHistory = new Collection({
    id: "btchathist00001",
    created: now,
    updated: now,
    name: "chat_history",
    type: "base",
    system: false,
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
  chatHistory.fields.add(
    new TextField({ name: "uuid", required: true }),
    new TextField({ name: "matrix_room_id", required: true }),
    new TextField({ name: "sender_agent_uuid" }),
    new TextField({ name: "sender_matrix_user_id", required: true }),
    new TextField({ name: "matrix_event_id" }),
    new TextField({ name: "modality", required: true }),
    new TextField({ name: "content", required: true }),
    new JSONField({ name: "citations", maxSize: 5000000 })
  );
  app.save(chatHistory);
}, (app) => {
  [
    "btchathist00001",
    "btsegments000001",
    "btsources0000001",
    "btprofilerm0001",
    "btemosconf00001",
    "btagents0000001"
  ].forEach((id) => {
    try {
      const c = app.findCollectionByNameOrId(id);
      if (c) {
        app.delete(c);
      }
    } catch (_) {}
  });
});
