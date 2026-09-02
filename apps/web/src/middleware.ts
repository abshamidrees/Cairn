import { NextResponse, type NextRequest } from "next/server";

const SUBDOMAIN_ROOT: Record<string, string> = {
  explorer: "/explorer",
  docs: "/docs",
};

export function middleware(req: NextRequest) {
  const host = req.headers.get("host")?.split(":")[0] ?? "";
  const sub = host.endsWith("usecairn.xyz") ? host.split(".")[0] : null;
  const root = sub ? SUBDOMAIN_ROOT[sub] : undefined;
  if (!root) return NextResponse.next();

  // explorer.usecairn.xyz/0xabc  ->  /explorer/0xabc
  const url = req.nextUrl.clone();
  if (!url.pathname.startsWith(root)) url.pathname = root + url.pathname;
  return NextResponse.rewrite(url);
}

export const config = { matcher: ["/((?!_next|api|.*\..*).*)"] };
