# Submission field playbook

Everything the build page asks for, drafted in advance. Team page: `hack.sibyllabs.org/team/prime-works-4c21`. Keep that link private; anyone with it can edit the submission.

The page marks each milestone the moment you paste the matching artifact, so fill it in as you go rather than at the deadline. **You can edit until submissions close, so paste rough versions early.** A saved rough answer beats a perfect one you did not have time to write.

Four milestones: Public repo, Demo video, 2 posts, Memory fields.

---

## What the page does NOT ask for

There is **no live URL field**. No deployed-site requirement, no contract address field, no staging link. Judges score the repo, the video, the posts and the memory fields. That is the whole surface.

So the live site is not a scoring requirement. It still earns its keep in three other ways, which is why the build plan keeps it:

1. **PMF bonus.** That bonus needs a publicly verifiable artifact a judge can check in five minutes. A working explorer with real indexed Base data is exactly that, and it is far more convincing than a waitlist count.
2. **The demo video.** Recording against a deployed site rather than `localhost:3000` reads as a product rather than a project. Same effort, better impression.
3. **The README and the posts.** Both link to it, and both are scored.

Put the URLs in the README header and in the posts. Nothing breaks if the site is down on judging day, which is the correct amount of risk to carry.

---

## Field 1: Public repo URL

`https://github.com/<you>/cairn`

Public by Sep 1. MIT licence present. Real commit history inside the window. The README is what a judge reads first, so treat it as a scored deliverable, not documentation.

## Field 2: Demo video URL

YouTube unlisted is fine, and safer than Loom for a judge in another timezone. 2 to 5 minutes. Structure is in `BRIEF.md` part 15.

The one thing that cannot be compromised: **the cold-start beat is a single continuous unedited take** with a clock or `git rev-parse HEAD` visible on screen. Kill the process, show the terminal, start a fresh one, look up the same counterparty, get the same dossier back. If that segment has a cut in it, the gate is at risk.

## Field 3: Post URLs (2 or more)

Build-in-public posts on X or Farcaster. Tag `@sibylcap` and each partner you claim.

**Post 1, around Sep 6.** Lead with the deletion toggle as a short screen recording. It is the most legible thing you will build.

> Most agent reputation on Base is fake. 90.6% of ERC-8004 reviewers show coordinated Sybil behaviour; strip them out and 86.8% of rated agents have no valid feedback left.
>
> Cairn only records what it witnessed itself. Here is what happens when you delete its memory.
>
> Building for @sibylcap's memory hackathon with @base and @virtuals_io.

**Post 2, around Sep 9.** Lead with the PMF artifact, the grounded scan of your indexed set.

> We ran Cairn over [N] agents on Base and rebuilt their records from scratch, using only interactions we watched happen.
>
> [N] hold up. [N] do not. Full results and method: [link]
>
> Every verdict points at the observations it came from. @sibylcap @base @virtuals_io

Do not post more than three times. A flood of build-log posts reads as padding.

---

## Field 4: What breaks when memory is deleted?

One or two sentences. The page says this plus a primitive marks the memory milestone and is the core of how memory PMF is judged, so it carries real weight for its length.

Draft:

> Cairn has nothing to reason over. Its entire product is an accumulated record of interactions it witnessed, so with the memory layer removed there are no dossiers, no priors, no reviewer weights and no basis to cite, and the verdict engine returns NO_BASIS rather than a degraded guess. `scripts/deletion_test.py` in the repo runs the same lookup with and without memory and exits non-zero if the memory-off run ever produces a usable verdict.

Why this works: it names the concrete thing that disappears, states the failure mode in the product's own vocabulary, and hands the judge a command they can run. Most teams will write something that amounts to "it would be less personalised", which passes the gate and scores at the floor.

---

## Field 5: Memory walkthrough

Three lines. The page says judges score the 40% from this, which makes it the highest value-per-word field in the entire submission. It exists so a judge can score memory **without watching the video**, so it has to stand alone.

Draft:

> **Persist:** every interaction we witness (ACP job outcome, escrow settlement, delivery hash mismatch) as an append-only observation in the COLD journal, under a memory tenant scoped to that counterparty. Behaviour seen three or more times is promoted to a WARM entity; evidence that ages out is archived with a written reason; a contradicting observation overwrites the entity and journals both values.
>
> **Recall (fresh session):** on boot Cairn drains the `forward` list from its last journal events, then a lookup reloads that counterparty's tenant, pulls its priors from HOT state and its evidence from COLD, and switches into each reviewer's own tenant to weight their past claims by how often we later corroborated them. Three separate tenants are read to produce one answer.
>
> **Decision it changes:** the verdict, its confidence and its cited basis, which is what an agent uses to decide whether to fund an escrow. Same counterparty, same code, memory removed: NO_BASIS.

Three things are doing the work there, and they map directly onto the rubric's phrase about coordination and dynamic-storage patterns topping the band: **multiple tenants coordinating**, **data moving between tiers over time**, and **a concrete decision that flips**. Keep all three when you edit it.

---

## Field 6: Memory primitives you used

Chips on the page: recall, entities, semantic search, temporal / time-travel, summarization, reflection, consolidation.

Tick only what is genuinely load-bearing. A judge who opens the repo and finds a ticked primitive with no code behind it will discount the ones that are real.

| Primitive | Tick it? | What backs it |
|---|---|---|
| **recall** | Yes | `load_prior()` and `gather_basis()` in `judge/verdict.py` |
| **entities** | Yes | WARM tier, `set_entity` / `get_entity`, promoted behaviour |
| **semantic search** | Yes | `m.search()` over FTS5, cross-tier, used to find related observations |
| **temporal / time-travel** | Yes | `read_events(since=, until=)`, recency decay, the prior panel showing what we believed before |
| **consolidation** | Yes | promotion at three occurrences, contradiction collapse via the UNIQUE constraint, archival with a reason |
| **reflection** | Yes, if reviewer weighting ships | Cairn scoring its own past judgments against later outcomes is reflection in the literal sense |
| **summarization** | Only if the rationale renderer ships | Claude turning a basis into a sentence. Marginal and presentational. Leave it unticked if phase 3 runs late |

Six of seven is a strong, honest answer. Do not tick all seven for the sake of it.

---

## Before you mark ready

Mark ready on **Sep 10 morning**, not at the deadline. You can unmark it and keep editing until submissions close, so there is no reason to wait.

- [ ] Repo public, MIT licence, real in-window commit history
- [ ] README opens with the memory map, file paths a judge can follow in two minutes
- [ ] `python scripts/deletion_test.py` runs clean from a fresh clone on a clean machine
- [ ] Demo video public and playable in an incognito window
- [ ] Cold-start beat is one unedited take with a visible timestamp or commit hash
- [ ] Two post URLs live, tagging `@sibylcap` and each partner claimed
- [ ] "What breaks" and the three-line walkthrough pasted and saved
- [ ] Memory primitives ticked, each with code behind it
- [ ] Both partner stacks declared **and visibly exercised in the video**
- [ ] Prior Work declaration honest and complete
- [ ] Every link in the submission opened in an incognito window and confirmed working
