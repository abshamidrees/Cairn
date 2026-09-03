/**
 * What Cairn currently holds, fetched on the server for the landing page.
 *
 * Every figure the page prints comes from here. When the API cannot be reached
 * this returns null and the sections that depend on it are not rendered at all,
 * because a section that needs a number Cairn does not have is a section that
 * should not exist. Showing a zero would be a claim; showing nothing is not.
 */

import { apiBase } from "@/lib/api";

export interface ObservationExample {
  readonly kind: string;
  readonly source: string | null;
  readonly content_hash: string | null;
  readonly occurred_at: string | null;
  readonly tx_hash: string | null;
  readonly counterparty: string;
}

export interface ReviewerExample {
  readonly address: string;
  readonly claims: number;
  readonly corroborated: number;
  readonly weight: number;
  readonly provisional: boolean;
}

export interface RecentObservation {
  readonly at: string;
  readonly kind: string;
  readonly counterparty: string;
}

export interface Stats {
  readonly available: true;
  readonly generated_at: string;
  readonly counterparties: number;
  readonly reviewers: number;
  readonly observations: number;
  readonly observation_kinds: Readonly<Record<string, number>>;
  readonly observation_examples: readonly ObservationExample[];
  readonly tiers: Readonly<Record<string, number>>;
  readonly standings: Readonly<Record<string, number>>;
  readonly reviewer_example: ReviewerExample | null;
  readonly reviewers_provisional: number;
  readonly recent: readonly RecentObservation[];
}

export async function getStats(): Promise<Stats | null> {
  try {
    const response = await fetch(`${apiBase()}/v1/stats`, { cache: "no-store" });
    if (!response.ok) return null;
    const body = (await response.json()) as Stats | { available: false };
    return body.available ? (body as Stats) : null;
  } catch {
    // The record lives on the machine that serves it. If that machine is not
    // answering, the page says less rather than saying something untrue.
    return null;
  }
}
