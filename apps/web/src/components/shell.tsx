import type { ReactNode } from "react";

import { FirsthandMark, type Standing } from "@/components/firsthand-mark";
import { CommandPalette } from "@/components/command-palette";

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
          <FirsthandMark standing={standing} width={28} height={28} />
          <span className="font-display text-[1.25rem] tracking-[-0.02em] text-graphite">Firsthand</span>
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
          {/* Mounted once, in the nav, which is on every page. A second copy
              in the footer meant two keydown listeners and two stacked dialogs
              answering one keystroke. */}
          <CommandPalette />
          {/* If the API is down this disappears rather than showing a zero,
              because a zero would be a claim Firsthand cannot support. */}
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
          <FirsthandMark standing="grounded" width={48} height={48} />
          <span className="font-display text-[2.5rem] leading-none tracking-[-0.02em]">Firsthand</span>
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
          © 2026 Firsthand · MIT licensed · Built on Sibyl Memory
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
    <div className="min-w-0 border-l-0 border-seam md:border-l md:pl-8">
      <p className="font-mono text-[0.6875rem] uppercase tracking-[0.13em] text-slate">{label}</p>
      {/* This column exists to show hashes, addresses and source strings, and
          every one of them is longer than the column is wide. Breaking is the
          default here rather than something each row remembers to ask for: one
          line that forgot pushed the whole grid track past the viewport and put
          a horizontal scrollbar on the page. `anywhere` rather than break-all,
          so ordinary words still break on spaces. */}
      <div className="mt-4 font-mono text-[0.8125rem] text-slate [overflow-wrap:anywhere]">
        {children}
      </div>
    </div>
  );
}

export function ClaimBasis({
  claim,
  basisLabel,
  basis,
  stacked = false,
}: {
  readonly claim: ReactNode;
  readonly basisLabel: string;
  readonly basis: ReactNode;
  /**
   * Puts the basis full width beneath the claim instead of beside it. The
   * split is the thesis and does not change; where it sits on the page is
   * execution, and running the same two columns five times reads as a
   * template. Wide bases, a table of every tier for instance, are also
   * simply better full width.
   */
  readonly stacked?: boolean;
}) {
  if (stacked) {
    return (
      <div className="flex flex-col gap-10">
        <div className="min-w-0 max-w-[52rem]">{claim}</div>
        <BasisColumn label={basisLabel}>{basis}</BasisColumn>
      </div>
    );
  }
  // fr, not percent. 58% + 42% + gap-8 sums to the container plus 32px, so the
  // grid sat wider than the page at every width that used two columns and put a
  // horizontal scrollbar under the whole site. fr divides what is left after the
  // gap, which is what a 58/42 split was always supposed to mean.
  return (
    <div className="grid gap-8 md:grid-cols-[58fr_42fr]">
      <div className="min-w-0">{claim}</div>
      <BasisColumn label={basisLabel}>{basis}</BasisColumn>
    </div>
  );
}
