import type { ReactNode } from "react";

import { CairnMark, type Standing } from "@/components/cairn-mark";

/**
 * The page chrome, and the claim / basis split that carries every section.
 */

/* ---- Nav --------------------------------------------------------------- */

export interface NavProps {
  /** The nav mark's keystone carries whatever the explorer is showing. */
  readonly standing?: Standing;
  /** The real count from the API. Omitted entirely when the API is unreachable. */
  readonly observations?: number | null;
}

export function Nav({ standing = "default", observations = null }: NavProps) {
  return (
    <nav className="border-b border-seam bg-chalk">
      <div className="mx-auto flex h-[60px] max-w-[78rem] items-center justify-between gap-6 px-6">
        <a href="/" className="flex items-center gap-3">
          <CairnMark standing={standing} width={28} height={28} />
          <span className="font-display text-[1.25rem] tracking-[-0.02em] text-graphite">Cairn</span>
        </a>

        <ul className="hidden items-center gap-8 md:flex">
          {["EXPLORER", "DOCS", "GITHUB"].map((label) => (
            <li key={label}>
              <a
                href={`/${label.toLowerCase()}`}
                className="font-mono text-[0.6875rem] uppercase tracking-[0.13em] text-slate hover:text-graphite"
              >
                {label}
              </a>
            </li>
          ))}
        </ul>

        <div className="flex items-center gap-4">
          {/* If the API is down this disappears rather than showing a zero,
              because a zero would be a claim Cairn cannot support. */}
          {observations !== null ? (
            <span className="hidden font-mono text-[0.6875rem] uppercase tracking-[0.13em] tabular-nums text-scree sm:inline">
              {observations} observations
            </span>
          ) : null}
          <a
            href="/explorer"
            className="rounded-pill bg-lapis px-4 py-1.5 font-mono text-[0.6875rem] uppercase tracking-[0.13em] text-chalk transition-colors duration-[var(--dur-fast)] hover:bg-lapis-ink"
          >
            Look up an agent
          </a>
        </div>
      </div>
    </nav>
  );
}

/* ---- Footer ------------------------------------------------------------ */

export interface TickerEntry {
  readonly id: string;
  readonly at: string;
  readonly kind: string;
  readonly counterparty: string;
  readonly standing: string;
}

const FOOTER_LINKS: readonly (readonly [string, readonly string[]])[] = [
  ["Product", ["Explorer", "Docs", "Standing definitions"]],
  ["Build", ["GitHub", "API reference", "Memory note"]],
  ["Company", ["X", "Discord", "Hackathon submission"]],
];

export function Footer({ ticker = [] }: { readonly ticker?: readonly TickerEntry[] }) {
  return (
    <footer className="bg-basalt text-chalk">
      <div className="mx-auto flex max-w-[78rem] flex-col gap-12 px-6 py-16 md:flex-row md:justify-between">
        <div className="flex items-center gap-4">
          <CairnMark standing="grounded" width={48} height={48} />
          <span className="font-display text-[2.5rem] leading-none tracking-[-0.02em]">Cairn</span>
        </div>

        <div className="grid grid-cols-2 gap-10 sm:grid-cols-3">
          {FOOTER_LINKS.map(([heading, links]) => (
            <div key={heading}>
              <p className="font-mono text-[0.6875rem] uppercase tracking-[0.13em] text-scree">
                {heading}
              </p>
              <ul className="mt-3 space-y-2">
                {links.map((link) => (
                  <li key={link}>
                    <a href="#" className="text-[0.9375rem] text-chalk/80 hover:text-chalk">
                      {link}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>

      {/* The footer proves the thing is running. With nothing to show it says
          nothing, rather than scrolling invented rows. */}
      {ticker.length > 0 ? (
        <div className="border-t border-chalk/10">
          <ul className="mx-auto flex max-w-[78rem] flex-wrap gap-x-8 gap-y-2 px-6 py-3">
            {ticker.map((entry) => (
              <li key={entry.id} className="font-mono text-[0.6875rem] tabular-nums text-scree">
                {entry.at} {entry.kind} {entry.counterparty} {entry.standing}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="border-t border-chalk/10">
        <p className="mx-auto max-w-[78rem] px-6 py-4 font-mono text-[0.6875rem] text-scree">
          © 2026 Cairn · MIT licensed · Built on Sibyl Memory
        </p>
      </div>
    </footer>
  );
}

/* ---- BasisColumn ------------------------------------------------------- */

/**
 * The right half of the claim / basis split: what the claim on the left rests
 * on. Under 900px it collapses beneath its claim rather than being hidden,
 * because a claim without its basis is the thing this product exists to reject.
 */
export function BasisColumn({
  label,
  children,
}: {
  readonly label: string;
  readonly children: ReactNode;
}) {
  return (
    <div className="border-l-0 border-seam md:border-l md:pl-8">
      <p className="font-mono text-[0.6875rem] uppercase tracking-[0.13em] text-scree">{label}</p>
      <div className="mt-4 font-mono text-[0.8125rem] text-slate">{children}</div>
    </div>
  );
}

export function ClaimBasis({
  claim,
  basisLabel,
  basis,
}: {
  readonly claim: ReactNode;
  readonly basisLabel: string;
  readonly basis: ReactNode;
}) {
  return (
    <div className="grid gap-8 md:grid-cols-[58%_42%]">
      <div>{claim}</div>
      <BasisColumn label={basisLabel}>{basis}</BasisColumn>
    </div>
  );
}
