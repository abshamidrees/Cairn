# Cairn, build brief for Claude Code

Version 1.0, August 2026. Put this at `docs/BRIEF.md` in the repo. It is the source of truth for every phase. `CLAUDE.md` at the repo root is the short version that stays loaded.

Built for the Sibyl Labs Memory Hackathon. Build window Sep 1-10, 2026. Every decision in this file is made against the rubric in part 12.

---

## 0. What Cairn is

Cairn is a memory-native trust layer for agent commerce.

When one AI agent is about to transact with another, it has no way to answer the only question that matters: *has this counterparty done what it said it would, before?* The registries that were supposed to answer it don't. On Base, 90.6% of ERC-8004 reviewers show coordinated Sybil behaviour, 86.8% of rated agents have no valid feedback left once you strip it, and a reputation can be fabricated or destroyed for a median of $0.0027. The ERC-8004 spec itself defers the fix to a reviewer-reputation layer that, in its own words, does not yet exist.

Cairn is that layer, and it is built out of memory. Cairn watches real interactions (ACP jobs, escrow settlements, x402 payments, delivery rejections) and writes each one into Sibyl Memory as an **observation** it witnessed itself. It keeps an isolated **dossier** per counterparty, promotes repeated behaviour into durable entities, decays and archives what goes stale, and scores *reviewers* by whether their past claims were later corroborated by outcomes Cairn verified. When an agent asks about a stranger, Cairn returns a **verdict** with a **confidence** and a **basis**: the specific observations the judgment rests on.

Every competitor returns a number. Cairn returns the record the number came from.

**The load-bearing claim, stated plainly:** delete the memory layer and Cairn is a stateless LLM guessing about a wallet address. No dossiers, no priors, no reviewer weights, no calibration, no basis. The core function does not degrade, it ceases. Part 11 ships a script that proves it.

**Core primitives (locked, do not redesign):**

| | |
|---|---|
| Observation ledger | Every judgment traces to an event Cairn itself witnessed and hashed, never to a self-reported rating. This is the fix for evidence-free feedback |
| Counterparty dossier | One isolated memory tenant per agent. Five tiers, promoted and demoted as evidence accumulates or goes stale |
| Reviewer weighting | Cairn keeps a dossier on reviewers too, weighted by whether their past claims were later corroborated. This is the layer ERC-8004 says is missing |
| Portable standing | The verdict is published back on Base as an attestation, so the record survives outside Cairn |

**Vocabulary. Use these words everywhere, UI, docs, API, errors, commit messages.** The record for one counterparty is a **dossier**. One witnessed event is an **observation**. Tying a claim to an observation is **grounding**. Cairn's current judgment is a **verdict**, carrying a **confidence** and a **basis**. What Cairn believed going in is a **prior**. A counterparty's position is its **standing**: `grounded`, `thin`, `suspect`, `dormant`.

Never say *reputation score*, *rating*, *review*, or *trust score*. Those are the broken things Cairn replaces, and using their vocabulary concedes the argument.

---

## 1. Surfaces to build

Four surfaces would sink a ten-day build. Three, and the docs live inside the web app.

| Surface | Hostname | Served by |
|---|---|---|
| Landing | `usecairn.xyz` | `apps/web` |
| Explorer | `explorer.usecairn.xyz` | `apps/web`, rewritten to `/explorer` |
| Docs | `docs.usecairn.xyz` | `apps/web`, rewritten to `/docs` |
| API and agent | `api.usecairn.xyz` | `apps/agent` on Fly.io |

**Four hostnames, two deployments, one frontend codebase.** Splitting the explorer and the docs into separate Next.js apps would cost days we do not have and would break shared components. Instead all three web hostnames point at the same Vercel project and middleware rewrites by `Host` header. Add all three domains to the one Vercel project in Cloudflare DNS, then:

```ts
// apps/web/src/middleware.ts
import { NextResponse, type NextRequest } from "next/server";

const SUBDOMAIN_ROOT: Record<string, string> = {
  "explorer": "/explorer",
  "docs": "/docs",
};

export function middleware(req: NextRequest) {
  const host = req.headers.get("host")?.split(":")[0] ?? "";
  const sub = host.endsWith("usecairn.xyz") ? host.split(".")[0] : null;
  const root = sub ? SUBDOMAIN_ROOT[sub] : undefined;
  if (!root) return NextResponse.next();

  // explorer.usecairn.xyz/0xabc  ->  /explorer/0xabc
  const url = req.nextUrl.clone();
  if (!url.pathname.startsWith(root)) url.pathname = root + url.pathname;
  return NextResponse.rewrite(url);
}

export const config = { matcher: ["/((?!_next|api|.*\\..*).*)"] };
```

Two things this needs so it does not cost points. Set a canonical link on every page pointing at the subdomain form, or `usecairn.xyz/docs` and `docs.usecairn.xyz` will both index as duplicates. And build every internal link from a `hostFor(surface)` helper rather than hardcoding, so a link from the landing page to a dossier lands on `explorer.usecairn.xyz/0xabc` and not on the path form. Do both in phase 0, not phase 9.

`api.usecairn.xyz` is a CNAME to the Fly.io app. It is a separate deployment because the memory database needs a persistent disk (part 2), not because of the URL.

---

## 2. Stack

Locked. Do not substitute without asking. Three constraints below were verified by running the SDK, not read off a docs page, do not design around them differently.

```
apps/
├─ agent/            Python 3.12. Cairn core. THE LOAD-BEARING CODE LIVES HERE
│  ├─ memory/        Sibyl Memory adapter: tiers, tenants, promotion, decay
│  ├─ observe/       ACP + Base + x402 watchers that produce observations
│  ├─ judge/         verdict engine: priors → evidence → verdict + basis
│  ├─ publish/       attestation writer (Base)
│  └─ api/           FastAPI, mounted on the same box as memory.db
└─ web/              Next.js 15 (App Router, React 19) - landing, explorer, docs
packages/
└─ chain/            web3.py - ERC-8004 registry reads/writes, USDC, x402
```

**Three verified constraints. Violating any of them costs you a day.**

1. **Sibyl Memory is Python-only.** There is no JS SDK. `MemoryClient.local(path)` over SQLite + FTS5. It works fully offline with no credentials, no network call on read, write, or search.
2. **`memory.db` needs a persistent disk.** Memory content never leaves the machine, so there is no hosted mode to point at. Vercel serverless cannot hold it. The agent and API run on one Fly.io machine with a mounted volume; only `apps/web` goes to Vercel.
3. **`learn()`, `lint()` and skill proposals are paid-tier gated.** They raise `TierGateError` on free. Do not build on them. Cairn's promotion, decay and consolidation logic in part 10 is ours, which scores better anyway, it is our sophistication on display, not theirs.

- **Memory:** `sibyl-memory-client`. Also install `sibyl-memory-cli` and run `sibyl init` + `sibyl status` so the tier and DB size are visible.
- **Styling:** Tailwind v4 CSS-first (`@theme`), tokens from `cairn-tokens.css`. No `tailwind.config.js`.
- **Components:** shadcn/ui (new-york) as the base layer, restyled to the tokens. Never ship shadcn defaults, neutral greys and `--radius: 0.5rem` are an instant tell.
- **Motion:** `motion/react`. One preset file. No ad hoc durations.
- **Chain:** `web3.py` against Base mainnet. ERC-8004 Identity Registry `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432`, Reputation Registry `0x8004BAa17C55a88189AE136b182e5fdA19dE9b63`, ACP Core `0x238E541BfefD82238730D00a2208E5497F1832E0`. Read from a Base RPC with an archive-capable provider; do not scrape an explorer.
- **ACP:** drive `@virtuals-protocol/acp-cli` by subprocess. Every command supports `--json`. Do not write a second chain client for it.
- **LLM:** Claude via the Anthropic API for summarisation and the natural-language verdict rationale. Never for the verdict itself, the verdict is computed from the record, and a judge will ask.
- **Docs:** MDX in `apps/web`, not a second app.
- **Deploy:** `apps/web` on Vercel. `apps/agent` on Fly.io with a volume mounted at `/data`, `SIBYL_DB=/data/memory.db`.

---

## 3. Brand

Tokens live in `cairn-tokens.css`, attached. Do not invent colours, radii, shadows or durations that are not in that file.

### Palette

| Token | Hex | Only ever used for |
|---|---|---|
| chalk | `#F2F3EF` | page background, ~80% of any screen |
| paper | `#FBFBF9` | cards, panels, inputs |
| seam | `#DFE1DA` | every border and divider, one hairline weight |
| graphite | `#16181A` | headings, the mark, numbers |
| slate | `#454B4F` | body copy |
| scree | `#8A9197` | captions, labels, placeholders, THIN standing |
| **lapis** `#223FA6` | | primary buttons, links, GROUNDED standing |
| **oxide** `#8C2130` | | SUSPECT standing, contradiction, the kill switch |
| basalt | `#101214` | the single dark panel: footer, code blocks, explorer shell |

**The rule that makes this palette a brand and not a swatch: colour means evidence.** Lapis appears only where Cairn has grounded a claim in an observation it holds. Oxide appears only where Cairn's own record contradicts a claim. `thin`: Cairn has nothing, is rendered in scree, deliberately colourless, because absence of evidence should look like absence. If a colour appears where Cairn cannot point at an observation, it is wrong. There is no fourth accent, no gradient anywhere, and no colour on the mark other than the keystone.

Why cool limestone and not cream: t54 runs `#faf9f6` with a `#ff4d32` coral, Kite runs white with a charred-umber `#22140d` and oat accents, Aptos runs mint and warm brown. All three are warm. A cool, mineral off-white with a deep ultramarine reads as a different species next to any of them, and it is the one axis none of the references occupy.

### Type

Three families, all OFL, all from `next/font/google`. No local font files, no CDN at runtime.

| Role | Family | Used for |
|---|---|---|
| Display | **Newsreader** 400, 400 italic | Headings, the wordmark, anything over 24px |
| Text | **Geist** 400 / 500 | Body copy, lead paragraphs, form labels |
| Data | **Geist Mono** 400 / 500 | Every number, ID, hash, address, timestamp, label, eyebrow, button label, code |

Why these, and where the risk is. Both references reach for a serif display. Kite runs Crimson Text, Aptos runs a high-contrast didone. So a serif alone is not a differentiator. Three moves make ours ours. **First, weight 400, never bold.** Both references set their serif heavy; Cairn sets Newsreader light at 5-6rem, which reads as a document of record rather than a headline. Confidence comes from size, not weight. **Second, mono carries far more of the page than in either reference.** Every label, eyebrow, button, number and timestamp is mono, so the page reads as a serif claim sitting on a machine-made basis. That tension is the product. **Third, italic is reserved for exactly one element**: the verdict line. Nothing else in the product is ever italic, so italic *means* "this is Cairn's judgment." No competitor site uses display italic as a semantic.

```ts
// apps/web/src/fonts.ts
import { Newsreader, Geist, Geist_Mono } from "next/font/google";

export const newsreader = Newsreader({
  subsets: ["latin"], weight: ["400"], style: ["normal", "italic"],
  variable: "--font-newsreader", display: "swap",
});
export const geist = Geist({
  subsets: ["latin"], weight: ["400", "500"],
  variable: "--font-geist", display: "swap",
});
export const geistMono = Geist_Mono({
  subsets: ["latin"], weight: ["400", "500"],
  variable: "--font-geist-mono", display: "swap",
});

export const fontVars = [newsreader, geist, geistMono].map(f => f.variable).join(" ");
```

Put `className={fontVars}` on `<html>`. The token file maps roles onto those variables, so no component ever names a family. Verify preload with `curl -s localhost:3000 | grep 'rel="preload"'` and expect four hits.

Type scale is in the token file. Hero `clamp(2.75rem, 7.5vw, 6rem)` at `-0.03em` and `0.94` leading. Section `clamp(2rem, 4.4vw, 3.5rem)` at `-0.022em`. Card `1.5rem`. Lead `1.0625rem` at `1.62`. Body `0.9375rem`. Mono data `0.8125rem`. Mono labels `0.6875rem` at `+0.13em` uppercase.

Every number in the product is `--font-mono` with `font-variant-numeric: tabular-nums`. No exceptions, including KPI figures and chart axes.

### Logo

Attached as `cairn-mark.svg` (five stones, monochrome, `currentColor`), `cairn-mark-standing.svg` (graphite stones, lapis keystone), `cairn-icon.svg` (simplified three-stone, for 24px and below) and `cairn-app-icon.svg` (512 app icon).

The mark is five stones stacked by hand. Each stone is a rounded rect with a distinct width, a horizontal offset and a 1-2.5° tilt, and the middle stone is **wider than the one beneath it**. That overhang is the whole design: a perfect pyramid reads as a children's stacking toy, an imperfect stack reads as something a person built and left behind. Do not straighten the stones and do not make the widths monotonic.

The stones are deliberately chunky, 15 units tall in a 120 box with 5-unit gaps. An earlier, thinner draft read as precise but weightless. Weight matters here: the mark has to look like something that was stacked, not drawn.

The five stones are the five Sibyl Memory tiers, bottom to top: ARCHIVE, REFERENCE, COLD, WARM, HOT. The top stone is the keystone, the most recent evidence, and it is the only element that ever takes a colour other than the mark's own. It carries the standing.

Ship it as a React component with a standing prop and use that everywhere:

```tsx
// apps/web/src/components/cairn-mark.tsx
type Standing = "default" | "grounded" | "thin" | "suspect";
const KEYSTONE: Record<Standing, string> = {
  default:  "currentColor",
  grounded: "var(--color-lapis)",
  thin:     "var(--color-scree)",
  suspect:  "var(--color-oxide)",
};

// Bottom to top. These five rows are the mark AND the seed geometry for
// the Stack in part 5. Do not change them in one place only.
const STONES = [
  { x: 14, y: 93, w: 92, h: 15, r: 4, tilt: -1.0 },  // ARCHIVE
  { x: 27, y: 73, w: 58, h: 15, r: 4, tilt:  2.5 },  // REFERENCE
  { x: 22, y: 53, w: 82, h: 15, r: 4, tilt: -1.5 },  // COLD   ← the overhang
  { x: 31, y: 33, w: 52, h: 15, r: 4, tilt:  2.0 },  // WARM
  { x: 45, y: 13, w: 38, h: 15, r: 4, tilt: -2.5 },  // HOT · keystone
];

export function CairnMark({ standing = "default", ...props }:
  { standing?: Standing } & React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 120 120" fill="none" role="img" aria-label="Cairn" {...props}>
      {STONES.map((s, i) => (
        <rect key={i} x={s.x} y={s.y} width={s.w} height={s.h} rx={s.r}
          fill={i === STONES.length - 1 ? KEYSTONE[standing] : "currentColor"}
          transform={`rotate(${s.tilt} ${s.x + s.w / 2} ${s.y + s.h / 2})`} />
      ))}
    </svg>
  );
}
```

Rules: minimum size 20px for the five-stone mark. Below 20px switch to `cairn-icon.svg`, which is three stones at the same proportions and holds cleanly at 16px. Clear space equal to the height of one stone on all sides. The favicon carries the standing of whatever the explorer is currently showing. Never outline the mark, never place it on a coloured field other than chalk, paper or basalt.

**Wordmark lockup.** Mark at cap height, then a gap of one stone-height, then `Cairn` in Newsreader 400 with `-0.02em` tracking, in graphite. Never all-caps, never letterspaced, never bold. In the nav the wordmark sits hard left at 28px mark height.

### Taglines

Primary: *A record, not a rating.*
Alternates for OG cards and social: *Every verdict points at the evidence.* / *No agent starts from zero.*

---

## 4. The design blend, made explicit

The references contribute named things and nothing else. Take structure, spacing, rhythm and motion. Take zero assets, zero copy strings, zero colour values, zero typefaces.

### From t54.ai, section rhythm and the product frame

- Mono uppercase eyebrow, then a large display heading, then generous whitespace. Sections separated by space, not by heavy rules.
- The product screenshot in a browser-chrome frame with a floating detail card overlapping one corner. t54 uses this for a live decision; Cairn uses it for a live verdict.
- The stat strip: a large mono figure on the left, a label on the right, hairline rules between rows.
- **Not taken:** the centred hero, the dot-matrix halftone field, the coral. Warrant already runs a halftone field, and a second one would make the two projects look like the same studio's template.

### From agentpassport.ai, the shell and the developer moments

- Top nav: hairline bottom border, mark plus wordmark hard left, links centred, one filled pill CTA hard right, hamburger sheet under 900px. Compact, 56-64px.
- The install command in the hero, in a rounded terminal card with a copy button.
- Feature blocks that show a real UI fragment instead of an illustration.
- **Not taken:** the white background, the charred-umber-and-oat palette, Crimson Text.

### From aptosnetwork.com, scale and the panel break

- Display type set very large and left-aligned, broken across three short lines.
- One full-bleed colour-blocked panel used as a hard break in the scroll rhythm. Aptos runs mint and warm brown; Cairn runs exactly one basalt panel, once, and never repeats it.
- Small mono uppercase labels sitting under enormous display figures.
- **Not taken:** the floating pill nav, the scrolling code-as-wallpaper side panel, the mint, the wireframe globe.

### Cairn's own, this is the 40% that has to carry the page

- **The claim / basis split.** Every section on the landing page is two columns: the claim on the left in Newsreader, the basis on the right in Geist Mono, the actual observations, hashes, counts and timestamps the claim rests on. It repeats down the whole page. This is not a layout preference, it is the product's thesis rendered as a grid: nothing is asserted without showing what it rests on. Under 900px the basis column collapses beneath its claim, never hidden.
- **The Stack** (part 5). The signature element.
- **The deletion toggle** (part 5). The hackathon's pass/fail gate, rendered as a switch.
- **Italic means verdict.** The only italic in the product.
- **Colourless means no evidence.** The only design system where the absence of an accent is itself a state.

Blend rule: if a section ends up looking like a colour swap of t54 or Aptos, cut it and rebuild it around the claim / basis split.

---

## 5. The Stack, specified

This is the one thing the page is remembered by. It is specified rather than described, because it is also the demo's money shot.

The Stack renders one counterparty's dossier as a literal cairn. It is a single component used in the hero, in the explorer, and in the demo video.

```
  HOT        ▬▬▬▬▬▬▬▬▬                    ← keystone: the live verdict
  WARM       ▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬
             ▭▭▭▭▭▭▭▭                     ← outline only = thin
  COLD       ▬▬▬▬▬▬▬▬▬▬▬▬
             ▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬
             ▬▬▬▬▬▬▬▬▬  ← oxide = suspect
  REFERENCE  ▬▬▬▬▬▬▬▬▬▬▬▬▬▬
  ARCHIVE    ▭▭▭▭▭▭  ▭▭▭▭
             └──────────────────────────┘
             43 observations · 11 grounded
```

Rules, all of them load-bearing:

- **Five horizontal bands, labelled in mono uppercase on the left: ARCHIVE, REFERENCE, COLD, WARM, HOT.** These are the real Sibyl tiers, not decoration. A stone's band is the tier its observation actually lives in. A judge who reads the README can match a stone to a row in the database.
- **One stone per observation.** Width encodes weight, how much that observation moves the verdict. Fill encodes grounding: lapis solid for grounded, hairline outline for thin, oxide for suspect, seam for dormant. Width is never colour and colour is never width.
- **Tilt is deterministic, not random.** Derive it from a hash of the observation id so it is stable across renders. `tilt = ((hash % 500) / 100) - 2.5` degrees. A stack that reshuffles on every render looks like a toy.
- **Stones enter bottom-up** on a 90ms stagger with `--ease-settle`, `--dur-stack`, arriving at their tilt rather than starting there.
- **Hover or focus a stone** and a paper card appears with the observation: what happened, when, the source, the content hash, and which tier it sits in. Keyboard reachable, arrow keys move between stones.
- Below the stack: a mono line reading `N observations · M grounded`, and the verdict in Newsreader italic.

### The deletion toggle

Directly beneath the Stack, a switch labelled `memory` in mono, default on.

Flick it off and: every stone falls away downward and out over 420ms, the counts go to `0 observations · 0 grounded`, the verdict line changes to *no basis*, the confidence reads `-`, and the keystone in the nav mark goes to scree. Flick it back on and the stack rebuilds bottom-up.

This is not an animation. It is the hackathon's eligibility gate, *delete the memory layer, does the product still do what it claims*, made physical, on the landing page, in four seconds. It is also the single highest-leverage element in the demo video. Wire it to the real API with a `?memory=off` flag that genuinely bypasses the memory layer rather than faking the empty state client-side, because a judge will open the network tab.

---

## 6. Motion and component budget

**Exactly three motion moments in the whole product.** Anything that moves and is not on this list gets cut.

1. **Page load.** The hero Stack builds itself bottom-up, five stones, 90ms stagger, settling into tilt. Runs once. Does not replay on scroll.
2. **The Stack receiving evidence.** A new stone enters its band.
3. **The deletion toggle.** Stones fall, verdict desaturates.

Everything else is a state change under `--dur-fast`: hover lifts a card by nothing and changes its border from seam to graphite at 20% opacity; buttons darken lapis to lapis-ink; links underline on hover with a 1px offset. No parallax, no scroll-jacking, no count-up numbers, no marquee, no gradient mesh, no floating orbs.

Every animation respects `prefers-reduced-motion`, which the token file already handles.

**Component inventory for `apps/web/src/components`.** Build these in phase 1 with a `/kitchen-sink` route showing every one at every state, before any page work: `CairnMark`, `Stack`, `Stone`, `StandingChip`, `VerdictLine`, `ObservationCard`, `BasisColumn`, `Eyebrow`, `StatRow`, `TerminalCard`, `BrowserFrame`, `Button` (primary lapis pill / ghost), `Nav`, `Footer`, `MonoTable`, `EmptyState`, `ErrorState`, `Skeleton`.

---

## 7. Landing page, section by section

Copy is written. Use it verbatim. Every section is the claim / basis split unless noted.

### Nav
Hairline bottom border on chalk, 60px. Wordmark hard left. Centre links in mono uppercase: `EXPLORER` `DOCS` `GITHUB`. Hard right: a lapis pill, `Look up an agent`. To the left of the pill, a live mono chip: `N OBSERVATIONS`: the real count from the API, not a hardcoded number. If the API is down the chip disappears rather than showing a zero.

### Hero
Full-bleed chalk. Left column, left-aligned, three lines of Newsreader 400 at hero scale:

> Agents can't
> check who they're
> about to pay.

Under it, one lead line in Geist: *Cairn keeps the record. Every verdict points at the observations it came from.*

Two buttons: `Look up an agent` (lapis pill) and `Read the memory note` (ghost pill).

Right column: **the Stack**, live, showing a real dossier, with the deletion toggle beneath it. This replaces the dashboard screenshot every competitor puts here. The most characteristic thing about the product is that it can show you its own basis, so that is what the hero shows.

### Stat strip
Four rows, hairline rules between, big mono figure left, label right. Real numbers from the Base registries, computed by our own indexer, with the source linked:

- `90.6%`: of ERC-8004 reviewers on Base show coordinated Sybil behaviour
- `86.8%`: of rated agents have no valid feedback once it is removed
- `$0.0027`: median cost to move an agent's reputation on Base
- `0`: mainnet deployments of the Validation Registry

Below the strip, one mono line: `Source: Xiong et al., arXiv:2606.26028 · independently verifiable`. Attribute it. Never present someone else's research as your own measurement.

### 01 What Cairn holds
Eyebrow `THE RECORD`. Claim: *An observation is something Cairn watched happen.* Basis column: a mono list of the four observation types with a real example of each, an ACP job completing, an escrow rejection, an x402 settlement, a delivery hash mismatch.

### 02 The five tiers
Eyebrow `HOW IT REMEMBERS`. Claim: *Memory is not one bucket.* Basis: the five tiers as a mono table, tier, what lives there, and the live count of rows Cairn currently holds in each. This section is where the 40-point criterion is argued visually, so it gets the most room on the page.

### 03 Reviewer weighting
Eyebrow `THE MISSING LAYER`. Claim: *We score the reviewers too.* Basis: a worked example, a reviewer who rated twelve agents highly, three of which Cairn later watched fail, and the weight that reviewer now carries. Real numbers from the indexed set.

### 04 Standing
Four cards on paper, hairline border, one per standing. `grounded` / `thin` / `suspect` / `dormant`, each with its chip, a one-line definition, and the count of indexed agents currently in it. The `thin` card is deliberately the plainest thing on the page, that is the point.

### 05 For agents
Eyebrow `INTEGRATE`. The terminal card with the install line and a copy button, then a four-line code sample showing an agent asking Cairn about a counterparty before funding an escrow, and branching on the answer. Tabs for Python and CLI.

### 06 Full-bleed basalt panel
The one dark moment in the product, used once. Centred, Newsreader in chalk at section scale: *Delete the memory and there is nothing left to ask.* Below it, in mono, the actual command a judge can run: `python scripts/deletion_test.py`, and its real output, abbreviated to six lines. Then a ghost pill to the repo.

### 07 CTA
Back on chalk. Centred, one Newsreader line: *Look up an agent you were about to pay.* One lapis pill. One mono line beneath: `Free while in beta · no wallet connection required to read`.

### Footer
Full-bleed basalt panel. Oversized `Cairn` wordmark in chalk on the left with the mark's keystone in lapis. Three link columns on the right: **Product** (Explorer, Docs, Standing definitions), **Build** (GitHub, API reference, Memory note), **Company** (X, Discord, hackathon submission). Socials as icons.

**No legal column.** Instead, the footer's bottom rail carries a live mono ticker of the last five observations Cairn wrote, timestamp, type, counterparty, standing delta, scrolling at 20s per cycle, paused on hover and under `prefers-reduced-motion`. The footer proves the thing is running. That is worth more than a privacy page nobody reads.

Bottom line, mono, scree: `© 2026 Cairn · MIT licensed · Built on Sibyl Memory`.

---

## 8. Explorer (`/explorer`)

Basalt shell, chalk content. This is the product, not a marketing page, treat it as an instrument.

**Search.** One field, mono, placeholder `agent id, wallet address, or ACP handle`. Cmd+K anywhere on the site. Recent lookups persisted in memory, not localStorage.

**Dossier view.** The page is one long claim / basis split.
- Header: the counterparty's identity, its standing chip, the verdict in Newsreader italic, the confidence as a mono percentage, and the timestamp of the most recent observation.
- Left: the Stack, full height, all five bands, every observation.
- Right: the basis, a mono table of observations, sortable, each row linking to its source (a Basescan tx, an ACP job id, an x402 receipt). Every row has a content hash.
- Beneath: **the prior panel.** What Cairn believed before the most recent observation, what changed, and why. This is the single screen that proves memory is doing work, so it is not collapsible and not below the fold on desktop.
- The deletion toggle sits in the header, always available.

**Reviewer view.** Same layout for a reviewer address: how many claims they have made, how many Cairn later corroborated, how many it contradicted, and the weight that produces.

Every screen needs a real loading state, a real empty state that says what will appear and links to the action that creates it, and a real error state. No route may 404. No placeholder data, no lorem, no invented metrics. If Cairn has never seen a counterparty, the empty state says so in the product's own voice: *No observations. Cairn has never watched this agent do anything.*, and offers to start watching.

---

## 9. Docs (`/docs`)

MDX inside `apps/web`. Sidebar with mono uppercase group labels, right-hand page table of contents, cmd+K search.

IA: **Start** (What Cairn is, Quickstart, Ask about a counterparty) · **Concepts** (Observation, Dossier, Grounding, Verdict and basis, Standing, Reviewer weight) · **Memory** (The five tiers, How Cairn promotes and decays, The deletion test) · **API** (Lookup, Observations, Attestations, Webhooks) · **Partners** (Base, Virtuals ACP).

Every concept page opens with a one-sentence bold definition, then a mono example, then prose. Every API page gets a request and response pair plus a curl tab. Code blocks on basalt with a copy button. Do not invent endpoints, read them out of `apps/agent/api`.

---

## 10. The memory architecture

This is the 40-point section. Build it first and build it properly; everything else is presentation.

### The adapter

`apps/agent/memory/store.py` wraps `MemoryClient` and is the only module in the codebase that imports it. Everything else goes through this interface, which is also what makes the deletion test a two-line change.

Verified API surface, use exactly these, they exist:

```python
from sibyl_memory_client import MemoryClient
m = MemoryClient.local("/data/memory.db")

m.set_tenant(tenant_id)                       # dossier isolation
m.set_entity(category, name, body, status=...)  # WARM
m.get_entity(category, name)
m.list_entities(category, status=..., limit=...)
m.archive_entity(category, name, reason=...)    # recoverable
m.delete_entity(category, name)               # permanent
m.set_state(key, body) / m.get_state(key)     # HOT
m.set_reference(key, body) / m.get_reference(key)
m.write_event(evaluated=..., acted=..., forward=...)  # COLD, returns event id
m.read_events(limit=..., since=..., until=...)
m.search(query, tiers=(...), limit=...)           # FTS5 across tiers
m.search_entities(query, category=...)
```

### Tenancy, the coordination pattern

One tenant per subject, never one shared store. `MemoryClient.set_tenant()` gives fully isolated rows inside the same database file; this is verified, and it is what makes Cairn a coordination system rather than a notepad.

- `cp:<chain>:<address>`: one dossier per counterparty
- `rv:<address>`: one dossier per reviewer
- `cairn:self`: Cairn's own operating state, priors and calibration

Cairn switches tenants as it reasons. A verdict about counterparty A reads A's dossier, then reads the reviewer dossiers of everyone who has made claims about A, then writes back to both. Three tenants coordinate to produce one answer. Say this out loud in the demo video.

### Tier policy, the dynamic-storage pattern

Do not dump everything into entities. The tier an observation lives in is a decision Cairn makes and revises, and that migration is the thing the rubric rewards.

| Tier | API | What Cairn puts there |
|---|---|---|
| HOT · state | `set_state` | The live verdict and confidence for a counterparty under active evaluation. Rewritten in place |
| WARM · entities | `set_entity` | Durable facts: a counterparty's identity, its declared services, and any behaviour observed **three or more times**. Unique per (category, name) at the schema level, so a contradiction overwrites rather than duplicates |
| COLD · journal | `write_event` | Every single observation, append-only, in time order. This is the ledger and it is never rewritten |
| REFERENCE | `set_reference` | Things that rarely change: the ERC-8004 registration file, the ACP offering schema, Cairn's own scoring policy version |
| ARCHIVE | `archive_entity` | Counterparties dormant beyond the decay window, retired with a `reason` so a judge can see why |

**Promotion.** A pattern seen once stays in the journal. Seen three times within the window, Cairn promotes it to a WARM entity with a `first_seen`, `last_seen` and `n`, and writes a journal event recording the promotion itself. **Demotion.** An entity whose supporting observations all age past the decay window is archived with `reason="evidence aged out"`, not deleted. **Contradiction.** When a new observation contradicts a WARM entity, Cairn overwrites the entity (the UNIQUE constraint guarantees no drift) and writes both the old and new values into the journal, so the change is auditable even though the entity is not.

**The `forward` field is the session baton.** In `write_event(evaluated=..., acted=..., forward=...)`, the `forward` list holds what the next session must pick up: counterparties due for re-check, claims awaiting corroboration, reviewers whose weight is still provisional. On boot, Cairn's first act is to read the last N events and drain `forward`. That is cross-session coordination using their own designed primitive, and it is a one-line thing to point at in the README.

### The verdict engine

`judge/verdict.py`. Deterministic, not an LLM call:

1. Load the prior from HOT state. If none, cold-start from WARM entities.
2. Pull every observation for the counterparty from COLD, weighted by recency decay and by the reviewer weight of whoever surfaced it.
3. Compute standing: `grounded` if ≥3 corroborated observations and no unresolved contradiction; `suspect` if any observation directly contradicts a claim; `thin` if fewer than 3; `dormant` past the decay window.
4. Confidence is a function of observation count, corroboration rate and recency. Show the formula in the docs.
5. Write the new verdict to HOT, write a journal event with `evaluated`, `acted` and `forward`, and return the verdict with its basis, the list of observation ids it used.
6. Only then, optionally, call Claude to render the basis into a sentence of English. The rationale is presentation. The verdict is arithmetic over the record. A judge will ask which is which, and the answer has to be clean.

### The free-tier cap

The free tier caps `memory.db` at 5,242,880 bytes (their docs say 2 MB in one table and 5 MB in another, run `sibyl status` on day one and believe the CLI). You cannot index all 28,592 rated Base agents into that.

Decide on day one and write the decision into the README: either scope the indexed set to the ~2,000 ACP-active agents and say so, or subscribe at $29/month in USDC. Scoping is the more honest answer and it demos identically. What is not acceptable is silently truncating and letting a judge discover it.

### Data model, outside memory

Postgres holds only what memory must not: the raw chain event cache, the indexer cursor, and API rate-limit counters. If a fact influences a verdict, it lives in Sibyl Memory. If it is infrastructure, it lives in Postgres. Never split a fact across both.

---

## 11. The deletion test

Ship `scripts/deletion_test.py` in the repo root and document it in the README's first screen.

It runs the full verdict pipeline twice against the same counterparty: once normally, once with `memory/store.py` swapped for a null adapter whose every read returns empty and every write is a no-op. It prints both results side by side and exits non-zero if the memory-off run produces a usable verdict.

```
$ python scripts/deletion_test.py --agent 0x...

  memory ON      standing=grounded  confidence=0.87  basis=41 observations
  memory OFF     standing=thin      confidence=-     basis=0  observations
                 ↳ verdict engine returned NO_BASIS

  Cairn's core function is unavailable without the memory layer.  PASS
```

No other team will hand the judges the tool that proves their own gate. This costs half a day and it is the best half-day in the build.

---

## 12. Scoring the rubric, deliberately

Keep this table in `CLAUDE.md`. Every phase should be checkable against it.

| Criterion | Weight | How this build earns it |
|---|---|---|
| Memory load-bearing | 40 | Multi-tenant coordination across three tenants per verdict; five-tier promotion, demotion and archival with reasons; `forward` as the session baton; the deletion test as proof |
| Innovation & originality | 25 | The reviewer-weighting layer that ERC-8004 names as missing; grounding every verdict in a witnessed observation rather than a self-reported rating |
| Technical execution | 20 | Deterministic verdict engine, not an LLM in a trenchcoat; real chain reads; clean adapter boundary; tests; survives a second run |
| Pitch & presentation | 15 | The Stack plus the deletion toggle make the load-bearing moment visible in four seconds |
| PMF bonus | +10 | Publish Cairn's grounded scan of the indexed Base set as a public artifact a judge can check in five minutes, plus a waitlist and named design partners |
| Base stack | ×1.15 | Registry reads on Base, and an executed onchain write publishing a verdict as an attestation |
| Virtuals stack | ×1.25 | Registered ACP agent with a live offering, acting as neutral Evaluator on one real job in the demo |

**Partner stacks must do real work.** A claimed stack a judge cannot see exercised loses the bonus. Both of ours are on the critical path: without Base there is nothing to observe, and without ACP there is no evaluator role to occupy.

**Base.** Read the Identity and Reputation registries. Then write: publish each verdict as an attestation. The Validation Registry has no mainnet deployment, so a minimal attestation contract is a real contribution rather than a demo prop. Show one write landing in the demo, with the Basescan link on screen.

**Virtuals ACP.** `npm i -g @virtuals-protocol/acp-cli`, `acp configure`, `acp agent create`, `acp agent add-signer`, fund the wallet, `acp offering create`. Cairn lists one offering, *Counterparty dossier*, and takes the Evaluator role on one real job, earning the protocol-enforced 5%. Do the account setup before Sep 1; it is configuration, not code.

---

## 13. Build order, ten days

One phase per session. Solo, so the order is ruthless: the memory layer and the demo beat come first, polish is last and expendable.

| Day | Phase | Ships |
|---|---|---|
| 1 | 0 | Repo, monorepo layout, tokens, `CairnMark`, fonts, `.env.example`, Fly volume, `sibyl init` + `sibyl status` recorded in the README |
| 1-2 | 1 | The memory adapter and tier policy. Tests for promotion, demotion, contradiction and tenant isolation. **No UI.** |
| 2-3 | 2 | The Base indexer. Real registry reads, observation extraction, journal writes |
| 3-4 | 3 | The verdict engine and reviewer weighting. Tests. `scripts/deletion_test.py` |
| 4 | 4 | FastAPI: lookup, observations, verdict, `?memory=off` |
| 5 | 5 | `packages/ui` per part 6 plus `/kitchen-sink`. The Stack and the deletion toggle, wired to the real API |
| 6 | 6 | Landing page, section by section from part 7, in order, verbatim copy |
| 7 | 7 | Explorer per part 8 |
| 8 | 8 | ACP: agent registration, offering, one real job as Evaluator. Base: attestation write |
| 9 | 9 | Docs, README, memory implementation note. PMF artifact published |
| 10 | 10 | Record the demo. Polish only what the video shows. Submit early in the day, not at 23:59 |

**Cut list, in order, if you fall behind:** docs beyond the README, the reviewer view in the explorer, the attestation contract (fall back to `giveFeedback()`), the footer ticker. **Never cut:** the deletion test, the Stack, the cold-start recall beat, the ACP job.

---

## 14. Paste-ready phase prompts

Give Claude Code this brief plus the attachments once, then paste one of these per session.

> **Phase 0.** Read `docs/BRIEF.md` fully before writing code. Scaffold the repo exactly as in part 2. Install `cairn-tokens.css` as the only source of colour, spacing, radius and motion. Build `CairnMark` from part 3 wired to the four standings, and generate the favicon and app icon set. Set up the Python side with `sibyl-memory-client`, confirm `MemoryClient.local()` works offline with no credentials, and print `sibyl status` into the README. Strict TypeScript, ruff and mypy on the Python, `.env.example` covering every variable. No page content. Stop and show me the file tree plus the mark rendering.

> **Phase 1.** Build `apps/agent/memory/store.py` per part 10. It is the only module allowed to import `sibyl_memory_client`. Implement tenancy, the tier policy, promotion at three occurrences, demotion by decay window, contradiction handling, and the `forward` baton drained on boot. Write tests that prove: two tenants cannot see each other's rows; a third occurrence promotes a journal pattern to a WARM entity and records the promotion; a contradicting write overwrites the entity and journals both values; an aged entity archives with a reason. Tests over everything. No UI, no chain calls.

> **Phase 2.** Build `apps/agent/observe/base.py`. Read the ERC-8004 Identity and Reputation registries on Base via web3.py at the addresses in part 2. Extract observations, resolve off-chain registration files, hash raw evidence, and write each observation to COLD through the phase 1 adapter. Cursor-based, resumable, and it must not re-write an observation it has already seen. Scope the indexed set per part 10's cap decision and record the scope in the README. Report how many agents and observations you indexed.

> **Phase 3.** Build `judge/verdict.py` and the reviewer weighting per part 10. The verdict is deterministic arithmetic over the record, no LLM call in the decision path. Then write `scripts/deletion_test.py` per part 11 with the exact output shape shown there, exiting non-zero if a memory-off run produces a usable verdict. Tests for each standing transition and for the confidence formula.

> **Phase 5.** Build the components in part 6 and a `/kitchen-sink` route showing every one at every state. Then the Stack to the exact spec in part 5: five real tier bands, one stone per observation, width for weight, fill for grounding, deterministic hash-derived tilt, keyboard-navigable stones. Then the deletion toggle, wired to the real `?memory=off` API flag, not a client-side fake. Measure the stack's frame time with 200 stones and report it. Do not start the landing page.

> **Phase 6.** Build the landing page section by section from part 7, in order, using the copy verbatim. Follow the blend rules in part 4 and the motion budget in part 6: exactly three motion moments. Every section is the claim / basis split, and the basis column shows real data from the API, never placeholders. After each section, screenshot at 390px and 1440px and check rhythm, spacing and type scale against `refs/`, then fix what is off before moving on. Report Lighthouse at the end.

> **Phase 7.** Build the explorer per part 8. Dossier view, reviewer view, the prior panel, cmd+K search. Every screen gets a real loading, empty and error state in the product's voice. No route may 404, no placeholder data, no invented metrics.

> **Phase 8.** Register Cairn on ACP with the CLI per part 12, create the *Counterparty dossier* offering, and run one real job end to end with Cairn as Evaluator, driven by subprocess with `--json`. Then the Base write: publish a verdict as an attestation and surface the tx hash in the explorer. Both must be exercisable live on camera.

> **Phase 9.** Write the README as the judge's entry point: what it does, where memory is written and read with file and line links a judge can follow in under two minutes, which partner stacks and where, the "how memory made this possible" note, and the Prior Work declaration. Then the docs in part 9. Then publish the PMF artifact.

---

## 15. Demo video, planned as a build artifact

Two to five minutes. Record it on day 10, but design for it from day one, the rubric gives 15 points for this and the gate itself is decided on the video.

1. **0:00-0:25 The problem.** One sentence, then the four stat rows on screen. Name the source.
2. **0:25-1:10 The product.** Look up a counterparty in the explorer. The Stack builds. Point at a stone, open its observation, follow the link to Basescan.
3. **1:10-1:50 The cold-start beat.** *One continuous unedited take, no cuts.* Kill the process on camera. Show the terminal. Start a fresh process. Look up the same counterparty. It returns the same dossier and the same verdict, built from the journal, plus the priors it drained from `forward`. Have a clock or `git rev-parse HEAD` visible on screen throughout, per the rules.
4. **1:50-2:20 The deletion test.** Run `python scripts/deletion_test.py` in the terminal. Let the judges watch it fail with memory off.
5. **2:20-3:00 The partner stacks.** The ACP job completing with Cairn as Evaluator, the 5% landing. The attestation write, with the Basescan link on screen.
6. **3:00-3:30 The memory note.** Say the three tenants out loud. Say promotion and demotion out loud. Say `forward` out loud. The judges are scoring a specific rubric line; make it easy to tick.

Do not narrate over a slide deck. Every claim in the video is shown running.

---

## 16. What to attach to Claude Code

**Files, dropped in the repo rather than pasted in chat:**

1. `cairn-mark.svg`, `cairn-mark-standing.svg`, `cairn-icon.svg`, `cairn-app-icon.svg` → `apps/web/src/assets/`
2. `cairn-tokens.css` → `apps/web/src/styles/tokens.css`
3. This file → `docs/BRIEF.md`
4. `CLAUDE.md` → repo root, with the part 12 rubric table in it
5. The hackathon rules page, saved → `docs/RULES.md`

**Reference screenshots** → `refs/`, full-page captures at 1440px: `refs/t54-hero.png`, `t54-product.png`, `t54-research.png`, `kite-nav.png`, `kite-hero.png`, `aptos-hero.png`, `aptos-panel.png`, `aptos-stat.png`. The two skillui extractions you already have go in `refs/t54-design/` and `refs/agentpassport-design/`: Claude Code reads their `DESIGN.md` automatically. **Use them as measurement of spacing and type scale only. Override every colour and every typeface with Cairn tokens.**

**Environment (`.env.local`, never in a prompt):** `ANTHROPIC_API_KEY`, `BASE_RPC_URL`, `SIBYL_DB=/data/memory.db`, `CAIRN_ATTESTOR_KEY`, `ACP_AGENT_ADDRESS`, `DATABASE_URL`, `NEXT_PUBLIC_API_URL`.

**Tooling worth installing before phase 5:**
- `npx skills add emilkowalski/skills`: `animate` while building the Stack, `review-animations` at the end of phases 5 and 6. The gap between your build and Aptos's is easing curves and restraint, nothing else.
- A browser MCP (Playwright or Chrome DevTools) so Claude Code can screenshot `localhost` and compare against `refs/` itself. Without it you are the feedback loop and you will lose a day.

---

## 17. Guardrails

1. No invented metrics, no fake logos, no "trusted by" rows. Every number on the site comes from the indexer or is attributed to its source.
2. No copied copy strings, assets, icons, illustrations or typefaces from t54, Kite, Aptos or Sibyl. Structure and rhythm only.
3. No colour, radius, shadow or duration that is not in the token file. No gradients anywhere.
4. Colour means evidence. If lapis or oxide appears where Cairn cannot point at an observation, it is a bug.
5. Exactly three motion moments. Everything else is a state change.
6. The verdict is never produced by an LLM. The rationale may be; the decision may not.
7. Only `memory/store.py` imports `sibyl_memory_client`. Everything else goes through the interface.
8. No fact that influences a verdict lives outside Sibyl Memory.
9. `?memory=off` genuinely bypasses the memory layer. Never fake the empty state client-side.
10. Every animation respects `prefers-reduced-motion`. Every interactive element is keyboard reachable with a visible focus ring.
11. The repo is MIT, public, with real commit history inside the build window, and the README carries an honest Prior Work declaration covering the brand and design work done before Sep 1.
12. If a section cannot be built without inventing a number, cut the section.

---

## 18. Craft standard

Judges see 126 submissions. Most will look like they were generated. The fastest way to lose points that the rubric never names is to look like one of them, so this section is not style advice, it is a checklist a session can be failed against.

Two failure modes to avoid, and they are different. **Cheap** is when the work looks rushed: placeholder data, broken links, one screen polished and the rest ignored. **Slop** is when the work looks generated: the em-dashes, the triads, the gradient hero, the icon grid, the words nobody says out loud. Slop is worse, because it makes a judge stop reading and assume the code underneath is also generated.

### Punctuation and prose

**No em-dashes or en-dashes. Anywhere.** Not in the UI, not in the docs, not in code comments, not in commit messages, not in the README. Use a comma, a colon, a full stop, or parentheses. This one rule catches more machine-written text than any other.

Also banned: the ellipsis character (write three dots), decorative arrows in prose (fine inside diagrams and terminal output), and curly quotes in code.

**Words that are not in the product's vocabulary.** Never write: delve, leverage (as a verb), robust, seamless, seamlessly, elevate, unlock, empower, harness, revolutionize, game-changing, cutting-edge, blazing fast, enterprise-grade, production-ready, best-in-class, comprehensive, holistic, ecosystem (except when naming an actual blockchain ecosystem), journey, in today's landscape, at its core, it's worth noting.

**Sentence shapes to avoid.** No "It's not just X, it's Y." No "X isn't merely Y, it's Z." No rule-of-three lists where two items would do ("fast, simple, and secure"). No opening a section by restating the heading as a sentence. No closing a section with a summary of what was just said.

Write short declarative sentences about what the thing does. If a sentence could appear unchanged in any other startup's copy, delete it.

### Never in this repo

- **No emoji.** Not in headings, not in the README, not in commit messages, not in the UI. Zero.
- **No badges** in the README unless the thing they claim actually exists and passes. A build-passing badge with no CI is a lie a judge will check.
- **No "Built with love", no "Made by", no ASCII art signature.**
- **No fake social proof.** No testimonials, no "Trusted by" logo row, no user counts we cannot produce from the database.
- **No placeholder anything.** No lorem, no `example.com`, no `John Doe`, no stock avatars, no invented metric to make a card look full. If the data does not exist, cut the component.
- **No TODO comments** in shipped code. Either do it or open an issue.
- **No commented-out code.** Git remembers.
- **No `console.log`** left behind. No `print()` debugging in the agent.
- **No swallowed errors.** A bare `except: pass` or an empty `catch {}` is an automatic fail on technical execution when a judge greps for it, and they do.

### Visual tells that mark a page as generated

- No gradient text, no gradient buttons, no gradient backgrounds, no mesh, no glow, no glassmorphism.
- No three-column feature grid where each card is an icon, a bold noun and one line of grey text. If the page needs to explain three things, use the claim and basis split from part 4.
- No shadcn defaults. The neutral greys and `--radius: 0.5rem` are recognisable on sight. Every component gets Cairn tokens or it does not ship.
- No default Tailwind palette. If `slate-900`, `indigo-600` or `gray-50` appears in a class name, it is a bug.
- No count-up animated numbers. No parallax. No floating shapes. No typewriter effect. Part 6 allows three motion moments and that is the whole budget.
- No hero screenshot floating at a 15 degree angle with a drop shadow.
- No icon on every heading.

### Code quality a curious judge will actually check

The rubric says technical execution must survive "a second run and a curious judge." Assume they will clone the repo cold and run it.

- The quickstart in the README works on a fresh machine. Test it in a clean container before Sep 10.
- No secret, key, RPC URL or `.env` file is ever committed. Check the diff before every push.
- Comments explain why, never what. `# increment counter` above `counter += 1` is noise. `# three occurrences, not two: two is coincidence in this dataset` is worth reading.
- Type hints on every Python function signature. Strict TypeScript, no `any`.
- Tests assert real behaviour, not that a function returns something. A test that cannot fail is worse than no test.
- Commit messages describe the change in the product's vocabulary, lowercase, no prefix soup, no emoji. `promote journal patterns to entities at three occurrences` beats `feat: add promotion logic`.
- Every dependency in `requirements.txt` and `package.json` is one we actually import.

### The self-check before a session ends

Run this list before saying a phase is done:

1. Scan the diff for em-dashes, en-dashes and emoji: `git diff | grep -P '\\xe2\\x80\\x94|\\xe2\\x80\\x93'` and `git diff | grep -P '[\\x{1F300}-\\x{1FAFF}]'`. Any hit is a fix, not a discussion.
2. Read the copy out loud. Anything you would not say to a person gets rewritten.
3. Grep for `TODO`, `console.log`, `print(`, `any`, `lorem`, `example.com`, `placeholder`.
4. Open every new screen at 390px. If it was only ever checked at 1440px, it is not done.
5. Ask: would this look identical if the product were about something else entirely? If yes, it is generic, and part 4 says rebuild it around the claim and basis split.
