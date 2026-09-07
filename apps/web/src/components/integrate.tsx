"use client";

import { useState } from "react";

/**
 * The four lines that decide whether to pay.
 *
 * There is no install line because there is no published package: the API is
 * the integration surface, and the CLI tab calls it exactly as written.
 *
 * Both tabs show the same decision: ask Firsthand what it has witnessed, and refuse
 * to fund if the answer is not grounded.
 */

const SAMPLES: readonly { readonly label: string; readonly code: string }[] = [
  {
    label: "Python",
    code: `verdict = firsthand.lookup("0x01f9…84d3")
if verdict.standing != "grounded":
    raise Refuse(verdict.basis)      # nothing witnessed, so do not pay
escrow.fund(job_id)`,
  },
  {
    label: "CLI",
    code: `curl -s "$FIRSTHAND/v1/lookup/0x01f9…84d3" \\
  | jq -e '.standing == "grounded"' \\
  && acp client fund --job-id 42 --chain-id 8453 \\
  || echo "no grounded record, holding the escrow"`,
  },
];

export function Integrate() {
  const [active, setActive] = useState(0);
  const sample = SAMPLES[active] ?? SAMPLES[0];

  return (
    <div className="flex flex-col gap-4">
      <div className="rounded-stone bg-basalt">
        <div
          role="tablist"
          aria-label="Integration language"
          className="flex gap-1 border-b border-chalk/10 px-2 pt-2"
        >
          {SAMPLES.map((entry, index) => (
            <button
              key={entry.label}
              type="button"
              role="tab"
              aria-selected={index === active}
              onClick={() => setActive(index)}
              className={`rounded-stone px-3 py-1.5 font-mono text-[0.6875rem] uppercase tracking-[0.13em] transition-colors duration-[var(--dur-fast)] ${
                index === active ? "bg-chalk/10 text-chalk" : "text-scree hover:text-chalk"
              }`}
            >
              {entry.label}
            </button>
          ))}
        </div>
        <pre className="overflow-x-auto p-4">
          <code className="font-mono text-[0.8125rem] leading-relaxed text-chalk">
            {sample?.code}
          </code>
        </pre>
      </div>
    </div>
  );
}
