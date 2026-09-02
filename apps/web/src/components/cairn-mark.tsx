import type { SVGProps } from "react";

/** The four standings a counterparty can hold, plus the mark's uncoloured form. */
export type Standing = "default" | "grounded" | "thin" | "suspect" | "dormant";

/**
 * Only the keystone ever takes a colour. Colour means evidence: lapis where
 * Cairn holds a grounded observation, oxide where its own record contradicts a
 * claim. `thin` is scree on purpose, absence of evidence should look like it.
 */
const KEYSTONE: Record<Standing, string> = {
  default: "currentColor",
  grounded: "var(--color-lapis)",
  thin: "var(--color-scree)",
  suspect: "var(--color-oxide)",
  dormant: "var(--color-seam)",
};

/** Bottom to top. The five stones are the five Sibyl Memory tiers. */
export const TIERS = ["ARCHIVE", "REFERENCE", "COLD", "WARM", "HOT"] as const;
export type Tier = (typeof TIERS)[number];

export interface StoneGeometry {
  readonly tier: Tier;
  readonly x: number;
  readonly y: number;
  readonly w: number;
  readonly h: number;
  readonly r: number;
  readonly tilt: number;
}

/**
 * The mark AND the seed geometry for the Stack. Changing these in one place
 * only will desync the logo from the product's signature element.
 *
 * The middle stone is wider than the one beneath it. That overhang is the
 * design: a monotonic pyramid reads as a stacking toy, not as something a
 * person built and left behind. Do not straighten the tilts.
 */
export const STONES: readonly StoneGeometry[] = [
  { tier: "ARCHIVE", x: 14, y: 93, w: 92, h: 15, r: 4, tilt: -1.0 },
  { tier: "REFERENCE", x: 27, y: 73, w: 58, h: 15, r: 4, tilt: 2.5 },
  { tier: "COLD", x: 22, y: 53, w: 82, h: 15, r: 4, tilt: -1.5 },
  { tier: "WARM", x: 31, y: 33, w: 52, h: 15, r: 4, tilt: 2.0 },
  { tier: "HOT", x: 45, y: 13, w: 38, h: 15, r: 4, tilt: -2.5 },
];

export type CairnMarkProps = { readonly standing?: Standing } & SVGProps<SVGSVGElement>;

export function CairnMark({ standing = "default", ...props }: CairnMarkProps) {
  return (
    <svg viewBox="0 0 120 120" fill="none" role="img" aria-label="Cairn" {...props}>
      {STONES.map((s, i) => (
        <rect
          key={s.tier}
          x={s.x}
          y={s.y}
          width={s.w}
          height={s.h}
          rx={s.r}
          fill={i === STONES.length - 1 ? KEYSTONE[standing] : "currentColor"}
          transform={`rotate(${s.tilt} ${s.x + s.w / 2} ${s.y + s.h / 2})`}
        />
      ))}
    </svg>
  );
}

/**
 * Three stones at the same proportions, for 16px to 20px where the five-stone
 * mark closes up and reads as a smudge. Never used above 20px.
 */
export function CairnIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 120 120" fill="none" role="img" aria-label="Cairn" {...props}>
      <rect x="41" y="20" width="46" height="22" rx="6" fill="currentColor" transform="rotate(-3 64 31)" />
      <rect x="16" y="48" width="90" height="22" rx="6" fill="currentColor" transform="rotate(-1 61 59)" />
      <rect x="19" y="76" width="80" height="22" rx="6" fill="currentColor" transform="rotate(2 59 87)" />
    </svg>
  );
}
