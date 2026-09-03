"use client";

import { useState, type ReactNode } from "react";

/** Code on basalt, with a copy button. Copying is a state change. */
export function CodeBlock({ children }: { readonly children: ReactNode }) {
  const [copied, setCopied] = useState(false);

  return (
    <div className="relative mt-6 max-w-[46rem] rounded-stone bg-basalt">
      <button
        type="button"
        onClick={(event) => {
          const pre = event.currentTarget.parentElement?.querySelector("pre");
          const text = pre?.textContent ?? "";
          void navigator.clipboard.writeText(text).then(() => {
            setCopied(true);
            window.setTimeout(() => setCopied(false), 1200);
          });
        }}
        className="absolute right-2 top-2 rounded-stone border border-chalk/20 px-2 py-1 font-mono text-[0.6875rem] uppercase tracking-[0.13em] text-scree transition-colors duration-[var(--dur-fast)] hover:text-chalk"
      >
        {copied ? "copied" : "copy"}
      </button>
      <pre className="overflow-x-auto p-4 pr-16">
        <code className="font-mono text-[0.8125rem] leading-relaxed text-chalk">{children}</code>
      </pre>
    </div>
  );
}
