import { StandingChip } from "@/components/primitives";
import { Nav } from "@/components/shell";
import { DossierStack } from "@/components/stack";
import { BasisTable } from "@/components/basis-table";
import { PriorPanel } from "@/components/prior-panel";
import { apiBase, type Dossier } from "@/lib/api";

/**
 * One counterparty's dossier: the product, not a marketing page.
 *
 * The header carries the identity, the standing, the verdict and the timestamp
 * of the most recent observation. The Stack is on the left at full height, the
 * observations it was built from on the right, and the prior panel beneath
 * them, which is the screen that shows memory doing work rather than asserting
 * that it does.
 *
 * There is no 404 here. An address Cairn has never seen is a real answer, and a
 * malformed one is a mistake worth explaining rather than a dead end.
 */

export const dynamic = "force-dynamic";

const ADDRESS = /^0x[0-9a-fA-F]{40}$/;

async function getDossier(address: string): Promise<Dossier | "unreachable"> {
  try {
    const response = await fetch(`${apiBase()}/v1/dossier/${address}`, { cache: "no-store" });
    if (!response.ok) return "unreachable";
    return (await response.json()) as Dossier;
  } catch {
    return "unreachable";
  }
}

function Frame({ address, children }: { address: string; children: React.ReactNode }) {
  return (
    <>
      <Nav />
      <main className="mx-auto max-w-[78rem] px-6 py-12">
        <p className="eyebrow">Dossier</p>
        <h1 className="mt-3 break-all font-mono text-[1.25rem] text-graphite">{address}</h1>
        {children}
      </main>
    </>
  );
}

export default async function DossierPage({
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
            A counterparty is a 40 character address beginning 0x. Cairn has not judged this
            one either way, because it cannot tell what it refers to.
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

  const dossier = await getDossier(address);

  if (dossier === "unreachable") {
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
            This is a failure to answer, not an answer. Nothing on this screen should be read
            as a judgment about this counterparty, in either direction.
          </p>
        </div>
      </Frame>
    );
  }

  const newest = dossier.stones.COLD.reduce<string>((latest, stone) => {
    const at = String(stone.detail["occurred_at"] ?? "");
    return at > latest ? at : latest;
  }, "");

  return (
    <Frame address={address}>
      <div className="mt-6 flex flex-wrap items-center gap-x-5 gap-y-3">
        <StandingChip standing={dossier.verdict.standing} />
        <span className="verdict text-[1.25rem]">
          {dossier.verdict.no_basis
            ? "no basis"
            : dossier.verdict.standing === "grounded"
              ? "Cairn has watched this counterparty do what it said it would."
              : dossier.verdict.standing === "suspect"
                ? "Cairn's own record contradicts a claim about this counterparty."
                : dossier.verdict.standing === "dormant"
                  ? "Cairn has not witnessed this counterparty in some time."
                  : "Cairn has too little to go on."}
        </span>
        <span className="font-mono text-[0.8125rem] tabular-nums text-slate">
          {dossier.verdict.confidence === null
            ? "confidence -"
            : `confidence ${Math.round(dossier.verdict.confidence * 100)}%`}
        </span>
        {newest ? (
          <span className="font-mono text-[0.6875rem] uppercase tracking-[0.13em] text-slate">
            last observed {newest.slice(0, 10)}
          </span>
        ) : null}
      </div>

      {dossier.counts.observations === 0 ? (
        <div className="mt-10 rounded-stone border border-seam bg-paper p-8">
          <p className="font-display text-[1.5rem] text-graphite">
            No observations. Cairn has never watched this agent do anything.
          </p>
          <p className="mt-2 max-w-[40rem] text-slate">
            That is not the same as having watched it do something wrong. Once this
            counterparty settles an escrow, is registered, or is written about by someone
            Cairn indexes, the event lands in the journal below and a verdict follows from it.
          </p>
          <a
            href="/docs"
            className="mt-5 inline-block rounded-pill bg-lapis px-5 py-2 font-mono text-[0.6875rem] uppercase tracking-[0.13em] text-chalk hover:bg-lapis-ink"
          >
            How Cairn starts watching
          </a>
        </div>
      ) : (
        <>
          <div className="mt-10 grid gap-12 lg:grid-cols-[26rem_1fr]">
            <DossierStack address={address} />
            <BasisTable stones={dossier.stones.COLD} />
          </div>

          <PriorPanel verdict={dossier.verdict} observations={dossier.counts.observations} />
        </>
      )}

      <section className="mt-16 border-t border-seam pt-10">
        <p className="eyebrow">Published on Base</p>
        {dossier.attestation === null ? (
          <p className="mt-4 max-w-[46rem] text-slate">
            This verdict has not been published on chain. Cairn attests a verdict only when it
            carries a basis, so nothing is written for a counterparty it has nothing on.
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
              <dd className="break-all text-graphite">{dossier.attestation.contract ?? "unknown"}</dd>
            </div>
          </dl>
        )}
      </section>
    </Frame>
  );
}
