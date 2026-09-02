/**
 * Fixtures for the kitchen sink only.
 *
 * These exist so every component can be shown in every state, including states
 * the live indexed set does not currently contain, such as a suspect standing.
 * Nothing here is ever rendered on a product surface, and none of it is a
 * measurement: no counts, percentages or figures from this file appear anywhere
 * a reader could mistake them for something Cairn witnessed.
 */

import { TIERS, tiltFor, type Stone, type Tier } from "@/lib/api";

type Grounding = Stone["grounding"];

function stone(id: string, tier: Tier, weight: number, grounding: Grounding): Stone {
  return {
    id,
    tier,
    weight,
    grounding,
    tilt: tiltFor(id),
    label: "erc8004_feedback",
    detail: {
      occurred_at: "2026-09-01T12:00:00.000Z",
      source: "base:0x8004BAa17C55a88189AE136b182e5fdA19dE9b63",
      content_hash: "sha256:fixture",
      corroborated: grounding === "grounded",
    },
  };
}

function empty(): Record<Tier, Stone[]> {
  return { ARCHIVE: [], REFERENCE: [], COLD: [], WARM: [], HOT: [] };
}

export const GROUNDED_STACK: Record<Tier, Stone[]> = {
  ...empty(),
  ARCHIVE: [stone("a1", "ARCHIVE", 0.3, "dormant"), stone("a2", "ARCHIVE", 0.22, "dormant")],
  REFERENCE: [stone("r1", "REFERENCE", 0.45, "thin")],
  COLD: [
    stone("c1", "COLD", 0.9, "grounded"),
    stone("c2", "COLD", 0.62, "grounded"),
    stone("c3", "COLD", 0.4, "thin"),
    stone("c4", "COLD", 0.75, "grounded"),
  ],
  WARM: [stone("w1", "WARM", 0.8, "grounded"), stone("w2", "WARM", 0.5, "thin")],
  HOT: [stone("h1", "HOT", 0.87, "grounded")],
};

export const THIN_STACK: Record<Tier, Stone[]> = {
  ...empty(),
  COLD: [stone("t1", "COLD", 0.35, "thin"), stone("t2", "COLD", 0.28, "thin")],
};

export const SUSPECT_STACK: Record<Tier, Stone[]> = {
  ...empty(),
  COLD: [
    stone("s1", "COLD", 0.7, "suspect"),
    stone("s2", "COLD", 0.55, "grounded"),
    stone("s3", "COLD", 0.3, "thin"),
  ],
  HOT: [stone("s0", "HOT", 0.4, "suspect")],
};

export const EMPTY_STACK: Record<Tier, Stone[]> = empty();

/** The performance harness. Two hundred stones spread across the five bands. */
export function largeStack(total: number): Record<Tier, Stone[]> {
  const out = empty();
  const groundings: readonly Grounding[] = ["grounded", "thin", "suspect", "dormant"];
  for (let i = 0; i < total; i += 1) {
    const tier = TIERS[i % TIERS.length] as Tier;
    const grounding = groundings[i % groundings.length] as Grounding;
    out[tier].push(stone(`perf-${i}`, tier, ((i * 37) % 100) / 100, grounding));
  }
  return out;
}

export function countsOf(stones: Record<Tier, Stone[]>): {
  observations: number;
  grounded: number;
} {
  const cold = stones.COLD;
  return {
    observations: cold.length,
    grounded: cold.filter((s) => s.grounding === "grounded").length,
  };
}
