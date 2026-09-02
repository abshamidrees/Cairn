"use client";

import type { CSSProperties } from "react";

import type { Stone as StoneData } from "@/lib/api";

/**
 * One stone is one row in the database.
 *
 * Width encodes weight, how much the observation moves the verdict. Fill encodes
 * grounding. The two channels never swap: a wide stone is not a trusted one, and
 * a lapis stone is not an important one.
 */

/** Narrowest a stone may be drawn, so a near-zero weight is still a stone. */
const MIN_WIDTH_PCT = 18;

export function stoneWidth(weight: number): number {
  const clamped = Math.max(0, Math.min(1, weight));
  return MIN_WIDTH_PCT + clamped * (100 - MIN_WIDTH_PCT);
}

export interface StoneProps {
  readonly stone: StoneData;
  readonly index: number;
  readonly focused: boolean;
  readonly leaving: boolean;
  /** Bottom-up entry order across the whole stack, for the stagger. */
  readonly enterOrder: number;
  readonly animate: boolean;
  /**
   * Upper bound on the per-stone delay, in milliseconds. The spec's 90ms is
   * right for a dossier of a few dozen stones and absurd for a few hundred:
   * two hundred at 90ms would take eighteen seconds to finish arriving. The
   * cap is applied in CSS so `--stagger` remains the token that decides.
   */
  readonly staggerCapMs?: number;
  readonly onFocus: () => void;
  readonly onSelect: () => void;
}

export function Stone({
  stone,
  index,
  focused,
  leaving,
  enterOrder,
  animate,
  staggerCapMs,
  onFocus,
  onSelect,
}: StoneProps) {
  const style: CSSProperties & Record<"--tilt", string> = {
    "--tilt": `${stone.tilt}deg`,
    width: `${stoneWidth(stone.weight)}%`,
    transform: `rotate(${stone.tilt}deg)`,
    animationDelay: animate
      ? staggerCapMs === undefined
        ? `calc(${enterOrder} * var(--stagger))`
        : `calc(${enterOrder} * min(var(--stagger), ${staggerCapMs}ms))`
      : undefined,
  };

  const state = leaving ? "stone--leaving" : animate ? "stone--entering" : "";

  return (
    <button
      type="button"
      data-stone-index={index}
      tabIndex={focused ? 0 : -1}
      onFocus={onFocus}
      onClick={onSelect}
      aria-label={`${stone.label}, ${stone.grounding}, tier ${stone.tier}`}
      className={`stone stone--${stone.grounding} ${state} block cursor-pointer`}
      style={style}
    />
  );
}

/**
 * What a stone is, shown when one is hovered or focused. Every field here is
 * something Cairn witnessed and can point at, including the hash of the raw
 * evidence, so the card is the grounding made legible.
 */
export function ObservationCard({ stone }: { readonly stone: StoneData | null }) {
  if (stone === null) {
    return (
      <div className="rounded-stone border border-dashed border-seam p-4">
        <p className="font-mono text-[0.6875rem] uppercase tracking-[0.13em] text-scree">
          select a stone
        </p>
        <p className="mt-2 text-[0.8125rem] text-scree">
          Every stone is one observation. Focus one to see what Cairn witnessed.
        </p>
      </div>
    );
  }

  const detail = stone.detail;
  const rows: readonly (readonly [string, string])[] = [
    ["tier", stone.tier],
    ["grounding", stone.grounding],
    ["weight", stone.weight.toFixed(4)],
    ...Object.entries(detail).map(
      ([key, value]) => [key, value === null || value === undefined ? "-" : String(value)] as const,
    ),
  ];

  return (
    <div className="rounded-stone border border-seam bg-paper p-4">
      <p className="font-mono text-[0.6875rem] uppercase tracking-[0.13em] text-scree">
        {stone.label}
      </p>
      <dl className="mt-3 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1.5">
        {rows.map(([key, value]) => (
          <div key={key} className="contents">
            <dt className="font-mono text-[0.6875rem] uppercase tracking-[0.13em] text-scree">
              {key}
            </dt>
            <dd className="break-all font-mono text-[0.8125rem] tabular-nums text-slate">
              {value}
            </dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
