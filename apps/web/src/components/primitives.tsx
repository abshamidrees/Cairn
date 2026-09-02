/**
 * The small components everything else is built from.
 *
 * Every colour, radius and duration here comes from tokens.css. Nothing in this
 * file names a font family: the token file maps roles onto the font variables,
 * so a component asks for display, sans or mono and never for Newsreader.
 */

import type { ButtonHTMLAttributes, ReactNode } from "react";

import type { Standing } from "@/lib/api";

/* ---- Eyebrow ---------------------------------------------------------- */

export function Eyebrow({ children }: { children: ReactNode }) {
  return <p className="eyebrow">{children}</p>;
}

/* ---- Button ------------------------------------------------------------ */

type ButtonVariant = "primary" | "ghost";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  readonly variant?: ButtonVariant;
}

export function Button({ variant = "primary", className = "", ...props }: ButtonProps) {
  const base =
    "inline-flex items-center gap-2 rounded-pill px-5 py-2 font-mono text-[0.6875rem] " +
    "uppercase tracking-[0.13em] transition-colors " +
    "duration-[var(--dur-fast)] disabled:opacity-40 disabled:pointer-events-none";
  const tone =
    variant === "primary"
      ? "bg-lapis text-chalk hover:bg-lapis-ink"
      : "border border-seam text-graphite hover:border-graphite/20";
  return <button className={`${base} ${tone} ${className}`} {...props} />;
}

/* ---- StandingChip ------------------------------------------------------ */

/**
 * `thin` is deliberately colourless. Absence of evidence should look like
 * absence, not like a warning.
 */
export function StandingChip({ standing }: { standing: Standing }) {
  return <span className={`standing standing--${standing}`}>{standing}</span>;
}

/* ---- VerdictLine ------------------------------------------------------- */

/** The only italic in the product, so italic means "this is Cairn's judgment". */
export function VerdictLine({
  standing,
  confidence,
  noBasis = false,
}: {
  readonly standing: Standing;
  readonly confidence: number | null;
  readonly noBasis?: boolean;
}) {
  const sentence = noBasis
    ? "no basis"
    : standing === "grounded"
      ? "Cairn has watched this counterparty do what it said it would."
      : standing === "suspect"
        ? "Cairn's own record contradicts a claim about this counterparty."
        : standing === "dormant"
          ? "Cairn has not witnessed this counterparty in some time."
          : "Cairn has too little to go on.";

  return (
    <p className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
      <span className="verdict text-[1.25rem]">{sentence}</span>
      <span className="font-mono text-[0.8125rem] text-scree tabular-nums">
        confidence {confidence === null ? "-" : confidence.toFixed(2)}
      </span>
    </p>
  );
}

/* ---- StatRow ----------------------------------------------------------- */

export function StatRow({ figure, label }: { readonly figure: string; readonly label: string }) {
  return (
    <div className="flex items-baseline justify-between gap-6 border-b border-seam py-5">
      <span className="font-mono text-[2rem] tabular-nums text-graphite">{figure}</span>
      <span className="max-w-[28rem] text-right text-slate">{label}</span>
    </div>
  );
}

/* ---- MonoTable --------------------------------------------------------- */

export function MonoTable({
  columns,
  rows,
}: {
  readonly columns: readonly string[];
  readonly rows: readonly (readonly ReactNode[])[];
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse font-mono text-[0.8125rem]">
        <thead>
          <tr>
            {columns.map((column) => (
              <th
                key={column}
                scope="col"
                className="border-b border-seam py-2 pr-6 text-left text-[0.6875rem] uppercase tracking-[0.13em] text-scree font-normal"
              >
                {column}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i}>
              {row.map((cell, j) => (
                <td key={j} className="border-b border-seam py-2 pr-6 tabular-nums text-slate">
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* ---- TerminalCard ------------------------------------------------------ */

export function TerminalCard({ command }: { readonly command: string }) {
  return (
    <div className="rounded-stone bg-basalt p-4">
      <code className="block font-mono text-[0.8125rem] text-chalk">
        <span className="text-scree select-none">$ </span>
        {command}
      </code>
    </div>
  );
}

/* ---- BrowserFrame ------------------------------------------------------ */

export function BrowserFrame({
  label,
  children,
}: {
  readonly label: string;
  readonly children: ReactNode;
}) {
  return (
    <div className="rounded-stone border border-seam bg-paper">
      <div className="flex items-center gap-2 border-b border-seam px-4 py-2">
        <span className="font-mono text-[0.6875rem] text-scree">{label}</span>
      </div>
      <div className="p-4">{children}</div>
    </div>
  );
}

/* ---- Skeleton ---------------------------------------------------------- */

/** A shape, not a shimmer. The motion budget is spent on the Stack. */
export function Skeleton({ width = "100%" }: { readonly width?: string }) {
  return (
    <span
      aria-hidden
      className="block h-3 rounded-stone bg-seam"
      style={{ width }}
    />
  );
}

/* ---- EmptyState / ErrorState ------------------------------------------- */

export function EmptyState({
  title,
  detail,
  action,
}: {
  readonly title: string;
  readonly detail: string;
  readonly action?: ReactNode;
}) {
  return (
    <div className="rounded-stone border border-seam bg-paper p-8">
      <p className="font-display text-[1.5rem] text-graphite">{title}</p>
      <p className="mt-2 max-w-[36rem] text-slate">{detail}</p>
      {action ? <div className="mt-5">{action}</div> : null}
    </div>
  );
}

export function ErrorState({
  title,
  detail,
  action,
}: {
  readonly title: string;
  readonly detail: string;
  readonly action?: ReactNode;
}) {
  return (
    <div className="rounded-stone border border-oxide/30 bg-paper p-8">
      <p className="font-mono text-[0.6875rem] uppercase tracking-[0.13em] text-oxide">
        could not read the record
      </p>
      <p className="mt-3 font-display text-[1.5rem] text-graphite">{title}</p>
      <p className="mt-2 max-w-[36rem] text-slate">{detail}</p>
      {action ? <div className="mt-5">{action}</div> : null}
    </div>
  );
}
