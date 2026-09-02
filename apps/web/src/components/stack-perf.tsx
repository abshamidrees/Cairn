"use client";

import { useCallback, useMemo, useState } from "react";

import { Button } from "@/components/primitives";
import { Stack } from "@/components/stack";
import { countsOf, largeStack } from "@/lib/fixtures";

/**
 * Frame time for a Stack carrying two hundred stones.
 *
 * Samples requestAnimationFrame deltas across the mount and the busiest part of
 * the entry, which is where all the layout and paint work happens. Reported
 * rather than asserted: the number belongs in the phase report, and a budget
 * that is never measured is a budget nobody is keeping.
 */

const STONE_COUNT = 200;
const SAMPLE_MS = 1500;
const FRAME_BUDGET_MS = 1000 / 60;

// A frame marginally past 16.67ms is vsync jitter, not jank. A frame past two
// intervals is one the viewer genuinely lost, so both are reported: the first
// alone would read as failure on a display that is simply running at 60Hz.

interface Stats {
  readonly frames: number;
  readonly mean: number;
  readonly p95: number;
  readonly worst: number;
  readonly over: number;
  /** Frames past two vsync intervals, which is a frame the viewer actually lost. */
  readonly dropped: number;
}

function summarise(deltas: readonly number[]): Stats {
  const sorted = [...deltas].sort((a, b) => a - b);
  const total = deltas.reduce((sum, d) => sum + d, 0);
  const p95Index = Math.max(0, Math.floor(sorted.length * 0.95) - 1);
  return {
    frames: deltas.length,
    mean: total / Math.max(1, deltas.length),
    p95: sorted[p95Index] ?? 0,
    worst: sorted[sorted.length - 1] ?? 0,
    over: deltas.filter((d) => d > FRAME_BUDGET_MS).length,
    dropped: deltas.filter((d) => d > FRAME_BUDGET_MS * 2).length,
  };
}

export function StackFrameTime() {
  const stones = useMemo(() => largeStack(STONE_COUNT), []);
  const [mounted, setMounted] = useState(false);
  const [stats, setStats] = useState<Stats | null>(null);
  const [running, setRunning] = useState(false);

  const measure = useCallback(() => {
    setStats(null);
    setRunning(true);
    setMounted(true);

    const deltas: number[] = [];
    let previous = performance.now();
    const started = previous;

    const tick = (now: number) => {
      deltas.push(now - previous);
      previous = now;
      if (now - started < SAMPLE_MS) {
        requestAnimationFrame(tick);
      } else {
        // The first delta spans the mount itself, so it is kept: dropping it
        // would flatter the number by hiding the most expensive frame.
        setStats(summarise(deltas));
        setRunning(false);
      }
    };
    requestAnimationFrame(tick);
  }, []);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center gap-4">
        <Button onClick={measure} disabled={running}>
          {running ? "Measuring" : `Measure ${STONE_COUNT} stones`}
        </Button>
        {stats !== null ? (
          <dl className="flex flex-wrap gap-x-8 gap-y-1 font-mono text-[0.8125rem] tabular-nums text-slate">
            {(
              [
                ["frames", String(stats.frames)],
                ["mean", `${stats.mean.toFixed(2)}ms`],
                ["p95", `${stats.p95.toFixed(2)}ms`],
                ["worst", `${stats.worst.toFixed(2)}ms`],
                ["over 16.7ms", String(stats.over)],
                ["dropped", String(stats.dropped)],
              ] as const
            ).map(([label, value]) => (
              <div key={label} className="flex gap-2">
                <dt className="text-scree">{label}</dt>
                <dd>{value}</dd>
              </div>
            ))}
          </dl>
        ) : null}
      </div>

      {mounted ? (
        <div className="max-h-[28rem] overflow-y-auto rounded-stone border border-seam p-4">
          <Stack
            stones={stones}
            counts={countsOf(stones)}
            standing="grounded"
            confidence={0.84}
            noBasis={false}
            memory="on"
            animate
          />
        </div>
      ) : null}
    </div>
  );
}
