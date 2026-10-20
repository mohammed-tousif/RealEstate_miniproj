// Same-origin proxy used in production (Render): the browser calls /api/v1/* and /media/* on the
// frontend, and this server forwards them to the FastAPI service. No CORS setup or build-time API URL
// is needed. Locally the browser talks to NEXT_PUBLIC_API_BASE_URL (default http://localhost:8000) instead.

const FORWARD_REQUEST = ["authorization", "content-type", "accept"];
const FORWARD_RESPONSE = ["content-type", "cache-control", "retry-after", "last-modified", "etag"];

export function backendOrigin(): string | null {
  const explicit = process.env.API_PROXY_URL?.trim();
  if (explicit) return explicit.replace(/\/$/, "");
  const host = process.env.API_HOST?.trim();
  return host ? `https://${host.replace(/^https?:\/\//, "").replace(/\/$/, "")}` : null;
}

export async function forward(req: Request, path: string): Promise<Response> {
  const origin = backendOrigin();
  if (!origin) {
    return Response.json(
      { error: { code: "proxy_not_configured", message: "API_PROXY_URL or API_HOST is not set on the frontend service", details: [] } },
      { status: 503 },
    );
  }
  const url = new URL(req.url);
  const headers = new Headers();
  for (const h of FORWARD_REQUEST) {
    const v = req.headers.get(h);
    if (v) headers.set(h, v);
  }
  const fwd = req.headers.get("x-forwarded-for");
  if (fwd) headers.set("x-forwarded-for", fwd);
  const hasBody = !["GET", "HEAD"].includes(req.method);
  let res: Response;
  try {
    res = await fetch(`${origin}${path}${url.search}`, {
      method: req.method,
      headers,
      body: hasBody ? await req.arrayBuffer() : undefined,
      cache: "no-store",
      redirect: "manual",
    });
  } catch {
    return Response.json(
      { error: { code: "backend_unreachable", message: "The PropWise API is not reachable (it may be starting up; try again in a minute)", details: [] } },
      { status: 502 },
    );
  }
  const out = new Headers();
  for (const h of FORWARD_RESPONSE) {
    const v = res.headers.get(h);
    if (v) out.set(h, v);
  }
  return new Response(res.status === 204 ? null : res.body, { status: res.status, headers: out });
}
