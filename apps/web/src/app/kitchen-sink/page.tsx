"use client";

import { useState } from "react";

import { CairnIcon, CairnMark, type Standing } from "@/components/cairn-mark";
import {
  BrowserFrame,
  Button,
  EmptyState,
  ErrorState,
  Eyebrow,
  MonoTable,
  Skeleton,
  StandingChip,
  StatRow,
  TerminalCard,
  VerdictLine,
} from "@/components/primitives";
import { DossierStack, MemoryToggle, Stack } from "@/components/stack";
import { ClaimBasis, Footer, Nav } from "@/components/shell";
import { ObservationCard, Stone } from "@/components/stone";
import { StackFrameTime } from "@/components/stack-perf";
import {
  EMPTY_STACK,
  GROUNDED_STACK,
  SUSPECT_STACK,
  THIN_STACK,
  countsOf,
} from "@/lib/fixtures";

/**
 * Every component, at every state.
 *
 * Built before any page so a state is designed once here rather than improvised
 * inside a section later. The Stack at the bottom is live against the API; the
 * ones above it use fixtures so states the indexed set does not currently
 * contain, such as suspect, can still be seen.
 */

const STANDINGS: readonly Standing[] = ["default", "grounded", "thin", "suspect", "dormant"];
const REAL_STANDINGS = ["grounded", "thin", "suspect", "dormant"] as const;

/** A counterparty in the indexed set with three independent claimants. */
const LIVE_ADDRESS = "0x01f90369170c917a2c0e9d26d54c6a3a400984d3";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="border-t border-seam py-12">
      <Eyebrow>{title}</Eyebrow>
      <div className="mt-6">{children}</div>
    </section>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-3 py-4">
      <span className="font-mono text-[0.6875rem] text-scree">{label}</span>
      {children}
    </div>
  );
}

export default function KitchenSinkPage() {
  const [memory, setMemory] = useState<"on" | "off">("on");

  return (
    <div className="bg-chalk">
      <Nav standing="grounded" observations={364} />

      <main className="mx-auto max-w-[78rem] px-6 py-12">
        <h1 className="font-display text-[2.5rem] text-graphite">Kitchen sink</h1>
        <p className="mt-2 max-w-[42rem] text-slate">
          Every component at every state. Fixtures above, the live API below.
        </p>

        <Section title="CairnMark">
          <div className="flex flex-wrap gap-10">
            {STANDINGS.map((standing) => (
              <div key={standing} className="flex flex-col items-center gap-3">
                <CairnMark standing={standing} width={56} height={56} />
                <span className="font-mono text-[0.6875rem] text-scree">{standing}</span>
              </div>
            ))}
            <div className="flex flex-col items-center gap-3">
              <CairnIcon width={16} height={16} />
              <span className="font-mono text-[0.6875rem] text-scree">icon 16px</span>
            </div>
          </div>
        </Section>

        <Section title="Button">
          <div className="flex flex-wrap items-center gap-4">
            <Button>Look up an agent</Button>
            <Button variant="ghost">Read the memory note</Button>
            <Button disabled>Disabled</Button>
            <Button variant="ghost" disabled>
              Disabled ghost
            </Button>
          </div>
        </Section>

        <Section title="StandingChip">
          <div className="flex flex-wrap gap-4">
            {REAL_STANDINGS.map((standing) => (
              <StandingChip key={standing} standing={standing} />
            ))}
          </div>
        </Section>

        <Section title="VerdictLine">
          <div className="flex flex-col gap-4">
            {REAL_STANDINGS.map((standing) => (
              <VerdictLine key={standing} standing={standing} confidence={0.84} />
            ))}
            <VerdictLine standing="thin" confidence={null} noBasis />
          </div>
        </Section>

        <Section title="StatRow">
          <StatRow figure="90.6%" label="of reviewers on Base show coordinated behaviour" />
          <StatRow figure="$0.0027" label="median cost to move an agent's standing" />
        </Section>

        <Section title="MonoTable">
          <MonoTable
            columns={["tier", "holds", "rows"]}
            rows={[
              ["HOT", "the live verdict", "1"],
              ["WARM", "behaviour seen three times", "7"],
              ["COLD", "every observation", "364"],
            ]}
          />
        </Section>

        <Section title="TerminalCard and BrowserFrame">
          <div className="grid gap-6 md:grid-cols-2">
            <TerminalCard command="curl https://api.usecairn.xyz/v1/lookup/0x..." />
            <BrowserFrame label="explorer.usecairn.xyz">
              <p className="text-slate">A real UI fragment sits here, never an illustration.</p>
            </BrowserFrame>
          </div>
        </Section>

        <Section title="Skeleton, EmptyState, ErrorState">
          <div className="flex flex-col gap-6">
            <div className="flex flex-col gap-2">
              <Skeleton width="88%" />
              <Skeleton width="64%" />
              <Skeleton width="40%" />
            </div>
            <EmptyState
              title="No observations."
              detail="Cairn has never watched this agent do anything."
              action={<Button variant="ghost">Start watching</Button>}
            />
            <ErrorState
              title="Cairn could not reach its record."
              detail="The API did not answer. The record lives on the machine that serves it."
            />
          </div>
        </Section>

        <Section title="Stone">
          <div className="flex flex-col gap-6">
            <Row label="fill encodes grounding">
              <div className="flex flex-col gap-2">
                {REAL_STANDINGS.map((grounding, i) => (
                  <Stone
                    key={grounding}
                    stone={{
                      id: `demo-${grounding}`,
                      tier: "COLD",
                      weight: 0.7,
                      grounding,
                      tilt: [-1.5, 2, -2.5, 1][i] ?? 0,
                      label: grounding,
                      detail: {},
                    }}
                    index={i}
                    focused={false}
                    leaving={false}
                    enterOrder={i}
                    animate={false}
                    onFocus={() => undefined}
                    onSelect={() => undefined}
                  />
                ))}
              </div>
            </Row>
            <Row label="width encodes weight, and never grounding">
              <div className="flex flex-col gap-2">
                {[0.1, 0.35, 0.6, 0.85, 1].map((weight, i) => (
                  <Stone
                    key={weight}
                    stone={{
                      id: `w-${weight}`,
                      tier: "COLD",
                      weight,
                      grounding: "grounded",
                      tilt: 0,
                      label: `weight ${weight}`,
                      detail: {},
                    }}
                    index={i}
                    focused={false}
                    leaving={false}
                    enterOrder={i}
                    animate={false}
                    onFocus={() => undefined}
                    onSelect={() => undefined}
                  />
                ))}
              </div>
            </Row>
          </div>
        </Section>

        <Section title="ObservationCard">
          <div className="grid gap-6 md:grid-cols-2">
            <ObservationCard stone={null} />
            <ObservationCard stone={GROUNDED_STACK.COLD[0] ?? null} />
          </div>
        </Section>

        <Section title="MemoryToggle">
          <MemoryToggle memory={memory} onChange={setMemory} />
        </Section>

        <Section title="Stack, fixtures at every standing">
          <div className="grid gap-12 lg:grid-cols-2">
            {(
              [
                ["grounded", GROUNDED_STACK, "grounded", 0.87, false],
                ["thin", THIN_STACK, "thin", 0.31, false],
                ["suspect", SUSPECT_STACK, "suspect", 0.22, false],
                ["no basis", EMPTY_STACK, "thin", null, true],
              ] as const
            ).map(([label, stones, standing, confidence, noBasis]) => (
              <div key={label}>
                <p className="mb-4 font-mono text-[0.6875rem] text-scree">{label}</p>
                <Stack
                  stones={stones}
                  counts={countsOf(stones)}
                  standing={standing}
                  confidence={confidence}
                  noBasis={noBasis}
                  memory="on"
                  animate={false}
                />
              </div>
            ))}
          </div>
        </Section>

        <Section title="ClaimBasis, the split every section uses">
          <ClaimBasis
            claim={
              <p className="font-display text-[2rem] leading-tight text-graphite">
                An observation is something Cairn watched happen.
              </p>
            }
            basisLabel="the basis"
            basis={
              <ul className="space-y-1">
                <li>erc8004_registration · base:0x8004A169</li>
                <li>erc8004_feedback · base:0x8004BAa1</li>
                <li>erc8004_claim · base:0x8004BAa1</li>
              </ul>
            }
          />
        </Section>

        <Section title="Stack frame time, 200 stones">
          <StackFrameTime />
        </Section>

        <Section title="Stack, live against the API">
          <p className="mb-6 max-w-[42rem] text-slate">
            This one reads the real record. The toggle calls the API again with{" "}
            <code className="font-mono text-[0.8125rem]">?memory=off</code>, which swaps the adapter
            on the server, so the empty state comes back from an engine that genuinely had nothing
            to read.
          </p>
          <DossierStack address={LIVE_ADDRESS} />
        </Section>
      </main>

      <Footer
        ticker={[
          {
            id: "1",
            at: "17:00:07Z",
            kind: "erc8004_feedback",
            counterparty: "0x01f9…84d3",
            standing: "grounded",
          },
        ]}
      />
    </div>
  );
}
