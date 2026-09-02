/**
 * Every internal link is built from here rather than hardcoded, so a link to a
 * dossier lands on explorer.usecairn.xyz/0xabc and not on the path form. The
 * middleware rewrites subdomains onto path roots; this is the inverse, and the
 * two must agree.
 */

export type Surface = "landing" | "explorer" | "docs";

export const ROOT_DOMAIN = "usecairn.xyz";

const SUBDOMAIN: Record<Surface, string | null> = {
  landing: null,
  explorer: "explorer",
  docs: "docs",
};

/** The path root each subdomain is rewritten onto. Mirrors middleware.ts. */
const PATH_ROOT: Record<Surface, string> = {
  landing: "",
  explorer: "/explorer",
  docs: "/docs",
};

function devOrigin(): string {
  return process.env["NEXT_PUBLIC_SITE_ORIGIN"] ?? "http://localhost:3000";
}

function isProduction(): boolean {
  return process.env.NODE_ENV === "production";
}

/** Absolute origin for a surface. In development every surface is one origin. */
export function hostFor(surface: Surface): string {
  if (!isProduction()) return devOrigin();
  const sub = SUBDOMAIN[surface];
  return sub ? `https://${sub}.${ROOT_DOMAIN}` : `https://${ROOT_DOMAIN}`;
}

/**
 * A full URL for a surface. In development the path root is kept so the same
 * route resolves without subdomains; in production the subdomain carries it.
 */
export function urlFor(surface: Surface, path = ""): string {
  const suffix = path && !path.startsWith("/") ? `/${path}` : path;
  if (!isProduction()) return `${devOrigin()}${PATH_ROOT[surface]}${suffix}`;
  return `${hostFor(surface)}${suffix}`;
}

/**
 * The canonical form is always the subdomain, never the path form, or
 * usecairn.xyz/docs and docs.usecairn.xyz both index as duplicates.
 */
export function canonicalFor(surface: Surface, path = ""): string {
  const suffix = path && !path.startsWith("/") ? `/${path}` : path;
  const sub = SUBDOMAIN[surface];
  return sub ? `https://${sub}.${ROOT_DOMAIN}${suffix}` : `https://${ROOT_DOMAIN}${suffix}`;
}
