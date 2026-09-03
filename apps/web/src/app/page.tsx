import { StandingChip } from "@/components/primitives";
import { DossierStack } from "@/components/stack";
import { Integrate } from "@/components/integrate";
import { ClaimBasis, Footer, Nav } from "@/components/shell";
import { getStats, type Stats } from "@/lib/stats";

/**
 * The landing page.
 *
 * Every section is the claim / basis split: the claim on the left in Newsreader,
 * the basis on the right in mono, showing the observations, counts and hashes
 * the claim rests on. That repetition is the product's thesis rendered as a
 * grid, so nothing is asserted here without showing what it stands on.
 *
 * The motion budget is three moments, all of them in the hero Stack: it builds
 * on load, it accepts a new stone, and it falls when memory is switched off.
 * Nothing on this page animates on scroll.
 */

export const dynamic = "force-dynamic";

/** A counterparty in the indexed set with three independent claimants. */
const HERO_DOSSIER = "0x01f90369170c917a2c0e9d26d54c6a3a400984d3";

const TIER_MEANING: Readonly<Record<string, string>> = {
  HOT: "the live verdict, rewritten in place",
  WARM: "behaviour seen three times or more",
  COLD: "every observation, append-only",
  REFERENCE: "things that rarely change",
  ARCHIVE: "retired once its evidence aged out",
};

const STANDING_MEANING: readonly (readonly ["grounded" | "thin" | "suspect" | "dormant", string])[] =
  [
    ["grounded", "Three or more corroborated observations, and nothing contradicting itself."],
    ["thin", "Fewer than three corroborated observations. Cairn has too little to go on."],
    ["suspect", "The record contradicts itself, and Cairn can name the observations."],
    ["dormant", "Nothing witnessed inside the decay window."],
  ];

function Section({
  eyebrow,
  children,
}: {
  readonly eyebrow: string;
  readonly children: React.ReactNode;
}) {
  return (
    <section className="border-t border-seam py-20">
      <p className="eyebrow mb-10">{eyebrow}</p>
      {children}
    </section>
  );
}

function Claim({ children }: { readonly children: React.ReactNode }) {
  return (
    <h2 className="max-w-[18ch] text-[length:var(--text-section)] leading-[var(--text-section-lead)] tracking-[var(--text-section-track)]">
      {children}
    </h2>
  );
}

/* ---- Stat strip -------------------------------------------------------- */

const STATS: readonly (readonly [string, string])[] = [
  ["90.6%", "of ERC-8004 reviewers on Base show coordinated Sybil behaviour"],
  ["86.8%", "of rated agents have no valid feedback once it is removed"],
  ["$0.0027", "median cost to move an agent's reputation on Base"],
  ["0", "mainnet deployments of the Validation Registry"],
];

function StatStrip() {
  return (
    <section className="py-20">
      <div className="border-t border-seam">
        {STATS.map(([figure, label]) => (
          <div
            key={figure}
            className="flex flex-col gap-2 border-b border-seam py-6 sm:flex-row sm:items-baseline sm:justify-between sm:gap-8"
          >
            <span className="font-mono text-[clamp(2rem,4vw,3rem)] tabular-nums leading-none text-graphite">
              {figure}
            </span>
            <span className="max-w-[34rem] text-slate sm:text-right">{label}</span>
          </div>
        ))}
      </div>
      <p className="mt-4 font-mono text-[0.6875rem] text-slate">
        Source: Xiong et al., arXiv:2606.26028 · independently verifiable
      </p>
    </section>
  );
}

/* ---- 01 What Cairn holds ----------------------------------------------- */

function WhatCairnHolds({ stats }: { readonly stats: Stats }) {
  const examples = stats.observation_examples;
  if (examples.length === 0) return null;

  return (
    <Section eyebrow="THE RECORD">
      <ClaimBasis
        claim={
          <>
            <Claim>An observation is something Cairn watched happen.</Claim>
            <p className="mt-6 max-w-[34rem] text-[length:var(--text-lead)] leading-[var(--text-lead-lead)] text-slate">
              Not a rating somebody left. Each one is an event on Base that Cairn read from
              the registry itself and hashed, so the judgment it supports can be traced back to
              the transaction it came from.
            </p>
          </>
        }
        basisLabel={`the ${examples.length} kinds Cairn currently holds`}
        basis={
          <ul className="space-y-5">
            {examples.map((example) => (
              <li key={example.kind} className="border-b border-seam pb-4 last:border-b-0">
                <p className="text-graphite">{example.kind}</p>
                <p className="mt-1 text-slate">
                  {stats.observation_kinds[example.kind] ?? 0} held · {example.source}
                </p>
                <p className="mt-1 break-all text-slate">{example.content_hash}</p>
              </li>
            ))}
          </ul>
        }
      />
    </Section>
  );
}

/* ---- 02 The five tiers -------------------------------------------------- */

function FiveTiers({ stats }: { readonly stats: Stats }) {
  const order = ["HOT", "WARM", "COLD", "REFERENCE", "ARCHIVE"] as const;
  return (
    <Section eyebrow="HOW IT REMEMBERS">
      <ClaimBasis
        claim={
          <>
            <Claim>Memory is not one bucket.</Claim>
            <p className="mt-6 max-w-[34rem] text-[length:var(--text-lead)] leading-[var(--text-lead-lead)] text-slate">
              Where a fact lives is information. An observation seen once stays in the journal.
              Seen three times, Cairn promotes it to a durable fact and records the promotion.
              When the evidence behind it ages out, the fact is archived with a reason rather
              than deleted.
            </p>
          </>
        }
        basisLabel="rows Cairn holds right now"
        basis={
          <table className="w-full border-collapse">
            <thead>
              <tr>
                {["tier", "what lives there", "rows"].map((heading) => (
                  <th
                    key={heading}
                    scope="col"
                    className="border-b border-seam py-2 pr-4 text-left text-[0.6875rem] font-normal uppercase tracking-[0.13em] text-slate"
                  >
                    {heading}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {order.map((tier) => (
                <tr key={tier}>
                  <td className="border-b border-seam py-2 pr-4 text-graphite">{tier}</td>
                  <td className="border-b border-seam py-2 pr-4 text-slate">
                    {TIER_MEANING[tier]}
                  </td>
                  <td className="border-b border-seam py-2 tabular-nums text-slate">
                    {stats.tiers[tier] ?? 0}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        }
      />
    </Section>
  );
}

/* ---- 03 Reviewer weighting ---------------------------------------------- */

function ReviewerWeighting({ stats }: { readonly stats: Stats }) {
  const reviewer = stats.reviewer_example;
  // Without a real reviewer to point at there is no worked example, and an
  // invented one would be the exact failure this section is arguing against.
  if (reviewer === null) return null;

  return (
    <Section eyebrow="THE MISSING LAYER">
      <ClaimBasis
        claim={
          <>
            <Claim>We score the reviewers too.</Claim>
            <p className="mt-6 max-w-[34rem] text-[length:var(--text-lead)] leading-[var(--text-lead-lead)] text-slate">
              ERC-8004 defers this layer to a reviewer reputation system that, in its own words,
              does not yet exist. Cairn keeps a dossier on claimants as well as counterparties,
              and weighs a claim by whether anyone else independently witnessed the same agent.
              A claimant cannot corroborate itself.
            </p>
          </>
        }
        basisLabel="the busiest claimant in the indexed set"
        basis={
          <>
            <dl className="space-y-2">
            {(
              [
                ["address", reviewer.address],
                ["claims made", String(reviewer.claims)],
                ["independently corroborated", String(reviewer.corroborated)],
                ["weight carried", reviewer.weight.toFixed(2)],
                ["provisional", reviewer.provisional ? "yes" : "no"],
              ] as const
            ).map(([key, value]) => (
              <div key={key} className="flex justify-between gap-4 border-b border-seam pb-2">
                <dt className="text-slate">{key}</dt>
                <dd className="break-all text-right tabular-nums text-graphite">{value}</dd>
              </div>
            ))}
            </dl>
            <p className="pt-4 text-slate">
              {reviewer.claims} claims, none of them corroborated by another party. The weight
              stays at the neutral {reviewer.weight.toFixed(2)} and is returned flagged, because
              having spoken often is not evidence and Cairn will not treat it as any.
            </p>
          </>
        }
      />
    </Section>
  );
}

/* ---- 04 Standing --------------------------------------------------------- */

function Standing({ stats }: { readonly stats: Stats }) {
  return (
    <Section eyebrow="STANDING">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {STANDING_MEANING.map(([standing, definition]) => (
          <div key={standing} className="rounded-stone border border-seam bg-paper p-6">
            <StandingChip standing={standing} />
            <p className="mt-4 text-[0.9375rem] leading-relaxed text-slate">{definition}</p>
            <p className="mt-6 font-mono text-[1.5rem] tabular-nums text-graphite">
              {stats.standings[standing] ?? 0}
            </p>
            <p className="font-mono text-[0.6875rem] uppercase tracking-[0.13em] text-slate">
              of {stats.counterparties} indexed
            </p>
          </div>
        ))}
      </div>
    </Section>
  );
}

/* ---- 06 The one dark panel ----------------------------------------------- */

const DELETION_OUTPUT = `  memory ON      standing=grounded  confidence=0.84  basis=3  observations
  memory OFF     standing=thin      confidence=-     basis=0  observations
                 ↳ verdict engine returned NO_BASIS

  Cairn's core function is unavailable without the memory layer.  PASS`;

function DeletionPanel() {
  return (
    <section className="bg-basalt py-24">
      <div className="mx-auto flex max-w-[52rem] flex-col items-center gap-10 px-6 text-center">
        <h2 className="text-[length:var(--text-section)] leading-[var(--text-section-lead)] tracking-[var(--text-section-track)] text-chalk">
          Delete the memory and there is nothing left to ask.
        </h2>
        <div className="w-full text-left">
          <code className="block font-mono text-[0.8125rem] text-chalk">
            <span className="select-none text-scree">$ </span>
            python scripts/deletion_test.py
          </code>
          <pre className="mt-4 overflow-x-auto">
            <code className="font-mono text-[0.8125rem] leading-relaxed text-scree">
              {DELETION_OUTPUT}
            </code>
          </pre>
        </div>
        <a
          href="https://github.com/abshamidrees/cairn"
          className="rounded-pill border border-chalk/20 px-5 py-2 font-mono text-[0.6875rem] uppercase tracking-[0.13em] text-chalk transition-colors duration-[var(--dur-fast)] hover:border-chalk/50"
        >
          Read the source
        </a>
      </div>
    </section>
  );
}

/* ---- the page ------------------------------------------------------------ */

export default async function LandingPage() {
  const stats = await getStats();

  return (
    <>
      <Nav standing="grounded" observations={stats?.observations ?? null} />

      <main>
        {/* Hero */}
        <section className="mx-auto max-w-[78rem] px-6 py-20 lg:py-28">
          <div className="grid gap-16 lg:grid-cols-[1fr_26rem] lg:gap-20">
            <div>
              <h1 className="text-[length:var(--text-hero)] leading-[var(--text-hero-lead)] tracking-[var(--text-hero-track)]">
                Agents can&rsquo;t
                <br />
                check who they&rsquo;re
                <br />
                about to pay.
              </h1>
              <p className="mt-8 max-w-[34rem] text-[length:var(--text-lead)] leading-[var(--text-lead-lead)] text-slate">
                Cairn keeps the record. Every verdict points at the observations it came from.
              </p>
              <div className="mt-10 flex flex-wrap gap-3">
                <a
                  href="/explorer"
                  className="rounded-pill bg-lapis px-5 py-2.5 font-mono text-[0.6875rem] uppercase tracking-[0.13em] text-chalk transition-colors duration-[var(--dur-fast)] hover:bg-lapis-ink"
                >
                  Look up an agent
                </a>
                <a
                  href="/docs"
                  className="rounded-pill border border-seam px-5 py-2.5 font-mono text-[0.6875rem] uppercase tracking-[0.13em] text-graphite transition-colors duration-[var(--dur-fast)] hover:border-graphite/30"
                >
                  Read the memory note
                </a>
              </div>
            </div>

            {/* The Stack replaces the dashboard screenshot every competitor puts
                here: the characteristic thing about Cairn is that it can show
                you its own basis, so that is what the hero shows. */}
            <div>
              <DossierStack address={HERO_DOSSIER} />
            </div>
          </div>
        </section>

        <div className="mx-auto max-w-[78rem] px-6">
          <StatStrip />
          {stats ? <WhatCairnHolds stats={stats} /> : null}
          {stats ? <FiveTiers stats={stats} /> : null}
          {stats ? <ReviewerWeighting stats={stats} /> : null}
          {stats ? <Standing stats={stats} /> : null}

          <Section eyebrow="INTEGRATE">
            <ClaimBasis
              claim={
                <>
                  <Claim>Ask before you pay.</Claim>
                  <p className="mt-6 max-w-[34rem] text-[length:var(--text-lead)] leading-[var(--text-lead-lead)] text-slate">
                    One call, before the escrow is funded. If Cairn has not watched the
                    counterparty do what it said it would, it says so, and the basis comes back
                    with the answer.
                  </p>
                </>
              }
              basisLabel="the call, and the branch"
              basis={<Integrate />}
            />
          </Section>
        </div>

        <DeletionPanel />

        {/* 07 CTA */}
        <section className="mx-auto max-w-[78rem] px-6 py-24 text-center">
          <h2 className="text-[length:var(--text-section)] leading-[var(--text-section-lead)] tracking-[var(--text-section-track)]">
            Look up an agent you were about to pay.
          </h2>
          <div className="mt-10">
            <a
              href="/explorer"
              className="rounded-pill bg-lapis px-6 py-3 font-mono text-[0.6875rem] uppercase tracking-[0.13em] text-chalk transition-colors duration-[var(--dur-fast)] hover:bg-lapis-ink"
            >
              Look up an agent
            </a>
          </div>
          <p className="mt-6 font-mono text-[0.6875rem] text-scree">
            Free while in beta · no wallet connection required to read
          </p>
        </section>
      </main>

      <Footer
        ticker={(stats?.recent ?? []).map((row, i) => ({
          id: `${row.at}-${i}`,
          at: row.at.slice(11, 19),
          kind: row.kind,
          counterparty: `${row.counterparty.slice(8, 14)}…${row.counterparty.slice(-4)}`,
          standing: "",
        }))}
      />
    </>
  );
}
