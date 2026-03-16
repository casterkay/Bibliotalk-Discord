import type { FastifyRequest } from "fastify";

export class AppserviceAuthError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "AppserviceAuthError";
  }
}

function getBearerToken(authorization: string | undefined): string | null {
  if (!authorization) return null;
  const [scheme, token] = authorization.split(" ", 2);
  if (!scheme || !token) return null;
  if (scheme.toLowerCase() !== "bearer") return null;
  return token.trim() || null;
}

export function requireHsToken(request: FastifyRequest): void {
  const expected = process.env.MATRIX_HS_TOKEN ?? "";
  if (!expected) {
    throw new AppserviceAuthError("MATRIX_HS_TOKEN is not configured");
  }

  const queryAny = request.query as Record<string, unknown>;
  const queryToken = typeof queryAny.access_token === "string" ? queryAny.access_token : null;
  const headerToken = getBearerToken(request.headers.authorization);
  const provided = queryToken ?? headerToken ?? "";

  if (!provided || provided !== expected) {
    throw new AppserviceAuthError("Unauthorized");
  }
}
