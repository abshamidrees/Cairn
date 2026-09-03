import { Nav } from "@/components/shell";

/** No route 404s into nothing. This is a real page in the product's voice. */

export default function NotFound() {
  return (
    <>
      <Nav />
      <main className="mx-auto max-w-[78rem] px-6 py-20">
        <p className="eyebrow">Nothing here</p>
        <h1 className="mt-3 max-w-[20ch] text-[length:var(--text-section)] leading-[var(--text-section-lead)] tracking-[var(--text-section-track)]">
          Cairn has no page at this address.
        </h1>
        <p className="mt-6 max-w-[36rem] text-[length:var(--text-lead)] leading-[var(--text-lead-lead)] text-slate">
          This is a missing route, not a judgment about a counterparty. If you were looking up
          an agent, the dossier lives at /explorer/&lt;address&gt;.
        </p>
        <a
          href="/explorer"
          className="mt-8 inline-block rounded-pill bg-lapis px-5 py-2.5 font-mono text-[0.6875rem] uppercase tracking-[0.13em] text-chalk hover:bg-lapis-ink"
        >
          Look up an agent
        </a>
      </main>
    </>
  );
}
