/**
 * Every internal link is built from here rather than hardcoded, so a link to a
 * dossier lands on explorer.usefirsthand.xyz/0xabc and not on the path form. The
 * middleware rewrites subdomains onto path roots; this is the inverse, and the
 * two must agree.
 *
 * Subdomains are only used when NEXT_PUBLIC_ROOT_DOMAIN names a domain that
 * actually resolves. Until one is pointed here the site is served from a single
 * platform origin, where every surface is a path, exactly as in development.
 * Writing the domain in as a constant would mean canonical tags and OG urls
 * pointing at a host that answers nothing.
 */

export type Surface = "landing" | "explorer" | "docs";

const CONFIGURED_ROOT = process.env["NEXT_PUBLIC_ROOT_DOMAIN"] ?? "";

/** The domain the subdomain surfaces live on once DNS points at the deployment. */
export const ROOT_DOMAIN = CONFIGURED_ROOT || "usefirsthand.xyz";

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

function siteOrigin(): string {
  return process.env["NEXT_PUBLIC_SITE_ORIGIN"] ?? "http://localhost:3000";
}

/** True only when a root domain is configured, which is what splits the surfaces. */
function useSubdomains(): boolean {
  return CONFIGURED_ROOT !== "";
}

/** Absolute origin for a surface. On a single origin every surface shares it. */
export function hostFor(surface: Surface): string {
  if (!useSubdomains()) return siteOrigin();
  const sub = SUBDOMAIN[surface];
  return sub ? `https://${sub}.${ROOT_DOMAIN}` : `https://${ROOT_DOMAIN}`;
}

/**
 * A full URL for a surface. On a single origin the path root carries the
 * surface; with subdomains configured the subdomain does.
 */
export function urlFor(surface: Surface, path = ""): string {
  const suffix = path && !path.startsWith("/") ? `/${path}` : path;
  if (!useSubdomains()) return `${siteOrigin()}${PATH_ROOT[surface]}${suffix}`;
  return `${hostFor(surface)}${suffix}`;
}

/**
 * The canonical form is always the subdomain, never the path form, or
 * usefirsthand.xyz/docs and docs.usefirsthand.xyz both index as duplicates.
 * With no root domain configured there is only one origin, so there is no
 * duplicate to resolve and the path form is itself canonical.
 */
export function canonicalFor(surface: Surface, path = ""): string {
  return urlFor(surface, path);
}
