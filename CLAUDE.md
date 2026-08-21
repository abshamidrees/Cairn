# CLAUDE.md for Cairn

Read `docs/BRIEF.md` in full before writing any code. It is the source of truth. This file is the part that stays loaded.

## What we are building

Cairn is a memory-native trust layer for agent commerce. It watches real interactions on Base and Virtuals ACP, keeps an isolated dossier per counterparty in Sibyl Memory, and returns a **verdict** with a **confidence** and a **basis**: the specific observations the judgment rests on.

Submission for the Sibyl Labs Memory Hackathon. Build window Sep 1-10, 2026.

## The scoring table, check every phase against this

| Criterion | Weight | How we earn it |
|---|---|---|
| Memory load-bearing | 40 | Three-tenant coordination per verdict; five-tier promotion/demotion/archival; `forward` as session baton; the deletion test as proof |
| Innovation & originality | 25 | Reviewer weighting, the layer ERC-8004 says is missing; verdicts grounded in witnessed observations, not self-reported ratings |
| Technical execution | 20 | Deterministic verdict engine, real chain reads, clean adapter boundary, tests, survives a second run |
| Pitch & presentation | 15 | The Stack + the deletion toggle make the load-bearing moment visible in four seconds |
| PMF bonus | +10 | Public grounded scan of the indexed Base set, waitlist, named design partners |
| Base stack | ×1.15 | Registry reads plus an executed on-chain attestation write |
| Virtuals stack | ×1.25 | Registered ACP agent, live offering, neutral Evaluator on a real job |

If a change does not move a row in this table, it is probably not worth the session.

## Vocabulary, use these words everywhere

**observation** (one witnessed event) · **dossier** (one counterparty's record) · **grounding** (tying a claim to an observation) · **verdict** (carries a **confidence** and a **basis**) · **prior** (belief before the latest observation) · **standing** (`grounded` / `thin` / `suspect` / `dormant`).

Never write *reputation score*, *rating*, *review* or *trust score*. Not in the UI, not in the API, not in a variable name, not in a commit message.

## Hard rules

1. Only `apps/agent/memory/store.py` imports `sibyl_memory_client`. Everything else goes through the interface, that boundary is what makes the deletion test a two-line swap.
2. **The verdict is never produced by an LLM.** It is arithmetic over the record. The rationale sentence may be rendered by Claude; the decision may not.
3. No fact that influences a verdict lives outside Sibyl Memory. Postgres holds infrastructure only: the chain event cache, the indexer cursor, rate limits.
4. `?memory=off` genuinely bypasses the memory layer. Never fake the empty state client-side, a judge will open the network tab.
5. No colour, radius, shadow or duration that is not in `apps/web/src/styles/tokens.css`. No gradients anywhere.
6. **Colour means evidence.** Lapis only where Cairn can point at an observation it holds. Oxide only where its own record contradicts a claim. `thin` is deliberately colourless. A colour without an observation behind it is a bug.
7. Exactly three motion moments in the whole product (brief part 6). Everything else is a state change.
8. Display type is Newsreader 400, never bold. Italic is reserved for the verdict line and nothing else.
9. No invented metrics, no fake logos, no placeholder data, no lorem. If a section needs a number we do not have, cut the section.
10. Every animation respects `prefers-reduced-motion`. Every interactive element is keyboard reachable with a visible focus ring.

## Verified environment constraints, do not design around these differently

- **Sibyl Memory is Python-only.** No JS SDK exists. `MemoryClient.local(path)` over SQLite + FTS5, fully offline, no credentials needed.
- **`memory.db` needs a persistent disk.** There is no hosted mode. Vercel serverless cannot hold it. Agent + API run on one Fly.io machine with a volume; only `apps/web` goes to Vercel.
- **`learn()`, `lint()` and skill proposals are paid-tier gated** and raise `TierGateError` on free. Do not build on them. Our promotion and decay logic is ours.
- **Free tier caps the DB at 5,242,880 bytes.** Run `sibyl status` and believe the CLI over the docs. The indexed set is scoped to fit, see `docs/BRIEF.md` part 10.

## Craft standard

Full version in `docs/BRIEF.md` part 18. The rules that get broken most:

1. **No em-dashes or en-dashes anywhere.** Not in the UI, docs, comments, or commit messages. Use a comma, a colon, a full stop, or parentheses. Also no ellipsis character, no curly quotes in code.
2. **No emoji.** Zero. Not in headings, the README, the UI, or commit messages.
3. **Banned words:** delve, leverage (verb), robust, seamless, elevate, unlock, empower, harness, revolutionize, game-changing, cutting-edge, blazing fast, enterprise-grade, production-ready, comprehensive, journey, at its core, it's worth noting.
4. **Banned sentence shapes:** "It's not just X, it's Y." Rule-of-three lists where two would do. Restating a heading as the first sentence under it.
5. **No fake anything:** no placeholder data, no lorem, no example.com, no testimonials, no "Trusted by" row, no README badge for a thing that does not exist.
6. **No gradients, no glow, no glassmorphism, no three-column icon-and-blurb feature grid, no count-up numbers, no tilted hero screenshot.**
7. **No shadcn defaults and no default Tailwind palette.** If `slate-900`, `indigo-600` or `gray-50` appears in a class name, it is a bug.
8. **No `TODO`, no commented-out code, no `console.log`, no `print()` debugging, no `except: pass`, no empty `catch {}`.**
9. Comments explain why, never what. Type hints on every Python signature. No `any` in TypeScript.
10. Commit messages: lowercase, product vocabulary, no prefix soup, no emoji. `promote journal patterns to entities at three occurrences`, not `feat: add promotion logic`.

Before ending a session: grep the diff for `-`-family dashes and emoji, grep for `TODO`, `console.log`, `lorem`, `placeholder`, and open every new screen at 390px.

## Working style

- One phase per session, in the order in `docs/BRIEF.md` part 13. Paste-ready prompts are in part 14.
- Tests before UI for anything in `apps/agent`.
- Complete file rewrites are preferred over partial patches.
- Screenshot `localhost` at 390px and 1440px and compare against `refs/` before calling a section done.
- Commit messages use the product vocabulary. The commit log is part of the submission.
