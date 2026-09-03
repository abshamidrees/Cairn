"use client";

import { useState } from "react";

/** One field, mono, the same destinations the palette resolves. */

const ADDRESS = /^0x[0-9a-fA-F]{40}$/;

export function ExplorerSearch() {
  const [query, setQuery] = useState("");
  const [error, setError] = useState<string | null>(null);

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        const value = query.trim();
        const reviewer = value.startsWith("rv:") || value.startsWith("@");
        const address = value.replace(/^rv:/, "").replace(/^@/, "").replace(/^cp:base:/, "");
        if (!ADDRESS.test(address)) {
          setError("Cairn looks up a 40 character address beginning 0x.");
          return;
        }
        window.location.href = reviewer ? `/explorer/reviewer/${address}` : `/explorer/${address}`;
      }}
    >
      <input
        value={query}
        onChange={(event) => {
          setQuery(event.target.value);
          setError(null);
        }}
        placeholder="agent id, wallet address, or ACP handle"
        aria-label="agent id, wallet address, or ACP handle"
        className="w-full rounded-stone border border-seam bg-paper px-4 py-3 font-mono text-[0.8125rem] text-graphite placeholder:text-scree focus:border-graphite/30 focus:outline-none"
      />
      {error ? <p className="mt-2 font-mono text-[0.6875rem] text-oxide">{error}</p> : null}
    </form>
  );
}
