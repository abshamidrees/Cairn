import { Nav } from "@/components/shell";
import { Skeleton } from "@/components/primitives";

/** A real loading state: the shape of a dossier, with nothing asserted in it. */

export default function Loading() {
  return (
    <>
      <Nav />
      <main className="mx-auto max-w-[78rem] px-6 py-12">
        <p className="eyebrow">Dossier</p>
        <p className="mt-4 font-mono text-[0.8125rem] text-slate">
          Reading the record.
        </p>
        <div className="mt-8 max-w-[30rem] space-y-3">
          <Skeleton width="60%" />
          <Skeleton width="85%" />
          <Skeleton width="45%" />
        </div>
      </main>
    </>
  );
}
