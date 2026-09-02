import { CairnIcon, CairnMark, type Standing } from "@/components/cairn-mark";

// Phase 0 scaffold check, not landing content. Replaced wholesale in phase 6.
// It exists so the mark, the tokens and the fonts can be verified rendering
// together before any page is built on top of them.

const STANDINGS: readonly Standing[] = ["default", "grounded", "thin", "suspect", "dormant"];

function Field({ label, tone, children }: {
  label: string;
  tone: "chalk" | "paper" | "basalt";
  children: React.ReactNode;
}) {
  const surface =
    tone === "basalt"
      ? "bg-basalt text-chalk"
      : tone === "paper"
        ? "bg-paper text-graphite border border-seam"
        : "bg-chalk text-graphite border border-seam";

  return (
    <section className={`${surface} rounded-stone p-8`}>
      <p className="eyebrow mb-6">{label}</p>
      {children}
    </section>
  );
}

export default function ScaffoldPage() {
  return (
    <main className="mx-auto max-w-5xl px-6 py-16">
      <p className="eyebrow">Phase 0 · scaffold</p>
      <h1 className="font-display mt-3 text-4xl text-graphite">CairnMark</h1>

      <div className="mt-12 space-y-6">
        <Field label="Standing · the keystone is the only stone that takes colour" tone="chalk">
          <ul className="flex flex-wrap gap-10">
            {STANDINGS.map((s) => (
              <li key={s} className="flex flex-col items-center gap-3">
                <CairnMark standing={s} width={64} height={64} />
                <span className="font-mono text-[0.6875rem] uppercase tracking-[0.13em] text-scree">
                  {s}
                </span>
              </li>
            ))}
          </ul>
        </Field>

        <Field label="Size ladder · below 20px the five-stone mark becomes the icon" tone="paper">
          <div className="flex flex-wrap items-end gap-x-10 gap-y-8">
            {[64, 40, 28, 20].map((px) => (
              <div key={px} className="flex flex-col items-center gap-3">
                <CairnMark standing="grounded" width={px} height={px} />
                <span className="font-mono text-[0.6875rem] text-scree">{px}px</span>
              </div>
            ))}
            <div className="flex flex-col items-center gap-3">
              <CairnIcon width={16} height={16} />
              <span className="font-mono text-[0.6875rem] text-scree">16px icon</span>
            </div>
          </div>
        </Field>

        <Field label="Wordmark lockup · nav scale, mark at 28px" tone="basalt">
          <div className="flex items-center" style={{ gap: "15px" }}>
            <CairnMark standing="grounded" width={28} height={28} />
            <span className="font-display text-2xl tracking-[-0.02em]">Cairn</span>
          </div>
        </Field>
      </div>
    </main>
  );
}
