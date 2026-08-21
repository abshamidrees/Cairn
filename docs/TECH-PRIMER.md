# Cairn, explained plainly

This is the "what actually happens" document. No jargon that isn't defined. Read it before you run the first Claude Code prompt so you can tell when something is going wrong.

---

## 1. The problem, in one paragraph

AI agents are starting to pay each other. On Virtuals ACP, one agent hires another, money sits in escrow, work gets delivered, escrow releases. That works fine when both parties are known. It falls apart when they aren't, because there is no reliable way to check a stranger. The system that was supposed to provide that check, the ERC-8004 Reputation Registry on Base, is broken in a measurable way: anyone can leave feedback about anyone, without ever having transacted with them, for a fraction of a cent. Researchers measured it in July 2026 and found that when you strip the coordinated fake feedback, 86.8% of rated agents on Base have no valid feedback left at all.

So the scores exist, and they mean nothing.

## 2. What Cairn does about it

Cairn refuses to accept anyone's word for anything. It only records things it watched happen.

That's the entire idea. Everything else is plumbing.

When an ACP job completes, Cairn saw it complete. When an escrow gets rejected, Cairn saw the rejection. When a delivery hash doesn't match what was promised, Cairn computed both hashes itself. Each of those is an **observation**: a single event, with a timestamp, a source link, and a content hash.

Cairn stores every observation. Over weeks it accumulates a **dossier** on each agent: not a score, a pile of things that happened. When you ask "should I pay `0xabc...`?", Cairn doesn't return a number from a database. It runs the arithmetic over that pile and returns three things:

- a **standing**: `grounded`, `thin`, `suspect`, or `dormant`
- a **confidence**: how sure it is, given how much it has seen and how recently
- a **basis**: the actual list of observations the answer rests on, each one clickable

The basis is the product. Anyone can give you a number. Cairn shows its work.

## 3. Why memory isn't a feature here

This is the part that has to be crystal clear, because 40 of the 110 available points ride on it.

Cairn has no model to fall back on. There is no "estimate" it can produce from first principles. The answer to "has this agent behaved well before?" lives *entirely* in what was previously observed and written down. Delete the stored observations and the question becomes unanswerable, not harder, unanswerable.

Compare that to a typical hackathon entry: "a chatbot that remembers your preferences." Delete its memory and it's still a chatbot. It's worse, but it works. That's a wrapper, and the rules say wrappers are disqualified before scoring even starts.

`scripts/deletion_test.py` is how we prove which one we are. It runs the same lookup twice, once with memory and once with a null adapter, and shows the second one failing.

## 4. The five tiers, and why we don't just dump everything in one place

Sibyl Memory isn't a key-value store. It has five tiers, each with its own API, and choosing the right one is a real decision. This is the part the rubric calls "dynamic-storage patterns," and it's where the top of the band is.

| Tier | Sibyl API | What Cairn puts there |
|---|---|---|
| **HOT** · state | `set_state` / `get_state` | The live verdict for a counterparty being evaluated right now. Rewritten in place, always current |
| **WARM** · entities | `set_entity` / `get_entity` | Durable facts, an agent's identity, its declared services, any behaviour seen three or more times |
| **COLD** · journal | `write_event` / `read_events` | Every single observation, append-only, in time order. This is the ledger and it is never rewritten |
| **REFERENCE** | `set_reference` / `get_reference` | Things that rarely change, an ERC-8004 registration file, an ACP offering schema, our own scoring policy version |
| **ARCHIVE** | `archive_entity` | Counterparties gone quiet past the decay window, retired with a written reason |

Three movements between those tiers are what make this sophisticated rather than tidy:

**Promotion.** You see an agent deliver late once, that's noise, it stays in the journal. You see it three times, that's a pattern, and Cairn promotes it to a WARM entity with a `first_seen`, a `last_seen` and a count. It also writes a journal event recording that the promotion happened, so the decision itself is auditable.

**Demotion.** An entity whose supporting observations have all aged past the decay window gets archived with `reason="evidence aged out"`. Not deleted, archived, because "we used to believe this and here's why we stopped" is information.

**Contradiction.** Sibyl enforces `UNIQUE (tenant_id, category, name)` at the database schema level. Two rows describing the same thing literally cannot exist. So when a new observation contradicts a WARM entity, the entity is overwritten, but both the old and new values go into the journal. The current belief is always single and clean; the history of how it changed is always complete.

## 5. Tenants, and why this is a coordination system

`MemoryClient.set_tenant(id)` switches which isolated slice of the database you're reading and writing. Everything is scoped by `tenant_id`; one tenant physically cannot see another's rows. I verified this works.

Cairn uses three kinds of tenant:

- `cp:base:0xabc...`: one per counterparty
- `rv:0xdef...`: one per reviewer
- `cairn:self`: Cairn's own operating state and calibration

Now here's the interesting part. Producing one verdict about counterparty A means:

1. switch to A's tenant, read its dossier and priors
2. for each reviewer who has ever made a claim about A, switch to *that reviewer's* tenant and read how often their past claims were later corroborated
3. weight A's evidence by those reviewer weights
4. switch back to A's tenant and write the new verdict
5. switch to each reviewer's tenant and update their weight based on how this turned out

Three separate memory identities coordinate to produce one answer, and the answer changes what gets written back to all of them. That is a coordination pattern, not recall. **Say this out loud in the demo video**: it's the single highest-value sentence you will say.

## 6. Reviewer weighting, the actually novel bit

The ERC-8004 spec admits its own reputation numbers are only meaningful if some *other* system scores the reviewers, and then says, in effect, that system doesn't exist yet.

Cairn is that system, and it can only exist because of memory.

The logic is simple to state and impossible without history: a reviewer who rated twelve agents highly, three of which Cairn later watched fail, is a reviewer whose future claims count for less. You cannot compute that in one session. You need the original claim from months ago, the outcome from last week, and a link between them. That link is what Cairn stores.

## 7. The verdict engine is arithmetic, not a prompt

Important, and a judge will probe it.

The verdict is computed:

1. load the prior from HOT state (or cold-start from WARM entities)
2. pull every observation from COLD, weighted by recency decay and reviewer weight
3. `grounded` if ≥3 corroborated observations with no unresolved contradiction; `suspect` if anything directly contradicts a claim; `thin` if fewer than 3; `dormant` past the decay window
4. confidence is a documented function of count, corroboration rate and recency
5. write the new verdict to HOT, write a journal event, return the verdict with its basis

*Only then*, optionally, Claude renders that basis into a readable sentence.

The rationale is presentation. The decision is arithmetic over the record. If someone asks "is this just an LLM guessing?", the answer has to be clean, and it is.

## 8. The shape of the running system

```
      Base chain                    Virtuals ACP
          │                              │
          ▼                              ▼
   ┌──────────────────────────────────────────┐
   │  observe/  - watchers                    │   turns real events
   │  base.py · acp.py · x402.py              │   into observations
   └───────────────────┬──────────────────────┘
                       │  record_observation()
                       ▼
   ┌──────────────────────────────────────────┐
   │  memory/store.py                         │   ← the ONLY module that
   │  the one door to Sibyl Memory            │     imports the Sibyl SDK
   │  tenancy · tiers · promotion · decay     │
   └───────────────────┬──────────────────────┘
                       │  load_prior() / gather_basis()
                       ▼
   ┌──────────────────────────────────────────┐
   │  judge/verdict.py    deterministic        │
   │  standing · confidence · basis            │
   └────────┬──────────────────────┬───────────┘
            │                      │
            ▼                      ▼
      publish/  → Base       api/ → FastAPI → apps/web
      attestation            /v1/lookup      landing · explorer
```

Two things about this diagram matter more than the rest.

**`memory/store.py` is the only door.** Nothing else imports the Sibyl SDK. That's not tidiness, it's what makes the deletion test a two-line swap instead of a refactor, and it's what a judge will check when they want to know whether the memory is real or bolted on.

**The web app never talks to memory.** It talks to the API. That's why `?memory=off` can be a genuine backend bypass rather than a frontend fake.

## 9. Why the stack is split across two languages

You build in Next.js. Half of this is Python. Here's why, and it isn't negotiable:

Sibyl Memory ships as a Python package only. There is no JavaScript SDK. The memory lives in a SQLite file on disk that never leaves the machine, there's no hosted API to call from a serverless function. So anything that touches memory has to be a Python process running on a box with a real disk.

That gives a clean split, and it plays to your strengths:

- **`apps/agent`**: Python, on one Fly.io machine with a mounted volume at `/data`. Claude Code writes almost all of this. It's the load-bearing 40 points.
- **`apps/web`**: Next.js 15 on Vercel, talking to the API over HTTP. This is your home turf, and it's where the 15 presentation points are won.

Do not try to put the memory on Vercel. It will appear to work in dev and lose everything on every deploy.

## 10. What good looks like at each stage

A checklist for telling whether a phase actually landed.

**Memory adapter (phase 1).** Two tenants cannot see each other's rows. A third occurrence promotes a journal pattern to an entity and records the promotion. A contradicting write overwrites the entity and journals both values. An aged entity archives with a reason. All four have tests.

**Indexer (phase 2).** It's resumable, kill it, restart it, it picks up from the cursor. It never writes the same observation twice. You can state how many agents and how many observations it indexed.

**Verdict engine (phase 3).** No LLM call anywhere in the decision path. Every standing transition has a test. `deletion_test.py` exits non-zero when you sabotage it.

**The Stack (phase 5).** Stone tilts are derived from a hash of the observation id, so they're identical across renders. The deletion toggle hits the real API. Stones are keyboard reachable.

**Landing (phase 6).** Every number on the page came from the API or is attributed to its source. No section needed an invented figure to work.

**Partner stacks (phase 8).** You can run both live, on camera, without a rehearsal.
