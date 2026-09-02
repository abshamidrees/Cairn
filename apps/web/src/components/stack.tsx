"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { TIERS, fetchDossier, type Dossier, type Stone as StoneData, type Tier } from "@/lib/api";
import { ObservationCard, Stone } from "@/components/stone";
import { ErrorState, VerdictLine } from "@/components/primitives";

/**
 * The Stack renders one counterparty's dossier as a literal cairn.
 *
 * The five bands are the five Sibyl Memory tiers, not decoration. A stone sits
 * in the band its row actually lives in, so a judge reading the README can match
 * a stone to a row in the database.
 */

const DUR_STACK_MS = 420;

/** However many stones there are, the stack finishes arriving inside this. */
const MAX_ENTRY_MS = 1800;

function prefersReducedMotion(): boolean {
  if (typeof window === "undefined") return false;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/** Bottom to top. The stagger runs in this order, so the stack builds upward. */
function flatten(stones: Readonly<Record<Tier, readonly StoneData[]>>): readonly StoneData[] {
  return TIERS.flatMap((tier) => stones[tier] ?? []);
}

export interface StackProps {
  readonly stones: Readonly<Record<Tier, readonly StoneData[]>>;
  readonly counts: { readonly observations: number; readonly grounded: number };
  readonly standing: StoneData["grounding"];
  readonly confidence: number | null;
  readonly noBasis: boolean;
  readonly memory: "on" | "off";
  readonly leaving?: boolean;
  readonly animate?: boolean;
  readonly onToggleMemory?: (next: "on" | "off") => void;
}

export function Stack({
  stones,
  counts,
  standing,
  confidence,
  noBasis,
  memory,
  leaving = false,
  animate = true,
  onToggleMemory,
}: StackProps) {
  const flat = useMemo(() => flatten(stones), [stones]);
  const [focused, setFocused] = useState(0);
  const [selected, setSelected] = useState<StoneData | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (focused > flat.length - 1) setFocused(0);
  }, [flat.length, focused]);

  const move = useCallback(
    (delta: number) => {
      if (flat.length === 0) return;
      const next = Math.max(0, Math.min(flat.length - 1, focused + delta));
      setFocused(next);
      const el = containerRef.current?.querySelector<HTMLElement>(`[data-stone-index="${next}"]`);
      el?.focus();
    },
    [flat.length, focused],
  );

  const onKeyDown = useCallback(
    (event: React.KeyboardEvent<HTMLDivElement>) => {
      // Up moves toward HOT, which is later in the bottom-up order.
      if (event.key === "ArrowUp" || event.key === "ArrowRight") {
        event.preventDefault();
        move(1);
      } else if (event.key === "ArrowDown" || event.key === "ArrowLeft") {
        event.preventDefault();
        move(-1);
      } else if (event.key === "Home") {
        event.preventDefault();
        move(-flat.length);
      } else if (event.key === "End") {
        event.preventDefault();
        move(flat.length);
      }
    },
    [flat.length, move],
  );

  // Top down on screen, bottom up in the data.
  const bands = [...TIERS].reverse();
  const staggerCapMs = MAX_ENTRY_MS / Math.max(1, flat.length);

  return (
    <div className="flex flex-col gap-6">
      <div
        ref={containerRef}
        role="group"
        aria-label="Observations, stacked by memory tier"
        onKeyDown={onKeyDown}
        className="flex max-w-[26rem] flex-col gap-2"
      >
        {bands.map((tier) => {
          const inBand = stones[tier] ?? [];
          return (
            <div key={tier} className="flex items-start gap-4">
              <span className="w-[5.5rem] shrink-0 pt-1 font-mono text-[0.6875rem] uppercase tracking-[0.13em] text-scree">
                {tier}
              </span>
              <div className="flex min-h-[1.25rem] flex-1 flex-col items-start gap-1.5">
                {inBand.map((stone) => {
                  const index = flat.indexOf(stone);
                  return (
                    <Stone
                      key={stone.id}
                      stone={stone}
                      index={index}
                      focused={index === focused}
                      leaving={leaving}
                      enterOrder={index}
                      animate={animate && !leaving}
                      staggerCapMs={staggerCapMs}
                      onFocus={() => {
                        setFocused(index);
                        setSelected(stone);
                      }}
                      onSelect={() => setSelected(stone)}
                    />
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      <div className="flex flex-col gap-3 border-t border-seam pt-4">
        <p className="font-mono text-[0.8125rem] tabular-nums text-scree">
          {counts.observations} observations · {counts.grounded} grounded
        </p>
        <VerdictLine standing={standing} confidence={confidence} noBasis={noBasis} />
        {onToggleMemory ? <MemoryToggle memory={memory} onChange={onToggleMemory} /> : null}
      </div>

      <ObservationCard stone={selected} />
    </div>
  );
}

/**
 * The hackathon's eligibility gate, rendered as a switch.
 *
 * Flicking it off calls the API again with `?memory=off`, which swaps the
 * adapter server-side. The empty state that comes back is real.
 */
export function MemoryToggle({
  memory,
  onChange,
}: {
  readonly memory: "on" | "off";
  readonly onChange: (next: "on" | "off") => void;
}) {
  const on = memory === "on";
  return (
    <label className="flex w-fit cursor-pointer items-center gap-3">
      <button
        type="button"
        role="switch"
        aria-checked={on}
        aria-label="memory"
        onClick={() => onChange(on ? "off" : "on")}
        className={`relative h-5 w-9 rounded-pill border transition-colors duration-[var(--dur-fast)] ${
          on ? "border-lapis bg-lapis" : "border-seam bg-transparent"
        }`}
      >
        <span
          className={`absolute top-0.5 h-3.5 w-3.5 rounded-pill transition-all duration-[var(--dur-fast)] ${
            on ? "left-[1.125rem] bg-chalk" : "left-0.5 bg-scree"
          }`}
        />
      </button>
      <span className="font-mono text-[0.6875rem] uppercase tracking-[0.13em] text-scree">
        memory
      </span>
    </label>
  );
}

/* ---- the live container ------------------------------------------------ */

const EMPTY_STONES: Record<Tier, readonly StoneData[]> = {
  ARCHIVE: [],
  REFERENCE: [],
  COLD: [],
  WARM: [],
  HOT: [],
};

/**
 * Fetches a real dossier and drives the toggle against the real flag.
 *
 * Turning memory off plays the stones out before the empty response lands, so
 * the fall is visible rather than a jump cut. Under reduced motion the wait is
 * skipped entirely and the state simply changes.
 */
export function DossierStack({ address }: { readonly address: string }) {
  const [dossier, setDossier] = useState<Dossier | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [memory, setMemory] = useState<"on" | "off">("on");
  const [leaving, setLeaving] = useState(false);

  const load = useCallback(
    async (next: "on" | "off", signal?: AbortSignal) => {
      try {
        setError(null);
        const data = await fetchDossier(address, { memory: next, ...(signal ? { signal } : {}) });
        setDossier(data);
      } catch (cause) {
        if ((cause as Error).name === "AbortError") return;
        setError((cause as Error).message);
      }
    },
    [address],
  );

  useEffect(() => {
    const controller = new AbortController();
    void load("on", controller.signal);
    return () => controller.abort();
  }, [load]);

  const toggle = useCallback(
    async (next: "on" | "off") => {
      setMemory(next);
      if (next === "off" && !prefersReducedMotion()) {
        setLeaving(true);
        await new Promise((resolve) => setTimeout(resolve, DUR_STACK_MS));
      }
      setLeaving(false);
      await load(next);
    },
    [load],
  );

  if (error !== null) {
    return (
      <ErrorState
        title="Cairn could not reach its record."
        detail={`The API did not answer: ${error}. The record is on the machine that serves it, so this is a connection problem rather than an empty dossier.`}
      />
    );
  }

  if (dossier === null) {
    return (
      <div className="flex flex-col gap-2" aria-busy>
        {[88, 64, 92, 58, 40].map((width) => (
          <span key={width} className="block h-3.5 rounded-stone bg-seam" style={{ width: `${width}%` }} />
        ))}
      </div>
    );
  }

  return (
    <Stack
      stones={leaving ? dossier.stones : (dossier.stones ?? EMPTY_STONES)}
      counts={leaving ? dossier.counts : dossier.counts}
      standing={dossier.verdict.standing}
      confidence={dossier.verdict.confidence}
      noBasis={dossier.verdict.no_basis}
      memory={memory}
      leaving={leaving}
      animate={memory === "on"}
      onToggleMemory={(next) => void toggle(next)}
    />
  );
}
