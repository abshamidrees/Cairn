import { NextResponse, type NextRequest } from "next/server";

const SUBDOMAIN_ROOT: Record<string, string> = {
  explorer: "/explorer",
  docs: "/docs",
};

// Empty until a domain is pointed at the deployment, which leaves every surface
// on one origin as a path. Mirrors useSubdomains() in lib/host.ts.
const ROOT_DOMAIN = process.env["NEXT_PUBLIC_ROOT_DOMAIN"] ?? "";

export function middleware(req: NextRequest) {
  if (!ROOT_DOMAIN) return NextResponse.next();
  const host = req.headers.get("host")?.split(":")[0] ?? "";
  const sub = host.endsWith(ROOT_DOMAIN) ? host.split(".")[0] : null;
  const root = sub ? SUBDOMAIN_ROOT[sub] : undefined;
  if (!root) return NextResponse.next();

  // explorer.usefirsthand.xyz/0xabc  ->  /explorer/0xabc
  const url = req.nextUrl.clone();
  if (!url.pathname.startsWith(root)) url.pathname = root + url.pathname;
  return NextResponse.rewrite(url);
}

export const config = { matcher: ["/((?!_next|api|.*\..*).*)"] };
