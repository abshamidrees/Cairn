"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { apiBase } from "@/lib/api";

/**
 * Cmd+K anywhere on the site.
 *
 * Recent lookups come from `/v1/recent`, which reads them out of Cairn's own
 * dossier rather than localStorage. Part 8 asks for them to be persisted in
 * memory, and this is the one place where following that literally also makes
 * the demo better: the list survives a different browser, because it was never
 * in the browser.
 *
 * Opening the palette is a state change, not a motion moment. It appears.
 */

const ADDRESS = /^0x[0-9a-fA-F]{40}$/;

function destinationFor(query: string): string | null {
  const value = query.trim();
  if (!value) return null;
  const reviewer = value.startsWith("rv:") || value.startsWith("@");
  const address = value.replace(/^rv:/, "").replace(/^@/, "").replace(/^cp:base:/, "");
  if (!ADDRESS.test(address)) return null;
  return reviewer ? `/explorer/reviewer/${address}` : `/explorer/${address}`;
}

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [recent, setRecent] = useState<readonly string[]>([]);
  const inputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setOpen((was) => !was);
      }
      if (event.key === "Escape") setOpen(false);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    if (!open) return;
    inputRef.current?.focus();
    const controller = new AbortController();
    void (async () => {
      try {
        const response = await fetch(`${apiBase()}/v1/recent`, { signal: controller.signal });
        if (!response.ok) return;
        const body = (await response.json()) as { recent?: readonly string[] };
        setRecent(body.recent ?? []);
      } catch {
        // The palette still works without a history. Nothing is claimed here.
        setRecent([]);
      }
    })();
    return () => controller.abort();
  }, [open]);

  const go = useCallback((destination: string) => {
    setOpen(false);
    window.location.href = destination;
  }, []);

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="font-mono text-[0.6875rem] uppercase tracking-[0.13em] text-slate hover:text-graphite"
        aria-label="Search, or press Command K"
      >
        ⌘K
      </button>
    );
  }

  const destination = destinationFor(query);

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Look up an agent"
      className="fixed inset-0 z-50 flex items-start justify-center bg-basalt/40 px-6 pt-[12vh]"
      onClick={() => setOpen(false)}
    >
      <div
        className="w-full max-w-[40rem] rounded-stone border border-seam bg-paper"
        onClick={(event) => event.stopPropagation()}
      >
        <form
          onSubmit={(event) => {
            event.preventDefault();
            if (destination) go(destination);
          }}
        >
          <input
            ref={inputRef}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="agent id, wallet address, or ACP handle"
            aria-label="agent id, wallet address, or ACP handle"
            className="w-full bg-transparent px-5 py-4 font-mono text-[0.8125rem] text-graphite placeholder:text-scree focus:outline-none"
          />
        </form>

        <div className="border-t border-seam px-5 py-3">
          {query.trim() && !destination ? (
            <p className="font-mono text-[0.6875rem] text-slate">
              Not an address Cairn can look up. Paste a 0x address, or prefix rv: for a claimant.
            </p>
          ) : recent.length > 0 ? (
            <>
              <p className="font-mono text-[0.6875rem] uppercase tracking-[0.13em] text-slate">
                recent, from Cairn&rsquo;s own record
              </p>
              <ul className="mt-2 space-y-1">
                {recent.map((tenant) => {
                  const address = tenant.replace(/^cp:base:/, "");
                  return (
                    <li key={tenant}>
                      <button
                        type="button"
                        onClick={() => go(`/explorer/${address}`)}
                        className="w-full break-all text-left font-mono text-[0.8125rem] text-lapis hover:underline"
                      >
                        {address}
                      </button>
                    </li>
                  );
                })}
              </ul>
            </>
          ) : (
            <p className="font-mono text-[0.6875rem] text-slate">
              Nothing looked up yet. The first search will show here.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
