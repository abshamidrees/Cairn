import { Nav } from "@/components/shell";

/** The explorer's entry point. The dossier view is /explorer/<address>. */

export const dynamic = "force-dynamic";

const KNOWN: readonly (readonly [string, string])[] = [
  ["0x01f90369170c917a2c0e9d26d54c6a3a400984d3", "three independent claimants"],
  ["0x69747c4ce6185d21a33b3bcdba980d659600ac7b", "100 pieces of feedback, one claimant"],
];

export default function ExplorerPage() {
  return (
    <>
      <Nav />
      <main className="mx-auto max-w-[78rem] px-6 py-16">
        <p className="eyebrow">Explorer</p>
        <h1 className="mt-3 text-[length:var(--text-section)] leading-[var(--text-section-lead)] tracking-[var(--text-section-track)]">
          Look up an agent.
        </h1>
        <p className="mt-6 max-w-[34rem] text-[length:var(--text-lead)] leading-[var(--text-lead-lead)] text-slate">
          A dossier lives at /explorer/&lt;address&gt;. Two from the indexed set, for a start.
        </p>
        <ul className="mt-10 space-y-3">
          {KNOWN.map(([address, note]) => (
            <li key={address}>
              <a
                href={`/explorer/${address}`}
                className="font-mono text-[0.8125rem] text-lapis underline underline-offset-[1px]"
              >
                {address}
              </a>
              <span className="ml-3 text-slate">{note}</span>
            </li>
          ))}
        </ul>
      </main>
    </>
  );
}
