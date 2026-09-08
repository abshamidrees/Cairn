import { Nav } from "@/components/shell";
import { ExplorerSearch } from "@/components/explorer-search";
import { apiBase } from "@/lib/api";
import { getStats } from "@/lib/stats";

/** The explorer's entry point. An instrument, not a marketing page. */

export const dynamic = "force-dynamic";

async function getRecent(): Promise<readonly string[]> {
  try {
    const response = await fetch(`${apiBase()}/v1/recent`, { cache: "no-store" });
    if (!response.ok) return [];
    const body = (await response.json()) as { recent?: readonly string[] };
    return body.recent ?? [];
  } catch {
    return [];
  }
}

const STANDING_ORDER = ["grounded", "thin", "suspect", "dormant"] as const;

const STANDING_GLOSS: Readonly<Record<(typeof STANDING_ORDER)[number], string>> = {
  grounded: "corroborated by a party that did not make the claim",
  thin: "too little witnessed to say anything",
  suspect: "the record contradicts itself, and the rows can be named",
  dormant: "nothing witnessed inside the decay window",
};

export default async function ExplorerPage() {
  const [recent, stats] = await Promise.all([getRecent(), getStats()]);

  return (
    <>
      <Nav />
      <main className="mx-auto max-w-[78rem] px-6 py-16">
        <p className="eyebrow">Explorer</p>
        <h1 className="mt-3 text-[length:var(--text-section)] leading-[var(--text-section-lead)] tracking-[var(--text-section-track)]">
          Look up an agent.
        </h1>

        <div className="mt-10 max-w-[40rem]">
          <ExplorerSearch />
          {/* A first-time reader has no address to type, and an empty search is a
              dead end on the one page that has to demonstrate the product. This
              is the counterparty three separate claimants spoke about, which is
              the only grounded dossier in the indexed set. */}
          <p className="mt-3 font-mono text-[0.6875rem] text-slate">
            Nothing to hand? Open{" "}
            <a
              href="/explorer/0x01f90369170c917a2c0e9d26d54c6a3a400984d3"
              className="text-lapis underline underline-offset-2 hover:text-lapis-ink"
            >
              0x01f90369…84d3
            </a>
            , the one counterparty in the indexed set with a grounded record.
          </p>
          <p className="mt-2 font-mono text-[0.6875rem] text-slate">
            Press Ctrl+K, or Cmd+K on a Mac, anywhere on the site. Prefix rv: to look up a claimant.
          </p>
        </div>

        {/* The page ran two thirds empty below the search. This is what the
            front of a reference work carries: what is in the set, and what a
            lookup returns. Counts are live, so a set that changes says so. */}
        {stats === null ? null : (
          <section className="mt-16 max-w-[46rem]">
            <p className="font-mono text-[0.6875rem] uppercase tracking-[0.13em] text-slate">
              the indexed set, {stats.counterparties} counterparties
            </p>
            <dl className="mt-4 border-t border-seam">
              {STANDING_ORDER.map((standing) => (
                <div
                  key={standing}
                  className="flex items-baseline justify-between gap-6 border-b border-seam py-3"
                >
                  <dt className="font-mono text-[0.8125rem] uppercase tracking-[0.13em] text-graphite">
                    {standing}
                  </dt>
                  <dd className="flex items-baseline gap-6">
                    <span className="hidden text-right text-slate sm:inline">
                      {STANDING_GLOSS[standing]}
                    </span>
                    <span className="w-12 shrink-0 text-right font-mono text-[1.125rem] tabular-nums text-graphite">
                      {stats.standings[standing] ?? 0}
                    </span>
                  </dd>
                </div>
              ))}
            </dl>
            <p className="mt-5 max-w-[42rem] text-slate">
              A counterparty address returns its dossier: the observations Firsthand witnessed,
              arranged by the tier each one lives in, and a verdict with the basis it rests on.
              Prefix an address with rv: to read a claimant instead, and see how much of what they
              said anybody else corroborated.
            </p>
          </section>
        )}

        <section className="mt-16">
          <p className="font-mono text-[0.6875rem] uppercase tracking-[0.13em] text-slate">
            recent, from Firsthand&rsquo;s own record
          </p>
          {recent.length === 0 ? (
            <p className="mt-3 max-w-[40rem] text-slate">
              Nothing looked up yet. Recent lookups are kept in Firsthand&rsquo;s own dossier
              rather than in this browser, so the first search will appear here and on any
              other machine.
            </p>
          ) : (
            <ul className="mt-3 space-y-2">
              {recent.map((tenant) => {
                const address = tenant.replace(/^cp:base:/, "");
                return (
                  <li key={tenant}>
                    <a
                      href={`/explorer/${address}`}
                      className="break-all font-mono text-[0.8125rem] text-lapis underline underline-offset-[1px]"
                    >
                      {address}
                    </a>
                  </li>
                );
              })}
            </ul>
          )}
        </section>
      </main>
    </>
  );
}
