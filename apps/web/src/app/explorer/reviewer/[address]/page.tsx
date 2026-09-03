import { Nav } from "@/components/shell";
import { apiBase } from "@/lib/api";

/**
 * A claimant's own dossier.
 *
 * The layer ERC-8004 says is missing, rendered: how much a party has said, how
 * much of it anyone else independently witnessed, and the weight that produces.
 * A claimant cannot corroborate itself, so a long record of unwitnessed claims
 * carries the neutral weight rather than a large one.
 */

export const dynamic = "force-dynamic";

const ADDRESS = /^0x[0-9a-fA-F]{40}$/;

interface Weight {
  readonly address: string;
  readonly claims: number;
  readonly corroborated: number;
  readonly contradicted?: number;
  readonly weight: number;
  readonly provisional: boolean;
}

interface ReviewerPayload {
  readonly reviewer: string;
  readonly address: string;
  readonly known: boolean;
  readonly claims: readonly { readonly id: string; readonly body?: Record<string, unknown> }[];
  readonly weight: Weight | null;
  readonly generated_at: string | null;
}

async function getReviewer(address: string): Promise<ReviewerPayload | "unreachable"> {
  try {
    const response = await fetch(`${apiBase()}/v1/reviewer/${address}`, { cache: "no-store" });
    if (!response.ok) return "unreachable";
    return (await response.json()) as ReviewerPayload;
  } catch {
    return "unreachable";
  }
}

function Frame({ address, children }: { address: string; children: React.ReactNode }) {
  return (
    <>
      <Nav />
      <main className="mx-auto max-w-[78rem] px-6 py-12">
        <p className="eyebrow">Claimant</p>
        <h1 className="mt-3 break-all font-mono text-[1.25rem] text-graphite">{address}</h1>
        {children}
      </main>
    </>
  );
}

export default async function ReviewerPage({
  params,
}: {
  params: Promise<{ address: string }>;
}) {
  const { address } = await params;

  if (!ADDRESS.test(address)) {
    return (
      <Frame address={address}>
        <div className="mt-8 rounded-stone border border-seam bg-paper p-8">
          <p className="font-display text-[1.5rem] text-graphite">
            That is not an address Cairn can look up.
          </p>
          <p className="mt-2 max-w-[36rem] text-slate">
            A claimant is a 40 character address beginning 0x.
          </p>
        </div>
      </Frame>
    );
  }

  const found = await getReviewer(address);

  if (found === "unreachable") {
    return (
      <Frame address={address}>
        <div className="mt-8 rounded-stone border border-oxide/30 bg-paper p-8">
          <p className="font-mono text-[0.6875rem] uppercase tracking-[0.13em] text-oxide">
            could not read the record
          </p>
          <p className="mt-3 font-display text-[1.5rem] text-graphite">
            Cairn could not reach its own memory.
          </p>
          <p className="mt-2 max-w-[36rem] text-slate">
            This is a failure to answer, not an answer. Nothing here should be read as a
            judgment about this claimant.
          </p>
        </div>
      </Frame>
    );
  }

  if (!found.known) {
    return (
      <Frame address={address}>
        <div className="mt-8 rounded-stone border border-seam bg-paper p-8">
          <p className="font-display text-[1.5rem] text-graphite">
            No claims. Cairn has never watched this address say anything about anyone.
          </p>
          <p className="mt-2 max-w-[40rem] text-slate">
            Claimants enter the record by leaving feedback on an agent in the ERC-8004
            reputation registry. When this one does, the claim lands in its own dossier and a
            weight follows from whether anybody else witnessed the same agent.
          </p>
          <a
            href="/explorer"
            className="mt-5 inline-block rounded-pill border border-seam px-5 py-2 font-mono text-[0.6875rem] uppercase tracking-[0.13em] text-graphite hover:border-graphite/30"
          >
            Back to the explorer
          </a>
        </div>
      </Frame>
    );
  }

  const weight = found.weight;
  const rows: readonly (readonly [string, string])[] = weight
    ? [
        ["claims made", String(weight.claims)],
        ["independently corroborated", String(weight.corroborated)],
        ["contradicted by the record", String(weight.contradicted ?? 0)],
        ["weight carried", weight.weight.toFixed(2)],
        ["provisional", weight.provisional ? "yes" : "no"],
      ]
    : [];

  return (
    <Frame address={address}>
      <div className="mt-10 grid gap-12 md:grid-cols-[58%_42%]">
        <div className="min-w-0">
          <h2 className="max-w-[18ch] text-[length:var(--text-section)] leading-[var(--text-section-lead)] tracking-[var(--text-section-track)]">
            {weight && weight.corroborated === 0 && weight.claims > 0
              ? "Nothing this claimant said was witnessed by anyone else."
              : "What this claimant said, and who else saw it."}
          </h2>
          <p className="mt-6 max-w-[34rem] text-[length:var(--text-lead)] leading-[var(--text-lead-lead)] text-slate">
            A claim counts as corroborated when a different claimant left a record about the
            same agent. Nobody corroborates themselves, so speaking often is not evidence and
            Cairn does not treat it as any. Below the threshold a claimant carries the neutral
            weight, returned flagged, because a short record is not a bad one.
          </p>
          {weight?.provisional ? (
            <p className="mt-6 font-mono text-[0.8125rem] text-slate">
              This weight is provisional and the API returns it flagged.
            </p>
          ) : null}
        </div>

        <div className="min-w-0 border-l-0 border-seam md:border-l md:pl-8">
          <p className="font-mono text-[0.6875rem] uppercase tracking-[0.13em] text-slate">
            measured over the whole indexed set
          </p>
          {weight === null ? (
            <p className="mt-4 font-mono text-[0.8125rem] text-slate">
              This claimant has {found.claims.length} claims in the journal, but no weight has
              been computed yet. Weights are measured over the whole indexed set by
              scripts/summarise.py, not per request.
            </p>
          ) : (
            <dl className="mt-4 space-y-2 font-mono text-[0.8125rem]">
              {rows.map(([key, value]) => (
                <div key={key} className="flex justify-between gap-4 border-b border-seam pb-2">
                  <dt className="text-slate">{key}</dt>
                  <dd className="tabular-nums text-graphite">{value}</dd>
                </div>
              ))}
            </dl>
          )}
        </div>
      </div>

      <section className="mt-16 border-t border-seam pt-10">
        <p className="eyebrow">The claims</p>
        {found.claims.length === 0 ? (
          <p className="mt-4 text-slate">No claims held.</p>
        ) : (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full border-collapse font-mono text-[0.8125rem]">
              <thead>
                <tr>
                  {["about agent", "tagged", "source"].map((h) => (
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
                {found.claims.slice(0, 25).map((claim) => {
                  const body = claim.body ?? {};
                  const tx = body["tx_hash"];
                  return (
                    <tr key={claim.id}>
                      <td className="border-b border-seam py-2 pr-6 tabular-nums text-graphite">
                        {String(body["agent_id"] ?? "")}
                      </td>
                      <td className="border-b border-seam py-2 pr-6 text-slate">
                        {String(body["tag1"] ?? "untagged")}
                      </td>
                      <td className="border-b border-seam py-2 text-slate">
                        {typeof tx === "string" && tx ? (
                          <a
                            href={`https://basescan.org/tx/${tx}`}
                            rel="noreferrer"
                            className="text-lapis underline underline-offset-[1px]"
                          >
                            {tx.slice(0, 10)}…
                          </a>
                        ) : (
                          "-"
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            {found.claims.length > 25 ? (
              <p className="mt-3 font-mono text-[0.6875rem] text-slate">
                Showing 25 of {found.claims.length}.
              </p>
            ) : null}
          </div>
        )}
      </section>
    </Frame>
  );
}
