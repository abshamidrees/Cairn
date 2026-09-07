import { Nav } from "@/components/shell";
import { ExplorerSearch } from "@/components/explorer-search";
import { apiBase } from "@/lib/api";

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

export default async function ExplorerPage() {
  const recent = await getRecent();

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

        <section className="mt-14">
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
