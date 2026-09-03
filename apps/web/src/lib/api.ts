/**
 * The read API, typed.
 *
 * `memory: "off"` is a real query parameter on a real endpoint. The empty state
 * it produces comes back from a server that genuinely had nothing to read, and
 * the toggle in the Stack never fabricates it locally.
 */

export type Standing = "grounded" | "thin" | "suspect" | "dormant";

/** Bottom to top, the same order the mark stacks its stones in. */
export const TIERS = ["ARCHIVE", "REFERENCE", "COLD", "WARM", "HOT"] as const;
export type Tier = (typeof TIERS)[number];

export interface Stone {
  readonly id: string;
  readonly tier: Tier;
  /** 0 to 1. Width, and only ever width. */
  readonly weight: number;
  /** Fill, and only ever fill. */
  readonly grounding: Standing;
  /** Degrees, derived from the id so a stone leans the same way forever. */
  readonly tilt: number;
  readonly label: string;
  readonly detail: Readonly<Record<string, unknown>>;
}

export interface VerdictPayload {
  readonly counterparty: string;
  readonly standing: Standing;
  readonly confidence: number | null;
  readonly no_basis: boolean;
  readonly evaluated_at: string;
  readonly sources_unavailable: readonly string[];
}

export interface Attestation {
  /** The Base transaction that published this verdict. */
  readonly tx_hash: string;
  readonly explorer_url: string;
  readonly contract: string | null;
  readonly chain_id: number | null;
}

export interface Dossier {
  readonly counterparty: string;
  /** Null until a verdict has actually been published on Base. */
  readonly attestation: Attestation | null;
  readonly memory: "on" | "off";
  readonly verdict: VerdictPayload;
  readonly tiers: readonly Tier[];
  readonly stones: Readonly<Record<Tier, readonly Stone[]>>;
  readonly counts: { readonly observations: number; readonly grounded: number };
}

export function apiBase(): string {
  return process.env["NEXT_PUBLIC_API_URL"] ?? "http://localhost:8000";
}

/**
 * The tilt formula, kept here so fixtures and live data lean identically.
 * The server derives the same value from the same id.
 */
export function tiltFor(id: string): number {
  let hash = 0;
  for (let i = 0; i < id.length; i += 1) {
    hash = (hash * 31 + id.charCodeAt(i)) >>> 0;
  }
  return Math.round(((hash % 500) / 100 - 2.5) * 100) / 100;
}

export async function fetchDossier(
  address: string,
  options: { memory: "on" | "off"; signal?: AbortSignal },
): Promise<Dossier> {
  const url = `${apiBase()}/v1/dossier/${address}?memory=${options.memory}`;
  const response = await fetch(url, {
    signal: options.signal ?? null,
    headers: { accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(`lookup failed: ${response.status}`);
  }
  return (await response.json()) as Dossier;
}
