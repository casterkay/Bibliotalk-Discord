import fastify, { type FastifyInstance } from "fastify";

import { createAppserviceRouter } from "./matrix/appservice.js";

function envInt(name: string, fallback: number): number {
  const raw = process.env[name];
  if (!raw) return fallback;
  const value = Number(raw);
  return Number.isFinite(value) ? value : fallback;
}

export function buildServer(): FastifyInstance {
  const app = fastify({ logger: true });

  app.get("/healthz", async () => ({ status: "ok" }));

  app.register(createAppserviceRouter());

  return app;
}

async function main(): Promise<void> {
  const port = envInt("MATRIX_SERVICE_PORT", envInt("PORT", 9009));
  const host = process.env.MATRIX_SERVICE_HOST ?? "0.0.0.0";

  const app = buildServer();
  await app.listen({ host, port });
}

if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch((err) => {
    // eslint-disable-next-line no-console
    console.error("matrix_service failed", err);
    process.exit(1);
  });
}
