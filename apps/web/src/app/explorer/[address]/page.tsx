import { notFound } from "next/navigation";

import { StandingChip, VerdictLine } from "@/components/primitives";
import { Nav } from "@/components/shell";
import { DossierStack } from "@/components/stack";
import { apiBase, type Dossier } from "@/lib/api";

/**
 * One counterparty's dossier.
 *
 * The page is the claim / basis split at full height: the Stack on the left,
 * the observations it is built from on the right, and beneath them what Cairn
 * published about this agent on Base. An attestation is only shown when one
 * exists; there is no placeholder row for a transaction that was never sent.
 */

export const dynamic = "force-dynamic";

async function getDossier(address: string): Promise<Dossier | null> {
  try {
    const response = await fetch(`${apiBase()}/v1/dossier/${address}`, { cache: "no-store" });
    if (!response.ok) return null;
    return (await response.json()) as Dossier;
  } catch {
    return null;
  }
}

function short(value: string): string {
  return value.length > 18 ? `${value.slice(0, 10)}…${value.slice(-8)}` : value;
}

export default async function DossierPage({
  params,
}: {
  params: Promise<{ address: string }>;
}) {
  const { address } = await params;
  if (!/^0x[0-9a-fA-F]{40}$/.test(address)) notFound();

  const dossier = await getDossier(address);

  return (
    <>
      <Nav standing={dossier?.verdict.standing ?? "default"} />

      <main className="mx-auto max-w-[78rem] px-6 py-12">
        <p className="eyebrow">Dossier</p>
        <h1 className="mt-3 break-all font-mono text-[1.25rem] text-graphite">{address}</h1>

        {dossier === null ? (
          <div className="mt-10 rounded-stone border border-oxide/30 bg-paper p-8">
            <p className="font-mono text-[0.6875rem] uppercase tracking-[0.13em] text-oxide">
              could not read the record
            </p>
            <p className="mt-3 max-w-[36rem] text-slate">
              Cairn could not reach its own memory. This is a failure to answer, not an
              answer: nothing here should be read as a judgment about this counterparty.
            </p>
          </div>
        ) : (
          <>
            <div className="mt-6 flex flex-wrap items-center gap-4">
              <StandingChip standing={dossier.verdict.standing} />
              <VerdictLine
                standing={dossier.verdict.standing}
                confidence={dossier.verdict.confidence}
                noBasis={dossier.verdict.no_basis}
              />
            </div>

            <div className="mt-12 grid gap-12 lg:grid-cols-[26rem_1fr]">
              <DossierStack address={address} />

              <div className="min-w-0">
                <p className="font-mono text-[0.6875rem] uppercase tracking-[0.13em] text-slate">
                  the basis, {dossier.counts.observations} observations
                </p>
                {dossier.counts.observations === 0 ? (
                  <p className="mt-4 max-w-[36rem] text-slate">
                    No observations. Cairn has never watched this agent do anything, which is
                    not the same as having watched it do something wrong.
                  </p>
                ) : (
                  <div className="mt-4 overflow-x-auto">
                    <table className="w-full border-collapse font-mono text-[0.8125rem]">
                      <thead>
                        <tr>
                          {["kind", "witnessed", "grounding", "hash"].map((h) => (
                            <th
                              key={h}
                              scope="col"
                              className="border-b border-seam py-2 pr-6 text-left text-[0.6875rem] font-normal uppercase tracking-[0.13em] text-slate"
                            >
                              {h}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {dossier.stones.COLD.map((stone) => (
                          <tr key={stone.id}>
                            <td className="border-b border-seam py-2 pr-6 text-graphite">
                              {stone.label}
                            </td>
                            <td className="border-b border-seam py-2 pr-6 tabular-nums text-slate">
                              {String(stone.detail["occurred_at"] ?? "").slice(0, 10)}
                            </td>
                            <td className="border-b border-seam py-2 pr-6 text-slate">
                              {stone.grounding}
                            </td>
                            <td className="border-b border-seam py-2 text-slate">
                              {short(String(stone.detail["content_hash"] ?? ""))}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>

            {/* Published on Base, or plainly not yet. */}
            <section className="mt-16 border-t border-seam pt-10">
              <p className="eyebrow">Published on Base</p>
              {dossier.attestation === null ? (
                <p className="mt-4 max-w-[46rem] text-slate">
                  This verdict has not been published on chain. Cairn attests a verdict only
                  when it carries a basis, so nothing is written for a counterparty it has
                  nothing on.
                </p>
              ) : (
                <dl className="mt-4 space-y-2 font-mono text-[0.8125rem]">
                  <div className="flex flex-wrap justify-between gap-4 border-b border-seam pb-2">
                    <dt className="text-slate">transaction</dt>
                    <dd>
                      <a
                        href={dossier.attestation.explorer_url}
                        className="break-all text-lapis underline underline-offset-[1px]"
                        rel="noreferrer"
                      >
                        {dossier.attestation.tx_hash}
                      </a>
                    </dd>
                  </div>
                  <div className="flex flex-wrap justify-between gap-4 border-b border-seam pb-2">
                    <dt className="text-slate">contract</dt>
                    <dd className="break-all text-graphite">
                      {dossier.attestation.contract ?? "unknown"}
                    </dd>
                  </div>
                  <div className="flex flex-wrap justify-between gap-4 border-b border-seam pb-2">
                    <dt className="text-slate">chain</dt>
                    <dd className="tabular-nums text-graphite">
                      {dossier.attestation.chain_id ?? "unknown"}
                    </dd>
                  </div>
                </dl>
              )}
            </section>
          </>
        )}
      </main>
    </>
  );
}
