import fastify from "fastify";
import { WebSocketServer } from "ws";

import { BridgeManager } from "./voip/bridge_manager.js";
import { parseEnsureRequest, parseStopRequest } from "./voip/http_models.js";

function env(name, fallback = "") {
  return process.env[name] ?? fallback;
}

export async function buildServer() {
  const app = fastify({ logger: true });
  const gatewayWss = new WebSocketServer({ noServer: true });

  const manager = new BridgeManager({
    homeserverUrl: env("MATRIX_HOMESERVER_URL", "http://localhost:8008"),
    matrixAsToken: env("MATRIX_AS_TOKEN", ""),
    agentsServiceUrl: env("AGENTS_SERVICE_URL", "http://localhost:8009"),
    fallbackLivekitServiceUrl: env("VOIP_LIVEKIT_SERVICE_URL", ""),
  });

  app.server.on("upgrade", (request, socket, head) => {
    let parsed;
    try {
      parsed = new URL(request.url || "", "http://localhost");
    } catch {
      socket.destroy();
      return;
    }
    if (parsed.pathname !== "/v1/discord/gateway/ws") {
      socket.destroy();
      return;
    }

    const bridgeId = String(parsed.searchParams.get("bridge_id") || "").trim();
    if (!bridgeId) {
      socket.write("HTTP/1.1 400 Bad Request\r\n\r\nMissing bridge_id");
      socket.destroy();
      return;
    }

    gatewayWss.handleUpgrade(request, socket, head, (ws) => {
      gatewayWss.emit("connection", ws, bridgeId);
    });
  });

  gatewayWss.on("connection", (socket, bridgeId) => {
    try {
      manager.attachDiscordGatewaySocket(String(bridgeId), socket);
    } catch (err) {
      app.log.warn(
        { err: String(err?.message || err), bridge_id: bridgeId },
        "discord gateway socket rejected",
      );
      socket.close(1008, "unknown bridge_id");
    }
  });

  app.get("/healthz", async () => ({ status: "ok" }));

  app.post("/v1/voip/ensure", async (req, reply) => {
    const body = parseEnsureRequest(req.body);
    const status = await manager.ensure(body);
    return reply.send({ ok: true, status });
  });

  app.post("/v1/voip/stop", async (req, reply) => {
    const body = parseStopRequest(req.body);
    const status = await manager.stop(body);
    return reply.send({ ok: true, status });
  });

  app.addHook("onClose", async () => {
    await manager.stop({ room_id: null, reason: "shutdown" });
    for (const client of gatewayWss.clients) {
      try {
        client.close(1001, "shutdown");
      } catch {
        // ignore
      }
    }
    await new Promise((resolve) => gatewayWss.close(resolve));
  });

  return app;
}
