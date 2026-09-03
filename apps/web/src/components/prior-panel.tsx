import type { VerdictPayload } from "@/lib/api";

/**
 * What Cairn believed before the most recent observation, and what moved.
 *
 * This is the screen that shows memory doing work rather than asserting that it
 * does: a verdict without a prior is a guess, and a verdict with one is a
 * position that changed for a reason it can name. Part 8 keeps it out of a
 * collapsible and above the fold on desktop, so it is neither.
 *
 * Nothing here is inferred. When Cairn has no prior it says so, because a first
 * verdict having no history is a fact about the record, not a gap to paper over.
 */
export function PriorPanel({
  verdict,
  observations,
}: {
  readonly verdict: VerdictPayload;
  readonly observations: number;
}) {
  const prior = verdict.prior;
  const hadPrior = prior != null && typeof prior.standing === "string";
  const priorBasis = Array.isArray(prior?.basis) ? prior.basis.length : null;

  const standingMoved = hadPrior && prior.standing !== verdict.standing;
  const confidenceMoved =
    hadPrior &&
    typeof prior.confidence === "number" &&
    typeof verdict.confidence === "number" &&
    prior.confidence !== verdict.confidence;
  const basisGrew = priorBasis !== null && observations > priorBasis;

  return (
    <section className="mt-16 border-t border-seam pt-10">
      <p className="eyebrow">The prior</p>

      {!hadPrior ? (
        <div className="mt-4 max-w-[48rem]">
          <p className="font-display text-[1.5rem] text-graphite">
            This is the first verdict Cairn has formed about this counterparty.
          </p>
          <p className="mt-2 text-slate">
            {prior?.from === "warm-entities"
              ? `There is no earlier verdict, but the dossier already held ${prior.n ?? 0} durable facts promoted from repeated behaviour, and the verdict cold-started from those.`
              : "There is nothing to compare it against yet. The next observation will move it, or fail to, and this panel will say which."}
          </p>
        </div>
      ) : (
        <>
          <div className="mt-4 grid gap-6 md:grid-cols-[58%_42%]">
            <div className="min-w-0">
              <p className="font-display text-[1.5rem] text-graphite">
                {standingMoved
                  ? `Cairn moved this counterparty from ${prior.standing} to ${verdict.standing}.`
                  : `Cairn still reads this counterparty as ${verdict.standing}.`}
              </p>
              <p className="mt-2 max-w-[36rem] text-slate">
                {standingMoved
                  ? "The standing changed because the observations behind it did. What follows is the arithmetic, not a summary of it."
                  : basisGrew
                    ? "The standing held, but the record behind it grew. A verdict that does not move under new evidence is a claim about the evidence, not an oversight."
                    : "Nothing new has been witnessed since the last evaluation, so there was nothing to revise."}
              </p>
            </div>

            <dl className="min-w-0 space-y-2 font-mono text-[0.8125rem]">
              <div className="flex justify-between gap-4 border-b border-seam pb-2">
                <dt className="text-slate">standing before</dt>
                <dd className="text-graphite">{prior.standing}</dd>
              </div>
              <div className="flex justify-between gap-4 border-b border-seam pb-2">
                <dt className="text-slate">standing now</dt>
                <dd className="text-graphite">{verdict.standing}</dd>
              </div>
              <div className="flex justify-between gap-4 border-b border-seam pb-2">
                <dt className="text-slate">confidence before</dt>
                <dd className="tabular-nums text-graphite">
                  {typeof prior.confidence === "number" ? prior.confidence.toFixed(2) : "-"}
                </dd>
              </div>
              <div className="flex justify-between gap-4 border-b border-seam pb-2">
                <dt className="text-slate">confidence now</dt>
                <dd className="tabular-nums text-graphite">
                  {verdict.confidence === null ? "-" : verdict.confidence.toFixed(2)}
                </dd>
              </div>
              <div className="flex justify-between gap-4 border-b border-seam pb-2">
                <dt className="text-slate">observations before</dt>
                <dd className="tabular-nums text-graphite">{priorBasis ?? "-"}</dd>
              </div>
              <div className="flex justify-between gap-4 border-b border-seam pb-2">
                <dt className="text-slate">observations now</dt>
                <dd className="tabular-nums text-graphite">{observations}</dd>
              </div>
            </dl>
          </div>

          {confidenceMoved || basisGrew ? (
            <p className="mt-6 max-w-[48rem] font-mono text-[0.8125rem] text-slate">
              {basisGrew
                ? `${observations - (priorBasis ?? 0)} observations were added since the prior was written.`
                : ""}
              {confidenceMoved && typeof prior.confidence === "number" && verdict.confidence !== null
                ? ` Confidence moved ${(verdict.confidence - prior.confidence > 0 ? "+" : "")}${(verdict.confidence - prior.confidence).toFixed(2)}.`
                : ""}
            </p>
          ) : null}
        </>
      )}
    </section>
  );
}
