"use client";

import { BrowserFrame, StandingChip } from "@/components/primitives";
import type { Stone, Standing } from "@/lib/api";

/**
 * One real dossier response, in the slot the Stack keeps for a selected stone.
 *
 * That slot used to read "select a stone" and show nothing until someone
 * interacted, which spent the most valuable space on the page on an
 * instruction. This shows the answer instead: the standing, the confidence, and
 * the first rows of the basis with the transactions they were read from. A
 * reader who never touches anything still sees the product point at its own
 * evidence, which is the whole claim.
 *
 * Every field is from the API response. With memory off there is no basis and
 * the card says so, because that empty state is the point of the toggle.
 */

/** Two rows. Enough to show the basis is real, short enough to stay a card. */
const BASIS_ROWS = 2;

function shortAddress(tenant: string): string {
  const address = tenant.replace(/^cp:base:/, "");
  return address.length > 12 ? `${address.slice(0, 10)}…${address.slice(-4)}` : address;
}

function shortHash(hash: string): string {
  return hash.length > 14 ? `${hash.slice(0, 10)}…` : hash;
}

function dayOf(stamp: string | null): string {
  return stamp === null ? "-" : stamp.slice(0, 10);
}

export interface VerdictCardProps {
  readonly counterparty: string;
  readonly standing: Standing;
  readonly confidence: number | null;
  readonly basis: readonly Stone[];
  readonly total: number;
}

export function VerdictCard({
  counterparty,
  standing,
  confidence,
  basis,
  total,
}: VerdictCardProps) {
  const rows = basis.slice(0, BASIS_ROWS);

  return (
    <BrowserFrame label={`/v1/dossier/${shortAddress(counterparty)}`}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <StandingChip standing={standing} />
        <span className="font-mono text-[0.8125rem] tabular-nums text-scree">
          confidence {confidence === null ? "-" : confidence.toFixed(2)}
        </span>
      </div>

      {/* No verdict sentence here. The Stack above already carries it, and
          italic means "this is Firsthand's judgment": printing it twice on one
          screen spends the one typographic signal the product reserves. This
          card is the response payload, so it shows the fields. */}
      <p className="mt-5 font-mono text-[0.6875rem] uppercase tracking-[0.13em] text-scree">
        {rows.length === 0 ? "no basis to show" : `basis, ${rows.length} of ${total}`}
      </p>

      {rows.length === 0 ? (
        <p className="mt-2 text-[0.8125rem] text-scree">
          Nothing was read, so there is nothing to point at.
        </p>
      ) : (
        <ul className="mt-2">
          {rows.map((stone) => {
            const detail = stone.detail as {
              readonly tx_hash?: string | null;
              readonly occurred_at?: string | null;
            };
            const tx = typeof detail.tx_hash === "string" ? detail.tx_hash : null;
            return (
              <li
                key={stone.id}
                className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 border-b border-seam py-2 last:border-b-0"
              >
                <span className="font-mono text-[0.8125rem] text-slate">{stone.label}</span>
                <span className="flex items-baseline gap-4">
                  <span className="font-mono text-[0.8125rem] tabular-nums text-scree">
                    {dayOf(detail.occurred_at ?? null)}
                  </span>
                  {tx === null ? (
                    <span className="font-mono text-[0.8125rem] text-scree">off chain</span>
                  ) : (
                    <a
                      href={`https://basescan.org/tx/${tx}`}
                      target="_blank"
                      rel="noreferrer"
                      className="font-mono text-[0.8125rem] text-lapis underline underline-offset-[2px] hover:text-lapis-ink"
                    >
                      {shortHash(tx)}
                    </a>
                  )}
                </span>
              </li>
            );
          })}
        </ul>
      )}
    </BrowserFrame>
  );
}
