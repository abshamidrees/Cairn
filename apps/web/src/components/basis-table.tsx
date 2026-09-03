"use client";

import { useMemo, useState } from "react";

import type { Stone } from "@/lib/api";

/**
 * The basis: every observation the verdict rests on, sortable, each row
 * followable back to the transaction Cairn witnessed it in.
 *
 * Sorting is a state change, not a motion moment. The rows reorder.
 */

type Column = "kind" | "occurred_at" | "grounding" | "weight";

const COLUMNS: readonly (readonly [Column, string])[] = [
  ["kind", "kind"],
  ["occurred_at", "witnessed"],
  ["grounding", "grounding"],
  ["weight", "weight"],
];

function valueOf(stone: Stone, column: Column): string | number {
  if (column === "weight") return stone.weight;
  if (column === "grounding") return stone.grounding;
  if (column === "kind") return stone.label;
  return String(stone.detail["occurred_at"] ?? "");
}

export function BasisTable({ stones }: { readonly stones: readonly Stone[] }) {
  const [column, setColumn] = useState<Column>("occurred_at");
  const [descending, setDescending] = useState(true);

  const sorted = useMemo(() => {
    const rows = [...stones];
    rows.sort((a, b) => {
      const left = valueOf(a, column);
      const right = valueOf(b, column);
      const order = left < right ? -1 : left > right ? 1 : 0;
      return descending ? -order : order;
    });
    return rows;
  }, [stones, column, descending]);

  return (
    <div className="min-w-0">
      <p className="font-mono text-[0.6875rem] uppercase tracking-[0.13em] text-slate">
        the basis, {stones.length} observations
      </p>
      <div className="mt-4 overflow-x-auto">
        <table className="w-full border-collapse font-mono text-[0.8125rem]">
          <thead>
            <tr>
              {COLUMNS.map(([key, label]) => (
                <th key={key} scope="col" className="border-b border-seam py-2 pr-6 text-left">
                  <button
                    type="button"
                    onClick={() => {
                      if (key === column) setDescending((was) => !was);
                      else {
                        setColumn(key);
                        setDescending(true);
                      }
                    }}
                    className="text-[0.6875rem] uppercase tracking-[0.13em] text-slate hover:text-graphite"
                    aria-sort={column === key ? (descending ? "descending" : "ascending") : "none"}
                  >
                    {label}
                    {column === key ? (descending ? " \u2193" : " \u2191") : ""}
                  </button>
                </th>
              ))}
              <th
                scope="col"
                className="border-b border-seam py-2 text-left text-[0.6875rem] uppercase tracking-[0.13em] text-slate"
              >
                source
              </th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((stone) => {
              const tx = stone.detail["tx_hash"];
              const hash = String(stone.detail["content_hash"] ?? "");
              return (
                <tr key={stone.id}>
                  <td className="border-b border-seam py-2 pr-6 text-graphite">{stone.label}</td>
                  <td className="border-b border-seam py-2 pr-6 tabular-nums text-slate">
                    {String(stone.detail["occurred_at"] ?? "").slice(0, 10)}
                  </td>
                  <td className="border-b border-seam py-2 pr-6 text-slate">{stone.grounding}</td>
                  <td className="border-b border-seam py-2 pr-6 tabular-nums text-slate">
                    {stone.weight.toFixed(2)}
                  </td>
                  <td className="border-b border-seam py-2 text-slate">
                    {typeof tx === "string" && tx ? (
                      <a
                        href={`https://basescan.org/tx/${tx}`}
                        rel="noreferrer"
                        className="text-lapis underline underline-offset-[1px]"
                        title={hash}
                      >
                        {tx.slice(0, 10)}…
                      </a>
                    ) : (
                      <span title={hash}>{hash.slice(0, 18)}…</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
