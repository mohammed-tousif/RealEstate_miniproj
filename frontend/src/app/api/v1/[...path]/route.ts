import { forward } from "@/lib/proxy";

export const dynamic = "force-dynamic";

type Ctx = { params: { path: string[] } };
const handle = (req: Request, { params }: Ctx) => forward(req, `/api/v1/${params.path.map(encodeURIComponent).join("/")}`);

export { handle as GET, handle as POST, handle as PUT, handle as PATCH, handle as DELETE };
