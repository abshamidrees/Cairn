"use client";

/** A real error state. It says what failed, and refuses to imply a verdict. */

export default function DossierError({ reset }: { error: Error; reset: () => void }) {
  return (
    <main className="mx-auto max-w-[78rem] px-6 py-20">
      <p className="font-mono text-[0.6875rem] uppercase tracking-[0.13em] text-oxide">
        could not read the record
      </p>
      <h1 className="mt-3 max-w-[22ch] text-[length:var(--text-section)] leading-[var(--text-section-lead)] tracking-[var(--text-section-track)]">
        Cairn stopped before it could answer.
      </h1>
      <p className="mt-6 max-w-[36rem] text-[length:var(--text-lead)] leading-[var(--text-lead-lead)] text-slate">
        Nothing on this screen should be read as a judgment about this counterparty, in either
        direction. A failure to answer is not an answer.
      </p>
      <button
        type="button"
        onClick={reset}
        className="mt-8 rounded-pill border border-seam px-5 py-2.5 font-mono text-[0.6875rem] uppercase tracking-[0.13em] text-graphite hover:border-graphite/30"
      >
        Try again
      </button>
    </main>
  );
}
