import type { SVGProps } from "react";

/** The four standings a counterparty can hold, plus the mark's uncoloured form. */
export type Standing = "default" | "grounded" | "thin" | "suspect" | "dormant";

/**
 * Only the solid rule ever takes a colour. Colour means evidence: lapis where
 * Firsthand holds a grounded observation, oxide where its own record
 * contradicts a claim. `thin` is scree on purpose, absence of evidence should
 * look like it.
 */
const WITNESSED: Record<Standing, string> = {
  default: "currentColor",
  grounded: "var(--color-lapis)",
  thin: "var(--color-scree)",
  suspect: "var(--color-oxide)",
  dormant: "var(--color-seam)",
};

export interface RuleGeometry {
  readonly x: number;
  readonly y: number;
  readonly w: number;
  readonly h: number;
  readonly r: number;
  /** The one rule that is filled rather than outlined. */
  readonly solid?: boolean;
}

/**
 * Four claims, one witnessed. Flush left, ragged right, no tilt.
 *
 * The grammar is the token file's, not a new one: `.stone--thin` is a hairline
 * outline and `.stone--grounded` is solid lapis, so the mark is literally three
 * thin observations and one grounded one. Widths are ragged because a record is
 * uneven; straightening them would say something about the evidence that is not
 * true.
 */
export const RULES: readonly RuleGeometry[] = [
  { x: 19.5, y: 17.5, w: 49, h: 13, r: 3.5 },
  { x: 19.5, y: 41.5, w: 71, h: 13, r: 3.5 },
  { x: 18, y: 64, w: 92, h: 16, r: 4, solid: true },
  { x: 19.5, y: 89.5, w: 33, h: 13, r: 3.5 },
];

export type FirsthandMarkProps = { readonly standing?: Standing } & SVGProps<SVGSVGElement>;

export function FirsthandMark({ standing = "default", ...props }: FirsthandMarkProps) {
  return (
    <svg viewBox="0 0 120 120" fill="none" role="img" aria-label="Firsthand" {...props}>
      {RULES.map((rule) =>
        rule.solid ? (
          <rect
            key={`${rule.x}-${rule.y}`}
            x={rule.x}
            y={rule.y}
            width={rule.w}
            height={rule.h}
            rx={rule.r}
            fill={WITNESSED[standing]}
          />
        ) : (
          <rect
            key={`${rule.x}-${rule.y}`}
            x={rule.x}
            y={rule.y}
            width={rule.w}
            height={rule.h}
            rx={rule.r}
            fill="none"
            stroke="currentColor"
            strokeWidth={3}
          />
        ),
      )}
    </svg>
  );
}

/**
 * Three rules at the same construction, for 16px to 20px where the fourth rule
 * closes up and the mark reads as a smudge. Never used above 20px.
 */
export function FirsthandIcon({
  standing = "default",
  ...props
}: { readonly standing?: Standing } & SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 120 120" fill="none" role="img" aria-label="Firsthand" {...props}>
      <rect
        x="18"
        y="22"
        width="54"
        height="18"
        rx="3.5"
        fill="none"
        stroke="currentColor"
        strokeWidth={4}
      />
      <rect x="16" y="50" width="88" height="22" rx="4" fill={WITNESSED[standing]} />
      <rect
        x="18"
        y="82"
        width="36"
        height="18"
        rx="3.5"
        fill="none"
        stroke="currentColor"
        strokeWidth={4}
      />
    </svg>
  );
}
