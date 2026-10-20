import { afterEach, describe, expect, it } from "vitest";
import { backendOrigin, forward } from "./proxy";

afterEach(() => {
  delete process.env.API_PROXY_URL;
  delete process.env.API_HOST;
});

describe("backendOrigin", () => {
  it("prefers an explicit URL and trims the slash", () => {
    process.env.API_PROXY_URL = "http://127.0.0.1:8000/";
    process.env.API_HOST = "ignored.onrender.com";
    expect(backendOrigin()).toBe("http://127.0.0.1:8000");
  });
  it("builds an https origin from a Render hostname", () => {
    process.env.API_HOST = "propwise-api.onrender.com";
    expect(backendOrigin()).toBe("https://propwise-api.onrender.com");
  });
  it("is null when nothing is configured", async () => {
    expect(backendOrigin()).toBeNull();
    const res = await forward(new Request("http://x/api/v1/health"), "/api/v1/health");
    expect(res.status).toBe(503);
    expect((await res.json()).error.code).toBe("proxy_not_configured");
  });
});
