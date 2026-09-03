import { readFile } from "node:fs/promises";
import path from "node:path";

import { Nav } from "@/components/shell";

/**
 * The public scan of the indexed Base set.
 *
 * An aggregate finding about how the reputation layer is used, not a list of
 * bad actors. Nobody is named, ranked or accused here: the record supports a
 * claim about the registry's design, and it does not support a claim about any
 * individual agent's conduct. Publishing the second would be the mistake that
 * outlives the hackathon.
 *
 * The underlying JSON is served at /scan.json so a reader can check the numbers
 * rather than take them.
 */

export const dynamic = "force-dynamic";

interface Scan {
  readonly generated_at: string;
  readonly method: {
    readonly chain_id: number;
    readonly identity_registry: string;
    readonly reputation_registry: string;
    readonly blocks: string;
    readonly reproduce: readonly string[];
    readonly note: string;
  };
  readonly indexed: Readonly<Record<string, number>>;
  readonly finding: {
    readonly subjects_with_feedback: number;
    readonly subjects_with_a_single_voice: number;
    readonly share_single_voice: number | null;
    readonly voices_per_subject: Readonly<Record<string, number>>;
    readonly largest_single_claimant_volume: number;
    readonly reads: string;
  };
  readonly standings: Readonly<Record<string, number | string>>;
}

async function getScan(): Promise<Scan | null> {
  try {
    const file = path.join(process.cwd(), "public", "scan.json");
    return JSON.parse(await readFile(file, "utf8")) as Scan;
  } catch {
    return null;
  }
}

export default async function ScanPage() {
  const scan = await getScan();

  if (scan === null) {
    return (
      <>
        <Nav />
        <main className="mx-auto max-w-[78rem] px-6 py-20">
          <p className="eyebrow">The scan</p>
          <h1 className="mt-3 text-[length:var(--text-section)] leading-[var(--text-section-lead)] tracking-[var(--text-section-track)]">
            The scan has not been generated yet.
          </h1>
          <p className="mt-6 max-w-[36rem] text-slate">
            Run <code className="font-mono text-[0.8125rem]">python scripts/scan.py</code> against an
            indexed database. Nothing is shown here from memory.
          </p>
        </main>
      </>
    );
  }

  const { finding, indexed, method, standings } = scan;
  const share = finding.share_single_voice;

  return (
    <>
      <Nav />
      <main className="mx-auto max-w-[78rem] px-6 py-16">
        <p className="eyebrow">A finding about the registry, {scan.generated_at.slice(0, 10)}</p>
        <h1 className="mt-3 max-w-[20ch] text-[length:var(--text-hero)] leading-[var(--text-hero-lead)] tracking-[var(--text-hero-track)]">
          Most agents have one voice speaking for them.
        </h1>
        <p className="mt-8 max-w-[42rem] text-[length:var(--text-lead)] leading-[var(--text-lead-lead)] text-slate">
          {finding.reads}
        </p>

        <section className="mt-16 border-t border-seam pt-10">
          <p className="eyebrow">How many parties speak about one agent</p>
          <div className="mt-6 max-w-[42rem] space-y-3">
            {Object.entries(finding.voices_per_subject).map(([voices, count]) => {
              const width = (count / finding.subjects_with_feedback) * 100;
              return (
                <div key={voices} className="flex items-center gap-4">
                  <span className="w-24 shrink-0 font-mono text-[0.8125rem] tabular-nums text-slate">
                    {voices} {voices === "1" ? "party" : "parties"}
                  </span>
                  <span
                    className="h-3 rounded-stone bg-lapis"
                    style={{ width: `${Math.max(width, 2)}%` }}
                    aria-hidden
                  />
                  <span className="font-mono text-[0.8125rem] tabular-nums text-graphite">
                    {count}
                  </span>
                </div>
              );
            })}
          </div>
          <p className="mt-6 max-w-[42rem] text-slate">
            {share === null
              ? null
              : `${Math.round(share * 100)}% of subjects carrying feedback have exactly one party behind them. A layer that counts feedback cannot tell that apart from several parties agreeing, and the largest single claimant in this set spoke ${finding.largest_single_claimant_volume} times.`}
          </p>
        </section>

        <section className="mt-16 grid gap-12 border-t border-seam pt-10 md:grid-cols-2">
          <div>
            <p className="eyebrow">What Cairn read</p>
            <dl className="mt-4 space-y-2 font-mono text-[0.8125rem]">
              {Object.entries(indexed).map(([key, value]) => (
                <div key={key} className="flex justify-between gap-4 border-b border-seam pb-2">
                  <dt className="text-slate">{key.replace(/_/g, " ")}</dt>
                  <dd className="tabular-nums text-graphite">{value}</dd>
                </div>
              ))}
            </dl>
          </div>
          <div>
            <p className="eyebrow">What it judged</p>
            <dl className="mt-4 space-y-2 font-mono text-[0.8125rem]">
              {(["grounded", "thin", "suspect", "dormant"] as const).map((key) => (
                <div key={key} className="flex justify-between gap-4 border-b border-seam pb-2">
                  <dt className="text-slate">{key}</dt>
                  <dd className="tabular-nums text-graphite">{String(standings[key] ?? 0)}</dd>
                </div>
              ))}
            </dl>
            <p className="mt-4 max-w-[30rem] text-[0.9375rem] text-slate">
              {String(standings["suspect_note"] ?? "")}
            </p>
          </div>
        </section>

        <section className="mt-16 border-t border-seam pt-10">
          <p className="eyebrow">Check it yourself</p>
          <p className="mt-4 max-w-[42rem] text-slate">{method.note}</p>
          <div className="mt-6 max-w-[46rem] rounded-stone bg-basalt p-4">
            <pre className="overflow-x-auto">
              <code className="font-mono text-[0.8125rem] leading-relaxed text-chalk">
                {method.reproduce.join("\n")}
              </code>
            </pre>
          </div>
          <dl className="mt-6 max-w-[42rem] space-y-2 font-mono text-[0.8125rem]">
            <div className="flex flex-wrap justify-between gap-4 border-b border-seam pb-2">
              <dt className="text-slate">chain</dt>
              <dd className="text-graphite">{method.chain_id}</dd>
            </div>
            <div className="flex flex-wrap justify-between gap-4 border-b border-seam pb-2">
              <dt className="text-slate">blocks</dt>
              <dd className="text-graphite">{method.blocks}</dd>
            </div>
            <div className="flex flex-wrap justify-between gap-4 border-b border-seam pb-2">
              <dt className="text-slate">reputation registry</dt>
              <dd className="break-all text-graphite">{method.reputation_registry}</dd>
            </div>
            <div className="flex flex-wrap justify-between gap-4 border-b border-seam pb-2">
              <dt className="text-slate">raw data</dt>
              <dd>
                <a href="/scan.json" className="text-lapis underline underline-offset-[1px]">
                  /scan.json
                </a>
              </dd>
            </div>
          </dl>
        </section>

        <section className="mt-16 border-t border-seam pt-10">
          <p className="eyebrow">What this does not say</p>
          <p className="mt-4 max-w-[42rem] text-[length:var(--text-lead)] leading-[var(--text-lead-lead)] text-slate">
            No agent here is accused of anything. One party speaking repeatedly is not proof of bad
            conduct, and Cairn cannot support that claim from what it witnessed. What the record does
            support is narrower and more useful: a reputation layer built on counting feedback cannot
            distinguish agreement from repetition, and a reader assuming otherwise is assuming
            something the data does not carry.
          </p>
          <p className="mt-4 max-w-[42rem] text-slate">
            Any agent can request removal from the indexed set, and it is honoured.
          </p>
        </section>
      </main>
    </>
  );
}
