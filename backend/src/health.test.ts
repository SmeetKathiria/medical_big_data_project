import { describe, expect, it } from "vitest";
import { healthPayload } from "./routes/health.js";

describe("health", () => {
  it("serves the health payload", async () => {
    expect(healthPayload).toMatchObject({ ok: true, service: "medintel-api" });
  });
});
