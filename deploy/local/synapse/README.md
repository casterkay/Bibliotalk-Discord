# Synapse (Local)

Synapse is run via `deploy/local/docker-compose.yml`, with its data/config persisted under:

- `deploy/local/synapse/data/` (gitignored)

## Appservice registration

1. Start Synapse once so `homeserver.yaml` is generated:

```bash
docker compose -f deploy/local/docker-compose.yml up -d synapse
```

2. Generate the Bibliotalk appservice registration YAML (writes into `deploy/local/synapse/data/appservices/` and updates repo-root `.env` tokens):

```bash
chmod +x deploy/local/bin/*.sh
deploy/local/bin/generate-appservice.sh
```

3. Enable the appservice in `homeserver.yaml` and restart Synapse:

```bash
(cd deploy/local && ./bin/enable-appservice.sh)
docker compose -f deploy/local/docker-compose.yml restart synapse
```

The registration template lives at `deploy/local/synapse/appservice/bibliotalk-appservice.example.yaml` for reference.

