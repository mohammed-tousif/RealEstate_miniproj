import { forward } from "@/lib/proxy";

export const dynamic = "force-dynamic";

export function GET(req: Request, { params }: { params: { path: string[] } }) {
  return forward(req, `/media/${params.path.map(encodeURIComponent).join("/")}`);
}
