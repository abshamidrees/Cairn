"use client";

import { useState } from "react";

/**
 * The install line and the four lines that use it.
 *
 * Both tabs show the same decision: ask Cairn what it has witnessed, and refuse
 * to fund if the answer is not grounded. Copying is a state change, not a
 * motion moment: the label swaps and nothing moves.
 */

const INSTALL = "pip install cairn";

const SAMPLES: readonly { readonly label: string; readonly code: string }[] = [
  {
    label: "Python",
    code: `verdict = cairn.lookup("0x01f9…84d3")
if verdict.standing != "grounded":
    raise Refuse(verdict.basis)      # nothing witnessed, so do not pay
escrow.fund(job_id)`,
  },
  {
    label: "CLI",
    code: `curl -s "$CAIRN/v1/lookup/0x01f9…84d3" \\
  | jq -e '.standing == "grounded"' \\
  && acp client fund --job-id 42 --chain-id 8453 \\
  || echo "no grounded record, holding the escrow"`,
  },
];

function CopyButton({ value }: { readonly value: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      type="button"
      onClick={() => {
        void navigator.clipboard.writeText(value).then(() => {
          setCopied(true);
          window.setTimeout(() => setCopied(false), 1200);
        });
      }}
      className="rounded-stone border border-chalk/20 px-2 py-1 font-mono text-[0.6875rem] uppercase tracking-[0.13em] text-scree transition-colors duration-[var(--dur-fast)] hover:text-chalk"
    >
      {copied ? "copied" : "copy"}
    </button>
  );
}

export function Integrate() {
  const [active, setActive] = useState(0);
  const sample = SAMPLES[active] ?? SAMPLES[0];

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between gap-4 rounded-stone bg-basalt px-4 py-3">
        <code className="font-mono text-[0.8125rem] text-chalk">
          <span className="select-none text-scree">$ </span>
          {INSTALL}
        </code>
        <CopyButton value={INSTALL} />
      </div>

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
